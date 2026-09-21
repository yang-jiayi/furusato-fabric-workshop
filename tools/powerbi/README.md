# Optional Direct Lake モデル / レポートの配置 / Deploy the optional Direct Lake model and report

[日本語](#日本語) | [English](#english)

---

## 日本語

### 目的

Optional な Direct Lake セマンティックモデルとレポートを、サポートされている
Fabric Items REST API で対象 workspace へ配置します。ツールの動作は次の 6 段階です。

1. 対象 workspace 内の `LH_Furusato_<PID>` と、その参加者 Folder を解決する。
2. 可搬な TMDL プレースホルダーをメモリ上で展開する。
3. 完全な TMDL 定義で SemanticModel を作成または更新する。
4. `definition.pbir` をローカルの `byPath` から、作成したセマンティックモデル ID を
   使う Fabric API の `byConnection` へ再バインドする。
5. すべての PBIR 定義パートで Report を作成または更新する。
6. ページング付きで両アイテムを再列挙し、指定 Folder 内の完全一致が 1 件であることを検証する。

Notebook 05 が `Ready` 状態で完了し、`gold` スキーマに 5 本の Direct Lake
テーブルが存在した後にのみ実行してください。

### 前提

- PowerShell 7 以降（`pwsh`）。
- Azure CLI がインストールされ、対象テナントに対して `az login` 済みであること。
  スクリプトは preview と apply のどちらを行うか決める**前**に
  `az account get-access-token --resource https://api.fabric.microsoft.com`
  を呼び出すため、preview 実行でも必要です。
  未実施の場合は `Azure CLI could not acquire a Fabric API token.` で停止します。
- Notebook 05 が `Ready` 状態で完了し、`gold` スキーマが存在すること。

### 使い方

既定の実行は読み取り専用の preview です。

`-FolderId` を省略すると Lakehouse の Folder GUID を使います。URL の数値
`subfolderId` は GUID ではありません。Folder 外へ作成せず、Lakehouse と配置先の
Folder が異なる場合は停止します。特定ユーザーでの検証には
`-ExpectedUserPrincipalName` と `-ExpectedTenantId` を渡してください。書き込み前にも
CLI identity を再確認します。

```powershell
pwsh .\tools\powerbi\Deploy-FurusatoPowerBI.ps1 `
  -WorkspaceId <workspace-guid> `
  -ParticipantId 001
```

既存の同名モデルまたはレポートは、明示的な `-UpdateExisting` がない限り更新しません。
このフラグは既存 ID と配置先を確認した意図的な更新にだけ使用してください。

パート数と SHA-256 の値を確認したうえで適用します。

```powershell
pwsh .\tools\powerbi\Deploy-FurusatoPowerBI.ps1 `
  -WorkspaceId <workspace-guid> `
  -ParticipantId 001 `
  -Apply `
  -Confirmation "DEPLOY POWER BI 001" `
  -Confirm:$false
```

### 制限

この可搬な Direct Lake プロジェクトに対して、Power BI Desktop の Publish コマンドは
使用しないでください。ローカルのレポートは `byPath` を使いますが、Fabric REST API は
具体的な `semanticmodelid=<id>` の `byConnection` バインディングを要求します。

---

## English

### Purpose

Deploy the optional Direct Lake semantic model and report into the target
workspace through the supported Fabric Items REST APIs. The tool does six things:

1. Resolve `LH_Furusato_<PID>` and its participant Folder in the target workspace.
2. Render the portable TMDL placeholders in memory.
3. Create or update the SemanticModel with the complete TMDL definition.
4. Rebind `definition.pbir` from local `byPath` to Fabric API
   `byConnection` using the created semantic-model ID.
5. Create or update the Report with every PBIR definition part.
6. Re-list with pagination and verify one exact match inside the target Folder.

Run this only after Notebook 05 finishes in `Ready` state and the
`gold` schema contains the five Direct Lake tables.

### Prerequisites

- PowerShell 7 or later (`pwsh`).
- Azure CLI installed and `az login` completed against the target tenant.
  The script calls `az account get-access-token --resource https://api.fabric.microsoft.com`
  **before** it decides between preview and apply, so the preview run needs it too.
  Without it the script stops at
  `Azure CLI could not acquire a Fabric API token.`
- Notebook 05 finished in `Ready` state, so the `gold` schema exists.

### Usage

The default run is read-only preview:

When `-FolderId` is omitted, the Lakehouse's Folder GUID is used. The numeric
portal `subfolderId` is not a GUID. Creation outside the participant Folder is
refused. For identity-pinned validation, pass `-ExpectedUserPrincipalName` and
`-ExpectedTenantId`; CLI identity is checked again before writes.

```powershell
pwsh .\tools\powerbi\Deploy-FurusatoPowerBI.ps1 `
  -WorkspaceId <workspace-guid> `
  -ParticipantId 001
```

An existing same-name model or report is not updated without explicit
`-UpdateExisting`. Use that flag only after inspecting the existing IDs and
confirming the intended update.

After reviewing the part counts and SHA-256 values:

```powershell
pwsh .\tools\powerbi\Deploy-FurusatoPowerBI.ps1 `
  -WorkspaceId <workspace-guid> `
  -ParticipantId 001 `
  -Apply `
  -Confirmation "DEPLOY POWER BI 001" `
  -Confirm:$false
```

### Limitations

Do not use Power BI Desktop's Publish command for this portable Direct Lake
project. The local report uses `byPath`, while the Fabric REST API requires a
concrete `semanticmodelid=<id>` `byConnection` binding.
