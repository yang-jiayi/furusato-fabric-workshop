"""Public MCP tests use synthetic fixtures only; no auth or network calls."""

from __future__ import annotations

import copy
from collections import UserDict
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_native as runner
import native_evaluation as ne
import native_mcp as mcp
import preflight_mcp
from test_native_evaluation import example_case
from test_native_runner import definition


def config():
    return {
        "label": "fixture", "workspace_id": str(UUID(int=1)),
        "data_agent_id": str(UUID(int=2)), "stage": "production", "transport": "mcp",
    }


def reply(text="Native synthetic answer.", *, error=False):
    return {
        "jsonrpc": "2.0", "id": 3,
        "result": {"content": [{"type": "text", "text": text}], "isError": error},
    }


class Credential:
    def __init__(self):
        self.scopes = []
        self.closed = False

    def get_token(self, scope):
        self.scopes.append(scope)
        return SimpleNamespace(token="offline-placeholder")

    def close(self):
        self.closed = True


class Response:
    def __init__(self, body, status, wire, headers=None):
        self.content, self.status_code = body, status
        self.request = SimpleNamespace(body=wire)
        self.headers = headers or {}
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True


class Session:
    def __init__(self, index=0, argument="userQuestion"):
        self.calls = []
        self.responses = []
        self.index = index
        self.argument = argument
        self.native = reply()
        self.tools = [{
            "name": "fixture_tool",
            "inputSchema": {"type": "object", "properties": {argument: {"type": "string"}},
                            "required": [argument]},
        }]
        self.query_status = 200
        self.query_exception = None
        self.closed = False
        self.extra_headers = {
            "Authorization": "must-not-save",
            "Set-Cookie": "must-not-save",
            "Location": "https://example.invalid/?access_token=must-not-save",
        }
        self.notification_body = b""
        self.notification_mime = "text/plain; charset=utf-8"
        self.notification_status = 202
        self.session_id = f"transport-session-{index}"
        self.delete_status = 204
        self.deletes = []

    def post(self, url, **kwargs):
        message = json.loads(kwargs["data"])
        self.calls.append({"url": url, "message": message, **kwargs, "headers": dict(kwargs["headers"])})
        method = message["method"]
        headers = dict(self.extra_headers)
        status = 200
        if method == "initialize":
            payload = {"jsonrpc": "2.0", "id": 1, "result": {
                "protocolVersion": mcp.PROTOCOL_VERSION, "capabilities": {"tools": {}},
            }}
            if self.session_id is not None:
                headers["Mcp-Session-Id"] = self.session_id
        elif method == "notifications/initialized":
            payload, status = self.notification_body, self.notification_status
            headers["Content-Type"] = self.notification_mime
        elif method == "tools/list":
            payload = {"jsonrpc": "2.0", "id": 2, "result": {"tools": self.tools}}
        elif method == "tools/call":
            if self.query_exception:
                raise self.query_exception
            payload, status = self.native, self.query_status
        else:
            raise AssertionError("Unexpected request method")
        body = payload if isinstance(payload, bytes) else (ne.encode(payload) if payload else b"")
        response = Response(body, status, kwargs["data"], headers)
        self.responses.append(response)
        return response

    def delete(self, url, **kwargs):
        self.deletes.append({"url": url, **kwargs, "headers": dict(kwargs["headers"])})
        response = Response(b"", self.delete_status, None)
        self.responses.append(response)
        return response

    def close(self):
        self.closed = True


class Factory:
    def __init__(self):
        self.sessions = []
        self.configure = lambda s: None

    def __call__(self):
        session = Session(len(self.sessions))
        self.configure(session)
        self.sessions.append(session)
        return session


def approve(case, record):
    review = ne.review_template(case, record)
    review.update(reviewer="Offline fixture review", data_matches_frozen_fixture=True,
                  platform_block_detected=False)
    for condition in review["conditions"]:
        condition.update(
            verdict="PASS", basis="native_answer", note="Checked the synthetic native text.",
            evidence=["/result/content/0/text"],
        )
    return review


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.factory, self.credential = Factory(), Credential()
        self.client = mcp.NativeMcpClient(config(), self.credential, 17, session_factory=self.factory)
        self.emitted = {}
        self.submissions = 0

    def emit(self, name, body):
        self.assertNotIn(name, self.emitted)
        self.emitted[name] = body

    def submitted(self):
        self.submissions += 1

    def test_constructor_needs_no_auth_network_capacity_or_regional_host(self):
        self.assertEqual(self.credential.scopes, [])
        self.assertEqual(self.factory.sessions, [])
        self.assertTrue(self.client.url.startswith("https://api.fabric.microsoft.com/v1/mcp/workspaces/"))

    def test_published_stage_required_before_authentication(self):
        with self.assertRaises(ne.EvaluationError):
            mcp.NativeMcpClient({**config(), "stage": "sandbox"}, self.credential, 17)
        self.assertEqual(self.credential.scopes, [])

    def test_ids_must_be_valid_before_authentication(self):
        with self.assertRaises(ne.EvaluationError):
            mcp.NativeMcpClient({**config(), "data_agent_id": "../other"}, self.credential, 17)

    def test_exact_unicode_question_and_discovered_argument(self):
        self.factory.configure = lambda s: setattr(s, "tools", [{
            "name": "renamed_native_tool", "inputSchema": {
                "type": "object", "properties": {"questionText": {"type": "string"}},
                "required": ["questionText"],
            },
        }])
        question = "合成テスト：ＡとA\n末尾の空白も保持。 "
        result = self.client.ask(question, self.emit, self.submitted)
        self.assertEqual((result.tool_name, result.question_argument), ("renamed_native_tool", "questionText"))
        request = json.loads(self.emitted["question-request.body"])
        self.assertEqual(request["params"], {
            "name": "renamed_native_tool", "arguments": {"questionText": question},
        })
        self.assertEqual(result.response, reply())
        self.assertEqual(self.submissions, 1)
        self.assertEqual(self.credential.scopes, [mcp.SCOPE])

    def test_one_tool_call_per_fresh_session_and_no_history_reuse(self):
        handles = []
        for index in range(2):
            self.emitted = {}
            handles.append(self.client.ask("Fixture question.", self.emit, self.submitted).mcp_session_id)
        self.assertEqual(len(self.factory.sessions), 2)
        self.assertEqual(len(set(handles)), 2)
        for session in self.factory.sessions:
            self.assertTrue(session.closed)
            self.assertEqual([c["message"]["method"] for c in session.calls],
                             ["initialize", "notifications/initialized", "tools/list", "tools/call"])
            self.assertNotIn("Mcp-Session-Id", json.loads(self.emitted["initialize-request.body"]))
            self.assertNotIn("Mcp-Session-Id", session.calls[0]["headers"])
            self.assertFalse(session.trust_env)

    def test_ambiguous_tools_and_schema_stop_before_question(self):
        variations = [
            [], [Session().tools[0]] * 2,
            [{"name": "fixture", "inputSchema": {"type": "object", "properties": {
                "q": {"type": "string"}, "history": {"type": "array"},
            }, "required": ["q"]}}],
            [{"name": "fixture", "inputSchema": {"type": "object", "properties": {
                "q": {"type": "integer"},
            }, "required": ["q"]}}],
        ]
        for tools in variations:
            with self.subTest(tools=tools):
                self.factory = Factory()
                self.factory.configure = lambda s, tools=tools: setattr(s, "tools", tools)
                client = mcp.NativeMcpClient(config(), self.credential, 17, session_factory=self.factory)
                with self.assertRaises(ne.EvaluationError):
                    client.ask("Fixture", lambda *_: None, self.submitted)
                self.assertFalse(any(c["message"]["method"] == "tools/call" for c in self.factory.sessions[0].calls))
        self.assertEqual(self.submissions, 0)

    def test_question_timeout_never_retries(self):
        self.factory.configure = lambda s: setattr(s, "query_exception", TimeoutError())
        with self.assertRaises(TimeoutError):
            self.client.ask("Fixture", self.emit, self.submitted)
        self.assertEqual(self.submissions, 1)
        self.assertEqual(len(self.factory.sessions[0].calls), 4)
        self.assertIn("question-request.body", self.emitted)
        self.assertNotIn("question-reply.body", self.emitted)
        self.assertTrue(self.factory.sessions[0].closed)

    def test_redirect_or_throttle_never_replayed(self):
        for status in (307, 429, 503):
            with self.subTest(status=status):
                self.factory = Factory()
                self.factory.configure = lambda s, status=status: setattr(s, "query_status", status)
                client = mcp.NativeMcpClient(config(), self.credential, 17, session_factory=self.factory)
                saved = {}
                with self.assertRaises(mcp.McpFailure):
                    client.ask("Fixture", lambda n, b: saved.update({n: b}), lambda: None)
                self.assertIn("question-reply.body", saved)
                self.assertEqual(len(self.factory.sessions[0].calls), 4)
                self.assertTrue(all(not c["allow_redirects"] for c in self.factory.sessions[0].calls))

    def test_tokens_cookies_and_signed_locations_never_saved(self):
        self.client.ask("Fixture", self.emit, self.submitted)
        saved = b"\n".join(self.emitted.values())
        self.assertNotIn(b"offline-placeholder", saved)
        self.assertNotIn(b"must-not-save", saved)
        self.assertNotIn(b"Authorization", saved)
        self.assertNotIn(b"Set-Cookie", saved)
        self.assertTrue(all(r.closed for r in self.factory.sessions[0].responses))

    def test_complete_native_sse_retained_without_rewriting(self):
        native = reply("Native full text.\nNo rewriting.")
        wire = b"event: message\r\ndata: " + json.dumps(native).encode() + b"\r\n\r\ndata: [DONE]\r\n\r\n"
        self.factory.configure = lambda s: setattr(s, "native", wire)
        result = self.client.ask("Fixture", self.emit, self.submitted)
        self.assertEqual(self.emitted["question-reply.body"], wire)
        self.assertEqual(result.response, native)

    def test_incomplete_or_ambiguous_rpc_has_no_text_fallback(self):
        for body in (
            b'data: {"type":"response.output_text.delta","delta":"answer"}\n\n',
            b'data: {"jsonrpc":"2.0","id":3,"result":{}}\n\ndata: {"jsonrpc":"2.0","id":3,"result":{}}\n\n',
            b'{"jsonrpc":"2.0","id":2,"result":{}}',
        ):
            with self.subTest(body=body), self.assertRaises(ne.EvaluationError):
                mcp.parse_rpc(body, 3)

    def test_view_does_not_invent_ids_calls_or_query_rows(self):
        view, problems = mcp.native_view(reply("SQL: SELECT something\n| Rows | fixture |"))
        self.assertEqual(problems, [])
        self.assertEqual(set(view), {"final_texts"})
        self.assertNotIn("calls", view)
        self.assertIsNone(mcp.observability()["source_query_count"])

    def test_platform_message_is_not_a_business_refusal(self):
        _, issues = mcp.native_view(reply("There's content here I can't work with."))
        self.assertIn("native_platform_content_block", issues)

    def test_optional_is_error_field_is_not_an_error_or_trace_proof(self):
        native = reply()
        del native["result"]["isError"]
        _, issues = mcp.native_view(native)
        self.assertEqual(issues, [])
        self.assertFalse(mcp.observability()["strict_acceptance_eligible"])

    def test_preflight_discovers_without_question_or_callback(self):
        result = self.client.preflight(self.emit)
        self.assertIsInstance(result, mcp.McpDiscovery)
        self.assertEqual(result.question_submissions, 0)
        self.assertFalse(result.strict_acceptance_eligible)
        self.assertEqual(result.tool_name, "fixture_tool")
        self.assertEqual(result.question_argument, "userQuestion")
        self.assertEqual(len(result.input_schema_sha256), 64)
        session = self.factory.sessions[0]
        self.assertEqual([call["message"]["method"] for call in session.calls],
                         ["initialize", "notifications/initialized", "tools/list"])
        self.assertEqual(len(session.deletes), 1)
        self.assertTrue(session.closed)
        self.assertNotIn("question-request.body", self.emitted)
        self.assertEqual(self.submissions, 0)

    def test_native_notification_plaintext_ack_is_not_rpc(self):
        self.factory.configure = lambda session: setattr(session, "notification_body", b"Accepted")
        self.client.preflight(self.emit)
        self.assertEqual(self.emitted["initialized-reply.body"], b"Accepted")
        self.assertEqual(json.loads(self.emitted["initialized-http.json"])["status"], 202)

    def test_arbitrary_notification_body_or_error_is_not_ignored(self):
        for status, body, mime in (
            (202, b"Error", "text/plain"), (200, b"Accepted", "text/plain"),
            (202, b"Accepted!", "text/plain"), (202, b"Accepted", "application/json"),
            (202, b'{"error":{"code":-1}}', "application/json"),
        ):
            factory = Factory()
            def configure(session):
                session.notification_status = status
                session.notification_body = body
                session.notification_mime = mime
            factory.configure = configure
            client = mcp.NativeMcpClient(config(), self.credential, 17, session_factory=factory)
            with self.subTest(status=status, body=body), self.assertRaises(mcp.McpFailure):
                client.preflight(lambda *_: None)
            self.assertEqual(len(factory.sessions[0].calls), 2)
            self.assertTrue(factory.sessions[0].closed)

    def test_every_preflight_and_cleanup_request_carries_skill_attribution(self):
        client = mcp.NativeMcpClient(config(), self.credential, 17, session_factory=self.factory, skill_name="spark-cli")
        client.preflight(self.emit)
        session = self.factory.sessions[0]
        for call in session.calls + session.deletes:
            self.assertEqual(call["headers"]["x-ms-fabric-skill"], "spark-cli")
            self.assertEqual(call["headers"]["Authorization"], "Bearer offline-placeholder")
        self.assertNotIn(b"offline-placeholder", b"".join(self.emitted.values()))

    def test_question_requests_also_carry_attribution(self):
        self.client.ask("Fixture", self.emit, self.submitted)
        self.assertTrue(all(call["headers"]["x-ms-fabric-skill"] == mcp.SKILL
                            for call in self.factory.sessions[0].calls))

    def test_stateless_preflight_has_no_invented_cleanup_handle(self):
        self.factory.configure = lambda session: setattr(session, "session_id", None)
        self.assertIsNone(self.client.preflight(self.emit).mcp_session_id)
        self.assertEqual(self.factory.sessions[0].deletes, [])

    def test_cleanup_failure_cannot_report_success(self):
        self.factory.configure = lambda session: setattr(session, "delete_status", 500)
        with self.assertRaises(mcp.McpFailure):
            self.client.preflight(self.emit)
        self.assertIn("session-close-http.json", self.emitted)
        self.assertTrue(self.factory.sessions[0].closed)

    def test_failed_discovery_keeps_original_error_and_cleanup_evidence(self):
        def configure(session):
            session.tools = []
            session.delete_status = 500
        self.factory.configure = configure
        with self.assertRaisesRegex(ne.EvaluationError, "exactly one"):
            self.client.preflight(self.emit)
        self.assertIn("session-close-error.json", self.emitted)

    def test_bad_timeout_or_skill_rejected_without_authentication(self):
        for timeout in (0, -1, True, float("nan"), float("inf")):
            with self.assertRaises(ne.EvaluationError):
                mcp.NativeMcpClient(config(), self.credential, timeout)
        for skill in ("", "person@example.com", "name\r\nOther: value"):
            with self.assertRaises(ne.EvaluationError):
                mcp.NativeMcpClient(config(), self.credential, 17, skill_name=skill)
        self.assertEqual(self.credential.scopes, [])


class NotebookCredentialTests(unittest.TestCase):
    def setUp(self):
        self.context = UserDict({
            "productType": "Fabric", "currentNotebookId": str(UUID(int=3)),
            "currentNotebookName": "Owned_Preflight", "currentWorkspaceId": str(UUID(int=1)),
            "isForPipeline": False, "isReferenceRun": False, "isForInteractive": False,
            "defaultLakehouseId": None,
        })
        self.provider = MagicMock(return_value="offline-managed-token")
        self.module = SimpleNamespace(runtime=SimpleNamespace(context=self.context),
                                      credentials=SimpleNamespace(getToken=self.provider))
        self.credential = mcp.NotebookMcpCredential(
            self.module, notebook_id=str(UUID(int=3)), notebook_name="Owned_Preflight",
            workspace_id=str(UUID(int=1)),
        )

    def test_non_dict_mapping_uses_documented_managed_auth(self):
        self.assertNotIsInstance(self.context, dict)
        self.assertEqual(self.credential.get_token(mcp.SCOPE).token, "offline-managed-token")
        self.provider.assert_called_once_with("pbi")

    def test_identity_execution_and_source_gates_hold_before_authentication(self):
        for key, value in (
            ("productType", "Another"), ("currentNotebookId", str(UUID(int=4))),
            ("currentWorkspaceId", str(UUID(int=4))), ("currentNotebookName", "Another"),
            ("isForPipeline", True), ("isReferenceRun", True),
            ("isForInteractive", None), ("defaultLakehouseId", str(UUID(int=4))),
        ):
            previous = self.context[key]
            self.context[key] = value
            with self.subTest(key=key), self.assertRaises(ne.EvaluationError):
                self.credential.get_token(mcp.SCOPE)
            self.context[key] = previous
        self.provider.assert_not_called()

    def test_missing_field_is_not_silently_defaulted(self):
        del self.context["defaultLakehouseId"]
        with self.assertRaises(ne.EvaluationError):
            self.credential.get_token(mcp.SCOPE)
        self.provider.assert_not_called()

    def test_scope_and_token_guards_do_not_fall_back(self):
        with self.assertRaises(ne.EvaluationError):
            self.credential.get_token("https://other.invalid")
        self.provider.assert_not_called()
        for token in ("", "value\nheader", None):
            self.provider.return_value = token
            with self.assertRaises(ne.EvaluationError):
                self.credential.get_token(mcp.SCOPE)


class PreflightCommandTests(unittest.TestCase):
    def args(self, path):
        return ["--workspace-id", str(UUID(int=1)), "--data-agent-id", str(UUID(int=2)),
                "--out", str(path)]

    def test_no_connection_without_explicit_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "unused"
            with patch.object(preflight_mcp, "NativeMcpClient") as client:
                with self.assertRaises(SystemExit):
                    preflight_mcp.main(self.args(out))
            client.assert_not_called()
            self.assertFalse(out.exists())

    def test_used_intent_is_never_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(preflight_mcp, "NativeMcpClient") as client:
                with self.assertRaises(SystemExit):
                    preflight_mcp.main(self.args(Path(temp)) + ["--allow-connect"])
            client.assert_not_called()

    def test_command_has_no_question_path_and_records_native_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "preflight"
            discovery = mcp.McpDiscovery("fixture", "question", "a" * 64, None)
            with patch("azure.identity.AzureCliCredential", return_value=Credential()):
                with patch.object(preflight_mcp, "NativeMcpClient") as client:
                    client.return_value.config = config()
                    client.return_value.preflight.return_value = discovery
                    self.assertEqual(preflight_mcp.main(self.args(out) + ["--allow-connect"]), 0)
                    client.return_value.ask.assert_not_called()
            self.assertEqual(json.loads((out / "intent.json").read_bytes())["questionSubmissionsAllowed"], 0)
            self.assertEqual(json.loads((out / "result.json").read_bytes())["question_submissions"], 0)


class CaptureAndGradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("EVALUATION_TEST_TEMP"))
        self.store = ne.PrivateStore(Path(self.temp.name) / "private")
        self.factory, self.credential = Factory(), Credential()
        self.client = mcp.NativeMcpClient(config(), self.credential, 17, session_factory=self.factory)
        self.case = example_case()

    def tearDown(self):
        self.temp.cleanup()

    def capture(self, path="batch/T01", reader=definition):
        return runner.capture_mcp_case(
            self.store, path, self.case, self.client, reader, runner.definition_digest(definition()),
        )

    def test_capture_preserves_raw_and_explicit_answer_only_mode(self):
        record = self.capture()
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["protocol"], mcp.PROTOCOL)
        self.assertEqual(record["submission_count"], 1)
        self.assertTrue(record["fresh_mcp_session"])
        self.assertNotIn("conversation_id", record)
        self.assertNotIn("fresh_conversation", record)
        self.assertEqual(record["observability"]["mode"], "answer_only")
        runner.verify_record(self.store, record)
        self.assertEqual(self.store.read("batch/T01/review.json")["conditions"][0]["verdict"], "UNCLEAR")

    def test_existing_case_is_immutable_and_cannot_resubmit(self):
        self.capture()
        with self.assertRaises(FileExistsError):
            self.capture()
        self.assertEqual(len(self.factory.sessions), 1)

    def test_snapshot_drift_prevents_question_or_invalidates_completed_capture(self):
        record = self.capture(reader=lambda: definition("changed"))
        self.assertEqual(record["submission_count"], 0)
        self.assertEqual(self.factory.sessions, [])
        sequence = iter([definition(), definition("changed")])
        record = self.capture("other/T01", reader=lambda: next(sequence))
        self.assertEqual(record["status"], "configuration_changed")
        self.assertEqual(record["submission_count"], 1)

    def test_network_ambiguity_is_not_replayed(self):
        self.factory.configure = lambda s: setattr(s, "query_exception", TimeoutError())
        record = self.capture()
        self.assertEqual(record["status"], "submission_outcome_unknown")
        self.assertEqual(record["submission_count"], 1)
        self.assertEqual(len(self.factory.sessions[0].calls), 4)

    def test_native_error_remains_failure_not_safety_success(self):
        self.factory.configure = lambda s: setattr(s, "native", reply(error=True))
        record = self.capture()
        self.assertEqual(record["status"], "native_failure_captured")
        score = ne.grade_case(self.case, record, approve(self.case, record))
        self.assertFalse(score["question_pass"])
        self.assertEqual(score["pass"], 0)

    def test_provable_content_can_pass_while_strict_acceptance_stays_blocked(self):
        record = self.capture()
        review = approve(self.case, record)
        # A manual checkbox cannot manufacture execution observability.
        review["trace"] = {"all_steps_and_results_complete": True}
        record["observability"]["strict_acceptance_eligible"] = True
        review["record_sha256"] = ne.digest(record)
        score = ne.grade_case(self.case, record, review)
        self.assertEqual((score["pass"], score["fail"]), (1, 0))
        self.assertFalse(score["question_pass"])
        self.assertTrue(score["all_reviewed_conditions_pass"])
        self.assertEqual(set(score["observability_blockers"]), set(mcp.OBSERVABILITY_BLOCKERS))

    def test_original_execution_criterion_cannot_pass_from_answer_sql_text(self):
        self.case = example_case(condition_ids=["T01.evidence.1"])
        record = self.capture()
        score = ne.grade_case(self.case, record, approve(self.case, record))
        self.assertEqual((score["pass"], score["fail"]), (0, 1))
        self.assertIn("native_execution_evidence_unobservable", score["condition_decisions"][0]["errors"])

    def test_custom_execution_requirement_is_not_waived(self):
        self.case["conditions"][0]["required_evidence"] = "native_execution"
        record = self.capture()
        self.assertEqual(ne.grade_case(self.case, record, approve(self.case, record))["pass"], 0)

    def test_unreviewed_basis_unclear_and_missing_citation_fail(self):
        record = self.capture()
        for field, value in (("basis", "unreviewed"), ("verdict", "UNCLEAR"),
                             ("evidence", ["/id"]), ("evidence", []), ("note", "")):
            with self.subTest(field=field, value=value):
                review = approve(self.case, record)
                review["conditions"][0][field] = value
                self.assertEqual(ne.grade_case(self.case, record, review)["pass"], 0)

    def test_allowed_t03_na_stays_intact_despite_observability_block(self):
        self.case = example_case("T03", [], [
            "T03.evidence.1", "T03.evidence.2", "T03.evidence.3",
            "T03.pass_criteria.1", "T03.pass_criteria.2", "T03.pass_criteria.3",
        ])
        record = self.capture()
        review = approve(self.case, record)
        review.update(branch="clarification", branch_evidence_pointer="/result/content/0/text",
                      branch_note="Both meanings explicitly offered for clarification.")
        for row in review["conditions"]:
            if row["id"] in ne.T03_NA:
                row.update(verdict="NA", note="Allowed numeric-only clarification branch.")
        score = ne.grade_case(self.case, record, review)
        self.assertEqual((score["pass"], score["fail"], score["na"]), (3, 0, 3))
        self.assertFalse(score["question_pass"])
        review["conditions"][2]["verdict"] = "NA"
        score = ne.grade_case(self.case, record, review)
        self.assertEqual((score["pass"], score["fail"], score["na"]), (2, 1, 3))

    def test_fabricated_backend_identity_is_rejected(self):
        record = self.capture()
        record["conversation_id"] = record["mcp_session_id"]
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, record)
        score = ne.grade_case(self.case, record, approve(self.case, record))
        self.assertEqual(score["pass"], 0)
        self.assertIn("unsupported_backend_conversation_claim", score["gate_errors"])

    def test_parsed_or_raw_answer_edits_are_detected(self):
        record = self.capture()
        changed = copy.deepcopy(record)
        changed["response"]["result"]["content"][0]["text"] = "Externally corrected."
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, changed)
        self.store.path(record["response_artifact"]).write_bytes(ne.encode(reply("Edited raw answer.")))
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, record)

    def test_discovered_tool_schema_is_bound_to_wire_question(self):
        record = self.capture()
        record["question_argument"] = "fabricated_argument"
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, record)

    def test_missing_handshake_evidence_cannot_claim_fresh_session(self):
        record = self.capture()
        record["artifacts"] = [
            a for a in record["artifacts"] if not a["path"].endswith("/initialize-reply.body")
        ]
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, record)

    def test_stale_review_or_platform_flag_never_passes_content(self):
        record = self.capture()
        review = approve(self.case, record)
        review["record_sha256"] = "wrong"
        self.assertEqual(ne.grade_case(self.case, record, review)["pass"], 0)
        review = approve(self.case, record)
        review["platform_block_detected"] = True
        self.assertEqual(ne.grade_case(self.case, record, review)["pass"], 0)

    def test_plan_cli_freezes_mcp_without_auth_and_old_reports_are_read_only(self):
        original = {
            "schema_version": 1, "kind": "original", "cases": [
                example_case(f"T{i:02}", [], [f"T{i:02}.fixture.{j}" for j in range(n)])
                for i, n in enumerate(ne.ORIGINAL_COUNTS, 1)
            ],
        }
        heldout = {"schema_version": 1, "kind": "heldout", "cases": [example_case("H01", [])]}
        ne.freeze_suite(self.store, "original.json", original)
        ne.freeze_suite(self.store, "heldout.json", heldout)
        self.store.write("data.json", {"fixture": True})
        deployment = {"configurations": [{
            **config(), "transport": "sdk", "data_fingerprint_file": "data.json",
        }]}
        self.store.write("deployment.json", deployment)
        with patch.object(runner, "credential_for") as credential:
            status = runner.main([
                "--private-root", str(self.store.root), "plan", "--name", "fixture",
                "--deployment", "deployment.json", "--original-suite", "original.json",
                "--held-out-suite", "heldout.json", "--repeats", "1", "--held-out-repeats", "1",
                "--transport", "mcp",
            ])
        credential.assert_not_called()
        self.assertEqual(status, 0)
        path = "campaigns/fixture/plan.json"
        plan = runner.load_plan(self.store, path)
        self.assertEqual(plan["configurations"][0]["transport"], "mcp")
        old_bytes = self.store.path(path).read_bytes()
        with patch.object(runner, "harness_sources", return_value={"new": "version"}):
            with self.assertRaises(ne.EvaluationError):
                runner.load_plan(self.store, path)
            loaded = runner.load_plan(self.store, path, for_execution=False)
            report = runner.report_campaign(self.store, loaded)
        self.assertFalse(report["acceptance"])
        self.assertFalse(report["harness_sources_match_current"])
        self.assertEqual(self.store.path(path).read_bytes(), old_bytes)

    def test_repeated_rpc_ids_are_not_backend_conversation_reuse(self):
        original = {
            "schema_version": 1, "kind": "original", "cases": [
                example_case(f"T{i:02}", [], [f"T{i:02}.fixture.{j}" for j in range(n)])
                for i, n in enumerate(ne.ORIGINAL_COUNTS, 1)
            ],
        }
        heldout = {"schema_version": 1, "kind": "heldout", "cases": [example_case("H01", [])]}
        ne.freeze_suite(self.store, "original.json", original)
        ne.freeze_suite(self.store, "heldout.json", heldout)
        self.store.write("data.json", {"fixture": True})
        path = runner.create_plan(self.store, "batch", {"configurations": [{
            **config(), "data_fingerprint_file": "data.json",
        }]}, "original.json", "heldout.json", 1, 1)
        plan = runner.load_plan(self.store, path)
        reader = MagicMock()
        reader.read.return_value = definition()
        with patch.object(runner, "original_suite", return_value=original), \
             patch.object(runner, "credential_for", return_value=self.credential), \
             patch.object(runner, "DefinitionReader", return_value=reader), \
             patch.object(runner, "NativeMcpClient", return_value=self.client):
            for slot in plan["slots"]:
                batch = runner.run_batch(self.store, plan, slot, "azure-cli", 17)
                self.assertEqual(batch["status"], "captured_pending_human_review")
                suite = original if slot["suite"] == "original" else heldout
                for case in suite["cases"]:
                    base = runner.slot_path(plan, slot) + "/" + case["id"]
                    record = self.store.read(base + "/record.json")
                    self.store.path(base + "/review.json").write_bytes(ne.encode(approve(case, record)))
        report = runner.report_campaign(self.store, plan)
        self.assertFalse(report["acceptance"])
        for batch in report["batches"]:
            self.assertGreater(batch["summary"]["condition_pass"], 0)
            self.assertEqual(batch["summary"]["question_pass"], 0)
            self.assertTrue(all(not any("integrity_failed" in e for e in case["gate_errors"])
                                for case in batch["cases"]))
        self.assertEqual(len(self.factory.sessions), 11)

    def test_run_requires_explicit_opt_in_before_any_auth(self):
        with patch.object(runner, "credential_for") as auth:
            code = runner.main([
                "--private-root", str(self.store.root), "run", "--plan", "absent.json",
                "--configuration", "fixture", "--suite", "original", "--repeat", "1",
            ])
        self.assertEqual(code, 2)
        auth.assert_not_called()


if __name__ == "__main__":
    unittest.main()
