"""Bilingual participant gates follow current source contracts without relaxing them."""

from __future__ import annotations

import copy
import html
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "html"))

import validate_html as v
from furusato_html.render import bilingual
from sync_i18n import _strings
from validate_html import Report, check_optional_exercise_gate

STATEMENTS = (
    "D.1 から D.5 は、Core の外にある実習です",
    "D.1 through D.5 are exercises outside Core",
    "preview を持つ Notebook / 配置ツールは必ず preview から始めます",
    "Always start Notebooks and deployment tools that support preview in preview mode",
    "Core の成果物を残して、許可された検証範囲で実施してください",
    "retaining Core artifacts and staying within the authorized validation scope",
    "D.6 だけは実習ではありません",
    "D.6 is reference information for understanding evaluation considerations, not an exercise",
)


def parse(raw: str):
    structure = v.Structure()
    structure.feed(raw)
    structure.close()
    if structure.errors:
        raise AssertionError(structure.errors)
    return structure.root


def status_for(report: Report, check: str) -> str:
    matches = [status for status, name, _ in report.results if name == check]
    if len(matches) != 1:
        raise AssertionError((check, matches))
    return matches[0]


def child_index(element) -> int:
    return next(index for index, child in enumerate(element.parent.children) if child is element)


class OptionalExerciseGateTests(unittest.TestCase):
    def test_supported_preview_contract_passes(self):
        report = Report()
        check_optional_exercise_gate(report, "\n".join(STATEMENTS))
        self.assertFalse(report.failures)

    def test_each_required_statement_is_enforced(self):
        for missing in STATEMENTS:
            with self.subTest(missing=missing):
                report = Report()
                check_optional_exercise_gate(
                    report, "\n".join(statement for statement in STATEMENTS if statement != missing)
                )
                self.assertEqual(
                    {check for status, check, _ in report.results if status == "FAIL"},
                    {"content.appendixDGateSplit"},
                )

    def test_old_universal_preview_claim_is_not_a_substitute(self):
        report = Report()
        text = "\n".join(STATEMENTS).replace(
            STATEMENTS[2], "いずれも preview を先に実行します"
        ).replace(STATEMENTS[3], "run preview first")
        check_optional_exercise_gate(report, text)
        self.assertTrue(report.failures)


class ProtocolReferenceTests(unittest.TestCase):
    def test_documentation_and_exact_oauth_audience_are_allowed(self):
        for url in (
            "https://learn.microsoft.com/en-us/fabric/",
            "https://azure.microsoft.com/support/legal/",
            "https://www.microsoft.com/ai/",
            "https://database.windows.net/",
        ):
            with self.subTest(url=url):
                raw = f'<a href="{html.escape(url, quote=True)}">Reference</a>'
                report = Report()
                v.check_no_external_dependencies(report, raw, parse(raw))
                self.assertFalse(report.failures)

    def test_resource_exception_does_not_allow_host_or_uri_variants(self):
        for url in (
            "https://database.windows.net.evil.invalid/",
            "https://database.windows.net@evil.invalid/",
            "https://database.windows.net/extra",
            "https://database.windows.net/?redirect=https://evil.invalid/",
            "https://database.windows.net/?",
            "https://database.windows.net/#fragment",
            "https://database.windows.net/#",
            " https://database.windows.net/?query=1",
            "\nhttps://database.windows.net/#fragment",
            "https://database.windows.net/%2f",
            "https://database.windows.net:443/",
            "https://database.windows.net",
            "http://database.windows.net/",
            "HTTPS://database.windows.net/",
            "//database.windows.net/",
            "https://evil.invalid/",
        ):
            with self.subTest(url=url):
                raw = f'<a href="{html.escape(url, quote=True)}">Reference</a>'
                report = Report()
                v.check_no_external_dependencies(report, raw, parse(raw))
                self.assertEqual(status_for(report, "offline.onlyDocumentationLinks"), "FAIL")

    def test_resource_exception_does_not_allow_remote_dependencies(self):
        raw = '<img src="https://database.windows.net/" alt="Not an offline image">'
        report = Report()
        v.check_no_external_dependencies(report, raw, parse(raw))
        self.assertEqual(status_for(report, "offline.noExternalResources"), "FAIL")


class ParameterCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = v.load_context(ROOT)
        cls.mirror = v.load_mirror()
        tables = []

        def cells(row, tag):
            return "".join(
                f"<{tag}>{bilingual(v.Text(ja=value, en=cls.mirror.get(value)))}</{tag}>"
                for value in row
            )

        for key in sorted(v.CATALOG):
            caption = f"Notebook {key.removeprefix('Notebook_')} のパラメーター仕様（全項目）"
            rows = "".join(
                f'<tr>{cells(row, "td")}</tr>'
                for row in v.build_parameter_rows(cls.context, key)
            )
            tables.append(
                f'<table><caption><span lang="ja">{caption}</span></caption>'
                f'<thead><tr>{cells(v.PARAMETER_COLUMNS, "th")}</tr></thead>'
                f"<tbody>{rows}</tbody></table>"
            )
        cls.fixture = "".join(tables)

    def setUp(self):
        self.root = parse(self.fixture)
        self.tables = dict(zip(sorted(v.CATALOG), v.find(self.root, "table")))

    def check(self):
        report = Report()
        v.check_parameter_catalog(report, self.root, self.context, self.mirror)
        return report

    def parameter_row(self, notebook, name):
        return next(
            row for row in v.find(self.tables[notebook], "tr")
            if row.children and v._language_text(row.children[0], "ja") == name
        )

    def test_full_current_runtime_catalog_passes(self):
        self.assertEqual(
            {key: len(notebook.parameters) for key, notebook in self.context.notebooks.items()},
            {"Notebook_01": 8, "Notebook_02": 7, "Notebook_03": 7, "Notebook_04": 19, "Notebook_05": 10},
        )
        self.assertIs(self.context.notebooks["Notebook_04"].parameters["ENABLE_UNIFIED_DATA_AGENT"], False)
        report = self.check()
        self.assertFalse(report.failures)
        self.assertIn("51/51 runtime parameters", report.results[0][2])

    def test_missing_row_cannot_be_hidden_by_mentions_elsewhere(self):
        row = self.parameter_row("Notebook_04", "ENABLE_AI_REFERENCE_ARCHITECTURE")
        self.root.text += row.all_text()
        del row.parent.children[child_index(row)]
        self.assertEqual(status_for(self.check(), "facts.parameters"), "FAIL")

    def test_duplicate_replacement_fails_even_when_total_count_is_unchanged(self):
        row = self.parameter_row("Notebook_04", "REFERENCE_AGENT_NAME")
        replacement = self.parameter_row("Notebook_04", "REFERENCE_AGENT_ROLE")
        row.parent.children[child_index(row)] = copy.deepcopy(replacement)
        self.assertEqual(status_for(self.check(), "facts.parameters"), "FAIL")

    def test_same_name_cannot_move_between_notebook_roles(self):
        first = self.parameter_row("Notebook_01", "PARTICIPANT_ID")
        fourth = self.parameter_row("Notebook_04", "PARTICIPANT_ID")
        first.parent.children[child_index(first)] = copy.deepcopy(fourth)
        fourth.parent.children[child_index(fourth)] = copy.deepcopy(first)
        self.assertEqual(status_for(self.check(), "facts.parameters"), "FAIL")

    def test_default_and_role_columns_are_checked_in_both_languages(self):
        for column in range(1, len(v.PARAMETER_COLUMNS)):
            for language in ("ja", "en"):
                with self.subTest(column=v.PARAMETER_COLUMNS[column], language=language):
                    row = self.parameter_row("Notebook_04", "REFERENCE_AGENT_ROLE")
                    cell = row.children[column]
                    span = next(n for n in cell.walk() if n.attrs.get("lang") == language)
                    original_text, original_children = span.text, span.children
                    span.text, span.children = "incorrect value", []
                    self.assertEqual(status_for(self.check(), "facts.parameters"), "FAIL")
                    span.text, span.children = original_text, original_children

    def test_duplicate_parameter_table_fails(self):
        self.root.children.append(copy.deepcopy(self.tables["Notebook_04"]))
        self.assertEqual(status_for(self.check(), "facts.parameters"), "FAIL")

    def test_catalog_must_cover_every_runtime_notebook_and_parameter(self):
        for catalog in (
            {key: value for key, value in v.CATALOG.items() if key != "Notebook_04"},
            {**v.CATALOG, "Notebook_04": v.CATALOG["Notebook_04"][:-1]},
        ):
            with self.subTest(keys=list(catalog)):
                with patch.object(v, "CATALOG", catalog):
                    self.assertEqual(status_for(self.check(), "facts.parameters"), "FAIL")


class ParticipantMirrorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        context = v.load_context(ROOT)
        facts = v.compute_facts(context)
        capture = v.capture_participant_guide(
            context, facts, v.build_tests(context, facts), v.StyleCarrier.resolve(ROOT)
        )
        mirror = v.load_mirror()
        source = []
        d6 = []
        in_d6 = False
        for node in capture.nodes:
            if node.kind == "heading" and node["text"].startswith("D.6 "):
                in_d6 = True
            elif node.kind == "heading" and node["text"].startswith("D.7 "):
                in_d6 = False
            for text, _ in _strings(node):
                pair = f"{text} {mirror.get(text)}"
                source.append(pair)
                if in_d6:
                    d6.append(pair)
        cls.source = v._normalize("\n".join(source))
        cls.d6 = v._normalize("\n".join(d6))

    def test_current_source_satisfies_optional_and_d6_reference_gates(self):
        report = Report()
        v.check_optional_exercise_gate(report, self.source)
        v.check_ontology_editing_reference_mirror(report, self.d6)
        self.assertFalse(report.failures)

    def test_d6_reference_and_lifecycle_conditions_cannot_disappear(self):
        for needle in (
            "生成 AI による Ontology 編集支援を評価するための参考情報です",
            "does not guarantee the availability or behavior of any specific product feature",
            "there are no operations to perform in this section",
            "does not affect the Core flow",
            "confirm that the target feature and conditions are documented in current official sources",
            "1. Discover evidence", "2. Domain design", "3. Structure and grounding checks",
            "4. Read-only preview and review", "5. Apply behind an explicit gate",
            "Generating, grounding and binding are different",
            "The Notebook 02 manifest is canonical",
            "UI names and layout", "Limits", "Retention", "What each role can do",
            "Per-feature compliance scope", "Pricing", "Fairness evaluation", "Consent and collection",
            "8 topics to verify in public documentation",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.d6)
                report = Report()
                v.check_ontology_editing_reference_mirror(report, self.d6.replace(needle, ""))
                self.assertEqual(status_for(report, "content.appendixD6Mirrored"), "FAIL")

    def test_d6_authoring_history_is_rejected_in_both_languages(self):
        for history in (
            "この節のもとになった資料は 2026 年 8 月 19 日に提供されたものです。",
            "読んだうえで採用しないという判断です。",
            "The material behind this section was supplied on 19 August 2026.",
            "These subjects were deliberately not adopted.",
        ):
            with self.subTest(history=history):
                report = Report()
                v.check_ontology_editing_reference_mirror(report, self.d6 + history)
                self.assertEqual(status_for(report, "content.appendixD6AuthoringHistory"), "FAIL")

    def test_data_history_is_not_authoring_history(self):
        report = Report()
        v.check_ontology_editing_reference_mirror(report, self.d6 + "実行履歴を記録する。 Check data history.")
        self.assertFalse(report.failures)

    def test_current_practice_statements_preserve_their_meaning(self):
        report = Report()
        v.check_data_agent_practice_mirror(report, self.source, v.Element("#document", {}))
        self.assertEqual(status_for(report, "content.dataAgentPracticeMirrored"), "PASS")
        for needle in (
            "Ontology static bindings require managed Delta tables",
            "does not mean access controls are unnecessary in production",
            "Unavailable engine history for a source does not itself fail a question",
            "Optional engine history does not waive failure to capture required native evidence",
            "Do not copy query text into the record sheet's answer field",
            "D.7 is also reference information rather than an exercise",
            "conservative ceiling imposed by the workshop",
            "not a published product-schema guarantee or a permanent limit",
            "本教材では Eventhouse の例クエリは別途登録せず",
            "This workshop does not register separate Eventhouse example queries",
            "KQL example patterns are included in these source instructions",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.source)
                report = Report()
                v.check_data_agent_practice_mirror(
                    report, self.source.replace(needle, ""), v.Element("#document", {})
                )
                self.assertEqual(status_for(report, "content.dataAgentPracticeMirrored"), "FAIL")


class EnglishTypographyTests(unittest.TestCase):
    def test_current_mirror_uses_straight_quotes(self):
        report = Report()
        v.check_english_typography(report, v.load_mirror())
        self.assertFalse(report.failures)

    def test_stale_html_quotes_fail_even_when_the_current_mirror_is_clean(self):
        report = Report()
        root = parse('<span lang="en">The workshop’s “instructions”</span>')
        v.check_english_typography(report, SimpleNamespace(entries={}), root)
        self.assertEqual(status_for(report, "i18n.straightQuotes"), "FAIL")

    def test_straight_english_and_quoted_japanese_punctuation_are_allowed(self):
        report = Report()
        text = "Japanese original: 「東京の寄付」、を確認する。"
        root = parse(f'<span lang="en">{html.escape(text)}</span>')
        v.check_english_typography(report, SimpleNamespace(entries={"example": text}), root)
        self.assertFalse(report.failures)


if __name__ == "__main__":
    unittest.main()
