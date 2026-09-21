"""Read-only checks for participant-facing optional quality verification."""

from __future__ import annotations

import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(ROOT / "tools" / "html"))

from furusato_docs.context import load_context  # noqa: E402
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.guide_agent import chapter_17_tests  # noqa: E402
from furusato_docs.guide_handson import RETIRED_SCREENSHOTS, _shot  # noqa: E402
from furusato_docs.oox import StyleCarrier  # noqa: E402
from furusato_docs.tests10 import build_tests  # noqa: E402
from furusato_html.capture import CaptureBuilder  # noqa: E402
from furusato_html.mirror import NEEDS_MIRROR, load_mirror, suspicious_english  # noqa: E402
from sync_i18n import _strings  # noqa: E402

HEADING = "17.13 品質を改善するための追加検証（Optional）"


class QualityIterationContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        context = load_context(ROOT)
        cls.tests = build_tests(context, compute_facts(context))
        carrier = StyleCarrier.resolve(ROOT)
        cls.carrier = carrier
        cls.chapters = {}
        cls.sections = {}
        for public in (False, True):
            builder = CaptureBuilder(carrier)
            chapter_17_tests(builder, context, cls.tests, public_documents_only=public)
            cls.chapters[public] = builder.nodes
            start = next(
                i for i, node in enumerate(builder.nodes)
                if node.kind == "heading" and node["text"] == HEADING
            )
            cls.sections[public] = builder.nodes[start:-1]
        cls.strings = [text for node in cls.sections[False] for text, _ in _strings(node)]
        cls.text = "\n".join(cls.strings)

    def assert_markers(self, *markers: str) -> None:
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_section_is_compact_identical_in_both_modes_and_before_pointer(self) -> None:
        self.assertEqual(self.sections[False], self.sections[True])
        for nodes in self.chapters.values():
            self.assertEqual(nodes[-1]["title"], "うまくいかないときは")
            self.assertIn("第 17 章", nodes[-1]["text"])
            self.assertEqual(
                [n["text"] for n in nodes if n.kind == "heading"][-2:],
                ["17.12.1 再評価の引き金", HEADING],
            )
        section = self.sections[False]
        tables = [n for n in section if n.kind == "table"]
        steps = [n for n in section if n.kind == "bullets"]
        self.assertEqual(len(tables), 1)
        self.assertEqual(len(tables[0]["rows"]), 4)
        self.assertEqual(len(steps), 1)
        self.assertTrue(steps[0]["numbered"])
        self.assertEqual(len(steps[0]["items"]), 5)
        self.assertEqual([n["tone"] for n in section if n.kind == "callout"], ["stop"])
        self.assertFalse([n for n in section if n.kind in ("figure", "code")])
        self.assertLess(len(self.text), 2800)

    def test_original_contract_is_not_weakened_or_stuffed_into_examples(self) -> None:
        self.assert_markers(
            "本章の元の 10 問／84 要件",
            "質問・rubric を改名・緩和せず", "該当要件はすべて AND",
            "受入判定とソース／データの正確さは別の軸",
            "T01 は「静的 2025」という期間の意味が必須",
            "T03 は確認質問の分岐も許容",
            "選択した分岐に適用されない要件だけを NA",
            "T04 は `Relationship:`／`Traversal:` の literal 行",
            "T06 は `All timestamps are UTC.` の literal 文が必須",
            "held-out の質問・期待解を指示や例へ埋め込みません",
        )
        for test in self.tests:
            with self.subTest(test=test.test_id):
                self.assertNotIn(test.question, self.text)
                self.assertNotIn(test.expected, self.text)

    def test_layer_responsibilities_keep_data_and_safety_boundaries(self) -> None:
        self.assert_markers(
            "ソース指示（query・期間・粒度）／schema（要素の意味）",
            "global（routing・回答形式・拒否）",
            "raw 観測と保存済み MV の bucket を区別",
            "一意性の拒否より先に許可されたスカラー SUM",
            "GROUP BY の明細サンプルで代用しない",
            "静的 2025 と UTC scope を明示",
            "根拠のない JST 日付フィルターを作らない",
            "合算値は否定文にも引用しない", "ラベルは翻訳しない",
            "個人に関する推論や安全機構の迂回を認めない",
            "例は対応ソースで適切な場合だけ決定的な query 形",
            "物理データ／Ontology／接続済み semantic model",
            "実体の table/view、型・key・binding・関係方向を照合",
            "未接続の Optional semantic model を調整しても Core の改善証拠にはならない",
        )

    def test_optional_comparison_is_isolated_and_preserves_the_used_configuration(self) -> None:
        self.assert_markers(
            "使用中の Agent の設定・定義を非公開で保存",
            "許可された Folder に検証用と分かる名前の別 Agent",
            "Code Interpreter・runtime・例クエリ・ソース bindings・選択要素を照合",
            "未選択の EventID や raw テーブルは追加しない",
            "基線・変更する層・変更しない項目・評価回数を先に固定",
            "共有 Ontology は変更しない",
            "出典分担・UTC 見出し・照合キー・拒否",
            "必要なソースと返却項目を先に決め",
            "実行済みの根拠が揃うまで完了扱いにしない",
            "指示の短さだけで優劣を決めず",
            "metadata も変える場合は変更点を分けて記録",
            "Published モードで検証する場合",
            "検証用と明記した別 Agent だけを Publish",
            "使用中の Agent や利用者の権限は変更しません",
            "Publish の成功だけで第 18 章の品質条件を満たしたとは扱いません",
        )

    def test_ui_evidence_cannot_rewrite_or_excuse_a_failure(self) -> None:
        self.assert_markers(
            "対象 Agent・Draft / Published・runtime・ソース選択を開始前に確認",
            "毎問［Clear chat］の確認完了と新規会話を確認",
            "クリックだけで済ませない",
            "入力欄の Unicode 全文を読み戻し、元の質問と完全一致してから Send",
            "1 会話に正確な 1 問だけ",
            "全 query・全返却結果・analysis steps・最終回答の全文を記録",
            "固定 10 問を 1 バッチ", "エラー・途切れた応答も原本を残す",
            "回答を後編集して合格にせず", "実行エラーを適切な拒否と扱わない",
            "終了後も指示・runtime・ソース選択・bindings が評価開始時と一致",
            "部分的な再テストで済ませず、10 問すべてをやり直す",
            "予定していない設定変更、選択要素の追加、参照先の変更、または証跡の欠落",
            "実際の UI で構成を確認し直し",
            "評価結果に合わせて質問・必要な根拠・NA の範囲を変えません",
        )

    def test_repeat_evaluation_is_required_before_sharing(self) -> None:
        self.assert_markers(
            "利用者に共有する前に反復と未見セットで評価", "1 回の 10/10 は保証ではない",
            "修正の参考にした未見問題は以後の回帰問題",
            "再実行を初見と呼ばない",
            "追加の未見問題・基準は次の指示変更より前に凍結",
            "非退行が検証され承認された構成だけ",
            "第 18 章の共有手順へ進める",
            "この操作と、合格後の利用者への共有は別",
        )

    def test_english_mirrors_cover_exactly_the_new_section_in_both_modes(self) -> None:
        entries = json.loads(
            (ROOT / "tools" / "html" / "furusato_html" / "i18n" / "guide-19.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(set(entries), {s for s in self.strings if NEEDS_MIRROR.search(s)})
        self.assertFalse(suspicious_english(entries))
        for public in (False, True):
            mirror = load_mirror(public_documents_only=public)
            with self.subTest(public=public):
                self.assertEqual({s: mirror.get(s) for s in entries}, entries)
        english = "\n".join(entries.values())
        for literal in ("Relationship:", "Traversal:", "All timestamps are UTC."):
            self.assertIn(literal, english)
        self.assertIn("T03 also permits the clarification branch", english)
        self.assertIn("all applicable requirements with AND", english)
        self.assertIn("One stochastic 10/10 run is not a guarantee", english)
        self.assertIn("only requirements that do not apply to the chosen branch as NA", english)
        for pattern in (
            r"quality-v\d+", r"atomic-v\d+", r"full build", r"source tests?",
            r"reseal", r"not promoted", r"not acceptance.*report",
        ):
            with self.subTest(pattern=pattern):
                self.assertNotRegex(english, pattern)

    def test_history_screens_cannot_be_reinserted_with_new_captions(self) -> None:
        for tag in ("17-2", "17-3", "17-4"):
            with self.subTest(tag=tag):
                self.assertIn(tag, RETIRED_SCREENSHOTS)
                with self.assertRaisesRegex(ValueError, f"figure {tag} is retired"):
                    _shot(CaptureBuilder(self.carrier), tag, "new caption", "new alt text")

    def test_history_screens_are_absent_from_the_distributed_carrier(self) -> None:
        with zipfile.ZipFile(ROOT / "tools" / "docs" / "assets" / "style-carrier.zip") as archive:
            index = json.loads(archive.read("index.json"))
            screenshot_index = json.dumps(index["screenshots"])
            records = index.get("qualityCaptureProvenance", [])
            for tag in ("17-2", "17-3", "17-4"):
                with self.subTest(tag=tag):
                    self.assertNotIn(f"screenshots/{tag}.png", archive.namelist())
                    self.assertNotIn(f'"{tag}"', screenshot_index)
                    self.assertNotIn(f"{tag}.png", screenshot_index)
                    self.assertNotIn(tag, {record["tag"] for record in records})


if __name__ == "__main__":
    unittest.main()
