"""The public regression suite is rebuilt from repository sources only."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_native as runner
import native_evaluation as ne
import regression_suite as rs
from test_native_evaluation import example_case


class RegressionSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = rs.build_suite(rs.REPO)
        cls.manifest = json.loads(
            (rs.REPO / rs.VERSION_ROOT / "data" / "dataset-manifest.json").read_text(encoding="utf-8"))

    def test_committed_suite_equals_source_rebuild(self):
        committed = json.loads(rs.SUITE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(ne.digest(committed), ne.digest(self.suite))

    def test_shape_is_fact_and_content_pairs(self):
        ne.validate_suite(self.suite)
        self.assertEqual(self.suite["kind"], "regression")
        self.assertEqual([c["id"] for c in self.suite["cases"]], [f"B{i:02}" for i in range(1, 20)])
        for case in self.suite["cases"]:
            self.assertEqual([c["id"] for c in case["conditions"]],
                             [f"{case['id']}.fact", f"{case['id']}.content"])
            self.assertTrue(set(case["required_query_languages"]) <= {"SQL", "KQL", "GQL"})

    def test_follow_up_cases_are_bound_to_sources(self):
        values = {c["id"]: c["expected_values"] for c in self.suite["cases"]}
        self.assertEqual(values["B16"]["donation_events_002.csv"]["count"], 5000)
        self.assertEqual(values["B17"]["result"], "BLANK")
        self.assertIn("KEEPFILTERS", values["B17"]["definition"])
        b19 = values["B19"]
        self.assertEqual(b19["gold_count"], b19["static_seed"] + b19["accepted_increment"])
        self.assertEqual(values["B18"]["observed_2026_08"]["count"], 15000)
        self.assertEqual(values["B15"]["observed_amount_rank"], 3)

    def test_gold_layers_agree_with_the_dataset_manifest(self):
        values = {c["id"]: c["expected_values"] for c in self.suite["cases"]}
        text = json.dumps(self.manifest)
        self.assertIn('"uniqueEventIds": 14900', text)
        self.assertEqual(values["B05"]["accepted_increment"], {"count": 14900, "amount_yen": 252058000})
        self.assertEqual(values["B05"]["raw_increment_not_gold"]["count"], 15000)
        self.assertEqual(values["B05"]["gold_total"]["count"], 94900)
        self.assertEqual(values["B06"]["threshold_yen_exclusive"], 57000)
        self.assertEqual(values["B02"]["result"], "BLANK")
        self.assertIn("KEEPFILTERS", values["B02"]["definition"])
        self.assertEqual(sum(h["count"] for h in values["B03"]["hours_utc"]), values["B03"]["count"])
        self.assertEqual(len(values["B03"]["hours_utc"]), 24)

    def test_original_questions_are_not_reused(self):
        original = {c["question"] for c in ne.original_suite(rs.REPO)["cases"]}
        self.assertFalse(original & {c["question"] for c in self.suite["cases"]})

    def test_screen_lists_missing_tokens_but_never_grades(self):
        b14 = next(c for c in self.suite["cases"] if c["id"] == "B14")
        result = rs.screen(self.suite, {"B14": b14["expected"], "B01": "0件です。"})
        by_id = {r["case_id"]: r for r in result}
        self.assertEqual(by_id["B14"]["missing_tokens"], [])
        self.assertIn("3,177,000", by_id["B01"]["missing_tokens"])
        self.assertFalse(by_id["B02"]["captured"])
        self.assertTrue(all("verdict" not in r for r in result))


class RegressionPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("EVALUATION_TEST_TEMP"))
        self.store = ne.PrivateStore(Path(self.temp.name) / "private")
        original = {"schema_version": 1, "kind": "original", "cases": [
            example_case(f"T{i:02}", [], [f"T{i:02}.fixture.{j}" for j in range(n)])
            for i, n in enumerate(ne.ORIGINAL_COUNTS, 1)
        ]}
        ne.freeze_suite(self.store, "original.json", original)
        ne.freeze_suite(self.store, "heldout.json", {
            "schema_version": 1, "kind": "heldout", "cases": [example_case("H01", [])]})
        ne.freeze_suite(self.store, "regression.json", {
            "schema_version": 1, "kind": "regression", "cases": [example_case("B01", [])]})
        self.store.write("data.json", {"fixture": True})
        self.deployment = {"configurations": [{
            "label": "fixture", "workspace_id": str(UUID(int=1)), "data_agent_id": str(UUID(int=2)),
            "stage": "production", "transport": "mcp", "data_fingerprint_file": "data.json",
        }]}

    def tearDown(self):
        self.temp.cleanup()

    def test_regression_slots_are_preregistered_and_reported(self):
        path = runner.create_plan(self.store, "gate", self.deployment, "original.json", "heldout.json",
                                  2, 1, regression_file="regression.json", regression_repeats=1)
        plan = runner.load_plan(self.store, path)
        suites = [s["suite"] for s in plan["slots"]]
        self.assertEqual(suites.count("original"), 2)
        self.assertEqual(suites.count("regression"), 1)
        report = runner.report_campaign(self.store, plan)
        self.assertIn("regression", {g["suite"] for g in report["groups"]})
        self.assertFalse(report["acceptance"])

    def test_suites_cannot_be_interchanged(self):
        with self.assertRaises(ne.EvaluationError):
            runner.create_plan(self.store, "swap", self.deployment, "original.json", "heldout.json",
                               1, 1, regression_file="heldout.json")

    def test_plan_without_regression_is_unchanged(self):
        path = runner.create_plan(self.store, "legacy", self.deployment, "original.json",
                                  "heldout.json", 1, 1)
        plan = runner.load_plan(self.store, path)
        self.assertEqual(set(plan["suite_files"]), {"original", "heldout"})


if __name__ == "__main__":
    unittest.main()
