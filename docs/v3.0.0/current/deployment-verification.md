# 新規配置・回答精度改善の検証 — 2026-10-07

**旧フォルダ（20261006）を空にし、指定フォルダ（20261007）へ21 Itemsを新規配置しました。
正式Agentの標準10問・84条件は初回36/84・34/84で、回答契約の復元後は74/84・73/84です。
成果物の整合性とAI回答品質は別の判定です。**

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
年なしの「8月」を静的seedの2025年と解釈して2026年8月の観測を0件としたことでした。
6構成の全経過、事前登録holdout（11 PASS／1 FAIL）、残件は
[2026-10-07追補](../tuning-20261007/README.md)にあります。
T10はnativeのコンテンツフィルターで遮断され、回避せずFAILとして数えています（上限77）。

## 第3報（同日）: 手順の逸脱の完了と対策

| 項目 | 結果 |
|---|---|
| Agent の SQL ビュー要素 | 公開の Data Agent 管理 API で、6 views が View・Available・選択済み、列が INFORMATION_SCHEMA と一致することを確認 |
| 任意の Power BI レポート | 既存モデルに接続するレポートだけを配置。PDF で表示を確認し、DAX で Gold 94,900件／1,596,157,000円・高額1,392件と一致 |
| `handoff-ontology` | 承認済みコミットのソースで記録（配置時の source fingerprint を維持） |
| Activator の自動配送 | **UI での引き継ぎ**。ルールのアクションがバンドル側の Pipeline 接続を参照しており、Edit action → Apply → Save が必要。手動取り込み済みのため、再配送の前に承認されたリセットが必要 |
| 時系列バインド・native Metrics | **UI での引き継ぎ**（定義形式と Generate Ontology の API が公開されていない） |
| Example queries の検証状態 | KQL 9件は Valid、Lakehouse の SQL 17件はすべて Invalid（検証がエンドポイントに接続できない。実行時の SQL は成功）。製品サポートへの報告案を作成 |
| 残件への候補 R7・R8 | 事前に記録した採用規則を満たさず不採用（R7: 69／76、R8: 76／74・拡張の内容 11）。正式 Agent を R6 に戻し、14 パーツの一致を確認 |
| 新しい事前登録 holdout 12問 | R6 で1回だけ実行。事実 9／12、内容 7／12 |
| 実行ソースの観測 | Temp の一時ノートブックで SDK の run steps を取得（使用後に削除）。T09 は Kusto と LakehouseTables だけを実行し、Ontology は実行していない |

詳細は[第3報](../followup-20261007/README.md)と[製品サポートへの報告案](../followup-20261007/platform-support-cases.md)にあります。

## 成果物の整合性

| 項目 | 結果 |
|---|---|
| Agent compiler | 4段階（source-grounded → complete-contract → time-layer-isolation → standard-contract-restoration）。commitした入力から再compileした定義が公開中の定義と一致。回答値の混入防止は、桁区切り・全角数字・JSONのエスケープを正規化して検査 |
| Notebook02–04 | 新しいcompilerとprofile入力で再封印。第3報で更新した評価モジュール（native_evaluation）も再封印。再buildしてもbytesが一致 |
| artifact-set | **313ファイル**。全ファイルのGit blobとSHA-256が一致（第3報のソースコミットに再結合） |
| Word / HTML | **232ページ**。実Word描画・日英HTML・印刷・操作など**203検査／0 FAIL**（第3報で19章のT10注記を追加して再生成） |
| テスト | data-agent 325、provisioning 308がPASS。文書テストは380件中379件PASSで、残る1件はPython版に依存する既存の失敗（未変更の`main`でも同じ結果）。全体実行中に一時フォルダーのアクセス拒否が1件出たテストは、単独の再実行で32件すべてPASS |

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
