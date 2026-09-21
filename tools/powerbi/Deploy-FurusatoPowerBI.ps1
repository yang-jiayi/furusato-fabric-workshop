#Requires -Version 7.0

[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}$')]
    [string]$WorkspaceId,

    [ValidatePattern('^(?!000$)[0-9]{3}$')]
    [string]$ParticipantId = '001',

    [string]$LakehouseId,

    [string]$FolderId,

    [string]$ExpectedUserPrincipalName,

    [string]$ExpectedTenantId,

    [string]$ProjectRoot = (
        Join-Path $PSScriptRoot '..\..\workshop\v2.7.0\powerbi'
    ),

    [string]$SemanticModelName,

    [string]$ReportName,

    [switch]$Apply,

    [switch]$UpdateExisting,

    [string]$Confirmation,

    [ValidateRange(60, 1800)]
    [int]$OperationTimeoutSeconds = 600
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$api = 'https://api.fabric.microsoft.com/v1'
$resource = 'https://api.fabric.microsoft.com'
$modelSource = Join-Path $ProjectRoot 'Furusato_Analytics.SemanticModel'
$reportSource = Join-Path $ProjectRoot 'Furusato_Analytics.Report'

if (-not $SemanticModelName) {
    $SemanticModelName = "SM_Furusato_Analytics_$ParticipantId"
}
if (-not $ReportName) {
    $ReportName = "RPT_Furusato_Analytics_$ParticipantId"
}

foreach ($requiredPath in @(
    (Join-Path $modelSource 'definition.pbism'),
    (Join-Path $modelSource 'definition'),
    (Join-Path $reportSource 'definition.pbir'),
    (Join-Path $reportSource 'definition')
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required PBIP path is missing: $requiredPath"
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory)][byte[]]$Bytes)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return [Convert]::ToHexString($sha.ComputeHash($Bytes)).ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-FabricToken {
    $value = & az account get-access-token `
        --resource $resource `
        --query accessToken `
        -o tsv
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($value)) {
        throw 'Azure CLI could not acquire a Fabric API token.'
    }
    return $value.Trim()
}

function Assert-DeploymentIdentity {
    if (-not $ExpectedUserPrincipalName -and -not $ExpectedTenantId) {
        return
    }
    $accountText = & az account show --output json
    if ($LASTEXITCODE -ne 0) {
        throw 'Azure CLI identity could not be verified.'
    }
    $account = $accountText | ConvertFrom-Json
    if (
        ($ExpectedUserPrincipalName -and $account.user.name -ine $ExpectedUserPrincipalName) -or
        ($ExpectedTenantId -and $account.tenantId -ine $ExpectedTenantId)
    ) {
        throw 'Azure CLI user or tenant does not match the explicit deployment guard.'
    }
}

Assert-DeploymentIdentity
$token = Get-FabricToken
$headers = @{
    Authorization = "Bearer $token"
    'Content-Type' = 'application/json'
}

function Invoke-Fabric {
    param(
        [Parameter(Mandatory)][ValidateSet('GET', 'POST', 'PATCH', 'DELETE')]
        [string]$Method,
        [Parameter(Mandatory)][string]$Url,
        [object]$Body
    )
    $parameters = @{
        Method = $Method
        Uri = $Url
        Headers = $headers
        SkipHttpErrorCheck = $true
    }
    if ($Method -ne 'GET') {
        Assert-DeploymentIdentity
    }
    if ($PSBoundParameters.ContainsKey('Body')) {
        $parameters.Body = (
            $Body | ConvertTo-Json -Depth 100 -Compress
        )
    }
    $response = Invoke-WebRequest @parameters
    $statusCode = [int]$response.StatusCode
    if ($statusCode -ge 400) {
        throw "Fabric API $Method $Url failed ($statusCode): $($response.Content)"
    }
    return [pscustomobject]@{
        StatusCode = [int]$statusCode
        Headers = $response.Headers
        Content = $response.Content
        Json = if ($response.Content) {
            $response.Content | ConvertFrom-Json -Depth 100
        }
        else {
            $null
        }
    }
}

function Wait-FabricOperation {
    param([Parameter(Mandatory)]$Response)
    if ($Response.StatusCode -ne 202) {
        return $Response.Json
    }
    $operationId = [string]$Response.Headers['x-ms-operation-id']
    $location = if ($operationId) {
        "$api/operations/$operationId"
    } else {
        [string]$Response.Headers['Location']
    }
    if (-not $location) {
        throw 'Fabric 202 response did not include a Location header.'
    }
    $monitorUri = [uri]$location
    if ($monitorUri.Scheme -ne 'https' -or $monitorUri.Host -ne 'api.fabric.microsoft.com') {
        throw 'Refusing an operation monitor outside the Fabric API host.'
    }
    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(
        $OperationTimeoutSeconds
    )
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        Start-Sleep -Seconds 5
        $poll = Invoke-Fabric -Method GET -Url $location
        $state = [string]$poll.Json.status
        if ($state -eq 'Succeeded') {
            return $poll.Json
        }
        if ($state -in @('Failed', 'Cancelled')) {
            throw "Fabric operation ended in state $state`: $($poll.Content)"
        }
    }
    throw "Fabric operation timed out after $OperationTimeoutSeconds seconds."
}

function Get-WorkspaceItems {
    $url = "$api/workspaces/$WorkspaceId/items"
    if ($FolderId) {
        $url += "?rootFolderId=$FolderId&recursive=false"
    }
    $result = [Collections.Generic.List[object]]::new()
    do {
        $response = Invoke-Fabric -Method GET -Url $url
        foreach ($item in $response.Json.value) {
            $result.Add($item)
        }
        $continuation = $response.Json.PSObject.Properties['continuationUri']
        $url = if ($continuation) { [string]$continuation.Value } else { $null }
    } while ($url)
    return @($result.ToArray())
}

$workspace = (
    Invoke-Fabric -Method GET -Url "$api/workspaces/$WorkspaceId"
).Json
if (-not $workspace.capacityId) {
    throw 'Target workspace is not assigned to a Fabric capacity.'
}

$items = Get-WorkspaceItems
if (-not $LakehouseId) {
    $lakehouseName = "LH_Furusato_$ParticipantId"
    $matches = @(
        $items | Where-Object {
            $_.type -eq 'Lakehouse' -and
            $_.displayName -eq $lakehouseName
        }
    )
    if ($matches.Count -ne 1) {
        throw (
            "Expected exactly one Lakehouse named '$lakehouseName'; " +
            "found $($matches.Count)."
        )
    }
    $LakehouseId = [string]$matches[0].id
}

$lakehouse = (Invoke-Fabric -Method GET -Url "$api/workspaces/$WorkspaceId/items/$LakehouseId").Json
if ($lakehouse.type -ne 'Lakehouse') {
    throw 'The supplied source item is not a Lakehouse.'
}
$sourceFolder = $lakehouse.PSObject.Properties['folderId']
if (-not $FolderId) {
    $FolderId = if ($sourceFolder) { [string]$sourceFolder.Value } else { '' }
}
$parsedFolder = [guid]::Empty
if (-not [guid]::TryParse($FolderId, [ref]$parsedFolder) -or $parsedFolder -eq [guid]::Empty) {
    throw 'A real target Folder GUID is required; a portal numeric subfolderId is not a Folder GUID.'
}
if (-not $sourceFolder -or [string]$sourceFolder.Value -ne $FolderId) {
    throw 'The Lakehouse and Power BI outputs must use the same participant Folder.'
}
[void](Invoke-Fabric -Method GET -Url "$api/workspaces/$WorkspaceId/folders/$FolderId")

function New-DefinitionParts {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][ValidateSet('SemanticModel', 'Report')]
        [string]$Kind,
        [string]$SemanticModelId
    )
    $parts = [Collections.Generic.List[object]]::new()
    foreach ($file in Get-ChildItem $Root -Recurse -File | Sort-Object FullName) {
        if ($file.Name -eq '.platform') {
            continue
        }
        $relative = [IO.Path]::GetRelativePath(
            $Root,
            $file.FullName
        ).Replace('\', '/')
        $text = [IO.File]::ReadAllText($file.FullName)
        if ($Kind -eq 'SemanticModel') {
            $text = $text.Replace('{{workspace.id}}', $WorkspaceId)
            $text = $text.Replace('{{item.lakehouse.id}}', $LakehouseId)
        }
        elseif ($relative -eq 'definition.pbir') {
            if (-not $SemanticModelId) {
                throw 'SemanticModelId is required to bind the report.'
            }
            $pbir = $text | ConvertFrom-Json -Depth 20
            $pbir.datasetReference = [ordered]@{
                byConnection = [ordered]@{
                    connectionString = "semanticmodelid=$SemanticModelId"
                }
            }
            $text = $pbir | ConvertTo-Json -Depth 20
        }
        if ($text -match '\{\{[^{}]+\}\}') {
            throw "Unresolved placeholder remains in $Kind part '$relative'."
        }
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes($text)
        $parts.Add([ordered]@{
            path = $relative
            payload = [Convert]::ToBase64String($bytes)
            payloadType = 'InlineBase64'
        })
    }
    return @($parts)
}

function Get-PartsDigest {
    param([Parameter(Mandatory)][object[]]$Parts)
    $entries = foreach ($part in $Parts | Sort-Object path) {
        $bytes = [Convert]::FromBase64String([string]$part.payload)
        [ordered]@{
            path = [string]$part.path
            sha256 = Get-Sha256 -Bytes $bytes
        }
    }
    $json = $entries | ConvertTo-Json -Depth 10 -Compress
    return Get-Sha256 -Bytes (
        [Text.UTF8Encoding]::new($false).GetBytes($json)
    )
}

$modelParts = New-DefinitionParts `
    -Root $modelSource `
    -Kind SemanticModel
$previewReportParts = New-DefinitionParts `
    -Root $reportSource `
    -Kind Report `
    -SemanticModelId '00000000-0000-0000-0000-000000000000'
$plan = [ordered]@{
    mode = if ($Apply) { 'Apply' } else { 'Preview' }
    workspaceId = $WorkspaceId
    workspaceName = $workspace.displayName
    capacityId = $workspace.capacityId
    lakehouseId = $LakehouseId
    folderId = $FolderId
    semanticModelName = $SemanticModelName
    semanticModelParts = $modelParts.Count
    semanticModelSha256 = Get-PartsDigest -Parts $modelParts
    reportName = $ReportName
    reportParts = $previewReportParts.Count
    reportPreviewSha256 = Get-PartsDigest -Parts $previewReportParts
}
$planText = $plan | ConvertTo-Json -Depth 10
Write-Output $planText

if (-not $Apply) {
    Write-Output 'PREVIEW_ONLY: no Fabric item was created or updated.'
    return
}

$expectedConfirmation = "DEPLOY POWER BI $ParticipantId"
if ($Confirmation -cne $expectedConfirmation) {
    throw "Set -Confirmation exactly to '$expectedConfirmation'."
}
if (
    -not $PSCmdlet.ShouldProcess(
        $workspace.displayName,
        "deploy $SemanticModelName and $ReportName"
    )
) {
    return
}

$items = Get-WorkspaceItems
$existingModel = @(
    $items | Where-Object {
        $_.type -eq 'SemanticModel' -and
        $_.displayName -eq $SemanticModelName
    }
)
if ($existingModel.Count -gt 1) {
    throw "Multiple SemanticModel items are named '$SemanticModelName'."
}

$modelDefinition = [ordered]@{
    format = 'TMDL'
    parts = $modelParts
}
if ($existingModel.Count -eq 0) {
    $response = Invoke-Fabric -Method POST -Url (
        "$api/workspaces/$WorkspaceId/semanticModels"
    ) -Body ([ordered]@{
        displayName = $SemanticModelName
        folderId = $FolderId
        description = 'Furusato v2.7.0 Direct Lake semantic model'
        definition = $modelDefinition
    })
    [void](Wait-FabricOperation -Response $response)
}
else {
    if (-not $UpdateExisting) {
        throw 'A scoped SemanticModel already exists. Inspect it and use -UpdateExisting only for an intentional update.'
    }
    $modelId = [string]$existingModel[0].id
    $response = Invoke-Fabric -Method POST -Url (
        "$api/workspaces/$WorkspaceId/semanticModels/$modelId/updateDefinition"
    ) -Body ([ordered]@{ definition = $modelDefinition })
    [void](Wait-FabricOperation -Response $response)
}

$items = Get-WorkspaceItems
$modelMatches = @(
    $items | Where-Object {
        $_.type -eq 'SemanticModel' -and
        $_.displayName -eq $SemanticModelName
    }
)
if ($modelMatches.Count -ne 1) {
    throw "SemanticModel verification found $($modelMatches.Count) items."
}
if ([string]$modelMatches[0].folderId -ne $FolderId) {
    throw 'SemanticModel was not created in the requested participant Folder.'
}
$modelId = [string]$modelMatches[0].id

$reportParts = New-DefinitionParts `
    -Root $reportSource `
    -Kind Report `
    -SemanticModelId $modelId
$plan.reportParts = $reportParts.Count
$plan.reportSha256 = Get-PartsDigest -Parts $reportParts

$existingReport = @(
    $items | Where-Object {
        $_.type -eq 'Report' -and
        $_.displayName -eq $ReportName
    }
)
if ($existingReport.Count -gt 1) {
    throw "Multiple Report items are named '$ReportName'."
}
$reportDefinition = [ordered]@{ parts = $reportParts }
if ($existingReport.Count -eq 0) {
    $response = Invoke-Fabric -Method POST -Url (
        "$api/workspaces/$WorkspaceId/reports"
    ) -Body ([ordered]@{
        displayName = $ReportName
        folderId = $FolderId
        description = 'Furusato v2.7.0 Direct Lake report'
        definition = $reportDefinition
    })
    [void](Wait-FabricOperation -Response $response)
}
else {
    if (-not $UpdateExisting) {
        throw 'A scoped Report already exists. Inspect it and use -UpdateExisting only for an intentional update.'
    }
    $reportId = [string]$existingReport[0].id
    $response = Invoke-Fabric -Method POST -Url (
        "$api/workspaces/$WorkspaceId/reports/$reportId/updateDefinition"
    ) -Body ([ordered]@{ definition = $reportDefinition })
    [void](Wait-FabricOperation -Response $response)
}

$items = Get-WorkspaceItems
$reportMatches = @(
    $items | Where-Object {
        $_.type -eq 'Report' -and
        $_.displayName -eq $ReportName
    }
)
if ($reportMatches.Count -ne 1) {
    throw "Report verification found $($reportMatches.Count) items."
}
if ([string]$reportMatches[0].folderId -ne $FolderId) {
    throw 'Report was not created in the requested participant Folder.'
}

[pscustomobject]@{
    Mode = 'Applied'
    WorkspaceId = $WorkspaceId
    LakehouseId = $LakehouseId
    FolderId = $FolderId
    SemanticModelId = $modelId
    SemanticModelName = $SemanticModelName
    SemanticModelParts = $modelParts.Count
    ReportId = [string]$reportMatches[0].id
    ReportName = $ReportName
    ReportParts = $reportParts.Count
    SemanticModelSha256 = $plan.semanticModelSha256
    ReportSha256 = $plan.reportSha256
}
