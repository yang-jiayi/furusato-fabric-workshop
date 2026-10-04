# v3成果物整合性・正式配置の検証 — 2026-10-04

**指定フォルダへの正式配置と、Notebook・CSV・Word/HTMLの整合性を確認しました。
AI回答品質は別の判定で、最新の既知10問には2 FAILが残っています。**

## 削除とTemp

旧環境の23 Itemsは完全削除し、active/recoverableの両方から消えたことを確認しました。
最初の通常削除が失敗した理由は次のとおりです。

| 対象 | 実際の応答・対応 |
|---|---|
| Semantic Model、Activator、Eventhouse、KQL Database | `ItemTypeNotSupportedForSoftDeletion`。承認済みの完全削除に切り替えて成功 |
| Lakehouse、Pipeline | 通常削除では非再試行の`UnknownError`。同じ通常削除を繰り返さず、完全削除APIで成功。内部原因は公開応答からは特定不能 |
| SQL Endpoint・その他managed children | 親からの削除が必要。確認済みの親子関係に沿って親の削除により除去 |
| 復元可能なItems | active用APIではなく、専用`recoverableItems` APIで完全削除 |

新環境のTempは、比較用Agentと静的consumer Ontologyの隔離に使われていました。
修正版Agentに必要なOntologyとmanaged childrenを消してしまわないよう、まず親のMoveItemで
**4 Itemsを正式フォルダ直下へ移動**し、ID・定義・source bindingが変わらないことを確認しました。
正式Agentへ修正版profileを反映して評価した後、不要な比較Agent2件と空のTempを削除しました。
この2 Agentは通常削除のため復元可能です。旧環境23 Itemsの完全削除とは別の操作です。

最終のactive状態は**21 Items、Data Agent1件、Tempフォルダ0件**です。
正式Agentの4ソースもすべて同じ指定フォルダ直下にあります。
旧root/旧Tempは最後の再取得時には既に存在しなかったため、再作成や追加の削除はしていません。

## v2.7表記とv3の整合性

| 項目 | 最終確認 |
|---|---|
| 教材・配布Notebook版 | `WORKSHOP_VERSION=3.0.0`。全5 Notebookの見出し・metadataを一致 |
| Notebook01の`NOTEBOOK_VERSION` | 配布版・監査表示として3.0.0へ変更 |
| Notebook01/05の処理ロジック | 上記Notebook01の監査・表示用値を除いて元コードと一致 |
| 既存実行の監査記録 | 実行当時の2.7.0等の来歴を保存。新しい版として偽装する更新はしない |
| CSV | 11ファイルすべて元のbytesと一致。データ仕様`2.7.0-realistic.1`を保持 |
| 内部publication key・generation・API互換性番号 | データ/API契約として維持。教材版3.0に一律置換しない |
| Notebook02–04のsealed package | 最新の3段階Agent compiler、6 SQL views、SQL/KQL例を収録。内部モジュールのhashとGit blobを照合 |
| Word / HTML | 同じ共有原稿・artifact-set SHAで生成。実Notebookのliteralパラメーターを掲載 |

整合性manifestは**305ファイル**を対象とし、Gitに格納されたbytesと作業ファイルが一致することを
確認しました。技術的パス`v3.0.0-preview`、基線用`VERSION=2.7.0`、CSV仕様2.7と、
教材版3.0.0はそれぞれ役割が異なります。

Wordは**232ページ**です。実Word描画、日英HTML、印刷、操作、内部リンク、共有本文、
対応するWordのSHA等の**203検査は0 FAIL**でした。
途中で見つけた付録anchorの重複と目次末尾の孤立ページは修正し、失敗時のprivate証拠を保持しています。

## データ・実行・モデル

| 検証対象 | 実結果 |
|---|---:|
| 静的寄附 | 80,000件／1,344,099,000円 |
| Pipelineの手動Copy | 3回、各5,000行。全列・重複込みの元CSVと照合 |
| Eventhouse raw | 15,000件／253,886,000円 |
| 品質処理後の受入増分 | 14,900件／252,058,000円 |
| 隔離 | 100件 |
| Gold全体 | 94,900件／1,596,157,000円 |
| Notebook01・05 | 各1回Completed。版/定義更新に伴う再実行0回 |
| Model | Direct Lake refresh Completed。実DAXの静的・増分値と、両向きの相反するsource filterのBLANKを確認 |
| 静的consumer Graph | 109,592 nodes／297,303 directed edges。3 GQL検査と経路連続性を確認 |
| Agent source例 | SQL15件・KQL6件を実ソースで検証し、native例検証のerror/pendingなしを確認 |

GoldはEventhouseから作ったものではなく、検証済みのLakehouse staged CSVから独立に処理しました。
Pipelineの3回は**手動**です。自動イベント配送と読み替えません。
Activatorは停止状態・安全な既定値を維持しています。

## 既知10問の回答評価

質問・oracle・必須条件は変更していません。各構成の各問は1回のみで、
過去の正答の選び集め、同一構成の再送、旧UNKNOWN質問の再実行はありません。

| 構成 | 事実 P / F / U | 必須条件を含む内容 P / F / U |
|---|---:|---:|
| 初回の新環境・比較用Agent | 8 /2 /0 | 7 /3 /0 |
| 整合版・正式フォルダの正式Agent | **8 /2 /0** | **8 /2 /0** |

初回の3問題（時間集約行をsource bucket行と説明、月指定だけのGoldへStaticSeedを追加、
高額フラグ条件があるのにStaticSeed全行と説明）は、最後の構成で改善を確認しました。
一方、最後の構成には以下の2件が残っています。

| ケース | 残るFAIL |
|---|---|
| F30-O11 | JSTの月またぎ観測を「存在しない」と回答。実ソースでは178件／3,177,000円、UTCの実観測範囲は2026-08-31 15:00:05〜23:58:20 |
| F30-D09 | BLANKという数値結果は正しいが、`KEEPFILTERS`固有の交差をDAX同一列filter全般へ誤って一般化。通常の`CALCULATE`は上書き得る |

この2件はNotebook/CSVの版ずれや欠落で説明できる状態ではなく、
native回答が検証済みソースや実メジャー定義と食い違ったものです。
内部生成クエリは**UNOBSERVABLE**なので、見えていない具体的な生成条件を原因と断定しません。
**AI回答0 FAIL、元32/100問全体の合格、独立holdout、人間による品質承認は主張しません。**

## 検証範囲の境界

主Ontologyのnative時系列・Metric binding、および自動イベント配送は、この配置での合格認定に
含めていません。source-owned DAXや別の静的Graphの成功を、その代わりにしません。
本配置で正式Agentを1件にしたのはユーザー指定の配置形態であり、一般的なAI品質合格とは別です。

元3.0.0タグ、旧Word/HTML、過去の評価結果は保持しています。
過去のUNKNOWNであるF30-N10は再送していません。
版・配布物の整合性、実データの整合性、AI回答品質は別々に報告しています。

## English summary

The current v3 source set, five deployed Notebooks, unchanged CSVs and full
Word/HTML guide are hash-bound and checked. Production now has21 active Items,
one formal Data Agent and no Temp folder. Necessary compatibility dependencies
were moved without changing their IDs; unused comparison Agents were deleted
normally and remain recoverable.

The232-page guide passed203 local checks. Data, explicit manual Copies, source-owned
DAX and static GQL were verified without rerunning completed data notebooks.
The final known10 native answer check is **8 PASS /2 FAIL /0 UNKNOWN**.
Artifact consistency does not imply zero-failure AI acceptance, automatic event
delivery, native time-series/Metric certification or a new independent holdout.
