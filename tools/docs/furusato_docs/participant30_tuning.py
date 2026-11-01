"""Source-bound participant steps for reproducing the adopted Data Agent profile.

Only document models are produced here. No authentication or Fabric operation is
performed. Instruction and query literals intentionally retain canonical bytes
(after the same outer-whitespace trim as the profile compiler).
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from furusato_html.model import Block, Section, Text

PROFILE = "measured-contract-20261015"
PROFILE_REL = Path("workshop/v3.0.0-preview/data-agent/candidates") / PROFILE
VIEW_RELS = (
    Path("workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_donation_detail.sql"),
    Path("workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_donor_catalog_supplier.sql"),
    Path("workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_municipality_snapshot.sql"),
    Path("workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_supplier_catalog.sql"),
    Path("workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views/agent_relationship_dictionary.sql"),
    Path("workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views/agent_prefecture_category_metric.sql"),
)
INSTRUCTION_FILES = (
    ("global-instructions.txt", "Agent instructions", "全体の回答方針", "Agent-wide answer policy"),
    ("lakehouse-instructions.txt", "Lakehouse / SQL instructions", "静的データと品質処理の SQL", "SQL for static data and quality processing"),
    ("kusto-instructions.txt", "KQL Database / instructions", "8月の観測データの KQL", "KQL for August observations"),
    ("semantic-model-instructions.txt", "Semantic model / instructions", "Gold と既存メジャーの DAX", "DAX for Gold and existing measures"),
)


def _text(ja, en=None):
    return Text(ja, ja if en is None else en)


def _paragraph(ja, en):
    return Block("paragraph", {"text": _text(ja, en), "lead": False})


def _steps(rows):
    return Block("list", {"numbered": True, "items": [_text(*row) for row in rows]})


def _code(value, label="text", *, canonical=False):
    payload = {"text": value, "language": _text(label)}
    if canonical:
        payload["canonicalLiteral"] = True
    return Block("code", payload)


def _table(headers, rows, ja, en, widths=None):
    def cell(value):
        return _text(*value) if isinstance(value, tuple) else _text(str(value))
    result = {"number": 0, "headers": [cell(h) for h in headers],
              "rows": [[cell(c) for c in row] for row in rows],
              "caption": _text(ja, en), "wide": len(headers) >= 5}
    if widths:
        result["widths"] = widths
    return Block("table", result)


def _append(parent, suffix, title, blocks):
    number = f"{parent.number}.{suffix}"
    section = Section(ident=f"{parent.ident}-{suffix}", level=2, number=number,
                      title=_text(number + " " + title[0], number + " " + title[1]),
                      blocks=blocks, chapter=parent.chapter, appendix=parent.appendix)
    if any(child.ident == section.ident for child in parent.children):
        raise ValueError("Duplicate participant tuning section: " + section.ident)
    parent.children.append(section)


def _assets(root):
    profile = root / PROFILE_REL
    manifest = json.loads((profile / "profile-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("profile") != PROFILE:
        raise ValueError("Participant guide profile must match its source manifest")
    for name, digest in manifest["sha256"].items():
        if hashlib.sha256((profile / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Participant tuning source hash mismatch: " + name)
    selections = json.loads((profile / "selection-contract.json").read_text(encoding="utf-8"))["sources"]
    examples = json.loads((profile / "kusto-examples.json").read_text(encoding="utf-8"))["examples"]
    descriptions = json.loads((profile / "source-descriptions.json").read_text(encoding="utf-8"))
    sql_nodes = selections["lakehouse_tables"]
    objects = [node for node in sql_nodes if node["type"] in {"lakehouse_tables.table", "lakehouse_tables.view"}]
    columns = [node for node in sql_nodes if node["type"] == "lakehouse_tables.column"]
    if (len(objects), len(columns), len(examples)) != (17, 143, 9):
        raise ValueError("Participant guide needs exactly 17 SQL objects, 143 columns and nine KQL examples")
    compiler = ast.parse((root / "tools/data-agent/measured_contract_profile.py").read_text(encoding="utf-8"))
    measures = next(ast.literal_eval(node.value) for node in compiler.body
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MEASURES" for t in node.targets))
    if len(measures) != 10:
        raise ValueError("Participant guide needs the ten source-owned DAX measures")
    return profile, manifest, selections, examples, descriptions, measures


def append_tuning_sections(chapter: Section, root: Path, *, figures):
    """Append sections 17.5–17.16 after the existing four chapter-17 sections."""
    if chapter.chapter != 17:
        raise ValueError("Participant tuning belongs to Chapter 17")
    profile, manifest, selections, examples, descriptions, measures = _assets(root)
    _append(chapter, 5, ("ここから始める：教材と実施順", "Start here: materials and order"), [
        _paragraph("この章の到達点は、配布版と同じ指示・データ選択・クエリ例を自分の1件の Data Agent に設定し、公開後に確認して、19章で再評価できることです。同じ数値の評価結果を保証するものではありません。17.5〜17.8で準備し、17.11の KQL 選択、17.12の9例の直接実行、17.13のモデル選択、17.14の Ontology を確認したら、17.16のコマンドを実施します。17.9〜17.14の指示原文は設定の確認用です。その後17.2の SQL と Code Interpreter の確認へ戻ります。",
                   "The goal is to configure your one Data Agent with the distributed instructions, data selection and query examples, verify the published configuration, and evaluate it in Chapter 19. An identical evaluation score is not guaranteed. Prepare in 17.5–17.8, check KQL selection in 17.11, directly execute all nine examples in 17.12, check model selection in 17.13 and ontology in 17.14, then run the commands in 17.16. The original instruction text in 17.9–17.14 is a configuration reference. Afterwards return to the SQL and Code Interpreter checks in 17.2."),
        _steps([
            ("参加者用 ZIP をすべて展開します。展開先の START_HERE.txt、guide、attachments、source を確認します。以下の workshop/ と tools/ のパスは、展開先の source フォルダーを起点とします。Word または HTML を操作手順書にして、長い指示や SQL は同梱ファイルを UTF-8 のテキストとしてコピーできます。別の README を探して手順を補う必要はありません。",
             "Extract the entire participant ZIP and locate START_HERE.txt, guide, attachments and source. All workshop/ and tools/ paths below start at the extracted source folder. Use Word or HTML as the procedure; long instructions and SQL can be copied from the supplied UTF-8 files. No separate README search is needed to fill in these steps."),
            ("4章で作業フォルダーと自分の参加者IDを確認し、5〜13章を実施します。Lakehouse の静的データ、Notebook 05 の Gold と品質管理テーブル、Eventhouse の集計ビュー、Semantic model、主 Ontology が必要です。未完了の時系列・Metrics は別欄に記録します。これらの警告を SQL の成功で完了扱いにしません。",
             "Confirm your folder and participant ID in Chapter 4 and complete Chapters 5–13. You need the static Lakehouse data, Notebook 05 Gold and quality tables, Eventhouse aggregate view, semantic model and main ontology. Record incomplete time-series or Metrics setup separately; SQL success does not resolve those warnings."),
            ("自分の DA_Furusato_<PID> を開き、ワークスペースとアイテムの URL を記録します。まだ無い場合は、指定フォルダーで New item から Data agent を作成し、この名前を付けます。既存の Agent があれば同じアイテムを使います。公開版がある場合は変更前の4つの指示、選択、クエリ例、公開状態を自分の記録フォルダーに保存します。",
             "Open your DA_Furusato_<PID> and record its workspace and item URL. If absent, use New item in the assigned folder to create a Data agent with this name. Reuse an existing agent. If a published version exists, save the four current instruction fields, selections, query examples and publication state in your own record folder before editing."),
            ("公開前に Explorer の Tools を確認し、Code Interpreter が無い場合は Add tools から同じ Agent に追加して保存します。既にある場合は変更しません。17.16の prepare より前にこの操作を完了し、公開後の確認で初めて追加することがないようにします。",
             "Before publication, inspect Tools in Explorer. If Code Interpreter is absent, use Add tools to add it to this same agent and save; leave it unchanged if already present. Finish this before prepare in 17.16 so that you do not first add it during post-publication checks."),
            ("編集権限がない場合はワークスペース管理者に自分の作業範囲の権限を依頼します。テナント設定や容量が機能を許可していない場合は、その前提条件を解消してから再開します。管理権限を持たない参加者が設定を書き換える必要はありません。",
             "If you cannot edit, ask the workspace administrator for access to your assigned scope. Resolve tenant or capacity prerequisites before continuing when they disable a feature. Participants without administrative permissions do not need to change tenant settings."),
        ]),
        _table([("用途", "Purpose"), ("ZIP 内の場所", "Location in ZIP")], [
            [("今回採用した指示・選択・例", "Adopted instructions, selections and examples"), PROFILE_REL.as_posix()],
            [("前半4つの SQL ビュー", "First four SQL views"), "workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views"],
            [("後半2つの SQL ビュー", "Last two SQL views"), "workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views"],
            [("既存モデルの照合元", "Existing-model contract source"), "tools/data-agent/measured_contract_profile.py / MEASURES"],
            [("評価の問題・記録方法", "Evaluation questions and recording procedure"), ("本書19章と付録C", "Chapter 19 and Appendix C in this guide")],
        ], "この章で使う同梱ファイル", "Included files used in this chapter", (2.0, 4.6)),
    ])
    view_blocks = [
        _paragraph("Lakehouse の SQL analytics endpoint を開き、New SQL query を選びます。下の6つの CREATE VIEW を上から順に、各ブロックごとに1回ずつ実行します。5番目の agent_relationship_dictionary を先に作成し、それを参照する6番目の agent_prefecture_category_metric はその後に作成します。これらは読み取り用のビューで、CSV や基礎テーブルの値は変更しません。既にあるビューは再作成せず、定義を下記と照合します。異なる場合は現在の定義を保存してから、同じ名前のビューの定義だけを変更します。別の参加者のビューやテーブルを削除しません。",
                   "Open the Lakehouse SQL analytics endpoint and select New SQL query. Run the six CREATE VIEW blocks from top to bottom, once each and separately. Create the fifth view, agent_relationship_dictionary, before the sixth view, agent_prefecture_category_metric, which references it. These are read-only views and do not change CSV or base-table values. For existing views, compare their definitions with the blocks instead of creating them again. Save any differing definition before changing only that same view's definition. Do not delete other participants' views or tables."),
        _paragraph("テーブルが見えなければ、5章の Notebook 01 と11章の Notebook 05 の完了、SQL endpoint の同期状態、接続先 Lakehouse を確認します。CREATE VIEW 権限がなければ、その Lakehouse の管理者に権限または下記の実行を依頼します。ビュー名だけがある状態では完了ではありません。",
                   "If tables are absent, check completion of Notebook 01 in Chapter 5 and Notebook 05 in Chapter 11, SQL endpoint synchronization and the selected Lakehouse. If CREATE VIEW permission is missing, request permission or execution of the blocks from that Lakehouse's administrator. A view name alone does not establish completion."),
    ]
    for relative in VIEW_RELS:
        view_blocks += [_paragraph("実行するファイル：" + str(relative), "File to run: " + str(relative)),
                        _code((root / relative).read_text(encoding="utf-8").strip(), "SQL")]
    view_blocks += [_paragraph("6つとも作成または照合できたら、各ビューを SELECT TOP (5) * FROM dbo.<ビュー名> で開き、エラーなく結果が返ることを確認します。続いて次の照会を実行し、17.7の選択対象の全列名・型と照合します。実テーブルに追加の列がある場合でも、選択するのは17.7の143列だけです。たとえば agent_donation_detail の DonationDataLayer は選択しません。品質管理テーブルが未作成の場合は11章に戻り、空の表を代わりに作りません。",
                               "Once all six views are created or checked, run SELECT TOP (5) * FROM dbo.<view name> for each and verify successful results. Then run the following inventory query and compare every selected column name and type with 17.7. Physical objects may have additional columns; select only the 143 listed columns. For example, leave DonationDataLayer in agent_donation_detail unselected. If quality tables are absent, return to Chapter 11; do not create empty substitutes."),
                    _code((profile / "sql-schema-inventory.sql").read_text(encoding="utf-8").strip(), "SQL")]
    _append(chapter, 6, ("SQL の6つのビューを用意する", "Prepare the six SQL views"), view_blocks)

    selection_blocks = [
        _paragraph("Data Agent の Add data / Sources で、自分の Lakehouse の SQL endpoint を選びます。下表の17オブジェクトだけを選び、展開して計143列を選びます。全テーブルを一括選択しません。6つの dbo.agent_* は Views、ほかは該当スキーマの Tables にあります。画面が更新されていなければソースのスキーマを再取得してから、実在する項目を選びます。ID を手入力で作りません。",
                   "In the Data Agent Add data / Sources area, select your Lakehouse SQL endpoint. Select exactly the 17 objects below and expand them to select all 143 listed columns. Do not select every table. The six dbo.agent_* objects are under Views; the others are under their schema's Tables. If the UI is stale, refresh source schema before selecting actual objects. Never manufacture an ID."),
    ]
    sql_nodes = selections["lakehouse_tables"]
    for node in sql_nodes:
        if node["type"] not in {"lakehouse_tables.table", "lakehouse_tables.view"}:
            continue
        path = node["path"]
        columns = [c for c in sql_nodes if c["type"] == "lakehouse_tables.column" and c["path"][:-1] == path]
        qualified = path[1] + "." + path[-1]
        selection_blocks.append(_table([("列名", "Column"), ("SQL の型", "SQL type")],
                                       [[c["path"][-1], c["dataType"]] for c in columns],
                                       qualified + "：選択する" + str(len(columns)) + "列",
                                       qualified + ": select " + str(len(columns)) + " columns", (4.8, 1.8)))
    selection_blocks += [
        _paragraph("143列は業務列だけの選択契約で、システムの世代管理列は含みません。サービスが親テーブルの選択を展開した結果、最初のソース探索に無かった _WorkshopGenerationId が選択される場合があります。17テーブルを選んだだけで143列と判断せず、現在の列の選択状態を読み直します。",
                   "The 143-column contract contains business columns only, excluding system generation metadata. When the service expands selected parent tables, it may select _WorkshopGenerationId leaves absent from the initial source discovery. Selecting 17 parent objects alone does not establish 143 selected columns; read the current leaf selections back."),
        _table([("親テーブル（選択を残す）", "Parent table (keep selected)"), ("表示された場合に外すシステム列", "System column to uncheck if displayed")],
               [["dbo." + name, "_WorkshopGenerationId"] for name in (
                   "ot_donor", "ot_gift", "ot_gift_category", "ot_mun_category_metric",
                   "ot_pref_donation_flow", "ot_prefecture")],
               "143業務列の対象外となる6つの世代管理列", "Six generation-metadata leaves outside the 143 business columns", (3.5, 3.1)),
        _steps([
            ("SQL ソースを開き直し、必要ならスキーマを更新して、上の6テーブルの列を展開します。実際のソース探索・読戻しで得られたノードと列を確認します。表示されない列の ID を推測したり、新しい項目を作ったりしません。",
             "Reopen the SQL source, refresh its schema if needed, and expand columns under the six tables above. Inspect nodes and columns returned by actual discovery/readback. Never guess an ID or create a synthetic item for an undisplayed column."),
            ("_WorkshopGenerationId が選択されている場合は、その6つの列のチェックだけを外します。17親オブジェクトと、この節に列挙した143業務列の選択を残します。親を一括選択し直してシステム列を再選択しないようにします。",
             "If _WorkshopGenerationId is selected, uncheck only those six leaves. Keep the 17 parent objects and all 143 business columns listed in this section selected. Do not select all parent contents again and reselect the metadata leaves."),
            ("保存後に実際のソースと選択状態を読み戻し、17オブジェクト・143業務列と、表示された6つのシステム列が未選択であることを確認します。149列のまま公開へ進まず、143の条件や選択契約を書き換えて検査を通しません。",
             "After saving, read the actual source and selections back. Confirm 17 objects and 143 business columns, with the six displayed metadata leaves unselected. Do not proceed to publication with 149 columns or change the 143-column contract to make validation pass."),
            ("選択を修正した場合は、17.16で新しい記録先を使って読み取り専用 prepare を実行し直します。変更前の記録と使用済みの apply-intent / publish-intent を保持し、同じ書き込みを再送しません。新しい読戻しと143列の確認が成功してから、その構成に対応する後続の操作へ進みます。",
             "After a selection correction, run read-only prepare again in a new record directory as described in 17.16. Retain prior evidence and spent apply-intent/publish-intent records; do not replay the same write. Continue with operations for the newly prepared configuration only after fresh readback and the 143-column check succeed."),
        ]),
        _paragraph("この確認はソースの構成を一致させるためのものです。設定の一致や公開の成功を、回答精度や実際のソース問い合わせの成功と扱いません。17.2と19章で実回答を別に評価します。",
                   "This check aligns source configuration. Configuration equality or publication success does not establish answer accuracy or actual source-query success. Evaluate real answers separately in 17.2 and Chapter 19."),
        _paragraph("選択契約には各テーブル・列の説明も含まれます。同じ説明を設定できる画面では、selection-contract.json の同じ path の description を使います。編集欄がない項目に独自の JSON フィールドを作りません。指示のコピーだけでは、この説明と実際の選択の一致まで確認したことにはなりません。17.15の構成確認で、UI 確認済みと定義照合済みを区別して記録します。",
                                    "The selection contract also contains table and column descriptions. Where an editing field is available, use the description at the same path in selection-contract.json. Do not invent JSON fields for properties without an editor. Copying instructions alone does not verify these descriptions or actual selections; distinguish UI checks from definition checks in the configuration record in 17.15.")]
    _append(chapter, 7, ("17オブジェクト・143列を選択する", "Select 17 objects and 143 columns"), selection_blocks)

    field_rows = [
        ["Agent instructions", "global-instructions.txt", ("全体の欄。追記せず全文置換", "Agent-wide field; replace, do not append")],
        ["Lakehouse SQL", "lakehouse-instructions.txt", ("この SQL ソースの指示欄", "Instructions for this SQL source")],
        ["KQL Database", "kusto-instructions.txt", ("この KQL ソースの指示欄", "Instructions for this KQL source")],
        ["Semantic model", "semantic-model-instructions.txt", ("このモデルソースの指示欄", "Instructions for this model source")],
        ["Ontology (Gen2)", ("挿入する指示ファイルなし", "No instruction file to insert"), ("同じ主 Ontology の選択と Entity 説明を保持", "Preserve the same main ontology selection and entity descriptions")],
    ]
    _append(chapter, 8, ("入力先を決めて指示を設定する", "Map fields and set instructions"), [
        _paragraph("17.16のコマンドが4つの指示・説明・選択・例をまとめて設定するので、通常は手で貼り付ける必要はありません。以下の4つの指示本文は配布プロファイルから直接収録した原文です。手作業で確認・復元する場合は、日本語版・英語版で同じ原文を使います。入力先にある文章をすべて選択して置き換え、見出し・ファイル名・説明・ハッシュ値は貼り付けません。本文を翻訳したり、別の欄の末尾に足したりしません。HTML の Copy または同梱 txt が長文のコピーに適しています。Word からコピーした場合も、保存後に改行や記号が変わっていないか確認します。",
                   "The commands in 17.16 configure all four instructions, descriptions, selections and examples together, so manual pasting is normally unnecessary. The following four instruction bodies are included directly from the distributed profile. For manual inspection or restoration, follow these rules. Both guide languages use the same original text. Replace the whole destination field; do not paste headings, filenames, explanations or hashes. Do not translate the bodies or append them to another field. HTML Copy or the included txt files are convenient for long text; after copying from Word, also check that line breaks and symbols survived saving."),
        _table([("設定先", "Destination"), ("同梱ファイル", "Included file"), ("操作", "Action")], field_rows,
               "4つの指示と Gen2 Ontology の対応", "Four instruction fields and the Gen2 ontology mapping", (1.5, 2.5, 2.6)),
        _paragraph("新規 Agent は3つの通常ソースを追加した後、画面の Ontology 区画から既存の主 Ontology を追加します。移行済み Agent は、その区画の同じ主 Ontology と選択を保持します。通常ソースの一覧が3件でも、主 Ontology が別にあれば欠落とは限りません。ontology-instructions.txt は旧形式用です。Gen2 の global や別ソースの欄には貼り付けず、Notebook 04 の初期定義も移行済み Agent に再適用しません。",
                   "For a new agent, add the three ordinary sources, then add the existing main ontology through the ontology area. For a migrated agent, preserve the same main ontology and selections there. Three ordinary sources do not imply a missing ontology if it appears separately. ontology-instructions.txt is for the legacy format: never paste it into Gen2 global instructions or another source, and never reapply the Notebook 04 initial definition to a migrated agent."),
    ])
    for suffix, (filename, field, ja_title, en_title) in zip((9, 10, 11, 13), INSTRUCTION_FILES):
        value = (profile / filename).read_text(encoding="utf-8").strip()
        units = len(value.encode("utf-16-le")) // 2
        if units > 10000:
            raise ValueError("Participant instruction exceeds the service field limit: " + filename)
        blocks = [_paragraph("設定先：" + field + "。同梱ファイル：" + (PROFILE_REL / filename).as_posix() + "。本文は前後の空白を除いて" + str(units) + " UTF-16単位です。",
                             "Destination: " + field + ". Included file: " + (PROFILE_REL / filename).as_posix() + ". The body is " + str(units) + " UTF-16 units after trimming outer whitespace."),
                  _code(value, "instructions", canonical=True)]
        if filename == "kusto-instructions.txt":
            blocks.insert(0, _paragraph("KQL Database は Eventhouse の入れ物ではなく、その中のデータベースを選択します。DonationObservationSummaryForAgent だけを選び、次の10列をすべて選びます。この集計の粒度は自治体・1分・WorkshopRunId・ParticipantAlias・SourceFile の5項目です。ObservationCount の合計が観測件数であり、集計後の行数ではありません。",
                                        "Select the KQL database inside your Eventhouse. Select only DonationObservationSummaryForAgent and all ten columns below. Its grain has five fields: municipality, minute, WorkshopRunId, ParticipantAlias and SourceFile. Sum ObservationCount for observations; do not count the aggregate rows."))
            kql_columns = [n for n in selections["kusto"] if n["type"] == "kusto.column"]
            blocks.insert(1, _table([("列名", "Column"), ("型", "Type")],
                                   [[c["path"][-1], c["dataType"]] for c in kql_columns],
                                   "KQL で選択する10列", "The ten selected KQL columns", (4.8, 1.8)))
        if filename == "semantic-model-instructions.txt":
            blocks.insert(0, _paragraph("Semantic model を同じ Agent に直接追加し、寄附・寄附者・日付・自治体・返礼品の5テーブルを選びます。寄附[寄附金額] が表示可能で、下記の10メジャーが12章で作成したモデルに実在することをモデルの編集画面で照合します。メジャーを新しく作ったり式を書き換えたりして採点結果に合わせません。メジャー名と列の ID は実際のモデルのものを選び、例示 ID を入力しません。",
                                        "Add the semantic model directly to the same agent and select five tables: 寄附, 寄附者, 日付, 自治体 and 返礼品. In the model editor, confirm that 寄附[寄附金額] is visible and the ten measures below exist in the model created in Chapter 12. Do not add measures or rewrite expressions to fit evaluation results. Select names and IDs from the actual model; never enter example IDs."))
            for name, expression in measures.items():
                blocks += [_paragraph("既存メジャー：" + name, "Existing measure: " + name), _code(name + " = " + expression, "DAX")]
        _append(chapter, suffix, (ja_title + "の指示全文", en_title + ": complete instructions"), blocks)
    # Insert the example section between the KQL and semantic-model sections.
    example_blocks = [_paragraph("まず8章の KQL Queryset で、自分の KQL Database を接続先に選び、下の9件の KQL を1件ずつ読み取り専用で実行します。各クエリの実行日時、成功またはエラー、返された結果を記録します。これは自分による実行の確認で、Data Agent が実行した証拠ではありません。すべて成功してから17.16で設定を適用・公開します。KQL ソースの Example queries / Examples でも9件のサービス検証を確認します。手作業で設定する場合は既存の例を記録してから、下の質問と KQL の組を9件設定します。質問欄には質問だけ、クエリ欄には対応する KQL だけを貼ります。評価問題や期待値を例に追加しません。各例を保存して検証結果を確認します。Valid にならない例は Agent に使われないため、9件の登録数だけで完了にしません。",
                                 "First connect the Chapter 8 KQL queryset to your KQL database and run each of the nine KQL queries below as a separate read-only query. Record its execution time, success or error and returned results. This proves your direct execution, not Data Agent execution. Apply and publish through 17.16 only after all nine succeed. Also check all nine service validations under the KQL source Example queries / Examples. For manual configuration, record existing examples before configuring the nine question-and-KQL pairs below. Paste only the question into the question field and only its paired KQL into the query field. Do not add evaluation questions or expected answers as examples. Save each and check validation. Non-Valid examples are not used by the agent, so a count of nine alone does not establish completion.")]
    example_blocks += [
        _paragraph("17.16で公開した後は、画面右上で Published を選び、Setup → 自分の KQL Database → Example queries を開きます。Showing 9 items と、下記の9組の質問・KQL が保存されていることを確認します。登録数だけを Valid の証拠にせず、各例のサービス検証、先に行った直接実行の記録、19章の Agent の実回答を別々に照合します。画面内で横に隠れた KQL は横スクロールで確認し、コピーには下記の原文または同梱の kusto-examples.json を使います。",
                   "After publishing through 17.16, select Published at the top right and open Setup → your KQL Database → Example queries. Check Showing 9 items and the saved nine question/KQL pairs below. Do not treat the registered count as proof of Valid status: compare each service validation, your earlier direct-execution record and the actual Agent answers in Chapter 19 separately. Horizontally scroll any clipped KQL; copy from the complete source below or the included kusto-examples.json."),
        figures.block("pc-17-published-kql-examples"),
    ]
    for index, example in enumerate(examples, 1):
        example_blocks += [_paragraph(f"KQL 例 {index}：質問欄", f"KQL example {index}: question field"),
                           _code(example["question"], "question", canonical=True),
                           _paragraph(f"KQL 例 {index}：クエリ欄", f"KQL example {index}: query field"),
                           _code(example["query"], "KQL", canonical=True)]
    _append(chapter, 12, ("9件の KQL クエリ例を設定・検証する", "Set and validate nine KQL examples"), example_blocks)
    description_blocks = [_paragraph("通常ソースに Description の編集欄がある場合は、対応する以下の原文を設定します。入力欄が表示されない場合は無理に別の欄へ貼らず、17.15の確認記録にその状態を残します。Gen2 Ontology は、このソース説明を挿入する対象ではありません。6〜7章で作成した同じ Entity・Relationship と、13章の Entity の説明をそのまま保持します。",
                                     "Where an ordinary source exposes a Description editor, set the corresponding original text below. If no editor is shown, do not paste it into another field; record that state in 17.15. Gen2 ontology is not a destination for these source descriptions. Retain the same entities and relationships from Chapters 6–7 and the authored entity descriptions from Chapter 13.")]
    for kind, label in (("lakehouse_tables", "Lakehouse SQL"), ("kusto", "KQL Database"), ("semantic_model", "Semantic model")):
        description_blocks += [_paragraph(label + "：Description", label + ": Description"), _code(descriptions[kind], "description", canonical=True)]
    description_blocks += [_paragraph("Ontology の文脈が開けない場合は、主 Ontology 自体を開き、Entity とデータバインドが存在するか、選択したアイテムが自分の作業範囲かを確認します。No data added、SchemaUnavailable、502、definition.json 欠落などは、そのままエラー本文と日時を記録します。通常 SQL が動いても Ontology 接続の成功にはせず、追加の Ontology やダミー定義で回避しません。",
                                      "If ontology context cannot be opened, open the main ontology itself and check its entities and data bindings and whether the selected item belongs to your assigned scope. Record No data added, SchemaUnavailable, 502, missing definition.json and similar errors with timestamps. Ordinary SQL success does not prove ontology connectivity; do not work around these errors by creating another ontology or a dummy definition.")]
    _append(chapter, 14, ("ソース説明と Ontology の状態を確認する", "Check source descriptions and ontology state"), description_blocks)
    _append(chapter, 15, ("保存・公開・読み戻し・復元", "Save, publish, read back and restore"), [
        _paragraph("次の手順は、保存・公開・復元で確認する内容です。参加者の標準操作は17.16のコマンドで実施します。コマンドが公開済みの場合に、以下を読んでもう一度 Publish を押す必要はありません。", "These steps explain what saving, publication and restoration must verify. Participants use the commands in 17.16 for the standard procedure. Do not press Publish again merely because you read these steps after the command already published."),
        _steps([
            ("Agent の保存状態を確認します。編集画面を開き直し、4つの指示をそれぞれ元ファイルと照合します。全体指示は上限ちょうどなので、末尾に別の注記を追記しません。17オブジェクト・143列、KQL の10列、5つのモデルテーブルと10メジャー、主 Ontology の選択を再確認します。",
             "Check the agent's save state. Reopen the editor and compare each of the four instruction bodies with its original file. The global instruction fills the limit, so do not append notes. Recheck 17 objects and 143 SQL columns, ten KQL columns, five model tables and ten measures, and the main ontology selection."),
            ("KQL の9例がすべて Valid か確認します。SQL と Semantic model に評価問題の例を追加していないことも確認します。Draft のテストをした場合は、Draft と明記して公開版の結果と混同しません。",
             "Confirm that all nine KQL examples are Valid and that no evaluation-question examples have been added to SQL or the semantic model. Label Draft tests as Draft and keep them distinct from published-version results."),
            ("同じ Data Agent の Publish を1回実行し、完了を待ちます。失敗やタイムアウトがあれば状態を確認してから判断し、成功したことにしません。公開リンクの Agent が同じアイテムかを確認し、公開版で新しい会話を開始します。",
             "Publish the same Data Agent once and wait for completion. On failure or timeout, inspect the state before deciding what to do; do not assume success. Confirm that the published link targets the same item and start a new conversation in the published version."),
            ("公開日時・Agent URL・プロファイル名・データ確認値を記録します。UI から公開版の設定を直接読めない場合、Draft を開き直しただけで「公開定義一致」と書きません。次の表では UI 確認と公開定義の読み戻しを別々に判定します。厳密な構成再現は、公開版の指示・選択・説明・例を実際に読み戻して照合できた場合にだけ達成とします。",
             "Record the publication time, agent URL, profile name and data checks. If the UI cannot show published configuration directly, reopening Draft is not evidence of published-definition equality. Grade UI inspection and published-definition readback separately in the table below. Claim exact configuration reproduction only after actually reading back and comparing published instructions, selections, descriptions and examples."),
            ("17.2の SQL・Code Interpreter を確認してから、19章の固定問題で評価します。回答の値だけでなく実行ソース・クエリ・結果を保存します。うまくいかない問題を成功するまで送り直して採点しません。",
             "Run the SQL and Code Interpreter checks in 17.2, then evaluate the fixed questions in Chapter 19. Save the source, query and results as well as answer values. Do not grade by repeatedly sending failed questions until one succeeds."),
            ("変更が原因で悪化した場合は、変更前に保存した同じ Agent の指示・選択・例へ戻し、再保存・再公開・読み戻しを行います。SQL ビューを変更した場合は保存した定義に戻します。新しい Agent や Ontology を増やしたり、データを削除したりして復元しません。変更前の設定がない初回構築では、推測した旧版へ戻さず、問題の設定とエラーを保存して修正します。",
             "If a change causes regression, restore the instructions, selections and examples saved from this same agent, then save, republish and read back. Restore a changed SQL view from its saved definition. Do not restore by adding agents or ontologies or deleting data. On first construction without a previous configuration, preserve the failing configuration and error and repair them instead of inventing a prior version."),
        ]),
        _table([("確認項目", "Check"), ("合格条件", "Pass condition")], [
            [("データと SQL schema", "Data and SQL schema"), ("5・10・11章の値と17.7の全列が一致", "Chapter 5/10/11 data checks and every column in 17.7 match")],
            [("UI での設定確認", "UI configuration check"), ("4指示・SQL17/143・KQL10列・モデル・主 Ontology を記録", "Record four instructions, SQL17/143, KQL10 columns, model and main ontology")],
            [("KQL 例", "KQL examples"), ("9件とも同じ質問・クエリで Valid", "All nine exact question/query pairs are Valid")],
            [("公開定義の一致", "Published-definition equality"), ("読み戻した実定義の指示・選択・説明・例が一致。未取得は未確認", "Read-back instructions, selections, descriptions and examples match; unavailable readback is unverified")],
            [("Ontology の利用", "Ontology use"), ("選択状態とは別に、実際の native query と結果を確認", "Verify actual native query/results separately from selection")],
            [("回答の評価", "Answer evaluation"), ("19章の全問題・失敗・未確認を含む記録がある", "Chapter 19 records include all questions, failures and unknowns")],
        ], "構成と回答を別々に判定する完了表", "Completion table separating configuration from answers", (2.0, 4.6)),
    ])
    _append(chapter, 16, ("コマンドで設定全体を適用・公開・確認する", "Apply, publish and verify the complete configuration"), [
        _paragraph("この手順は、指示のほか、ソース説明、SQL/KQL の選択と列の説明、9件の KQL 例を同じ Agent に設定します。新しい Agent や Ontology を作るコマンドではありません。17.6のビュー、17.7の SQL 選択、17.11の KQL 選択、17.13のモデル選択と10メジャー、17.14の主 Ontology が実在し、Agent に表示されるところまでを先に行います。", "This procedure configures instructions, source descriptions, SQL/KQL selections and column descriptions, and nine KQL examples on the same agent. It does not create an agent or ontology. First complete the views in 17.6, SQL selection in 17.7, KQL selection in 17.11, model selection and ten measures in 17.13, and main ontology in 17.14, so they actually exist and appear in the agent."),
        _paragraph("Windows では PowerShell を開きます。Python 3.11以降と Azure CLI を用意します。標準の SQL schema 照合は HTTPS の Fabric SQL MCP を使うため、ODBC Driver は不要です。Python と Azure CLI は次のコマンドでインストールできます。既に入っている場合は再インストールせず、次の確認へ進みます。", "On Windows, open PowerShell. Install Python 3.11 or newer and Azure CLI. The standard schema check uses Fabric SQL MCP over HTTPS and does not require an ODBC driver. The following commands install Python and Azure CLI. If already installed, proceed to verification without reinstalling."),
        _code("winget install --exact --id Python.Python.3.11\nwinget install --exact --id Microsoft.AzureCLI", "PowerShell"),
        _paragraph("インストール後に PowerShell を開き直します。Linux を使う場合は Python 3.11以降と Azure CLI を用意し、python3 -m venv .venv で仮想環境を作ります。以下の Windows の Python パスを .venv/bin/python に、PowerShell の変数を利用中のシェルの変数構文に読み替えます。", "Reopen PowerShell after installation. On Linux, install Python 3.11 or newer and Azure CLI and create the virtual environment with python3 -m venv .venv. Substitute .venv/bin/python for the Windows Python path below and use your shell's variable syntax instead of PowerShell syntax."),
        _paragraph("ZIP の展開先に合わせて最初のパスを変更し、source フォルダーに移動します。仮想環境はこの作業専用です。認証トークンやライブ定義を ZIP、Git、配布フォルダーに保存しないよう、実行記録は次の別フォルダーに保存します。", "Change the first path to your extracted ZIP and enter its source folder. The virtual environment belongs to this task. Keep live definitions and credentials out of ZIP, Git and distribution folders by putting run records in the separate folder shown below."),
        _code('Set-Location "C:\\Workshop\\Furusato_Workshop\\source"\npy -3 --version\naz version\n$env:PYTHONDONTWRITEBYTECODE = "1"\npy -3 -B -m venv .venv\n.\\.venv\\Scripts\\python.exe -m pip install -r tools/provisioning/requirements-preview30.txt', "PowerShell"),
        _paragraph("標準経路では SQL analytics endpoint の MCP 接続が使えることを確認します。SQL 権限や MCP の利用条件が満たされない場合は、その前提を解消してから再開します。別の接続方法が必要な環境では prepare に --sql-transport odbc を追加できます。その場合だけ pyodbc、Microsoft ODBC Driver 18 for SQL Server と SQL endpoint への TCP 1433 接続が必要です。ドライバーの公式配布先は https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server です。ダミーの schema で代用しません。", "The standard route requires the SQL analytics endpoint MCP connection to be available. Resolve SQL permissions or MCP prerequisites before continuing if they are missing. Environments needing another transport can add --sql-transport odbc to prepare; only that alternative requires pyodbc, Microsoft ODBC Driver 18 for SQL Server and TCP 1433 access to the SQL endpoint. Obtain the driver from https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server. Never substitute dummy schema metadata."),
        _steps([
            ("Fabric 右上のアカウントで利用中のテナントを確認します。Workspace の URL の /groups/ に続く GUID が Workspace ID、Data Agent を開いた URL のアイテム部分の GUID が Agent ID です。フォルダーの subfolderId はこの2つの代わりに使いません。アイテム名と自分の参加者IDも照合します。", "Confirm your tenant in the Fabric account menu. The GUID after /groups/ in the workspace URL is the workspace ID; the item GUID in the opened Data Agent URL is the agent ID. The folder subfolderId is neither of these. Also match the item name and your participant ID."),
            ("ブラウザーで F12 → Network を開き、主 Ontology の画面を再読み込みします。metadata/artifacts で絞り込み、主 Ontology の ID に対する要求の Request URL を確認します。その URL の https:// からホスト名まで（末尾の /metadata/... は含めない）を RoutingOrigin に使います。ホストは実際に観測した https://<名前>.analysis.windows.net です。トークン、Cookie、Authorization、Copy as cURL の内容はコピーしません。該当要求が見つからない場合は推測したホストで実行せず、ネットワーク表示のフィルターと主 Ontology の画面を確認します。", "Open browser F12 → Network and reload the main ontology page. Filter for metadata/artifacts and inspect the Request URL for the main ontology ID. Use only the origin, from https:// through the hostname, as RoutingOrigin; omit /metadata/... and everything after it. The host must be an actually observed https://<name>.analysis.windows.net. Do not copy tokens, cookies, Authorization headers or Copy as cURL contents. If the request is absent, check the filter and ontology page instead of guessing a host."),
            ("次のプレースホルダーを自分の値に置き換えます。PrivateRoot は配布物の外にある新規フォルダーです。1回の構成変更で同じフォルダーを使い、過去の実行記録へ上書きしません。Azure CLI の初回ログインは表示された本人認証の案内に従います。期限内のログインを再利用でき、期限切れでは同じログインをやり直します。", "Replace the following placeholders with your values. PrivateRoot must be a new folder outside the distribution. Use that same folder for one configuration change without overwriting an old run. Follow the interactive instructions for your first Azure CLI sign-in. A valid login can be reused; sign in again when it expires."),
        ]),
        _code('$TenantId = "<tenant GUID>"\n$WorkspaceId = "<workspace GUID>"\n$AgentId = "<Data Agent item GUID>"\n$RoutingOrigin = "https://<observed hostname>.analysis.windows.net"\n$PrivateRoot = Join-Path $env:USERPROFILE "furusato-private\\profile-20261015-01"\naz login --tenant $TenantId --use-device-code --allow-no-subscriptions\n$ProfileArgs = @("--workspace-id", $WorkspaceId, "--agent-id", $AgentId, "--profile", "measured-contract-20261015", "--private-root", $PrivateRoot)', "PowerShell"),
        _paragraph("まず prepare を実行します。これは読み取り専用で、現状の定義、実際の SQL 列、モデルの10メジャー、Gen2 Ontology を照合し、ローカルの候補を作ります。status が prepared、cloudWrites が0、selectedSqlObjects が17、selectedSqlColumns が143であることを確認します。prepare が失敗した場合も、途中までの記録フォルダーは保持します。指摘されたソース・列・メジャーを修正し、PrivateRoot を profile-20261015-02 など新しい名前に変更して、ProfileArgs を作り直してから prepare を実行します。同じフォルダーの再利用や検査の無効化はしません。prepared まで成功した後の apply・publish・verify は、その成功した同じフォルダーを使います。", "First run prepare. It is read-only: it checks current definitions, actual SQL columns, ten model measures and Gen2 ontology, then creates a local candidate. Confirm status prepared, cloudWrites 0, selectedSqlObjects 17 and selectedSqlColumns 143. A failed prepare still leaves a partial record folder; retain it. Repair the named source, column or measure, change PrivateRoot to a new name such as profile-20261015-02, rebuild ProfileArgs, then run prepare again. Do not reuse the failed folder or disable validation. Once prepared succeeds, use that same successful folder for apply, publish and verify."),
        _code('.\\.venv\\Scripts\\python.exe -B tools/data-agent/participant_profile.py prepare @ProfileArgs --routing-origin $RoutingOrigin', "PowerShell"),
        _paragraph("PrivateRoot の prepared.json と compile-receipt.json を開き、対象、プロファイル、17オブジェクト・143列・10メジャーを確認します。inputs.json には変更前の実定義、candidate.json には適用する候補が保存されます。これらは自分の構成情報なので配布資料へ戻しません。次の apply は同じ Agent の Draft だけを変更し、公開版はまだ変えません。成功時の status は draft-matches です。", "Open prepared.json and compile-receipt.json in PrivateRoot and check the target, profile, 17 objects, 143 columns and ten measures. inputs.json holds the original live definitions and candidate.json the candidate to apply. Keep these private configuration records out of the distribution. The next apply changes only Draft on the same agent; it does not publish. Its success status is draft-matches."),
        _code('.\\.venv\\Scripts\\python.exe -B tools/data-agent/participant_profile.py apply @ProfileArgs --apply', "PowerShell"),
        _paragraph("次の publish は Draft の一致と KQL の9例が Valid であることを確認してから、1回だけ公開し、公開版を読み戻します。status が published-matches になることを確認します。verify は読み取り専用なので、後日も同じ保存先を指定して再確認できます。", "The next publish checks Draft equality and all nine KQL examples being Valid, publishes once and reads the published version back. Confirm status published-matches. verify is read-only and can be rerun later with the same record folder."),
        _code('.\\.venv\\Scripts\\python.exe -B tools/data-agent/participant_profile.py publish @ProfileArgs --apply\n.\\.venv\\Scripts\\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage published', "PowerShell"),
        _paragraph("公開版の確認で directSources=3、selectedSqlObjects=17、selectedSqlColumns=143、activeKqlExamples=9、ontologyContextPreserved=true を確認します。ontologyContextAvailabilityVerified=false と answerAccuracyVerified=false は、このコマンドが接続成功や回答精度まで保証しないことを示します。17.2と19章の実回答評価を続けます。", "In the published verification, confirm directSources=3, selectedSqlObjects=17, selectedSqlColumns=143, activeKqlExamples=9 and ontologyContextPreserved=true. ontologyContextAvailabilityVerified=false and answerAccuracyVerified=false mean this command does not establish native connectivity or answer quality. Continue to actual-answer checks in 17.2 and Chapter 19."),
        _paragraph("apply や publish の送信後にタイムアウトした場合は、同じ書き込みを繰り返しません。次の読み取り専用 verify で対象の段階を確認します。apply-intent.json / publish-intent.json は二重送信を防ぐ記録なので削除しません。別の人や画面操作で設定が変わったというエラーも、自動で上書きせず現在の変更を確認します。復元が必要なら inputs.json と apply-backup.json / publish-backup.json を保持し、17.15の同じ Agent の復元手順で指示と選択を戻します。", "If apply or publish times out after sending, do not repeat the write. Use the read-only verify below for the affected stage. Do not delete apply-intent.json or publish-intent.json: they prevent duplicate sends. If the configuration changed through another user or the UI, inspect that change rather than overwriting it automatically. For restoration, retain inputs.json and apply-backup.json / publish-backup.json and use the same-agent restoration procedure in 17.15."),
        _code('.\\.venv\\Scripts\\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage draft\n.\\.venv\\Scripts\\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage published', "PowerShell"),
    ])
    chapter.children.sort(key=lambda section: tuple(int(part) for part in section.number.split(".")))
    return {"profile": PROFILE, "sqlObjects": 17, "sqlColumns": 143, "kqlExamples": len(examples),
            "modelMeasures": len(measures), "instructionFiles": [row[0] for row in INSTRUCTION_FILES]}
