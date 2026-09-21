"""Offline contract tests for the path-focused Ontology transformer."""

from __future__ import annotations

import base64
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "data-agent"))

import path_ontology  # noqa: E402
from path_ontology import (  # noqa: E402
    OutputWriteError,
    RELATIONSHIP_NAMES,
    build_artifacts,
    decode_parts,
    model_counts,
    parse_model,
    strict_json_loads,
    transform,
    write_fresh_directory,
)

TEMPLATE = (
    ROOT
    / "workshop"
    / "v2.7.0"
    / "ontology"
    / "ontology-full-definition-template.json"
)
CANDIDATE_NAME = "ONT_Furusato_AIPath_Test"
PROTECTED_IDS = [
    "90000000-0000-4000-8000-000000000001",
    "90000000-0000-4000-8000-000000000002",
]
PROTECTION_BASELINE = {
    "path": "synthetic-baseline/snapshot.json",
    "sha256": "a" * 64,
}
SOURCE_FILE_SHA256 = "b" * 64

EXPECTED_KEPT = {
    "Prefecture": ["PrefectureId", "PrefectureName"],
    "Municipality": [
        "MunicipalityId",
        "MunicipalityName",
        "MunicipalityDisplayName",
    ],
    "Donor": ["DonorId", "DonorName", "DonorDisplayName"],
    "GiftCategory": ["CategoryId", "CategoryName"],
    "Gift": ["GiftId", "GiftName", "GiftDisplayName"],
    "Supplier": ["SupplierId", "SupplierName", "SupplierDisplayName"],
    "Donation": ["DonationId", "DonationDisplayName"],
    "MunicipalityCategoryMetric": ["MunCategoryMetricId"],
    "PrefectureCategoryMetric": ["PrefCategoryMetricId"],
    "PrefectureDonationFlow": ["PrefDonationFlowId"],
}


def template_envelope() -> dict:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    return {
        "definition": {
            "parts": [
                {
                    "path": part["path"],
                    "payload": base64.b64encode(
                        json.dumps(
                            part["content"],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).decode("ascii"),
                    "payloadType": "InlineBase64",
                }
                for part in template["parts"]
            ]
        }
    }


def part(envelope: dict, path: str) -> dict:
    record = next(
        record for record in envelope["definition"]["parts"] if record["path"] == path
    )
    return json.loads(base64.b64decode(record["payload"]))


def replace_part(envelope: dict, path: str, mutate) -> None:
    record = next(
        record for record in envelope["definition"]["parts"] if record["path"] == path
    )
    value = json.loads(base64.b64decode(record["payload"]))
    mutate(value)
    record["payload"] = base64.b64encode(
        json.dumps(value, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")


def entity_path(envelope: dict, name: str) -> str:
    model = parse_model(envelope)
    return model.entity_paths[name]


class PathOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = template_envelope()

    def test_actual_canonical_contract_is_54_parts_with_full_graph(self):
        model = parse_model(self.source)
        self.assertEqual(
            model_counts(model),
            {
                "parts": 54,
                "entities": 10,
                "staticProperties": 72,
                "timeseriesProperties": 1,
                "dataBindings": 11,
                "propertyBindings": 74,
                "relationships": 15,
                "contextualizations": 15,
                "contextualizationKeyBindings": 30,
            },
        )
        self.assertEqual(set(model.relationships), RELATIONSHIP_NAMES)
        self.assertIn("MunicipalityCatalogsGift", model.relationships)

    def test_transform_keeps_only_keys_display_and_required_exact_names(self):
        candidate, delta = transform(self.source, CANDIDATE_NAME)
        self.assertEqual(delta["keptProperties"], EXPECTED_KEPT)
        self.assertEqual(
            delta["afterCounts"],
            {
                "parts": 52,
                "entities": 10,
                "staticProperties": 21,
                "timeseriesProperties": 0,
                "dataBindings": 10,
                "propertyBindings": 21,
                "relationships": 15,
                "contextualizations": 15,
                "contextualizationKeyBindings": 30,
            },
        )
        self.assertFalse(delta["liveDeploymentPerformed"])
        self.assertFalse(delta["acceptanceClaimed"])
        self.assertFalse(delta["unsupportedAiPropertyFlagsAdded"])
        self.assertFalse(delta["truthClaimsAdded"])
        self.assertEqual(
            set(parse_model(candidate).relationships),
            RELATIONSHIP_NAMES,
        )

    def test_keys_types_display_names_bindings_and_all_refs_remain_valid(self):
        candidate, _ = transform(self.source, CANDIDATE_NAME)
        model = parse_model(candidate)
        by_name = model.entities
        self.assertEqual(
            next(
                prop["valueType"]
                for prop in by_name["Prefecture"]["properties"]
                if prop["name"] == "PrefectureId"
            ),
            "BigInt",
        )
        self.assertEqual(
            next(
                prop["valueType"]
                for prop in by_name["Donation"]["properties"]
                if prop["name"] == "DonationId"
            ),
            "BigInt",
        )
        self.assertEqual(
            next(
                prop["valueType"]
                for prop in by_name["Municipality"]["properties"]
                if prop["name"] == "MunicipalityId"
            ),
            "String",
        )
        for name, entity in by_name.items():
            with self.subTest(entity=name):
                property_ids = {
                    prop["id"]
                    for collection in (
                        "properties",
                        "timeseriesProperties",
                        "untypedProperties",
                    )
                    for prop in entity.get(collection, [])
                }
                self.assertTrue(set(entity["entityIdParts"]) <= property_ids)
                self.assertIn(entity["displayNamePropertyId"], property_ids)
                bindings = model.bindings[entity["id"]]
                self.assertEqual(len(bindings), 1)
                config = bindings[0][1]["dataBindingConfiguration"]
                self.assertEqual(config["dataBindingType"], "NonTimeSeries")
                self.assertEqual(
                    {mapping["targetPropertyId"] for mapping in config["propertyBindings"]},
                    property_ids,
                )
                self.assertTrue(
                    all(
                        isinstance(mapping["sourceColumnName"], str)
                        and mapping["sourceColumnName"]
                        for mapping in config["propertyBindings"]
                    )
                )

    def test_relationship_structure_and_contextualization_payloads_are_preserved(self):
        candidate, delta = transform(self.source, CANDIDATE_NAME)
        before = decode_parts(self.source)
        after = decode_parts(candidate)
        removed_names = {
            record["name"]
            for records in delta["removedProperties"].values()
            for record in records
        }
        for path, raw in before.items():
            if "/Contextualizations/" in path:
                with self.subTest(path=path):
                    self.assertEqual(after[path], raw)
            elif path.startswith("RelationshipTypes/") and path.endswith("/definition.json"):
                with self.subTest(path=path):
                    source_value = json.loads(raw)
                    candidate_value = json.loads(after[path])
                    source_value.pop("semanticEnrichment", None)
                    candidate_value.pop("semanticEnrichment", None)
                    self.assertEqual(candidate_value, source_value)
                    source_custom = json.loads(raw).get(
                        "semanticEnrichment", {}
                    ).get("customAttributes", {})
                    candidate_custom = json.loads(after[path]).get(
                        "semanticEnrichment", {}
                    ).get("customAttributes", {})
                    for key, value in source_custom.items():
                        rendered = json.dumps({key: value}, ensure_ascii=False)
                        if any(name in rendered for name in removed_names):
                            self.assertEqual(key, "aggregationGuard")
                            self.assertIn(key, candidate_custom)
                            self.assertFalse(
                                any(name in candidate_custom[key] for name in removed_names)
                            )
                        else:
                            self.assertEqual(candidate_custom.get(key), value)
        self.assertFalse(delta["relationshipPayloadsPreservedByteForByte"])
        self.assertTrue(delta["relationshipIdsEndpointsAndOtherFieldsPreserved"])
        self.assertTrue(delta["contextualizationPayloadsPreservedByteForByte"])
        inspection = delta["semanticReferenceInspection"]["relationships"]
        self.assertEqual(len(inspection["detectedBeforeTargetedRepair"]), 5)
        self.assertEqual(inspection["unresolvedAfterRepair"], [])
        relationship_semantics = "\n".join(
            json.dumps(
                value.get("semanticEnrichment", {}),
                ensure_ascii=False,
            )
            for value in parse_model(candidate).relationships.values()
        )
        self.assertFalse(
            any(name in relationship_semantics for name in removed_names)
        )

    def test_numeric_kusto_timeseries_and_empty_overview_are_removed_coherently(self):
        source_model = parse_model(self.source)
        timeseries_path = next(
            path
            for entries in source_model.bindings.values()
            for path, value in entries
            if value["dataBindingConfiguration"]["dataBindingType"] == "TimeSeries"
        )
        candidate, delta = transform(self.source, CANDIDATE_NAME)
        paths = set(decode_parts(candidate))
        self.assertNotIn(timeseries_path, paths)
        self.assertNotIn(
            "EntityTypes/57727254480397/Overviews/definition.json",
            paths,
        )
        removed = {
            prop["name"]
            for prop in delta["removedProperties"]["Municipality"]
        }
        self.assertIn("IncomingDonationAmountYen", removed)
        model = parse_model(candidate)
        self.assertTrue(
            all(
                value["dataBindingConfiguration"]["sourceTableProperties"]["sourceType"]
                != "KustoTable"
                for entries in model.bindings.values()
                for _, value in entries
            )
        )

    def test_platform_identity_is_not_carried_and_unknown_fields_survive(self):
        source = copy.deepcopy(self.source)
        source["auditExtension"] = {"preserve": True}
        entity = entity_path(source, "Gift")
        replace_part(source, entity, lambda value: value.update({"futureField": {"x": 1}}))
        replace_part(
            source,
            ".platform",
            lambda value: value["config"].update({"futurePlatformField": "keep"}),
        )
        candidate, delta = transform(source, CANDIDATE_NAME)
        self.assertEqual(candidate["auditExtension"], {"preserve": True})
        self.assertEqual(part(candidate, entity)["futureField"], {"x": 1})
        platform = part(candidate, ".platform")
        self.assertEqual(platform["metadata"]["displayName"], CANDIDATE_NAME)
        self.assertEqual(platform["config"]["futurePlatformField"], "keep")
        self.assertNotIn("logicalId", platform["config"])
        self.assertTrue(delta["sourcePlatformLogicalIdRemoved"])

    def test_semantic_guidance_is_path_only_without_compliance_claim(self):
        candidate, delta = transform(self.source, CANDIDATE_NAME)
        for name, text in delta["entityDescriptionGuidance"].items():
            with self.subTest(entity=name):
                self.assertIn("exact lookup", text)
                self.assertIn("endpoint label", text)
                self.assertIn("explicit relationship membership/count questions", text)
                self.assertIn("execute graph COUNT", text)
                self.assertIn("does not guarantee Data Agent routing", text)
                self.assertEqual(
                    part(candidate, entity_path(candidate, name))["semanticEnrichment"][
                        "description"
                    ],
                    text,
                )

    def test_relationship_business_roles_and_count_evidence_remain_explicit(self):
        candidate, _ = transform(self.source, CANDIDATE_NAME)
        before = parse_model(self.source)
        after = parse_model(candidate)
        for name, original in before.relationships.items():
            original_description = original["semanticEnrichment"]["description"].replace(
                "DonationAmountYen", "donation amounts from the governed SQL source"
            )
            description = after.relationships[name]["semanticEnrichment"]["description"]
            with self.subTest(relationship=name):
                self.assertTrue(description.startswith(original_description))
                self.assertIn("execute graph COUNT", description)
                self.assertNotIn("no metric, allocation, count", description)
        supplier = after.relationships["SupplierProvidesGift"]["semanticEnrichment"]
        self.assertIn("does not prove an actual fulfillment", supplier["description"])
        self.assertIn("No allocation", supplier["customAttributes"]["aggregationGuard"])

    def test_unknown_stale_relationship_metadata_is_not_silently_deleted(self):
        source = copy.deepcopy(self.source)
        model = parse_model(source)
        path = model.relationship_paths["MunicipalityInPrefecture"]
        replace_part(
            source,
            path,
            lambda value: value["semanticEnrichment"]["customAttributes"].update(
                {"futureRule": "DonationAmountYen"}
            ),
        )
        with self.assertRaisesRegex(ValueError, "Unassessed stale relationship custom attribute"):
            transform(source, CANDIDATE_NAME)

    def test_rejects_ambiguous_unknown_duplicate_and_unknown_payload_paths(self):
        cases = []

        backslash = copy.deepcopy(self.source)
        backslash["definition"]["parts"][0]["path"] = r"EntityTypes\1\definition.json"
        cases.append((backslash, "Ambiguous or noncanonical"))

        unknown = copy.deepcopy(self.source)
        unknown["definition"]["parts"].append(
            {
                "path": "EntityTypes/1/Documents/readme.json",
                "payload": base64.b64encode(b"{}").decode("ascii"),
                "payloadType": "InlineBase64",
            }
        )
        cases.append((unknown, "Unhandled Ontology definition part path"))

        duplicate = copy.deepcopy(self.source)
        duplicate["definition"]["parts"].append(
            copy.deepcopy(duplicate["definition"]["parts"][0])
        )
        cases.append((duplicate, "Duplicate definition part path"))

        payload = copy.deepcopy(self.source)
        payload["definition"]["parts"][0]["payloadType"] = "InlineJson"
        cases.append((payload, "Unsupported payloadType"))

        for envelope, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                decode_parts(envelope)

    def test_rejects_duplicate_property_ids_key_removal_and_missing_display(self):
        duplicate = copy.deepcopy(self.source)
        path = entity_path(duplicate, "Prefecture")

        def duplicate_id(value):
            value["properties"][1]["id"] = value["properties"][0]["id"]

        replace_part(duplicate, path, duplicate_id)
        with self.assertRaisesRegex(ValueError, "Duplicate property ID"):
            parse_model(duplicate)

        missing_key = copy.deepcopy(self.source)
        path = entity_path(missing_key, "Donation")
        replace_part(
            missing_key,
            path,
            lambda value: value["properties"].pop(0),
        )
        with self.assertRaisesRegex(ValueError, "key references a missing property"):
            parse_model(missing_key)

        missing_display = copy.deepcopy(self.source)
        path = entity_path(missing_display, "Gift")

        def remove_display(value):
            display = value["displayNamePropertyId"]
            value["properties"] = [
                prop for prop in value["properties"] if prop["id"] != display
            ]

        replace_part(missing_display, path, remove_display)
        with self.assertRaisesRegex(ValueError, "display name references a missing property"):
            parse_model(missing_display)

    def test_rejects_nonempty_overview_instead_of_guessing_references(self):
        source = copy.deepcopy(self.source)
        path = "EntityTypes/57727254480397/Overviews/definition.json"
        replace_part(
            source,
            path,
            lambda value: value.update({"widgets": [{"type": "lineChart"}]}),
        )
        with self.assertRaisesRegex(ValueError, "Nonempty Overview semantics are unsupported"):
            parse_model(source)

    def test_rejects_unknown_overview_fields_before_omission(self):
        source = copy.deepcopy(self.source)
        path = "EntityTypes/57727254480397/Overviews/definition.json"
        replace_part(
            source,
            path,
            lambda value: value.update(
                {"futureSemanticSelection": {"property": "MunicipalityName"}}
            ),
        )
        with self.assertRaisesRegex(ValueError, "Unassessed Overview fields"):
            parse_model(source)

    def test_rejects_cross_entity_property_name_type_conflicts(self):
        source = copy.deepcopy(self.source)
        path = entity_path(source, "Donor")

        def create_type_conflict(value):
            donor_name = next(
                prop for prop in value["properties"] if prop["name"] == "DonorName"
            )
            donor_name["name"] = "PrefectureId"
            donor_name["valueType"] = "String"

        replace_part(source, path, create_type_conflict)
        with self.assertRaisesRegex(ValueError, "conflicting value types"):
            parse_model(source)

    def test_transform_rejects_any_unassessed_extra_removal(self):
        extra_overview = copy.deepcopy(self.source)
        donor_id = parse_model(extra_overview).entities["Donor"]["id"]
        extra_overview["definition"]["parts"].append(
            {
                "path": f"EntityTypes/{donor_id}/Overviews/definition.json",
                "payload": base64.b64encode(
                    json.dumps({"widgets": [], "settings": None}).encode("utf-8")
                ).decode("ascii"),
                "payloadType": "InlineBase64",
            }
        )
        with self.assertRaisesRegex(ValueError, "assessed canonical 54-part contract"):
            transform(extra_overview, CANDIDATE_NAME)

        extra_timeseries = copy.deepcopy(self.source)
        extra_model = parse_model(extra_timeseries)
        municipality_id = extra_model.entities["Municipality"]["id"]
        original = next(
            record for record in extra_timeseries["definition"]["parts"]
            if any(
                record["path"] == path
                and value["dataBindingConfiguration"]["dataBindingType"] == "TimeSeries"
                for entries in extra_model.bindings.values()
                for path, value in entries
            )
        )
        duplicate_binding = copy.deepcopy(original)
        duplicate_binding["path"] = (
            f"EntityTypes/{municipality_id}/DataBindings/"
            "30000000-0000-4000-8000-000000000001.json"
        )
        value = json.loads(base64.b64decode(duplicate_binding["payload"]))
        value["id"] = "30000000-0000-4000-8000-000000000001"
        duplicate_binding["payload"] = base64.b64encode(
            json.dumps(value).encode("utf-8")
        ).decode("ascii")
        extra_timeseries["definition"]["parts"].append(duplicate_binding)
        with self.assertRaisesRegex(ValueError, "assessed canonical 54-part contract"):
            transform(extra_timeseries, CANDIDATE_NAME)

    def test_rejects_empty_or_ambiguous_binding_column_references(self):
        empty_static = copy.deepcopy(self.source)
        model = parse_model(empty_static)
        static_path = model.bindings[model.entities["Donation"]["id"]][0][0]
        replace_part(
            empty_static,
            static_path,
            lambda value: value["dataBindingConfiguration"]["propertyBindings"][0].update(
                {"sourceColumnName": ""}
            ),
        )
        with self.assertRaisesRegex(ValueError, "source-column identifier"):
            parse_model(empty_static)

        empty_context = copy.deepcopy(self.source)
        context_path = next(
            path
            for path in decode_parts(empty_context)
            if "/Contextualizations/" in path
        )
        replace_part(
            empty_context,
            context_path,
            lambda value: value["sourceKeyRefBindings"][0].update(
                {"sourceColumnName": "has space"}
            ),
        )
        with self.assertRaisesRegex(ValueError, "source-column identifier"):
            parse_model(empty_context)

    def test_rejects_duplicate_json_members_before_lossy_parsing(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON object member: futureField"):
            strict_json_loads('{"futureField":1,"futureField":2}')
        source = copy.deepcopy(self.source)
        path = entity_path(source, "Gift")
        record = next(
            record for record in source["definition"]["parts"] if record["path"] == path
        )
        record["payload"] = base64.b64encode(
            b'{"id":"21065477330866","futureField":1,"futureField":2}'
        ).decode("ascii")
        with self.assertRaisesRegex(ValueError, "not valid UTF-8 JSON"):
            parse_model(source)

    def test_private_artifacts_are_explicitly_not_deployed_or_accepted(self):
        artifacts = build_artifacts(
            self.source,
            CANDIDATE_NAME,
            PROTECTED_IDS,
            PROTECTION_BASELINE,
            SOURCE_FILE_SHA256,
        )
        self.assertEqual(
            set(artifacts),
            {
                "candidate-definition.json",
                "semantic-delta.json",
                "protected-inventory.json",
                "readiness-summary.json",
                "deployment-plan.json",
            },
        )
        readiness = artifacts["readiness-summary.json"]
        self.assertEqual(
            readiness["status"],
            "OFFLINE_STRUCTURALLY_READY_FOR_PARENT_REVIEW",
        )
        self.assertFalse(readiness["liveDeploymentPerformed"])
        self.assertFalse(readiness["accepted"])
        self.assertFalse(artifacts["deployment-plan.json"]["automaticWrite"])
        self.assertEqual(
            artifacts["protected-inventory.json"]["protectedItemIds"],
            PROTECTED_IDS,
        )
        self.assertEqual(
            artifacts["protected-inventory.json"]["reusedProtectionBaseline"],
            PROTECTION_BASELINE,
        )
        inspection = artifacts["semantic-delta.json"]["semanticReferenceInspection"][
            "entitiesAndRetainedProperties"
        ]
        self.assertEqual(
            artifacts["semantic-delta.json"]["sourceDefinitionSha256"],
            SOURCE_FILE_SHA256,
        )
        self.assertEqual(
            artifacts["protected-inventory.json"]["sourceDefinitionSha256"],
            SOURCE_FILE_SHA256,
        )
        self.assertEqual(len(inspection["detectedBeforeTargetedRepair"]), 1)
        self.assertEqual(
            inspection["detectedBeforeTargetedRepair"][0]["removedProperties"][0]["name"],
            "DonationAmountYen",
        )
        self.assertEqual(len(inspection["targetedRepairs"]), 1)
        self.assertEqual(inspection["unresolvedAfterRepair"], [])
        self.assertTrue(
            readiness["checks"]["noDanglingSemanticReferences"]
        )
        plan = artifacts["deployment-plan.json"]
        self.assertNotIn(
            "new server-assigned item identity",
            plan["requiredExplicitDeploymentInputs"],
        )
        self.assertTrue(
            any("after the create LRO" in step for step in plan["steps"])
        )
        self.assertFalse(any("literal yes" in step for step in plan["steps"]))

    def test_output_must_be_external_and_fresh(self):
        artifacts = build_artifacts(
            self.source,
            CANDIDATE_NAME,
            PROTECTED_IDS,
            PROTECTION_BASELINE,
            SOURCE_FILE_SHA256,
        )
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            target = parent / "fresh"
            write_fresh_directory(target, artifacts)
            self.assertEqual(
                json.loads((target / "semantic-delta.json").read_text("utf-8"))[
                    "keptProperties"
                ],
                EXPECTED_KEPT,
            )
            with self.assertRaisesRegex(ValueError, "already exists"):
                write_fresh_directory(target, artifacts)

            empty = parent / "existing-empty"
            empty.mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                write_fresh_directory(empty, artifacts)

            nonempty = parent / "existing-nonempty"
            nonempty.mkdir()
            (nonempty / "owned-by-someone-else.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "already exists"):
                write_fresh_directory(nonempty, artifacts)
            self.assertEqual(
                (nonempty / "owned-by-someone-else.txt").read_text(encoding="utf-8"),
                "keep",
            )

            with self.assertRaisesRegex(ValueError, "parent traversal"):
                write_fresh_directory(parent / "alias" / ".." / "escaped", artifacts)

        with self.assertRaisesRegex(ValueError, "outside the repository"):
            write_fresh_directory(ROOT / "private-output-must-fail", artifacts)

    def test_output_rejects_link_alias_when_supported(self):
        artifacts = build_artifacts(
            self.source,
            CANDIDATE_NAME,
            PROTECTED_IDS,
            PROTECTION_BASELINE,
            SOURCE_FILE_SHA256,
        )
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            destination = parent / "real"
            destination.mkdir()
            alias = parent / "alias"
            try:
                alias.symlink_to(destination, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Directory symlinks unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "symbolic links|reparse points"):
                write_fresh_directory(alias, artifacts)

    def test_concurrent_directory_appearance_writes_nothing(self):
        artifacts = build_artifacts(
            self.source,
            CANDIDATE_NAME,
            PROTECTED_IDS,
            PROTECTION_BASELINE,
            SOURCE_FILE_SHA256,
        )
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "race"

            def concurrent_mkdir(path, *args, **kwargs):
                os.mkdir(path)
                raise FileExistsError(path)

            with patch.object(Path, "mkdir", new=concurrent_mkdir):
                with self.assertRaisesRegex(ValueError, "appeared concurrently"):
                    write_fresh_directory(target, artifacts)
            self.assertTrue(target.is_dir())
            self.assertEqual(list(target.iterdir()), [])

    def test_partial_owned_output_is_retained_and_marked_failed(self):
        artifacts = build_artifacts(
            self.source,
            CANDIDATE_NAME,
            PROTECTED_IDS,
            PROTECTION_BASELINE,
            SOURCE_FILE_SHA256,
        )
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "partial"
            original_write = path_ontology._exclusive_write
            calls = 0

            def fail_second_write(path, data):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic write failure")
                return original_write(path, data)

            with patch.object(
                path_ontology,
                "_exclusive_write",
                side_effect=fail_second_write,
            ):
                with self.assertRaisesRegex(OutputWriteError, "Partial output retained"):
                    write_fresh_directory(target, artifacts)
            self.assertTrue(target.is_dir())
            self.assertTrue((target / "candidate-definition.json").is_file())
            failure = json.loads((target / "_FAILED.json").read_text(encoding="utf-8"))
            self.assertEqual(failure["status"], "FAILED_PARTIAL_OUTPUT_RETAINED")
            self.assertEqual(failure["writtenFiles"], ["candidate-definition.json"])
            self.assertEqual(failure["failedArtifact"], "semantic-delta.json")


if __name__ == "__main__":
    unittest.main()
