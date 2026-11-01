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
