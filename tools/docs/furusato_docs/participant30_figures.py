"""Participant captions for screenshots (Japanese, English).

Keys are capture IDs from docs/assets/v3.0.0-evidence/manifest.json. Each image was reviewed for
what it shows, privacy and agreement with the steps; images that show history, failed states or
internal notes are not used.
"""

FIGURES = {
    'p30-06-entities': {
        "caption": ('Municipality の Configure 画面。キーは MunicipalityId で、静的 Property は ot_municipality にバインド済み。時系列 Property は10章でバインドするまで Unbound',
                    'Municipality Configure page: the key is MunicipalityId and the static properties are bound to ot_municipality. The time-series property stays Unbound until Chapter 10.'),
        "alt": ('Municipality の Properties 表。キー MunicipalityId、Local の各 Property の型と Data source（ot_municipality）、時系列 Property は Unbound',
                'Municipality Properties table: key MunicipalityId, Local properties with their types bound to ot_municipality, and an Unbound time-series property.'),
    },
    'p30-06-instances': {
        "caption": ('Municipality の Instances タブ。実際の行が表示され、012262 のように ID の先頭のゼロも残っている',
                    'Municipality Instances tab: actual rows from ot_municipality are listed, and leading zeros in MunicipalityId (for example 012262) are kept.'),
        "alt": ('Municipality の Instances タブ。MunicipalityId から PrefectureId までの8列で、自治体の行が並ぶ表',
                'Municipality Instances tab: a table of municipality rows with eight columns, from MunicipalityId to PrefectureId.'),
    },
    'p30-07-relationships': {
        "caption": ('Relationship を作成した後の Home。グラフの下に Visible: 10 of 10 entities | 15 of 15 relationships と表示される',
                    'Ontology Home after creating the relationships: the status under the graph reads Visible: 10 of 10 entities | 15 of 15 relationships.'),
        "alt": ('Ontology の Home。Explorer に10の Entity type、中央に Relationship で結ばれたグラフ、下部に 10 of 10 entities・15 of 15 relationships の表示',
                'Ontology Home with ten entity types in Explorer, a relationship graph, and the status 10 of 10 entities, 15 of 15 relationships.'),
    },
    'p30-09-copy-002': {
        "caption": ('Pipeline の実行の Copy data1 の Output。Succeeded で、rowsRead と rowsCopied がともに 5000（1ファイル分）',
                    'Output of Copy data1 in a Pipeline run: the activity Succeeded, and rowsRead and rowsCopied are both 5000 for one file.'),
        "alt": ('Pipeline の実行の監視画面。Copy data1 が Succeeded、Output の JSON に rowsRead 5000 と rowsCopied 5000、右に実行の詳細',
                'Pipeline run monitor: Copy data1 Succeeded; the output JSON shows rowsRead 5000 and rowsCopied 5000; run details on the right.'),
    },
    'p30-09-manual-recovery': {
        "caption": ('講師の指示で手動実行するときの Parameters。IncrementFileName にファイル名を入力し、Type・Subject・Source は空のまま',
                    "Parameters for a manual run on the instructor's instruction: enter the file name in IncrementFileName and leave Type, Subject and Source empty."),
        "alt": ('Pipeline run の Parameters 表。IncrementFileName の値は donation_events_001.csv、Type・Subject・Source の値は空欄',
                'Pipeline run Parameters: IncrementFileName is donation_events_001.csv; Type, Subject and Source are empty.'),
    },
    'p30-09-native-delivery': {
        "caption": ('ルールの History タブ。Activation details に、起動のもとになったファイルのパスと FileCreated が表示される（図は 002 と 003 の2件）',
                    'Rule History tab: Activation details list the path of each file that triggered the rule and the FileCreated type (the figure shows files 002 and 003).'),
        "alt": ('Activator のルールの History タブ。Activation count のグラフと、ファイルのパスと FileCreated が並ぶ Activation details の表',
                'Activator rule History tab: an activation-count chart and an Activation details table of file paths and FileCreated types.'),
    },
    'p30-09-source-events': {
        "caption": ('イベントソースの Live feed タブ。アップロードしたファイルごとに、FileCreated イベント（api は PutBlob）が1行表示される（図は3ファイル分）',
                    'Live feed tab of the event source: each uploaded file appears as one FileCreated event with api PutBlob (the figure shows all three files).'),
        "alt": ('イベントソースの Live feed タブ。Event details の表に3つのファイルのパス、Microsoft.Fabric.OneLake.FileCreated、PutBlob が並ぶ',
                'Event source Live feed: an Event details table with three increment file paths, type Microsoft.Fabric.OneLake.FileCreated and api PutBlob.'),
    },
    'p30-10-timeseries': {
        "caption": ('IncomingDonationAmountYen を DonationEvents の金額の列に対応させた状態。型は Timeseries<Integer>、Timestamp column は DonatedAt',
                    'Time-series binding: IncomingDonationAmountYen is mapped to the DonationEvents amount column as Timeseries<Integer>, with Timestamp column DonatedAt.'),
        "alt": ('Property の対応表。静的 Property は ot_municipality の列、IncomingDonationAmountYen は Timeseries<Integer> で、Timestamp column は DonatedAt',
                'Binding table: static properties map to ot_municipality columns; IncomingDonationAmountYen uses Timeseries<Integer> and Timestamp column DonatedAt.'),
    },
    'p30-11-executed-output': {
        "caption": ('Notebook 05 の適用の実行後の出力。ANALYTICS_MODE=applied、outputTables=29、ANALYTICS_READY の行を確認する',
                    'Output after the Notebook 05 apply run: check ANALYTICS_MODE=applied, outputTables=29 and the ANALYTICS_READY line.'),
        "alt": ('Notebook のセルの出力。schemas、sourceTables=13、outputTables=29、ANALYTICS_MODE=applied、ANALYTICS_READY の行が並ぶ',
                'Notebook cell output listing schemas, sourceTables=13, outputTables=29, ANALYTICS_MODE=applied and ANALYTICS_READY.'),
    },
    'p30-11-gold': {
        "caption": ('ops.dq_rule_results の品質チェックの結果。7つのルールすべてで期待値と実測値が一致し、Status は PASS（重複 100、増分の行数 15000）',
                    'Quality results in ops.dq_rule_results: all seven rules have matching expected and actual values and Status PASS (100 duplicates, 15000 increment rows).'),
        "alt": ('Lakehouse の ops.dq_rule_results の表。RuleName・Severity・ExpectedValue・ActualValue・Status の7行で、期待値と実測値が一致',
                'Lakehouse table ops.dq_rule_results: seven rule rows with Severity, ExpectedValue, ActualValue and Status; the values match.'),
    },
    'p30-11-schema-preview': {
        "caption": ('gold.donations の列と先頭の行。DataSource で静的データと増分を区別し、IsHighValue は 57,000円を超える寄付で true',
                    'gold.donations columns and first rows: DataSource separates static data from increments, and IsHighValue is true for donations over JPY 57,000.'),
        "alt": ('Lakehouse の Explorer で gold.donations を選んだ画面。DonationId、金額、日時、支払方法、DataSource、IsHighValue、DonorId などの列の表',
                'gold.donations in Lakehouse Explorer: a table with columns such as DonationId, amount, dates, payment method, DataSource, IsHighValue and DonorId.'),
    },
    'p30-12-metric-list': {
        "caption": ('「寄附」の Configure 画面の Metrics 欄。Semantic model のメジャーが 10 metrics と表示される（図は一部）',
                    "Metrics section of the 寄附 entity: the semantic model's measures are listed as 10 metrics (only part of the list is shown)."),
        "alt": ('「寄附」の Metrics 表。10 metrics と、Metric name・Source・Result type・Description の列に、受入増分寄附件数などのメジャー',
                'Metrics table of the 寄附 entity: 10 metrics with Metric name, Source, Result type and Description columns.'),
    },
    'p30-12-metrics': {
        "caption": ('Metric の詳細（受入増分寄附総額）。View expression で表示した元の DAX と、Applies to の「寄附」を確認する',
                    'Metric details (受入増分寄附総額): the original DAX shown with View expression, and Applies to 寄附.'),
        "alt": ('Metric の詳細画面。DAX の式 CALCULATE…RealtimeIncrement、Applies to「寄附」、Description、Synonyms 欄',
                'Metric details for 受入増分寄附総額: a DAX expression filtering RealtimeIncrement, Applies to 寄附, Description and Synonyms.'),
    },
    'p30-13-rule-list': {
        "caption": ('Explorer の Overview → Rules で開く Business rules 画面。保存した Rule と、関連する Entity type が一覧表示される（図は4つの Rule がある状態）',
                    'Business rules page (Overview → Rules in Explorer): saved rules are listed with their linked entity types (the figure shows four rules).'),
        "alt": ('Business rules の一覧。New rule ボタンと、RankTieBreak、RawObservationSemantics、StaticAndOperationalSeparation、SupplierAttribution と関連する Entity type',
                'Business rules list: a New rule button and four rules with their linked entity types; Explorer shows Overview > Rules.'),
    },
    'p30-13-rules': {
        "caption": ('Rule の編集画面。Rule name・Rule definition と、Add concept でリンクした Supplier・Gift・Donation（Rule metadata は空）',
                    'Edit rule page: Rule name, Rule definition, and Supplier, Gift and Donation linked with Add concept (Rule metadata is empty).'),
        "alt": ('Edit rule 画面。Rule name は SupplierAttribution、英文の Rule definition、Supplier・Gift・Donation のタグ、空の Rule metadata',
                'Edit rule form: name SupplierAttribution, an English definition, linked Supplier, Gift and Donation, and empty Rule metadata.'),
    },
    'p30-14-inheritance': {
        "caption": ('継承で作った Municipality。AreaName は Inherited、Details の Direct Parent は AdministrativeArea',
                    'Municipality created with inheritance: AreaName shows as Inherited, and Details list AdministrativeArea as the Direct Parent.'),
        "alt": ('Municipality の Configure 画面。Properties 表で AreaName が Inherited、ほかは Local。Details に Direct Parent AdministrativeArea、Ancestors 1',
                'Municipality Configure: AreaName Inherited, others Local; Details show Direct Parent AdministrativeArea, Ancestors 1.'),
    },
    'p30-14-shared': {
        "caption": ('親の AdministrativeArea。AreaName の Property source は Global（共有プロパティ）で、キーとバインドはまだ無い',
                    'Parent entity AdministrativeArea: AreaName has property source Global (a shared property); no entity key and no binding yet.'),
        "alt": ('AdministrativeArea の Properties 表。Define entity type key ボタンと、AreaName（Global・String・Unbound）の1行',
                'AdministrativeArea Properties: a Define entity type key button and one row, AreaName, Global, String, Unbound.'),
    },
    'p30-15-attachments': {
        "caption": ('新しい会話で4つのファイルを添付した状態。Plan のままプロンプトを入力して送信する',
                    'In a new conversation, attach the four files, keep Plan selected, then enter the prompt and send.'),
        "alt": ('Ontology agent の開始画面。候補3件、入力欄に4つのファイル、Plan/Act の切り替え、送信ボタン',
                'Ontology agent start screen with three suggestions; the input box holds four file chips, a Plan/Act toggle and Send.'),
    },
    'p30-15-additive-plan': {
        "caption": ('Plan の提案を開いた読み取り専用の画面。AI Proposal に、追加される PaymentMethod が表示される（まだ保存されていない）',
                    'The Plan proposal opens in a read-only view; the PaymentMethod entity to be added appears under AI Proposal. Nothing is saved yet.'),
        "alt": ('提案された Ontology の読み取り専用の画面。上部に承認を促す帯、Explorer の AI Proposal とキャンバスに PaymentMethod',
                'Read-only proposed ontology: a banner asks you to approve; PaymentMethod is listed under AI Proposal and on the canvas.'),
    },
    'p30-15-additive-readback': {
        "caption": ('Act で適用した後の PaymentMethod。キーは未設定で、PaymentMethodName（String）がバインドなしで追加され、説明も入っている',
                    'PaymentMethod after Act: no key is set, and one unbound String property, PaymentMethodName, has been added with a description.'),
        "alt": ('PaymentMethod の Configure タブ。キーは未設定、PaymentMethodName は Local・String・Unbound、説明が入力済み',
                'PaymentMethod Configure tab: no key; PaymentMethodName is Local, String, Unbound; the description is filled in.'),
    },
    'p30-15-attachment-grounding': {
        "caption": ('添付あり（B）の回答例。4つの資料からデータの層の違いを読み取り、配送や発送を推測していない',
                    'Answer with attachments (B): it uses all four files to keep the data layers apart and does not assume delivery or shipment.'),
        "alt": ('Ontology agent の回答。4つのファイル名、層の区別の箇条書き、不足点、DonationQualityScope の追加案と変更しない項目',
                'Agent answer: the four files, layer distinctions, missing links, a DonationQualityScope draft and unchanged items.'),
    },
    'p30-15-attachment-response-bottom': {
        "caption": ('回答の末尾。検証の結果（エラー0件・警告1件）を確認し、緑の Preview ontology ボタンで提案を開く',
                    'End of the answer: check the validation results (0 errors, 1 warning), then open the proposal with the green Preview ontology button.'),
        "alt": ('回答の後半。変更しない項目、Validation Error 0・Warning 1、結論、提案を開く緑のボタン、Plan/Act の切り替えがある入力欄',
                'Answer end: unchanged items, Validation Error 0 and Warning 1, the conclusion, a green button to open the proposal and the input box.'),
    },
    'p30-15-noattachment-preview': {
        "caption": ('添付なし（A）の提案。DataLayer（String）は追加されるが説明は空で、資料に無い層の意味は推測していない',
                    'Proposal without attachments (A): DataLayer (String) is added, its description stays empty, and undefined layers are not guessed.'),
        "alt": ('DonationQualityScope の提案画面。DataLayer は Local・String・Unbound で説明は空。右に、推測しないと述べる回答',
                'Proposed DonationQualityScope: DataLayer is Local, String, Unbound; no description; the answer says it will not guess.'),
    },
    'p30-15-preview': {
        "caption": ('添付あり（B）の提案。DataLayer に加え、承認や配送を意味しないという説明が、資料をもとに入っている',
                    'Proposal with attachments (B): besides DataLayer, it has a description, based on the files, saying that it implies no approval or delivery.'),
        "alt": ('DonationQualityScope の提案画面。DataLayer は Local・String・Unbound で説明あり。右に Error 0・Warning 1',
                'Proposed DonationQualityScope with a description; DataLayer is Local, String, Unbound; the answer shows Error 0, Warning 1.'),
    },
    'p30-16-eligibility': {
        "caption": ('Configure Graph の Choose what to project。各 Entity の Status と Source を確認する（図は全体を選んだ状態。演習では必要な範囲だけを選ぶ）',
                    "Choose what to project in Configure Graph: check each entity's Status and Source. The figure shows the whole model selected; in this lab, select only what you need."),
        "alt": ('Choose what to project の画面。Use the entire Ontology は Yes で、10の Entity がすべて選ばれて Eligible、Source は ot_* テーブル。右に関係のグラフ、左下に Continue',
                'Choose what to project: Use the entire Ontology is Yes and all ten entities are checked and Eligible, with ot_* sources; a relationship graph and a Continue button.'),
    },
    'p30-16-gql': {
        "caption": ('全体を実体化した Graph で、Prefecture にフィルターを付けて Run query した結果。矢印は自治体 → 都道府県。ノードの数字は ID とは限らないため、Table view で確かめる',
                    'Run query with a filter on Prefecture in a graph of the whole model: arrows go from municipality to prefecture. Numbers on nodes may not be IDs, so check them in Table view.'),
        "alt": ('Explore graph のクエリ画面。Municipality → Prefecture の図と、1つの都道府県に多数の自治体がつながる結果のグラフ',
                'Explore graph query: a Municipality-to-Prefecture pattern; the result links many municipalities to one prefecture.'),
    },
    'p30-17-ci-sql-output': {
        "caption": ('回答のステップを展開した Code タブ。実行された SQL と、Output に返された値（先頭は 452025 都城市、1,813件・41,151,000円）を確認する',
                    'Code tab of the expanded answer step: check the SQL that ran and the values returned in Output (first row 452025 Miyakonojo, 1,813 donations / JPY 41,151,000).'),
        "alt": ('Code タブに ot_municipality の上位10件を取る SQL、下に Output の表。先頭は 452025 都城市/宮崎県 1813 41151000',
                'Code tab with a TOP 10 SQL query on ot_municipality and an Output table led by 452025 Miyakonojo, 1813, 41151000.'),
    },
    'p30-22-import': {
        "caption": ('Import complete の画面。Preserved・Fixed automatically・Not supported の件数を確認し、Done の前に Download log でログを保存する',
                    'Import complete: check the Preserved, Fixed automatically and Not supported counts, and save the log with Download log before Done.'),
        "alt": ('Import complete のダイアログ。Preserved 98・Fixed automatically 0・Not supported 0、Entity types 10・Properties 73・Relationships 15、Download log',
                'Import complete: Preserved 98, Fixed automatically 0, Not supported 0; 10 entity types, 73 properties, 15 relationships; Download log.'),
    },
}
