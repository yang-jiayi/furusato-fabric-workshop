# 24.5 配置計画を読み、自分の範囲を承認する

[Lab 目次](../README.md) · [この章の目次](README.md)

フォルダーの対応を確認できたら、次のコマンドで自分の scope.json を作ります。forbiddenItemIds は操作対象外として明示された既存アイテムがあれば、その GUID を配列に入れます。空配列でも、配置ツールは他人の既存アイテムを引き継いだり上書きしたりしません。

**Readable wrapped view — PowerShell**

<div>
$ScopeDocument = [ordered]@{<br>
  tenantId = $TenantId<br>
  workspaceId = $WorkspaceId<br>
  workspaceName = $WorkspaceName<br>
  folderId = $FolderId<br>
  portalSubfolderId = $PortalSubfolderId<br>
  participantId = $ParticipantId<br>
  folderMappingVerified = $true<br>
  forbiddenItemIds = @()<br>
}<br>
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)<br>
[IO.File]::WriteAllText($Scope, ($ScopeDocument | ConvertTo-Json -Depth 10), $Utf8NoBom)<br>
$Common = @("--environment", $Environment, "--scope", $Scope, "--evidence-dir", $DeploymentPrivate)
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
$ScopeDocument = [ordered]@{
  tenantId = $TenantId
  workspaceId = $WorkspaceId
  workspaceName = $WorkspaceName
  folderId = $FolderId
  portalSubfolderId = $PortalSubfolderId
  participantId = $ParticipantId
  folderMappingVerified = $true
  forbiddenItemIds = @()
}
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($Scope, ($ScopeDocument | ConvertTo-Json -Depth 10), $Utf8NoBom)
$Common = @("--environment", $Environment, "--scope", $Scope, "--evidence-dir", $DeploymentPrivate)
```

次の preflight は読み取りだけを行います。実ワークスペース、容量、フォルダー、既存・削除済みアイテムの名前衝突、配布データを照合します。status が preflight-passed-write-gated、blockers が空であることを確認します。書き込みはまだ許可されていません。

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py preflight @Common --online<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py preflight @Common --online
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

1. DeploymentPrivate の resource-plan.json を開き、scope の Workspace・folder・参加者ID、resources の名前と種類を1件ずつ確認します。主 Ontology は1件、Data Agent は1件で、2件目の Ontology を作るオプションは使いません。既存名の衝突があれば別の許可済み空フォルダーと参加者IDを選び直し、新しい記録フォルダーで preflight します。既存アイテムの削除で回避しません。
2. 計画が自分に許可された作業範囲で、作成とデータ書き込みを自分で承認できることを確認します。共同管理の環境で別の所有者の承認が必要なら、計画をその所有者に確認してもらいます。承認できた場合だけ次の確認入力を実施します。resource-plan.json の内容やハッシュは編集しません。

**Readable wrapped view — PowerShell**

<div>
$Plan = [IO.File]::ReadAllText((Join-Path $DeploymentPrivate "resource-plan.json")) | ConvertFrom-Json<br>
if (@($Plan.blockers).Count -ne 0) { throw "Resolve blockers before approval." }<br>
$PlanSha = $Plan.planSha256<br>
$Approval = Read-Host "After reviewing this exact plan, type APPROVE $PlanSha"<br>
if ($Approval -ne "APPROVE $PlanSha") { throw "Plan not approved." }<br>
if (-not (Test-Path $MappingEvidence)) { throw "Folder mapping evidence is missing." }<br>
$Gate = Join-Path $DeploymentPrivate "write-gate.json"<br>
$GateDocument = [IO.File]::ReadAllText((Join-Path $DeploymentPrivate "write-gate.template.json")) | ConvertFrom-Json<br>
$GateDocument.allowCloudMutations = $true<br>
$GateDocument.folderMappingVerified = $true<br>
$GateDocument.approvedAt = [DateTime]::UtcNow.ToString("o")<br>
$GateDocument.folderMappingEvidence = $MappingEvidence<br>
[IO.File]::WriteAllText($Gate, ($GateDocument | ConvertTo-Json -Depth 10), $Utf8NoBom)<br>
$Write = $Common + @("--write-gate", $Gate, "--confirm", $PlanSha)
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
$Plan = [IO.File]::ReadAllText((Join-Path $DeploymentPrivate "resource-plan.json")) | ConvertFrom-Json
if (@($Plan.blockers).Count -ne 0) { throw "Resolve blockers before approval." }
$PlanSha = $Plan.planSha256
$Approval = Read-Host "After reviewing this exact plan, type APPROVE $PlanSha"
if ($Approval -ne "APPROVE $PlanSha") { throw "Plan not approved." }
if (-not (Test-Path $MappingEvidence)) { throw "Folder mapping evidence is missing." }
$Gate = Join-Path $DeploymentPrivate "write-gate.json"
$GateDocument = [IO.File]::ReadAllText((Join-Path $DeploymentPrivate "write-gate.template.json")) | ConvertFrom-Json
$GateDocument.allowCloudMutations = $true
$GateDocument.folderMappingVerified = $true
$GateDocument.approvedAt = [DateTime]::UtcNow.ToString("o")
$GateDocument.folderMappingEvidence = $MappingEvidence
[IO.File]::WriteAllText($Gate, ($GateDocument | ConvertTo-Json -Depth 10), $Utf8NoBom)
$Write = $Common + @("--write-gate", $Gate, "--confirm", $PlanSha)
```

このファイルは、確認した1つの計画の承認記録です。全段階で同じ scope、resource-plan、write-gate、deployment-state と配布版を使います。手順の途中で記録やハッシュを書き換えて停止を回避しません。PowerShell を閉じた場合は、既存ファイルを読み、同じ変数と Common / Write を設定し直します。フォルダーや計画を新規作成し直しません。

<details>
<summary>English</summary>

## 24.5 Review and authorize your exact deployment plan

After verifying the folder mapping, create your scope.json with the following commands. Put any explicitly forbidden existing item GUIDs in forbiddenItemIds. An empty array still does not allow the deployment tool to adopt or overwrite other users' existing items.

**Readable wrapped view — PowerShell**

<div>
$ScopeDocument = [ordered]@{<br>
  tenantId = $TenantId<br>
  workspaceId = $WorkspaceId<br>
  workspaceName = $WorkspaceName<br>
  folderId = $FolderId<br>
  portalSubfolderId = $PortalSubfolderId<br>
  participantId = $ParticipantId<br>
  folderMappingVerified = $true<br>
  forbiddenItemIds = @()<br>
}<br>
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)<br>
[IO.File]::WriteAllText($Scope, ($ScopeDocument | ConvertTo-Json -Depth 10), $Utf8NoBom)<br>
$Common = @("--environment", $Environment, "--scope", $Scope, "--evidence-dir", $DeploymentPrivate)
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
$ScopeDocument = [ordered]@{
  tenantId = $TenantId
  workspaceId = $WorkspaceId
  workspaceName = $WorkspaceName
  folderId = $FolderId
  portalSubfolderId = $PortalSubfolderId
  participantId = $ParticipantId
  folderMappingVerified = $true
  forbiddenItemIds = @()
}
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($Scope, ($ScopeDocument | ConvertTo-Json -Depth 10), $Utf8NoBom)
$Common = @("--environment", $Environment, "--scope", $Scope, "--evidence-dir", $DeploymentPrivate)
```

The following preflight only reads and checks the actual workspace, capacity, folder, active/recoverable name conflicts and distributed data. Confirm status preflight-passed-write-gated and an empty blockers list. Writes are not yet enabled.

**Readable wrapped view — PowerShell**

<div>
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py preflight @Common --online<br>
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/provisioning/preview30_runtime.py preflight @Common --online
if ($LASTEXITCODE -ne 0) { throw "Stage stopped; inspect the saved evidence before continuing." }
```

1. Open resource-plan.json in DeploymentPrivate. Review the workspace, folder and participant ID under scope and every resource name and type. There must be one main ontology and one Data Agent; do not opt into a second ontology. On name conflicts, choose another authorized empty folder and participant ID and run preflight in a new record folder. Do not delete existing items to bypass conflicts.
2. Confirm that the plan is within your authorized scope and that you can approve its creation and data writes. If another owner must approve work in a shared environment, have that owner review the concrete plan. Complete the confirmation below only after approval. Never edit resource-plan.json or its hashes.

**Readable wrapped view — PowerShell**

<div>
$Plan = [IO.File]::ReadAllText((Join-Path $DeploymentPrivate "resource-plan.json")) | ConvertFrom-Json<br>
if (@($Plan.blockers).Count -ne 0) { throw "Resolve blockers before approval." }<br>
$PlanSha = $Plan.planSha256<br>
$Approval = Read-Host "After reviewing this exact plan, type APPROVE $PlanSha"<br>
if ($Approval -ne "APPROVE $PlanSha") { throw "Plan not approved." }<br>
if (-not (Test-Path $MappingEvidence)) { throw "Folder mapping evidence is missing." }<br>
$Gate = Join-Path $DeploymentPrivate "write-gate.json"<br>
$GateDocument = [IO.File]::ReadAllText((Join-Path $DeploymentPrivate "write-gate.template.json")) | ConvertFrom-Json<br>
$GateDocument.allowCloudMutations = $true<br>
$GateDocument.folderMappingVerified = $true<br>
$GateDocument.approvedAt = [DateTime]::UtcNow.ToString("o")<br>
$GateDocument.folderMappingEvidence = $MappingEvidence<br>
[IO.File]::WriteAllText($Gate, ($GateDocument | ConvertTo-Json -Depth 10), $Utf8NoBom)<br>
$Write = $Common + @("--write-gate", $Gate, "--confirm", $PlanSha)
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
$Plan = [IO.File]::ReadAllText((Join-Path $DeploymentPrivate "resource-plan.json")) | ConvertFrom-Json
if (@($Plan.blockers).Count -ne 0) { throw "Resolve blockers before approval." }
$PlanSha = $Plan.planSha256
$Approval = Read-Host "After reviewing this exact plan, type APPROVE $PlanSha"
if ($Approval -ne "APPROVE $PlanSha") { throw "Plan not approved." }
if (-not (Test-Path $MappingEvidence)) { throw "Folder mapping evidence is missing." }
$Gate = Join-Path $DeploymentPrivate "write-gate.json"
$GateDocument = [IO.File]::ReadAllText((Join-Path $DeploymentPrivate "write-gate.template.json")) | ConvertFrom-Json
$GateDocument.allowCloudMutations = $true
$GateDocument.folderMappingVerified = $true
$GateDocument.approvedAt = [DateTime]::UtcNow.ToString("o")
$GateDocument.folderMappingEvidence = $MappingEvidence
[IO.File]::WriteAllText($Gate, ($GateDocument | ConvertTo-Json -Depth 10), $Utf8NoBom)
$Write = $Common + @("--write-gate", $Gate, "--confirm", $PlanSha)
```

This file records approval of one reviewed plan. Keep the same scope, resource plan, write gate, deployment state and distributed source version throughout. Do not change records or hashes to bypass a stop. If you close PowerShell, reload the existing files and reestablish the same variables and Common / Write arrays; do not recreate the folder or plan.

</details>
