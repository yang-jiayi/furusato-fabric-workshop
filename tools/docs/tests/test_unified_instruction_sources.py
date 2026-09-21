"""Source-only instruction checks; no runtime loading, resealing or output files."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
NEEDS_MIRROR = re.compile(r"[\u3000-\u303f\u3040-\u30ff\u4e00-\u9fff\uff00-\uffef]")


def static_strings(node):
    if isinstance(node, ast.JoinedStr):
        return  # Rendered templates are covered by the full-context guide tests.
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node.value
    for child in ast.iter_child_nodes(node):
        yield from static_strings(child)


class UnifiedInstructionSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "tools" / "docs" / "furusato_docs" / "guide_unified.py").read_bytes().decode("utf-8")
        cls.functions = {
            node.name: node for node in ast.parse(cls.source).body
            if isinstance(node, ast.FunctionDef)
        }
        cls.translations = json.loads(
            (ROOT / "tools" / "html" / "furusato_html" / "i18n" / "unified-documents.json").read_text("utf-8")
        )["add"]
        cls.confirmation = cls.functions["confirmation_workflow"]
        cls.confirmation_text = "\n".join(static_strings(cls.confirmation))
        calls = [
            node.value for node in cls.confirmation.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        ]
        cls.dialogue = ast.literal_eval(next(call for call in calls if call.func.attr == "bullets").args[0])
        cls.branches = dict(ast.literal_eval(next(call for call in calls if call.func.attr == "table").args[1]))

    def test_ci_prompts_remain_byte_exact(self):
        hashes = {}
        for node in ast.walk(self.functions["ci_exercise"]):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "callout":
                continue
            title = next(
                (ast.literal_eval(kw.value) for kw in node.keywords if kw.arg == "title"), ""
            )
            if title.startswith("CI 演習 "):
                self.assertEqual(ast.literal_eval(node.args[0]), "note")
                self.assertNotIn(title, hashes)
                hashes[title] = hashlib.sha256(
                    ast.literal_eval(node.args[1]).encode("utf-8")
                ).hexdigest()
        self.assertEqual(hashes, {
            "CI 演習 1：SQL の全母集団から分布を描く":
                "5aeba5aeea794ad02cd7c93555ed70490ccf6e2f6e3a28562730441a88731d85",
            "CI 演習 2：KQL の file/run 内訳を可視化する":
                "294d6c4839223962378456c6ccf11e56241f4bb33e4e0181c7a41d5edd97510f",
        })

    def test_static_source_and_ci_guidance_has_exact_english_keys(self):
        for name in ("source_rules", "native_evidence", "ci_exercise", "confirmation_workflow"):
            for text in static_strings(self.functions[name]):
                if not NEEDS_MIRROR.search(text):
                    continue
                with self.subTest(section=name, text=text):
                    self.assertIn(text, self.translations)
                    self.assertTrue(self.translations[text].strip())

    def test_selection_wording_never_turns_into_receipt_with_a_later_caveat(self):
        text = "\n".join(static_strings(self.functions["source_rules"]))
        for marker in (
            "見出し・箇条書き・要約でも「選択した返礼品」",
            "後から注意書きを付けても", "寄付金を受領するという指標とは区別",
            "Ontology の JSON にだけある値を SQL の出力として記しません",
        ):
            self.assertIn(marker, text)

    def test_protected_columns_and_real_provenance_are_participant_checks(self):
        text = "\n".join(static_strings(self.functions["source_rules"]))
        for marker in (
            "MunicipalityById の 22 列", "DonationTraceById の 30 列",
            "MunicipalityDerivedNationwideCountRank", "存在しない MunicipalityStoredNationwideCountRank",
            "MunicipalityStoredNationwideAmountRank", "14 / 17 / 15 列",
            "HasMatches や EventIdentityFieldExists", "false の行を除外して異常を隠しません",
            "SourceSystem・SourceObject・Scope", "作成したラベルをスキーマ検査",
        ):
            self.assertIn(marker, text)

    def test_confirmation_dialogue_is_wired_after_ci_only_in_the_unified_course(self):
        source = (ROOT / "tools" / "docs" / "furusato_docs" / "guide_agent.py").read_text("utf-8")
        chapter = next(
            node for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef) and node.name == "chapter_17_tests"
        )
        calls = [
            node for node in ast.walk(chapter)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "confirmation_workflow"
        ]
        self.assertEqual(len(calls), 1)
        branch = next(node for node in chapter.body if isinstance(node, ast.If) and calls[0] in ast.walk(node))
        self.assertEqual(ast.unparse(branch.test), "context.is_unified_guide")
        direct_calls = [
            node.value.func.attr for node in branch.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
        ]
        self.assertEqual(direct_calls, ["native_evidence", "ci_exercise", "confirmation_workflow"])
        self.assertIsInstance(branch.body[-1], ast.Return)
        self.assertIn("17.14 同じ Agent で確認してから照会する", self.confirmation_text)

    def test_one_precise_donation_proposal_waits_for_agreement(self):
        self.assertEqual(self.dialogue[0], "利用者：「東京のお金持ちはだれ？」")
        proposal = self.dialogue[1]
        self.assertEqual(proposal.count("という質問でよいですか"), 1)
        for marker in (
            "所得・資産や『お金持ち』は判断できません",
            "東京都在住の合成寄付者", "Static 2025 UTC snapshot 全体",
            "累計寄付金額（JPY）を寄付者ごとに集計",
            "東京都在住の寄付者内で金額の降順",
            "寄付者の在住地であり、受入自治体ではありません",
            "同意されるまで SQL・KQL・GQL・CI は実行せずに待ちます",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, proposal)
        self.assertEqual(self.dialogue[2], "利用者：「はい、その寄付金額ランキングをお願いします。」")
        waiting = self.branches["確認を待つ間"]
        for field in ("Entity", "地域の役割（在住／受入）", "期間", "指標", "順位範囲"):
            self.assertIn(field, waiting)
        self.assertIn("承諾前の SQL・KQL・GQL・CI がない", waiting)
        self.assertIn("寄付指標へ自動で読み替えません", self.confirmation_text)

    def test_target_changes_do_not_reuse_previous_consent_or_execution_evidence(self):
        for marker in (
            "割り当てられた Workspace / Folder", "主 Agent の実 ID", "Draft / Published",
            "Runtime=Preview と第 16 章の設定",
            "以前の会話の承諾、別 Agent の応答、配布画像",
            "今回の同意や実行の証跡として流用しません",
            "対象や設定が変わった場合は新しい会話で開始",
            "確認が必要な問いは提案からやり直します",
        ):
            self.assertIn(marker, self.confirmation_text)
        self.assertNotRegex(self.confirmation_text, r"\b\d{5}\b")
        self.assertNotRegex(
            self.confirmation_text,
            r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b",
        )

    def test_yes_only_accepts_the_latest_pending_proposal(self):
        yes = self.branches["「はい」／yes"]
        self.assertIn("この会話で最後に提示された未処理の提案だけ", yes)
        self.assertIn("提案がない、取消済み", yes)
        self.assertIn("何への同意か特定できない場合は照会せず確認し直す", yes)
        self.assertIn("実 query の対象と出力ラベルが承諾した問いに一致", yes)
        after_agreement = self.dialogue[3]
        for marker in (
            "同意した問いだけを Lakehouse SQL", "成功した実結果",
            "DonorId", "寄付金額順位", "Source・Scope・Metric・Unit・RankScope",
            "JST 暦年の追加フィルターにはしません",
            "照会成功は保証せず", "失敗・欠落を 0 や推測値で補いません",
        ):
            self.assertIn(marker, after_agreement)

    def test_scope_correction_takes_precedence_over_yes_and_requires_reconfirmation(self):
        correction = self.branches["条件の訂正"]
        for marker in (
            "東京は受入側。自治体ごとにしてください", "旧提案を置き換え",
            "「はい」が付いていても、範囲の訂正は同意ではない",
            "対象と順位範囲を東京都の受入自治体内", "1 問を再提示",
            "期間・指標も明記", "新しい提案への同意を待つ",
            "訂正時には SQL・KQL・GQL・CI を実行しない",
        ):
            self.assertIn(marker, correction)

    def test_no_and_cancel_stop_without_queries_or_stale_yes(self):
        cancellation = self.branches["「いいえ」／no／キャンセル／cancel"]
        self.assertIn("未処理の提案を取り消して停止", cancellation)
        self.assertIn("SQL・KQL・GQL・CI を実行せず", cancellation)
        self.assertIn("後の「はい」で取り消した提案を復活させない", cancellation)

    def test_clear_questions_do_not_authorize_old_proposals_or_need_reconfirmation(self):
        unrelated = self.branches["無関係な明確な新しい質問"]
        self.assertIn("新しい質問は旧提案への承諾ではない", unrelated)
        self.assertIn("未処理の提案を取り消し", unrelated)
        self.assertIn("不要な再確認を挟まず新しい質問だけを通常どおり扱う", unrelated)
        self.assertIn("旧提案の照会を一緒に実行しない", unrelated)
        self.assertIn("後の曖昧な「はい」を旧提案へ自動で結び付けない", unrelated)
        clear = self.branches["初めから明確な通常質問"]
        self.assertIn("全国の Static 2025 UTC snapshot 全体の寄付件数と合計金額", clear)
        self.assertIn("不要な再確認を挟まず", clear)

    def test_confirmed_donation_metrics_are_not_personal_inferences(self):
        for marker in (
            "同意があっても、所得・資産・税額の推論は拒否のまま",
            "納税額は寄付金額ではなく、寄付データから納税順位を求めません",
            "承諾されるのは提案した寄付指標の照会だけ",
            "結果を「お金持ち」「貧乏」の順位として表示しません",
            "サービスの汎用拒否やブロックが残る場合",
            "言い換えや別経路で回避しません",
        ):
            self.assertIn(marker, self.confirmation_text)

    def test_personal_rankings_need_clarification_even_when_wording_is_clear(self):
        self.assertIn(
            "人物の富裕・貧困・税額の順位は、言い方が明確でも確認が必要",
            self.confirmation_text,
        )
        self.assertIn("不要な再確認を挟まず", self.branches["初めから明確な通常質問"])
        english = "\n".join(
            self.translations[text] for text in static_strings(self.confirmation) if NEEDS_MIRROR.search(text)
        )
        self.assertIn(
            "Rankings of people by wealth, poverty or tax require clarification even when the wording is clear",
            english,
        )
        self.assertIn("Tax paid is not donation amount", english)

    def test_example_is_not_native_proof_or_an_enforced_state_machine(self):
        for marker in (
            "検証済みの native 応答や実行結果ではありません",
            "分岐ごとに新しい会話", "その分岐の提案・承諾・訂正・中止は同じ会話",
            "標準の Fabric UI では指示に基づく対話", "強制された状態機械ではありません",
            "製品によって保証されるとは扱いません",
            "承諾前・訂正時・中止時に query や tool 実行がないことを確認",
            "証跡が取得できない部分は未確認",
        ):
            self.assertIn(marker, self.confirmation_text)
        for internal_detail in ("候補プロファイル", "revision", "profile8", "Windows Hello", "SR識別子"):
            self.assertNotIn(internal_detail, self.confirmation_text)
        english = "\n".join(
            self.translations[text] for text in static_strings(self.confirmation) if NEEDS_MIRROR.search(text)
        )
        for marker in (
            "not a verified native response", "not an enforced state machine",
            "latest pending proposal", "A scope correction is not consent, even if it includes yes",
            "Do not run SQL, KQL, GQL or CI on a correction", "Clear the pending proposal",
            "A later yes must not revive", "without needless reconfirmation", "not passed",
        ):
            self.assertIn(marker, english)
        self.assertNotRegex(english, r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")

    def test_original_questions_and_84_condition_expressions_are_unchanged(self):
        source = (ROOT / "tools" / "docs" / "furusato_docs" / "tests10.py").read_text("utf-8")
        tests = [
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "HeldOutTest"
        ]
        questions = []
        conditions = []
        condition_count = 0
        for test in tests:
            fields = {keyword.arg: keyword.value for keyword in test.keywords}
            questions.append(ast.dump(fields["question"], include_attributes=False))
            for field in ("evidence", "pass_criteria"):
                conditions.append(ast.dump(fields[field], include_attributes=False))
                condition_count += len(fields[field].elts)
        self.assertEqual(len(questions), 10)
        self.assertEqual(condition_count, 84)
        for values, digest in (
            (questions, "d970d7bb292c138d656e025592ffe5cb88303b337c902088ef66c87c7c2af509"),
            (conditions, "4639f0db009ad6c023707deb10b85ccce45d7e747964b82dba39a7755bad897b"),
        ):
            encoded = json.dumps(values, ensure_ascii=False).encode("utf-8")
            self.assertEqual(hashlib.sha256(encoded).hexdigest(), digest)
        self.assertIn("元の 10 問／84 条件を変えずに全問を再評価", self.confirmation_text)
        self.assertIn("両方の CI 演習も元の質問のまま再実施", self.confirmation_text)
        self.assertIn("置き換えたり、免除したりしません", self.confirmation_text)


if __name__ == "__main__":
    unittest.main()
