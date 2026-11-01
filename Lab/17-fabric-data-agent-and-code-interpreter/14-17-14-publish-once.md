# 17.14 公開を一度だけ実施する

[Lab 目次](../README.md) · [この章の目次](README.md)

Draft が完全に一致し、全ての事前条件と readback が通った場合に限り、同じ既存 Agent の公開を一度だけ実行します。明示的な --apply が必要です。publish intent を再利用・削除せず、応答不明や timeout のときは再送しません。

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py publish --workspace-id $WorkspaceId --folder-id $FolderId --agent-id $AgentId --private-root $PrivateRoot --apply
```

<details>
<summary>English</summary>

## 17.14 Publish once

Only after Draft fully matches and all prerequisites and readbacks pass, publish the same existing agent once. Explicit --apply is required. Do not reuse or delete the publish intent, and never resend after an uncertain response or timeout.

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py publish --workspace-id $WorkspaceId --folder-id $FolderId --agent-id $AgentId --private-root $PrivateRoot --apply
```

</details>
