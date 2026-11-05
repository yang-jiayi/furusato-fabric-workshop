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


def summary_group(registered, passed, failed=0, unclear=0, na=0):
    applicable = registered - na
    return {
        "PASS": passed,
        "FAIL": failed,
        "UNCLEAR": unclear,
        "NA": na,
        "registeredConditions": registered,
        "applicableConditions": applicable,
        "passPercent": round(passed / applicable * 100, 2),
    }


def synthetic_summary():
    return {
        "schema": "furusato-measured-contract-summary/v1",
        "date": "2026-01-15",
        "method": {
            "independentHumanSignoff": False,
            "strictNativeAcceptanceAssigned": False,
            "strictGradersChanged": False,
            "favorableRetrySelection": False,
            "causalEffectIsolatedFromCaptureAvailability": False,
            "latestFull51Retested": False,
            "originalVerdictsPreserved": True,
        },
        "original": {
            "conditionsPerRepetition": 2,
            "repetitions": 2,
            "baseline": summary_group(4, 2, failed=1, na=1),
            "R8": summary_group(4, 4),
        },
        "regression": {
            "baseline": summary_group(4, 2, failed=1, unclear=1),
            "R8": summary_group(4, 3, failed=1),
        },
        "disjointUnusedSets": {
            "baseline": summary_group(2, 1, failed=1),
            "R8": summary_group(2, 2),
        },
        "qualitySupplement": {
            "baseline": summary_group(2, 1, failed=1),
            "R8": summary_group(2, 1, unclear=1),
        },
        "matchedOriginal": {
            "conditions": 2,
            "baseline": {"PASS": 1, "FAIL": 1, "passPercent": 50.0},
            "R8": {"PASS": 2, "FAIL": 0, "passPercent": 100.0},
            "deltaPercentagePoints": 50.0,
            "exclusionsFromBothPhases": {
                "baselineClarificationNotApplicable": 1,
                "other": 1,
            },
            "original252JudgmentsModified": False,
        },
        "latestTargetedChecks": [
            {
                "conditions": summary_group(2, 1, na=1),
                "full51Retested": False,
                "questions": 2,
                "questionPOSTs": 2,
                "knownTerminalResponses": 2,
                "captureStatuses": {"completed": 1, "notCaptured": 1},
            },
            {
                "conditions": summary_group(4, 3, failed=1),
                "full51Retested": False,
                "questions": 4,
                "questionPOSTs": 4,
                "knownTerminalResponses": 4,
                "captureStatuses": {"completed": 4},
            },
        ],
        "artifactSourceDateEpoch": 1760000000,
        "privateEvidenceDigests": [{"sha256": "a" * 64}],
        "remainingLimitations": [],
    }


class MeasuredReportValidationTests(unittest.TestCase):
    def setUp(self):
        self.summary = synthetic_summary()

    def test_source_owned_aggregate_retains_all_verdicts_and_phase_boundaries(self):
        validated = validate_summary(self.summary)
        matched = validated["matchedOriginal"]
        actual_delta = (matched["R8"]["PASS"] - matched["baseline"]["PASS"]) / matched["conditions"] * 100
        self.assertEqual(matched["deltaPercentagePoints"], round(actual_delta, 2))
        self.assertFalse(validated["method"]["latestFull51Retested"])
        self.assertEqual(validated["latestTargetedChecks"][-1]["conditions"]["registeredConditions"], 4)

    def test_inconsistent_denominators_and_capture_counts_are_rejected(self):
        for changed in ("verdict", "percentage", "exclusion", "captures",
                        "na-applicable", "na-percentage", "later-phase"):
            with self.subTest(changed=changed):
                study = copy.deepcopy(self.summary)
                if changed == "verdict":
                    study["regression"]["baseline"]["UNCLEAR"] = 0
                elif changed == "percentage":
                    study["matchedOriginal"]["deltaPercentagePoints"] += 1
                elif changed == "exclusion":
                    study["matchedOriginal"]["exclusionsFromBothPhases"]["baselineClarificationNotApplicable"] = 0
                elif changed == "captures":
                    study["latestTargetedChecks"][0]["captureStatuses"]["completed"] += 1
                elif changed == "na-applicable":
                    study["original"]["baseline"]["applicableConditions"] -= 1
                elif changed == "na-percentage":
                    study["original"]["baseline"]["passPercent"] += 1
                else:
                    study["latestTargetedChecks"][-1]["full51Retested"] = True
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
