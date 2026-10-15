# Furusato Workshop 3.0.0 — 現行の参加者用教材 / Current participant materials

参加者には、**Word または日英HTMLのいずれかと、同じ版のZIPを1組で渡してください。** 手順はWord・HTMLに収録し、実行するNotebook、CSV、SQL、モデル、ツール、評価用紙はZIPに同梱しています。初回の配置から、採用済みData Agent設定の適用・公開・確認、回答評価までを参加者が進める構成です。

[参加者用Word](guide/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0.docx) ·
[参加者用日英HTML](guide/furusato-workshop-v3-0-0-complete.html) ·
[同じ版のZIP](Furusato_Workshop_v3.0.0_current-20261015.zip) ·
[配布SHA-256](SHA256SUMS.txt) ·
[今回の検証と過去の実測の区別](deployment-verification.md)

## 渡すものと始め方

1. ZIPを展開する前に、配布元の[SHA256SUMS.txt](SHA256SUMS.txt)とZIPのSHA-256を照合します。
2. ZIPをすべて展開します。`guide/`が手順書、`attachments/`が添付資料、`source/`がNotebook・データ・実行ツールです。コマンドは`source/`から実行します。
3. 第4章で利用可能なワークスペース、容量、機能、権限、空の作業フォルダー、参加者IDを確認します。講習では割り当てられた範囲、自習では自分に操作が許可された範囲を使います。
4. 次の章対応に従って進みます。具体的なコマンド、入力値の確認、完了条件、停止した場合の扱いは手順書に含まれます。別のREADMEを探して不足する操作を補う必要はありません。

| 順番 | 手順書の箇所 | 実施すること |
|---|---|---|
| 1 | 第4章 → 24.4〜24.6 | Python 3.11以降・Azure CLIの準備、本人認証、フォルダー対応、配置計画の確認と承認、基盤作成 |
| 2 | 第5〜8章 | 作成済みのLakehouse・Notebook01・主Ontology・Eventhouseを確認。同じアイテムを重複作成しない |
| 3 | 24.7・第9〜10章 | Activatorの実状態確認、3ファイルの各1回の取り込み、イベント・実行・Copy・KQLの確認 |
| 4 | 第11章 → 24.8 | Notebook05のプレビューと適用、Goldの確認、Semantic model・Data Agentの作成 |
| 5 | 第12〜13章 → 17.5〜17.16 | モデルと意味の確認、SQLビューと選択、採用済み指示・例の適用、公開・読み戻し |
| 6 | 第17章の実回答確認 → 第19章・付録C | SQL・Code Interpreterの確認、固定問題の評価、改善案の比較と採用判断 |

主OntologyとData Agentは**各1件**です。Gen2では通常ソース3件と同じ主Ontologyの独立したcontextを扱います。接続エラーを別のOntology追加で回避しません。組織の容量・テナント設定・アクセス権は管理者が用意する前提です。必須のソースやAgentが利用できない場合は、依存する作業を完了扱いにしません。

## チューニングを再現する内容

第17章には、6つのSQLビュー、選択する17オブジェクト・143列、全体と3ソースの指示全文、9件のKQL例、既存10メジャー、入力先と操作順を収録しています。`participant_profile.py`の`prepare → apply → publish → verify`で、実際のschemaとメジャーを確認して同じAgentに設定し、公開版を読み戻します。手順書の原文と同梱ファイルは同じ正本から生成します。

このツールは固定した`measured-contract-20261015`の構成再現に使います。参加者が次の改善を試す場合の手動編集・公開・比較は第19章に区別して記載しています。独自に変更した指示へ固定プロファイルを再適用して上書きする手順ではありません。

まず**基本演習10回・84条件**で操作と採点を学び、その後、必要に応じて**完全な公開評価49回・290条件／段階**へ進む構成を勧めます。完全評価は公開29問のうちT01〜T10を各3回、B01〜B19を各1回実施します。前後比較用紙は98枠・580条件行・290組で、質問だけを新しい会話へ送ります。採点基準・期待値はAgentの指示や例へ入れません。

初めて採用済み設定を適用した後の測定は「再現確認」です。次の修正の評価では、その時点の公開版をbaselineとして保存します。同じ設定を2回測った差を、指示変更による改善とは呼びません。質問・条件・データを固定し、失敗、不明、退行、実行根拠、採用しなかった案も残します。

## 今回確認した範囲

手順書の生成元は`723465ba15bd56206061b540b833ab4c5b7a29f2`です。今回の追加は、参加者が再現できる配置・設定・評価の手順、同梱ツール、ZIP単体からの実行対応と文書生成の整合です。

新しいプロファイル用ツールは、既存環境に対する**読み取り専用prepareと公開版verifyが成功**しています。実際の17オブジェクト・143列、通常ソース3件、9件のValidなKQL例を確認しました。新しいツールによる書き込み経路は模擬応答で検証しています。今回の教材改訂を理由にクラウドの再配置、全演習の通し直し、Data Agentの新しい回答精度評価は実施していません。

再生成したNotebookの同梱パッケージには、ZIPからの実行に必要なruntimeの検査処理を反映していますが、クラウド上のNotebookへ再同期していません。以前に行ったNotebook01〜05とクラウド定義の一致確認は、旧ソース`c724bc3cb906ef5278bb301a1af6887b65affd0a`に対応する記録です。

関連する自動検査960件と、実ファイルを使った文書・日英ブラウザー検査257件が成功しました。LibreOfficeのWord 147ページ、日本語HTML 167ページ、英語HTML 169ページ、計483ページを画像で確認しました（今回68ページを新たに確認し、残る415ページは前候補で実際に確認した画像とページ番号・PNGのSHA-256が完全一致することを検証しました。さらに、この一致した画像のうち14ページは本文保持の診断で再度開いて確認しました）。ZIPの全429エントリーをCRC・SHA-256で照合し、417ソースを固定commitのGit blobと照合しました。実際に展開したZIPからGitなしのoffline preflightと依存ツールの読み込みが成功し、保護対象の改変も拒否されました。Microsoft Word自体の描画・ページ割りは未検証です。 記録は[文書検査](DOCUMENT_VALIDATION.json)、[ページ確認](participant-render-validation.json)、[検証JSON](verification.json)、[配布SHA-256](SHA256SUMS.txt)にあります。

## 2026-10-15の実回答評価について

[日付付きレポート](../tuning-20261015/README.md)の過去の測定では、対応付けた281条件の補助条件充足率が189/281（67.26%）から217/281（77.22%）へ上がりました。これは今回の教材改訂後に再測定した値でも、参加者が必ず達成する正答率でもありません。厳密な受理1件→2件は確認質問の分岐で、ソース照会を伴う完成回答の厳密な受理は両方0件でした。

過去の51枠・296条件には非公開2問・6条件が含まれるため、配布する公開49枠・290条件とは範囲が異なります。Ontology contextの`SchemaUnavailable`／502、native Metrics 0件、Time SeriesとCode Interpreterの一部実行根拠不足を保持しています。過去の3ファイルの自動取り込みとReport表示の確認も、日付付きの実測であり、今回の新しい通し検証ではありません。

[採用済みプロファイル](../../../workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261015/README.md) ·
[評価・校正の記録](../tuning-20261015/calibration-and-proofreading.md) ·
[版とソースの対応](artifact-set.json) ·
[旧資料の固定ソース](https://github.com/yang-jiayi/furusato-fabric-workshop/tree/c724bc3cb906ef5278bb301a1af6887b65affd0a)

## English

Give participants **either the Word guide or bilingual HTML, together with the matching ZIP**. Instructions are in the guide; Notebooks, CSVs, SQL, models, tools and evaluation forms are in the ZIP. Verify its external SHA-256 before extracting it. Run commands from `source/`.

Follow Chapter 4 → 24.4–24.6 deployment → Chapters 5–8 inspection → 24.7 and Chapters 9–11 ingestion/quality → 24.8 model/Agent deployment → Chapters 12–13 → Chapter 17 configuration → Chapter 19 and Appendix C evaluation. Workspace/capacity/access prerequisites remain organizational responsibilities. The guide includes creation of the Pipeline, Activator and semantic model, without undistributed instructor scripts. Keep one main Ontology and one Data Agent.

Chapter 17 includes six SQL view definitions, 17 selected objects and 143 columns, four complete instruction bodies, nine KQL examples and ten existing measures. The helper prepares, applies, publishes and verifies the fixed adopted profile. Chapter 19 separately explains subsequent manual tuning, publication and comparison. Start with ten practice attempts / 84 conditions, then use 49 attempts / 290 conditions per phase for the full public evaluation. Two phases have 98 slots, 580 condition rows and 290 paired conditions. Send question text only, in a fresh conversation for every attempt.

The source for this participant revision is `723465ba15bd56206061b540b833ab4c5b7a29f2`. The new helper's read-only prepare and Published verification passed against the existing environment; its write path was tested with mocked responses. The updated Notebook payloads have **not** been synchronized to Fabric, and this revision has **not** been deployed and evaluated end to end in a new workspace. Earlier Notebook/cloud synchronization belongs to source `c724bc3cb906ef5278bb301a1af6887b65affd0a`.

All 960 affected unit checks and 257 actual-document/bilingual-browser checks passed. Reviewers inspected all 483 actual pages: 147 LibreOffice Word pages, 167 Japanese HTML pages and 169 English HTML pages. Of these, 68 were newly inspected and 415 reused actual prior review only after matching PDF label, page number and the entire PNG SHA-256. Another 14 of those identical pages were additionally reopened for text-preservation diagnostics, so 82 current images were actually opened. All 429 ZIP entries passed CRC/SHA-256 checks and all 417 source entries matched the pinned Git blobs. The actual extracted ZIP passed offline preflight without Git and dependency checks; tampered protected source was rejected. Microsoft Word rendering and pagination remain unverified. See [document checks](DOCUMENT_VALIDATION.json), [all-page review](participant-render-validation.json) and [verification](verification.json).

The dated October 15 result, 189/281 → 217/281 supplemental condition fulfillment, is historical and is neither a new measurement nor a guaranteed participant accuracy target. Its private questions are excluded from the public course kit. Preserve the documented Ontology, Metrics, time-series and execution-evidence limitations and evaluate actual answers in each participant environment.
