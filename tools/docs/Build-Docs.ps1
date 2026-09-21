<#
.SYNOPSIS
    Build and validate the Furusato v2.7.0 Office deliverables.

.DESCRIPTION
    Thin wrapper around tools/docs/build_docs.py and tools/docs/validate_docs.py so
    the deliverables can be reproduced with one command. Exits non-zero when the
    build or the validation fails.

.PARAMETER OutputDirectory
    Where to write the deliverables. Defaults to 'docs'.

.PARAMETER Edition
    Append a correction edition to each filename without replacing the originals.

.PARAMETER SkipWord
    Skip the optional Word COM field and table-of-contents refresh.

.PARAMETER PublicDocumentsOnly
    Build/validate only the participant Word in a fresh external OutputDirectory.
    Requires Edition; never removes or overwrites an existing release.

.PARAMETER SkipExcel
    Skip the optional Excel COM formula recalculation.

.PARAMETER KeepLegacy
    Keep the superseded deliverables this release replaces instead of deleting them.
    Deleting them is a no-op on a clean checkout.

.PARAMETER ValidateOnly
    Run the validators against an existing build without rebuilding.

.PARAMETER CheckUrls
    Also probe the reference URLs during validation.

.PARAMETER Render
    Also render every page with Word and reject blank or caption-only pages.

.EXAMPLE
    ./tools/docs/Build-Docs.ps1

.EXAMPLE
    ./tools/docs/Build-Docs.ps1 -Render -CheckUrls

.EXAMPLE
    ./tools/docs/Build-Docs.ps1 -OutputDirectory _out -KeepLegacy -SkipWord
#>
[CmdletBinding()]
param(
    [string]$OutputDirectory = 'docs',
    [string]$Edition = '',
    [switch]$SkipWord,
    [switch]$SkipExcel,
    [switch]$KeepLegacy,
    [switch]$ValidateOnly,
    [switch]$CheckUrls,
    [switch]$Render,
    [switch]$PublicDocumentsOnly
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $repoRoot
try {
    $env:PYTHONIOENCODING = 'utf-8'
    if ($PublicDocumentsOnly -and (-not $Edition -or -not $PSBoundParameters.ContainsKey('OutputDirectory'))) {
        throw '-PublicDocumentsOnly requires -Edition and an explicit external -OutputDirectory.'
    }

    if (-not $ValidateOnly) {
        $buildArgs = @('tools/docs/build_docs.py', '--out', $OutputDirectory)
        if ($Edition) { $buildArgs += @('--edition', $Edition) }
        if ($PublicDocumentsOnly) { $buildArgs += '--public-documents-only' }
        if ($SkipWord) { $buildArgs += '--skip-word' }
        if ($SkipExcel) { $buildArgs += '--skip-excel' }
        if ($KeepLegacy) { $buildArgs += '--keep-legacy' }
        Write-Host "Building deliverables into $OutputDirectory ..." -ForegroundColor Cyan
        & python @buildArgs
        if ($LASTEXITCODE -ne 0) { throw "build_docs.py exited with $LASTEXITCODE" }
    }

    $validateArgs = @('tools/docs/validate_docs.py', '--out', $OutputDirectory)
    if ($Edition) { $validateArgs += @('--edition', $Edition) }
    if ($PublicDocumentsOnly) { $validateArgs += '--public-documents-only' }
    if ($CheckUrls) { $validateArgs += '--check-urls' }
    if ($Render) { $validateArgs += '--render' }
    Write-Host "Validating deliverables in $OutputDirectory ..." -ForegroundColor Cyan
    & python @validateArgs
    if ($LASTEXITCODE -ne 0) { throw "validate_docs.py reported failures (exit $LASTEXITCODE)" }

    Write-Host 'All deliverables built and validated.' -ForegroundColor Green
}
finally {
    Pop-Location
}
