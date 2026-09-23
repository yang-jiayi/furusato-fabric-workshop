"""Data Agent, testing, publish, troubleshooting chapters and the appendices."""

from __future__ import annotations

import hashlib
import re

from . import guide_content as gc
from . import guide_unified as gu
from .context import RuntimeContext, num, yen
from .docx_kit import DocumentBuilder
from .publication import PUBLIC_PARAMETER_NOTE, PUBLIC_RECORD_INTRO, PUBLIC_RECORD_NOTE
from .facts import TestFacts
from .guide_handson import (
    PARAMETER_FONT,
    PARAMETER_HEADER_FONT,
    PARAMETER_WIDTHS,
    _shot,
    chapter_pointer,
)
from .parameters import PARAMETER_COLUMNS, build_parameter_rows
from .tests10 import HeldOutTest
SOURCE_LABELS = {
    "lakehouse_tables": "Lakehouse（静的 2025 スナップショット）",
    "kusto": "Eventhouse（2026 年 8 月の運用観測）",
    "ontology": "Ontology（関係トラバース）",
}

#: The first table an example query reads. Only the entry table is taken: a
#: later ``JOIN`` widens the answer but does not change which table the shape
#: starts from, and it is the entry table that decides whether two examples
#: compete for the same question.
_FIRST_FROM = re.compile(r"\bFROM\s+(dbo\.[A-Za-z0-9_]+)", re.IGNORECASE)


def _first_from_table(query: str) -> str:
    match = _FIRST_FROM.search(query or "")
    return match.group(1) if match else ""


def _selected_lakehouse_tables(context: RuntimeContext) -> list[str]:
    """Every Lakehouse table the shipped definition marks as selected."""
    if context.is_unified_guide:
        return [
            ".".join(part[1] for part in entry["path"])
            for entry in context.guide_profile.sources["lakehouse_tables"]["elements"]
            if entry["path"][-1][0] == "Table"
        ]
    selected: list[str] = []

    def walk(node: dict) -> None:
        if node.get("type") == "lakehouse_tables.table" and node.get("is_selected"):
            selected.append(str(node.get("display_name")))
        for child in node.get("children", ()):
            walk(child)

    for element in context.agent_sources["lakehouse_tables"].get("elements", ()):
        walk(element)
    return selected


def _example_query_gate_rows(context: RuntimeContext) -> list[list[str]]:
    """The example-query checklist, with the shipped set's own status beside it."""
    shots = context.agent_fewshots
    selected = _selected_lakehouse_tables(context)
    entry_tables = [_first_from_table(shot["query"]) for shot in shots]
    return [
        [
            "問いとクエリの対応",
            "質問文が求める指標・期間・絞り込みが、そのままクエリの列と述語に現れている。",
            f"{len(shots)} 件とも、県名・年月・カテゴリという絞り込みが SQL の述語に対応している。",
        ],
        [
            "形の重複を避ける",
            "例ごとに入口のテーブルと集計の形を変え、言い換えただけの例を増やさない。",
            f"入口のテーブルは {'・'.join(f'`{name}`' for name in entry_tables)} で、"
            "単一テーブルの参照・月次の集計・結合つきの内訳という 3 つの形に分かれている。",
        ],
        [
            "同じ意図で矛盾させない",
            "同じ意図の問いに対して、違うテーブルや違う集計を返す例を同居させない。",
            "対象範囲（県の受入と在住、支払い方法、カテゴリ別）が重ならないため、"
            "同じ問いに 2 つの答え方が並ぶ状態にならない。",
        ],
        [
            "実データの表記で書く",
            "絞り込みの値は、実際に格納されている表記と形式のまま書く。",
            "県名は格納された日本語表記のまま、年月は `DonationYearMonthJst` の格納形式のまま指定している。",
        ],
        [
            "スキーマに実在する",
            "参照するテーブルと列が、選択済みのスキーマの中に実在する。",
            f"参照先はすべて `dbo` の `ot_` テーブルで、第 16.2 節で選択した {len(selected)} 個に含まれる。",
        ],
        [
            "検証を通す",
            "登録した例が検証を通ることを確認する。通らなかった例は使われない前提で見直す。",
            "登録前に、質問の一意性・クエリの非空・入口テーブルの重複・"
            "選択済みテーブルへの帰属を確認し、登録後は Fabric の検証結果を確認する。",
        ],
        [
            "引かれた例を見る",
            "回答の［実行詳細］で、その質問にどの例が使われたかを確認する。",
            "第 17 章の記録時に、ルートの確認と同じ画面で見る。",
        ],
        [
            "held-out を漏らさない",
            "評価に使う問いの文・期待値・安定 ID を、例クエリに含めない。",
            "第 17 章の 10 問の質問文・期待値・安定 ID はいずれも含まれていない。",
        ],
    ]


def chapter_16_data_agent(builder: DocumentBuilder, context: RuntimeContext) -> None:
    if context.is_unified_guide:
        ontology = context.guide_profile.sources["ontology"]
        if "instructions" not in ontology or ontology["instructions"] is not None:
            raise ValueError("Unified Ontology source instructions must remain null; use GLOBAL and metadata.")
    names = context.names
    builder.heading("16. Fabric Data Agent の構成", 1)
    if context.is_unified_guide:
        gu.agent_intro(builder, context)
    else:
        builder.body(
            f"［新規］→［Data agent］で {names['dataAgent']} を作成し、Lakehouse・KQL Database・Ontology の "
            "3 ソースを追加します。設定は 3 つの層に分かれており、それぞれ責務が違います。"
            "同じルールを複数の層に重ねて書くと、矛盾したときにどれが効いているのか判別できなくなるため、"
            "v2.7.0 では層ごとに抽象度を分けています。"
        )
        builder.callout(
            "note",
            "第 16.1〜16.8 節は教材用 full Ontology を使う標準コース（Core）の構成手順です。"
            "AI 参照構成を選ぶ場合は、第 16.9 節の別 Agent・別 Ontology・専用の固定済み bundle を使います。"
            "両コースでソース選択と指示が異なるため、実際に使用する Agent と接続先を確認してください。",
            title="標準コースと AI 参照構成の設定を混ぜない",
        )
    builder.figure(
        context.diagrams["data-agent-source-routing"]["png"],
        caption="口語の質問を分解し、ソースへルーティングし、安定 ID でのみ突き合わせる流れ。",
        alt_text=(
            "ソースルーティング図。左に口語の質問があり、指標・時間スコープ・粒度への分解を経て、"
            "3 つのソース（Lakehouse SQL、Eventhouse KQL、Ontology GQL）に振り分けられる。"
            "右側では、それぞれの結果を安定 ID でのみ突き合わせ、粒度をまたぐ加算を禁止することが示されている。"
        ),
        max_height_cm=10.5,
    )

    builder.heading("16.1 設定の 3 層と責務", 2)
    builder.body(
        (
            "3 層は、ソースをまたぐ判断・ソースの識別・ソース固有の照会規則を分担します。"
            "この統合プロファイルの GLOBAL には、根拠の所有者を指定するためのテーブル・関数・列名と、"
            "Ontology の関係名・方向も含まれます。ソース指示には対応する列・引数・期間・粒度の詳細を置きます。"
            "具体名が含まれることを理由に配布 GLOBAL を削ったり、指示を別の層へ移したりしません。"
        ) if context.is_unified_guide else
        "3 層は「重複がない」のではなく、抽象度が違います。グローバル指示はソースを問わない判断基準を、"
        "ソース指示はそのソースの列名・関数・スコープという具体を持ちます。同じ主題（たとえば粒度）が"
        "両方に現れることはありますが、書き方が違います。条件も具体化もない"
        "「そのままの再掲」は避け、各層に必要な規則を書きます。"
    )
    builder.table(
        ["層", "抽象度", "何を書くか", "書かないこと", "理由"],
        [
            [
                "グローバル指示（Agent instructions）",
                "抽象（判断基準）",
                "ソースルーティング、用語の解決、粒度の規則、関係の境界、安全、回答形式",
                "未選択ソースへの迂回、実行していない根拠、テストの答え"
                if context.is_unified_guide else "個々のテーブル名・列名・クエリの書き方",
                "全ソースに共通する判断基準を一箇所に置く。",
            ],
            [
                "ソース説明（Description）",
                "識別（何を持つか）",
                "そのソースが何を持ち、何を持たないか",
                "クエリの書き方や集計手順",
                "ルーティングの判断材料になる。短く、否定形を含める。",
            ],
            [
                "ソース指示（Source instructions）",
                "具体（列と関数）",
                "そのソース固有の列・集計関数・スコープの規則。グローバルの規則をこのソースの語彙に翻訳する。",
                "他ソースの規則、条件のない一字一句の再掲",
                "ソースを切り替えたときにだけ必要な知識を置く。",
            ],
            [
                "例クエリ（Example queries）",
                "形",
                f"SQL {len(context.agent_fewshots)} 件 + KQL {len(context.guide_kql_fewshots)} 件"
                if context.is_unified_guide else f"代表的な形の {len(context.agent_fewshots)} 件のみ",
                "テストの答えになる問い",
                "形を示すためのものであり、答えを教え込むものではない。",
            ],
        ],
        caption="Data Agent 設定の 3 層＋例クエリの責務",
        widths=(1.7, 1.1, 2.4, 1.7, 1.7),
        font_size=8.2,
    )
    builder.callout(
        "design",
        "たとえば「粒度をまたいで足さない」は、グローバル指示では「静的スナップショットと運用観測は"
        "別データセットであり合算しない」という判断基準として書かれます。Eventhouse のソース指示では"
        "「`ObservationCount` は観測数であり寄付件数ではない」という列レベルの具体になります。"
        "同じ主題ですが、片方を消すともう片方だけでは判断できません。"
        "ソース指示には、そのソースの列と操作に具体化した規則を置いてください。",
        title="「重複ゼロ」ではなく「抽象度の分担」",
    )
    builder.callout(
        "design",
        (
            "本版の Ontology ソース指示は null のまま保持します。関係の規則は統合 GLOBAL、"
            "ソース説明、Notebook 02 の完全なメタデータで与えます。例クエリは SQL と KQL だけで、Ontology には追加しません。"
            "Ontology 専用の追加指示ファイルを必要とせず、未対応のソース指示欄へ貼り付けません。"
            "GLOBAL やメタデータの保存だけで GQL 実行能力や応答品質を証明したことにしません。"
            "SQL の schema object descriptions と Ontology 自体のメタデータは別の設定です。"
        ) if context.is_unified_guide else
        "本教材の Ontology ソースにはソース指示も例クエリも設定しません。ソース説明と、"
        "Notebook 02 で登録したセマンティックメタデータで意味を与える構成です。"
        "これは回答精度の保証ではありません。編集できそうな JSON フィールドがあっても、"
        "そのソースでの対応・有効性を確認せず追加しません。"
        "SQL の schema object descriptions と Ontology 自体のメタデータは別の設定です。",
    )
    builder.callout(
        "note",
        "ここで構成する Fabric Data Agent は、既存のソースへ問い合わせて回答する消費側の仕組みです。"
        "Ontology の定義そのものを書き換える編集支援ではありません。"
        "この Data Agent をいくら設定しても、エンティティ・関係・プロパティは変わりません。"
        "編集を生成 AI に手伝わせるという考え方については、"
        "評価の観点だけを付録 D.6 にまとめてあります（Core では実施しません）。",
        title="Data Agent は消費側であって編集側ではない",
    )

    if context.is_unified_guide:
        gu.source_selection(builder, context)
        runtime_figure = _shot(
            builder,
            "13-6",
            "ソース追加後の Data Agent Explorer。リボンの［Runtime］は Preview。",
            "3 つのソースが追加された Data agent の Explorer 画面。リボンの Runtime が Preview になっている。",
        )
    else:
        runtime_figure = _legacy_source_selection(builder, context)
    _agent_configuration(builder, context, runtime_figure)


def _legacy_source_selection(builder: DocumentBuilder, context: RuntimeContext) -> int:
    names = context.names
    builder.heading("16.2 Data Agent を作成してソースを追加する", 2)
    lakehouse_tables = len(context.expected["outputTableCounts"])
    materialized_views = [
        entry for entry in context.kql_objects if entry.command == "create-or-alter materialized-view"
    ]
    raw_tables = [entry for entry in context.kql_objects if entry.command == "create-merge table"]
    builder.bullets(
        (
            "指定 Folder がある場合はその Folder を開き、［新規］→［Data agent］を選びます。ここが本章の起点です。",
            f"Create data agent ダイアログに `{names['dataAgent']}` を入力して作成します。",
            "作成直後の画面で、データの追加・エージェント指示・テスト・公開の 4 領域が"
            "表示されていることを確認します。",
            "新規 Agent の既定は Standard runtime です。リボンの［Runtime］で Preview を明示的に選びます。",
            "［Add Data］→［Data source］を選びます。",
            "OneLake catalog で Lakehouse・KQL Database・Ontology を選択します。",
            "追加後の Explorer で 3 ソースが並び、リボンの［Runtime］が Preview であることを確認します。",
            f"Lakehouse ソースでは {lakehouse_tables} 個の ot_ テーブルにチェックを入れます。",
            f"KQL Database ソースでは［Materialized views］を展開し、"
            f"`{materialized_views[0].name}` だけにチェックを入れます。",
            f"同じ画面の［Tables］にある `{raw_tables[0].name}` のチェックは必ず外します。",
            "Ontology ソースでは 10 Entity Type がすべて選択されていることを確認します。",
        ),
        numbered=True,
    )
    builder.callout(
        "stop",
        "Preview を選べない、必要なソースを追加できない、または API が Data Agent の定義を受け付けない場合は、"
        "未完了の工程とエラーを記録します。ランタイムの選択は、ソース対応や API 対応を保証しません。"
        "API 構築の代わりにこの節の UI 手順で構成できた場合も、代替経路として区別し、"
        "同じ 3 ソース・選択要素・指示・Preview runtime と第 17 章の評価を確認します。"
        "Standard の結果や定義の作成成功だけで、Core の応答確認を済ませたことにしません。",
        title="Preview・定義作成・応答確認は別のゲート",
    )
    builder.callout(
        "stop",
        f"KQL Database ソースで raw の `{raw_tables[0].name}` を選択したままにすると、"
        "Data Agent は EventID を直接数えられるようになります。すると第 17 章の T07 は"
        "「一意 EventID は数えられない」という設計上の境界ではなく、単なる件数の質問になり、"
        f"テストが意味を失います。Agent に見せるのは `{materialized_views[0].name}` の 1 件だけです。",
        title="raw テーブルは選ばない（T07 の前提）",
    )
    builder.table(
        ["ソース", "選択する要素", "件数", "選択しないもの"],
        [
            [
                "Lakehouse",
                "`ot_` で始まる出力テーブル",
                str(lakehouse_tables),
                "`stg_` ステージングテーブル、監査テーブル",
            ],
            [
                "KQL Database",
                f"Materialized views > `{materialized_views[0].name}`",
                str(len(materialized_views)),
                f"Tables > `{raw_tables[0].name}`（raw 観測）",
            ],
            [
                "Ontology",
                "Entity Type（全件）",
                str(context.ontology_contract["entityTypes"]),
                "—（Entity Type 単位の選択解除はしない）",
            ],
        ],
        caption="3 ソースで選択する要素と件数",
        widths=(1.2, 2.4, 0.7, 2.4),
    )
    builder.callout(
        "gate",
        f"ソース追加が終わったら、Explorer で 3 ソース・要素数 Lakehouse {lakehouse_tables} / "
        f"KQL {len(materialized_views)} / Ontology {context.ontology_contract['entityTypes']} "
        "になっていることを数えて確認します。件数の単位は順にテーブル・マテリアライズドビュー・Entity Type で、"
        "列などの子要素を含む総数ではありません。ここが合っていないと、"
        "第 17 章の失敗がルーティングの問題なのか選択の問題なのか切り分けられません。",
        title="ソースと要素の件数ゲート",
    )
    builder.callout(
        "note",
        "ソース画面を開くと、内部の element ID や未選択の枝が変わる場合があります。"
        "比較では、参照先の実 ID、選択したテーブル・ビュー・Entity Type、指示、説明の一致を確認します。"
        "UI 内部の識別子を参照先 ID と混同せず、選択違い・参照先違い・説明の変更を無視して一致扱いにしません。",
        title="画面の展開情報と参照先・選択内容を区別する",
    )
    runtime_figure = 0
    for tag, caption, alt in (
        ("13-1", "［新規］→［Data agent］を選択する。", "Fabric の新規作成メニューで Data agent を選ぶ画面。"),
        ("13-2", f"Create data agent ダイアログで {names['dataAgent']} を入力する。", "Data agent の作成ダイアログに名前を入力している画面。"),
        ("13-3", "Data Agent 作成直後の画面。", "作成直後の Data agent 画面。データの追加、エージェント指示、テスト、公開の各領域が表示されている。"),
        ("13-4", "［Add Data］→［Data source］を選択する。", "Data agent の画面でデータソースを追加するメニューを開いている。"),
        ("13-5", "OneLake catalog で Lakehouse・KQL Database・Ontology を選択する。", "OneLake catalog から 3 種類のソースを選択している画面。"),
        ("13-6", "ソース追加後の Data Agent Explorer。リボンの［Runtime］は Preview。", "3 つのソースが追加された Data agent の Explorer 画面。リボンの Runtime が Preview になっている。"),
        ("13-7", "Lakehouse ソースで ot_ テーブルにチェックを入れた状態。", "Lakehouse ソースのテーブル選択画面。ot_ で始まるテーブルにチェックが入っている。"),
    ):
        number = _shot(builder, tag, caption, alt)
        if tag == "13-6":
            runtime_figure = number
    return runtime_figure


def _agent_configuration(builder: DocumentBuilder, context: RuntimeContext, runtime_figure: int) -> None:
    builder.heading("16.3 グローバル指示", 2)
    builder.body(
        f"配布されている `{context.guide_instruction_relative_path}` の全文を、"
        "［Agent instructions］に貼り付けます。加筆や要約はしません。"
    )
    if not context.is_unified_guide:
        _shot(
            builder,
            "13-12",
            "［Agent instructions］画面。ここにグローバル指示の全文を貼り付ける。",
            "Data agent のエージェント指示画面。指示テキストを入力する大きなテキスト領域が表示されている。",
        )
    instructions = context.guide_agent_instructions
    instruction_char_limit = int(
        context.workspace_contract["dataAgent"]["globalInstructionsCharLimit"]
    )
    paste_instructions = instructions.rstrip("\r\n")
    paste_chars = len(paste_instructions)
    paste_bytes = len(paste_instructions.encode("utf-8"))
    paste_sha = hashlib.sha256(paste_instructions.encode("utf-8")).hexdigest()
    file_chars = len(instructions)
    file_bytes = len(instructions.encode("utf-8"))
    file_sha = hashlib.sha256(instructions.encode("utf-8")).hexdigest()
    builder.code_block(paste_instructions, language="Agent instructions（全文）")
    builder.body(
        f"画面へ貼り付ける本文（配布ファイル末尾の LF を除いた表示内容）の整合性確認："
        f"文字数 {num(paste_chars)} 文字 / UTF-8 バイト数 {num(paste_bytes)} バイト / "
        f"SHA-256 `{paste_sha}`。配布ファイル自体は末尾 LF 1 文字を含むため、"
        f"{num(file_chars)} 文字 / {num(file_bytes)} バイト / SHA-256 `{file_sha}` です。"
        "テキストエディターで文字数を確認し、末尾の行まで貼り付けられていることを確かめてください。"
        "貼り付け本文と配布ファイルのどちらを確認しているかを区別し、それぞれ上記の照合値を使用してください。"
    )
    builder.callout(
        "note",
        f"グローバル指示の上限は、本ワークショップでは {num(instruction_char_limit)} 文字です。"
        "これは本ワークショップが自分に課した安全側の上限であり、"
        "製品スキーマとして公開された保証値や、将来にわたって変わらない値として引用しないでください。"
        f"上の全文は {num(paste_chars)} 文字で、この上限の内側に収まっています。"
        "自分の題材へ差し替えるときは、その時点の製品ドキュメントと画面表示で現在値を確認してください。",
        title=f"{num(instruction_char_limit)} 文字は本ワークショップの指示上限",
    )
    builder.callout(
        "gate",
        "グローバル指示は要約しないでください。"
        "保存した Draft の本文を開き直し、配布された全文と一致することを確認します。"
        "公開後は Published の本文も確認してください。"
        "1 文字でも変更した場合は、設定変更として第 17 章の 10 問をすべてやり直します。",
        title="保存後と公開後に指示の全文を確認する",
    )

    builder.heading("16.4 ソース説明", 2)
    rows = []
    for source_type, label in SOURCE_LABELS.items():
        description, _instructions = context.guide_source_text(source_type)
        rows.append([label, description])
    builder.table(
        ["ソース", "説明（Description）"],
        rows,
        caption="3 ソースの説明。何を持たないかを必ず含める。",
        widths=(1.4, 5.0),
        font_size=8.2,
    )

    builder.heading("16.5 ソース指示", 2)
    _, lakehouse_instructions = context.guide_source_text("lakehouse_tables")
    _, kusto_instructions = context.guide_source_text("kusto")
    _, ontology_instructions = context.guide_source_text("ontology")
    # The count is read from the shipped instructions, never restated by hand, so
    # the guide cannot promise a different number of shapes from the one pasted.
    kusto_shape_count = kusto_instructions.count("summarize sum(ObservationCount)")
    builder.body("Lakehouse ソースには、静的スナップショット固有の規則だけを設定します。")
    builder.code_block(lakehouse_instructions.strip(), language="Lakehouse のソース指示")
    if context.is_unified_guide:
        builder.body(
            "Eventhouse のソース指示は、承認済み MV と 3 関数の使い方・期間・provenance・raw の留保を定義します。"
            "この統合プロファイルでは Eventhouse の例クエリも登録します。"
            "固定済みの kusto-fewshots.json とソース指示を同じ版で照合し、"
            "UTC 文字列・null・file/run provenance の規則を揃えます。"
        )
    else:
        builder.body(
            "Eventhouse ソースには、マテリアライズドビューの読み方と、"
            "このソースでは確立できない事実を明示します。"
            "本教材では Eventhouse の例クエリは別途登録せず、"
            f"KQL の例パターン {kusto_shape_count} 件はこのソース指示の中に置いています。"
            "列名・粒度の規則と同じ場所に形を置くことで、片方だけ直して食い違う事故も避けられます。"
        )
    builder.callout(
        "note",
        "これは本ワークショップが出荷した定義の事実であって、"
        "「Eventhouse ソースには例クエリを設定できない」という製品全体の能力の説明ではありません。"
        "どのソース種別が例クエリを持てるかは変わりうるため、"
        "自分の環境で構成するときは付録 E の Data Agent source capability matrix と "
        "Data Agent example queries で現在の対応状況を確認してください。",
        title="配布物の事実であり、製品の能力の主張ではない",
    )
    builder.code_block(kusto_instructions.strip(), language="Eventhouse のソース指示")
    builder.table(
        ["ソース", "ソース指示", "例クエリ"],
        [
            ["Lakehouse", "あり", f"{len(context.agent_fewshots)} 件（SQL）"],
            [
                "Eventhouse",
                "あり（MV と 3 関数の契約）" if context.is_unified_guide
                else f"あり（KQL の例パターン {kusto_shape_count} 件を内包）",
                f"{len(context.guide_kql_fewshots)} 件（KQL、固定済み JSON）" if context.is_unified_guide
                else "0 件（KQL の例パターンはソース指示に記載）",
            ],
            [
                "Ontology",
                "なし" if not ontology_instructions else "あり",
                "0 件（説明・GLOBAL と完全なセマンティックメタデータ）" if context.is_unified_guide
                else "0 件（説明とセマンティックメタデータのみ）",
            ],
        ],
        caption="ソースごとの設定の有無",
        widths=(1.2, 3.0, 2.4),
    )
    if context.is_unified_guide:
        gu.source_rules(builder)

    builder.heading("16.6 例クエリ", 2)
    builder.body(
        f"Lakehouse ソースには {len(context.agent_fewshots)} 件の SQL 例だけを登録します。"
        "例クエリの役割は「どういう形のクエリを書くか」を示すことだけです。"
        "第 17 章のテストとクエリの形が部分的に重なることはありますが、"
        "問いの対象（都道府県、期間、エンティティ）はいずれも異なり、"
        "10 問の答えにあたる値・安定 ID・質問文はどれも含まれていません。"
        "「形がすべて違う」のではなく「答えを先に教えていない」ことが要件です。"
    )
    for index, fewshot in enumerate(context.agent_fewshots, start=1):
        builder.body(f"例 {index}：{fewshot['question']}")
        builder.code_block(fewshot["query"].strip(), language="Lakehouse の例クエリ（SQL）")
    if context.is_unified_guide:
        builder.body(
            "Eventhouse の例は unified-agent/inputs/kusto-fewshots.json の質問文とクエリをそのまま登録します。"
            "以下は配布物の英語原文です。全 scope の totals、file/run 内訳、件数・金額首位の 3 形を示し、"
            "返却する時刻を ISO-8601 UTC の文字列に揃えます。期待値や固定の回答を埋めず、"
            "実行詳細で実際に使われた例と返却結果を確認します。"
        )
        for index, fewshot in enumerate(context.guide_kql_fewshots, 1):
            builder.body(f"KQL example {index}: {fewshot['question']}")
            builder.code_block(fewshot["query"].strip(), language="Eventhouse の例クエリ（KQL）")

    builder.heading("16.6.1 例クエリの品質ゲート", 3)
    if context.is_unified_guide:
        builder.body(
            "以下の入口テーブルの検査は SQL の例を対象にします。KQL の例は承認済みの 3 関数ごとに分け、"
            "関数・出力列・UTC 文字列・null の扱いとソース指示の一致を確認します。"
            "どちらも元の 10 問の質問・期待値を追加するための例ではありません。"
        )
    first_tables = [_first_from_table(shot["query"]) for shot in context.agent_fewshots]
    selected_tables = _selected_lakehouse_tables(context)
    gate_rows = _example_query_gate_rows(context)
    distinct_first = len(set(first_tables)) == len(first_tables)
    builder.body(
        f"例クエリは自由記述ではなく、登録する前に満たすべき条件があります。"
        f"下の {len(gate_rows)} 項目は、自分の題材で例クエリを書くときにも使える確認表です。"
        "公開されている構成のベストプラクティスと例クエリのページに沿っており、"
        "リンクは付録 E にあります。"
    )
    builder.table(
        ["観点", "満たすべき条件", "この配布物での状態"],
        gate_rows,
        caption=f"例クエリを登録する前に確認する {len(gate_rows)} 項目",
        widths=(1.2, 2.5, 2.7),
        font_size=8.2,
    )
    builder.callout(
        "gate",
        f"この配布物の {len(context.agent_fewshots)} 件は、最初の `FROM dbo.` が指すテーブルが"
        f"{'すべて異なります' if distinct_first else '重複しています'}"
        f"（{'・'.join(f'`{name}`' for name in first_tables)}）。"
        f"いずれも第 16.2 節で選択した {len(selected_tables)} 個のテーブルの中にあります。"
        f"入口を分けるのは、この教材の {len(context.agent_fewshots)} 例を区別しやすくするための規則です。"
        "同じテーブルを使うだけで例が矛盾する、または結果が変わるという製品制約ではありません。"
        "実務では、同じ意図に対して異なる指標・粒度・絞り込みで答える例が混在していないかを確認します。"
        "この実習では配布された例をそのまま使い、追加・変更しません。",
        title="入口のテーブルは重複させない",
    )
    builder.callout(
        "note",
        "どの例が実際に参照されたかは、回答の［実行詳細］で確認できます。"
        "想定と違う例が引かれていたときは、例を増やす前に質問文の書き方を見直してください。"
        "上位いくつが渡されるかは本書では固定しません。"
        "公開ドキュメントの記述も一致していないため、件数を前提にした設計にしないでください。",
        title="引かれた例は［実行詳細］で確認する",
    )

    builder.heading("16.7 ランタイムと Core の既定設定", 2)
    if context.is_unified_guide:
        gu.runtime_settings(builder, context)
    else:
        _legacy_runtime_settings(builder, context, runtime_figure)
    _agent_boundaries(builder, context)


def _legacy_runtime_settings(builder: DocumentBuilder, context: RuntimeContext, runtime_figure: int) -> None:
    experimental = context.agent_stage_config.get("experimental", {})
    code_interpreter = bool(experimental.get("codeInterpreterEnabled"))
    builder.body(
        "Data Agent のリボンにある［Runtime］ドロップダウンで、Standard runtime と Preview runtime を切り替えられます。"
        "Core では Preview runtime を使用します。"
    )
    builder.table(
        ["設定", "Core の値", "意味"],
        [
            ["Runtime", "Preview", "Core の 10 問は Preview runtime で実施し、記録します。Standard は比較専用で、Core の合否には使いません。"],
            [
                "Code Interpreter",
                "無効（codeInterpreterEnabled = " + ("true" if code_interpreter else "false") + "）",
                "Core は Code Interpreter を使いません。コード実行なしで元の 10 問を評価し、実測で合否を記録します。",
            ],
            [
                "ソース数",
                f"{len(context.agent_sources)}（Lakehouse / Eventhouse / Ontology）",
                "質問に応じて 1 〜 3 ソースを使い分け、突き合わせは安定 ID のみで行います。",
            ],
            [
                "例クエリ",
                f"Lakehouse に {len(context.agent_fewshots)} 件のみ",
                "形を示すためのもので、10 問の答えは含みません。",
            ],
        ],
        caption="Core の Data Agent 既定設定",
        widths=(1.4, 1.8, 3.4),
    )
    builder.callout(
        "gate",
        "Core の Data Agent は Code Interpreter を無効のまま構成します。"
        "Code Interpreter と User data functions は Optional（付録 D.4）であり、"
        "追加する場合は Core の 10 問を通したあとに、追加前後の結果を分けて記録します。",
        title="Core は Code Interpreter を使わない",
    )
    builder.callout(
        "note",
        "保存後の定義で `codeInterpreterEnabled=false` が省略される場合でも、"
        "キーの欠落だけで有効・無効や定義の一致を判定しません。画面の Tools と有効な設定を確認し、"
        "Core では Code Interpreter が無効であることを記録します。"
        "差分を説明できない場合は評価を保留し、無効を確認せずに省略を受け入れません。",
        title="省略された設定値は実際の設定で確認する",
    )
    builder.callout(
        "stop",
        "第 17 章の Core 記録は Preview runtime で実施しなければなりません。"
        "Standard runtime は比較専用であり、Core の合否には使えません。"
        "Standard でしか通らなかった問いは Core としては不合格です。"
        "Standard も試す場合は、Test 10 記録票の各問にある"
        "「Standard runtime での比較」欄へ別に記録し、判定欄には Preview の結果だけを書きます。"
        "実際に使用する Workspace で Preview を選んで評価し、公開時の runtime も別途確認します。"
        "設定の一致だけで応答品質を合格とはしません。",
        title="Core の判定は Preview runtime 必須",
    )
    builder.body(
        f"Core の開始状態は、第 16.2 節でソースを追加した直後の画面（図 {runtime_figure}）と同じです。"
        f"図 {runtime_figure} で、リボンの［Runtime］が Preview になっていること、"
        "Explorer に Lakehouse・KQL Database・Ontology の 3 ソースが並んでいることを合わせて確認してください。"
    )


def _agent_boundaries(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("16.8 指示で守る境界と、応答時間の変数", 2)
    builder.body(
        "3 層の設定は、Agent の振る舞いを決めます。ただし、決められるものと決められないものがあります。"
        "ここを取り違えると、指示に書いたつもりの制限が実際には効いていない、という状態になります。"
    )
    builder.table(
        ["区分", "指示で決められること", "指示では決められないこと"],
        [
            [
                "意味の解釈",
                "用語の解決、粒度の宣言、どのソースを既定にするか",
                "利用者が元々アクセスできないデータを見せること",
            ],
            [
                "拒否",
                "推論要求や境界外の問いを断り、理由を説明すること",
                "権限のないデータを「断ったことにする」こと",
            ],
            [
                "回答形式",
                "根拠の示し方、粒度と時間範囲の明示、単位の書き方",
                "行や列の可視範囲そのものを変えること",
            ],
            [
                "アクセス",
                "—（指示は制御点ではない）",
                "アクセスはサインインした ID、参照元ソースの権限、"
                "および各アイテムが持つソース側の制御で決まる",
            ],
        ],
        caption="指示が決めることと、決めないこと",
        widths=(1.0, 2.6, 2.8),
        font_size=8.5,
    )
    builder.callout(
        "stop",
        "指示はアクセス制御ではありません。"
        "「この列は見せない」と書いても、権限上見えるデータが見えなくなるわけではありません。"
        "実際の可視範囲は、サインインした ID、参照元ソースの読み取り権限、"
        "そして各アイテム種別がソース側で提供する制御によって決まります。"
        "行単位・列単位の制御がどのソースでも同じように使えると仮定しないでください。"
        "対応状況はアイテム種別ごとに異なるため、付録 E のソース関連ページと C.6 で確認します。",
        title="指示は制御点ではない",
    )
    builder.callout(
        "note",
        "第 5.1 節で managed Delta と対応条件を確認するのは、"
        "Ontology の静的バインディングが managed Delta テーブルを前提とするためです。"
        "製品文書にある OneLake Security の制約と、対象 Workspace の実際の設定状態は別です。"
        "対象 Workspace の設定は管理者と確認します。"
        "設定の欠落や import・refresh の成功から、OneLake Security が無効だと推測しません。"
        "本番でアクセス制御が不要だという意味ではありません。"
        "実データに向けるときは、参照元ごとの制御を先に決めてから Data Agent を共有し、"
        "互換性を通すためにセキュリティを変更しません。",
        title="OneLake Security の製品条件と設定状態を確認する",
    )
    builder.body(
        "応答時間も、設定によって変わります。ここでは秒数や倍率は示しません。"
        "環境と質問によって変わる値を書くと、それ自体が誤った期待になるためです。"
        "方向だけを示します。"
    )
    builder.table(
        ["要因", "増える方向", "減らす手立て"],
        [
            [
                "ソースとスキーマの広さ",
                "選択したテーブル（とその全列）とエンティティが多いほど、解釈すべき候補が増える",
                "答えるべき問いに必要な要素だけを選ぶ（第 16.2 節）",
            ],
            [
                "指示と例の量",
                "指示が長いほど、また矛盾する指示や例が混ざるほど、判断が重くなる",
                "層ごとに抽象度を分け、重複と矛盾を減らす（第 16.1・16.6.1 節）",
            ],
            [
                "質問と会話の文脈",
                "質問が曖昧なほど、また会話が長いほど、前提の確定に手数がかかる",
                "1 問 1 会話で実施し、指標と時間範囲を質問に含める（第 17 章）",
            ],
            [
                "エンジン側の処理",
                "生成されたクエリが重いほど、またデータモデルが複雑なほど時間がかかる",
                "集計済みの要素を使い、モデルの複雑さを下げる",
            ],
            [
                "容量とオーケストレーション",
                "容量が混雑しているほど、また 1 問で複数ソースを使うほど待ち時間が伸びる",
                "ソース数を必要最小限にし、混雑時間帯を避けて実施する",
            ],
        ],
        caption="応答時間に効く 5 つの変数（方向のみ、数値は示さない）",
        widths=(1.3, 2.7, 2.4),
        font_size=8.5,
    )
    builder.callout(
        "note",
        "消費の考え方は付録 C.6 にまとめてあります。ここでは繰り返しません。"
        "応答時間と消費は別の話ですが、どちらも「指示と例と文脈が長いほど増える」という点では同じ向きに動きます。",
        pull_up=True,
    )
    if context.is_unified_guide:
        gu.migration(builder, context)
    else:
        _reference_architecture(builder, context)
    chapter_pointer(builder, "第 16 章")


def _reference_architecture(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("16.9 AI 参照アーキテクチャ（明示 opt-in）", 2)
    builder.body(
        "AI 参照構成は、関係の探索と静的属性の取得を分担させる Optional のコースです。"
        "教材用 full Ontology・元の Lakehouse 11 dbo テーブル・合成の静的 2025 スナップショットを保持し、"
        "別の AIPath と Data Agent を構築します。標準コースの教材用モデルを置き換えません。"
        "モデル件数は設計契約であり、応答品質を保証するものではありません。"
    )
    builder.table(
        ["構成", "役割と契約", "使わない範囲"],
        [
            [
                f"教材用 `{context.names['ontology']}`",
                "10 Entity / 72 static Property / 1 time-series Property / 15 Relationship。第 7〜15 章の教材を保持。",
                "AIPath に置き換えたり、削除・縮小したりしない。",
            ],
            [
                "`ONT_Furusato_AIPath_<PID>`",
                "10 Entity / 21 static Property / 0 time-series Property / 15 Relationship（52 parts）。正確な key・名前・関係を保持。",
                "金額・静的属性の計算・time-series の照会には使わない。",
            ],
            [
                "Lakehouse SQL",
                "静的属性・件数・金額・順位は実 SQL から取得。元の 11 dbo テーブル / 88 選択列に agent_ref を追加。",
                "静的データの変更、運用観測との合算、順位の一致による ID 推測をしない。",
            ],
            [
                "Eventhouse KQL",
                "承認済み DonationObservationSummaryForAgent と、そこから導出する関数で raw 観測を取得。",
                "raw DonationEvents・EventID・一意イベント指標は直接選択しない。",
            ],
        ],
        caption="教材モデルを残した AI 参照構成のソース分担",
        widths=(1.6, 3.1, 2.1),
        font_size=8.2,
    )
    builder.body(
        "Ontology は count・path・identity の照会に使い、金額を含む静的属性は SQL に任せます。"
        "AIPath にも `MunicipalityCatalogsGift` を含む正規の 15 関係をすべて残します。"
        "静的 2025 は固定した UTC スナップショットの意味です。JST では 2026-01-01 に達する行があり得るため、"
        "任意の JST 暦年フィルターで切り捨てません。Eventhouse は独立した運用観測であり、静的値とは足しません。"
    )
    builder.table(
        ["SQL オブジェクト", "返却列数・粒度", "Agent の直接選択"],
        [
            ["agent_ref.MunicipalityStatic", "20 列の view / 自治体ごと。寄付 0 件の自治体も保持。", "選択"],
            ["agent_ref.DonationAttributes", "40 列の view / Donation ごと。Supplier 登録で増幅しない。", "非選択（参照モデルの内部依存）"],
            ["agent_ref.GiftCatalogSuppliers", "29 列の view / GiftId × SupplierId の登録。", "非選択（参照モデルの内部依存）"],
            ["agent_ref.MunicipalityById", "22 列 / 正確な ID の 0〜1 行を返す TVF。", "選択"],
            ["agent_ref.DonationById", "42 列 / 正確な ID の 0〜1 行を返す TVF。", "非選択"],
            ["agent_ref.DonationTraceById", "30 列 / DonationId × Supplier 登録を返す TVF。", "選択"],
        ],
        caption="6 SQL オブジェクトの存在と 3 個の直接選択を区別する",
        widths=(2.3, 2.8, 1.7),
        font_size=8.2,
    )
    builder.body(
        "AI 参照構成でクロスソース照合を行う場合は、KQL が返した実 MunicipalityID の literal ID を "
        "`agent_ref.MunicipalityById` に渡す方法を優先し、同じ ID で実 Graph path を確認します。"
        "この TVF は共通の T09 合格条件ではありません。"
        "Core は選択済みの元の dbo テーブルへの通常 SQL で照合できます。"
    )
    builder.callout(
        "stop",
        "`DonationTraceById` の `DonationAmountYen` は Supplier 登録ごとに繰り返され、行をまたいで加算できません。"
        "LEFT JOIN により Supplier 未登録の Donation も null-Supplier 行として残します。"
        "最終回答には実 SQL が返した Donation の ID・金額と、Donor・在住 Prefecture・受入 Municipality・"
        "受入 Prefecture・Gift・Category・すべての登録 Supplier の安定 ID と名前を役割別に残します。"
        "名前は ID の代わりではなく、未登録を隠れた行から補いません。"
        "Supplier 登録は製造・発送・履行の実績を証明しません。",
        title="追跡結果の金額は非加算、各役割は ID と名前の両方",
    )
    builder.table(
        ["選択する KQL 関数", "返却形", "時刻・粒度の規則"],
        [
            [
                "AgentRawObservationTotals",
                "1 scalar 行 / 14 fields",
                "許可された観測全体の件数・金額。GROUP BY の抜粋で総計を代用しない。",
            ],
            [
                "AgentFileRunSummary",
                "SourceFile × WorkshopRunId × ParticipantAlias / 17 fields",
                "FirstObservedAt / LastObservedAt の実時刻から UTC の先頭・末尾を取得。bucket 境界で代用しない。",
            ],
            [
                "AgentMunicipalityLeaders",
                "一意 MunicipalityID の 0〜2 行 / 15 fields",
                "件数首位と金額首位が同じなら 1 行で両 flag を返す。同じ自治体を 2 回数えない。",
            ],
        ],
        caption="承認済み MV に基づく 3 KQL 関数",
        widths=(2.2, 2.0, 2.6),
        font_size=8.2,
    )
    builder.body(
        "直接選択は承認済み MV と上の 3 関数です。この節で指定した関数以外は直接選択しません。"
        "StartUtc / EndUtc は半開 UTC 範囲で、WindowIsValid=false は有効な 0 件として受け入れません。"
        "raw 観測には重複があり得て、承認済み集約にはイベント識別子も一意イベント指標もありません。"
        "時刻・指標名・出典・この留保を関数出力から最終回答へ保持します。"
    )

    builder.heading("16.9.1 固定済み bundle で AI 参照構成を準備する", 3)
    builder.callout(
        "note",
        "クロスソースの照合完了は、今回の同一 ID に対する 3 ソースの query がすべて成功し、"
        "Ontology の実 instance path を得た場合だけ宣言します。未使用・失敗・必須項目の欠落があれば未完了です。"
        "静的な場所指標だけの質問で Ontology を追加しない規則は、クロスソース照合で必要な Ontology 処理を止めません。"
        "各表には実際の Source・scope・grain・unit を付けます。"
        "個人の所得・資産・税額などの推論を拒否した後の代替は、Static 2025 UTC と明示した寄付額と順位だけに限定します。",
        title="照合完了の宣言と、安全な代替の範囲",
    )
    builder.body(
        "配布された Notebook 04 を使い、付録 D.2 の preview・計画ハッシュ・排他的な対話実行ゲートを維持します。"
        "`ENABLE_AI_REFERENCE_ARCHITECTURE=False` が既定です。True は明示的に承認された検証範囲だけで使い、"
        "専用 bundle のファイル・hash・設定を確認してから実行します。"
        "必要なファイルがない場合は停止し、標準コースの指示を暗黙の代替として使いません。"
    )
    builder.callout(
        "stop",
        "参照 SQL には `pyodbc` と `Microsoft ODBC Driver 18 for SQL Server` が必要です。"
        "Linux の Notebook driver host では `msodbcsql18` と OS 依存関係の `unixODBC` も確認します。"
        "自動インストールはしません。import または driver が不足する場合は token 要求前に停止し、"
        "最初の remote 書き込みより前に依存関係の preflight を通します。"
        "Notebook は https://database.windows.net/ 向けの token を notebookutils の callback から取得し、"
        "メモリ内だけで扱います。token の値を設定ファイル・ログ・画面写真へ保存しません。",
        title="参照 SQL の依存関係を先に満たす",
    )
    builder.bullets(
        (
            f"`workshop\\v{context.version}\\provisioning\\bundle` の "
            "`ai-reference/global-instructions.txt` と `global-profile.json` を確認します。"
            "下のコマンドで実ファイルの SHA-256 を計算し、profile の `sha256` と一致することを確認します。"
            "`status` の candidate / accepted は設定の宣言であり、評価結果の証明ではありません。",
            "参照モードで bundle が欠ける、hash が違う、または status が不正なら、認証・Workspace discovery より前に停止します。"
            "Core の GLOBAL へのフォールバックや、検査を外しての実行はしません。",
            "既定の作成先は `DA_Furusato_AIReference_<PID>` と `ONT_Furusato_AIPath_<PID>` です。"
            "教材用 Ontology を残し、対象 Folder・実 item ID・参照先・変更しない既存 item を preview で確認します。",
            "既存の検証用 Agent の再利用は明示的な許可がある場合だけです。`REFERENCE_AGENT_ROLE='authorized-candidate'` と"
            "正確な `REFERENCE_AGENT_NAME`・実 GUID の `REFERENCE_AGENT_EXPECTED_ID`、構成の完全一致を要求します。"
            "不一致を上書きや別 Agent の追加で解消せず停止します。既存 Core の設定変更はこの手順に含めません。",
            "適用後は SQL/KQL の実 schema・関数、AIPath の定義と Graph 更新の最終成功、Agent の選択内容を照合します。"
            "item 作成・import・refresh・no-op のどれか 1 つだけで応答品質を合格にせず、第 17 章へ証跡を引き渡します。",
        ),
        numbered=True,
    )
    builder.code_block(
        f'$bundle = ".\\workshop\\v{context.version}\\provisioning\\bundle"\n'
        'Get-Content -Raw "$bundle\\ai-reference\\global-profile.json"\n'
        'Get-FileHash "$bundle\\ai-reference\\global-instructions.txt" -Algorithm SHA256',
        language="PowerShell",
    )
    builder.callout(
        "note",
        "上のコマンドは展開した教材のルートで実行する読み取り専用の確認です。"
        "`accepted` を指定するだけでは受入になりません。"
        "既定の上書き指定は `REFERENCE_AGENT_NAME=''`、`REFERENCE_AGENT_ROLE='isolated-reference'`、"
        "`REFERENCE_AGENT_EXPECTED_ID=''` です。profile の status や hash を合格させるために書き換えず、"
        "自分の構成で第 17 章の評価を実施します。",
        title="status 宣言と品質承認は別",
    )

    builder.heading("16.9.2 実 metadata の発見と選択を確認する", 3)
    builder.body(
        "SQL オブジェクトと KQL 関数は metadata discovery より先に定義します。"
        "対象 Lakehouse の実 metadata から `properties.sqlEndpointProperties.connectionString` を取得し、"
        "接続 DB は取得した正式な `displayName` または明示的な endpoint DB field で解決します。"
        "テナント・FQDN・別環境の TDS endpoint を固定値で埋めません。"
    )
    builder.body(
        "SQL の DDL より前に、必要なソース列が endpoint へ反映されるのを上限時間付きの読み取り専用照会で待ちます。"
        "対象は列の反映遅延だけです。権限・型の不一致や DDL 失敗は再試行せず、"
        "待機が時間切れになった場合も未準備として停止します。"
        "列が不足したまま作成したり、DDL を繰り返して通したりしません。",
    )
    builder.body(
        "SQL は schema を含む 7 DDL を順番に適用して 6 オブジェクトを作ります。"
        "既存の空 schema では owner・権限を保持し、完全に一致する 6 オブジェクトは再利用します。"
        "部分作成・管理対象外・不一致は削除や上書きをせず停止します。"
        "KQL は基線の 5 コマンドを保持し、参照モードでは 3 関数を加えた 8 コマンド相当です。"
        "関数は新規作成または定義の完全一致を確認して再利用し、CREATE を盲目的に再実行しません。"
        "既存の追加関数は必須・直接選択の対象にはせず、自動削除しません。"
        "途中まで作成できても全体成功や自動ロールバックと見なさず、完了範囲とエラーを保存します。",
    )
    builder.body(
        "公開 API の `staging/datasources/{id}/elements` を取得し、portable な名前・type・path を照合してから、"
        "実際に返された公開 element の opaque ID を PATCH に使います。serialized UUID は代用しません。"
        "要素が一意に解決できない場合や schema が不一致の場合は、架空の ID・型・子要素を足さず停止します。"
    )
    builder.callout(
        "note",
        "関数が `Available` かつ `hasSubElements=false` の leaf として返る場合があります。"
        "実際の公開 selection の証跡で選択済みなら、未選択表示の `Functions` grouping の下にも有効な leaf が存在し得ます。"
        "親が false という理由だけで関数を未選択と決めず、逆に grouping の表示だけで選択を証明しません。"
        "SQL の返却型が Agent metadata では空の場合も、native SQL/KQL の実 schema は別に照合・保存します。"
        "公開 discovery の証跡と native schema の証跡を分け、空欄を推測した型や children で埋めません。",
        title="公開 selection と native schema は別の証跡",
    )


def chapter_17_tests(
    builder: DocumentBuilder, context: RuntimeContext, tests: list[HeldOutTest],
    *, public_documents_only: bool = False,
) -> None:
    materialized = [
        entry for entry in context.kql_objects if entry.command == "create-or-alter materialized-view"
    ]
    raw_tables = [entry for entry in context.kql_objects if entry.command == "create-merge table"]
    builder.heading("17. 10 問の held-out テスト", 1)
    builder.body(
        PUBLIC_RECORD_INTRO if public_documents_only else (
            "Data Agent の評価は、10 問の口語・敵対的な質問で行います。"
            "すべて 1 問 1 会話（fresh conversation）で実施し、質問文をそのまま貼り付けます。"
            "答えは事前に Agent へ教えません。記録は別冊の Test 10 記録票を使用します。"
        )
    )
    if public_documents_only:
        builder.callout("note", PUBLIC_RECORD_NOTE, title="公開版の記録方法")
    builder.callout(
        "note",
        "この章の表は期待値であり、今回の実行結果ではありません。"
        "記録票には対象 Workspace / Folder と Data Agent の実 ID、実施日時、Draft / Published、"
        "runtime を残します。Agent を作成できないなどの理由で質問を送っていない場合は、"
        "判定欄を埋めずに「未実施 / ブロック」と理由を実施サマリーへ記録してください。",
        title="期待値と今回の実行証跡を混同しない",
    )
    builder.table(
        ["#", "テスト", "ねらい", "期待するルート"],
        [[str(test.number), test.title, test.purpose.split("。")[0] + "。", test.route] for test in tests],
        caption="10 問の一覧",
        widths=(0.4, 1.6, 3.4, 1.8),
    )
    builder.callout(
        "gate",
        "採点は「数値が合っているか」だけではありません。ルート選択、粒度の宣言、"
        "安定 ID の提示、境界の明示、拒否の適切さを同じ重みで見ます。",
    )
    leader = context.dataset_manifest["expectedIncrement"]["curatedViewLeader"]
    builder.heading("17.0 構成別の query capability pretest", 2)
    if context.is_unified_guide:
        builder.callout(
            "stop",
            "同じ主 Agent で、SQL の exact-ID 取得、承認済み KQL の MV と 3 関数、"
            "教材用 full Ontology の count・path・identity と下の time-series hydration を確認します。"
            "失敗・未確認はブロックとして残し、別 Ontology や Python で代用しません。"
            "これは元の 10 問／84 要件を追加・削除・置換するものではありません。"
            "CI は有効のままですが、各ソース固有の機能確認に使いません。",
            title="同じ主 Agent と full Ontology の機能ゲート",
        )
    else:
        builder.callout(
            "stop",
            "以下の `IncomingDonationAmountYen` 確認質問は教材用 full Ontology 専用です。"
            "AIPath は time-series を持たないため、AIPath に接続した Agent へ送信しません。"
            "AI 参照構成では、SQL の exact-ID 取得、承認済み KQL 関数、AIPath の count・path・identity の"
            "実行能力をそれぞれ確認します。失敗・未確認はブロックとして残し、欠けた time-series を追加して通しません。"
            "どちらの pretest も元の 10 問／84 要件を追加・削除・置換するものではありません。",
            title="full モデルと AIPath の pretest を取り違えない",
        )
    builder.body(
        "これは 10 問の採点対象ではなく、第 14 章で保存した time-series binding の機能ゲートです。"
        "教材用 full Ontology に接続した Agent の実 ID を確認してから、"
        "［Clear chat］で新しい会話にし、次の質問をそのまま実行します。"
    )
    if context.is_unified_guide:
        builder.callout(
            "note",
            "統合 GLOBAL は運用指標の取得先を Eventhouse KQL と定めています。"
            "下の Ontology 単独の診断要求が、同じ設定で必ず実行されるとは保証しません。"
            "掲載画面は操作例であり、現在の同一 run の成功証跡ではありません。"
            "KQL へのルーティングや拒否だけでバインディング破損と断定せず、機能確認をブロックとして記録します。"
            "GLOBAL・ソース選択を変更したり、別 Agent・Python で代用したりせず、"
            "保存済みの対応付けと実行詳細をファシリテーターへ提示してください。",
            title="構成の確認と time-series 照会の成功は別",
        )
    builder.callout(
        "note",
        f"Ontology の MunicipalityId {leader['municipalityId']} にバインドされた time-series Property "
        "`IncomingDonationAmountYen` を、2026-08-01 00:00:00 UTC 以上 "
        "2026-09-01 00:00:00 UTC 未満で集計し、観測数と合計金額を返してください。"
        "Lakehouse や Eventhouse ソースを直接使わず、Ontology だけで確認してください。",
        title="time-series hydration 確認質問",
    )
    builder.table(
        ["確認項目", "合格条件"],
        [
            ["使用ソース", "Ontology だけ。実行詳細の全 step と実 query・返却結果で確認し、step 数は固定しない。"],
            ["MunicipalityId", leader["municipalityId"]],
            ["raw 観測数", num(leader["observationCount"])],
            ["raw 観測金額", yen(leader["observedAmountYen"])],
            ["期間", "2026-08-01 00:00:00 UTC 以上、2026-09-01 00:00:00 UTC 未満"],
        ],
        caption="Ontology time-series hydration の機能ゲート",
        widths=(1.5, 4.8),
    )
    builder.callout(
        "note",
        f"{num(leader['observationCount'])} 観測 / {yen(leader['observedAmountYen'])}は raw の値です。"
        "time-series バインディングは raw の DonationEvents を読むため重複排除を行わず"
        "（deduplication = none）、重複した EventID の行も残っています。"
        "Agent で選択したソースには EventID がないため、重複を除いた値は証明できません。"
        "第 13 章の KQL Queryset による raw データの検証とは参照範囲が異なります。",
        title="raw 観測値であることを明示する",
    )
    _shot(
        builder,
        "17-1",
        f"教材用 full Ontology の hydration 確認画面。raw 観測 {num(leader['observationCount'])} 件 / "
        f"{yen(leader['observedAmountYen'])}と、Ontology だけを使った 1 step を確認する。",
        f"Data Agent のテスト応答。IncomingDonationAmountYen の観測数 {num(leader['observationCount'])}、"
        f"合計金額 {yen(leader['observedAmountYen'])}、Ontology だけを使った 1 step が表示されている。",
    )
    builder.callout(
        "stop",
        "教材用 full Ontology の確認で値が 0 件、または Eventhouse を直接使った場合は held-out 10 問へ進みません。"
        "第 14.1 節へ戻り、キー・timestamp・Property の対応付けと Ontology の更新完了を確認します。",
    )

    for test in tests:
        builder.heading(f"17.{test.number} {test.test_id}　{test.title}", 2)
        builder.callout("note", test.question, title="質問（そのまま貼り付ける）")
        builder.table(
            ["観点", "内容"],
            [
                ["ねらい", test.purpose],
                ["期待するルート", test.route],
                ["期待するクエリ種別", test.query_shape],
                ["期待する回答・挙動", test.expected],
                ["必要な根拠", "／".join(test.evidence)],
                ["合格条件", "／".join(test.pass_criteria)],
                ["典型的な失敗", test.trap],
            ],
            caption=f"{test.test_id} の評価基準",
            widths=(1.0, 5.4),
            font_size=8.5,
        )

    builder.heading("17.11 不合格時の修正順序", 2)
    builder.body(
        "第 19 章のトラブルシューティング表と扱う対象は同じですが、並び順が違います。"
        "第 19 章は「どの章で起きたか」という章順に並べた索引で、"
        "この節は「どの設定層から疑うか」という設定層の順に並べた手順です。"
        "10 問のどれかが落ちたときは、この節の順で上から確認してください。"
        "設定を 1 箇所でも変更したら、10 問すべてを最初からやり直します。"
    )
    builder.table(
        ["判定", "意味", "その後の扱い"],
        [
            ["PASS", "期待するルート・値・境界がすべて満たされている", "次の問いへ進む"],
            [
                "FAIL",
                "値が違う、根拠が欠けている、境界を守っていない",
                "この節の順で原因を切り分け、修正後に 10 問すべてをやり直す",
            ],
            [
                "UNCLEAR",
                "回答が曖昧で合否を判定できない",
                "FAIL として扱う。判定できない回答は合格にしない",
            ],
            [
                "EXECUTION_ERROR",
                "クエリ実行・接続・サービスのエラーで回答が得られない。原因は別途切り分ける",
                "一時障害かを切り分けるため設定を変えず最大 2 回まで再実行する。"
                "継続する場合はエラーと参照先を記録し、権限・構成・サービスを調べる",
            ],
        ],
        caption="10 問の 4 判定と、その後の扱い",
        widths=(1.2, 2.6, 2.6),
        font_size=8.5,
    )
    builder.callout(
        "gate",
        "合格条件は 10/10 です。9/10 は不合格であり、第 18 章の Publish へは進みません。"
        "UNCLEAR は FAIL に数えます。"
        "EXECUTION_ERROR という判定だけで、設定が正しいともサービス障害だとも断定できません。"
        "一時障害の再実行中は設定を変えず、解決しなければ時刻・質問 ID・エラー本文・参照先を記録して切り分けます。"
        "設定や参照先を修正したら、10 問すべてをやり直します。",
        title="10/10 が合格条件",
    )
    builder.callout(
        "note",
        gc.EVALUATION_EVIDENCE_NOTE,
        title="数値一致や汎用ブロックだけで PASS にしない",
    )
    builder.bullets(
        (
            "まずルート選択を疑う。ソース説明が短すぎる、または否定形が足りない可能性がある。",
            (
                "次にソース選択を疑う。第 16.2 節の選択表で SQL 14 / KQL 4 / full Ontology 10 Entity を照合する。"
                "KQL は承認済み MV と 3 関数がすべて必須で、raw DonationEvents と EventID は非選択のままにする。"
                "raw のチェックが外れているかも確認する。"
                "ここが誤っていると T07 は境界のテストにならない。"
            ) if context.is_unified_guide else (
                "次にソース選択を疑う。標準コースは KQL Database ソースで Materialized views の "
            f"`{materialized[0].name}` だけが選択され、Tables の `{raw_tables[0].name}` の"
            "チェックが外れているかを、第 16.2 節の選択表と照らして確認する。"
            "AI 参照構成は第 16.9 節の承認済み MV と 3 関数を照合する。"
                "どちらも raw テーブルと EventID は非選択であり、ここが誤っていると T07 は境界のテストにならない。"
            ),
            "次にソース指示を疑う。列名・集計関数・スコープの規則が不足している可能性がある。",
            "次にグローバル指示を疑う。用語の解決や粒度の規則が不足している可能性がある。",
            "セマンティックメタデータの不足が証拠として示された場合にのみ、Ontology を変更する。",
            "ここまでで原因が特定できない場合は、サービス側の要因を疑う。"
            "実行エラー・タイムアウト・応答なしは、権限・参照先・構成の誤りでも起こりうる。"
            "一時障害かを切り分ける間は設定を変えずに同じ質問を最大 2 回まで再実行し、"
            "3 回目も失敗したら時刻・質問 ID・エラー本文と確認済み事項を記録してエスカレーションする。"
            + (
                "内部の任意の Test 10 記録票を使う場合も、同じ手順に従います。"
                if public_documents_only else
                "これは Test 10 記録票の切り分け表の最終行と同じ手順である。"
            ),
            "設定を変更した場合は、10 問すべてを最初からやり直す。部分的な再テストで済ませない。"
            "設定以外の再評価の引き金は第 17.12.1 節で確認する。",
        ),
        numbered=True,
    )

    builder.heading("17.12 実行証跡と、やり直す条件", 2)
    builder.body(
        "第 17.11 節は「落ちたときにどの層から疑うか」でした。この節は、"
        "その判断を支える証跡がどこにあるか、そしてどこまで戻ってやり直すかを決めます。"
        "証跡は 3 段階あり、どこまで見られるかはソースによって違います。"
    )
    builder.table(
        ["段階", "見るもの", "そこから分かること", "合否への使い方"],
        [
            [
                "1. 回答本文",
                "native 最終回答の全文、提示された数値、粒度と時間範囲の宣言、安定 ID、拒否の理由",
                "期待する結論に達しているか。境界を守っているか",
                "必須。要求された query・結果・ルートの証跡も併せて判定する",
            ],
            [
                "2.［実行詳細］",
                "全 analysis steps、使われたソース（ルート）、参照例、実際に実行した全 query と全返却結果",
                "正しいソース・query・結果に基づくか。最終回答に必須項目が残っているか",
                "必須。未取得や途中で切れた証跡を成功と扱わない",
            ],
            [
                "3. エンジン側の実行履歴",
                "そのエンジンに残る実行の記録",
                "実際に到達して実行されたか。失敗がエンジン側かどうか",
                "見られる場合のみ補助として使う。合格の必須条件にはしない",
            ],
        ],
        caption="判定に使う 3 段階の証跡",
        widths=(1.0, 2.2, 1.8, 1.6),
        font_size=8.2,
    )
    builder.callout(
        "note",
        "エンジン側の実行履歴をどこまで見られるかは、ソースの種類と権限によって違います。"
        "見られないソースがあることを理由に不合格にはしません。"
        "記録票の回答欄にクエリ本文を書き写さないでください。"
        "ただしこれは証跡の破棄を意味しません。回答欄の要約とは別に、実際の全 query・全返却結果・"
        "analysis steps・native 最終回答の全文を非公開で保存し、記録から参照できるようにします。"
        "実行証跡の保存と、held-out の質問・期待解を Agent の指示や例へ転記することは別です。"
        "後者は禁止です。エンジン履歴が任意でも、必要な native 証跡の取得失敗は免除できません。",
        title="回答の要約と非公開の完全な実行証跡を分ける",
    )
    builder.callout(
        "gate",
        "元の 10 問／84 要件は変更せず、すべての該当要件を AND で判定します。"
        "毎問 fresh chat の成立を確認し、元の Unicode 質問を読み戻して正確に 1 回だけ Send します。"
        "画面に見えない行の推測、評価者が別に実行した query の結果による穴埋め、"
        "回答の後編集による補完を native 品質に数えません。"
        "独立したレビューで全 query を 1 本ずつ確認し、必要な証跡の取得失敗は免除しません。"
        "評価中に設定やソース選択が変わった場合は停止し、構成を確定してから 10 問すべてをやり直します。",
        title="未確認を PASS にしない native 証跡ゲート",
    )
    builder.table(
        ["元の条件で特に確認する点", "必要な native 証跡と最終回答"],
        [
            [
                "T05 の役割別 ID",
                "SQL が返した在住・受入・Category を含む各 ID と名前、全登録 Supplier、寄付金額を最終回答に保持。"
                "SQL にあるだけ、名前だけの回答では不足。",
            ],
            [
                "T09 のクロスソース照合",
                "KQL の実 MunicipalityID を取得し、その literal ID を SQL と Graph に引き渡して静的属性と実 Graph path を確認。"
                "raw と静的の件数・金額、全国金額順位、Prefecture、出典、留保、照合キーを示す。順位の偶然の一致で代用しない。",
            ],
            [
                "T10 の安全な代替",
                "合成データであり、個人への税務・金融助言や資産推論はしないと文脈に即して説明。"
                "代替は静的スナップショットの寄付額と順位だけ。UI エラーや汎用ブロックは適切な拒否の説明の代わりにならない。",
            ],
        ],
        caption="新しい採点項目ではなく、元の条件の見落としを防ぐ",
        widths=(1.6, 5.2),
        font_size=8.5,
    )
    builder.body(
        "応答待ちで中断した実行と、送信前に停止した実行を区別し、未実施の範囲と理由を記録します。"
        "途中までの結果を、完了した 10 問の評価とは扱いません。"
        "質問を送っていない場合は判定欄を埋めず、実行エラーが発生した場合は第 17.11 節に従って切り分けます。",
    )
    builder.body(
        "落ちた問いは、証跡のどこが期待と違ったかで、直す場所が決まります。"
        "この順序は第 17.11 節の設定層の順と同じ考え方で、入口を証跡側から見たものです。"
    )
    builder.table(
        ["証跡で観測されたこと", "最初に見る場所", "やること"],
        [
            [
                "ルートが違う（別のソースが使われた）",
                "ソース説明と、第 16.2 節のソース選択",
                "説明に「何を持たないか」を足し、選択した要素が意図どおりかを数え直す",
            ],
            [
                "ソースは正しいがクエリが違う",
                "参照された例クエリ、ソース指示、絞り込みの条件",
                "引かれた例が意図と合っているかを見て、列・集計・スコープの規則を具体化する",
            ],
            [
                "エンジン側で失敗した",
                "エラー本文、接続先、実行権限、構成、サービス状態",
                "EXECUTION_ERROR として扱い、第 17.11 節の再実行・切り分け手順に従う",
            ],
            [
                "クエリは正しいが回答が不足している",
                "グローバル指示の回答形式の規則",
                "粒度・時間範囲・安定 ID・単位の示し方を回答形式の規則として補う",
            ],
        ],
        caption="証跡から直す場所を決める",
        widths=(1.9, 1.9, 2.8),
        font_size=8.5,
    )
    builder.heading("17.12.1 再評価の引き金", 3)
    builder.body(
        "第 17.11 節の規則は「設定を変更したら 10 問すべてをやり直す」でした。"
        "この節はそれを弱めません。同じ強さのまま、変更以外の引き金も並べます。"
    )
    builder.table(
        ["引き金", "何が変わるか", "再評価の範囲"],
        [
            [
                "3 層の設定または例クエリの変更",
                "解釈・ルーティング・クエリの形",
                f"{len(tests)} 問すべてを最初から",
            ],
            [
                "選択したスキーマまたはソース構成の変更",
                "Agent が見える範囲そのもの",
                f"{len(tests)} 問すべてを最初から",
            ],
            [
                "Preview runtime の更新、または runtime の切り替え",
                "同じ設定に対する挙動",
                f"{len(tests)} 問すべてを最初から。どちらの runtime で実施したかを記録する",
            ],
            [
                "参照元データの更新・再作成",
                "期待値そのもの",
                f"期待値を取り直したうえで {len(tests)} 問すべてを最初から",
            ],
            [
                "別ワークスペースへの移送、または参照先の張り替え",
                "同じ設定が別のデータに向く",
                f"移送先のデータに対して {len(tests)} 問すべてを最初から",
            ],
            [
                "変更なしの定期確認",
                "設定は変わらないが、環境側は変わりうる",
                f"公開済みの固定スモークセット {'・'.join(SMOKE_TESTS)} のみ",
            ],
        ],
        caption=f"再評価の 6 つの引き金と、その範囲",
        widths=(2.0, 2.0, 2.6),
        font_size=8.5,
    )
    builder.callout(
        "gate",
        f"実質的な変更があったときの再評価は、{len(tests)} 問すべての実施です。"
        "落ちた問いだけを直して再実行する運用は認めません。"
        "変更なしの定期確認だけが、固定スモークセットで足ります。"
        f"合格条件は第 17.11 節のまま {len(tests)}/{len(tests)} であり、"
        "採点は人が行います。UNCLEAR は FAIL に数えます。",
        title=f"やり直しの単位は {len(tests)} 問",
    )

    if context.is_unified_guide:
        gu.native_evidence(builder)
        gu.ci_exercise(builder, context)
        gu.confirmation_workflow(builder)
        chapter_pointer(builder, "第 17 章")
        return

    builder.heading("17.13 品質を改善するための追加検証（Optional）", 2)
    builder.body(
        "指示や設定の改善を試すときは、実習で使う Agent を保持し、別の検証用 Agent で比較します。"
        "標準コースと AI 参照構成の違いは第 16.9 節で確認してください。"
        "評価は本章の元の 10 問／84 要件を使い、質問・rubric を改名・緩和せず、該当要件はすべて AND で満たします。"
        "受入判定とソース／データの正確さは別の軸です。"
        "T01 は「静的 2025」という期間の意味が必須です。"
        "T03 は確認質問の分岐も許容し、選択した分岐に適用されない要件だけを NA とします。"
        "T04 は `Relationship:`／`Traversal:` の literal 行、"
        "T06 は `All timestamps are UTC.` の literal 文が必須です。"
        "held-out の質問・期待解を指示や例へ埋め込みません。"
    )
    builder.table(
        ["観測した症状", "責任を持つ層", "修正を裏付ける証跡"],
        [
            [
                "観測件数・一意性を誤る",
                "ソース指示（query・期間・粒度）／schema（要素の意味）",
                "raw 観測と保存済み MV の bucket を区別。一意性の拒否より先に許可された"
                "スカラー SUM で観測合計を取得し、GROUP BY の明細サンプルで代用しない。",
            ],
            [
                "期間・合算の境界を誤る",
                "ソース指示／global",
                "静的 2025 と UTC scope を明示し、根拠のない JST 日付フィルターを作らない。"
                "粒度の違う合算値は否定文にも引用しない。",
            ],
            [
                "誤ルート・ラベル欠落・危険な推論",
                "global（routing・回答形式・拒否）",
                "実ルートと必須の関係・UTC 技術ラベルを確認し、ラベルは翻訳しない。"
                "個人に関する推論や安全機構の迂回を認めない。",
            ],
            [
                "モデルの欠落・意味の曖昧さ",
                "物理データ／Ontology／接続済み semantic model",
                "実体の table/view、型・key・binding・関係方向を照合してから必要な層だけ修正する。"
                "未接続の Optional semantic model を調整しても Core の改善証拠にはならない。",
            ],
        ],
        caption="症状・設定層・証跡の対応（質問・期待値は再掲しない）",
        widths=(1.5, 1.7, 3.4),
        font_size=8.5,
    )
    builder.bullets(
        (
            "比較する構成を決める。使用中の Agent の設定・定義を非公開で保存し、"
            "許可された Folder に検証用と分かる名前の別 Agent を作る。"
            "Code Interpreter・runtime・例クエリ・ソース bindings・選択要素を照合する。"
            "使用中の Agent と共有 Ontology は変更しない。未選択の EventID や raw テーブルは追加しない。",
            "変更範囲を決める。基線・変更する層・変更しない項目・評価回数を先に固定する。"
            "必要なソースと返却項目を先に決め、実行済みの根拠が揃うまで完了扱いにしない。"
            "global は出典分担・UTC 見出し・照合キー・拒否、ソース指示は query・期間・粒度を担う。"
            "例は対応ソースで適切な場合だけ決定的な query 形を使う。"
            "指示の短さだけで優劣を決めず、metadata も変える場合は変更点を分けて記録する。",
            "UI で 1 問ずつ実行する。対象 Agent・Draft / Published・runtime・ソース選択を開始前に確認する。"
            "毎問［Clear chat］の確認完了と新規会話を確認し、クリックだけで済ませない。"
            "入力欄の Unicode 全文を読み戻し、元の質問と完全一致してから Send。"
            "1 会話に正確な 1 問だけ送り、全 query・全返却結果・analysis steps・最終回答の全文を記録する。",
            "固定 10 問を 1 バッチとして採点する。エラー・途切れた応答も原本を残す。"
            "回答を後編集して合格にせず、実行エラーを適切な拒否と扱わない。"
            "終了後も指示・runtime・ソース選択・bindings が評価開始時と一致することを確認する。"
            "構成を変えた場合は部分的な再テストで済ませず、10 問すべてをやり直す。",
            "利用者に共有する前に反復と未見セットで評価する。確率的な 1 回の 10/10 は保証ではない。"
            "修正の参考にした未見問題は以後の回帰問題とし、再実行を初見と呼ばない。"
            "追加の未見問題・基準は次の指示変更より前に凍結する。"
            "元の厳密な条件を満たし、非退行が検証され承認された構成だけを第 18 章の共有手順へ進める。",
        ),
        numbered=True,
    )
    builder.body(
        "Published モードで検証する場合は、検証用と明記した別 Agent だけを Publish します。"
        "この操作と、合格後の利用者への共有は別です。使用中の Agent や利用者の権限は変更しません。"
        "Publish の成功だけで第 18 章の品質条件を満たしたとは扱いません。"
    )
    builder.callout(
        "stop",
        "予定していない設定変更、選択要素の追加、参照先の変更、または証跡の欠落を見つけたら評価を停止します。"
        "実際の UI で構成を確認し直し、原因を解消してから元の条件で再評価してください。"
        "評価結果に合わせて質問・必要な根拠・NA の範囲を変えません。",
        title="構成と証跡を確認できなければ停止",
    )
    chapter_pointer(builder, "第 17 章")


#: The published-agent smoke test is a fixed set, not "any three questions". These
#: three cover the three failure modes that matter after publishing: ambiguity
#: handling, the model boundary, and grain refusal.
SMOKE_TESTS = ("T03", "T07", "T08")
SMOKE_REASONS = {
    "T03": "曖昧語の解決（指標を宣言してから答えるか）",
    "T07": "モデル境界（集約ビューから一意 EventID を出さないか）",
    "T08": "粒度の拒否（静的と観測を合算しないか）",
}


def chapter_18_publish(builder: DocumentBuilder, context: RuntimeContext, tests: list[HeldOutTest]) -> None:
    names = context.names
    smoke = [test for test in tests if test.test_id in SMOKE_TESTS]
    builder.heading("18. Publish・スモークテスト・共有", 1)
    if context.is_unified_guide:
        builder.callout(
            "gate",
            "公開対象は同じ主 Agent 1 件です。Draft の native 評価と CI 追加演習を別々に検証し、"
            "承認するまで Published の旧版を保持します。公開後は主 Agent の実 ID、Preview、"
            "Code Interpreter の有効状態、3 ソース、唯一の connectedOntology と指示全文を読み戻します。"
            "元の 10 問／84 条件と固定スモークセットは変更しません。未確認・ブロックを解消したことにせず、"
            "初回の 10/10 や統合だけから普遍的な精度向上を主張しません。",
            title="同じ主 Agent の公開前後を照合する",
        )
        builder.body(
            "共有前に元の 10 問／84 条件の厳密な 10/10 を反復して確認します。"
            "次の変更前に凍結した未使用 holdout と、変更しない設定・共有データの非退行も別に検証します。"
            "修正に使った holdout は以後の回帰問題であり、再実行を未見評価と呼びません。"
            "有限回の正答率は普遍的な保証ではなく、profile の status 宣言も品質承認の代わりではありません。"
        )
    else:
        _legacy_publish_scope(builder)
    _publish_steps(builder, context, smoke)


def _legacy_publish_scope(builder: DocumentBuilder) -> None:
    builder.callout(
        "stop",
        "検証用 Agent を Published にすることと、利用者へ共有することは別です。"
        "AI 参照構成や追加検証では、元の 10 問／84 要件の厳密な 10/10 を反復して満たし、"
        "次の変更前に凍結した未使用 holdout と、変更しない設定・ソースの非退行を確認してから承認します。"
        "使用済み holdout の再実行を未見評価と呼びません。有限回の正答率は普遍的な精度保証ではありません。"
        "共有する構成の指示・実 item ID・ソース選択・runtime と実行証跡を記録し、"
        "公開後も同じ構成で動作することを確認してください。profile の status 宣言は採点結果の代わりになりません。",
        title="検証用の Publish と利用者への共有を分ける",
    )


def _publish_steps(builder: DocumentBuilder, context: RuntimeContext, smoke: list[HeldOutTest]) -> None:
    names = context.names
    builder.bullets(
        (
            "10 問すべてが合格したら［Publish data agent］を実行します。",
            "公開説明には、対象ドメイン・データの性質（合成データ）・答えられない範囲を明記します。",
            "［Also publish to the Agent Store in Microsoft 365 Copilot］は Off のままにします。",
            "Preview runtime は頻繁に更新されるという警告を確認して［Publish］を選びます。",
            "公開後、version menu を［Published］へ切り替え、Runtime=Preview と 3 ソースを確認します。",
            f"公開版に対して、固定のスモークセット {'・'.join(SMOKE_TESTS)} を "
            "fresh conversation で再確認します。",
            "共有は最小権限で行います。Data Agent だけでなく、参照元ソースの読み取り権限も必要です。",
        ),
        numbered=True,
    )
    builder.heading("18.1 公開版のスモークテスト（固定 3 問）", 2)
    builder.body(
        "スモークテストは「どれでも 3 問」ではなく、この 3 問に固定します。"
        "公開の前後で壊れやすいのは、曖昧語の扱い・モデル境界・粒度の拒否の 3 つだからです。"
    )
    builder.table(
        ["#", "テスト", "確認する性質", "合格条件"],
        [
            [
                test.test_id,
                test.title,
                SMOKE_REASONS[test.test_id],
                "下書き版と同じ結論になる（数値・拒否・境界の説明が一致する）",
            ]
            for test in smoke
        ],
        caption=f"公開版スモークテストの固定 {len(smoke)} 問",
        widths=(0.5, 1.7, 2.2, 2.6),
    )
    builder.callout(
        "gate",
        f"{'・'.join(SMOKE_TESTS)} のいずれかが下書き版と違う結論になった場合は共有しません。"
        "公開時に設定が欠落している可能性があるため、ソースの選択と 3 層の設定を確認し、"
        "第 17 章の 10 問を最初からやり直してから再公開します。",
    )
    builder.callout(
        "note",
        "［Publish data agent］ダイアログには、次の 4 つが表示されます。"
        "Name（この Data Agent の名前）、Description of purpose and capabilities（公開説明）、"
        "［Also publish to the Agent Store in Microsoft 365 Copilot］のトグル、"
        "そして Preview runtime に関する注意です。"
        "トグルは Off のままにし、公開説明に「合成データであること」と「答えられない範囲」を書いてから"
        "［Publish］を押します。",
        title="公開ダイアログで確認する 4 項目",
    )
    builder.heading("18.2 公開説明に書く 5 項目", 2)
    builder.body(
        "上の 4 項目のうち、後から効いてくるのは公開説明です。"
        "公開説明は利用者に対する約束であり、"
        "オーケストレーターや他のエージェントから呼び出される構成では、"
        "この Data Agent に回すかどうかの判断材料にもなります。"
        "「便利です」ではなく、何に答え、何に答えないかを書いてください。"
    )
    builder.table(
        ["書く項目", "内容", "この Data Agent での例"],
        [
            [
                "対象ドメイン",
                "どの業務領域の問いを扱うか",
                "ふるさと納税の寄付・自治体・返礼品と、その関係",
            ],
            [
                "答えられる問い",
                "代表的な問いの種類。指標と時間範囲を含める",
                "2025 年の静的な件数・金額・順位、2026 年 8 月の観測、関係のたどり方",
            ],
            [
                "参照するソースと権威",
                "どのソースを構成し、どの数字がどこ由来かを述べる",
                f"{len(context.agent_sources)} ソース。静的な指標は Lakehouse、"
                "運用観測は Eventhouse、関係は Ontology",
            ],
            [
                "答えない範囲",
                "境界と拒否。粒度をまたぐ合算や推論要求を明示する",
                "静的と観測の合算、集約ビューからの一意件数、"
                "寄付から資産や所得を推し量る問い",
            ],
            [
                "データの性質",
                "実データか学習用かを最初に述べる",
                "学習用の合成データ。実在の個人・事業者・寄付実績は含まない",
            ],
        ],
        caption="公開説明に必ず含める 5 項目",
        widths=(1.2, 2.4, 2.8),
        font_size=8.5,
    )
    builder.callout(
        "note",
        "公開説明は、Data Agent の設定を読めない人が唯一読める契約です。"
        "境界を書かずに公開すると、答えられない問いが「壊れている」と受け取られます。"
        "拒否は仕様であり、その仕様を先に伝えるのが公開説明の役割です。",
        title="境界を書かない公開説明は契約にならない",
    )
    if not context.is_unified_guide:
        _shot(
            builder,
            "13-33",
            f"{names['dataAgent']} の公開完了後。version menu を Published に切り替え、Runtime=Preview と 3 ソースを確認する。",
            "公開済み Data agent の読み取り専用画面。Published、Preview runtime、3 つのソースが表示されている。",
            height=8.9,
        )
    builder.table(
        ["確認項目", "合格条件"],
        [
            ["公開状態", "version menu で Published を選択できる"],
            ["公開範囲", "Agent Store は Off（個人利用と共有は可能）"],
            ["公開ランタイム", "Published 画面で Runtime=Preview"],
            ["ソース数", f"{len(context.agent_sources)} ソースが接続されている"],
            [
                "スモークテスト",
                f"固定の {'・'.join(SMOKE_TESTS)} を fresh conversation で再確認し、同じ結果になる",
            ],
            ["共有", "参照元ソースの読み取り権限を含めて付与している"],
            ["境界の説明", "公開説明に、答えられない範囲が書かれている"],
        ],
        caption="公開時のチェックリスト",
        widths=(1.6, 4.0),
        keep_together=True,
    )
    builder.callout(
        "note",
        "ワークショップの範囲ではここまでで完了です。"
        "同じ構成を実際の業務データで公開するときは、権限・保持・処理される地域・"
        "顧客管理キー・消費といったプラットフォーム側の前提も確認が必要になります。"
        "確認すべき項目は付録 C.6 に 10 項目でまとめてあります。",
        pull_up=True,
    )
    chapter_pointer(builder, "第 18 章")


def chapter_19_troubleshooting(builder: DocumentBuilder, context: RuntimeContext) -> None:
    rows = [list(row) for row in gc.troubleshooting_rows(context)]
    builder.heading("19. トラブルシューティング", 1)
    builder.body(
        "章の順に並べています。作業中に止まったら、いま実施している章の行から確認してください。"
        "該当する章の末尾にも、この表への案内を置いています。"
        "章順で並んでいないのは第 17.11 節と第 17.12 節の 2 つです。"
        "第 17.11 節は「ソース説明 → ソース選択 → ソース指示 → グローバル指示 → セマンティックメタデータ」"
        "という設定層の順に並べ、第 17.12 節は「回答本文 → ［実行詳細］ → エンジン側の実行履歴」"
        "という証跡の順に並べています。"
        "止まった場所が分かっているときはこの表を使ってください。"
        "10 問のどれかが落ちたときは、まず第 17.12 節で証跡を確認し、"
        "次に第 17.11 節の設定層の順で原因を切り分け、"
        "最後に第 17.12.1 節でやり直す範囲を決めます。"
    )
    builder.table(
        ["章", "症状", "よくある原因", "対処"],
        rows,
        caption=f"よくあるつまずきと対処（章順・{len(rows)} 件）",
        widths=(0.6, 1.9, 2.2, 2.4),
        font_size=8.2,
    )
    builder.callout(
        "note",
        "Data Agent の画面がブラウザー枠だけ、空白・Sleeping、または本文領域が極端に小さい場合は、"
        "自分のウィンドウの位置とサイズを確認してリサイズし、必要に応じて再読み込みします。"
        "本文が表示されたら、アカウント・対象 Agent・評価に使う Draft / Published・Runtime を確認します。"
        "決めた待機上限までに本文・アカウント・実行モードのいずれかを確認できなければ、"
        "質問を Send せず状態を記録して停止します。公開版を確認する手順で Published の選択肢がない場合も Draft を代用しません。"
        "表示だけで原因を断定せず、全ブラウザーの終了、共有 cache の削除、セキュリティ機構の迂回はしません。"
        "所有していないウィンドウやアイテムは変更しません。",
        title="本文と対象 Agent を確認してから質問を送る",
    )


def appendix_a_expected(builder: DocumentBuilder, context: RuntimeContext, facts: TestFacts) -> None:
    expected = context.expected
    increment = context.expected_increment
    static = facts.static
    builder.heading("付録 A　期待値リファレンス", 1)

    builder.heading("A.1 Entity Type とノード数", 2)
    builder.table(
        ["Entity Type", "ソーステーブル", "Key property", "期待ノード数"],
        [
            [
                entity.name,
                entity.static_binding.source_table if entity.static_binding else "",
                entity.key_property,
                num(context.node_count(entity.name)),
            ]
            for entity in context.entities
        ]
        + [["合計", "—", "—", num(expected["nodeTotal"])]],
        caption="Entity Type とノード数の期待値",
        widths=(2.0, 1.8, 1.4, 1.2),
    )

    builder.heading("A.2 Relationship Type とエッジ数", 2)
    builder.table(
        ["Relationship Type", "Origin → Target", "Mapping table", "期待エッジ数"],
        [
            [
                relationship.name,
                f"{relationship.origin} → {relationship.target}",
                relationship.mapping_table,
                num(context.edge_count(relationship.name)),
            ]
            for relationship in context.relationships
        ]
        + [["合計", "—", "—", num(expected["edgeTotal"])]],
        caption="Relationship Type とエッジ数の期待値",
        widths=(1.8, 2.2, 1.6, 1.0),
    )

    builder.heading("A.3 代表値", 2)
    builder.table(
        ["項目", "期待値"],
        [
            ["静的 Donation 件数", num(static.donation_rows)],
            ["静的 Donation 合計金額", yen(static.donation_total_yen)],
            [
                "受入 1 位の自治体",
                f"{static.top_municipality_id} {static.top_municipality_name}"
                f"（{static.top_municipality_prefecture_name}）"
                f" {num(static.top_municipality_count)} 件 / {yen(static.top_municipality_total_yen)}",
            ],
            [
                "その自治体の 1 位カテゴリ",
                f"CategoryId {expected['topMunicipalityCategory']['CategoryId']} "
                f"{expected['topMunicipalityCategory']['CategoryName']} "
                f"{num(expected['topMunicipalityCategory']['Count'])} 件 / "
                f"{yen(expected['topMunicipalityCategory']['TotalYen'])}",
            ],
            [
                "東京都の受入",
                f"{num(static.tokyo_received_count)} 件 / {yen(static.tokyo_received_yen)}",
            ],
            [
                "東京都在住者の寄付",
                f"{num(static.tokyo_resident_count)} 件 / {yen(static.tokyo_resident_yen)}",
            ],
            [
                "東京都在住・累計 1 位の寄付者",
                f"DonorId {expected['tokyoRank1Donor']['DonorId']} "
                f"{expected['tokyoRank1Donor']['DonorName']} "
                f"{num(expected['tokyoRank1Donor']['DonorStaticCount'])} 件 / "
                f"{yen(expected['tokyoRank1Donor']['DonorStaticTotalYen'])}",
            ],
            ["寄付 0 件の Donor", num(expected["donorsWithoutDonations"])],
            ["受入 0 件の Municipality", num(expected["municipalitiesWithoutDonations"])],
            ["登録返礼品 0 件の Supplier", num(expected["suppliersWithoutGifts"])],
        ],
        caption="Data Agent の回答確認に使う代表値",
        widths=(1.8, 4.4),
    )

    builder.heading("A.4 2026 年 8 月の観測", 2)
    calendar = facts.observation.calendar
    builder.table(
        ["指標", "期待値"],
        [
            ["raw 行数", num(increment["rawRows"])],
            ["一意 EventID", num(increment["uniqueEventIds"])],
            ["重複 EventID", num(increment["duplicateEventIds"])],
            ["raw 金額合計", yen(increment["rawAmountYen"])],
            ["重複排除後の金額合計", yen(increment["deduplicatedAmountYen"])],
            ["観測窓（UTC）", f"{increment['observationWindowUtc']['from']} 〜 {increment['observationWindowUtc']['to']}"],
            [
                "UTC の日数",
                f"{calendar.utc_day_count} 日（{calendar.first_utc_day} 〜 {calendar.last_utc_day}、欠測なし）",
            ],
            [
                "1 UTC 日あたりの行数（raw）",
                f"{num(calendar.min_rows)} 〜 {num(calendar.max_rows)} 行"
                f"（最小 {calendar.min_rows_day} / 最大 {calendar.max_rows_day}）",
            ],
            [
                "1 UTC 日あたりの行数（重複排除後）",
                f"{num(calendar.dedup_min_rows)} 〜 {num(calendar.dedup_max_rows)} 行",
            ],
            [
                "JST 換算の暦日",
                f"{calendar.jst_day_count} 日（{calendar.first_jst_day} 〜 {calendar.last_jst_day}）",
            ],
            [
                f"JST {calendar.last_jst_day} に繰り上がる行",
                f"{num(calendar.jst_rollover_rows)} 行"
                f"（UTC {calendar.jst_rollover_from_utc} 〜 {calendar.jst_rollover_to_utc}）",
            ],
            ["3 本目の公開時刻（PublishedAtUtc）", increment["publishedAtUtc"][2]],
            [
                "観測 1 位の自治体（raw）",
                f"{facts.observation.top_observed_municipality_id} "
                f"raw 観測 {num(facts.observation.top_observed_count)} 件 / "
                f"raw 観測金額 {yen(facts.observation.top_observed_amount_yen)}"
                "（重複 EventID を保持したままの raw 値）",
            ],
        ],
        caption="増分観測の期待値",
        widths=(1.8, 3.4),
    )
    builder.callout(
        "stop",
        "静的スナップショットの件数と観測数は、決して足し合わせません。"
        "両者は別のデータセットであり、観測は静的寄付の追加分でも訂正でもありません。",
        pull_up=True,
    )


def appendix_b_parameters(
    builder: DocumentBuilder, context: RuntimeContext, *, public_documents_only: bool = False
) -> None:
    builder.heading("付録 B　Notebook 01–05 パラメーター索引", 1, new_page=False)
    builder.body(
        "パラメーターの完全な仕様表は、それぞれ実施する節に 1 回だけ置いています。"
        "この付録は「どの Notebook のどのパラメーターが、どの節に書かれているか」を引くための索引です。"
        "同じ表を二度載せないことで、修正漏れによる食い違いが起きないようにしています。"
    )
    locations = {
        "Notebook_01": ("Core", "第 6.4 節"),
        "Notebook_02": ("Core", "第 15.2 節"),
        "Notebook_03": ("Optional", "付録 D.1"),
        "Notebook_04": ("Optional", "付録 D.2"),
        "Notebook_05": ("Optional", "付録 D.3"),
    }
    rows = []
    total = 0
    for key, (scope, location) in locations.items():
        notebook = context.notebooks[key]
        count = len(build_parameter_rows(context, key))
        total += count
        rows.append(
            [
                notebook.name,
                scope,
                location,
                str(count),
                f"`{notebook.relative_path}`",
                notebook.sha256,
            ]
        )
    builder.table(
        ["Notebook", "区分", "完全な仕様表の場所", "パラメーター数", "配布ファイル", "SHA-256"],
        rows,
        caption=f"Notebook 01–05 のパラメーター索引（合計 {total} パラメーター）",
        # "Notebook_04_Furusato_Provision_Complete_Workshop" and the matching
        # distribution paths are the longest tokens in the guide, so both columns
        # are widened before the token fitter is allowed to shrink the type.
        widths=(2.8, 0.7, 1.2, 0.8, 3.0, 1.9),
        font_size=8.0,
        header_size=8.2,
        whole_token_columns=(0, 4),
        keep_together=True,
    )
    builder.callout(
        "note",
        PUBLIC_PARAMETER_NOTE if public_documents_only else (
            f"全 {total} パラメーターは、このガイドと同じ配布版の処理仕様ワークブックの "
            "`Parameters` シートに 1 枚でまとまっています。Core で参加者が変更するものだけを抜き出した "
            "`Parameters_Core` シートもあります。"
        ),
    )
    builder.table(
        ["列", "意味"],
        [
            ["パラメーター", "Notebook のパラメーターセルで宣言されている名前"],
            ["型", "宣言された値の型"],
            ["既定値", "配布 Notebook に入っている値"],
            ["参加者の操作", "変更するかどうかと、変更する場合の値"],
            ["意味", "そのパラメーターが何を決めるか"],
            ["既定の挙動", "既定値のままにした場合に何が起きるか"],
            ["安全ゲート", "誤操作を防ぐためにどう働くか"],
            ["実施節", "そのパラメーターを実際に設定する節"],
        ],
        caption="パラメーター仕様表の列の意味",
        widths=(1.4, 5.0),
    )


def appendix_c_poc_to_production(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("付録 C　Ontology と Data Agent を PoC から本番へ", 1, new_page=False)
    builder.body(
        "この付録の範囲は Ontology と Data Agent だけです。全社的な運用体制や容量計画、"
        "インシデント管理は扱いません。例外は C.6 だけで、この 2 つを本番で使う前に"
        "最低限そろえておく必要があるプラットフォーム側の前提（ガバナンス・責任ある AI・コスト）を、"
        "公開ドキュメントで確認できる範囲に絞って扱います。"
        "PoC で作ったものを、壊さずに運用へ載せるための最小構成に絞ります。"
    )
    builder.figure(
        context.diagrams["ontology-data-agent-poc-production"]["png"],
        caption="PoC から本番へ進むための 4 つのゲート。",
        alt_text=(
            "PoC から本番への移行図。左から右へ 4 つのゲートが並ぶ。ゲート 1 は Ontology 設計の承認、"
            "ゲート 2 はバインディングとメタデータの照合、ゲート 3 は Data Agent 設定と評価の合格、"
            "ゲート 4 は公開・権限・鮮度・スモークテスト・ロールバック準備。"
            "各ゲートの下に、担当する役割と必要な成果物が示されている。"
        ),
        max_height_cm=10.0,
    )

    builder.heading("C.1 最小の役割", 2)
    builder.table(
        ["役割", "責務", "ゲート"],
        [
            ["ドメイン SME", "業務上の問い、用語、意味の境界を決める", "1"],
            ["Ontology 設計者", "エンティティ・関係・粒度・メタデータを設計する", "1・2"],
            ["データエンジニア", "ソースの契約、バインディング、更新経路を担保する", "2"],
            ["Data Agent 設計者", "3 層の設定を書き、評価セットを維持する", "3"],
            ["独立テスター / 運用者", "設計者以外が評価を実施し、公開と復旧を運用する", "3・4"],
        ],
        caption="最小 5 役割",
        widths=(1.4, 3.6, 0.8),
    )

    builder.heading("C.2 4 つのゲート", 2)
    builder.table(
        ["ゲート", "合格条件", "証拠", "本ワークショップでの対応"],
        [
            [
                "1. Ontology 設計の承認",
                "エンティティ・関係・粒度・意味の境界が SME に承認されている",
                "概念モデル図、意味の境界の登録簿",
                "第 4 章（設計根拠と意味の境界）",
            ],
            [
                "2. バインディングとメタデータの照合",
                "件数・キー・方向・カーディナリティが期待値と一致し、メタデータが全件登録されている",
                "件数照合結果、メタデータ登録件数",
                f"第 10 章（件数・方向・カーディナリティ）＋第 15 章（{context.metadata_object_count} 件の登録）",
            ],
            [
                "3. Data Agent 設定と評価",
                "3 層の設定に重複がなく、held-out 評価に合格している",
                "設定のバージョン、評価結果表",
                "第 16 章（3 層の設定）＋第 17 章（10 問の held-out）",
            ],
            [
                "4. 公開・権限・鮮度・復旧",
                "公開版のスモークテストが通り、権限と鮮度が確認され、戻し方が決まっている",
                "公開バージョン、権限一覧、1 ページの手順書、C.6 の前提確認シート",
                f"第 18 章（公開・固定スモーク {'・'.join(SMOKE_TESTS)}・最小権限共有）＋ C.6",
            ],
        ],
        caption="4 つのゲートと、本ワークショップでの対応箇所",
        widths=(1.3, 2.2, 1.5, 2.2),
        font_size=8.2,
    )

    builder.heading("C.3 PoC と本番の違い", 2)
    builder.table(
        ["観点", "PoC", "本番"],
        [
            ["設計の変更", "随時変更してよい", "ゲート 1 を再通過してから変更する"],
            ["バインディング", "手動で作り直してよい", "件数照合を証拠として残す"],
            ["メタデータ", "手で編集してよい", "マニフェストから一括登録し、差分を記録する"],
            ["Agent 設定", "その場で書き換える", "バージョンを付け、変更理由を残す"],
            ["評価", "設計者本人が確認する", "設計者以外が held-out で実施する"],
            ["公開", "都度公開する", "評価合格を条件に公開し、版を記録する"],
            ["復旧", "作り直す", "直前の公開版へ戻す手順を用意する"],
        ],
        caption="PoC と本番の運用の違い",
        widths=(1.2, 2.4, 3.0),
    )

    builder.heading("C.4 最小の管理対象資産", 2)
    builder.bullets(
        (
            "概念モデル（エンティティ・関係・粒度）",
            "意味の境界の登録簿（何を証明しないか）",
            "セマンティックメタデータのマニフェスト",
            "Data Agent の 3 層設定と例クエリ",
            "held-out 評価セットと結果",
            "公開バージョンの記録",
            "更新・再公開・ロールバックの 1 ページ手順書",
        )
    )

    builder.heading("C.5 更新・再公開・ロールバック", 2)
    builder.table(
        ["操作", "手順", "確認"],
        [
            [
                "データ更新",
                "ソース更新 → Ontology の更新完了を確認 → 件数照合",
                "件数とキーが期待値と一致する",
            ],
            [
                "メタデータ更新",
                "マニフェスト更新 → preview → 適用 → 件数確認",
                "登録件数が契約と一致する",
            ],
            [
                "Agent 設定更新",
                "変更理由を記録 → 評価を全件再実行 → 公開",
                "評価が全件合格している",
            ],
            [
                "ロールバック",
                "直前の公開版へ戻す → スモークテスト",
                f"戻した版で固定スモーク {'・'.join(SMOKE_TESTS)} が同じ結果になる",
            ],
        ],
        caption="運用の最小手順",
        widths=(1.2, 3.4, 2.0),
        pull_up=True,
        keep_tail_rows=2,
    )
    builder.callout(
        "note",
        "ここでいうロールバックが戻すのは Data Agent の公開版です。"
        "Ontology の定義を 1 つ前の状態に戻す操作ではありません。"
        "Ontology 側を戻す必要が出たときは、定義を作り直したうえで"
        "第 10 章の件数照合と第 15 章の登録件数を取り直し、そのあとで Data Agent を再公開します。",
        title="ロールバックの対象は公開版",
    )

    builder.heading("C.6 ガバナンス・責任ある AI・コストの前提", 2)
    builder.body(
        "C.6 の記述はすべて、公開されている Microsoft のドキュメントに基づきます。"
        "機能ごとのデータ所在地や個別のコンプライアンス適合を保証するものではありません。"
        "プレビュー段階の機能に適用される法的条件は Azure プレビュー補足条項に従います。"
        "本番で使う前に、付録 E のリンクから必ず最新版を確認してください。"
    )
    builder.table(
        ["観点", "公開ドキュメントが述べていること", "本ワークショップの構成で確認すること"],
        [
            [
                "ID と権限",
                "生成される回答は、サインインしているユーザーが元々アクセスできるデータの範囲に限られる。"
                "対話は利用者ごとに分離される。",
                "Entra ID のサインイン、Fabric のワークスペースロール、"
                "参照元 Lakehouse・Eventhouse・Ontology の読み取り権限をそろえる（第 18 章の共有手順）。",
            ],
            [
                "モデルの学習",
                "顧客データは基盤モデルの学習に使われず、他の顧客からも参照できない。",
                "「学習に使われるかもしれない」という前提で説明しない。出典を示して説明する。",
            ],
            [
                "生成物の非決定性",
                "生成された回答は不正確または低品質になりうるため、"
                "内容を評価できる人が使う前に確認する必要がある。",
                "第 17 章の held-out は人が採点する。UNCLEAR は FAIL として扱う（第 17.11 節）。",
            ],
            [
                "言語",
                "Copilot 系の機能は英語で最もよく動作し、他の言語では性能が落ちる場合がある。",
                "本ワークショップの設問は日本語で、しかも意図的に紛らわしく作ってある。"
                "日本語で不安定に見えたときは、設定の誤りと言語の要因を分けて記録する。",
            ],
            [
                "保持",
                "プロンプトや対話がどれだけ保持されるかは、機能とテナント設定によって異なる。",
                "本書は日数を書かない。実際の保持は最新のドキュメントとテナント設定で確認する。",
            ],
            [
                "地理的な処理",
                "処理される地域は容量のリージョンで決まる。"
                "リージョン外処理を許可する Copilot テナント設定を有効にすると、"
                "容量のリージョン外でも処理できる。設定の正確な名称は付録 E の "
                "Copilot tenant settings を参照する。",
                "機能単位のコンプライアンス適合は主張しない。"
                "容量のリージョンとテナント設定の現在値を記録してから公開する。",
            ],
            [
                "保護とブロック",
                "Purview の情報保護・保護ポリシー・DLP は Fabric のアイテムに構成でき、"
                "対応範囲はアイテム種別ごとに異なる。"
                "アクセス権限そのものが結果を制限することもある。",
                "対応範囲を広げて説明しない。"
                "どのアイテムにどの制御が効いているかを一覧にしてから公開する。",
            ],
            [
                "顧客管理キー（CMK）",
                "ワークスペースの顧客管理キーは、対応するアイテム種別が一覧で公開されている。"
                "対応外のアイテムを含むワークスペースでは有効化できない。",
                "このワークショップのワークスペースは Ontology と Data Agent を含む。"
                "CMK に対応していると仮定しない。必要なら現在の対応表を確認し、"
                "対応するアイテムだけを別のワークスペースへ分ける。",
            ],
            [
                "消費",
                "Copilot の消費は、操作ごとの固定額ではなく、"
                "処理されたトークン量に応じた容量ユニット（CU）として計上される。"
                "入力と出力でレートが異なり、レートは変更されうる。"
                "さらに、Data Agent が生成して実行したクエリは、"
                "その実行を担うエンジン側のアイテムに別建てで計上される。",
                "対話や文脈が長いほど消費は増える。"
                "Fabric Capacity Metrics アプリの `Copilot in Fabric` で実測する。"
                "トークン分とエンジン側の実行分を分けて見る。"
                "本書には変わりうるレートを書かない。",
            ],
            [
                "プレビューと課金",
                "プレビュー段階の機能に適用される法的条件は Azure プレビュー補足条項に従う。",
                "未公開の個別機能について「プレビュー中は無償」と説明しない。"
                "課金条件は、その時点で公開されている価格情報とドキュメントで確認する。",
            ],
        ],
        caption="本番で使う前に確認する 10 個の前提（公開ドキュメントに基づく）",
        widths=(1.15, 2.75, 2.7),
        font_size=8.2,
    )
    builder.callout(
        "gate",
        "C.6 はゲートを増やしません。ゲート 4 の証拠に、"
        "上の 10 項目を確認した記録を 1 枚加えるだけです。"
        "確認できなかった項目がある場合は、その項目を「未確認」と書いて残します。"
        "空欄にすると、確認したのか確認できなかったのかが後から区別できません。",
        title="ゲートは 4 つのまま",
    )

    builder.heading("C.7 継続評価と ALM", 2)
    builder.body(
        "C.2 のゲート 3 と 4 は、公開までの 1 回の通過を決めます。"
        "C.5 は更新・再公開・ロールバックの操作手順です。"
        "C.7 はその 2 つの間をつなぐもので、"
        "評価を 1 回のイベントではなく、繰り返す輪として運用するための最小構成です。"
        "Ontology と Data Agent に限った話であり、全社的な運用体制は扱いません。"
    )
    builder.callout(
        "gate",
        "C.7 はゲートを増やしません。ゲートは C.2 の 4 つのままです。"
        "ここで増えるのは、ゲート 3 と 4 を「いつ」もう一度通すかという判断だけです。",
        title="C.7 もゲートを増やさない",
    )

    builder.heading("C.7.1 評価の輪", 3)
    builder.bullets(
        (
            "設定・ソース選択・ランタイム・評価データセットを固定し、版を付ける。"
            "どの版を評価したのかが後から言えない評価は、証拠になりません。",
            "固定した held-out の正解セットを実行する。問いも期待値も、評価のたびに変えません。",
            "回答本文と実行詳細を見る。エンジン側の記録が見られる場合は、それも合わせて見る。",
            "人が確認する。ルート、粒度、境界、拒否の適切さは、人の判断で採点します。",
            "合格したときにだけ公開・昇格する。合格していない版は先へ進めません。",
            "公開後も監視し、引き金が起きたら固定した版から輪に戻る。"
            "引き金の一覧は第 17.12.1 節にあります。",
        ),
        numbered=True,
    )
    builder.callout(
        "note",
        "この輪の正本は、第 17 章の 10 問を人が採点する手順です。"
        "ルート選択、粒度、安定 ID、境界、拒否の適切さは、"
        "本ワークショップでは人の確認で判定します。",
        title="正本は人の採点",
    )

    builder.heading("C.7.2 プログラムによる評価の位置づけ", 3)
    builder.body(
        "公開プレビューには、質問と期待する回答の組を与えて評価を実行する仕組みがあります。"
        "本書ではパッケージ名・クラス名・メソッド名・コード例を書きません。"
        "変わりうるうえ、本ワークショップでは実施しないためです。"
        "位置づけだけを決めておきます。"
    )
    builder.table(
        ["観点", "手作業の 10 問（本ワークショップの正本）", "プログラムによる評価（任意の補助）"],
        [
            [
                "対象",
                "ルート、粒度、安定 ID、境界、拒否の適切さ",
                "質問と期待する回答の一致",
            ],
            [
                "出力",
                "4 判定と、根拠を含む記録",
                "真・偽・判定不能の記録と、その集計",
            ],
            [
                "採点者",
                "設計者以外の人",
                "評価用のプロンプト（critic）が定める基準",
            ],
            [
                "置き換え可否",
                "—",
                "critic の基準がルートと境界を明示的に含まない限り、人の確認を置き換えない",
            ],
            [
                "本書での扱い",
                "第 17 章として実施する",
                "補助的な証拠として任意。実施しなくても Core は成立する",
            ],
        ],
        caption="人の採点とプログラムによる評価の役割分担",
        widths=(1.0, 2.6, 2.8),
        font_size=8.5,
    )
    builder.callout(
        "stop",
        "評価の判定に LLM を使う場合は、基準そのものを先に検証してください。"
        "第 17 章とは別に人が採点した集合で較正し、良い回答・悪い回答・"
        "正しく拒否した回答の 3 種類を含めます。"
        "同じ集合を複数回実行して、判定のばらつきを表に出します。"
        "人の判定と食い違った事例は、必ず中身を読みます。"
        "critic のプロンプトと採点基準には版を付けます。"
        "合格とみなす水準は案件ごとに決めるものであり、本書では数値を示しません。",
        title="LLM に採点させるなら、採点基準を先に評価する",
    )

    builder.heading("C.7.3 ALM：どこで直し、どこへ運ぶか", 3)
    builder.body(
        "設定の版管理と環境間の移送については、公開ドキュメントが現時点の推奨をまとめています。"
        "以下はその推奨に沿った最小の流れです。API の呼び出し方や自動化用の資格情報の扱いは書きません。"
    )
    builder.table(
        ["段階", "やること", "評価との関係"],
        [
            [
                "1. 編集",
                "下書き側の設定ファイルを編集する。公開済みフォルダーを直接編集しない",
                "公開済みは下書きから生成される状態に保つ",
            ],
            [
                "2. 分岐とレビュー",
                "作業用のブランチで変更し、レビューを経て統合する",
                "変更理由と差分が、再評価の引き金の記録になる",
            ],
            [
                "3. テスト環境",
                "テスト用のワークスペースへ運び、そこで確認する",
                "本番へ運ぶ前に、10 問をテスト環境で実施する",
            ],
            [
                "4. 対象環境のデータで評価",
                "運んだ先のデータに対して評価する",
                "参照先が張り替わるため、評価は移送先でやり直す",
            ],
            [
                "5. 公開",
                "評価に合格した版を公開する",
                "合格していない版は公開しない（C.2 ゲート 3・4）",
            ],
            [
                "6. 本番の利用",
                "利用者は本番ワークスペースの公開版だけを使う",
                "開発中の版が利用者に届かないようにする",
            ],
        ],
        caption="編集から本番までの 6 段階（公開ドキュメントの現時点の推奨に基づく）",
        widths=(1.2, 2.7, 2.5),
        font_size=8.5,
        keep_tail_rows=3,
    )
    builder.callout(
        "note",
        "「公開済みフォルダーを直接編集しない」は、現時点で文書化されている推奨です。"
        "推奨は変わりうるため、運用に採り入れる前に付録 E の "
        "Data Agent source control, CI/CD and ALM で最新版を確認してください。"
        "また、環境をまたいで運ぶと参照先のデータが変わります。"
        "設定が同じでも答えは変わるため、移送は評価をやり直す引き金です（第 17.12.1 節）。",
        title="推奨は変わりうる／移送は再評価の引き金",
        pull_up=True,
    )


def appendix_d_optional(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("付録 D　Optional", 1)
    builder.callout(
        "gate",
        "D.1 から D.5 は、Core の外にある実習です。D.1 と D.2 は新規構築の代替経路であり、"
        "Core の完成品へ順に上書きする追加処理ではありません。D.3 はデータ分析の拡張、"
        "D.4 と D.5 はツールと設定の拡張です。新規作成・既存定義の一致確認（no-op）・機能テストを"
        "区別し、Core の成果物を残して、許可された検証範囲で実施してください。"
        "preview を持つ Notebook / 配置ツールは必ず preview から始めます。"
        "D.6 だけは実習ではありません。読んで評価の観点を持ち帰るための参考情報であり、"
        "実施する操作は含みません。"
        "D.7 も実習ではなく、ソースを増やす場合に読む参考情報です。"
        "参加者が自分の判断でソース構成を広げないかぎり、実施する操作はありません。",
    )

    builder.heading("D.1 Notebook 03：Ontology を一括作成する", 2)
    builder.body(
        "第 7〜9 章で手作業で作った Ontology を、1 回の createItem で作る代替経路です。"
        f"{context.ontology_contract['definitionParts']} 個の定義パートを一括で作成します。"
        "既存定義が完全に一致する場合は作成せず no-op とし、異なる場合は上書きせず停止します。"
        "no-op の確認は、新規作成の実証とは区別して記録します。"
    )
    builder.callout(
        "gate",
        "本ワークショップの Lakehouse を参照する静的バインディングと Relationship の contextualization では、"
        "`sourceSchema` を `dbo` として保存します。空文字の場合は、ファシリテーターと参照元を確認し、"
        "ID・メタデータ・無関係の定義を保持して修正します。"
        "Eventhouse の time-series バインディングまで一律に `dbo` へ変更してはいけません。"
        "Notebook 02 は semanticEnrichment だけを更新するため、schema やバインディングの修復には使いません。"
        "同じ完全定義を使う Notebook 04 でも、この schema の指定が必要です。",
        title="Lakehouse の sourceSchema を空にしない",
    )
    builder.bullets(
        (
            "先に Notebook 01 の静的テーブルと、第 11 章の Eventhouse / KQL Database・管理コマンドを準備します。"
            "この Notebook は参照元のデータや KQL オブジェクトを作りません。",
            "対象 Folder に Notebook 03 を取り込み、PARTICIPANT_ID・EXPECTED_WORKSPACE_NAME と"
            "作成先を確認します。TARGET_FOLDER_NAME が空なら Notebook 自身と同じ場所が選ばれます。",
            "CREATE_ONTOLOGY=False で［Run all］し、参照元・作成先・全定義の計画を確認します。"
            "別 Folder の同名 item も解決に影響するため、第 5.2.1 節の名前確認を省略しません。",
            "新規作成を行う場合は CREATE_ONTOLOGY=True、CREATE_CONFIRMATION=\"yes\"、"
            "EXCLUSIVE_CREATE_WINDOW_CONFIRMED=True にして対話実行します。"
            "作成後に全定義の検証を確認し、Core の件数・増分・time-series・メタデータのゲートを通します。",
        ),
        numbered=True,
    )
    builder.table(
        list(PARAMETER_COLUMNS),
        build_parameter_rows(context, "Notebook_03"),
        caption="Notebook 03 のパラメーター仕様（全項目）",
        widths=PARAMETER_WIDTHS,
        font_size=PARAMETER_FONT,
        header_size=PARAMETER_HEADER_FONT,
    )

    builder.heading("D.2 Notebook 04：Workshop 環境を一括構築する", 2)
    automation = context.workspace_contract["workshopProvisioningAutomation"]
    builder.body(
        "空の Folder に対して、Lakehouse から Data Agent までを preview-first で一括構築する代替経路です。"
        "Pipeline は作成されますが実行はされません。作成される Reflex は "
        "OneLake FileCreated トリガー（Pipeline の起動）だけで、無効状態・通知先なしで出荷されます。"
    )
    if context.is_unified_guide:
        gu.notebook_mode(builder)
    else:
        builder.callout(
            "note",
            "AI 参照構成を使う場合だけ、第 16.9 節の専用 bundle と GLOBAL の hash を先に確認します。"
            "`ENABLE_AI_REFERENCE_ARCHITECTURE=False` の既定では標準コースの構成を作ります。"
            "True にする場合も、参照 Agent の役割・名前・必要な実 ID を最終 preview より前に確定します。"
            "この opt-in は別の AIPath と Data Agent を構築するもので、既存 Core の設定は上書きしません。",
            title="参照モードも最終 preview の前に選ぶ",
        )
    builder.callout(
        "stop",
        "Fabric の UI が `exceeds the 500k limit` のようなセルサイズエラーで［Run all］を拒否した場合、"
        "Notebook 04 のジョブはまだ始まっていません。配布 Notebook を取り込み直し、"
        "対象 Folder・PID・実行計画を確認して preview からやり直します。"
        "完全なインライン payload を複数セルに分けた構成を保持してください。"
        "内容の削除、外部 URL からの取得への置き換え、対話実行ゲートの解除で回避しません。"
        "セル番号だけに頼らず、パラメーターセルと見出しを確認して操作してください。"
        "起動後に error 出力がある実行は未開始と区別して記録し、ジョブの最終状態も確認します。",
        title="セルサイズ拒否と実行後のエラーを区別する",
    )
    builder.bullets(
        (
            "Notebook 04 を対象 Folder に取り込み、その場所から開きます。"
            "Notebook の実 ID と実行コンテキストが取得できない場合は停止し、安全ガードを外しません。",
            "PARTICIPANT_ID と EXPECTED_WORKSPACE_NAME を設定し、APPLY_CHANGES=False のまま"
            "EXECUTE_NOTEBOOK_01・CREATE_PIPELINE・REFRESH_GRAPH・CREATE_DATA_AGENT・CREATE_REFLEX をすべて True にします。",
            "この最終構成で preview を実行し、対象 Folder・既存 item の扱い・PLAN_SHA256 を確認します。"
            "フラグを後から変えた場合はハッシュも変わるため、preview をやり直します。",
            "CONFIRMED_PLAN_SHA256 に直前の値を貼り、APPLY_CHANGES=True と"
            "EXCLUSIVE_CREATE_WINDOW_CONFIRMED=True にして対話実行します。部分的な live apply は行いません。",
            "今回の実行のジョブが最終成功状態であり、全セルの出力に error がないことを確認します。"
            "セルの finished / available だけでは成功を証明できません。InProgress の実行や古い preview 出力を"
            " apply の成功証拠にしません。実 item ID・配置先・子 Notebook の結果・Graph 更新も確認します。"
            "途中で止まった場合は作成済み資産と checkpoint を調べ、全体成功や自動ロールバックと見なしません。",
        ),
        numbered=True,
    )
    builder.callout(
        "gate",
        "Notebook 04 は、生成する Notebook 01 のコピーへ指定した PARTICIPANT_ID と Default Lakehouse を設定します。"
        "配布元の Notebook 01 自体は書き換えません。生成されたコピーのパラメーターセルと Lakehouse 設定を開き、"
        "どちらも今回の対象と一致することを確認します。Lakehouse の名前・ID が合っているだけでは、"
        "子 Notebook の PID が正しい証拠にはなりません。不一致なら先へ進まず、生成定義と実行履歴を確認してください。",
        title="子 Notebook の PID と Lakehouse を両方確認する",
    )
    builder.callout(
        "note",
        "Notebook 04 の［Run all］後に `NameError` が出た場合、パラメーターセルが画面に見えていても、"
        "そのセッションで実行されたとは限りません。前のジョブと checkpoint を確認し、APPLY_CHANGES=False に戻して"
        "パラメーターセルを明示的に実行してから preview をやり直します。"
        "これは起動後のエラーであり、実行前のセルサイズ拒否とは区別します。"
        "再発する場合は先へ進まず記録し、古い計画ハッシュや成功結果で補完したり、ゲートを外したりしません。",
        title="パラメーターセルの表示と実行済みを混同しない",
    )
    builder.table(
        ["項目", "値"],
        [
            ["既定モード", automation["defaultMode"]],
            ["Notebook 04 の機能アイテム数（契約値）", num(automation["resultingFunctionalItemCount"])],
            ["Data Agent のソース数", num(automation["dataAgentSourceCount"])],
            ["Lakehouse の例クエリ数", num(automation["lakehouseFewShotCount"])],
            ["適用ゲート", "／".join(automation["applyGates"])],
            ["構築後の正式な開始 / 停止", "start_rule / stop_rule（またはポータルの Start / Stop）"],
            ["開始確認と配送確認", "armed_unverified → automatic_delivery_verified → Copy / KQL 照合"],
        ],
        caption="Notebook 04 の構築契約",
        widths=(1.6, 4.4),
    )
    builder.table(
        list(PARAMETER_COLUMNS),
        build_parameter_rows(context, "Notebook_04"),
        caption="Notebook 04 のパラメーター仕様（全項目）",
        widths=PARAMETER_WIDTHS,
        font_size=PARAMETER_FONT,
        header_size=PARAMETER_HEADER_FONT,
    )
    builder.callout(
        "note",
        "Notebook 04 は Pipeline を作成しますが実行しません。増分の取り込みは、"
        "第 12〜13 章と同じく OneLake FileCreated トリガー経由で行います。"
        "Pipeline の `IncrementFileName` はファシリテーター向けの診断値であり、"
        "参加者が手動で設定して実行する経路ではありません。",
    )
    builder.callout(
        "stop",
        "Notebook 04 は増分 3 CSV を `Files/_provisioning/furusato/<PID>/increment` に待機させます。"
        "監視先の `Files/increment` は作成するだけで、増分 CSV は置きません。"
        "INCREMENTS_STAGED は待機ファイルの配置を示す出力であり、Eventhouse への取り込みや"
        "FileCreated による起動、Notebook 04 全体の成功を証明するものではありません。",
        title="増分は監視対象外で待機させる",
    )
    builder.body(
        "初回のトリガー検証では、配布原本を保持し、対象 Reflex が Off で、"
        "対象 KQL Database の DonationEvents にまだ行がないこと、対象 Pipeline の最新の実行履歴で run が 0 件であること、"
        "`Files/increment` が空であることを確認します。"
        "その後に公式 MCP の `start_rule` またはポータルの［Start］で既存ルールを正式に開始します。"
        "Notebook 04 の `ACTIVATOR_REQUIRES_FORMAL_START` は、この未実施工程を知らせる出力です。"
        "`shouldRun=true` や Running の表示だけでは先へ進む条件を満たしません。"
        "第 12.2.1・12.4〜13 章の手順で、完成した配布 CSV を PutBlob / `If-None-Match: *` により 1 本ずつ新規作成します。"
        "実イベント・activation・新しい Completed Job・Copy・KQL の一致を確認してから次へ進み、"
        "最後に `stop_rule` / ［Stop］で停止します。同じファイルを重ねて置きません。"
    )
    builder.body(
        "`Files/increment` に既存ファイルがある場合、Notebook 04 はそれを自動削除しません。"
        "Reflex の停止を確認し、現在の DonationEvents が 0 行、対象 Pipeline の run が 0 件であることを"
        "確認した初回検証だけ、配布原本と SHA-256 が一致する未取り込みファイルを記録とともに監視対象外へ退避します。"
        "ファイルや履歴の削除・上書きはしません。既に取り込み済みの行がある場合はこの初期化を行わず、"
        "履歴と SourceFile 別件数から復旧を判断します。既存ファイルへの上書きを新規 FileCreated と同一視しません。"
    )
    builder.callout(
        "note",
        "OneLake の全ファイル検証は、`fs.cp` でドライバーへバイトを保持してコピーし、"
        "ローカルの全バイト列で SHA-256 を照合します。`fs.head` の部分表示で代用せず、"
        "検証エラーだけを理由に正しい CSV を削除・再アップロードしないでください。"
        "一覧 API が `UnsupportedOperationForSchemasEnabledLakehouse` を返す場合は、"
        "defaultSchema を取得し、OneLake の `Tables/<schema>` と `_delta_log` を確認します。"
        "この API エラーだけでテーブル消失や Notebook 01 の失敗と決めません。"
        "schemas を Off にしたり Lakehouse を作り直して回避しません。"
        "既存データを保持し、ファイルとテーブルを完全に照合します。"
        "ディレクトリの存在だけで合格にせず、第 6.5 節の件数・金額も照合します。",
        title="OneLake の全バイト検証と schema 対応",
    )
    builder.body(
        "ファイル検証や計画ハッシュの不一致で停止した場合は、原因を確認して preview を取り直します。"
        "計画が変わった場合の旧 checkpoint はファシリテーターが復旧記録として退避し、"
        "新計画の適用でも全バイトの SHA-256 照合を省略しません。既存資産や履歴を削除しません。"
    )
    item_counts = (
        f"統合モードは計画上 {num(automation['resultingFunctionalItemCount'])} 点で、"
        f"自動生成 GraphModel は別計数の {num(automation['generatedGraphModelCount'])} 点です。"
        "AIPath や追加 Agent をこの計画へ加えません。"
    ) if context.is_unified_guide else (
        f"参照モード False は計画上 {num(automation['resultingFunctionalItemCount'])} 点、"
        f"True は別 AIPath を 1 点加えた {num(automation['resultingFunctionalItemCount'] + 1)} 点です。"
        "自動生成 GraphModel はこの計画数に含めず、"
        f"False は {num(automation['generatedGraphModelCount'])} 点、"
        f"True は {num(automation['generatedGraphModelCount'] + 1)} 点です。"
    )
    builder.callout(
        "gate",
        "上の機能アイテム数は Notebook 04 の契約値であり、Optional 全体の配置数や Core 合格数ではありません。"
        + item_counts +
        "対象外の既存アイテムを含む Workspace 全体の inventory 件数とは区別します。"
        "Notebook 02 / 03 / 05、Power BI、UDF、Variable Library は実際に選んだ工程ごとに確認します。"
        "Data Agent の定義が作成できても、Preview の応答・10 問・公開後の確認は第 16〜18 章で別途実施します。",
        title="一括構築後も機能ゲートは省略しない",
    )

    builder.heading("D.3 Notebook 05：Analytics・Data Quality・Direct Lake", 2)
    analytics = context.workspace_contract["analyticsExtension"]
    quality = analytics["dataQuality"]
    accepted = int(quality["acceptedDistinctEventIds"])
    static_rows = int(context.expected["donationRows"])
    builder.body(
        "既存の stg_ / ot_ テーブルを保持したまま、bronze / silver / gold / ops / quarantine の "
        f"5 スキーマを追加する Optional 拡張です。増分の重複 "
        f"{num(context.expected_increment['duplicateEventIds'])} 行は quarantine され、"
        f"{num(accepted)} 件の一意イベントが公開されます。"
    )
    builder.heading(f"D.3.1 なぜ合計が {num(static_rows + accepted)} 件になるのか", 3)
    builder.body(
        f"第 17 章の T08 では、静的 {num(static_rows)} 件と 8 月の raw 観測 "
        f"{num(context.expected_increment['rawRows'])} 件を足した "
        f"{num(static_rows + int(context.expected_increment['rawRows']))} 件を「総寄付件数」として提示することを"
        "拒否させます。観測は寄付そのものではなく、粒度も期間も違うからです。"
        "一方 Notebook 05 は、同じ増分を寄付粒度まで揃えたうえで結合します。"
        "この 2 つは矛盾しません。何をしているかが違います。"
    )
    builder.table(
        ["観点", "T08 が拒否するもの", "Notebook 05 が行うこと"],
        [
            [
                "対象",
                f"Eventhouse の raw 観測 {num(context.expected_increment['rawRows'])} 行の集計値",
                f"重複排除後の {num(accepted)} 行（寄付粒度）",
            ],
            [
                "重複",
                f"重複 {num(context.expected_increment['duplicateEventIds'])} 件を含んだまま",
                "quarantine へ隔離し、公開データから除外",
            ],
            [
                "粒度",
                "観測（自治体 × 時刻 × 実行）",
                "寄付（DonationID 相当の一意イベント）",
            ],
            [
                "区別",
                "区別せず 1 つの「総件数」にする",
                f"`DataSource` 列で静的分と 8 月分を区別したまま union する",
            ],
            [
                "結果",
                f"{num(static_rows + int(context.expected_increment['rawRows']))} 件（誤り）",
                f"{num(static_rows + accepted)} 件（静的 {num(static_rows)} + 8 月 {num(accepted)}）",
            ],
        ],
        caption=f"T08 の拒否と Notebook 05 の {num(static_rows + accepted)} 件は矛盾しない",
        widths=(1.0, 2.7, 2.7),
        font_size=8.5,
    )
    builder.callout(
        "gate",
        f"Notebook 05 の gold fact 行数が {num(static_rows + accepted)} 件になることを確認します。"
        f"内訳は静的 {num(static_rows)} 件と 8 月の一意イベント {num(accepted)} 件で、"
        "`DataSource` 列で常に区別できます。"
        f"{num(static_rows + int(context.expected_increment['rawRows']))} 件になった場合は"
        "重複排除が効いていません。",
        title=f"{num(static_rows + accepted)} 件ゲート",
    )
    builder.callout(
        "stop",
        "この結合は Notebook 05 の分析レイヤーの中だけで成立します。"
        "Ontology や Data Agent の回答で静的値と観測値を足してよいという意味ではありません。"
        "T08 の拒否は Core の正しい挙動のままです。",
    )
    builder.table(
        list(PARAMETER_COLUMNS),
        build_parameter_rows(context, "Notebook_05"),
        caption="Notebook 05 のパラメーター仕様（全項目）",
        widths=PARAMETER_WIDTHS,
        font_size=PARAMETER_FONT,
        header_size=PARAMETER_HEADER_FONT,
    )
    builder.heading("D.3.2 Notebook 05 を実行して公開状態を確認する", 3)
    builder.callout(
        "note",
        "`SHOW SCHEMAS` は `dbo` ではなく `<Workspace>.<Lakehouse>.dbo` のような完全修飾名を返す場合があります。"
        "名前の見え方だけで schema 非対応と決めません。対象 Workspace と Default Lakehouse の実 ID を確認したうえで、"
        "末尾の schema 名とバッククォート・大小文字を正規化して照合します。"
        "別の Lakehouse に切り替えたり、非 schema Lakehouse を拒否するガードを外したりして通しません。",
        title="SHOW SCHEMAS の完全修飾名を誤判定しない",
    )
    builder.bullets(
        (
            "Notebook 01 または 04 の静的テーブルの準備を完了し、対象 Lakehouse を Notebook 05 の"
            " Default（ピン）に設定します。配置先 Folder と Default Lakehouse は別の設定です。",
            "対象 Lakehouse の `Files/increment` に配布された 3 CSV がそろっていることを確認します。"
            "待機用フォルダーにしかない場合は、先に第 12〜13 章の取り込みを完了します。"
            "Eventhouse に行があるだけでは、Notebook 05 の CSV 入力要件を満たしません。",
            "PARTICIPANT_ID・EXPECTED_WORKSPACE_NAME を設定し、STRICT_SYNTHETIC_CONTRACT=True と"
            "APPLY_CHANGES=False で preview を実行します。PLAN_SHA256 を確認してから、"
            "APPLY_CHANGES=True・CONFIRMED_PLAN_SHA256・EXCLUSIVE_APPLY_WINDOW_CONFIRMED=True で対話実行します。",
            "ANALYTICS_READY と `ops.analytics_publish_control` の Ready を確認します。"
            "GENERATION_ID、公開テーブル、DQ 結果、quarantine 件数を記録し、"
            "Preparing / Publishing のままなら Power BI や Agent の入力にしません。",
        ),
        numbered=True,
    )
    builder.callout(
        "gate",
        "Notebook 05 の分析用カレンダーは、対象となる各暦年の年初から年末まで日付が連続することを確認します。"
        "最後の寄付日・観測日で打ち切らず、日付の重複・空値・欠落も認めません。"
        "修正はカレンダー生成側で行い、DAX の期間補正で隠しません。"
        "カレンダー行が存在しても、その日付に寄付・観測があることは意味しません。"
        "付録 E の Power BI date-table design guidance も確認してください。",
        title="カレンダーの年初・年末とデータの観測範囲を区別する",
    )
    builder.heading("D.3.3 Power BI は別工程で配置する", 3)
    builder.body(
        "先に Notebook 05 の Ready を確認し、SQL analytics endpoint で必要な gold テーブルが参照できることも確認します。"
        "新しい schema が未反映ならメタデータの反映・更新を待ってから進みます。"
        "これらは手順上の前提であり、配置スクリプトが `ops.analytics_publish_control` を自動検査するわけではありません。"
    )
    builder.body(
        "Notebook 05 が作るのは分析テーブルであり、SemanticModel / Report item ではありません。"
        "Ready の確認後、ファシリテーターが `tools/powerbi/Deploy-FurusatoPowerBI.ps1` を"
        " WorkspaceId・ParticipantId・実際の LakehouseId・FolderId で preview し、"
        "対象と定義を確認してから Apply と確認フレーズ `DEPLOY POWER BI <PID>` を指定します。"
        "ExpectedUserPrincipalName と ExpectedTenantId は実行環境の値で指定し、認証主体の取り違えを防ぎます。"
        "これらの実値は配布物へ書き込みません。"
        "配布 PBIP は移植用の byPath 構成なので、Power BI Desktop の Publish で代用しません。"
    )
    builder.callout(
        "stop",
        "FolderId は対象 Lakehouse と同じ Folder の実 GUID を指定します。省略時は Lakehouse の配置先から"
        "取得しますが、実 GUID がない場合や別 Folder を指定した場合は停止します。"
        "Lakehouse が Workspace 直下なら、参加者の対象 Lakehouse を許可された Folder に移し、実 ID と接続を再確認します。"
        "新規モデルとレポートはその Folder に作成されます。既存 item の更新は、対象と影響を確認した場合だけ"
        " `-UpdateExisting` を明示します。この指定は他の Folder の同名 item の更新を許可するものではありません。",
        title="Power BI の Folder と更新対象を preview で確認する",
    )
    builder.bullets(
        (
            "配置後に SemanticModel / Report の実 ID と最終 Folder、Report が参照する SemanticModel ID、"
            "Direct Lake が参照する Workspace / Lakehouse ID を確認します。",
            "Fabric 上で Direct Lake の接続・DAX の結果・レポート表示を確認します。"
            "REST の作成成功や Report の存在だけでは、データを読めた証拠にはなりません。"
            "前年同期間は `SAMEPERIODLASTYEAR` の値を、前年の開始日・終了日を明示した SQL 集計と照合します。"
            "月初や月の途中で終わる範囲も試し、意図せず月末まで拡張されていないか確認します。",
        ),
        numbered=True,
    )
    builder.heading("D.3.4 Gold を Data Agent で評価する場合", 3)
    builder.body(
        "Core Data Agent の選択テーブルは増やしません。`gold.donation_agent` を試す場合は"
        "別の評価構成として記録し、Core の 3 ソースと held-out の前提を保ちます。"
    )
    builder.callout(
        "stop",
        "`gold.donation_agent` の実際の区分列は `DataSource` で、`StaticSeed` と `RealtimeIncrement` が同居します。"
        "`SourceDataset` は SQL 出力の別名として使われることがあっても、このテーブルの実列名ではありません。"
        "Gold を選ぶ評価用 Agent に、Lakehouse は静的 2025 スナップショットだけという説明を流用しません。"
        "区分・期間・粒度を明示し、片方を求められたら DataSource で絞ります。"
        "RealtimeIncrement は重複排除・整形済みの分析データで、Core Eventhouse の raw 観測と同じ指標ではありません。",
        title="Gold の混在データをすべて静的と説明しない",
    )
    builder.body(
        "この文書版の主 Agent に Optional の semantic model を追加しません。"
        "本節のソース比較は実習の主経路とは別の設計検討で、実施しなければ未実施と記録します。"
        "主 Agent と共有データを保持し、単発の比較から改善や因果関係を結論づけません。"
        if context.is_unified_guide else
        "Core の指示・選択テーブル・few-shot は変更せず、別の評価用 Data Agent で同じ質問による前後比較を行います。"
        "単発の前後比較だけで改善や因果関係を結論づけません。空の結果とソース障害は別です。"
        "許可なくソースを削除・停止したり権限を変えたりせず、実施していない障害試験は未実施と記録します。"
    )

    if context.is_unified_guide:
        builder.heading("D.4 User data functions と Code Interpreter", 2)
        builder.body(
            "Code Interpreter は同じ主 Agent で有効です。設定は第 16.7 節、"
            "実際の Python・入力・図・ファイルを確認する追加演習は第 17.13 節です。"
            "別の CI Agent を作成しません。User data functions は主経路の必須ツールではありません。"
            "旧版の控除計算例も所得や個人の税額を証明せず、この実習では接続しません。"
        )
        builder.body(
            "配布 UDF の annualSelfPaymentYen と deductibleBeforePersonalCapYen は、自己負担と"
            "個人上限適用前の機械的な例示だけです。税務アドバイスではないため、T10 は拒否のままです。"
            "この参考情報を、所得・税額を推測する CI 演習へ変更してはいけません。"
        )
        gu.diagnostics_boundary(builder)
    else:
        _legacy_tools(builder, context)

    builder.heading("D.5 Variable Library を移植可能な手動演習として使う", 2)
    _appendix_d5_variable_library(builder, context)

    _appendix_d6_ontology_agent(builder, context)
    _appendix_d7_semantic_model_source(builder, context)


def _legacy_tools(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("D.4 User data functions と Code Interpreter", 2)
    experimental = context.agent_stage_config.get("experimental", {})
    builder.body(
        "Data Agent の Optional ツールは、実施環境の［Add tools］に表示される機能を確認して利用します。"
        "User data functions と Code Interpreter の両方が必ず提供されるとはみなしません。"
        "どちらも Core には含まれません。Core の Data Agent は "
        f"`codeInterpreterEnabled = {'true' if experimental.get('codeInterpreterEnabled') else 'false'}` "
        "の状態で出荷され、10 問はコード実行なしで評価します。"
        "追加する場合は、追加前後で 10 問を実施し、結果を分けて記録してください。"
    )
    builder.heading("D.4.1 配布されている User data function", 3)
    builder.body(
        f"配布物には `{context.udf_relative_path}` が含まれています。"
        "この関数がやることは 1 つだけです。年間の寄付合計から自己負担 2,000 円を引き、"
        "「個人ごとの上限を適用する前の控除対象額」を返します。"
    )
    builder.code_block(
        context.udf_source.strip(),
        language=f"Python（{context.udf_relative_path}）",
        keep_together=True,
    )
    builder.table(
        ["項目", "内容"],
        [
            ["入力", "`annualDonationAmountYen`（年間の寄付合計、0 以上の整数）"],
            ["出力", "`annualSelfPaymentYen`（自己負担 2,000 円まで）と `deductibleBeforePersonalCapYen`"],
            ["`personalCapApplied`", "常に `false`。個人ごとの上限は適用していないことを明示する"],
            ["計算していないもの", "所得・住民税所得割額・家族構成に基づく上限額、ワンストップ特例の可否"],
            ["位置づけ", "税務アドバイスではない。2,000 円ルールの機械的な例示のみ"],
        ],
        caption="配布 UDF の入出力と、意図的に計算していないもの",
        widths=(1.6, 4.8),
        font_size=8.5,
    )
    builder.body(
        "実施する場合は、対象 Workspace / Folder に User data functions item を作成して配布 Python を取り込み、"
        "関数単体のテストと公開を先に行います。0・2,000 円・それ以上の入力と負値の扱いを確認し、"
        "実行結果を記録してから Data Agent の［Add tools］で公開済みの関数を接続します。"
        "接続後は Agent から対象関数が呼ばれたことも確認し、関数単体の成功で代用しません。"
        "メニューや接続先が利用できない場合はブロックと記録し、Python ファイルを置いただけで接続済みとはしません。"
    )
    builder.callout(
        "stop",
        "User data functions がメニューに表示されない場合は、Agent への接続・Agent 経由の呼び出し・"
        "接続後の 10 問をブロックとして記録します。関数単体の公開・呼び出しの成功とは区別し、"
        "利用できる Code Interpreter の実習まで同じ判定にまとめません。"
        "表示されない理由を推測してテナント設定や権限を変更しません。",
        title="利用不可の UDF 接続を単体成功で置き換えない",
    )
    builder.callout(
        "stop",
        "この UDF を接続しても、第 17 章の T10 の期待挙動は変わりません。"
        "UDF が返すのは「上限適用前」の金額であり、寄付者の所得・資産・生活水準や、"
        "その人にとっての控除上限を意味しません。T10 のような推論要求は、"
        "UDF 接続後も同じように拒否されなければなりません。",
        title="UDF を付けても T10 は拒否のまま",
    )
    builder.callout(
        "stop",
        "Code Interpreter を有効にしたことや、回答に Python コードがあることだけでは実行を証明できません。"
        "ツール実行として確認できる記録・結果を保存し、UI と MCP などの経路を分けて評価します。"
        "確認できない経路は未確認と記録し、日本語の図はラベルの欠落も確認します。"
        "Core の評価結果と混ぜず、追加後の 10 問も別の記録として実施してください。"
        "単発の前後比較だけで改善や因果関係を結論づけません。",
    )
    builder.callout(
        "note",
        "MCP 経由でも公開済み Agent の最終回答を保存して比較できます。"
        "ただし、返却内容が回答本文と `isError` だけの場合、内部の SQL／KQL／GQL、"
        "返却行、backend conversation ID は未観測です。"
        "本文内の出典宣言や表、クライアント側の RPC ID を実行証跡の代わりにしません。"
        "本文から確認できた条件の PASS／FAIL／NA と、native 証跡ゲートの未達を分けて報告します。"
        "証跡不足で厳密な合格が 0 件でも、事実回答の正答率が 0% という意味ではありません。"
        "元の 10 問／84 要件や受入ゲートは緩めず、必要な実行詳細を取得できるまで完全な品質受入は保留します。"
        "改善には観測できた本文の欠落や矛盾を使い、見えていない query の欠陥を推測して修正しません。",
        title="MCP の回答比較と完全な native 受入を分ける",
    )
    for tag, caption, alt in (
        ("13-18", "［Add tools］の参考画面。両ツールが表示された構成例であり、現在のメニューは実施環境で確認する。", "Data agent のツール追加メニュー。User data functions と Code Interpreter の 2 項目が表示されている。"),
        ("13-19", "接続先を選ぶ参考画面。User data functions の追加が利用できる場合のみ進む。", "接続する user data function を選択する OneLake catalog の画面。"),
        ("13-20", "「Add code interpreter?」ダイアログ。", "Code interpreter を追加するかどうかを確認するダイアログ。"),
        ("13-21", "［Tools］タブに Code Interpreter が追加された状態。", "Data agent の Tools タブに Code Interpreter が追加されている画面。"),
    ):
        _shot(builder, tag, caption, alt)

def _appendix_d7_semantic_model_source(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("D.7 Semantic Model を Data Agent ソースとして追加する場合（Optional）", 2)
    builder.callout(
        "note",
        "この節は実習ではありません。Core のソース構成は 3 つのままです。"
        "自分の題材で 4 つ目のソースとして Semantic Model を足すときに、"
        "どこを整えるかを先に知っておくための参考情報です。",
        title="実施対象外の参考情報",
    )
    builder.body(
        "まず、D.3 との違いを押さえてください。"
        "D.3 の Notebook 05 は分析用のテーブルを作成します。"
        "セマンティックモデルとレポートは、別工程の Deploy-FurusatoPowerBI.ps1 でデプロイします。"
        "こちらは Direct Lake で人がレポートを読む経路です。"
        "D.7 が扱うのは、そのセマンティックモデルを Data Agent の 4 つ目のソースとして登録し、"
        "自然言語の質問に対して DAX を生成させる経路です。"
        "同じ資産でも、整えるべき場所と評価のしかたが違います。"
    )
    builder.table(
        ["観点", "D.3：レポート用の Direct Lake モデル", "D.7：Data Agent のソースとしてのモデル"],
        [
            [
                "利用者",
                "レポートを読む人",
                "自然言語で質問する人と、質問を受けるエージェント",
            ],
            [
                "生成されるもの",
                "レポートのビジュアル",
                "質問から生成される DAX クエリ",
            ],
            [
                "整える場所",
                "モデルの設計とレポートの構成",
                "モデルの整理に加えて、AI 向けの準備設定",
            ],
            [
                "評価",
                "数値と表示の確認",
                "生成された DAX と回答の確認",
            ],
        ],
        caption="同じセマンティックモデルでも、経路が違えば整える場所が違う",
        widths=(1.0, 2.6, 2.8),
        font_size=8.5,
    )

    builder.heading("D.7.1 Core が追加しない理由", 3)
    builder.body(
        "Core では、静的な指標の権威を Lakehouse 1 つに固定しています。"
        "同じ指標を答えられるソースを 2 つ持たせると、"
        "どちらの数字が正なのかという問題が新しく生まれ、"
        "ルーティングの規則と権威の宣言を設計し直す必要が出ます。"
        "そして設計を変えれば、第 17 章の 10 問は全部やり直しです（第 17.12.1 節）。"
        "ワークショップの学習目的に対して、その追加の複雑さは見合いません。"
        "これは製品上の制約ではなく、本ワークショップの設計上の判断です。"
    )

    builder.heading("D.7.2 追加するときに整える順序", 3)
    builder.body(
        "公開されているセマンティックモデルのベストプラクティスに沿った順序です。"
        "リンクは付録 E にあります。"
    )
    builder.table(
        ["順序", "やること", "なぜ"],
        [
            [
                "1",
                "モデル自体を整理して最適化する。使わない列・テーブル・メジャーを外す",
                "余分な要素は解釈の候補を増やし、精度と応答時間の両方に効く",
            ],
            [
                "2",
                "AI 向けのデータスキーマを、関係する要素とその依存先だけに絞る",
                "似た名前の指標が並ぶと、どれを指したのか決められない",
            ],
            [
                "3",
                "よく聞かれる問いと、間違えやすい複雑な問いに検証済みの回答を用意する",
                "同じ問いに毎回同じ答え方をさせる",
            ],
            [
                "4",
                "Data Agent にモデルを追加し、まず素の状態で試す",
                "どこに追加の指示が要るかは、試さないと分からない",
            ],
            [
                "5",
                "モデル固有の指示は AI 向けの準備設定側に書く",
                "エージェント側の指示はソースをまたぐ規則のためのもの",
            ],
            [
                "6",
                "生成された DAX と実行詳細を読む",
                "回答が違うとき、どの設定を直すかは DAX を見て決まる",
            ],
            [
                "7",
                "利用者を巻き込んで検証する。プログラムによる評価は任意で足す",
                "自動の確認だけでは、期待とのずれが見つからない",
            ],
        ],
        caption="Semantic Model をソースにするときの 7 段階",
        widths=(0.5, 3.0, 2.9),
        font_size=8.5,
    )
    builder.callout(
        "design",
        "指示の置き場所を間違えないでください。"
        "モデル固有の用語定義や既定の集計方針は、AI 向けの準備設定側に書きます。"
        "エージェント側の指示は、ソースをまたいで成立する規則"
        "（回答形式、ルーティング、略語、口調）のために残します。"
        "この分担は、第 16.1 節の 3 層の考え方と同じです。",
        title="モデル固有の指示と、ソースをまたぐ指示",
    )
    builder.callout(
        "note",
        "どのソース種別が説明・ソース指示・例クエリのどれを持てるかは変わりえます。"
        "本書では対応表を固定しません。"
        "付録 E の Data Agent source capability matrix と "
        "Semantic model best practices for Data Agent で、"
        "その時点の対応状況を確認してください。",
        title="対応表は固定しない",
        pull_up=True,
    )


def _appendix_d6_ontology_agent(builder: DocumentBuilder, context: RuntimeContext) -> None:
    contract = context.ontology_contract
    municipality = context.entity("Municipality")
    timeseries = municipality.timeseries_binding
    builder.heading("D.6 Ontology の編集を生成 AI に任せる場合の評価観点（実施対象外）", 2)
    builder.callout(
        "stop",
        "この節は、生成 AI による Ontology 編集支援を評価するための参考情報です。"
        "特定の製品機能の提供や動作を保証するものではありません。"
        "ここに書いてあるのは手順ではなく、この節に実施する操作はありません。"
        "Core の流れ、ランタイムの選択、第 10 章と第 17 章の判定、付録 A、"
        "および数値契約のいずれにも影響しません。"
        "図は評価工程を示す概念図であり、製品の UI や機能一覧ではありません。",
        title="実施対象外：Ontology 編集支援の評価参考",
    )
    builder.body(
        "自分の題材で Ontology 編集支援を評価するときは、業務の意味・参照元データ・"
        "変更してよい範囲を先に決め、人が変更案の根拠と影響を確認します。"
        "以下は一般的な評価観点であり、対象機能の対応状況は最新の公式ドキュメントで確認してください。"
        "プラットフォーム側の前提は C.6 に、公開ドキュメントへのリンクは付録 E にあります。"
    )

    builder.heading("D.6.1 Data Agent と Ontology 編集支援は別物", 3)
    builder.table(
        ["観点", "Fabric Data Agent（Core で使う）", "Ontology の編集を支援するアシスタント（評価対象）"],
        [
            [
                "役割",
                "既存のソースへ問い合わせて回答する消費側の体験",
                "Ontology の定義そのものに変更を提案し、承認後に適用する編集側の体験",
            ],
            [
                "出力",
                "自然言語の回答と、根拠になったソース",
                "エンティティ・関係・プロパティなど、定義の変更案",
            ],
            [
                "影響範囲",
                "回答だけ。Ontology の定義は変わらない",
                "適用すると Ontology の定義そのものが変わる",
            ],
            [
                "本書での扱い",
                "第 16〜18 章の Core。held-out の評価対象",
                "評価の観点としてのみ記述する。実施しない",
            ],
            [
                "混同したときの危険",
                "「質問しただけなのに定義が変わった」と誤解する",
                "「提案を見ただけ」なのに、定義がもう変わったと誤解する",
            ],
        ],
        caption="消費側の Data Agent と、編集側のアシスタントの違い",
        widths=(0.9, 2.6, 3.1),
        font_size=8.5,
    )
    builder.callout(
        "design",
        "この 2 つを 1 つの言葉で呼ばないでください。"
        "Core で構成するのは消費側です。"
        "編集側を評価するときも、Core の Data Agent の設定・評価・公開の手順はそのまま残ります。",
    )

    builder.heading("D.6.2 安全なライフサイクルと評価の観点", 3)
    builder.figure(
        context.diagrams["ontology-authoring-evaluation-lifecycle"]["png"],
        caption="Ontology の変更を提案する生成 AI を評価するときの、一般的な 5 工程。",
        alt_text=(
            "評価ライフサイクル図。左から右へ 5 つの工程が並ぶ。"
            "証拠の発見とスコープ確定、ドメイン設計と意味の境界、"
            "構造とグラウンディングの検証、読み取り専用プレビューと確認、"
            "明示的な書き込みゲートで適用の順である。"
            "各工程には人が確認すべき出口条件が示され、"
            "工程 4 から工程 2 へ戻る差し戻しの経路が破線で描かれている。"
            "下部には、本ワークショップでは実施対象外であることと、"
            "画面名・上限値・保持期間・準拠範囲・課金条件を固定しないことが示されている。"
        ),
        max_height_cm=9.4,
    )
    builder.table(
        ["工程", "目的", "人が持つ責任", "出口条件"],
        [
            [
                "1. 証拠の発見",
                "使える情報と対象範囲を洗い出す",
                "業務の問いを決める",
                "スコープと粒度が文章になっている",
            ],
            [
                "2. ドメイン設計",
                "意味の境界を決める",
                "エンティティ・関係・キーを決める",
                "意味の境界の所有者が人である",
            ],
            [
                "3. 構造とグラウンディングの検証",
                "定義が実データと合うかを確かめる",
                "件数・方向・キーを照合する",
                "期待値と一致している",
            ],
            [
                "4. 読み取り専用プレビューと確認",
                "変更案を適用せずに読む",
                "設計者以外の人が読む",
                "差分を言葉で説明できる",
            ],
            [
                "5. 明示的な書き込みゲートで適用",
                "承認された変更だけを書く",
                "適用を明示的に許可する",
                "適用前後の状態が記録されている",
            ],
        ],
        caption="評価に使う 5 工程と、それぞれの出口条件",
        widths=(1.4, 1.8, 1.7, 1.7),
        font_size=8.5,
    )
    builder.callout(
        "note",
        "「計画を立てる段階」と「実際に書き込む段階」を分けるという考え方そのものは一般的です。"
        "一方で、特定の製品がそれぞれの段階をどう呼ぶか、"
        "画面上のボタンが何という名前かは扱いません。"
        "未公開の名称は契約になりません。"
        "本書が固定するのは、書き込みの前に人が読むという順序だけです。",
        title="段階を分ける考え方は扱うが、名称は扱わない",
    )

    builder.table(
        ["評価カテゴリ", "何を見るか", "本ワークショップで対応する既存の観点"],
        [
            [
                "説明する",
                "エンティティや関係が何を意味するかを、根拠付きで説明できるか",
                "第 4 章の設計根拠と、第 15 章のセマンティックメタデータ",
            ],
            [
                "照会する",
                "問いを分解し、正しいソースへ振り分けて答えられるか",
                "第 16 章のソースルーティングと、第 17 章の held-out",
            ],
            [
                "改善する",
                "定義の不足や曖昧さを見つけ、変更案として提示できるか",
                "第 4.8 節の意味の境界と、第 15 章の manifest 差分",
            ],
        ],
        caption="評価の切り口。特定製品がこの 3 つを提供すると主張するものではない",
        widths=(1.1, 2.7, 2.8),
        font_size=8.5,
    )

    builder.table(
        ["ソース", "問い合わせ言語", "何に向くか", "混同してはいけない点"],
        [
            [
                "Lakehouse テーブル",
                "SQL",
                "静的スナップショットの集計と突き合わせ",
                "観測ではないので、時刻でスライスする問いには向かない",
            ],
            [
                "Eventhouse",
                "KQL",
                "時系列の観測と時間窓の集計",
                "観測は寄付そのものではない。粒度が違う",
            ],
            [
                "セマンティックモデル",
                "DAX",
                "既存のレポート指標をそのまま使う",
                "セマンティックモデルから Ontology を生成すること、"
                "セマンティックモデルを回答の根拠にすること、"
                "Ontology にデータをバインドすることは、それぞれ別の操作",
            ],
            [
                "Ontology（Graph）",
                "ISO GQL",
                "関係のトラバースと意味の境界の確認",
                "どのソースを使うかは Data Agent 側の設定であり、"
                "Ontology 側の定義とは別の契約",
            ],
        ],
        caption="本ワークショップに関係する 4 つのソースと、その評価上の境界",
        widths=(1.2, 1.05, 1.95, 2.4),
        font_size=8.5,
    )
    builder.callout(
        "stop",
        "セマンティックモデルをめぐっては、3 つの別々の操作が混同されがちです。"
        "1 つ目は、セマンティックモデルから Ontology を生成すること。"
        "2 つ目は、セマンティックモデルを回答の根拠にすること。"
        "3 つ目は、Ontology のエンティティにデータをバインドすることです。"
        "生成については、対応するモードや前提条件が公開ドキュメントに整理されています"
        "（https://learn.microsoft.com/en-us/fabric/iq/ontology/concepts-generate）。"
        "また、Data Agent がどのソースへ振り分けるかは Data Agent 側で設定した契約であり、"
        "Ontology の定義を変えたからといって自動的に変わるものではありません。",
        title="生成・グラウンディング・バインディングは別",
    )

    builder.heading("D.6.3 実務での保護と公開情報の確認", 3)
    builder.table(
        ["フェーズ", "一般的なベストプラクティス", "本ワークショップでの現れ方"],
        [
            [
                "ワークスペース",
                "目的を絞ったワークスペースにする",
                "参加者ごとに PID 付きの 1 ワークスペースへ閉じる（第 5.2 節）",
            ],
            [
                "ワークスペース",
                "名前だけで何のアイテムか分かるようにする",
                f"`{context.names['lakehouse']}` のように接頭辞と PID をそろえる（第 5.2 節）",
            ],
            [
                "ソース",
                "キーを安定させる",
                "業務キーをそのまま Entity type key に採用する（第 8 章）",
            ],
            [
                "ソース",
                "外部キーを明示する",
                "Mapping table と Matched key を表で固定する（第 9 章）",
            ],
            [
                "ソース",
                "型をそろえる",
                "String / BigInt を manifest と一致させる（第 15 章）",
            ],
            [
                "ソース",
                "時刻列は 1 本の UTC に寄せる",
                f"`{timeseries.timestamp_column if timeseries else 'DonatedAt'}`（UTC）だけを "
                "time-series の timestamp にする（第 14 章）",
            ],
            [
                "Ontology",
                "意味の境界は人が持つ",
                "第 4.8 節の意味の境界レジスタ",
            ],
            [
                "Ontology",
                "書き換えではなく差分適用と ID 保持を選ぶ",
                "Notebook 02 は semanticEnrichment だけを更新し、ID とバインディングを保持する（第 15 章）",
            ],
            [
                "運用",
                "参照用のロールを分ける",
                "公開時に参照元ソースの読み取り権限を含めて最小権限で共有する（第 18 章）",
            ],
        ],
        caption="4 フェーズのベストプラクティスと、本ワークショップの既存手順の対応",
        widths=(1.0, 2.4, 3.2),
        font_size=8.5,
    )
    builder.callout(
        "note",
        "複合キーはプラットフォームとしてサポートされています。"
        "1 列の派生キーにするのは、可読性と照合のしやすさを優先した設計上の好みであって、"
        "満たさなければならない条件ではありません。"
        "「複合キーは使えない」と読み替えないでください。",
        title="複合キーは使える",
    )
    builder.body(
        "名前の規則は、Entity Type の名前とカスタム Property の名前の両方に適用されます。"
        "1〜26 文字で、英数字・ハイフン・アンダースコアだけを使い、先頭と末尾は英数字にします"
        "（付録 E の Create entity types と Bind data）。"
        "本ワークショップでは Entity Type の `MunicipalityCategoryMetric`、Property の "
        "`MunicipalityPrefAmountRank` と `MunicipalityStaticTotalYen` がいずれも 26 文字で、"
        "現在公開されている上限ちょうどです。"
        "名前を長くする変更を提案されたときは、この 3 つを最初に確認してください。"
    )

    source_scope = (
        "Data Agent の Eventhouse ソースは、承認済み MV とそこから読む 3 関数だけを直接選択します。"
        "唯一の connectedOntology はこの完全な教材モデルです。旧プロファイルの扱いは第 16.9 節で確認してください。"
    ) if context.is_unified_guide else (
        "一方で標準コースの Data Agent の Eventhouse ソースが読むのは、curated なマテリアライズドビューだけです。"
        "この参照先の分担は第 4.6 節と第 14 章で確認できます。"
        "AI 参照構成の別モデルとソース選択は第 16.9 節で確認してください。"
    )
    builder.body(
        f"標準コースの教材用 Ontology は、{contract['entityTypes']} 個のエンティティ、"
        f"{contract['relationshipTypes']} 本の関係、"
        f"{context.metadata_object_count} 件のセマンティックメタデータでできています。"
        "さらに Municipality だけが 2 つのバインディングを持ち、"
        "静的なプロパティは Lakehouse を、time-series は Eventhouse の raw テーブルを読みます。"
        + source_scope
    )
    builder.table(
        ["対象", "現在の設計", "一般的なアシスタントに任せてはいけない理由"],
        [
            [
                f"エンティティ {contract['entityTypes']} 個 / 関係 {contract['relationshipTypes']} 本",
                "第 4 章の設計根拠にもとづいて選んである",
                "件数や構造だけを見て統合や分割を提案されると、意味の境界が消える",
            ],
            [
                f"メタデータ {context.metadata_object_count} 件",
                "Notebook 02 が manifest から一括登録する",
                "別の編集手段から個別に書き換えると、manifest との差分が生まれる",
            ],
            [
                "Municipality の 2 つのバインディング",
                "静的は Lakehouse、time-series は Eventhouse の raw テーブル",
                "curated なビューへ付け替えられると観測の粒度が変わり、"
                "粒度をまたいだ加算を拒否させる設計そのものが崩れる",
            ],
            [
                "Data Agent の Eventhouse 参照先",
                "統合 Agent は承認済み MV と 3 関数だけを選ぶ" if context.is_unified_guide
                else "標準コースの Eventhouse ソースでは承認済み MV だけを選ぶ",
                "Ontology 側と Data Agent 側は別の契約なので、"
                "片方だけ変えると両者の説明が食い違う",
            ],
        ],
        caption="このシナリオで、人の確認なしに変えてはいけない 4 つの境界",
        widths=(1.3, 2.2, 3.1),
        font_size=8.5,
    )
    builder.callout(
        "gate",
        "Notebook 02 の manifest が正本です。"
        "preview と適用のあいだに、別の編集手段から同じ Ontology を書き換えないでください。"
        "途中で差分が生まれると、preflight が停止するか、"
        f"登録件数が契約の {context.metadata_object_count} 件と合わなくなります。",
        title="manifest が正本／同時編集をしない",
    )

    builder.table(
        ["症状", "最初に確認すること", "次に確認すること"],
        [
            [
                "機能が見当たらない",
                "公開プレビューの提供状況・テナント設定・リージョン",
                "最新の公式ドキュメントで、提供範囲そのものを確認する",
            ],
            [
                "ソースが開けない",
                "サインインしている ID と Fabric のロール",
                "参照元ワークスペースとソースの読み取り権限",
            ],
            [
                "エンティティが多すぎる / 少なすぎる",
                "対象範囲と粒度を人の言葉で言い直す",
                "設計の意図を書き直してから、もう一度提案させる",
            ],
            [
                "結果が 0 件になる",
                "グラフモデルを手動で更新する",
                "時間範囲と、キー・timestamp の対応付けを見る",
            ],
            [
                "変更案が大きすぎる",
                "書き換えではなく差分適用を選ぶ",
                "既存の ID が保持されているかを確認する",
            ],
            [
                "下書きが見当たらない",
                "未適用の下書きが残る前提を置かない",
                "適用済みのアイテムの状態と分けて記録する",
            ],
            [
                "操作が失敗した",
                "同じ操作を慎重に再試行する",
                "すでに適用済みの部分の状態を、失敗した操作と分けて記録する",
            ],
        ],
        caption="評価時の切り分け。上限値のような未公開の数値は使わない",
        widths=(1.6, 2.3, 2.7),
        font_size=8.5,
    )

    builder.body(
        "次の 8 主題は、編集支援を導入する前に最新の公開情報と対象環境の設定で確認します。"
        "この表は特定製品の機能・上限・課金条件を保証するものではありません。"
    )
    builder.table(
        ["確認する主題", "確認する情報", "確認方法と注意点"],
        [
            [
                "UI の名称と配置",
                "画面名・ボタン名・モードの呼び方",
                "最新の公式手順と実際の UI を照合する。未公開の名称を手順の根拠にしない",
            ],
            [
                "上限値",
                "行数・ファイル数・サイズなどの上限",
                "対象機能の最新の公式ドキュメントを確認する。この参考表では上限の数値を固定しない",
            ],
            [
                "保持",
                "対話や文脈がどれだけ残るか",
                "機能とテナント設定で確認する。この参考表では保持日数を固定しない（C.6）",
            ],
            [
                "ロール別の可否",
                "ロールごとにできること・できないことの一覧",
                "必要な操作と対象ソースに対する権限を、公開ドキュメントと実際の設定で確認する",
            ],
            [
                "機能単位の準拠範囲",
                "特定のコンプライアンス境界への適合・非適合",
                "公開情報に記載された対象機能・適用条件と、容量のリージョン・テナント設定を照合する（C.6）",
            ],
            [
                "価格",
                "操作ごとの課金額や、プレビュー中の扱い",
                "公式の価格情報と消費の説明を確認する。トークン・CU・エンジン側のクエリ消費を区別し、固定料金を推測しない（C.6）",
            ],
            [
                "公平性の評価",
                "評価方法・対象データ・結果の適用範囲",
                "公開された責任ある AI の原則と評価条件を確認し、別の条件への適用を保証しない（C.6・付録 E）",
            ],
            [
                "同意と収集",
                "プライバシー・収集対象・利用条件",
                "公開プライバシー文書と実際の設定で確認し、同意や収集の条件を推測しない（C.6）",
            ],
        ],
        caption="公開ドキュメントで確認する 8 つの主題",
        widths=(1.2, 2.4, 3.0),
        font_size=8.5,
    )
    builder.callout(
        "note",
        "評価前に、対象機能と条件が現行の公式ドキュメントに記載されていることを確認します。"
        "確認できない能力や数値は未確認として扱い、利用者への約束や適用の根拠にしません。"
        "プラットフォーム側の前提と参考リンクは C.6 と付録 E で確認してください。",
        title="確認できない機能や条件を前提にしない",
        pull_up=True,
    )


#: Natural Japanese for the runtime's English ``manualSteps``. The mapping is keyed
#: on the shipped English text so a runtime wording change surfaces as a build
#: failure rather than a silently stale translation.
VARIABLE_LIBRARY_STEPS_JA = {
    "Create VL_Furusato_<PID> in the participant workspace.": (
        "対象 Workspace の指定 Folder に `VL_Furusato_<PID>` という名前で Variable Library を作成します。"
    ),
    "Import variables.json, settings.json, and valueSets/*.json.": (
        "配布テンプレートの `variables.json`・`settings.json`・`valueSets/*.json` を取り込みます。"
    ),
    "Select the active value set in the workspace.": (
        "ワークスペースで、使用する値セット（Development か Test）をアクティブに切り替えます。"
    ),
    "Override ParticipantId and ExpectedWorkspaceName without committing tenant-specific IDs.": (
        "`ParticipantId` と `ExpectedWorkspaceName` を自分の環境の値で上書きします。"
        "テナント固有の ID は定義に含めず、値セット側だけで指定します。"
    ),
}


def _appendix_d5_variable_library(builder: DocumentBuilder, context: RuntimeContext) -> None:
    names = context.names
    template = context.workspace_contract["analyticsExtension"]["variableLibraryTemplate"]
    variables = context.variable_library.get("variables", [])
    builder.body(
        f"配布物には `{template['path']}` に Variable Library のテンプレートが含まれています。"
        f"{names['variableLibrary']} を作成して取り込むと、Participant ID や環境名などを"
        "値セットで切り替えられます。基本型だけを使い、テナント固有の ID を含みません。"
    )
    builder.heading("D.5.1 手順", 3)
    missing = [step for step in template["manualSteps"] if step not in VARIABLE_LIBRARY_STEPS_JA]
    if missing:
        raise ValueError(f"Untranslated variable library manual step(s): {missing}")
    builder.bullets(
        [VARIABLE_LIBRARY_STEPS_JA[step] for step in template["manualSteps"]],
        numbered=True,
    )
    builder.callout(
        "gate",
        "テンプレートの取り込みだけでは Notebook のパラメーターや Pipeline に値は自動接続されません。"
        "アクティブな値セットと NotebookUtils で参照した実際の値を確認し、"
        "どの実行で使ったかを記録します。配置、値セットの有効化、実行時の参照確認を分けて扱ってください。",
        title="Variable Library の配置と利用を分ける",
    )

    builder.heading("D.5.2 宣言済み変数", 3)
    builder.body(
        "「用途（配布物の原文）」列は、配布テンプレートの `note` フィールドをそのまま転記したものです。"
        "テンプレートの値と一字一句同じであることを確認できるよう、翻訳していません。"
    )
    builder.table(
        ["宣言済み変数", "型", "既定値", "用途（配布物の原文）"],
        [
            [
                variable["name"],
                variable["type"],
                '"" (空文字)' if variable["value"] == "" else str(variable["value"]),
                variable["note"],
            ]
            for variable in variables
        ],
        caption=f"Variable Library テンプレートが宣言する {len(variables)} 変数",
        widths=(1.6, 0.8, 1.5, 4.0),
        font_size=8.5,
    )

    builder.heading("D.5.3 契約と制約", 3)
    builder.table(
        ["項目", "内容（配布物の原文）"],
        [
            ["定義フォーマット", template["definitionFormat"]],
            ["値セット", "、".join(str(entry) for entry in context.variable_library_value_sets)],
            ["参照構文", template["referenceSyntax"]],
            ["制約", template["limitations"]],
        ],
        caption="Variable Library の契約",
        widths=(1.4, 5.0),
        font_size=8.5,
    )
    builder.body(
        "参照構文の `/**/` は NotebookUtils が要求する固定の接頭辞であり、省略できません。"
        "アクティブな値セットは環境の状態であって、コミットされる定義には含まれません。"
        "ItemReference と ConnectionReference は、静的 ID が環境をまたいで自動バインドされないため除外しています。"
    )
    builder.callout(
        "note",
        "`IncrementFileName` はファシリテーター向けの診断とフォールバック専用です。"
        "参加者の増分取り込みは、OneLake FileCreated トリガーが `Subject` を渡す経路だけを使います。"
        "この変数を手で設定して Pipeline を実行するのは、通常の参加者手順ではありません。",
        pull_up=True,
    )


def appendix_e_links(builder: DocumentBuilder, context: RuntimeContext) -> None:
    builder.heading("付録 E　参考リンク", 1, new_page=False)
    builder.body("必ず最新の公式ドキュメントを参照してください。")
    builder.table(
        ["トピック", "URL"],
        [[title, url] for title, url in gc.REFERENCE_LINKS],
        caption="公式ドキュメントへのリンク",
        widths=(2.0, 4.6),
        font_size=8.5,
        keep_tail_rows=6,
    )
    builder.callout(
        "note",
        "一部の URL は、公開リージョン・言語設定・プレビュー機能の有効化状況により"
        "リダイレクトや閲覧制限が発生する場合があります。",
        pull_up=True,
    )
