"""Offline regression coverage for first-start, safe upload and delivery evidence."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from activation_runtime import (
    ActivationError, ActivatorLifecycle, AmbiguousActivationError, FILE_CREATED,
    PrivateStore, complete_blob_url, put_complete_increment, tool_result,
    verify_automatic_delivery,
)
from manage_activation import main, resolve_scope


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = "00000000-0000-0000-0000-000000000001"
ACTIVATOR = "00000000-0000-0000-0000-000000000002"
RULE = "00000000-0000-0000-0000-000000000003"
PIPELINE = "00000000-0000-0000-0000-000000000004"
LAKEHOUSE = "00000000-0000-0000-0000-000000000005"
FOLDER = "00000000-0000-0000-0000-000000000006"
TENANT = "00000000-0000-0000-0000-000000000007"
SUBJECT = "/Files/increment/donation_events_001.csv"
SOURCE = f"/tenants/{TENANT}/workspaces/{WORKSPACE}/items/{LAKEHOUSE}"
FILES_ROOT = f"https://onelake.dfs.fabric.microsoft.com/{WORKSPACE}/{LAKEHOUSE}/Files"
PREFIX = "System.Action.FabricItem."


def evidence():
    return {
        "workspace_id": WORKSPACE, "pipeline_id": PIPELINE, "rule_id": RULE,
        "subject": SUBJECT, "source": SOURCE, "expected_bytes": 43, "uploaded_bytes_verified": True,
        "events": [{"___id": "file-event", "___subject": SUBJECT, "___source": SOURCE,
                    "___type": FILE_CREATED, "api": "PutBlob", "contentLength": "43"}],
        "history": {"activations": [{"activationTime": "2026-09-01T00:00:00Z", "properties": {
            "___id": "activation", "System.RuleId": RULE, PREFIX + "WorkspaceId": WORKSPACE,
            PREFIX + "ItemId": PIPELINE, PREFIX + "ItemType": "Pipeline", PREFIX + "JobType": "Pipeline",
            PREFIX + "Parameters.Type.String": FILE_CREATED, PREFIX + "Parameters.Subject.String": SUBJECT,
            PREFIX + "Parameters.Source.String": SOURCE,
        }}]},
        "jobs_before": [{"id": "manual-control"}],
        "jobs_after": [{"id": "manual-control"}, {
            "id": "automatic", "itemId": PIPELINE, "status": "Completed", "failureReason": None,
            "invokeType": "Manual", "startTimeUtc": "2026-09-01T00:00:03Z", "endTimeUtc": "2026-09-01T00:00:08Z",
        }],
        "manual_job_ids": {"manual-control"},
    }


class MemoryStore:
    def __init__(self):
        self.values = {}

    def write(self, key, value):
        if key in self.values:
            raise FileExistsError(key)
        self.values[key] = copy.deepcopy(value)


class FakeLifecycle(ActivatorLifecycle):
    def __init__(self, running):
        self.workspace_id, self.activator_id = WORKSPACE, ACTIVATOR
        self.running, self.calls = running, []
        self.sleeper = lambda _: None
        self.clock, self.timeout = lambda: 0, 60
        self.store = MemoryStore()

    def rules(self):
        return [{"uniqueIdentifier": RULE, "isRunning": self.running}]

    def _call(self, name, parameters):
        self.calls.append(name)
        self.running = name == "start_rule"
        return {"content": [{"type": "text", "text": "acknowledged"}]}


class Response:
    def __init__(self, body=b"", status=200, headers=None):
        self.content, self.status_code = body, status
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = body.decode("utf-8")
        self.request = type("Request", (), {"body": b""})()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def json(self):
        return json.loads(self.content)

    def iter_lines(self, **kwargs):
        return iter(self.content.splitlines())


class Session:
    def __init__(self, replies):
        self.replies, self.calls, self.closed = list(replies), [], False

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        response = self.replies.pop(0)
        response.request.body = kwargs["data"]
        return response

    def close(self):
        self.closed = True


class LifecycleTests(unittest.TestCase):
    def test_running_metadata_never_skips_formal_first_start(self):
        client = FakeLifecycle(True)
        result = client.set_running(RULE, True)
        self.assertEqual(client.calls, ["start_rule"])
        self.assertEqual(result["state"], "armed_unverified")
        self.assertFalse(result["automaticDeliveryVerified"])

    def test_stopped_metadata_never_skips_formal_stop(self):
        client = FakeLifecycle(False)
        result = client.set_running(RULE, False)
        self.assertEqual(client.calls, ["stop_rule"])
        self.assertEqual(result["state"], "stopped")

    def test_reused_write_slot_is_rejected_before_a_second_operation(self):
        client = FakeLifecycle(False)
        client.set_running(RULE, True)
        with self.assertRaises(FileExistsError):
            client.set_running(RULE, True)
        self.assertEqual(client.calls, ["start_rule"])

    def test_foreign_rule_cannot_be_started(self):
        with self.assertRaises(ActivationError):
            FakeLifecycle(False).set_running(PIPELINE, True)

    def test_tool_error_is_not_empty_success(self):
        with self.assertRaises(ActivationError):
            tool_result({"result": {"isError": True, "content": [{"text": "DataNotAvailable"}]}})

    def test_empty_notification_does_not_wait_for_rpc_id(self):
        session = Session([Response(status=202, headers={"Content-Type": "text/event-stream"})])
        with tempfile.TemporaryDirectory() as directory:
            client = ActivatorLifecycle(WORKSPACE, ACTIVATOR, lambda: "test-token", Path(directory), session=session)
            self.assertIsNone(client._rpc("notifications/initialized", notification=True))
            self.assertFalse(session.trust_env)
            self.assertNotIn("test-token", (Path(directory) / "rpc" / "001-request.json").read_text())

    def test_sse_reply_is_decoded_and_journalled(self):
        body = b'data: {"jsonrpc":"2.0","id":1,"result":{"rules":[]}}\n\n'
        session = Session([Response(body, headers={"Content-Type": "text/event-stream"})])
        with tempfile.TemporaryDirectory() as directory:
            client = ActivatorLifecycle(WORKSPACE, ACTIVATOR, lambda: "test-token", Path(directory), session=session)
            self.assertEqual(client._rpc("tools/list", {})["result"], {"rules": []})
            self.assertEqual((Path(directory) / "rpc" / "001-reply.body").read_bytes(), body)

    def test_write_timeout_is_not_retried(self):
        import requests
        session = Session([])
        with tempfile.TemporaryDirectory() as directory:
            client = ActivatorLifecycle(WORKSPACE, ACTIVATOR, lambda: "test-token", Path(directory), session=session)
            with patch.object(session, "post", side_effect=requests.ReadTimeout) as post:
                with self.assertRaises(AmbiguousActivationError):
                    client._rpc("tools/call", {"name": "start_rule", "arguments": {}})
            self.assertEqual(post.call_count, 1)

    def test_git_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            with self.assertRaises(ValueError):
                ActivatorLifecycle(WORKSPACE, ACTIVATOR, lambda: "never-called", root / "evidence", session=Session([]))

    def test_late_nested_git_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = ActivatorLifecycle(WORKSPACE, ACTIVATOR, lambda: "never-called", root, session=Session([]))
            (root / ".git").mkdir()
            with self.assertRaises(ValueError):
                client._rpc("tools/list", {})


class DeliveryTests(unittest.TestCase):
    def test_native_chain_is_verified_without_claiming_copy_data(self):
        result = verify_automatic_delivery(**evidence())
        self.assertEqual(result["pipelineJobId"], "automatic")
        self.assertEqual(result["state"], "automatic_delivery_verified")
        self.assertFalse(result["copyAndDataVerified"])
        self.assertFalse(result["manualInvocation"])

    def test_invalid_evidence_never_passes(self):
        mutations = {
            "no event": lambda e: e.update(events=[]),
            "duplicate events": lambda e: e["events"].append(copy.deepcopy(e["events"][0])),
            "empty create": lambda e: e["events"][0].update(api="CreateFile", contentLength=0),
            "wrong subject": lambda e: e["events"][0].update(___subject="/Files/increment/other.csv"),
            "no activation": lambda e: e.update(history={"activations": []}),
            "history unavailable": lambda e: e.update(history={"isError": True, "activations": []}),
            "wrong target": lambda e: e["history"]["activations"][0]["properties"].update({PREFIX + "ItemId": ACTIVATOR}),
            "wrong source": lambda e: e["history"]["activations"][0]["properties"].update({PREFIX + "Parameters.Source.String": "other"}),
            "duplicate activation": lambda e: e["history"]["activations"].append(copy.deepcopy(e["history"]["activations"][0])),
            "no job": lambda e: e.update(jobs_after=[{"id": "manual-control"}]),
            "duplicate jobs": lambda e: e["jobs_after"].append({**e["jobs_after"][1], "id": "duplicate"}),
            "manual control": lambda e: e["manual_job_ids"].add("automatic"),
            "job failed": lambda e: e["jobs_after"][1].update(status="Failed"),
            "late job": lambda e: e["jobs_after"][1].update(startTimeUtc="2026-09-02T00:00:03Z"),
            "unverified bytes": lambda e: e.update(uploaded_bytes_verified=False),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                value = evidence()
                mutate(value)
                with self.assertRaises(ActivationError):
                    verify_automatic_delivery(**value)


class UploadTests(unittest.TestCase):
    def test_discovered_url_must_match_scope(self):
        self.assertEqual(
            complete_blob_url(FILES_ROOT, WORKSPACE, LAKEHOUSE, "donation_events_001.csv"),
            FILES_ROOT.replace(".dfs.", ".blob.") + "/increment/donation_events_001.csv",
        )
        for invalid in (
            FILES_ROOT.replace(WORKSPACE, PIPELINE), FILES_ROOT + "?secret=unexpected",
            FILES_ROOT.replace("onelake.dfs.fabric.microsoft.com", "example.com"),
            FILES_ROOT.replace("https://", "https://user:password@"),
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ActivationError):
                complete_blob_url(invalid, WORKSPACE, LAKEHOUSE, "donation_events_001.csv")

    def test_complete_upload_is_one_put_without_overwrite(self):
        data = b"complete,csv\none,row\n"
        calls = []
        class BlobSession:
            def put(self, url, **kwargs):
                calls.append(("PUT", url, kwargs))
                return Response(status=201)
            def get(self, url, **kwargs):
                calls.append(("GET", url, kwargs))
                return Response(data)
        with tempfile.TemporaryDirectory() as directory:
            result = put_complete_increment(
                one_lake_files_path=FILES_ROOT, workspace_id=WORKSPACE, lakehouse_id=LAKEHOUSE,
                filename="donation_events_001.csv", content=data, expected_sha256=hashlib.sha256(data).hexdigest(),
                token_provider=lambda: "test-token", store=PrivateStore(Path(directory)), session=BlobSession(),
            )
            self.assertEqual([call[0] for call in calls], ["PUT", "GET"])
            self.assertEqual(calls[0][2]["headers"]["If-None-Match"], "*")
            self.assertEqual(calls[0][2]["headers"]["x-ms-blob-type"], "BlockBlob")
            self.assertEqual(calls[0][2]["data"], data)
            self.assertEqual(result["state"], "uploaded_unverified")
            self.assertFalse(result["automaticDeliveryVerified"])

    def test_wrong_bytes_fail_before_authentication(self):
        with tempfile.TemporaryDirectory() as directory, patch("requests.Session") as session:
            with self.assertRaises(ActivationError):
                put_complete_increment(
                    one_lake_files_path=FILES_ROOT, workspace_id=WORKSPACE, lakehouse_id=LAKEHOUSE,
                    filename="donation_events_001.csv", content=b"bad", expected_sha256="0" * 64,
                    token_provider=lambda: self.fail("No token should be acquired"), store=PrivateStore(Path(directory)),
                )
            session.assert_not_called()

    def test_existing_file_is_not_overwritten_or_retried(self):
        class BlobSession:
            def __init__(self):
                self.calls = 0
            def put(self, *args, **kwargs):
                self.calls += 1
                return Response(status=412)
        blob = BlobSession()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ActivationError):
                put_complete_increment(
                    one_lake_files_path=FILES_ROOT, workspace_id=WORKSPACE, lakehouse_id=LAKEHOUSE,
                    filename="donation_events_001.csv", content=b"csv", expected_sha256=hashlib.sha256(b"csv").hexdigest(),
                    token_provider=lambda: "test-token", store=PrivateStore(Path(directory)), session=blob,
                )
            self.assertEqual(blob.calls, 1)


class ScopeTests(unittest.TestCase):
    def setUp(self):
        raw = (ROOT / "workshop/v2.7.0/provisioning/bundle/reflex/ReflexEntities.json").read_text(encoding="utf-8")
        for old, new in {
            "{{workspace.id}}": WORKSPACE, "{{tenant.id}}": TENANT,
            "{{item.lakehouse.id}}": LAKEHOUSE, "{{item.pipeline.id}}": PIPELINE,
            "{{name.lakehouse}}": "LH_Furusato_001",
        }.items():
            raw = raw.replace(old, new)
        self.entities = json.loads(raw)
        outer = self
        class Client:
            def _request(self, *args, **kwargs):
                return type("Reply", (), {"json": lambda self: {"displayName": "Workshop"}})()
            def list_items(self, *args, **kwargs):
                return [
                    {"id": LAKEHOUSE, "type": "Lakehouse", "displayName": "LH_Furusato_001", "folderId": FOLDER},
                    {"id": PIPELINE, "type": "DataPipeline", "displayName": "PL_Furusato_001", "folderId": FOLDER},
                    {"id": ACTIVATOR, "type": "Reflex", "displayName": "My activator_001", "folderId": FOLDER},
                ]
            def require_item_in_folder(self, workspace, item, **kwargs):
                return item
            def get_definition(self, *args, **kwargs):
                return {"parts": [{"path": "ReflexEntities.json", "payloadType": "InlineBase64", "payload": base64.b64encode(json.dumps(outer.entities).encode()).decode()}]}
        self.client = Client()

    def test_released_scope_resolves(self):
        scope, _ = resolve_scope(self.client, WORKSPACE, FOLDER, "001", "Workshop")
        self.assertEqual(scope["pipelineId"], PIPELINE)
        self.assertEqual(scope["activatorId"], ACTIVATOR)
        self.assertIs(scope["configuredShouldRun"], False)

    def test_other_workspace_is_rejected(self):
        with self.assertRaises(ActivationError):
            resolve_scope(self.client, WORKSPACE, FOLDER, "001", "Wrong workspace")

    def test_wrong_action_is_rejected(self):
        next(entity for entity in self.entities if entity["type"] == "fabricItemAction-v1")["payload"]["fabricItem"]["itemId"] = LAKEHOUSE
        with self.assertRaises(ActivationError):
            resolve_scope(self.client, WORKSPACE, FOLDER, "001", "Workshop")

    def test_history_reprocessing_is_not_authorized(self):
        rule = next(entity for entity in self.entities if entity.get("payload", {}).get("definition", {}).get("type") == "Rule")
        rule["payload"]["definition"]["settings"]["shouldApplyRuleOnUpdate"] = True
        with self.assertRaises(ActivationError):
            resolve_scope(self.client, WORKSPACE, FOLDER, "001", "Workshop")

    def test_confirmation_fails_before_credentials(self):
        with tempfile.TemporaryDirectory() as directory, patch("azure.identity.AzureCliCredential") as credential:
            result = main([
                "start", "--workspace-id", WORKSPACE, "--folder-id", FOLDER,
                "--expected-workspace-name", "Workshop", "--participant-id", "001",
                "--private-root", directory, "--run", "first", "--apply", "--confirmation", "wrong",
            ])
            self.assertEqual(result, 1)
            credential.assert_not_called()


if __name__ == "__main__":
    unittest.main()
