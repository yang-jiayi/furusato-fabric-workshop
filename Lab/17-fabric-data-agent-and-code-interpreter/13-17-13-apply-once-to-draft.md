# 17.13 Draft へ一度だけ適用する

[Lab 目次](../README.md) · [この章の目次](README.md)

直前の prepare で対象・差分・readback を確認してから、同じ既存 Agent の Draft に候補を一度だけ適用します。明示的な --apply がなければ書き込みません。apply intent は使い切りです。送信後に失敗・timeout・不明状態が起きても再送せず、intentを保持して読み取り専用 verify で実状態を調べます。

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py apply `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --apply
```

Draft の完全な shared-field readback と complete-stage の結果を確認します。失敗や不一致がある場合は停止し、公開しません。既存の Agent、Schema、Selection を作成・拡張する回避策を試しません。

<details>
<summary>English</summary>

## 17.13 Apply once to Draft

After reviewing the target, diffs and readbacks from prepare, apply the candidate exactly once to Draft on the same existing agent. No write occurs without explicit --apply. The apply intent is single-use. After a failed, timed-out or uncertain submission, do not resend; preserve the intent and inspect live state with read-only verify.

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py apply `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --apply
```

Inspect complete shared-field readback and complete-stage results for Draft. Stop and do not publish on failure or mismatch. Do not work around the problem by creating or expanding agents, schema or selections.

</details>
