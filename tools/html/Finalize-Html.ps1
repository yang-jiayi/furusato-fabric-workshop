<#
.SYNOPSIS
    Finalize the bilingual HTML guide against a pinned Word release.

.DESCRIPTION
    Runs the whole finalization in one step and refuses to declare success
    unless the mirror provably matches the pinned Word deliverables:

        1. report translation drift and drop obsolete mirror entries
        2. build docs/furusato-workshop-v2-7-0-complete.html
        3. validate, pinning the Office digests and the Word structural totals
        4. run the headless interaction suite

    Any failing step stops the run. The pinned digests default to the Office
    release currently in docs/, which is the deterministic final one.

    For a layout-only reissue (Word repaginates the DOCX but text, tables and
    runtime are unchanged) pass -LayoutOnlyParticipantSha together with
    -ContentFingerprint. The build then records the new release digest while
    keeping the on-disk digest beside it, and refuses if the content model moved.

.EXAMPLE
    pwsh tools/html/Finalize-Html.ps1
    pwsh tools/html/Finalize-Html.ps1 -Artifacts $env:TEMP\furusato-html
    pwsh tools/html/Finalize-Html.ps1 -LayoutOnlyParticipantSha <v5> -ContentFingerprint <v4-content>
#>
[CmdletBinding()]
param(
    [ValidatePattern('^$|^[a-z0-9]+(?:[-_][a-z0-9]+)*$')]
    [ValidateLength(0, 40)]
    [string]$Edition = '',
    [string]$ParticipantSha = '9632c04b57ca26cebdf1b1bb796d24201cd7ae1f2465eccf475e3ebf0a767e32',
    [string]$TestRecordSha  = '2ee87fda5fcf8b263759ab1ecc4accc5cbcb6b6e904d96e8e9a9b1dae10a049f',
    [string]$WorkbookSha    = '22c666033a9a97819b918f056a3ebe09f028246e38b2487dc5510ccef8d2f89b',
    [string]$ChecklistSha   = '7f014a4319d4213b1d57c88cb4852fc15b58b6a2782099901f1ac91a67cdf1c3',
    # A layout-only Office reissue repaginates the DOCX without changing text,
    # tables or runtime. Supply its digest here together with -ContentFingerprint:
    # the build records it as the release digest, keeps the on-disk digest beside
    # it, and refuses if the content model moved at all.
    [string]$LayoutOnlyParticipantSha,
    [string]$ContentFingerprint,
    [int]$Chapters = 24,
    [int]$Headings = 144,
    [int]$Tables   = 118,
    [int]$Figures  = 101,
    [int]$Tests    = 10,
    [string]$Artifacts,
    [switch]$PublicDocumentsOnly,
    [string]$Out
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $repoRoot
try {
    if ($PublicDocumentsOnly) {
        if (-not $Edition -or -not $Out) {
            throw '-PublicDocumentsOnly requires -Edition and an external -Out holding the participant Word.'
        }
        if ($LayoutOnlyParticipantSha -or $PSBoundParameters.ContainsKey('TestRecordSha') -or $PSBoundParameters.ContainsKey('WorkbookSha')) {
            throw 'Public mode requires the actual participant hash only; companion pins and layout-only restamping are not allowed.'
        }
        if ($Artifacts) {
            $pairPath = [IO.Path]::GetFullPath($Out).TrimEnd('\', '/')
            $artifactPath = [IO.Path]::GetFullPath($Artifacts)
            if ($artifactPath -eq $pairPath -or $artifactPath.StartsWith("$pairPath\", [StringComparison]::OrdinalIgnoreCase)) {
                throw '-Artifacts must be outside the public document directory.'
            }
        }
    }
    if ($Edition) {
        $requiredPins = @('ParticipantSha', 'Chapters', 'Headings', 'Tables', 'Figures', 'Tests')
        if (-not $PublicDocumentsOnly) { $requiredPins += @('TestRecordSha', 'WorkbookSha') }
        foreach ($pin in $requiredPins) {
            if (-not $PSBoundParameters.ContainsKey($pin)) {
                throw "Named edition finalization requires -$pin from that edition's release evidence; original-release pins must not be reused."
            }
        }
    }
    $version = (Get-Content (Join-Path $repoRoot 'VERSION') -Raw).Trim()
    $suffix = if ($Edition) { "_$Edition" } else { '' }
    $participant = "Fabric_IQ_Ontology_Workshop_Furusato_Participant_v$version$suffix.docx"
    $testRecord  = "Furusato_Data_Agent_Validation_10_v$version$suffix.docx"
    $workbook    = "Furusato_Notebook_01-05_Processing_Specification_v$version$suffix.xlsx"
    $htmlName = "furusato-workshop-v$($version.Replace('.', '-'))-complete$suffix.html"

    # The checklist is not embedded in the HTML, so it is verified here rather
    # than by the validator: a stale checklist means a stale Word release.
    if (-not $PublicDocumentsOnly) {
        $checklistPath = Join-Path $repoRoot 'docs/data-validation-checklist.md'
        $actual = (Get-FileHash $checklistPath -Algorithm SHA256).Hash.ToLower()
        if ($actual -ne $ChecklistSha.ToLower()) {
            throw "docs/data-validation-checklist.md is $actual, expected $ChecklistSha. The pinned Word release is not on disk; refusing to finalize."
        }
        Write-Host "==> checklist digest matches the pinned release" -ForegroundColor Cyan
    }

    Write-Host '==> translation drift' -ForegroundColor Cyan
    $driftArgs = @('tools/html/sync_i18n.py')
    if ($PublicDocumentsOnly) { $driftArgs += '--public-documents-only' } else { $driftArgs += '--prune' }
    & python @driftArgs
    if ($LASTEXITCODE -ne 0) { throw 'the English mirror is incomplete; translate the reported delta first' }

    Write-Host '==> build' -ForegroundColor Cyan
    $buildArgs = @('tools/html/build_html.py')
    if ($Out) { $buildArgs += @('--out', $Out) }
    if ($Edition) { $buildArgs += @('--edition', $Edition) }
    if ($PublicDocumentsOnly) { $buildArgs += '--public-documents-only' }
    if ($LayoutOnlyParticipantSha) {
        if (-not $ContentFingerprint) {
            throw '-LayoutOnlyParticipantSha requires -ContentFingerprint so the "layout only" claim is checked, not trusted.'
        }
        $buildArgs += @('--release-digest', "$participant=$LayoutOnlyParticipantSha",
                        '--content-fingerprint', $ContentFingerprint)
        $ParticipantSha = $LayoutOnlyParticipantSha
    }
    & python @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "build_html.py exited with $LASTEXITCODE" }

    Write-Host '==> validate (pinned)' -ForegroundColor Cyan
    $validateArgs = @(
        'tools/html/validate_html.py',
        '--expect-source', "$participant=$ParticipantSha",
        '--expect-shape', "chapters=$Chapters",
        '--expect-shape', "headings=$Headings",
        '--expect-shape', "tables=$Tables",
        '--expect-shape', "figures=$Figures",
        '--expect-shape', "tests=$Tests"
    )
    if (-not $PublicDocumentsOnly) {
        $validateArgs += @('--expect-source', "$testRecord=$TestRecordSha", '--expect-source', "$workbook=$WorkbookSha")
    }
    if ($Out) { $validateArgs += @('--out', $Out) }
    if ($Edition) { $validateArgs += @('--edition', $Edition) }
    if ($PublicDocumentsOnly) { $validateArgs += '--public-documents-only' }
    & python @validateArgs
    if ($LASTEXITCODE -ne 0) { throw 'validation failed against the pinned Word release' }

    Write-Host '==> interaction tests' -ForegroundColor Cyan
    $testArgs = @('tools/html/tests/test_interaction.py')
    $targetDirectory = if ($Out) { $Out } else { Join-Path $repoRoot 'docs' }
    $testArgs += @('--target', (Join-Path $targetDirectory $htmlName))
    if ($Artifacts) { $testArgs += @('--artifacts', $Artifacts) }
    & python @testArgs
    if ($LASTEXITCODE -ne 0) { throw 'interaction tests reported failures' }

    Write-Host ''
    Write-Host 'FINALIZED — the HTML mirrors the pinned Word release.' -ForegroundColor Green
    Get-FileHash (Join-Path $targetDirectory $htmlName) -Algorithm SHA256 |
        Format-List Algorithm, Hash, Path
}
finally {
    Pop-Location
}
