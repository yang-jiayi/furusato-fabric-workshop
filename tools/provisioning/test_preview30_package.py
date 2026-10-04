"""Package-integrity and refusal tests, explicitly not live feature validation."""
from __future__ import annotations
import ast
import base64
import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import preview30_runtime as rt
from preview30_verify import assess_sources, source_queries
from workshop_runtime import EXPECTED_TABLES
from preview30_deploy import Deployment
from test_preview30_runtime import scope


class PackageTests(unittest.TestCase):
    def test_data_bytes_unchanged(self):
        for p in (rt.BASE / "data").rglob("*"):
            if p.is_file():
                self.assertEqual(p.read_bytes(), (rt.PREVIEW / p.relative_to(rt.BASE)).read_bytes())

    def test_safe_data_notebook_code_preserved(self):
        for number in ("01", "05"):
            old = rt.load(next((rt.BASE / "notebooks").glob(f"Notebook_{number}_*.ipynb")))
            new = rt.load(next((rt.PREVIEW / "notebooks").glob(f"Notebook_{number}_*.ipynb")))
            if number == "01":
                parameter = next(c for c in new["cells"] if "parameters" in c["metadata"].get("tags", []))
                current = f'NOTEBOOK_VERSION = "{rt.WORKSHOP_VERSION}"\n'
                self.assertEqual(parameter["source"].count(current), 1)
                parameter["source"] = [
                    'NOTEBOOK_VERSION = "2.7.0"\n' if line == current else line
                    for line in parameter["source"]
                ]
            code = lambda n: [c["source"] for c in n["cells"] if c["cell_type"] == "code"]
            self.assertEqual(code(old), code(new), "Only the explicitly checked Notebook01 audit/display version may differ.")

    def test_all_five_notebooks_output_free_and_compile(self):
        notebooks = list((rt.PREVIEW / "notebooks").glob("*.ipynb"))
        self.assertEqual(len(notebooks), 5)
        for path in notebooks:
            notebook = rt.load(path)
            self.assertEqual(notebook["metadata"]["furusato"]["version"], rt.WORKSHOP_VERSION)
            self.assertEqual(notebook["metadata"]["furusato"]["edition"], "v" + rt.WORKSHOP_VERSION)
            self.assertEqual(notebook["metadata"]["furusato"]["dataContract"], "2.7.0-realistic.1")
            self.assertIn("Furusato Workshop " + rt.WORKSHOP_VERSION, "".join(notebook["cells"][0]["source"]))
            self.assertEqual(sum("parameters" in c["metadata"].get("tags", []) for c in notebook["cells"]), 1)
            for index, cell in enumerate(notebook["cells"]):
                if cell["cell_type"] == "code":
                    self.assertFalse(cell.get("outputs"))
                    self.assertIsNone(cell.get("execution_count"))
                    code = "".join(cell["source"])
                    self.assertLessEqual(len(code.encode("utf-8")), 450000)
                    compile(code, f"{path.name}/{index}", "exec")

    def test_bundle_integrity_and_safe_paths(self):
        for number in ("02", "03", "04"):
            notebook = rt.load(next((rt.PREVIEW / "notebooks").glob(f"Notebook_{number}_*.ipynb")))
            chunks = []
            for cell in notebook["cells"]:
                if "furusato-preview30-payload" in cell["metadata"].get("tags", []):
                    node = ast.parse("".join(cell["source"])).body[0]
                    chunks.append(ast.literal_eval(node.value.args[0]))
            compressed = base64.b64decode("".join(chunks), validate=True)
            self.assertEqual(hashlib.sha256(compressed).hexdigest(), notebook["metadata"]["furusato"]["bundleSha256"])
            files = json.loads(gzip.decompress(compressed))
            self.assertFalse(any(Path(name).is_absolute() or ".." in Path(name).parts for name in files))
            self.assertFalse(any("/attachments/" in name or "coordination.json" in name for name in files))
            for name in ("preview30_runtime.py", "preview30_deploy.py", "preview30_verify.py"):
                self.assertEqual(base64.b64decode(files["tools/provisioning/" + name]),
                                 (rt.REPO / "tools/provisioning" / name).read_bytes())
            prefix = "workshop/v3.0.0-preview/"
            roots = tuple(prefix + name + "/" for name in (
                "ontology/definition", "ontology/relationships/definition", "data-agent/definition",
                "powerbi/Furusato_Analytics.SemanticModel"))
            exact = set(rt.RUNTIME_INPUT_FILES) | {
                prefix + "provisioning/gold-contract.json", prefix + "powerbi/native-metrics-contract.json",
                prefix + "ontology/relationships/contract.json"}
            candidate_inputs = {name: hashlib.sha256(base64.b64decode(value)).hexdigest()
                                for name, value in files.items() if name in exact or name.startswith(roots)
                                or (any(name.startswith(prefix + "data-agent/candidates/" + profile + "/")
                                        for profile in rt.CORRECTED_PROFILE_DIRECTORIES)
                                    and Path(name).suffix in {".json", ".txt", ".sql"})}
            self.assertEqual(rt.digest(candidate_inputs), rt.candidate_fingerprint())
            self.assertEqual(base64.b64decode(files["WORKSHOP_VERSION"]).decode().strip(), rt.WORKSHOP_VERSION)
            for profile in rt.CORRECTED_PROFILE_DIRECTORIES:
                for path in (rt.PREVIEW / "data-agent/candidates" / profile).rglob("*"):
                    if path.is_file() and path.suffix in {".json", ".txt", ".sql"}:
                        self.assertEqual(base64.b64decode(files[path.relative_to(rt.REPO).as_posix()]), path.read_bytes())

    def test_four_source_candidate_is_not_accuracy_claim(self):
        contract = rt.load(rt.PREVIEW / "data-agent/candidate-contract.json")
        self.assertEqual(set(contract["sourceTypes"]), {"lakehouse_tables", "kusto", "ontology", "semantic_model"})
        self.assertFalse(contract["accuracyAccepted"])
        self.assertFalse(contract["publishedByBuild"])
        sources = [rt.load(p) for p in (rt.PREVIEW / "data-agent/definition").rglob("datasource.json")]
        self.assertEqual(len(sources), 4)
        model_paths = [p for p in (rt.PREVIEW / "data-agent/definition").rglob("datasource.json")
                       if rt.load(p).get("type") == "semantic_model"]
        self.assertEqual(len(model_paths), 1)
        self.assertTrue(model_paths[0].parent.name.startswith("semantic-model-"))
        model = next(s for s in sources if s["type"] == "semantic_model")
        self.assertEqual(model["artifactId"], "{{item.semanticModel.id}}")
        measures = [c["display_name"] for t in model["elements"] for c in t["children"]
                    if c["type"] == "semantic_model.measure"]
        self.assertTrue({"静的寄附総額", "静的寄附件数", "受入増分寄附総額", "受入増分寄附件数"}.issubset(measures))


class RequestSafetyTests(unittest.TestCase):
    def test_existing_watch_directory_never_puts(self):
        with tempfile.TemporaryDirectory() as tmp:
            deployment = object.__new__(Deployment)
            deployment.scope = scope()
            deployment.evidence = Path(tmp)
            deployment.state = {"scopeSha256": "unit-scope", "items": {
                "lakehouse": {"id": "44444444-4444-4444-8444-444444444444"}}}
            deployment.client = Mock()
            deployment.client.credential.get_token.return_value = SimpleNamespace(token="unit-test-only")
            deployment.client.session.head.return_value = SimpleNamespace(
                status_code=200, headers={"x-ms-resource-type": "directory"})
            deployment.ensure_watch_directory("44444444-4444-4444-8444-444444444444")
            deployment.client.session.put.assert_not_called()

    def test_watch_path_file_collision_refused(self):
        deployment = object.__new__(Deployment)
        deployment.scope = scope()
        deployment.state = {"items": {"lakehouse": {"id": "44444444-4444-4444-8444-444444444444"}}}
        deployment.client = Mock()
        deployment.client.credential.get_token.return_value = SimpleNamespace(token="unit-test-only")
        deployment.client.session.head.return_value = SimpleNamespace(
            status_code=200, headers={"x-ms-resource-type": "file"})
        with self.assertRaises(rt.SafetyError):
            deployment.ensure_watch_directory("44444444-4444-4444-8444-444444444444")
        deployment.client.session.put.assert_not_called()

    def test_empty_watch_directory_created_without_file_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            deployment = object.__new__(Deployment)
            deployment.scope = scope()
            deployment.evidence = Path(tmp)
            deployment.state = {"scopeSha256": "unit-scope", "items": {
                "lakehouse": {"id": "44444444-4444-4444-8444-444444444444"}}}
            deployment.client = Mock()
            deployment.client.credential.get_token.return_value = SimpleNamespace(token="unit-test-only")
            deployment.client.session.head.side_effect = [
                SimpleNamespace(status_code=404, headers={}),
                SimpleNamespace(status_code=200, headers={"x-ms-resource-type": "directory"}),
            ]
            deployment.client.session.put.return_value = SimpleNamespace(status_code=201, headers={}, text="")
            deployment.ensure_watch_directory("44444444-4444-4444-8444-444444444444")
            call = deployment.client.session.put.call_args
            self.assertTrue(call.args[0].endswith("/Files/increment?resource=directory"))
            self.assertEqual(call.kwargs["data"], b"")
            self.assertEqual(call.kwargs["headers"]["If-None-Match"], "*")

    def test_reserved_sql_alias_is_quoted(self):
        self.assertIn("AS [RowCount]", source_queries()["generationCounts"])
        self.assertNotIn("AS RowCount", source_queries()["generationCounts"])

    def test_closed_gate_rejects_before_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            credential = Mock()
            client = rt.EvidenceClient(scope(), Path(tmp), credential=credential)
            with self.assertRaises(rt.SafetyError):
                client.request("POST", "/workspaces/" + scope()["workspaceId"] + "/items", body={})
            credential.get_token.assert_not_called()

    def test_exact_body_and_one_shot_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            credential = Mock()
            credential.get_token.return_value = SimpleNamespace(token="unit-test-only-not-a-credential")
            client = rt.EvidenceClient(scope(), Path(tmp), credential=credential)
            client.gate = {"test": True}
            path = "/v1/workspaces/" + scope()["workspaceId"] + "/items"
            client.allowed_writes[("POST", path, "")] = rt.digest({"displayName": "approved"})
            with self.assertRaises(rt.SafetyError):
                client.request("POST", path[3:], body={"displayName": "different"})
            credential.get_token.assert_not_called()
            reply = Mock(status_code=201, headers={}, text="{}", json=lambda: {})
            client.session.request = Mock(return_value=reply)
            client.request("POST", path[3:], body={"displayName": "approved"}, expected=(201,))
            sent = client.session.request.call_args.kwargs
            self.assertEqual(sent["headers"]["x-ms-fabric-skill"], "spark-cli")
            self.assertFalse(client.session.trust_env)
            with self.assertRaises(rt.SafetyError):
                client.request("POST", path[3:], body={"displayName": "approved"}, expected=(201,))
            self.assertEqual(client.session.request.call_count, 1)

    def test_source_assessment_rejects_stale_generation(self):
        generation_id = "furusato-v2.7.0-generation-00000000000000000001"
        rows = [{"TableName": name, "RowCount": "80000" if name in {"ot_donation", "stg_donation_orders"} else "1", "GenerationCount": "1",
                 "MinGeneration": generation_id, "MaxGeneration": generation_id} for name in EXPECTED_TABLES]
        control = [{"RecordType": "Lease", "PublishState": "Ready", "Generation": "1"}]
        control += [{"RecordType": "Table", "TableName": name, "PublishState": "Ready",
                     "Generation": "1", "FailureReason": ""} for name in EXPECTED_TABLES]
        results = {"generationCounts": rows, "publishControl": control,
                   "staticTotals": [{"DonationRows": "80000", "DonationYen": "1344099000"}]}
        self.assertTrue(assess_sources(results)["verified"])
        broken = copy.deepcopy(results)
        broken["generationCounts"][0]["MaxGeneration"] = "stale"
        with self.assertRaises(rt.SafetyError):
            assess_sources(broken)


if __name__ == "__main__":
    unittest.main()
