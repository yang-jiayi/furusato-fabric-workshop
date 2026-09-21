"""Build the v2.7.0 participant guide DOCX."""

from __future__ import annotations

import re
from pathlib import Path

from docx.enum.text import WD_ALIGN_PARAGRAPH

from . import guide_agent as ga
from . import guide_content as gc
from . import guide_handson as gh
from . import guide_unified as gu
from .context import RuntimeContext, num, yen
from .docx_kit import DocumentBuilder, cover_page
from .facts import TestFacts
from .oox import StyleCarrier, apply_package_metadata
from .parameters import PARAMETER_COLUMNS, build_parameter_rows
from .publication import PUBLIC_COVER, PUBLIC_NOTICE
from .tests10 import HeldOutTest

PARAMETER_WIDTHS = (1.7, 0.85, 1.35, 1.6, 2.5, 1.95, 2.1, 0.85)


def _pid(name: str) -> str:
    return name.replace("<PID>", "<PID>")


def build(
    context: RuntimeContext,
    facts: TestFacts,
    tests: list[HeldOutTest],
    carrier: StyleCarrier,
    output: Path,
    scratch: Path,
    *,
    public_documents_only: bool = False,
) -> DocumentBuilder:
    if context.is_unified_guide:
        _ = context.guide_profile
        build_parameter_rows(context, "Notebook_04")
    names = context.names
    expected = context.expected
    increment = context.expected_increment
    builder = DocumentBuilder(carrier, scratch / "participant-shell.docx")

    cover_page(
        builder,
        title="Fabric IQ Ontology ハンズオン（ふるさと納税）",
        title_break_after="Fabric IQ Ontology",
        subtitle=(
            "RDB・BI から Ontology への設計転換／10 Entity・15 Relationship の手動構築／"
            "Pipeline と OneLake イベントによる 2026 年 8 月増分／Notebook 02 による "
            f"{context.metadata_object_count} メタデータ登録／"
            + ("1 Data Agent・3 ソース・Code Interpreter／" if context.is_unified_guide else "3 ソース Data Agent と ")
            + "10 問の held-out テスト"
        ),
        version=context.version,
        tagline="Microsoft Fabric IQ Workshop FY27 — 参加者用ハンズオンガイド",
        footer_lines=(
            "Furusato Fabric Workshop",
            f"データセット契約 {context.dataset_manifest['datasetVersion']}",
            "合成データ（人物・事業者・寄付はすべて架空。自治体名とコードのみ実在の参照ラベル）",
        ) + ((f"文書版 {context.document_edition}",) if context.is_unified_guide else ())
        + ((PUBLIC_COVER,) if public_documents_only else ()),
    )

    builder.table_of_contents()

    _chapter_01_scenario(builder, context, public_documents_only=public_documents_only)
    _chapter_02_mental_model(builder, context)
    _chapter_03_method(builder, context)
    _chapter_04_rationale(builder, context)
    _chapter_05_prerequisites(builder, context, facts)
    gh.chapter_06_lakehouse(builder, context)
    gh.chapter_07_ontology(builder, context)
    gh.chapter_08_entities(builder, context)
    gh.chapter_09_relationships(builder, context)
    gh.chapter_10_static_gate(builder, context, facts)
    gh.chapter_11_eventhouse(builder, context)
    gh.chapter_12_pipeline(builder, context)
    gh.chapter_13_increment(builder, context, facts)
    gh.chapter_14_timeseries(builder, context, facts)
    gh.chapter_15_notebook02(builder, context)
    ga.chapter_16_data_agent(builder, context)
    ga.chapter_17_tests(builder, context, tests, public_documents_only=public_documents_only)
    ga.chapter_18_publish(builder, context, tests)
    ga.chapter_19_troubleshooting(builder, context)
    ga.appendix_a_expected(builder, context, facts)
    ga.appendix_b_parameters(builder, context, public_documents_only=public_documents_only)
    ga.appendix_c_poc_to_production(builder, context)
    ga.appendix_d_optional(builder, context)
    ga.appendix_e_links(builder, context)

    builder.update_fields_on_open()
    builder.save(output)

    apply_package_metadata(
        output,
        title=f"Fabric IQ Ontology Workshop Furusato Participant v{context.version}",
        subject="Microsoft Fabric participant workshop guide",
        keywords="Microsoft Fabric, Fabric IQ, Ontology, Eventhouse, Data Pipeline, Data Agent, Workshop",
        description=(
            f"v{context.version} participant guide: RDB/BI to Ontology design method, "
            f"{context.ontology_contract['entityTypes']} entity types, "
            f"{context.ontology_contract['relationshipTypes']} relationship types, "
            "Pipeline-only August 2026 increment, and ten held-out Data Agent tests."
        ),
        label_info=carrier.label_info(),
        custom_properties=carrier.custom_properties(),
    )
    return builder


# --------------------------------------------------------------------- part 1
def _chapter_01_scenario(
    builder: DocumentBuilder, context: RuntimeContext, *, public_documents_only: bool = False
) -> None:
    expected = context.expected
    increment = context.expected_increment
    builder.heading("1. シナリオと完成アーキテクチャ", 1)
    if public_documents_only:
        builder.callout("note", PUBLIC_NOTICE, title="公開文書の範囲")
    if context.is_unified_guide:
        gu.edition_notice(builder, context)

    builder.heading("1.1 背景と解きたい問い", 2)
    builder.body(
        "自治体は、寄付総額を伸ばすだけでなく、返礼品カテゴリと事業者の組み合わせを最適化し、"
        "リピーターを育て、地域内のサプライチェーンを強くしたいと考えています。しかしデータは部門ごとに分かれ、"
        "「自治体」「返礼品」「事業者」といった同じ言葉が、チームやツールごとに違う定義で使われています。"
    )
    builder.body(
        "さらに寄付の申込は日々増えます。マスタと履歴（バッチ）と、日々届く増分（運用観測）を、"
        "同じビジネス言語で、しかし粒度を混ぜずに扱える状態が必要です。本ハンズオンは、この状態を "
        "Microsoft Fabric の Lakehouse・Eventhouse・Ontology・Data Agent で作り上げます。"
    )
    builder.bullets(
        (
            "受入が多いのはどの自治体か。それは件数で見ているのか、金額で見ているのか。",
            "「東京の寄付」とは、東京都が受け取った寄付か、東京都在住者が出した寄付か。",
            "ある寄付の返礼品を供給できる事業者はどこか。それは「発送した」と同じ意味か。",
            "8 月に届いた運用観測は、静的スナップショットの続きなのか、別のデータセットなのか。",
        )
    )
    builder.callout(
        "design",
        "これらはすべて「クエリが書けるか」ではなく「意味が宣言されているか」の問題です。"
        "本ガイドの中心は SQL の書き方ではなく、業務の意味をモデルとして宣言する方法です。",
        title="このワークショップの主題",
    )

    builder.heading("1.2 完成アーキテクチャ", 2)
    builder.body(
        "Core ハンズオンを終えると、次のデータフローが完成します。静的シードは Notebook 01 が検証して "
        "Lakehouse の Delta テーブルへ発行し、増分 CSV は OneLake の FileCreated トリガーが Pipeline を起動して "
        "Eventhouse へ取り込みます。Ontology は両方をバインドし、Notebook 02 がセマンティックメタデータを一括登録し、"
        "3 つのソースが Data Agent の根拠になります。"
    )
    if context.is_unified_guide:
        builder.table(
            ["層", "実習での役割"],
            [
                ["Lakehouse", "Notebook 01 の静的 Delta と共有 SQL ヘルパー。静的属性・件数・金額・順位の根拠。"],
                ["Eventhouse", "Pipeline の運用観測。承認済み MV と共有 KQL 関数。静的データと合算しない。"],
                ["Ontology", "教材用 full Ontology を唯一の connectedOntology とし、関係の件数・path・identity を GQL で確認。"],
                ["主 Data Agent", context.names["dataAgent"] + " 1 件。SQL / KQL / GQL の根拠を分ける。"],
                ["Code Interpreter", "同じ Agent の Preview ツール。取得済みの bounded / full-scope 集約から分析・図・ファイルを作る。"],
            ],
            caption="文書版の完成アーキテクチャ（共有データ・完全モデル・主 Agent 1 件）",
            widths=(1.3, 5.3),
        )
    else:
        _legacy_architecture_figure(builder, context)

    builder.heading("1.3 到達点と Core / Optional の境界", 2)
    setup_path = (
        "主経路は第 6〜15 章でデータと完全な教材 Ontology を作り、"
        "第 16.2 節で共有 SQL/KQL ヘルパーを準備してから、主 Agent 1 件を構成します。"
        "Notebook 03 は Ontology 作成の代替、Notebook 04 は統合モードによる新規環境一括構築の代替です。"
        "Notebook 05 は既存データへの分析拡張です。"
    ) if context.is_unified_guide else (
        "Core は Notebook 01 と Notebook 02 の 2 本だけを使います。Notebook 03 は Ontology 作成の代替、"
        "Notebook 04 は環境一括構築の代替、Notebook 05 は既存データへの分析拡張です。"
    )
    builder.body(
        setup_path +
        "同じ成果物に 01 → 02 → 03 → 04 → 05 を順番に適用する手順ではありません。"
        "Core の完成条件を確認してから、付録 D の前提に合う経路を選んでください。"
    )
    _chapter_01_outcomes(builder, context, public_documents_only=public_documents_only)


def _legacy_architecture_figure(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.figure(
        context.diagrams["system-data-flow"]["png"],
        caption=(
            "v2.7.0 のシステムとデータフロー。青の実線が静的経路（静的シード → Notebook 01 → Lakehouse）、"
            "橙の破線が増分経路（増分 CSV → OneLake FileCreated → Pipeline → Eventhouse、Pipeline のみ）、"
            "緑が Ontology のバインディング、濃緑が Notebook 02 のメタデータ、青緑が評価と公開。"
            "灰の破線で囲まれた下段は Optional で、Notebook 04 は全環境の一括作成（増分経路は Pipeline のみ）。"
        ),
        alt_text=(
            "システムとデータフローの全体図。上段の静的経路は青の実線で、静的シード CSV が Notebook 01 を通って "
            "Lakehouse の ot_ テーブル群になる。中段の増分経路は橙の破線で、増分 CSV 3 本が OneLake の "
            "FileCreated トリガーで Data Pipeline を起動し、Eventhouse の DonationEvents テーブルと "
            "マテリアライズドビューに入る。増分の経路は Pipeline のみで、ほかの取り込み経路はない。"
            "中央の Ontology は緑で、Lakehouse の静的バインディングと Eventhouse の time-series バインディングを受け取り、"
            "濃緑の Notebook 02 がセマンティックメタデータを登録する。右側では Lakehouse (SQL)、Eventhouse (KQL)、"
            "Ontology (GQL) の 3 ソースが Data Agent に接続され、各ソースに「層をまたぐ加算と JOIN の発明は禁止」"
            "という注意が付く。青緑の枠は 10 問の評価に合格したあと公開し、スモークテストを経て最小権限で共有する流れ。"
            "最下段は灰の破線で囲まれた Optional 領域で、Core の完了後に扱い参加者フローには含めない。"
            "Notebook 03 は Ontology 作成の代替、Notebook 04 は全環境を一括作成し増分経路は Pipeline のみ、"
            "Notebook 05 と Power BI はレポートと可視化、UDF と Code Interpreter は計算と分析の拡張。"
        ),
        max_height_cm=11.5,
    )
    builder.callout(
        "note",
        "この図は教材用の full Ontology を使う標準コース（Core）の経路です。"
        "第 16.9 節の AI 参照構成は、このモデルを残して別の path-only Ontology と Data Agent を作る Optional です。"
        "Notebook 04 の `ENABLE_AI_REFERENCE_ARCHITECTURE=False` が標準コースの既定であり、"
        "True にする場合は専用 bundle と hash を確認します。選んだ構成に対応する手順とソース選択を使ってください。",
        title="標準コースと AI 参照構成を選び分ける",
    )



def _chapter_01_outcomes(
    builder: DocumentBuilder, context: RuntimeContext, *, public_documents_only: bool = False
) -> None:
    expected = context.expected
    increment = context.expected_increment
    builder.table(
        ["作業", "区分", "章"],
        [list(row) for row in gc.core_scope_rows(context)],
        caption="Core と Optional の切り分け",
        widths=(4.0, 1.0, 1.2),
    )
    builder.table(
        ["到達点", "確認方法"],
        [
            [
                f"静的 Donation {num(expected['donationRows'])} 件 / {yen(expected['totalDonationAmountYen'])}が Lakehouse にある",
                "Notebook 01 の READY 出力と第 10 章の件数ゲート",
            ],
            [
                f"Ontology に {context.ontology_contract['entityTypes']} Entity / "
                f"{context.ontology_contract['relationshipTypes']} Relationship がある",
                "Entity type details と Instances の件数照合",
            ],
            [
                f"ノード合計 {num(expected['nodeTotal'])} / エッジ合計 {num(expected['edgeTotal'])}",
                "付録 A の期待値表",
            ],
            [
                f"Eventhouse に raw {num(increment['rawRows'])} 行 / "
                f"一意 EventID {num(increment['uniqueEventIds'])} / 重複 {num(increment['duplicateEventIds'])}",
                "第 13 章の KQL Queryset",
            ],
            [
                f"Ontology に {context.metadata_object_count} 件のセマンティックメタデータが登録されている",
                "Notebook 02 の適用後サマリー",
            ],
            [
                "3 ソースの Data Agent が 10 問の held-out テストに合格する",
                "第 17 章の評価基準とガイド内の記録方法"
                if public_documents_only else "第 17 章と Test 10 記録票",
            ],
        ],
        caption="Core 完了時に満たしている状態",
        widths=(3.0, 2.0),
    )
    builder.callout(
        "gate",
        "item の作成・配置、Notebook の完了、トリガーによる自動起動、Data Agent の応答、公開後の動作は"
        "別々に検証します。定義の作成成功やオフライン検証だけでは Core 完了になりません。"
        "未実施の工程は「未実施」、権限やサービス制約で進めない工程は「ブロック」として、理由を残してください。"
        "各工程は、実際に選んだ配置先と設定に対して確認してください。",
        title="配置できたことと、動作を確認できたことを分ける",
    )


def _chapter_02_mental_model(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("2. DBA・BI エンジニアのための思考の切り替え", 1)
    builder.body(
        "RDB とセマンティックモデルの経験は Ontology 設計でそのまま活きます。ただし目的が違います。"
        "RDB は「正しく保存する」ため、BI セマンティックモデルは「速く正しく集計する」ため、"
        "Ontology は「業務上の意味を宣言し、人とエージェントが同じ理解で辿れるようにする」ためにあります。"
    )
    builder.figure(
        context.diagrams["rdb-bi-ontology-mental-model"]["png"],
        caption="RDB・BI セマンティックモデル・Ontology の役割の違い。三者は置き換えではなく積み重ねの関係にある。",
        alt_text=(
            "3 列の比較図。左列は RDB で、テーブル、主キー、外部キー、正規化、整合性を示す。"
            "中央列は BI セマンティックモデルで、ファクト、ディメンション、メジャー、スタースキーマ、"
            "フィルター伝播を示す。右列は Ontology で、Entity Type、Property、Relationship Type、"
            "ビジネスグラフ、意味と境界の宣言を示す。下部に、三者は置き換えではなく積み重ねであることを示す帯がある。"
        ),
        max_height_cm=11.0,
    )
    builder.table(
        ["観点", "RDB", "BI セマンティックモデル", "Ontology"],
        [list(row) for row in gc.MENTAL_MODEL_ROWS],
        caption="3 つのモデルの比較",
        widths=(1.0, 2.0, 2.0, 2.2),
    )

    builder.heading("2.1 「JOIN できる」と「関係が意味を持つ」は違う", 2)
    builder.body(
        "RDB では、列の型と値が合えば JOIN できます。BI では、リレーションシップを引けばフィルターが伝播します。"
        "しかし Ontology の Relationship は「業務としてそう主張してよいか」を宣言します。"
        "たとえば Supplier と Gift は結べますが、その関係が意味するのはカタログ登録であって、"
        "発送でも売上配賦でもありません。この「証明しないこと」を宣言できるかどうかが、"
        "エージェントの回答精度を決めます。"
    )
    builder.table(
        ["概念", "意味", "設計上の注意"],
        [list(row) for row in gc.RELATIONSHIP_SEMANTICS_ROWS],
        caption="外部キー・フィルター方向・Relationship 方向の違い",
        widths=(1.4, 2.6, 3.0),
    )

    builder.heading("2.2 移行時によくある誤解", 2)
    builder.table(
        ["よくある思い込み", "実際", "対処"],
        [
            [
                "テーブルの数だけ Entity を作ればよい",
                "業務上の主語にならないテーブルは Entity にしない",
                "第 3 章のパターン表で分類してから作る",
            ],
            [
                "外部キーはすべて Relationship にする",
                "意味のない経路はノイズになり、誤った多段推論を招く",
                "業務的に意味のある経路だけを選ぶ",
            ],
            [
                "集計はすべて明細から計算すればよい",
                "複合粒度は二重集計の温床になる",
                "複合粒度のみメトリック Entity として独立させる",
            ],
            [
                "同義語や説明は後から足せばよい",
                "曖昧語の解決はモデルの一部であり、回答精度に直結する",
                "設計時に境界と同義語を宣言する",
            ],
            [
                "リアルタイムのイベントも明細に入れればよい",
                "粒度が違うデータを混ぜると件数が意味を失う",
                "観測は time-series として分離する",
            ],
        ],
        caption="RDB・BI からの移行でつまずきやすい点",
        widths=(2.0, 2.6, 2.4),
    )


def _chapter_03_method(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("3. RDB から Ontology への設計手順", 1)
    builder.body(
        "この章は、既存の RDB やセマンティックモデルを持っている読者が、"
        "自分のドメインで Ontology を設計するための手順です。埋めれば終わるマッピング表ではなく、"
        "「何を根拠に、どちらを選ぶか」という判断の手順として書いています。"
    )

    builder.heading("3.1 12 ステップ", 2)
    builder.bullets(gc.DESIGN_STEPS, numbered=True)
    builder.callout(
        "note",
        "ステップ 10 が「バインドは最後」である点が重要です。物理列に合わせて概念を決めると、"
        "ソースを差し替えた瞬間に業務語彙が壊れます。",
    )

    builder.heading("3.2 粒度・業務識別子・代理キー", 2)
    builder.body(
        "設計の最初に決めるのは粒度です。粒度を 1 文で書けない概念は、まだ設計が決まっていません。"
        "次に、業務側が会話で使う安定した識別子と、実装都合の代理キー、そして表示名を分離します。"
    )
    builder.table(
        ["用語", "定義", "本データセットの例", "設計上の扱い"],
        [list(row) for row in gc.GRAIN_ROWS],
        caption="粒度と識別子の整理",
        widths=(1.0, 2.0, 2.0, 2.0),
    )

    builder.heading("3.3 ソース構造からパターンへの対応", 2)
    builder.body(
        "RDB のテーブルは、そのままでは Ontology の構成要素になりません。"
        "次の表は、ソース側の構造を Ontology のどのパターンへ写すかの対応です。"
    )
    builder.table(
        ["ソース側の構造", "Ontology のパターン", "判断の根拠", "本データセットの例"],
        [list(row) for row in gc.PATTERN_ROWS],
        caption="ソース構造から Ontology パターンへの対応",
        widths=(2.0, 1.6, 2.4, 2.0),
    )

    builder.heading("3.4 判定木（ソース構造から Ontology 構成要素へ）", 2)
    builder.body(
        "迷ったときは次の判定木を上から順にたどります。判定は 7 段あり、"
        "1 つのソース構造につき 1 回だけ通して、最初に当てはまった結論を採用します。"
    )
    builder.table(
        ["#", "判定", "はいのときの結論"],
        [
            ["1", "監査・制御・技術メタデータ専用か", "除外（Ontology に持ち込まない）"],
            ["2", "既存エンティティに対し 1 件 1 値か", "Property（既存 Entity Type の属性）"],
            ["3", "2 つの外部キーだけの純粋な中間表か", "Relationship の文脈化（コンテキスト表）"],
            ["4", "独自の属性・ライフサイクルを持つ中間表か", "連関エンティティ（Associative Entity）"],
            ["5", "複合粒度の事前集計か", "メトリック / フロー エンティティ"],
            ["6", "安定した識別子・金額・時刻・状態を持つ取引か", "トランザクションエンティティ"],
            [
                "7",
                "既存エンティティへの時刻付き観測か",
                "事象自体を業務対象として問い合わせるならイベントエンティティ、"
                "そうでなければ time-series バインディング",
            ],
            [
                "—",
                "いずれにも当てはまらず、独立した業務識別子を持つ",
                "マスター / ディメンションの Entity Type",
            ],
        ],
        caption="判定木の 7 段と、それぞれの結論",
        widths=(0.35, 2.75, 3.5),
        font_size=8.8,
    )
    builder.callout(
        "note",
        "判定 4 を飛ばさないでください。2 つの外部キーだけに見える中間表でも、"
        "登録日・状態・契約期間などの独自属性やライフサイクルを持つなら、"
        "それは Relationship の文脈化ではなく連関エンティティです。"
        f"本ワークショップの `{context.relationship('SupplierProvidesGift').mapping_table}` は"
        "独自属性を持たないため、判定 3 で止まります。",
        title="判定 3 と判定 4 の分かれ目",
    )
    builder.figure(
        context.diagrams["rdb-to-ontology-decision-tree"]["png"],
        caption=(
            "1 つのソース構造を 7 段の判定で振り分ける判定木。結論は除外、Property、"
            "Relationship の文脈化、連関エンティティ（Associative Entity）、"
            "メトリック / フロー エンティティ、トランザクションエンティティ、"
            "イベントエンティティ（Event Entity）、time-series バインディング、"
            "マスター / ディメンションのいずれか。"
        ),
        alt_text=(
            "判定木の図。候補となるソース構造を 1 つ取り上げ、7 段の判定を順に通す。"
            "判定 1 は監査・制御・技術メタデータ専用かで、該当すれば除外。"
            "判定 2 は既存エンティティに対し 1 件 1 値かで、該当すれば Property。"
            "判定 3 は 2 つの外部キーだけの純粋な中間表かで、該当すれば Relationship の文脈化。"
            "判定 4 は独自の属性やライフサイクルを持つ中間表かで、該当すれば連関エンティティ。"
            "判定 5 は複合粒度の事前集計かで、該当すればメトリック / フロー エンティティ。"
            "判定 6 は安定した識別子と金額と時刻と状態を持つ取引かで、該当すればトランザクションエンティティ。"
            "判定 7 は既存エンティティへの時刻付き観測かで、事象自体を業務対象として問い合わせる場合は"
            "イベントエンティティ、そうでなければ time-series バインディング。"
            "いずれにも当てはまらない独立した業務識別子を持つものはマスター / ディメンションのエンティティ型。"
            "判定は菱形、結論は角丸の箱、除外は赤の破線枠、集計専用は二重枠、時系列と事象は橙で示されている。"
        ),
        max_height_cm=12.0,
    )

    builder.heading("3.5 Relationship の向きとカーディナリティ", 2)
    builder.body(
        "Relationship は、起点（Origin）と終点（Target）を選んだ時点で業務上の主張になります。"
        "「自治体は都道府県に属する」は Municipality → Prefecture であり、逆ではありません。"
        "逆方向の質問（ある都道府県に属する自治体の一覧）は、宣言された向きを保ったまま逆トラバースで答えます。"
    )
    builder.bullets(
        (
            "向き：業務の主語と目的語をそのまま写す。実装の都合で反転させない。",
            "カーディナリティ：1 側と多側を業務ルールとして宣言する（例：1 自治体は必ず 1 都道府県に属する）。",
            "否定的意味：その関係が証明しないことを明記する（例：カタログ登録は発送ではない）。",
            "集計ガード：どの経路で件数・金額を集計してよいかを宣言する。",
            "多対多：橋を通した金額集計は、明示的な配賦ルールがない限り禁止する。",
        )
    )

    builder.heading("3.6 メトリック Entity にするかどうか", 2)
    builder.table(
        ["対象", "選択", "理由"],
        [list(row) for row in gc.metric_decision_rows()],
        caption="集計値をどこに置くかの判断",
        widths=(2.2, 1.8, 3.0),
    )

    builder.heading("3.7 time-series バインディングにするか、イベント Entity にするか", 2)
    builder.table(
        ["条件", "選択", "理由"],
        [list(row) for row in gc.timeseries_decision_rows()],
        caption="時刻付き観測の扱いの判断",
        widths=(2.4, 1.6, 3.0),
    )
    builder.callout(
        "gate",
        "本ワークショップは time-series バインディングを選びます。したがって Data Agent が参照する集約ビューには "
        "EventID が存在せず、重複排除後の件数を「証明する」ことはできません。"
        "この制約は第 17 章のテスト 7 で明示的に確認します。",
    )

    builder.heading("3.8 アンチパターン", 2)
    builder.table(
        ["アンチパターン", "何が起きるか", "対処"],
        [list(row) for row in gc.ANTIPATTERN_ROWS],
        caption="Ontology 設計のアンチパターン",
        widths=(2.0, 2.6, 2.4),
    )

    builder.heading("3.9 設計の検証項目", 2)
    builder.bullets(
        (
            "すべての Entity Type にキーがあり、キーが一意である。",
            "すべての Relationship に方向・カーディナリティ・否定的意味が宣言されている。",
            "外部キーが解決でき、件数が期待値と一致する。",
            "代表的な多段経路が意図どおり辿れる。",
            "曖昧語（同名・同義語）が ID で解決できる。",
            "モデル外の質問に対して、境界を答えられる。",
        )
    )


def _chapter_04_rationale(builder: DocumentBuilder, context: RuntimeContext) -> None:
    expected = context.expected
    builder.heading("4. Furusato Ontology の設計根拠", 1)
    builder.body(
        "第 3 章の手順を、このワークショップのドメインに適用した結果が次のモデルです。"
        "なぜこの形になったのかを、選ばなかった選択肢とあわせて説明します。"
    )
    builder.figure(
        context.diagrams["furusato-ontology-layers"]["png"],
        caption=(
            "上段が「基幹エンティティ / Core entities (7)」（マスタ 6 + トランザクション 1）、"
            "下段が「集計層 / Metric / Flow entities (3)」。"
            f"{context.ontology_contract['relationshipTypes']} 本の有向 Relationship と、"
            "Municipality だけが持つ time-series バインディングを示す。"
        ),
        alt_text=(
            "Furusato Ontology の全体図。上段の帯は「基幹エンティティ Core entities (7)」で、"
            "マスタ 6 種類の Prefecture、Municipality、Donor、GiftCategory、Gift、Supplier と、"
            "トランザクション 1 種類の Donation から成り、有向の矢印で結ばれている。"
            "下段の帯は「集計層 Metric / Flow entities (3)」で、MunicipalityCategoryMetric、"
            "PrefectureCategoryMetric、PrefectureDonationFlow が並び、基幹エンティティとは別経路で接続される。"
            "合計 15 本の Relationship の向きが矢印で示されている。"
            "Municipality だけが Eventhouse からの時系列バインディングを持ち、橙の破線で示される。"
            "Donor と Supplier を直接つなぐ関係は存在せず、赤い破線とバツ印で否定されている。"
            "正しい経路は Supplier から Gift、Donation から Gift、Donor から Donation である。"
        ),
        max_height_cm=11.5,
    )
    builder.body(
        f"10 の Entity Type は 7 + 3 に分かれます。7 は{gc.CORE_ENTITY_LAYER}で、"
        f"マスタ 6 種類（{'、'.join(gc.MASTER_ENTITIES)}）と"
        f"トランザクション 1 種類（{'、'.join(gc.TRANSACTION_ENTITIES)}）です。"
        f"残る 3 は集計層で、複合粒度の事前集計を持つメトリック 2 種類と、"
        f"方向を持つフロー 1 種類（{'、'.join(gc.AGGREGATE_ENTITIES)}）です。"
        "この 7 + 3 という分け方が、以降のすべての判断（どこで数えるか、何を足さないか）の基準になります。"
    )
    builder.table(
        ["層", "内訳", "Entity Type", "この層で答えること"],
        [
            [
                gc.CORE_ENTITY_LAYER,
                f"マスタ {len(gc.MASTER_ENTITIES)}",
                "、".join(gc.MASTER_ENTITIES),
                "何が存在するか／どうつながるか",
            ],
            [
                "",
                f"トランザクション {len(gc.TRANSACTION_ENTITIES)}",
                "、".join(gc.TRANSACTION_ENTITIES),
                "件数と金額の唯一の正式な集計経路",
            ],
            [
                "集計層（メトリック / フロー）",
                f"{len(gc.AGGREGATE_ENTITIES)}",
                "、".join(gc.AGGREGATE_ENTITIES),
                "複合粒度の事前集計値（再集計しない）",
            ],
        ],
        caption="10 Entity Type の 7 + 3 の内訳",
        widths=(1.9, 1.0, 2.6, 1.9),
        font_size=8.5,
    )

    builder.heading("4.1 10 の Entity を選んだ理由", 2)
    builder.table(
        ["Entity Type", "層", "キー", "インスタンス数", "選定理由"],
        gc.furusato_entity_rationale(context),
        caption="10 Entity Type の選定理由",
        widths=(1.6, 0.8, 1.3, 0.9, 4.0),
    )

    builder.heading("4.2 なぜ Donation は Entity なのか", 2)
    builder.body(
        "Donation は、安定した DonationId、金額、時刻、支払方法を持ち、Donor・Municipality・Gift の "
        "3 つの概念が交差する唯一の点です。属性として他エンティティに畳み込むと、"
        "「誰が」「どこへ」「何を選んで」という 3 方向の質問が同時に成立しなくなります。"
        "したがって Donation は独立したトランザクション Entity であり、"
        "本モデルにおける唯一のトランザクション粒度です。"
    )
    builder.callout(
        "design",
        f"件数と金額の正式な集計経路は Donation です。ほかのエンティティが持つ "
        f"{'/'.join(('StaticCount', 'TotalYen'))} 系の Property は、その粒度における事前集計であり、"
        "異なるスコープで再集計してはいけません。",
    )

    builder.heading("4.3 なぜ business_gifts は Entity ではないのか", 2)
    supplier_gift = context.relationship("SupplierProvidesGift")
    builder.body(
        "配布される `business_gifts.csv` は `BusinessID` と `GiftID` の 2 列だけを持つ橋です。"
        "行そのものに名前・状態・ライフサイクルがなく、業務会話で「その登録」を指し示す必要がありません。"
        f"したがって Entity にはせず、{supplier_gift.name} という Relationship のコンテキスト表として使います。"
        f"エッジ数は {num(context.edge_count(supplier_gift.name))} 本になります。"
    )
    builder.table(
        ["段階", "テーブル / ファイル", "列名", "備考"],
        [
            [
                "配布ソース CSV",
                "`business_gifts.csv`",
                "`BusinessID` / `GiftID`",
                "元システムの命名。事業者は Business と呼ばれている。",
            ],
            [
                "Notebook 01 が発行する Delta テーブル",
                f"`{supplier_gift.mapping_table}`",
                f"`{supplier_gift.origin_key_column}` / `{supplier_gift.target_key_column}`",
                "Ontology の語彙に合わせて Supplier へ改名し、Id 表記も統一する。",
            ],
            [
                "Relationship の設定値",
                f"{supplier_gift.name}",
                f"Origin key `{supplier_gift.origin_key_column}` / Target key `{supplier_gift.target_key_column}`",
                "第 9 章で入力するのはこちらの列名。",
            ],
        ],
        caption="`business_gifts.csv` と発行後テーブルの列名は同じではない",
        widths=(1.6, 1.6, 1.9, 2.3),
        font_size=8.5,
    )
    builder.callout(
        "note",
        f"第 9 章で Mapping table に `{supplier_gift.mapping_table}` を指定するとき、"
        f"Matched keys は `{supplier_gift.origin_key_column}` と `{supplier_gift.target_key_column}` です。"
        "CSV の `BusinessID` / `GiftID` を入力すると列が見つかりません。"
        "「業務上の同じもの」でも、層が変われば名前が変わります。",
    )
    builder.callout(
        "stop",
        "この橋は多対多です。1 つの Gift に複数の Supplier が登録されている場合、"
        "橋を通して DonationAmountYen を集計すると金額が重複計上されます。"
        "明示的な配賦ルールがない限り、この経路での金額集計は禁止です。",
    )

    builder.heading("4.4 なぜ Donor と Supplier を直接つながないのか", 2)
    builder.body(
        "「この寄付者はどの事業者から返礼品を受け取ったか」という質問は自然に見えますが、"
        "本データセットにその事実はありません。モデル化されている唯一の間接経路は次のとおりです。"
    )
    builder.code_block(
        "Supplier -SupplierProvidesGift-> Gift <-DonationSelectedGift- Donation <-DonorMadeDonation- Donor",
        language="Ontology のトラバース経路（カタログ登録と返礼品選択のみを証明する）",
    )
    builder.body(
        "この経路が証明するのは「その事業者がその返礼品をカタログ登録している」ことと"
        "「その寄付がその返礼品を選択した」ことだけです。発送元の特定にはなりません。"
        "直接の Donor–Supplier 関係を作ると、この区別が消え、エージェントが履行を断定します。"
    )

    builder.heading("4.5 受入 Prefecture と在住 Prefecture", 2)
    prefecture = context.entity("Prefecture")
    received = [p.name for p in prefecture.properties if p.name.startswith("PrefReceived")]
    resident = [p.name for p in prefecture.properties if p.name.startswith("PrefResident")]
    builder.body(
        "「東京の寄付」は 2 通りに読めます。受入（その都道府県の自治体が受け取った寄付）と、"
        "在住（その都道府県に住む寄付者が出した寄付）です。本モデルは両方を別の経路と別の Property として保持します。"
    )
    builder.table(
        ["読み方", "経路", "Prefecture の Property"],
        [
            [
                "受入（recipient）",
                "Donation -DonationToMunicipality-> Municipality -MunicipalityInPrefecture-> Prefecture",
                "、".join(received),
            ],
            [
                "在住（resident）",
                "Donation <-DonorMadeDonation- Donor -DonorLivesInPrefecture-> Prefecture",
                "、".join(resident),
            ],
        ],
        caption="受入と在住の分離",
        widths=(1.0, 3.4, 2.6),
    )
    builder.callout(
        "stop",
        "2 つの値は別の意味を持つため、決して足し合わせません。"
        "曖昧な質問に対しては、両方を提示するか、どちらの意味かを確認するのが正しい挙動です。",
    )

    builder.heading("4.6 なぜ Municipality だけが 2 つのバインディングを持つのか", 2)
    municipality = context.entity("Municipality")
    static_binding = municipality.static_binding
    timeseries_binding = municipality.timeseries_binding
    builder.body(
        "運用観測（8 月の増分）には Donor も Gift も Supplier も含まれていません。"
        "含まれるのは受入自治体・金額・時刻・実行メタデータだけです。したがって観測を接続できる唯一のエンティティが "
        "Municipality です。観測を新しいエンティティにせず、既存の Municipality に時間軸の測定値として"
        "バインドすることで、静的スナップショットの件数を汚さずに運用の動きを見られます。"
    )
    builder.table(
        ["バインディング", "種別", "ソース", "対象 Property", "タイムスタンプ列"],
        [
            [
                "静的バインディング",
                static_binding.binding_type,
                f"Lakehouse `{static_binding.source_table}`",
                f"{len(static_binding.column_map)} 件の静的 Property",
                "—",
            ],
            [
                "time-series バインディング",
                timeseries_binding.binding_type,
                f"Eventhouse `{timeseries_binding.source_table}`",
                "、".join(target for _, target in timeseries_binding.column_map),
                timeseries_binding.timestamp_column or "",
            ],
        ],
        caption="Municipality の 2 つのバインディング",
        widths=(1.4, 1.0, 1.8, 2.6, 1.0),
    )

    builder.heading("4.7 15 本の Relationship を選んだ理由", 2)
    builder.table(
        ["Relationship Type", "方向", "カーディナリティ / 粒度", "Mapping table", "エッジ数", "選定理由"],
        gc.furusato_relationship_rationale(context),
        caption="15 Relationship Type の選定理由",
        widths=(1.5, 1.6, 2.0, 1.3, 0.7, 2.4),
        font_size=8.0,
    )

    builder.heading("4.8 意味の境界（semantic boundary register）", 2)
    builder.body(
        "モデルは「何を主張するか」と同じくらい「何を主張しないか」が重要です。"
        "次の表は、本 Ontology が明示的に否定する解釈の一覧です。Data Agent の指示にも同じ境界が書かれています。"
    )
    builder.table(
        ["対象", "主張すること", "主張しないこと"],
        [list(row) for row in gc.semantic_boundaries(context)],
        caption="意味の境界の登録簿",
        widths=(1.8, 2.4, 3.0),
    )


# --------------------------------------------------------------------- part 2
def _chapter_05_prerequisites(builder: DocumentBuilder, context: RuntimeContext, facts: TestFacts) -> None:
    names = context.names
    builder.heading("5. 前提条件・命名規則・配布物", 1)

    builder.heading("5.1 前提条件", 2)
    builder.bullets(
        (
            "有料 F2 以上、または Fabric 有効の P1 以上の capacity を使用します。",
            "Fabric IQ の Ontology item と Data Agent が UI に表示されることを、管理者とともに確認します。",
            "Data Agent とソース Workspace を同一リージョンに配置します。",
            "参加者には対象 Workspace で item を作成できる Member または Contributor 相当の権限を付与します。",
            "共有相手には Data Agent だけでなく、参照元ソースの読み取り権限も必要です。",
            "静的バインディングには managed Delta テーブルを使い、Delta column mapping は有効にしません。"
            "OneLake Security の対応条件は現行の製品文書で確認し、実環境の設定状態とは分けて記録します（第 16.8 節）。",
            "キーは String または Integer を使用し、MunicipalityId は先頭ゼロを保持する 6 桁 String にします。",
        )
    )
    builder.callout(
        "note",
        "Core の所要時間は約 6〜8 時間です。10 問の held-out テストと記録に追加 1〜2 時間を見込み、"
        "標準は 2 日構成とします。Graph の更新、Data Agent の初期化、capacity の混雑により延びる場合があります。",
    )
    builder.callout(
        "note",
        "上の 7 項目はワークショップを実施するための前提です。"
        "同じ構成を実際の業務データに向けるときは、これに加えて権限・保持・処理される地域・"
        "顧客管理キー・消費といったプラットフォーム側の前提も確認が必要になります。"
        "確認すべき項目は付録 C.6 にまとめてあります。"
        "ワークショップの実施にあたって、C.6 の内容を先に整えておく必要はありません。",
        title="実施の前提と、本番で使うときの前提は別",
    )

    builder.heading("5.2 命名規則", 2)
    builder.body(
        "参加者ごとの空の専用 Workspace を基本とし、3 桁の Participant ID（PID）を item 名の末尾に付けます。"
        "既存 Workspace の指定 Folder を使う場合は、第 5.2.1 節の配置・名前解決の確認を先に行います。"
        "テーブル名は専用 Lakehouse 内で共通のため PID を付けません。"
    )
    builder.table(
        ["アイテム種別", "命名規則", "例（PID=001）"],
        [
            ["Lakehouse", names["lakehouse"], names["lakehouse"].replace("<PID>", "001")],
            ["Notebook 01", names["notebook"], "PID を付けない"],
            ["Notebook 02", names["ontologyMetadataNotebook"], "PID を付けない"],
            ["Ontology", names["ontology"], names["ontology"].replace("<PID>", "001")],
            ["Eventhouse / KQL DB", names["eventhouse"], names["eventhouse"].replace("<PID>", "001")],
            ["KQL テーブル", "DonationEvents", "DonationEvents"],
            ["Data Pipeline", names["pipeline"], names["pipeline"].replace("<PID>", "001")],
            ["Activator（トリガー用）", names["activator"], names["activator"].replace("<PID>", "001")],
            ["Data Agent", names["dataAgent"], names["dataAgent"].replace("<PID>", "001")],
        ],
        caption="参加者用の命名規則",
        widths=(1.6, 2.2, 2.0),
    )
    builder.callout(
        "stop",
        "Participant ID は 001〜999 の 3 桁文字列です。000、空文字、4 桁以上は Notebook 01 が停止します。",
    )

    builder.heading("5.2.1 既存 Workspace の指定 Folder に配置する場合", 3)
    builder.body(
        "開始前に対象の Workspace 名・ID、Folder のパス・ID、PID を記録します。"
        "Fabric の Folder は item の整理単位であり、Lakehouse 内の `Files/increment` とは別物です。"
        "Folder は Workspace の権限を継承するため、専用 Workspace と同じ権限分離にはなりません。"
    )
    builder.callout(
        "stop",
        "実行先の Workspace / Folder は、配布物の参照例から推測せず、自分に割り当てられた場所を確認します。"
        "EXPECTED_WORKSPACE_NAME には、現在選んだ Workspace の実際の表示名を設定します。"
        "URL の `subfolderId` が数値の場合は REST の `folderId`（GUID）として使わず、"
        "UI の階層と API の Folder 一覧を突き合わせて対象を確定します。"
        "一意に確定できるまで書き込まず、別 Folder の既存 item で代用しません。",
        title="実行先の Workspace と Folder を確定する",
    )
    builder.bullets(
        (
            "対象 Folder を開いてから［新規］や Notebook のインポートを行います。"
            "ホームや作成ハブから作ると Workspace 直下に置かれるため、作成後にも配置先を確認します。",
            "既存 item を Folder 外も含めて確認します。Notebook 02 と単独の Notebook 03 は、"
            "参照する item 名を Workspace 全体から完全一致で解決します。Folder が違っても同名なら安全とは限りません。"
            "他の実習と衝突する場合は停止し、既存 item を削除・改名して回避しません。",
            "Notebook 03 の TARGET_FOLDER_NAME は作成先だけの指定です。Notebook 04 は自分自身の Folder を"
            "作成先にするため、先に対象 Folder へ配置します。Workspace 直下から実行してはいけません。"
            "EXPECTED_WORKSPACE_NAME を持つ Notebook では対象 Workspace 名も設定します。",
            "作成後の item ID、親 item ID、最終 Folder を実環境で確認して記録します。"
            "自動生成される KQL Database・SQL analytics endpoint・GraphModel も親との対応を確認します。"
            "例の ID や表示名だけから ID を推測して接続先を埋めません。",
        ),
        numbered=True,
    )
    builder.callout(
        "stop",
        "指定 Folder 外の既存 item は変更しません。自動生成された item が想定外の場所にある場合は、"
        "今回作成した ID と親子関係を確認してから、対応する移動手順で配置を整えます。"
        "移動できないものは例外として記録し、すべてが指定 Folder 内にあると報告しません。"
        "API が長時間操作を返した場合も、完了状態と実体の再取得を確認するまでは成功扱いにしません。",
        title="作成先と参照先を ID で確認する",
    )

    builder.heading("5.3 配布物", 2)
    seed_rows = [
        [entry["file"], num(entry["rows"]), entry["header"].split(",")[0], "静的シード"]
        for entry in context.seed_files
    ]
    increment_rows = [
        [entry["file"], num(entry["rows"]), "EventID", "2026 年 8 月増分"]
        for entry in context.increment_files
    ]
    builder.table(
        ["ファイル", "行数", "先頭列", "用途"],
        seed_rows + increment_rows,
        caption=f"配布 CSV（静的 {len(context.seed_files)} + 増分 {len(context.increment_files)} = {context.csv_count} ファイル）",
        widths=(2.4, 0.8, 1.4, 1.6),
    )
    builder.bullets(
        (
            f"`workshop/v{context.version}/data/SHA256SUMS.txt` と `dataset-manifest.json` で "
            f"{context.csv_count} 個の CSV の完全性を確認します。",
            (
                f"Notebook は `workshop/v{context.version}/notebooks` にあります。手動経路は Notebook 01 / 02 と"
                "共有ヘルパースクリプト、一括構築の代替は統合モードの Notebook 04 を使います。"
            ) if context.is_unified_guide else
            f"Notebook は `workshop/v{context.version}/notebooks` にあります。Core は Notebook 01 と 02 のみ使用します。",
            f"Eventhouse の管理コマンドは `workshop/v{context.version}/kql/Furusato_Eventhouse_Setup_v{context.version}.kql` です。",
            f"Data Agent のグローバル指示は `{context.guide_instruction_relative_path}` です。",
        )
    )
    builder.body(
        (
            "次の配布物には、主経路で使う完全な Ontology 定義と共有ヘルパー、Optional の分析資産が含まれます。"
            "provisioning 配下の統合プロファイルと SQL/KQL は第 16.2 節でも使うため、"
            "一括構築を選ばない場合も準備してください。"
        ) if context.is_unified_guide else
        "Core では使いませんが、参照用または Optional 用として次のファイルも配布されています。"
        "どこで使うかを対応する付録とあわせて示します。"
    )
    builder.table(
        ["パス", "内容", "使う場面"],
        [
            [
                f"`workshop/v{context.version}/ontology/`",
                "Ontology の完全定義テンプレートとセマンティックメタデータ",
                "第 15 章（メタデータの内容）／付録 D.1（一括作成）",
            ],
            [
                f"`workshop/v{context.version}/provisioning/`",
                "一括構築で使う bundle 定義と payload マニフェスト",
                "付録 D.2（Notebook 04）",
            ],
            [
                f"`workshop/v{context.version}/powerbi/`",
                "Power BI プロジェクト（PBIP：レポートとセマンティックモデル）",
                "付録 D.3（Notebook 05 の Direct Lake）",
            ],
            [
                f"`{context.udf_relative_path}`",
                "Optional の User data function（2,000 円ルールの機械的な例示）",
                "付録 D.4",
            ],
            [
                f"`workshop/v{context.version}/variable-library-template/`",
                "Variable Library のテンプレート（変数・設定・値セット）",
                "付録 D.5",
            ],
            [
                "`tools/powerbi/`",
                "Power BI プロジェクトを配置するための補助スクリプト",
                "付録 D.3（ファシリテーター向け）",
            ],
            [
                "（配布物ではない）",
                "ガバナンス・責任ある AI・コストの前提と、公開ドキュメントへのリンク",
                "付録 C.6 と付録 E",
            ],
        ],
        caption="Optional・参照用の配布物と、対応する付録",
        widths=(2.4, 2.4, 2.2),
        font_size=8.5,
    )
    builder.callout(
        "note",
        "Donor・Supplier・Gift・Donation はすべて架空の合成データです。実在の人物・取引として扱わず、"
        "実データと結合しません。都道府県・自治体の名称とコードは行政区域の参照ラベルです。",
        title="合成データ",
    )

    builder.heading("5.4 2026 年 8 月の観測窓と JST 境界", 2)
    increment = context.expected_increment
    calendar = facts.observation.calendar
    builder.body(
        f"増分 3 ファイルの観測時刻（`DonatedAt`）はすべて UTC で、"
        f"{increment['observationWindowUtc']['from']} から {increment['observationWindowUtc']['to']} の範囲に収まります。"
        f"この期間は UTC の {calendar.first_utc_day} から {calendar.last_utc_day} までの "
        f"{calendar.utc_day_count} 日間で、欠測日はありません。"
    )
    builder.table(
        ["項目", "値", "備考"],
        [
            ["観測窓の開始（UTC）", increment["observationWindowUtc"]["from"], "1 本目の最初の観測"],
            ["観測窓の終了（UTC）", increment["observationWindowUtc"]["to"], "3 本目の最後の観測"],
            [
                "UTC の日数",
                f"{calendar.utc_day_count} 日（{calendar.first_utc_day} 〜 {calendar.last_utc_day}）",
                "欠測日なし",
            ],
            [
                "1 UTC 日あたりの行数（raw）",
                f"{num(calendar.min_rows)} 〜 {num(calendar.max_rows)} 行",
                f"最小 {calendar.min_rows_day}、最大 {calendar.max_rows_day}",
            ],
            [
                "1 UTC 日あたりの行数（重複排除後）",
                f"{num(calendar.dedup_min_rows)} 〜 {num(calendar.dedup_max_rows)} 行",
                f"{calendar.duplicate_day} は raw {num(calendar.duplicate_day_raw_rows)} 行のうち"
                f"追加重複 {num(calendar.duplicate_extra_rows_on_day)} 行"
                f"（{num(calendar.duplicate_event_ids_on_day)} EventID・該当 "
                f"{num(calendar.duplicate_group_rows_on_day)} 行）を除いて "
                f"{num(calendar.duplicate_day_dedup_rows)} 行",
            ],
            [
                "公開時刻（PublishedAtUtc）",
                "、".join(increment["publishedAtUtc"]),
                "3 本目の公開時刻のみ 2026 年 9 月 1 日",
            ],
            [
                "JST 換算の暦日",
                f"{calendar.jst_day_count} 日（{calendar.first_jst_day} 〜 {calendar.last_jst_day}）",
                "UTC + 9 時間のため 1 日多くなる",
            ],
        ],
        caption="観測窓・日次分布・時刻の扱い",
        widths=(1.8, 2.4, 2.4),
    )

    builder.heading("5.4.1 UTC 日次分布", 3)
    builder.body(
        f"raw {num(facts.observation.raw_rows)} 行の UTC 日次内訳は次のとおりです。"
        f"毎日 {num(calendar.min_rows)} 〜 {num(calendar.max_rows)} 行の範囲に収まり、"
        f"欠測日はありません。ただし {calendar.duplicate_day} には追加重複 "
        f"{num(calendar.duplicate_extra_rows_on_day)} 行が集中するため、raw の件数が多くなっています。"
        "第 13 章の検証で同じ分布が得られることを確認します。"
    )
    day_rows = [
        [
            entry["date"],
            num(entry["rows"]),
            yen(entry["amount"]),
            num(entry["dedupRows"]),
            (
                f"追加重複 {num(calendar.duplicate_extra_rows_on_day)} 行"
                f"（{num(calendar.duplicate_event_ids_on_day)} EventID・該当 "
                f"{num(calendar.duplicate_group_rows_on_day)} 行）"
                if entry["date"] == calendar.duplicate_day
                else ""
            ),
        ]
        for entry in calendar.utc_days
    ]
    day_rows.append(
        [
            "合計",
            num(sum(entry["rows"] for entry in calendar.utc_days)),
            yen(sum(entry["amount"] for entry in calendar.utc_days)),
            num(sum(entry["dedupRows"] for entry in calendar.utc_days)),
            "",
        ]
    )
    builder.table(
        ["UTC 日", "raw 行数", "raw 金額", "重複排除後の行数", "備考"],
        day_rows,
        caption=(
            f"2026 年 8 月の UTC 日次分布（{calendar.utc_day_count} 日、"
            f"1 日あたり {num(calendar.min_rows)}〜{num(calendar.max_rows)} 行）"
        ),
        widths=(1.4, 1.1, 1.6, 1.6, 1.8),
        font_size=8.5,
    )
    builder.callout(
        "note",
        f"最大の {calendar.max_rows_day}（raw {num(calendar.duplicate_day_raw_rows)} 行）が突出して見えるのは、"
        f"配布データの重複 {num(calendar.duplicate_event_ids_on_day)} EventID がこの日に集中しているためです。"
        f"重複する EventID は 2 行ずつ存在するため、該当行は "
        f"{num(calendar.duplicate_group_rows_on_day)} 行、"
        f"重複排除で取り除かれる追加分はその半分の {num(calendar.duplicate_extra_rows_on_day)} 行です。"
        f"したがって raw {num(calendar.duplicate_day_raw_rows)} 行 − 追加重複 "
        f"{num(calendar.duplicate_extra_rows_on_day)} 行 = {num(calendar.duplicate_day_dedup_rows)} 行となり、"
        f"日次の上限は {num(calendar.dedup_max_rows)} 行になります。異常値ではありません。",
        title="8 月 11 日が多い理由（100 EventID・該当 200 行・追加 100 行）",
    )

    builder.heading("5.4.2 UTC 月末は JST では 9 月 1 日になる", 3)
    builder.body(
        "JST は UTC + 9 時間です。したがって UTC の 8 月 31 日 15:00 以降に観測された行は、"
        "日本時間では 9 月 1 日の朝に相当します。UTC で見れば 8 月の月末ですが、"
        "JST で日付を切ると 9 月 1 日の暦日が 1 日分現れます。これは仕様どおりの挙動であり、"
        "観測窓の外に出たわけではありません。"
    )
    builder.table(
        ["観点", "値", "意味"],
        [
            [
                "UTC 観測窓の末尾",
                f"{calendar.jst_rollover_from_utc} 〜 {calendar.jst_rollover_to_utc}",
                f"この {num(calendar.jst_rollover_rows)} 行が JST では {calendar.last_jst_day} に入る",
            ],
            [
                "JST に換算した暦日数",
                f"{calendar.jst_day_count} 日（{calendar.first_jst_day} 〜 {calendar.last_jst_day}）",
                f"UTC の {calendar.utc_day_count} 日より 1 日多い",
            ],
            [
                "3 本目の公開時刻",
                increment["publishedAtUtc"][2],
                "観測時刻ではなく、ファイルが公開された時刻",
            ],
        ],
        caption="UTC から JST への繰り上がり",
        widths=(1.6, 2.4, 2.6),
    )
    builder.callout(
        "gate",
        f"`PublishedAtUtc` の {increment['publishedAtUtc'][2]}（3 本目）と、JST で現れる "
        f"{calendar.last_jst_day} の {num(calendar.jst_rollover_rows)} 行は、"
        "どちらも想定どおりです。観測窓外エラーでも、取り込み漏れでもありません。"
        "`DonatedAt`（観測時刻）と `PublishedAtUtc`（公開時刻）は別の列であり、"
        "検証は必ず UTC の `DonatedAt` で行います。",
        title="「9 月の日付が出る」のは正常",
    )
