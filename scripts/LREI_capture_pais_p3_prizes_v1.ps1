# Capture only the specific 14 public operator prize pages for quarantined P3 review.
# NO DATA PROMOTION, NO PLAY. Raw pages and parsed candidates stay PRIVATE.
[CmdletBinding()]
param(
    [switch]$FullCohort,
    [switch]$RemainingCohort,
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$maxPageBytes = 6MB
# PowerShell unwraps a one-item array emitted by an if expression. Under
# StrictMode, the resulting scalar has no .Count property (observed in the
# successful #3955 pilot at manifest generation). Always retain an array.
# After a successful locally verified #3955 pilot, the optional remaining
# cohort begins at #3956 and never needlessly re-downloads #3955.
# Both extended modes are private/research-only and require a human check
# of operator terms before use; no script option grants rights or attests data.
if ($FullCohort -and $RemainingCohort) {
    throw 'Choose FullCohort OR RemainingCohort, not both.'
}
$draws = @(3955)
if ($FullCohort) { $draws = @(3955..3968) }
if ($RemainingCohort) { $draws = @(3956..3968) }
if ($RepoRoot -ne '') {
    $repoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}
else {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}
$historyFile = Join-Path $repoRoot 'data\lottery.csv'
if (-not (Test-Path -LiteralPath $historyFile -PathType Leaf)) {
    throw 'Trusted historical CSV missing. Run from checked-out LREI repository.'
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher py is missing; install Python and LREI before running.'
}

# The offline parser must come from THIS reviewed checkout, never an unrelated
# globally installed package that happens to have the same module name.
$localParser = Join-Path $repoRoot 'src\lrei\lottery\prize_capture_intake.py'
if (-not (Test-Path -LiteralPath $localParser -PathType Leaf)) {
    throw 'The local trusted LREI prize intake module is missing.'
}
# Do not append inherited PYTHONPATH. Empty segments can add the shell's
# working directory to import resolution, and inherited segments need not
# belong to this reviewed checkout. The offline parser only needs local src.
$env:PYTHONPATH = (Join-Path $repoRoot 'src')

$stampDir = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
$folder = Join-Path (Join-Path $HOME 'Downloads') ('LREI-P3-private-' + $stampDir + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
[void][System.IO.Directory]::CreateDirectory($folder)
$scriptDigest = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$utf8 = New-Object System.Text.UTF8Encoding($false)
$records = New-Object 'System.Collections.Generic.List[object]'

function Read-BoundedOperatorPage {
    param([int]$DrawId, [long]$MaxBytes)
    $url = 'https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=' + $DrawId
    $req = [System.Net.HttpWebRequest][System.Net.WebRequest]::Create($url)
    $req.Method = 'GET'
    $req.AllowAutoRedirect = $false
    $req.Timeout = 30000
    $req.ReadWriteTimeout = 30000
    $req.Accept = 'text/html'
    $req.UserAgent = 'LREI-research-source-check/1.0 (individual public-page review)'
    $req.KeepAlive = $false
    $response = $null
    $sourceStream = $null
    $buffered = $null
    try {
        $response = [System.Net.HttpWebResponse]$req.GetResponse()
        if ([int]$response.StatusCode -ne 200) {
            throw ('Unexpected HTTP status ' + [int]$response.StatusCode + '; no redirects are followed.')
        }
        if ($response.ResponseUri.AbsoluteUri -cne $url) {
            throw 'The final URL differed from the exact official draw URL.'
        }
        $kind = ($response.ContentType -split ';')[0].Trim().ToLowerInvariant()
        if ($kind -ne 'text/html') {
            throw ('Source is not HTML (Content-Type: ' + $kind + ').')
        }
        if ($response.ContentLength -gt $MaxBytes) {
            throw 'Page exceeds the private capture size limit.'
        }
        $sourceStream = $response.GetResponseStream()
        if ($null -eq $sourceStream) { throw 'Empty HTTP response stream.' }
        $buffered = New-Object System.IO.MemoryStream
        $chunk = New-Object byte[] 8192
        while (($read = $sourceStream.Read($chunk, 0, $chunk.Length)) -gt 0) {
            if ($buffered.Length + $read -gt $MaxBytes) {
                throw 'Page exceeded the 6 MiB capture limit while downloading.'
            }
            $buffered.Write($chunk, 0, $read)
        }
        if ($buffered.Length -lt 1000) { throw 'HTML page appears truncated (under 1 KiB).' }
        $raw = $buffered.ToArray()
        $hash = [System.Security.Cryptography.SHA256]::Create()
        try {
            $hex = ([BitConverter]::ToString($hash.ComputeHash($raw))).Replace('-', '').ToLowerInvariant()
        }
        finally { $hash.Dispose() }
        return [pscustomobject]@{
            raw = $raw
            bytes = [int]$raw.Length
            sha256 = $hex
            source_url = $url
            content_type = $kind
            captured_at_utc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
        }
    }
    finally {
        if ($null -ne $buffered) { $buffered.Dispose() }
        if ($null -ne $sourceStream) { $sourceStream.Dispose() }
        if ($null -ne $response) { $response.Dispose() }
    }
}

foreach ($id in $draws) {
    $url = 'https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=' + $id
    $entry = [ordered]@{
        draw_id = $id
        requested_url = $url
        final_response_url = $null
        captured_at_utc = $null
        http_status = $null
        content_type = $null
        raw_source_bytes = $null
        raw_source_sha256 = $null
        status = 'CAPTURE_FAILED_PRIVATE_REVIEW_ONLY'
        parsed_tiers = 0
        error = $null
    }
    try {
        $fetched = Read-BoundedOperatorPage -DrawId $id -MaxBytes $maxPageBytes
        $originalFile = Join-Path $folder ('draw-' + $id + '-operator-original.html')
        if ([IO.File]::Exists($originalFile)) { throw 'Original private file already exists.' }
        [IO.File]::WriteAllBytes($originalFile, $fetched.raw)
        $entry.final_response_url = $fetched.source_url
        $entry.captured_at_utc = $fetched.captured_at_utc
        $entry.http_status = 200
        $entry.content_type = $fetched.content_type
        $entry.raw_source_bytes = $fetched.bytes
        $entry.raw_source_sha256 = $fetched.sha256
        $entry.status = 'RAW_PAGE_CAPTURED_PARSER_REVIEW_PENDING'

        # The repository's existing STRICT 16-tier parser operates OFFLINE only.
        # Output is written privately and never committed to GitHub.
        $parserError = Join-Path $folder ('draw-' + $id + '-parser-stderr.txt')
        # Windows PowerShell 5.1 may treat a native tool's redirected stderr
        # as a terminating error when ErrorActionPreference = Stop. Capture its
        # actual exit code, then restore strict handling for the remainder.
        $previousAction = $ErrorActionPreference
        $pushedRepoLocation = $false
        try {
            # Python -m also considers its current working directory. Invoke
            # from the checked-out repository, not an arbitrary shell folder.
            Push-Location -LiteralPath $repoRoot
            $pushedRepoLocation = $true
            $ErrorActionPreference = 'Continue'
            $parseOutput = @(& py -m lrei.lottery.prize_capture_intake `
                --source-file $originalFile `
                --content-type text/html `
                --draw-id $id `
                --captured-at-utc $fetched.captured_at_utc `
                --historical-csv $historyFile 2> $parserError)
            $parserExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousAction
            if ($pushedRepoLocation) { Pop-Location }
        }
        if ($parserExitCode -eq 0) {
            $asString = $parseOutput -join [Environment]::NewLine
            $candidate = $asString | ConvertFrom-Json
            if ($candidate.draw_id -ne $id -or
                @($candidate.candidate_tiers.regular).Count -ne 8 -or
                @($candidate.candidate_tiers.double).Count -ne 8 -or
                $candidate.auto_promoted_to_prize_observations -ne $false) {
                throw 'Unexpected candidate parser result: refusing promotion or missing prize tiers.'
            }
            $candidateFile = Join-Path $folder ('draw-' + $id + '-quarantine-candidate.json')
            [IO.File]::WriteAllText($candidateFile, $asString + [Environment]::NewLine, $utf8)
            $entry.status = '16_TIERS_QUARANTINED_PENDING_HUMAN_REVIEW'
            $entry.parsed_tiers = 16
        }
        else {
            $entry.status = 'RAW_PAGE_CAPTURED_PARSER_FAILED_REVIEW_ONLY'
            $entry.error = 'The strict offline parser rejected the saved HTML; review private stderr. Do not guess missing rows.'
        }
    }
    catch {
        # Exception messages can include absolute local paths or sensitive
        # fragments. Keep details PRIVATE; the manifest gets only a category.
        $privateErrorFile = Join-Path $folder ('draw-' + $id + '-private-error.txt')
        try { [IO.File]::WriteAllText($privateErrorFile, $_.Exception.ToString(), $utf8) }
        catch { } # Never expose or retry failed captures due to logging errors.
        $entry.error = ($_.Exception.GetType().Name + ': details retained locally; inspect private diagnostics')
        if ($_.Exception -is [System.Net.WebException] -and
            $_.Exception.Response -is [System.Net.HttpWebResponse]) {
            $entry.http_status = [int]$_.Exception.Response.StatusCode
        }
        if ($entry.raw_source_sha256) {
            $entry.status = 'RAW_PAGE_CAPTURED_REVIEW_REQUIRED'
        }
        else {
            $entry.status = 'CAPTURE_FAILED_PRIVATE_REVIEW_ONLY'
        }
    }
    $records.Add([pscustomobject]$entry)
    Write-Host ('Draw ' + $id + ': ' + $entry.status)
    # Fail closed on the first capture or parser failure. Do not probe other
    # pages after a site refusal, timeout, format drift, or parse rejection.
    if ($entry.status -ne '16_TIERS_QUARANTINED_PENDING_HUMAN_REVIEW') {
        Write-Host 'Stopping batch after first unsuccessful page; private manifest will still be written.'
        break
    }
    # Respect the public site's rate; no retries, no parallel crawling.
    if ($id -ne $draws[-1]) { Start-Sleep -Seconds 3 }
}

$completed = @($records | Where-Object { $_.parsed_tiers -eq 16 }).Count
$captured = @($records | Where-Object { $null -ne $_.raw_source_sha256 }).Count
$manifest = [ordered]@{
    schema = 'lrei-p3-private-operator-page-batch-v1'
    status = if ($completed -eq $draws.Count) { 'ALL_CANDIDATES_QUARANTINED_NO_ADMISSION' } else { 'PARTIAL_OR_FAILED_REVIEW_ONLY' }
    script_sha256 = $scriptDigest
    run_completed_at_utc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    draw_ids_requested = @($draws)
    pages_captured = $captured
    draws_with_sixteen_tiers_quarantined = $completed
    rows_approved_for_production = 0
    first_party_source_network_independently_attested = $false
    binding_committee_protocol_verified = $false
    source_use_rights_verified = $false
    eligible_for_play = $false
    research_only_no_play = $true
    captures = @($records.ToArray())
}
$reportPath = Join-Path $folder 'private-capture-manifest.json'
[IO.File]::WriteAllText($reportPath, ($manifest | ConvertTo-Json -Depth 8) + [Environment]::NewLine, $utf8)
Write-Host ('Private evidence directory: ' + $folder)
Write-Host ('Sanitized manifest: ' + $reportPath)
Write-Host ('Captured: ' + $captured + ' / ' + $draws.Count + '; strict tier candidates: ' + $completed + ' / ' + $draws.Count)
Write-Host 'Private original HTML and candidate files must NOT be committed or shared publicly.'
Write-Host 'This is informational operator-page content and never binding approval or permission to play.'