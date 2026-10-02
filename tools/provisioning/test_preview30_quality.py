import copy
import json
from pathlib import Path
import tempfile
import unittest

from preview30_quality import PROFILE, build_candidate, canonical_relationship_grounding, query_examples
from preview30_runtime import SafetyError


def frozen_stage():
    stage = {"stage_config.json": {
        "$schema": "stage", "aiInstructions": "baseline",
        "experimental": {"enableExperimentalFeatures": True, "codeInterpreterEnabled": True},
    }}
    for kind in ("kusto", "lakehouse_tables", "ontology", "semantic_model"):
        stage[kind + "/datasource.json"] = {
            "type": kind, "artifactId": kind + "-item", "workspaceId": "workspace",
            "dataSourceInstructions": "old " + kind, "metadata": {},
            "userDescription": "source", "elements": [{"name": "same", "is_selected": True}],
        }
    return stage


class QualityCandidateTests(unittest.TestCase):
    def test_transformation_preserves_input_and_every_non_guidance_field(self):
        original = frozen_stage()
        snapshot = copy.deepcopy(original)
        candidate, contract = build_candidate(original)
        self.assertEqual(original, snapshot)
        self.assertEqual(candidate["stage_config.json"]["experimental"], original["stage_config.json"]["experimental"])
        for path, source in original.items():
            if path.endswith("/datasource.json"):
                expected = dict(source)
                observed = dict(candidate[path])
                expected.pop("dataSourceInstructions")
                observed.pop("dataSourceInstructions")
                if source["type"] == "semantic_model":
                    expected.pop("userDescription")
                    observed.pop("userDescription")
                self.assertEqual(expected, observed)
        self.assertIn("StaticSeed", candidate["semantic_model/datasource.json"]["dataSourceInstructions"])
        self.assertFalse(contract["semanticModelGuidancePreserved"])
        self.assertFalse(contract["answerQualityAccepted"])
        self.assertFalse(contract["nativeExamplesValidated"])

    def test_examples_use_selected_view_and_general_parameters_not_benchmark_answers(self):
        examples = query_examples()
        payload = json.dumps(examples)
        for forbidden in ("5000001", "452025", "80000", "15000", "14900", "5737000", "1344099000", "東京都", "宮崎県"):
            self.assertNotIn(forbidden, payload)
        for row in examples["kusto"]["fewShots"]:
            self.assertIn("DonationObservationSummaryForAgent", row["query"])
            self.assertNotIn("DonationEvents", row["query"])
            self.assertNotIn("distinct EventID", row["query"])
        for row in examples["kusto"]["fewShots"][1:]:
            self.assertIn("YearCount == 1", row["query"])
            self.assertIn("SelectedYear", row["query"])
            self.assertNotIn("2025", row["query"])
            self.assertNotIn("2026", row["query"])
            self.assertNotIn("yyyy-MM-ddTHH:mm:ssZ", row["query"])
        self.assertEqual(examples, query_examples())

    def test_kql_utc_rendering_uses_supported_format_tokens_and_explicit_literals(self):
        for row in query_examples()["kusto"]["fewShots"][1:3]:
            self.assertIn("replace_string(format_datetime(", row["query"])
            self.assertIn("'yyyy-MM-dd HH:mm:ss'", row["query"])
            self.assertIn("' ', 'T'), 'Z'", row["query"])

    def test_trace_contains_intermediate_ids_and_no_order_fulfillment_claim(self):
        trace = query_examples()["lakehouse_tables"]["fewShots"][0]["query"]
        for column in ("DonorResidencePrefectureId", "RecipientPrefectureId", "category.CategoryId", "supplier.SupplierId"):
            self.assertIn(column, trace)
        self.assertIn("ORDER BY supplier.SupplierId", trace)
        self.assertNotIn("SUM(", trace)
        for column in ("AS AttributeSource", "AS AttributeDataset", "AS AttributeGrain",
                       "LEFT JOIN dbo.ot_supplier_gift", "LEFT JOIN dbo.ot_supplier"):
            self.assertIn(column, trace)
        for column in ("supplier.PrefectureId AS SupplierPrefectureId",
                       "supplier_pref.PrefectureName AS SupplierPrefectureName",
                       "LEFT JOIN dbo.ot_prefecture AS supplier_pref"):
            self.assertIn(column, trace)

    def test_reapplying_identical_guidance_reports_no_fictitious_changes(self):
        first, _ = build_candidate(frozen_stage())
        second, contract = build_candidate(first)
        self.assertEqual(first, second)
        self.assertEqual([], contract["changedFields"])
        self.assertTrue(contract["semanticModelGuidancePreserved"])
        self.assertIsNone(contract["semanticModelGuidanceChanged"])

    def test_full_sql_attribute_proof_is_not_replaced_by_graph_properties(self):
        global_text = (PROFILE / "global-instructions.txt").read_text(encoding="utf-8")
        sql_text = (PROFILE / "lakehouse-instructions.txt").read_text(encoding="utf-8")
        for clause in ("COMPLETE SQL attribute ledger FIRST", "does NOT discharge the SQL attribute requirement",
                       "An introductory list of both engines is not attribution", "GQL-only attributes"):
            self.assertIn(clause, global_text)
        for clause in ("even when a separately executed GQL query", "every catalog supplier",
                       "AS AttributeSource", "AS AttributeDataset", "AS AttributeGrain"):
            self.assertIn(clause, sql_text)
        self.assertIn("Provenance is field-level, not merely engine-level", global_text)
        self.assertIn('Never use a blanket "all attributes and IDs came from SQL"', sql_text)

    def test_semantic_scope_uses_existing_static_measures_without_changing_model_data(self):
        text = (PROFILE / "semantic-model-instructions.txt").read_text(encoding="utf-8")
        for required in ("[静的寄附件数]", "[静的寄附総額]", "StaticSeed", "Combined Gold is legitimate only"):
            self.assertIn(required, text)
        for forbidden in ("2661", "8784", "54,520,000", "T03"):
            self.assertNotIn(forbidden, text)

    def test_canonical_grounding_preserves_real_schema_names_without_instance_answers(self):
        text = canonical_relationship_grounding()
        self.assertEqual(15, len([line for line in text.splitlines() if line.startswith("- ")]))
        self.assertIn("Municipality -MunicipalityInPrefecture-> Prefecture", text)
        self.assertIn("schema metadata, not evidence of an instance query", text)
        self.assertNotIn("PrefectureContainsMunicipality", text)
        self.assertNotIn("5000001", text)

    def test_global_has_distinct_temporal_grain_and_literal_direction_contracts(self):
        text = (PROFILE / "global-instructions.txt").read_text(encoding="utf-8")
        self.assertLessEqual(len(text), 15000)
        for clause in ("never inherits the static snapshot year",         "Do NOT request individual child IDs",
                       "FirstObservedAtUtc", "All timestamps are UTC.",
                       "Relationship: <stored source type>", "(reverse)",
                       "Respect native safety blocks", "No selected source exposes raw EventID"):
            self.assertIn(clause, text)
        for forbidden in ("T04", "T05", "T06", "48 PASS", "36 FAIL", "5000001", "452025", "14,900"):
            self.assertNotIn(forbidden, text)

    def test_refusal_and_count_contracts_do_not_require_invented_queries_or_child_rows(self):
        global_text = (PROFILE / "global-instructions.txt").read_text(encoding="utf-8")
        ontology_text = (PROFILE / "ontology-instructions.txt").read_text(encoding="utf-8")
        self.assertIn("they do not require a data query", global_text)
        self.assertIn("without SQL/KQL/GQL/DAX or Python", global_text)
        self.assertIn("If a native safety block is returned, preserve it", global_text)
        self.assertIn("GROUP BY ParentId, ParentName", ontology_text)
        self.assertIn("Do not generate OVER, PARTITION BY, or WITH", ontology_text)

    def test_missing_or_extra_source_and_disabled_ci_fail_closed(self):
        for change in ("missing", "extra", "ci"):
            stage = frozen_stage()
            if change == "missing":
                del stage["ontology/datasource.json"]
            elif change == "extra":
                stage["extra/datasource.json"] = dict(stage["kusto/datasource.json"])
            else:
                stage["stage_config.json"]["experimental"]["codeInterpreterEnabled"] = False
            with self.assertRaises(SafetyError):
                build_candidate(stage)

    def test_oversized_global_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            (profile / "global-instructions.txt").write_text("x" * 15001, encoding="utf-8")
            with self.assertRaises(SafetyError):
                build_candidate(frozen_stage(), profile=profile)


if __name__ == "__main__":
    unittest.main()
