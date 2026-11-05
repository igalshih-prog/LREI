# P3-A.2: private operator prize-page capture pilot (source-blocked research)

> **RESEARCH ONLY / NO PLAY / NO SOURCE ATTESTATION.** This is a *new optional path* to acquire the 14 actual **operator-page originals** for the historical #3955–#3968 cohort when our research browser repeatedly times out. It may not solve reuse rights, signed supervisory-committee protocols or independent TLS/network attestation. Do not bypass blocking, crawl around access controls or continue if the operator's applicable conditions prohibit the intended retrieval/use.

## Why this new path exists

The operator's informational per-draw page `https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=<draw>` includes **eight Regular and eight Double prize tiers** (winner count and payout per winning entry) for a verified example **#3954**. Its current [archive](https://www.pais.co.il/lotto/archive.aspx) has pages for historical draws, but a direct research-browser request for #3955/#3956/#3957/#3958/#3964 timed out or returned access failure. These are **network-access failures**, not evidence the pages do not exist.

A **newly found external research site**, [Sikui](https://sikui.vercel.app/about/), explicitly says it compiled regular, double and Extra prize tiers from each first-party individual-draw page **since January 2018**, so the entire #3955–#3968 study window is likely retrievable. This claim is a **lead**, not the underlying first-party bytes, a republication licence, or independently attested proof. The existing secondary [Lottery Reminder 2026-08 archive](https://israel.lottery-reminder.com/lotto/archive/2026/08) and [2026-09 archive](https://israel.lottery-reminder.com/lotto/archive/2026/09) cover all 14 as an alternative public comparator, but may share one upstream feed.

Do not confuse the four-digit lottery **outcome CSV** (contains dates, numbers and two top-tier winner counts) with the missing **224 Regular+Double tier rows**. Those rows are **14 × (8 Regular + 8 Double)** and cannot be generated from the outcomes CSV.

## Reuse existing strict code instead of inventing data

The trusted `main` code already implements [`lrei.lottery.prize_capture_intake`](../src/lrei/lottery/prize_capture_intake.py) (offline, strict 16-tier extraction from stored original bytes, output **quarantined**) and [`lrei.lottery.source_capture_check`](../src/lrei/lottery/source_capture_check.py) (compare against separately checked observations). This PR adds only a private **one-shot Windows page capture front-end** and static safety tests, not an alternative data importer or a way to turn an unofficial page into a signed draw protocol.

## Windows pilot from the reviewed DRAFT (without changing `main`)

The capture script **does not exist in main yet**: PR #116 remains DRAFT until its exact-head CI and Windows review pass. Therefore **do not run** `main/scripts/LREI_capture_pais_p3_prizes_v1.ps1`, and do not merge the draft just to obtain the file. Use the following explicit **Git-blob-pinned extraction** from the draft. This reads one file, does not check out/switch branches, and refuses a changed script blob before running. Do this only if the official site's current access and personal-use terms allow the intended one-page private retrieval.

Open **Windows PowerShell 5.1** in your existing LREI repository directory (for example `Documents/Codex/LREI`, if that is where your reviewed checkout is). The local `main/data/lottery.csv` must match the pinned historical Git object, and must not contain uncommitted changes:

```powershell
$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$localBranch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $localBranch -ne 'main') { throw 'Run from the existing LREI main checkout.' }
$historyBlob = (git rev-parse 'HEAD:data/lottery.csv').Trim()
if ($LASTEXITCODE -ne 0 -or $historyBlob -ne '3f3d4c28e8973861fa7b1eb54773096c3f0fb459') {
    throw 'Local historical CSV does not match the reviewed approved archive.'
}
git diff --quiet HEAD -- data/lottery.csv
if ($LASTEXITCODE -ne 0) { throw 'Historical CSV has local changes.' }

git fetch origin pull/116/head
if ($LASTEXITCODE -ne 0) { throw 'Could not fetch PR #116.' }
$expectedBlob = '27b1f8ec593e61ed075660df6e4642bb4510329c'
$remoteBlob = (git rev-parse 'FETCH_HEAD:scripts/LREI_capture_pais_p3_prizes_v1.ps1').Trim()
if ($LASTEXITCODE -ne 0 -or $remoteBlob -ne $expectedBlob) {
    throw 'PR #116 capture script changed; require fresh review before execution.'
}

$folder = Join-Path (Join-Path $HOME 'Downloads') ('LREI-P3-pilot-reviewed-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $folder | Out-Null
$zip = Join-Path $folder 'script.zip'
git archive --format=zip --output="$zip" FETCH_HEAD scripts/LREI_capture_pais_p3_prizes_v1.ps1
if ($LASTEXITCODE -ne 0) { throw 'Failed to export script from pinned Git object.' }
Expand-Archive -LiteralPath $zip -DestinationPath $folder
$pilot = Join-Path $folder 'scripts\LREI_capture_pais_p3_prizes_v1.ps1'
$extractedBlob = (git hash-object -- $pilot).Trim()
if ($LASTEXITCODE -ne 0 -or $extractedBlob -ne $expectedBlob) {
    throw 'Extracted script bytes mismatch; do not execute.'
}
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $pilot -RepoRoot $repo
```

Do not post the resulting raw HTML or the 16-tier candidate JSON publicly. For initial troubleshooting share **only** the resulting `private-capture-manifest.json` after inspecting it for local paths or other sensitive content. HTTP/parser failures stop the batch; full exception details are kept in local `draw-<ID>-private-error.txt` or parser-stderr files and **must not be shared or committed**. The script sources the offline parser from this checkout's `src` directory before making a request, rather than importing an unrelated globally installed Python module.

**Only if** the single draw #3955 succeeds, the operator's current site terms allow the intended collection, and a separate review approves expanding the private audit, use the same reviewed `$pilot` and `$repo` variables in the same PowerShell session:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $pilot -RepoRoot $repo -FullCohort
```

Default is exactly **#3955**; no retries, no third-party redirects, default TLS certificate validation, 30-second timeout, 6-MiB page cap. Save the private directory under `Downloads/LREI-P3-private-*`. It produces private `draw-3955-operator-original.html`, a possibly parsed `draw-3955-quarantine-candidate.json`, parser stderr and `private-capture-manifest.json`. **Only the manifest is suitable for sharing for initial triage**, not the HTML or full tier dataset, unless rights and necessity have been reviewed. A parser failure does **not** infer zeros or silently fill prize tiers; preserve the original HTML locally for a reviewed adapter change.

### Private remaining 13 draws, with no duplicate #3955

After the #3955 pilot's private original and candidate match (reported source SHA-256 `dfcac287e19499aa2d0104724dc129efea6b35ee90f1a8889e4ba04326970d85`, 138445 bytes, 8+8 tiers), the optional `-RemainingCohort` mode scopes **exactly #3956–#3968 (13 pages, maximum 208 candidate rows)**. It does not request #3955 again. This source hash is a researcher's local integrity checkpoint, **not** network attestation.

**Do not run an extended capture without confirming that your use is personal/non-commercial, compatible with the operator's current terms, and limited to the private review.** The site permits viewing and downloading for personal non-commercial use but does not thereby grant publication, redistribution, bulk dataset-sharing rights, or an approved committee protocol. Abort on a 403/redirect/timeout/parser mismatch; never evade access restrictions.

Use the **reviewed updated PR script** extracted by the Git-blob-pinned steps above (not the earlier 2026-11-05 copy with the pre-manifest `Count` bug). After exact-head CI and local Windows tests have been checked, in the same PowerShell session as the verified `$pilot` and `$repo`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $pilot -RepoRoot $repo -RemainingCohort
```

This runs at most thirteen fixed operator HTTPS GETs, with 3 seconds between successful pages, no retries and immediate stop at the first failure. Raw HTML and quarantined candidate rows stay privately under `Downloads/LREI-P3-private-*`; share only the sanitized manifest after checking that it contains no private paths. **13 successful captures do not grant permission to import or use 208 values for production/EV.**

The older `-FullCohort` option remains available for a fresh separate study of the entire #3955–#3968 window, but it would redundantly request #3955 here. Do not use both flags together. The `-RemainingCohort` option is the preferred private follow-up in this existing research workflow.

The script uses one public operator URL per draw in ascending order with a fixed 3-second pause, zero parallel fetching, no retries, no changed user-agent secrets and no TLS bypass; it **does not** authenticate the source/session independently, certify a protocol, obtain rights, modify any repository dataset, add an approved observation, change the four-day stale-dataset gate, or authorize a winning/prediction claim. The per-draw private artifacts are never published or sent automatically.

## Offline recovery after the successful #3955 pilot and pre-manifest Count crash (2026-11-05)

The Windows 5.1 pilot at pinned old HEAD `24707e8` reported `16_TIERS_QUARANTINED_PENDING_HUMAN_REVIEW` for #3955 and then threw `PropertyNotFoundStrict: Count` **before writing the final manifest**. The saved original HTML and quarantined candidate were already written. Root cause: `$draws = if (...) { @(...) } else { @(3955) }` is flattened to a scalar for the singleton case. This draft now explicitly retains an array, with a regression assertion. **Do not redownload or use `-FullCohort` to repair the missing report.**

The following read-only network-free recovery checks the existing local original against the private candidate's digest and byte count, verifies exactly 8+8 tier rows and non-promotion, and writes **only sanitized metadata** to the same private folder. It deliberately does not authenticate the network, verify a signed draw protocol, grant reuse rights or export prize tiers. Use PowerShell 5.1:

```powershell
& {
  $ErrorActionPreference = 'Stop'
  $dirs = @(Get-ChildItem -LiteralPath (Join-Path $HOME 'Downloads') -Directory -Filter 'LREI-P3-private-*' |
    Where-Object {
      (Test-Path -LiteralPath (Join-Path $_.FullName 'draw-3955-operator-original.html') -PathType Leaf) -and
      (Test-Path -LiteralPath (Join-Path $_.FullName 'draw-3955-quarantine-candidate.json') -PathType Leaf)
    } | Sort-Object LastWriteTimeUtc -Descending)
  if ($dirs.Count -lt 1) { throw 'No complete private #3955 capture found; stop.' }
  $folder = $dirs[0].FullName
  $original = Join-Path $folder 'draw-3955-operator-original.html'
  $candidatePath = Join-Path $folder 'draw-3955-quarantine-candidate.json'
  $candidate = Get-Content -LiteralPath $candidatePath -Raw -Encoding UTF8 | ConvertFrom-Json
  $sourceHash = (Get-FileHash -LiteralPath $original -Algorithm SHA256).Hash.ToLowerInvariant()
  $sourceBytes = (Get-Item -LiteralPath $original).Length
  $r = @($candidate.candidate_tiers.regular)
  $d = @($candidate.candidate_tiers.double)
  if ([int]$candidate.draw_id -ne 3955 -or $r.Count -ne 8 -or $d.Count -ne 8 -or
    $candidate.auto_promoted_to_prize_observations -ne $false -or
    $candidate.candidate_source.operator_page_claimed_url -ne 'https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3955' -or
    $sourceHash -ne $candidate.candidate_source.sha256_of_actual_supplied_bytes -or
    $sourceBytes -ne [long]$candidate.candidate_source.supplied_byte_count) {
    throw 'Private original/candidate integrity mismatch; stop, do not admit data.'
  }
  $summary = [ordered]@{
    schema = 'lrei-p3-private-offline-reconciliation-v1'
    draw_id = 3955
    status = 'LOCAL_BYTES_MATCH_STRICT_16_TIERS_QUARANTINED'
    source_bytes = $sourceBytes
    source_sha256 = $sourceHash
    captured_at_utc_as_reported = $candidate.candidate_source.captured_at_utc_supplied_by_researcher
    regular_tiers = $r.Count
    double_tiers = $d.Count
    first_party_source_network_independently_attested = $false
    binding_committee_protocol_verified = $false
    source_use_rights_verified = $false
    rows_approved_for_production = 0
    eligible_for_play = $false
  }
  $summaryPath = Join-Path $folder 'private-capture-recovered-summary.json'
  [IO.File]::WriteAllText($summaryPath, ($summary | ConvertTo-Json -Depth 4), (New-Object System.Text.UTF8Encoding($false)))
  Write-Host 'Local offline reconciliation completed (NO SOURCE ATTESTATION)'
  Write-Host ('Sanitized summary: ' + $summaryPath)
  $summary | ConvertTo-Json -Depth 4
}
```

Only share `private-capture-recovered-summary.json` after inspecting it. Do not share the original HTML, candidate prize arrays, parser stderr, private exception logs or local site-session metadata. Retain original bytes unchanged.
## Gate after pilot

- **If 1/1 captured and 16/16 tiers extracted:** review the `private-capture-manifest.json`, confirm draw/date/current source hashing, check top-level page against independently archived draw numbers; then decide on full cohort collection and separately required permissions, signed protocols or evidence policy.
- **If HTTP 403/timeout/redirect:** stop; do not bypass blocking or rotate hosts. Secondary links remain research leads.
- **If original HTML fetched but parser refused:** maintain original bytes and fail-closed. Add a reviewed, *synthetic-test-covered* adapter only after inspecting the saved page privately, never infer missing tiers.
- **If all 14 pages yield candidates:** that is at most **224/224 candidate secondary-like values extracted from purported first-party page bytes**, **not 224/224 admitted records**. Preserve explicit zero admitted until independent provenance and use-rights gates are met. The source pages themselves state that only the supervising committee's accepted protocol has legally binding results.

The official [site terms — especially section 3](https://pais.co.il/info/Term-Of-Use.aspx) expressly allow **viewing/downloading for personal, non-commercial use**, while restricting republication, sharing, copying for commercial or public purposes and other uses without prior written authorization. The [operator's archive disclaimer](https://www.pais.co.il/lotto/archive.aspx) also says that web-displayed results are informational; only committee-approved protocols are binding. This **private personal audit only** does not establish the research project's right to publicly redistribute the pages, source data or derived bulk tables. A third party's public display does not grant such permission. Do not run any retrieval that conflicts with the site's current terms or access controls.

### Legal scope is narrower than "no facts may be researched"

Israeli Copyright Act (2007), [section 5(4)](https://wipolex-res.wipo.int/edocs/lexdocs/laws/en/il/il033en.html), explicitly excludes **facts or data themselves** from copyright protection, although original arrangement/selection of a database can be protected under section 4(b). That does **not** automatically override the operator's website terms, permit publishing full copied webpages, or prove permission to redistribute/repackage a bulk source database. **Practical distinction:** private fact checking of individually displayed winning counts/payouts is different from publishing a source site's whole page or data compilation. Publication/commercial use and contractual constraints require separate legal review. No legal approval or project admission gate has been changed.
