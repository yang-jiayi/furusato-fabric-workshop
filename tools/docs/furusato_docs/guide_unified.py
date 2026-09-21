"""One-Agent edition content; the data/runtime baseline remains v2.7.0."""

from __future__ import annotations

import json

from .context import RuntimeContext, UNIFIED_DOCUMENT_EDITION


MIGRATION_HEADING = "16.9 旧プロファイルの保管と段階的移行"
CI_HEADING = "17.13 同じ Agent で Code Interpreter を実行する（追加演習）"


def edition_notice(builder, context: RuntimeContext) -> None:
    builder.callout(
        "note",
        f"データ・runtime の基線は v{context.version}、文書版は {UNIFIED_DOCUMENT_EDITION} です。"
        f"この版の実習では `{context.names['dataAgent']}` 1 件を使います。"
        "SQL・KQL・GQL の 3 ソースと Code Interpreter（Preview）の 1 ツールを区別します。"
        "本文の Core はこの版の標準手順、Optional は代替構築や追加分析を指します。"
        "旧プロファイルへ切り替える指示ではありません。設定の完了と応答品質の確認は別であり、"
        "第 17 章で実際の根拠と回答を評価します。",
        title="1 Agent・3 ソース・1 ツールの文書版",
    )


def agent_intro(builder, context: RuntimeContext) -> None:
    builder.body(
        f"この章では既存の主 Agent `{context.names['dataAgent']}` を確認し、"
        "同じ Lakehouse と Eventhouse の参照ヘルパーを使う統合構成を設定します。"
        f"接続する Ontology は教材用の完全な `{context.names['ontology']}` 1 件だけです。"
        "10 Entity / 72 static Property / 1 time-series Property / 15 Relationship を保持します。"
        "静的属性・金額・順位は SQL、運用観測は KQL、関係の件数・path・identity は GQL が根拠を返します。"
        "Code Interpreter は返却済み結果の分析・図・ファイルを作るツールであり、4 つ目のデータソースではありません。"
    )
    builder.callout(
        "stop",
        "既存の主 Agent は、実 item ID・接続先・選択要素・指示・Preview runtime・ツール設定が"
        "この文書版のプロファイルと既に完全一致する場合だけ、そのまま再利用します。"
        "既存一致の場合は以降を読み取り確認として行い、ソースや指示を再追加しません。"
        "旧 Core の設定が残る場合は不一致として停止し、第 16.9 節の承認された段階的移行を依頼します。"
        "名前だけの一致を理由に上書きせず、別名 Agent を追加して回避しません。"
        "主 Agent が存在しない新規環境だけ、以下の手順で正規名を 1 件作成します。",
        title="一致確認と旧 Core の更新は別の操作",
    )


def helper_preparation(builder, context: RuntimeContext) -> None:
    builder.heading("16.2.1 ソースを選ぶ前に参照ヘルパーを準備する", 3)
    builder.body(
        "agent_ref が存在すると仮定して Agent の設定を始めてはいけません。"
        "新規環境の一括構築は付録 D.2 の Notebook 04 で ENABLE_UNIFIED_DATA_AGENT=True、"
        "ENABLE_AI_REFERENCE_ARCHITECTURE=False を最終 preview 前に明示します。"
        "手動コースで既にデータを作った場合は、同じ Lakehouse の SQL analytics endpoint と同じ KQL Database に"
        "以下の共有スクリプトを適用する手順を使います。完成品に Notebook 04 を重ねて実行する手順ではありません。",
    )
    bundle = f"workshop/v{context.version}/provisioning/bundle/ai-reference"
    contract = json.loads((context.root / bundle / "contract.json").read_text("utf-8"))
    builder.table(
        ["順序", "共有ファイル", "操作と停止条件"],
        [
            [
                str(index),
                f"`{bundle}/sql/{name}`",
                "対象 SQL endpoint で順に実行。既存定義は先に照合し、完全一致だけ再利用。"
                "部分作成・不一致・管理対象外なら停止し、上書きしない。",
            ]
            for index, name in enumerate(contract["sqlDdlOrder"], 1)
        ],
        caption="SQL の schema と 6 オブジェクトを先に作る共有スクリプト",
        widths=(0.5, 3.5, 2.6),
        font_size=8.2,
    )
    builder.table(
        ["共有ファイル", "前提"],
        [
            [
                f"`{bundle}/kql/{name}.kql`",
                "第 11 章の DonationObservationSummaryForAgent を保持して定義。"
                "既存関数は完全一致だけ再利用し、CREATE を盲目的に再送しない。",
            ]
            for name in contract["kqlFunctions"]
        ],
        caption="同じ Eventhouse に追加する 3 KQL 関数",
        widths=(3.6, 3.0),
        font_size=8.2,
    )
    builder.callout(
        "gate",
        "SQL は元の dbo 列の同期と型を確認してから作成し、6 オブジェクトの定義・返却 schema・引数を照合します。"
        "KQL は MV と 3 関数の実 schema を確認します。途中成功を全体成功とせず、部分失敗の履歴を保持します。"
        "Notebook 経路では pyodbc と Microsoft ODBC Driver 18 for SQL Server を事前確認します。"
        "不足時に安全ゲートを外したり、資格情報を教材へ書いたりしません。"
        "共有スクリプトの ai-reference というフォルダー名は資産の由来であり、"
        "AIReference Agent や AIPath Ontology を作る指示ではありません。",
        title="ヘルパー作成 → native schema 確認 → Agent の discovery",
    )


def source_selection(builder, context: RuntimeContext) -> None:
    builder.heading("16.2 Data Agent と共有ソースを確認する", 2)
    helper_preparation(builder, context)
    builder.heading("16.2.2 主 Agent に 3 ソースを接続する", 3)
    builder.bullets(
        (
            f"対象 Folder・PID と `{context.names['dataAgent']}` の実 ID を確認します。"
            "既存なら一致確認または承認された移行を先に完了します。未作成の場合だけ"
            "［新規］→［Data agent］を選び、Create data agent ダイアログへ正規名を入力して 1 件作成します。",
            "［Runtime］で Preview を選び、［Add Data］→［Data source］から対象 Lakehouse・"
            "KQL Database・教材用 full Ontology を追加します。共有データを複製しません。",
            "ヘルパー作成後に Explorer の metadata を更新し、実際に discovery された名前・type・path と"
            "実 ID を照合して、下表の全要素を選択します。公開 element ID を推測した UUID で代用しません。",
            "［Tools］で Code Interpreter を有効にし、保存後の有効状態も確認します。"
            "ツールの有効化と、実際のツール実行の証明は分けます（第 17.13 節）。",
        ),
        numbered=True,
    )
    builder.table(
        ["ソース", "必ず選択する要素", "直接選択する個数", "選択しないもの"],
        [
            [
                "Lakehouse SQL",
                "11 dbo.ot_* テーブル + agent_ref.MunicipalityStatic view + "
                "agent_ref.MunicipalityById / agent_ref.DonationTraceById TVF",
                "14（11 テーブル + 1 view + 2 関数）",
                "stg_*・監査表・DonationAttributes / DonationById / GiftCatalogSuppliers の直接選択",
            ],
            [
                "Eventhouse KQL",
                "DonationObservationSummaryForAgent + AgentRawObservationTotals + "
                "AgentFileRunSummary + AgentMunicipalityLeaders",
                "4（1 MV + 3 関数）",
                "raw DonationEvents・EventID・未承認関数",
            ],
            [
                "Ontology GQL",
                f"`{context.names['ontology']}` の全 10 Entity Type",
                "10 Entity（完全モデル）",
                "別の connectedOntology・AIPath",
            ],
        ],
        caption="統合 Agent の直接選択と物理オブジェクト数を区別する",
        widths=(1.0, 2.9, 1.3, 1.8),
        font_size=8.2,
    )
    builder.callout(
        "gate",
        "物理 Lakehouse の ot_* テーブル数は 11 のままで、SQL endpoint の view / TVF を含む直接選択が 14 です。"
        "KQL の直接選択は MV 1 + 関数 3、Ontology は 10 Entity です。列・引数・返却列をこの個数へ混ぜません。"
        "関数は 3 件とも必須です。Functions grouping の表示だけで判定せず、実際の選択済み leaf を確認します。"
        "metadata の型が空なら native schema の証跡を別に保存し、架空の型・children・ID を補いません。"
        "raw を非選択のまま保持し、集約から EventID の一意件数や重複排除を証明しません。",
        title="3 ソースの選択ゲート（14 / 4 / 10）",
    )
    builder.body("Tables の raw DonationEvents のチェックは必ず外します。")


def runtime_settings(builder, context: RuntimeContext) -> None:
    builder.body(
        "Core 記録は Preview runtime で実施しなければなりません。"
        "Standard runtime は比較専用であり、Core の合否には使えません。"
        "Standard でしか通らなかった問いは Core としては不合格です。"
    )
    builder.table(
        ["設定", "この文書版の値", "確認"],
        [
            ["Runtime", "Preview", "Draft と Published を別々に確認。Standard の比較は主評価へ混ぜない。"],
            [
                "Code Interpreter",
                "有効（codeInterpreterEnabled = true）",
                "同じ主 Agent の Tools で有効化を確認。実行の有無は native 実行詳細で確認。",
            ],
            ["Data Agent", context.names["dataAgent"], "実 item ID が同じ主 Agent であること。"],
            ["connectedOntology", context.names["ontology"], "教材用 full Ontology 1 件だけ。"],
        ],
        caption="統合プロファイルの runtime とツール",
        widths=(1.4, 2.3, 3.0),
    )
    builder.callout(
        "stop",
        "キーの欠落だけで Code Interpreter が有効だと推測しません。保存後の Tools と実際の設定を確認し、"
        "codeInterpreterEnabled=true と一致しなければ停止します。Preview やツールが利用できない場合は"
        "ブロックとして記録し、別 Agent の作成や Standard の成功でこの構成の確認を代用しません。"
        "元の 10 問の必要な SQL/KQL/GQL は省略せず、Python の結果へ置き換えません。",
        title="有効なツールと実行済みの根拠は別",
    )


def migration(builder, context: RuntimeContext) -> None:
    builder.heading(MIGRATION_HEADING, 2)
    builder.body(
        "旧 Core（Code Interpreter 無効）、AIReference、CI 比較用の独立プロファイルは履歴用です。"
        "この文書版の参加者は作成も切替も行いません。AIPath は legacy optional 資産であり、"
        "接続先・Notebook 02 の対象・事前作成の要件にはしません。"
    )
    builder.callout(
        "stop",
        "既存の旧 Core を更新する場合は、管理者が対象の主 Agent の実 ID と承認範囲を固定し、"
        "元の定義・Published 状態・非公開の証跡を保存してから Draft だけを段階的に変更します。"
        "Published は検証が完了するまで旧版を保持します。Draft の全選択・指示・実クエリ・"
        "元の 10 問／84 条件・CI 追加演習を確認して承認した後だけ Publish します。"
        "公開後の一致確認とスモークテストに失敗した場合は共有・削除へ進みません。",
        title="同じ主 Agent の Draft で検証してから公開",
    )
    builder.body(
        "移行後の整理は管理者の別工程です。削除が明示的に承認された旧 Agent 2 件だけを実 ID で照合して対象にします。"
        "同名検索や接尾辞だけで削除せず、主 Agent、共有 Lakehouse / Eventhouse、完全な教材 Ontology、"
        "過去に保持した Eventhouse、履歴・ファイル・共有データは残します。"
        "Notebook 04 は不一致の旧 Core を自動移行・上書きする道具ではありません。",
    )


def source_rules(builder) -> None:
    builder.callout(
        "stop",
        "DonationTraceById の金額は DonationId × Supplier 登録の各行で繰り返されるため加算しません。"
        "SQL が返した全役割の ID と名前・全 Supplier を保持し、登録を発送・製造・履行の実績に読み替えません。"
        "DonationSelectedGift は選択を表し、返礼品を受領・配送済みとは断定しません。"
        "KQL の実 MunicipalityID を literal ID として SQL と GQL に渡し、"
        "3 ソースの実結果が揃うまで照合完了と宣言しません。Graph の件数・path・identity を Python で作りません。",
        title="SQL・KQL・GQL の所有する根拠を保持する",
    )
    builder.body(
        "返礼品は、見出し・箇条書き・要約でも「選択した返礼品」と表現します。"
        "後から注意書きを付けても、「受け取った」「配送済み」と断定した箇所の根拠にはなりません。"
        "これは返礼品の履行の境界であり、受入自治体が寄付金を受領するという指標とは区別します。",
    )
    builder.body(
        "MunicipalityById の 22 列と DonationTraceById の 30 列は、元の列名・値を保ったまま返します。"
        "MunicipalityDerivedNationwideCountRank は導出した件数順位であり、"
        "存在しない MunicipalityStoredNationwideCountRank へ改名しません。"
        "金額順位の MunicipalityStoredNationwideAmountRank とも区別します。"
        "追加の日時・属性が必要な場合は、その属性を返す承認済み SQL を別に実行して出典を示し、"
        "Ontology の JSON にだけある値を SQL の出力として記しません。",
    )
    builder.body(
        "KQL ヘルパーはそれぞれ 14 / 17 / 15 列の返却契約を保ち、"
        "HasMatches や EventIdentityFieldExists などの列を付け加えません。"
        "WindowIsValid は返った値を確認し、false の行を除外して異常を隠しません。"
        "SourceSystem・SourceObject・Scope・単位・RawDuplicateCaveat は実際の返却値を保持します。"
        "説明用の訳語は元の列名に添えられますが、作成したラベルをスキーマ検査や別ソースの実行証拠として扱いません。",
    )
    builder.body(
        "静的 2025 UTC はデータセットのラベルであり、JST 暦年の追加フィルターではありません。"
        "SQL は寄付 0 件を含む母集団を保持し、KQL は raw 観測と file/run provenance を保持します。"
        "ISO UTC の時刻文字列、SourceFile・WorkshopRunId・ParticipantAlias と実時刻を出力に残します。"
        "有効な範囲への照会が成功して返した空結果と、入力欠落・失敗・未実行は区別します。"
        "WindowIsValid=false や失敗した照会は確認済み 0 件ではありません。"
        "静的/raw の合算、EventID の推測 dedup、所得・税額の推論をしません。",
    )
    builder.body(
        "最終回答にも Source・Scope（DatasetScope を含む）・Metric・Unit と粒度を残します。"
        "順位には RankScope が全国か都道府県内かを明記し、後者は対象都道府県も示します。"
        "Source は static / operational という区別だけで済ませず、各結果を所有する SQL / KQL / GQL と"
        "実際に照会したソース・オブジェクト名をすべて記します。未実行・失敗はその状態を示し、"
        "照会したと装ったり、根拠なしに取得・分析完了と書いたりしません。",
    )
    builder.callout(
        "note",
        "AgentRawObservationTotals・AgentFileRunSummary・AgentMunicipalityLeaders は集約済みです。"
        "leaders は MunicipalityID ごとに一意で、同じ自治体が件数・金額の首位なら 1 行の両フラグを保持します。"
        "配布 kusto-fewshots.json の helper wrapper を使い、StartUtc / EndUtc は質問の実際の境界"
        "（下限以上・上限未満）に合わせます。期間指定に全期間用の datetime(null) を流用しません。"
        "wrapper の ISO-8601 UTC（T / Z）書式と null の扱い、返却された Scope・provenance・"
        "WindowIsValid・leader フラグを保持します。ヘルパー出力に追加の summarize・dedup・"
        "Boolean metadata の集約をかけません。承認済み MV DonationObservationSummaryForAgent を"
        "直接読む custom 集約では summarize を使えます。ヘルパーの再集計禁止と混同しません。",
        title="集約済み KQL ヘルパーは配布 wrapper で使う",
    )


def native_evidence(builder) -> None:
    builder.heading("17.12.2 SQL・KQL・GQL とツールの証跡を分ける", 3)
    builder.body(
        "元の判定条件をそのまま使います。T01 は静的 2025 の期間の意味を保持します。"
        "T03 は確認質問の分岐も許容し、選択した分岐に適用されない条件だけを NA にします。"
        "T04 の `Relationship:` / `Traversal:` の literal 行と、T06 の `All timestamps are UTC.` は"
        "翻訳・省略で置き換えません。CI の成功で該当条件を NA にしません。"
    )
    builder.table(
        ["根拠の所有者", "同じ実行から保存するもの", "代用できないもの"],
        [
            ["SQL", "実 query、全返却行、DatasetScope・rank scope・ID/name・単位", "Python の再計算や Graph だけの属性"],
            ["KQL", "実 query、全返却行、ISO UTC・file/run provenance・有効範囲・raw 留保", "Top N の抜粋による全件総計、架空の一意 EventID"],
            ["GQL", "実 query、関係の件数・向き・instance path・identity", "Python のノード数や合成 path、SQL の結合だけ"],
            ["Code Interpreter", "実 tool 実行、native の実行済みセルの Python・入力・stdout/stderr、図・生成ファイル", "SQL/KQL/GQL の必須根拠や元の 10 問の採点"],
        ],
        caption="根拠 3 種と CI の追加成果物",
        widths=(1.1, 3.2, 2.4),
    )
    builder.callout(
        "gate",
        "［実行詳細］を開き、同じ質問の UI Export で analysis steps・全 query・全返却結果・最終回答を保存します。"
        "実際の同一 run の Agent item ID・Draft / Published・runtime・conversation ID と "
        "request / activity ID（提供されるもの）・時刻を突き合わせます。"
        "別会話の export、クライアントの採番、別実行の補助 query を native 証跡へ混ぜません。"
        "対応する実行 ID を確認できない場合は未確認とし、図や最終回答だけで採点を補完しません。",
        title="UI Export は実際の同一 run に結び付ける",
    )
    builder.body(
        "CI の実行証跡は native の実行済みセルにある Python・実入力・stdout / stderr です。"
        "export された .py は、「実行コード」などのラベルがあっても、後から再構成されたコードや"
        "コメントだけの workflow 要約の場合があります。.py を native 実行証跡の代用にしません。"
        "再現用コードは「再現用コード」と明示し、実行済みセルの原本と分けます。",
    )
    builder.body(
        "証跡用の画面写真は、実際の Fabric Web UI を操作して取得し、対象 Agent・質問・実行を記録します。"
        "画面を HTML で再構成したり、画像内のラベルを差し替えたり、保存ログの表示を UI の実行証跡として"
        "使ったりしません。CI の図ファイルは分析成果物として区別します。"
        "配布ガイドの画像や自分の画面写真だけでは、今回の全 query・返却結果・ツール実行を証明できません。"
        "同一 run の元の native 証跡も保持します。"
    )
    builder.body(
        "T10 ではプラットフォームのブロックが残る可能性があります。"
        "汎用ブロックは文脈に即した拒否と安全な代替の代用ではなく、元の条件を満たさないまま合格にしません。",
    )


def ci_exercise(builder, context: RuntimeContext) -> None:
    builder.heading(CI_HEADING, 2)
    builder.body(
        f"元の 10 問は質問文も 84 条件も変えずに記録します。その後、同じ `{context.names['dataAgent']}` の"
        "新しい会話で以下の追加演習を行います。CI の図が作れたことを元の 10 問の合格へ加点しません。"
        "Code Interpreter が有効なだけ、回答に Python が載っただけ、report_specs の図の指定があるだけでは"
        "ツール実行を確認したことになりません。",
    )
    builder.callout(
        "note",
        "静的 2025 UTC スナップショットについて、まず SQL で寄付 0 件も含む全都道府県の ID・名前・"
        "受入寄付件数・受入寄付金額を都道府県ごとの集約として返してください。在住側の指標と区別します。"
        "返却結果が全母集団を覆い、"
        "切り捨てがないことを確認してから、その実結果だけを Code Interpreter の入力にして、"
        "件数と金額の散布図を作成し、入力 CSV と図ファイルを出力してください。"
        "全件を取得できない場合は停止し、抜粋から全国分布を作らないでください。"
        "Source・DatasetScope・grain・unit を保持し、所得・税額は推測しないでください。",
        title="CI 演習 1：SQL の全母集団から分布を描く",
    )
    builder.callout(
        "note",
        "2026-08-01 00:00:00 UTC 以上、2026-09-01 00:00:00 UTC 未満の運用観測を、"
        "承認済み KQL の AgentRawObservationTotals と AgentFileRunSummary で取得してください。"
        "成功した返却結果だけを Code Interpreter に渡し、SourceFile × WorkshopRunId × ParticipantAlias の"
        "観測件数と金額を別々の棒グラフにして、元の返却データと図ファイルを出力してください。"
        "ISO UTC の実時刻と provenance を保持し、スカラー総計と内訳を照合してください。"
        "静的データを加えず、EventID の一意件数や dedup 値を作らないでください。",
        title="CI 演習 2：KQL の file/run 内訳を可視化する",
    )
    builder.bullets(
        (
            "実行前に実 Agent ID・Draft / Published・Runtime=Preview・Tools の Code Interpreter を確認します。"
            "各演習は元の 10 問とは別の fresh conversation にします。",
            "CI の開始前に、同じターンで必要な SQL / KQL / GQL の照会をすべて成功させ、"
            "［実行詳細］で全返却結果を開きます。"
            "対象範囲、返却件数、全件/上限つきの別、切り捨て、ゼロの意味、単位を確認します。"
            "図に必要な範囲を全件取得できなければ止めます。bounded な結果はその範囲の分析にしか使いません。"
            "今回のターンへ渡すファイル・行・列が揃い、実際に読めることも確認します。",
            "Code Interpreter の tool step を開き、native の実行済みセルで実行した Python と実際の入力を読みます。"
            "入力の列名・行数・集計値を直前の返却結果へ結び付け、人工データ・期待値・隠れたファイルでの補完がないかを確認します。"
            "GQL の count/path を Python へ置き換えていないことも確認します。",
            "日本語グリフが読めない図になる場合があります。描画前にインストール済みの CJK 対応フォントを確認して指定します。"
            "使えるフォントがなければ安定した ID をラベルにし、CSV に ID と元の日本語名の対応を残します。"
            "全点・全行を保持し、英語名を作ったり、読めない名前のデータを黙って省いたりしません。"
            "描画後も可読性とデータの網羅を確認し、すべての図が成功するとは扱いません。",
            "stdout / stderr、図、実際に生成された CSV / 画像ファイルを開いて確認します。"
            "日本語ラベル・軸・JPY と件数の単位・UTC・出典・file/run の対応を点検します。"
            "失敗と未実行を区別し、欠落ラベルやダウンロード不能を成功として隠しません。",
            "同一 run の tool 記録・入力・Python・出力を非公開で保存します。"
            "修正のため設定を変えた場合は、元の 10 問をすべて再評価し、CI 演習も別枠でやり直します。",
        ),
        numbered=True,
    )
    builder.body(
        "成果物はソース結果の CSV / JSON と PNG を優先し、依頼されていない Excel / Word などの "
        "Office export は追加しません。JSON export では必要に応じて NumPy / Pandas scalar を "
        "Python-native の int / float / bool / str へ変換し、欠損値は None / null として区別します。"
        "変換で行・列を落としたり、欠損値を 0 に置き換えたりしません。",
    )
    builder.figure(
        builder.carrier.screenshot("17-40"),
        caption="Code Interpreter の実行詳細の操作例。実 Fabric UI の生成グラフと Succeeded の表示を確認する。",
        alt_text="Steps completed 画面の操作例。ファイル・実行・参加者別の観測件数グラフと Succeeded の表示。",
        max_height_cm=9.6,
    )
    builder.callout(
        "note",
        "ファイルの作成や Succeeded の表示は、各ファイルの表示・ダウンロード成功とは別です。"
        "リンクの無効化や Can't load file があれば、実行結果とファイル取得の失敗を分けて記録します。"
        "回答で提供すると案内した必須ファイルは 1 件ずつ実際にダウンロードして内容を開き、"
        "ファイル名やリンクだけで取得成功と判定しません。HTTP 400 に MIP の supported-file-type 制限が"
        "示された場合は失敗を記録し、保護の無効化や、拒否されたファイルの再包装・拡張子変更で回避しません。"
        "画像だけで、同一 run の全入力・コード・出力が検証済みだとは扱いません。",
        title="実行成功とファイル取得成功を分ける",
    )
    builder.callout(
        "stop",
        "CI は、取得済みの bounded 結果または全 scope の集約を分析するためだけに使います。"
        "データ取得の失敗・未選択ソース・GQL の未実行を Python で隠しません。"
        "ソース照会が成功していても、今回の CI に渡す入力が欠けていれば分析成功ではありません。"
        "有効な照会が成功して返した空結果はそのまま記録し、描く点がないことを明示します。"
        "確認済みの 0 件は保持しますが、失敗・欠落を 0 として埋めません。"
        "有効化できない、または実際の入力・実行・出力を確認できない場合は CI 演習をブロックとして記録します。",
        title="CI は根拠を置き換えない",
    )


def confirmation_workflow(builder) -> None:
    builder.heading("17.14 同じ Agent で確認してから照会する", 2)
    builder.body(
        "曖昧な表現やデータで答えられない意味を、寄付指標へ自動で読み替えません。"
        "人物の富裕・貧困・税額の順位は、言い方が明確でも確認が必要です。"
        "同じ主 Agent が限界を説明し、対象 Entity・地域と役割・期間・指標・順位範囲を明示した"
        "寄付だけの質問を 1 問提案して、同意を待つことを確認します。"
        "元の 10 問と CI 演習とは別の対話確認です。分岐ごとに新しい会話で始め、"
        "その分岐の提案・承諾・訂正・中止は同じ会話で続けます。"
    )
    builder.callout(
        "gate",
        "開始前に、割り当てられた Workspace / Folder、主 Agent の実 ID、Draft / Published、"
        "Runtime=Preview と第 16 章の設定を確認します。"
        "以前の会話の承諾、別 Agent の応答、配布画像を今回の同意や実行の証跡として流用しません。"
        "対象や設定が変わった場合は新しい会話で開始し、確認が必要な問いは提案からやり直します。",
        title="対象 Agent と会話を確認する",
    )
    builder.callout(
        "note",
        "以下は対話の説明例であり、検証済みの native 応答や実行結果ではありません。"
        "利用者の「東京」や「お金持ち」を無断で在住地や寄付金額に決めません。",
        title="対話の説明例（実行結果ではない）",
    )
    builder.bullets(
        (
            "利用者：「東京のお金持ちはだれ？」",
            "Agent：「この合成データから所得・資産や『お金持ち』は判断できません。"
            "代わりに『東京都在住の合成寄付者について、Static 2025 UTC snapshot 全体の"
            "累計寄付金額（JPY）を寄付者ごとに集計し、東京都在住の寄付者内で金額の降順に"
            "順位を付けてください』という質問でよいですか。地域は寄付者の在住地であり、"
            "受入自治体ではありません。同意されるまで SQL・KQL・GQL・CI は実行せずに待ちます。」",
            "利用者：「はい、その寄付金額ランキングをお願いします。」",
            "承諾後の確認対象：同意した問いだけを Lakehouse SQL で照会します。"
            "成功した実結果の DonorId・名前・累計寄付金額（JPY）・寄付金額順位を示し、"
            "Source・Scope・Metric・Unit・RankScope を残します。Scope は Static 2025 UTC snapshot 全体、"
            "RankScope は東京都在住の合成寄付者内です。JST 暦年の追加フィルターにはしません。"
            "この問いに不要な KQL・GQL・CI は実行しません。照会成功は保証せず、失敗・欠落を 0 や推測値で補いません。",
        ),
        numbered=True,
    )
    builder.table(
        ["対話の分岐", "応答と実行詳細で確認すること"],
        [
            [
                "確認を待つ間",
                "限界の説明と提案は 1 問だけ。Entity・地域の役割（在住／受入）・期間・指標・"
                "順位範囲が揃い、承諾前の SQL・KQL・GQL・CI がない。",
            ],
            [
                "「はい」／yes",
                "この会話で最後に提示された未処理の提案だけを承諾する。"
                "提案がない、取消済み、または何への同意か特定できない場合は照会せず確認し直す。"
                "実 query の対象と出力ラベルが承諾した問いに一致する。",
            ],
            [
                "条件の訂正",
                "例：「東京は受入側。自治体ごとにしてください」。"
                "「はい」が付いていても、範囲の訂正は同意ではない。旧提案を置き換え、"
                "対象と順位範囲を東京都の受入自治体内へ直した 1 問を再提示する。"
                "期間・指標も明記し、新しい提案への同意を待つ。"
                "訂正時には SQL・KQL・GQL・CI を実行しない。",
            ],
            [
                "「いいえ」／no／キャンセル／cancel",
                "未処理の提案を取り消して停止する。SQL・KQL・GQL・CI を実行せず、"
                "後の「はい」で取り消した提案を復活させない。",
            ],
            [
                "無関係な明確な新しい質問",
                "新しい質問は旧提案への承諾ではない。未処理の提案を取り消し、"
                "不要な再確認を挟まず新しい質問だけを通常どおり扱う。"
                "旧提案の照会を一緒に実行しない。後の曖昧な「はい」を旧提案へ自動で結び付けない。",
            ],
            [
                "初めから明確な通常質問",
                "例：「全国の Static 2025 UTC snapshot 全体の寄付件数と合計金額を教えてください」。"
                "不要な再確認を挟まず、必要な承認済みソースでその問いを扱う。",
            ],
        ],
        caption="確認・承諾・訂正・中止を混同しないための対話確認",
        widths=(1.6, 5.0),
        font_size=8.5,
    )
    builder.callout(
        "stop",
        "同意があっても、所得・資産・税額の推論は拒否のままです。"
        "納税額は寄付金額ではなく、寄付データから納税順位を求めません。"
        "承諾されるのは提案した寄付指標の照会だけで、元の人物評価ではありません。"
        "結果を「お金持ち」「貧乏」の順位として表示しません。"
        "サービスの汎用拒否やブロックが残る場合があり、言い換えや別経路で回避しません。",
        title="同意しても人物の富裕・貧困は推論しない",
    )
    builder.callout(
        "note",
        "標準の Fabric UI では指示に基づく対話であり、強制された状態機械ではありません。"
        "確認を待つことやツールを実行しないことが、製品によって保証されるとは扱いません。"
        "「待っています」という本文だけで判定せず、第 17.12.2 節の同一会話・各ターンの実行詳細で"
        "承諾前・訂正時・中止時に query や tool 実行がないことを確認します。"
        "証跡が取得できない部分は未確認とし、合格にしません。",
        title="指示上の手順と実際の実行を区別する",
    )
    builder.callout(
        "gate",
        "指示や設定を変更した場合は、元の 10 問／84 条件を変えずに全問を再評価し、"
        "両方の CI 演習も元の質問のまま再実施します。"
        "この対話確認で元の条件や CI 演習を置き換えたり、免除したりしません。",
        title="追加の対話確認でも元の回帰確認を省略しない",
    )


def notebook_mode(builder) -> None:
    builder.callout(
        "note",
        "この文書版は最終 preview 前に ENABLE_UNIFIED_DATA_AGENT=True、"
        "ENABLE_AI_REFERENCE_ARCHITECTURE=False を明示します。両方 True は禁止です。"
        "runtime の ENABLE_UNIFIED_DATA_AGENT の既定 False は旧呼び出し元との互換性のためで、"
        "この文書版のセットアップ値とは異なります。unified-agent の固定済みプロファイルと共有 SQL/KQL を先に確認し、"
        "ファイル不足や hash 不一致なら停止します。旧 Core GLOBAL へフォールバックしません。"
        "作成するのは主 Agent 1 件と教材用 full Ontology です。AIPath は作りません。",
        title="統合モードを選んでから計画ハッシュを承認する",
    )
    builder.callout(
        "stop",
        "preview / PLAN_SHA256 / CONFIRMED_PLAN_SHA256 / EXCLUSIVE_CREATE_WINDOW_CONFIRMED の"
        "既存ゲートは保持します。フラグを変えたら preview を取り直します。"
        "途中で失敗しても自動 resume・自動 rollback とみなさず、既存ジョブ・checkpoint・作成済み実 ID を確認します。"
        "古い計画を使った再送、同時作成、不一致の既存主 Agent の上書きはしません。"
        "旧 Core の移行は第 16.9 節の別承認工程です。",
        title="統合モードでも排他・hash・no-auto-resume を保持",
    )


def diagnostics_boundary(builder) -> None:
    builder.callout(
        "note",
        "第 17 章の参加者実習は UI と UI Export を使います。"
        "必要な実行詳細を取得できない場合は、対象 Agent・質問・時刻と取得できなかった範囲を記録し、"
        "ファシリテーターへ確認します。別の会話・別の照会や回答本文だけで不足分を補いません。"
        "native 証跡が揃わない範囲は保留し、取得できた記録は非公開で保持します。",
        title="実行証跡を取得できない場合",
    )
