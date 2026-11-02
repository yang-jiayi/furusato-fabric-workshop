# 24.6 基盤と Notebook を配置する

[Lab 目次](../README.md) · [この章の目次](README.md)

以下は1ブロックずつ実行し、成功結果を確認してから次へ進みます。最初の段階は Lakehouse、Notebook 01、Eventhouse を作り、8つの CSV を置いて Notebook 01 を1回実行します。増分3ファイルは監視対象の Files/increment の外へ待機配置されます。5章のアップロードや Notebook 01 の Run all を重ねて行いません。

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-sources @Write --run-notebook01<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-sources @Write --run-notebook01
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

次の確認では SQL endpoint の実際の20テーブルと、静的データ80,000件・1,344,099,000円を照合します。同期が未完了の場合は、作成を繰り返さず同期状態を確認します。

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py verify-sources @Common<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py verify-sources @Common
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

Notebook 02〜05を取り込みます。この段階では実行しません。Notebook 05 は11章で参加者がプレビューしてから実行します。

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-notebooks @Write<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-notebooks @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

KQL のテーブル・マッピング・集計ビュー、Pipeline と停止した Activator を作ります。8章で定義を確認し、既にある管理コマンドをもう一度実行しません。

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-realtime @Write<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-realtime @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

主 Ontology を1件作り、Gen2、10 Entity、72静的 Propertyと1時系列 Property、15 Relationship を読み戻します。6〜7章では既存のキー・型・バインド・関係を確認し、同じものを追加しません。時系列はこの時点では未バインドです。

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-core @Write<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-core @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

次の handoff は、以後この Ontology をネイティブ画面で扱うという記録を残し、自動 TMDL 上書きを禁止します。実行後は Notebook 02 や deploy-core で主 Ontology を置き換えません。10章の時系列、12章の Metrics のネイティブ操作はこの後に行います。既定の4つの Rule の文は配置に含まれるので、標準構成のために Notebook 02 を追加実行する必要はありません。

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py handoff-ontology @Write<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py handoff-ontology @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

作業フォルダーのアイテム名と DeploymentPrivate/deployment-state.json の items を照合します。これで Pipeline と Activator を自分で用意できました。次に5〜8章の確認表を使い、作成操作の代わりに実データと設定を確認してから24.7へ進みます。

<details>
<summary>English</summary>

## 24.6 Deploy core resources and Notebooks

Run one block at a time and inspect its successful result before continuing. The first stage creates the Lakehouse, Notebook 01 and Eventhouse, uploads eight CSVs and runs Notebook 01 once. The three increments are staged outside the watched Files/increment directory. Do not repeat the Chapter 5 uploads or Notebook 01 Run all afterwards.

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-sources @Write --run-notebook01<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-sources @Write --run-notebook01
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

The next check reads the actual SQL endpoint's 20 tables and verifies static totals of 80,000 donations and JPY 1,344,099,000. If synchronization is pending, inspect its state rather than repeating creation.

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py verify-sources @Common<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py verify-sources @Common
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

Import Notebooks 02–05 without executing them. You preview and run Notebook 05 in Chapter 11.

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-notebooks @Write<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-notebooks @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

Create the KQL table, mapping and aggregate view, Pipeline and stopped Activator. Inspect their definitions in Chapter 8 without rerunning existing management commands.

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-realtime @Write<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-realtime @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

Create one main ontology and read back Gen2, ten entities, 72 static plus one time-series property and 15 relationships. In Chapters 6–7, inspect the existing keys, types, bindings and relationships without adding duplicates. The time series is still unbound at this stage.

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-core @Write<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py deploy-core @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

The handoff records that the ontology will now be managed through native UI and disables automated TMDL replacement. Afterwards, do not replace the main ontology with Notebook 02 or deploy-core. Perform Chapter 10 time-series and Chapter 12 Metrics native operations afterwards. Deployment already includes the four default rule statements, so the standard setup does not require running Notebook 02.

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py handoff-ontology @Write<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py handoff-ontology @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

Compare the folder item names with items in DeploymentPrivate/deployment-state.json. You have now provisioned the Pipeline and Activator yourself. Use the Chapter 5–8 check tables to inspect data and configuration instead of repeating creation, then continue to 24.7.

</details>
