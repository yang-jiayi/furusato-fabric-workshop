"""Source fidelity and usable copy blocks for the participant tuning procedure.

These checks render real OOXML/HTML locally. They neither contact Fabric nor
claim that a matching configuration guarantees the historical answer score.
"""

import ast
import copy
import csv
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

from lxml import etree, html

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/docs"), str(ROOT / "tools/html"),
               str(ROOT / "tools/data-agent")]

import build_preview30 as builder
import validate_preview30 as validator
from furusato_docs import participant30_tuning as tuning
from furusato_docs import participant30_evaluation as evaluation
from furusato_docs import preview30_release as release
from furusato_docs.oox import StyleCarrier
from furusato_html.model import Block, Document, Section, Text
from furusato_html.render import RenderContext, render_block
from standard_contract_restoration import _answer_values_in
import native_evaluation


def chapter(number):
    return Section(ident=f"ch-{number}", level=1, number=str(number),
                   title=Text("参加者手順", "Participant procedure"), chapter=number)


def code_blocks(section):
    return [block for block in section.iter_blocks() if block.kind == "code"]


class ParticipantSelfServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tuning = chapter(17)
        cls.counts = tuning.append_tuning_sections(cls.tuning, ROOT)
        cls.document = Document([cls.tuning], [], [], [])
        cls.profile = ROOT / tuning.PROFILE_REL
        cls.instructions = {
            filename: (cls.profile / filename).read_text(encoding="utf-8").strip()
            for filename in ("global-instructions.txt", "lakehouse-instructions.txt",
                             "kusto-instructions.txt", "semantic-model-instructions.txt")
        }
        cls.examples = json.loads((cls.profile / "kusto-examples.json").read_text(encoding="utf-8"))["examples"]
        cls.selections = json.loads((cls.profile / "selection-contract.json").read_text(encoding="utf-8"))["sources"]
        cls.codes = code_blocks(cls.tuning)
        cls.code_texts = [block["text"] for block in cls.codes]

    def test_all_four_instruction_fields_are_complete_unmodified_and_fit_service_limit(self):
        instruction_blocks = [b for b in self.codes if b["language"].en == "instructions"]
        self.assertEqual(4, len(instruction_blocks))
        self.assertCountEqual(self.instructions.values(), [b["text"] for b in instruction_blocks])
        for filename, body in self.instructions.items():
            with self.subTest(filename=filename):
                self.assertEqual(1, self.code_texts.count(body))
                self.assertLessEqual(len(body.encode("utf-16-le")) // 2, 10000)
                self.assertEqual([], _answer_values_in(body))
        legacy = (self.profile / "ontology-instructions.txt").read_text(encoding="utf-8").strip()
        self.assertNotIn(legacy, self.code_texts)

    def test_kql_questions_and_queries_keep_every_original_pair_and_order(self):
        section = next(s for s in self.tuning.walk() if s.number == "17.12")
        actual = [(b["language"].en, b["text"]) for b in code_blocks(section)]
        expected = []
        for example in self.examples:
            expected.extend((("question", example["question"]), ("KQL", example["query"])))
        self.assertEqual(9, len(self.examples))
        self.assertEqual(expected, actual)

    def test_sql_selection_tables_cover_exactly_the_seventeen_objects_and_143_columns(self):
        section = next(s for s in self.tuning.walk() if s.number == "17.7")
        tables = [b for b in section.blocks if b.kind == "table"]
        objects = [n for n in self.selections["lakehouse_tables"]
                   if n["type"] in {"lakehouse_tables.table", "lakehouse_tables.view"}]
        self.assertEqual(17, len(objects))
        self.assertEqual(17, len(tables))
        self.assertEqual(143, sum(len(table["rows"]) for table in tables))
        for node, table in zip(objects, tables):
            path = node["path"]
            with self.subTest(object=path):
                self.assertTrue(table["caption"].en.startswith(path[1] + "." + path[-1] + ":"))
                expected = [(c["path"][-1], c["dataType"]) for c in self.selections["lakehouse_tables"]
                            if c["type"] == "lakehouse_tables.column" and c["path"][:-1] == path]
                for language in ("ja", "en"):
                    self.assertEqual(expected, [tuple(cell.get(language) for cell in row) for row in table["rows"]])

    def test_all_view_creation_and_schema_inventory_queries_are_included_verbatim(self):
        section = next(s for s in self.tuning.walk() if s.number == "17.6")
        expected = [(ROOT / relative).read_text(encoding="utf-8").strip() for relative in tuning.VIEW_RELS]
        expected.append((self.profile / "sql-schema-inventory.sql").read_text(encoding="utf-8").strip())
        self.assertEqual(6, len(tuning.VIEW_RELS))
        self.assertEqual(expected, [b["text"] for b in code_blocks(section)])

    def test_kql_columns_and_source_descriptions_match_canonical_sources(self):
        kql_section = next(s for s in self.tuning.walk() if s.number == "17.11")
        columns = [n for n in self.selections["kusto"] if n["type"] == "kusto.column"]
        self.assertEqual(10, len(columns))
        table = next(b for b in kql_section.blocks if b.kind == "table")
        self.assertEqual([(n["path"][-1], n["dataType"]) for n in columns],
                         [tuple(c.en for c in row) for row in table["rows"]])
        descriptions = json.loads((self.profile / "source-descriptions.json").read_text(encoding="utf-8"))
        section = next(s for s in self.tuning.walk() if s.number == "17.14")
        self.assertEqual([descriptions[k] for k in ("lakehouse_tables", "kusto", "semantic_model")],
                         [b["text"] for b in code_blocks(section)])

    def test_all_ten_dax_definitions_match_the_shipped_model_without_new_measures(self):
        compiler = ast.parse((ROOT / "tools/data-agent/measured_contract_profile.py").read_text(encoding="utf-8"))
        definitions = next(ast.literal_eval(n.value) for n in compiler.body
                           if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MEASURES" for t in n.targets))
        model = (ROOT / "workshop/v3.0.0-preview/powerbi/Furusato_Analytics.SemanticModel/definition/tables/寄附.tmdl").read_text(encoding="utf-8")
        actual_model = {name.strip().strip("'"): value.strip() for name, value in
                        re.findall(r"^\s*measure (.+?)\s*=\s*(.+)$", model, re.MULTILINE)}
        self.assertEqual(10, len(definitions))
        self.assertEqual(definitions, actual_model)
        shown = [b["text"] for b in self.codes if b["language"].en == "DAX"]
        self.assertEqual([name + " = " + expression for name, expression in definitions.items()], shown)

    def test_modified_source_profile_is_rejected_before_documenting_it(self):
        with tempfile.TemporaryDirectory(prefix="participant-profile-tamper-") as directory:
            root = Path(directory)
            profile = root / tuning.PROFILE_REL
            shutil.copytree(self.profile, profile)
            with (profile / "global-instructions.txt").open("a", encoding="utf-8") as output:
                output.write("\nUnreviewed change\n")
            with self.assertRaisesRegex(ValueError, "source hash mismatch"):
                tuning.append_tuning_sections(chapter(17), root)

    def test_only_exact_attributed_literals_are_exempt_from_work_log_guard(self):
        canonical = list(validator.canonical_literals(self.document, "en"))
        self.assertTrue(canonical)
        for body in self.instructions.values():
            with self.subTest(instruction=body[:45]):
                self.assertIn(body, canonical)
                self.assertEqual([], validator.participant_working_content("\n".join(body.split()), self.document, "en"))
        quoted = next(value for value in canonical if validator.working_content(value))
        altered = "ALTERED_LITERAL " + quoted[1:]
        self.assertTrue(validator.participant_working_content(altered, self.document, "en"))
        self.assertIn("source commit", validator.participant_working_content(
            quoted + "\nUnrelated source commit: 1234567890", self.document, "en"))
        self.assertIn("76 PASS / 8 FAIL", validator.participant_working_content(
            quoted + "\n76 PASS / 8 FAIL", self.document, "ja"))
        unmarked = copy.deepcopy(self.document)
        for section in unmarked.walk():
            for block in section.blocks:
                block.payload.pop("canonicalLiteral", None)
        self.assertTrue(validator.participant_working_content(quoted, unmarked, "en"))

    def test_source_code_survives_actual_word_xml_and_html_copy_targets(self):
        # Use the release renderer with real source-bound code blocks. This is a
        # local structural fixture, not a release approval or page-layout claim.
        model = Document([Section("code-check", 1, "17", Text("コピー確認", "Copy check"),
                                  blocks=copy.deepcopy(self.codes), chapter=17)], [], [], [])
        with tempfile.TemporaryDirectory(prefix="participant-code-preservation-") as directory:
            work = Path(directory)
            target = work / "guide.docx"
            builder.write_word(model, None, StyleCarrier.resolve(ROOT), {"captures": {}},
                               {"version": release.PREVIEW.version, "contentSha256": "0" * 64,
                                "participantEdition": True}, target, work,
                               release_profile=release.PREVIEW, word_navigation="headings")
            with zipfile.ZipFile(target) as archive:
                doc = etree.fromstring(archive.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = ["".join(p.xpath(".//w:t/text()", namespaces=ns))
                          for p in doc.xpath("//w:p", namespaces=ns)]
            word_text = "\n".join(paragraphs)
            for block in self.codes:
                with self.subTest(word=block["text"][:50]):
                    self.assertIn(block["text"], word_text)

        context = RenderContext(ui={"copy.aria": {"ja": "コピー", "en": "Copy"},
                                    "copy.label": {"ja": "コピー", "en": "Copy"}},
                                assets=None, version="test", fingerprint="test", runtime_fingerprint="",
                                facts=None, context=SimpleNamespace(), stats={})
        counter = {"code": 0}
        markup = "<main>" + "".join(render_block(b, context, counter) for b in self.codes) + "</main>"
        page = html.fromstring(markup)
        nodes = page.xpath("//pre/code")
        self.assertEqual(self.code_texts, [node.text_content() for node in nodes])
        self.assertEqual([node.get("id") for node in nodes],
                         page.xpath("//button/@data-copy-target"))

    def test_canonical_table_punctuation_is_preserved_without_relaxing_ordinary_typography(self):
        blocks = [Block("table", {"number": 1, "caption": Text("比較", "Comparison"),
                  "headers": [Text("項目", "Field"), Text("値", "Value")],
                  "rows": [[Text("原文（固定）", "原文（固定）"), Text("条件（全文）", "条件（全文）")]],
                  "canonicalLiteral": True}),
                  Block("paragraph", {"text": Text("通常（説明）", "Ordinary（prose）")})]
        model = Document([Section("literal-check", 1, "17", Text("比較", "Comparison"), blocks=blocks)], [], [], [])
        with tempfile.TemporaryDirectory(prefix="participant-table-literals-") as directory:
            work = Path(directory)
            target = work / "guide.docx"
            builder.write_word(model, None, StyleCarrier.resolve(ROOT), {"captures": {}},
                               {"version": release.PREVIEW.version, "contentSha256": "0" * 64,
                                "participantEdition": True}, target, work,
                               release_profile=release.PREVIEW, word_navigation="headings")
            with zipfile.ZipFile(target) as archive:
                tree = etree.fromstring(archive.read("word/document.xml"))
            values = tree.xpath("//w:t/text()", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
            self.assertIn("原文（固定）", values)
            self.assertIn("条件（全文）", values)
            self.assertIn("通常(説明)", values)
            self.assertNotIn("通常（説明）", values)
        context = RenderContext(ui={"table.label": {"ja": "表", "en": "Table"},
                                    "table.scroll": {"ja": "スクロール", "en": "Scroll"}},
                                assets=None, version="test", fingerprint="test", runtime_fingerprint="",
                                facts=None, context=SimpleNamespace(), stats={})
        text = html.fromstring("<main>" + "".join(render_block(b, context, {"code": 0}) for b in blocks) + "</main>").text_content()
        self.assertIn("原文（固定）", text)
        self.assertIn("条件（全文）", text)
        self.assertIn("通常(説明)", text)
        self.assertNotIn("通常（説明）", text)

    def test_parentheses_validation_exempts_only_canonical_body_text(self):
        quoted = "原文（固定された指示）"
        block = Block("code", {"text": quoted, "language": Text("text", "text"), "canonicalLiteral": True})
        model = Document([Section("literal", 1, "17", Text("手順", "Steps"), blocks=[block])], [], [], [])
        namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

        def parts(*values):
            tree = etree.Element("{" + namespace + "}document", nsmap={"w": namespace})
            for value in values:
                etree.SubElement(tree, "{" + namespace + "}t").text = value
            return {"word/document.xml": etree.tostring(tree)}

        good = validator.old.Report(target="canonical punctuation test")
        validator.check_participant_parentheses(parts(quoted, "通常(説明)"), model, good)
        self.assertTrue(good.passed)
        for value in ("通常（説明）", quoted.replace("固定された", "変更された")):
            # A changed literal must not acquire an exception merely because it
            # includes the same technical term or shares its trailing words.
            bad = validator.old.Report(target="unquoted punctuation test")
            validator.check_participant_parentheses(parts(quoted, value), model, bad)
            self.assertFalse(bad.passed)
        header = parts(quoted)
        header["word/header1.xml"] = parts("別の（ヘッダー）")["word/document.xml"]
        report = validator.old.Report(target="other story punctuation test")
        validator.check_participant_parentheses(header, model, report)
        self.assertFalse(report.passed)


class ParticipantEvaluationMaterialsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT / evaluation.ASSET_RELATIVE
        cls.suite = evaluation.load_suite(ROOT)
        cls.cases = cls.suite["original"]["cases"] + cls.suite["regression"]["cases"]
        cls.appendix = Section("appendix-c", 1, "C", Text("評価", "Evaluation"), appendix="C")
        evaluation.append_rubric_sections(cls.appendix, ROOT)

    def rows(self, name):
        return list(csv.DictReader(io.StringIO((self.root / name).read_text(encoding="utf-8-sig"))))

    def test_distributed_suite_and_assets_reproduce_the_unchanged_public_sources(self):
        self.assertEqual(native_evaluation.original_suite(ROOT), self.suite["original"])
        regression = json.loads((ROOT / "tools/data-agent/regression/extended-suite.json").read_text(encoding="utf-8"))
        self.assertEqual(regression, self.suite["regression"])
        for filename, expected in evaluation.build_assets(ROOT).items():
            with self.subTest(asset=filename):
                self.assertEqual(expected, (self.root / filename).read_bytes())
        self.assertTrue(self.suite["publicNotUnseen"])
        self.assertFalse(self.suite["protocol"]["historicalPrivateQuestionsIncluded"])

    def test_questions_and_all_122_unique_rubric_conditions_are_complete_in_both_languages(self):
        self.assertEqual(29, len(self.cases))
        self.assertEqual(29, len(self.appendix.children))
        questions = self.rows("questions.csv")
        rubric = self.rows("rubric.csv")
        self.assertEqual(29, len(questions))
        self.assertEqual(122, len(rubric))
        self.assertEqual(122, len({row["condition_id"] for row in rubric}))
        self.assertEqual([c["question"] for c in self.cases], [r["question_ja"] for r in questions])
        self.assertEqual([(c["id"], condition["id"], condition["text"])
                          for c in self.cases for condition in c["conditions"]],
                         [(r["case_id"], r["condition_id"], r["criterion_ja"]) for r in rubric])
        for case, section in zip(self.cases, self.appendix.children):
            with self.subTest(case=case["id"]):
                self.assertEqual([case["question"]], [b["text"] for b in code_blocks(section)])
                self.assertTrue(code_blocks(section)[0].get("canonicalLiteral"))
                tables = [b for b in section.blocks if b.kind == "table"]
                for language in ("ja", "en"):
                    cells = [cell.get(language) for table in tables for row in table["rows"] for cell in row]
                    self.assertIn(case["expected"], cells)
                    if "query_shape" in case:
                        self.assertIn(case["query_shape"], cells)
                    for condition in case["conditions"]:
                        self.assertIn(condition["id"], cells)
                        self.assertIn(condition["text"], cells)
                    if "expected_values" in case:
                        def leaves(value):
                            if isinstance(value, dict):
                                return [leaf for child in value.values() for leaf in leaves(child)]
                            if isinstance(value, list):
                                return [leaf for child in value for leaf in leaves(child)]
                            return ["null" if value is None else str(value)]
                        self.assertCountEqual(leaves(case["expected_values"]),
                                              [row[1].get(language) for row in tables[-1]["rows"]])

    def test_blank_templates_register_every_49_slot_and_290_condition_per_phase(self):
        slots, conditions = self.rows("slots-template.csv"), self.rows("conditions-template.csv")
        paired = self.rows("paired-template.csv")
        self.assertEqual(98, len(slots))
        self.assertEqual(580, len(conditions))
        self.assertEqual(290, len(paired))
        case_map = {c["id"]: c for c in self.cases}
        expected_keys = {(kind, str(repeat), case["id"], condition["id"])
                         for kind, repeats in (("original", 3), ("regression", 1))
                         for repeat in range(1, repeats + 1)
                         for case in self.suite[kind]["cases"] for condition in case["conditions"]}
        keys = lambda rows: {(r["suite"], r["repeat"], r["case_id"], r["condition_id"]) for r in rows}
        self.assertEqual(expected_keys, keys(paired))
        for phase in ("baseline", "final"):
            phase_slots = [r for r in slots if r["phase"] == phase]
            phase_conditions = [r for r in conditions if r["phase"] == phase]
            self.assertEqual(49, len(phase_slots))
            self.assertEqual(49, len({r["slot_id"] for r in phase_slots}))
            self.assertEqual(290, len(phase_conditions))
            self.assertEqual(expected_keys, keys(phase_conditions))
            for row in phase_slots:
                self.assertEqual(case_map[row["case_id"]]["question"], row["question_ja"])
                self.assertEqual("", row["native_status"])
                self.assertEqual("", row["response_status"])
            for row in phase_conditions:
                self.assertEqual("", row["status"])
                self.assertEqual("", row["private_evidence_file_and_location"])

    def test_evaluation_answers_stay_separate_from_the_four_configuration_fields(self):
        model = chapter(17)
        tuning.append_tuning_sections(model, ROOT)
        instructions = [b["text"] for b in code_blocks(model) if b["language"].en == "instructions"]
        self.assertEqual(4, len(instructions))
        for case in self.cases:
            for body in instructions:
                self.assertNotIn(case["question"], body)
                self.assertNotIn(case["expected"], body)
        for body in instructions:
            self.assertEqual([], _answer_values_in(body))


if __name__ == "__main__":
    unittest.main()
