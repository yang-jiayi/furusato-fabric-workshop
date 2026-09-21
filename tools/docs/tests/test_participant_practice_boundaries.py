"""Keep participant guidance checks independent of authoring history."""

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from furusato_docs import quality
from furusato_docs.validators import Report


class ParticipantPracticeBoundaries(unittest.TestCase):
    def failures(self, text):
        report = Report(target="participant practice fixture")
        quality.check_data_agent_practice(SimpleNamespace(agent_fewshots=[]), text, report)
        return {f.check for f in report.findings if f.level == "FAIL"}

    def test_budget_requires_current_guidance_not_authoring_history(self):
        text = (
            "グローバル指示の上限は、本ワークショップでは 15,000 文字です。"
            "これは本ワークショップが自分に課した安全側の上限であり、"
            "製品スキーマとして公開された保証値や、将来にわたって変わらない値として引用しないでください。"
            "配布された全文はこの上限の内側に収まっています。"
            "その時点の製品ドキュメントと画面表示で現在値を確認してください。"
        )
        self.assertNotIn("content.instructionBudgetFraming", self.failures(text))
        self.assertIn(
            "content.instructionBudgetFraming",
            self.failures(text.replace("その時点の製品ドキュメントと画面表示で現在値を確認してください", "")),
        )
        self.assertIn(
            "content.instructionBudgetNotUniversal",
            self.failures(text + "Fabric の上限は 15,000 文字です。"),
        )

    def test_kql_rationale_stays_scoped_to_the_distribution(self):
        text = (
            "本教材では Eventhouse の例クエリは別途登録せず、"
            "列名・粒度の規則と同じ場所に形を置くことで一致を保ちます。"
            "これは設定できないという製品全体の能力の説明ではありません。"
            "付録 E の Data Agent source capability matrix を確認してください。"
        )
        self.assertNotIn("content.kustoShapeRationale", self.failures(text))
        self.assertIn(
            "content.kustoShapeRationale",
            self.failures(text.replace("本教材では Eventhouse の例クエリは別途登録せず", "")),
        )

    def test_instruction_boundary_excludes_optional_setup_parameters(self):
        label, start, end = next(row for row in quality.PRACTICE_SECTIONS if row[0] == "16.8")
        self.assertEqual("16.8", label)
        self.assertEqual("16.9 AI 参照アーキテクチャ（明示 opt-in）", end)
        text = start + "\n指示はアクセス制御ではありません。\n" + end + "\nAPPLY_CHANGES"
        self.assertNotIn("APPLY_CHANGES", quality._section(text, start, end))
        self.assertIn(
            "content.practiceSectionIsolation",
            self.failures(start + "\nAPPLY_CHANGES\n" + end),
        )


if __name__ == "__main__":
    unittest.main()
