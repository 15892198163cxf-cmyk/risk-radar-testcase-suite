param(
    [string]$RemoteRoot = "viking://resources/ziniao-online-bugs-governed",
    [string]$BaseUrl = "http://10.96.0.8:1933",
    [switch]$Force,
    [switch]$RequireRemote
)

$ErrorActionPreference = "Stop"
$skillRoot = if ([string]::IsNullOrWhiteSpace($env:ZINIAO_LANDMINE_ROOT)) {
    Split-Path -Parent $PSScriptRoot
} else {
    [System.IO.Path]::GetFullPath($env:ZINIAO_LANDMINE_ROOT)
}
$dataRoot = Join-Path $skillRoot "data"
$target = Join-Path $dataRoot "normalized_bugs.jsonl"
$landmine = Join-Path $PSScriptRoot "landmine.py"
$token = $env:OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY

function Complete-WithFallback {
    param([string]$Reason)
    if ($RequireRemote) { throw $Reason }
    [pscustomobject]@{
        Status = "local_fallback"
        Reason = $Reason
        LocalCache = $target
        LocalExists = Test-Path -LiteralPath $target
    } | Format-List
    exit 0
}

function Assert-Command {
    param([string[]]$Arguments)
    & py @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: py $($Arguments -join ' ')"
    }
}

if (-not $token) {
    Complete-WithFallback "OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY is not configured."
}

if ($RemoteRoot -notlike "viking://resources/*") {
    throw "Only viking://resources/ URIs are supported: $RemoteRoot"
}

$relativeRoot = $RemoteRoot.Substring("viking://resources/".Length)
$headers = @{ Authorization = "Bearer $token" }
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ziniao-bug-cache-" + [guid]::NewGuid())
$null = New-Item -ItemType Directory -Path $tempRoot
$remoteFile = Join-Path $tempRoot "normalized_bugs.jsonl"

try {
    try {
        $manifestResponse = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri "$BaseUrl/webdav/resources/$relativeRoot/manifest.json" `
            -Headers $headers `
            -TimeoutSec 15
        $manifest = $manifestResponse.Content | ConvertFrom-Json
    }
    catch {
        Complete-WithFallback ("OpenViking Bug manifest unavailable: " + $_.Exception.Message)
    }

    if ([string]$manifest.schema_version -ne "1.1") {
        Complete-WithFallback "OpenViking Bug dataset schema is not 1.1."
    }

    $manifestHash = ([string]$manifest.source_sha256).ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($manifestHash)) {
        Complete-WithFallback "OpenViking Bug manifest has no source_sha256."
    }
    $localHash = if (Test-Path -LiteralPath $target) {
        (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    } else { "" }

    # Fast path: the remote manifest already identifies the current dataset.
    # Do not download the full normalized archive when the local bytes match it.
    if (-not $Force -and $localHash -eq $manifestHash) {
        [pscustomobject]@{
            Status = "current"
            Records = [int]$manifest.record_count
            Current182Days = [int]$manifest.current_182d_count
            HistoricalView = [int]$manifest.historical_view_count
            ArchiveOnly = [int]$manifest.archive_only_count
            GeneratedAt = [string]$manifest.generated_at
            SourceSha256 = $manifestHash
            DownloadedDataset = $false
        } | Format-List
        exit 0
    }

    try {
        Invoke-WebRequest `
            -UseBasicParsing `
            -Uri "$BaseUrl/webdav/resources/$relativeRoot/normalized/normalized_bugs.jsonl" `
            -Headers $headers `
            -OutFile $remoteFile `
            -TimeoutSec 60 | Out-Null
    }
    catch {
        Complete-WithFallback ("OpenViking Bug dataset unavailable: " + $_.Exception.Message)
    }

    $remoteHash = (Get-FileHash -LiteralPath $remoteFile -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($remoteHash -ne $manifestHash) {
        Complete-WithFallback "OpenViking Bug dataset hash does not match its manifest."
    }

    $records = @(Get-Content -LiteralPath $remoteFile -Encoding UTF8 | Where-Object { $_.Trim() } | ForEach-Object {
        $_ | ConvertFrom-Json
    })
    $duplicateIds = @($records | Group-Object id | Where-Object Count -gt 1)
    $invalidRows = @($records | Where-Object {
        [string]::IsNullOrWhiteSpace([string]$_.id) -or
        $null -eq $_.view_memberships -or
        $null -eq $_.source_view_ids -or
        @(@($_.view_memberships) | Where-Object { $_ -notin @('current_182d', 'historical_view') }).Count -gt 0
    })
    $currentCount = @($records | Where-Object { @($_.view_memberships) -contains 'current_182d' }).Count
    $historicalCount = @($records | Where-Object { @($_.view_memberships) -contains 'historical_view' }).Count
    $overlapCount = @($records | Where-Object {
        @($_.view_memberships) -contains 'current_182d' -and
        @($_.view_memberships) -contains 'historical_view'
    }).Count
    $archiveOnlyCount = @($records | Where-Object { @($_.view_memberships).Count -eq 0 }).Count

    if ($records.Count -ne [int]$manifest.record_count -or
        $duplicateIds.Count -gt 0 -or
        $invalidRows.Count -gt 0 -or
        $currentCount -ne [int]$manifest.current_182d_count -or
        $historicalCount -ne [int]$manifest.historical_view_count -or
        $overlapCount -ne [int]$manifest.view_overlap_count -or
        $archiveOnlyCount -ne [int]$manifest.archive_only_count) {
        Complete-WithFallback "OpenViking Bug dataset failed count, uniqueness, or membership validation."
    }

    $managedFiles = @(
        "normalized_bugs.jsonl",
        "scenario_candidates.json",
        "scenario_candidates.md",
        "scenario_index.json",
        "feishu_clusters.json",
        "feishu_clusters.md",
        "feishu_cluster_landmines.jsonl"
    )
    $backupRoot = Join-Path $tempRoot "backup"
    $null = New-Item -ItemType Directory -Path $backupRoot
    foreach ($name in $managedFiles) {
        $path = Join-Path $dataRoot $name
        if (Test-Path -LiteralPath $path) {
            Copy-Item -LiteralPath $path -Destination (Join-Path $backupRoot $name)
        }
    }

    try {
        Copy-Item -LiteralPath $remoteFile -Destination $target -Force
        Assert-Command @($landmine, "build-scenarios")
        Assert-Command @($landmine, "cluster-feishu", "--source", $target)
        Assert-Command @($landmine, "sync-clusters")
        Assert-Command @($landmine, "eval", "--limit", "20")
    }
    catch {
        foreach ($name in $managedFiles) {
            $backup = Join-Path $backupRoot $name
            $path = Join-Path $dataRoot $name
            if (Test-Path -LiteralPath $backup) {
                Copy-Item -LiteralPath $backup -Destination $path -Force
            }
            elseif (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -Force
            }
        }
        Complete-WithFallback ("Remote cache update was rolled back after validation failed: " + $_.Exception.Message)
    }

    [pscustomobject]@{
        Status = "updated"
        Records = $records.Count
        Current182Days = $currentCount
        HistoricalView = $historicalCount
        ViewOverlap = $overlapCount
        ArchiveOnly = $archiveOnlyCount
        GeneratedAt = [string]$manifest.generated_at
        SourceSha256 = $remoteHash
        DownloadedDataset = $true
    } | Format-List
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
