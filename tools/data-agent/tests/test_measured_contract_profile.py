import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import measured_contract_profile as measured
from source_grounded_profile import decoded_parts, inline_part


def native_tree(rows):
    roots, indexed = [], {}
    for row in rows:
        path = tuple(row["path"])
        parent = roots if len(path) == 1 else indexed[path[:-1]]["children"]
        node = {"id": "observed-" + "/".join(path), "display_name": path[-1], "type": row["type"],
                "is_selected": False, "children": []}
        if "dataType" in row:
            node["data_type"] = row["dataType"]
        parent.append(node)
        indexed[path] = node
    return roots


class MeasuredContractTests(unittest.TestCase):
    def fixture(self):
        _, _, selections, _, _ = measured.profile_inputs()
        workspace = "00000000-0000-0000-0000-000000000001"
        docs = {"Files/Config/data_agent.json": {"displayName": "test-agent"},
                "Files/Config/published/stage_config.json": {"aiInstructions": "old instructions",
                    "experimental": {"codeInterpreterEnabled": True, "retainedSetting": "retained"}}}
        rows = []
        for index, kind in enumerate(sorted(measured.KINDS), 2):
            path = "Files/Config/published/" + kind + "/datasource.json"
            elements = native_tree(selections[kind]) if kind in selections else []
            if kind == "semantic_model":
                elements = [{"id": "observed-model-table", "display_name": "寄附", "type": "semantic_model.table",
                    "is_selected": True, "children": [{"id": "observed-model-" + name, "display_name": name,
                        "type": "semantic_model.column" if name == "寄附金額" else "semantic_model.measure",
                        "is_selected": True, "children": []}
                        for name in ("寄附金額", *measured.MEASURES)]}]
            docs[path] = {"type": kind, "workspaceId": workspace,
                "artifactId": str(uuid.UUID(int=index)), "displayName": "public-test-" + kind,
                "dataSourceInstructions": "old source instructions", "userDescription": "old source description",
                "metadata": {"retained": True}, "elements": elements}
        for row in selections["lakehouse_tables"]:
            if row["type"] == "lakehouse_tables.column":
                path = row["path"]
                rows.append({"TABLE_SCHEMA": path[1], "TABLE_NAME": path[-2], "COLUMN_NAME": path[-1], "DATA_TYPE": row["dataType"]})
        docs["Files/Config/published/lakehouse_tables/fewshots.json"] = {"fewShots": [{"id": "old-sql", "question": "old", "query": "SELECT 1"}]}
        # Preserve inactive Draft/service metadata as input evidence, but derive
        # the new Draft from the explicit Published stage.
        docs["Files/Config/draft/stage_config.json"] = {"aiInstructions": "inactive draft"}
        docs["Files/Config/publish_info.json"] = {"description": "service-owned retained evidence"}
        # Use the public source model as an independent fixture, rather than
        # creating a second model definition from the compiler's constants.
        expression = (measured.REPO / "workshop/v3.0.0-preview/powerbi/Furusato_Analytics.SemanticModel/definition/tables/寄附.tmdl").read_text(encoding="utf-8")
        import re
        expression = re.sub(r"(\tcolumn 寄附金額\n\t\tdataType: int64\n)\t\tisHidden\n", r"\1", expression)
        model = {"format": "TMDL", "parts": [{"path": "definition/tables/寄附.tmdl", "payloadType": "InlineBase64",
            "payload": base64.b64encode(expression.encode()).decode()}]}
        ontology = {"objectId": docs["Files/Config/published/ontology/datasource.json"]["artifactId"], "artifactType": "Ontology",
                    "extendedProperties": {"FeatureLevel": 2, "ChildItems": json.dumps({
                        "GraphInstance": str(uuid.UUID(int=90)), "OntologyEventhouse": str(uuid.UUID(int=91))})}}
        definition = {"parts": [inline_part(path, value) for path, value in docs.items()]}
        return definition, {"input_stage": "published", "sql_columns": rows, "native_model": model, "ontology_item": ontology}

    def replace_docs(self, original, mutator):
        docs = decoded_parts(original)
        mutator(docs)
        return {"parts": [inline_part(path, value) for path, value in docs.items()]}

    def test_compilation_is_deterministic_and_preserves_published_evidence_and_identity(self):
        definition, inputs = self.fixture()
        saved = copy.deepcopy((definition, inputs))
        result, receipt = measured.compile_measured_draft(definition, **inputs)
        self.assertEqual((definition, inputs), saved)
        self.assertEqual((result, receipt), measured.compile_measured_draft(definition, **inputs))
        unchanged_parts = [p for p in definition["parts"] if "/draft/" not in p["path"]]
        self.assertEqual(unchanged_parts, [p for p in result["parts"] if "/draft/" not in p["path"]])
        before, after = decoded_parts(definition), decoded_parts(result)
        for kind in measured.KINDS:
            pub, draft = ("Files/Config/" + stage + "/" + kind + "/datasource.json" for stage in ("published", "draft"))
            for key in ("artifactId", "workspaceId", "displayName", "type", "metadata"):
                self.assertEqual(before[pub][key], after[draft][key])
            if kind in {"ontology", "semantic_model"}:
                self.assertEqual(before[pub]["elements"], after[draft]["elements"])
        self.assertNotIn("Files/Config/draft/lakehouse_tables/fewshots.json", after)
        self.assertEqual(len(after["Files/Config/draft/kusto/fewshots.json"]["fewShots"]), 9)
        self.assertEqual(receipt["instructionUtf16Units"], {"global": 9981, "lakehouse_tables": 9989,
                         "kusto": 8665, "ontology": 4963, "semantic_model": 6989})
        self.assertEqual(receipt["cloudCalls"], 0)
        self.assertFalse(receipt["freshDeploymentOrAnswerAccuracyVerified"])
        self.assertEqual(receipt["sourceOwnedWorkshopMeasuresVerified"], 10)

    def test_missing_service_column_id_and_native_or_independent_type_drift_are_refused(self):
        definition, inputs = self.fixture()
        for mutation in ("missing", "id", "type"):
            def alter(docs):
                nodes = list(measured.walk(docs["Files/Config/published/lakehouse_tables/datasource.json"]["elements"]))
                column = next(n for path, n in nodes if path[-1] == "DonationAmountYen")
                if mutation == "id":
                    column.pop("id")
                elif mutation == "type":
                    column["data_type"] = "varchar"
                else:
                    table = next(n for path, n in nodes if path[-1] == "agent_donation_detail")
                    table["children"].remove(column)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                measured.compile_measured_draft(self.replace_docs(definition, alter), **inputs)
        inputs["sql_columns"][0]["DATA_TYPE"] = "unknown"
        with self.assertRaises(ValueError):
            measured.compile_measured_draft(definition, **inputs)

    def test_same_kind_duplicate_selected_ids_and_ambiguous_paths_are_refused(self):
        definition, inputs = self.fixture()
        def alter(docs):
            columns = [n for path, n in measured.walk(docs["Files/Config/published/kusto/datasource.json"]["elements"])
                       if n["type"] == "kusto.column"]
            columns[1]["id"] = columns[0]["id"]
        with self.assertRaises(ValueError):
            measured.compile_measured_draft(self.replace_docs(definition, alter), **inputs)

    def test_changed_model_measure_or_hidden_amount_prevents_false_visibility_contract(self):
        definition, inputs = self.fixture()
        part = inputs["native_model"]["parts"][0]
        text = base64.b64decode(part["payload"]).decode()
        for changed in (text.replace('"StaticSeed"', '"RealtimeIncrement"', 1),
                        text.replace("SUM('寄附'[寄附金額])", "SUM('寄附'[寄附ID])", 1),
                        text.replace("\tcolumn 寄附金額\n", "\tcolumn 寄附金額\n\t\tisHidden\n")):
            args = copy.deepcopy(inputs)
            args["native_model"]["parts"][0]["payload"] = base64.b64encode(changed.encode()).decode()
            with self.subTest(model=changed), self.assertRaises(ValueError):
                measured.compile_measured_draft(definition, **args)

    def test_model_selection_requires_actual_native_measure_kind_and_id(self):
        definition, inputs = self.fixture()
        for field, value in (("type", "semantic_model.column"), ("id", "")):
            def alter(docs):
                table = docs["Files/Config/published/semantic_model/datasource.json"]["elements"][0]
                measure = next(node for node in table["children"] if node["display_name"] == "静的寄附件数")
                measure[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                measured.compile_measured_draft(self.replace_docs(definition, alter), **inputs)

    def test_foreign_workspace_extra_source_gen1_and_disabled_interpreter_are_refused(self):
        definition, inputs = self.fixture()
        for mutation in ("workspace", "source", "interpreter", "topic"):
            def alter(docs):
                if mutation == "workspace":
                    docs["Files/Config/published/ontology/datasource.json"]["workspaceId"] = str(uuid.UUID(int=99))
                elif mutation == "source":
                    docs["Files/Config/published/second-ontology/datasource.json"] = copy.deepcopy(docs["Files/Config/published/ontology/datasource.json"])
                elif mutation == "interpreter":
                    docs["Files/Config/published/stage_config.json"]["experimental"]["codeInterpreterEnabled"] = False
                else:
                    docs["Files/Config/published/topics.json"] = {"topics": []}
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                measured.compile_measured_draft(self.replace_docs(definition, alter), **inputs)
        inputs["ontology_item"]["extendedProperties"]["FeatureLevel"] = 1
        with self.assertRaises(ValueError):
            measured.compile_measured_draft(definition, **inputs)

    def test_manifest_drift_and_utf16_overflow_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            for path in measured.PROFILE.iterdir():
                if path.suffix in {".txt", ".json"}:
                    (profile / path.name).write_bytes(path.read_bytes())
            instructions = profile / "global-instructions.txt"
            instructions.write_text("changed", encoding="utf-8")
            with self.assertRaises(ValueError):
                measured.profile_inputs(profile)
            instructions.write_text("😀" * 5001, encoding="utf-8")
            manifest_path = profile / "profile-manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            import hashlib
            manifest["sha256"][instructions.name] = hashlib.sha256(instructions.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                measured.profile_inputs(profile)

    def test_json_unicode_escapes_cannot_hide_benchmark_values_case_ids_or_live_guids(self):
        for value in ("都城市", "Q01", "12345678-1234-1234-1234-123456789abc", "12345678-1234-1234-1234-123456789ABC"):
            with tempfile.TemporaryDirectory() as directory:
                profile = Path(directory)
                for path in measured.PROFILE.iterdir():
                    if path.suffix in {".txt", ".json"}:
                        (profile / path.name).write_bytes(path.read_bytes())
                descriptions = profile / "source-descriptions.json"
                data = json.loads(descriptions.read_bytes())
                data["lakehouse_tables"] += " " + value
                # Escape ASCII too, covering escaped case IDs and GUIDs.
                encoded = json.dumps(data, ensure_ascii=True)
                if value.isascii():
                    encoded = encoded.replace(value, "".join("\\u%04x" % ord(c) for c in value))
                self.assertEqual(json.loads(encoded), data)
                descriptions.write_text(encoded, encoding="utf-8")
                manifest_path = profile / "profile-manifest.json"
                manifest = json.loads(manifest_path.read_bytes())
                import hashlib
                manifest["sha256"][descriptions.name] = hashlib.sha256(descriptions.read_bytes()).hexdigest()
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.subTest(value=value), self.assertRaises(ValueError):
                    measured.profile_inputs(profile)

    def test_cli_writes_fresh_private_artifacts_and_refuses_overwrite_or_git_output(self):
        definition, inputs = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = {"definition": definition, "sql-columns": inputs["sql_columns"],
                      "model-definition": inputs["native_model"], "ontology-item": inputs["ontology_item"]}
            cmd = [sys.executable, "-B", str(Path(measured.__file__).resolve()), "--input-stage", "published"]
            for key, value in values.items():
                path = root / (key + ".json")
                path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                cmd.extend(("--" + key, str(path)))
            cmd.extend(("--output", str(root / "draft.json"), "--receipt", str(root / "receipt.json")))
            completed = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["cloudCalls"], 0)
            self.assertEqual((root / "draft.json").stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        with self.assertRaises(ValueError):
            measured.private_path(measured.REPO / "should-never-contain-live-definitions.json")


if __name__ == "__main__":
    unittest.main()
