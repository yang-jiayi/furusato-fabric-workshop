"""Current Lab keeps the full participant procedure and rejects damaged exports."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/docs"), str(ROOT / "tools/html")]

from furusato_docs import lab


class LabExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = lab.load_model(ROOT)
        cls.temporary = tempfile.TemporaryDirectory(prefix="furusato-lab-test-", dir=ROOT)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.out = Path(cls.temporary.name) / "Lab"
        cls.receipt = lab.write_lab(ROOT, cls.out, model=cls.model)

    def validate(self):
        return lab.validate_lab(ROOT, self.out, self.receipt, model=self.model)

    def mutate(self, path, replacement):
        original = path.read_bytes()
        self.addCleanup(path.write_bytes, original)
        path.write_bytes(replacement)

    def test_complete_current_curriculum_and_evaluation_are_present(self):
        result = self.validate()
        self.assertEqual((24, 5), (result["chapters"], result["appendices"]))
        self.assertEqual(84, self.model[-1]["counts"]["conditions"])
        self.assertEqual(10, self.model[-1]["counts"]["tests"])
        self.assertEqual(len([b for s in self.model[0].walk() for b in s.blocks]),
                         result["sourceBlocksChecked"])
        self.assertEqual(len(self.model[0].figures), result["imageFilesVerified"])
        self.assertGreater(result["canonicalCodeAndPromptBlocksChecked"], 90)
        self.assertFalse(result["newDeploymentCaptureClaimed"])

    def test_profile_paths_are_platform_independent(self):
        chapter=self.out/'17-fabric-data-agent-and-code-interpreter'
        prefix='workshop/v3.0.0-preview/data-agent/profiles/current-experimental'
        start=(chapter/'06-17-6-profile-assets-and-preflight.md').read_text(encoding='utf-8')
        instructions=(chapter/'08-17-8-review-the-global-instructions.md').read_text(encoding='utf-8')
        self.assertIn(prefix,start)
        self.assertIn("global-instructions.txt",start)
        self.assertIn("Do not edit the UI field at this step", instructions)
        self.assertNotIn(prefix.replace('/','\\'),start+instructions)

    def test_omitted_japanese_step_is_rejected(self):
        page = next(p for p in self.receipt["pagesCoverage"] if p["section"] == "ch-4-2")
        path = self.out / page["path"]
        block = next(s for s in self.model[0].walk() if s.ident == "ch-4-2").blocks[0]
        text = lab.prose(block["items"][0], "ja", "test")
        self.assertIn(text, path.read_text(encoding="utf-8"))
        self.mutate(path, path.read_text(encoding="utf-8").replace(text, "", 1).encode())
        with self.assertRaises(ValueError):
            self.validate()

    def test_modified_query_or_command_literal_is_rejected(self):
        page = next(p for p in self.receipt["pagesCoverage"] if p["codeBlocks"])
        path = self.out / page["path"]
        blocks = {f"{s.ident}:{i}": b for s in self.model[0].walk() for i, b in enumerate(s.blocks)}
        block = next(blocks[ident] for ident in page["sourceBlockIds"] if blocks[ident].kind == "code")
        changed = path.read_text(encoding="utf-8").replace(block["text"], "CHANGED COMMAND", 2)
        self.mutate(path, changed.encode())
        with self.assertRaises(ValueError):
            self.validate()

    def test_modified_capture_bytes_are_rejected(self):
        image = next(iter(self.receipt["assets"].values()))
        path = self.out / image["file"]
        self.mutate(path, path.read_bytes() + b"changed")
        with self.assertRaises(ValueError):
            self.validate()

    def test_broken_navigation_is_rejected(self):
        path = self.out / "README.md"
        changed = path.read_text(encoding="utf-8").replace("/README.md)", "/missing.md)", 1)
        self.assertNotEqual(changed, path.read_text(encoding="utf-8"))
        self.mutate(path, changed.encode())
        with self.assertRaises(ValueError):
            self.validate()

    def test_retired_current_distribution_reference_is_rejected(self):
        path = self.out / "README.md"
        self.mutate(path, path.read_bytes() + b"\nDownload the Word guide.\n")
        with self.assertRaises(ValueError):
            self.validate()

    def test_bilingual_validation_uses_explicit_utf8(self):
        read_text = Path.read_text

        def read_utf8(path, *args, **kwargs):
            self.assertEqual("utf-8", kwargs.get("encoding"))
            return read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", read_utf8):
            result = self.validate()
        self.assertEqual("passed", result["status"])
        self.assertGreater(result["bilingualTextValuesChecked"], 0)


if __name__ == "__main__":
    unittest.main()
