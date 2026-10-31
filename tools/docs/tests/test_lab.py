"""Current Lab keeps the full participant procedure and rejects damaged exports."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/docs"), str(ROOT / "tools/html")]

from furusato_docs import lab


class LabExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = lab.load_model(ROOT)
        cls.temporary = tempfile.TemporaryDirectory(prefix="furusato-lab-test-")
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
        self.assertGreater(result["canonicalCodeAndPromptBlocksChecked"], 100)
        self.assertFalse(result["newDeploymentCaptureClaimed"])

    def test_omitted_japanese_step_is_rejected(self):
        page = next(p for p in self.receipt["pagesCoverage"] if p["section"] == "ch-4-2")
        path = self.out / page["path"]
        block = next(s for s in self.model[0].walk() if s.ident == "ch-4-2").blocks[0]
        text = lab.prose(block["items"][0], "ja", "test")
        self.assertIn(text, path.read_text())
        self.mutate(path, path.read_text().replace(text, "", 1).encode())
        with self.assertRaises(ValueError):
            self.validate()

    def test_modified_query_or_command_literal_is_rejected(self):
        page = next(p for p in self.receipt["pagesCoverage"] if p["codeBlocks"])
        path = self.out / page["path"]
        blocks = {f"{s.ident}:{i}": b for s in self.model[0].walk() for i, b in enumerate(s.blocks)}
        block = next(blocks[ident] for ident in page["sourceBlockIds"] if blocks[ident].kind == "code")
        changed = path.read_text().replace(block["text"], "CHANGED COMMAND", 2)
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
        changed = path.read_text().replace("/README.md)", "/missing.md)", 1)
        self.assertNotEqual(changed, path.read_text())
        self.mutate(path, changed.encode())
        with self.assertRaises(ValueError):
            self.validate()

    def test_retired_current_distribution_reference_is_rejected(self):
        path = self.out / "README.md"
        self.mutate(path, path.read_bytes() + b"\nDownload the Word guide.\n")
        with self.assertRaises(ValueError):
            self.validate()


if __name__ == "__main__":
    unittest.main()
