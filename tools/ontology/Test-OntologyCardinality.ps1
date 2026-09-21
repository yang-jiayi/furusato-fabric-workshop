<#
.SYNOPSIS
    Read-only validation of the Furusato ontology relationship contract: declared
    cardinality, deployable-template integrity, and - by default - the real
    cardinality recomputed from the packaged seed CSVs.

.DESCRIPTION
    The workshop declares relationship cardinality in five places that must stay
    aligned: the semantic metadata manifest, the full ontology definition
    template, the Notebook 02 / Notebook 03 embedded copies of those two files,
    and the participant workspace contract.

    A declaration on its own proves nothing, so this script derives the real
    cardinality too. There are two derivation modes, and the script always states
    which one produced a verdict:

      Declared-count mode (-FromData:$false)
        Reads expected.nodeCounts and expected.edgeCounts from the packaged
        dataset manifest. Those numbers are themselves *declared* values, so this
        mode proves only that the ontology agrees with the manifest. It cannot
        detect a manifest that disagrees with the CSVs.

      Actual-data mode (default)
        Streams the packaged seed CSVs and recomputes every node count, edge
        count and participation figure from the rows themselves, checks the
        dataset manifest against that recomputation, and only then derives
        cardinality. This is the only mode that can prove the declared
        cardinality is true of the shipped data.

    In either mode one edge is emitted per row of the binding table, therefore:

      * edge count equals the source node count  -> each source row joins once
                                                    -> many-to-one
      * edge count equals the target node count  -> each target row joins once
                                                    -> one-to-many from source
      * edge count equals both                   -> one-to-one
      * edge count equals neither                -> many-to-many

    Optionality is a separate question from multiplicity, so actual-data mode
    also recomputes participation - how many source instances emit no edge - and
    requires the declared vocabulary to match exactly: "zero-to-many from X" when
    some X has no edge, and "one-to-many from X" when every X has at least one.
    Either word is accepted only in declared-count mode, which cannot see the
    difference. "many-to-many" is reserved for the registration bridge, which
    matches neither node count.

    Beyond cardinality the script validates that the deployable template can
    actually be deployed: every relationship endpoint resolves to a real entity
    type, every contextualization key resolves to a real property, and all 104
    referenced source columns exist in the Notebook 01 output-schema contract
    that creates those tables.

    The script never writes, never calls a network service, and needs no module
    beyond PowerShell 7.

.PARAMETER WorkshopRoot
    Path of the versioned workshop folder. Defaults to workshop/v2.7.0 under the
    repository that contains this script.

.PARAMETER FromData
    Recompute node counts, edge counts and participation from the packaged seed
    CSVs. Enabled by default; use -FromData:$false for the faster declared-count
    mode.

.PARAMETER Detailed
    Print every passing check instead of the summary only.

.PARAMETER SelfTest
    Also run the built-in negative tests, which mutate in-memory copies of the
    runtime and assert that each planted defect is detected. Nothing is written.

.EXAMPLE
    pwsh ./tools/ontology/Test-OntologyCardinality.ps1

.EXAMPLE
    pwsh ./tools/ontology/Test-OntologyCardinality.ps1 -FromData:$false -Detailed

.EXAMPLE
    pwsh ./tools/ontology/Test-OntologyCardinality.ps1 -SelfTest
#>
[CmdletBinding()]
param(
    [string] $WorkshopRoot,
    [bool] $FromData = $true,
    [switch] $Detailed,
    [switch] $SelfTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $WorkshopRoot) {
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $WorkshopRoot = Join-Path $repoRoot 'workshop/v2.7.0'
}
$WorkshopRoot = (Resolve-Path -LiteralPath $WorkshopRoot).Path

$script:Passed = 0
$script:Failures = New-Object System.Collections.Generic.List[string]

function Assert-Check {
    param([string] $Label, [bool] $Condition, [string] $Detail = '')
    if ($Condition) {
        $script:Passed++
        if ($Detailed) { Write-Host "  ok   $Label" }
    }
    else {
        $message = if ($Detail) { "$Label -- $Detail" } else { $Label }
        $script:Failures.Add($message)
    }
}

function Read-JsonFile {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required file not found: $Path"
    }
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-PropertyNames {
    param($Object)
    if ($null -eq $Object) { return @() }
    return @($Object.PSObject.Properties.Name)
}

function Test-HasProperty {
    param($Object, [string] $Name)
    if ($null -eq $Object) { return $false }
    return ((Get-PropertyNames -Object $Object) -contains $Name)
}

function Get-EmbeddedJson {
    param([string] $NotebookPath, [int] $CellIndex)
    $notebook = Read-JsonFile -Path $NotebookPath
    $source = -join $notebook.cells[$CellIndex].source
    $marker = "json.loads(r'''"
    $start = $source.IndexOf($marker)
    if ($start -lt 0) { throw "No embedded JSON literal in $NotebookPath cell $CellIndex" }
    $start += $marker.Length
    $end = $source.IndexOf("''')", $start)
    if ($end -lt 0) { throw "Unterminated embedded JSON literal in $NotebookPath" }
    return ($source.Substring($start, $end - $start) | ConvertFrom-Json)
}

function Get-RelationshipPart {
    param($Template, [string] $Name)
    return @($Template.parts | Where-Object {
        $_.path -like 'RelationshipTypes/*/definition.json' -and
        (Test-HasProperty -Object $_.content -Name 'name') -and
        $_.content.name -eq $Name
    })
}

function Get-EntityTypeParts {
    param($Template)
    $map = @{}
    foreach ($part in $Template.parts) {
        if ($part.path -notlike 'EntityTypes/*') { continue }
        if ($part.path -notlike '*/definition.json') { continue }
        if ($part.path -like '*/Overviews/*') { continue }
        if (-not (Test-HasProperty -Object $part.content -Name 'id')) { continue }
        $map[[string] $part.content.id] = $part.content
    }
    return $map
}

function Read-DelimitedRows {
    <#
        Minimal streaming CSV reader. The packaged seed files are plain
        comma-separated UTF-8 with quoting only around free text, so a manual
        split is both correct and far faster than Import-Csv for the
        80,000-row donation file.
    #>
    param([string] $Path)
    $reader = [System.IO.StreamReader]::new($Path, [System.Text.UTF8Encoding]::new($false))
    try {
        $header = $reader.ReadLine()
        if ($null -eq $header) { return }
        $names = $header.Split(',')
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            if ([string]::IsNullOrEmpty($line)) { continue }
            $fields = New-Object System.Collections.Generic.List[string]
            $current = [System.Text.StringBuilder]::new()
            $inQuotes = $false
            foreach ($char in $line.ToCharArray()) {
                if ($char -eq '"') { $inQuotes = -not $inQuotes; continue }
                if ($char -eq ',' -and -not $inQuotes) {
                    [void] $fields.Add($current.ToString())
                    [void] $current.Clear()
                    continue
                }
                [void] $current.Append($char)
            }
            [void] $fields.Add($current.ToString())
            $row = @{}
            for ($index = 0; $index -lt $names.Length; $index++) {
                $row[$names[$index]] = if ($index -lt $fields.Count) { $fields[$index] } else { '' }
            }
            Write-Output $row
        }
    }
    finally {
        $reader.Dispose()
    }
}

function Measure-SeedGraph {
    param([string] $SeedRoot)

    $prefectures = @{}
    foreach ($row in Read-DelimitedRows (Join-Path $SeedRoot 'prefectures.csv')) {
        $prefectures[$row['PrefectureID']] = $true
    }
    $municipalityPrefecture = @{}
    foreach ($row in Read-DelimitedRows (Join-Path $SeedRoot 'municipalities.csv')) {
        $municipalityPrefecture[$row['MunicipalityID']] = $row['PrefectureID']
    }
    $donorPrefecture = @{}
    foreach ($row in Read-DelimitedRows (Join-Path $SeedRoot 'donors.csv')) {
        $donorPrefecture[$row['DonorID']] = $row['PrefectureID']
    }
    $categories = @{}
    foreach ($row in Read-DelimitedRows (Join-Path $SeedRoot 'categories.csv')) {
        $categories[$row['CategoryID']] = $true
    }
    $giftCategory = @{}
    $catalogMunicipalities = @{}
    foreach ($row in Read-DelimitedRows (Join-Path $SeedRoot 'gifts.csv')) {
        $giftCategory[$row['GiftID']] = $row['CategoryID']
        $catalogMunicipalities[$row['MunicipalityID']] = $true
    }
    $suppliers = @{}
    foreach ($row in Read-DelimitedRows (Join-Path $SeedRoot 'businesses.csv')) {
        $suppliers[$row['BusinessID']] = $true
    }

    $supplierGiftPairs = 0
    $suppliersWithGift = @{}
    $giftsWithSupplier = @{}
    foreach ($row in Read-DelimitedRows (Join-Path $SeedRoot 'business_gifts.csv')) {
        $supplierGiftPairs++
        $suppliersWithGift[$row['BusinessID']] = $true
        $giftsWithSupplier[$row['GiftID']] = $true
    }

    $donations = 0
    $donorsWithDonation = @{}
    $municipalitiesWithDonation = @{}
    $munCategoryPairs = @{}
    $prefCategoryPairs = @{}
    $flowPairs = @{}
    foreach ($row in Read-DelimitedRows (Join-Path $SeedRoot 'donation_orders.csv')) {
        $donations++
        $donorId = $row['DonorID']
        $municipalityId = $row['MunicipalityID']
        $giftId = $row['GiftID']
        $donorsWithDonation[$donorId] = $true
        $municipalitiesWithDonation[$municipalityId] = $true
        $categoryId = $giftCategory[$giftId]
        $recipientPrefecture = $municipalityPrefecture[$municipalityId]
        $residencePrefecture = $donorPrefecture[$donorId]
        $munCategoryPairs["$municipalityId|$categoryId"] = $true
        $prefCategoryPairs["$recipientPrefecture|$categoryId"] = $true
        $flowPairs["$residencePrefecture|$recipientPrefecture"] = $true
    }

    $nodeCounts = @{
        ot_prefecture           = $prefectures.Count
        ot_municipality         = $municipalityPrefecture.Count
        ot_donor                = $donorPrefecture.Count
        ot_gift_category        = $categories.Count
        ot_gift                 = $giftCategory.Count
        ot_supplier             = $suppliers.Count
        ot_donation             = $donations
        ot_mun_category_metric  = $munCategoryPairs.Count
        ot_pref_category_metric = $prefCategoryPairs.Count
        ot_pref_donation_flow   = $flowPairs.Count
    }
    $edgeCounts = @{
        MunicipalityInPrefecture = $municipalityPrefecture.Count
        DonorLivesInPrefecture   = $donorPrefecture.Count
        SupplierInPrefecture     = $suppliers.Count
        GiftInCategory           = $giftCategory.Count
        MunicipalityCatalogsGift = $giftCategory.Count
        SupplierProvidesGift     = $supplierGiftPairs
        DonorMadeDonation        = $donations
        DonationToMunicipality   = $donations
        DonationSelectedGift     = $donations
        MunHasCategoryMetric     = $munCategoryPairs.Count
        MunMetricForCategory     = $munCategoryPairs.Count
        PrefHasCategoryMetric    = $prefCategoryPairs.Count
        PrefMetricForCategory    = $prefCategoryPairs.Count
        ResidencePrefHasFlow     = $flowPairs.Count
        FlowToRecipientPref      = $flowPairs.Count
    }
    #: Source instances that emit no edge at all. A non-zero value makes the
    #: relationship optional on that side, which must be declared zero-to-many.
    $orphanSources = @{
        DonorMadeDonation        = $donorPrefecture.Count - $donorsWithDonation.Count
        MunHasCategoryMetric     = $municipalityPrefecture.Count - $municipalitiesWithDonation.Count
        SupplierProvidesGift     = $suppliers.Count - $suppliersWithGift.Count
        MunicipalityCatalogsGift = $municipalityPrefecture.Count - $catalogMunicipalities.Count
        PrefHasCategoryMetric    = $prefectures.Count - (@($prefCategoryPairs.Keys | ForEach-Object { $_.Split('|')[0] } | Sort-Object -Unique)).Count
        ResidencePrefHasFlow     = $prefectures.Count - (@($flowPairs.Keys | ForEach-Object { $_.Split('|')[0] } | Sort-Object -Unique)).Count
    }
    return @{
        nodeCounts    = $nodeCounts
        edgeCounts    = $edgeCounts
        orphanSources = $orphanSources
        participation = @{
            donorsWithoutDonations         = $donorPrefecture.Count - $donorsWithDonation.Count
            municipalitiesWithoutDonations = $municipalityPrefecture.Count - $municipalitiesWithDonation.Count
            suppliersWithoutGifts          = $suppliers.Count - $suppliersWithGift.Count
            giftsWithoutSuppliers          = $giftCategory.Count - $giftsWithSupplier.Count
        }
    }
}

function Get-Notebook01OutputColumns {
    <#
        Notebook 01 owns the output schema as STATIC_PROPERTY_CONTRACT plus
        RELATION_COLUMN_CONTRACT; OUTPUT_SCHEMA_CONTRACT is just their union.
        Both dictionaries are parsed and merged per table.
    #>
    param([string] $NotebookPath)
    $notebook = Read-JsonFile -Path $NotebookPath
    $source = ''
    foreach ($cell in $notebook.cells) {
        if ($cell.cell_type -ne 'code') { continue }
        $text = -join $cell.source
        if ($text.Contains('STATIC_PROPERTY_CONTRACT') -and $text.Contains('RELATION_COLUMN_CONTRACT')) {
            $source = $text
            break
        }
    }
    if (-not $source) { throw "Output schema contract not found in $NotebookPath" }

    $columns = @{}
    $currentTable = $null
    foreach ($line in ($source -split "`n")) {
        $tableMatch = [regex]::Match($line, '^\s*"(ot_[a-z_]+)"\s*:\s*\[(.*)$')
        if ($tableMatch.Success) {
            $currentTable = $tableMatch.Groups[1].Value
            if (-not $columns.ContainsKey($currentTable)) {
                $columns[$currentTable] = New-Object System.Collections.Generic.HashSet[string]
            }
            $rest = $tableMatch.Groups[2].Value
            foreach ($columnMatch in [regex]::Matches($rest, '\(\s*"([A-Za-z0-9_]+)"\s*,')) {
                [void] $columns[$currentTable].Add($columnMatch.Groups[1].Value)
            }
            if ($rest.Contains(']')) { $currentTable = $null }
            continue
        }
        if ($null -eq $currentTable) { continue }
        foreach ($columnMatch in [regex]::Matches($line, '\(\s*"([A-Za-z0-9_]+)"\s*,')) {
            [void] $columns[$currentTable].Add($columnMatch.Groups[1].Value)
        }
        if ($line -match '^\s*\]') { $currentTable = $null }
    }
    return $columns
}

function Invoke-CardinalityChecks {
    param(
        $Metadata,
        $Template,
        $Contract,
        $EmbeddedMetadata,
        $EmbeddedTemplate,
        $NodeCounts,
        $EdgeCounts,
        $OrphanSources,
        [string] $DerivationMode,
        $Notebook01Columns
    )

    $entityTable = @{
        'Prefecture'                 = 'ot_prefecture'
        'Municipality'               = 'ot_municipality'
        'Donor'                      = 'ot_donor'
        'GiftCategory'               = 'ot_gift_category'
        'Gift'                       = 'ot_gift'
        'Supplier'                   = 'ot_supplier'
        'Donation'                   = 'ot_donation'
        'MunicipalityCategoryMetric' = 'ot_mun_category_metric'
        'PrefectureCategoryMetric'   = 'ot_pref_category_metric'
        'PrefectureDonationFlow'     = 'ot_pref_donation_flow'
    }

    $relationshipNames = @(Get-PropertyNames -Object $Metadata.relationships) | Sort-Object
    Assert-Check 'metadata declares 15 relationships' ($relationshipNames.Count -eq 15) `
        "found $($relationshipNames.Count)"

    $entityTypes = Get-EntityTypeParts -Template $Template
    $propertyOwner = @{}
    foreach ($entry in $entityTypes.GetEnumerator()) {
        if (-not (Test-HasProperty -Object $entry.Value -Name 'properties')) { continue }
        foreach ($property in $entry.Value.properties) {
            $propertyOwner[[string] $property.id] = [string] $entry.Value.name
        }
    }

    $oneToManyGate = 0
    $manyToOneGate = 0
    $manyToManyGate = 0

    foreach ($name in $relationshipNames) {
        $relationship = $Metadata.relationships.$name
        $attributes = $null
        if (Test-HasProperty -Object $relationship.semanticEnrichment -Name 'customAttributes') {
            $attributes = $relationship.semanticEnrichment.customAttributes
        }

        foreach ($key in @('direction', 'cardinality', 'grain', 'sourceParticipation', 'targetParticipation')) {
            $present = (Test-HasProperty -Object $attributes -Name $key) -and
                       -not [string]::IsNullOrWhiteSpace([string] $attributes.$key)
            Assert-Check "$name declares customAttributes.$key" $present
        }
        if (-not (Test-HasProperty -Object $attributes -Name 'cardinality')) { continue }
        $declared = [string] $attributes.cardinality

        $templatePart = Get-RelationshipPart -Template $Template -Name $name
        Assert-Check "$name has exactly one template definition part" ($templatePart.Count -eq 1)
        if ($templatePart.Count -eq 1) {
            $templateCardinality = [string] $templatePart[0].content.semanticEnrichment.customAttributes.cardinality
            Assert-Check "$name template cardinality matches metadata" ($templateCardinality -ceq $declared) `
                "template='$templateCardinality' metadata='$declared'"

            $sourceId = [string] $templatePart[0].content.source.entityTypeId
            $targetId = [string] $templatePart[0].content.target.entityTypeId
            $sourceName = if ($entityTypes.ContainsKey($sourceId)) { [string] $entityTypes[$sourceId].name } else { '' }
            $targetName = if ($entityTypes.ContainsKey($targetId)) { [string] $entityTypes[$targetId].name } else { '' }
            Assert-Check "$name template source entityTypeId resolves to $($relationship.sourceEntityType)" `
                ($sourceName -ceq [string] $relationship.sourceEntityType) "id=$sourceId resolved='$sourceName'"
            Assert-Check "$name template target entityTypeId resolves to $($relationship.targetEntityType)" `
                ($targetName -ceq [string] $relationship.targetEntityType) "id=$targetId resolved='$targetName'"
        }

        $embeddedCardinality = [string] $EmbeddedMetadata.relationships.$name.semanticEnrichment.customAttributes.cardinality
        Assert-Check "$name Notebook 02 embedded cardinality matches" ($embeddedCardinality -ceq $declared) `
            "embedded='$embeddedCardinality'"

        $embeddedPart = Get-RelationshipPart -Template $EmbeddedTemplate -Name $name
        Assert-Check "$name Notebook 03 embedded definition part found" ($embeddedPart.Count -eq 1)
        if ($embeddedPart.Count -eq 1) {
            $embeddedTemplateCardinality = [string] $embeddedPart[0].content.semanticEnrichment.customAttributes.cardinality
            Assert-Check "$name Notebook 03 embedded cardinality matches" `
                ($embeddedTemplateCardinality -ceq $declared) "embedded='$embeddedTemplateCardinality'"
        }

        $contractEntry = @($Contract.ontology.relationships | Where-Object { $_.name -eq $name })
        Assert-Check "$name appears once in the participant contract" ($contractEntry.Count -eq 1)
        if ($contractEntry.Count -ne 1) { continue }
        Assert-Check "$name contract cardinality matches metadata" `
            ([string] $contractEntry[0].cardinality -ceq $declared) `
            "contract='$([string] $contractEntry[0].cardinality)'"
        Assert-Check "$name contract endpoints match metadata" `
            ($contractEntry[0].source -ceq $relationship.sourceEntityType -and
             $contractEntry[0].target -ceq $relationship.targetEntityType) `
            "contract=$($contractEntry[0].source)->$($contractEntry[0].target) metadata=$($relationship.sourceEntityType)->$($relationship.targetEntityType)"

        $sourceTable = $entityTable[$relationship.sourceEntityType]
        $targetTable = $entityTable[$relationship.targetEntityType]
        Assert-Check "$name source entity maps to an output table" ($null -ne $sourceTable) `
            $relationship.sourceEntityType
        Assert-Check "$name target entity maps to an output table" ($null -ne $targetTable) `
            $relationship.targetEntityType
        if (-not $sourceTable -or -not $targetTable) { continue }

        Assert-Check "$name has an edge count ($DerivationMode)" ($EdgeCounts.ContainsKey($name))
        if (-not $EdgeCounts.ContainsKey($name)) { continue }

        $edges = [int] $EdgeCounts[$name]
        $sourceNodes = [int] $NodeCounts[$sourceTable]
        $targetNodes = [int] $NodeCounts[$targetTable]
        Assert-Check "$name edge count is positive" ($edges -gt 0) "edges=$edges"

        if ($edges -eq $sourceNodes -and $edges -eq $targetNodes) {
            $derived = 'one-to-one'
        }
        elseif ($edges -eq $targetNodes) {
            $derived = 'one-to-many from ' + $relationship.sourceEntityType
        }
        elseif ($edges -eq $sourceNodes) {
            $derived = 'many-to-one'
        }
        else {
            $derived = 'many-to-many'
        }

        switch -Wildcard ($derived) {
            'one-to-many from *' {
                $oneToManyGate++
                # Multiplicity says the edge count follows the target; optionality
                # is a separate fact the data settles. A source instance that emits
                # no edge makes the relationship zero-to-many; when every source
                # instance emits at least one, the honest word is one-to-many.
                # Declared-count mode cannot see this, so it accepts either word.
                $orphans = if ($OrphanSources.ContainsKey($name)) { [int] $OrphanSources[$name] } else { -1 }
                if ($orphans -gt 0) {
                    $expectedPrefix = 'zero-to-many from ' + $relationship.sourceEntityType
                }
                elseif ($orphans -eq 0) {
                    $expectedPrefix = 'one-to-many from ' + $relationship.sourceEntityType
                }
                else {
                    $expectedPrefix = $null
                }
                if ($expectedPrefix) {
                    $agrees = $declared.StartsWith($expectedPrefix)
                    Assert-Check "$name optionality vocabulary matches participation" $agrees `
                        "declared='$declared' expected prefix='$expectedPrefix' orphanSources=$orphans"
                }
                else {
                    $agrees = $declared.StartsWith('one-to-many from ' + $relationship.sourceEntityType) -or
                              $declared.StartsWith('zero-to-many from ' + $relationship.sourceEntityType)
                }
            }
            'many-to-one' { $manyToOneGate++; $agrees = $declared.StartsWith('many-to-one') }
            'one-to-one' { $agrees = $declared.StartsWith('one-to-one') }
            default {
                $manyToManyGate++
                $agrees = $declared.StartsWith('zero-to-many') -or $declared.StartsWith('many-to-many')
            }
        }
        Assert-Check "$name declared cardinality matches key uniqueness ($DerivationMode)" $agrees `
            "declared='$declared' derived='$derived' edges=$edges $sourceTable=$sourceNodes $targetTable=$targetNodes"
    }

    # The three structural gates the guide and the checklist tell a participant to
    # tick after Notebook 03.
    Assert-Check 'exactly 5 one-to-many relationships (edge count = target instances)' `
        ($oneToManyGate -eq 5) "found $oneToManyGate"
    Assert-Check 'exactly 9 many-to-one relationships (edge count = source instances)' `
        ($manyToOneGate -eq 9) "found $manyToOneGate"
    Assert-Check 'exactly 1 many-to-many relationship (edge count = neither side)' `
        ($manyToManyGate -eq 1) "found $manyToManyGate"

    $contractNames = @($Contract.ontology.relationships | ForEach-Object { $_.name }) | Sort-Object
    Assert-Check 'contract declares the same 15 relationships' `
        ($null -eq (Compare-Object -ReferenceObject $relationshipNames -DifferenceObject $contractNames)) `
        "contract=$($contractNames -join ',')"

    $withCardinality = @($Contract.ontology.relationships | Where-Object {
        -not [string]::IsNullOrWhiteSpace([string] $_.cardinality) })
    Assert-Check 'all 15 contract relationships declare cardinality' ($withCardinality.Count -eq 15) `
        "found $($withCardinality.Count)"

    $templateRelParts = @($Template.parts | Where-Object { $_.path -like 'RelationshipTypes/*/definition.json' })
    Assert-Check 'template holds 15 relationship definitions' ($templateRelParts.Count -eq 15) `
        "found $($templateRelParts.Count)"
    $templateWithCardinality = @($templateRelParts | Where-Object {
        Test-HasProperty -Object $_.content.semanticEnrichment.customAttributes -Name 'cardinality' })
    Assert-Check 'all 15 template relationships declare cardinality' `
        ($templateWithCardinality.Count -eq 15) "found $($templateWithCardinality.Count)"

    $edgeNames = @($EdgeCounts.Keys) | Sort-Object
    Assert-Check "edge counts cover the same 15 relationships ($DerivationMode)" `
        ($null -eq (Compare-Object -ReferenceObject $relationshipNames -DifferenceObject $edgeNames)) `
        "counted=$($edgeNames -join ',')"

    # ------------------------------------------- deployable-template integrity
    $boundTables = New-Object System.Collections.Generic.List[string]
    $eventhouseTables = New-Object System.Collections.Generic.List[string]
    $referencedColumns = 0
    $defects = New-Object System.Collections.Generic.List[string]

    foreach ($part in $Template.parts) {
        if ($part.path -notlike '*/DataBindings/*') { continue }
        $configuration = $part.content.dataBindingConfiguration
        $tableProperties = $configuration.sourceTableProperties
        $tableName = [string] $tableProperties.sourceTableName
        $isKusto = ([string] $tableProperties.sourceType -eq 'KustoTable')
        if ($isKusto) {
            if (-not $eventhouseTables.Contains($tableName)) { [void] $eventhouseTables.Add($tableName) }
        }
        elseif (-not $boundTables.Contains($tableName)) {
            [void] $boundTables.Add($tableName)
        }
        foreach ($binding in $configuration.propertyBindings) {
            $referencedColumns++
            if ($isKusto) { continue }
            if (-not $Notebook01Columns.ContainsKey($tableName)) {
                [void] $defects.Add("$tableName is not created by Notebook 01")
                continue
            }
            if (-not $Notebook01Columns[$tableName].Contains([string] $binding.sourceColumnName)) {
                [void] $defects.Add("$tableName.$([string] $binding.sourceColumnName)")
            }
        }
    }

    $contextualizationTables = New-Object System.Collections.Generic.List[string]
    foreach ($part in $Template.parts) {
        if ($part.path -notlike '*/Contextualizations/*') { continue }
        $tableName = [string] $part.content.dataBindingTable.sourceTableName
        if (-not $contextualizationTables.Contains($tableName)) { [void] $contextualizationTables.Add($tableName) }
        foreach ($side in @('sourceKeyRefBindings', 'targetKeyRefBindings')) {
            foreach ($binding in $part.content.$side) {
                $referencedColumns++
                if (-not $Notebook01Columns.ContainsKey($tableName)) {
                    [void] $defects.Add("$tableName is not created by Notebook 01")
                    continue
                }
                if (-not $Notebook01Columns[$tableName].Contains([string] $binding.sourceColumnName)) {
                    [void] $defects.Add("$tableName.$([string] $binding.sourceColumnName)")
                }
                if (-not $propertyOwner.ContainsKey([string] $binding.targetPropertyId)) {
                    [void] $defects.Add("targetPropertyId $([string] $binding.targetPropertyId) resolves to no property")
                }
            }
        }
    }

    Assert-Check 'every referenced source column exists in the Notebook 01 output contract' `
        ($defects.Count -eq 0) ($defects -join '; ')
    Assert-Check 'the template references 104 source columns' ($referencedColumns -eq 104) `
        "found $referencedColumns"

    $declaredLakehouse = @($Template.expectedSourceTables.lakehouse) | Sort-Object
    $actualLakehouse = @(@($boundTables) + @($contextualizationTables)) | Sort-Object -Unique
    Assert-Check 'expectedSourceTables.lakehouse matches the bound and contextualization tables' `
        ($null -eq (Compare-Object -ReferenceObject $declaredLakehouse -DifferenceObject $actualLakehouse)) `
        "declared=$($declaredLakehouse -join ',') actual=$($actualLakehouse -join ',')"
    Assert-Check 'exactly 10 Lakehouse tables carry an entity data binding' `
        ($boundTables.Count -eq 10) "found $($boundTables.Count): $($boundTables -join ',')"
    $contextualizationOnly = @($contextualizationTables | Where-Object { -not $boundTables.Contains($_) })
    Assert-Check 'ot_supplier_gift is the only contextualization-only Lakehouse table' `
        ($contextualizationOnly.Count -eq 1 -and $contextualizationOnly[0] -eq 'ot_supplier_gift') `
        "found $($contextualizationOnly -join ',')"
    $declaredEventhouse = @($Template.expectedSourceTables.eventhouse) | Sort-Object
    Assert-Check 'expectedSourceTables.eventhouse matches the Kusto time-series binding' `
        ($null -eq (Compare-Object -ReferenceObject $declaredEventhouse -DifferenceObject (@($eventhouseTables) | Sort-Object))) `
        "declared=$($declaredEventhouse -join ',') actual=$($eventhouseTables -join ',')"
    Assert-Check 'the time-series binding reads the raw DonationEvents table, not the curated view' `
        ($eventhouseTables.Count -eq 1 -and $eventhouseTables[0] -eq 'DonationEvents') `
        "found $($eventhouseTables -join ',')"
}

Write-Host 'Furusato ontology cardinality validator (read-only)'
Write-Host "Workshop root: $WorkshopRoot"

$metadataPath = Join-Path $WorkshopRoot 'ontology/ontology-semantic-metadata.json'
$templatePath = Join-Path $WorkshopRoot 'ontology/ontology-full-definition-template.json'
$metadata = Read-JsonFile -Path $metadataPath
$template = Read-JsonFile -Path $templatePath
$contract = Read-JsonFile -Path (Join-Path $WorkshopRoot 'participant-workspace-contract.json')
$dataset = Read-JsonFile -Path (Join-Path $WorkshopRoot 'data/dataset-manifest.json')
$embeddedMetadata = Get-EmbeddedJson `
    -NotebookPath (Join-Path $WorkshopRoot 'notebooks/Notebook_02_Furusato_Apply_Ontology_Metadata.ipynb') `
    -CellIndex 3
$embeddedTemplate = Get-EmbeddedJson `
    -NotebookPath (Join-Path $WorkshopRoot 'notebooks/Notebook_03_Furusato_Create_Complete_Ontology.ipynb') `
    -CellIndex 3
$notebook01Columns = Get-Notebook01OutputColumns `
    -NotebookPath (Join-Path $WorkshopRoot 'notebooks/Notebook_01_Furusato_Prepare_Ontology_Data.ipynb')

$declaredNodeCounts = @{}
foreach ($name in Get-PropertyNames -Object $dataset.expected.nodeCounts) {
    $declaredNodeCounts[$name] = [int] $dataset.expected.nodeCounts.$name
}
$declaredEdgeCounts = @{}
foreach ($name in Get-PropertyNames -Object $dataset.expected.edgeCounts) {
    $declaredEdgeCounts[$name] = [int] $dataset.expected.edgeCounts.$name
}

if ($FromData) {
    Write-Host 'Derivation:    actual-data mode (recomputed from the packaged seed CSVs)'
    Write-Host ''
    $measured = Measure-SeedGraph -SeedRoot (Join-Path $WorkshopRoot 'data/seed')
    $nodeCounts = $measured.nodeCounts
    $edgeCounts = $measured.edgeCounts
    $orphanSources = $measured.orphanSources
    $derivationMode = 'actual data'

    foreach ($table in @($declaredNodeCounts.Keys | Sort-Object)) {
        Assert-Check "dataset manifest nodeCounts.$table matches the CSVs" `
            ($declaredNodeCounts[$table] -eq $nodeCounts[$table]) `
            "manifest=$($declaredNodeCounts[$table]) csv=$($nodeCounts[$table])"
    }
    foreach ($name in @($declaredEdgeCounts.Keys | Sort-Object)) {
        Assert-Check "dataset manifest edgeCounts.$name matches the CSVs" `
            ($declaredEdgeCounts[$name] -eq $edgeCounts[$name]) `
            "manifest=$($declaredEdgeCounts[$name]) csv=$($edgeCounts[$name])"
    }
    foreach ($key in @('donorsWithoutDonations', 'municipalitiesWithoutDonations', 'suppliersWithoutGifts')) {
        Assert-Check "dataset manifest expected.$key matches the CSVs" `
            ([int] $dataset.expected.$key -eq [int] $measured.participation[$key]) `
            "manifest=$([int] $dataset.expected.$key) csv=$($measured.participation[$key])"
    }
    Assert-Check 'every Gift has at least one registered Supplier in this dataset' `
        ($measured.participation['giftsWithoutSuppliers'] -eq 0) `
        "giftsWithoutSuppliers=$($measured.participation['giftsWithoutSuppliers'])"
}
else {
    Write-Host 'Derivation:    declared-count mode (dataset-manifest counts only; it cannot'
    Write-Host '               detect a manifest that disagrees with the packaged CSVs)'
    Write-Host ''
    $nodeCounts = $declaredNodeCounts
    $edgeCounts = $declaredEdgeCounts
    $orphanSources = @{
        DonorMadeDonation        = [int] $dataset.expected.donorsWithoutDonations
        MunHasCategoryMetric     = [int] $dataset.expected.municipalitiesWithoutDonations
        SupplierProvidesGift     = [int] $dataset.expected.suppliersWithoutGifts
        MunicipalityCatalogsGift = -1
        PrefHasCategoryMetric    = -1
        ResidencePrefHasFlow     = -1
    }
    $derivationMode = 'declared counts'
}

Invoke-CardinalityChecks -Metadata $metadata -Template $template -Contract $contract `
    -EmbeddedMetadata $embeddedMetadata -EmbeddedTemplate $embeddedTemplate `
    -NodeCounts $nodeCounts -EdgeCounts $edgeCounts -OrphanSources $orphanSources `
    -DerivationMode $derivationMode -Notebook01Columns $notebook01Columns

if ($SelfTest) {
    Write-Host ''
    Write-Host 'Negative tests (each planted defect must be detected)'
    $negatives = @(
        @{
            Name  = 'flipped optionality vocabulary on DonorMadeDonation'
            Apply = {
                param($state)
                $state.Metadata.relationships.DonorMadeDonation.semanticEnrichment.customAttributes.cardinality =
                    'one-to-many from Donor, exactly one Donor per Donation'
            }
        },
        @{
            # The mirror image, and the case a dead branch used to let through:
            # every Municipality catalogs a Gift, so zero-to-many overstates the
            # optionality and must be rejected just as firmly.
            Name  = 'zero-to-many claimed where participation is total (MunicipalityCatalogsGift)'
            Apply = {
                param($state)
                $state.Metadata.relationships.MunicipalityCatalogsGift.semanticEnrichment.customAttributes.cardinality =
                    'zero-to-many from Municipality, exactly one catalog Municipality per Gift'
            }
        },
        @{
            Name  = 'zero-to-many claimed where participation is total (ResidencePrefHasFlow)'
            Apply = {
                param($state)
                $state.Metadata.relationships.ResidencePrefHasFlow.semanticEnrichment.customAttributes.cardinality =
                    'zero-to-many from Prefecture, exactly one residence Prefecture per PrefectureDonationFlow row'
            }
        },
        @{
            Name  = 'template cardinality drifts from the metadata manifest'
            Apply = {
                param($state)
                $part = Get-RelationshipPart -Template $state.Template -Name 'MunicipalityInPrefecture'
                $part[0].content.semanticEnrichment.customAttributes.cardinality = 'many-to-many'
            }
        },
        @{
            Name  = 'relationship endpoint points at a missing entity type'
            Apply = {
                param($state)
                $part = Get-RelationshipPart -Template $state.Template -Name 'GiftInCategory'
                $part[0].content.target.entityTypeId = '0000000000000'
            }
        },
        @{
            Name  = 'contextualization references a column the table does not have'
            Apply = {
                param($state)
                foreach ($part in $state.Template.parts) {
                    if ($part.path -like '*/Contextualizations/*') {
                        $part.content.sourceKeyRefBindings[0].sourceColumnName = 'NoSuchColumn'
                        break
                    }
                }
            }
        },
        @{
            Name  = 'expectedSourceTables loses the contextualization-only table'
            Apply = {
                param($state)
                $state.Template.expectedSourceTables.lakehouse =
                    @($state.Template.expectedSourceTables.lakehouse | Where-Object { $_ -ne 'ot_supplier_gift' })
            }
        },
        @{
            Name  = 'time-series binding is repointed at the curated view'
            Apply = {
                param($state)
                foreach ($part in $state.Template.parts) {
                    if ($part.path -notlike '*/DataBindings/*') { continue }
                    if ([string] $part.content.dataBindingConfiguration.sourceTableProperties.sourceType -ne 'KustoTable') { continue }
                    $part.content.dataBindingConfiguration.sourceTableProperties.sourceTableName =
                        'DonationObservationSummaryForAgent'
                    break
                }
            }
        },
        @{
            Name  = 'a relationship stops declaring participation'
            Apply = {
                param($state)
                $attributes = $state.Metadata.relationships.SupplierProvidesGift.semanticEnrichment.customAttributes
                $attributes.PSObject.Properties.Remove('sourceParticipation')
            }
        }
    )

    $undetected = New-Object System.Collections.Generic.List[string]
    foreach ($negative in $negatives) {
        $state = @{
            Metadata = (Read-JsonFile -Path $metadataPath)
            Template = (Read-JsonFile -Path $templatePath)
        }
        & $negative.Apply $state

        $savedPassed = $script:Passed
        $savedFailures = $script:Failures
        $script:Passed = 0
        $script:Failures = New-Object System.Collections.Generic.List[string]
        Invoke-CardinalityChecks -Metadata $state.Metadata -Template $state.Template -Contract $contract `
            -EmbeddedMetadata $embeddedMetadata -EmbeddedTemplate $embeddedTemplate `
            -NodeCounts $nodeCounts -EdgeCounts $edgeCounts -OrphanSources $orphanSources `
            -DerivationMode $derivationMode -Notebook01Columns $notebook01Columns
        $detected = $script:Failures.Count -gt 0
        $script:Passed = $savedPassed
        $script:Failures = $savedFailures

        if ($detected) {
            $script:Passed++
            Write-Host "  ok   detected: $($negative.Name)"
        }
        else {
            [void] $undetected.Add("negative test not detected: $($negative.Name)")
        }
    }
    foreach ($failure in $undetected) { $script:Failures.Add($failure) }
}

Write-Host ''
Write-Host "Checks passed: $($script:Passed)"
if ($script:Failures.Count -gt 0) {
    Write-Host "Checks failed: $($script:Failures.Count)" -ForegroundColor Red
    foreach ($failure in $script:Failures) {
        Write-Host "  FAIL $failure" -ForegroundColor Red
    }
    exit 1
}
Write-Host 'Relationship cardinality contract satisfied.'
exit 0
