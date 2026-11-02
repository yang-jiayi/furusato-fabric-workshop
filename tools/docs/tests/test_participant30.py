"""Participant edition of the v3.0.0 guide: procedure only, no working records or history."""

import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

import validate_preview30 as validator
from furusato_docs import participant30
from furusato_docs import participant30_figures as figures
from furusato_docs import participant30_text as text
from furusato_docs import preview30_content as content
from furusato_docs import preview30_release as release

MANIFEST = ROOT / "workshop" / "v3.0.0-preview" / "provisioning" / "artifact-set.json"


def texts(document):
    for value in validator.model_texts(document):
        yield value
    for section in document.walk():
        for block in section.blocks:
            if block.kind == "figure":
                yield block["alt"]


class ParticipantEditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="participant30-test-")
        cls.addClassCleanup(temporary.cleanup)
        projection = ROOT / release.V300.evidence_relative
        approval = Path(temporary.name) / "release-approval.json"
        approval.write_text(json.dumps({
            "schemaVersion": release.APPROVAL_SCHEMA, "approved": True, "userAuthorized": True,
            "version": "3.0.0", "selectedOriginalSuiteRunId": release.RELEASE_RUN_ID,
            "evidenceProjectionSha256": validator.hashlib.sha256(projection.read_bytes()).hexdigest(),
            "knownLimitationsAcknowledged": True, "originalCounts": dict(release.RELEASE_COUNTS),
        }), encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        binding = {"manifestSha256": "0" * 64, "sourceCommit": manifest["sourceCommit"],
                   "sourceTreeSha256": manifest["sourceTreeSha256"], "workshopVersion": manifest["workshopVersion"],
                   "csvFiles": manifest["csvFiles"], "notebookCount": len(manifest["notebooks"]), "tempRequired": False}
        # Artifact hashes are verified by the release build; this test checks composition only.
        with patch.object(content, "verify_artifact_manifest", return_value=(manifest, binding)):
            cls.document, _, _, _, cls.evidence, cls.metadata = content.build(
                ROOT, release_profile=release.V300, release_approval=approval,
                artifact_manifest_path=MANIFEST, participant_edition=True,
            )

    def test_shape_and_checklists(self):
        sections = self.document.sections
        self.assertEqual(29, len(sections))
        self.assertTrue(self.metadata["participantEdition"])
        for section in sections[:24]:
            numbers = [child.number for child in section.children]
            self.assertEqual([f"{section.chapter}.1", f"{section.chapter}.2"], numbers[:2])
            steps = section.children[1]
            self.assertEqual(section.chapter >= 4, steps.checklist_id is not None, section.number)
        self.assertNotIn("-legacy-", " ".join(s.ident for s in self.document.walk()))

    def test_no_working_records_or_history(self):
        found = {}
        for language in ("ja", "en"):
            prose = " ".join(value.get(language) for value in texts(self.document))
            hits = validator.participant_working_content(prose, self.document, language)
            if hits:
                found[language] = hits
        self.assertEqual({}, found)
        joined = " ".join(value.ja + " " + value.en for value in texts(self.document))
        for phrase in ("76 PASS", "48 PASS", "artifact-set", "sourceCommit", "Temp", "R8", "holdout"):
            self.assertNotIn(phrase, joined)

    def test_step_numbering_continues_around_figures(self):
        for section in self.document.walk():
            if not section.number.endswith(".2") or section.level != 2 or not section.chapter:
                continue
            expected = 1
            for block in section.blocks:
                if block.kind == "list" and block["numbered"]:
                    self.assertEqual(expected, block.get("start", 1), section.number)
                    expected += len(block["items"])
            self.assertGreater(expected, 1, section.number)

    def test_figures_have_participant_captions(self):
        used = self.metadata["participantFigures"]
        self.assertEqual(len(used), len(set(used)))
        self.assertEqual(len(used), len(self.document.figures))
        for ident in used:
            spec = figures.FIGURES[ident]
            for key in ("caption", "alt"):
                self.assertTrue(all(part.strip() for part in spec[key]), ident)
            if not ident.startswith("diagram:") and ident not in participant30.participant_figures():
                self.assertIn(ident, self.evidence["captures"])

    def test_history_illustration_cannot_substitute_for_target_file_evidence(self):
        caption_ja, caption_en = figures.FIGURES["p30-09-native-delivery"]["caption"]
        step = next(step for step in text.CHAPTERS[9]["steps"]
                    if "p30-09-native-delivery" in step.get("figures", []))
        instruction_ja, instruction_en = step["text"]
        self.assertIn("この概要だけでは001の処理", caption_ja)
        self.assertIn("does not verify processing of 001", caption_en)
        self.assertIn("six KPIs", caption_en)
        self.assertIn("/Files/increment/donation_events_001.csv", instruction_en)
        self.assertIn("record the actual activation row", instruction_en)
        self.assertIn("stop without re-uploading", instruction_en)
        self.assertIn("未確認", instruction_ja)
        self.assertIn("再アップロードせずに停止", instruction_ja)
        capture = next(block for block in self.document.figures
                       if block["source_key"] == "p30-09-native-delivery")
        self.assertEqual("participant-capture", capture["source_kind"])
        manifest = participant30.participant_figures()["p30-09-native-delivery"]
        self.assertTrue(manifest["actualUI"])
        self.assertEqual((1469, 593), (manifest["width"], manifest["height"]))
        self.assertEqual(
            "7b78f7761dfa691c2b4a0ad9dfc8b779c436a05728fb426dedf6437bc9ef9353",
            manifest["originalSha256"],
        )

    def test_notebook05_preview_figure_is_plan_only_and_crop_excludes_execution_header(self):
        ident = "pc-11-notebook05-preview"
        caption_ja, caption_en = figures.FIGURES[ident]["caption"]
        alt_ja, alt_en = figures.FIGURES[ident]["alt"]
        manifest = participant30.participant_figures()[ident]

        self.assertEqual([32, 32, 704, 246], manifest["cropBox"])
        self.assertEqual((672, 214), (manifest["width"], manifest["height"]))
        self.assertEqual((1480, 270), (manifest["originalWidth"], manifest["originalHeight"]))
        self.assertEqual(
            "8f3ea3cce01a1a17799da5f2a913f1a5d956435803f6365d2c76bcf039790d7e",
            manifest["originalSha256"],
        )
        self.assertIn("PLAN_SHA256 は使わず", caption_ja)
        self.assertIn("図の PLAN_SHA256", caption_ja)
        self.assertIn("value freshly printed by your own preview", caption_en)
        self.assertIn("Do not reuse the illustrated PLAN_SHA256", caption_en)
        for caption in (caption_ja, caption_en):
            self.assertIn("13", caption)
            self.assertIn("29", caption)
        self.assertNotIn("成功のチェック", alt_ja)
        self.assertNotIn("実行時刻", alt_ja)
        self.assertNotIn("execution tick", alt_en.lower())
        self.assertNotIn("execution time", alt_en.lower())
        self.assertIn("apply", caption_en)
        self.assertIn("Gold updates", caption_en)
        self.assertIn("fresh 3.1 run", caption_en)

    def test_kql_overview_figure_distinguishes_rounded_ingestion_from_today(self):
        ident = "p30-08-kql-overview"
        caption_ja, caption_en = figures.FIGURES[ident]["caption"]
        alt_ja, alt_en = figures.FIGURES[ident]["alt"]
        manifest = participant30.participant_figures()[ident]

        self.assertEqual("p30-08-kql-overview-current.png", manifest["file"])
        self.assertEqual(
            "3e7ac914132d9a100eda22893c2cedc22552bacc77520d5c6ba6c53425138a03",
            manifest["sha256"],
        )
        self.assertEqual((1241, 720), (manifest["width"], manifest["height"]))
        for caption in (caption_ja, caption_en):
            self.assertIn("15K", caption)
            self.assertTrue(any(term in caption.lower() for term in ("exact", "正確")))
            for unavailable_claim in ("OneLakeDisabled", "mirror disabled", "execution tick"):
                self.assertNotIn(unavailable_claim.lower(), caption.lower())
        self.assertIn("3D", caption_ja)
        self.assertIn("3D", caption_en)
        self.assertIn("Rows today は 0", caption_ja)
        self.assertIn("Rows today is 0", caption_en)
        self.assertIn("exact total", caption_en)
        self.assertIn("正確な総数ではなく", caption_ja)
        self.assertIn("source reconciliation", caption_en)
        self.assertIn("source reconciliation", caption_ja)
        self.assertIn("not evidence of a fresh execution", caption_en)
        self.assertIn("実行、新規データの materialization", caption_ja)
        self.assertIn("table mirroring", caption_en)
        for value in (caption_ja, caption_en, alt_ja, alt_en):
            self.assertNotIn("completeDataActivityTracker", value)
        self.assertIn("DonationEvents", alt_en)
        self.assertIn("DonationEvents", alt_ja)
        self.assertIn("3D", alt_en)
        self.assertIn("3D", alt_ja)

    def test_graph_prerequisites_and_stop_guidance_follow_projection_support(self):
        graph = text.CHAPTERS[16]
        intro = " ".join(value for row in graph["intro"] for value in row)
        before = " ".join(value for row in graph["before"] for value in row)
        steps = " ".join(step["text"][1] for step in graph["steps"])
        checks = repr(graph["checks"])

        self.assertIn("narrower source requirements than general Ontology source support", intro)
        self.assertIn("Delta tables from Lakehouses or mirrored databases", intro)
        self.assertIn("bound to semantic models are unsupported", intro)
        self.assertIn("multiple backing tables", intro)
        self.assertIn("generic binding type alone", intro)
        self.assertIn("how-to-use-ontology-graph#limitations", " ".join(graph["links"]))
        self.assertIn("semantic-model binding or multiple backing tables", steps)
        self.assertIn("generic binding display", steps)
        self.assertIn("required entity or relationship is Ineligible", steps)
        self.assertIn("stop new materialization for that scope", steps)
        self.assertIn("independent SQL, KQL and DAX", steps)
        self.assertIn("not supported for Graph projection", checks)
        self.assertNotIn("AzureStorage.DataLake", intro + before + steps + checks)
        self.assertNotIn("DirectLake means", intro + before + steps + checks)

    def test_graph_selection_figure_is_controls_only_and_uses_verified_crop(self):
        ident = "p30-16-eligibility"
        caption_ja, caption_en = figures.FIGURES[ident]["caption"]
        alt_ja, alt_en = figures.FIGURES[ident]["alt"]
        manifest = participant30.participant_figures()[ident]

        self.assertTrue(manifest["actualUI"])
        self.assertEqual("graph-eligibility-controls-crop.png", manifest["file"])
        self.assertEqual(
            "8216fcf88f718a59b843ceb054775f83712bae555ea7e1836d107d1d4d3b0cea",
            manifest["sha256"],
        )
        self.assertEqual((686, 883), (manifest["width"], manifest["height"]))
        self.assertEqual((1372, 883), (manifest["originalWidth"], manifest["originalHeight"]))
        self.assertEqual([0, 0, 686, 883], manifest["cropBox"])
        self.assertEqual("Lab/assets/p30-16-eligibility.png", manifest["originalFile"])
        self.assertEqual(
            "3bc15540e94fe29adca9a564130f23ed3ad96d7e6afffc2705cce3ac0512ff3b",
            manifest["originalSha256"],
        )
        image = participant30.PARTICIPANT_ASSETS / manifest["file"]
        self.assertEqual(manifest["sha256"], hashlib.sha256(image.read_bytes()).hexdigest())

        for caption in (caption_ja, caption_en):
            self.assertTrue(any(term in caption for term in ("Status", "status")))
        self.assertIn("現在の適格性の証拠ではありません", caption_ja)
        self.assertIn("not current eligibility evidence", caption_en)
        for alt in (alt_ja, alt_en):
            self.assertIn("Status", alt)
            self.assertNotIn("Eligible", alt)
            self.assertNotIn("適格", alt)

        graph_step = text.CHAPTERS[16]["steps"][1]
        self.assertIn("必須範囲の Status を実行時に確認", graph_step["text"][0])
        self.assertIn("Check Status for your own required scope", graph_step["text"][1])
        self.assertIn("select only Eligible items", graph_step["text"][1])

    def test_protected_evaluation_questions_are_complete(self):
        appendix_c = next(s for s in self.document.sections if s.appendix == "C")
        questions = [child for child in appendix_c.children if re.search(r"\bT\d\d\b", child.title.ja)]
        self.assertEqual(10, len(questions))
        self.assertEqual(84, self.metadata["counts"]["conditions"])
        overview = next(b for b in appendix_c.children[0].blocks if b.kind == "table")
        expected = {row[2].ja for row in overview["rows"]}
        shown = {b["text"].ja if hasattr(b["text"], "ja") else b["text"]
                 for s in questions for b in s.blocks if b.kind in {"callout", "code"}}
        self.assertEqual(expected, expected & shown)
        for section in questions:
            self.assertIn("table", [b.kind for b in section.blocks], section.number)

    def test_text_module_covers_every_chapter_and_appendix(self):
        self.assertEqual(set(range(1, 25)), set(text.CHAPTERS))
        self.assertEqual(set("ABCDE"), set(text.APPENDICES))
        self.assertEqual(set(range(1, 25)), set(text.CHAPTER_TITLES))
        self.assertEqual(participant30.TAGLINE.keys(), {"ja", "en"})

    def test_calibration_uses_existing_measure_definitions(self):
        model = ROOT / "workshop/v3.0.0-preview/powerbi/Furusato_Analytics.SemanticModel/definition/tables/寄附.tmdl"
        definitions = dict(re.findall(r"^\s*measure ([^=\n]+?)\s*=\s*(.+)$", model.read_text(encoding="utf-8"), re.MULTILINE))
        examples = "\n".join(step["code"][1] for step in text.CHAPTERS[12]["steps"] if "code" in step)
        for name in ("静的寄附件数", "受入増分寄附件数"):
            self.assertIn(f"[{name}] = {definitions[name]}", examples)

    def test_standard_route_keeps_one_ontology_and_retains_execution_boundaries(self):
        procedures = " ".join(step["text"][1] for chapter in text.CHAPTERS.values() for step in chapter["steps"])
        for obsolete in ("create a separate ontology for this lab", "Create an empty ontology for this chapter",
                         "Import the exported file into another new, empty ontology", "ONT_Furusato_Relationships_<PID>"):
            self.assertNotIn(obsolete, procedures)
        agent = " ".join(step["text"][1] for step in text.CHAPTERS[17]["steps"])
        self.assertIn("measured-contract-20261015", agent)
        self.assertIn("bronze.donation_events_raw", agent)
        calibration = " ".join(step["text"][1] for step in text.CHAPTERS[19]["steps"])
        self.assertIn("12 AM=00, 12 PM=12", calibration)
        self.assertIn("Retain execution failures", calibration)
        self.assertIn("Do not resubmit questions", calibration)


if __name__ == "__main__":
    unittest.main()
