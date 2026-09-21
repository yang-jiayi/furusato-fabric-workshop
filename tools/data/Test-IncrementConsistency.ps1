#Requires -Version 7.0
<#
.SYNOPSIS
    Read-only consistency validator for the packaged Furusato workshop CSV dataset.

.DESCRIPTION
    Validates the eleven committed CSV files (eight seed files and three increment
    files) against workshop/<version>/data/dataset-manifest.json and the documented
    dataset contract. The script never writes, uploads, or mutates anything and needs
    no module beyond the PowerShell 7 base install.

    Checks performed:
      * File inventory, UTF-8 without BOM, LF line endings, trailing newline.
      * SHA-256, byte length, row count, and header for every manifest entry.
      * SHA256SUMS.txt agreement with the manifest.
      * Referential integrity: donation orders and increment events resolve to a
        known donor, municipality, gift, category, prefecture, and supplier.
      * Gift-to-Municipality catalog integrity for both static donations and events.
      * Distribution contracts: donation amounts, payment methods, prefecture and
        category coverage, and donor participation.
      * The approved August 2026 UTC observation window, PublishedAtUtc values, and
        DonatedAt ordering for the increment files.
      * Identifier formats: EventID, six-character MunicipalityID, numeric IDs.
      * The 15,000 raw / 14,900 unique / 100 duplicate layout, including the exact
        "last 100 rows of file 001 reappear as the first 100 rows of file 002" shape.

.PARAMETER DataRoot
    Path to the workshop data directory. Defaults to the v2.7.0 data folder in the
    repository that contains this script.

.PARAMETER Detailed
    Print every passing check instead of only the summary and failures.

.EXAMPLE
    pwsh ./tools/data/Test-IncrementConsistency.ps1

.EXAMPLE
    pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v2.7.0/data -Detailed
#>
[CmdletBinding()]
param(
    [string]$DataRoot,
    [switch]$Detailed
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $DataRoot) {
    $DataRoot = Join-Path $PSScriptRoot '..' '..' 'workshop' 'v2.7.0' 'data'
}
$DataRoot = (Resolve-Path -LiteralPath $DataRoot).Path

$script:Failures = [System.Collections.Generic.List[string]]::new()
$script:PassCount = 0

function Assert-Check {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][bool]$Condition,
        [string]$Detail = ''
    )
    if ($Condition) {
        $script:PassCount++
        if ($Detailed) {
            Write-Host "  PASS  $Name" -ForegroundColor DarkGreen
        }
        return
    }
    $message = if ($Detail) { "$Name -- $Detail" } else { $Name }
    $script:Failures.Add($message)
    Write-Host "  FAIL  $message" -ForegroundColor Red
}

function Get-CsvFileFacts {
    param([Parameter(Mandatory)][string]$Path)

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    $name = Split-Path -Leaf $Path

    Assert-Check -Name "$name has no UTF-8 BOM" -Condition (
        $bytes.Length -lt 3 -or -not ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
    )
    Assert-Check -Name "$name uses LF line endings" -Condition (-not $text.Contains("`r"))
    Assert-Check -Name "$name ends with a newline" -Condition $text.EndsWith("`n")

    $lines = $text -split "`n"
    $body = $lines[0..($lines.Length - 2)]

    return [pscustomobject]@{
        Header     = $body[0]
        Records    = @($text | ConvertFrom-Csv)
        RowCount   = $body.Length - 1
        Sha256     = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        ByteLength = $bytes.Length
    }
}

function ConvertTo-Utc {
    param([Parameter(Mandatory)][object]$Value)
    if ($Value -is [datetime]) {
        return ([datetime]$Value).ToUniversalTime()
    }
    $styles = [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor
    [System.Globalization.DateTimeStyles]::AssumeUniversal
    return [datetime]::Parse([string]$Value, [cultureinfo]::InvariantCulture, $styles)
}

function ConvertTo-UtcText {
    param([Parameter(Mandatory)][object]$Value)
    return (ConvertTo-Utc -Value $Value).ToString('yyyy-MM-ddTHH:mm:ssZ', [cultureinfo]::InvariantCulture)
}

function Get-Increment {
    param([hashtable]$Table, [string]$Key)
    if ($Table.ContainsKey($Key)) { return $Table[$Key] + 1 }
    return 1
}

Write-Host 'Furusato increment consistency validator (read-only)' -ForegroundColor Cyan
Write-Host "Data root: $DataRoot"

# ---------------------------------------------------------------- manifest ---
$manifestPath = Join-Path $DataRoot 'dataset-manifest.json'
Assert-Check -Name 'dataset-manifest.json exists' -Condition (Test-Path -LiteralPath $manifestPath)
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json

$seedNames = @($manifest.files | ForEach-Object { $_.file })
$incrementNames = @($manifest.incrementFiles | ForEach-Object { $_.file })
Assert-Check -Name 'manifest declares eight seed files' -Condition ($seedNames.Count -eq 8) -Detail "found $($seedNames.Count)"
Assert-Check -Name 'manifest declares three increment files' -Condition ($incrementNames.Count -eq 3) -Detail "found $($incrementNames.Count)"
Assert-Check -Name 'manifest declares no core fixture' -Condition (
    $manifest.PSObject.Properties.Name -notcontains 'coreFiles'
)

$presentSeed = @(Get-ChildItem -LiteralPath (Join-Path $DataRoot 'seed') -Filter '*.csv' | ForEach-Object { $_.Name })
$presentIncrement = @(Get-ChildItem -LiteralPath (Join-Path $DataRoot 'increment') -Filter '*.csv' | ForEach-Object { $_.Name })
Assert-Check -Name 'seed folder contains exactly the manifest files' -Condition (
    $null -eq (Compare-Object -ReferenceObject ($seedNames | Sort-Object) -DifferenceObject ($presentSeed | Sort-Object))
) -Detail ($presentSeed -join ',')
Assert-Check -Name 'increment folder contains exactly the manifest files' -Condition (
    $null -eq (Compare-Object -ReferenceObject ($incrementNames | Sort-Object) -DifferenceObject ($presentIncrement | Sort-Object))
) -Detail ($presentIncrement -join ',')
Assert-Check -Name 'no core folder remains' -Condition (-not (Test-Path -LiteralPath (Join-Path $DataRoot 'core')))

# ------------------------------------------------------------------- files ---
$files = @{}
foreach ($entry in @($manifest.files)) {
    $csv = Get-CsvFileFacts -Path (Join-Path $DataRoot 'seed' $entry.file)
    $files["seed/$($entry.file)"] = $csv
    Assert-Check -Name "seed/$($entry.file) SHA-256 matches manifest" -Condition ($csv.Sha256 -eq $entry.sha256) -Detail $csv.Sha256
    Assert-Check -Name "seed/$($entry.file) byte length matches manifest" -Condition ($csv.ByteLength -eq $entry.bytes) -Detail $csv.ByteLength
    Assert-Check -Name "seed/$($entry.file) row count matches manifest" -Condition ($csv.RowCount -eq $entry.rows) -Detail $csv.RowCount
    Assert-Check -Name "seed/$($entry.file) header matches manifest" -Condition ($csv.Header -eq $entry.header) -Detail $csv.Header
}
foreach ($entry in @($manifest.incrementFiles)) {
    $csv = Get-CsvFileFacts -Path (Join-Path $DataRoot 'increment' $entry.file)
    $files["increment/$($entry.file)"] = $csv
    Assert-Check -Name "increment/$($entry.file) SHA-256 matches manifest" -Condition ($csv.Sha256 -eq $entry.sha256) -Detail $csv.Sha256
    Assert-Check -Name "increment/$($entry.file) byte length matches manifest" -Condition ($csv.ByteLength -eq $entry.bytes) -Detail $csv.ByteLength
    Assert-Check -Name "increment/$($entry.file) row count matches manifest" -Condition ($csv.RowCount -eq $entry.rows) -Detail $csv.RowCount
    Assert-Check -Name "increment/$($entry.file) header matches manifest" -Condition ($csv.Header -eq $entry.header) -Detail $csv.Header
}
Assert-Check -Name 'eleven CSV files were validated' -Condition ($files.Count -eq 11) -Detail $files.Count

# --------------------------------------------------------------- SHA256SUMS --
$sumsPath = Join-Path $DataRoot 'SHA256SUMS.txt'
$sumLines = @(Get-Content -LiteralPath $sumsPath -Encoding utf8 | Where-Object { $_ })
Assert-Check -Name 'SHA256SUMS.txt lists eleven files' -Condition ($sumLines.Count -eq 11) -Detail $sumLines.Count
foreach ($line in $sumLines) {
    $parts = $line -split '\s+', 2
    $hash = $parts[0].ToLowerInvariant()
    $relative = $parts[1].Trim()
    $known = $files.ContainsKey($relative)
    Assert-Check -Name "SHA256SUMS.txt entry $relative is a packaged file" -Condition $known
    if ($known) {
        Assert-Check -Name "SHA256SUMS.txt hash matches $relative" -Condition ($files[$relative].Sha256 -eq $hash)
    }
}

# ------------------------------------------------------------- seed indexes --
$prefectures = $files['seed/prefectures.csv'].Records
$municipalities = $files['seed/municipalities.csv'].Records
$donors = $files['seed/donors.csv'].Records
$categories = $files['seed/categories.csv'].Records
$gifts = $files['seed/gifts.csv'].Records
$businesses = $files['seed/businesses.csv'].Records
$businessGifts = $files['seed/business_gifts.csv'].Records
$orders = $files['seed/donation_orders.csv'].Records

$prefectureIds = [System.Collections.Generic.HashSet[string]]::new()
foreach ($row in $prefectures) { [void]$prefectureIds.Add($row.PrefectureID) }
$municipalityPrefecture = @{}
foreach ($row in $municipalities) { $municipalityPrefecture[$row.MunicipalityID] = $row.PrefectureID }
$donorIds = [System.Collections.Generic.HashSet[string]]::new()
foreach ($row in $donors) { [void]$donorIds.Add($row.DonorID) }
$categoryIds = [System.Collections.Generic.HashSet[string]]::new()
foreach ($row in $categories) { [void]$categoryIds.Add($row.CategoryID) }
$giftMunicipality = @{}
$giftCategory = @{}
foreach ($row in $gifts) {
    $giftMunicipality[$row.GiftID] = $row.MunicipalityID
    $giftCategory[$row.GiftID] = $row.CategoryID
}
$businessIds = [System.Collections.Generic.HashSet[string]]::new()
foreach ($row in $businesses) { [void]$businessIds.Add($row.BusinessID) }

Assert-Check -Name 'prefectures.csv has 47 unique IDs' -Condition ($prefectureIds.Count -eq 47) -Detail $prefectureIds.Count
Assert-Check -Name 'municipalities.csv has 1741 unique IDs' -Condition ($municipalityPrefecture.Count -eq 1741) -Detail $municipalityPrefecture.Count
Assert-Check -Name 'donors.csv has 12000 unique IDs' -Condition ($donorIds.Count -eq 12000) -Detail $donorIds.Count
Assert-Check -Name 'categories.csv has 30 unique IDs' -Condition ($categoryIds.Count -eq 30) -Detail $categoryIds.Count
Assert-Check -Name 'gifts.csv has 6000 unique IDs' -Condition ($giftMunicipality.Count -eq 6000) -Detail $giftMunicipality.Count
Assert-Check -Name 'businesses.csv has 2500 unique IDs' -Condition ($businessIds.Count -eq 2500) -Detail $businessIds.Count

$badMunicipalityPrefecture = @($municipalities | Where-Object { -not $prefectureIds.Contains($_.PrefectureID) }).Count
Assert-Check -Name 'every municipality resolves to a prefecture' -Condition ($badMunicipalityPrefecture -eq 0) -Detail $badMunicipalityPrefecture
$badDonorPrefecture = @($donors | Where-Object { -not $prefectureIds.Contains($_.PrefectureID) }).Count
Assert-Check -Name 'every donor resolves to a residence prefecture' -Condition ($badDonorPrefecture -eq 0) -Detail $badDonorPrefecture
$badBusinessPrefecture = @($businesses | Where-Object { -not $prefectureIds.Contains($_.PrefectureID) }).Count
Assert-Check -Name 'every supplier resolves to a prefecture' -Condition ($badBusinessPrefecture -eq 0) -Detail $badBusinessPrefecture
$badGiftCategory = @($gifts | Where-Object { -not $categoryIds.Contains($_.CategoryID) }).Count
Assert-Check -Name 'every gift resolves to a category' -Condition ($badGiftCategory -eq 0) -Detail $badGiftCategory
$badGiftMunicipality = @($gifts | Where-Object { -not $municipalityPrefecture.ContainsKey($_.MunicipalityID) }).Count
Assert-Check -Name 'every gift resolves to a cataloging municipality' -Condition ($badGiftMunicipality -eq 0) -Detail $badGiftMunicipality
$badBridge = @($businessGifts | Where-Object {
    (-not $businessIds.Contains($_.BusinessID)) -or (-not $giftMunicipality.ContainsKey($_.GiftID))
    }).Count
Assert-Check -Name 'every supplier-gift bridge row resolves on both sides' -Condition ($badBridge -eq 0) -Detail $badBridge

# ------------------------------------------------- gift catalog wording -------
# Three Shizuoka fruit rows were renamed in v2.7.0 because 佐藤錦 is a Yamagata
# cherry cultivar. The old name must never come back, and the rows this release
# authors must keep GiftNameEn in plain ASCII. A file-wide ASCII rule is not
# possible: 4,005 packaged rows predate this release with a Japanese unit token
# in GiftNameEn, so those rows are bounded by a non-regression count instead.
$bannedGiftName = '静岡県産 さくらんぼ 佐藤錦'
$bannedGiftHits = @($gifts | Where-Object { $_.GiftName -like "*$bannedGiftName*" }).Count
Assert-Check -Name 'no gift is named 静岡県産 さくらんぼ 佐藤錦' -Condition ($bannedGiftHits -eq 0) -Detail $bannedGiftHits
$shizuokaSatoNishiki = @($gifts | Where-Object {
    $_.GiftName -like '*佐藤錦*' -and $_.GiftName -like '*静岡*' }).Count
Assert-Check -Name 'no 佐藤錦 gift is attributed to Shizuoka' -Condition ($shizuokaSatoNishiki -eq 0) -Detail $shizuokaSatoNishiki

$authoredGifts = @{
    '3001339' = @{ GiftName = '静岡県産 だいだい 3kg'; CategoryID = '4'; MunicipalityID = '222054'; Notes = '果物 / 3kg'; GiftNameEn = 'Shizuoka daidai citrus, 3 kg' }
    '3002512' = @{ GiftName = '静岡県産 温室メロン 1玉'; CategoryID = '4'; MunicipalityID = '222097'; Notes = '果物 / 1玉'; GiftNameEn = 'Shizuoka greenhouse melon, 1 fruit' }
    '3004059' = @{ GiftName = '静岡県産 ニューサマーオレンジ 3kg'; CategoryID = '4'; MunicipalityID = '223042'; Notes = '果物 / 3kg'; GiftNameEn = 'Shizuoka New Summer oranges, 3 kg' }
}
$giftRowById = @{}
foreach ($row in $gifts) { $giftRowById[$row.GiftID] = $row }
foreach ($giftId in ($authoredGifts.Keys | Sort-Object)) {
    $expected = $authoredGifts[$giftId]
    $row = $giftRowById[$giftId]
    Assert-Check -Name "gift $giftId is present" -Condition ($null -ne $row)
    if ($null -eq $row) { continue }
    foreach ($field in @('GiftName', 'CategoryID', 'MunicipalityID', 'Notes', 'GiftNameEn')) {
        Assert-Check -Name "gift $giftId $field matches the release contract" `
            -Condition ($row.$field -ceq $expected[$field]) -Detail $row.$field
    }
    $asciiOnly = -not ($row.GiftNameEn.ToCharArray() | Where-Object { [int]$_ -gt 127 })
    Assert-Check -Name "gift $giftId GiftNameEn is plain ASCII" -Condition $asciiOnly -Detail $row.GiftNameEn
    Assert-Check -Name "gift $giftId GiftNameEn carries no Japanese quantity glyph" `
        -Condition (-not $row.GiftNameEn.Contains([char]0x7389)) -Detail $row.GiftNameEn
    $unit = ($row.GiftName -split ' ')[-1]
    Assert-Check -Name "gift $giftId Notes unit matches its Japanese name" `
        -Condition ($row.Notes -ceq "果物 / $unit") -Detail $row.Notes
}

$mixedLanguageEn = @($gifts | Where-Object {
    $_.GiftNameEn.ToCharArray() | Where-Object { [int]$_ -gt 127 } }).Count
Assert-Check -Name 'GiftNameEn mixed-language rows do not exceed the packaged baseline' `
    -Condition ($mixedLanguageEn -le 4005) -Detail $mixedLanguageEn
$tamaEn = @($gifts | Where-Object { $_.GiftNameEn.Contains([char]0x7389) }).Count
Assert-Check -Name 'GiftNameEn rows carrying 玉 do not exceed the packaged baseline' `
    -Condition ($tamaEn -le 45) -Detail $tamaEn

# ------------------------------------------------------- static donations ----
$orderDonationIds = [System.Collections.Generic.HashSet[string]]::new()
$orderAmountTotal = [int64]0
$orderFkFailures = 0
$orderGiftMunicipalityFailures = 0
$orderPaymentMethods = @{}
$orderDonorParticipation = [System.Collections.Generic.HashSet[string]]::new()
$orderRecipientMunicipalities = [System.Collections.Generic.HashSet[string]]::new()
foreach ($row in $orders) {
    [void]$orderDonationIds.Add($row.DonationID)
    $orderAmountTotal += [int64]$row.DonationAmountYen
    if ((-not $donorIds.Contains($row.DonorID)) -or
        (-not $municipalityPrefecture.ContainsKey($row.MunicipalityID)) -or
        (-not $giftMunicipality.ContainsKey($row.GiftID))) {
        $orderFkFailures++
    }
    elseif ($giftMunicipality[$row.GiftID] -ne $row.MunicipalityID) {
        $orderGiftMunicipalityFailures++
    }
    $orderPaymentMethods[$row.PaymentMethod] = Get-Increment -Table $orderPaymentMethods -Key $row.PaymentMethod
    [void]$orderDonorParticipation.Add($row.DonorID)
    [void]$orderRecipientMunicipalities.Add($row.MunicipalityID)
}
Assert-Check -Name 'donation_orders.csv DonationID values are unique' -Condition ($orderDonationIds.Count -eq $orders.Count) -Detail $orderDonationIds.Count
Assert-Check -Name 'donation_orders.csv foreign keys all resolve' -Condition ($orderFkFailures -eq 0) -Detail $orderFkFailures
Assert-Check -Name 'donation_orders.csv gift always belongs to the recipient municipality' -Condition ($orderGiftMunicipalityFailures -eq 0) -Detail $orderGiftMunicipalityFailures
Assert-Check -Name 'donation_orders.csv total matches the manifest' -Condition ($orderAmountTotal -eq [int64]$manifest.expected.totalDonationAmountYen) -Detail $orderAmountTotal
$donorsWithoutDonations = $donorIds.Count - $orderDonorParticipation.Count
Assert-Check -Name 'donors without donations matches the manifest' -Condition (
    $donorsWithoutDonations -eq [int]$manifest.expected.donorsWithoutDonations
) -Detail $donorsWithoutDonations
$municipalitiesWithoutDonations = $municipalityPrefecture.Count - $orderRecipientMunicipalities.Count
Assert-Check -Name 'municipalities without donations matches the manifest' -Condition (
    $municipalitiesWithoutDonations -eq [int]$manifest.expected.municipalitiesWithoutDonations
) -Detail $municipalitiesWithoutDonations
Assert-Check -Name 'static payment methods are a small controlled set' -Condition (
    $orderPaymentMethods.Count -ge 2 -and $orderPaymentMethods.Count -le 8
) -Detail ($orderPaymentMethods.Keys -join ',')

# ---------------------------------------------------------- increment rows ---
$eventIdPattern = [regex]'^EVT-FRS-[0-9]{6}$'
$municipalityIdPattern = [regex]'^[0-9]{6}$'
$timestampPattern = [regex]'^2026-(08|09)-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'
$windowStart = ConvertTo-Utc -Value $manifest.expectedIncrement.observationWindowUtc.from
$windowEnd = ConvertTo-Utc -Value $manifest.expectedIncrement.observationWindowUtc.to

$allEvents = [System.Collections.Generic.List[object]]::new()
$perFileRows = @{}
foreach ($name in $incrementNames) {
    $records = @($files["increment/$name"].Records)
    $perFileRows[$name] = $records
    foreach ($row in $records) { $allEvents.Add($row) }

    $published = @($records | ForEach-Object { $_.PublishedAtUtc } | Sort-Object -Unique)
    Assert-Check -Name "$name uses one PublishedAtUtc value" -Condition ($published.Count -eq 1) -Detail ($published -join ',')
    Assert-Check -Name "$name PublishedAtUtc is in the packaged range" -Condition (
        $timestampPattern.IsMatch($published[0])
    ) -Detail $published[0]
    $sourceFiles = @($records | ForEach-Object { $_.SourceFile } | Sort-Object -Unique)
    Assert-Check -Name "$name SourceFile always names itself" -Condition (
        $sourceFiles.Count -eq 1 -and $sourceFiles[0] -eq $name
    ) -Detail ($sourceFiles -join ',')
    $runIds = @($records | ForEach-Object { $_.WorkshopRunId } | Sort-Object -Unique)
    Assert-Check -Name "$name uses one WorkshopRunId" -Condition ($runIds.Count -eq 1) -Detail ($runIds -join ',')
    $donatedAt = @($records | ForEach-Object { $_.DonatedAt })
    $sorted = @($donatedAt | Sort-Object)
    Assert-Check -Name "$name rows are ordered by DonatedAt" -Condition (
        $null -eq (Compare-Object -ReferenceObject $donatedAt -DifferenceObject $sorted -SyncWindow 0)
    )
}

$eventCounts = @{}
$eventAmountTotal = [int64]0
$incrementFkFailures = 0
$incrementGiftMunicipalityFailures = 0
$badEventIds = 0
$badMunicipalityFormat = 0
$badNumericIds = 0
$outsideWindow = 0
$incrementPaymentMethods = @{}
$incrementAmounts = @{}
$incrementPrefectures = [System.Collections.Generic.HashSet[string]]::new()
$incrementCategories = [System.Collections.Generic.HashSet[string]]::new()
$incrementDonors = [System.Collections.Generic.HashSet[string]]::new()
$rowsPerUtcDate = @{}
$countPerMunicipality = @{}
$amountPerMunicipality = @{}
foreach ($row in $allEvents) {
    $eventCounts[$row.EventID] = Get-Increment -Table $eventCounts -Key $row.EventID
    $eventAmountTotal += [int64]$row.DonationAmountYen
    $utcDate = $row.DonatedAt.Substring(0, 10)
    $rowsPerUtcDate[$utcDate] = Get-Increment -Table $rowsPerUtcDate -Key $utcDate
    $countPerMunicipality[$row.MunicipalityID] = Get-Increment -Table $countPerMunicipality -Key $row.MunicipalityID
    $priorAmount = if ($amountPerMunicipality.ContainsKey($row.MunicipalityID)) {
        $amountPerMunicipality[$row.MunicipalityID]
    }
    else { [int64]0 }
    $amountPerMunicipality[$row.MunicipalityID] = $priorAmount + [int64]$row.DonationAmountYen
    if (-not $eventIdPattern.IsMatch($row.EventID)) { $badEventIds++ }
    if (-not $municipalityIdPattern.IsMatch($row.MunicipalityID)) { $badMunicipalityFormat++ }
    foreach ($numeric in @($row.DonationID, $row.DonorID, $row.GiftID, $row.DonationAmountYen)) {
        if ($numeric -notmatch '^[0-9]+$') { $badNumericIds++ }
    }
    if ((-not $donorIds.Contains($row.DonorID)) -or
        (-not $municipalityPrefecture.ContainsKey($row.MunicipalityID)) -or
        (-not $giftMunicipality.ContainsKey($row.GiftID))) {
        $incrementFkFailures++
    }
    else {
        if ($giftMunicipality[$row.GiftID] -ne $row.MunicipalityID) { $incrementGiftMunicipalityFailures++ }
        [void]$incrementPrefectures.Add($municipalityPrefecture[$row.MunicipalityID])
        [void]$incrementCategories.Add($giftCategory[$row.GiftID])
    }
    [void]$incrementDonors.Add($row.DonorID)
    $incrementPaymentMethods[$row.PaymentMethod] = Get-Increment -Table $incrementPaymentMethods -Key $row.PaymentMethod
    $incrementAmounts[$row.DonationAmountYen] = Get-Increment -Table $incrementAmounts -Key $row.DonationAmountYen

    $donated = ConvertTo-Utc -Value $row.DonatedAt
    if ($donated -lt $windowStart -or $donated -gt $windowEnd) { $outsideWindow++ }
}

$expected = $manifest.expectedIncrement
Assert-Check -Name 'increment raw row count matches the manifest' -Condition ($allEvents.Count -eq [int]$expected.rawRows) -Detail $allEvents.Count
Assert-Check -Name 'increment unique EventID count matches the manifest' -Condition ($eventCounts.Count -eq [int]$expected.uniqueEventIds) -Detail $eventCounts.Count
$duplicateIds = @($eventCounts.GetEnumerator() | Where-Object { $_.Value -gt 1 })
Assert-Check -Name 'increment duplicate EventID count matches the manifest' -Condition (
    $duplicateIds.Count -eq [int]$expected.duplicateEventIds
) -Detail $duplicateIds.Count
$maxMultiplicity = if ($duplicateIds.Count -gt 0) {
    ($duplicateIds | ForEach-Object { $_.Value } | Measure-Object -Maximum).Maximum
}
else { 1 }
Assert-Check -Name 'increment duplicate multiplicity matches the manifest' -Condition (
    $maxMultiplicity -eq [int]$expected.duplicateMultiplicity
) -Detail $maxMultiplicity
Assert-Check -Name 'increment raw amount matches the manifest' -Condition ($eventAmountTotal -eq [int64]$expected.rawAmountYen) -Detail $eventAmountTotal

$seen = [System.Collections.Generic.HashSet[string]]::new()
$dedupTotal = [int64]0
foreach ($row in $allEvents) {
    if (-not $seen.Add($row.EventID)) { continue }
    $dedupTotal += [int64]$row.DonationAmountYen
}
Assert-Check -Name 'deduplicated amount matches the manifest' -Condition ($dedupTotal -eq [int64]$expected.deduplicatedAmountYen) -Detail $dedupTotal
Assert-Check -Name 'manifest declares no rule-threshold contract' -Condition (
    $expected.PSObject.Properties.Name -notcontains 'deduplicatedAboveRuleThreshold'
)

$firstFile = $perFileRows[$incrementNames[0]]
$secondFile = $perFileRows[$incrementNames[1]]
Assert-Check -Name 'first increment file row count matches the manifest' -Condition (
    $firstFile.Count -eq [int]$expected.firstFileRows
) -Detail $firstFile.Count
$firstFileTotal = [int64]0
foreach ($row in $firstFile) { $firstFileTotal += [int64]$row.DonationAmountYen }
Assert-Check -Name 'first increment file amount matches the manifest' -Condition (
    $firstFileTotal -eq [int64]$expected.firstFileAmountYen
) -Detail $firstFileTotal

$tail = @($firstFile[($firstFile.Count - 100)..($firstFile.Count - 1)] | ForEach-Object { $_.EventID })
$head = @($secondFile[0..99] | ForEach-Object { $_.EventID })
Assert-Check -Name 'the last 100 rows of file 001 reappear as the first 100 rows of file 002' -Condition (
    $null -eq (Compare-Object -ReferenceObject $tail -DifferenceObject $head -SyncWindow 0)
)
$businessFieldDrift = 0
$firstById = @{}
foreach ($row in $firstFile) { $firstById[$row.EventID] = $row }
foreach ($row in $secondFile[0..99]) {
    $origin = $firstById[$row.EventID]
    foreach ($field in @('DonationID', 'DonorID', 'MunicipalityID', 'GiftID', 'DonationAmountYen', 'DonatedAt', 'PaymentMethod')) {
        if ($origin.$field -ne $row.$field) { $businessFieldDrift++ }
    }
    foreach ($field in @('WorkshopRunId', 'SourceFile', 'PublishedAtUtc')) {
        if ($origin.$field -eq $row.$field) { $businessFieldDrift++ }
    }
}
Assert-Check -Name 'duplicate rows repeat business values and differ only in run metadata' -Condition (
    $businessFieldDrift -eq 0
) -Detail $businessFieldDrift

Assert-Check -Name 'increment foreign keys all resolve' -Condition ($incrementFkFailures -eq 0) -Detail $incrementFkFailures
Assert-Check -Name 'increment gift always belongs to the recipient municipality' -Condition (
    $incrementGiftMunicipalityFailures -eq 0
) -Detail $incrementGiftMunicipalityFailures
Assert-Check -Name 'every EventID uses the EVT-FRS-###### format' -Condition ($badEventIds -eq 0) -Detail $badEventIds
Assert-Check -Name 'every MunicipalityID keeps six characters' -Condition ($badMunicipalityFormat -eq 0) -Detail $badMunicipalityFormat
Assert-Check -Name 'numeric identifier columns contain digits only' -Condition ($badNumericIds -eq 0) -Detail $badNumericIds
Assert-Check -Name 'every DonatedAt falls inside the approved August 2026 window' -Condition ($outsideWindow -eq 0) -Detail $outsideWindow

# ------------------------------------------------ daily distribution --------
$hasDailyContract = $expected.PSObject.Properties.Name -contains 'dailyDistributionUtc'
Assert-Check -Name 'manifest declares the daily distribution contract' -Condition $hasDailyContract
if ($hasDailyContract) {
    $daily = $expected.dailyDistributionUtc
    $observedDates = @($rowsPerUtcDate.Keys | Sort-Object)
    $firstDate = ConvertTo-Utc -Value $daily.firstDate
    $lastDate = ConvertTo-Utc -Value $daily.lastDate
    $expectedDates = @(
        0..([int]($lastDate - $firstDate).TotalDays) | ForEach-Object {
            $firstDate.AddDays($_).ToString('yyyy-MM-dd', [cultureinfo]::InvariantCulture)
        }
    )

    Assert-Check -Name 'increment covers exactly the declared calendar-day count' -Condition (
        $observedDates.Count -eq [int]$daily.calendarDays
    ) -Detail "$($observedDates.Count) of $($daily.calendarDays)"
    Assert-Check -Name 'declared calendar range spans exactly 31 days' -Condition (
        $expectedDates.Count -eq 31 -and [int]$daily.calendarDays -eq 31
    ) -Detail $expectedDates.Count
    Assert-Check -Name 'increment covers every UTC date from firstDate through lastDate with no gap or extra' -Condition (
        $null -eq (Compare-Object -ReferenceObject $expectedDates -DifferenceObject $observedDates)
    ) -Detail (($observedDates | Select-Object -First 3) -join ',')
    Assert-Check -Name 'increment first UTC date matches the manifest' -Condition (
        $observedDates[0] -eq $firstDate.ToString('yyyy-MM-dd', [cultureinfo]::InvariantCulture)
    ) -Detail $observedDates[0]
    Assert-Check -Name 'increment last UTC date matches the manifest' -Condition (
        $observedDates[-1] -eq $lastDate.ToString('yyyy-MM-dd', [cultureinfo]::InvariantCulture)
    ) -Detail $observedDates[-1]

    $dailyCounts = @($rowsPerUtcDate.Values)
    $minDaily = ($dailyCounts | Measure-Object -Minimum).Minimum
    $maxDaily = ($dailyCounts | Measure-Object -Maximum).Maximum
    Assert-Check -Name 'minimum daily raw row count matches the manifest' -Condition (
        $minDaily -eq [int]$daily.minRowsPerDay
    ) -Detail $minDaily
    Assert-Check -Name 'maximum daily raw row count matches the manifest' -Condition (
        $maxDaily -eq [int]$daily.maxRowsPerDay
    ) -Detail $maxDaily
    $outOfBounds = @(
        $rowsPerUtcDate.GetEnumerator() | Where-Object {
            $_.Value -lt [int]$daily.minRowsPerDay -or $_.Value -gt [int]$daily.maxRowsPerDay
        } | ForEach-Object { "$($_.Key)=$($_.Value)" }
    )
    Assert-Check -Name 'every UTC date stays within the declared daily bounds' -Condition (
        $outOfBounds.Count -eq 0
    ) -Detail ($outOfBounds -join ',')
    Assert-Check -Name 'daily counts sum to the raw row count' -Condition (
        (($dailyCounts | Measure-Object -Sum).Sum) -eq [int]$expected.rawRows
    ) -Detail (($dailyCounts | Measure-Object -Sum).Sum)
    Assert-Check -Name 'manifest asserts a contiguous in-bounds daily distribution' -Condition (
        $daily.contiguous -eq $true -and $daily.everyDayWithinBounds -eq $true
    )
}

# --------------------------------------- curated-view leader oracle ---------
# Aggregated the way DonationObservationSummaryForAgent aggregates the raw
# DonationEvents table: every increment row, before any deduplication.
$hasLeaderContract = $expected.PSObject.Properties.Name -contains 'curatedViewLeader'
Assert-Check -Name 'manifest declares the curated-view leader oracle' -Condition $hasLeaderContract
if ($hasLeaderContract) {
    $leader = $expected.curatedViewLeader
    $rankedByCount = @(
        $countPerMunicipality.GetEnumerator() |
        Sort-Object -Property @{Expression = { $_.Value }; Descending = $true },
        @{Expression = { $_.Key }; Descending = $false }
    )
    $rankedByAmount = @(
        $amountPerMunicipality.GetEnumerator() |
        Sort-Object -Property @{Expression = { $_.Value }; Descending = $true },
        @{Expression = { $_.Key }; Descending = $false }
    )
    $topByCount = $rankedByCount[0]
    $topByAmount = $rankedByAmount[0]
    $secondByCount = $rankedByCount[1]

    Assert-Check -Name 'curated-view leader by observation count matches the manifest' -Condition (
        $topByCount.Key -eq $leader.municipalityId
    ) -Detail $topByCount.Key
    Assert-Check -Name 'curated-view leader observation count matches the manifest' -Condition (
        $topByCount.Value -eq [int]$leader.observationCount
    ) -Detail $topByCount.Value
    Assert-Check -Name 'curated-view leader by observed amount matches the manifest' -Condition (
        $topByAmount.Key -eq $leader.municipalityId
    ) -Detail $topByAmount.Key
    Assert-Check -Name 'curated-view leader observed amount matches the manifest' -Condition (
        $amountPerMunicipality[$leader.municipalityId] -eq [int64]$leader.observedAmountYen
    ) -Detail $amountPerMunicipality[$leader.municipalityId]
    Assert-Check -Name 'the same municipality leads by count and by amount' -Condition (
        $topByCount.Key -eq $topByAmount.Key -and $leader.sameLeaderByCountAndAmount -eq $true
    ) -Detail "$($topByCount.Key) vs $($topByAmount.Key)"
    Assert-Check -Name 'curated-view leader is strictly ahead of the runner-up on both metrics' -Condition (
        $topByCount.Value -gt $secondByCount.Value -and
        $amountPerMunicipality[$topByCount.Key] -gt $amountPerMunicipality[$secondByCount.Key] -and
        $leader.strictlyAheadOfRunnerUp -eq $true
    ) -Detail "$($topByCount.Value) vs $($secondByCount.Value)"
    Assert-Check -Name 'curated-view runner-up matches the manifest' -Condition (
        $secondByCount.Key -eq $leader.runnerUpMunicipalityId -and
        $secondByCount.Value -eq [int]$leader.runnerUpObservationCount -and
        $amountPerMunicipality[$secondByCount.Key] -eq [int64]$leader.runnerUpObservedAmountYen
    ) -Detail "$($secondByCount.Key)=$($secondByCount.Value)"
    Assert-Check -Name 'curated-view leader resolves to a seed municipality' -Condition (
        $municipalityPrefecture.ContainsKey($leader.municipalityId)
    ) -Detail $leader.municipalityId
    Assert-Check -Name 'curated-view leader aggregates cover every raw increment row' -Condition (
        (($countPerMunicipality.Values | Measure-Object -Sum).Sum) -eq [int]$expected.rawRows -and
        (($amountPerMunicipality.Values | Measure-Object -Sum).Sum) -eq [int64]$expected.rawAmountYen
    ) -Detail (($countPerMunicipality.Values | Measure-Object -Sum).Sum)
}

$publishedValues = @($allEvents | ForEach-Object { $_.PublishedAtUtc } | Sort-Object -Unique)
$manifestPublished = @($expected.publishedAtUtc | ForEach-Object { ConvertTo-UtcText -Value $_ } | Sort-Object)
Assert-Check -Name 'increment PublishedAtUtc values match the manifest' -Condition (
    $null -eq (Compare-Object -ReferenceObject $manifestPublished -DifferenceObject $publishedValues)
) -Detail ($publishedValues -join ',')

Assert-Check -Name 'increment payment methods reuse the static controlled set' -Condition (
    @($incrementPaymentMethods.Keys | Where-Object { -not $orderPaymentMethods.ContainsKey($_) }).Count -eq 0
) -Detail ($incrementPaymentMethods.Keys -join ',')
Assert-Check -Name 'increment amounts use rounded yen steps' -Condition (
    @($incrementAmounts.Keys | Where-Object { ([int64]$_) -le 0 -or ([int64]$_) % 100 -ne 0 }).Count -eq 0
) -Detail $incrementAmounts.Count
Assert-Check -Name 'increment amount distribution spans at least ten distinct values' -Condition (
    $incrementAmounts.Count -ge 10
) -Detail $incrementAmounts.Count
Assert-Check -Name 'increment events cover every prefecture' -Condition (
    $incrementPrefectures.Count -eq $prefectureIds.Count
) -Detail $incrementPrefectures.Count
Assert-Check -Name 'increment gift categories are all known categories' -Condition (
    @($incrementCategories | Where-Object { -not $categoryIds.Contains($_) }).Count -eq 0
) -Detail ($incrementCategories.Count)
Assert-Check -Name 'increment events cover at least 90 percent of gift categories' -Condition (
    $incrementCategories.Count -ge [math]::Ceiling($categoryIds.Count * 0.9)
) -Detail "$($incrementCategories.Count) of $($categoryIds.Count)"
Assert-Check -Name 'increment donors are a strict subset of the seed donors' -Condition (
    @($incrementDonors | Where-Object { -not $donorIds.Contains($_) }).Count -eq 0 -and
    $incrementDonors.Count -le $donorIds.Count
) -Detail $incrementDonors.Count

# ----------------------------------------------------------------- summary ---
Write-Host ''
Write-Host "Checks passed: $script:PassCount" -ForegroundColor Green
if ($script:Failures.Count -gt 0) {
    Write-Host "Checks failed: $($script:Failures.Count)" -ForegroundColor Red
    foreach ($failure in $script:Failures) {
        Write-Host "  - $failure" -ForegroundColor Red
    }
    exit 1
}
Write-Host 'Dataset consistency contract satisfied.' -ForegroundColor Green
exit 0
