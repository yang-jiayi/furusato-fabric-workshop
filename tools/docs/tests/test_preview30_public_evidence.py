"""Temporary synthetic fixtures only; no Word, HTML, ZIP or live operations."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]
from export_preview30_evidence import export_projection
from furusato_docs import preview30_content as content
from furusato_docs import preview30_evidence as private
from furusato_docs import preview30_public_evidence as public
from furusato_html.assets import AssetLibrary
from furusato_html.preview30 import register_reviewed_captures
from test_preview30_evaluation_content import fixture as evaluator_fixture


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PublicProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "source"
        self.root.mkdir()
        self.source_patch = patch.object(private, "ROOT", self.root)
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)
        self.raw_root = self.base / "private"
        self.raw_root.mkdir()
        self.original = self.raw_root / "original.png"
        self.sanitized = self.raw_root / "sanitized.png"
        Image.new("RGB", (800, 500), "#e7f1ee").save(self.original)
        self.sanitized.write_bytes(self.original.read_bytes())
        digest = private.digest(self.original)
        labs = private.load()["labs"]
        labs["entities"] = {
            "status": "observed", "reason": {"ja": "テストfixtureの部分観測", "en": "Synthetic test fixture observation"},
            "evidenceIds": ["p30-06-entities"], "executionAndReadbackObserved": False,
            "privateTranscript": "NEVER_EXPORT_THIS_PRIVATE_TRANSCRIPT",
        }
        self.input = self.raw_root / "manifest.json"
        self.data = {
            "schemaVersion": "furusato-preview30-evidence/v1",
            "captures": [{
                "id": "p30-06-entities", "original": "original.png", "sanitized": "sanitized.png",
                "originalSha256": digest, "sanitizedSha256": digest,
                "capturedAt": "2026-09-29T00:00:00Z", "actualUI": True, "experience": "new",
                "reviewed": True, "reviewer": "fixture-review",
                "redactions": "Synthetic fixture with no identities",
                "redactionReview": "accounts-urls-ids-paths-removed",
                "completionEvidence": False,
                "caption": {"ja": "テスト用fixture", "en": "Synthetic fixture, not actual evidence"},
                "privateDebug": "NEVER_EXPORT_THIS_PRIVATE_CAPTURE",
            }],
            "labs": labs, "privateContext": "NEVER_EXPORT_PRIVATE_CONTEXT",
        }
        dump(self.input, self.data)
        self.output = self.root / public.DEFAULT_RELATIVE.parent

    def export(self, output=None, **kwargs):
        return export_projection(
            self.input, output or self.output, reviewed_at="2026-09-30T00:00:00Z",
            reviewer="fixture-review", approved=True, root=self.root, **kwargs,
        )

    def public_data(self):
        return json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))

    def test_public_projection_works_after_private_originals_are_removed(self):
        self.export()
        self.original.unlink()
        self.sanitized.unlink()
        self.input.unlink()
        result = public.resolve(root=self.root)
        self.assertEqual(1, len(result["captures"]))
        self.assertFalse(result["complete"])
        self.assertEqual(public.SCOPE, result["scope"])
        self.assertEqual("observed", result["labs"]["entities"]["status"])

    def test_originals_and_private_fields_are_never_exported(self):
        self.export()
        text = (self.output / "manifest.json").read_text(encoding="utf-8")
        self.assertNotIn("NEVER_EXPORT", text)
        self.assertNotIn(str(self.raw_root), text)
        self.assertNotIn('"original":', text)
        self.assertEqual({"captures", "manifest.json"}, {path.name for path in self.output.iterdir()})
        self.assertEqual(self.data["captures"][0]["originalSha256"], self.public_data()["captures"][0]["originalSha256"])

    def test_export_and_model_content_are_deterministic_and_path_independent(self):
        first = self.export()
        other = self.root / "docs" / "assets" / "same-evidence-elsewhere"
        second = self.export(other)
        self.assertEqual(first["manifestSha256"], second["manifestSha256"])
        self.assertEqual((self.output / "manifest.json").read_bytes(), (other / "manifest.json").read_bytes())
        original = public.load(self.output / "manifest.json", root=self.root)
        relocated = public.load(other / "manifest.json", root=self.root)
        with patch.object(content.preview30_public_evidence, "resolve", return_value=original):
            one = content.build(ROOT)[-1]
        with patch.object(content.preview30_public_evidence, "resolve", return_value=relocated):
            two = content.build(ROOT)[-1]
        self.assertEqual(one, two)
        self.assertEqual(24, one["counts"]["chapters"])
        self.assertFalse(one["newDeploymentReadinessCertified"])

    def test_private_loader_does_not_accept_public_source_paths(self):
        with self.assertRaises(ValueError):
            private._private_file(self.root, "anything.png")
        self.export()
        with self.assertRaisesRegex(ValueError, "schema"):
            private.load(self.output / "manifest.json")

    def test_private_original_hash_gate_is_not_bypassed_by_export(self):
        self.original.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.export()
        self.assertFalse(self.output.exists())

    def test_export_requires_explicit_approval_and_fresh_source_asset_path(self):
        with self.assertRaises(ValueError):
            export_projection(self.input, self.output, reviewed_at="2026-09-30T00:00:00Z", reviewer="fixture", approved=False, root=self.root)
        with self.assertRaises(ValueError):
            self.export(self.base / "outside")
        self.export()
        with self.assertRaises(ValueError):
            self.export()

    def test_public_path_hash_and_review_gates(self):
        self.export()
        good = self.public_data()
        sha = good["captures"][0]["sha256"]
        for path in ("../private.png", "/absolute.png", r"C:\private.png", r"\\host\share\image.png", "captures/../image.png", f"captures/{sha}.png:secret"):
            bad = copy.deepcopy(good)
            bad["captures"][0]["file"] = path
            dump(self.output / "manifest.json", bad)
            with self.subTest(path=path), self.assertRaises(ValueError):
                public.load(self.output / "manifest.json", root=self.root)
        for field, value in (("approved", False), ("scope", "new-deployment-ready"), ("reviewer", "person@example.com"), ("reviewedAt", "2026-09-30")):
            bad = copy.deepcopy(good)
            bad[field] = value
            dump(self.output / "manifest.json", bad)
            with self.subTest(field=field), self.assertRaises(ValueError):
                public.load(self.output / "manifest.json", root=self.root)
        bad = copy.deepcopy(good)
        bad["freezeStatus"] = "automatic-runtime-ready"
        dump(self.output / "manifest.json", bad)
        with self.assertRaisesRegex(ValueError, "freeze status"):
            public.load(self.output / "manifest.json", root=self.root)
        dump(self.output / "manifest.json", good)
        (self.output / good["captures"][0]["file"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            public.load(self.output / "manifest.json", root=self.root)

    def test_public_symlink_escape_is_rejected(self):
        self.export()
        data = self.public_data()
        image = self.output / data["captures"][0]["file"]
        image.unlink()
        try:
            image.symlink_to(self.sanitized)
        except (OSError, NotImplementedError) as error:
            self.skipTest("Symbolic links unavailable: " + str(error))
        with self.assertRaisesRegex(ValueError, "escapes"):
            public.load(self.output / "manifest.json", root=self.root)

    def test_unknown_and_private_fields_are_rejected_recursively(self):
        self.export()
        good = self.public_data()
        for location in ("root", "capture", "lab"):
            bad = copy.deepcopy(good)
            target = bad if location == "root" else bad["captures"][0] if location == "capture" else bad["labs"]["entities"]
            target["rawAnswer"] = "private"
            dump(self.output / "manifest.json", bad)
            with self.subTest(location=location), self.assertRaisesRegex(ValueError, "unknown/private"):
                public.load(self.output / "manifest.json", root=self.root)
        for text in (
            "person@example.com", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "https://cluster.kusto.fabric.microsoft.com", r"C:\Users\private\file",
            r"\\machine\share", "Bearer secret-value",
        ):
            bad = copy.deepcopy(good)
            bad["captures"][0]["caption"]["en"] = text
            dump(self.output / "manifest.json", bad)
            with self.subTest(text=text), self.assertRaises(ValueError):
                public.load(self.output / "manifest.json", root=self.root)

    def test_no_review_chronology_or_image_metadata_shortcut(self):
        self.export()
        good = self.public_data()
        bad = copy.deepcopy(good)
        bad["captures"][0]["reviewedAt"] = "2026-09-28T00:00:00Z"
        dump(self.output / "manifest.json", bad)
        with self.assertRaises(ValueError):
            public.load(self.output / "manifest.json", root=self.root)
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Author", "private author")
        with Image.open(self.sanitized) as image:
            image.save(self.sanitized, pnginfo=metadata)
        self.data["captures"][0]["sanitizedSha256"] = private.digest(self.sanitized)
        dump(self.input, self.data)
        other = self.root / "docs" / "assets" / "metadata-rejected"
        with self.assertRaisesRegex(ValueError, "metadata"):
            self.export(other)
        self.assertFalse(other.exists())

    def test_modes_cannot_be_mixed_and_explicit_public_path_cannot_be_private(self):
        with self.assertRaises(ValueError):
            public.resolve(self.input, self.input, root=self.root)
        with self.assertRaises(ValueError):
            public.resolve(public_path=self.input, root=self.root)

    def test_duplicate_pixels_keep_two_capture_provenances(self):
        self.export()
        first = public.load(self.output / "manifest.json", root=self.root)["captures"]["p30-06-entities"]
        assets = AssetLibrary()
        aliases = register_reviewed_captures(assets, {"first-observation": first, "later-observation": first})
        self.assertEqual({"later-observation": "first-observation"}, aliases)
        self.assertEqual(1, len(assets.digests))
        self.assertEqual(assets.screenshots["first-observation"], assets.screenshots["later-observation"])
        first = {**first, "sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "changed"):
            register_reviewed_captures(AssetLibrary(), {"tampered": first})

    def test_source_owned_aggregates_render_without_private_report(self):
        run = OriginalSuiteAggregateTests().fixture()
        runs_path = self.raw_root / "approved-runs.json"
        dump(runs_path, [run])
        self.export(runs_path=runs_path)
        runs_path.unlink()
        loaded = public.load(self.output / "manifest.json", root=self.root)
        self.assertEqual([run], loaded["originalSuiteRuns"])
        with patch.object(content.preview30_public_evidence, "resolve", return_value=loaded):
            document, _, _, _, _, metadata = content.build(ROOT)
            with self.assertRaisesRegex(ValueError, "private override"):
                content.build(ROOT, evaluation_path=self.raw_root / "private-report.json")
        rendered_model = json.dumps(asdict(document), ensure_ascii=False)
        self.assertIn("Historical baseline", rendered_model)
        self.assertEqual(84, metadata["originalSuiteRuns"][0]["conditionCount"])

    def test_run_after_review_and_private_aggregate_extras_are_rejected(self):
        self.export()
        original = self.public_data()
        run = OriginalSuiteAggregateTests().fixture()
        run["observedAt"] = "2026-10-01T00:00:00Z"
        bad = copy.deepcopy(original)
        bad["originalSuiteRuns"] = [run]
        dump(self.output / "manifest.json", bad)
        with self.assertRaisesRegex(ValueError, "after the public review"):
            public.load(self.output / "manifest.json", root=self.root)
        run["observedAt"] = "2026-09-29T00:00:00Z"
        run["rawAnswer"] = "must not be published"
        dump(self.output / "manifest.json", bad)
        with self.assertRaises(ValueError):
            public.load(self.output / "manifest.json", root=self.root)

    def test_normalized_evaluator_projection_cannot_hide_private_fields_or_uuid(self):
        self.export()
        original = self.public_data()
        for mutation in (
            lambda report: report.update(context="private-context"),
            lambda report: report["inventory"][0].update(case_id="AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"),
        ):
            bad = copy.deepcopy(original)
            report = evaluator_fixture()
            mutation(report)
            bad["evaluationReport"] = report
            dump(self.output / "manifest.json", bad)
            with self.assertRaises(ValueError):
                public.load(self.output / "manifest.json", root=self.root)


class OriginalSuiteAggregateTests(unittest.TestCase):
    def fixture(self):
        return {
            "id": "historical-baseline", "label": {"ja": "履歴baseline", "en": "Historical baseline"},
            "observedAt": "2026-09-30T00:00:00Z", "questionCount": 10, "conditionCount": 84,
            "submittedQuestions": 5, "preblockedQuestions": 5,
            "counts": {"pass": 9, "fail": 23, "executionUnverified": 1, "blocked": 51, "notApplicable": 0},
            "failureCounts": {"content": 23, "nativeAcceptance": 0},
            "independentExecutionTraces": 0, "freshBackendProof": False, "promoted": False, "accepted": False,
            "summary": {"ja": "失敗と未確認を保持", "en": "Failures and unknowns retained"},
        }

    def test_safe_aggregate_keeps_denominators(self):
        value = public.suite_runs([self.fixture()])[0]
        self.assertEqual(84, sum(value["counts"].values()))
        self.assertFalse(value["accepted"])

    def test_no_answer_fields_or_false_acceptance(self):
        for field, value in (("answer", "secret"), ("expectedValue", 5000), ("condition_verbatim", "secret")):
            bad = self.fixture()
            bad[field] = value
            with self.assertRaises(ValueError):
                public.suite_runs([bad])
        for mutate in (
            lambda v: v.update(accepted=True),
            lambda v: v["counts"].update(blocked=0),
            lambda v: v["failureCounts"].update(nativeAcceptance=7),
            lambda v: v.update(conditionCount=84.0),
            lambda v: v.update(submittedQuestions=True),
        ):
            bad = self.fixture()
            mutate(bad)
            with self.assertRaises(ValueError):
                public.suite_runs([bad])

    def test_context_na_is_explicit_and_keeps_all84_conditions(self):
        run = self.fixture()
        run.update(id="context-published-mcp", submittedQuestions=10, preblockedQuestions=0)
        run["counts"] = {"pass": 39, "fail": 38, "executionUnverified": 4, "blocked": 0, "notApplicable": 3}
        run["failureCounts"] = {"content": 31, "nativeAcceptance": 7}
        run["notApplicableReason"] = {"ja": "選択された回答branchでは3条件が非該当。", "en": "Three conditions are inapplicable to the recorded answer branches."}
        checked = public.suite_runs([run])[0]
        self.assertEqual(84, sum(checked["counts"].values()))
        self.assertEqual(3, checked["counts"]["notApplicable"])
        self.assertFalse(checked["accepted"])
        missing = copy.deepcopy(run)
        del missing["notApplicableReason"]
        with self.assertRaises(ValueError):
            public.suite_runs([missing])
        mixed = copy.deepcopy(run)
        mixed["nativeUiDiagnosticCreditedAsMcpExecution"] = True
        with self.assertRaises(ValueError):
            public.suite_runs([mixed])

    def test_legacy_zero_na_and_reviewed_applicability_are_not_denominator_shortcuts(self):
        legacy = self.fixture()
        del legacy["counts"]["notApplicable"]
        self.assertEqual(0, public.suite_runs([legacy])[0]["counts"]["notApplicable"])
        accepted = self.fixture()
        accepted.update(submittedQuestions=10, preblockedQuestions=0, independentExecutionTraces=10, freshBackendProof=True, accepted=True)
        accepted["counts"] = {"pass": 81, "fail": 0, "executionUnverified": 0, "blocked": 0, "notApplicable": 3}
        accepted["failureCounts"] = {"content": 0, "nativeAcceptance": 0}
        accepted["notApplicableReason"] = {"ja": "合成fixtureの条件付き3項目。実証結果ではない。", "en": "Three conditional synthetic-fixture checks; not a real result."}
        self.assertEqual(81, public.suite_runs([accepted])[0]["counts"]["pass"])
        accepted["independentExecutionTraces"] = 0
        with self.assertRaises(ValueError):
            public.suite_runs([accepted])
        accepted["independentExecutionTraces"] = 10
        accepted["counts"].update({"pass": 0, "notApplicable": 84})
        with self.assertRaises(ValueError):
            public.suite_runs([accepted])


class NativeCaseAggregateTests(unittest.TestCase):
    def fixture(self):
        run = OriginalSuiteAggregateTests().fixture()
        run.update(
            id="synthetic-native-fixture", submittedQuestions=10, preblockedQuestions=0,
            independentExecutionTraces=8, freshBackendProof=True, accepted=True,
        )
        run["counts"] = {key: 84 if key == "pass" else 0 for key in public.VERDICTS}
        run["failureCounts"] = {"content": 0, "nativeAcceptance": 0}
        required = (
            ["sql"], ["sql"], ["sql"], ["gql"], ["sql", "gql"],
            ["kql"], ["kql"], [], ["sql", "kql", "gql"], [],
        )
        denominators = (7, 6, 6, 11, 14, 10, 8, 7, 8, 7)
        run["caseAggregates"] = [
            {
                "case": f"T{index + 1:02d}",
                "counts": {key: count if key == "pass" else 0 for key in public.VERDICTS},
                "sourceAttempts": len(languages), "successfulSourceExecutions": len(languages),
                "rejectedSourceAttempts": 0, "nativeGate": False,
                "completedNativeResponse": True, "successfulQueryLanguages": languages,
            }
            for index, (count, languages) in enumerate(zip(denominators, required))
        ]
        run["method"] = {
            "surface": "native-ui", "transport": "responses", "stage": "sandbox",
            "runtime": "preview", "recordedModel": "synthetic-model",
            "judgment": "manual-fixed-rubric-offline", "distinctBackendConversationsProven": 10,
            "sourceExecutions": {"sql": 5, "gql": 3, "kql": 3},
            "successfulSourceExecutions": {"sql": 5, "gql": 3, "kql": 3},
            "rejectedSourceAttempts": {"sql": 0, "gql": 0, "kql": 0},
            "causalAbClaimed": False,
        }
        return run

    def test_complete_native_refusals_do_not_require_invented_queries(self):
        checked = public.suite_runs([self.fixture()])[0]
        self.assertTrue(checked["accepted"])
        self.assertEqual(8, checked["independentExecutionTraces"])
        self.assertEqual(0, checked["caseAggregates"][9]["sourceAttempts"])
        self.assertEqual(84, checked["counts"]["pass"])

    def test_dax_execution_family_is_retained_without_rewriting_sql_routes(self):
        run = self.fixture()
        run["accepted"] = False
        case = run["caseAggregates"][2]
        case["successfulQueryLanguages"] = ["dax"]
        for field in ("sourceExecutions", "successfulSourceExecutions"):
            run["method"][field]["sql"] -= 1
            run["method"][field]["dax"] = 1
        run["method"]["rejectedSourceAttempts"]["dax"] = 0
        self.assertEqual(1, public.suite_runs([run])[0]["method"]["sourceExecutions"]["dax"])
        run["accepted"] = True
        with self.assertRaisesRegex(ValueError, "complete execution proof"):
            public.suite_runs([run])

    def test_original_denominators_case_order_and_totals_are_closed(self):
        for mutation in (
            lambda run: run["caseAggregates"].pop(),
            lambda run: run["caseAggregates"][0].update(case="T02"),
            lambda run: run["caseAggregates"][0]["counts"].update(pass_=7),
            lambda run: run["caseAggregates"][0]["counts"].update({"pass": 6}),
            lambda run: run["caseAggregates"][0].update(sourceAttempts=2),
            lambda run: run["method"]["sourceExecutions"].update(sql=6),
            lambda run: run.update(independentExecutionTraces=7),
        ):
            run = self.fixture()
            mutation(run)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                public.suite_runs([run])

    def test_unproved_completion_routes_or_private_fields_cannot_pass(self):
        for mutation in (
            lambda run: run["caseAggregates"][9].pop("completedNativeResponse"),
            lambda run: run["caseAggregates"][9].update(completedNativeResponse=False),
            lambda run: run["caseAggregates"][9].update(completedNativeResponse=1),
            lambda run: run["caseAggregates"][3].update(successfulQueryLanguages=[]),
            lambda run: run["caseAggregates"][4].update(successfulQueryLanguages=["sql", "sql"]),
            lambda run: run["caseAggregates"][0].update(successfulQueryLanguages=[{}]),
            lambda run: run["caseAggregates"][0].update(successfulQueryLanguages=["sql", "dax"]),
            lambda run: run["caseAggregates"][9].update(rawAnswer="private"),
            lambda run: run["caseAggregates"][9].update(nativeGate=True),
            lambda run: run["method"].update(transport="mcp"),
        ):
            run = self.fixture()
            mutation(run)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                public.suite_runs([run])

    def test_attempts_do_not_become_successes_or_traced_slots(self):
        for mutation in (
            lambda run: run["method"].pop("rejectedSourceAttempts"),
            lambda run: run["method"]["successfulSourceExecutions"].update(sql=4),
            lambda run: run["method"]["rejectedSourceAttempts"].update(dax=1),
        ):
            run = self.fixture()
            mutation(run)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                public.suite_runs([run])
        run = self.fixture()
        run["accepted"] = False
        run["method"]["successfulSourceExecutions"] = {"sql": 1, "gql": 1, "kql": 1}
        run["method"]["rejectedSourceAttempts"] = {"sql": 4, "gql": 2, "kql": 2}
        with self.assertRaisesRegex(ValueError, "successfully traced"):
            public.suite_runs([run])


class ReviewedGoldCaptureTests(unittest.TestCase):
    def test_checked_in_subset_is_private_free_and_not_final_course_projection(self):
        directory = ROOT / "docs" / "assets" / "v3-preview-gold-attachments"
        loaded = public.load(directory / "manifest.json", root=ROOT)
        self.assertFalse(loaded["complete"])
        self.assertEqual({"p30-15-attachments", "p30-15-attachment-response"}, set(loaded["captures"]))
        self.assertEqual("observed", loaded["labs"]["copilot-attachments"]["status"])
        self.assertNotEqual(directory / "manifest.json", ROOT / public.DEFAULT_RELATIVE)
        review = json.loads((directory / "capture-review.json").read_text(encoding="utf-8"))
        for row in review["captures"]:
            with self.subTest(capture=row["id"]):
                self.assertTrue(row["originalUnchanged"])
                self.assertTrue(row["onlyDeclaredCropApplied"])
                self.assertFalse(row["uiValuesOrStatesChanged"])
                self.assertFalse(row["internalReasoningContentVisible"])
                self.assertEqual([], row["opaqueMasks"])
                left, top, right, bottom = row["cropBox"]
                with Image.open(directory / row["sanitizedFile"]) as image:
                    self.assertEqual((right - left, bottom - top), image.size)
                    self.assertEqual(row["sanitizedSha256"], private.digest(directory / row["sanitizedFile"]))
                    self.assertFalse(image.info)
                self.assertRegex(row["originalSha256"], r"^[0-9a-f]{64}$")

    def test_checked_in_subset_can_supply_the_shared_model_without_raw_files(self):
        path = ROOT / "docs" / "assets" / "v3-preview-gold-attachments" / "manifest.json"
        _, _, _, _, loaded, metadata = content.build(ROOT, public_evidence_path=path)
        self.assertTrue(loaded["publicProjection"])
        self.assertEqual(2, metadata["currentUICaptures"])
        self.assertFalse(metadata["newDeploymentReadinessCertified"])


class FullHistoricalProjectionTests(unittest.TestCase):
    def test_full_default_projection_preserves_history_and_failure_lanes(self):
        path = ROOT / public.DEFAULT_RELATIVE
        raw = json.loads(path.read_text(encoding="utf-8"))
        loaded = public.load(path, root=ROOT)
        self.assertIn(loaded["freezeStatus"], public.FREEZE_STATUSES)
        self.assertFalse(loaded["complete"])
        self.assertGreaterEqual(len(loaded["captures"]), 23)
        self.assertLessEqual(len({entry["sha256"] for entry in loaded["captures"].values()}), len(loaded["captures"]))
        self.assertIn("p30-15-historical-attachments", loaded["captures"])
        self.assertIn("p30-15-historical-response", loaded["captures"])
        self.assertEqual("failed", loaded["labs"]["copilot-act"]["status"])
        self.assertTrue(loaded["labs"]["copilot-act"]["knownIssue"]["rollbackVerified"])
        self.assertEqual("passed", loaded["labs"]["copilot-additive-entity"]["status"])
        self.assertEqual("add-unbound-keyless-entity", raw["labs"]["copilot-additive-entity"]["intent"]["kind"])
        for ident in ("p30-15-attachments", "p30-15-attachment-response"):
            with Image.open(loaded["captures"][ident]["path"]) as image:
                if image.width < 600:
                    self.assertFalse(loaded["captures"][ident]["completionEvidence"])
        runs = {run["id"]: run for run in loaded["originalSuiteRuns"]}
        for ident, expected in (("main-baseline", (9, 23, 1, 51, 0)), ("static-first", (22, 10, 1, 51, 0)), ("context-published-mcp", (39, 38, 4, 0, 3))):
            self.assertEqual(expected, tuple(runs[ident]["counts"][key] for key in ("pass", "fail", "executionUnverified", "blocked", "notApplicable")))

    def test_full_default_model_needs_no_private_originals_or_overlay(self):
        with patch.object(private, "_private_file", side_effect=AssertionError("No private files allowed")):
            document, _, _, _, loaded, metadata = content.build(ROOT)
        self.assertTrue(loaded["publicProjection"])
        self.assertGreaterEqual(metadata["currentUICaptures"], 23)
        self.assertEqual(metadata["currentUICaptures"] + 6, len(document.figures))
        self.assertEqual((24, 5, 10, 84), tuple(metadata["counts"][key] for key in ("chapters", "appendices", "tests", "conditions")))
        self.assertIn(metadata["releaseFreezeStatus"], public.FREEZE_STATUSES)
        self.assertFalse(metadata["newDeploymentReadinessCertified"])
        self.assertFalse(metadata["allFeaturesPassedClaimed"])


class AdditiveIntentTests(unittest.TestCase):
    def fixture(self):
        return {
            "intent": {"kind": "add-unbound-keyless-entity", "entityName": "PaymentMethod", "propertyName": "PaymentMethodName", "dataType": "string", "keyless": True, "unbound": True},
            "approvedDelta": {"addedParts": ["entities/PaymentMethod.tmdl"], "removedParts": [], "changedExistingParts": ["model.tmdl"], "modelReferencesAdded": ["PaymentMethod"], "newProperties": [{"name": "PaymentMethodName", "dataType": "string"}]},
            "invariants": {name: True for name in private.ADDITIVE_INVARIANTS},
        }

    def test_exact_additive_intent_is_separate_from_metadata_only_invariants(self):
        value = self.fixture()
        value["observedDelta"] = copy.deepcopy(value["approvedDelta"])
        private.validate_additive(value)
        self.assertEqual((
            "lineageIdsPreserved", "entityPropertySetPreserved", "propertyTypesPreserved",
            "keysPreserved", "bindingsPreserved", "inheritancePreserved",
            "sharedPropertyReferencesPreserved", "onlyApprovedMetadataDelta",
        ), private.ACT_INVARIANTS)

    def test_wrong_object_kind_extra_delta_and_lost_existing_parts_fail(self):
        for change in (
            lambda v: v["intent"].update(kind="add-relationship"),
            lambda v: v["observedDelta"]["addedParts"].append("relationships.tmdl"),
            lambda v: v["observedDelta"]["removedParts"].append("entities/Existing.tmdl"),
            lambda v: v["observedDelta"]["modelReferencesAdded"].append("AnotherEntity"),
            lambda v: v["invariants"].update(existingPartsExceptModelByteIdentical=False),
            lambda v: v["invariants"].update(existingIdsTypesKeysBindingsSharedRefsInheritancePreserved=False),
        ):
            value = self.fixture()
            value["observedDelta"] = copy.deepcopy(value["approvedDelta"])
            change(value)
            with self.assertRaises(ValueError):
                private.validate_additive(value)

    def test_additive_pass_still_needs_both_actual_completion_captures(self):
        value = self.fixture()
        value.update(status="passed", reason={"ja": "fixture", "en": "fixture"}, evidenceIds=["plan", "after"], executionAndReadbackObserved=True)
        value["observedDelta"] = copy.deepcopy(value["approvedDelta"])
        required = {key: {"id": key, "lab": "copilot-additive-entity"} for key in ("plan", "after")}
        captures = {key: {"completionEvidence": True} for key in required}
        _, complete = private.validate_labs({"labs": {"copilot-additive-entity": value}}, required, captures)
        self.assertTrue(complete)
        captures["plan"]["completionEvidence"] = False
        with self.assertRaisesRegex(ValueError, "Partial/orientation"):
            private.validate_labs({"labs": {"copilot-additive-entity": value}}, required, captures)

    def test_known_failure_review_does_not_turn_old_act_into_pass(self):
        value = {
            "status": "failed", "reason": {"ja": "既知失敗", "en": "Known failure"},
            "evidenceIds": ["failed"], "executionAndReadbackObserved": True,
            "invariants": {name: name != "sharedPropertyReferencesPreserved" for name in private.ACT_INVARIANTS},
            "knownIssue": {"reviewed": True, "rollbackVerified": True, "failedInvariants": ["sharedPropertyReferencesPreserved"]},
        }
        request = {"failed": {"id": "failed", "lab": "copilot-act"}}
        labs, complete = private.validate_labs({"labs": {"copilot-act": value}}, request, {"failed": {"completionEvidence": True}})
        self.assertTrue(complete)
        self.assertEqual("failed", labs["copilot-act"]["status"])
        with self.assertRaisesRegex(ValueError, "Known-issue"):
            private.validate_labs({"labs": {"copilot-act": value}}, request, {"failed": {"completionEvidence": False}})
        value["status"] = "passed"
        with self.assertRaisesRegex(ValueError, "shared-property"):
            private.validate_labs({"labs": {"copilot-act": value}}, request, {"failed": {"completionEvidence": True}})


if __name__ == "__main__":
    unittest.main()
