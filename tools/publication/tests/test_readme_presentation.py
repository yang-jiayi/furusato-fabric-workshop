"""Guard the GitHub-native README layout without changing workshop contracts."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
SVG = "{http://www.w3.org/2000/svg}"


class DisclosureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.maximum_depth = 0
        self.opened = 0
        self.closed = 0
        self.summaries = 0
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag == "details":
            self.depth += 1
            self.opened += 1
            self.maximum_depth = max(self.maximum_depth, self.depth)
            if "open" in dict(attrs):
                self.errors.append("Long sections should start collapsed")
        if tag == "summary":
            self.summaries += 1
            if self.depth != 1:
                self.errors.append("Summary must belong to a top-level disclosure")

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
        cls.markup = re.sub(r"```[^\n]*\n.*?\n```", "", cls.text, flags=re.S)

    def test_disclosures_are_balanced_flat_and_named(self):
        parser = DisclosureParser()
        parser.feed(self.markup)
        self.assertFalse(parser.errors)
        self.assertEqual(parser.depth, 0)
        self.assertEqual(parser.maximum_depth, 1)
        self.assertEqual(parser.opened, parser.closed)
        self.assertEqual(parser.opened, parser.summaries)
        self.assertGreaterEqual(parser.opened, 18)
        for summary in re.findall(r"<summary>(.*?)</summary>", self.markup, flags=re.S):
            self.assertTrue(re.sub(r"<[^>]+>", "", summary).strip())

    def test_navigation_retains_explicit_unique_landmarks(self):
        ids = re.findall(r'<a id="([^"]+)"></a>', self.markup)
        self.assertEqual(len(ids), len(set(ids)))
        for anchor in (
            "top", "ontology-schema-ja", "ontology-schema-en",
            "reference-run-ja", "reference-run-en", "deployment-integrity-checks",
        ):
            self.assertIn(anchor, ids)
            self.assertIn(f"](#{anchor})", self.markup)
        self.assertIn("[日本語](#日本語)", self.markup)
        self.assertIn("[English](#english)", self.markup)

    def test_accuracy_limits_and_safety_remain_visible_when_collapsed(self):
        visible = re.sub(r"<details>.*?</details>", "", self.markup, flags=re.S)
        for marker in (
            "6製品すべての実機デプロイを検証したものではありません",
            "not an end-to-end deployment test of all six clients",
            "### 前提と安全上の境界",
            "### Requirements and boundaries",
            "既存 Workspace 内の空フォルダーへの新規構築",
            "new deployment into an empty folder in an existing workspace",
            "標準所要時間・見積額・次回の上限を保証するものではありません",
            "not a standard duration, a quote or a guaranteed upper bound",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, visible)
        self.assertNotRegex(self.markup, r"<(?:script|style|iframe)\b|\bonclick\s*=")

    def test_hero_is_local_accessible_and_self_contained(self):
        relative = "docs/assets/readme/furusato-hero.svg"
        self.assertRegex(self.text, rf"!\[[^\]\n]+\]\({re.escape(relative)}\)")
        graphic = ET.parse(ROOT / relative).getroot()
        self.assertEqual(graphic.tag, SVG + "svg")
        self.assertEqual(graphic.get("role"), "img")
        ids = {element.get("id"): element for element in graphic.iter() if element.get("id")}
        for label in graphic.get("aria-labelledby", "").split():
            self.assertTrue("".join(ids[label].itertext()).strip())
        self.assertIsNotNone(graphic.find(SVG + "title"))
        self.assertIsNotNone(graphic.find(SVG + "desc"))
        for element in graphic.iter():
            self.assertNotIn(element.tag.removeprefix(SVG), ("script", "foreignObject", "image", "animate"))
            for key, value in element.attrib.items():
                self.assertFalse(key.lower().startswith("on"))
                self.assertNotIn("https://", value)
                self.assertNotIn("http://", value)

    def test_hero_matches_the_released_ontology_shape(self):
        contract = json.loads(
            (ROOT / "workshop" / "v2.7.0" / "participant-workspace-contract.json").read_text("utf-8")
        )
        graphic = ET.parse(ROOT / "docs" / "assets" / "readme" / "furusato-hero.svg").getroot()
        labels = ["".join(node.itertext()).strip() for node in graphic.iter(SVG + "text")]
        ontology = contract["ontology"]
        for label in (
            f"v{contract['packageVersion']}",
            f"{ontology['entityCount']} entities",
            f"{ontology['staticPropertyCount']} static + {ontology['timeseriesPropertyCount']} time-series property",
            f"{ontology['relationshipCount']} relationships",
            "Lakehouse", "Eventhouse", "Ontology", "Data Agent", "Code Interpreter", "TOOL",
        ):
            with self.subTest(label=label):
                self.assertIn(label, labels)


if __name__ == "__main__":
    unittest.main()
