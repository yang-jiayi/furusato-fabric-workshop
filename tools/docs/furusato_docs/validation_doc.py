"""Build the v2.7.0 ten-case Data Agent validation record DOCX."""

from __future__ import annotations

from pathlib import Path

from .context import RuntimeContext
from .docx_kit import DocumentBuilder, cover_page
from .facts import TestFacts
from .guide_content import EVALUATION_EVIDENCE_NOTE
from .oox import StyleCarrier, apply_package_metadata
from .tests10 import HeldOutTest

RESULT_VALUES = ("PASS", "FAIL", "UNCLEAR", "EXECUTION_ERROR")


def build(
    context: RuntimeContext,
    facts: TestFacts,
    tests: list[HeldOutTest],
    carrier: StyleCarrier,
    output: Path,
    scratch: Path,
) -> DocumentBuilder:
    builder = DocumentBuilder(carrier, scratch / "validation-shell.docx")

    cover_page(
        builder,
        title="Data Agent 検証記録票（10 問）",
        title_break_after="Data Agent",
        subtitle=(
            "口語・敵対的な 10 問を 1 問 1 会話で実施し、ルート・粒度・安定 ID・境界・拒否の適切さを記録します。"
            "10 問は Data Agent に対して held-out です。採点者用のこの記録票には期待する回答を記載しますが、"
            "実行可能なクエリ文だけは記載しません。"
        ),
        version=context.version,
        tagline="Microsoft Fabric IQ Workshop FY27 — Data Agent held-out 評価（採点者用）",
        footer_lines=(
            "Furusato Fabric Workshop",
            f"データセット契約 {context.dataset_manifest['datasetVersion']}",
            "合成データ（人物・事業者・寄付はすべて架空）",
        ),
    )

    builder.table_of_contents(levels="1-2")

    _how_to_use(builder, context, tests)
    _summary_sheet(builder, tests)
    for test in tests:
        _test_section(builder, test)
    _summary_notes(builder, context, tests)

    builder.update_fields_on_open()
    builder.save(output)

    apply_package_metadata(
        output,
        title=f"Furusato Data Agent Validation 10 v{context.version}",
        subject="Microsoft Fabric Data Agent held-out validation record",
        keywords="Microsoft Fabric, Fabric IQ, Ontology, Data Agent, Validation, Workshop",
        description=(
            f"v{context.version} participant validation record: ten colloquial and adversarial "
            "held-out tests with expected route, expected behaviour, required evidence and result columns."
        ),
        label_info=carrier.label_info(),
        custom_properties=carrier.custom_properties(),
    )
    return builder


def _how_to_use(builder: DocumentBuilder, context: RuntimeContext, tests: list[HeldOutTest]) -> None:
    total = len(tests)
    builder.heading("1. この記録票の使い方", 1)
    builder.callout(
        "design",
        "「held-out」とは、10 問とその期待値を Data Agent に与えないという意味です。"
        "採点する人には期待値が必要なので、この記録票には期待する回答・数値・拒否理由を書いてあります。"
        "伏せてあるのは実行可能なクエリ文（SQL / KQL / GQL の本文）だけです。"
        "Agent の設定（グローバル指示・ソース説明・ソース指示・例クエリ）に、"
        "この記録票の内容を写してはいけません。",
        title="何が held-out で、何が書いてあるのか",
    )
    builder.bullets(
        (
            f"{total} 問すべてを、1 問につき 1 つの新しい会話（fresh conversation）で実施します。",
            "質問文はそのまま貼り付けます。言い換えたり、ヒントを足したりしません。",
            "回答本文だけでなく、使用されたソースと提示された安定 ID を必ず記録します。",
            "判定は PASS / FAIL / UNCLEAR / EXECUTION_ERROR の 4 値から選びます。",
            f"合格の基準は {total} 問中 {total} 問 PASS です。1 問でも PASS でなければ公開しません。",
            f"不合格があった場合は、設定を修正してから {total} 問すべてを最初からやり直します。",
        ),
        numbered=True,
    )
    builder.table(
        ["判定", "意味", "扱い"],
        [
            ["PASS", "合格条件をすべて満たしている。", "合格。次の問へ進む。"],
            [
                "FAIL",
                "数値・ルート・境界・拒否のいずれかが合格条件を満たさない。",
                f"不合格。設定を修正して {total} 問を最初からやり直す。",
            ],
            [
                "UNCLEAR",
                "回答が曖昧で、合格条件を満たしたか判定できない。",
                "不合格として扱う（FAIL と同じ）。曖昧さ自体が Agent 側の問題。",
            ],
            [
                "EXECUTION_ERROR",
                "クエリ実行・接続・サービスのエラーで回答に至らなかった。原因は別途切り分ける。",
                "一時障害かを切り分けるため設定を変更せず最大 2 回まで再実行する。"
                "3 回目も同じなら、エラーと参照先を記録して権限・構成・サービスを調べる。",
            ],
        ],
        caption="判定値の定義と、判定後の扱い",
        widths=(1.2, 2.4, 2.8),
        font_size=8.8,
    )
    builder.callout(
        "note",
        EVALUATION_EVIDENCE_NOTE,
        title="数値一致や汎用ブロックだけで PASS にしない",
    )
    builder.table(
        ["項目", "基準"],
        [
            ["合格基準", f"{total} 問中 {total} 問が PASS"],
            ["UNCLEAR の扱い", "FAIL と同じ。合格件数に数えない。"],
            ["EXECUTION_ERROR の扱い", "設定を変えずに最大 2 回まで再実行。それでも解消しない場合はエスカレーション。"],
            ["再実行時の禁止事項", "再実行のあいだに Agent の設定・ソース選択・指示を変更しない。"],
            ["エスカレーション先", "参照先の実 ID・権限・構成と、capacity の SKU・混雑状況・リージョン一致を管理者と確認する。"],
            ["部分再テスト", f"禁止。設定を変更したら {total} 問すべてを最初からやり直す。"],
        ],
        caption="合格基準と再実行の扱い",
        widths=(1.6, 4.8),
    )
    builder.callout(
        "gate",
        "この記録票には、期待するルートとクエリ種別を記載していますが、"
        "SQL・KQL・GQL の文面は意図的に載せていません。参加者が Agent にクエリを与えると、"
        "評価しているのが Agent なのか参加者なのか分からなくなるためです。",
        keep_with_next=True,
    )
    builder.callout(
        "note",
        f"評価対象のデータセットは {context.dataset_manifest['datasetVersion']} です。"
        "静的スナップショットは 2025 年、運用観測は 2026 年 8 月（UTC）です。",
    )
    builder.callout(
        "note",
        "この記録票の期待値は今回の成功証拠ではありません。"
        "Agent 未作成や機能の利用不可により質問を送っていない場合は、判定欄を空欄のままにして、"
        "実施サマリーへ「未実施 / ブロック」と理由を記録します。"
        "item 作成やオフライン検証の成功から PASS を転記してはいけません。",
        title="未実施の問に判定を付けない",
    )


def _summary_sheet(builder: DocumentBuilder, tests: list[HeldOutTest]) -> None:
    # The judgement summary is kept whole on one page, which is taller than the
    # room left beside the short "実施条件" form. Letting this heading flow, and
    # pulling the closing notes of the previous section down with it, gives the
    # form a page with real content on it instead of a stub page.
    builder.heading("2. 実施サマリー", 1, new_page=False, pull_up=True)
    builder.table(
        ["実施項目", "記入欄"],
        [
            ["実施日", ""],
            ["実施者", ""],
            ["Participant ID", ""],
            ["対象 Workspace / Folder（名前と実 ID）", ""],
            ["Data Agent 名", ""],
            ["Data Agent の実 ID", ""],
            ["構成区分（Core / Optional）", ""],
            ["追加ツールと実行確認（Core は追加ツールなし）", ""],
            ["Core のランタイム（Preview 固定）", "Preview"],
            ["Standard runtime の比較実施（任意）", "☐ 実施した　☐ 実施していない"],
            ["公開前 / 公開後", ""],
            ["未実施 / ブロックの工程と理由", ""],
        ],
        caption="実施条件",
        widths=(2.0, 4.0),
    )
    builder.body(
        "追加ツールを使う Optional の前後評価は、Core とは別の記録票に構成と実行確認を記録します。"
        "単発の結果差を改善の証明とせず、接続機能が利用できない場合は、その工程と後続評価をブロックとして残します。"
    )
    builder.callout(
        "stop",
        "Core の記録は Preview runtime で実施したものでなければなりません。"
        "Standard runtime は比較用であり、Core の判定には使えません。"
        "Standard でしか通らなかった問いは、Core としては不合格です。"
        "Standard も試した場合は、各問の「Standard runtime での比較」欄に別途記録し、"
        "上の判定欄には Preview の結果だけを書いてください。",
        title="Core は Preview runtime 固定",
    )
    builder.table(
        ["#", "テスト", "期待するルート", "判定", "備考"],
        [
            [str(test.number), f"{test.test_id} {test.title}", test.route, "", ""]
            for test in tests
        ],
        caption="10 問の判定サマリー（実施後に記入）",
        widths=(0.4, 1.8, 2.0, 0.8, 1.6),
        keep_together=True,
    )
    builder.table(
        ["集計", "件数"],
        [[value, ""] for value in RESULT_VALUES] + [["合計", str(len(tests))]],
        caption="判定の集計",
        widths=(2.0, 1.0),
        keep_together=True,
        pull_up=True,
    )
    builder.body(
        f"合格条件は {len(tests)}/{len(tests)} です。UNCLEAR は FAIL として数えます。"
        "EXECUTION_ERROR だけでは原因を断定できません。設定を変えずに"
        "同じ質問を最大 2 回まで再実行し、3 回目も失敗した場合はエラー・参照先・確認済み事項を記録して"
        "エスカレーションします。設定や参照先を修正したら、10 問すべてをやり直します。"
    )


def _test_section(builder: DocumentBuilder, test: HeldOutTest) -> None:
    builder.heading(f"{test.number + 2}. {test.test_id}　{test.title}", 1)
    builder.callout("note", test.question, title="質問（そのまま貼り付ける）")
    builder.table(
        ["観点", "内容"],
        [
            ["ねらい", test.purpose],
            ["期待するルート", test.route],
            ["期待するクエリ種別", test.query_shape],
            ["期待する回答・挙動", test.expected],
            ["必要な根拠", "\n".join(f"・{item}" for item in test.evidence)],
            ["合格条件", "\n".join(f"・{item}" for item in test.pass_criteria)],
            ["典型的な失敗", test.trap],
        ],
        caption=f"{test.test_id} の評価基準",
        widths=(1.1, 5.3),
        font_size=8.8,
    )
    builder.heading(f"{test.test_id} 記録欄", 2)
    builder.table(
        ["記録項目", "記入欄"],
        [
            ["実際に使用されたソース", ""],
            ["実際の回答（要点）", ""],
            ["提示された安定 ID", ""],
            ["提示された数値", ""],
            ["粒度・スコープの記述", ""],
            ["境界・拒否の記述", ""],
            ["所見・再テストの要否", ""],
            ["判定（Preview runtime。該当するものを 1 つ塗りつぶす）", "　".join(f"☐ {value}" for value in RESULT_VALUES)],
            ["Standard runtime での比較（任意・Core の判定には使わない）", ""],
        ],
        caption=f"{test.test_id} の実施記録（判定は Preview runtime のみ。UNCLEAR は FAIL として集計する）",
        widths=(1.6, 4.8),
        # The seven free-text rows are what a grader writes into, so they carry the
        # tall "at least" height. The verdict row prints its checkboxes and the
        # Standard comparison row is a short note, so both keep a natural height and
        # the whole record still lands on one page per test.
        min_row_height_cm=2.7,
        free_text_rows={1, 2, 3, 4, 5, 6, 7},
        keep_together=True,
    )


def _summary_notes(builder: DocumentBuilder, context: RuntimeContext, tests: list[HeldOutTest]) -> None:
    total = len(tests)
    builder.heading(f"{total + 3}. 不合格時の対応記録", 1)
    builder.body(
        f"不合格が出た場合は、次の順序で原因を切り分け、修正内容を記録してから {total} 問を再実施します。"
    )
    builder.table(
        ["切り分けの順序", "確認内容", "修正内容の記録欄"],
        [
            ["1. ルート選択", "ソース説明が短すぎないか、否定形が足りているか", ""],
            ["2. ソース選択", "KQL でマテリアライズドビューだけを選んでいるか、raw テーブルを外しているか", ""],
            ["3. ソース指示", "列名・集計関数・スコープの規則が足りているか", ""],
            ["4. グローバル指示", "用語の解決・粒度の規則が足りているか", ""],
            ["5. セマンティックメタデータ", "Ontology 側の説明・境界が不足している証拠があるか", ""],
            ["6. 実行エラーの原因", "権限・参照先・構成を確認しても継続するか。サービス障害と断定せず証跡を記録する", ""],
        ],
        caption="原因の切り分けと修正記録",
        widths=(1.4, 2.8, 2.4),
    )
    builder.table(
        ["再実施", "記入欄"],
        [
            ["再実施日", ""],
            ["変更した設定", ""],
            [f"再実施後の PASS 件数（/{total}）", ""],
            ["EXECUTION_ERROR の再実行回数", ""],
            ["残課題", ""],
        ],
        caption="再実施の記録",
        widths=(2.0, 4.0),
    )
    builder.callout(
        "stop",
        "部分的な再テストで合格とはしません。設定を 1 箇所でも変更したら、"
        f"{total} 問すべてを新しい会話で最初から実施します。",
    )
