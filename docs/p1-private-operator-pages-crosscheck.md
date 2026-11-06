# P1 — Private official CSV ↔ per-draw operator-page crosscheck

Research-only, **NO PLAY**, **NO DATA PROMOTION**, **NO SIGNED PROTOCOL ATTESTATION**.

## New evidence, not another rehash

The project already preserves a separate original operator CSV export through #3981 on the researcher's Windows computer. This one-shot tool requests **exactly eight individual draw-result HTML pages #3974–3981 from the operator host** and checks each against the *pinned, separately retained* CSV original. The output tests date, six main numbers, strong number and both first-prize winner counts. In addition, it parses 16 Regular/Double payout tiers and five Extra tiers from each official page, and requires their calculated total to match the printed all-games source total.

**Why this matters:** two operator-hosted *endpoints* matching is a different cross-endpoint test from comparing a CSV to itself, and can catch transcription/draw-ID/count errors. Both endpoints may share one upstream database and neither is the **legally binding signed protocol**. This is neither independent network attestation nor authorization to republish source data.

## Security and use restrictions

- The original CSV remains private, and eight successful original HTML copies are retained in a new unique private directory under Downloads. Never commit or publish them.
- Certificate verification stays enabled; HTTP 200, exact official URL and HTML Content-Type required. No redirects, no retries, no host changes, a bounded 6 MiB page limit and a three-second interval.
- On a single timeout, 403, redirect, changed layout or inconsistency, STOP immediately. A sanitized local manifest records only completed checks; it does not override any status or make any data admissible.
- The existing Windows capture source is date-pinned at #3981 (3 November 2026). This is a **historical retrospective crosscheck** only. On or after a new draw, it does NOT establish a current four-day freshness or enable any live recommendation.
- Confirm the current [operator terms](https://pais.co.il/info/Term-Of-Use.aspx) are compatible with your personal noncommercial review. This tool does not grant rights to publicly republish the site's archives.

## Command (only after reviewed code is merged into main)

Windows PowerShell in the local reviewed checkout:

```powershell
$ErrorActionPreference = 'Stop'
$repo = "$HOME\Documents\Codex\LREI"
Set-Location $repo
if ((git branch --show-current).Trim() -ne 'main') { throw 'Wrong branch' }
git diff --quiet HEAD --
if ($LASTEXITCODE -ne 0) { throw 'Local changes: stop' }
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw 'Update refused' }
$oldPath = $env:PYTHONPATH
try {
  $env:PYTHONPATH = Join-Path $repo 'src'
  py -m lrei.lottery.p1_private_operator_page_crosscheck `
    --source-csv "$HOME\Downloads\LREI-source-20261106-134858-755\operator-source-original.csv" `
    --source-sha256 '0034509bdfa510c3978abcff14baee705f6bebf85701c7e6978ac07ecc171560' `
    --private-root "$HOME\Downloads"
  if ($LASTEXITCODE -ne 0) { throw 'Cross-endpoint audit refused; keep source private' }
}
finally { $env:PYTHONPATH = $oldPath }
```

Expected successful output *only if eight actual official pages compare successfully*: eight draws, 16 matching jackpot winner counts, 128 Regular+Double rows parsed, 40 Extra rows parsed and eight page-total arithmetic matches. This is not a pre-existing result or an assurance the operator will accept the HTTP requests. Share **sanitized summary only**; keep originals and full private manifest out of public GitHub.

No replacement of data/lottery.csv, PR #44 (DRAFT/NO MERGE), prospective ledger entries, or four-day freshness logic is permitted by this work.
