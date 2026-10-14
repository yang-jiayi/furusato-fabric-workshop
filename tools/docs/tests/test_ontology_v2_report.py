"""Synthetic fixtures only: validate public-report accounting, boundaries and real rendering.

No fixture is a Fabric response or an actual evaluation result. Render tests emit
only conspicuously labelled synthetic artifacts into temporary private storage.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_ontology_v2_report as report


def fake_digest(label):
    return hashlib.sha256(("SYNTHETIC FIXTURE ONLY: " + label).encode()).hexdigest()


def verdicts(passed, failed, unclear=0, na=0):
    return dict(zip(report.VERDICTS, (passed, failed, unclear, na)))


def group(phase, name, questions, conditions, repetitions, content):
    return {"name": name, "questions": questions, "conditions": conditions, "repetitions": repetitions,
            "suiteSha256": fake_digest(phase + name), "content": content,
            "strictNativeConditions": verdicts(max(0, content["PASS"] - 2), content["FAIL"] + min(2, content["PASS"]), content["UNCLEAR"], content["NA"])}


def phase(name, groups):
    questions = sum(row["questions"] for row in groups)
    return {"name": name,
            **{key: fake_digest(name + key) for key in ("publicationDefinitionSha256", "sourceDefinitionSha256", "sourceBusinessSha256",
               "captureLedgerSha256", "contentReviewLedgerSha256", "strictNativeReviewLedgerSha256", "independentContentReviewSha256", "phaseClosureSha256")},
            "groups": groups,
            "collection": {"httpTimeoutSeconds": 300, "captureTimeoutSeconds": 900, "definitionTimeoutSeconds": 600,
                           "newConversationPerQuestion": True, "retryPolicy": "never-resubmit-consumed-slot"},
            "captures": {"registeredQuestions": questions, "questionPOSTs": questions, "notSubmitted": 0,
                         "unfinalizedCaptures": 0, "uncertainQuestionPOSTUpperBound": 0,
                         "knownTerminalResponses": questions, "retainedFailures": 0,
                         "nativeRecordStatuses": {"completed": questions}, "unknownResponseStatus": 0,
                         "completed": questions, "failed": 0, "cancelled": 0, "incomplete": 0,
                         "responsesWithInternalErrors": 1, "responsesWithIncompleteEvidence": 1,
                         "responsesWithSuccessfulSourceExecution": questions - 1, "strictNativeAcceptedResponses": questions - 1}}


def synthetic_fixture():
    """Deliberately invented counts exercise accounting; they are not performance claims."""
    qualification = phase("qualification", [group("qualification", "qualification", 2, 5, 1, verdicts(3, 1, 1))])
    baseline = phase("baseline", [group("baseline", "original", 30, 252, 3, verdicts(180, 60, 12)),
                                  group("baseline", "regression", 19, 38, 1, verdicts(20, 14, 4)),
                                  group("baseline", "heldout", 2, 6, 1, verdicts(4, 1, 1))])
    final = phase("final", [group("final", "original", 30, 252, 3, verdicts(210, 36, 6)),
                            group("final", "regression", 19, 38, 1, verdicts(30, 6, 2)),
                            group("final", "heldout", 2, 6, 1, verdicts(5, 1))])
    counts = (195, 3, 2, 40, 30, 4, 5, 9, 2)
    matrix = [{"baseline": before, "final": after, "conditions": n}
              for (before, after), n in zip(((a, b) for a in report.MATCHED_VERDICTS for b in report.MATCHED_VERDICTS), counts)]
    text = {"ja": "合成fixture専用の文章です。実環境の結果ではありません。", "en": "Synthetic fixture prose only; this is not an observed deployment result."}
    return {"schema": report.SCHEMA, "date": "2026-10-15", "timeZone": "Asia/Tokyo", "inputKind": "synthetic-fixture",
            "artifactSourceDateEpoch": 1792022400, "protocolSha256": fake_digest("protocol"),
            "method": {"contentReview": "codex-supplemental-with-separate-review", "independentHumanSignoff": False,
                       "strictGradersChanged": False, "originalVerdictsPreserved": True, "favorableRetrySelection": False,
                       "platformWideBugFixClaimed": False, "heldoutComparison": "disjoint-groups-not-paired",
                       "unknownPolicy": "retain-in-denominator-not-pass", "evidenceReferences": "private-ledger-digests-not-public-evidence"},
            "phases": [qualification, baseline, final],
            "pairedComparison": {"scope": ["original", "regression"], "registeredConditionsPerPhase": 290,
                                 "matchingKey": report.MATCHING_KEY.copy(), "equalFields": report.EQUAL_FIELDS.copy(),
                                 "matchedLedgerSha256": fake_digest("paired"),
                                 "baselineContentReviewLedgerSha256": baseline["contentReviewLedgerSha256"],
                                 "finalContentReviewLedgerSha256": final["contentReviewLedgerSha256"],
                                 "matchedConditions": 290, "exclusions": [], "transitions": matrix},
            "changes": [copy.deepcopy(text)], "findings": [copy.deepcopy(text)], "limitations": [copy.deepcopy(text)],
            "calibrationSteps": [copy.deepcopy(text)], "recommendation": copy.deepcopy(text)}


class SummaryContractTests(unittest.TestCase):
    def setUp(self):
        self.study = synthetic_fixture()

    def validate(self, study=None):
        return report.validate_summary(self.study if study is None else study, allow_synthetic_fixture=True)

    def test_full_population_and_unpaired_holdout_are_preserved(self):
        self.validate()
        for phase_name in ("baseline", "final"):
            phase_value = next(row for row in self.study["phases"] if row["name"] == phase_name)
            self.assertEqual(51, sum(row["questions"] for row in phase_value["groups"]))
            self.assertEqual(296, sum(row["conditions"] for row in phase_value["groups"]))
        self.assertEqual(290, self.study["pairedComparison"]["matchedConditions"])
        blocks = report.shared_blocks(self.study)
        text = "\n".join(report.text_content(blocks))
        self.assertIn("SYNTHETIC TEST FIXTURE", text)
        self.assertIn("200/290", text)
        self.assertIn("240/290", text)
        self.assertIn("13.79 pp", text)
        self.assertNotIn("245/296", text.split("Exact paired-condition comparison")[1].split("Capture and internal-execution status")[0])

    def test_fixture_flag_required_and_cannot_look_observed(self):
        with self.assertRaisesRegex(ValueError, "Synthetic fixtures require"):
            report.validate_summary(self.study)

    def test_wrong_or_reduced_condition_denominators_fail(self):
        for change in ("original", "regression", "heldout", "verdict", "repeat", "bool"):
            with self.subTest(change=change):
                study = copy.deepcopy(self.study)
                groups = study["phases"][1]["groups"]
                if change in ("original", "regression", "heldout"):
                    next(row for row in groups if row["name"] == change)["conditions"] -= 1
                elif change == "verdict":
                    groups[0]["content"]["UNCLEAR"] -= 1
                elif change == "repeat":
                    groups[0]["repetitions"] = 1
                else:
                    groups[1]["repetitions"] = True
                with self.assertRaises(ValueError):
                    self.validate(study)

    def test_unseen_sets_are_separate_and_never_paired(self):
        for change in ("heldout-same", "scope", "denominator"):
            with self.subTest(change=change):
                study = copy.deepcopy(self.study)
                if change == "heldout-same":
                    study["phases"][-1]["groups"][2]["suiteSha256"] = study["phases"][1]["groups"][2]["suiteSha256"]
                elif change == "scope":
                    study["pairedComparison"]["scope"].append("heldout")
                else:
                    study["pairedComparison"]["registeredConditionsPerPhase"] = 296
                with self.assertRaises(ValueError):
                    self.validate(study)

    def test_pair_matrix_requires_every_cell_and_reconciles_both_margins(self):
        for change in ("missing-cell", "duplicate-cell", "different-ledger", "counts", "key", "eligibility"):
            with self.subTest(change=change):
                study = copy.deepcopy(self.study)
                pair = study["pairedComparison"]
                if change == "missing-cell":
                    pair["transitions"].pop()
                elif change == "duplicate-cell":
                    pair["transitions"][-1] = pair["transitions"][0].copy()
                elif change == "different-ledger":
                    pair["finalContentReviewLedgerSha256"] = fake_digest("wrong-ledger")
                elif change == "counts":
                    pair["transitions"][0]["conditions"] -= 1
                    pair["transitions"][1]["conditions"] += 1
                elif change == "key":
                    pair["matchingKey"].remove("condition_id")
                else:
                    pair["equalFields"].remove("sourceBusinessSha256")
                with self.assertRaises(ValueError):
                    self.validate(study)

    def test_explicit_clarification_na_requires_symmetric_proven_exclusion(self):
        group = self.study["phases"][1]["groups"][0]
        group["content"]["UNCLEAR"] -= 1
        group["content"]["NA"] += 1
        group["naEligibilityEvidenceSha256"] = fake_digest("allowed-original-na")
        pair = self.study["pairedComparison"]
        pair["matchedConditions"] -= 1
        cell = next(row for row in pair["transitions"] if row["baseline"] == "UNCLEAR" and row["final"] == "FAIL")
        cell["conditions"] -= 1
        pair["exclusions"] = [{"reasonCode": "declared-clarification-branch", "conditions": 1,
                               "reason": {"ja": "既定の確認質問分岐", "en": "Predeclared clarification branch"},
                               "baseline": verdicts(0, 0, 0, 1), "final": verdicts(0, 1),
                               "evidenceSha256": fake_digest("symmetric-exclusion") }]
        self.validate()
        invalid = copy.deepcopy(self.study)
        invalid["pairedComparison"]["exclusions"][0]["final"] = verdicts(0, 0, 1)
        with self.assertRaises(ValueError):
            self.validate(invalid)
        invalid = copy.deepcopy(self.study)
        del invalid["phases"][1]["groups"][0]["naEligibilityEvidenceSha256"]
        with self.assertRaises(ValueError):
            self.validate(invalid)

    def test_na_cannot_remove_failures_from_other_groups(self):
        for name in ("regression", "heldout"):
            with self.subTest(name=name):
                study = copy.deepcopy(self.study)
                row = next(g for g in study["phases"][1]["groups"] if g["name"] == name)
                row["content"]["FAIL"] -= 1
                row["content"]["NA"] += 1
                row["naEligibilityEvidenceSha256"] = fake_digest("not-allowed")
                with self.assertRaises(ValueError):
                    self.validate(study)

    def test_strict_question_passes_and_capture_counts_cannot_exceed_completed_records(self):
        for change in ("native-accept", "status-sum", "post-count", "timeout", "retry"):
            with self.subTest(change=change):
                study = copy.deepcopy(self.study)
                row = study["phases"][1]
                if change == "native-accept":
                    row["captures"]["strictNativeAcceptedResponses"] = 52
                elif change == "status-sum":
                    row["captures"]["incomplete"] = 1
                elif change == "post-count":
                    row["captures"]["questionPOSTs"] = 50
                elif change == "timeout":
                    row["collection"]["httpTimeoutSeconds"] = 120
                else:
                    row["collection"]["retryPolicy"] = "retry-to-pass"
                with self.assertRaises(ValueError):
                    self.validate(study)

    def test_strict_passes_keep_observational_query_and_error_counts_separate(self):
        capture = self.study["phases"][1]["captures"]
        capture.update(strictNativeAcceptedResponses=51, responsesWithSuccessfulSourceExecution=0,
                       responsesWithInternalErrors=12, responsesWithIncompleteEvidence=4)
        self.validate()
        rendered = " ".join(report.text_content(report.shared_blocks(self.study)))
        self.assertIn("A justified clarification or refusal can require no query", rendered)
        self.assertIn("Strict question passes", rendered)
        self.assertIn("Source execution", rendered)

    def test_incomplete_and_unsubmitted_questions_remain_in_full_denominator(self):
        capture = self.study["phases"][-1]["captures"]
        capture.update(questionPOSTs=50, notSubmitted=1, completed=48, failed=1, incomplete=1,
                       knownTerminalResponses=50, retainedFailures=3,
                       nativeRecordStatuses={"completed": 48, "native_failure_captured": 2, "pre_submission_blocked": 1},
                       responsesWithSuccessfulSourceExecution=47, strictNativeAcceptedResponses=47)
        self.validate()
        self.assertEqual(296, sum(g["conditions"] for g in self.study["phases"][-1]["groups"]))

    def test_targeted_waves_are_separate_and_limited_to_eight(self):
        wave1 = phase("targeted-01", [group("targeted-01", "targeted", 4, 8, 1, verdicts(6, 2))])
        wave2 = phase("targeted-02", [group("targeted-02", "targeted", 4, 8, 1, verdicts(7, 1))])
        self.study["phases"][2:2] = [wave1, wave2]
        self.validate()
        wave2["groups"][0]["questions"] = 5
        wave2["captures"].update(registeredQuestions=5, questionPOSTs=5, completed=5,
                                 knownTerminalResponses=5, nativeRecordStatuses={"completed": 5})
        with self.assertRaisesRegex(ValueError, "budget"):
            self.validate()

    def test_unfinalized_capture_and_uncertain_post_are_not_invented_known_submissions(self):
        capture = self.study["phases"][-1]["captures"]
        capture.update(questionPOSTs=48, notSubmitted=1, unfinalizedCaptures=2,
                       uncertainQuestionPOSTUpperBound=1, knownTerminalResponses=47,
                       completed=46, failed=1, incomplete=0, unknownResponseStatus=1,
                       nativeRecordStatuses={"completed": 44, "evidence_incomplete": 3,
                                             "pre_submission_blocked": 1, "unfinished_timeout": 1},
                       retainedFailures=7, responsesWithSuccessfulSourceExecution=43,
                       strictNativeAcceptedResponses=43)
        self.validate()
        self.assertEqual(296, sum(g["conditions"] for g in self.study["phases"][-1]["groups"]))
        for change in ("questionPOSTs", "knownTerminalResponses", "retainedFailures"):
            with self.subTest(change=change):
                broken = copy.deepcopy(self.study)
                broken["phases"][-1]["captures"][change] += 1
                with self.assertRaises(ValueError):
                    self.validate(broken)
        capture["uncertainQuestionPOSTUpperBound"] = 3
        with self.assertRaises(ValueError):
            self.validate()

    def test_completed_response_does_not_override_failed_native_capture(self):
        capture = self.study["phases"][-1]["captures"]
        capture.update(nativeRecordStatuses={"completed": 45, "evidence_incomplete": 6}, retainedFailures=6)
        with self.assertRaises(ValueError):
            self.validate()
        capture["strictNativeAcceptedResponses"] = 45
        self.validate()

    def test_fixture_cannot_change_review_or_platform_acceptance_boundaries(self):
        for key in ("independentHumanSignoff", "strictGradersChanged", "favorableRetrySelection", "platformWideBugFixClaimed"):
            with self.subTest(key=key):
                study = copy.deepcopy(self.study)
                study["method"][key] = True
                with self.assertRaises(ValueError):
                    self.validate(study)

    def test_decoded_secrets_paths_and_private_case_markers_are_rejected(self):
        for text in ("AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", "Heading\nAAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", "Heading\nT01", "/var/tmp/private", "/workspace/private", "T01", "OQ01", "C:\\private\\file", "Bearer " + "x" * 45):
            with self.subTest(kind=text[:4]):
                study = copy.deepcopy(self.study)
                study["limitations"][0]["en"] = text
                encoded = json.dumps(study).replace("A", "\\u0041")
                with self.assertRaises(ValueError):
                    self.validate(json.loads(encoded))

    def test_unknown_fields_and_partial_bilingual_text_are_rejected(self):
        for change in ("field", "language", "hash", "date"):
            with self.subTest(change=change):
                study = copy.deepcopy(self.study)
                if change == "field":
                    study["rawTrace"] = "unreviewed"
                elif change == "language":
                    del study["findings"][0]["en"]
                elif change == "hash":
                    study["protocolSha256"] = "not-a-digest"
                else:
                    study["date"] = "20261015"
                with self.assertRaises(ValueError):
                    self.validate(study)

    def test_undefined_percentage_and_rounding_are_explicit(self):
        self.assertIsNone(report.percentage(0, 0))
        self.assertEqual("13.79", report.percentage(40, 290))
        self.assertEqual("-13.79", report.percentage(-40, 290))


class SyntheticRenderingTests(unittest.TestCase):
    def test_actual_docx_html_render_shares_content_without_implying_live_evidence(self):
        parent = Path(os.environ["EVALUATION_TEST_TEMP"])
        self.assertTrue(parent.is_dir())
        with tempfile.TemporaryDirectory(prefix="materials-20261015-synthetic-fixture-", dir=parent) as root:
            root = Path(root)
            source = root / "SYNTHETIC-FIXTURE-summary.json"
            source.write_text(json.dumps(synthetic_fixture(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            before_epoch = os.environ.get("SOURCE_DATE_EPOCH")
            receipt = report.build(source, root / "rendered-SYNTHETIC-FIXTURE", allow_synthetic_fixture=True)
            self.assertEqual(before_epoch, os.environ.get("SOURCE_DATE_EPOCH"))
            self.assertTrue(receipt["wordHtmlSharedContentParity"])
            self.assertTrue(receipt["pairedTransitionsReconciled"])
            self.assertTrue(receipt["syntheticFixtureIsNotActualEvidence"])
            self.assertFalse(receipt["microsoftWordRenderChecked"])
            self.assertFalse(receipt["htmlBrowserChecked"])
            self.assertFalse(receipt["privateLedgerContentsIndependentlyVerifiedByRenderer"])
            files = receipt["outputs"]
            self.assertTrue(all(name.startswith("SYNTHETIC-FIXTURE-") for name in files))
            word = root / "rendered-SYNTHETIC-FIXTURE" / next(name for name in files if name.endswith(".docx"))
            web = root / "rendered-SYNTHETIC-FIXTURE" / next(name for name in files if name.endswith(".html"))
            html_text = web.read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC TEST FIXTURE", html_text)
            self.assertIn(files[word.name], html_text)
            self.assertIn("200/290", html_text)
            with zipfile.ZipFile(word) as archive:
                document = archive.read("word/document.xml")
                self.assertIn(b"Noto Sans CJK JP", document)
                self.assertIn(b"SYNTHETIC TEST FIXTURE", document)
                self.assertNotIn(b"fldChar", document)
                self.assertNotIn(b"instrText", document)
                self.assertIn(b"General", archive.read("docProps/custom.xml"))
            with self.assertRaises(FileExistsError):
                report.build(source, root / "rendered-SYNTHETIC-FIXTURE", allow_synthetic_fixture=True)

    def test_build_refuses_repository_output_before_writing(self):
        with self.assertRaises(ValueError):
            report.private_output(report.REPO / "docs/disallowed-output", report.REPO)


if __name__ == "__main__":
    unittest.main(verbosity=2)
