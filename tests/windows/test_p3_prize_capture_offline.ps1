# Offline Windows PowerShell 5.1 behavioral contract for the P3 operator-page pilot.
# NEVER invoke the capture script: doing so would make real HTTP requests.
# Instead parse it and exercise only its fixed draw-selection block.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$scriptPath = Join-Path $repo 'scripts\LREI_capture_pais_p3_prizes_v1.ps1'
$source = [IO.File]::ReadAllText($scriptPath)

# Verify the actual Python import-path assignment is immune to any inherited
# PYTHONPATH. Execute only that one assignment, not the capture script or HTTP.
$pythonPathLines = @($source -split "\r?\n" | Where-Object {
    $_.TrimStart().StartsWith('$env:PYTHONPATH = ', [StringComparison]::Ordinal)
})
if ($pythonPathLines.Count -ne 1) {
    throw 'Expected exactly one isolated PYTHONPATH assignment'
}
$oldPythonPath = [Environment]::GetEnvironmentVariable('PYTHONPATH', 'Process')
try {
    $env:PYTHONPATH = 'C:\untrusted\module\path;'
    $repoRoot = $repo
    & ([ScriptBlock]::Create($pythonPathLines[0]))
    if ($env:PYTHONPATH -cne (Join-Path $repo 'src')) {
        throw ('Ambient PYTHONPATH is still trusted: ' + $env:PYTHONPATH)
    }
}
finally {
    [Environment]::SetEnvironmentVariable('PYTHONPATH', $oldPythonPath, 'Process')
}
if (-not $source.Contains('Push-Location -LiteralPath $repoRoot') -or
    -not $source.Contains('if ($pushedRepoLocation) { Pop-Location }')) {
    throw 'The Python -m working directory is not anchored/restored'
}
Write-Host 'PASS offline P3 isolated local Python import path'

$tokens = $null
$parseErrors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath, [ref]$tokens, [ref]$parseErrors
)
if (@($parseErrors).Count -ne 0) {
    throw ('P3 PowerShell syntax invalid: ' + ($parseErrors | Out-String))
}

# Extract exactly the allowlisted mode-selection block. Never execute the
# script as a whole, invoke network functions, or write source artifacts.
$startMarker = 'if ($FullCohort -and $RemainingCohort) {'
$endMarker = 'if ($RemainingCohort) { $draws = @(3956..3968) }'
$start = $source.IndexOf($startMarker, [StringComparison]::Ordinal)
$end = $source.IndexOf($endMarker, [StringComparison]::Ordinal)
if ($start -lt 0 -or $end -le $start) {
    throw 'Fixed cohort mode selector was not found'
}
if ($source.LastIndexOf($startMarker, [StringComparison]::Ordinal) -ne $start -or
    $source.LastIndexOf($endMarker, [StringComparison]::Ordinal) -ne $end) {
    throw 'Duplicate selector fragments are unsafe'
}
$selectorText = $source.Substring($start, $end - $start + $endMarker.Length)
foreach ($disallowed in @('Read-BoundedOperatorPage', 'Invoke-WebRequest', 'Invoke-RestMethod',
        'Start-Process', 'Remove-Item', 'Set-Content', 'http://', 'https://')) {
    if ($selectorText.Contains($disallowed)) {
        throw ('Unexpected side effect in draw selector: ' + $disallowed)
    }
}
$selector = [ScriptBlock]::Create($selectorText)

function Check-Mode {
    param(
        [bool]$UseFull,
        [bool]$UseRemaining,
        [int[]]$Expected
    )
    $FullCohort = $UseFull
    $RemainingCohort = $UseRemaining
    $draws = $null
    . $selector
    if (-not ($draws -is [array])) {
        throw 'Draw list degraded into a strict-mode-incompatible scalar'
    }
    if ($draws.Count -ne $Expected.Count) {
        throw ('Wrong number of draws: ' + $draws.Count)
    }
    if (($draws -join ',') -cne ($Expected -join ',')) {
        throw ('Wrong draw identifiers: ' + ($draws -join ','))
    }
    # The real pilot crashed only after saving #3955, while writing the report.
    # Verify the manifest's draw-count expressions are safe for one draw too.
    $records = New-Object 'System.Collections.Generic.List[object]'
    foreach ($id in $draws) {
        $records.Add([pscustomobject]@{draw_id = $id; parsed_tiers = 16; raw_source_sha256 = 'synthetic-no-source'})
    }
    $completed = @($records | Where-Object { $_.parsed_tiers -eq 16 }).Count
    $captured = @($records | Where-Object { $null -ne $_.raw_source_sha256 }).Count
    if ($completed -ne $Expected.Count -or $captured -ne $Expected.Count) {
        throw 'Manifest count calculation failed'
    }
    Write-Host ('PASS offline P3 mode: ' + $Expected.Count + ' draws, first=' + $draws[0] + ', last=' + $draws[-1])
}

Check-Mode -UseFull $false -UseRemaining $false -Expected @(3955)
Check-Mode -UseFull $true -UseRemaining $false -Expected @(3955..3968)
Check-Mode -UseFull $false -UseRemaining $true -Expected @(3956..3968)

$FullCohort = $true
$RemainingCohort = $true
$caught = $false
try {
    . $selector
}
catch {
    if ($_.Exception.Message -match 'Choose FullCohort OR RemainingCohort') {
        $caught = $true
    }
}
if (-not $caught) { throw 'Conflicting FullCohort and RemainingCohort flags must fail closed' }
Write-Host 'PASS offline P3 conflicting mode rejection'
Write-Host 'Offline Windows P3 tests succeeded; NO HTTP or prize data were accessed.'