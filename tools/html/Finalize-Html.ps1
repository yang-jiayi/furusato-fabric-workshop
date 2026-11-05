<#
.SYNOPSIS
    Build and verify a staged Workshop 3.1 HTML guide.

.DESCRIPTION
    Uses the current HTML+Lab delivery renderer in an external, new output
    directory. It does not create an Office document, publish files, or claim
    live Fabric validation.

.EXAMPLE
    pwsh tools/html/Finalize-Html.ps1 -Out $env:TEMP\furusato-v31-guide
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Out,
    [string]$Artifacts
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $repoRoot
try {
    $outputPath = [IO.Path]::GetFullPath($Out)
    $repoPath = [IO.Path]::GetFullPath($repoRoot).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if ($outputPath.StartsWith($repoPath, [StringComparison]::OrdinalIgnoreCase)) {
        throw '-Out must be outside the repository so the staged build cannot replace participant files.'
    }
    if (Test-Path -LiteralPath $outputPath) {
        throw '-Out must be a new directory; existing artifacts are preserved.'
    }

    $version = (Get-Content (Join-Path $repoRoot 'WORKSHOP_VERSION') -Raw).Trim()
    $htmlName = "furusato-workshop-v$($version.Replace('.', '-'))-complete.html"
    $htmlPath = Join-Path $outputPath $htmlName

    Write-Host '==> build current participant HTML' -ForegroundColor Cyan
    & python tools/docs/current_delivery.py build --out $outputPath
    if ($LASTEXITCODE -ne 0) { throw "current_delivery.py build exited with $LASTEXITCODE" }

    Write-Host '==> validate exact staged HTML' -ForegroundColor Cyan
    & python tools/docs/current_delivery.py validate --out $outputPath --browser
    if ($LASTEXITCODE -ne 0) { throw "current_delivery.py validate exited with $LASTEXITCODE" }

    Write-Host '==> participant interaction tests' -ForegroundColor Cyan
    $testArgs = @('tools/html/tests/test_interaction.py', '--target', $htmlPath)
    if ($Artifacts) { $testArgs += @('--artifacts', [IO.Path]::GetFullPath($Artifacts)) }
    & python @testArgs
    if ($LASTEXITCODE -ne 0) { throw 'interaction tests reported failures' }

    Write-Host '==> print geometry tests' -ForegroundColor Cyan
    & python tools/html/tests/test_print_geometry.py --target $htmlPath
    if ($LASTEXITCODE -ne 0) { throw 'print geometry tests reported failures' }

    Write-Host ''
    Write-Host 'STAGED — current HTML checks passed; no release or live-service claim.' -ForegroundColor Green
    Get-FileHash -LiteralPath $htmlPath -Algorithm SHA256 |
        Format-List Algorithm, Hash, Path
}
finally {
    Pop-Location
}
