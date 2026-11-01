import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from furusato_docs.participant_current_tuning import (  # noqa: E402
    _assets,
    append_current_tuning_sections,
    current_chapter_spec,
)
from furusato_docs.participant30_deployment import append_deployment_sections  # noqa: E402
from furusato_html.model import Section, Text  # noqa: E402


class CurrentProfileGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = _assets(ROOT)
        cls.chapter = Section(
            "chapter-17",
            1,
            "17",
            Text("17. Agent", "17. Agent"),
            chapter=17,
        )
        cls.summary = append_current_tuning_sections(cls.chapter, ROOT)

    def test_assets_match_current_experimental_contract(self):
        manifest = self.assets["manifest"]
        self.assertEqual("current-experimental", manifest["profile"])
        self.assertEqual("experimental", manifest["status"])
        self.assertFalse(manifest["answerAccuracyAccepted"])
        self.assertEqual(9_422, self.assets["global_units"])
        self.assertEqual(0, self.assets["active_example_count"])
        self.assertEqual(0, manifest["definitionFewshotFiles"])
        self.assertEqual(5, len(self.assets["definition_files"]))
        self.assertEqual(170, len(self.assets["selection_rows"]))
        self.assertEqual(
            {
                "lakehouse_tables.table": 11,
                "lakehouse_tables.column": 88,
                "kusto.table": 1,
                "kusto.column": 10,
                "semantic_model.table": 5,
                "semantic_model.column": 31,
                "semantic_model.measure": 10,
                "ontology.entity": 10,
            },
            {
                kind: sum(
                    1 for row in self.assets["selection_rows"]
                    if row[2] == kind
                )
                for kind in (
                    "lakehouse_tables.table",
                    "lakehouse_tables.column",
                    "kusto.table",
                    "kusto.column",
                    "semantic_model.table",
                    "semantic_model.column",
                    "semantic_model.measure",
                    "ontology.entity",
                )
            },
        )
        self.assertEqual(
            {"instructions": None, "description": None},
            self.assets["source_instructions"]["ontology"],
        )

    def test_stable_chapter_sections_and_exact_profile_text(self):
        self.assertEqual(
            [f"chapter-17-{index}" for index in range(5, 17)],
            [section.ident for section in self.chapter.children],
        )
        sections = {section.ident: section for section in self.chapter.children}
        global_code = next(
            block["text"]
            for block in sections["chapter-17-8"].blocks
            if block.kind == "code"
        )
        global_block = next(
            block
            for block in sections["chapter-17-8"].blocks
            if block.kind == "code"
        )
        self.assertTrue(global_block.get("canonicalLiteral"))
        self.assertEqual(9_422, len(global_code.encode("utf-16-le")) // 2)
        self.assertEqual(self.assets["global"], global_code)
        source_block = next(
            block
            for block in sections["chapter-17-9"].blocks
            if block.kind == "code"
        )
        self.assertTrue(source_block.get("canonicalLiteral"))
        source_code = source_block["text"]
        self.assertEqual(
            json.dumps(self.assets["source_instructions"], ensure_ascii=False, indent=2),
            source_code,
        )
        self.assertEqual(self.assets["source_instructions"], json.loads(source_code))
        selection_table = next(
            block
            for block in sections["chapter-17-7"].blocks
            if block.kind == "table"
        )
        self.assertTrue(selection_table.get("canonicalLiteral"))
        self.assertEqual(170, len(selection_table["rows"]))
        expected_descriptions = [
            str(item.get("description") or "")
            for entries in self.assets["selection_contract"].values()
            for item in entries
        ]
        self.assertEqual(
            expected_descriptions,
            [row[5].ja for row in selection_table["rows"]],
        )
        template_codes = [
            block["text"]
            for block in sections["chapter-17-12"].blocks
            if block.kind == "code"
        ]
        self.assertEqual(
            [path.read_text(encoding="utf-8") for path in self.assets["definition_files"]],
            template_codes,
        )
        self.assertEqual(0, self.summary["kqlFewshotCount"])

    def test_cli_and_durable_limitations_are_documented(self):
        def strings(value):
            if isinstance(value, Text):
                yield value.ja
                yield value.en
            elif isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child in value.values():
                    yield from strings(child)
            elif isinstance(value, (tuple, list)):
                for child in value:
                    yield from strings(child)

        content = "\n".join(
            part
            for section in self.chapter.children
            for block in section.blocks
            for part in strings(block.payload)
        )
        for action in ("prepare", "apply", "publish", "verify"):
            self.assertIn(f"current_profile.py {action}", content)
        for flag in (
            "--workspace-id $WorkspaceId",
            "--folder-id $FolderId",
            "--agent-id $AgentId",
            "--private-root $PrivateRoot",
            "--routing-origin $RoutingOrigin",
            "--stage draft",
            "--stage published",
        ):
            self.assertIn(flag, content)
        self.assertIn("11:54:30 UTC", content)
        self.assertIn("14:18:14 UTC", content)
        self.assertIn("11:54:30 AM", content)
        self.assertIn("23:54:30", content)
        self.assertIn("2:18:14 PM", content)
        self.assertIn("02:18:14", content)
        self.assertIn("> 57,000", content)
        self.assertIn("KEEPFILTERS", content)
        self.assertIn("false “no data.”", content)
        self.assertNotIn("51-slot", content)
        self.assertNotIn("296-condition", content)
        self.assertNotIn("127", content)
        self.assertNotIn("170→192", content)

    def test_instruction_sections_are_reference_only_until_apply(self):
        sections = {section.ident: section for section in self.chapter.children}
        self.assertIn("review the global instructions", sections["chapter-17-8"].title.en.lower())
        self.assertIn("review source instructions", sections["chapter-17-9"].title.en.lower())
        for ident in ("chapter-17-8", "chapter-17-9"):
            content = " ".join(
                part
                for block in sections[ident].blocks
                if block.kind in {"paragraph", "list", "callout"}
                for part in self._strings(block.payload)
            ).lower()
            self.assertTrue(
                "do not edit the ui field at this step" in content
                or "do not edit ui instructions" in content
            )
            self.assertIn("authorized apply procedure", content)

    def test_current_profile_deployment_handoff_matches_chapter_17(self):
        def chapter():
            return Section(
                "chapter-24",
                1,
                "24",
                Text("24. 配置", "24. Deployment"),
                chapter=24,
            )

        current = chapter()
        append_deployment_sections(current, ROOT, current_profile=True)
        current_text = " ".join(
            part
            for block in current.children[-2].blocks
            for part in self._strings(block.payload)
        )
        self.assertIn("experimental current profile", current_text)
        self.assertNotIn("six SQL views", current_text)
        self.assertNotIn("measured-contract-20261015", current_text)

        historical = chapter()
        append_deployment_sections(historical, ROOT)
        historical_text = " ".join(
            part
            for block in historical.children[-2].blocks
            for part in self._strings(block.payload)
        )
        self.assertIn("six SQL views", historical_text)
        self.assertIn("measured-contract-20261015", historical_text)

    @staticmethod
    def _strings(value):
        if isinstance(value, Text):
            yield value.ja
            yield value.en
        elif isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for child in value.values():
                yield from CurrentProfileGuideTests._strings(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                yield from CurrentProfileGuideTests._strings(child)

    def test_first_four_sections_do_not_reintroduce_historical_tuning(self):
        text = current_chapter_spec()
        joined = " ".join(
            value
            for key in ("intro", "before", "steps", "checks")
            for part in text.get(key, [])
            for value in (part if isinstance(part, tuple) else part.get("text", ()))
            if isinstance(value, str)
        )
        self.assertIn("experimental profile", joined)
        self.assertNotIn("measured-contract-20261015", joined)
        self.assertNotIn("143 columns", joined)
        self.assertNotIn("nine KQL examples", joined)


if __name__ == "__main__":
    unittest.main()
