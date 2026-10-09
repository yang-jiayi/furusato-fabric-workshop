# Measured contract — 2026-10-09

## 日本語

2026-10-09 の実回答検証で採用した最終構成の、移植可能な指示・選択契約です。
過去の `standard-contract-restoration` と、この日付の R8〜R11 は別の検証系列です。
このディレクトリーは最新系列の R11 指示を保持します。実環境 ID、認証、質問別の正解、
回答ログは含みません。有限の実回答テストで確認した改善と未解決事項は
[測定結果](../../../../../docs/v3.0.0/tuning-20261010/README.md) に記載します。
最新 R11 の全 51 問は再評価していないため、R8 の全体得点を R11 の全体精度と表示しません。

`Notebook 04` の初期構成を作った後に明示的に適用します。Compiler の成功はローカル
Draft の作成であり、Fabric への適用・Publish・新しい環境の回答品質を意味しません。
既存 Agent を初期定義へ戻すために Notebook 04 を再実行しないでください。

### 必要な構成

標準 **Gen2 Ontology 1 個**、Lakehouse SQL、KQL Database、Semantic Model の 4 ソースを
使います。追加の互換 Ontology は作りません。Code Interpreter を有効にします。
SQL の 6 ビューは既存の公開定義から作成・照合します。

- [`source-grounded/views`](../source-grounded/views/): `agent_donation_detail`、
  `agent_donor_catalog_supplier`、`agent_municipality_snapshot`、`agent_supplier_catalog`。
- [`complete-contract/views`](../complete-contract/views/): `agent_prefecture_category_metric`、
  `agent_relationship_dictionary`。関係辞書は宣言を示し、実行済みグラフの証拠を代用しません。

Notebook 05 の処理と SQL endpoint の同期が完了してから、次の実オブジェクトを選択します。
選択する列・型・説明の完全な一覧は [`selection-contract.json`](selection-contract.json) です。

| ソース | 選択範囲 |
|---|---|
| Lakehouse SQL | 上記 6 ビュー、および `dbo.ot_prefecture`、`ot_donor`、`ot_gift_category`、`ot_gift`、`ot_mun_category_metric`、`ot_pref_donation_flow` |
| Lakehouse SQL の品質処理 | `bronze.donation_events_raw`、`silver.donation_event`、`quarantine.donation_events_rejected`、`ops.analytics_publish_control`、`ops.dq_rule_results` |
| KQL Database | `DonationObservationSummaryForAgent` の 10 列。生観測は重複込み。KQL のこの MV に `EventID` はありません |
| Semantic Model | 既存のテーブル・10 メジャーを保持。`寄附[寄附金額]` は非表示を解除して選択し、10 個の既存メジャーの実定義を照合 |
| Gen2 Ontology | 同じ標準アイテムの実選択を保持。追加アイテムを作って consumer エラーを隠さない |

SQL は合計 17 オブジェクト・141 列です。SQL の品質 3 表では `EventID` を選択できますが、
これは KQL MV の一意キー追加を意味しません。静的・生観測・受入済み Gold・品質処理は別の
母集団として扱います。Ready control の generation/run を集計前後に照合します。

### 指示と例

Global、SQL、KQL、Semantic Model、Ontology の各指示は 10,000 UTF16 単位以内です。
実 SQL の識別子を `[...]` で囲み、条件付き集計と順位で同じ母集団を使います。
AM/PM を実 UTC の 24 時間へ正規化し、JST の日付跨ぎを保持します。
件数メジャーの `KEEPFILTERS` は実モデルの DAX 定義から照合し、外側フィルターとの共通部分と
通常 `CALCULATE` の同じ列に対する置換を区別します。`BLANK` を無条件で 0 に変換しません。

| 指示ファイル | UTF16 単位 |
|---|---:|
| [`global-instructions.txt`](global-instructions.txt) | 9,981 |
| [`lakehouse-instructions.txt`](lakehouse-instructions.txt) | 9,989 |
| [`kusto-instructions.txt`](kusto-instructions.txt) | 8,665 |
| [`semantic-model-instructions.txt`](semantic-model-instructions.txt) | 6,989 |
| [`ontology-instructions.txt`](ontology-instructions.txt) | 4,963 |

実環境で staging 検証に失敗した 17 SQL fewshot は現行構成から除外します。
過去の公開ファイルは履歴として保持します。現行の 9 KQL 例は
[`kusto-examples.json`](kusto-examples.json) に質問・クエリーだけを保存します。
別環境では、すべての例を実ソースで read-only 実行し、staging 側の Valid 判定も確認します。
ローカルで例を読み込めたことはサービスの Valid 判定を証明しません。

### ローカル Draft の作成

1. 実際の Agent `getDefinition`、Semantic Model の TMDL `getDefinition`、標準 Ontology の
   アイテムメタデータを Git 外の非公開ディレクトリーへ保存します。公開 API の `type=Ontology`
   だけでは generation を判定できません。実 native metadata の `objectId`、`artifactType=Ontology`、
   `extendedProperties.FeatureLevel=2` と managed children を含む readback を保存します。
   アイテムの type を手で `Gen2Ontology` に書き換えないでください。
2. SQL endpoint で [`sql-schema-inventory.sql`](sql-schema-inventory.sql) を実行し、
   `TABLE_SCHEMA`、`TABLE_NAME`、`COLUMN_NAME`、`DATA_TYPE` を持つ JSON 配列として保存します。
3. Agent のソーススキーマを更新し、6 ビューと 5 品質表を含む実 native selection nodes を取得します。
   欠落した ID・列・型を手で作らないでください。Semantic Model では金額列と 10 個の既存メジャーが
   選択済みであり、実 TMDL の金額列が非表示ではないことが前提です。
4. 実際に入力する stage を `published` または `draft` と明示して compiler を実行します。

```powershell
python -B .\tools\data-agent\measured_contract_profile.py `
  --definition 'C:\private\agent-readback.json' --input-stage published `
  --sql-columns 'C:\private\sql-columns.json' `
  --model-definition 'C:\private\semantic-model-readback.json' `
  --ontology-item 'C:\private\ontology-item.json' `
  --output 'C:\private\new-run\agent-draft.json' `
  --receipt 'C:\private\new-run\compile-receipt.json'
```

Linux では絶対パスを `/var/tmp/...` などへ置き換えます。出力先は新しい別ファイルにします。
Compiler は実ソース ID、native metadata、実メジャーを保持し、観測した SQL/KQL の選択と
指示・説明・KQL 例を契約に合わせます。Published とその他の非 Draft パートはバイトのまま
保持します。Ontology/Model の選択・Code Interpreter・モデルメジャー・元データを変えません。
不足スキーマ、独立した SQL 型情報との不一致、Gen1/追加 Ontology、変更されたメジャー、
非表示の金額列、未選択メジャー、追加 topics は停止して実状態の確認を求めます。

### 適用・Publish・校正

5. 管理者/講師が同じ Agent の Draft に生成定義を適用し、Draft readback と receipt を照合します。
   UI の場合は 5 指示本文、4 ソース説明、完全な列選択、SQL 例 0、KQL 例 9 を同じ契約に合わせます。
6. 例の実照会とサービスの validation を確認して、同じ Agent を Publish します。
   Published readback を取得し、5 指示・4 ソース ID・1 Ontology・実選択・9 例を照合します。
7. [校正・資料の整合性手順](../../../../../docs/v3.0.0/tuning-20261010/calibration-and-proofreading.md)
   に従い、元の質問・条件を凍結した新規 campaign を 1 回だけ実行します。全問と未使用の
   held-out を残し、成功した質問だけの選別、期待値の指示への追加、同じ質問の再送を避けます。
   誤差、native エラー、`UNCLEAR`、証跡不足、スコープが変わった条件をそのまま報告します。

Ontology consumer の API version エラー、native Time Series/Metric、金額列の Agent schema 欠落、
Report のブラウザー表示や Activator の自動配送は、指示だけで成功したと扱えません。
Direct GQL や DAX engine の成功も Agent consumer の成功と区別します。

認証・接続なしのローカル検証:

```powershell
python -B -m unittest discover -s .\tools\data-agent\tests -p "test_measured_contract_profile.py"
```

## English

This portable contract retains the instruction texts and selected schema of the
measured 2026-10-09 R11 publication. It contains no live identities, credentials,
answer logs or answer keys. R8–R11 in this dated series are separate from the older
2026-10-07 series. See the linked measurement report for the bounded improvements,
retained failures and the absence of a full 51-question retest on final R11.

Use one standard Gen2 Ontology and the existing SQL, KQL and Semantic Model sources.
The measured public API calls its type `Ontology`; retain the actual native item
metadata with `FeatureLevel=2` and the observed managed child roles rather than
relabeling a public response as `Gen2Ontology`. A public type label alone does not
verify generation or consumer readiness.
Create and verify the six existing public SQL view definitions, finish Notebook 05,
refresh real service-discovered metadata and run the read-only SQL inventory. SQL
selects 17 objects / 141 fields; KQL selects the ten-field observation MV without
EventID. EventID in the three SQL quality populations does not add a KQL unique key.
Static, raw observations, accepted Gold and quality-processing populations remain
separate. Preserve actual Ready generation/run and requested file/run/alias scope.

The command above compiles locally from an explicitly chosen actual input stage.
It verifies all ten source-owned workshop measures, requires a visible and selected
amount column, and refuses missing IDs, schema/type drift, extra sources/topics or
unrecognized model definitions. It changes Draft instructions, descriptions,
observed SQL/KQL selection and examples only. Published evidence, source identities,
Ontology/Model selections, Code Interpreter, business data and measures are retained.
No credentials or cloud calls are used. Outputs must be fresh absolute private paths.

Apply to the same Agent, validate every example on the real source and in staging,
publish and reconcile the actual readback before evaluation. Use zero SQL examples
and the nine generic KQL examples; failed historical SQL example files remain history.
Do not reset the Agent by rerunning its factory Notebook. A successful local compile
or HTTP/response completion is not proof of deployment, native execution or answer
accuracy. Retain native failures and incomplete evidence in a fresh frozen evaluation.
