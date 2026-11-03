# 17.11 Draft へ一度だけ適用する

[Lab 目次](../README.md) · [この章の目次](README.md)

apply は対応欄だけを選んで更新せず、candidate の compiled Draft definition 全体を送信します。直前の prepare で対象・差分・readback を確認し、17.10 の semantic model source Instructions/Description の不変条件を候補と現行 Draft の比較で確認できた場合に限り、同じ既存 Agent の Draft に一度だけ適用します。不一致または確認不能なら --apply を実行せず、停止してレビューを依頼します。明示的な --apply がなければ書き込みません。apply intent は使い切りです。送信後に失敗・timeout・不明状態が起きても再送せず、intentを保持して読み取り専用 verify で実状態を調べます。

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py apply `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --apply
```

Draft の shared-field readback と complete-stage の結果を確認します。readback の文字列一致は、semantic model source の Instructions/Description がサポートされる、または DAX に作用することを意味しません。失敗や不一致がある場合は停止し、公開しません。既存の Agent、Schema、Selection を作成・拡張する回避策を試しません。

<details>
<summary>English</summary>

## 17.11 Apply once to Draft

Apply sends the candidate's entire compiled Draft definition; it does not select and update only supported fields. After reviewing the target, diffs and readbacks from prepare, apply once to the same existing agent only if the comparison in 17.10 confirms the semantic-model-source Instructions/Description are unchanged between the candidate and current Draft. If they differ or cannot be confirmed, do not run `--apply`; stop and request review. No write occurs without explicit `--apply`. The apply intent is single-use. After a failed, timed-out or uncertain submission, do not resend; preserve the intent and inspect live state with read-only verify.

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py apply `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --apply
```

Inspect shared-field readback and complete-stage results for Draft. A matching readback does not mean SemanticModel-source Instructions/Description are supported or affect DAX. Stop and do not publish on failure or mismatch. Do not work around the problem by creating or expanding agents, schema or selections.

</details>
