# 24.11 配布データと実行資産を確認する

[Lab 目次](../README.md) · [この章の目次](README.md)

この検査には PowerShell 7（pwsh）が必要です。Windows では未導入の場合、24.4の環境準備で導入します。Linux では Microsoft の公式インストール手順に従って導入してから実行します。

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

ソースの再現性を調べる場合だけ、コミットを固定したクリーンなcheckoutとPython 3.13を使い、次のコマンドで現在版を別コピーに展開して生成前後の全ファイルをSHA-256で比較します。抽出先に .git は作らず、生成器の保護基線検査に限り、固定したcheckoutのGitメタデータを一時的に参照します。旧版のreseal_runtime.py --checkはworkshop/v2.7.0だけを検査し、現在版の証明にはなりません。現在版のバイト単位の再現性は未確認です。Python 3.13の使用だけでバイト一致が保証されるわけではありません。差分があれば一覧を記録して停止し、生成した出力は使いません。配置元を変更せず、生成物を配置元へ戻したり、配布・配置に使ったりしません。CSV・NotebookのSHAだけを確認する参加者は、この再生成検査を行う必要はありません。

**Readable wrapped view — PowerShell**

<div>
$ErrorActionPreference = "Stop"<br>
python -c "import sys; assert sys.version_info[:2] == (3, 13)"<br>
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for the current generator compatibility check; this alone does not guarantee byte identity" }<br>
$Dirty = git status --porcelain<br>
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }<br>
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }<br>
$GitDir = (git rev-parse --absolute-git-dir).Trim()<br>
if ($LASTEXITCODE -ne 0) { throw "Could not locate the pinned checkout's Git metadata" }<br>
$CheckRoot = Join-Path $env:USERPROFILE ("Furusato-current-generation-check-" + [guid]::NewGuid().ToString("N"))<br>
New-Item -ItemType Directory -Path $CheckRoot | Out-Null<br>
$Archive = Join-Path $CheckRoot "source.zip"<br>
$Source = Join-Path $CheckRoot "source"<br>
$BeforeInventory = Join-Path $CheckRoot "before.json"<br>
$AfterInventory = Join-Path $CheckRoot "after.json"<br>
$Inventory = "import hashlib,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}; out.write_text(json.dumps(files,sort_keys=True,indent=2),encoding='utf-8')"<br>
$Compare = "import json,pathlib,sys; before=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); after=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')); diff=[{'path':p,'before':before.get(p),'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)]; print(json.dumps(diff,indent=2)); raise SystemExit(1 if diff else 0)"<br>
git archive --format=zip --output=$Archive HEAD<br>
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }<br>
Expand-Archive -LiteralPath $Archive -DestinationPath $Source<br>
python -c $Inventory $Source $BeforeInventory<br>
if ($LASTEXITCODE -ne 0) { throw "Could not hash the accepted archive" }<br>
Write-Output ("Private check evidence: " + $CheckRoot)<br>
Push-Location -LiteralPath $Source<br>
$PreviousGitDir = $env:GIT_DIR<br>
$PreviousGitWorkTree = $env:GIT_WORK_TREE<br>
$env:GIT_DIR = $GitDir<br>
$env:GIT_WORK_TREE = $Source<br>
try {<br>
    python -B ./tools/provisioning/build_preview30.py<br>
    if ($LASTEXITCODE -ne 0) { throw "Current source generation failed; do not use this copy" }<br>
    python -c $Inventory $Source $AfterInventory<br>
    if ($LASTEXITCODE -ne 0) { throw "Could not hash generated files" }<br>
    python -c $Compare $BeforeInventory $AfterInventory<br>
    if ($LASTEXITCODE -eq 1) { throw "Current generation differs from accepted bytes; record the hashes and stop" }<br>
    if ($LASTEXITCODE -ne 0) { throw "File inventory comparison failed" }<br>
}<br>
finally {<br>
    if ($null -eq $PreviousGitDir) { Remove-Item Env:GIT_DIR -ErrorAction SilentlyContinue }<br>
    else { $env:GIT_DIR = $PreviousGitDir }<br>
    if ($null -eq $PreviousGitWorkTree) { Remove-Item Env:GIT_WORK_TREE -ErrorAction SilentlyContinue }<br>
    else { $env:GIT_WORK_TREE = $PreviousGitWorkTree }<br>
    Pop-Location<br>
}
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
$ErrorActionPreference = "Stop"
python -c "import sys; assert sys.version_info[:2] == (3, 13)"
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for the current generator compatibility check; this alone does not guarantee byte identity" }
$Dirty = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }
$GitDir = (git rev-parse --absolute-git-dir).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not locate the pinned checkout's Git metadata" }
$CheckRoot = Join-Path $env:USERPROFILE ("Furusato-current-generation-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $CheckRoot | Out-Null
$Archive = Join-Path $CheckRoot "source.zip"
$Source = Join-Path $CheckRoot "source"
$BeforeInventory = Join-Path $CheckRoot "before.json"
$AfterInventory = Join-Path $CheckRoot "after.json"
$Inventory = "import hashlib,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}; out.write_text(json.dumps(files,sort_keys=True,indent=2),encoding='utf-8')"
$Compare = "import json,pathlib,sys; before=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); after=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')); diff=[{'path':p,'before':before.get(p),'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)]; print(json.dumps(diff,indent=2)); raise SystemExit(1 if diff else 0)"
git archive --format=zip --output=$Archive HEAD
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }
Expand-Archive -LiteralPath $Archive -DestinationPath $Source
python -c $Inventory $Source $BeforeInventory
if ($LASTEXITCODE -ne 0) { throw "Could not hash the accepted archive" }
Write-Output ("Private check evidence: " + $CheckRoot)
Push-Location -LiteralPath $Source
$PreviousGitDir = $env:GIT_DIR
$PreviousGitWorkTree = $env:GIT_WORK_TREE
$env:GIT_DIR = $GitDir
$env:GIT_WORK_TREE = $Source
try {
    python -B ./tools/provisioning/build_preview30.py
    if ($LASTEXITCODE -ne 0) { throw "Current source generation failed; do not use this copy" }
    python -c $Inventory $Source $AfterInventory
    if ($LASTEXITCODE -ne 0) { throw "Could not hash generated files" }
    python -c $Compare $BeforeInventory $AfterInventory
    if ($LASTEXITCODE -eq 1) { throw "Current generation differs from accepted bytes; record the hashes and stop" }
    if ($LASTEXITCODE -ne 0) { throw "File inventory comparison failed" }
}
finally {
    if ($null -eq $PreviousGitDir) { Remove-Item Env:GIT_DIR -ErrorAction SilentlyContinue }
    else { $env:GIT_DIR = $PreviousGitDir }
    if ($null -eq $PreviousGitWorkTree) { Remove-Item Env:GIT_WORK_TREE -ErrorAction SilentlyContinue }
    else { $env:GIT_WORK_TREE = $PreviousGitWorkTree }
    Pop-Location
}
```

検査後も配置元は元の固定コミットです。差分やエラーがあれば停止して記録し、生成した出力を使わずに原因を調べます。この検査はFabricの認証・実行・回答精度の確認とは別です。

<details>
<summary>English</summary>

## 24.11 Verify distributed data and runtime assets

This check requires PowerShell 7 (pwsh). On Windows, install it during the Chapter 24.4 environment setup if needed. On Linux, follow Microsoft's official installation instructions before running it: https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-linux

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

Only when checking source regeneration, use a clean checkout pinned to a commit and Python 3.13. The command below extracts that commit into a separate copy and compares SHA-256 inventories of all files before and after generation. The extracted copy has no .git directory; for the builder's protected-baseline check only, it temporarily refers to Git metadata from the pinned checkout. The legacy reseal_runtime.py --check examines workshop/v2.7.0 only; it does not prove the current edition. Current byte-for-byte regeneration is not qualified, and using Python 3.13 alone does not guarantee byte identity. If files differ, record the list and stop; do not use generated output. The source checkout is not modified, and generated files must not be copied back, distributed or deployed. Participants who only need CSV/Notebook hashes do not need this regeneration check.

**Readable wrapped view — PowerShell**

<div>
$ErrorActionPreference = "Stop"<br>
python -c "import sys; assert sys.version_info[:2] == (3, 13)"<br>
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for the current generator compatibility check; this alone does not guarantee byte identity" }<br>
$Dirty = git status --porcelain<br>
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }<br>
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }<br>
$GitDir = (git rev-parse --absolute-git-dir).Trim()<br>
if ($LASTEXITCODE -ne 0) { throw "Could not locate the pinned checkout's Git metadata" }<br>
$CheckRoot = Join-Path $env:USERPROFILE ("Furusato-current-generation-check-" + [guid]::NewGuid().ToString("N"))<br>
New-Item -ItemType Directory -Path $CheckRoot | Out-Null<br>
$Archive = Join-Path $CheckRoot "source.zip"<br>
$Source = Join-Path $CheckRoot "source"<br>
$BeforeInventory = Join-Path $CheckRoot "before.json"<br>
$AfterInventory = Join-Path $CheckRoot "after.json"<br>
$Inventory = "import hashlib,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}; out.write_text(json.dumps(files,sort_keys=True,indent=2),encoding='utf-8')"<br>
$Compare = "import json,pathlib,sys; before=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); after=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')); diff=[{'path':p,'before':before.get(p),'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)]; print(json.dumps(diff,indent=2)); raise SystemExit(1 if diff else 0)"<br>
git archive --format=zip --output=$Archive HEAD<br>
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }<br>
Expand-Archive -LiteralPath $Archive -DestinationPath $Source<br>
python -c $Inventory $Source $BeforeInventory<br>
if ($LASTEXITCODE -ne 0) { throw "Could not hash the accepted archive" }<br>
Write-Output ("Private check evidence: " + $CheckRoot)<br>
Push-Location -LiteralPath $Source<br>
$PreviousGitDir = $env:GIT_DIR<br>
$PreviousGitWorkTree = $env:GIT_WORK_TREE<br>
$env:GIT_DIR = $GitDir<br>
$env:GIT_WORK_TREE = $Source<br>
try {<br>
    python -B ./tools/provisioning/build_preview30.py<br>
    if ($LASTEXITCODE -ne 0) { throw "Current source generation failed; do not use this copy" }<br>
    python -c $Inventory $Source $AfterInventory<br>
    if ($LASTEXITCODE -ne 0) { throw "Could not hash generated files" }<br>
    python -c $Compare $BeforeInventory $AfterInventory<br>
    if ($LASTEXITCODE -eq 1) { throw "Current generation differs from accepted bytes; record the hashes and stop" }<br>
    if ($LASTEXITCODE -ne 0) { throw "File inventory comparison failed" }<br>
}<br>
finally {<br>
    if ($null -eq $PreviousGitDir) { Remove-Item Env:GIT_DIR -ErrorAction SilentlyContinue }<br>
    else { $env:GIT_DIR = $PreviousGitDir }<br>
    if ($null -eq $PreviousGitWorkTree) { Remove-Item Env:GIT_WORK_TREE -ErrorAction SilentlyContinue }<br>
    else { $env:GIT_WORK_TREE = $PreviousGitWorkTree }<br>
    Pop-Location<br>
}
</div>

**Verbatim source follows; copy from the canonical block.**

**PowerShell**

```powershell
$ErrorActionPreference = "Stop"
python -c "import sys; assert sys.version_info[:2] == (3, 13)"
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for the current generator compatibility check; this alone does not guarantee byte identity" }
$Dirty = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }
$GitDir = (git rev-parse --absolute-git-dir).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not locate the pinned checkout's Git metadata" }
$CheckRoot = Join-Path $env:USERPROFILE ("Furusato-current-generation-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $CheckRoot | Out-Null
$Archive = Join-Path $CheckRoot "source.zip"
$Source = Join-Path $CheckRoot "source"
$BeforeInventory = Join-Path $CheckRoot "before.json"
$AfterInventory = Join-Path $CheckRoot "after.json"
$Inventory = "import hashlib,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}; out.write_text(json.dumps(files,sort_keys=True,indent=2),encoding='utf-8')"
$Compare = "import json,pathlib,sys; before=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); after=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')); diff=[{'path':p,'before':before.get(p),'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)]; print(json.dumps(diff,indent=2)); raise SystemExit(1 if diff else 0)"
git archive --format=zip --output=$Archive HEAD
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }
Expand-Archive -LiteralPath $Archive -DestinationPath $Source
python -c $Inventory $Source $BeforeInventory
if ($LASTEXITCODE -ne 0) { throw "Could not hash the accepted archive" }
Write-Output ("Private check evidence: " + $CheckRoot)
Push-Location -LiteralPath $Source
$PreviousGitDir = $env:GIT_DIR
$PreviousGitWorkTree = $env:GIT_WORK_TREE
$env:GIT_DIR = $GitDir
$env:GIT_WORK_TREE = $Source
try {
    python -B ./tools/provisioning/build_preview30.py
    if ($LASTEXITCODE -ne 0) { throw "Current source generation failed; do not use this copy" }
    python -c $Inventory $Source $AfterInventory
    if ($LASTEXITCODE -ne 0) { throw "Could not hash generated files" }
    python -c $Compare $BeforeInventory $AfterInventory
    if ($LASTEXITCODE -eq 1) { throw "Current generation differs from accepted bytes; record the hashes and stop" }
    if ($LASTEXITCODE -ne 0) { throw "File inventory comparison failed" }
}
finally {
    if ($null -eq $PreviousGitDir) { Remove-Item Env:GIT_DIR -ErrorAction SilentlyContinue }
    else { $env:GIT_DIR = $PreviousGitDir }
    if ($null -eq $PreviousGitWorkTree) { Remove-Item Env:GIT_WORK_TREE -ErrorAction SilentlyContinue }
    else { $env:GIT_WORK_TREE = $PreviousGitWorkTree }
    Pop-Location
}
```

The original pinned commit remains the deployment source after the check. Stop and record any diff or error, and diagnose it without using generated output. This check is separate from Fabric authentication, execution and answer-quality verification.

</details>
