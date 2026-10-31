"""Guard the current participant entrypoint and complete GitHub-native Lab navigation."""
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]


class DisclosureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = self.maximum_depth = self.opened = self.closed = self.summaries = 0
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag == "details":
            self.depth += 1
            self.opened += 1
            self.maximum_depth = max(self.maximum_depth, self.depth)
            if "open" in dict(attrs):
                self.errors.append("English should start collapsed")
        if tag == "summary":
            self.summaries += 1
            if self.depth != 1:
                self.errors.append("Summary must belong to its disclosure")

    def handle_endtag(self, tag):
        if tag == "details":
            self.depth -= 1
            self.closed += 1
            if self.depth < 0:
                self.errors.append("Unmatched disclosure end")


class ReadmePresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "README.md").read_text("utf-8")
        cls.lab = ROOT / "Lab"

    def test_current_entrypoint_links_complete_lab_and_standalone_html(self):
        for target in ("Lab/README.md", "docs/furusato-workshop-v3-0-0-complete.html",
                       "docs/Furusato_Workshop_v3.0.0_current.zip", "docs/README.md"):
            self.assertIn(f"]({target})", self.text)
        self.assertNotRegex(self.text, r"\.docx|tuning-20|validation-20|reference-run|76 PASS|48 PASS")
        self.assertIn("24章・5付録", self.text)
        self.assertNotRegex(self.text, r"<(?:script|style|iframe)\b|\bonclick\s*=\s*", re.I)

    def test_navigation_reaches_all_chapters_appendices_and_capture_pages(self):
        index = (self.lab / "README.md").read_text()
        chapters = sorted(path for path in self.lab.iterdir() if path.is_dir() and (path / "README.md").exists())
        self.assertEqual(29, len(chapters))
        self.assertEqual(list(range(1, 25)), sorted(int(path.name[:2]) for path in chapters if path.name[:2].isdigit()))
        self.assertEqual(set("abcde"), {path.name.split("-")[1] for path in chapters if path.name.startswith("appendix-")})
        for directory in chapters:
            self.assertIn(f"]({directory.name}/README.md)", index)
            contents = (directory / "README.md").read_text()
            pages = set(re.findall(r"\]\(([^)]+\.md)\)", contents)) - {"../README.md"}
            expected = {path.name for path in directory.glob("*.md") if path.name != "README.md"}
            self.assertEqual(expected, pages, directory)
            self.assertTrue(expected, directory)
        for target in re.findall(r"\]\((Lab/[^)#]+\.md)\)", self.text):
            self.assertTrue((ROOT / target).is_file(), target)

    def test_bilingual_procedures_are_balanced_accessible_disclosures(self):
        pages = list(self.lab.glob("*/*.md"))
        operation_pages = [path for path in pages if path.name != "README.md"]
        self.assertGreater(len(operation_pages), 150)
        for path in operation_pages:
            text = re.sub(r"(`{3,})[^\n]*\n.*?\n\1", "", path.read_text(), flags=re.S)
            parser = DisclosureParser()
            parser.feed(text)
            self.assertFalse(parser.errors, path)
            self.assertEqual((0, 1, 1, 1, 1), (parser.depth, parser.maximum_depth,
                             parser.opened, parser.closed, parser.summaries), path)
            self.assertIn("<summary>English</summary>", text)

    def test_accuracy_and_data_boundaries_remain_visible(self):
        for marker in ("有効な容量", "必要な権限", "同じ回答精度を保証するわけではありません",
                       "合成データ", "母集団と粒度が異なる", "Code Interpreter"):
            self.assertIn(marker, self.text)
        for marker in ("Matching a configuration does not guarantee", "synthetic training material",
                       "static donations must remain distinct"):
            self.assertIn(marker, self.text)
        self.assertNotRegex(self.text, r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b")

    def test_active_architecture_is_local_and_matches_approved_asset_bytes(self):
        relative = "Lab/assets/pc-01-architecture.png"
        self.assertRegex(self.text, rf"!\[[^\]\n]+\]\({re.escape(relative)}\)")
        manifest = json.loads((ROOT / "docs/assets/v3.0.0-participant/manifest.json").read_text())
        entry = next(item for item in manifest["figures"] if item["id"] == "pc-01-architecture")
        path = ROOT / relative
        self.assertEqual(entry["sha256"], sha256(path.read_bytes()).hexdigest())
        self.assertEqual((ROOT / "docs/assets/v3.0.0-participant" / entry["file"]).read_bytes(), path.read_bytes())
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            self.assertGreaterEqual(image.width, 600)
            self.assertGreaterEqual(image.height, 250)


if __name__ == "__main__":
    unittest.main()
