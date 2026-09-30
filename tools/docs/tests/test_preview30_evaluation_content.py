"""Safe projection tests using synthetic aggregate fixtures, never private answers."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
from furusato_docs.preview30_evaluation import project, STATES


def fixture():
    return {
        "schema_version": "furusato-preview30-report/v1",
        "generated_at_utc": "2026-09-29T00:00:00+00:00",
        "case_count": 1, "requested_slots": 1, "supported_requested_slots": 0,
        "state_counts": {name: int(name == "blocked") for name in STATES},
        "supported_pass": 0, "supported_fail": 0, "supported_missing_evidence": 0,
        "ai": {
            "requested_questions": 1, "supported_requested_questions": 0,
            "scored_questions": 0, "pass": 0, "accuracy": None,
            "missing_supported_questions": 0,
            "aggregate_withheld_until_supported_inventory_complete": True,
        },
        "inventory": [{
            "case_id": "FIXTURE_AI", "repeat": 1, "category": "ai",
            "critical": True, "state": "blocked", "support": "pending",
        }],
        "original_inventory": {
            "question_count": 10, "condition_count": 84,
            "independent_hidden": False, "state": "blocked",
        },
    }


class EvaluationProjectionTests(unittest.TestCase):
    def test_unknown_support_and_unscored_accuracy_are_retained(self):
        safe = project(fixture())
        self.assertEqual(0, safe["supported_requested_slots"])
        self.assertEqual("pending", safe["inventory"][0]["support"])
        self.assertIsNone(safe["ai"]["accuracy"])
        self.assertTrue(safe["ai"]["aggregate_withheld_until_supported_inventory_complete"])

    def test_only_approved_fields_survive_recursively(self):
        raw = fixture()
        marker = "DO_NOT_PUBLISH_PRIVATE_CONTENT"
        raw.update({"context": marker, "reasons": marker, "errors": marker, "raw_evidence": marker, "traces": marker, "heldout": marker})
        raw["ai"]["private_answer"] = marker
        raw["inventory"][0].update({"reason": marker, "prompt": marker, "path": marker, "trace": marker})
        raw["original_inventory"]["routing_applicability"] = marker
        safe = project(raw)
        self.assertNotIn(marker, json.dumps(safe))
        self.assertEqual({"case_id", "repeat", "category", "critical", "state", "support"}, set(safe["inventory"][0]))
        self.assertEqual({"question_count", "condition_count", "independent_hidden", "state"}, set(safe["original_inventory"]))

    def test_does_not_mutate_private_input(self):
        raw = fixture()
        before = copy.deepcopy(raw)
        project(raw)
        self.assertEqual(before, raw)

    def test_wrong_document_kind_is_rejected(self):
        raw = fixture()
        raw["schema_version"] = "private-corpus/v1"
        with self.assertRaises(ValueError):
            project(raw)

    def test_zero_accuracy_cannot_replace_unscored_null(self):
        raw = fixture()
        raw["ai"]["accuracy"] = 0.0
        with self.assertRaises(ValueError):
            project(raw)

    def test_state_denominators_cannot_be_dropped(self):
        raw = fixture()
        raw["requested_slots"] = 0
        with self.assertRaises(ValueError):
            project(raw)

    def test_private_path_disguised_as_identifier_is_rejected(self):
        raw = fixture()
        raw["inventory"][0]["case_id"] = r"C:\private\answer.txt"
        with self.assertRaises(ValueError):
            project(raw)

    def test_original_ten84_is_not_relabelled_independent_hidden(self):
        raw = fixture()
        raw["original_inventory"]["independent_hidden"] = True
        with self.assertRaises(ValueError):
            project(raw)


if __name__ == "__main__":
    unittest.main()
