# 24.11 配布データと実行資産を確認する

[Lab 目次](../README.md) · [この章の目次](README.md)

ZIPの外部SHA-256照合に加えて、次の読み取り専用コマンドで現在版のCSVとOntologyをオフライン検証できます。リポジトリまたはZIP展開後のsourceディレクトリを起点に実行します。データ検査には現在版のdataパスを明示し、旧版の既定値を使いません。Python検査は現在の公開ソースマニフェストの整合性とGeneration 2定義・契約の実バイトを確認し、seed CSVからノード・エッジ・参加数を再計算します。どちらもFabricへ接続・書き込みません。旧版スクリプトの全検査との同等性や、Fabric上のOntology/Graph実行・配置を証明するものではありません。

**Readable wrapped view — PowerShell**

<div>
pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v3.0.0-preview/data<br>
if ($LASTEXITCODE -ne 0) { throw "Dataset check failed" }<br>
python ./tools/provisioning/check_current_ontology.py<br>
if ($LASTEXITCODE -ne 0) { throw "Current ontology check failed" }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v3.0.0-preview/data
if ($LASTEXITCODE -ne 0) { throw "Dataset check failed" }
python ./tools/provisioning/check_current_ontology.py
if ($LASTEXITCODE -ne 0) { throw "Current ontology check failed" }
```

ソースの再現性も調べる場合だけ、Gitでコミットを固定したクリーンなcheckoutとPython 3.13を使い、次の使い捨てコピーでreseal_runtime.py --checkを実行します。このコマンドは読み取り専用ではありません。元の配置元で実行したり、差分を通すために生成物を配置元へ戻したりしません。CSV・NotebookのSHAだけを確認したい参加者はこの再生成検査を行う必要はありません。

**Readable wrapped view — PowerShell**

<div>
$ErrorActionPreference = "Stop"<br>
python -c "import sys; assert sys.version_info[:2] == (3, 13)"<br>
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for byte-identical gzip output" }<br>
$Dirty = git status --porcelain<br>
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }<br>
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }<br>
$CheckRoot = Join-Path ([IO.Path]::GetTempPath()) ("furusato-check-" + [guid]::NewGuid().ToString("N"))<br>
New-Item -ItemType Directory -Path $CheckRoot | Out-Null<br>
$Archive = Join-Path $CheckRoot "source.zip"<br>
$Source = Join-Path $CheckRoot "source"<br>
git archive --format=zip --output=$Archive HEAD<br>
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }<br>
Expand-Archive -LiteralPath $Archive -DestinationPath $Source<br>
Push-Location -LiteralPath $Source<br>
try {<br>
    python -B ./tools/provisioning/reseal_runtime.py --check<br>
    if ($LASTEXITCODE -ne 0) { throw "Runtime drift; do not deploy this generated copy" }<br>
}<br>
finally {<br>
    Pop-Location<br>
}
</div>

**Verbatim source follows; copy from the canonical block.**

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

Alongside the external ZIP SHA-256 check, these read-only commands validate the current edition's CSVs and ontology offline. Run them from the repository root or the extracted ZIP's source directory. The data check explicitly selects the current data path instead of using the legacy default. The Python check validates the current publication source manifest and Generation 2 definition/contract bytes, then recomputes node, edge and participation counts from the seed CSVs. Neither connects to or writes to Fabric. This is not full parity with every legacy-script check and does not prove a Fabric Ontology/Graph runtime or deployment.

**Readable wrapped view — PowerShell**

<div>
pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v3.0.0-preview/data<br>
if ($LASTEXITCODE -ne 0) { throw "Dataset check failed" }<br>
python ./tools/provisioning/check_current_ontology.py<br>
if ($LASTEXITCODE -ne 0) { throw "Current ontology check failed" }
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v3.0.0-preview/data
if ($LASTEXITCODE -ne 0) { throw "Dataset check failed" }
python ./tools/provisioning/check_current_ontology.py
if ($LASTEXITCODE -ne 0) { throw "Current ontology check failed" }
```

Only when checking source regeneration reproducibility, use a clean Git checkout pinned to a commit and Python 3.13, then run reseal_runtime.py --check in the disposable copy below. This command is not read-only. Never run it in the deployment checkout or copy regenerated output back to force a match. Participants who only need to verify CSV/Notebook hashes do not need this regeneration check.

**Readable wrapped view — PowerShell**

<div>
$ErrorActionPreference = "Stop"<br>
python -c "import sys; assert sys.version_info[:2] == (3, 13)"<br>
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for byte-identical gzip output" }<br>
$Dirty = git status --porcelain<br>
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }<br>
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }<br>
$CheckRoot = Join-Path ([IO.Path]::GetTempPath()) ("furusato-check-" + [guid]::NewGuid().ToString("N"))<br>
New-Item -ItemType Directory -Path $CheckRoot | Out-Null<br>
$Archive = Join-Path $CheckRoot "source.zip"<br>
$Source = Join-Path $CheckRoot "source"<br>
git archive --format=zip --output=$Archive HEAD<br>
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }<br>
Expand-Archive -LiteralPath $Archive -DestinationPath $Source<br>
Push-Location -LiteralPath $Source<br>
try {<br>
    python -B ./tools/provisioning/reseal_runtime.py --check<br>
    if ($LASTEXITCODE -ne 0) { throw "Runtime drift; do not deploy this generated copy" }<br>
}<br>
finally {<br>
    Pop-Location<br>
}
</div>

**Verbatim source follows; copy from the canonical block.**

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
