"""Guard public report denominators, privacy and scoped acceptance boundaries."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from build_measured_tuning_report import validate_summary

ROOT = TOOLS.parents[1]


class MeasuredReportValidationTests(unittest.TestCase):
    def setUp(self):
        self.summary = json.loads(
            (ROOT / "docs/v3.0.0/tuning-20261010/result-20261010.json").read_text(encoding="utf-8")
        )

    def test_source_owned_aggregate_retains_all_verdicts_and_phase_boundaries(self):
        validated = validate_summary(self.summary)
        matched = validated["matchedOriginal"]
        actual_delta = (matched["R8"]["PASS"] - matched["baseline"]["PASS"]) / matched["conditions"] * 100
        self.assertEqual(matched["deltaPercentagePoints"], round(actual_delta, 2))
        self.assertFalse(validated["method"]["latestFull51Retested"])
        self.assertEqual(validated["latestTargetedChecks"][-1]["conditions"]["registeredConditions"], 4)

    def test_inconsistent_denominators_and_capture_counts_are_rejected(self):
        for changed in ("verdict", "percentage", "exclusion", "captures"):
            with self.subTest(changed=changed):
                study = copy.deepcopy(self.summary)
                if changed == "verdict":
                    study["regression"]["baseline"]["UNCLEAR"] = 0
                elif changed == "percentage":
                    study["matchedOriginal"]["deltaPercentagePoints"] += 1
                elif changed == "exclusion":
                    study["matchedOriginal"]["exclusionsFromBothPhases"]["baselineClarificationNotApplicable"] = 0
                else:
                    study["latestTargetedChecks"][0]["captureStatuses"]["completed"] += 1
                with self.assertRaises(ValueError):
                    validate_summary(study)

    def test_scoped_review_cannot_be_promoted_into_independent_or_full_acceptance(self):
        for key in ("independentHumanSignoff", "strictNativeAcceptanceAssigned", "latestFull51Retested"):
            with self.subTest(key=key):
                study = copy.deepcopy(self.summary)
                study["method"][key] = True
                with self.assertRaises(ValueError):
                    validate_summary(study)

    def test_decoded_uppercase_identifier_and_private_path_are_rejected(self):
        for value in ("AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", "/var/tmp/private-example"):
            with self.subTest(value=value):
                study = copy.deepcopy(self.summary)
                study["remainingLimitations"].append(value)
                encoded = json.dumps(study).replace("A", "\\u0041")
                with self.assertRaises(ValueError):
                    validate_summary(json.loads(encoded))


if __name__ == "__main__":
    unittest.main()
