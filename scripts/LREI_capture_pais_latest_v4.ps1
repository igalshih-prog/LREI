# LREI first-party Windows HTTPS research evidence capture — rolling draws (v4; bounded source and baseline)
# Independent data capture, NOT signed draw protocol / source license / dataset-promotion approval.
# Inspects all redirects before following, retains the exact raw download privately,
# compares all 6/37 historical rows to a previously retained first-party capture.
# Built for Windows PowerShell 5.1 and built-in .NET (no extra packages).
[CmdletBinding()]
param(
    [string]$PreviousCaptureCsv = '',
    [switch]$OfflineTestFunctionsOnly
)
$ErrorActionPreference = 'Stop'
$officialUrl = 'https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx'
$downloads = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads'
$folder = Join-Path $downloads ('LREI-source-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
$rawPath = Join-Path $folder 'operator-source-original.csv'
$reportPath = Join-Path $folder 'capture-report.json'

function Assert-FirstPartyUri([Uri]$uri) {
    if ($uri.Scheme -ne 'https' -or $uri.UserInfo -ne '' -or
        ($uri.DnsSafeHost.ToLowerInvariant() -notin @('pais.co.il','www.pais.co.il')) -or
        (-not $uri.IsDefaultPort -and $uri.Port -ne 443)) {
        throw ('Refusing non-first-party HTTPS URL or redirect: ' + $uri.AbsoluteUri)
    }
}

function Read-CurrentEra([byte[]]$contentBytes) {
    if ($contentBytes.Length -lt 10000 -or $contentBytes.Length -gt 8388608) {
        throw 'Unexpected operator archive size (must be between 10 KiB and 8 MiB).'
    }
    if ($contentBytes[0] -eq 60) { throw 'HTML response, not an operator CSV.' }
    $encoding = [System.Text.Encoding]::GetEncoding(
        1255, [System.Text.EncoderFallback]::ExceptionFallback,
        [System.Text.DecoderFallback]::ExceptionFallback)
    $decoded = $encoding.GetString($contentBytes)
    $lines = [System.Text.RegularExpressions.Regex]::Split($decoded, "\r\n|\n|\r")
    $expected = @('הגרלה','תאריך','1','2','3','4','5','6','המספר החזק/נוסף','מספר_זוכים_לוטו','מספר_זוכים_דאבל_לוטו')
    $header = $lines[0].Split(',')
    if ($header.Length -ne 12 -or $header[11] -cne '') { throw 'Unexpected CSV header width or trailing field.' }
    for ($i = 0; $i -lt $expected.Length; $i++) {
        if ($header[$i].Trim([char]0xFEFF) -cne $expected[$i]) { throw ('Unexpected CSV column at index ' + $i) }
    }
    $records = @{}
    $archiveRowCount = 0
    $cutoff = [DateTime]::ParseExact('10/10/2016','dd/MM/yyyy',[System.Globalization.CultureInfo]::InvariantCulture)
    foreach ($line in $lines | Select-Object -Skip 1) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $archiveRowCount++
        $fields = $line.Split(',')
        if ($fields.Length -ne 12 -or $fields[11] -cne '') { throw ('Malformed 12-column operator row ' + $archiveRowCount) }
        if ($fields[0] -cnotmatch '^\d+$') { throw ('Malformed draw ID in archive row ' + $archiveRowCount) }
        $drawId = [int]$fields[0]
        $drawDate = [DateTime]::MinValue
        if (-not [DateTime]::TryParseExact($fields[1], 'dd/MM/yyyy',
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::None, [ref]$drawDate)) {
            throw ('Invalid date in archive row ' + $archiveRowCount)
        }
        # Critical guard: legacy 1960s draw IDs can be numerically larger than modern IDs.
        if ($drawId -lt 2833 -or $drawDate -lt $cutoff) { continue }
        if ($drawDate.Date -gt ([DateTime]::Now.Date.AddDays(1))) {
            throw ('Future-dated archive draw not accepted: ' + $drawId)
        }
        $nums = @()
        for ($j = 2; $j -le 7; $j++) {
            if ($fields[$j] -cnotmatch '^\d{1,2}$') { throw ('Bad main number in draw ' + $drawId) }
            $v = [int]$fields[$j]
            if ($v -lt 1 -or $v -gt 37) { throw ('Out-of-range main number in draw ' + $drawId) }
            $nums += $v
        }
        if (@($nums | Select-Object -Unique).Count -ne 6) { throw ('Repeated main number in draw ' + $drawId) }
        if ($fields[8] -cnotmatch '^[1-7]$') { throw ('Invalid strong number in draw ' + $drawId) }
        if ($fields[9] -cnotmatch '^\d+$' -or $fields[10] -cnotmatch '^\d+$') {
            throw ('Malformed jackpot winner counts in draw ' + $drawId)
        }
        if ($records.ContainsKey($drawId)) { throw ('Duplicate modern draw ID ' + $drawId) }
        $canonical = @($nums | Sort-Object | ForEach-Object { '{0:D2}' -f $_ }) -join ','
        $records[$drawId] = ($drawDate.ToString('yyyy-MM-dd') + '|' + $canonical + '|' + [int]$fields[8] +
                            '|' + [int]$fields[9] + '|' + [int]$fields[10])
    }
    $ids = @($records.Keys | ForEach-Object { [int]$_ } | Sort-Object)
    if ($ids.Count -lt 1147 -or $ids[0] -ne 2833) { throw 'Modern 6/37 archive is incomplete before draw #3979.' }
    if ($ids.Count -ne ($ids[-1] - 2833 + 1)) { throw 'Missing current-format draw IDs in official source.' }
    $lastDate = [DateTime]::MinValue
    foreach ($id in $ids) {
        $dateString = $records[$id].Split('|')[0]
        $date = [DateTime]::ParseExact($dateString,'yyyy-MM-dd',[System.Globalization.CultureInfo]::InvariantCulture)
        if ($date -lt $lastDate) { throw ('Modern draw dates out of order at #' + $id) }
        $lastDate = $date
    }
    return [pscustomobject]@{
        Map = $records
        Ids = $ids
        LatestId = $ids[-1]
        LatestDate = $lastDate.ToString('yyyy-MM-dd')
        ModernCount = $ids.Count
        RawRowCount = $archiveRowCount
    }
}

# Bound re-reading of an older (possibly user-specified) capture as strictly as
# the new HTTPS response. Do not trust its file size or hash without re-checking
# the exact bytes that are subsequently parsed and compared.
function Read-BoundedCaptureFile([string]$path) {
    $limit = 8 * 1024 * 1024
    $file = New-Object System.IO.FileInfo -ArgumentList @($path)
    if (-not $file.Exists -or $file.Length -lt 10000 -or $file.Length -gt $limit) {
        throw 'Previous capture missing or outside 10 KiB to 8 MiB safety range.'
    }
    $stream = [System.IO.File]::OpenRead($path)
    $memory = New-Object System.IO.MemoryStream
    try {
        [byte[]]$buffer = New-Object byte[] 8192
        while ($true) {
            $n = $stream.Read($buffer, 0, $buffer.Length)
            if ($n -le 0) { break }
            if (($memory.Length + $n) -gt $limit) {
                throw 'Previous capture grew beyond the 8 MiB safety cap.'
            }
            $memory.Write($buffer, 0, $n)
        }
        if ($memory.Length -lt 10000) { throw 'Previous capture unexpectedly truncated.' }
        [byte[]]$result = $memory.ToArray()
        return ,$result
    }
    finally {
        $memory.Dispose()
        $stream.Dispose()
    }
}

function Get-BytesSha256([byte[]]$contentBytes) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha.ComputeHash($contentBytes))).Replace('-', '').ToLowerInvariant()
    }
    finally { $sha.Dispose() }
}

# Use a past response only when its matching report has a non-refusal status,
# a matching raw SHA-256, a first-party final URL and TLS verification enabled.
# A refused/partial capture must never become the automatic comparison baseline.
function Test-BaselineEvidence([string]$csvPath) {
    if (-not (Test-Path -LiteralPath $csvPath -PathType Leaf)) { return $false }
    $jsonPath = Join-Path (Split-Path -Path $csvPath -Parent) 'capture-report.json'
    if (-not (Test-Path -LiteralPath $jsonPath -PathType Leaf)) { return $false }
    try {
        $prior = Get-Content -LiteralPath $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $allowedStatuses = @(
            'HTTPS_SOURCE_CONTENT_MATCH_REQUIRES_HUMAN_REVIEW',
            'VALID_FIRST_PARTY_CONTENT_NO_PRIOR_CAPTURE_REVIEW_REQUIRED',
            'NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW',
            'NO_NEW_DRAW_ROWS_REQUIRES_FRESHNESS_REVIEW'
        )
        if ($prior.status -notin $allowedStatuses) { return $false }
        if ($prior.final_url_is_first_party_https -ne $true -or
            $prior.tls_certificate_validation_disabled -ne $false -or
            [int]$prior.http_status -ne 200) { return $false }
        $priorUrl = [Uri]$prior.final_response_url
        Assert-FirstPartyUri $priorUrl
        $digest = (Get-FileHash -LiteralPath $csvPath -Algorithm SHA256).Hash.ToLowerInvariant()
        return ($prior.raw_response_sha256 -ceq $digest)
    }
    catch { return $false }
}

function Select-Baseline([string]$manualPath, [string]$root) {
    if ($manualPath -ne '') {
        if (-not (Test-BaselineEvidence $manualPath)) {
            throw 'Specified previous raw CSV lacks matching accepted capture-report.json evidence.'
        }
        return $manualPath
    }
    $dirs = @(Get-ChildItem -LiteralPath $root -Directory -Filter 'LREI-source-*' -ErrorAction SilentlyContinue |
              Sort-Object Name -Descending)
    foreach ($dir in $dirs) {
        $csvPath = Join-Path $dir.FullName 'operator-source-original.csv'
        if (Test-BaselineEvidence $csvPath) { return $csvPath }
    }
    return ''
}

# Offline test injection point: dot-source this script with -OfflineTestFunctionsOnly
# to exercise functions without selecting a baseline or touching the network.
if ($OfflineTestFunctionsOnly) { return }

$previousCsv = Select-Baseline $PreviousCaptureCsv $downloads
New-Item -ItemType Directory -Path $folder -ErrorAction Stop | Out-Null
$report = [ordered]@{
    report_schema = 'lrei-windows-rolling-https-source-review-v4'
    capture_script_sha256 = $null
    requested_source = $officialUrl
    final_response_url = $null
    redirect_chain = @()
    captured_at_utc = $null
    http_status = $null
    content_type = $null
    raw_response_bytes = $null
    raw_response_sha256 = $null
    source_archive_rows = $null
    modern_era_first_draw_id = 2833
    modern_era_draw_count = $null
    modern_era_latest_draw_id = $null
    modern_era_latest_draw_date = $null
    prior_capture_found = ($previousCsv -ne '')
    prior_capture_sha256 = $null
    prior_capture_latest_draw_id = $null
    checked_prior_draw_rows = 0
    historical_differences = @()
    added_draw_ids = @()
    final_url_is_first_party_https = $false
    tls_certificate_validation_disabled = $false
    legally_binding_draw_protocol_verified = $false
    provenance_independently_attested = $false
    dataset_promotion_approved = $false
    research_only_no_play = $true
    status = 'NOT_STARTED'
    error = $null
}
if ($PSCommandPath -and (Test-Path -LiteralPath $PSCommandPath -PathType Leaf)) {
    $report.capture_script_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
}
$client = $null
$response = $null
try {
    # Windows/.NET normal certificate chain validation. Do not bypass cert errors.
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Add-Type -AssemblyName System.Net.Http
    $handler = New-Object System.Net.Http.HttpClientHandler
    $handler.AllowAutoRedirect = $false   # validate EACH redirect hop before any request
    $client = New-Object System.Net.Http.HttpClient -ArgumentList @($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(85)
    $target = [Uri]$officialUrl
    for ($hop = 0; $hop -le 5; $hop++) {
        Assert-FirstPartyUri $target
        if ($null -ne $response) { $response.Dispose(); $response = $null }
        $response = $client.GetAsync($target, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        $statusCode = [int]$response.StatusCode
        $report.redirect_chain += $target.AbsoluteUri
        if ($statusCode -in @(301,302,303,307,308)) {
            if ($hop -ge 5) { throw 'Exceeded 5 redirect hops.' }
            $location = $response.Headers.Location
            if ($null -eq $location) { throw 'Redirect response without Location.' }
            if ($location.IsAbsoluteUri) { $target = $location }
            else { $target = [Uri]::new($target, $location) }
            continue
        }
        $report.final_response_url = $target.AbsoluteUri
        $report.final_url_is_first_party_https = $true
        $report.http_status = $statusCode
        if ($statusCode -ne 200) { throw ('Unexpected official HTTP status ' + $statusCode) }
        if ($null -ne $response.Content.Headers.ContentType) {
            $report.content_type = $response.Content.Headers.ContentType.ToString()
        }
        # HttpCompletionOption.ResponseHeadersRead avoids buffering the whole response.
        # Stream at most 8 MiB + reject any oversized response BEFORE allocation.
        $maxCsvBytes = 8 * 1024 * 1024
        $declaredLength = $response.Content.Headers.ContentLength
        if ($null -ne $declaredLength -and $declaredLength -gt $maxCsvBytes) {
            throw 'Operator CSV declared length exceeds the 8 MiB safety cap.'
        }
        $sourceStream = $null
        $boundedBuffer = $null
        try {
            $sourceStream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
            $boundedBuffer = New-Object System.IO.MemoryStream
            [byte[]]$chunk = New-Object byte[] 8192
            while ($true) {
                $count = $sourceStream.Read($chunk, 0, $chunk.Length)
                if ($count -le 0) { break }
                if (($boundedBuffer.Length + $count) -gt $maxCsvBytes) {
                    throw 'Operator CSV streamed beyond the 8 MiB safety cap.'
                }
                $boundedBuffer.Write($chunk, 0, $count)
            }
            $bytes = $boundedBuffer.ToArray()
        }
        finally {
            if ($null -ne $boundedBuffer) { $boundedBuffer.Dispose() }
            if ($null -ne $sourceStream) { $sourceStream.Dispose() }
        }
        if ($bytes.Length -lt 10000) { throw 'Operator CSV response too short for a full historical archive.' }
        [System.IO.File]::WriteAllBytes($rawPath, $bytes)
        $report.captured_at_utc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
        $report.raw_response_bytes = [int]$bytes.Length
        $report.raw_response_sha256 = Get-BytesSha256 $bytes
        $parsed = Read-CurrentEra $bytes
        $report.source_archive_rows = $parsed.RawRowCount
        $report.modern_era_draw_count = $parsed.ModernCount
        $report.modern_era_latest_draw_id = $parsed.LatestId
        $report.modern_era_latest_draw_date = $parsed.LatestDate

        if ($previousCsv -eq '') {
            $report.status = 'VALID_FIRST_PARTY_CONTENT_NO_PRIOR_CAPTURE_REVIEW_REQUIRED'
        } else {
            [byte[]]$priorBytes = Read-BoundedCaptureFile $previousCsv
            $report.prior_capture_sha256 = Get-BytesSha256 $priorBytes
            $priorReportPath = Join-Path (Split-Path -Path $previousCsv -Parent) 'capture-report.json'
            $priorReport = Get-Content -LiteralPath $priorReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($report.prior_capture_sha256 -cne $priorReport.raw_response_sha256) {
                throw 'Previous capture bytes changed between baseline verification and comparison.'
            }
            $previous = Read-CurrentEra $priorBytes
            $report.prior_capture_latest_draw_id = $previous.LatestId
            $report.checked_prior_draw_rows = $previous.ModernCount
            $differences = @()
            foreach ($id in $previous.Ids) {
                if (-not $parsed.Map.ContainsKey($id) -or $parsed.Map[$id] -cne $previous.Map[$id]) {
                    $differences += [int]$id
                }
            }
            $report.historical_differences = @($differences)
            if ($differences.Count -gt 0) {
                $report.status = 'HISTORICAL_REVISIONS_OR_MISSING_DRAWS_STOP_REVIEW'
            } elseif ($parsed.LatestId -lt $previous.LatestId) {
                $report.status = 'SOURCE_OLDER_THAN_PRIOR_CAPTURE_STOP_REVIEW'
            } else {
                $newIds = @($parsed.Ids | Where-Object { $_ -gt $previous.LatestId })
                $report.added_draw_ids = $newIds
                if ($newIds.Count -gt 0) {
                    $report.status = 'NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW'
                } else {
                    $report.status = 'NO_NEW_DRAW_ROWS_REQUIRES_FRESHNESS_REVIEW'
                }
            }
        }
        break
    }
}
catch {
    $report.status = 'SOURCE_REJECTED_OR_DOWNLOAD_FAILED'
    $report.error = $_.Exception.Message
}
finally {
    if ($null -ne $response) { $response.Dispose() }
    if ($null -ne $client) { $client.Dispose() }
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
Write-Host ('Status: ' + $report.status)
Write-Host ('Evidence directory: ' + $folder)
Write-Host ('Report JSON: ' + $reportPath)
Write-Host ('Latest source draw: ' + $report.modern_era_latest_draw_id + ' (' + $report.modern_era_latest_draw_date + ')')
Write-Host ('Source SHA-256: ' + $report.raw_response_sha256)
Write-Host ('Added draw IDs since prior captured source: ' + (@($report.added_draw_ids) -join ', '))
if ($null -ne $report.error) { Write-Warning $report.error }
Write-Host 'Keep operator-source-original.csv PRIVATE. Share only capture-report.json for initial review.'
Write-Host 'The operator site CSV is nonbinding; this tool never approves a dataset or playing.'
if ($report.status -in @('NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW',
                         'NO_NEW_DRAW_ROWS_REQUIRES_FRESHNESS_REVIEW',
                         'VALID_FIRST_PARTY_CONTENT_NO_PRIOR_CAPTURE_REVIEW_REQUIRED')) { exit 0 }
exit 2
