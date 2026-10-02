"""Synthetic offline selection fixtures; no questions, answers or deliverable builds."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from build_preview30_reports import CASE_ROWS, FINAL_RUN_ID, generate, report_payloads
from export_preview30_evidence import export_projection
from furusato_docs import preview30_content as content
from furusato_docs import preview30_public_evidence as public
from furusato_docs import preview30_reporting as reporting
from package_preview30 import collect_public_reports, selected_package_status, start_here


def synthetic_run(ident="synthetic-selected", *, all_pass=False, accepted=False):
    denominators = (7, 6, 6, 11, 14, 10, 8, 7, 8, 7)
    decisions = (
        (5, 1, 1, 0, 0), (3, 1, 0, 1, 1), (6, 0, 0, 0, 0),
        (11, 0, 0, 0, 0), (11, 3, 0, 0, 0), (8, 2, 0, 0, 0),
        (8, 0, 0, 0, 0), (7, 0, 0, 0, 0), (7, 1, 0, 0, 0),
        (0, 7, 0, 0, 0),
    )
    calls = (
        {"sql": (2, 1)}, {"sql": (1, 1)}, {"sql": (1, 0)}, {"gql": (1, 1)},
        {"sql": (1, 1), "gql": (1, 1)}, {"kql": (1, 1)}, {"kql": (1, 0)},
        {}, {"sql": (1, 0), "gql": (1, 0), "kql": (1, 0), "dax": (1, 1)}, {},
    )
    successes = {language: 0 for language in reporting.SOURCE_LANGUAGES}
    rejections = dict(successes)
    cases = []
    for index, (count, decisions_row, calls_row) in enumerate(zip(denominators, decisions, calls)):
        for language, (successful, rejected) in calls_row.items():
            successes[language] += successful
            rejections[language] += rejected
        counts = (count, 0, 0, 0, 0) if all_pass else decisions_row
        cases.append({
            "case": f"T{index + 1:02d}", "counts": dict(zip(reporting.VERDICT_KEYS, counts)),
            "sourceAttempts": sum(sum(value) for value in calls_row.values()),
            "successfulSourceExecutions": sum(value[0] for value in calls_row.values()),
            "rejectedSourceAttempts": sum(value[1] for value in calls_row.values()),
            "nativeGate": index == 9 and not all_pass,
            "completedNativeResponse": index != 9 or all_pass,
            "successfulQueryLanguages": list(calls_row),
        })
    counts = {key: sum(case["counts"][key] for case in cases) for key in reporting.VERDICT_KEYS}
    run = {
        "id": ident, "label": {"ja": "合成suite fixture", "en": "Synthetic suite fixture"},
        "observedAt": "2026-09-30T00:00:00Z", "questionCount": 10, "conditionCount": 84,
        "submittedQuestions": 10, "preblockedQuestions": 0, "counts": counts,
        "failureCounts": {"content": counts["fail"] - (0 if all_pass else 7), "nativeAcceptance": 0 if all_pass else 7},
        "independentExecutionTraces": 8, "freshBackendProof": True,
        "accepted": accepted, "promoted": False,
        "summary": {"ja": "合成fixtureの審査記録。実結果ではありません。", "en": "Reviewed synthetic fixture; not an actual result."},
        "caseAggregates": cases,
        "method": {
            "surface": "native-ui", "transport": "responses", "stage": "sandbox",
            "runtime": "preview", "recordedModel": "synthetic-model",
            "judgment": "manual-fixed-rubric-offline", "distinctBackendConversationsProven": 10,
            "sourceExecutions": {language: successes[language] + rejections[language] for language in successes},
            "successfulSourceExecutions": successes, "rejectedSourceAttempts": rejections,
            "causalAbClaimed": False,
        },
    }
    if not all_pass:
        run["notApplicableReason"] = {
            "ja": "合成fixtureの1項目は非該当。元の分母を保持。",
            "en": "One synthetic-fixture check is inapplicable; the original denominator is retained.",
        }
    return run


def synthetic_legacy():
    run = synthetic_run(FINAL_RUN_ID)
    del run["caseAggregates"]
    del run["notApplicableReason"]
    run.update(
        counts=dict(zip(reporting.VERDICT_KEYS, (48, 36, 0, 0, 0))),
        failureCounts={"content": 29, "nativeAcceptance": 7}, independentExecutionTraces=7,
    )
    run["method"].update(recordedModel="gpt-5.6-terra", sourceExecutions={"sql": 5, "gql": 2, "kql": 2})
    del run["method"]["successfulSourceExecutions"]
    del run["method"]["rejectedSourceAttempts"]
    return run


def synthetic_projection():
    older = synthetic_run("synthetic-older", all_pass=True, accepted=True)
    older["observedAt"] = "2026-09-29T00:00:00Z"
    newer = synthetic_run("synthetic-newer", all_pass=True)
    newer["observedAt"] = "2026-09-30T01:00:00Z"
    labs = {
        item["lab"]: {
            "status": "not-run", "reason": {"ja": "合成fixtureのみ", "en": "Synthetic fixture only"},
            "evidenceIds": [],
        }
        for item in public.private.requests()
    }
    return {
        "schemaVersion": public.SCHEMA, "scope": public.SCOPE, "approved": True,
        "reviewedAt": "2026-09-30T02:00:00Z", "reviewer": "synthetic-review",
        "freezeStatus": "awaiting-final-consumer-proof", "captures": [], "labs": labs,
        "originalSuiteRuns": [synthetic_legacy(), older, synthetic_run(), newer],
        "selectedOriginalSuiteRunId": "synthetic-selected",
    }


class SelectedReportingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="preview30-selected-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.projection = self.root / "manifest.json"
        self.reports = self.root / "docs" / "v3-preview" / "selected-reports"
        self.data = synthetic_projection()
        self.write_projection()

    def write_projection(self):
        self.projection.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def selected(self):
        return self.data["originalSuiteRuns"][2]

    def payloads(self):
        return report_payloads(self.projection, root=self.root)

    def summary(self):
        return json.loads(self.payloads()["evaluation-summary.json"])

    def build_model(self):
        evidence = public.load(self.projection, root=self.root)
        with patch.object(public, "resolve", return_value=evidence):
            return content.build(ROOT, public_evidence_path=self.projection)

    def metadata(self):
        return self.build_model()[-1]

    def generate(self):
        return generate(self.projection, self.reports, root=self.root)

    def reseal_summary(self, summary):
        (self.reports / "evaluation-summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        (self.reports / "SHA256SUMS.txt").write_text(
            "".join(
                f"{hashlib.sha256((self.reports / name).read_bytes()).hexdigest()}  {name}\n"
                for name in ("evaluation-report.md", "evaluation-summary.json", "progress-report.md")
            ), encoding="utf-8",
        )

    def test_selection_is_explicit_not_highest_latest_or_legacy_and_does_not_mutate_ledgers(self):
        original = self.projection.read_bytes()
        evidence = public.load(self.projection, root=self.root)
        selected = public.selected_original_suite_run(evidence)
        self.assertEqual("synthetic-selected", selected["id"])
        self.assertEqual(66, selected["counts"]["pass"])
        summary = self.summary()
        self.assertEqual(self.selected(), summary["finalEvaluation"])
        self.assertEqual(
            [run for run in self.data["originalSuiteRuns"] if run["id"] != "synthetic-selected"],
            summary["historicalRuns"],
        )
        self.assertEqual(self.data["originalSuiteRuns"], evidence["originalSuiteRuns"])
        self.assertEqual(original, self.projection.read_bytes())

    def test_unknown_duplicate_or_nonportable_selection_is_rejected(self):
        for ident in ("synthetic-missing", None, False, 7, [], {}, "UPPERCASE", ""):
            self.data["selectedOriginalSuiteRunId"] = ident
            self.write_projection()
            with self.subTest(ident=ident), self.assertRaises(ValueError):
                public.load(self.projection, root=self.root)
        self.data = synthetic_projection()
        self.data["originalSuiteRuns"].append(copy.deepcopy(self.selected()))
        self.write_projection()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.payloads()

    def test_duplicate_json_selection_and_unknown_automatic_policy_are_rejected(self):
        raw = self.projection.read_text(encoding="utf-8").replace(
            '"selectedOriginalSuiteRunId": "synthetic-selected"',
            '"selectedOriginalSuiteRunId": "synthetic-selected",\n'
            '  "selectedOriginalSuiteRunId": "synthetic-newer"',
        )
        self.projection.write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate selectedOriginalSuiteRunId"):
            self.payloads()
        self.data["automaticSelection"] = "latest"
        self.write_projection()
        with self.assertRaisesRegex(ValueError, "unknown/private"):
            self.payloads()

    def test_nonlegacy_selection_requires_complete_validated_cases_and_method(self):
        mutations = (
            lambda run: run.pop("caseAggregates"),
            lambda run: run["caseAggregates"].pop(),
            lambda run: run["caseAggregates"][0].update(case="T02"),
            lambda run: run["caseAggregates"][0]["counts"].update({"pass": 6}),
            lambda run: run["method"].pop("successfulSourceExecutions"),
            lambda run: run["caseAggregates"][0].update(sourceAttempts=20),
        )
        for mutate in mutations:
            self.data = synthetic_projection()
            mutate(self.selected())
            self.write_projection()
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.payloads()

    def test_dynamic_cases_attempts_successes_rejections_dax_and_native_completion_are_distinct(self):
        summary = self.summary()
        self.assertEqual(self.selected()["caseAggregates"], summary["caseAggregates"])
        self.assertNotEqual([row[1:3] for row in CASE_ROWS], [
            (case["counts"]["pass"], case["counts"]["fail"]) for case in summary["caseAggregates"]
        ])
        proof = summary["executionEvidence"]
        self.assertEqual((20, 13, 7), tuple(proof[key] for key in (
            "sourceAttemptCount", "successfulSourceExecutionCount", "rejectedSourceAttemptCount",
        )))
        self.assertEqual({"sql": 9, "gql": 5, "kql": 4, "dax": 2}, proof["sourceAttempts"])
        self.assertEqual({"sql": 6, "gql": 3, "kql": 3, "dax": 1}, proof["successfulSourceExecutions"])
        self.assertEqual({"sql": 3, "gql": 2, "kql": 1, "dax": 1}, proof["rejectedSourceAttempts"])
        self.assertEqual(8, proof["independentlyTracedQuestionSlots"])
        self.assertEqual(10, proof["distinctBackendConversationsProven"])
        self.assertEqual({"completed": 9, "notCompleted": 1, "unverified": 0}, proof["nativeResponseCompletion"])
        text = self.payloads()["evaluation-report.md"].decode("utf-8")
        self.assertIn("| DAX | 2 | 1 | 1 |", text)
        self.assertIn("general-population accuracy", text)
        self.assertIn("direct causal MCP A/B", text)

    def test_selected_context_never_borrows_old_t04_postcheck_or_sdk_outcomes(self):
        summary = self.summary()
        self.assertEqual(0, summary["caseAggregates"][3]["counts"]["fail"])
        for key in ("scopedCompatibility", "postcheck", "externalSdk"):
            self.assertEqual("unverified-not-newly-rechecked", summary[key]["status"])
            self.assertIn("未検証", summary[key]["reason"]["ja"])
            self.assertIn("not newly rechecked", summary[key]["reason"]["en"])
        self.assertNotIn("unchangedPublications", summary["postcheck"])
        self.assertNotIn("questionsSubmitted", summary["externalSdk"])
        text = "\n".join(blob.decode("utf-8") for blob in self.payloads().values())
        self.assertNotIn("missing Fabric runtime service-discovery module", text)
        self.assertNotIn("T04 still failed", text)
        self.assertFalse(summary["allFeaturesPassedClaimed"])
        self.assertFalse(summary["finalUserAcceptanceCertified"])
        self.assertFalse(summary["pairBuildAuthorized"])

    def test_successful_calls_do_not_certify_complete_results_or_native_terminal_completion(self):
        before = copy.deepcopy(self.data)
        payloads = self.payloads()
        summary = json.loads(payloads["evaluation-summary.json"])
        ja, en = reporting.execution_completeness_notice()
        for name in ("evaluation-report.md", "progress-report.md"):
            text = payloads[name].decode("utf-8")
            self.assertIn(ja, text)
            self.assertIn(en, text)
            self.assertIn("incomplete/truncated results", text)
            self.assertIn("does not retroactively complete an earlier result", text)
            self.assertIn("Terminal native-response completion is separate proof", text)
        document, _, _, _, _, metadata = self.build_model()
        for ident in ("ch-17-7", "ch-19-10"):
            section = next(section for section in document.walk() if section.ident == ident)
            text = json.dumps(asdict(section), ensure_ascii=False)
            self.assertIn(ja, text)
            self.assertIn(en, text)
            self.assertIn("Terminal native responses completed", text)
        self.assertEqual(summary["executionEvidence"], metadata["selectedSuiteExecutionEvidence"])
        self.assertEqual(13, summary["executionEvidence"]["successfulSourceExecutionCount"])
        self.assertEqual(9, summary["executionEvidence"]["nativeResponseCompletion"]["completed"])
        self.assertEqual(before, self.data)
        self.assertNotIn("truncatedSuccessfulSourceCalls", payloads["evaluation-summary.json"].decode("utf-8"))
        self.assertFalse(summary["qualityAccepted"])

    def test_native_fixed_block_stays_failed_while_completed_contextual_cases_can_have_zero_queries(self):
        summary = self.summary()
        t08, t10 = summary["caseAggregates"][7], summary["caseAggregates"][9]
        self.assertEqual((0, 0, True, False), (
            t08["sourceAttempts"], t08["successfulSourceExecutions"],
            t08["completedNativeResponse"], t08["nativeGate"],
        ))
        self.assertEqual((7, 0, False, True), (
            t10["counts"]["fail"], t10["sourceAttempts"], t10["completedNativeResponse"], t10["nativeGate"],
        ))
        self.assertFalse(summary["qualityAccepted"])
        t10 = self.selected()["caseAggregates"][9]
        t10["counts"].update({"pass": 7, "fail": 0})
        self.write_projection()
        with self.assertRaisesRegex(ValueError, "native fixed block"):
            self.payloads()

    def test_missing_completion_model_or_dax_facts_remain_unverified_not_zero(self):
        run = self.selected()
        del run["caseAggregates"][0]["completedNativeResponse"]
        run["caseAggregates"][0]["successfulQueryLanguages"] = []
        run["method"].update(stage=None, runtime=None, recordedModel=None)
        run["caseAggregates"][8].update(
            sourceAttempts=3, successfulSourceExecutions=3, rejectedSourceAttempts=0,
            successfulQueryLanguages=["sql", "gql", "kql"],
        )
        for field in ("sourceExecutions", "successfulSourceExecutions", "rejectedSourceAttempts"):
            del run["method"][field]["dax"]
        self.write_projection()
        summary = self.summary()
        self.assertEqual({"completed": 8, "notCompleted": 1, "unverified": 1}, summary["executionEvidence"]["nativeResponseCompletion"])
        text = self.payloads()["evaluation-report.md"].decode("utf-8")
        self.assertIn("| DAX | 未検証<br>unverified | 未検証<br>unverified | 未検証<br>unverified |", text)
        self.assertNotIn("gpt-5.6-terra", text)
        self.assertIn("| stage<br>Stage | 未検証<br>unverified |", text)

    def test_all_pass_is_not_automatically_accepted_and_reviewed_acceptance_remains_scoped(self):
        for accepted in (False, True):
            self.data["originalSuiteRuns"][2] = synthetic_run(all_pass=True, accepted=accepted)
            self.write_projection()
            summary = self.summary()
            self.assertEqual(84, summary["finalEvaluation"]["counts"]["pass"])
            self.assertIs(summary["qualityAccepted"], accepted)
            self.assertIs(summary["originalSuiteAccepted"], accepted)
            self.assertFalse(summary["mainPromoted"])
            self.assertFalse(summary["finalUserAcceptanceCertified"])
            self.assertFalse(summary["allFeaturesPassedClaimed"])
        self.selected()["freshBackendProof"] = False
        self.write_projection()
        with self.assertRaisesRegex(ValueError, "acceptance"):
            self.payloads()

    def test_shared_model_metadata_cases_context_and_package_selection_match(self):
        document, _, _, _, _, metadata = self.build_model()
        summary = self.summary()
        self.assertEqual(summary["finalEvaluation"], metadata["finalEvaluation"])
        self.assertEqual(summary["executionEvidence"], metadata["selectedSuiteExecutionEvidence"])
        self.assertEqual(summary["presentation"], metadata["previewPresentation"])
        self.assertEqual("synthetic-selected", metadata["selectedOriginalSuiteRunId"])
        self.assertFalse(metadata["aiAnswerQualityAccepted"])
        chapter = next(section for section in document.walk() if section.ident == "ch-19-10")
        tables = [block for block in chapter.blocks if block.kind == "table"]
        cases = [[cell.en for cell in row] for row in tables[2]["rows"]]
        self.assertEqual(["T04", "11", "0", "0", "0", "0", "—"], cases[3])
        self.assertEqual(["T10", "0", "7", "0", "0", "0", "fixed-block failure"], cases[9])
        text = json.dumps(asdict(chapter), ensure_ascii=False)
        self.assertNotIn("48 PASS", text)
        self.assertNotIn("T04 aggregation grain/presentation", text)
        for ident in ("ch-17-7", "ch-20-6"):
            section_text = json.dumps(asdict(next(section for section in document.walk() if section.ident == ident)), ensure_ascii=False)
            self.assertNotIn("missing Fabric", section_text)
            self.assertNotIn("T04 still fails", section_text)
            self.assertIn("not newly rechecked", section_text)
        self.assertIn("synthetic-selected", document.sections[0].blocks[0]["text"].en)
        generated = self.generate()
        self.assertEqual("synthetic-selected", generated["selectedOriginalSuiteRunId"])
        self.assertEqual(0, generated["wordHtmlZipBuilds"])
        files = collect_public_reports(metadata, root=self.root, reports_path=self.reports)
        self.assertEqual(4, len(files))
        state = selected_package_status(metadata)
        self.assertEqual("synthetic-selected", state["selectedOriginalSuiteRunId"])
        self.assertEqual(summary["evidenceProjectionSha256"], state["publicEvidenceProjectionSha256"])
        self.assertFalse(state["aiAnswerQualityAccepted"])
        self.assertFalse(state["finalUserAcceptanceCertified"])
        self.assertIn("synthetic-selected", start_here(metadata))

    def test_packaging_rejects_resealed_wrong_run_cases_counters_context_or_history(self):
        metadata = self.metadata()
        self.generate()
        original = self.summary()
        mutations = (
            lambda summary: summary.update(selectedOriginalSuiteRunId="synthetic-newer"),
            lambda summary: summary.pop("selectedOriginalSuiteRunId"),
            lambda summary: summary.update(finalEvaluation=self.data["originalSuiteRuns"][3]),
            lambda summary: summary.update(caseAggregates=[{"case": "T01", "pass": 7, "fail": 0}]),
            lambda summary: summary["executionEvidence"]["successfulSourceExecutions"].update(dax=2),
            lambda summary: summary["scopedCompatibility"].update(status="verified"),
            lambda summary: summary["historicalRuns"][0]["counts"].update({"pass": 84}),
            lambda summary: summary.update(qualityAccepted=True),
            lambda summary: summary.update(finalUserAcceptanceCertified=True),
            lambda summary: summary.update(generalPopulationAccuracyClaimed=True),
            lambda summary: summary.update(directCausalMcpAbClaimed=True),
            lambda summary: summary["labStates"].update(evaluation="passed"),
        )
        for mutate in mutations:
            summary = copy.deepcopy(original)
            mutate(summary)
            self.reseal_summary(summary)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                collect_public_reports(metadata, root=self.root, reports_path=self.reports)
        self.reseal_summary(original)
        for mutate in (
            lambda model: model.update(publicEvidenceProjectionSha256="0" * 64),
            lambda model: model.update(selectedOriginalSuiteRunId="synthetic-newer"),
            lambda model: model.update(finalEvaluation=self.data["originalSuiteRuns"][3]),
            lambda model: model["selectedSuiteExecutionEvidence"].update(sourceAttemptCount=9),
        ):
            model = copy.deepcopy(metadata)
            mutate(model)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                collect_public_reports(model, root=self.root, reports_path=self.reports)

    def test_selected_acceptance_package_status_and_notice_follow_reviewed_flags(self):
        self.data["originalSuiteRuns"][2] = synthetic_run(all_pass=True, accepted=True)
        self.write_projection()
        metadata = self.metadata()
        self.generate()
        collect_public_reports(metadata, root=self.root, reports_path=self.reports)
        self.assertTrue(metadata["aiAnswerQualityAccepted"])
        self.assertTrue(selected_package_status(metadata)["aiAnswerQualityAccepted"])
        self.assertEqual(metadata["previewPresentation"], reporting.metadata_presentation(metadata))
        self.assertIn("審査記録上の受入のみ", reporting.metadata_presentation(metadata)["ja"])
        self.assertIn("reviewed original-suite acceptance only", reporting.metadata_presentation(metadata)["en"])
        self.assertFalse(selected_package_status(metadata)["finalUserAcceptanceCertified"])
        self.assertIn("reviewed record only", start_here(metadata))
        self.assertNotIn("AI answer quality is not accepted.", start_here(metadata))

    def test_renderer_notice_fallback_retains_legacy_bilingual_presentation_without_builds(self):
        self.assertEqual(
            {"ja": content.PREVIEW_NOTICE_JA, "en": content.PREVIEW_NOTICE_EN},
            reporting.metadata_presentation({}),
        )
        self.assertEqual(
            {"ja": content.PREVIEW_NOTICE_JA, "en": content.PREVIEW_NOTICE_EN},
            reporting.metadata_presentation(reporting.selection_metadata(public.load(self.projection, root=self.root))),
        )

    def test_report_check_rejects_changed_selection_and_package_path_cannot_escape(self):
        metadata = self.metadata()
        self.generate()
        generate(self.projection, self.reports, check=True, root=self.root)
        with self.assertRaisesRegex(ValueError, "source docs/v3-preview"):
            collect_public_reports(metadata, root=self.root, reports_path=self.root / "outside-reports")
        self.data["selectedOriginalSuiteRunId"] = "synthetic-newer"
        self.write_projection()
        with self.assertRaisesRegex(ValueError, "do not match"):
            generate(self.projection, self.reports, check=True, root=self.root)
        retained = {path.name: path.read_bytes() for path in self.reports.iterdir()}
        with self.assertRaisesRegex(ValueError, "fresh reviewed directory"):
            self.generate()
        self.assertEqual(retained, {path.name: path.read_bytes() for path in self.reports.iterdir()})

    def test_absent_selection_preserves_legacy_output_even_with_higher_later_runs(self):
        del self.data["selectedOriginalSuiteRunId"]
        self.write_projection()
        summary = self.summary()
        self.assertEqual(FINAL_RUN_ID, summary["finalEvaluation"]["id"])
        self.assertEqual(48, summary["finalEvaluation"]["counts"]["pass"])
        self.assertNotIn("selectedOriginalSuiteRunId", summary)
        self.assertEqual(
            [{"case": ident, "pass": passed, "fail": failed, "sourceExecutions": count, "nativeGate": gate}
             for ident, passed, failed, count, gate in CASE_ROWS],
            summary["caseAggregates"],
        )
        del self.data["originalSuiteRuns"][0]
        self.write_projection()
        evidence = public.load(self.projection, root=self.root)
        self.assertIsNone(public.selected_original_suite_run(evidence))
        with self.assertRaisesRegex(ValueError, "approved final"):
            self.payloads()

    def test_explicit_legacy_selection_keeps_frozen_contract_and_package_identity(self):
        self.data["selectedOriginalSuiteRunId"] = FINAL_RUN_ID
        self.write_projection()
        summary = self.summary()
        self.assertEqual(FINAL_RUN_ID, summary["selectedOriginalSuiteRunId"])
        self.assertEqual(48, summary["finalEvaluation"]["counts"]["pass"])
        metadata = self.metadata()
        self.generate()
        collect_public_reports(metadata, root=self.root, reports_path=self.reports)
        self.assertEqual(FINAL_RUN_ID, selected_package_status(metadata)["selectedOriginalSuiteRunId"])

    def test_legacy_selection_cannot_mix_new_counts_or_case_rows_into_frozen_output(self):
        self.data["selectedOriginalSuiteRunId"] = FINAL_RUN_ID
        self.data["originalSuiteRuns"][0] = synthetic_run(FINAL_RUN_ID, all_pass=True, accepted=True)
        self.write_projection()
        for operation in (self.payloads, self.metadata):
            with self.assertRaisesRegex(ValueError, "frozen Preview"):
                operation()
        run = synthetic_legacy()
        run["method"].update(
            successfulSourceExecutions=copy.deepcopy(run["method"]["sourceExecutions"]),
            rejectedSourceAttempts={"sql": 0, "gql": 0, "kql": 0},
        )
        run["caseAggregates"] = [
            {
                "case": ident, "counts": dict(zip(reporting.VERDICT_KEYS, (passed, failed, 0, 0, 0))),
                "sourceAttempts": attempts, "successfulSourceExecutions": attempts,
                "rejectedSourceAttempts": 0, "nativeGate": gate,
            }
            for ident, passed, failed, attempts, gate in CASE_ROWS
        ]
        run["caseAggregates"][3]["counts"].update({"pass": 7, "fail": 4})
        run["caseAggregates"][4]["counts"].update({"pass": 8, "fail": 6})
        self.data["originalSuiteRuns"][0] = run
        self.write_projection()
        public.load(self.projection, root=self.root)
        for operation in (self.payloads, self.metadata):
            with self.assertRaisesRegex(ValueError, "Legacy case aggregates"):
                operation()

    def test_export_preserves_explicit_reviewed_selection_and_rejects_unknown_id(self):
        source = self.root / "synthetic-source"
        source.mkdir()
        review = self.root / "synthetic-review.json"
        review.write_text(json.dumps({
            "schemaVersion": "furusato-preview30-evidence/v1", "captures": [], "labs": self.data["labs"],
        }), encoding="utf-8")
        runs = self.root / "synthetic-runs.json"
        runs.write_text(json.dumps(self.data["originalSuiteRuns"]), encoding="utf-8")
        output = source / "docs" / "assets" / "synthetic-projection"
        with patch.object(public.private, "ROOT", source):
            export_projection(
                review, output, reviewed_at=self.data["reviewedAt"], reviewer="synthetic-review",
                approved=True, runs_path=runs, root=source,
                selected_original_suite_run_id="synthetic-selected",
            )
            loaded = public.load(output / "manifest.json", root=source)
            self.assertEqual("synthetic-selected", loaded["selectedOriginalSuiteRunId"])
            self.assertEqual(self.data["originalSuiteRuns"], loaded["originalSuiteRuns"])
            bad_output = source / "docs" / "assets" / "synthetic-rejected"
            with self.assertRaisesRegex(ValueError, "exactly one"):
                export_projection(
                    review, bad_output, reviewed_at=self.data["reviewedAt"], reviewer="synthetic-review",
                    approved=True, runs_path=runs, root=source,
                    selected_original_suite_run_id="synthetic-missing",
                )
            self.assertFalse(bad_output.exists())


if __name__ == "__main__":
    unittest.main()
