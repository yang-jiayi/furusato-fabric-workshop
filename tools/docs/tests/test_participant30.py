"""Participant edition of the v3.0.0 guide: procedure only, no working records or history."""

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
        for value in texts(self.document):
            for language in ("ja", "en"):
                hits = validator.working_content(value.get(language))
                if hits:
                    found[value.get(language)[:60]] = hits
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

    def test_protected_evaluation_questions_are_complete(self):
        appendix_c = next(s for s in self.document.sections if s.appendix == "C")
        questions = [child for child in appendix_c.children if re.search(r"\bT\d\d\b", child.title.ja)]
        self.assertEqual(10, len(questions))
        self.assertEqual(84, self.metadata["counts"]["conditions"])
        overview = next(b for b in appendix_c.children[0].blocks if b.kind == "table")
        expected = {row[2].ja for row in overview["rows"]}
        shown = {b["text"].ja for s in questions for b in s.blocks if b.kind == "callout"}
        self.assertEqual(expected, expected & shown)
        for section in questions:
            self.assertIn("table", [b.kind for b in section.blocks], section.number)

    def test_text_module_covers_every_chapter_and_appendix(self):
        self.assertEqual(set(range(1, 25)), set(text.CHAPTERS))
        self.assertEqual(set("ABCDE"), set(text.APPENDICES))
        self.assertEqual(set(range(1, 25)), set(text.CHAPTER_TITLES))
        self.assertEqual(participant30.TAGLINE.keys(), {"ja", "en"})


if __name__ == "__main__":
    unittest.main()
