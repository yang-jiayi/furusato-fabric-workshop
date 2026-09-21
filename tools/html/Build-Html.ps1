<#
.SYNOPSIS
    Build and validate the bilingual single-file HTML participant guide.

.DESCRIPTION
    Wraps tools/html/build_html.py and tools/html/validate_html.py, and can also
    run the headless interaction tests. Any non-zero exit stops the pipeline.

.EXAMPLE
    pwsh tools/html/Build-Html.ps1
    pwsh tools/html/Build-Html.ps1 -Interaction -Artifacts $env:TEMP\furusato-html
#>
[CmdletBinding()]
param(
    [string]$Out,
    [string]$Edition = '',
    [switch]$SkipValidate,
    [switch]$Interaction,
    [string]$Artifacts,
    [switch]$Json,
    [switch]$PublicDocumentsOnly
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $repoRoot
try {
    if ($PublicDocumentsOnly) {
        if (-not $Edition -or -not $Out) {
            throw '-PublicDocumentsOnly requires -Edition and external -Out containing the participant Word.'
        }
        if ($Artifacts) {
            $pairPath = [IO.Path]::GetFullPath($Out).TrimEnd('\', '/')
            $artifactPath = [IO.Path]::GetFullPath($Artifacts)
            if ($artifactPath -eq $pairPath -or $artifactPath.StartsWith("$pairPath\", [StringComparison]::OrdinalIgnoreCase)) {
                throw '-Artifacts must be outside the public document directory.'
            }
        }
    }
    $buildArgs = @('tools/html/build_html.py')
    if ($Out) { $buildArgs += @('--out', $Out) }
    if ($Edition) { $buildArgs += @('--edition', $Edition) }
    if ($PublicDocumentsOnly) { $buildArgs += '--public-documents-only' }
    if ($Json) { $buildArgs += '--json' }

    Write-Host '==> build' -ForegroundColor Cyan
    & python @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "build_html.py exited with $LASTEXITCODE" }

    if (-not $SkipValidate) {
        Write-Host '==> validate' -ForegroundColor Cyan
        $validateArgs = @('tools/html/validate_html.py')
        if ($Out) { $validateArgs += @('--out', $Out) }
        if ($Edition) { $validateArgs += @('--edition', $Edition) }
        if ($PublicDocumentsOnly) { $validateArgs += '--public-documents-only' }
        if ($Json) { $validateArgs += '--json' }
        & python @validateArgs
        if ($LASTEXITCODE -ne 0) { throw "validate_html.py reported failures" }
    }

    if ($Interaction) {
        Write-Host '==> interaction tests' -ForegroundColor Cyan
        $testArgs = @('tools/html/tests/test_interaction.py')
        $version = (Get-Content (Join-Path $repoRoot 'VERSION') -Raw).Trim().Replace('.', '-')
        $suffix = if ($Edition) { "_$Edition" } else { '' }
        $targetDirectory = if ($Out) { $Out } else { Join-Path $repoRoot 'docs' }
        $testArgs += @('--target', (Join-Path $targetDirectory "furusato-workshop-v$version-complete$suffix.html"))
        if ($Artifacts) { $testArgs += @('--artifacts', $Artifacts) }
        & python @testArgs
        if ($LASTEXITCODE -ne 0) { throw "interaction tests reported failures" }
    }

    Write-Host 'done' -ForegroundColor Green
}
finally {
    Pop-Location
}
