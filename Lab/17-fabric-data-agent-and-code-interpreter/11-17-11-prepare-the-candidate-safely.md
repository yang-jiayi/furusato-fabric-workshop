# 17.11 適用候補を安全に準備する

[Lab 目次](../README.md) · [この章の目次](README.md)

prepare はリモートの変更を行わず、対象の既存 Agent を読み取り、ID-only binding を実定義と照合して、候補と private evidence を作成します。shared-field の実際の readback と complete-stage を確認し、予期しない意味差分があれば失敗として止まることを確認します。prepare の結果を見ずに apply へ進みません。

1. WorkspaceId・FolderId・AgentId は実際の許可済み環境から取得したGUIDを使います。PrivateRoot は絶対パスで指定し、全てのGit checkoutの外に置きます。RoutingOrigin は対象から観測した HTTPS regional analysis.windows.net のoriginだけを指定し、地域名やホストを推測しません。
2. 値は共有資料でなく、作業中の PowerShell 変数だけに設定します。PrivateRoot は新規で一意にし、既存の intent や記録を再利用・削除しません。prepare を実行し、出力された対象と候補を確認します。

**PowerShell**

```powershell
$WorkspaceId = "<authorized-workspace-guid>"
$FolderId = "<authorized-folder-guid>"
$AgentId = "<existing-agent-guid>"
$PrivateRoot = "C:\Users\<you>\Documents\Furusato-private\<unique-run>"
$RoutingOrigin = "https://<observed-region>.analysis.windows.net"
```

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py prepare `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --routing-origin $RoutingOrigin
```

<details>
<summary>English</summary>

## 17.11 Prepare the candidate safely

prepare makes no remote changes. It reads the existing agent, resolves ID-only bindings against its live definition and writes the candidate and private evidence. Check actual shared-field readback and complete-stage; verify unexpected semantic drift causes a fail-closed stop. Do not proceed to apply without inspecting prepare output.

1. Use actual GUIDs for WorkspaceId, FolderId and AgentId from the authorized environment. Set PrivateRoot to an absolute path outside every Git checkout. RoutingOrigin must be the observed HTTPS regional analysis.windows.net origin for the target; never guess its region or host.
2. Set these values only in local PowerShell variables, not shared documents. Use a new unique PrivateRoot; do not reuse or delete existing intents or records. Run prepare and inspect the reported target and candidate.

**PowerShell**

```powershell
$WorkspaceId = "<authorized-workspace-guid>"
$FolderId = "<authorized-folder-guid>"
$AgentId = "<existing-agent-guid>"
$PrivateRoot = "C:\Users\<you>\Documents\Furusato-private\<unique-run>"
$RoutingOrigin = "https://<observed-region>.analysis.windows.net"
```

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py prepare `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --routing-origin $RoutingOrigin
```

</details>
