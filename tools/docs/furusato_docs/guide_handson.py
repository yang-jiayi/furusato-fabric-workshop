"""Hands-on chapters and appendices for the participant guide.

Kept in a separate module from :mod:`participant_guide` purely for readability;
``participant_guide`` imports and calls these builders in order.
"""

from __future__ import annotations

from . import guide_content as gc
from .context import RuntimeContext, num, yen
from .docx_kit import DocumentBuilder
from .facts import TestFacts
from .parameters import PARAMETER_COLUMNS, STALE_LEASE_GROUP, build_parameter_rows
from .tests10 import HeldOutTest

PARAMETER_WIDTHS = (1.7, 0.85, 1.35, 1.6, 2.5, 1.95, 2.1, 1.15)
PARAMETER_FONT = 8.0
PARAMETER_HEADER_FONT = 8.2


def chapter_pointer(builder: DocumentBuilder, chapter: str, extra: str = "") -> None:
    """Close an action chapter with a pointer into the troubleshooting table."""
    text = f"この章でつまずいたときは、第 19 章のトラブルシューティング表で「{chapter}」の行を確認してください。"
    # Always bind to the preceding block: a one-line pointer must never be the only
    # thing on a page.
    builder.callout("note", text + (f" {extra}" if extra else ""), title="うまくいかないときは", pull_up=True)

ENTITY_SCREENSHOTS = {
    "Municipality": "7-14",
    "Donor": "7-17",
    "GiftCategory": "7-20",
    "Gift": "7-23",
    "Supplier": "7-26",
    "Donation": "7-29",
    "MunicipalityCategoryMetric": "7-32",
    "PrefectureCategoryMetric": "7-35",
    "PrefectureDonationFlow": "7-38",
}

RELATIONSHIP_SCREENSHOTS = {
    "MunicipalityInPrefecture": "8-2",
    "DonorLivesInPrefecture": "8-4",
    "SupplierInPrefecture": "8-5",
    "GiftInCategory": "8-6",
    "MunicipalityCatalogsGift": "8-7",
    "SupplierProvidesGift": "8-8",
    "DonorMadeDonation": "8-9",
    "DonationToMunicipality": "8-10",
    "DonationSelectedGift": "8-11",
    "MunHasCategoryMetric": "8-12",
    "MunMetricForCategory": "8-13",
    "PrefHasCategoryMetric": "8-14",
    "PrefMetricForCategory": "8-15",
    "ResidencePrefHasFlow": "8-16",
    "FlowToRecipientPref": "8-17",
}

#: Captures excluded from the participant guide and the reason for each exclusion.
RETIRED_SCREENSHOTS = {
    "5-4": "the notebook header in the capture still shows a superseded workshop version",
    "5-7": "the notebook header in the capture still shows a superseded workshop version",
    "5-8": "the parameter cell in the capture still shows superseded defaults",
    "5-9": "the notebook header in the capture still shows a superseded workshop version",
    "5-11": "the capture shows notebook source, not the audit output its caption claimed",
    "8-18": "the notebook header in the capture still shows a superseded workshop version",
    "11-5": "Eventstream is not part of v2.7.0",
    "11-6": "Eventstream is not part of v2.7.0",
    "11-7": "Eventstream is not part of v2.7.0",
    "11-8": "Eventstream is not part of v2.7.0",
    "11-14": "participants never run the pipeline manually",
    "11-15": "the capture shows a manual pipeline run",
    "12-9": "the high-value notification exercise was removed from participant materials",
    "12-10": "the high-value notification exercise was removed from participant materials",
    "12-11": "the high-value notification exercise was removed from participant materials",
    "12-12": "the high-value notification exercise was removed from participant materials",
    "12-13": "the high-value notification exercise was removed from participant materials",
    "12-14": "the superseded controlled-event validation is not part of v2.7.0",
    "13-8": "not referenced by the v2.6 document",
    "13-13": "the instructions pane in the capture still shows superseded agent instructions",
    "13-14": "superseded user data function walkthrough",
    "13-15": "superseded user data function walkthrough",
    "13-16": "superseded user data function walkthrough",
    "13-17": "superseded user data function walkthrough",
    "13-22": "internal regression-case result",
    "13-23": "internal regression-case result",
    "13-24": "internal regression-case result",
    "13-25": "internal regression-case result",
    "13-26": "internal regression-case result",
    "13-27": "internal regression-case result",
    "13-28": "internal regression-case result",
    "13-29": "internal regression-case result",
    "13-30": "internal regression-case result",
    "13-31": "internal regression-case result",
    "13-32": (
        "the shipped capture of the publish dialog is a blank frame, and the only historical "
        "capture shows Runtime=Standard with superseded agent instructions, which contradicts the "
        "Core configuration; section 18 states the four dialog fields in text instead"
    ),
    "17-2": "internal candidate configuration history, not a participant procedure",
    "17-3": "internal candidate configuration history, not a participant procedure",
    "17-4": "internal candidate configuration history, not a participant procedure",
}


def _shot(builder: DocumentBuilder, tag: str, caption: str, alt: str, height: float = 9.6) -> int:
    """Place a carrier screenshot and return the figure number it was given.

    Returning the number lets prose cross-reference a figure by name without
    hard-coding a value that would drift the moment a figure is added earlier.
    """
    if tag in RETIRED_SCREENSHOTS:
        raise ValueError(f"figure {tag} is retired: {RETIRED_SCREENSHOTS[tag]}")
    builder.figure(
        builder.carrier.screenshot(tag),
        caption=caption,
        alt_text=alt,
        max_height_cm=height,
    )
    return builder.figure_number


def chapter_06_lakehouse(builder: DocumentBuilder, context: RuntimeContext) -> None:
    names = context.names
    notebook = context.notebooks["Notebook_01"]
    expected = context.expected
    builder.heading("6. Lakehouse の作成と Notebook 01", 1)

    builder.heading("6.1 Lakehouse を作成する", 2)
    builder.bullets(
        (
            f"指定 Folder がある場合は先にその Folder を開き、［新規］→［Lakehouse］で Name に {names['lakehouse']} を入力します。",
            "［Lakehouse schemas］が On であることを確認します。",
            "作成直後の Explorer に Tables と Files が表示されることを確認します。",
        ),
        numbered=True,
    )
    _shot(
        builder,
        "5-1",
        f"［新規］→［Lakehouse］で {names['lakehouse']} を作成する。",
        "Fabric の新規作成メニューから Lakehouse を選び、名前と Lakehouse schemas の設定を入力するダイアログ。",
    )
    _shot(
        builder,
        "5-2",
        "Lakehouse 作成直後の画面。Explorer に Tables と Files が表示される。",
        "Lakehouse の初期画面。左側の Explorer に Tables と Files のフォルダーが空の状態で表示されている。",
    )

    builder.heading("6.2 静的シード CSV をアップロードする", 2)
    builder.body(
        f"Files 領域に `Files/furusato/seed` フォルダーを作り、静的 {len(context.seed_files)} CSV を"
        "アップロードします。増分 CSV はここには置きません（第 13 章で別フォルダーに置きます）。"
    )
    _shot(
        builder,
        "5-3",
        f"`Files/furusato/seed` に静的 {len(context.seed_files)} CSV をアップロードした状態。",
        "Lakehouse の Files 配下 furusato/seed フォルダーに 8 個の CSV ファイルが並んでいる一覧画面。",
    )
    builder.body(
        "続けて、Files 直下に空のフォルダー `Files/increment` を作成します。"
        "ここには今は何も置きません。"
        f"1 本目の `{context.increment_files[0]['file']}` は第 12.4 節で、"
        f"残りの `{context.increment_files[1]['file']}` と `{context.increment_files[2]['file']}` は"
        "第 13 章でアップロードします。"
    )
    builder.callout(
        "note",
        "`Files/increment` を先に作っておく理由は 2 つあります。"
        "第 12.2 節の OneLake FileCreated トリガーは、購読するフォルダーが既に存在していないと "
        "`/Files/increment` を選べません。"
        "また、フォルダーを空のまま作っておくと、トリガーを Running にした直後に "
        "1 本目を置くだけで「アップロードしたファイルだけが取り込まれた」ことを確認できます。"
        "この時点で増分 CSV を置いてしまうと、トリガーがまだ無い状態でファイルだけが増え、"
        "第 12.4 節のゲートが成立しません。",
        title="Files/increment は空のまま作る",
    )

    builder.heading("6.3 Notebook 01 を取り込んで実行する", 2)
    builder.bullets(
        (
            "対象の Workspace / Folder で［Import］→［Notebook］→［From this computer］から Notebook 01 を取り込み、配置先を確認します。",
            f"Lakehouse pane に {names['lakehouse']} を追加し、Default（ピン）に設定します。",
            "先頭の Fabric parameter cell で PARTICIPANT_ID を自分の 3 桁 PID に変更します。ほかの既定値は変更しません。",
            "［Run all］を実行し、Session ready のあとセルが順に完了することを確認します。",
        ),
        numbered=True,
    )
    _shot(
        builder,
        "5-5",
        "［Import］→［Notebook］→［From this computer］で Notebook 01 を取り込む。",
        "Fabric のインポートメニューから Notebook をこのコンピューターから取り込む選択肢を表示している画面。",
    )
    _shot(
        builder,
        "5-6",
        "Notebook 01 のインポート完了。Workspace のアイテム一覧に Notebook として表示される。",
        "Workspace のアイテム一覧。Lakehouse と Notebook 01 が並んで表示されている。",
    )
    builder.callout(
        "note",
        "パラメーターセルの正しい値は次節の表が正です。Notebook の見た目は Fabric の更新で変わるため、"
        "画面ではなく表の既定値と一致しているかを確認してください。",
    )

    builder.heading("6.4 Notebook 01 のパラメーター", 2)
    builder.body(
        "Core の通常の実行で参加者が変更するのは PARTICIPANT_ID だけです。"
        "例外は stale lease からの回復で、そのときだけ次の 3 つを同時に設定します。"
        "それ以外のパラメーターは安全ゲートであり、既定値のまま実行します。"
        "Notebook 01 の全パラメーターはこの表が唯一の完全版で、"
        "付録 B には 5 Notebook の索引だけを置いています。"
    )
    builder.callout(
        "note",
        f"`{STALE_LEASE_GROUP[0]}`・`{STALE_LEASE_GROUP[1]}`・`{STALE_LEASE_GROUP[2]}` の 3 つは、"
        "通常の実行では触りません。前の実行が異常終了して lease が残った場合にだけ、"
        "3 つを同時に設定して回復します。1 つだけ設定しても回復は始まりません。"
        "この 3 つは Notebook 01 にしかありません。Notebook 02 に lease のパラメーターはなく、"
        "同時実行の制御には `EXCLUSIVE_APPLY_WINDOW_CONFIRMED` を使います（第 15.2 節）。",
        title="stale lease 回復用の 3 パラメーター（Notebook 01 のみ）",
    )
    builder.table(
        list(PARAMETER_COLUMNS),
        build_parameter_rows(context, "Notebook_01"),
        caption="Notebook 01 のパラメーター仕様（全項目）",
        widths=PARAMETER_WIDTHS,
        font_size=PARAMETER_FONT,
        header_size=PARAMETER_HEADER_FONT,
    )

    builder.heading("6.5 静的ゲート", 2)
    builder.body(
        "Notebook 01 は、ヘッダー順・件数・SHA-256・主キー・外部キー・型を検証してから "
        f"{len(expected['outputTableCounts'])} 本の ot_ テーブルを発行します。"
        "次の件数と金額が一致しない場合は先へ進まず、Notebook 01 を先頭から再実行してください。"
    )
    builder.table(
        ["出力テーブル", "期待行数"],
        [[table, num(count)] for table, count in expected["outputTableCounts"].items()],
        caption=f"Notebook 01 が発行する {len(expected['outputTableCounts'])} テーブルの期待行数",
        widths=(2.4, 1.0),
    )
    builder.table(
        ["契約", "期待値"],
        [
            ["Notebook バージョン", notebook.version],
            ["静的 Donation 行数", num(expected["donationRows"])],
            ["静的 Donation 合計金額", yen(expected["totalDonationAmountYen"])],
            ["寄付 0 件の Donor", num(expected["donorsWithoutDonations"])],
            ["受入 0 件の Municipality", num(expected["municipalitiesWithoutDonations"])],
            ["登録返礼品 0 件の Supplier", num(expected["suppliersWithoutGifts"])],
        ],
        caption="Notebook 01 完了後の必須ゲート",
        widths=(2.4, 2.0),
    )
    _shot(
        builder,
        "5-10",
        "Notebook 01 完了後の Tables と監査マニフェスト。",
        "Lakehouse の Tables に stg_ で始まるステージングテーブルと ot_ で始まる出力テーブル、"
        "監査テーブルが並び、ロードマニフェストの内容が表示されている画面。",
    )
    builder.callout(
        "gate",
        "0 件のレコードが LEFT JOIN で保持されていることも確認します。寄付が 0 件の Donor が "
        f"{num(expected['donorsWithoutDonations'])} 件、受入が 0 件の Municipality が "
        f"{num(expected['municipalitiesWithoutDonations'])} 件残っているのが正しい状態です。",
    )
    chapter_pointer(builder, "第 6 章")


def chapter_07_ontology(builder: DocumentBuilder, context: RuntimeContext) -> None:
    names = context.names
    builder.heading("7. Ontology を作成する", 1, new_page=False)
    builder.callout(
        "note",
        f"第 7〜15 章の対象は教材用 `{names['ontology']}` です。完成時の契約は "
        "10 Entity / 72 static Property / 1 time-series Property / 15 Relationship です。"
        + (
            "この完全モデルを主 Agent の唯一の connectedOntology とします。"
            "旧 AIPath は作成せず、この手順や Notebook 02 の対象にしません。"
            if context.is_unified_guide else
            "第 16.9 節の `ONT_Furusato_AIPath_<PID>` は別モデルであり、この手順や Notebook 02 の対象にしません。"
        ),
        title="この実習では full Ontology を保持する",
    )
    builder.bullets(
        (
            "［新規］→［Ontology (preview)］を選択します。",
            f"New Ontology ダイアログで {names['ontology']} を入力します。",
            "初回だけ表示される［Welcome to Ontology］を［Close］で閉じます。"
            "再表示が不要なら［Don't show again］を先に選びます。",
            "作成直後の Home configuration canvas と Explorer が表示されることを確認します。",
        ),
        numbered=True,
    )
    _shot(
        builder,
        "6-1",
        "［新規］→［Ontology (preview)］を選択する。",
        "Fabric の新規作成メニューで Ontology (preview) の項目が表示されている画面。",
    )
    _shot(
        builder,
        "6-2",
        f"New Ontology ダイアログで {names['ontology']} を入力する。",
        "New Ontology ダイアログに Ontology の表示名を入力している画面。",
    )
    _shot(
        builder,
        "6-3",
        "Ontology 作成直後の configuration canvas と Explorer。",
        "作成直後の Ontology 画面。中央に空の configuration canvas、左に Explorer が表示されている。",
    )
    _shot(
        builder,
        "6-4",
        "初回の［Welcome to Ontology］。必要に応じて［Don't show again］を選び、［Close］で閉じる。",
        "Ontology の初回案内ダイアログ。チュートリアルと Add entity type の案内、Don't show again、Close が表示されている。",
    )
    builder.callout(
        "note",
        "この時点ではまだ Entity も Relationship もありません。第 8 章と第 9 章で、"
        "第 4 章で決めた設計をそのまま手で作っていきます。手で作ることが目的なので、"
        "Optional の一括作成（付録 D）は Core を終えてから試してください。",
    )
    builder.callout(
        "stop",
        "作成メニューや Ontology の画面に、生成 AI が Ontology の作成を手伝う入口や、"
        "別の作り始め方が表示されることがあります。Core ではどれも使いません。"
        "第 8 章と第 9 章の手作業をそのまま続けてください。"
        "評価の観点として読みたい場合は付録 D.6 にまとめてあります。"
        "画面の見え方は更新されるため、本書では入口の名称や位置を固定しません。",
        title="別の入口が見えても Core では使わない",
        pull_up=True,
    )


def chapter_08_entities(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("8. 10 Entity Type の作成と静的バインディング", 1)
    builder.body(
        "Entity Type の作り方はすべて同じです。まず Prefecture で全手順を通し、"
        "残りの 9 件は同じ手順を Property 表に従って繰り返します。"
    )
    builder.callout(
        "note",
        "Entity Type の名前とカスタム Property の名前には、同じ公式の規則があります。"
        "1〜26 文字で、英数字・ハイフン・アンダースコアだけを使い、先頭と末尾は英数字にします。"
        "この規則は Entity Type の作成手順とデータバインディングの手順の両方に記載されています"
        "（付録 E の Create entity types と Bind data）。"
        "本ワークショップでは Entity Type の `MunicipalityCategoryMetric`、Property の "
        "`MunicipalityPrefAmountRank` と `MunicipalityStaticTotalYen` がいずれも 26 文字で、"
        "現在公開されている上限ちょうどです。"
        "表のとおりに入力すれば問題ありませんが、名前を長くする変更を思いついたときは、"
        "この 3 つが真っ先に規則から外れます。",
        title="Entity Type と Property の名前は 1〜26 文字",
    )

    builder.heading("8.1 共通手順（Prefecture で通しの操作を確認する）", 2)
    builder.bullets(
        (
            "canvas の［Add entity type］で Entity type name を入力します。",
            "作成されたカードから［View Entity Type details］を開きます。",
            "［Configure］タブで［Manage property bindings］を選びます。"
            "初回バインディングでは OneLake catalog が直接開く場合があります。",
            f"OneLake catalog の［Filter by keyword］に `{context.names['lakehouse']}` を入力し、"
            "対象 Lakehouse だけに絞ります。",
            "Lakehouse → Tables → dbo → 対象の ot_ テーブルの順に展開し、テーブル行を選択します。",
            "［Define entity type key］で Entity type key を定義し、同名の source column を対応付けます。",
            "表に記載した Property だけを mapping し、自動追加される `WorkshopGenerationId`"
            "（source column は `_WorkshopGenerationId`）を削除してから保存します。",
            "保存後に［Entity type updated successfully］が表示されたら、breadcrumb の Entity 名を選んで details に戻ります。",
            "［Choose display name property］で表示名 Property を選びます。",
            "Instances タブで件数とキー・表示名・Property の値を確認します。",
        ),
        numbered=True,
    )
    for tag, caption, alt in (
        ("7-1", "［Add entity type］で Entity type name に Prefecture を入力する。", "Add entity type ダイアログに Entity type name を入力している画面。"),
        ("7-2", "canvas に Prefecture カードが作成された状態。", "Ontology の canvas に Prefecture のカードが 1 つ表示されている画面。"),
        ("7-3", "［Configure］→［Manage property bindings］を開く。", "Entity type details の Configure タブで Manage property bindings を選択している画面。"),
        ("7-4", "［Filter by keyword］で対象 Lakehouse だけに絞る。", "OneLake catalog のキーワードフィルターで対象 Lakehouse を絞り込んでいる画面。"),
        ("7-5", "OneLake catalog で Lakehouse → Tables → dbo → ot_prefecture を選択する。", "OneLake catalog で Lakehouse の Tables と dbo schema を展開し、ot_prefecture 行を選択している画面。"),
        ("7-6", "［Define entity type key］で PrefectureId を定義し、同名の source column を対応付ける。", "Define entity type key で PrefectureId とその source column を設定している画面。"),
        ("7-7", "`WorkshopGenerationId` を削除し、表の Property だけを mapping して保存する。", "プロパティのマッピング一覧。自動追加された WorkshopGenerationId の行を削除している画面。"),
        ("7-8", "静的バインディングを保存したあとの Entity type details。", "保存後の Entity type details。Property source が Local、Data source が ot_prefecture と表示されている。"),
        ("7-9", "［Choose display name property］で表示名 Property を選ぶ。", "表示名として使う Property を選択するドロップダウン。"),
        ("7-11", "Prefecture の Instances。件数とキー・表示名・Property 値を確認する。", "Prefecture の Instances タブ。インスタンス数と各プロパティの値が一覧表示されている。"),
    ):
        _shot(builder, tag, caption, alt)
    builder.callout(
        "note",
        "現行 UI は［Save］後に details へ自動では戻りません。"
        "成功トーストを確認してから breadcrumb の Entity 名を選んで戻ります。"
        "Instances の Count は `1,741` のように 3 桁区切りで表示されます。",
        title="Save 後は breadcrumb で戻る",
    )

    builder.heading("8.2 10 Entity Type の一覧", 2)
    rows = []
    for entity in context.entities:
        binding = entity.static_binding
        rows.append(
            [
                entity.name,
                gc.entity_layer(entity.name),
                entity.key_property,
                entity.display_name_property,
                binding.source_table if binding else "",
                str(len(entity.properties)),
                num(context.node_count(entity.name)),
            ]
        )
    builder.table(
        [
            "Entity Type",
            "層",
            "Key property",
            "表示名 Property",
            "バインディング元テーブル",
            "Property 数",
            "期待インスタンス数",
        ],
        rows,
        caption=f"10 Entity Type とバインディング先（静的 Property 合計 {context.ontology_contract['staticProperties']} 件）",
        widths=(1.6, 1.4, 1.2, 1.3, 1.9, 0.75, 1.05),
        font_size=8.2,
    )

    builder.heading("8.3 Entity Type ごとの Property 一覧", 2)
    builder.body(
        "各 Entity Type の Property は次の表のとおりです。source column と Property 名は同名です。"
        "表にない列（自動追加される管理列を含む）はマッピングしません。"
    )
    builder.callout(
        "stop",
        "表の「業務上の役割（NB02 が登録）」「粒度（NB02 が登録）」と、各 Entity Type の英語 Description・"
        "同義語（synonyms）は、Ontology の UI に入力欄がありません。これらは "
        "`ontology-semantic-metadata.json` に宣言され、第 15 章の Notebook 02 が semanticEnrichment として"
        "一括登録する値です。第 8 章では入力せず、設計の意図を読むための参考として使ってください。"
        "第 15 章の適用後に Entity type details で登録内容を確認できます。",
        title="この列は UI の入力欄ではありません",
    )
    for entity in context.entities:
        binding = entity.static_binding
        builder.heading(f"8.3.{context.entities.index(entity) + 1} {entity.name}", 3)
        builder.body(f"{entity.description}（この説明文も NB02 が登録します）")
        property_rows = [
            [
                prop.name,
                prop.value_type,
                "キー" if prop.is_key else ("表示名" if prop.is_display_name else ""),
                prop.attributes.get("businessRole", ""),
                prop.attributes.get("grain", ""),
                prop.attributes.get("rankScope", "") or prop.attributes.get("keyEncoding", ""),
            ]
            for prop in entity.properties
        ]
        builder.table(
            [
                "Property",
                "型",
                "役割（UI で設定）",
                "業務上の役割（NB02 が登録）",
                "粒度（NB02 が登録）",
                "ランクのスコープ / キー書式",
            ],
            property_rows,
            caption=(
                f"{entity.name} の Property（バインディング元 `{binding.source_table if binding else ''}`、"
                f"期待インスタンス数 {num(context.node_count(entity.name))}）"
            ),
            widths=(2.0, 0.6, 0.8, 1.4, 1.4, 1.4),
            font_size=8.5,
            whole_token_columns=(0,),
        )
        ranks = [prop for prop in entity.properties if prop.attributes.get("rankScope")]
        if ranks:
            builder.body(
                "ランク列はいずれも row_number による決定的な順位です。同額でも順位は重複しません："
                + "／".join(
                    f"`{prop.name}` は {prop.attributes.get('rankSort', '')}"
                    for prop in ranks
                )
                + "。順位を報告するときは、必ず上表の「ランクのスコープ」を併記してください。"
            )
        if entity.synonyms:
            builder.body("同義語（NB02 が登録）：" + "、".join(entity.synonyms))
        tag = ENTITY_SCREENSHOTS.get(entity.name)
        if tag:
            _shot(
                builder,
                tag,
                f"{entity.name} の Instances。件数 {num(context.node_count(entity.name))} を確認する。",
                f"{entity.name} の Instances タブ。インスタンス数とキー、表示名、各プロパティの値が一覧表示されている。",
            )
    chapter_pointer(builder, "第 8 章")


def chapter_09_relationships(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("9. 15 Relationship Type の作成とバインディング", 1)
    builder.body(
        "Relationship Type は Entity type details の［Manage relationships］→［Add new relationship］から作成します。"
        "Origin / Target entity type、Mapping table、Matched origin key / target key を指定します。"
        "第 4 章で決めた向きをそのまま入力してください。逆向きに作ると、逆トラバースでは復元できません。"
    )
    builder.body(
        "Mapping table は、対象 Lakehouse の `dbo` スキーマにある `ot_` テーブルを選びます。"
        "名前とキーだけでなく schema も参照先の一部です。"
    )
    builder.table(
        ["設定する場所", "この章で決まるもの", "第 15 章の Notebook 02 が登録するもの"],
        [
            [
                "Ontology の UI",
                "Origin / Target entity type、Mapping table、Matched origin key / target key",
                "—",
            ],
            [
                "semanticEnrichment（宣言メタデータ）",
                "—",
                "方向の意味、カーディナリティ、集計ガード、否定的意味（何を証明しないか）",
            ],
        ],
        caption="Relationship Type の設定はどこが持つか",
        widths=(1.6, 2.6, 2.6),
    )
    builder.callout(
        "note",
        "UI にはカーディナリティの入力欄がありません。UI が持つのは構造（どのエンティティを、どのキーで結ぶか）だけです。"
        "「Municipality 1 件に対して Prefecture はちょうど 1 件」といった業務上の制約は宣言メタデータであり、"
        f"第 15 章の Notebook 02 が {len(context.relationships)} 件すべてに登録します。"
        "この章では次表の「カーディナリティ」列を、向きを間違えないための設計意図として読んでください。",
    )
    _shot(
        builder,
        "8-1",
        "Entity type details →［Manage relationships］→［Add new relationship］。",
        "Entity type details 画面でリレーションシップの管理メニューを開き、新規追加を選ぶ画面。",
    )

    builder.heading("9.1 15 Relationship Type の設定値", 2)
    rows = [
        [
            relationship.name,
            relationship.origin,
            relationship.target,
            relationship.mapping_table,
            relationship.origin_key_column,
            relationship.target_key_column,
            num(context.edge_count(relationship.name)),
        ]
        for relationship in context.relationships
    ]
    builder.table(
        ["Relationship Type", "Origin", "Target", "Mapping table", "Origin key", "Target key", "期待エッジ数"],
        rows,
        caption=f"15 Relationship Type の UI 設定値（エッジ合計 {num(context.expected['edgeTotal'])}）",
        widths=(1.7, 1.3, 1.3, 1.4, 1.3, 1.3, 0.9),
        font_size=8.0,
    )

    builder.heading("9.2 15 Relationship Type のカーディナリティと集計ガード", 2)
    builder.body(
        "次の表は Notebook 02 が登録する宣言メタデータです。UI では入力しませんが、"
        "向きとキーを決めるときの根拠になります。第 10 章ではこの表と実データの件数を突き合わせます。"
    )
    builder.table(
        ["Relationship Type", "カーディナリティ", "任意性（origin / target）", "集計ガード"],
        [
            [
                relationship.name,
                relationship.cardinality,
                f"{relationship.attributes.get('sourceParticipation', '')}\n"
                f"{relationship.attributes.get('targetParticipation', '')}",
                relationship.attributes.get("aggregationGuard", ""),
            ]
            for relationship in context.relationships
        ],
        caption=(
            f"{len(context.relationships)} Relationship Type のカーディナリティ"
            f"（{sum(1 for r in context.relationships if r.cardinality)} / {len(context.relationships)} 件が宣言済み）"
        ),
        widths=(1.5, 1.9, 1.7, 1.7),
        font_size=8.0,
    )
    builder.callout(
        "stop",
        "`MunicipalityCatalogsGift` は「その自治体のカタログに載っている返礼品」であって、"
        "「その自治体が受け取った寄付」ではありません。"
        "配布データでは、すべての寄付が受入自治体自身のカタログにある返礼品を選んでいるため、"
        "この関係をたどって数えても `DonationToMunicipality` と同じ数になってしまいます。"
        "数が合うのは配布データの偶然であり、モデルが同じだからではありません。"
        "実際のカタログでは他自治体の返礼品が載ることがあり、そのとき 2 つの経路は必ず食い違います。"
        "受入の件数・金額は必ず `DonationToMunicipality` で数えてください。",
        title="MunicipalityCatalogsGift で寄付を数えない",
    )

    builder.heading("9.3 1 件ずつの設定画面", 2)
    for relationship in context.relationships:
        tag = RELATIONSHIP_SCREENSHOTS[relationship.name]
        _shot(
            builder,
            tag,
            (
                f"{relationship.name}：Origin={relationship.origin} / Target={relationship.target} / "
                f"Mapping table=`{relationship.mapping_table}`。"
            ),
            (
                f"{relationship.name} の設定画面。Origin entity type、Target entity type、Mapping table、"
                "Matched origin key、Matched target key を指定している。"
            ),
        )

    _shot(
        builder,
        "8-3",
        "10 Entity Type / 15 Relationship Type を構成し終えた Ontology canvas。",
        "Ontology の canvas に 10 個の Entity カードと、それらを結ぶ 15 本の有向リレーションシップが表示されている全体図。",
        height=10.0,
    )
    chapter_pointer(builder, "第 9 章")


def chapter_10_static_gate(builder: DocumentBuilder, context: RuntimeContext, facts: TestFacts) -> None:
    expected = context.expected
    builder.heading("10. 静的ゲート：instance・キー・方向・件数の検証", 1)
    builder.body(
        "Eventhouse に進む前に、静的モデルだけで正しさを確定させます。ここで一致しない値があると、"
        "後段の time-series バインディングや Data Agent のテストで原因の切り分けができなくなります。"
    )
    _shot(
        builder,
        "9-1",
        "Entity type details での確認（Property source / Data source / Entity metadata）。",
        "Entity type details 画面。プロパティのソース、データソース、エンティティのメタデータが表示されている。",
    )
    _shot(
        builder,
        "9-2",
        "Instances タブで件数とキー・表示名・Property 値を確認する。",
        "Instances タブでインスタンス件数と各プロパティの値を確認している画面。",
    )
    builder.table(
        ["確認項目", "期待値", "確認方法"],
        [
            ["Entity Type 数", num(context.ontology_contract["entityTypes"]), "Explorer の一覧"],
            ["Relationship Type 数", num(context.ontology_contract["relationshipTypes"]), "canvas と Manage relationships"],
            ["静的 Property 数", num(context.ontology_contract["staticProperties"]), "各 Entity type details の合計"],
            ["ノード合計", num(expected["nodeTotal"]), "各 Entity の Instances 件数の合計"],
            ["エッジ合計", num(expected["edgeTotal"]), "各 Relationship の件数の合計"],
            ["キーの一意性", "重複なし", "Instances のキー列"],
            ["方向", "第 9.1 節の表と一致", "Relationship の Origin / Target"],
        ],
        caption="静的ゲートのチェックリスト",
        widths=(1.8, 1.6, 2.6),
    )
    builder.callout(
        "stop",
        f"`{context.relationship('SupplierProvidesGift').mapping_table}` はノードではありません。"
        f"{num(context.edge_count('SupplierProvidesGift'))} 行は SupplierProvidesGift のエッジ数にだけ使います。",
    )

    builder.heading("10.1 カーディナリティを実データで確かめる", 2)
    builder.body(
        "第 9.2 節で読んだカーディナリティは宣言です。宣言と実データが食い違っていれば、"
        "キーの対応付けか mapping table が誤っています。"
        f"{len(context.relationships)} 件の関係は 3 つのグループに分かれ、"
        "グループごとにエッジ数の一致先が違います。次の 3 つを Instances 件数から確認します。"
    )
    many_to_one = [r for r in context.relationships if r.cardinality.startswith("many-to-one")]
    # Both optionality words describe the same multiplicity: the edge count follows
    # the target. The word only records whether a source may contribute zero rows.
    one_to_many = [
        r
        for r in context.relationships
        if r.cardinality.startswith(("one-to-many from", "zero-to-many from"))
    ]
    optional_sources = [r for r in one_to_many if r.cardinality.startswith("zero-to-many from")]
    many_to_many = [r for r in context.relationships if r.cardinality.startswith("many-to-many")]
    builder.table(
        ["確認するカーディナリティ", "確認方法", "期待値"],
        [
            [
                f"many-to-one（{len(many_to_one)} 件）",
                "エッジ数と Origin エンティティのインスタンス数を比べる",
                "エッジ数 = Origin のインスタンス数（1 件につき 1 本）",
            ],
            [
                f"one-to-many（{len(one_to_many)} 件）",
                "エッジ数と Target エンティティのインスタンス数を比べる",
                "エッジ数 = Target のインスタンス数（Target 1 件につき 1 本）",
            ],
            [
                f"many-to-many（{len(many_to_many)} 件）",
                "エッジ数を Origin・Target 双方のインスタンス数と比べる",
                "どちらとも一致しない",
            ],
            [
                "MunicipalityInPrefecture（many-to-one）",
                f"エッジ数 {num(context.edge_count('MunicipalityInPrefecture'))} と "
                f"Municipality の {num(context.node_count('Municipality'))} 件を比べる",
                "一致する（自治体 1 件に都道府県ちょうど 1 件）",
            ],
            [
                "DonorMadeDonation（one-to-many）",
                f"エッジ数 {num(context.edge_count('DonorMadeDonation'))} と "
                f"Donation の {num(context.node_count('Donation'))} 件を比べる",
                f"一致する（Donor 側は {num(context.node_count('Donor'))} 件と一致しない）",
            ],
            [
                "SupplierProvidesGift（many-to-many）",
                f"エッジ数 {num(context.edge_count('SupplierProvidesGift'))} と "
                f"Gift {num(context.node_count('Gift'))} 件・Supplier {num(context.node_count('Supplier'))} 件を比べる",
                "どちらとも一致しない（多対多なので件数の代用にできない）",
            ],
        ],
        caption="カーディナリティのゲート",
        widths=(1.8, 2.8, 2.4),
        font_size=8.5,
    )
    builder.callout(
        "gate",
        f"many-to-one の {len(many_to_one)} 件は、エッジ数が Origin 側のインスタンス数と一致します。"
        f"one-to-many の {len(one_to_many)} 件は、エッジ数が Target 側のインスタンス数と一致します。"
        f"many-to-many は SupplierProvidesGift の 1 件だけで、どちらとも一致しません。"
        f"{len(many_to_one)} + {len(one_to_many)} + {len(many_to_many)} = {len(context.relationships)} 件です。"
        "一致しない場合は Origin と Target を逆に設定しているか、mapping table を取り違えています。"
        f"宣言そのものは第 15 章で {len(context.relationships)} / {len(context.relationships)} 件が登録されます。",
    )
    builder.callout(
        "note",
        "one-to-many を「Origin 側に必ず 1 本以上ある」と読まないでください。"
        f"{len(one_to_many)} 件のうち {len(optional_sources)} 件は、Origin 側に 1 本も持たない"
        "インスタンスが実データに存在します。"
        f"Donor は {num(context.node_count('Donor'))} 件ありますが、寄付を 1 件もしていない Donor が "
        f"{context.expected['donorsWithoutDonations']} 件、"
        f"寄付を 1 件も受けていない Municipality が {context.expected['municipalitiesWithoutDonations']} 件あります。"
        "そのためこの 2 件の宣言は one-to-many ではなく zero-to-many from ... と書かれています。"
        f"残る {len(one_to_many) - len(optional_sources)} 件は、Origin 側の全インスタンスが必ず 1 本以上持つため "
        "one-to-many from ... と書きます。"
        "多重度（1 対多か多対多か）と、任意性（0 本があり得るか）は別の問いであり、"
        "宣言はどちらも実データから決めています。",
        title="zero-to-many と one-to-many の違い",
    )

    builder.heading("10.2 メトリック / フロー Entity を検証する", 2)
    static = facts.static
    builder.body(
        "第 17 章の 10 問はメトリック / フロー Entity を直接は問いません。"
        "口語の質問がこの 3 つに届くことは稀だからです。しかし複合粒度の設計が正しいことは、"
        "ここで数値として確認しておく必要があります。再集計を禁止した設計が効いているかどうかは、"
        "この 3 エンティティでしか確認できません。"
    )
    builder.table(
        ["確認対象", "確認方法", "期待値"],
        [
            [
                "MunicipalityCategoryMetric",
                f"Instances で `{static.metric_id}`（{static.metric_municipality_name} × "
                f"{static.metric_category_name}）の 1 行を開く",
                f"MunCategoryStaticCount {num(static.metric_static_count)} / "
                f"MunCategoryTotalYen {yen(static.metric_total_yen)}",
            ],
            [
                "同上（設計の意味）",
                "この行を Donation から数え直そうとしない",
                "複合粒度の事前集計であり、明細から毎回計算しない",
            ],
            [
                "PrefectureCategoryMetric",
                "Instances 件数を数える",
                f"{num(context.node_count('PrefectureCategoryMetric'))} 件"
                f"（受入 Prefecture × カテゴリの組のうち、寄付が 1 件以上あったもの。"
                f"組み合わせの上限は {num(context.node_count('Prefecture'))} × "
                f"{num(context.node_count('GiftCategory'))} = "
                f"{num(context.node_count('Prefecture') * context.node_count('GiftCategory'))} 通り）",
            ],
            [
                "PrefectureDonationFlow（方向）",
                f"`{static.flow_id}` の 1 行を開き、起点と終点を確認する",
                f"居住地：{static.flow_origin_label} → 受入先：{static.flow_destination_label}／"
                f"{num(static.flow_static_count)} 件 / {yen(static.flow_total_yen)}",
            ],
            [
                "PrefectureDonationFlow（逆向き）",
                f"`{static.flow_reverse_id}` の 1 行を開いて比べる",
                f"{num(static.flow_reverse_static_count)} 件 / {yen(static.flow_reverse_total_yen)}"
                "（逆向きは別の値。入れ替えても同じにはならない）",
            ],
        ],
        caption="メトリック / フロー Entity のゲート",
        widths=(1.7, 2.6, 2.7),
        font_size=8.5,
    )
    builder.callout(
        "note",
        "メトリック Entity のインスタンス数は「あり得る組み合わせの数」ではなく「実際に観測された組の数」です。"
        f"PrefectureCategoryMetric は上限 "
        f"{num(context.node_count('Prefecture') * context.node_count('GiftCategory'))} 通りのうち "
        f"{num(context.node_count('PrefectureCategoryMetric'))} 件しかありません。"
        "寄付が 1 件もなかった組は行が作られないためです。"
        "MunicipalityCategoryMetric も同じで、"
        f"{num(context.node_count('Municipality'))} × {num(context.node_count('GiftCategory'))} ではなく "
        f"{num(context.node_count('MunicipalityCategoryMetric'))} 件になります。",
        title="件数は「あり得る組」ではなく「実際にあった組」",
    )
    builder.callout(
        "design",
        f"`{static.metric_id}` の {num(static.metric_static_count)} 件は、"
        f"{static.metric_municipality_name}（{static.metric_municipality_id}）の全カテゴリ合計 "
        f"{num(static.metric_municipality_total_count)} 件 / {yen(static.metric_municipality_total_yen)}の一部です。"
        "メトリック Entity の値どうしを足したり、スコープの違う値を混ぜたりすると意味が壊れます。"
        "これが「複合粒度は事前集計として独立させ、再集計しない」という設計の実証です。",
        title="なぜ複合粒度を独立させたのか",
    )
    builder.callout(
        "stop",
        f"フローは方向を持ちます。`{static.flow_id}` と `{static.flow_reverse_id}` は"
        "別のインスタンスであり、値も異なります。起点と終点を入れ替えて読み替えないでください。",
    )

    builder.heading("10.3 downstream の更新を確認する", 2)
    builder.body(
        "静的バインディングやスキーマを変更したあとは、Ontology の更新が完了してから次に進みます。"
        "Workspace のアイテム一覧で Ontology と関連 item の更新状態を確認してください。"
    )
    builder.callout(
        "note",
        "公式ドキュメントでは、スキーマ側の変更（Property・型・関係の追加や削除）は "
        "downstream へ自動的に反映される一方、"
        "上流のソースデータだけが変わった場合はグラフ側がそれを知らないため、"
        "手動でグラフモデルを更新するまで古いデータが表示されうる、と説明されています。"
        "更新はワークスペースのアイテム一覧で Ontology に対応するグラフモデルを開き、"
        "［Schedule］から［Refresh now］を選びます。"
        "毎回の小さな変更ごとに実行せず、まとめてから 1 回実行してください。"
        "更新のたびに全件を取り込み直すため、容量の消費に効いてきます。",
        title="ソース側だけが変わったときは手動で更新する",
    )
    builder.callout(
        "stop",
        "Notebook 01 が完了していても、`GraphNotRefreshable` が出る、または Graph の source・node・edge が"
        " 0 のままなら、Graph の機能は未確認です。Ontology の定義作成やメタデータ登録の件数で代用しません。"
        "参照先の実 ID、Property source / Data source、Lakehouse 側の `sourceSchema` を確認します。"
        "修正後は Graph のコンパイルと更新ジョブが完了してから、本章の件数を照合します。"
        "更新を連打したり、item の存在だけで合格にしません。",
        title="Ontology の定義と Graph の機能を分けて確認する",
    )
    _shot(
        builder,
        "10-1",
        "Workspace のアイテム一覧で Ontology と関連 item の更新状態を確認する。",
        "Workspace のアイテム一覧画面。Ontology と関連する item の更新日時が表示されている。",
    )
    builder.body(
        "この章のゲートが通らなかった場合、直す場所は 2 つに絞られます。"
        "Instances の件数やキーが合わないときは第 8 章の Entity Type と静的バインディング、"
        "エッジ数や方向が合わないときは第 9 章の Relationship Type とバインディングに戻ってください。"
        "先に第 11 章へ進むと、Eventhouse 側の失敗なのか静的側の失敗なのか切り分けられなくなります。"
    )
    chapter_pointer(builder, "第 8 章と第 9 章")


#: How each parsed management command is explained to a participant. The build
#: fails if the shipped script introduces a command that is not described here,
#: so the chapter can never drift from the runtime.
KQL_OBJECT_ROLES = {
    "create-merge table": "Pipeline が取り込む raw 観測テーブル。EventID を含む唯一のオブジェクト。",
    "create-or-alter ingestion mapping": "配布 CSV のヘッダー順に合わせた取り込みマッピング。序数はテーブル定義順とは一致しない。",
    "create-or-alter materialized-view": "自治体 × 1 分バケットの集約。Data Agent が参照する唯一のオブジェクトで、EventID は含まない。",
    "alter table policy retention": "raw テーブルの保持期間。",
    "alter table policy caching": "raw テーブルのホットキャッシュ期間。",
}


def chapter_11_eventhouse(builder: DocumentBuilder, context: RuntimeContext) -> None:
    names = context.names
    objects = context.kql_objects
    builder.heading("11. Eventhouse と KQL スキーマ", 1)
    builder.body(
        f"［新規］→［Eventhouse］で {names['eventhouse']} を作成します。同名の KQL データベースが作られます。"
        f"次に、配布されている `Furusato_Eventhouse_Setup_v{context.version}.kql` の "
        f"{len(objects)} 個の管理コマンドを上から順に 1 回ずつ実行します。共有データベースに対しては実行しません。"
    )
    _shot(
        builder,
        "11-1",
        "［新規］→［Eventhouse］（Real-Time Intelligence）を選択する。",
        "Fabric の新規作成メニューで Real-Time Intelligence の Eventhouse を選ぶ画面。",
    )
    _shot(
        builder,
        "11-2",
        f"New Eventhouse ダイアログで {names['eventhouse']} を入力する。",
        "New Eventhouse ダイアログに Eventhouse 名を入力している画面。",
    )
    builder.body(
        "初回だけ［Welcome to Eventhouse!］が表示されます。［Get started］で閉じると System overview に進みます。"
    )
    _shot(
        builder,
        "11-26",
        "初回の［Welcome to Eventhouse!］。［Get started］で閉じる。",
        "Eventhouse 作成直後の Welcome to Eventhouse ダイアログ。Get started ボタンが表示されている。",
    )
    _shot(
        builder,
        "11-3",
        "Eventhouse 作成直後の System overview。左ペインの KQL databases に同名 DB が作られる。",
        "Eventhouse 作成直後のシステム概要画面。左ペインに同名の KQL データベースが表示されている。",
    )

    builder.heading(f"11.1 作成される {len(objects)} 個の管理オブジェクト", 2)
    builder.body(
        f"セットアップスクリプトが実行する管理コマンドはこの {len(objects)} 個だけです。"
        "順序どおりに 1 回ずつ実行し、実行結果にエラーがないことを確認します。"
    )
    unknown = [entry.command for entry in objects if entry.command not in KQL_OBJECT_ROLES]
    if unknown:
        raise ValueError(f"Unexplained KQL management command(s): {unknown}")
    builder.table(
        ["#", "オブジェクト", "種別", "管理コマンド", "設定", "役割"],
        [
            [
                str(index),
                entry.name,
                entry.kind,
                f"`.{entry.command}`",
                entry.detail,
                KQL_OBJECT_ROLES[entry.command],
            ]
            for index, entry in enumerate(objects, start=1)
        ],
        caption=f"KQL セットアップが作成する {len(objects)} 個の管理オブジェクト",
        widths=(0.3, 2.5, 1.2, 1.9, 1.4, 2.1),
        font_size=8.0,
        whole_token_columns=(1, 3),
    )
    builder.callout(
        "note",
        f"ファイルの後半には検証用のクエリも入っていますが、これらは管理コマンドではありません。"
        f"管理コマンドは先頭がドット（`.`）で始まる {len(objects)} 個だけで、"
        "検証クエリはテーブル名から始まる通常のクエリです。"
        f"取り込み確認クエリの `let targetSourceFile = \"<SourceFile>\";` は、"
        f"`<SourceFile>` を実際に取り込んだファイル名（例：`{context.increment_files[0]['file']}`）に"
        "置き換えてから実行します。二重引用符はそのまま残してください。"
        "置き換えずに実行すると 0 行が返り、取り込み失敗と誤読します。",
        title="管理コマンドと検証クエリは別物",
    )
    builder.callout(
        "design",
        (
            "ここまでが基線の KQL オブジェクトです。統合 Agent の設定前に第 16.2.1 節で"
            "同じ Eventhouse へ承認済みの 3 関数を追加します。関数はこの MV を読みます。"
            "raw DonationEvents と EventID を Agent に直接選択せず、別 Eventhouse や別 Agent を作りません。"
        ) if context.is_unified_guide else
        "オブジェクトはこれだけです。Agent 用の射影テーブルや関数、update policy は v2.7.0 にはありません。"
        "Data Agent に見せるのはマテリアライズドビュー 1 件だけで、raw テーブルは見せません。"
        "余分な層を作らないことで、「どのオブジェクトが Agent の答えの根拠なのか」が 1 つに定まります。",
        title="層を増やさない",
    )
    _shot(
        builder,
        "11-4",
        "KQL 管理コマンド実行後の KQL Database。テーブルとマテリアライズドビューが作成されている。",
        "KQL データベースの画面。Tables に DonationEvents、"
        "Materialized views に集約ビューが表示されている。",
    )

    builder.heading("11.2 マテリアライズドビューの定義", 2)
    builder.body(
        (
            "統合 Agent はこの MV と、ここから読み取る承認済みの 3 関数を参照します。"
            "MV の 1 行は「自治体 × 1 分バケット × 実行メタデータ」の集約であり、EventID は含みません。"
            "関数を追加しても一意 EventID や重複排除を証明できない境界は変わりません。"
        ) if context.is_unified_guide else
        "Data Agent が参照するのはこのビューだけです。1 行が「自治体 × 1 分バケット × 実行メタデータ」の集約であり、"
        "EventID は含まれません。この設計が、第 17 章のテスト 7 で確認する境界の理由です。"
    )
    builder.code_block(_extract_kql_block(context, "materialized-view"), language="KQL（マテリアライズドビューの定義）")
    builder.callout(
        "stop",
        "マテリアライズドビューは、取り込みの前に必ず作成してください。"
        "ビュー作成前に取り込んだ行が遡って集約される保証はありません。",
    )
    chapter_pointer(builder, "第 11 章")


def _extract_kql_block(context: RuntimeContext, marker: str) -> str:
    lines = context.kql_setup.splitlines()
    start = next(index for index, line in enumerate(lines) if marker in line)
    depth = 0
    collected: list[str] = []
    for line in lines[start:]:
        collected.append(line)
        depth += line.count("{") - line.count("}")
        if depth == 0 and len(collected) > 1:
            break
    return "\n".join(collected)


def chapter_12_pipeline(builder: DocumentBuilder, context: RuntimeContext) -> None:
    names = context.names
    parameters = context.pipeline["properties"]["parameters"]
    builder.heading("12. Data Pipeline と OneLake FileCreated トリガー", 1)
    builder.body(
        f"増分の唯一の経路は Pipeline です。{names['pipeline']} を作成し、Lakehouse の "
        "`Files/increment` から Eventhouse の DonationEvents へコピーする Copy activity を 1 つ置きます。"
        "起動は OneLake の FileCreated トリガーだけで行い、参加者が手動実行することはありません。"
    )
    builder.callout(
        "gate",
        "トリガーを作る前に `Files/increment` フォルダーを空にしておきます。"
        "既存ファイルがあること自体は FileCreated の受信証拠ではありません。"
        "Notebook 04 から進む場合は付録 D.2 の待機用フォルダーと監視先の確認を行い、"
        "別のルールや準備中のイベントによる意図しない取り込みも防ぎます。",
    )
    for tag, caption, alt in (
        ("11-9", "［新規アイテム］の一覧から［Pipeline］を選択する。", "Fabric の新規アイテム一覧から Data pipeline を選択している画面。"),
        ("11-10", "Pipeline 作成直後の開始画面。空のキャンバスから始める。", "作成直後の Data pipeline 画面。パイプラインアクティビティを追加する開始画面が表示されている。"),
    ):
        _shot(builder, tag, caption, alt)

    builder.heading("12.1 Pipeline パラメーター", 2)
    builder.table(
        ["パラメーター", "型", "既定値", "役割"],
        [
            [
                "IncrementFileName",
                parameters["IncrementFileName"]["type"],
                parameters["IncrementFileName"]["defaultValue"],
                "ファシリテーター向けの診断用フォールバック。通常のファイル選択では非空の Subject が優先される。",
            ],
            ["Type", parameters["Type"]["type"], "（空）", "OneLake イベントの種別が入る。"],
            [
                "Subject",
                parameters["Subject"]["type"],
                "（空）",
                "作成されたファイルのパスが入る。末尾がファイル名として使われる。",
            ],
            ["Source", parameters["Source"]["type"], "（空）", "イベントの発生元が入る。"],
        ],
        caption="Pipeline の 4 パラメーター",
        widths=(1.6, 0.8, 1.8, 3.2),
    )
    builder.callout(
        "stop",
        f"`IncrementFileName` の既定値 `{parameters['IncrementFileName']['defaultValue']}` は、"
        "トリガーを使わずに Pipeline 単体を検証したい場合のファシリテーター向け診断値です。"
        "参加者の手順では常に `Subject` から導出されたファイル名が使われます。"
        "この既定値が使われると、到着したファイルに関係なく 1 本目が選ばれ、取り込み済みなら重複します。",
        title="IncrementFileName は診断専用",
    )
    builder.body("ファイル名は Subject から導出されます。式は次のとおりです。")
    builder.code_block(
        context.pipeline["properties"]["activities"][0]["typeProperties"]["source"]["datasetSettings"][
            "typeProperties"
        ]["location"]["fileName"]["value"],
        language="Pipeline の式（Subject の末尾をファイル名として使う）",
    )
    _shot(
        builder,
        "11-11",
        "［Parameters］タブ。4 つのパラメーターを定義した状態。",
        "Data pipeline のパラメータータブ。IncrementFileName、Type、Subject、Source の 4 つが定義されている。",
    )
    _shot(
        builder,
        "11-12",
        "Copy activity の［Source］タブ。`increment` フォルダーと Subject 由来のファイル名式を設定する。",
        "Copy activity のソース設定画面。Lakehouse の increment フォルダーとファイル名の式が入力されている。",
    )
    _shot(
        builder,
        "11-13",
        f"Copy activity の［Destination］タブ。{names['eventhouse']} の DonationEvents を指定する。",
        "Copy activity の宛先設定画面。Eventhouse の DonationEvents テーブルが指定されている。",
    )
    builder.callout(
        "note",
        "取り込みマッピングには DonationEvents_IncrementCsvMap を指定します。"
        "配布 CSV のヘッダーは SourceFile が PublishedAtUtc より前にあるため、"
        "序数はテーブル定義順とは一致しません。",
    )

    builder.heading("12.2 OneLake FileCreated トリガーを作る", 2)
    builder.body(
        "以下はトリガーが未作成の場合の手順です。Notebook 04 などで作成済みなら、"
        "新規ルールを追加せず、既存ルールの保存・Start と引数を確認します。"
    )
    builder.bullets(
        (
            "リボンの［Trigger］→［Add trigger］を選びます。",
            "［Add rule］ペインで Action=Run Pipeline と対象 Pipeline を確認します。",
            "［Select a data source］で［OneLake events］を選びます。",
            "Event type(s) は FileCreated だけを残します。",
            f"OneLake catalog で {names['lakehouse']} を選択します。",
            "監視対象を `Files/increment` だけに絞ります。",
            "［Review + connect］で設定を確認し、作成します。",
            "［View triggers］で rule を開いて変更を保存します。未起動なら［Start］を選び、"
            "Running とアクションの実行状態を確認します。",
            f"自動作成された Activator を `{names['activator']}` にリネームします。",
        ),
        numbered=True,
    )
    builder.callout(
        "note",
        "Notebook 04 などで定義から作成した Reflex は、UI で既存ルールを開いて保存し、［Start］で起動します。"
        "定義の有効フラグだけで稼働したと判定しません。Run Pipeline のアクション引数に"
        f" `IncrementFileName` が必要な場合は、既定値 `{parameters['IncrementFileName']['defaultValue']}` を設定します。"
        "`Type`・`Subject`・`Source` は OneLake イベントからの動的な対応付けを保持します。"
        "ファイル選択は非空の Subject を使い、既定値だけの手動 run で代用しません。"
        "保存・引数設定・Start をまとめて確認する手順であり、Start 単独の効果と断定しません。",
        title="保存・Start とアクション引数を確認する",
    )
    for tag, caption, alt in (
        ("11-16", "リボンの［Trigger］→［Add trigger］／［View triggers］。", "Data pipeline のリボンでトリガーの追加と表示のメニューを開いた画面。"),
        ("11-17", "［Add rule］ペイン。Action=Run Pipeline と対象 Pipeline が既定で入る。", "ルール追加ペイン。アクションとして Run Pipeline と対象パイプラインが設定されている。"),
        ("11-18", "［Select a data source］で［OneLake events］を選択する。", "データソース選択画面で OneLake events を選んでいる。"),
        ("11-19", "Event type(s) の一覧。FileCreated だけを残す。", "イベント種別の一覧で FileCreated だけにチェックが入っている画面。"),
        ("11-20", "OneLake catalog で対象 Lakehouse を選択する。", "OneLake catalog から監視対象の Lakehouse を選択している画面。"),
        ("11-21", "監視対象を `Files/increment` だけに絞る。", "監視対象のフォルダーパスを Files/increment に限定している設定画面。"),
        ("11-22", "［Review + connect］。FileCreated と対象 Lakehouse が設定されている。", "レビューと接続の画面。イベント種別と対象 Lakehouse の設定が一覧表示されている。"),
        ("11-23", "作成前の最終確認。Source=OneLake events、Action=Run Pipeline。", "トリガー作成前の最終確認画面。ソースとアクションが表示されている。"),
        ("11-24", "Activator の［Rules］ペイン。作成した rule が Running になっている（所有者とテナントの情報は塗りつぶし）。", "Activator のルール一覧パネル。IncrementFileArrived のルールが New バッジ付きで表示され、トグルが Running になっている。ワークスペース所有者とテナントの表示は灰色で塗りつぶされている。"),
    ):
        _shot(builder, tag, caption, alt)

    builder.heading("12.3 Activator をリネームする", 2)
    builder.body(
        "トリガーを作成すると、Fabric がワークスペースに Activator（Reflex）item を自動生成します。"
        "既定名のままだと、複数の参加者が同じワークスペースを使う場合に自分の item を識別できません。"
        f"ワークスペースのアイテム一覧から［Rename］を選び、`{names['activator']}` に変更してください。"
        "トリガー本体の設定は変わりません。指定 Folder がある場合は、この item の ID と配置先も確認します。"
        "Notebook 04 が同じ用途の Reflex を作成済みなら、新しいルールを重ねて作らず、既存の 1 つを確認します。"
    )
    builder.table(
        ["item 種別", "命名規則", "作成方法"],
        [
            ["Lakehouse", f"`{names['lakehouse']}`", "手動作成（第 6 章）"],
            ["Ontology", f"`{names['ontology']}`", "手動作成（第 7 章）"],
            ["Eventhouse", f"`{names['eventhouse']}`", "手動作成（第 11 章）"],
            ["Data Pipeline", f"`{names['pipeline']}`", "手動作成（第 12 章）"],
            [
                "Activator（Reflex）",
                f"`{names['activator']}`",
                "トリガー作成時に自動生成 → この節でリネームする",
            ],
            ["Data Agent", f"`{names['dataAgent']}`", "手動作成（第 16 章）"],
        ],
        caption="Core で作成する item と命名規則（`<PID>` は自分の 3 桁 ID）",
        widths=(1.6, 2.4, 2.6),
    )

    builder.heading("12.4 1 本目のアップロードで導出結果を確認する", 2)
    builder.body(
        "トリガーが Running になったら、まず 1 本目だけをアップロードして、"
        "Pipeline が「アップロードしたファイル」を取り込んだことを確認します。"
        "ここを飛ばすと、誤ったファイルを 3 本ぶん取り込んでから気づくことになります。"
    )
    builder.bullets(
        (
            f"Lakehouse の `Files/increment`（第 6.2 節で空のまま作成したフォルダー）を開きます。",
            f"`{context.increment_files[0]['file']}` を 1 本だけアップロードします。",
            f"`{context.increment_files[1]['file']}` と `{context.increment_files[2]['file']}` は"
            "まだアップロードしません。この 2 本は第 13 章で 1 本ずつ置きます。",
            "アップロード後、下の表の 4 項目をすべて確認します。",
        ),
        numbered=True,
    )
    builder.table(
        ["確認項目", "確認場所", "合格条件"],
        [
            [
                "トリガーが発火した",
                "Activator の受信イベント・アクション実行記録と Pipeline の［View run history］",
                "対象ファイルの FileCreated とアクション実行が、正しい Subject を持つ 1 件の run に対応する",
            ],
            [
                "`Subject` が空でない",
                "実行の詳細 → Parameters",
                f"`Files/increment/{context.increment_files[0]['file']}` を含むパスが入っている",
            ],
            [
                "導出されたファイル名",
                "Copy activity の入力",
                f"`{context.increment_files[0]['file']}`（アップロードしたファイルと同じ）",
            ],
            [
                "取り込み行数",
                "実行の詳細 → Copy activity の出力",
                f"{num(context.increment_files[0]['rows'])} 行",
            ],
        ],
        caption="1 本目の取り込みで確認するゲート",
        widths=(1.6, 2.2, 2.8),
    )
    builder.callout(
        "gate",
        f"`Subject` が空のまま実行されると、Pipeline は既定値 "
        f"`{parameters['IncrementFileName']['defaultValue']}` にフォールバックします。"
        f"1 本目としては同じファイルなので気づきにくいのですが、2 本目・3 本目でも "
        f"`{parameters['IncrementFileName']['defaultValue']}` が取り込まれ、"
        "同じ行が繰り返し入ります。実行ごとに導出されたファイル名を確認してください。",
        title="Subject が空なら止める",
    )
    builder.callout(
        "stop",
        "手動 run へ `Type`・`Subject`・`Source` を入力して成功しても、"
        "OneLake → Activator → Pipeline の自動起動を確認したことにはなりません。"
        "手動診断は別記録にし、受信イベントと自動 run の対応を確認できない場合は"
        "「トリガー未検証」のままにします。失敗 run でも一部の行が書かれる可能性があるため、"
        "再送の前にトリガーを Off にして `SourceFile` 別件数を確認してください。",
        title="手動診断はトリガーの代替証拠にしない",
    )
    builder.callout(
        "note",
        "`invokeType` が `Manual` と表示されても、その項目だけで手動実行と決めません。"
        "OneLake の受信イベント、Activator の activation / アクション実行記録、Pipeline のジョブ ID、"
        "Subject・ファイル名・行数を対応付けます。イベントの受信だけ、定義の有効フラグだけ、"
        "実行履歴の集計グラフや実行種別の表示だけでは自動起動の証明になりません。ここで区別するのは実際の起動経路です。",
        title="invokeType ではなく実際の起動経路を確認する",
    )
    chapter_pointer(builder, "第 12 章")


def chapter_13_increment(builder: DocumentBuilder, context: RuntimeContext, facts: TestFacts) -> None:
    increment = context.expected_increment
    observation = facts.observation
    files = context.increment_files
    builder.heading("13. 増分の残り 2 ファイルの順次アップロードと KQL 検証", 1)
    builder.body(
        f"第 12.4 節で `{files[0]['file']}` は取り込み済みです。再アップロードしないでください。"
        f"この章では残りの `{files[1]['file']}` と `{files[2]['file']}` を 1 本ずつ "
        "`Files/increment` にアップロードします。"
        "1 本アップロードするたびに Pipeline の実行が成功することを確認し、成功してから次の 1 本を置きます。"
        "2 本とも終わったらトリガーを Off に戻します。"
    )
    builder.callout(
        "stop",
        f"`{files[0]['file']}` は第 12.4 節のゲートで既に取り込まれています。"
        "ここでもう一度アップロードすると、同じ行が二重に入り、"
        f"raw {num(increment['rawRows'])} 行という期待値に到達できなくなります。"
        f"この章でアップロードするのは `{files[1]['file']}` と `{files[2]['file']}` の 2 本だけです。",
        title=f"{files[0]['file']} は取り込み済み",
    )
    builder.bullets(
        (
            f"{files[1]['file']} をアップロードし、Pipeline の実行が Succeeded になることを確認する。",
            f"{files[2]['file']} をアップロードし、同様に確認する。",
            "［Stop］または Off 操作でルールを停止し、Stopped / Off を確認する。"
            "作成済みの run もすべて終了していることを確認し、実行記録を保持する。",
        ),
        numbered=True,
    )
    builder.table(
        ["ファイル", "アップロードする節", "この章での操作"],
        [
            [f"`{files[0]['file']}`", "第 12.4 節（1 本目のゲート）", "取り込み済み。再アップロードしない"],
            [f"`{files[1]['file']}`", "第 13 章", "アップロードする"],
            [f"`{files[2]['file']}`", "第 13 章", "アップロードする"],
        ],
        caption=f"増分 {len(files)} ファイルをどこでアップロードするか",
        widths=(2.0, 2.0, 2.6),
    )
    _shot(
        builder,
        "11-25",
        f"{len(files)} 本の取り込みが終わったらトグルを Off に戻す。",
        "トリガー一覧でトリガーのトグルを Off に切り替えている画面。",
    )
    builder.callout(
        "note",
        "実行状況は Pipeline の［View run history］で確認します。参加者が Pipeline を手動実行することはありません。"
        "起動はすべて OneLake の FileCreated トリガー経由です。",
    )
    builder.callout(
        "stop",
        "同じファイルを再アップロードすると二重に取り込まれます。取り込み後は必ずトリガーを Off に戻し、"
        "`SourceFile` 単位で件数を確認してください。",
    )

    builder.heading("13.1 ファイル単位の期待値", 2)
    builder.table(
        ["SourceFile", "行数", "金額合計", "最初の観測（UTC）", "最後の観測（UTC）", "WorkshopRunId"],
        [
            [
                entry["file"],
                num(entry["rows"]),
                yen(entry["amount"]),
                entry["first"],
                entry["last"],
                run["run"],
            ]
            for entry, run in zip(observation.per_file, observation.per_run)
        ],
        caption="増分ファイルごとの期待値",
        widths=(2.0, 0.7, 1.3, 1.5, 1.5, 1.4),
        font_size=8.0,
    )

    builder.heading("13.2 全体の期待値", 2)
    builder.table(
        ["指標", "期待値", "意味"],
        [
            ["raw 行数", num(increment["rawRows"]), "3 ファイルの合計。重複を含む。"],
            ["一意 EventID", num(increment["uniqueEventIds"]), "重複を除いた実質の観測数。"],
            [
                "重複 EventID",
                num(increment["duplicateEventIds"]),
                # The manifest records the layout in English for machine readers;
                # the guide states the same fact in Japanese, composed from the
                # file names and the count rather than by pasting that sentence.
                f"`{files[0]['file']}` の末尾 {num(increment['duplicateEventIds'])} 行が、"
                f"`{files[1]['file']}` の先頭 {num(increment['duplicateEventIds'])} 行として再出現します。",
            ],
            ["raw 金額合計", yen(increment["rawAmountYen"]), "重複を含む合計。"],
            ["重複排除後の金額合計", yen(increment["deduplicatedAmountYen"]), "一意 EventID の合計。"],
            ["観測窓（UTC）", f"{increment['observationWindowUtc']['from']} 〜 {increment['observationWindowUtc']['to']}", "DonatedAt の最小・最大。"],
        ],
        caption="増分 3 ファイル全体の期待値",
        widths=(1.6, 2.4, 2.6),
    )
    builder.body(
        "KQL Queryset で次を確認します。ファイル単位の検証クエリと全体の検証クエリは、"
        f"配布されている `Furusato_Eventhouse_Setup_v{context.version}.kql` の末尾に含まれています。"
    )
    builder.code_block(_kql_tail(context), language="KQL（取り込み後の検証）")
    builder.callout(
        "gate",
        f"raw {num(increment['rawRows'])} 行・一意 {num(increment['uniqueEventIds'])}・"
        f"重複 {num(increment['duplicateEventIds'])} が一致し、マテリアライズドビューの "
        f"`sum(ObservationCount)` が {num(increment['rawRows'])}、"
        f"`sum(ObservedAmountYen)` が {yen(increment['rawAmountYen'])}になることを確認します。",
    )

    builder.heading("13.3 UTC 日次分布を確認する", 2)
    calendar = observation.calendar
    builder.body(
        f"合計だけでなく、日次の分布も確認します。取り込みが正しければ、UTC の "
        f"{calendar.first_utc_day} から {calendar.last_utc_day} まで {calendar.utc_day_count} 日ぶんの行が並び、"
        f"1 日あたり {num(calendar.min_rows)} 〜 {num(calendar.max_rows)} 行に収まります。"
        "欠測日が出る、または範囲外の日が現れる場合は、ファイルの取り込み漏れか二重取り込みを疑います。"
    )
    builder.code_block(
        "DonationEvents\n"
        "| summarize Rows=count(), TotalYen=sum(DonationAmountYen) by UtcDay=bin(DonatedAt, 1d)\n"
        "| order by UtcDay asc",
        language="KQL（UTC 日次分布）",
    )
    builder.table(
        ["確認項目", "期待値"],
        [
            ["UTC の日数", f"{calendar.utc_day_count} 日（{calendar.first_utc_day} 〜 {calendar.last_utc_day}）"],
            ["欠測日", "なし"],
            ["1 日あたりの行数", f"{num(calendar.min_rows)} 〜 {num(calendar.max_rows)} 行"],
            ["最小の日", f"{calendar.min_rows_day}（{num(calendar.min_rows)} 行）"],
            [
                "最大の日",
                f"{calendar.max_rows_day}（raw {num(calendar.duplicate_day_raw_rows)} 行、"
                f"追加重複 {num(calendar.duplicate_extra_rows_on_day)} 行"
                f"（{num(calendar.duplicate_event_ids_on_day)} EventID・該当 "
                f"{num(calendar.duplicate_group_rows_on_day)} 行）を除いて "
                f"{num(calendar.duplicate_day_dedup_rows)} 行）",
            ],
            ["日次合計", f"{num(observation.raw_rows)} 行"],
        ],
        caption="UTC 日次分布のゲート",
        widths=(1.8, 3.6),
    )
    builder.callout(
        "note",
        f"日次の全 {calendar.utc_day_count} 行の内訳は第 5.4.1 節の表にあります。"
        f"{calendar.max_rows_day} だけ raw {num(calendar.duplicate_day_raw_rows)} 行と多いのは、"
        f"配布データの重複 {num(increment['duplicateEventIds'])} EventID がこの日に集中しているためです。"
        f"該当行は {num(calendar.duplicate_group_rows_on_day)} 行、"
        f"重複排除で取り除かれる追加分は {num(calendar.duplicate_extra_rows_on_day)} 行で、"
        f"結果は {num(calendar.duplicate_day_dedup_rows)} 行になります。",
    )
    builder.callout(
        "gate",
        f"日付で切るときは必ず UTC の `DonatedAt` を使います。JST に変換すると "
        f"{calendar.jst_rollover_from_utc} 以降の {num(calendar.jst_rollover_rows)} 行が "
        f"{calendar.last_jst_day} に繰り上がり、暦日が {calendar.jst_day_count} 日になります。"
        f"また 3 本目の `PublishedAtUtc` は {increment['publishedAtUtc'][2]} です。"
        "どちらも仕様どおりで、観測窓外エラーではありません。",
        title="9 月 1 日が出ても正常",
    )
    chapter_pointer(builder, "第 13 章")


def _kql_tail(context: RuntimeContext) -> str:
    lines = context.kql_setup.splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line.startswith("// After all three increment files")
    )
    return "\n".join(lines[start:]).strip()


def _municipality_name(context: RuntimeContext, municipality_id: str) -> str:
    """Resolve a municipality display name straight from the packaged seed CSV."""
    import csv

    path = context.root / "workshop" / f"v{context.version}" / "data" / "seed" / "municipalities.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["MunicipalityID"] == municipality_id:
                return row["MunicipalityName"]
    raise KeyError(municipality_id)


def chapter_14_timeseries(builder: DocumentBuilder, context: RuntimeContext, facts: TestFacts) -> None:
    names = context.names
    municipality = context.entity("Municipality")
    binding = municipality.timeseries_binding
    observed_id = facts.observation.top_observed_municipality_id
    municipality_name = _municipality_name(context, observed_id)
    builder.heading("14. Municipality への time-series バインディング", 1, new_page=False)
    builder.body(
        "Eventhouse に観測が入った状態で、教材用 full Ontology の Municipality に time-series バインディングを追加します。"
        "第 4 章で述べたとおり、観測は新しいエンティティにせず、既存の Municipality の時間軸の測定値にします。"
        "path-only の AIPath には追加しません。第 17.0 節の hydration 確認も教材用モデルだけの機能ゲートです。"
    )
    builder.bullets(
        (
            "Municipality の Entity type details を開きます。",
            "［Configure］→［Manage property bindings］を選びます。",
            "［Add data binding］→［Eventhouse table or materialized view］を選びます。",
            f"OneLake catalog で {names['eventhouse']} を選択します。",
            f"テーブル一覧では raw の `{binding.source_table}` を選びます。"
            "マテリアライズドビュー `DonationObservationSummaryForAgent` は選びません。",
            "Eventhouse テーブルを追加すると［Timeseries data］セクションが表示されます。",
            f"［Timestamp column］に {binding.timestamp_column}（UTC）を指定します。",
            "自動追加された不要 Property を削除し、必要な列だけを残します。",
            "キー・タイムスタンプ・Property を確認して保存します。",
        ),
        numbered=True,
    )
    builder.callout(
        "stop",
        f"ここで選ぶのは raw の `{binding.source_table}` です。"
        "`DonationObservationSummaryForAgent` を選ぶと、1 分バケットの集約値が"
        "そのまま time-series の測定値になり、値の意味が変わります。"
        "同じ Eventhouse を使うのに Data Agent と Ontology で参照先が違うのは意図した非対称です。"
        f"Ontology の time-series は raw の `{binding.timestamp_column}` と `DonationAmountYen` を"
        "そのまま束ねるので、重複排除は行われず、重複した EventID の行も残ったまま集計されます。"
        + (
            "統合 Agent には承認済み MV とその 3 関数だけを直接選択し、EventID を渡しません。"
            if context.is_unified_guide else
            "Data Agent には逆に curated なマテリアライズドビューだけを見せ、EventID を渡しません。"
        ) +
        "前者は「時間軸の生の観測」を、後者は「Agent に渡してよい粒度」を目的にしているためです。",
        title=f"raw {binding.source_table} を選ぶ（ビューではない）",
    )
    builder.table(
        ["設定項目", "値"],
        [
            ["バインディング種別", binding.binding_type],
            ["ソース種別", binding.source_type],
            ["ソーステーブル", binding.source_table],
            ["タイムスタンプ列", binding.timestamp_column or ""],
        ]
        + [[f"列マッピング：{source}", target] for source, target in binding.column_map],
        caption="Municipality の time-series バインディング設定",
        widths=(2.0, 3.4),
    )
    for tag, caption, alt in (
        ("12-1", "Municipality の Entity type details を開く。", "Municipality の Entity type details 画面。"),
        ("12-2", "［Configure］→［Manage property bindings］。", "設定メニューからプロパティバインディングの管理を選ぶ画面。"),
        ("12-3", "［Add data binding］→［Eventhouse table or materialized view］を選択する。", "データバインディングの追加でソース種別として Eventhouse のテーブルまたはマテリアライズドビューを選ぶ画面。"),
        ("12-4", "OneLake catalog で Eventhouse を選択する。", "OneLake catalog から Eventhouse を選択している画面。"),
        ("12-5", "Eventhouse テーブルを追加すると［Timeseries data］セクションが表示される。", "バインディング設定画面に Timeseries data のセクションが表示されている状態。"),
        ("12-6", "［Timestamp column］に DonatedAt（UTC）を指定する。", "タイムスタンプ列として DonatedAt を選択している画面。"),
        ("12-7", "自動追加された不要 Property を削除し、必要な列だけを残す。", "プロパティ一覧から不要な行を削除アイコンで取り除いている画面。"),
        ("12-8", "保存直前の確認。キー・タイムスタンプ・Property を確認する。", "time-series バインディングの保存前の確認画面。キー列、タイムスタンプ列、対象プロパティが表示されている。"),
    ):
        _shot(builder, tag, caption, alt)
    builder.callout(
        "gate",
        "バインディングを変更したら、Ontology の更新が完了してから次に進みます。"
        "更新前に Notebook 02 を実行すると、time-series Property が存在せずメタデータ件数が合いません。",
    )

    builder.heading("14.1 保存直後はバインディング構造を確認する", 2)
    builder.body(
        "現行の Ontology (preview) では、time-series バインディングを保存しても Overview にタイルは自動作成されません。"
        "［There are no tiles to display for this overview］はバインディング失敗を意味しません。"
        "ここでは Configure の定義を確認し、実データの hydration は Data Agent 作成後の第 17.0 節で Ontology 単独照会します。"
    )
    builder.table(
        ["確認項目", "確認方法", "期待値"],
        [
            [
                "キー対応",
                "Configure → Manage property bindings",
                f"`MunicipalityID` → `{municipality.key_property}`",
            ],
            [
                "タイムスタンプ",
                "Timeseries data",
                f"`{binding.timestamp_column}`（UTC）",
            ],
            [
                "Property 対応",
                "Properties",
                "`DonationAmountYen` → `IncomingDonationAmountYen`",
            ],
            [
                "Overview",
                f"Municipality `{observed_id}` を開く",
                "タイルが空でも可（自動作成されない）",
            ],
            [
                "機能ゲート",
                "第 17.0 節の教材用 full Ontology 単独照会",
                f"{municipality_name}：raw 観測 {num(facts.observation.top_observed_count)} 件 / "
                f"raw 観測金額 {yen(facts.observation.top_observed_amount_yen)}",
            ],
        ],
        caption="time-series バインディングの構造ゲートと後続の機能ゲート",
        widths=(1.4, 2.8, 2.4),
    )
    builder.callout(
        "note",
        f"この {num(facts.observation.top_observed_count)} 観測 / "
        f"{yen(facts.observation.top_observed_amount_yen)}は raw の観測値です。"
        f"time-series バインディングは raw `{binding.source_table}` を読むため、"
        "重複排除は行われません（deduplication = none）。"
        f"重複した EventID の行も残っており、raw 全体は "
        f"{num(context.expected_increment['rawRows'])} 行 / "
        f"{yen(context.expected_increment['rawAmountYen'])}です。"
        f"重複を除いた {num(context.expected_increment['uniqueEventIds'])} 件 / "
        f"{yen(context.expected_increment['deduplicatedAmountYen'])}は、"
        "設計を理解するための比較値であって、Ontology も Data Agent も返せる値ではありません。",
        title="ここに出る数値は raw 観測値",
    )
    builder.table(
        ["症状", "原因", "直す場所"],
        [
            [
                "Instances に観測が 1 件も出ない",
                "選んだテーブルがマテリアライズドビューだった、"
                "またはトリガー経由の取り込みがまだ 1 本も成功していない",
                f"第 14 章の手順 5（raw `{binding.source_table}` を選ぶ）と第 12.4 節",
            ],
            [
                "観測は出るが件数が想定より小さい",
                "Timestamp 列が UTC でない列に設定されている",
                f"第 14 章の手順 7（`{binding.timestamp_column}` を指定）",
            ],
            [
                "自治体と観測がひも付かない",
                "キー対応が `MunicipalityID` → "
                f"`{municipality.key_property}` になっていない",
                "第 14.1 節のキー対応ゲート",
            ],
            [
                "定義は正しいのに古い値のまま見える",
                "上流のソースだけが更新され、グラフモデルがそれを知らない",
                "グラフモデルの［Schedule］→［Refresh now］で手動更新してから再確認する",
            ],
        ],
        caption="time-series バインディングのトラブルシュート",
        widths=(1.8, 2.6, 2.2),
        font_size=8.5,
    )
    _shot(
        builder,
        "14-1",
        "Municipality の Overview。time-series binding 保存直後はタイルが自動作成されず、空表示でも正常。",
        "Municipality インスタンスの Overview に There are no tiles to display for this overview と表示されている現行 UI。",
    )
    builder.callout(
        "gate",
        "Overview の空表示だけで再作成しないでください。"
        "Configure で 3 つの対応付けを確認し、第 15 章の Notebook 02 と第 16 章の Data Agent 構成を完了します。"
        f"第 17.0 節の教材用 full Ontology 確認で `{observed_id}` が {num(facts.observation.top_observed_count)} 観測 / "
        f"{yen(facts.observation.top_observed_amount_yen)}にならない場合にだけ、"
        f"Timestamp と `MunicipalityID` → `{context.entity('Municipality').key_property}` を見直します。",
        title="機能確認は第 17.0 節へ",
    )
    builder.callout(
        "stop",
        f"time-series Property が 1 件も作られていない状態で第 15 章の Notebook 02 を実行しても、"
        "件数が 1 つ少ないまま登録されるわけではありません。preflight が契約の差分を検出して停止します。"
        f"出力される差分は `Count mismatch for timeseriesProperties: Ontology has 0, manifest expects "
        f"{context.ontology_contract['timeseriesProperties']}` です。"
        "この時点で定義へのパッチは生成されず、書き込みも行われないため、登録件数は 0 件です。"
        f"このときの Ontology は {context.ontology_contract['entityTypes']} + "
        f"{context.ontology_contract['staticProperties']} + 0 + "
        f"{context.ontology_contract['relationshipTypes']} = "
        f"{context.metadata_object_count - context.ontology_contract['timeseriesProperties']} という"
        "前提条件の状態にあり、契約が要求するのは "
        f"{context.ontology_contract['entityTypes']} + {context.ontology_contract['staticProperties']} + "
        f"{context.ontology_contract['timeseriesProperties']} + "
        f"{context.ontology_contract['relationshipTypes']} = {context.metadata_object_count} です。"
        "この章のバインディングが、足りない 1 件を作ります。",
        title=f"time-series Property がないと Notebook 02 は 0 件で停止する",
    )
    chapter_pointer(builder, "第 14 章")


def chapter_15_notebook02(builder: DocumentBuilder, context: RuntimeContext) -> None:
    contract = context.ontology_contract
    builder.heading("15. Notebook 02：セマンティックメタデータの一括登録", 1, new_page=False)
    builder.body(
        "Notebook 02 は、Fabric Ontology の getDefinition / updateDefinition を使って "
        "semanticEnrichment だけを更新します。ID・バインディング・コンテキスト化・その他の部分はすべて保持されます。"
        "既定は preview のみで、書き込みには 3 つのゲートをすべて満たす必要があります。"
    )
    builder.table(
        ["対象", "件数", "内容"],
        [
            ["Entity Type", num(contract["entityTypes"]), "説明・同義語・追加メタデータ"],
            ["静的 Property", num(contract["staticProperties"]), "説明・業務上の役割・粒度・集計既定"],
            ["time-series Property", num(contract["timeseriesProperties"]), "観測であることと集計境界"],
            ["Relationship Type", num(contract["relationshipTypes"]), "方向・カーディナリティ・集計ガード・否定的意味"],
            [
                "合計",
                num(context.metadata_object_count),
                f"{contract['entityTypes']} + {contract['staticProperties']} + "
                f"{contract['timeseriesProperties']} + {contract['relationshipTypes']}",
            ],
        ],
        caption=f"Notebook 02 が登録する {context.metadata_object_count} 件のメタデータ",
        widths=(1.8, 0.8, 3.6),
    )
    builder.callout(
        "gate",
        f"time-series Property が存在しない状態で実行すると、preflight が "
        f"`Count mismatch for timeseriesProperties: Ontology has 0, manifest expects "
        f"{contract['timeseriesProperties']}` を出して停止します。"
        "定義へのパッチは生成されず、1 件も登録されません（部分適用はありません）。"
        "第 14 章のバインディングと Ontology の更新完了を先に確認してください。",
    )

    builder.heading("15.1 実行手順（preflight → preview → apply）", 2)
    builder.bullets(
        (
            "Notebook 02 を対象 Workspace / Folder に取り込みます。"
            "PARTICIPANT_ID と EXPECTED_WORKSPACE_NAME を確認し、Workspace 全体で対象 Ontology 名が一意であることを確かめます。",
            "preview：APPLY_CHANGES=False のまま［Run all］し、DRY_RUN_COMPLETE と計画内容を確認します。",
            "apply：APPLY_CHANGES=True、APPLY_CONFIRMATION=\"APPLY ONTOLOGY METADATA\"、"
            "EXCLUSIVE_APPLY_WINDOW_CONFIRMED=True を設定して再実行します。",
            f"適用後に {context.metadata_object_count} 件が登録されたことを出力で確認します。",
        ),
        numbered=True,
    )
    builder.callout(
        "note",
        f"Notebook 03 / 04 の完全定義には、time-series Property と {context.metadata_object_count} 件の"
        "semanticEnrichment が既に含まれます。その経路では Notebook 02 の差分が 0 件でも異常ではありません。"
        "手動構築では第 14 章が先、完全定義の経路では既存定義の確認が先です。"
        "「今回追加した件数」と「現在の定義にある総件数」を区別して記録してください。",
        title="代替構築後のメタデータは既存分も数える",
    )
    builder.callout(
        "note",
        "preflight は契約の差分をすべて集めてから停止します。差分が 1 つでもあれば、"
        "パッチ済みの定義を作る前に例外を投げるため、部分的に書き込まれた状態にはなりません。"
        "差分を直したうえで preview からやり直してください。",
        title="fail-closed（部分適用はしない）",
    )
    builder.table(
        ["preflight が止まる理由", "出力に現れる差分", "直す場所"],
        [
            [
                "Direction 不一致",
                "Relationship の source / target が manifest と逆",
                "第 9 章の Relationship Type（Origin と Target の入れ替え）",
            ],
            [
                "名前集合の不一致",
                "Entity Type / Property / Relationship の名前が manifest に無い、または足りない",
                "第 8 章の Property 名と第 9 章の Relationship 名（大文字小文字も一致させる）",
            ],
            [
                "値の型（valueType）不一致",
                "Property の String / BigInt が manifest と違う",
                "第 8 章の Property 定義（型を選び直す）",
            ],
            [
                "キー指定（isKey）不一致",
                "キーに指定した Property が manifest と違う",
                "第 8 章の Entity Type ごとのキー Property",
            ],
            [
                "表示名指定（isDisplayName）不一致",
                "表示名に指定した Property が manifest と違う",
                "第 8 章の Entity Type ごとの表示名 Property",
            ],
            [
                "time-series Property 件数不一致",
                f"`Count mismatch for timeseriesProperties: Ontology has 0, manifest expects "
                f"{contract['timeseriesProperties']}`",
                "第 14 章の time-series バインディング",
            ],
        ],
        caption="Notebook 02 の preflight が停止する 6 つのパターン",
        widths=(1.6, 2.8, 2.2),
        font_size=8.2,
    )
    builder.callout(
        "gate",
        "preflight のメッセージは「どのオブジェクトのどの属性が」まで出ます。"
        "名前・型・キー・表示名の差分は第 8 章に、方向の差分は第 9 章に戻ります。"
        "Notebook 02 側のパラメーターを変えて回避しようとしないでください。"
        "manifest は runtime の正本であり、合わせるのは Ontology 側です。",
        title="差分は Ontology 側で直す",
    )
    builder.callout(
        "stop",
        "manifest が正本であるという前提は、preview と apply のあいだも変わりません。"
        "preview を実行してから apply を実行するまでのあいだに、"
        "別の編集手段から同じ Ontology を書き換えないでください。"
        "途中で定義が変わると、apply の再検証で差分が出て停止するか、"
        f"登録件数が契約の {context.metadata_object_count} 件と合わなくなります。"
        "共同作業をしている場合は、apply が終わるまで編集を止めてもらってください。",
        title="preview と apply のあいだは同時編集しない",
    )
    _shot(
        builder,
        "8-19",
        "preview の完了。DRY_RUN_COMPLETE により定義を変更していないことを確認する。",
        "Notebook 02 の実行結果。DRY_RUN_COMPLETE と表示され、定義への書き込みが行われていないことを示している。",
    )
    _shot(
        builder,
        "15-1",
        f"apply 完了後。{context.metadata_object_count} 件のメタデータが適用され、差分 0 件になったことを確認する。",
        "Notebook 02 の apply 実行結果。メタデータ適用完了と再検証の差分ゼロが表示されている。",
    )

    builder.heading("15.2 Notebook 02 のパラメーター", 2)
    builder.body(
        "Notebook 02 の全パラメーターはこの表が唯一の完全版です。付録 B には 5 Notebook の索引だけを置いています。"
    )
    builder.table(
        list(PARAMETER_COLUMNS),
        build_parameter_rows(context, "Notebook_02"),
        caption="Notebook 02 のパラメーター仕様（Core で使用する全項目）",
        widths=PARAMETER_WIDTHS,
        font_size=PARAMETER_FONT,
        header_size=PARAMETER_HEADER_FONT,
    )
    chapter_pointer(builder, "第 15 章")
