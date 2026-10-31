# 24.11 配布データと実行資産を確認する

[Lab 目次](../README.md) · [この章の目次](README.md)

ZIPの外部SHA-256照合に加えて、ローカルのCSVと関係の整合性を次の読み取り専用コマンドで確認できます。リポジトリまたはZIPのsourceを起点に実行します。実環境へのアップロードや書き込みは行いません。

**PowerShell**

```powershell
pwsh ./tools/data/Test-IncrementConsistency.ps1
if ($LASTEXITCODE -ne 0) { throw "Dataset check failed" }
pwsh ./tools/ontology/Test-OntologyCardinality.ps1
if ($LASTEXITCODE -ne 0) { throw "Ontology check failed" }
```

ソースの再現性も調べる場合だけ、Gitでコミットを固定したクリーンなcheckoutとPython 3.13を使い、次の使い捨てコピーでreseal_runtime.py --checkを実行します。このコマンドは読み取り専用ではありません。元の配置元で実行したり、差分を通すために生成物を配置元へ戻したりしません。CSV・NotebookのSHAだけを確認したい参加者はこの再生成検査を行う必要はありません。

**PowerShell**

```powershell
$ErrorActionPreference = "Stop"
python -c "import sys; assert sys.version_info[:2] == (3, 13)"
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for byte-identical gzip output" }
$Dirty = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }
$CheckRoot = Join-Path ([IO.Path]::GetTempPath()) ("furusato-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $CheckRoot | Out-Null
$Archive = Join-Path $CheckRoot "source.zip"
$Source = Join-Path $CheckRoot "source"
git archive --format=zip --output=$Archive HEAD
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }
Expand-Archive -LiteralPath $Archive -DestinationPath $Source
Push-Location -LiteralPath $Source
try {
    python -B ./tools/provisioning/reseal_runtime.py --check
    if ($LASTEXITCODE -ne 0) { throw "Runtime drift; do not deploy this generated copy" }
}
finally {
    Pop-Location
}
```

検査後も配置元は元の固定コミットです。差分やエラーがあれば停止し、原因を調べます。この検査の成功はFabricの認証・実行・回答精度の確認とは別です。

<details>
<summary>English</summary>

## 24.11 Verify distributed data and runtime assets

In addition to the external ZIP SHA-256 check, use these read-only commands to validate local CSV and relationship integrity. Run from the repository or ZIP source directory. They do not upload or write to Fabric.

**PowerShell**

```powershell
pwsh ./tools/data/Test-IncrementConsistency.ps1
if ($LASTEXITCODE -ne 0) { throw "Dataset check failed" }
pwsh ./tools/ontology/Test-OntologyCardinality.ps1
if ($LASTEXITCODE -ne 0) { throw "Ontology check failed" }
```

Only when checking source regeneration reproducibility, use a clean Git checkout pinned to a commit and Python 3.13, then run reseal_runtime.py --check in the disposable copy below. This command is not read-only. Never run it in the deployment checkout or copy regenerated output back to force a match. Participants who only need to verify CSV/Notebook hashes do not need this regeneration check.

**PowerShell**

```powershell
$ErrorActionPreference = "Stop"
python -c "import sys; assert sys.version_info[:2] == (3, 13)"
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for byte-identical gzip output" }
$Dirty = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }
$CheckRoot = Join-Path ([IO.Path]::GetTempPath()) ("furusato-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $CheckRoot | Out-Null
$Archive = Join-Path $CheckRoot "source.zip"
$Source = Join-Path $CheckRoot "source"
git archive --format=zip --output=$Archive HEAD
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }
Expand-Archive -LiteralPath $Archive -DestinationPath $Source
Push-Location -LiteralPath $Source
try {
    python -B ./tools/provisioning/reseal_runtime.py --check
    if ($LASTEXITCODE -ne 0) { throw "Runtime drift; do not deploy this generated copy" }
}
finally {
    Pop-Location
}
```

The original pinned commit remains the deployment source after the check. Stop and diagnose any drift or error. This check is separate from Fabric authentication, execution and answer-quality verification.

</details>
