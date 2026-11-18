param(
    [string]$Source = (Join-Path (Split-Path -Parent $PSScriptRoot) "data\normalized_bugs.jsonl"),
    [string]$RemoteRoot = "viking://resources/ziniao-online-bugs-governed",
    [string]$CurrentViewSnapshot = (Join-Path (Split-Path -Parent $PSScriptRoot) "data\feishu_raw\view_Khmxw2UDR_normalized.json"),
    [string]$HistoricalViewSnapshot = (Join-Path (Split-Path -Parent $PSScriptRoot) "data\feishu_raw\view_ZZdtquUvR_normalized.json")
)

$ErrorActionPreference = "Stop"
$baseUrl = "http://10.96.0.8:1933"
$endpoint = "$baseUrl/mcp"
$token = $env:OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY

if (-not $token) { throw "OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY is not configured." }
if (-not (Test-Path -LiteralPath $Source)) { throw "Source file not found: $Source" }

function Invoke-OpenVikingTool {
    param([string]$Name, [hashtable]$Arguments)

    $request = @{
        jsonrpc = "2.0"
        id = [guid]::NewGuid().ToString()
        method = "tools/call"
        params = @{ name = $Name; arguments = $Arguments }
    } | ConvertTo-Json -Depth 30 -Compress

    $response = Invoke-WebRequest -UseBasicParsing -Uri $endpoint -Method Post -Headers @{
        Authorization = "Bearer $token"
        Accept = "application/json, text/event-stream"
    } -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($request))

    $dataLine = $response.Content -split "`r?`n" | Where-Object { $_ -like "data: *" } | Select-Object -Last 1
    if (-not $dataLine) { throw "No JSON-RPC data returned by '$Name'." }
    $payload = $dataLine.Substring(6) | ConvertFrom-Json
    if ($payload.error) { throw $payload.error.message }
    if ($payload.result.isError) {
        throw (($payload.result.content | ForEach-Object text) -join "`n")
    }
    return $payload.result
}

function Read-OpenVikingText {
    param([string[]]$Uris)
    $result = Invoke-OpenVikingTool -Name "read" -Arguments @{ uris = $Uris }
    return (($result.content | Where-Object type -eq "text" | ForEach-Object text) -join "`n")
}

function Convert-FieldToJson {
    param($Value)
    return (ConvertTo-Json -InputObject $Value -Depth 30 -Compress)
}

$local = @(Get-Content -LiteralPath $Source -Encoding UTF8 | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
$localById = @{}
foreach ($record in $local) { $localById[[string]$record.id] = $record }

$relativeRoot = $RemoteRoot.Substring("viking://resources/".Length)
$manifestResponse = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/webdav/resources/$relativeRoot/manifest.json" -Headers @{
    Authorization = "Bearer $token"
}
$manifest = $manifestResponse.Content | ConvertFrom-Json
$remoteResponse = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/webdav/resources/$relativeRoot/normalized/normalized_bugs.jsonl" -Headers @{
    Authorization = "Bearer $token"
}
$remoteRaw = $remoteResponse.Content
$localRaw = Get-Content -Raw -LiteralPath $Source -Encoding UTF8
$jsonlTextExactMatch = $localRaw -ceq $remoteRaw
$remote = @($remoteRaw -split "`r?`n" | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })

$remoteById = @{}
$remoteDuplicates = @()
foreach ($record in $remote) {
    $id = [string]$record.id
    if ($remoteById.ContainsKey($id)) { $remoteDuplicates += $id }
    $remoteById[$id] = $record
}

$missingRemote = @($localById.Keys | Where-Object { -not $remoteById.ContainsKey($_) } | Sort-Object)
$extraRemote = @($remoteById.Keys | Where-Object { -not $localById.ContainsKey($_) } | Sort-Object)
$fieldSetMismatches = @()
$valueMismatches = @()

foreach ($id in $localById.Keys | Where-Object { $remoteById.ContainsKey($_) }) {
    $left = $localById[$id]
    $right = $remoteById[$id]
    $leftFields = @($left.PSObject.Properties.Name | Sort-Object)
    $rightFields = @($right.PSObject.Properties.Name | Sort-Object)
    if (($leftFields -join "|") -ne ($rightFields -join "|")) {
        $fieldSetMismatches += $id
        continue
    }
    foreach ($field in $leftFields) {
        if ((Convert-FieldToJson $left.$field) -ne (Convert-FieldToJson $right.$field)) {
            $valueMismatches += "$id.$field"
        }
    }
}

$semanticUris = 1..([int]$manifest.semantic_parts) | ForEach-Object {
    "$RemoteRoot/semantic/normalized/ziniao-online-bugs/part-{0:D4}.md" -f $_
}
$semanticBuilder = [System.Text.StringBuilder]::new()
foreach ($semanticUri in $semanticUris) {
    $semanticRelativePath = $semanticUri.Substring("viking://resources/".Length)
    $semanticResponse = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/webdav/resources/$semanticRelativePath" -Headers @{
        Authorization = "Bearer $token"
    }
    $null = $semanticBuilder.AppendLine($semanticResponse.Content)
}
$semanticText = $semanticBuilder.ToString()
$headingMatches = [regex]::Matches($semanticText, '(?m)^## \[(?<id>\d+)\] (?<title>.*)\r?$')
$semanticIds = @($headingMatches | ForEach-Object { $_.Groups['id'].Value })
$semanticDuplicates = @($semanticIds | Group-Object | Where-Object Count -gt 1 | ForEach-Object Name)
$semanticMissing = @($localById.Keys | Where-Object { $_ -notin $semanticIds } | Sort-Object)
$semanticExtra = @($semanticIds | Where-Object { -not $localById.ContainsKey($_) } | Sort-Object -Unique)
$titleMismatches = @()
foreach ($match in $headingMatches) {
    $id = $match.Groups['id'].Value
    $remoteTitle = $match.Groups['title'].Value.TrimEnd("`r")
    $expectedTitle = (([string]$localById[$id].title) -replace '\s+', ' ').Trim()
    if ($localById.ContainsKey($id) -and $remoteTitle -ne $expectedTitle) {
        $titleMismatches += [pscustomobject]@{
            Id = $id
            LocalTitle = [string]$localById[$id].title
            RemoteTitle = $remoteTitle
        }
    }
}

$localFields = @($local[0].PSObject.Properties.Name)
$semanticSourceFields = @('trigger_conditions', 'failure_symptoms', 'expected_result', 'fix_clues', 'evidence')
$missingSemanticSourceFields = @($semanticSourceFields | Where-Object { $_ -notin $localFields })
$semanticValueOmissions = @()
foreach ($id in $localById.Keys) {
    $sectionMatch = [regex]::Match($semanticText, "(?ms)^## \[$([regex]::Escape($id))\] .*?(?=^## \[\d+\] |\z)")
    if (-not $sectionMatch.Success) { continue }
    $section = $sectionMatch.Value
    foreach ($field in $semanticSourceFields) {
        foreach ($value in @($localById[$id].$field)) {
            $text = ([string]$value).Trim()
            if ($text -and -not $section.Contains($text)) {
                $semanticValueOmissions += "$id.$field"
            }
        }
    }
}

$localCurrentIds = @($local | Where-Object { @($_.view_memberships) -contains 'current_182d' } | ForEach-Object { [string]$_.id })
$localHistoricalIds = @($local | Where-Object { @($_.view_memberships) -contains 'historical_view' } | ForEach-Object { [string]$_.id })
$localOverlapIds = @($local | Where-Object {
    @($_.view_memberships) -contains 'current_182d' -and
    @($_.view_memberships) -contains 'historical_view'
} | ForEach-Object { [string]$_.id })
$localArchiveOnlyIds = @($local | Where-Object { @($_.view_memberships).Count -eq 0 } | ForEach-Object { [string]$_.id })
$membershipErrors = @()

if ([string]$manifest.schema_version -ne '1.1') { $membershipErrors += "manifest.schema_version" }
if ([int]$manifest.record_count -ne $local.Count) { $membershipErrors += "manifest.record_count" }
if ([int]$manifest.current_182d_count -ne $localCurrentIds.Count) { $membershipErrors += "manifest.current_182d_count" }
if ([int]$manifest.historical_view_count -ne $localHistoricalIds.Count) { $membershipErrors += "manifest.historical_view_count" }
if ([int]$manifest.view_overlap_count -ne $localOverlapIds.Count) { $membershipErrors += "manifest.view_overlap_count" }
if ([int]$manifest.archive_only_count -ne $localArchiveOnlyIds.Count) { $membershipErrors += "manifest.archive_only_count" }

if ((Test-Path -LiteralPath $CurrentViewSnapshot) -and (Test-Path -LiteralPath $HistoricalViewSnapshot)) {
    $currentSnapshot = Get-Content -Raw -LiteralPath $CurrentViewSnapshot -Encoding UTF8 | ConvertFrom-Json
    $historicalSnapshot = Get-Content -Raw -LiteralPath $HistoricalViewSnapshot -Encoding UTF8 | ConvertFrom-Json
    $expectedCurrentIds = @($currentSnapshot.items | ForEach-Object { [string]$_.id } | Sort-Object -Unique)
    $expectedHistoricalIds = @($historicalSnapshot.items | ForEach-Object { [string]$_.id } | Sort-Object -Unique)
    if (($expectedCurrentIds -join '|') -ne (($localCurrentIds | Sort-Object -Unique) -join '|')) {
        $membershipErrors += "current_182d.snapshot"
    }
    if (($expectedHistoricalIds -join '|') -ne (($localHistoricalIds | Sort-Object -Unique) -join '|')) {
        $membershipErrors += "historical_view.snapshot"
    }
}

$semanticMembershipOmissions = @()
foreach ($id in $localById.Keys) {
    $sectionMatch = [regex]::Match($semanticText, "(?ms)^## \[$([regex]::Escape($id))\] .*?(?=^## \[\d+\] |\z)")
    if (-not $sectionMatch.Success) { continue }
    $section = $sectionMatch.Value
    $expectedMemberships = (@($localById[$id].view_memberships) -join ', ')
    $expectedViewIds = (@($localById[$id].source_view_ids) -join ', ')
    if (-not $expectedMemberships) { $expectedMemberships = '未记录' }
    if (-not $expectedViewIds) { $expectedViewIds = '未记录' }
    if (-not $section.Contains("- view_memberships: $expectedMemberships")) {
        $semanticMembershipOmissions += "$id.view_memberships"
    }
    if (-not $section.Contains("- source_view_ids: $expectedViewIds")) {
        $semanticMembershipOmissions += "$id.source_view_ids"
    }
}

[pscustomobject]@{
    LocalRecords = $local.Count
    RemoteNormalizedRecords = $remote.Count
    RemoteNormalizedUniqueIds = $remoteById.Count
    JsonlTextExactMatch = $jsonlTextExactMatch
    MissingRemoteIds = $missingRemote.Count
    ExtraRemoteIds = $extraRemote.Count
    RemoteDuplicateIds = $remoteDuplicates.Count
    FieldSetMismatches = $fieldSetMismatches.Count
    FieldValueMismatches = $valueMismatches.Count
    SemanticHeadings = $semanticIds.Count
    SemanticUniqueIds = @($semanticIds | Sort-Object -Unique).Count
    SemanticMissingIds = $semanticMissing.Count
    SemanticExtraIds = $semanticExtra.Count
    SemanticDuplicateIds = $semanticDuplicates.Count
    SemanticTitleMismatches = $titleMismatches.Count
    SemanticMappingFieldsAbsentLocally = ($missingSemanticSourceFields -join ', ')
    SemanticValueOmissions = $semanticValueOmissions.Count
    MembershipErrors = ($membershipErrors -join ', ')
    SemanticMembershipOmissions = $semanticMembershipOmissions.Count
    Current182Days = $localCurrentIds.Count
    HistoricalView = $localHistoricalIds.Count
    ViewOverlap = $localOverlapIds.Count
    ArchiveOnly = $localArchiveOnlyIds.Count
    LocalWithTriggerConditions = @($local | Where-Object { @($_.trigger_conditions).Count -gt 0 }).Count
    LocalWithFailureSymptoms = @($local | Where-Object { @($_.failure_symptoms).Count -gt 0 }).Count
    LocalWithFixClues = @($local | Where-Object { @($_.fix_clues).Count -gt 0 }).Count
} | Format-List

if ($titleMismatches.Count) {
    Write-Host "Semantic title mismatches:"
    $titleMismatches | Format-Table -AutoSize -Wrap
}

if (-not $jsonlTextExactMatch -or $missingRemote.Count -or $extraRemote.Count -or $remoteDuplicates.Count -or $fieldSetMismatches.Count -or $valueMismatches.Count -or $semanticMissing.Count -or $semanticExtra.Count -or $semanticDuplicates.Count -or $titleMismatches.Count -or $missingSemanticSourceFields.Count -or $semanticValueOmissions.Count -or $membershipErrors.Count -or $semanticMembershipOmissions.Count) {
    Write-Error "Remote normalized data does not exactly match the local normalized data."
}
