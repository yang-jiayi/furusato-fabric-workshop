# 新規配置・回答精度改善の検証 — 2026-10-07

**旧フォルダ（20261006）を空にし、指定フォルダ（20261007）へ21 Itemsを新規配置しました（第3報で22 Items）。
正式Agentの標準10問・84条件は初回36/84・34/84で、回答契約の復元後は74/84・73/84、第4報でご指示により
採用したR8は76/84・74/84です。成果物の整合性とAI回答品質は別の判定です。**

2026-10-04の記録は[history/20261004](history/20261004/deployment-verification.md)に変更せず保持しています。

## 旧フォルダの削除

| 対象 | 実際の応答・対応 |
|---|---|
| 20261006直下とTempの29 Items | 通常削除から開始。managed children 10件は親の削除で既に消えていたため再削除なし |
| Eventhouse | 公開APIの完全削除は`UnknownError`（再試行不可）。内部のmetadata削除応答で`AssociationPreventsArtifactDeletion`を確認し、原因の通常削除済みAutoProbe PipelineとNotebookを完全削除した後に成功 |
| Tempフォルダ | 中身が空になった後に削除。20261006フォルダ自体は空のまま保持 |
| 復元可能なItems | Notebook5件、Lakehouse、Ontology2件（managed childrenを含む）は通常削除のため2026-10-14まで復元可能 |

削除前に旧Agent2件の定義を非公開で保存しました。削除後のworkspaceのactive Itemsは0件でした。

## 新規配置

ポータルはWindows Helloを要求するため、[runtime](../../../workshop/v3.0.0-preview/README-runtime.md)の
API経路で配置しました。番号付きのsubfolder参照は、内部のfolder一覧で実際のGUIDとの対応を確認してから使用しています。

| 段階 | 結果 |
|---|---|
| preflight・sources・Notebook01 | 静的80,000件／1,344,099,000円。Notebook01は1回のみ |
| notebooks・realtime・core | Notebook02–05を配置。generation2の主Ontologyを読み戻し |
| 増分 | 3ファイルを各1回PutBlobし、Pipelineを**手動で**3回実行。raw 15,000件／253,886,000円 |
| 静的consumer Ontology | generation1互換Ontologyを作成し53 partsを読み戻し。Graph refresh完了、109,592 nodes／297,303 edges |
| SQL views | 6 viewsを作成し、列と件数を確認 |
| 品質処理・Gold | Notebook05のpreview hashを確認してapply（1回）。受入14,900件／252,058,000円、隔離100件、Gold 94,900件／1,596,157,000円 |
| Semantic Model | Direct Lake refresh完了。実DAXで静的・増分・BLANKを確認 |
| Data Agent | 4ソースで作成・公開後、正式profileを適用。SQL/KQL例は実ソースで全件が行を返すことを確認 |

最終のactive状態は**21 Items・Data Agent1件・Tempフォルダ0件**です
（Notebook5、Lakehouse2、SQL Endpoint2、Eventhouse2、KQL Database2、Ontology2、GraphModel2、
Semantic Model1、Pipeline1、Activator1、Data Agent1）。Activatorは停止状態で、自動イベント配送は検証していません。
第3報で任意のPower BIレポート1件を追加し、現在は**22 Items**です。

## 回答精度の評価と改善

公開Data Agent MCPで、元の10問・84条件を各2回、拡張14問を1回評価しました。

| 構成 | 標準84条件 | 拡張14問 事実／内容PASS |
|---|---:|---:|
| 配置直後（time-layer-isolation） | 36 ／ 34 | 13 ／ 10 |
| 採用構成（standard-contract-restoration） | **74 ／ 73** | **14 ／ 13** |

主な原因は、修正チェーンが元の統合指示を置き換えて標準10問の回答契約が失われたこと、
年の指定がない「8月」を2025年の寄付データの8月と解釈して2026年8月の観測を0件としたことでした。
6構成の全経過、事前登録holdout（11 PASS／1 FAIL）、残件は
[2026-10-07追補](../tuning-20261007/README.md)にあります。
T10はnativeのコンテンツフィルターで遮断され、回避せずFAILとして数えています（上限77）。

## 第3報（同日）: 手順の逸脱の完了と対策

| 項目 | 結果 |
|---|---|
| Agent の SQL ビュー要素 | 公開の Data Agent 管理 API で、6 views が View・Available・選択済み、列が INFORMATION_SCHEMA と一致することを確認 |
| 任意の Power BI レポート | 既存モデルに接続するレポートだけを配置。PDF で表示を確認し、DAX で Gold 94,900件／1,596,157,000円・高額1,392件と一致 |
| `handoff-ontology` | 承認済みコミットのソースで記録（配置時の source fingerprint を維持） |
| Activator の自動配送 | **UI での引き継ぎ**。ルールのアクションはこの配置の Pipeline を指している（当初「バンドル側の Pipeline 接続を参照」と書いたのは誤りで、第4報で訂正）。遅延の許容時間の保存（Edit action → Apply → Save）と、配送ごとのイベントの書き出しが UI でのみ可能。手動取り込み済みのため、再配送の前に承認されたリセットが必要 |
| 時系列バインド・native Metrics | **UI での引き継ぎ**（定義形式と Generate Ontology の API が公開されていない） |
| Example queries の検証状態 | KQL 9件は Valid、Lakehouse の SQL 17件はすべて Invalid（検証がエンドポイントに接続できない。実行時の SQL は成功）。製品サポートへの報告案を作成 |
| 残件への候補 R7・R8 | 第3報の時点では事前に記録した採用規則を満たさず不採用（R7: 69／76、R8: 76／74・拡張の内容 11）。正式 Agent を R6 に戻し、14 パーツの一致を確認 |
| 事前に固定した未公開の確認問題12問（2回目のセット） | R6 で1回だけ実行。事実 9／12、内容 7／12 |
| 実行ソースの観測 | Temp の一時ノートブックで SDK の run steps を取得（使用後に削除）。T09 は Kusto と LakehouseTables だけを実行し、Ontology は実行していない |

詳細は[第3報](../followup-20261007/README.md)と[製品サポートへの報告](../followup-20261007/platform-support-cases.md)にあります。

## 第4報（同日）: 対策の順にすべて対応

| 項目 | 結果 |
|---|---|
| R8 の採用（ご指示） | 公開して、評価した R8 と定義の14パーツが一致することを確認。標準10問・84条件 76／74、公開の回帰14問 事実12／内容11（1問は通信タイムアウト） |
| 言葉づかいを直した候補 R9・R10 | 専門用語を含む回答は 28件 → 0件。ただし標準の平均が 73.0・73.5 で採用基準（74.5）に届かず不採用。本番を R8 に戻して一致を確認 |
| 3回目の未公開の確認問題12問 | R8 の採用前に固定し、R8 で1回だけ実行。事実 11／12、内容 10／12 |
| 製品サポート | Azure のサポート API は Fabric を管理ポータルへ案内するため、管理ポータルから2件を起票（重大度 C） |
| サービス正常性 | 「Ontology V2 を使う Data Agent で操作が完了しない」障害（10-02〜、10-09 修正予定、回避策は V1）。正式 Agent は V1 の互換 Ontology を使用 |
| 回帰スイート | 14問 → 19問（B15〜B19 を追加。期待値はリポジトリのデータから計算） |
| Activator・時系列・Metrics | ポータルの画面での作業が残る（この環境のブラウザーでは編集画面を操作できない）。KQL のデータは消していない。Copy の記録を API から取得する読み取り専用ツールを追加 |

## 第5報（2026-10-08）: 追加5問と参加者用の手順書

| 項目 | 結果 |
|---|---|
| 追加の回帰5問（B15〜B19、R8 で1回） | 事実 4／5、内容 3／5。B16 はファイルごとの件数と金額を示さず、B19 は非表示の金額列を「ない」と答えた。実行前に本番の定義が R8 と一致することを確認 |
| 回帰19問の合計（R8） | 事実 16 PASS・2 FAIL・1 判定不能、内容 14 PASS・4 FAIL・1 判定不能（B01〜B14 は 10/7 の測定） |
| 参加者用の手順書 | 各章を目的・操作手順・完了の確認・参照表・参考資料だけにした版（`--participant-edition`）。旧版の写し、評価の記録、撮影日時の注記、リリースの注記、ハッシュを本文から除き、ふだんの言葉に書き直した |
| 画面のキャプチャ | 48枚を確認し、28 枚を手順の該当箇所に配置して説明を書き直した。失敗した状態・古い手順・作業用のメモが写る画面と、旧版の構成図は使わない |
| Word / HTML | 94 ページ、155 検査／0 FAIL（参加者用の版に作業用・履歴の言葉がないことの検査を含む） |

## 第6報（2026-10-09）: R11、モデルの説明の言葉、構成図

| 項目 | 結果 |
|---|---|
| 候補 R11（B16・B19 の対策） | Agent の指示を2つ追加（重複を判定できないときもファイルごとの件数と金額を示す、非表示の列も DAX で使える）。採用基準は評価の前に記録 |
| R11 の結果 | 標準10問・84条件 **84／78**（T10 は2回とも止められずに回答）、回帰19問 事実 17／内容 15。B16 は PASS、B19 は FAIL のまま、B06・B12・B18 が新しく FAIL。基準（内容 16 以上、B19 の PASS）に届かず**不採用** |
| 本番の Agent | R8 に戻し、定義が R8 の記録と一致することを確認。違いは公開時の説明文だけ（ふだんの言葉の1文に変更） |
| B19 の原因 | Data Agent はモデルで非表示の列（寄附金額・高額寄附フラグ）を使わない。指示だけでは直らず、列を表示にする変更（要承認）が次の候補 |
| 4回目の未公開の確認問題12問 | R11 の前に固定し、本番の構成で1回だけ実行。事実 11／12、内容 10／12（Q04 は B19 と同じ原因、Q11 は登録と発送を分けて書かず） |
| T10 | 本番の R8 で採点に含めずに2回送り、1回は止められ1回は回答。止められるかどうかはプラットフォーム側の判定で変わる |
| Semantic model の説明 | 寄附テーブルの説明7か所（テーブル1、メジャー5、列1）をふだんの言葉に直し、本番に反映して読み戻しで一致を確認。式と DAX の結果は変わらない（94,900件・1,596,157,000円、高額 1,392件） |
| 手順書 | 1章に v3 の構成図を追加（95 ページ、157 検査／0 FAIL）。ポータルの画面の撮り直しは、この環境から画面の画像を取得できないため未実施 |

## 成果物の整合性

| 項目 | 結果 |
|---|---|
| Agent compiler | 4段階（source-grounded → complete-contract → time-layer-isolation → standard-contract-restoration）。commitした入力から再compileした定義が公開中の定義と一致。回答値の混入防止は、桁区切り・全角数字・JSONのエスケープを正規化して検査 |
| Notebook02–04 | 新しいcompilerとprofile入力で再封印。第3報で更新した評価モジュール（native_evaluation）も再封印。第4報で採用したR8のprofileで再び封印し、第5報で成果物一覧のツールの更新にあわせて再封印。第6報でモデルの説明の変更と成果物一覧のツールの更新にあわせて再封印。再buildしてもbytesが一致 |
| artifact-set | **319ファイル**（第5報で参加者用の手順書の原稿3ファイル、第6報で参加者用の画像3ファイルを追加）。全ファイルのGit blobとSHA-256が一致（第6報のソースコミットに再結合） |
| Word / HTML | 第5報で参加者用の版に作り直し、第6報で構成図を追加して**95ページ**。実Word描画・日英HTML・印刷・操作など**157検査／0 FAIL**（作業用・履歴の言葉が含まれていないことの検査を含む） |
| テスト | data-agent 326、provisioning 311、HTML 36（図形の配置のテストを含む）、Ontology 18がPASS。文書テストは386件中385件PASSで、残る1件はPython版に依存する既存の失敗。公開用のテストは51件中42件PASSで、残る9件は2026-09-21版のREADMEの見た目を前提にした既存の失敗（どちらも2026-10-04の`main`で同じ結果） |

## 検証範囲の境界

自動イベント配送と主Ontologyのnative時系列・Metric bindingは、UIでの引き継ぎが残るため
この配置の合格認定に含めていません。Example queriesの検証状態はAPIで確認し、SQL例が
Invalidであることを記録しています。回答評価はAI補助審査で、MCPでは内部クエリは**UNOBSERVABLE**です
（SDKのrun stepsによる観測は診断用で、採点には使いません）。
**AI回答0 FAIL、独立した人間の品質承認、全機能合格は主張しません。**

## English summary

The previous folder was emptied (29 Items; one Eventhouse required purging two
soft-deleted probe Items first) and 21 Items were deployed to the target folder with
one formal Data Agent and no Temp. Increments were delivered manually; automatic
delivery remains unverified. The formal Agent scored 36/84 and 34/84 on the standard
ten/84 as deployed and 74/84 and 73/84 after the standard-contract restoration
(ceiling 77; T10 is blocked natively). The 313-file artifact set has Git blob parity,
and the 232-page guide passed 203 checks. These are separate from AI-answer acceptance.

Same-day follow-up: the six SQL views were verified through the public Data Agent
management API, and the optional Power BI report was deployed and reconciled (22
items). Activator delivery and the time-series binding/Metrics remain UI hand-offs.
All 17 Lakehouse SQL examples fail service validation (KQL 9/9 valid). Candidates R7
and R8 missed the pre-recorded adoption rule, so the Agent was rolled back to the
adopted configuration and verified; a new pre-registered 12-question holdout scored
fact 9/12 and content 7/12 on it. SDK run steps showed T09 executing Kusto and
Lakehouse only.

Fourth same-day report: on the owner's instruction R8 was adopted and verified part
for part (standard ten/84: 76/84 and 74/84). Plain-wording candidates R9 and R10
removed internal terms from the answers (28 answers to 0) but missed the adoption rule
recorded in advance (standard mean 73.0 and 73.5 against 74.5), so production stays on
R8. A third author-written 12-question holdout, frozen before the adoption and run
once on R8, scored fact 11/12 and content 10/12. Two product support cases were filed
through the Fabric admin portal, and the public regression suite grew to 19 questions.
Activator delivery and the time-series steps still need the portal screens; the KQL
data was not cleared.

Fifth report (2026-10-08): the five added regression questions B15–B19 were run once
on R8 (fact 4/5, content 3/5; B16 omitted the per-file counts and amounts, and B19
said the hidden amount column was missing). The Word and HTML guide and the package
were rebuilt as the participant edition: procedure only, in plain wording, with 28
recaptioned screenshots and no evaluation records, history or hashes in the body
(94 pages, 155 checks, 0 failures). The runbook now states that Notebook02 refuses to
run after handoff-ontology.

Sixth report (2026-10-09): candidate R11 added two instructions for B16 and B19 and
was measured with the same procedure and a rule recorded in advance. It scored 84/84
and 78/84 on the standard ten (T10 was not blocked in either run) and fact 17 /
content 15 on the 19 regression questions; B16 was fixed, but B19 still failed and
B06, B12 and B18 regressed, so R11 was not adopted and production was restored to R8
(only the published description changed, to a plain sentence). B19 fails because the
Data Agent does not use columns hidden in the semantic model. A fourth frozen
12-question check set, run once on the final configuration, scored fact 11/12 and
content 10/12. Seven semantic-model descriptions were reworded in plain language and
deployed (read back; DAX results unchanged), the guide gained a v3 architecture
diagram (95 pages, 157 checks, 0 failures), and the portal screenshots could not be
recaptured from this environment.
