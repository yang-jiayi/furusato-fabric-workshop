[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Stage,
    [string]$EvidenceManifest,
    [string]$PublicEvidenceManifest,
    [string]$EvaluationReport,
    [switch]$RequireAcceptance,
    [string]$AcceptanceApproval,
    [ValidateSet('preview', 'v3.0.0')][string]$ReleaseProfile = 'preview',
    [string]$ReleaseApproval
)

$ErrorActionPreference = 'Stop'
if ($EvidenceManifest -and $PublicEvidenceManifest) {
    throw 'Choose private evidence OR an approved public projection, never both.'
}
if ($AcceptanceApproval -and -not $RequireAcceptance) {
    throw 'AcceptanceApproval requires RequireAcceptance.'
}
if ($RequireAcceptance -and ($EvidenceManifest -or -not $PublicEvidenceManifest)) {
    throw 'Final admission requires an explicitly selected reviewed PublicEvidenceManifest.'
}
if ($ReleaseApproval -and $ReleaseProfile -ne 'v3.0.0') {
    throw 'ReleaseApproval requires ReleaseProfile v3.0.0.'
}
if ($ReleaseProfile -eq 'v3.0.0' -and (-not $ReleaseApproval -or $EvidenceManifest -or $EvaluationReport)) {
    throw 'v3.0.0 requires a private known-limitations ReleaseApproval and a source-owned public projection without private overrides.'
}
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$stagePath = [System.IO.Path]::GetFullPath($Stage, (Get-Location).ProviderPath)
$rootPrefix = $root.TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
if ($stagePath.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or
    $stagePath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Choose a fresh PRIVATE stage outside the public source tree.'
}
if (Test-Path -LiteralPath $stagePath) {
    throw 'The stage already exists; choose a new directory. No files were overwritten.'
}
if ($EvidenceManifest) {
    $EvidenceManifest = (Resolve-Path -LiteralPath $EvidenceManifest).Path
}
if ($PublicEvidenceManifest) {
    $PublicEvidenceManifest = (Resolve-Path -LiteralPath $PublicEvidenceManifest).Path
}
if ($EvaluationReport) {
    $EvaluationReport = (Resolve-Path -LiteralPath $EvaluationReport).Path
}
if ($ReleaseApproval) {
    $ReleaseApproval = (Resolve-Path -LiteralPath $ReleaseApproval).Path
}
$pair = Join-Path $stagePath 'pair'
$review = Join-Path $stagePath 'review'
$checks = Join-Path $stagePath 'checks'
$package = Join-Path $stagePath 'package'
$previousEncoding = $env:PYTHONIOENCODING
$env:PYTHONIOENCODING = 'utf-8'

function Invoke-PythonChecked {
    param([string[]]$Arguments)
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Local command failed (exit $LASTEXITCODE). Preserve the draft/logs and correct the failure; do not claim verification."
    }
}

Push-Location $root
try {
    $buildArgs = @((Join-Path $PSScriptRoot 'build_preview30.py'), '--out', $pair, '--review', $review)
    $checkArgs = @((Join-Path $PSScriptRoot 'validate_preview30.py'), '--pair', $pair, '--review', $checks,
        '--render', '--interactions', '--print-html')
    $packArgs = @((Join-Path $PSScriptRoot 'package_preview30.py'), '--pair', $pair,
        '--validation', (Join-Path $checks 'validation.json'), '--out', $package)
    $buildArgs += @('--release-profile', $ReleaseProfile)
    $checkArgs += @('--release-profile', $ReleaseProfile)
    $packArgs += @('--release-profile', $ReleaseProfile)
    if ($ReleaseApproval) {
        $buildArgs += @('--release-approval', $ReleaseApproval)
        $checkArgs += @('--release-approval', $ReleaseApproval)
        $packArgs += @('--release-approval', $ReleaseApproval)
    }
    if ($RequireAcceptance) {
        $buildArgs += '--require-acceptance'
        $packArgs += '--require-acceptance'
        if ($AcceptanceApproval) {
            $approvalPath = (Resolve-Path -LiteralPath $AcceptanceApproval).Path
            $buildArgs += @('--acceptance-approval', $approvalPath)
            $packArgs += @('--acceptance-approval', $approvalPath)
        }
    }
    if ($EvidenceManifest) {
        $buildArgs += @('--evidence', $EvidenceManifest)
        $checkArgs += @('--evidence', $EvidenceManifest)
        $packArgs += @('--evidence', $EvidenceManifest)
    }
    if ($PublicEvidenceManifest) {
        $buildArgs += @('--public-evidence', $PublicEvidenceManifest)
        $checkArgs += @('--public-evidence', $PublicEvidenceManifest)
        $packArgs += @('--public-evidence', $PublicEvidenceManifest)
    }
    if ($EvaluationReport) {
        $buildArgs += @('--evaluation-report', $EvaluationReport)
        $checkArgs += @('--evaluation-report', $EvaluationReport)
        $packArgs += @('--evaluation-report', $EvaluationReport)
    }
    Invoke-PythonChecked -Arguments @((Join-Path $root 'tools\preview30-attachments\test_attachments.py'))
    Invoke-PythonChecked -Arguments $buildArgs
    Invoke-PythonChecked -Arguments $checkArgs
    Invoke-PythonChecked -Arguments $packArgs
    if ($ReleaseProfile -eq 'v3.0.0') {
        Write-Output "User-authorized 3.0.0 known-limitations document pair: $pair"
        Write-Output "Portable 3.0.0 document package (AI unaccepted, not GA or Agent promotion): $package"
    }
    else {
        Write-Output "LOCAL DRAFT ready: $pair"
        Write-Output "Portable DRAFT package: $package"
    }
    Write-Output 'No Fabric authentication, deployment, permission change, commit, push or publication was performed.'
}
finally {
    Pop-Location
    if ($null -eq $previousEncoding) {
        Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONIOENCODING = $previousEncoding
    }
}
