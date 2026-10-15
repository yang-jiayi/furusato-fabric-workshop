"""Participant workflow tests; no credentials, real identities or network calls."""
import base64
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import participant_profile as app
import measured_contract_profile as measured
from source_grounded_profile import decoded_parts, inline_part
from test_measured_contract_gen2 import fixture

W = "00000000-0000-0000-0000-000000000001"
A = "00000000-0000-0000-0000-000000000009"
ORIGIN = "https://observed-fixture.analysis.windows.net"


def inputs_fixture():
    definition, args, _ = fixture("draft")
    return {"definition": definition, "normalized": copy.deepcopy(definition),
            "sql_columns": args["sql_columns"], "model": args["native_model"], "ontology": args["ontology_item"],
            "typed_ontology": {"properties": {"generation": 2}}, "sql_tree": [], "normalization_proof": []}


class FakeClient:
    def __init__(self, inputs):
        self.workspace, self.agent, self.origin = W, A, ORIGIN
        self.sql_transport = "mcp"
        self.current = copy.deepcopy(inputs["definition"])
        self.calls = []
        self.fail_write = False

    def definition(self, *args, **kwargs):
        return copy.deepcopy(self.current)

    def request(self, method, url, body=None, **kwargs):
        self.calls.append((method, url, copy.deepcopy(body)))
        if self.fail_write:
            raise app.ProfileError("Uncertain outcome")
        if url.endswith("/updateDefinition"):
            self.current = copy.deepcopy(body["definition"])
        elif url.endswith("/staging/publish"):
            docs = decoded_parts(self.current)
            docs = {p: v for p, v in docs.items() if "/published/" not in p}
            docs.update({p.replace("/draft/", "/published/", 1): copy.deepcopy(v)
                         for p, v in list(docs.items()) if "/draft/" in p})
            self.current = {"parts": [inline_part(p, v) for p, v in docs.items()]}
        return SimpleNamespace(status_code=200)

    def completed(self, response):
        return None

    base = app.API + f"/workspaces/{W}/dataAgents/{A}"


class ParticipantProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.inputs = inputs_fixture()
        self.candidate, self.receipt = app.compile_inputs(self.inputs)
        self.client = FakeClient(self.inputs)

    def tearDown(self):
        self.temp.cleanup()

    def test_prepare_is_local_compile_after_readonly_gather_and_binds_evidence(self):
        with patch.object(app, "gather", return_value=self.inputs):
            result = app.prepare(self.client, self.root)
        self.assertEqual(result["cloudWrites"], 0)
        self.assertFalse(self.client.calls)
        manifest, inputs, candidate = app.prepared(self.root, W, A, measured.CURRENT_PROFILE)
        self.assertEqual(candidate, self.candidate)
        self.assertEqual(inputs, self.inputs)
        self.assertFalse(self.receipt["freshDeploymentOrAnswerAccuracyVerified"])
        self.assertEqual(self.receipt["sourceOwnedWorkshopMeasuresVerified"], 10)
        self.assertEqual(self.receipt["activeKqlExamples"], 9)
        with self.assertRaises(app.ProfileError):
            app.prepared(self.root, W, "00000000-0000-0000-0000-000000000008", measured.CURRENT_PROFILE)

    def test_apply_once_preserves_published_and_context_then_publish_reads_back(self):
        with patch.object(app, "gather", return_value=self.inputs):
            result = app.apply(self.client, self.root, self.inputs, self.candidate)
        self.assertEqual(result["status"], "draft-matches")
        self.assertTrue(app.load(self.root, "applied.json")["publishedUnchanged"])
        self.assertEqual(len(self.client.calls), 1)
        with patch.object(app, "verify_public", return_value={"answerAccuracyVerified": False}):
            result = app.publish(self.client, self.root, self.inputs, self.candidate)
        self.assertEqual(result["status"], "published-matches")
        self.assertEqual(len(self.client.calls), 2)
        self.assertTrue(self.client.calls[1][1].endswith("/staging/publish"))
        self.assertFalse(result["answerAccuracyVerified"])
        with self.assertRaises(app.ProfileError):
            app.publish(self.client, self.root, self.inputs, self.candidate)
        self.assertEqual(len(self.client.calls), 2)

    def test_unknown_update_outcome_cannot_be_resubmitted(self):
        self.client.fail_write = True
        with patch.object(app, "gather", return_value=self.inputs):
            with self.assertRaises(app.ProfileError):
                app.apply(self.client, self.root, self.inputs, self.candidate)
            with self.assertRaises(app.ProfileError):
                app.apply(self.client, self.root, self.inputs, self.candidate)
        self.assertEqual(len(self.client.calls), 1)
        self.assertTrue((self.root / "apply-intent.json").exists())
        self.assertTrue((self.root / "apply-backup.json").exists())

    def test_concurrent_agent_change_stops_before_write(self):
        fresh = copy.deepcopy(self.inputs)
        docs = decoded_parts(fresh["definition"])
        docs["Files/Config/published/stage_config.json"]["aiInstructions"] = "Someone else's new publication"
        fresh["definition"] = {"parts": [inline_part(p, v) for p, v in docs.items()]}
        fresh["normalized"] = copy.deepcopy(fresh["definition"])
        with patch.object(app, "gather", return_value=fresh), self.assertRaises(app.ProfileError):
            app.apply(self.client, self.root, self.inputs, self.candidate)
        self.assertFalse(self.client.calls)
        self.assertFalse((self.root / "apply-intent.json").exists())

    def test_changed_model_measure_stops_before_write(self):
        fresh = copy.deepcopy(self.inputs)
        part = fresh["model"]["parts"][0]
        text = base64.b64decode(part["payload"]).decode().replace("COUNTROWS('寄附')", "COUNTROWS('自治体')")
        part["payload"] = base64.b64encode(text.encode()).decode()
        with patch.object(app, "gather", return_value=fresh), self.assertRaises(ValueError):
            app.apply(self.client, self.root, self.inputs, self.candidate)
        self.assertFalse(self.client.calls)

    def test_readback_failure_is_not_success_and_never_rewrites(self):
        self.client.current = copy.deepcopy(self.candidate)
        docs = decoded_parts(self.client.current)
        docs["Files/Config/draft/stage_config.json"]["aiInstructions"] = "Wrong"
        self.client.current = {"parts": [inline_part(p, v) for p, v in docs.items()]}
        with self.assertRaises(app.ProfileError):
            app.verify(self.client, self.root, self.candidate, "draft")
        self.assertFalse(self.client.calls)
        self.assertEqual(len(list(self.root.glob("verify-draft-*.json"))), 1)

    def test_pending_or_invalid_examples_block_publish_before_intent(self):
        self.client.current = copy.deepcopy(self.candidate)
        with patch.object(app, "verify_public", side_effect=app.ProfileError("Few-shots not Valid")), self.assertRaises(app.ProfileError):
            app.publish(self.client, self.root, self.inputs, self.candidate)
        self.assertFalse(self.client.calls)
        self.assertFalse((self.root / "publish-intent.json").exists())

    def test_concurrent_published_change_blocks_publish(self):
        self.client.current = copy.deepcopy(self.candidate)
        docs = decoded_parts(self.client.current)
        docs["Files/Config/published/stage_config.json"]["aiInstructions"] = "Changed concurrently"
        self.client.current = {"parts": [inline_part(p, v) for p, v in docs.items()]}
        with patch.object(app, "verify_public", return_value={}), self.assertRaises(app.ProfileError):
            app.publish(self.client, self.root, self.inputs, self.candidate)
        self.assertFalse(self.client.calls)

    def test_private_evidence_cannot_overwrite_or_live_under_git_or_symlink(self):
        app.save(self.root, "evidence.json", {"a": 1})
        with self.assertRaises(FileExistsError):
            app.save(self.root, "evidence.json", {"a": 2})
        (self.root / "checkout").mkdir()
        (self.root / "checkout/.git").mkdir()
        with self.assertRaises(app.ProfileError):
            app.private_root(self.root / "checkout/evidence", create=True)
        (self.root / "alias").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(app.ProfileError):
            app.private_root(self.root / "alias/evidence", create=True)
        self.assertEqual((self.root / "evidence.json").stat().st_mode & 0o777, 0o600)

    def test_extracted_source_without_git_is_not_a_private_evidence_directory(self):
        extracted = self.root / "extracted" / "source"
        extracted.mkdir(parents=True)
        with patch.object(app, "REPO", extracted), self.assertRaises(app.ProfileError):
            app.private_root(extracted / "private-evidence", create=True)
        self.assertFalse((extracted / "private-evidence").exists())

    def test_non_apply_flag_never_constructs_authenticated_client(self):
        with patch.object(app, "Client") as client:
            code = app.main(["apply", "--workspace-id", W, "--agent-id", A, "--profile", measured.CURRENT_PROFILE, "--private-root", str(self.root)])
        self.assertEqual(code, 2)
        client.assert_not_called()

    def test_only_observed_origin_accepted(self):
        self.assertEqual(app.routing_origin(ORIGIN + "/"), ORIGIN)
        for value in ("https://example.com", ORIGIN + "/metadata", ORIGIN + "?token=x", ORIGIN + "#fragment", "http://observed-fixture.analysis.windows.net", "https://u:p@observed-fixture.analysis.windows.net", "https://observed-fixture.analysis.windows.net.evil.test"):
            with self.subTest(value=value), self.assertRaises(app.ProfileError):
                app.routing_origin(value)

    def test_blank_type_requires_independent_public_and_sql_evidence(self):
        definition = copy.deepcopy(self.inputs["definition"])
        docs, sources, _ = measured.stage_sources(definition, "draft")
        path, source = sources["lakehouse_tables"]
        records = []
        for ancestry, node in measured.walk(source["elements"]):
            if node["type"] != "lakehouse_tables.column":
                continue
            records.append({"path": (("Schema", ancestry[1]), ("View" if ancestry[2] == "Views" else "Table", ancestry[3]), ("Column", ancestry[4])),
                            "element": {"type": "Column", "id": "public:" + node["id"], "state": "Available", "dataType": node["data_type"]}})
            node["data_type"] = ""
        definition = {"parts": [inline_part(p, v) for p, v in docs.items()]}
        normalized, proof = app.normalize_sql_types(definition, self.inputs["sql_columns"], records)
        self.assertEqual(len(proof), 143)
        measured.compile_measured_draft(normalized, input_stage="draft", sql_columns=self.inputs["sql_columns"], native_model=self.inputs["model"], ontology_item=self.inputs["ontology"])
        records[0]["element"]["dataType"] = "invented-type"
        with self.assertRaises(app.ProfileError):
            app.normalize_sql_types(definition, self.inputs["sql_columns"], records)


class PublicReadbackTests(unittest.TestCase):
    def setUp(self):
        self.inputs = inputs_fixture()
        self.candidate, _ = app.compile_inputs(self.inputs)
        docs, sources = app.bound_sources(self.candidate, W)
        self.sources, self.shots, self.records = [], {}, []
        for kind in sorted(measured.DIRECT_KINDS):
            path, source = sources[kind]
            row = {"id": "public-" + kind, "type": "LakehouseTables" if kind == "lakehouse_tables" else "FabricItem",
                   "instructions": source["dataSourceInstructions"], "description": source["userDescription"]}
            if kind != "lakehouse_tables":
                row["fabricItemType"] = {"kusto": "KQLDatabase", "semantic_model": "SemanticModel"}[kind]
            row["lakehouseReference" if kind == "lakehouse_tables" else "itemReference"] = {
                "referenceType": "ById", "itemId": source["artifactId"], "workspaceId": W}
            self.sources.append(row)
            self.shots[row["id"]] = [dict(v, validationStatus={"value": "Valid"})
                for v in docs.get(path.replace("datasource.json", "fewshots.json"), {}).get("fewShots", [])]
        for path, node in measured.walk(sources["lakehouse_tables"][1]["elements"]):
            kind = node["type"].split(".")[-1]
            if kind not in {"table", "view", "column"}:
                continue
            p = (("Schema", path[1]), ("View" if path[2] == "Views" else "Table", path[3]))
            if kind == "column":
                p += (("Column", path[4]),)
            self.records.append({"path": p, "ancestors": [], "element": {
                "type": {"table": "Table", "view": "View", "column": "Column"}[kind],
                "id": "public-" + node["id"], "state": "Available", "isSelected": node["is_selected"],
                "description": node.get("description"), "hasSubElements": kind != "column"}})
        self.client = SimpleNamespace(workspace=W, base=FakeClient.base, pages=self.pages)

    def pages(self, url):
        if url.endswith("/datasources"):
            return copy.deepcopy(self.sources)
        for source, shots in self.shots.items():
            if url.endswith("/datasources/" + source + "/fewshots"):
                return copy.deepcopy(shots)
        raise AssertionError("Unexpected endpoint " + url)

    def verify(self):
        with patch.object(app, "tree", return_value=self.records):
            return app.verify_public(self.client, self.candidate, "draft")

    def test_actual_public_shapes_select_exact_columns_and_nine_valid_examples(self):
        result = self.verify()
        self.assertEqual((result["selectedSqlObjects"], result["selectedSqlColumns"], result["activeKqlExamples"]), (17, 143, 9))
        self.assertFalse(result["ontologyContextAvailabilityVerified"])
        self.assertFalse(result["answerAccuracyVerified"])

    def test_extra_selected_column_is_rejected(self):
        extra = copy.deepcopy(self.records[-1])
        extra["path"] = (*extra["path"][:-1], ("Column", "UnexpectedColumn"))
        extra["element"].update(type="Column", isSelected=True, id="extra")
        self.records.append(extra)
        with self.assertRaises(app.ProfileError):
            self.verify()
        extra["element"]["isSelected"] = False
        self.verify()

    def test_deselected_required_column_is_rejected(self):
        next(row for row in self.records if row["element"]["type"] == "Column")["element"]["isSelected"] = False
        with self.assertRaises(app.ProfileError):
            self.verify()

    def test_source_description_and_column_description_must_match(self):
        original = self.sources[0]["description"]
        self.sources[0]["description"] = "Changed"
        with self.assertRaises(app.ProfileError):
            self.verify()
        self.sources[0]["description"] = original
        self.records[0]["element"]["description"] = "Changed"
        with self.assertRaises(app.ProfileError):
            self.verify()

    def test_invalid_example_blocks_publication_and_changed_query_is_rejected(self):
        shot = self.shots["public-kusto"][0]
        shot["validationStatus"]["value"] = "Invalid"
        with self.assertRaises(app.ProfileError):
            self.verify()
        shot["validationStatus"]["value"] = "Valid"
        shot["query"] = "Different table"
        with self.assertRaises(app.ProfileError):
            self.verify()


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.credential = SimpleNamespace(get_token=lambda _: SimpleNamespace(token="FAKE_SECRET_TOKEN"))
        self.calls = []
        self.replies = []
        self.session = SimpleNamespace(request=self.request)
        self.client = app.Client(W, A, ORIGIN, Path(self.temp.name), credential=self.credential, session=self.session, sleeper=lambda _: None)

    def tearDown(self):
        self.temp.cleanup()

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        value = self.replies.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def reply(self, data, status=200, headers=None):
        text = json.dumps(data)
        return SimpleNamespace(json=lambda: data, status_code=status, text=text, content=text.encode(), headers=headers or {})

    def test_redirect_and_foreign_origin_never_forward_token(self):
        with self.assertRaises(app.ProfileError):
            self.client.request("GET", "https://example.test/v1/items")
        self.assertFalse(self.calls)
        self.replies.append(self.reply({}, 302))
        with self.assertRaises(app.ProfileError):
            self.client.request("GET", app.API + "/workspaces/" + W)
        self.assertFalse(self.calls[0][2]["allow_redirects"])

    def test_lro_polls_same_operation_without_resending_write(self):
        op = "00000000-0000-0000-0000-000000000099"
        self.replies = [self.reply({"status": "Running"}), self.reply({"status": "Succeeded"}), self.reply({"definition": {"parts": []}})]
        result = self.client.completed(self.reply({}, 202, {"x-ms-operation-id": op}), result=True)
        self.assertEqual(result, {"definition": {"parts": []}})
        self.assertTrue(all(method == "GET" for method, _, _ in self.calls))

    def test_ambiguous_request_is_not_retried_or_token_persisted(self):
        self.replies = [RuntimeError("FAKE_SECRET_TOKEN")]
        with self.assertRaises(app.ProfileError) as error:
            self.client.request("POST", self.client.base + "/updateDefinition", {})
        self.assertNotIn("FAKE_SECRET_TOKEN", str(error.exception))
        self.assertEqual(len(self.calls), 1)
        for file in Path(self.temp.name).glob("*.json"):
            self.assertNotIn("FAKE_SECRET_TOKEN", file.read_text())

    def test_pagination_rejects_escape_and_supports_token(self):
        self.replies = [self.reply({"value": [1], "continuationToken": "page2"}), self.reply({"value": [2]})]
        self.assertEqual(self.client.pages(self.client.base + "/datasources"), [1, 2])
        self.replies = [self.reply({"value": [], "continuationUri": "https://example.test/v1/stolen"})]
        with self.assertRaises(app.ProfileError):
            self.client.pages(self.client.base + "/datasources")


if __name__ == "__main__":
    unittest.main()
