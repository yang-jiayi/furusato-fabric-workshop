# 24.8 Gold・Semantic model・Data Agent を完成させる

[Lab 目次](../README.md) · [この章の目次](README.md)

11章へ進み、既に配置した Notebook 05 を開いて自分の Lakehouse を接続します。参加者IDと Files/increment を確認し、APPLY_CHANGES=False で全セルを実行して実際の PLAN_SHA256 を確認します。他の書き込みセッションを閉じ、11章の3つの適用パラメーターを設定して1回実行します。画面実行なので ALLOW_AUTOMATED_APPLY は既定の False のままです。

ANALYTICS_READY の後、11章の画面または SQL で ops.dq_rule_results の7つの品質ルールがPASSかを自分で確認します。次の読み取りコマンドは明示的に OneLake Delta/Parquet を使い、最新 Delta version の active file を実際に読み取って件数を検証します。Gold94,900件・1,596,157,000円、受入増分14,900件・252,058,000円、quarantine100件、Ready と出力世代の一致を検査します。7ルールの判定確認は別です。SQL endpoint に Gold のテーブルが表示されない場合、SQL で推測したり代用したりせず、この明示した読み取り経路を使います。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py verify-gold @Common --gold-method onelake-delta-parquet
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

Semantic model を配布定義から自分の Gold に接続して作成し、初回の Direct Lake refresh と実DAXを順に確認します。各ブロックの成功を見て次へ進みます。モデルはこのコマンドで参加者自身が作成するため、講師による事前配置は不要です。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-semantic-model @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py refresh-model @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py verify-model @Common
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

12章で同じモデルの10メジャーとフィルターを確認できます。Metrics の追加や時系列の状態は主 Ontology のネイティブ機能として別に確認し、未対応の場合もモデル自体の DAX 実行と区別して記録します。

同じフォルダーに Data Agent を1件作り、初期構成を公開します。Lakehouse、KQL Database、主 Ontology、Semantic model と Code Interpreter の配置を読み戻します。初期公開の完了は、今回の調整済みプロファイルの適用や回答品質の合格ではありません。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-agent @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py publish-agent @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

ここで初回配置は完了です。12〜13章の確認を終え、17.5から6つの SQL ビューと選択、9例の直接実行を確認して、17.16で measured-contract-20261015 を同じ Agent に適用・公開・読み戻します。配置の記録フォルダーと、17章のプロファイル適用記録フォルダーは別に保持します。

<details>
<summary>English</summary>

## 24.8 Complete Gold, the semantic model and Data Agent

Go to Chapter 11, open the already deployed Notebook 05 and attach your Lakehouse. Check participant ID and Files/increment, run all cells with APPLY_CHANGES=False and inspect the actual PLAN_SHA256. Close other writing sessions, set the three apply parameters in Chapter 11 and run once. This portal execution keeps ALLOW_AUTOMATED_APPLY at its default False.

After ANALYTICS_READY, inspect ops.dq_rule_results through the Chapter 11 UI or SQL and confirm all seven quality rules PASS. The following read-only command explicitly uses OneLake Delta/Parquet and counts rows from the actual active files in the latest Delta version. It checks Gold 94,900 rows / JPY 1,596,157,000, accepted increments 14,900 / JPY 252,058,000, quarantine 100, Ready state and matching output generations. Checking all seven rule verdicts is separate. If Gold tables are not visible in the SQL endpoint, do not infer or substitute a SQL result; use this explicit read path.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py verify-gold @Common --gold-method onelake-delta-parquet
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

Create the semantic model from the supplied definition against your Gold, then verify its initial Direct Lake refresh and actual DAX. Inspect each block before continuing. These commands create the model for you; an instructor does not need to deploy it first.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-semantic-model @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py refresh-model @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py verify-model @Common
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

Chapter 12 lets you inspect this same model's ten measures and filters. Check Metrics and time-series state as separate native capabilities of the main ontology, distinguishing unsupported cases from actual model DAX execution.

Create one Data Agent in the same folder and publish its initial configuration. Read back the Lakehouse, KQL database, main ontology, semantic model and Code Interpreter configuration. Initial publication does not establish application of the adopted tuned profile or passing answer quality.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-agent @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py publish-agent @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

The initial deployment is complete. Finish the Chapter 12–13 checks, then start at 17.5 to prepare six SQL views, selections and direct execution of nine examples. Use 17.16 to apply, publish and read back measured-contract-20261015 on the same agent. Retain separate record folders for resource deployment and Chapter 17 profile application.

</details>
