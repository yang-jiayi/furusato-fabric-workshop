"""Native serialization regression checks; all identities are synthetic fixtures."""
import base64
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import measured_contract_profile as measured
from source_grounded_profile import decoded_parts, inline_part
import test_measured_contract_profile as legacy_tests


def fixture(stage="published"):
    definition, inputs = legacy_tests.MeasuredContractTests().fixture()
    docs = decoded_parts(definition)
    legacy = docs.pop("Files/Config/published/ontology/datasource.json")
    context = {key: legacy[key] for key in ("workspaceId", "artifactId", "displayName")}
    context.update({"$schema": measured.ONTOLOGY_SCHEMA,
        "elements": [{"id": "observed-entity", "display_name": "SourceEntity",
            "type": "ontology.entity", "is_selected": True,
            "description": "Authored source-owned entity description.", "children": []}],
        "entitiesWithUserAuthoredDescriptions": ["observed-entity"]})
    docs["Files/Config/data_agent.json"] = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/dataAgent/2.1.0/schema.json"}
    if stage == "draft":
        docs = {path: value for path, value in docs.items() if "/draft/" not in path}
        docs = {path.replace("/published/", "/draft/"): value for path, value in docs.items()}
        docs["Files/Config/published/stage_config.json"] = {"aiInstructions": "Preserve unrelated published evidence."}
    path = "Files/Config/" + stage + "/ontologies/" + context["displayName"] + "/ontology.json"
    docs[path] = context
    parts = [inline_part(p, value) for p, value in docs.items() if p != path]
    # Different key order, whitespace and part metadata must survive compilation.
    payload = (json.dumps(context, ensure_ascii=False, indent=5) + "\n\n").encode()
    parts.append({"path": path, "payloadType": "InlineBase64",
        "payload": base64.b64encode(payload).decode(), "serviceMetadata": {"retained": True}})
    inputs["input_stage"] = stage
    return {"parts": parts}, inputs, path


def changed_definition(definition, change):
    docs = decoded_parts(definition)
    change(docs)
    return {"parts": [inline_part(path, value) for path, value in docs.items()]}


class MeasuredNativeContextTests(unittest.TestCase):
    def test_native_context_bytes_and_metadata_survive_both_input_stages(self):
        for stage in ("draft", "published"):
            with self.subTest(stage=stage):
                original, inputs, path = fixture(stage)
                saved = copy.deepcopy((original, inputs))
                output, receipt = measured.compile_measured_draft(original, **inputs)
                self.assertEqual((original, inputs), saved)
                self.assertEqual((output, receipt), measured.compile_measured_draft(original, **inputs))
                expected = copy.deepcopy(next(p for p in original["parts"] if p["path"] == path))
                expected["path"] = path.replace("/published/", "/draft/")
                self.assertEqual(next(p for p in output["parts"] if p["path"] == expected["path"]), expected)
                self.assertEqual([p for p in original["parts"] if "/draft/" not in p["path"]],
                                 [p for p in output["parts"] if "/draft/" not in p["path"]])
                self.assertEqual(receipt["sourceSerialization"], "native-ontology-context")
                self.assertEqual(receipt["physicalDatasourceCount"], 3)
                self.assertEqual(receipt["logicalBindingCount"], 4)
                self.assertTrue(receipt["nativeOntologyPartPreservedByteIdentical"])
                self.assertEqual(receipt["cloudCalls"], 0)
                self.assertFalse(receipt["freshDeploymentOrAnswerAccuracyVerified"])

    def test_unsupported_legacy_fields_are_neither_invented_nor_added_to_global(self):
        original, inputs, path = fixture()
        output, receipt = measured.compile_measured_draft(original, **inputs)
        docs = decoded_parts(output)
        context = docs[path.replace("/published/", "/draft/")]
        self.assertEqual(context, decoded_parts(original)[path])
        for field in ("type", "dataSourceInstructions", "userDescription"):
            self.assertNotIn(field, context)
        instructions, descriptions, _, _, _ = measured.profile_inputs()
        self.assertEqual(docs["Files/Config/draft/stage_config.json"]["aiInstructions"], instructions["global"])
        for kind in measured.DIRECT_KINDS:
            source = docs["Files/Config/draft/" + kind + "/datasource.json"]
            self.assertEqual(source["dataSourceInstructions"], instructions[kind])
            self.assertEqual(source["userDescription"], descriptions[kind])
        self.assertEqual(set(receipt["instructionUtf16Units"]), {"global", *measured.DIRECT_KINDS})
        self.assertEqual(receipt["unsupportedLegacyOntologyInstructionSha256"], measured.digest(instructions["ontology"]))
        self.assertEqual(receipt["unsupportedLegacyOntologyDescriptionSha256"], measured.digest(descriptions["ontology"]))
        self.assertFalse(receipt["legacyOntologyInstructionsInsertedIntoGlobal"])
        self.assertFalse(receipt["legacyOntologyFieldsSynthesized"])
        self.assertNotIn("Files/Config/draft/lakehouse_tables/fewshots.json", docs)
        self.assertEqual(len(docs["Files/Config/draft/kusto/fewshots.json"]["fewShots"]), 9)

    def test_wrapper_and_historical_four_datasources_remain_supported(self):
        for native in (False, True):
            definition, inputs = fixture()[:2] if native else legacy_tests.MeasuredContractTests().fixture()
            with self.subTest(native=native):
                result, receipt = measured.compile_measured_draft({"definition": definition}, **inputs)
                docs, sources, serialization = measured.stage_sources(result, "draft")
                self.assertEqual(set(sources), measured.KINDS)
                self.assertEqual(serialization, "native-ontology-context" if native else "legacy-datasources")
                if not native:
                    self.assertEqual(receipt["physicalDatasourceCount"], 4)
                    self.assertIn("ontology", receipt["instructionUtf16Units"])
                    self.assertIn("dataSourceInstructions", docs["Files/Config/draft/ontology/datasource.json"])

    def test_mixed_duplicate_missing_and_unknown_context_parts_are_rejected(self):
        original, inputs, path = fixture()
        legacy, _ = legacy_tests.MeasuredContractTests().fixture()
        legacy_context = decoded_parts(legacy)["Files/Config/published/ontology/datasource.json"]
        mutations = {
            "mixed": lambda docs: docs.update({"Files/Config/published/ontology/datasource.json": legacy_context}),
            "duplicate": lambda docs: docs.update({path.replace("/ontologies/", "/ontologies/second-"): docs[path]}),
            "missing": lambda docs: docs.pop(path),
            "wrong_path": lambda docs: docs.update({path.replace("/ontologies/", "/contexts/"): docs.pop(path)}),
            "schema": lambda docs: docs[path].update({"$schema": "unobserved-schema"}),
            "instructions": lambda docs: docs[path].update({"dataSourceInstructions": "unsupported"}),
            "description": lambda docs: docs[path].update({"userDescription": "unsupported"}),
            "type": lambda docs: docs[path].update({"type": "ontology"}),
            "empty_elements": lambda docs: docs[path].update({"elements": []}),
            "authored_descriptions": lambda docs: docs[path].update({"entitiesWithUserAuthoredDescriptions": {}}),
            "part_shape": lambda docs: docs.update({path: []}),
            "source_type": lambda docs: docs["Files/Config/published/kusto/datasource.json"].update({"type": []}),
            "duplicate_source": lambda docs: docs.update({"Files/Config/published/another-kusto/datasource.json": docs["Files/Config/published/kusto/datasource.json"]}),
        }
        for name, mutation in mutations.items():
            changed = changed_definition(original, mutation)
            with self.subTest(mutation=name):
                with self.assertRaises(ValueError):
                    measured.stage_sources(changed, "published")
                with self.assertRaises(ValueError):
                    measured.compile_measured_draft(changed, **inputs)

    def test_native_context_identity_generation_and_source_evidence_remain_required(self):
        original, inputs, path = fixture()
        for field, value in (("workspaceId", "00000000-0000-0000-0000-000000000099"),
                             ("artifactId", "00000000-0000-0000-0000-000000000099"),
                             ("artifactId", "not-an-observed-guid")):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                measured.compile_measured_draft(changed_definition(original, lambda docs: docs[path].update({field: value})), **inputs)
        for mutation in ("sql", "model", "gen1", "interpreter", "model_selection"):
            definition, args, _ = fixture()
            if mutation == "sql":
                args["sql_columns"][0]["DATA_TYPE"] = "incorrect"
            elif mutation == "model":
                part = args["native_model"]["parts"][0]
                text = base64.b64decode(part["payload"]).decode().replace("SUM('寄附'[寄附金額])", "SUM('寄附'[寄附ID])", 1)
                part["payload"] = base64.b64encode(text.encode()).decode()
            elif mutation == "gen1":
                args["ontology_item"]["extendedProperties"]["FeatureLevel"] = 1
            elif mutation == "interpreter":
                definition = changed_definition(definition, lambda docs: docs["Files/Config/published/stage_config.json"]["experimental"].update({"codeInterpreterEnabled": False}))
            else:
                definition = changed_definition(definition, lambda docs: docs["Files/Config/published/semantic_model/datasource.json"]["elements"][0]["children"][1].update({"is_selected": False}))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                measured.compile_measured_draft(definition, **args)

    def test_ambiguous_stage_or_extra_topics_cannot_be_silently_dropped(self):
        original, inputs, _ = fixture()
        with self.assertRaises(ValueError):
            measured.stage_sources(original, "unselected")
        changed = changed_definition(original, lambda docs: docs.update({"Files/Config/published/topics.json": {"topics": []}}))
        with self.assertRaises(ValueError):
            measured.compile_measured_draft(changed, **inputs)

    def test_reused_ids_outside_selection_do_not_weaken_selected_identity_checks(self):
        original, inputs, _ = fixture()
        source_path = "Files/Config/published/lakehouse_tables/datasource.json"
        def add_unselected(docs):
            elements = docs[source_path]["elements"]
            grouping = elements[0]
            schema = grouping["children"][0]
            tables = schema["children"][0]
            repeated = "observed-unselected-and-grouping-id"
            for node in (grouping, schema, tables):
                node["id"] = repeated
            tables["children"].append({"id": repeated, "display_name": "ot_supplier_gift",
                "type": "lakehouse_tables.table", "is_selected": False,
                "children": [{"id": repeated, "display_name": name,
                    "type": "lakehouse_tables.column", "data_type": "bigint",
                    "is_selected": False, "children": []} for name in ("SupplierId", "GiftId")]})
        original = changed_definition(original, add_unselected)
        output, _ = measured.compile_measured_draft(original, **inputs)
        before = dict(measured.walk(decoded_parts(original)[source_path]["elements"]))
        after = dict(measured.walk(decoded_parts(output)[source_path.replace("/published/", "/draft/")]["elements"]))
        for path, node in before.items():
            self.assertEqual(after[path]["id"], node["id"])
            if "ot_supplier_gift" in path:
                self.assertEqual(after[path], node)
        def collide_selected(docs):
            columns = [node for path, node in measured.walk(docs[source_path]["elements"])
                       if node["type"] == "lakehouse_tables.column" and "ot_supplier_gift" not in path]
            columns[1]["id"] = columns[0]["id"]
        with self.assertRaises(ValueError):
            measured.compile_measured_draft(changed_definition(original, collide_selected), **inputs)


if __name__ == "__main__":
    unittest.main()
