"""Synthetic final-gate tests; no live questions, auth, Word build or publication."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(Path(__file__).resolve().parent)]
import build_preview30
import check_preview30_acceptance as command
import package_preview30
from furusato_docs import preview30_acceptance as gate
from test_preview30_selected_reporting import synthetic_run


class FinalAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.request = {"id": "fixture-capture", "lab": "fixture-lab", "completionRequired": True}
        self.evidence = {
            "complete": True, "publicProjection": True, "freezeStatus": "frozen-for-build",
            "labs": {"fixture-lab": {"status": "passed"}},
            "captures": {"fixture-capture": {"completionEvidence": True}},
        }
        self.run = synthetic_run(all_pass=True, accepted=True)
        self.approval = {
            "schemaVersion": gate.APPROVAL_SCHEMA, "selectedOriginalSuiteRunId": self.run["id"],
            "evidenceSha256": "a" * 64, "finalPublicationApproved": True,
            "reviewer": "synthetic-review", "reviewedAt": "2026-10-02T00:00:00Z",
        }

    def assess(self, **changes):
        values = {
            "evidence": self.evidence, "runs": [self.run], "selected_id": self.run["id"],
            "evidence_sha256": "a" * 64, "approval": self.approval,
        }
        values.update(changes)
        with patch.object(gate.private, "requests", return_value=[self.request]):
            return gate.assess(**values)

    def test_all_independent_conditions_and_exact_approval_are_required(self):
        result = self.assess()
        self.assertTrue(result["readyForFinalPublication"])
        self.assertFalse(result["publicationPerformed"])
        self.assertFalse(result["mainPromotionPerformed"])

    def test_earlier_better_or_newer_run_is_never_selected(self):
        failed = synthetic_run()
        better = synthetic_run("synthetic-better", all_pass=True, accepted=True)
        result = self.assess(runs=[better, failed])
        self.assertFalse(result["readyForFinalPublication"])
        self.assertEqual(result["selectedOriginalSuiteRunId"], failed["id"])

    def test_accepted_flag_is_not_inferred_from_zero_fail(self):
        self.run["accepted"] = False
        self.assertFalse(self.assess()["readyForFinalPublication"])

    def test_native_fixed_block_remains_failure(self):
        result = self.assess(runs=[synthetic_run()])
        checks = {row["check"]: row["passed"] for row in result["checks"]}
        self.assertFalse(checks["original-zero-fail"])
        self.assertFalse(checks["original-native-acceptance"])

    def test_targeted_or_heldout_cannot_replace_original_denominator(self):
        for questions, conditions in ((1, 14), (4, 13), (10, 77)):
            run = copy.deepcopy(self.run)
            run.update(questionCount=questions, conditionCount=conditions)
            with self.assertRaises(ValueError):
                self.assess(runs=[run])

    def test_na_is_not_a_workaround_for_an_original_failure(self):
        self.run["counts"]["pass"] -= 1
        self.run["counts"]["notApplicable"] += 1
        self.run["caseAggregates"][1]["counts"]["pass"] -= 1
        self.run["caseAggregates"][1]["counts"]["notApplicable"] += 1
        self.run["notApplicableReason"] = {"ja": "合成の不正な免除", "en": "Synthetic invalid waiver"}
        result = self.assess()
        self.assertFalse(result["readyForFinalPublication"])
        self.assertFalse(next(row["passed"] for row in result["checks"] if row["check"] == "original-na-scope"))

    def test_known_issue_coverage_is_not_all_feature_acceptance(self):
        for status in ("blocked", "failed", "unverified", "observed", "unsupported", "not-run"):
            self.evidence["labs"]["fixture-lab"]["status"] = status
            self.assertFalse(self.assess()["readyForFinalPublication"], status)

    def test_partial_or_missing_capture_never_completes_gate(self):
        self.evidence["captures"]["fixture-capture"]["completionEvidence"] = False
        self.assertFalse(self.assess()["readyForFinalPublication"])
        self.evidence["captures"].clear()
        self.assertFalse(self.assess()["readyForFinalPublication"])

    def test_explicit_hash_bound_approval_cannot_be_defaulted(self):
        self.assertFalse(self.assess(approval=None)["readyForFinalPublication"])
        for key, value in (
            ("finalPublicationApproved", False), ("evidenceSha256", "b" * 64),
            ("selectedOriginalSuiteRunId", "synthetic-other"),
        ):
            approval = {**self.approval, key: value}
            self.assertFalse(self.assess(approval=approval)["readyForFinalPublication"])

    def test_private_or_unfrozen_evidence_cannot_authorize_publication(self):
        self.evidence["publicProjection"] = False
        self.assertFalse(self.assess()["readyForFinalPublication"])
        self.evidence["publicProjection"] = True
        self.evidence["freezeStatus"] = "awaiting-final-consumer-proof"
        self.assertFalse(self.assess()["readyForFinalPublication"])

    def test_malformed_approval_fails_explicitly(self):
        with self.assertRaises(ValueError):
            self.assess(approval={**self.approval, "finalPublicationApproved": "true"})
        with self.assertRaises(ValueError):
            self.assess(approval={**self.approval, "unknown": True})

    def test_builder_stops_before_creating_artifacts_when_admission_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            out, review = Path(temp) / "pair", Path(temp) / "review"
            with patch.object(build_preview30, "require_public_acceptance", side_effect=ValueError("blocked")) as check:
                with patch.object(build_preview30, "build") as build:
                    with self.assertRaisesRegex(ValueError, "blocked"):
                        build_preview30.main(["--out", str(out), "--review", str(review), "--require-acceptance"])
            check.assert_called_once()
            build.assert_not_called()
            self.assertFalse(out.exists())
            self.assertFalse(review.exists())

    def test_packager_stops_before_reading_or_writing_pair(self):
        with patch.object(package_preview30, "require_public_acceptance", side_effect=ValueError("blocked")):
            with patch.object(package_preview30, "load_validated_inputs") as read:
                with self.assertRaisesRegex(ValueError, "blocked"):
                    package_preview30.package(Path("absent"), Path("absent"), Path("absent"), None,
                                              require_acceptance=True)
        read.assert_not_called()

    def test_cli_persists_blocked_result_once_without_submissions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runs, evidence, out = root / "runs.json", root / "evidence.json", root / "decision.json"
            runs.write_text(json.dumps([synthetic_run()]), encoding="utf-8")
            evidence.write_text("{}", encoding="utf-8")
            args = ["--private-evidence", str(evidence), "--original-suite-runs", str(runs),
                    "--selected-original-suite-run-id", self.run["id"], "--out", str(out)]
            with patch.object(command.private, "load", return_value=self.evidence):
                with patch.object(gate.private, "requests", return_value=[self.request]):
                    self.assertEqual(command.main(args), 2)
                    first = out.read_bytes()
                    with self.assertRaises(Exception):
                        command.main(args)
                    self.assertEqual(first, out.read_bytes())
            self.assertFalse(json.loads(first)["readyForFinalPublication"])


if __name__ == "__main__":
    unittest.main()
