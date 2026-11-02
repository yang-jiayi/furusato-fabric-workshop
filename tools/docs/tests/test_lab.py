"""Current Lab keeps the full participant procedure and rejects damaged exports."""
from __future__ import annotations

from pathlib import Path
import json
import re
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

    def test_selection_contract_is_a_bilingual_source_ordered_field_list(self):
        ident = lab.SELECTION_CONTRACT_BLOCK_ID
        page = next(p for p in self.receipt["pagesCoverage"] if ident in p["sourceBlockIds"])
        content = (self.out / page["path"]).read_text(encoding="utf-8")
        block = next(b for s in self.model[0].walk() for i, b in enumerate(s.blocks)
                     if f"{s.ident}:{i}" == ident)
        profile = lab.PROFILE_REL.as_posix()
        reference = f"{profile}/selection-contract.json"

        self.assertIn(f"**Readable field list — source order from `{reference}`**", content)
        self.assertNotIn("| Source kind |", content)
        for language, record_label in (("ja", "レコード"), ("en", "Record")):
            numbers = [int(value) for value in re.findall(
                rf"<strong>{record_label} (\d+)</strong><br>", content
            )]
            self.assertEqual(list(range(1, len(block["rows"]) + 1)), numbers)
            for value in block["headers"] + [cell for row in block["rows"] for cell in row]:
                expected = lab.prose(value, language, ident, table=True, canonical=True)
                self.assertIn(expected, content)
            description_index = next(
                index for index, value in enumerate(block["headers"])
                if value.get(language) in ("Description", "説明")
            )
            description_label = block["headers"][description_index].get(language)
            empty_descriptions = sum(not row[description_index].get(language) for row in block["rows"])
            self.assertGreater(empty_descriptions, 0)
            self.assertEqual(
                empty_descriptions,
                len(re.findall(rf"<strong>{re.escape(description_label)}:</strong>(?=\n</p>)", content)),
            )

    def test_readable_instruction_and_prompt_views_keep_canonical_literals(self):
        pages = {ident: (self.out / page["path"]).read_text(encoding="utf-8")
                 for page in self.receipt["pagesCoverage"]
                 for ident in page["sourceBlockIds"]}
        sources = {f"{s.ident}:{i}": b for s in self.model[0].walk()
                   for i, b in enumerate(s.blocks)}
        profile = lab.PROFILE_REL.as_posix()

        global_id = "ch-17-8:1"
        global_text = pages[global_id]
        global_source = sources[global_id]["text"]
        global_ref = f"{profile}/global-instructions.txt"
        self.assertIn(f"**Readable instruction view — `{global_ref}` (`global instructions`)**",
                      global_text)
        self.assertIn(lab.readable_literal(global_source), global_text)
        self.assertIn(global_source, global_text)

        source_id = "ch-17-9:1"
        source_page = pages[source_id]
        source_block = sources[source_id]["text"]
        source_values = json.loads(source_block)
        source_ref = f"{profile}/source-instructions.json"
        for name in ("kusto", "lakehouse_tables", "semantic_model"):
            field = f"{name}.instructions"
            value = source_values[name]["instructions"]
            self.assertIn(f"**Readable instruction view — `{source_ref}` (`{field}`)**",
                          source_page)
            self.assertIn(lab.readable_literal(value), source_page)
        self.assertIn(source_block, source_page)

        definition_paths = {
            "ch-17-12:8": "definition/kusto.json",
            "ch-17-12:9": "definition/lakehouse_tables.json",
            "ch-17-12:11": "definition/semantic_model.json",
            "ch-17-12:12": "definition/stage_config.json",
        }
        for ident, path in definition_paths.items():
            content = pages[ident]
            source = sources[ident]["text"]
            definition = json.loads(source)
            key = "aiInstructions" if "aiInstructions" in definition else "dataSourceInstructions"
            reference = f"{profile}/{path}"
            self.assertIn(f"**Readable instruction view — `{reference}` (`{key}`)**", content)
            self.assertIn(lab.readable_literal(definition[key]), content)
            self.assertIn(source, content)

        ontology_page = pages["ch-17-12:10"]
        self.assertNotIn(f"**Readable instruction view — `{profile}/definition/ontology.json`",
                         ontology_page)
        self.assertIn(sources["ch-17-12:10"]["text"], ontology_page)

        prompt_ids = [ident for ident, block in sources.items() if block.kind == "prompt"]
        self.assertTrue(prompt_ids)
        for ident in prompt_ids:
            content = pages[ident]
            prompt = sources[ident]["text"]
            for language, label in (("ja", "日本語"), ("en", "English")):
                literal = prompt.get(language)
                self.assertIn(f"**Readable prompt — {label}**", content)
                self.assertIn(lab.readable_literal(literal), content)
                self.assertIn(literal, content)

    def test_long_non_json_code_gets_a_wrapping_view_and_verbatim_copy(self):
        pages = {ident: (self.out / page["path"]).read_text(encoding="utf-8")
                 for page in self.receipt["pagesCoverage"]
                 for ident in page["sourceBlockIds"]}
        sources = {f"{s.ident}:{i}": b for s in self.model[0].walk()
                   for i, b in enumerate(s.blocks)}
        checked = []
        for ident, block in sources.items():
            if block.kind != "code":
                continue
            label = block.get("language")
            label = label.get("en") if hasattr(label, "get") else str(label or "")
            if ("json" in label.lower() or
                    max(map(len, block["text"].splitlines()), default=0) <= lab.READABLE_CODE_LINE_LIMIT):
                continue
            content = pages[ident]
            self.assertIn(lab.readable_literal(block["text"]), content)
            self.assertIn(block["text"], content)
            checked.append(ident)
        self.assertIn("ch-9-2:1", checked)
        self.assertGreaterEqual(len(checked), 5)

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
