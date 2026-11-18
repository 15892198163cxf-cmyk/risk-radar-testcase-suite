param(
    [string]$Source = (Join-Path (Split-Path -Parent $PSScriptRoot) "data\normalized_bugs.jsonl"),
    [string]$RemoteRoot = "viking://resources/ziniao-online-bugs-governed"
)

$ErrorActionPreference = "Stop"
$baseUrl = "http://10.96.0.8:1933"
$endpoint = "$baseUrl/mcp"
$token = $env:OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY

if (-not $token) {
    throw "OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY is not configured."
}
if (-not (Test-Path -LiteralPath $Source)) {
    throw "Bug source file not found: $Source"
}

function Invoke-OpenVikingTool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][hashtable]$Arguments
    )

    $request = @{
        jsonrpc = "2.0"
        id = [guid]::NewGuid().ToString()
        method = "tools/call"
        params = @{
            name = $Name
            arguments = $Arguments
        }
    } | ConvertTo-Json -Depth 30 -Compress

    $response = Invoke-WebRequest `
        -Uri $endpoint `
        -Method Post `
        -UseBasicParsing `
        -Headers @{
            Authorization = "Bearer $token"
            Accept = "application/json, text/event-stream"
        } `
        -ContentType "application/json; charset=utf-8" `
        -Body ([Text.Encoding]::UTF8.GetBytes($request))

    $dataLine = ($response.Content -split "`r?`n" | Where-Object { $_ -like "data: *" } | Select-Object -Last 1)
    if (-not $dataLine) {
        throw "OpenViking returned no JSON-RPC data for tool '$Name'."
    }

    $payload = $dataLine.Substring(6) | ConvertFrom-Json
    if ($payload.error) {
        throw "OpenViking tool '$Name' failed: $($payload.error.message)"
    }
    if ($payload.result.isError) {
        $message = ($payload.result.content | ForEach-Object { $_.text }) -join "`n"
        throw "OpenViking tool '$Name' failed: $message"
    }
    return $payload.result
}

function Write-OpenVikingFile {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content
    )

    $null = Invoke-OpenVikingTool -Name "write" -Arguments @{
        uri = $Uri
        content = $Content
        mode = "replace"
        wait = $false
    }
}

function Get-ResourceRelativePath {
    param([Parameter(Mandatory = $true)][string]$Uri)
    if ($Uri -notlike "viking://resources/*") {
        throw "Only viking://resources/ URIs are supported: $Uri"
    }
    return $Uri.Substring("viking://resources/".Length)
}

function Write-OpenVikingJsonl {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $relativePath = Get-ResourceRelativePath -Uri $Uri
    $webDavUri = "$baseUrl/webdav/resources/$relativePath"
    $headers = @{ Authorization = "Bearer $token" }

    # The canonical JSONL is an exact download artifact. Semantic retrieval is
    # provided by the Markdown chunks below, so do not index this large file a
    # second time through the content API.
    $null = Invoke-WebRequest -UseBasicParsing -Uri $webDavUri -Method Put -Headers $headers -InFile $Path -ContentType "application/x-ndjson"
}

function Remove-OpenVikingResourceFile {
    param([Parameter(Mandatory = $true)][string]$Uri)

    $relativePath = Get-ResourceRelativePath -Uri $Uri
    try {
        $null = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/webdav/resources/$relativePath" -Method Delete -Headers @{
            Authorization = "Bearer $token"
        }
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -ne 404) { throw }
    }
}

function Text-OrDash {
    param($Value)
    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text)) { return "未记录" }
    return $text.Trim()
}

function Single-LineText {
    param($Value)
    return ((Text-OrDash $Value) -replace '\s+', ' ').Trim()
}

function Append-MarkdownValues {
    param(
        [Parameter(Mandatory = $true)][System.Text.StringBuilder]$Builder,
        $Values
    )

    $items = @($Values | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    if ($items.Count -eq 0) {
        $null = $Builder.AppendLine("未记录")
        return
    }
    foreach ($item in $items) {
        $null = $Builder.AppendLine(([string]$item).Trim())
    }
}

$records = @(Get-Content -LiteralPath $Source -Encoding UTF8 | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
if ($records.Count -eq 0) {
    throw "Bug source file contains no records."
}

$missingIds = @($records | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.id) })
if ($missingIds.Count -gt 0) {
    throw "$($missingIds.Count) records have no Bug ID."
}

$duplicateIds = @($records | Group-Object id | Where-Object Count -gt 1)
if ($duplicateIds.Count -gt 0) {
    throw "Duplicate Bug IDs found: $($duplicateIds.Name -join ', ')"
}

$invalidMemberships = @($records | Where-Object {
    $memberships = @($_.view_memberships)
    $viewIds = @($_.source_view_ids)
    ($null -eq $_.view_memberships) -or
    ($null -eq $_.source_view_ids) -or
    @($memberships | Where-Object { $_ -notin @('current_182d', 'historical_view') }).Count -gt 0 -or
    ($memberships -contains 'current_182d' -and $viewIds -notcontains 'Khmxw2UDR') -or
    ($memberships -contains 'historical_view' -and $viewIds -notcontains 'ZZdtquUvR')
})
if ($invalidMemberships.Count -gt 0) {
    throw "$($invalidMemberships.Count) records have invalid view membership metadata."
}

$current182Count = @($records | Where-Object { @($_.view_memberships) -contains 'current_182d' }).Count
$historicalViewCount = @($records | Where-Object { @($_.view_memberships) -contains 'historical_view' }).Count
$viewOverlapCount = @($records | Where-Object {
    @($_.view_memberships) -contains 'current_182d' -and
    @($_.view_memberships) -contains 'historical_view'
}).Count
$archiveOnlyCount = @($records | Where-Object { @($_.view_memberships).Count -eq 0 }).Count

$semanticChunkSize = 20
$normalizedParts = 1
$semanticParts = [math]::Ceiling($records.Count / $semanticChunkSize)
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $stream = [System.IO.File]::OpenRead((Resolve-Path -LiteralPath $Source).ProviderPath)
    try {
        $sourceHash = [System.BitConverter]::ToString($sha256.ComputeHash($stream)).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $stream.Dispose()
    }
}
finally {
    $sha256.Dispose()
}
$generatedAt = (Get-Date).ToUniversalTime().ToString("o")
$relativeRoot = Get-ResourceRelativePath -Uri $RemoteRoot
$previousSemanticParts = 0
try {
    $previousManifest = (Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/webdav/resources/$relativeRoot/manifest.json" -Headers @{
        Authorization = "Bearer $token"
    }).Content | ConvertFrom-Json
    $previousSemanticParts = [int]$previousManifest.semantic_parts
}
catch {
    $previousSemanticParts = 0
}

$manifest = [ordered]@{
    schema_version = "1.1"
    dataset = "ziniao-online-bugs-governed"
    evidence_level = "ONLINE_BUG_HISTORY"
    evidence_role = "risk_history"
    source_type = "feishu_online_bug"
    record_count = $records.Count
    unique_bug_ids = $records.Count
    source_sha256 = $sourceHash
    generated_at = $generatedAt
    normalized_parts = $normalizedParts
    normalized_format = "jsonl"
    normalized_file = "normalized/normalized_bugs.jsonl"
    semantic_parts = $semanticParts
    current_182d_count = $current182Count
    historical_view_count = $historicalViewCount
    view_overlap_count = $viewOverlapCount
    archive_only_count = $archiveOnlyCount
    source_view_ids = @($records | ForEach-Object { @($_.source_view_ids) } | Where-Object { $_ } | Sort-Object -Unique)
    created_at_min = ($records.created_at | Where-Object { $_ } | Sort-Object | Select-Object -First 1)
    created_at_max = ($records.created_at | Where-Object { $_ } | Sort-Object | Select-Object -Last 1)
}
$readme = @"
# 紫鸟历史线上 Bug 治理库

- dataset: ziniao-online-bugs-governed
- evidence_level: ONLINE_BUG_HISTORY
- evidence_role: risk_history
- source_type: feishu_online_bug
- record_count: $($records.Count)
- current_182d_count: $current182Count
- historical_view_count: $historicalViewCount
- view_overlap_count: $viewOverlapCount
- archive_only_count: $archiveOnlyCount
- generated_at: $generatedAt
- source_sha256: $sourceHash

## 目录

- `normalized/normalized_bugs.jsonl`: 与本地归档格式和内容一致，一行一条 Bug。
- `semantic/normalized/ziniao-online-bugs/`: 面向语义检索的 Bug 证据摘要，按 20 条分片。

## 三层归属

- `current_182d`: 当前滚动 182 天视图 `Khmxw2UDR` 中的 Bug，用于新鲜度和近期复发权重。
- `historical_view`: 较宽历史视图 `ZZdtquUvR` 中的 Bug，用于补充一年以上的同功能历史。
- 长期归档: `normalized/normalized_bugs.jsonl` 的全部记录；不复制第三份数据，退出视图的 Bug 仍保留在归档中。
- 单条 Bug 通过 `view_memberships` 和 `source_view_ids` 表达归属；同一 Bug 只存一次、按 ID 去重。

## 使用边界

历史 Bug 用于识别曾发生的故障模式、复现条件和回归风险，不能单独定义当前产品预期。
引用时必须保留 Bug ID，并结合当前需求、模块、版本、入口和业务规则判断适用性。
本库与本地飞书 Bug 归档内容相同，跨来源检索必须按 Bug ID 去重。
"@
Write-OpenVikingFile -Uri "$RemoteRoot/README.md" -Content $readme

Write-OpenVikingJsonl -Uri "$RemoteRoot/normalized/normalized_bugs.jsonl" -Path $Source
Write-Host "Uploaded normalized/normalized_bugs.jsonl ($($records.Count) records)"

for ($part = 1; $part -le 5; $part++) {
    Remove-OpenVikingResourceFile -Uri ("$RemoteRoot/normalized/part-{0:D4}.json" -f $part)
}

for ($part = 0; $part -lt $semanticParts; $part++) {
    $start = $part * $semanticChunkSize
    $end = [math]::Min($start + $semanticChunkSize - 1, $records.Count - 1)
    $chunk = @($records[$start..$end])
    $builder = [System.Text.StringBuilder]::new()
    $null = $builder.AppendLine("# 紫鸟历史线上 Bug 证据")
    $null = $builder.AppendLine()
    $null = $builder.AppendLine("- evidence_level: ONLINE_BUG_HISTORY")
    $null = $builder.AppendLine("- evidence_role: risk_history")
    $null = $builder.AppendLine("- source_type: feishu_online_bug")
    $null = $builder.AppendLine("- dataset: ziniao-online-bugs-governed")

    foreach ($bug in $chunk) {
        $null = $builder.AppendLine()
        $null = $builder.AppendLine("## [$($bug.id)] $(Single-LineText $bug.title)")
        $null = $builder.AppendLine()
        $null = $builder.AppendLine("- bug_id: $($bug.id)")
        $null = $builder.AppendLine("- category: $(Text-OrDash $bug.category)")
        $null = $builder.AppendLine("- module: $(Text-OrDash $bug.module)")
        $null = $builder.AppendLine("- defect_type: $(Text-OrDash $bug.defect_type)")
        $null = $builder.AppendLine("- severity: $(Text-OrDash $bug.severity)")
        $null = $builder.AppendLine("- priority: $(Text-OrDash $bug.priority)")
        $null = $builder.AppendLine("- status: $(Text-OrDash $bug.status)")
        $null = $builder.AppendLine("- created_at: $(Text-OrDash $bug.created_at)")
        $null = $builder.AppendLine("- updated_at: $(Text-OrDash $bug.updated_at)")
        $null = $builder.AppendLine("- source_view_id: $(Text-OrDash $bug.source_view_id)")
        $null = $builder.AppendLine("- view_memberships: $((@($bug.view_memberships) -join ', ') | ForEach-Object { Text-OrDash $_ })")
        $null = $builder.AppendLine("- source_view_ids: $((@($bug.source_view_ids) -join ', ') | ForEach-Object { Text-OrDash $_ })")
        $null = $builder.AppendLine("- archived_at: $(Text-OrDash $bug.archived_at)")
        $null = $builder.AppendLine("- last_seen_in_window: $(Text-OrDash $bug.last_seen_in_window)")
        $null = $builder.AppendLine("- window_status: $(Text-OrDash $bug.window_status)")
        $null = $builder.AppendLine("- has_detail: $(Text-OrDash $bug.has_detail)")
        $null = $builder.AppendLine("- keywords: $(Single-LineText $bug.keywords)")
        $null = $builder.AppendLine()
        $null = $builder.AppendLine("### 触发条件")
        $null = $builder.AppendLine()
        Append-MarkdownValues -Builder $builder -Values $bug.trigger_conditions
        $null = $builder.AppendLine()
        $null = $builder.AppendLine("### 历史故障现象")
        $null = $builder.AppendLine()
        Append-MarkdownValues -Builder $builder -Values $bug.failure_symptoms
        $null = $builder.AppendLine()
        $null = $builder.AppendLine("### 期望结果")
        $null = $builder.AppendLine()
        Append-MarkdownValues -Builder $builder -Values $bug.expected_result
        $null = $builder.AppendLine()
        $null = $builder.AppendLine("### 修复线索")
        $null = $builder.AppendLine()
        Append-MarkdownValues -Builder $builder -Values $bug.fix_clues
        $null = $builder.AppendLine()
        $null = $builder.AppendLine("### 证据")
        $null = $builder.AppendLine()
        Append-MarkdownValues -Builder $builder -Values $bug.evidence
    }

    $name = "part-{0:D4}.md" -f ($part + 1)
    Write-OpenVikingFile -Uri "$RemoteRoot/semantic/normalized/ziniao-online-bugs/$name" -Content $builder.ToString()
    Write-Host "Uploaded semantic/normalized/ziniao-online-bugs/$name ($($chunk.Count) records)"
}

if ($previousSemanticParts -gt $semanticParts) {
    for ($part = $semanticParts + 1; $part -le $previousSemanticParts; $part++) {
        Remove-OpenVikingResourceFile -Uri ("$RemoteRoot/semantic/normalized/ziniao-online-bugs/part-{0:D4}.md" -f $part)
    }
}

# Commit marker: consumers trust the new archive only after all payload files
# have been uploaded and the manifest is replaced last.
Write-OpenVikingFile -Uri "$RemoteRoot/manifest.json" -Content ($manifest | ConvertTo-Json -Depth 10)

[pscustomobject]@{
    RemoteRoot = $RemoteRoot
    Records = $records.Count
    NormalizedParts = $normalizedParts
    SemanticParts = $semanticParts
    Current182Days = $current182Count
    HistoricalView = $historicalViewCount
    ViewOverlap = $viewOverlapCount
    ArchiveOnly = $archiveOnlyCount
    SourceSha256 = $sourceHash
} | Format-List
