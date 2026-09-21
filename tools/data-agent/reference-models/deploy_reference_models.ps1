[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [Parameter(Mandatory = $true)][string]$Database,
    [Parameter(Mandatory = $true)][string]$ExpectedUser,
    [Parameter(Mandatory = $true)][string]$TenantId,
    [Parameter(Mandatory = $true)][string]$SubscriptionId,
    [Parameter(Mandatory = $true)][string]$EvidenceDirectory,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-Match([string]$Value, [string]$Pattern, [string]$Label) {
    if ($Value -notmatch $Pattern) { throw "Invalid $Label; deployment refused." }
}

function Write-JsonEvidence([string]$Name, $Value) {
    $path = Join-Path $EvidenceDirectory $Name
    $json = $Value | ConvertTo-Json -Depth 20
    $stream = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes($json + [Environment]::NewLine)
        $stream.Write($bytes, 0, $bytes.Length)
    } finally {
        $stream.Dispose()
    }
}

function Invoke-Query([System.Data.SqlClient.SqlConnection]$Connection, [string]$Sql) {
    $command = $Connection.CreateCommand()
    $reader = $null
    try {
        $command.CommandTimeout = 180
        $command.CommandText = $Sql
        $reader = $command.ExecuteReader()
        $rows = @()
        while ($reader.Read()) {
            $row = [ordered]@{}
            for ($index = 0; $index -lt $reader.FieldCount; $index++) {
                $row[$reader.GetName($index)] = if ($reader.IsDBNull($index)) { $null } else { $reader.GetValue($index) }
            }
            $rows += [pscustomobject]$row
        }
        return @($rows)
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
        $command.Dispose()
    }
}

function Invoke-NonQuery([System.Data.SqlClient.SqlConnection]$Connection, [string]$Sql) {
    $command = $Connection.CreateCommand()
    try {
        $command.CommandTimeout = 180
        $command.CommandText = $Sql
        [void]$command.ExecuteNonQuery()
    } finally {
        $command.Dispose()
    }
}

function Read-NativeCatalog([System.Data.SqlClient.SqlConnection]$Connection) {
    $catalog = [ordered]@{}
    foreach ($name in @("state", "objects", "columns", "parameters", "types", "sourceColumns", "integrity")) {
        $rows = @(Invoke-Query $Connection $validatedPlan.nativeCatalogQueries.$name)
        if ($name -in @("state", "integrity")) {
            if ($rows.Count -ne 1) { throw "Incomplete native $name catalog; deployment refused." }
            $catalog[$name] = $rows[0]
        } else {
            $catalog[$name] = @($rows)
        }
        if ($name -eq "state") {
            if ($catalog.state.DatabaseName -cne $Database -or $catalog.state.CanViewDefinition -ne 1) {
                throw "SQL database mismatch or missing database VIEW DEFINITION visibility; deployment refused."
            }
        }
    }
    return [pscustomobject]$catalog
}

function Get-CatalogDecision($Catalog) {
    # Only DDL and native metadata go to this pure local validator, never tokens.
    $request = [ordered]@{
        database = $Database
        ddl = @($ddl | ForEach-Object { ,@($_.Path, $_.Sql) })
        catalog = $Catalog
    } | ConvertTo-Json -Depth 20 -Compress
    $decisionJson = $request | & python (Join-Path $PSScriptRoot "reference_models.py") --catalog-decision
    if ($LASTEXITCODE -ne 0) { throw "Exact native SQL contract verification failed; no automatic repair is allowed." }
    return ($decisionJson | ConvertFrom-Json).decision
}

Assert-Match $Server '^[a-z0-9-]+\.datawarehouse\.fabric\.microsoft\.com$' "Fabric SQL server"
Assert-Match $Database '^[A-Za-z0-9_]{1,128}$' "database"
Assert-Match $ExpectedUser '^[^@\s]+@[^@\s]+$' "expected user"
Assert-Match $TenantId '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' "tenant ID"
Assert-Match $SubscriptionId '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' "subscription ID"

$planJson = & python (Join-Path $PSScriptRoot "reference_models.py")
if ($LASTEXITCODE -ne 0) { throw "Local DDL contract validation failed." }
$validatedPlan = $planJson | ConvertFrom-Json
$ddlOrder = @(
    "001_create_schema.sql",
    "010_municipality_static.sql",
    "020_donation_attributes.sql",
    "030_gift_catalog_suppliers.sql",
    "040_municipality_by_id.sql",
    "050_donation_by_id.sql",
    "060_donation_trace_by_id.sql"
)
$ddl = @()
foreach ($name in $ddlOrder) {
    $path = Join-Path $PSScriptRoot $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing DDL file: $name" }
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $text = [Text.Encoding]::UTF8.GetString($bytes)
    $batches = @([regex]::Split($text, '(?im)^\s*GO\s*(?:--.*)?$') | Where-Object { $_.Trim() })
    if ($batches.Count -ne 1) { throw "$name must contain exactly one executable batch." }
    if ($text -match '(?i)\b(?:ALTER|DROP|GRANT|DENY|REVOKE|INSERT|UPDATE|DELETE|MERGE|TRUNCATE|BEGIN\s+TRAN(?:SACTION)?|COMMIT|ROLLBACK)\b') {
        throw "Forbidden SQL in $name."
    }
    $hash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
    $pinned = @($validatedPlan.files | Where-Object { $_.path -ceq $name })
    if ($pinned.Count -ne 1 -or $pinned[0].sha256 -cne $hash) {
        throw "DDL changed after local plan validation: $name"
    }
    $ddl += [pscustomobject]@{ Path = $name; Sha256 = $hash; Sql = $batches[0].Trim() }
}

# A dry plan is entirely local: no directory creation, account lookup, token,
# connection, catalog claim, or service write. Only -Apply passes this gate.
if (-not $Apply) {
    $validatedPlan | ConvertTo-Json -Depth 20
    return
}

$accountJson = & az account show --output json
if ($LASTEXITCODE -ne 0) { throw "Azure CLI account lookup failed." }
$account = $accountJson | ConvertFrom-Json
if ($account.user.name.ToLowerInvariant() -ne $ExpectedUser.ToLowerInvariant() -or
    $account.tenantId -ne $TenantId -or $account.id -ne $SubscriptionId) {
    throw "Azure CLI identity, tenant, or subscription mismatch; deployment refused."
}

$tokenJson = & az account get-access-token --resource "https://database.windows.net" --subscription $SubscriptionId --output json
if ($LASTEXITCODE -ne 0) { throw "SQL access-token acquisition failed." }
$tokenResult = $tokenJson | ConvertFrom-Json
$connection = [System.Data.SqlClient.SqlConnection]::new(
    "Server=tcp:$Server,1433;Initial Catalog=$Database;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
)
$connection.AccessToken = $tokenResult.accessToken
$tokenResult = $null
$tokenJson = $null
try {
    $connection.Open()
    $identity = @(Invoke-Query $connection "SELECT SUSER_SNAME() AS LoginName, DB_NAME() AS DatabaseName;")[0]
    if ($identity.LoginName.ToLowerInvariant() -ne $ExpectedUser.ToLowerInvariant() -or $identity.DatabaseName -cne $Database) {
        throw "SQL identity or database mismatch; deployment refused."
    }

    Invoke-NonQuery $connection "SET NOCOUNT ON; SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;"
    $before = Read-NativeCatalog $connection
    $decision = Get-CatalogDecision $before
    if ($decision -notin @("fresh", "reuse")) { throw "Unknown native catalog decision." }

    $evidencePlanJson = & python (Join-Path $PSScriptRoot "reference_models.py") --prepare-evidence $EvidenceDirectory
    if ($LASTEXITCODE -ne 0) { throw "Private evidence path validation failed." }
    $EvidenceDirectory = ($evidencePlanJson | ConvertFrom-Json).evidenceDirectory

    $manifest = [pscustomobject]@{
        CapturedAtUtc = [DateTime]::UtcNow.ToString("o")
        Mode = "apply"
        Decision = $decision
        Identity = $identity
        Target = [pscustomobject]@{ Server = $Server; Database = $Database }
        Ddl = @($ddl | Select-Object Path, Sha256)
        SourceIntegrity = $before.integrity
    }
    Write-JsonEvidence "plan.json" $manifest
    Write-JsonEvidence "source-catalog-before.json" $before.sourceColumns
    Write-JsonEvidence "before-objects.json" $before.objects

    $operations = @()
    $pendingDdl = @()
    if ($decision -eq "fresh") {
        # Existing empty schema: retain its owner/permissions and skip only 001.
        $pendingDdl = @($ddl | Where-Object { $_.Path -cne "001_create_schema.sql" -or $null -eq $before.state.SchemaId })
    }
    foreach ($entry in $pendingDdl) {
        $started = [DateTime]::UtcNow
        try {
            Invoke-NonQuery $connection $entry.Sql
            $operations += [pscustomobject]@{
                Path = $entry.Path; Sha256 = $entry.Sha256; Status = "Succeeded"
                StartedAtUtc = $started.ToString("o"); CompletedAtUtc = [DateTime]::UtcNow.ToString("o")
            }
        }
        catch {
            $record = [pscustomobject]@{
                Path = $entry.Path; Sha256 = $entry.Sha256; Status = "Failed"
                StartedAtUtc = $started.ToString("o"); CompletedAtUtc = [DateTime]::UtcNow.ToString("o")
                Error = "SQL DDL failed. Partial creation is not automatically repaired."
            }
            $operations += $record
            Write-JsonEvidence "deployment-operations.json" $operations
            throw "SQL DDL failed. Partial creation is not automatically repaired."
        }
    }

    # Re-read native definitions, all output columns and input parameters now.
    # A count alone (including a five-object pre-Trace deployment) is not success.
    $after = Read-NativeCatalog $connection
    if ((Get-CatalogDecision $after) -ne "reuse") {
        throw "Immediate native catalog re-read did not confirm all six exact objects."
    }
    Write-JsonEvidence "deployment-operations.json" $operations
    Write-JsonEvidence "after-objects.json" $after.objects
    Write-JsonEvidence "after-columns.json" $after.columns
    Write-JsonEvidence "after-parameters.json" $after.parameters
    [pscustomobject]@{
        Mode = "apply"
        State = if ($decision -eq "reuse") { "REUSED" } else { "CREATED" }
        Operations = $operations
        ObjectCount = @($after.objects).Count
        OutputColumnCounts = $validatedPlan.outputColumnCounts
        NativeCatalogProvenance = "sys.objects/sys.sql_modules/sys.columns/sys.parameters; not Agent type fields"
    } | ConvertTo-Json -Depth 10
}
finally {
    try {
        if ($connection.State -ne [System.Data.ConnectionState]::Closed) { $connection.Close() }
    } finally {
        $connection.Dispose()
    }
}
