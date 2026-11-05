# 17.9 適用候補を安全に準備する

[Lab 目次](../README.md) · [この章の目次](README.md)

次の prepare コマンドは --common-guidance で17.6と12.6の現行共通指示を固定します。この参加者経路でも既存 profile とソース全体の照合は必須で、Draft の共通指示だけを変更します。他の部品は元の payload を保持し、stage JSON だけを再シリアライズします。照合に失敗したら停止し、ソースを直して通過させません。

候補ファイルはUTF-8 BOMなしで保持します。CRLFをLFに揃えた本文と元ファイルの両ハッシュ、UTF-16単位数、対象範囲が準備記録に固定されます。今回の本文はLFで3,394文字です。以降は同じファイルとPrivateRootを保持し、apply・publish・verifyにはオプションを繰り返さず、固定された候補で確認します。ファイルや候補の変更、同時変更では停止し、新しい準備と許可が必要です。モデルPrep、ソースの利用可能性、回答精度はこの操作では確認されません。

`prepare` はリモートの変更を行わず、対象の既存 Agent を読み取り、ID-only binding を実定義と照合して、候補と private evidence を作成します。shared-field の実際の readback と complete-stage を確認し、予期しない意味差分があれば失敗として止まることを確認します。`prepare` の結果を見ずに `apply` へ進みません。

1. WorkspaceId・FolderId・AgentId は実際の許可済み環境から取得した GUID を使います。PrivateRoot は絶対パスで指定し、全ての Git checkout の外に置きます。RoutingOrigin は対象から観測した HTTPS regional analysis.windows.net の origin だけを指定し、地域名やホストを推測しません。
2. 値は共有資料でなく、作業中の PowerShell 変数だけに設定します。PrivateRoot は新規で一意にし、既存の intent や記録を再利用・削除しません。prepare を実行し、出力された対象と候補を確認します。

**PowerShell**

```powershell
$WorkspaceId = "<authorized-workspace-guid>"
$FolderId = "<authorized-folder-guid>"
$AgentId = "<existing-agent-guid>"
$PrivateRoot = "C:\Users\<you>\Documents\Furusato-private\<unique-run>"
$RoutingOrigin = "https://<observed-region>.analysis.windows.net"
```

**Readable wrapped view — PowerShell**

<div>
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py prepare `<br>
  --workspace-id $WorkspaceId `<br>
  --folder-id $FolderId `<br>
  --agent-id $AgentId `<br>
  --private-root $PrivateRoot `<br>
  --routing-origin $RoutingOrigin `<br>
  --common-guidance workshop/v3.0.0-preview/powerbi/prep-for-ai/agent-instructions.txt
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py prepare `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --routing-origin $RoutingOrigin `
  --common-guidance workshop/v3.0.0-preview/powerbi/prep-for-ai/agent-instructions.txt
```

<details>
<summary>English</summary>

## 17.9 Prepare the candidate safely

The prepare command below binds the current common guidance in17.6 and12.6 with --common-guidance. This participant path still requires complete profile/source reconciliation and changes only Draft common instructions. Other parts retain their original payloads; only stage JSON is reserialized. Stop on reconciliation failure; do not alter sources to pass.

Keep the candidate as UTF-8 without BOM. Preparation binds both original-file and LF-normalized hashes, UTF-16 units and target scope; CRLF is normalized to LF. This text has3,394LF characters. Retain the same file and PrivateRoot for later phases; do not repeat the option on apply, publish or verify, which use the bound candidate. File/candidate or concurrent changes stop the operation and require new preparation and authorization. This operation verifies neither model Prep, source availability nor answer accuracy.

`prepare` makes no remote changes. It reads the existing agent, resolves ID-only bindings against its live definition and writes the candidate and private evidence. Check actual shared-field readback and complete-stage; verify unexpected semantic drift causes a fail-closed stop. Do not proceed to `apply` without inspecting `prepare` output.

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

**Readable wrapped view — PowerShell**

<div>
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py prepare `<br>
  --workspace-id $WorkspaceId `<br>
  --folder-id $FolderId `<br>
  --agent-id $AgentId `<br>
  --private-root $PrivateRoot `<br>
  --routing-origin $RoutingOrigin `<br>
  --common-guidance workshop/v3.0.0-preview/powerbi/prep-for-ai/agent-instructions.txt
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py prepare `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --routing-origin $RoutingOrigin `
  --common-guidance workshop/v3.0.0-preview/powerbi/prep-for-ai/agent-instructions.txt
```

</details>
