# 参加者用改訂の検証と過去の配置記録 / Participant revision validation and historical deployment

## 今回の参加者用改訂

今回の生成元は `723465ba15bd56206061b540b833ab4c5b7a29f2` です。参加者への配布単位は **Word または日英HTML ＋ 同じ版のZIP** です。手順書だけを読み進めて同梱資産を操作できるよう、配置・採用済み設定・公開確認・評価の説明を追加しました。

| 今回の変更・確認 | 範囲 |
|---|---|
| 基盤の作成 | 第4章から24.4〜24.8へ進み、実フォルダー対応、計画レビュー、参加者の範囲承認、Pipeline・Activator・Semantic modelを含む配置を実施する手順を収録 |
| 採用済み設定 | 第17章に6ビュー、17 SQLオブジェクト・143選択列、4指示全文、9 KQL例、10既存メジャー、適用・公開・読み戻しを収録 |
| 評価 | 基本10枠・84条件、完全な公開評価49枠・290条件／段階。前後98枠・580条件行・290組の用紙と固定29問・122種類の条件を同梱 |
| 追加の修正 | 第19章で仮説、変更箇所、UIによる編集・公開、再評価、採用・復元を説明。固定プロファイル用ツールとの用途を区別 |
| 実環境の読み取り | 新しい `participant_profile.py` のprepareと公開版verifyが成功。通常ソース3件、同じ主Ontology context、17オブジェクト・143列、9件のValid例を確認 |
| 新しいツールの書き込み | apply／publishの経路は模擬応答による検査。今回のツールからクラウドへ書き込みを行った実績とは区別 |
| クラウドへの再適用 | 今回再生成したNotebookの同梱パッケージはクラウドへ再同期していない。新しい教材経路のクラウド通し実行・新たな回答精度評価も未実施 |
| 文書・ZIPの最終確認 | 自動検査960件、実文書検査257件成功。Word 147／日本語HTML 167／英語HTML 169の計483ページの画像確認（新規68、前候補と画像SHA完全一致415）。全429 ZIPエントリーと417ソースの一致、Gitなしoffline preflightを確認。[検証JSON](verification.json)・[配布SHA-256](SHA256SUMS.txt) |

読み戻した構成が一致すること、KQL例のサービス検証がValidであること、実際のソース照会の成功、回答の条件充足は別の判定です。構成再現だけでOntologyの利用可能性や過去と同じ回答精度を保証しません。新しいツールの確認結果でも `ontologyContextAvailabilityVerified=false` と `answerAccuracyVerified=false` を保持しています。

以下の配置、回答、Notebook同期、文書ページ数とZIP件数は、**旧ソース `c724bc3cb906ef5278bb301a1af6887b65affd0a` に対応する2026-10-15の履歴**です。今回の改訂の検証件数として流用しません。特にNotebook01〜05のクラウド定義とのコード一致確認を、新しい同梱パッケージのクラウド同期と読み替えません。

## 過去の配置・評価 — 2026-10-15、ソース c724bc3

この節の旧文書検証リンクは、旧配布物を保持する固定リリースcommit `930aa520f8b14a7e756999223bc9abac3c9f2539` を参照します。配置・Notebook同期に対応するソースcommitは `c724bc3cb906ef5278bb301a1af6887b65affd0a` です。

旧フォルダー18アイテムを削除し、指定した新フォルダーに18アイテムを配置しました。OntologyとData Agentは各1件です。
復元可能な旧資産・一時資産9件も削除し、後続のGET棚卸しで旧フォルダー0件、現行18件、両ごみ箱0件を再確認しました。
[作業・実測レポート](../tuning-20261015/README.md)と[校正手順](../tuning-20261015/calibration-and-proofreading.md)に評価・再現手順を記載します。

| 項目 | 実測結果 |
|---|---|
| ソースcommit・manifest | `c724bc3cb906ef5278bb301a1af6887b65affd0a` / manifest `7abd339724375ed536308f434d9fff5b52afa320fcfd4ccf28c41228071ca5fb` / 371成果物 |
| 配布Notebook | Notebook01–05の実生成とcloud定義のコード一致を確認。01・05は同一定義、02–04は既存アイテムの定義だけを同期。ジョブ再実行なし。 |
| 現行Agent | `measured-contract-20261015`。通常ソース3件と同じOntologyの独立context登録。同期後の新しい公開定義と、可搬profileの全区画・選択状態の一致を確認。 |
| 参加者Word・日英HTML | 152 PASS / 0 FAIL。実ファイルのSHA-256は[検証JSON（旧版）](https://github.com/yang-jiayi/furusato-fabric-workshop/blob/930aa520f8b14a7e756999223bc9abac3c9f2539/docs/v3.0.0/current/verification.json)と[配布SHA-256（旧版）](https://github.com/yang-jiayi/furusato-fabric-workshop/blob/930aa520f8b14a7e756999223bc9abac3c9f2539/docs/v3.0.0/current/SHA256SUMS.txt)に記録。 |
| LibreOfficeと日英印刷 | Word 92、日本語HTML 100、英語HTML 102、合計294ページを全件実画像確認。1,878テキスト断片中の診断未一致2件はページ境界によるもので全文保持を実確認。 |
| 配布ZIP | 383エントリー、17,135,542 bytes、SHA-256 `2b9a8b982f872ed62b4406656601023414f895fe5ea3f9fa64fe57ba7753a227`。全エントリーと371ソースGit blobの一致を確認。 |
| 検査 | ソース・レポートcommit `dbd498a` で908検査が成功（provisioning 122、Data Agent 354、資料 432）。その後の印刷CSSだけの修正 `c724bc3` で関連25検査と実文書152検査を実行して成功。908検査全件の再実行とは区別。失敗・エラー・skip 0。日付付き資産が未配置だった先行検査1件の失敗は保持し、配置後に再実行して解消。 |

## 過去の実回答と制約 — 2026-10-15

baselineと最終評価は、それぞれ51問・296条件の全件を評価しました。回答内容の補助条件は、baselineがPASS 200・FAIL 91・UNCLEAR 2・NA 3、最終評価がPASS 225・FAIL 65・UNCLEAR 0・NA 6です。調整に用いない保留問題は別の問題集合で、両フェーズとも6条件中PASS 5・FAIL 1でした。これらは対応付けた改善比較には含めません。

同一質問・同一条件の比較は、元の290条件から既定の確認質問分岐で適用外となる9条件を両側同じキーで除いた281条件です。補助条件充足率は189/281（67.26%）から217/281（77.22%）へ9.96ポイント上がりました。内訳はPASS維持187、PASS→FAIL 2、FAIL→PASS 28、FAIL維持62、UNCLEAR→PASS 2です。最後の2条件は対応する最終回答で新たに証拠が得られたもので、baseline枠の送信・結果は不明のまま保持し、確認済みの誤答が改善したとは扱いません。

厳密なnative判定で受理された回答はbaselineの51問中1件から最終の51問中2件になりましたが、いずれも確認質問の分岐です。ソース照会を伴う完成回答の厳密な受理は両方0件です。実際のソース実行を1つ以上確認できた回答は28件から27件であり、内容の条件充足率とは別の指標です。有限回の回答で観測された差から、指示修正による確実な因果的改善、全文章の正しさ、Ontology接続の復旧を保証しません。
補助条件充足率は回答要素・見出し・ソース経路も含みます。厳密なnative判定とソース実行の観測数は別に示し、すべての反復・失敗・不明を保持します。
baselineの中断した回帰問題1枠の送信・結果不明は、対応する最終回帰問題の結果で上書きしません。正式登録112枠と実際に確認できたPOST数、別枠Code Interpreter1問を区別します。

最終評価のファイル別観測問題では3回中2回、回答内の時刻が3分12秒の空きを示すのに「観測期間が重なる」と誤って補足しました。固定条件外の誤りとして残します。
重複イベントを問う問題の「承認済みソース全体にEventIDがない」という固定条件は、Eventhouse集計ビューに対する適切な拒否だけでは満たせません。品質処理用LakehouseテーブルにはEventIDがあるため、固定条件のFAILを保持します。
月別比較問題は月別金額と大小関係を示しましたが、Code Interpreterエラーで差・倍率・増減率を計算できませんでした。
最終評価後の別枠1問では、SQLの返却は順位列を含む10行・5列で、ダウンロードしたCSVの指定4列は全10行の値と順序が一致し、6桁の自治体IDの先頭0も保持されていました。取得した横棒グラフは、上位10自治体の順序・金額、日本語、StaticSeed・2025年・円の表記を実画像で確認しました。これは実際に取得した成果物とSQL結果の整合性の確認です。

この追加確認の厳密な能力判定はinconclusiveです。実SQLは日付で絞らない静的スナップショット全体を参照し、UTC暦年かJST暦年かの明示がなかったため、固定した暦年参照との独立比較は行っていません。コードと成果物を返すfunction記録はありますが、native Code Interpreterの完了状態・標準出力と入力ファイルの実bytesの結合は取得できず、native実行の完全な合格とは扱いません。

追加確認の最終回答には、実行したSQLの再掲にも誤りがありました。実SQLはMunicipalityNameをMunicipalityDisplayNameという別名で返しましたが、回答はMunicipalityDisplayNameを直接選ぶ異なるSQLを「実行したSQL」として示しました。CSV・画像の整合性とは別の誤りとして記録し、引用されたSQLを試すための再質問や再実行はしていません。

## 過去の配置・データ・機能 — 2026-10-15

StaticSeed80,000件・1,344,099,000円、生観測15,000行・253,886,000円、受入増分14,900件・252,058,000円、隔離100行、Gold94,900件・1,596,157,000円を別々に照合しました。CSV11ファイルのデータ契約は保持します。

3ファイルのFileCreated→Activator→Completed Pipeline→Copy→KQLを関連付けて自動取り込みを検証し、終了後にActivatorを停止しました。初回の未成立試行は保存しています。
Reportは公式埋め込みで実描画、5可視化のデータ出力、年フィルター変更・復元を確認しました。2026年JSTはStaticSeedの年越し分を含む16,072件・272,421,000円です。

静的Graphの25本の直接GQLは成功しました。後続の物理Time Series追加後にはUnsupported KQL sourceとhasDriftが残ります。
Time Seriesの保存バインドは読戻し済みですが、native返却行と成功状態が得られない実行確認はinconclusiveです。native Ontology Metricsは0件です。
Data AgentのOntology contextはSchemaUnavailable／502を保持し、直接Graph/GQLの成功をAgent経由の接続成功とは扱いません。
Turtleの意図した10クラス・73プロパティ・15関係は照合済みですが、追加FK14件、整数rangeの変化、Time Series range欠落があり、可逆変換の保証ではありません。

Notebook01の実Spark完了と外側CapacityNotActive失敗を両方保存しています。Notebook05のapplyはCompleted、29テーブル検証済みです。Notebook02–04のimportと同等CLI処理を、各Notebook画面からの実行成功と混同しません。

## 旧文書と旧ソースの対応 — c724bc3

参加者版は構造・日英ブラウザー検査152件が成功（FAIL 0）し、LibreOfficeで描画したWord92ページ、Chromiumで印刷した日本語100ページ・英語102ページの全294ページを実画像で確認しました。Word本文・表の可視テキスト1,878断片のうち単純連結診断で2断片が未一致となりましたが、いずれもページ境界に挟まるヘッダー・フッターによるもので、実画像と実PDFテキストで全文の保持を確認しました。

一部の元UI画像には周辺操作部の切れや密なGraphラベルの重なりが残りますが、手順本文・キャプション・必要な証拠は読めます。余白の多い参照ページや表見出しから次ページへの継続も記録しました。fieldを含まない目次方式のためページ番号はなく、フッターの「Page」だけが残る点は体裁上の制約です。29章・付録への内部リンクを利用できます。

ZIPの383エントリーをCRC・SHA-256で全件確認し、371ソース成果物を固定ソースcommitのGit blobと照合しました。Notebook01–05・CSV・モデル・採用profile・校正手順・実測レポートを同梱します。 [文書検査（旧版）](https://github.com/yang-jiayi/furusato-fabric-workshop/blob/930aa520f8b14a7e756999223bc9abac3c9f2539/docs/v3.0.0/current/DOCUMENT_VALIDATION.json)・[全ページ確認（旧版）](https://github.com/yang-jiayi/furusato-fabric-workshop/blob/930aa520f8b14a7e756999223bc9abac3c9f2539/docs/v3.0.0/current/participant-render-validation.json)。
Microsoft Wordによるページ割り・描画は未検証です。資料検査とmainへの統合は、AI回答や全native機能の合格証明ではありません。

[検証JSON（旧版）](https://github.com/yang-jiayi/furusato-fabric-workshop/blob/930aa520f8b14a7e756999223bc9abac3c9f2539/docs/v3.0.0/current/verification.json)・[配布SHA-256（旧版）](https://github.com/yang-jiayi/furusato-fabric-workshop/blob/930aa520f8b14a7e756999223bc9abac3c9f2539/docs/v3.0.0/current/SHA256SUMS.txt)・[現行教材](README.md)。
[以前のcurrent（固定commit）](https://github.com/yang-jiayi/furusato-fabric-workshop/tree/f255989351b418fe99f9ee8ef3d562233adfd9f7/docs/v3.0.0/current)は別記録として保持します。

## English — current revision scope

The current participant revision is generated from `723465ba15bd56206061b540b833ab4c5b7a29f2`. Distribute either Word or HTML with the matching ZIP. The guide contains the scoped core-deployment procedure, exact adopted profile, publication/readback steps, full public questions and evaluation records. The standard route is Chapter 4 → 24.4–24.6 → Chapters 5–8 inspection → 24.7 and Chapters 9–11 → 24.8 → Chapters 12–13 → Chapter 17 → Chapter 19.

The new profile helper's read-only prepare and Published verification succeeded against the existing environment. Its apply/publish paths were checked with mocked responses. The regenerated Notebook payloads have not been synchronized to Fabric, and the new participant route has not been rerun end to end in a new cloud deployment. No new answer-quality campaign was executed for this document revision. Configuration equality and service example validation do not prove native Ontology availability or answer quality.

The public full evaluation has 29 distinct questions, 49 attempts and 290 conditions per phase; its two-phase forms contain 98 slots, 580 condition rows and 290 pairs. Practice uses ten attempts and 84 conditions. Historical private questions are not distributed. Future custom tuning uses the separate documented edit/publish/compare route, not reapplication of the fixed profile.

All 960 affected unit checks and 257 actual-document/bilingual-browser checks passed. Reviewers inspected all 483 actual pages: 147 LibreOffice Word pages, 167 Japanese HTML pages and 169 English HTML pages. Of these, 68 were newly inspected and 415 reused actual prior review only after matching PDF label, page number and the entire PNG SHA-256. Another 14 of those identical pages were additionally reopened for text-preservation diagnostics, so 82 current images were actually opened. All 429 ZIP entries passed CRC/SHA-256 checks and all 417 source entries matched the pinned Git blobs. The actual extracted ZIP passed offline preflight without Git and dependency checks; tampered protected source was rejected. Microsoft Word rendering and pagination remain unverified. See [document checks](DOCUMENT_VALIDATION.json), [all-page review](participant-render-validation.json) and [verification](verification.json).

## English — historical 2026-10-15 observations

The old folder was cleared and 18 items were deployed in the requested destination, with exactly one Ontology and one Data Agent. Nine recoverable old or temporary items were removed; a later GET-only inventory confirmed both recycle bins empty and the current 18 identities stable.
Baseline and final evaluation each covered all 51 questions and 296 conditions. Supplemental content outcomes were 200 PASS, 91 FAIL, 2 UNCLEAR and 3 NA at baseline, and 225 PASS, 65 FAIL, 0 UNCLEAR and 6 NA at final. The separate heldout sets, which were not used for tuning, each had 5 PASS and 1 FAIL across six conditions. These disjoint sets are excluded from the paired improvement comparison.

The paired comparison uses 281 conditions after removing nine predeclared clarification-branch inapplicable conditions symmetrically by the same keys from the original 290. Supplemental condition fulfillment rose from 189/281 (67.26%) to 217/281 (77.22%), a 9.96 percentage-point increase. The transitions were 187 PASS→PASS, 2 PASS→FAIL, 28 FAIL→PASS, 62 FAIL→FAIL and 2 UNCLEAR→PASS. The last two reflect evidence obtained in the final evaluation for the interrupted baseline slot, not a demonstrated correction of a known wrong answer.

Strict native acceptance increased from 1 of 51 baseline responses to 2 of 51 final responses, but all accepted responses were clarification branches. Neither phase had a strictly accepted completed answer involving a source query. Responses with at least one observed successful source execution changed from 28 to 27, a separate measure from content fulfillment. Differences in this finite set of responses do not guarantee a causal tuning improvement, correctness of every sentence or restored Ontology consumption.
Supplemental condition fulfillment, strict native acceptance and observed source execution are separate. The interrupted baseline regression slot remains an uncertain submission/outcome. In the final phase, the file-observation question contains two false-overlap assertions across three responses outside the frozen conditions; the event-duplication question retains its broader EventID-premise failure. The monthly comparison question could not compute the requested difference/ratio/growth after a native Code Interpreter error.
In the separate one-question check after final evaluation, the four requested CSV columns matched those columns of the ten-row SQL result (five columns including rank), in the same order. Leading zeros in six-digit municipality IDs were preserved. The returned horizontal chart was actually viewed: all ten municipalities, ordering, amounts, Japanese labels and the StaticSeed, 2025 and yen title were legible and consistent. This verifies the returned artifacts against the executed SQL result.

The strict capability result remains inconclusive. The executed SQL queried the full static snapshot without date filtering or an explicit UTC/JST calendar-year statement, so no independent comparison with the fixed calendar reference was performed. Function records returned code and artifacts, but did not expose a completed native Code Interpreter status, stdout or binding to the actual input-file bytes. These observations do not establish a full native execution pass.

The capability response also quoted the executed SQL inaccurately. The actual query selected MunicipalityName AS MunicipalityDisplayName, while the final answer presented a different query selecting MunicipalityDisplayName directly as the executed SQL. This reproduction error is recorded separately from CSV/chart consistency. No question or query was rerun to test the quoted version.

Three automatic file ingestions and official embedded Report rendering were verified. Static GQL success, saved physical Time Series binding, inconclusive native Time Series execution, zero Ontology Metrics and the Agent's SchemaUnavailable context are stated separately. The initial activation trial and Notebook01 outer-job failure remain in the record.
The participant edition passed 152 structure and bilingual browser checks with zero failures. Every one of the 294 actual page images was inspected: 92 LibreOffice Word pages, 100 Japanese Chromium print pages and 102 English print pages. Of 1,878 visible Word paragraph/table-cell text fragments, two did not match the raw concatenated PDF text because repeated headers/footers interrupted paragraphs across page boundaries; actual images and PDF text confirmed that both complete paragraphs were retained.

Some retained UI screenshots show cropped peripheral controls or overlapping dense graph labels; the instructions, captions and required evidence remain readable. Sparse reference pages and table continuations are documented. The field-free navigation edition intentionally has no page numbers and retains a cosmetic bare “Page” footer label; 29 chapter/appendix links provide navigation.

All 383 ZIP entries were checked by CRC and SHA-256, and all 371 source artifacts matched Git blobs at the pinned source commit. The package includes Notebooks01–05, CSV data, models, the adopted profile, calibration procedure and measured report. See [document checks（旧版）](https://github.com/yang-jiayi/furusato-fabric-workshop/blob/930aa520f8b14a7e756999223bc9abac3c9f2539/docs/v3.0.0/current/DOCUMENT_VALIDATION.json) and [all-page review（旧版）](https://github.com/yang-jiayi/furusato-fabric-workshop/blob/930aa520f8b14a7e756999223bc9abac3c9f2539/docs/v3.0.0/current/participant-render-validation.json).
Microsoft Word layout remains unverified. Document checks or merging main do not establish universal AI correctness or all-feature acceptance.
