# 24.7 Activator を準備して3ファイルを取り込む

[Lab 目次](../README.md) · [この章の目次](README.md)

9章の手順1〜2で Pipeline と Activator を開き、ルールが停止中であること、正しい Pipeline と Type・Subject・Source の対応を確認します。Edit action → Apply → Save を1回実施し、履歴適用を無効、遅延待機を2分にします。認証の初期化を確認するためのネイティブ画面操作です。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py start-activator @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

start の armed_unverified は開始操作の記録で、まだ取り込み成功ではありません。次の読み取り確認で backendRunningState=Running、isRuleInSync=true、正常な health、アクション資格情報 Initialized を確認します。未準備ならアップロードせず、読み取り確認だけを再実施します。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py check-activator-readiness @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

この参加者用経路では、9章の手順4以降で Fabric の画面から001を1回だけアップロードし、FileCreated → activation → Pipeline Succeeded → Copy 5,000行 → KQL の件数・金額を確認します。記録はUIで確認した根拠として保存します。続いて10章で002、003をそれぞれ前の成功確認後に1回だけ送ります。各ファイルの前に上の readiness 確認を繰り返します。

配布ファイルは source/workshop/v3.0.0-preview/data/increment にあります。この経路では画面でのアップロードと CLI の deliver-increment を併用しません。画面の記録を、CLI の verify-delivery が実行済みという記録に置き換えません。送信が不明なら再アップロードせず、9章の実行履歴と件数で調べます。自動処理の進行中に手動 Pipeline を重ねません。

3ファイルについて15,000観測行、一意EventID14,900件、金額253,886,000円を10章で確認してから、次のコマンドでルールを停止します。すでに画面で停止した場合は現在の状態を確認し、開始して停止し直す必要はありません。停止後も履歴は保持します。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py stop-activator @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

<details>
<summary>English</summary>

## 24.7 Prepare Activator and ingest three files

Follow steps 1–2 in Chapter 9 to open the Pipeline and Activator. Confirm the stopped rule, intended Pipeline and Type/Subject/Source mappings. Do Edit action → Apply → Save once, leave historical application off and set the late-arrival wait to two minutes. This native UI step initializes the action configuration for verification.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py start-activator @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

The start result armed_unverified records a start operation, not successful ingestion. The following read check requires backendRunningState=Running, isRuleInSync=true, healthy state and Initialized action credentials. If not ready, do not upload; repeat only the read check.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py check-activator-readiness @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

In this participant route, use the Fabric UI from step 4 of Chapter 9 to upload 001 once. Verify FileCreated → activation → Pipeline Succeeded → Copy of 5,000 rows → KQL counts and amounts. Save the observations as UI evidence. Then follow Chapter 10 to upload 002 and 003 once each, only after confirming the previous file, and repeat the readiness read check before each file.

The files are in source/workshop/v3.0.0-preview/data/increment in the ZIP. Do not combine this route's UI uploads with CLI deliver-increment, and do not label UI evidence as a completed CLI verify-delivery. On uncertain upload, inspect Chapter 9 history and counts without uploading again. Do not manually run a Pipeline while automatic processing may still be in flight.

After Chapter 10 confirms 15,000 observation rows, 14,900 unique EventIDs and JPY 253,886,000 across the three files, stop the rule with the next command. If already stopped in the UI, inspect the current state; do not start it just to stop it again. Retain the history.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py stop-activator @Write
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

</details>
