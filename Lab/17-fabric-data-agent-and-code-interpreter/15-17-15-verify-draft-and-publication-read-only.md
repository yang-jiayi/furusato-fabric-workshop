# 17.15 Draft と公開版を読み取り専用で検証する

[Lab 目次](../README.md) · [この章の目次](README.md)

verify は read-only で、Draft または Published を明示して確認します。両方の段階を読み戻し、intent 結果、shared-field readbacks、complete-stage、4論理ソース、実指示全文・説明・Ontology context・全selectionを照合します。verifyの成功も、回答精度、Graph/GQL、時系列、mirror完全性を証明しません。

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py verify `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --stage draft
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py verify `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --stage published
```

記録には自分の作業で得た実際の stage、状態、読み戻し、理由だけを残します。設定の readback と、実際に観測したSQL/KQL/DAX/GQL実行・結果・Agent回答を別にします。回答品質の採用・正確性・保証を主張しません。

<details>
<summary>English</summary>

## 17.15 Verify Draft and publication read-only

verify is read-only and explicitly targets Draft or Published. Read back both stages and reconcile intent results, shared-field readbacks, complete-stage, four logical sources, exact instructions/descriptions/Ontology context and all selections. Successful verify does not establish answer accuracy, Graph/GQL, time-series support or mirror completeness.

**PowerShell**

```powershell
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py verify `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --stage draft
.venv\Scripts\python.exe -B tools/data-agent/current_profile.py verify `
  --workspace-id $WorkspaceId `
  --folder-id $FolderId `
  --agent-id $AgentId `
  --private-root $PrivateRoot `
  --stage published
```

Record only the actual stage, status, readbacks and reasons from your own run. Keep configuration readback separate from observed SQL/KQL/DAX/GQL executions, results and Agent answers. Do not claim accepted, accurate or guaranteed answer quality.

</details>
