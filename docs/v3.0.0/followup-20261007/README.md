# 手順の逸脱と対策の完了 — 2026-10-07（第3報）

**2026-10-07 の配置で残っていた手順の逸脱4件と、対策 E・F・G、残件（T09・H09・欠落・B02・観測性）を
優先度順に実施しました。逸脱は2件完了、2件は UI でしか行えない手順が残り、手順書（引き継ぎ）を整備しました。
残件への新しい候補 R7・R8 は、事前に記録した採用規則を満たさなかったため採用せず、
本番の Agent は第2報の採用構成（R6）のままです。**

[結果 JSON](result-followup-20261007.json) ·
[製品サポートへの報告案](platform-support-cases.md) ·
[R8 候補の指示差分](r8-candidate-contracts.diff) ·
[運用手順（引き継ぎ）](../../../workshop/v3.0.0-preview/README-runtime.md) ·
[回帰ゲート](../../../tools/data-agent/README.md) ·
[SHA-256](SHA256SUMS.txt)

## 手順からの逸脱

| # | 逸脱 | 状態 | 内容 |
|---|---|---|---|
| 1 | Activator による増分の自動配送 | **引き継ぎ（UI）** | バンドルから作られたルールのアクションはバンドル側の Pipeline 接続を参照しており、この配置の Pipeline への結び付けは Activator の UI（Edit action → Apply → Save）でしか行えません。増分は手動で取り込み済みのため、再配送には承認されたリセット（KQL の clear と CSV 削除）が先に必要です。読み戻しの基準とリセット手順を手順書に記載しました |
| 2 | Agent の SQL ビュー要素 | **完了（サービスで確認）** | 公開の Data Agent 管理 API で、6つのビューが View・Available・選択済み、列が INFORMATION_SCHEMA と一致（`agent_donation_detail` の `DonationDataLayer` は未選択）、重複する `ot_*` テーブルは未選択であることを確認 |
| 3 | 時系列バインドと native Metrics | **一部完了・引き継ぎ（UI）** | `handoff-ontology` を承認済みのソースで記録。Eventhouse の時系列バインドは定義形式が公開されておらず、Generate Ontology にも API がないため UI 専用。設定値、331件 / 5,737,000円の確認、Notebook02（98 オブジェクト）、Temp での Metrics を手順書に記載 |
| 4 | 任意の Power BI レポート | **完了** | 既存モデルに接続するレポートだけを配置し、定義を読み戻し。テナントで画像出力が無効なため PDF で表示を確認。DAX で Gold 94,900件 / 1,596,157,000円、高額 1,392件と一致。フォルダーは 22 Items |

## 対策

| 対策 | 実施内容 |
|---|---|
| **E** T10 の遮断 | 採点に「プラットフォーム遮断」の区分を追加（厳密な分母は変えず FAIL のまま、診断用の内訳だけを別に出す）。ガイド19章に教材の注記。サポートへの報告案。関連する3つの質問では遮断されず Agent が正しく拒否したため、遮断は「特定の上位個人」＋「年収・控除額」の組合せに限られます |
| **F** 回帰ゲート | 拡張14問（B01–B14）を公開の回帰スイートとして追加。期待値は同梱 CSV・TMDL・Notebook05・Ontology 契約から再計算し、調整時にライブソースで確かめた値と全問一致。`evaluate_native.py` が `regression` を凍結・事前登録・実行・報告できるようにしました |
| **G** 手順書 | 承認済みコミットでの段階実行、Notebook05 の plan hash（ヘルパー付き）、ビューと例の検証状態のサービス確認（ツール付き）、レポートのみの配置、Activator と時系列の引き継ぎ |

## 残件への候補（採用せず）

採用規則（標準10問2回の平均 ≥ 73.5、拡張の内容 PASS ≥ 13、事実 PASS ≥ 13）は、各候補の結果を見る前に記録しました。

| 構成 | 標準84（1回目／2回目） | 拡張 事実 / 内容 | 判定 |
|---|---:|---:|---|
| R6（採用中） | 74 ／ 73 | 14 / 13 | — |
| R7 3ソースの順序・重複の有無・回答前確認・KEEPFILTERS 対比 | 69 ／ 76 | 13 / 13 | 不採用（平均 72.5） |
| R8 R7＋突き合わせキーを先頭に・人気の値を必須に | 76 ／ 74 | 12 / 11（B11 は通信タイムアウトで不明） | 不採用（拡張の内容 11） |

R8 では T09 が2回とも 8/8 になり、標準の平均は 75.0 でした。一方で T07 の raw 総数の欠落、B08 の取得失敗、
B02 の KEEPFILTERS に触れない説明が出ました。規則どおり R6 に戻し、Draft・Published の 14 パーツすべてが
R6 と一致することを確認しています。R8 の指示差分は[こちら](r8-candidate-contracts.diff)にあり、採否はご判断ください。

**事前登録した新しい holdout 12問**（R7 の前に SHA-256 で固定し、採用中の R6 で1回だけ実行）は
**事実 9 / 12、内容 7 / 12** でした。失敗は、3ソースの複合質問で Ontology を使わない、重複の有無を断定する、
BLANK の理由に KEEPFILTERS を使わない、合算拒否で対象月ではなくスナップショット全体を示す、
57,000円ちょうどの件数を「算出できない」とする、の5件です。前の3つは R7・R8 が対象とした分類と同じです。
著者が作成した問題で、独立した評価ではありません。

## 観測性とサービスの状態

- Fabric ノートブック内の SDK の run steps で実行内容を確認しました（Temp の一時ノートブックで実行し、使用後に削除）。
  R6 の標準 T09 は Kusto と LakehouseTables だけを実行し、Ontology は実行していません（第2報の推定を確認）。
- Example queries の検証状態: Lakehouse の SQL 例 17件はすべて Invalid（検証がエンドポイントに接続できない）、
  KQL 9件はすべて Valid。run steps では SQL 例も読み込まれますが、例の照合で返ったのは KQL だけでした。
  サポートへの報告案に含めています。

判定は固定期待値と回答本文を照合した AI 補助審査です。ライブ ID・回答本文・holdout の質問は公開していません。

## English summary

All four procedural deviations of the 2026-10-07 deployment were addressed in priority
order. Two are complete: the Data Agent's six SQL views are verified through the public
management API, and the optional Power BI report is deployed and reconciled (22 items).
Two depend on native UI steps that cannot be automated here, so they are documented as
hand-offs: initializing the Activator action (plus an approved reset before any
re-delivery) and the Eventhouse time-series binding, Notebook02 and native Metrics
(`handoff-ontology` is recorded).

Countermeasures E, F and G are implemented: a strict-denominator-preserving
`platform_blocked` classification, a guide note and support drafts for T10; a public
regression suite B01–B14 whose expected values are recomputed from repository sources
and wired into `evaluate_native.py`; and runbook sections with helper tools.

Two residual-fix candidates were evaluated against an adoption rule recorded before
their results: R7 (69/76; extended 13/13) and R8 (76/74; extended 12/11 with one
transport timeout). Neither met the rule, so production was rolled back to R6 and
verified part-for-part. A new pre-registered 12-question holdout, run once on R6,
scored fact 9/12 and content 7/12; its failures repeat the residual categories.
SDK run steps confirmed that R6 answers T09 without executing the Ontology. All 17
Lakehouse SQL examples fail service validation while all 9 KQL examples pass; both
platform issues are drafted for product support. This is AI-assisted review of answer
text, not independent human acceptance.
