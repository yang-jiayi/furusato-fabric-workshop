# 精度の校正と資料の校正手順 / Calibration and proofreading

同じ Workshop に Ontology 1件・Data Agent 1件を使用します。構成・データ・回答・実行証跡を別々に確認してから、共有原稿から Word と HTML を生成します。今回の実測結果は [作業・評価レポート](README.md) に記録します。以下は再利用する手順であり、実行済みという報告ではありません。

Use one Ontology and one Data Agent for the workshop. Verify configuration, data, answers and execution evidence separately, then generate Word and HTML from shared content. The [work and evaluation report](README.md) records this deployment's actual outcomes. The following is a reusable procedure, not a claim that every step has run.

[実結果の Word / Actual-results Word](furusato-ontology-v2-evaluation-20261015.docx) · [実結果の HTML / Actual-results HTML](furusato-ontology-v2-evaluation-20261015.html) · [実評価の集計 / Actual evaluation aggregate](result-20261015.json)

## 1. 構成とデータを固定する / Freeze configuration and data

1. 導入先と Item の範囲を確認し、対象外を保護します。削除対象、現在の18 Items、管理下の子 Item、回復可能な削除済み Item を区別します。認証情報と実環境 ID は Git の外に保管します。
2. 3つの通常ソース（Lakehouse、KQL Database、Semantic Model）と、別の Ontology 登録を確認します。現在の Gen2 定義では Ontology が通常の datasource 一覧に含まれないため、「一覧が3件」を接続欠落と決めつけません。登録、schema、選択、生成された文脈をそれぞれ読み戻します。
3. Lakehouse の6ビュー・6参照表・5品質表、合計17オブジェクト・143列を実 metadata と照合します。KQL の集計ビューの10列に EventID はありません。既存の Semantic Model 10メジャーの式と、表示対象の金額列を照合します。
4. 静的80,000件・1,344,099,000円、生観測15,000行・253,886,000円、受入14,900件・252,058,000円、隔離100件、Gold94,900件・1,596,157,000円を異なる母集団として照合します。生観測の重複は取り除きません。Gold は同じ Ready run と generation を前後で確認します。
5. 自動配送はイベント、activation、元の Pipeline の新規実行、Copy の5,000行、KQL の増加をファイルごとに結び付けます。全3ファイルの確認後は Activator を停止し、評価中に業務データを変えません。完了済み Notebook や取込を再実行して失敗履歴を置き換えません。
6. 公開 Agent 定義、ソース定義・選択、指示、例、元CSV、業務値をハッシュで固定します。後続修正は別 revision とし、元の失敗と実行結果を保持します。

1. Confirm the deployment and Item scope, preserving unrelated resources. Distinguish deletion targets, the current 18 Items, managed children and recoverable deleted Items. Keep credentials and live identifiers outside Git.
2. Verify three ordinary sources (Lakehouse, KQL database and semantic model) plus the separate Ontology registration. The current Gen2 definition does not list the Ontology as an ordinary datasource; a list of three alone does not prove a missing connection. Read back registration, schema, selection and generated context separately.
3. Reconcile six SQL views, six reference tables and five quality tables: 17 objects and 143 columns. The KQL summary's ten columns do not include EventID. Verify all ten existing semantic-model measure expressions and the visible amount column.
4. Reconcile separate populations: static 80,000 / JPY 1,344,099,000; raw observations 15,000 / JPY 253,886,000; accepted 14,900 / JPY 252,058,000; quarantined 100; Gold 94,900 / JPY 1,596,157,000. Preserve raw duplicates. Check the same Ready run and generation before and after Gold queries.
5. For every automatically delivered file, correlate the event, activation, new execution of the original Pipeline, 5,000 copied rows and KQL increase. Stop Activator after all three files and keep business data fixed during evaluation. Do not replay completed Notebooks or ingestion to replace failure history.
6. Hash the published Agent, source definitions and selections, instructions, examples, source CSVs and business values. Store later changes as separate revisions and retain original failures and results.

## 2. 接続の合否と回答の合否を分ける / Separate connection and answer acceptance

Gen2 Ontology の TMDL が読み戻せても、Data Agent の consumer が使えるとは限りません。`SchemaUnavailable`、空の文脈、`definition.json` 欠落のエラーは実状態として保存します。古い形式のダミーファイルを追加したり、2件目の Ontology を作ったりして成功扱いしません。接続の再登録を検証する場合は、事前に同じ Agent の全定義を保存し、失敗時はその定義を厳密に復元します。

A readable Gen2 TMDL definition does not prove that the Data Agent consumer can use it. Preserve `SchemaUnavailable`, empty context and missing-`definition.json` errors as observed. Do not add a dummy legacy file or another Ontology to claim success. A bounded registration test requires an exact full-Agent backup and exact restoration if it fails.

正常な利用資格は、同じ Ontology の利用可能な文脈と、実際のバインド先の照会・返却結果で確認します。通常の SQL 回答だけでは Ontology を利用した証明になりません。接続障害を保持した診断評価を行う場合は、そのモードを事前に固定し、利用資格の合格や製品全体の Bug 解消とは表示しません。

Qualify the route through available context from the same Ontology plus actual queries and returned results from its bound source. An ordinary SQL answer alone does not prove Ontology use. If running diagnostic evaluation while retaining a connector failure, declare that mode before collection; it is neither qualification acceptance nor proof of a product-wide bug fix.

## 3. 評価計画を回答取得前に固定する / Register the evaluation before collection

| フェーズ / Phase | 質問 / Questions | 条件 / Conditions | 取扱い / Treatment |
|---|---:|---:|---|
| 接続資格 / Qualification | 2 | 5 | ソース利用資格を独立に判定 / Separate source qualification |
| 初期全体 / Baseline | 51 | 296 | 元10問×3回、回帰19問、未使用2問 / Original ten repeated three times, 19 regression and two unused |
| 限定修正 / Targeted | 最大8 / Up to 8 | 事前固定 / Registered beforehand | 最大2回、各4問 / At most two waves of four |
| 最終全体 / Final | 51 | 296 | 同じ元・回帰、別の未使用2問 / Same original and regression, two different unused |

1. 質問・rubric・適用条件・繰返し・タイムアウト・会話の初期化・未取得の扱いを凍結します。HTTP 300秒、capture全体900秒、定義取得全体600秒という異なる制限を混同しません。
2. 1問ごとに新しい会話へ1回だけ送信します。送信済み、結果不明、取得途中で停止した枠は再送しません。既存 Response の読み取りによる回収と、新しい質問の送信を分けます。
3. 未送信、結果不明、途中エラー、ブロック、証跡不足を登録分母に残します。記録の状態、HTTP の成否、Response の完了、内部 query の成功を別々に集計します。
4. 修正用と未使用の問題を分け、未使用問題の結果をチューニングに使いません。質問文・期待解答・評価条件を指示や例へ埋め込みません。ソース自身のスキーマ、業務定義、既存 DAX は照合に使えます。
5. 内容を PASS／FAIL／UNCLEAR／NA で採点し、native 実行の判定を別に残します。NA は事前に認めた確認質問の分岐に限ります。UNCLEAR を成功へ変えたり、分母から外したりしません。

1. Freeze questions, rubrics, applicability, repetitions, timeouts, conversation initialization and missing-outcome rules. Distinguish the 300-second HTTP, 900-second total capture and 600-second total definition limits.
2. Submit once per question in a fresh conversation. Never resubmit a consumed, uncertain or interrupted slot. Reading an existing Response to recover evidence is separate from sending a new question.
3. Retain unsubmitted, unknown, errored, blocked and evidence-incomplete slots in registered denominators. Account separately for record state, HTTP success, Response completion and internal-query success.
4. Separate development from unused questions and do not tune from unused results. Keep question text, expected answers and scoring conditions out of instructions and examples. Source-owned schemas, business definitions and existing DAX are legitimate reconciliation inputs.
5. Score content as PASS, FAIL, UNCLEAR or NA and retain a separate native-execution judgment. NA is limited to the predeclared clarification branch. Never promote UNCLEAR to success or remove it from the denominator.

## 4. ソース由来の誤りを直す / Correct source-grounded errors

- SQL の識別子・別名を引用し、名称は実 dimension から取得します。集計と順位に同じ fact filter を使い、関連先の多対多をたどって寄付を二重計上しません。
- `StaticSeed2025` の名称と暦年条件を区別します。年で絞る場合は UTC／JST と半開区間を明示し、同じ時刻変換を source と回答へ適用します。AM/PM は12 AM=00時、12 PM=12時として変換し、日付繰越を確認します。
- DAX は実 TMDL の式を保持し、内部 `KEEPFILTERS` と外部 filter の交差を説明します。想定した答えを出すためにメジャーを書き換えず、BLANK と0を区別します。
- Gen2 では実際の `ontology.json` を保持します。対応しない legacy Ontology 指示フィールドを挿入せず、global と3つの対応ソース指示の差分を明示します。
- 同じ Agent へ適用・Publish して読み戻しを照合します。9 KQL例の実照会とサービスの validation を確認し、候補・Draft・公開版の hash を区別します。定義一致を回答精度の合格と扱いません。

- Quote SQL identifiers and aliases, obtain names from actual dimensions, and apply identical fact filters to totals and rankings. Do not double-count donations through many-to-many relationships.
- Distinguish the `StaticSeed2025` dataset label from a calendar-year predicate. Specify UTC or JST and half-open bounds, then apply the same conversion to source and answer. Convert 12 AM to 00 and retain 12 PM as 12; check date rollover.
- Preserve actual TMDL expressions and explain intersection of inner `KEEPFILTERS` with outer filters. Do not rewrite measures to produce an expected answer; distinguish BLANK from zero.
- Preserve the actual Gen2 `ontology.json`. Do not insert unsupported legacy Ontology instruction fields; disclose changes to global instructions and the three supported source instructions.
- Apply, publish and read back the same Agent. Check actual execution and service validation of nine KQL examples; distinguish candidate, Draft and published hashes. Definition equality is not answer-quality acceptance.

## 5. 機能別の実行証跡を確認する / Verify each capability

| 機能 / Capability | 必要な確認 / Required verification |
|---|---|
| Graph | 実体化・load済みモデルと同じ source の実 GQL を照合。時系列追加後の Unsupported／drift を隠さない / Reconcile loaded-model GQL with the same source; retain Unsupported projection and drift after time-series changes |
| 時系列 / Time series | 物理 source・join key・timestamp・value の読戻し、実 query/result と独立 KQL/CSV を照合 / Read back physical source, join key, timestamp and value, then reconcile actual query/results with independent KQL/CSV |
| Metrics | Native Metrics の登録と実行を確認。直接 DAX の成功で置き換えない / Verify native registration and execution separately from direct DAX |
| Ontology MCP | tools/entity/rule 一覧と実照会を分ける。正しい prose だけでは query 実行済みとしない / Separate tool/entity/rule discovery from executed queries; correct prose alone does not prove execution |
| RDF | 意図した class/property/relationship と label/comment/domain を照合し、追加 FK・型の拡張・range欠落も記録 / Reconcile intended structure and annotations; retain generated foreign keys, widened types and missing ranges |
| Report | 実描画、visual 数、export値、filter適用と復元を照合。embed と native portal の確認を区別 / Check actual rendering, visuals, exported values and filter/restore; distinguish embed from native portal checks |
| Code Interpreter | 最終評価後の別枠。実 SQL→CI→ダウンロードした CSV・画像を追跡し、期間と値と表示を照合 / A separate post-final probe: trace actual SQL to CI and downloaded CSV/image, checking scope, values and presentation |

SQL／KQL／DAX／GQL が回答文に書かれたこと、HTTP 200、Response completed は、実クエリ成功の代わりになりません。Code Interpreter の年指定が曖昧な場合は、実 SQL と明示された時刻系から比較対象を先に固定します。値が合う方を後から選ばず、特定不能は UNCLEAR とします。

A query printed in an answer, HTTP 200 or a completed Response does not replace actual successful execution. For ambiguous calendar scope in Code Interpreter, freeze the comparison reference from actual SQL and stated timezone before comparing values. Do not select whichever reference matches; unresolved semantics remain UNCLEAR.

## 6. 比較・Word・HTML・配布物を整合させる / Reconcile comparisons and artifacts

1. 前後の対応比較は元・回帰の290条件から開始し、質問、条件、業務データ、適用前提が同じものだけを対応させます。除外は両側同数で、理由と元判定を保持します。別々の未使用6条件は対応比較に混ぜません。
2. すべての PASS／FAIL／UNCLEAR の遷移を示し、改善と退行の両方を報告します。構成を変更していない比較は反復確認であり、修正による改善や因果効果と呼びません。Codex 補助審査と独立した人の承認を区別します。
3. 現行の共通日英原稿、profile の手順、当日の作業レポートを更新します。過去の日付のスコアと v2.7 資産を保持し、過去の画面を今回の成功証拠へ転用しません。
4. ソース・Notebook 同梱資産・日付付きレポートを検証して先に commit します。その commit を基に artifact-set を作り、同じ manifest と共通原稿から参加者 Word／HTML を新しい外部 stage へ生成します。
5. HTML の日英切替、検索、目次、checklist、リンク、図、印刷を実ブラウザーで確認します。Word は構造、表、図、改ページ、見出しリンクを確認して実描画します。LibreOffice の描画と Microsoft Word の実行を区別します。
6. Word／HTML の対応 hash、artifact-set、全 ZIP entry、SHA256SUMS、README のリンクを照合します。公開差分・配布物から認証、実環境 ID、私有パス、私有質問・期待解答・生 trace を除きます。
7. 関連テストと資料検証を完了し、review 済みの変更を GitHub main にマージします。main commit、配布物 hash、実測範囲、残る製品制約を記録します。資料の検査成功と AI の全問合格は別の結果です。

1. Start pairing from 290 original and regression conditions. Match only equal questions, conditions, business data and applicable premises. Exclude symmetrically with reasons and original judgments. The two disjoint groups of six unused conditions are not paired.
2. Report every PASS/FAIL/UNCLEAR transition, including gains and regressions. An unchanged-configuration comparison measures repeatability, not improvement caused by a fix. Distinguish Codex-assisted review from independent human approval.
3. Update the shared bilingual course source, profile procedure and dated work report. Preserve historical scores and v2.7 assets; do not relabel old screenshots as evidence for this deployment.
4. Verify and commit source, embedded Notebook assets and the dated report first. Create artifact-set against that commit, then generate participant Word/HTML together in a fresh external stage from the same manifest and source.
5. Check language switching, search, contents, checklists, links, figures and printing in an actual browser. Check Word structure, tables, figures, pagination and heading links with actual rendering. Distinguish LibreOffice rendering from running Microsoft Word.
6. Reconcile paired hashes, artifact-set, every ZIP entry, SHA256SUMS and README links. Exclude credentials, live identifiers, private paths, private questions, answer keys and raw traces from public diffs and packages.
7. Complete relevant tests and document checks, review changes and merge GitHub main. Record the main commit, artifact hashes, measured scope and remaining product limits. Artifact validation and perfect AI-answer acceptance are different results.
