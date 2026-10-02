"""Synthetic offline contract fixtures, including observed-live approval branches.

No values here are live results. No suite, private report, ledger or network is read.
"""

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from contextlib import ExitStack, redirect_stdout
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html"), str(Path(__file__).resolve().parent)]

import build_preview30 as builder
import package_preview30 as packager
import validate_preview30 as validator
from build_preview30_reports import report_payloads
from furusato_docs import preview30_acceptance as acceptance
from furusato_docs import preview30_content as content
from furusato_docs import preview30_evaluation100 as study100
from furusato_docs import preview30_release as release
from furusato_docs import preview30_reporting as reporting
from furusato_docs.validators import Report
from furusato_html import preview30 as html_renderer
from furusato_html.model import Document
from test_preview30_content import signature
from test_preview30_release import snapshot, SyntheticRefresh, WORD_FIXTURE, HTML_FIXTURE


def h(label):
    return hashlib.sha256(("SYNTHETIC PRIVATE TEST " + label).encode("ascii")).hexdigest()


def add(left, right):
    return {key: add(left[key], right[key]) if isinstance(left[key], dict) else left[key] + right[key] for key in left}


def metrics(n, passes, *, blocks=0, protected=0, error=0, unsent=0, uncertain=0, failed=0, unreviewed=0):
    answers = n - blocks - protected - error - unsent - uncertain - failed
    factual_fail = answers - unreviewed - passes
    return {
        "uniqueCases": n, "terminalCases": n,
        "submissionIntents": answers + blocks + error + uncertain + failed,
        "capturedResponses": answers + blocks + error, "nativeBlocks": blocks,
        "unknownOutcomes": uncertain + failed,
        "terminalCounts": {
            "answerCaptured": answers, "nativeServiceBlocked": blocks, "nativeErrorReply": error,
            "protectedNotResubmitted": protected, "notSubmitted": unsent,
            "submissionUncertain": uncertain, "captureFailed": failed,
        },
        "axes": {
            "factualCorrectness": {"pass": passes, "fail": factual_fail, "unknown": n - answers + unreviewed, "notApplicable": 0},
            "contextualHelpfulness": {"pass": passes, "fail": factual_fail + blocks + protected,
                                     "unknown": error + unsent + uncertain + failed + unreviewed},
            "protectiveBoundary": {"pass": answers - unreviewed, "fail": 0,
                                   "unknown": error + unsent + uncertain + failed + unreviewed,
                                   "notApplicable": 0, "nativeServiceBlock": blocks, "retainedServiceBlock": protected},
            "answerContent": {"pass": passes, "fail": factual_fail + blocks + protected + error + failed,
                              "unknown": unsent + uncertain + unreviewed},
        },
    }


def synthetic_study(*, intervention=False, buckets=False, observed=False, execution_amendment=False):
    bindings = {
        "suiteManifestSha256": h("suite"), "inputManifestSha256": h("inputs"),
        "splitLockSha256": h("split"), "rubricSha256": h("unchanged rubric"),
        "sourceFileHashes": {key: h(key) for key in ("capture-client", "shared-reviewer", "ai-review-entrypoint")},
    }
    bindings["sourceFilesSha256"] = study100.digest(bindings["sourceFileHashes"])
    binding_sha, policy_sha = study100.digest(bindings), h("review policy finalized during capture")

    def run(name, candidate_name, parts):
        result = {
            "candidate": {"profileLabel": "synthetic-" + candidate_name,
                          "candidateSha256": h(candidate_name), "definitionSha256": h(candidate_name + " definition")},
            "bindingSha256": binding_sha, "reviewPolicySha256": policy_sha, "sourceReportSha256": h(name + " report"),
            "metrics": add(parts[0], parts[1]),
        }
        if buckets:
            result["buckets"] = [{"label": label, "metrics": value} for label, value in zip(("synthetic-a", "synthetic-b"), parts)]
        return result

    base_parts = [metrics(40, 25, blocks=2, uncertain=1, unreviewed=2),
                  metrics(40, 19, blocks=2, error=2, unsent=2, uncertain=2, failed=1, unreviewed=3)]
    changed_parts = [metrics(40, 23, blocks=1, protected=2, unsent=1, unreviewed=1),
                     metrics(40, 17, blocks=1, protected=2, error=1, unsent=1, uncertain=1, failed=1, unreviewed=2)]
    held_parts = [metrics(10, 6, blocks=1, unreviewed=1), metrics(10, 4, unsent=1, uncertain=1, unreviewed=1)]
    baseline = run("baseline", "baseline", base_parts)
    changed = run("intervention", "intervention", changed_parts) if intervention else None
    name = "intervention" if intervention else "baseline"
    final_dev = changed if intervention else baseline
    heldout = run("heldout", name, held_parts)
    combined = run("combined", name, [add(a, b) for a, b in zip(changed_parts if intervention else base_parts, held_parts)])
    combined.update(finalDevelopmentReportSha256=final_dev["sourceReportSha256"], heldoutReportSha256=heldout["sourceReportSha256"])
    result = {
        "schemaVersion": study100.SCHEMA,
        "evidenceKind": "observed-live" if observed else "synthetic-private-test",
        "snapshotDate": "2026-10-02", "projectedAtUtc": "2026-10-02T10:00:00Z",
        "denominators": {"unique": 100, "development": 80, "heldout": 20},
        "bindings": bindings, "bindingSha256": binding_sha,
        "review": {"mode": "ai-assisted", "policySha256": policy_sha,
                   "reviewPolicyTiming": study100.REVIEW_POLICY_TIMING, "fullReviewPolicyPreregistered": False,
                   "methodTimingEvidence": "operator-receipt-and-filesystem-corroboration",
                   "methodTimingIndependentlyCertified": False, "methodPreregistered": False,
                   "methodPreregistrationClaim": "corroborated-not-independently-proven",
                   "originalMethodTimingCorroborated": True, "reviewToolingPreregistered": False,
                   "methodEvidenceHashProvenance": "computedAtAdmission",
                   "methodIntentSha256": h("preserved method intent hashed at admission"),
                   "timingAdmissionReceiptSha256": h("timing admission before content grading"),
                   "timingAdmissionBeforeContentGrading": True,
                   "rubricUnchanged": True, "noIndependentHumanSignoff": True, "automaticSemanticPass": False},
        "observability": {"internalQueries": "UNOBSERVABLE", "backendConversations": "UNOBSERVABLE"},
        "final": {"stage": "final-frozen", "developmentRound": name, "candidateSha256": h(name),
                  "freezeReceiptSha256": h("final freeze"), "heldoutClaimSha256": h("irreversible reservation"),
                  "frozenAtUtc": "2026-10-02T08:00:00Z", "heldoutReservedAtUtc": "2026-10-02T08:01:00Z",
                  "frozenBeforeHeldout": True, "heldoutIrreversiblySpent": True, "heldoutUsedForTuning": False,
                  "bestOfPooling": False, "baselineAnswersBorrowed": False, "selectionPolicy": "all_once_declared_cases_no_best_of"},
        "baseline": baseline,
        "intervention": {"authorizationSha256": h("single intervention authorization"), "baselineReportSha256": baseline["sourceReportSha256"],
                         "meaningfulChange": True, "noSafetyBypass": True, "run": changed} if intervention else None,
        "heldout": heldout, "combined": combined,
    }
    if execution_amendment:
        amend_execution_fixture(result)
    return result


def amend_execution_fixture(value, *, captured=17, failure=None, outcome="completed"):
    """Synthetic terminal accounting only; never an actual continuation report."""
    development = value["intervention"]["run"]
    candidate = {
        "profileLabel": "synthetic-final-candidate",
        "candidateSha256": study100.CONTINUATION_CANDIDATE_SHA256,
        "definitionSha256": study100.CONTINUATION_DEFINITION_SHA256,
    }
    value["final"].update(developmentRound="intervention", candidateSha256=candidate["candidateSha256"])
    for run in (development, value["heldout"], value["combined"]):
        run["candidate"] = copy.deepcopy(candidate)
    ordered = ["answerCaptured"] * captured + ([failure] if failure else [])
    ordered += ["notSubmitted"] * (17 - len(ordered))
    continued = {key: ordered.count(key) for key in study100.TERMINALS}
    parts = []
    for index, slots in enumerate((ordered[:7], ordered[7:])):
        terminal = {key: slots.count(key) for key in study100.TERMINALS}
        if index == 0:
            terminal["answerCaptured"] += 2
            terminal["submissionUncertain"] += 1
        parts.append(metrics(
            10, 0, blocks=terminal["nativeServiceBlocked"], protected=terminal["protectedNotResubmitted"],
            error=terminal["nativeErrorReply"], unsent=terminal["notSubmitted"],
            uncertain=terminal["submissionUncertain"], failed=terminal["captureFailed"],
            unreviewed=terminal["answerCaptured"],
        ))
    heldout = value["heldout"]
    heldout["metrics"] = add(parts[0], parts[1])
    value["combined"]["metrics"] = add(development["metrics"], heldout["metrics"])
    value["combined"]["finalDevelopmentReportSha256"] = development["sourceReportSha256"]
    if "buckets" in heldout:
        for bucket, part in zip(heldout["buckets"], parts):
            bucket["metrics"] = part
        for total, dev, held in zip(value["combined"]["buckets"], development["buckets"], heldout["buckets"]):
            total["metrics"] = add(dev["metrics"], held["metrics"])
    value["executionProtocol"] = {
        "label": "post-stop-unsent-slots-only",
        "originalPlanSha256": study100.ORIGINAL_HELDOUT_PLAN_SHA256,
        "continuationPlanSha256": study100.CONTINUATION_PLAN_SHA256,
        "originalStoppedBatchSha256": h("unchanged stopped heldout batch"),
        "reconciliationSha256": h("synthetic immutable reconciliation"),
        "reportSha256": value["combined"]["sourceReportSha256"],
        "executionAmendmentPreregistered": False, "originalNoResumePolicyAmended": True,
        "originalProtocolWasFullyFollowed": False, "originalClaimsRemainSpent": True,
        "retrySubmittedOrUncertainCases": False, "sourceTransportCandidateOrQuestionChanges": False,
        "heldoutFeedbackTuning": False, "noBestOf": True,
        "priorCaptured": 2, "priorUnknown": 1, "eligibleUnsent": 17, "priorUnknownHttpStatus": 500,
        "continuationInvocations": 1, "stopOnNextFailure": True, "outcome": outcome,
        "continuationTerminalCounts": continued,
    }


class StudyContractTests(unittest.TestCase):
    def rejects(self, mutation, *, intervention=True, buckets=True):
        value = synthetic_study(intervention=intervention, buckets=buckets)
        mutation(value)
        with self.assertRaises(ValueError):
            study100.validate(value)

    def test_valid_baseline_and_worse_intervention_are_distinct_not_improvement_claims(self):
        for intervention in (False, True):
            for buckets in (False, True):
                with self.subTest(intervention=intervention, buckets=buckets):
                    value = synthetic_study(intervention=intervention, buckets=buckets)
                    original = copy.deepcopy(value)
                    checked = study100.validate(value)
                    self.assertEqual(original, value)
                    self.assertEqual(original, checked)
                    self.assertIsNot(value, checked)
                    self.assertNotIn("methodPreregisteredBeforePlanAuthQuestions", checked["review"])
                    self.assertIs(False, checked["review"]["methodPreregistered"])
                    self.assertIs(False, checked["review"]["methodTimingIndependentlyCertified"])
                    if intervention:
                        self.assertLess(checked["intervention"]["run"]["metrics"]["axes"]["answerContent"]["pass"],
                                        checked["baseline"]["metrics"]["axes"]["answerContent"]["pass"])
                        self.assertEqual(50, checked["combined"]["metrics"]["axes"]["answerContent"]["pass"])

    def test_original_denominators_and_all_terminal_slots_are_mandatory(self):
        mutations = [
            lambda d: d["denominators"].update(unique=99),
            lambda d: d["denominators"].update(development=100, heldout=0),
            lambda d: d["baseline"]["metrics"].update(terminalCases=79),
            lambda d: d["baseline"]["metrics"].update(uniqueCases=79),
            lambda d: d["heldout"]["metrics"]["terminalCounts"].update(notSubmitted=0),
            lambda d: d["combined"]["metrics"]["axes"]["answerContent"].pop("unknown"),
            lambda d: d["combined"]["metrics"]["axes"]["factualCorrectness"].update(unknown=0),
        ]
        for change in mutations:
            with self.subTest(change=change):
                self.rejects(change)

    def test_non_integer_negative_boolean_and_non_finite_counts_are_rejected(self):
        for value in (-1, 1.0, True, None, "1", float("nan"), float("inf"), 101):
            with self.subTest(value=value):
                self.rejects(lambda d: d["baseline"]["metrics"].update(submissionIntents=value))

    def test_submission_capture_unknown_and_native_block_counts_cannot_disagree(self):
        for field in ("submissionIntents", "capturedResponses", "nativeBlocks", "unknownOutcomes"):
            with self.subTest(field=field):
                self.rejects(lambda d: d["baseline"]["metrics"].update({field: 0}))
        self.rejects(lambda d: d["intervention"]["run"]["metrics"]["terminalCounts"].update(protectedNotResubmitted=0))
        self.rejects(lambda d: d["baseline"]["metrics"]["axes"]["protectiveBoundary"].update(nativeServiceBlock=0, **{"pass": 67}))
        self.rejects(lambda d: d["baseline"]["metrics"]["axes"]["factualCorrectness"].update(unknown=0, **{"pass": 61}))
        self.rejects(lambda d: d["baseline"]["metrics"]["axes"]["answerContent"].update(unknown=0, **{"pass": 54}))

    def test_all_unsubmitted_unknowns_are_not_zero_percent_or_false_pass(self):
        value = synthetic_study()
        for key, count in (("baseline", 80), ("heldout", 20), ("combined", 100)):
            value[key]["metrics"] = metrics(count, 0, unsent=count)
        study100.validate(value)
        self.assertEqual(100, value["combined"]["metrics"]["axes"]["answerContent"]["unknown"])
        self.assertNotIn("accuracy", json.dumps(value).lower())
        invalid = copy.deepcopy(value)
        invalid["combined"]["metrics"]["axes"]["answerContent"].update({"pass": 100, "unknown": 0})
        with self.assertRaises(ValueError):
            study100.validate(invalid)

    def test_content_cannot_hide_contributing_axis_failures_as_unknown(self):
        value = synthetic_study()
        value["baseline"]["metrics"] = metrics(80, 40)
        value["baseline"]["metrics"]["axes"]["answerContent"].update(fail=20, unknown=20)
        value["combined"]["metrics"] = add(value["baseline"]["metrics"], value["heldout"]["metrics"])
        with self.assertRaisesRegex(ValueError, "content cannot pass"):
            study100.validate(value)

    def test_each_stage_is_bound_to_suite_files_rubric_and_review_policy(self):
        mutations = [
            lambda d: d["bindings"].update(suiteManifestSha256=h("wrong suite")),
            lambda d: d["bindings"].update(rubricSha256=h("wrong rubric")),
            lambda d: d["bindings"]["sourceFileHashes"].update(**{"capture-client": h("changed source")}),
            lambda d: d["bindings"].update(sourceFilesSha256=h("wrong file inventory")),
            lambda d: d["bindings"].update(sourceFileHashes={}),
            lambda d: d["heldout"].update(bindingSha256=h("another source")),
            lambda d: d["intervention"]["run"].update(reviewPolicySha256=h("another review policy")),
            lambda d: d["combined"].update(sourceReportSha256=d["heldout"]["sourceReportSha256"]),
        ]
        for change in mutations:
            with self.subTest(change=change):
                self.rejects(change)
        for bad in ("", "SHA256", "a" * 63, "A" * 64, "g" * 64, None, 0):
            with self.subTest(sha=bad):
                self.rejects(lambda d: d["baseline"]["candidate"].update(candidateSha256=bad))

    def test_ai_assisted_mode_is_not_human_or_native_proof(self):
        for key, value in (("mode", "human"), ("noIndependentHumanSignoff", False),
                           ("automaticSemanticPass", True), ("rubricUnchanged", False),
                           ("originalMethodTimingCorroborated", 1),
                           ("timingAdmissionBeforeContentGrading", False)):
            with self.subTest(key=key):
                self.rejects(lambda d: d["review"].update({key: value}))
        for key in ("internalQueries", "backendConversations"):
            for value in ("OBSERVED", 0, None, "inferred-from-answer"):
                with self.subTest(key=key, value=value):
                    self.rejects(lambda d: d["observability"].update({key: value}))

    def test_corroboration_and_admission_require_explicit_noncertification_without_stronger_claims(self):
        for key in study100.REVIEW_FIELDS:
            with self.subTest(missing=key):
                self.rejects(lambda d: d["review"].pop(key))
        for key in ("methodTimingIndependentlyCertified", "methodPreregistered",
                    "fullReviewPolicyPreregistered", "reviewToolingPreregistered"):
            for value in (True, 0, None, "false"):
                with self.subTest(flag=key, value=value):
                    self.rejects(lambda d: d["review"].update({key: value}))
        for value in ("fully-preregistered", "before-questions", None, ""):
            with self.subTest(timing=value):
                self.rejects(lambda d: d["review"].update(reviewPolicyTiming=value))
        self.rejects(lambda d: d["review"].update(policyFrozenBeforeBaseline=True))
        self.rejects(lambda d: d["review"].update(methodPreregisteredBeforePlanAuthQuestions=True))
        self.rejects(lambda d: d["review"].update(methodTimingEvidence="independent-preregistration-proof"))
        self.rejects(lambda d: d["review"].update(methodPreregistrationClaim="independently-proven"))
        self.rejects(lambda d: d["review"].update(methodEvidenceHashProvenance="computedBeforeQuestions"))
        self.rejects(lambda d: d["review"].update(originalMethodTimingCorroborated=False))
        for key in ("methodIntentSha256", "timingAdmissionReceiptSha256"):
            with self.subTest(hash=key):
                self.rejects(lambda d: d["review"].update({key: "pending"}))
                self.rejects(lambda d: d["review"].update({key: d["review"]["policySha256"]}))
        self.rejects(lambda d: d["review"].update(timingAdmissionReceiptSha256=d["review"]["methodIntentSha256"]))

    def test_timing_disclosure_is_visible_in_both_live_and_synthetic_notices(self):
        for observed in (False, True):
            notice = study100.notice(synthetic_study(observed=observed))
            for lang in ("ja", "en"):
                with self.subTest(observed=observed, lang=lang):
                    self.assertIn("METHOD timing", notice[lang])
                    self.assertIn("methodPreregistered=false", notice[lang])
                    self.assertIn("fullReviewPolicyPreregistered=false", notice[lang])
                    self.assertIn("computedAtAdmission", notice[lang])
            self.assertIn("NOT independently proven", notice["en"])
            self.assertNotIn("Only METHOD intent was preregistered", notice["en"])
            if not observed:
                self.assertIn("SYNTHETIC PRIVATE TEST", notice["en"])

    def test_final_freeze_irreversible_heldout_and_no_pooling_are_required(self):
        for key, value in (
            ("stage", "development"), ("developmentRound", "best"),
            ("frozenBeforeHeldout", False), ("heldoutIrreversiblySpent", False),
            ("heldoutUsedForTuning", True), ("bestOfPooling", True), ("baselineAnswersBorrowed", True),
            ("selectionPolicy", "retry-until-pass"), ("frozenAtUtc", "2026-10-02T08:02:00Z"),
            ("heldoutReservedAtUtc", "2026-10-02T11:00:00Z"), ("frozenAtUtc", "2026-10-02T08:00:00"),
        ):
            with self.subTest(key=key):
                self.rejects(lambda d: d["final"].update({key: value}))
        self.rejects(lambda d: d.update(intervention=None))
        self.rejects(lambda d: d["intervention"].update(meaningfulChange=False))
        self.rejects(lambda d: d["intervention"].update(noSafetyBypass=False))
        self.rejects(lambda d: d["intervention"].update(baselineReportSha256=h("unrelated baseline")))
        self.rejects(lambda d: d["intervention"]["run"].update(candidate=copy.deepcopy(d["baseline"]["candidate"])))

    def test_combined_rejects_baseline_borrowing_and_mixed_final_candidates(self):
        self.rejects(lambda d: d["combined"].update(finalDevelopmentReportSha256=d["baseline"]["sourceReportSha256"]))
        self.rejects(lambda d: d["combined"].update(heldoutReportSha256=d["baseline"]["sourceReportSha256"]))
        self.rejects(lambda d: d["heldout"].update(candidate=copy.deepcopy(d["baseline"]["candidate"])))
        self.rejects(lambda d: d["combined"].update(metrics=add(d["baseline"]["metrics"], d["heldout"]["metrics"])))
        self.rejects(lambda d: d["final"].update(candidateSha256=h("mixed")))

    def test_final_candidate_may_be_baseline_but_not_a_per_case_best_of(self):
        value = synthetic_study(intervention=True, buckets=True)
        value["final"].update(developmentRound="baseline", candidateSha256=value["baseline"]["candidate"]["candidateSha256"])
        for key in ("heldout", "combined"):
            value[key]["candidate"] = copy.deepcopy(value["baseline"]["candidate"])
        value["combined"]["finalDevelopmentReportSha256"] = value["baseline"]["sourceReportSha256"]
        value["combined"]["metrics"] = add(value["baseline"]["metrics"], value["heldout"]["metrics"])
        for combined, baseline, heldout in zip(value["combined"]["buckets"], value["baseline"]["buckets"], value["heldout"]["buckets"]):
            combined["metrics"] = add(baseline["metrics"], heldout["metrics"])
        study100.validate(value)
        self.assertEqual(54, value["combined"]["metrics"]["axes"]["answerContent"]["pass"])

    def test_optional_buckets_partition_all_metrics_and_use_the_same_final_round(self):
        self.rejects(lambda d: d["heldout"].pop("buckets"))
        self.rejects(lambda d: d["baseline"].update(buckets=[]))
        self.rejects(lambda d: d["baseline"]["buckets"][1].update(label="synthetic-a"))
        self.rejects(lambda d: d["baseline"]["buckets"][0]["metrics"].update(terminalCases=39))
        self.rejects(lambda d: d["combined"]["buckets"][0].update(metrics=add(d["baseline"]["buckets"][0]["metrics"], d["heldout"]["buckets"][0]["metrics"])))
        self.rejects(lambda d: d["intervention"]["run"]["buckets"][0].update(label="unrelated-bucket"))

    def test_unknown_private_fields_are_rejected_at_every_object_boundary(self):
        for target in (
            lambda d: d, lambda d: d["bindings"], lambda d: d["review"], lambda d: d["final"],
            lambda d: d["baseline"], lambda d: d["baseline"]["candidate"],
            lambda d: d["baseline"]["metrics"], lambda d: d["baseline"]["metrics"]["terminalCounts"],
            lambda d: d["baseline"]["metrics"]["axes"], lambda d: d["baseline"]["metrics"]["axes"]["answerContent"],
            lambda d: d["heldout"]["buckets"][0], lambda d: d["intervention"], lambda d: d["observability"],
        ):
            for key in ("prompt", "answers", "oracle", "reasoning", "workspaceId", "localPath"):
                with self.subTest(target=target, field=key):
                    self.rejects(lambda d: target(d).update({key: "PRIVATE_SENTINEL_DO_NOT_PUBLISH"}))

    def test_labels_reject_guids_endpoints_upns_paths_and_free_text(self):
        for value in (
            "12345678-1234-1234-1234-123456789abc", "abcdefabcdefabcdefabcdefabcdefab",
            "profile-abcdefab-1234-1234-1234-123456789abc", "https://example.invalid/query",
            "user@example.invalid", "tenant.example.invalid", r"C:\private\report.json",
            r"\\server\private", "/tmp/secret", "a sentence with an answer", "<script>", "x" * 65,
        ):
            with self.subTest(value=value):
                self.rejects(lambda d: d["baseline"]["candidate"].update(profileLabel=value))
                self.rejects(lambda d: d["baseline"]["buckets"][0].update(label=value))
                self.rejects(lambda d: d["bindings"]["sourceFileHashes"].update({value: h("source")}))

    def test_exact_file_digest_duplicate_keys_raw_reports_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SYNTHETIC-PRIVATE-study.json"
            value = synthetic_study()
            raw = json.dumps(value, indent=2)
            path.write_bytes(raw.encode("utf-8"))
            loaded = study100.load(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), loaded["evaluation100Sha256"])
            path.write_bytes((raw + "\n").encode("utf-8"))
            self.assertNotEqual(loaded["evaluation100Sha256"], study100.load(path)["evaluation100Sha256"])
            self.assertEqual(loaded["evaluation100"], study100.load(path)["evaluation100"])
            for bad in (
                raw.replace('"mode": "ai-assisted"', '"mode": "human", "mode": "ai-assisted"'),
                raw.replace('"submissionIntents": 78', '"submissionIntents": NaN', 1),
                json.dumps({"schemaVersion": "furusato100-report/v1", "cases": []}),
                " " * (study100.MAX_BYTES + 1),
            ):
                if bad == raw:
                    bad = raw.replace('"uniqueCases": 80', '"uniqueCases": NaN', 1)
                path.write_text(bad, encoding="utf-8")
                with self.subTest(kind=bad[:35]), self.assertRaises(ValueError):
                    study100.load(path)

    def test_metadata_requires_both_study_and_hash_and_synthetic_is_visibly_labelled(self):
        value = synthetic_study()
        self.assertIn("SYNTHETIC PRIVATE TEST", study100.notice(value)["ja"])
        self.assertIn("never publish", study100.notice(value)["en"])
        for metadata in ({"evaluation100": value}, {"evaluation100Sha256": h("alone")}):
            with self.assertRaises(ValueError):
                study100.require_metadata(metadata)
        self.assertIsNone(study100.require_metadata({}))
        self.assertEqual({}, study100.load(None))


class ExecutionProtocolTests(unittest.TestCase):
    def fixture(self, **kwargs):
        value = synthetic_study(intervention=True, buckets=True)
        amend_execution_fixture(value, **kwargs)
        return value

    def rejects(self, mutate):
        value = self.fixture()
        mutate(value)
        with self.assertRaises(ValueError):
            study100.validate(value)

    def test_completed_continuation_is19_captures_and_unknown_not20_successes(self):
        value = self.fixture()
        checked = study100.validate(value)
        heldout = checked["heldout"]["metrics"]
        self.assertEqual((20, 19, 1), tuple(heldout[key] for key in ("submissionIntents", "capturedResponses", "unknownOutcomes")))
        self.assertEqual(1, heldout["terminalCounts"]["submissionUncertain"])
        self.assertEqual(0, heldout["axes"]["answerContent"]["pass"])
        self.assertEqual(20, heldout["axes"]["answerContent"]["unknown"])
        self.assertIs(False, checked["executionProtocol"]["originalProtocolWasFullyFollowed"])
        self.assertIs(False, checked["executionProtocol"]["executionAmendmentPreregistered"])
        self.assertEqual(value, checked)
        self.assertIn("HTTP500 stays UNKNOWN", study100.notice(value)["en"])

    def test_preflight_and_partial_fail_closed_outcomes_retain_unsent_and_unknown_slots(self):
        for captured, failure in ((0, None), (0, "submissionUncertain"), (4, "nativeServiceBlocked"),
                                  (6, "nativeErrorReply"), (10, "captureFailed"), (16, "submissionUncertain"),
                                  (17, None)):
            with self.subTest(captured=captured, failure=failure):
                value = self.fixture(captured=captured, failure=failure, outcome="stopped-fail-closed")
                study100.validate(value)
                terminal = value["heldout"]["metrics"]["terminalCounts"]
                self.assertEqual(20, sum(terminal.values()))
                self.assertEqual(captured + 2, terminal["answerCaptured"])
                self.assertGreaterEqual(terminal["submissionUncertain"], 1)
                self.assertEqual(17 - captured - bool(failure), terminal["notSubmitted"])
                self.assertEqual(100, value["combined"]["metrics"]["uniqueCases"])

    def test_protocol_deviation_and_no_replay_flags_are_mandatory_typed_facts(self):
        for key in study100.EXECUTION_FIELDS:
            with self.subTest(missing=key):
                self.rejects(lambda d: d["executionProtocol"].pop(key))
        for key in study100.EXECUTION_TRUE_FIELDS:
            for bad in (False, 1, None):
                with self.subTest(flag=key, value=bad):
                    self.rejects(lambda d: d["executionProtocol"].update({key: bad}))
        for key in study100.EXECUTION_FALSE_FIELDS:
            for bad in (True, 0, None):
                with self.subTest(flag=key, value=bad):
                    self.rejects(lambda d: d["executionProtocol"].update({key: bad}))

    def test_exact_plan_report_candidate_and_definition_bindings_cannot_change(self):
        for key in ("originalPlanSha256", "continuationPlanSha256", "reportSha256"):
            with self.subTest(binding=key):
                self.rejects(lambda d: d["executionProtocol"].update({key: h("wrong binding")}))
        for key in study100.EXECUTION_HASH_FIELDS:
            with self.subTest(hash=key):
                self.rejects(lambda d: d["executionProtocol"].update({key: "pending"}))
        self.rejects(lambda d: d["executionProtocol"].update(reconciliationSha256=d["executionProtocol"]["originalStoppedBatchSha256"]))
        for key in ("candidateSha256", "definitionSha256"):
            value = self.fixture()
            for run in (value["intervention"]["run"], value["heldout"], value["combined"]):
                run["candidate"][key] = h("another frozen candidate")
            value["final"]["candidateSha256"] = value["heldout"]["candidate"]["candidateSha256"]
            with self.subTest(candidate_field=key), self.assertRaisesRegex(ValueError, "actual frozen final candidate"):
                study100.validate(value)

    def test_no_second_invocation_pending_status_or_relabelled_http_failure(self):
        for key, bad in (("priorCaptured", 3), ("priorUnknown", 0), ("eligibleUnsent", 18),
                         ("priorUnknownHttpStatus", 403), ("continuationInvocations", 0),
                         ("continuationInvocations", 2), ("continuationInvocations", True),
                         ("outcome", "running"), ("outcome", "stopped-without-reconciliation"),
                         ("label", "resume-retry")):
            with self.subTest(field=key, value=bad):
                self.rejects(lambda d: d["executionProtocol"].update({key: bad}))

    def test_original_unknown_cannot_be_replayed_dropped_or_replaced_with_capture(self):
        value = self.fixture()
        value["heldout"]["metrics"] = metrics(20, 20)
        value["combined"]["metrics"] = add(value["intervention"]["run"]["metrics"], value["heldout"]["metrics"])
        for run in (value["baseline"], value["intervention"]["run"], value["heldout"], value["combined"]):
            run.pop("buckets")
        with self.assertRaisesRegex(ValueError, "unreplayed HTTP500"):
            study100.validate(value)

    def test_continuation_must_account_for17_and_stop_after_one_new_failure(self):
        self.rejects(lambda d: d["executionProtocol"]["continuationTerminalCounts"].update(answerCaptured=16))
        value = self.fixture(captured=3, failure="submissionUncertain", outcome="stopped-fail-closed")
        value["executionProtocol"]["outcome"] = "completed"
        with self.assertRaisesRegex(ValueError, "completed continuation"):
            study100.validate(value)
        value = self.fixture(captured=15, failure="submissionUncertain", outcome="stopped-fail-closed")
        value["executionProtocol"]["continuationTerminalCounts"].update(submissionUncertain=2, notSubmitted=0)
        with self.assertRaisesRegex(ValueError, "first new failed"):
            study100.validate(value)
        self.rejects(lambda d: d["executionProtocol"]["continuationTerminalCounts"].update(answerCaptured=16, protectedNotResubmitted=1))

    def test_private_error_details_identifiers_or_case_content_are_rejected(self):
        for key in ("requestId", "workspaceId", "endpoint", "caseIds", "questions", "answers", "oracle", "ledgerPath"):
            with self.subTest(field=key):
                self.rejects(lambda d: d["executionProtocol"].update({key: "PRIVATE_SENTINEL"}))
        self.rejects(lambda d: d["executionProtocol"]["continuationTerminalCounts"].update(requestId="PRIVATE_SENTINEL"))

    def test_base_contract_optional_amendment_is_not_a_snapshot_omission_permission(self):
        value = synthetic_study(intervention=True)
        study100.validate(value)
        self.assertEqual({}, study100.execution_binding(value))
        with self.assertRaisesRegex(ValueError, "requires explicit post-stop"):
            study100.execution_binding(value, required=True)
        value["executionProtocol"] = None
        with self.assertRaises(ValueError):
            study100.validate(value)


class SnapshotIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="frozen100-synthetic-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.source, self.private = self.work / "source", self.work / "private"
        self.source.mkdir()
        self.private.mkdir()
        self.projection = self.source / release.V300.evidence_relative
        self.projection.parent.mkdir(parents=True)
        self.projection.write_text(json.dumps(snapshot(), ensure_ascii=False), encoding="utf-8")
        self.study = synthetic_study(intervention=True, buckets=True, observed=True, execution_amendment=True)
        self.study_path = self.private / "SYNTHETIC-PRIVATE-study.json"
        self.write_study()
        self.approval_path = self.private / "SYNTHETIC-PRIVATE-approval.json"
        self.approval = {
            "schemaVersion": release.SNAPSHOT_APPROVAL_SCHEMA, "approved": True, "userAuthorized": True,
            "version": "3.0.0", "selectedOriginalSuiteRunId": release.RELEASE_RUN_ID,
            "evidenceProjectionSha256": packager.sha(self.projection.read_bytes()),
            "knownLimitationsAcknowledged": True, "originalCounts": dict(release.RELEASE_COUNTS),
            "snapshotDate": "2026-10-02", "evaluation100Sha256": packager.sha(self.study_path.read_bytes()),
            "approvedAtUtc": "2026-10-02T10:01:00Z", "knownLimitations": list(release.SNAPSHOT_LIMITATIONS),
            **study100.execution_binding(self.study, required=True),
        }
        self.write_approval()

    def write_study(self):
        self.study_path.write_text(json.dumps(self.study, indent=2) + "\n", encoding="utf-8")

    def write_approval(self):
        self.approval_path.write_text(json.dumps(self.approval, indent=2) + "\n", encoding="utf-8")

    def resolve(self):
        return release.resolve_evidence(
            self.source, release_profile=release.VALIDATION_20261002, release_approval=self.approval_path,
            evaluation100_path=self.study_path,
        )

    def metadata(self):
        evidence, binding = self.resolve()
        return {
            "version": "3.0.0", "contentSha256": h("shared content"),
            "counts": {"chapters": 24, "appendices": 5, "headings": 0, "tables": 0, "figures": 0, "tests": 10, "conditions": 84},
            "evidenceComplete": evidence["complete"], "evidenceScope": "historical-observed-run",
            "labStates": {key: row["status"] for key, row in evidence["labs"].items()},
            "knownIssueLabs": [], "releaseFreezeStatus": evidence["freezeStatus"],
            "allFeaturesPassedClaimed": False, "finalUserAcceptanceCertified": False,
            "publicEvidenceProjectionSha256": evidence["projectionSha256"],
            "originalSuiteRuns": evidence["originalSuiteRuns"], **reporting.selection_metadata(evidence),
            "documentRelease": binding, "evaluation100": self.study,
            "evaluation100Sha256": packager.sha(self.study_path.read_bytes()),
        }

    def model_stub(self, root, evidence_path, evaluation_path, **kwargs):
        evidence, _ = release.resolve_evidence(root, evidence_path, evaluation_path, **kwargs)
        return Document([], [], [], []), None, None, None, evidence, self.metadata()

    def flags(self):
        return ["--release-profile", "validation-20261002", "--release-approval", str(self.approval_path),
                "--evaluation100", str(self.study_path)]

    def package_inputs(self):
        profile = release.VALIDATION_20261002
        pair = self.private / "SYNTHETIC-pair"
        pair.mkdir()
        (pair / profile.word_name).write_bytes(WORD_FIXTURE)
        (pair / profile.html_name).write_text(HTML_FIXTURE, encoding="utf-8")
        receipt = {
            "syntheticFixtureOnly": True, "passedLocalChecks": True,
            "findings": [{"check": key, "level": "PASS"} for key in sorted(packager.REQUIRED_FULL_CHECKS)],
            "files": {file.name: packager.sha(file.read_bytes()) for file in pair.iterdir()},
            "documentIdentity": release.document_identity(self.metadata(), profile),
        }
        receipt_path = self.private / "SYNTHETIC-validation.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        attachments = self.source / "workshop" / "v3.0.0-preview" / "attachments"
        attachments.mkdir(parents=True)
        manifest = {"files": {}}
        for name in packager.ATTACHMENTS:
            if name != "manifest.json":
                blob = ("SYNTHETIC PRIVATE TEST attachment: " + name).encode("utf-8")
                (attachments / name).write_bytes(blob)
                manifest["files"][name] = {"sha256": packager.sha(blob)}
        (attachments / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        reports = self.source / profile.reports_relative
        reports.mkdir(parents=True)
        files = report_payloads(self.projection, root=self.source)
        files["SHA256SUMS.txt"] = "".join(f"{packager.sha(blob)}  {name}\n" for name, blob in sorted(files.items())).encode("utf-8")
        for name, blob in files.items():
            (reports / name).write_bytes(blob)
        return pair, receipt_path

    def test_snapshot_profile_keeps_course_version_but_has_a_distinct_destination_and_identity(self):
        profile = release.VALIDATION_20261002
        self.assertEqual("3.0.0", profile.version)
        self.assertEqual(release.V300.word_name, profile.word_name)
        self.assertEqual(release.V300.html_name, profile.html_name)
        self.assertNotEqual(release.V300.package_name, profile.package_name)
        self.assertEqual("docs/v3.0.0/validation-20261002/guide", profile.guide_relative.as_posix())
        self.assertEqual("docs/v3.0.0/reports", profile.reports_relative.as_posix())
        self.assertIn("validation snapshot 2026-10-02", profile.title)
        metadata = self.metadata()
        identity = release.document_identity(metadata, profile)
        self.assertEqual(metadata["evaluation100Sha256"], identity["evaluation100Sha256"])
        self.assertEqual(self.study["bindingSha256"], identity["evaluation100BindingSha256"])
        self.assertEqual(self.study["review"], identity["evaluation100Review"])
        self.assertEqual(study100.REVIEW_POLICY_TIMING, metadata["documentRelease"]["reviewPolicyTiming"])
        for key in ("methodTimingIndependentlyCertified", "methodPreregistered",
                    "fullReviewPolicyPreregistered", "reviewToolingPreregistered"):
            self.assertIs(False, metadata["documentRelease"][key])
        self.assertEqual("operator-receipt-and-filesystem-corroboration", metadata["documentRelease"]["methodTimingEvidence"])
        self.assertEqual("corroborated-not-independently-proven", metadata["documentRelease"]["methodPreregistrationClaim"])
        self.assertEqual("computedAtAdmission", metadata["documentRelease"]["methodEvidenceHashProvenance"])
        self.assertEqual(self.study["review"]["methodIntentSha256"], metadata["documentRelease"]["methodIntentSha256"])
        self.assertEqual(self.study["review"]["timingAdmissionReceiptSha256"], metadata["documentRelease"]["timingAdmissionReceiptSha256"])
        execution_binding = study100.execution_binding(self.study)
        self.assertEqual(execution_binding["executionProtocolSha256"], identity["evaluation100ExecutionProtocolSha256"])
        self.assertEqual(execution_binding["executionProtocolHashes"], identity["evaluation100ExecutionProtocolHashes"])
        self.assertEqual(self.study["executionProtocol"], metadata["documentRelease"]["executionProtocol"])
        for key in ("originalSuiteAccepted", "aiAnswerQualityAccepted", "mainPromoted", "allFeaturesPassedClaimed",
                    "generalAvailabilityClaimed", "finalUserAcceptanceCertified", "originalReleaseAssetsReplaced"):
            self.assertIs(False, metadata["documentRelease"][key])
        self.assertNotIn(str(self.private), json.dumps(identity))
        self.assertIn("no independent human sign-off", release.presentation(metadata, profile)["en"])

    def test_snapshot_requires_fresh_study_sha_known_limitations_and_unchanged_original_projection(self):
        original = copy.deepcopy(self.approval)
        for change in (
            lambda a: a.update(schemaVersion=release.APPROVAL_SCHEMA),
            lambda a: a.update(snapshotDate="2026-10-01"),
            lambda a: a.update(evaluation100Sha256=h("stale study")),
            lambda a: a.update(approvedAtUtc="2026-10-02T09:59:59Z"),
            lambda a: a.update(approvedAtUtc="2026-10-02T10:01:00"),
            lambda a: a.update(knownLimitations=[]),
            lambda a: a["knownLimitations"].remove("post-stop-unsent-slots-only-execution-amendment-not-preregistered"),
            lambda a: a.update(executionProtocolSha256=h("another execution")),
            lambda a: a["executionProtocolHashes"].update(continuationPlanSha256=h("unapproved plan")),
            lambda a: a["executionProtocolHashes"].update(originalStoppedBatchSha256=h("rewritten batch")),
            lambda a: a["executionProtocolHashes"].update(reconciliationSha256=h("stale reconciliation")),
            lambda a: a["executionProtocolHashes"].update(reportSha256=h("undisclosed report")),
            lambda a: a.pop("executionProtocolHashes"),
            lambda a: a["knownLimitations"].remove("method-timing-corroborated-not-independently-proven"),
            lambda a: a["knownLimitations"].__setitem__(1, "method-preregistered-review-tooling-finalized-during-capture"),
            lambda a: a.update(evidenceProjectionSha256=h("new projection")),
            lambda a: a.update(knownLimitationsAcknowledged=False),
            lambda a: a.update(approved=1),
            lambda a: a["originalCounts"].update({"pass": 84, "fail": 0}),
            lambda a: a.update(privateReviewer="PRIVATE_SENTINEL"),
        ):
            self.approval = copy.deepcopy(original)
            change(self.approval)
            self.write_approval()
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve()
        self.approval = original
        self.write_approval()
        self.study_path.write_bytes(self.study_path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "exact dated study"):
            self.resolve()

    def test_original_release_approval_cannot_be_repurposed_and_synthetic_cannot_be_a_snapshot(self):
        with self.assertRaisesRegex(ValueError, "cannot alter"):
            release.resolve_evidence(self.source, release_profile=release.V300, release_approval=self.approval_path,
                                     evaluation100_path=self.study_path)
        with self.assertRaisesRegex(ValueError, "requires --evaluation100"):
            release.resolve_evidence(self.source, release_profile=release.VALIDATION_20261002, release_approval=self.approval_path)
        for kind, day in (("synthetic-private-test", "2026-10-02"), ("observed-live", "2026-10-01")):
            self.study.update(evidenceKind=kind, snapshotDate=day)
            self.write_study()
            self.approval["evaluation100Sha256"] = packager.sha(self.study_path.read_bytes())
            self.write_approval()
            with self.subTest(kind=kind, day=day), self.assertRaisesRegex(ValueError, "exact snapshot date"):
                self.resolve()

    def test_current_snapshot_requires_execution_disclosure_without_weakening_base_contract(self):
        self.study.pop("executionProtocol")
        self.write_study()
        study100.validate(self.study)
        self.approval["evaluation100Sha256"] = packager.sha(self.study_path.read_bytes())
        self.write_approval()
        with self.assertRaisesRegex(ValueError, "requires explicit post-stop"):
            self.resolve()

    def test_failed_continuation_needs_fresh_exact_amendment_approval_and_remains_failed(self):
        stopped_batch = self.study["executionProtocol"]["originalStoppedBatchSha256"]
        amend_execution_fixture(self.study, captured=4, failure="submissionUncertain", outcome="stopped-fail-closed")
        self.study["heldout"]["sourceReportSha256"] = h("disclosed partial heldout report")
        self.study["combined"]["sourceReportSha256"] = h("disclosed partial combined report")
        self.study["combined"]["heldoutReportSha256"] = self.study["heldout"]["sourceReportSha256"]
        self.study["executionProtocol"].update(
            reconciliationSha256=h("partial terminal reconciliation"),
            reportSha256=self.study["combined"]["sourceReportSha256"],
        )
        self.write_study()
        self.approval["evaluation100Sha256"] = packager.sha(self.study_path.read_bytes())
        self.write_approval()
        with self.assertRaisesRegex(ValueError, "execution amendment hashes"):
            self.resolve()
        self.approval.update(study100.execution_binding(self.study, required=True))
        self.write_approval()
        evidence, binding = self.resolve()
        self.assertEqual("stopped-fail-closed", binding["executionProtocol"]["outcome"])
        self.assertEqual(stopped_batch, binding["executionProtocol"]["originalStoppedBatchSha256"])
        terminal = evidence["evaluation100"]["heldout"]["metrics"]["terminalCounts"]
        self.assertEqual((6, 2, 12), tuple(terminal[key] for key in ("answerCaptured", "submissionUncertain", "notSubmitted")))
        self.assertFalse(binding["originalSuiteAccepted"])
        self.assertFalse(binding["executionProtocol"]["originalProtocolWasFullyFollowed"])

    def test_amendment_does_not_change_review_rubric_or_original_acceptance_guards(self):
        for mutate in (
            lambda d: d["review"].update(rubricUnchanged=False),
            lambda d: d["review"].update(noIndependentHumanSignoff=False),
            lambda d: d["review"].update(methodTimingIndependentlyCertified=True),
            lambda d: d["observability"].update(internalQueries="PROVEN"),
        ):
            original = copy.deepcopy(self.study)
            mutate(self.study)
            self.write_study()
            self.approval["evaluation100Sha256"] = packager.sha(self.study_path.read_bytes())
            self.write_approval()
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.resolve()
            self.study = original

    def test_bad_study_or_approval_blocks_all_entrypoints_before_model_and_output(self):
        pair, review, output = (self.private / name for name in ("pair", "review", "package"))
        self.approval["evaluation100Sha256"] = h("stale")
        self.write_approval()
        operations = (
            (builder, lambda: builder.main(["--out", str(pair), "--review", str(review), *self.flags()])),
            (validator, lambda: validator.main(["--pair", str(pair), "--review", str(review), *self.flags()])),
            (packager, lambda: packager.package(
                pair, self.private / "validation.json", output, None, release_profile="validation-20261002",
                release_approval=self.approval_path, evaluation100_path=self.study_path)),
        )
        for module, operation in operations:
            with self.subTest(module=module.__name__), patch.object(module, "ROOT", self.source):
                with patch.object(content, "load_context") as load, self.assertRaises(ValueError):
                    operation()
                load.assert_not_called()
            self.assertFalse(any(path.exists() for path in (pair, review, output)))

    def test_snapshot_never_bypasses_strict_require_acceptance(self):
        self.resolve()
        strict = {
            "schemaVersion": acceptance.APPROVAL_SCHEMA, "selectedOriginalSuiteRunId": release.RELEASE_RUN_ID,
            "evidenceSha256": self.approval["evidenceProjectionSha256"], "finalPublicationApproved": True,
            "reviewer": "synthetic-review", "reviewedAt": "2026-10-02T10:02:00Z",
        }
        path = self.private / "SYNTHETIC-strict.json"
        path.write_text(json.dumps(strict), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "original-zero-fail"):
            acceptance.require_public_acceptance(self.projection, path, root=self.source)
        with patch.object(builder, "ROOT", self.source), patch.object(builder, "build") as model:
            with self.assertRaisesRegex(ValueError, "Final publication acceptance blocked"):
                builder.main(["--out", str(self.private / "pair"), "--review", str(self.private / "review"),
                              *self.flags(), "--require-acceptance", "--acceptance-approval", str(path)])
            model.assert_not_called()
        with patch.object(packager, "ROOT", self.source), patch.object(packager, "build") as model:
            with self.assertRaisesRegex(ValueError, "Final publication acceptance blocked"):
                packager.package(self.private / "pair", self.private / "validation.json", self.private / "package", None,
                                 release_profile="validation-20261002", release_approval=self.approval_path,
                                 evaluation100_path=self.study_path, require_acceptance=True, acceptance_approval=path)
            model.assert_not_called()

    def test_shared_model_adds_two_subsections_and_keeps_original_ten84_and_histories(self):
        context = content.load_context(ROOT, document_edition="unified-20260923", source_version="2.7.0")
        carrier = content.StyleCarrier.resolve(ROOT)
        runtime_sections = content.runtime_candidate_sections
        before_bytes = self.projection.read_bytes()
        old_approval = {key: value for key, value in self.approval.items() if key in release.APPROVAL_FIELDS}
        old_approval["schemaVersion"] = release.APPROVAL_SCHEMA
        old_path = self.private / "SYNTHETIC-old-approval.json"
        old_path.write_text(json.dumps(old_approval), encoding="utf-8")
        with patch.object(content, "load_context", return_value=context), patch.object(content.StyleCarrier, "resolve", return_value=carrier):
            with patch.object(content, "runtime_candidate_sections", side_effect=lambda sections, root: runtime_sections(sections, ROOT)):
                old = content.build(self.source, release_profile=release.V300, release_approval=old_path)
                new = content.build(self.source, release_profile=release.VALIDATION_20261002,
                                    release_approval=self.approval_path, evaluation100_path=self.study_path)
        self.assertEqual(before_bytes, self.projection.read_bytes())
        self.assertEqual((24, 5, 10, 84), tuple(new[-1]["counts"][key] for key in ("chapters", "appendices", "tests", "conditions")))
        self.assertEqual(old[-1]["originalSuiteRuns"], new[-1]["originalSuiteRuns"])
        self.assertEqual(old[-1]["finalEvaluation"], new[-1]["finalEvaluation"])
        self.assertEqual(old[-1]["currentUICaptures"], new[-1]["currentUICaptures"])
        new_sections = {section.ident: section for section in new[0].walk()}
        self.assertEqual({"ch-19-11", "ch-24-11"}, set(new_sections) - {section.ident for section in old[0].walk()})
        for section in old[0].walk():
            prior, current = section.blocks, new_sections[section.ident].blocks
            if section.ident == "ch-1":
                prior, current = prior[1:], current[2:]
            self.assertEqual([signature(block) for block in prior], [signature(block) for block in current], section.ident)
        text = json.dumps(asdict(new_sections["ch-19-11"]), ensure_ascii=False)
        for token in ("AI-assisted", "no independent human sign-off", "UNKNOWN", "UNOBSERVABLE",
                      "GQL/DAX/SQL/KQL", "unchanged frozen rubric", "best-of pooling", "14/0", "13/0",
                      "REVIEW TIMING LIMITATION", "NOT independently proven preregistration",
                      "every frozen criterion", "heuristic substitution", "no original method-intent hash or eventId",
                      "08:24:25", "08:24:55", "08:25:23", "mtime", "frozenAt", "computedAtAdmission",
                      "methodTimingIndependentlyCertified=false", "methodPreregistered=false",
                      "reviewToolingPreregistered=false", "compatibility label, not a preregistration certification",
                      "fullReviewPolicyPreregistered=false", "original capture plan, candidate or spent claims",
                      "POST-STOP EXECUTION-PROTOCOL AMENDMENT", "originalProtocolWasFullyFollowed=false",
                      "NOT a preregistered resume mechanism", "HTTP500 UNKNOWN", "never replay",
                      "Only the17 never-submitted slots", "at most one continuation invocation",
                      "Journal absence alone is not independent proof", "20/100 denominators",
                      "stopped_fail_closed"):
            self.assertIn(token, text)
        self.assertNotIn("METHOD intent was registered before", text)
        self.assertEqual("callout", new_sections["ch-19-11"].blocks[1].kind)
        self.assertEqual("stop", new_sections["ch-19-11"].blocks[1]["tone"])
        deployment = json.dumps(asdict(new_sections["ch-24-11"]), ensure_ascii=False)
        for token in ("Three Copies each Completed exactly once", "5,000", "manual 3 / automatic 0",
                      "15,000", "253,886,000 JPY", "14,900 accepted EventIDs", "252,058,000 JPY",
                      "100 duplicates", "Original safe Pipeline defaults were restored", "native Published UI",
                      "all 10 entities", "Both were preserved unchanged pending evaluation",
                      "not a docbuilder rerun or 100-case AI grades"):
            self.assertIn(token, deployment)
        for key in ("methodIntentSha256", "timingAdmissionReceiptSha256"):
            self.assertIn(self.study["review"][key], deployment)
        for key in study100.EXECUTION_HASH_FIELDS:
            self.assertIn(self.study["executionProtocol"][key], deployment)

    def test_html_and_word_cover_bind_snapshot_title_and_study_metadata(self):
        metadata, profile = self.metadata(), release.VALIDATION_20261002
        with patch.object(html_renderer, "build_library", return_value=SimpleNamespace(screenshots={}, screenshot_sizes={})):
            with patch.object(html_renderer, "load_ui_strings", return_value={}):
                html = html_renderer.render(Document([], [], [], []), None, None, None, {"captures": {}},
                                            metadata, packager.sha(WORD_FIXTURE), ROOT, release_profile=profile)
        self.assertIn("<title>" + profile.title + "</title>", html)
        self.assertIn("UNOBSERVABLE", html)
        self.assertIn(metadata["evaluation100Sha256"], html)
        self.assertIn("fullReviewPolicyPreregistered=false", html)
        self.assertIn("methodPreregistered=false", html)
        self.assertIn("computedAtAdmission", html)
        self.assertIn("NOT independently proven", html)
        self.assertIn("POST-STOP EXECUTION AMENDMENT", html)
        self.assertIn("originalProtocolWasFullyFollowed=false", html)
        fake = MagicMock()
        fake.document.styles, fake.document.paragraphs, fake.figures, fake.tables = [], [], [], []
        with patch.object(builder, "DocumentBuilder", return_value=fake), patch.object(builder, "cover_page") as cover:
            with patch.object(builder, "apply_package_metadata") as core:
                builder.write_word(Document([], [], [], []), None, MagicMock(), {}, metadata,
                                   self.private / "absent.docx", self.private, release_profile=profile)
        self.assertEqual(profile.title, cover.call_args.kwargs["title"])
        self.assertIn("2026-10-02", core.call_args.kwargs["subject"])
        self.assertIn("fullReviewPolicyPreregistered=false", core.call_args.kwargs["subject"])
        self.assertIn("methodPreregistered=false", core.call_args.kwargs["subject"])
        self.assertIn("computedAtAdmission", core.call_args.kwargs["subject"])
        variants = (
            ("untampered", html),
            ("binding", html.replace('"bindingSha256": "' + self.study["bindingSha256"] + '"',
                                     '"bindingSha256": "' + h("tampered metadata") + '"')),
            ("false-certification", html.replace('"methodTimingIndependentlyCertified": false',
                                                  '"methodTimingIndependentlyCertified": true')),
            ("false-preregistration", html.replace('"methodPreregistered": false', '"methodPreregistered": true')),
            ("false-execution-preregistration", html.replace('"executionAmendmentPreregistered": false',
                                                             '"executionAmendmentPreregistered": true')),
            ("false-original-compliance", html.replace('"originalProtocolWasFullyFollowed": false',
                                                        '"originalProtocolWasFullyFollowed": true')),
        )
        for name, source in variants:
            report = Report(target="synthetic study metadata fixture")
            with patch.object(Path, "read_text", return_value=source), patch.object(Path, "read_bytes", return_value=WORD_FIXTURE):
                with patch.object(Path, "is_file", return_value=True):
                    validator.inspect_html(self.private, Document([], [], [], []), metadata, report, release_profile=profile)
            self.assertEqual(name == "untampered", report.passed, name)
            if name != "untampered":
                self.assertIn("html.selectedProjection", [row.check for row in report.failures], name)

    def test_snapshot_frontmatter_compacts_styles_without_losing_text_or_changing_other_editions(self):
        for profile in (release.PREVIEW, release.V300, release.VALIDATION_20261002):
            styles = [
                SimpleNamespace(style_id=name, font=SimpleNamespace(size=builder.Pt(size)),
                                paragraph_format=SimpleNamespace(space_before=None, space_after=None, line_spacing=None))
                for name, size in (("Title", 30), ("TOC1", 12), ("TOC2", 12), ("Normal", 10.5))
            ]
            fake = MagicMock()
            fake.document.styles, fake.document.paragraphs, fake.figures, fake.tables = styles, [], [], []
            # Isolate the style policy; the real metadata/profile gates have their own tests.
            with patch.object(release, "require_metadata_profile", return_value=profile):
                with patch.object(release, "presentation", return_value={"ja": "Full disclosure retained", "en": "Full disclosure retained"}):
                    with patch.object(builder, "DocumentBuilder", return_value=fake), patch.object(builder, "cover_page") as cover:
                        with patch.object(builder, "apply_package_metadata"):
                            builder.write_word(
                                Document([], [], [], []), None, MagicMock(), {}, {"contentSha256": h("layout fixture")},
                                self.private / "unused.docx", self.private, release_profile=profile,
                            )
            with self.subTest(profile=profile.name):
                self.assertEqual(builder.Pt(25 if profile.is_snapshot else 30), styles[0].font.size)
                for style in styles[1:3]:
                    self.assertEqual(builder.Pt(11), style.font.size)
                    self.assertEqual(builder.Pt(0), style.paragraph_format.space_before)
                    self.assertEqual(builder.Pt(0 if profile.is_snapshot else 1), style.paragraph_format.space_after)
                    self.assertEqual(1.0, style.paragraph_format.line_spacing)
                self.assertEqual(builder.Pt(10.5), styles[3].font.size)
                self.assertIsNone(styles[3].paragraph_format.space_after)
                self.assertEqual(profile.title, cover.call_args.kwargs["title"])
                self.assertEqual("Full disclosure retained", cover.call_args.kwargs["tagline"])
                self.assertEqual(4, len(cover.call_args.kwargs["footer_lines"]))

    def test_build_and_validation_cli_forward_the_same_study_and_profile(self):
        pair, review, checks = (self.private / name for name in ("pair", "build", "checks"))
        def fake_word(document, context, carrier, evidence, metadata, target, review, **kwargs):
            target.write_bytes(WORD_FIXTURE)
            return {"syntheticFixtureOnly": True}
        with ExitStack() as stack:
            stack.enter_context(patch.object(builder, "ROOT", self.source))
            model = stack.enter_context(patch.object(builder, "build", side_effect=self.model_stub))
            stack.enter_context(patch.object(builder, "write_word", side_effect=fake_word))
            stack.enter_context(patch.object(builder, "render_html", return_value=HTML_FIXTURE))
            stack.enter_context(patch.object(builder, "refresh_with_word", return_value=SyntheticRefresh()))
            for name, result in (("tidy_contents_tail", 0), ("apply_japanese_typography", {}), ("normalise_package_metadata", {})):
                stack.enter_context(patch.object(builder, name, return_value=result))
            stack.enter_context(redirect_stdout(io.StringIO()))
            self.assertEqual(0, builder.main(["--out", str(pair), "--review", str(review), *self.flags()]))
            self.assertEqual(self.study_path, model.call_args.kwargs["evaluation100_path"])
        with ExitStack() as stack:
            stack.enter_context(patch.object(validator, "ROOT", self.source))
            model = stack.enter_context(patch.object(validator, "build", side_effect=self.model_stub))
            for name in ("inspect_word", "inspect_html", "check_capture_fidelity"):
                stack.enter_context(patch.object(validator, name))
            stack.enter_context(redirect_stdout(io.StringIO()))
            self.assertEqual(0, validator.main(["--pair", str(pair), "--review", str(checks), *self.flags()]))
            self.assertEqual(self.study_path, model.call_args.kwargs["evaluation100_path"])
        build_report = json.loads((review / "build.json").read_text(encoding="utf-8"))
        receipt = json.loads((checks / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(build_report["documentIdentity"], receipt["documentIdentity"])
        self.assertEqual("more-local-validation-required", receipt["status"])
        with self.assertRaisesRegex(ValueError, "Full Word"):
            packager.require_full_validation(receipt)

    def test_receipt_must_bind_study_and_source_not_merely_document_version(self):
        metadata, profile = self.metadata(), release.VALIDATION_20261002
        for key in ("evaluation100Sha256", "evaluation100BindingSha256", "evaluation100FinalCandidateSha256"):
            receipt = {"documentIdentity": release.document_identity(metadata, profile)}
            receipt["documentIdentity"][key] = h("different study")
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "package inputs disagree"):
                release.require_validation_identity(receipt, metadata, profile)
        receipt = {"documentIdentity": release.document_identity(metadata, profile)}
        receipt["documentIdentity"]["evaluation100ExecutionProtocolHashes"]["reconciliationSha256"] = h("old continuation")
        with self.assertRaisesRegex(ValueError, "package inputs disagree"):
            release.require_validation_identity(receipt, metadata, profile)
        for key, value in (("reviewPolicyTiming", "fully-preregistered"), ("fullReviewPolicyPreregistered", True),
                           ("methodPreregistered", True), ("methodTimingIndependentlyCertified", True),
                           ("methodEvidenceHashProvenance", "computedBeforeQuestions"),
                           ("methodIntentSha256", h("different method")), ("timingAdmissionReceiptSha256", h("different admission"))):
            receipt = {"documentIdentity": release.document_identity(metadata, profile)}
            receipt["documentIdentity"]["evaluation100Review"][key] = value
            with self.subTest(review_field=key), self.assertRaisesRegex(ValueError, "package inputs disagree"):
                release.require_validation_identity(receipt, metadata, profile)

    def test_package_includes_exact_study_and_bound_status_but_no_approval_or_private_paths(self):
        profile = release.VALIDATION_20261002
        pair, receipt = self.package_inputs()
        output = self.private / "SYNTHETIC-package"
        projection_before = self.projection.read_bytes()
        with ExitStack() as stack:
            stack.enter_context(patch.object(packager, "ROOT", self.source))
            model = stack.enter_context(patch.object(packager, "build", side_effect=self.model_stub))
            for name in ("inspect_word", "inspect_html", "check_capture_fidelity"):
                stack.enter_context(patch.object(packager, name))
            result = packager.package(pair, receipt, output, None, release_profile=profile,
                                      release_approval=self.approval_path, evaluation100_path=self.study_path)
            self.assertEqual(self.study_path, model.call_args.kwargs["evaluation100_path"])
        self.assertEqual(projection_before, self.projection.read_bytes())
        self.assertEqual(profile.package_name, result["archive"])
        with zipfile.ZipFile(output / result["archive"]) as archive:
            names = archive.namelist()
            self.assertEqual(self.study_path.read_bytes(), archive.read("reports/evaluation100.json"))
            state = json.loads(archive.read(profile.status_name))
            self.assertEqual("furusato-document-validation-snapshot-package/v1", state["schemaVersion"])
            self.assertEqual(self.study, state["evaluation100"])
            self.assertEqual(self.approval["evaluation100Sha256"], state["evaluation100Sha256"])
            self.assertEqual(state["documentIdentity"], result["documentIdentity"])
            self.assertFalse(state["aiAnswerQualityAccepted"])
            self.assertFalse(state["mainPromoted"])
            self.assertFalse(state["liveVerificationCertified"])
            self.assertFalse(state["documentRelease"]["originalReleaseAssetsReplaced"])
            self.assertFalse(state["documentRelease"]["fullReviewPolicyPreregistered"])
            self.assertFalse(state["documentRelease"]["methodPreregistered"])
            self.assertFalse(state["documentRelease"]["methodTimingIndependentlyCertified"])
            self.assertFalse(state["documentRelease"]["reviewToolingPreregistered"])
            self.assertEqual("computedAtAdmission", state["documentRelease"]["methodEvidenceHashProvenance"])
            self.assertEqual(self.study["executionProtocol"], state["executionProtocol"])
            self.assertIs(False, state["executionProtocol"]["originalProtocolWasFullyFollowed"])
            self.assertIs(False, state["executionProtocol"]["executionAmendmentPreregistered"])
            self.assertEqual(study100.execution_binding(self.study)["executionProtocolSha256"], state["executionProtocolSha256"])
            self.assertEqual(state["executionProtocolHashes"], state["documentRelease"]["executionProtocolHashes"])
            self.assertEqual(study100.REVIEW_POLICY_TIMING, state["documentRelease"]["reviewPolicyTiming"])
            self.assertEqual(dict(release.RELEASE_COUNTS), state["documentRelease"]["originalCounts"])
            self.assertNotIn("RELEASE_STATUS.json", names)
            self.assertNotIn(self.approval_path.name, "\n".join(names))
            self.assertNotIn(str(self.private), archive.read(profile.status_name).decode("utf-8"))
            start = archive.read("START_HERE.txt").decode("utf-8")
            self.assertIn("no independent human sign-off", start)
            self.assertIn("not a replacement release", start)
            self.assertIn("not pooled", start)
            self.assertIn("fullReviewPolicyPreregistered=false", start)
            self.assertIn("methodPreregistered=false", start)
            self.assertIn("methodTimingIndependentlyCertified=false", start)
            self.assertIn("reviewToolingPreregistered=false", start)
            self.assertIn("computedAtAdmission", start)
            self.assertIn(study100.REVIEW_POLICY_TIMING, start)
            self.assertIn("does not rewrite the original capture plan/candidate/claims", start)
            self.assertIn("original blanket no-resume policy WAS amended", start)
            self.assertIn("originalProtocolWasFullyFollowed=false", start)
            self.assertIn("HTTP500 outcome remains UNKNOWN and is never replayed", start)
            self.assertIn("not20", start)
            entries = dict(line.split("  ", 1)[::-1] for line in archive.read("SHA256SUMS.txt").decode("utf-8").splitlines())
            self.assertEqual(self.approval["evaluation100Sha256"], entries["reports/evaluation100.json"])

    def test_stale_receipt_and_study_changed_during_packaging_fail_before_output(self):
        pair, receipt_path = self.package_inputs()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        good_receipt = copy.deepcopy(receipt)
        output = self.private / "SYNTHETIC-rejected-package"
        with ExitStack() as stack:
            stack.enter_context(patch.object(packager, "ROOT", self.source))
            stack.enter_context(patch.object(packager, "build", side_effect=self.model_stub))
            inspect = stack.enter_context(patch.object(packager, "inspect_word"))
            for name in ("inspect_html", "check_capture_fidelity"):
                stack.enter_context(patch.object(packager, name))
            receipt["documentIdentity"]["evaluation100Sha256"] = h("old study")
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "package inputs disagree"):
                packager.package(pair, receipt_path, output, None, release_profile="validation-20261002",
                                 release_approval=self.approval_path, evaluation100_path=self.study_path)
            inspect.assert_not_called()
            receipt_path.write_text(json.dumps(good_receipt), encoding="utf-8")
            def change_study(*args, **kwargs):
                self.study_path.write_bytes(self.study_path.read_bytes() + b"\n")
                return {}
            with patch.object(packager, "collect_public_reports", side_effect=change_study):
                with self.assertRaisesRegex(ValueError, "study changed during packaging"):
                    packager.package(pair, receipt_path, output, None, release_profile="validation-20261002",
                                     release_approval=self.approval_path, evaluation100_path=self.study_path)
        self.assertFalse(output.exists())

    def test_synthetic_preview_smoke_cannot_be_packaged_even_with_a_mock_receipt(self):
        metadata = self.metadata()
        metadata.pop("documentRelease")
        metadata["version"] = release.PREVIEW.version
        metadata["evaluation100"] = synthetic_study()
        metadata["evaluation100Sha256"] = h("synthetic bytes")
        with patch.object(packager, "ROOT", self.source), patch.object(packager, "build", return_value=(
            Document([], [], [], []), None, None, None, {}, metadata,
        )):
            with patch.object(packager, "load_validated_inputs") as check:
                with self.assertRaisesRegex(ValueError, "Synthetic private study fixtures"):
                    packager.package(self.private / "pair", self.private / "receipt.json", self.private / "package", None,
                                     evaluation100_path=self.study_path)
                check.assert_not_called()
        self.assertFalse((self.private / "package").exists())

    def test_preview_study_identity_survives_without_an_original_suite_selection(self):
        metadata = {"version": release.PREVIEW.version, "contentSha256": h("private preview"),
                    "evaluation100": synthetic_study(), "evaluation100Sha256": h("synthetic bytes")}
        state = packager.selected_package_status(metadata)
        self.assertEqual(metadata["evaluation100"], state["evaluation100"])
        self.assertEqual(metadata["evaluation100Sha256"], state["documentIdentity"]["evaluation100Sha256"])
        self.assertIn("SYNTHETIC PRIVATE TEST", packager.start_here(metadata))
        with self.assertRaisesRegex(ValueError, "package inputs disagree"):
            release.require_validation_identity({}, metadata)

    def test_powershell_threads_study_to_all_three_steps_and_preserves_strict_gate(self):
        text = (ROOT / "tools" / "docs" / "Build-Preview30.ps1").read_text(encoding="utf-8")
        self.assertEqual(3, text.count("@('--evaluation100', $Evaluation100)"))
        for token in ("'validation-20261002'", "$buildArgs += '--require-acceptance'",
                      "$packArgs += '--require-acceptance'", "A dated snapshot requires Evaluation100"):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
