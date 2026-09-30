"""Public report tests; no Word/HTML/ZIP, cloud calls or private inputs."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]
from build_preview30_reports import FINAL_RUN_ID, report_payloads, publication_link, generate
from package_preview30 import collect_public_reports
from furusato_docs import preview30_public_evidence as public
from furusato_docs.preview30_content import build, PREVIEW_NOTICE_JA


class PublicFinalReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = ROOT / public.DEFAULT_RELATIVE
        cls.evidence = public.load(cls.projection, root=ROOT)
        cls.final = next(run for run in cls.evidence["originalSuiteRuns"] if run["id"] == FINAL_RUN_ID)

    def test_final_method_differentiates_calls_question_slots_and_conversations(self):
        self.assertEqual({"pass": 48, "fail": 36, "executionUnverified": 0, "blocked": 0, "notApplicable": 0}, self.final["counts"])
        self.assertEqual({"content": 29, "nativeAcceptance": 7}, self.final["failureCounts"])
        self.assertEqual(7, self.final["independentExecutionTraces"])
        self.assertEqual(9, sum(self.final["method"]["sourceExecutions"].values()))
        self.assertEqual(10, self.final["method"]["distinctBackendConversationsProven"])
        self.assertEqual("manual-fixed-rubric-offline", self.final["method"]["judgment"])
        self.assertTrue(self.final["freshBackendProof"])
        self.assertFalse(self.final["accepted"])
        self.assertFalse(self.final["promoted"])
        self.assertFalse(self.final["method"]["causalAbClaimed"])

    def test_method_cannot_inflate_traces_freshness_or_causal_claim(self):
        for mutate in (
            lambda run: run["method"].update(causalAbClaimed=True),
            lambda run: run["method"].update(distinctBackendConversationsProven=9),
            lambda run: run["method"].update(sourceExecutions={"sql": 1, "gql": 0, "kql": 0}),
            lambda run: run["method"].update(recordedModel="person@example.com"),
            lambda run: run.update(accepted=True),
        ):
            candidate = copy.deepcopy(self.final)
            mutate(candidate)
            with self.assertRaises(ValueError):
                public.suite_runs([candidate])

    def test_reports_reproduce_from_source_only_and_keep_unknown_urls_unlinked(self):
        first = report_payloads(self.projection, root=ROOT)
        second = report_payloads(self.projection, root=ROOT)
        self.assertEqual(first, second)
        summary = json.loads(first["evaluation-summary.json"])
        self.assertIsNone(summary["publication"]["previewBranchUrl"])
        self.assertIsNone(summary["publication"]["previewReleaseUrl"])
        self.assertFalse(summary["publication"]["stableArtifactsReplaced"])
        self.assertFalse(summary["qualityAccepted"])
        self.assertEqual(4, summary["postcheck"]["unchangedPublications"])
        self.assertFalse(summary["postcheck"]["republished"])
        self.assertTrue(summary["postcheck"]["compatDraftCatalogMetadataExpanded"])
        self.assertTrue(summary["postcheck"]["effectiveSelectedTablesAndColumnsUnchanged"])
        self.assertEqual({"kql": 11, "lakehouse": 99}, summary["postcheck"]["effectiveSelectionCounts"])
        self.assertEqual(0, summary["externalSdk"]["questionsSubmitted"])
        self.assertFalse(summary["externalSdk"]["universalSdkFailureClaimed"])
        generate(self.projection, ROOT / "docs" / "v3-preview" / "reports", check=True, root=ROOT)

    def test_report_packaging_requires_matching_projection_and_explicit_allowlist(self):
        metadata = build(ROOT)[-1]
        reports = collect_public_reports(metadata, root=ROOT)
        self.assertEqual({"reports/evaluation-summary.json", "reports/evaluation-report.md", "reports/progress-report.md", "reports/SHA256SUMS.txt"}, set(reports))
        metadata["publicEvidenceProjectionSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "selected source evidence"):
            collect_public_reports(metadata, root=ROOT)

    def test_preview_presentation_and_residual_boundaries_are_explicit(self):
        reports = report_payloads(self.projection, root=ROOT)
        text = "\n".join(blob.decode("utf-8") for blob in reports.values())
        self.assertIn("実装・検証結果を収録したPreview", PREVIEW_NOTICE_JA)
        for token in ("AI回答品質は未合格", "48 PASS", "36 FAIL", "generation2 connector",
                      "not a direct causal MCP A/B", "native-gate acceptance",
                      "effective", "unselected raw EventID", "missing Fabric",
                      "not a universal SDK-failure", "no verified URL supplied"):
            self.assertIn(token.lower(), text.lower())
        self.assertNotIn("condition_text", text)
        self.assertNotIn("conversation_id", text)
        self.assertNotIn("answer_pointer", text)
        self.assertNotIn("reasoningItems", text)

    def test_fake_or_private_publication_links_are_rejected(self):
        for value in ("https://example.com/preview", "http://github.com/o/r/tree/preview",
                      "https://github.com/o/r/tree/", "https://github.com/o/r/issues/1"):
            with self.assertRaises(ValueError):
                publication_link(value, "branch")
        self.assertIsNone(publication_link(None, "branch"))


if __name__ == "__main__":
    unittest.main()
