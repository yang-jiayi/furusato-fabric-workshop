# 17.16 コマンドで設定全体を適用・公開・確認する

[Lab 目次](../README.md) · [この章の目次](README.md)

この手順は、指示のほか、ソース説明、SQL/KQL の選択と列の説明、9件の KQL 例を同じ Agent に設定します。新しい Agent や Ontology を作るコマンドではありません。17.6のビュー、17.7の SQL 選択、17.11の KQL 選択、17.13のモデル選択と10メジャー、17.14の主 Ontology が実在し、Agent に表示されるところまでを先に行います。

Windows では PowerShell を開きます。Python 3.11以降と Azure CLI を用意します。標準の SQL schema 照合は HTTPS の Fabric SQL MCP を使うため、ODBC Driver は不要です。Python と Azure CLI は次のコマンドでインストールできます。既に入っている場合は再インストールせず、次の確認へ進みます。

**PowerShell**

```powershell
winget install --exact --id Python.Python.3.11
winget install --exact --id Microsoft.AzureCLI
```

インストール後に PowerShell を開き直します。Linux を使う場合は Python 3.11以降と Azure CLI を用意し、python3 -m venv .venv で仮想環境を作ります。以下の Windows の Python パスを .venv/bin/python に、PowerShell の変数を利用中のシェルの変数構文に読み替えます。

ZIP の展開先に合わせて最初のパスを変更し、source フォルダーに移動します。仮想環境はこの作業専用です。認証トークンやライブ定義を ZIP、Git、配布フォルダーに保存しないよう、実行記録は次の別フォルダーに保存します。

**PowerShell**

```powershell
Set-Location "C:\Workshop\Furusato_Workshop\source"
py -3 --version
az version
$env:PYTHONDONTWRITEBYTECODE = "1"
py -3 -B -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/provisioning/requirements-preview30.txt
```

標準経路では SQL analytics endpoint の MCP 接続が使えることを確認します。SQL 権限や MCP の利用条件が満たされない場合は、その前提を解消してから再開します。別の接続方法が必要な環境では prepare に --sql-transport odbc を追加できます。その場合だけ pyodbc、Microsoft ODBC Driver 18 for SQL Server と SQL endpoint への TCP 1433 接続が必要です。ドライバーの公式配布先は https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server です。ダミーの schema で代用しません。

1. Fabric 右上のアカウントで利用中のテナントを確認します。Workspace の URL の /groups/ に続く GUID が Workspace ID、Data Agent を開いた URL のアイテム部分の GUID が Agent ID です。フォルダーの subfolderId はこの2つの代わりに使いません。アイテム名と自分の参加者IDも照合します。
2. ブラウザーで F12 → Network を開き、主 Ontology の画面を再読み込みします。metadata/artifacts で絞り込み、主 Ontology の ID に対する要求の Request URL を確認します。その URL の https:// からホスト名まで（末尾の /metadata/... は含めない）を RoutingOrigin に使います。ホストは実際に観測した https://&lt;名前&gt;.analysis.windows.net です。トークン、Cookie、Authorization、Copy as cURL の内容はコピーしません。該当要求が見つからない場合は推測したホストで実行せず、ネットワーク表示のフィルターと主 Ontology の画面を確認します。
3. 次のプレースホルダーを自分の値に置き換えます。PrivateRoot は配布物の外にある新規フォルダーです。1回の構成変更で同じフォルダーを使い、過去の実行記録へ上書きしません。Azure CLI の初回ログインは表示された本人認証の案内に従います。期限内のログインを再利用でき、期限切れでは同じログインをやり直します。

**PowerShell**

```powershell
$TenantId = "<tenant GUID>"
$WorkspaceId = "<workspace GUID>"
$AgentId = "<Data Agent item GUID>"
$RoutingOrigin = "https://<observed hostname>.analysis.windows.net"
$PrivateRoot = Join-Path $env:USERPROFILE "furusato-private\profile-20261015-01"
az login --tenant $TenantId --use-device-code --allow-no-subscriptions
$ProfileArgs = @("--workspace-id", $WorkspaceId, "--agent-id", $AgentId, "--profile", "measured-contract-20261015", "--private-root", $PrivateRoot)
```

まず prepare を実行します。これは読み取り専用で、現状の定義、実際の SQL 列、モデルの10メジャー、Gen2 Ontology を照合し、ローカルの候補を作ります。status が prepared、cloudWrites が0、selectedSqlObjects が17、selectedSqlColumns が143であることを確認します。prepare が失敗した場合も、途中までの記録フォルダーは保持します。指摘されたソース・列・メジャーを修正し、PrivateRoot を profile-20261015-02 など新しい名前に変更して、ProfileArgs を作り直してから prepare を実行します。同じフォルダーの再利用や検査の無効化はしません。prepared まで成功した後の apply・publish・verify は、その成功した同じフォルダーを使います。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py prepare @ProfileArgs --routing-origin $RoutingOrigin
```

PrivateRoot の prepared.json と compile-receipt.json を開き、対象、プロファイル、17オブジェクト・143列・10メジャーを確認します。inputs.json には変更前の実定義、candidate.json には適用する候補が保存されます。これらは自分の構成情報なので配布資料へ戻しません。次の apply は同じ Agent の Draft だけを変更し、公開版はまだ変えません。成功時の status は draft-matches です。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py apply @ProfileArgs --apply
```

次の publish は Draft の一致と KQL の9例が Valid であることを確認してから、1回だけ公開し、公開版を読み戻します。status が published-matches になることを確認します。verify は読み取り専用なので、後日も同じ保存先を指定して再確認できます。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py publish @ProfileArgs --apply
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage published
```

公開版の確認で directSources=3、selectedSqlObjects=17、selectedSqlColumns=143、activeKqlExamples=9、ontologyContextPreserved=true を確認します。ontologyContextAvailabilityVerified=false と answerAccuracyVerified=false は、このコマンドが接続成功や回答精度まで保証しないことを示します。17.2と19章の実回答評価を続けます。

apply や publish の送信後にタイムアウトした場合は、同じ書き込みを繰り返しません。次の読み取り専用 verify で対象の段階を確認します。apply-intent.json / publish-intent.json は二重送信を防ぐ記録なので削除しません。別の人や画面操作で設定が変わったというエラーも、自動で上書きせず現在の変更を確認します。復元が必要なら inputs.json と apply-backup.json / publish-backup.json を保持し、17.15の同じ Agent の復元手順で指示と選択を戻します。

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage draft
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage published
```

<details>
<summary>English</summary>

## 17.16 Apply, publish and verify the complete configuration

This procedure configures instructions, source descriptions, SQL/KQL selections and column descriptions, and nine KQL examples on the same agent. It does not create an agent or ontology. First complete the views in 17.6, SQL selection in 17.7, KQL selection in 17.11, model selection and ten measures in 17.13, and main ontology in 17.14, so they actually exist and appear in the agent.

On Windows, open PowerShell. Install Python 3.11 or newer and Azure CLI. The standard schema check uses Fabric SQL MCP over HTTPS and does not require an ODBC driver. The following commands install Python and Azure CLI. If already installed, proceed to verification without reinstalling.

**PowerShell**

```powershell
winget install --exact --id Python.Python.3.11
winget install --exact --id Microsoft.AzureCLI
```

Reopen PowerShell after installation. On Linux, install Python 3.11 or newer and Azure CLI and create the virtual environment with python3 -m venv .venv. Substitute .venv/bin/python for the Windows Python path below and use your shell's variable syntax instead of PowerShell syntax.

Change the first path to your extracted ZIP and enter its source folder. The virtual environment belongs to this task. Keep live definitions and credentials out of ZIP, Git and distribution folders by putting run records in the separate folder shown below.

**PowerShell**

```powershell
Set-Location "C:\Workshop\Furusato_Workshop\source"
py -3 --version
az version
$env:PYTHONDONTWRITEBYTECODE = "1"
py -3 -B -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/provisioning/requirements-preview30.txt
```

The standard route requires the SQL analytics endpoint MCP connection to be available. Resolve SQL permissions or MCP prerequisites before continuing if they are missing. Environments needing another transport can add --sql-transport odbc to prepare; only that alternative requires pyodbc, Microsoft ODBC Driver 18 for SQL Server and TCP 1433 access to the SQL endpoint. Obtain the driver from https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server. Never substitute dummy schema metadata.

1. Confirm your tenant in the Fabric account menu. The GUID after /groups/ in the workspace URL is the workspace ID; the item GUID in the opened Data Agent URL is the agent ID. The folder subfolderId is neither of these. Also match the item name and your participant ID.
2. Open browser F12 → Network and reload the main ontology page. Filter for metadata/artifacts and inspect the Request URL for the main ontology ID. Use only the origin, from https:// through the hostname, as RoutingOrigin; omit /metadata/... and everything after it. The host must be an actually observed https://&lt;name&gt;.analysis.windows.net. Do not copy tokens, cookies, Authorization headers or Copy as cURL contents. If the request is absent, check the filter and ontology page instead of guessing a host.
3. Replace the following placeholders with your values. PrivateRoot must be a new folder outside the distribution. Use that same folder for one configuration change without overwriting an old run. Follow the interactive instructions for your first Azure CLI sign-in. A valid login can be reused; sign in again when it expires.

**PowerShell**

```powershell
$TenantId = "<tenant GUID>"
$WorkspaceId = "<workspace GUID>"
$AgentId = "<Data Agent item GUID>"
$RoutingOrigin = "https://<observed hostname>.analysis.windows.net"
$PrivateRoot = Join-Path $env:USERPROFILE "furusato-private\profile-20261015-01"
az login --tenant $TenantId --use-device-code --allow-no-subscriptions
$ProfileArgs = @("--workspace-id", $WorkspaceId, "--agent-id", $AgentId, "--profile", "measured-contract-20261015", "--private-root", $PrivateRoot)
```

First run prepare. It is read-only: it checks current definitions, actual SQL columns, ten model measures and Gen2 ontology, then creates a local candidate. Confirm status prepared, cloudWrites 0, selectedSqlObjects 17 and selectedSqlColumns 143. A failed prepare still leaves a partial record folder; retain it. Repair the named source, column or measure, change PrivateRoot to a new name such as profile-20261015-02, rebuild ProfileArgs, then run prepare again. Do not reuse the failed folder or disable validation. Once prepared succeeds, use that same successful folder for apply, publish and verify.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py prepare @ProfileArgs --routing-origin $RoutingOrigin
```

Open prepared.json and compile-receipt.json in PrivateRoot and check the target, profile, 17 objects, 143 columns and ten measures. inputs.json holds the original live definitions and candidate.json the candidate to apply. Keep these private configuration records out of the distribution. The next apply changes only Draft on the same agent; it does not publish. Its success status is draft-matches.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py apply @ProfileArgs --apply
```

The next publish checks Draft equality and all nine KQL examples being Valid, publishes once and reads the published version back. Confirm status published-matches. verify is read-only and can be rerun later with the same record folder.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py publish @ProfileArgs --apply
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage published
```

In the published verification, confirm directSources=3, selectedSqlObjects=17, selectedSqlColumns=143, activeKqlExamples=9 and ontologyContextPreserved=true. ontologyContextAvailabilityVerified=false and answerAccuracyVerified=false mean this command does not establish native connectivity or answer quality. Continue to actual-answer checks in 17.2 and Chapter 19.

If apply or publish times out after sending, do not repeat the write. Use the read-only verify below for the affected stage. Do not delete apply-intent.json or publish-intent.json: they prevent duplicate sends. If the configuration changed through another user or the UI, inspect that change rather than overwriting it automatically. For restoration, retain inputs.json and apply-backup.json / publish-backup.json and use the same-agent restoration procedure in 17.15.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage draft
.\.venv\Scripts\python.exe -B tools/data-agent/participant_profile.py verify @ProfileArgs --stage published
```

</details>
