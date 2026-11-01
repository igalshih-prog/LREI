# Synthetic fixture only. No live network, outcomes, or promotion.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\scripts\LREI_capture_pais_latest_v4.ps1') -OfflineTestFunctionsOnly

function Assert-True([bool]$condition, [string]$label) {
    if (-not $condition) { throw ('OFFLINE TEST FAILED: ' + $label) }
}
function Assert-Refuses([scriptblock]$action, [string]$label) {
    $refused = $false
    try { & $action | Out-Null } catch { $refused = $true }
    if (-not $refused) { throw ('OFFLINE TEST FAILED: expected refusal for ' + $label) }
}

$enc = [System.Text.Encoding]::GetEncoding(1255)
$crlf = ([string][char]13) + ([string][char]10)
$header = 'הגרלה,תאריך,1,2,3,4,5,6,המספר החזק/נוסף,מספר_זוכים_לוטו,מספר_זוכים_דאבל_לוטו,'
$start = [DateTime]::ParseExact('2016-10-10', 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
$builder = New-Object System.Text.StringBuilder
[void]$builder.Append($header + $crlf)
[void]$builder.Append("6801,03/09/1968,03,14,18,22,25,33,42,,," + $crlf)
for ($index = 0; $index -lt 1147; $index++) {
    $id = 2833 + $index
    $when = $start.AddDays($index).ToString('dd/MM/yyyy')
    [void]$builder.Append(('{0},{1},01,02,03,04,05,06,3,0,0,' -f $id, $when) + $crlf)
}
$csv = $builder.ToString()
[byte[]]$bytes = $enc.GetBytes($csv)

$parsed = Read-CurrentEra $bytes
Assert-True ($parsed.LatestId -eq 3979) 'exactly 1147 synthetic modern draws'
Assert-True ($parsed.ModernCount -eq 1147) 'modern draw count'
Assert-True ($parsed.RawRowCount -eq 1148) 'legacy row retained in total'
Assert-True ($parsed.Map.ContainsKey(2833)) 'first modern draw present'
Assert-True (-not $parsed.Map.ContainsKey(6801)) 'legacy high ID excluded'

$badMain = $csv.Replace(',01,02,03,04,05,06,3,0,0,', ',01,02,03,04,05,05,3,0,0,')
Assert-Refuses { Read-CurrentEra ($enc.GetBytes($badMain)) } 'duplicate main numbers'
$badHeader = $csv.Replace('מספר_זוכים_דאבל_לוטו,', 'unknown_col,')
Assert-Refuses { Read-CurrentEra ($enc.GetBytes($badHeader)) } 'modified original header'
$badCount = $csv.Replace(',3,0,0,', ',3,-1,0,')
Assert-Refuses { Read-CurrentEra ($enc.GetBytes($badCount)) } 'negative jackpot count'
Assert-Refuses { Assert-FirstPartyUri ([Uri]'https://example.com/lotto.csv') } 'external redirect'
Assert-Refuses { Assert-FirstPartyUri ([Uri]'http://www.pais.co.il/Lotto/lotto_resultsDownload.aspx') } 'insecure redirect'
Assert-FirstPartyUri ([Uri]'https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx')

# Deterministic four-day content-age boundary checks in Israel-local dates.
# All dates below are fixtures, independent of the CI runner's timezone.
$referenceIsraelDate = [DateTime]::ParseExact('2026-11-01', 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
foreach ($case in @(
    [pscustomobject]@{ Age = 0; Expected = $true }
    [pscustomobject]@{ Age = 4; Expected = $true }
    [pscustomobject]@{ Age = 5; Expected = $false }
    [pscustomobject]@{ Age = 22; Expected = $false }
    [pscustomobject]@{ Age = -1; Expected = $false }
)) {
    $result = Test-SourceContentAge ($referenceIsraelDate.AddDays(-$case.Age)) $referenceIsraelDate
    Assert-True ($result.AgeDays -eq $case.Age) ('Israel age count ' + $case.Age)
    Assert-True ($result.MeetsFourDayLimit -eq $case.Expected) ('Israel four-day limit ' + $case.Age)
}
foreach ($status in @(
    'VALID_FIRST_PARTY_CONTENT_NO_PRIOR_CAPTURE_REVIEW_REQUIRED',
    'NO_NEW_DRAW_ROWS_REQUIRES_FRESHNESS_REVIEW',
    'NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW'
)) {
    Assert-True ((Get-SourceReviewStatus $status $false) -eq 'STALE_SOURCE_CONTENT_STOP_REVIEW') ('stale source refused: ' + $status)
    Assert-True ((Get-SourceReviewStatus $status $true) -eq $status) ('fresh source stays review-only: ' + $status)
}
Assert-True ((Get-SourceReviewStatus 'HISTORICAL_REVISIONS_OR_MISSING_DRAWS_STOP_REVIEW' $false) -eq 'HISTORICAL_REVISIONS_OR_MISSING_DRAWS_STOP_REVIEW') 'historical tampering refusal takes precedence'
Assert-True ((Get-SourceReviewStatus 'SOURCE_OLDER_THAN_PRIOR_CAPTURE_STOP_REVIEW' $false) -eq 'SOURCE_OLDER_THAN_PRIOR_CAPTURE_STOP_REVIEW') 'old source refusal takes precedence'

# Exercise the SAME history-comparison function used by the live diagnostic.
# All fixtures below are synthetic. No real draw #3980 is asserted or retrieved.
$same = Compare-CurrentEraSnapshots $parsed $parsed
Assert-True ($same.Status -eq 'NO_NEW_DRAW_ROWS_REQUIRES_FRESHNESS_REVIEW') 'same source is review-only'
Assert-True (@($same.HistoricalDifferences).Count -eq 0) 'same source has no revisions'
Assert-True (@($same.AddedDrawIds).Count -eq 0) 'same source has no new rows'

$nextDate = $start.AddDays(1147).ToString('dd/MM/yyyy')
$oneMoreCsv = $csv + ('3980,{0},01,02,03,04,05,06,3,0,0,' -f $nextDate) + $crlf
$oneMore = Read-CurrentEra ($enc.GetBytes($oneMoreCsv))
$append = Compare-CurrentEraSnapshots $parsed $oneMore
Assert-True ($append.Status -eq 'NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW') 'synthetic append requires human review'
Assert-True (@($append.AddedDrawIds).Count -eq 1 -and $append.AddedDrawIds[0] -eq 3980) 'only synthetic next ID added'
Assert-True (@($append.HistoricalDifferences).Count -eq 0) 'no historic edits in synthetic append'

$older = Compare-CurrentEraSnapshots $oneMore $parsed
Assert-True ($older.Status -eq 'HISTORICAL_REVISIONS_OR_MISSING_DRAWS_STOP_REVIEW') 'older source refused as missing an earlier known row'
Assert-True (@($older.HistoricalDifferences).Count -eq 1 -and $older.HistoricalDifferences[0] -eq 3980) 'precise missing synthetic ID'

$changeDate = $start.AddDays(500).ToString('dd/MM/yyyy')
$originalRow = ('3333,{0},01,02,03,04,05,06,3,0,0,' -f $changeDate)
Assert-True ($csv.Contains($originalRow)) 'target synthetic historic row exists'
$changedRows = @(
    [pscustomobject]@{ Name = 'main number'; Replacement = ('3333,{0},01,02,03,04,05,07,3,0,0,' -f $changeDate) }
    [pscustomobject]@{ Name = 'strong number'; Replacement = ('3333,{0},01,02,03,04,05,06,4,0,0,' -f $changeDate) }
    [pscustomobject]@{ Name = 'jackpot winner count'; Replacement = ('3333,{0},01,02,03,04,05,06,3,1,0,' -f $changeDate) }
    [pscustomobject]@{ Name = 'double jackpot winner count'; Replacement = ('3333,{0},01,02,03,04,05,06,3,0,1,' -f $changeDate) }
    [pscustomobject]@{ Name = 'draw date'; Replacement = ('3333,{0},01,02,03,04,05,06,3,0,0,' -f ($start.AddDays(501).ToString('dd/MM/yyyy'))) }
)
foreach ($change in $changedRows) {
    $revisedCsv = $csv.Replace($originalRow, $change.Replacement)
    Assert-True ($revisedCsv -cne $csv) ('fixture changes ' + $change.Name)
    $revised = Read-CurrentEra ($enc.GetBytes($revisedCsv))
    $comparison = Compare-CurrentEraSnapshots $parsed $revised
    Assert-True ($comparison.Status -eq 'HISTORICAL_REVISIONS_OR_MISSING_DRAWS_STOP_REVIEW') ('historic ' + $change.Name + ' refuses')
    Assert-True (@($comparison.HistoricalDifferences).Count -eq 1 -and $comparison.HistoricalDifferences[0] -eq 3333) ('pinpoint historic ' + $change.Name)
    Assert-True (@($comparison.AddedDrawIds).Count -eq 0) ('historic ' + $change.Name + ' does not masquerade as new draw')
}

$root = Join-Path ([System.IO.Path]::GetTempPath()) ('LREI-win-offline-' + [guid]::NewGuid().ToString('N'))
$folder = Join-Path $root 'LREI-source-20261030-175209'
New-Item -ItemType Directory -Path $folder -Force | Out-Null
try {
    $source = Join-Path $folder 'operator-source-original.csv'
    [System.IO.File]::WriteAllBytes($source, $bytes)
    $loaded = Read-BoundedCaptureFile $source
    Assert-True ($loaded.Length -eq $bytes.Length) 'bounded previous input preserves bytes'
    $sha = Get-BytesSha256 $bytes
    Assert-True ((Get-BytesSha256 $loaded) -ceq $sha) 'read bytes SHA-256 equals pin'

    $prior = [ordered]@{
        status = 'NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW'
        final_url_is_first_party_https = $true
        tls_certificate_validation_disabled = $false
        http_status = 200
        final_response_url = 'https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx'
        raw_response_sha256 = $sha
    }
    $reportPath = Join-Path $folder 'capture-report.json'
    $prior | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Assert-True (Test-BaselineEvidence $source) 'accept pinned non-promoting metadata'
    Assert-True ((Select-Baseline '' $root) -eq $source) 'select accepted private baseline'
    # The real 30 October report uses this legacy v1 status and identical fields.
    $prior.status = 'HTTPS_SOURCE_CONTENT_MATCH_REQUIRES_HUMAN_REVIEW'
    $prior | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Assert-True (Test-BaselineEvidence $source) 'accept safely pinned v1 capture-report schema'
    $prior.status = 'NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW'
    $prior.final_response_url = 'https://example.com/forged.csv'
    $prior | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Assert-True (-not (Test-BaselineEvidence $source)) 'reject forged off-domain prior URL'
    $prior.final_response_url = 'https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx'
    $prior.status = 'SOURCE_REJECTED_OR_DOWNLOAD_FAILED'
    $prior | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Assert-True (-not (Test-BaselineEvidence $source)) 'reject failed capture baseline'
    $prior.status = 'STALE_SOURCE_CONTENT_STOP_REVIEW'
    $prior | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Assert-True (-not (Test-BaselineEvidence $source)) 'do not auto-select stale source report as trusted baseline'
    $prior.status = 'NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW'
    $prior.raw_response_sha256 = ('0' * 64)
    $prior | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Assert-True (-not (Test-BaselineEvidence $source)) 'reject tampered baseline hash'

    $oversized = Join-Path $root 'oversized.csv'
    $stream = [System.IO.File]::Create($oversized)
    try { $stream.SetLength(8388609) } finally { $stream.Dispose() }
    Assert-Refuses { Read-BoundedCaptureFile $oversized } 'oversized baseline (8 MiB cap)'
}
finally { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host 'OFFLINE WINDOWS SOURCE TESTS PASSED (synthetic only; no network or attestation)'
