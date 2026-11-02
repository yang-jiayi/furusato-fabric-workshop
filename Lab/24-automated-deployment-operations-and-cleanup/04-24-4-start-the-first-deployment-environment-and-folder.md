# 24.4 初回の配置を始める：環境とフォルダー

[Lab 目次](../README.md) · [この章の目次](README.md)

初めて参加する場合は4章の確認後に、この節から始めます。24.4〜24.6で自分の作業フォルダーへ基盤を作り、5〜8章で作成済みの内容を確認します。24.7と9〜10章で3ファイルを取り込み、11章で Notebook 05 を実行し、24.8で Semantic model と Data Agent を作ります。12〜13章で意味とモデルを確認し、17章で今回の調整済み設定を適用して、19章で評価します。

管理者から利用可能な Fabric ワークスペース、容量と必要な機能、読み取り・作成・編集の権限を用意してもらいます。これは組織のアクセス設定です。Pipeline、Activator、Semantic model を講師に作ってもらう必要はなく、以下のコマンドで自分の範囲へ配置します。ワークスペースの権限で許可された空の作業フォルダーと、他の参加者と重ならない001〜999の参加者IDを使います。容量の一覧を読めないなどの権限エラーは、権限を管理者に確認してから再開します。

配布元の docs/v3.1.0/current にある SHA256SUMS.txt と同じ版のZIPを受け取り、展開前にZIPのSHA-256を照合します。PowerShellでは次のパスを自分のダウンロード先に変更します。表示されたハッシュが配布元の同じファイル名の値と一致してから展開します。ZIP内だけのハッシュを外部の配布確認の代わりにしません。

**Readable wrapped view — PowerShell**

<div>
Get-FileHash -Algorithm SHA256 -LiteralPath "C:\Downloads\Furusato_Workshop_v3.1.0_current.zip"
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "C:\Downloads\Furusato_Workshop_v3.1.0_current.zip"
```

同じ版の参加者用 ZIP をすべて展開します。Windows の PowerShell で Python 3.11以降と Azure CLI を確認します。未導入の場合は次の2行で導入し、PowerShell を開き直します。Linux では同じバージョンの Python と Azure CLI を使い、Python のパスと変数構文をシェルに合わせます。

**PowerShell**

```powershell
winget install --exact --id Python.Python.3.11
winget install --exact --id Microsoft.AzureCLI
```

最初のパスを自分の展開先へ変更します。以後は ZIP の source フォルダーが作業場所です。配布済みの定義・Notebook・CSV は編集せず、そのまま使います。配置の途中で新しい版へ入れ替えません。

**Readable wrapped view — PowerShell**

<div>
Set-Location "C:\Workshop\Furusato_Workshop\source"<br>
py -3 --version<br>
az version<br>
$env:PYTHONDONTWRITEBYTECODE = "1"<br>
py -3 -B -m venv .venv<br>
.\.venv\Scripts\python.exe -m pip install -r tools/provisioning/requirements-preview30.txt -r tools/provisioning/requirements-activation.txt
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
Set-Location "C:\Workshop\Furusato_Workshop\source"
py -3 --version
az version
$env:PYTHONDONTWRITEBYTECODE = "1"
py -3 -B -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/provisioning/requirements-preview30.txt -r tools/provisioning/requirements-activation.txt
```

1. Fabric のアカウントでテナントを確認し、Workspace の URL の /groups/ に続く GUID と、正確なワークスペース表示名を記録します。作業フォルダーを開いた URL の subfolderId は数値の参照です。API に使う folderId の GUID とは別物です。
2. F12 → Network を開いてワークスペースのフォルダー一覧を再読み込みし、実際のフォルダー一覧を返す要求を見つけます。環境によっては /powerbi/metadata/groupmetadata/?folderObjectId=&lt;自分のWorkspace GUID&gt; などの要求に含まれます。固定のパスだけを前提にせず、要求URLとResponseの内容を確認します。Response の subfolders 配列で id が URL の subfolderId と一致する行を見つけ、その行の objectId を folderId の GUID として使います。行の folderId や、同じ表示名の別の行ではありません。応答と要求URLの対応を自分の記録として保存します。
3. 次の変数を自分の値へ変更します。DeploymentPrivate は ZIP や Git の外の新しいフォルダーです。作成後、前の手順の応答本文だけを folder-map.json に保存し、要求URLと確認日時を folder-map-note.txt に記録します。Cookie、Authorization、トークン、HAR は保存しません。対応を確認できない場合は、folderMappingVerified を true にせず停止します。

**Readable wrapped view — PowerShell**

<div>
$TenantId = "&lt;tenant GUID&gt;"<br>
$WorkspaceId = "&lt;workspace GUID&gt;"<br>
$WorkspaceName = "&lt;exact workspace display name&gt;"<br>
$FolderId = "&lt;objectId GUID from the matching folder row&gt;"<br>
$PortalSubfolderId = "&lt;numeric subfolderId from the folder URL&gt;"<br>
$ParticipantId = "001"<br>
$Environment = "dev"<br>
$DeploymentPrivate = Join-Path $env:USERPROFILE "furusato-private\deployment-001-01"<br>
New-Item -ItemType Directory -Path $DeploymentPrivate -ErrorAction Stop<br>
$MappingEvidence = Join-Path $DeploymentPrivate "folder-map.json"<br>
$Scope = Join-Path $DeploymentPrivate "scope.json"<br>
az login --tenant $TenantId --use-device-code --allow-no-subscriptions
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
$TenantId = "<tenant GUID>"
$WorkspaceId = "<workspace GUID>"
$WorkspaceName = "<exact workspace display name>"
$FolderId = "<objectId GUID from the matching folder row>"
$PortalSubfolderId = "<numeric subfolderId from the folder URL>"
$ParticipantId = "001"
$Environment = "dev"
$DeploymentPrivate = Join-Path $env:USERPROFILE "furusato-private\deployment-001-01"
New-Item -ItemType Directory -Path $DeploymentPrivate -ErrorAction Stop
$MappingEvidence = Join-Path $DeploymentPrivate "folder-map.json"
$Scope = Join-Path $DeploymentPrivate "scope.json"
az login --tenant $TenantId --use-device-code --allow-no-subscriptions
```

dev はこの演習の明示的な環境名です。組織で test や prod が指定されている場合だけ変更し、全段階で同じ値を使います。初回の本人認証は画面の案内に従い、後のコマンドは期限内の Azure CLI ログインを再利用します。

<details>
<summary>English</summary>

## 24.4 Start the first deployment: environment and folder

For your first workshop, start here after the checks in Chapter 4. Create the core resources in your folder with 24.4–24.6, inspect them in Chapters 5–8, ingest the three files with 24.7 and Chapters 9–10, run Notebook 05 in Chapter 11, then create the semantic model and Data Agent in 24.8. Inspect meaning and models in Chapters 12–13, apply the adopted configuration in Chapter 17 and evaluate in Chapter 19.

Your administrator must provide an available Fabric workspace, capacity, required features and permission to read, create and edit resources. These are organizational access prerequisites. You do not need an instructor to create the Pipeline, Activator or semantic model; the commands below deploy them in your scope. Use an authorized empty folder and a participant ID from 001 to 999 that is distinct from other participants. If access fails, including capacity-list access, resolve it with the administrator before continuing.

Obtain the ZIP and its matching SHA256SUMS.txt from docs/v3.1.0/current at the distribution source. Before extraction, verify the ZIP SHA-256. Change the path below to your download location and compare the output with the same filename in the distributor’s checksum list. Do not substitute a checksum found only inside the ZIP for this external check.

**Readable wrapped view — PowerShell**

<div>
Get-FileHash -Algorithm SHA256 -LiteralPath "C:\Downloads\Furusato_Workshop_v3.1.0_current.zip"
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "C:\Downloads\Furusato_Workshop_v3.1.0_current.zip"
```

Extract the participant ZIP of the same version. In Windows PowerShell, check for Python 3.11 or newer and Azure CLI. If absent, install them with these two lines and reopen PowerShell. On Linux, use the same Python and Azure CLI requirements and adapt paths and variable syntax to your shell.

**PowerShell**

```powershell
winget install --exact --id Python.Python.3.11
winget install --exact --id Microsoft.AzureCLI
```

Change the first path to your extracted directory. Work from the ZIP's source folder. Use the distributed definitions, Notebooks and CSVs without editing them, and do not switch versions during deployment.

**Readable wrapped view — PowerShell**

<div>
Set-Location "C:\Workshop\Furusato_Workshop\source"<br>
py -3 --version<br>
az version<br>
$env:PYTHONDONTWRITEBYTECODE = "1"<br>
py -3 -B -m venv .venv<br>
.\.venv\Scripts\python.exe -m pip install -r tools/provisioning/requirements-preview30.txt -r tools/provisioning/requirements-activation.txt
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
Set-Location "C:\Workshop\Furusato_Workshop\source"
py -3 --version
az version
$env:PYTHONDONTWRITEBYTECODE = "1"
py -3 -B -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/provisioning/requirements-preview30.txt -r tools/provisioning/requirements-activation.txt
```

1. Confirm the tenant in your Fabric account. Record the GUID after /groups/ in the workspace URL and the exact workspace display name. The subfolderId in the opened folder URL is a numeric portal reference, distinct from the folderId GUID used by the API.
2. Open F12 → Network, reload the workspace folder list and find the actual request that returns the folders. Depending on the environment this may be /powerbi/metadata/groupmetadata/?folderObjectId=&lt;your workspace GUID&gt;. Inspect the request URL and Response rather than assuming one fixed endpoint. In Response, find the row in subfolders whose id matches the URL's subfolderId; use that row's objectId as the folder GUID. Do not use the row's folderId or a different same-named row. Save the response together with its request-URL association in your private records.
3. Replace the variables below with your values. DeploymentPrivate is a new folder outside ZIP and Git. After creating it, save only the prior response body as folder-map.json and record its request URL and inspection time in folder-map-note.txt. Never save cookies, Authorization headers, tokens or HAR files. If the mapping cannot be verified, stop without setting folderMappingVerified to true.

**Readable wrapped view — PowerShell**

<div>
$TenantId = "&lt;tenant GUID&gt;"<br>
$WorkspaceId = "&lt;workspace GUID&gt;"<br>
$WorkspaceName = "&lt;exact workspace display name&gt;"<br>
$FolderId = "&lt;objectId GUID from the matching folder row&gt;"<br>
$PortalSubfolderId = "&lt;numeric subfolderId from the folder URL&gt;"<br>
$ParticipantId = "001"<br>
$Environment = "dev"<br>
$DeploymentPrivate = Join-Path $env:USERPROFILE "furusato-private\deployment-001-01"<br>
New-Item -ItemType Directory -Path $DeploymentPrivate -ErrorAction Stop<br>
$MappingEvidence = Join-Path $DeploymentPrivate "folder-map.json"<br>
$Scope = Join-Path $DeploymentPrivate "scope.json"<br>
az login --tenant $TenantId --use-device-code --allow-no-subscriptions
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
$TenantId = "<tenant GUID>"
$WorkspaceId = "<workspace GUID>"
$WorkspaceName = "<exact workspace display name>"
$FolderId = "<objectId GUID from the matching folder row>"
$PortalSubfolderId = "<numeric subfolderId from the folder URL>"
$ParticipantId = "001"
$Environment = "dev"
$DeploymentPrivate = Join-Path $env:USERPROFILE "furusato-private\deployment-001-01"
New-Item -ItemType Directory -Path $DeploymentPrivate -ErrorAction Stop
$MappingEvidence = Join-Path $DeploymentPrivate "folder-map.json"
$Scope = Join-Path $DeploymentPrivate "scope.json"
az login --tenant $TenantId --use-device-code --allow-no-subscriptions
```

dev is the explicit environment label for this lab. Use test or prod only when that is your assigned environment, and keep the same value for every stage. Complete initial user authentication as prompted; subsequent commands reuse a valid Azure CLI login.

</details>
