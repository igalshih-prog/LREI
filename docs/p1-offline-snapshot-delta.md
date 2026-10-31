# P1 — Read-only delta check between two preserved operator exports

**Research only / NO PLAY.** This offline comparison verifies CSV structure and
detects changed or missing historical draw values in two **untrusted** local
source files. It does **not** download, authenticate, certify binding protocols,
approve data use, update the dataset or authorize a monetary claim.

## When to run

After a genuinely new first-party Windows HTTPS capture has actually produced
a new raw operator CSV, retain both original raw files privately. Do not run
against invented draw data, mirrors, Excel-resaved files, or just a JSON report.

The already reviewed 30 October 2026 private Windows capture:
- LREI-source-20261030-175209/operator-source-original.csv
- Raw SHA-256: 3f6ff3b40bcf4ac26407fe09cdea6ac5c23cac78fffccc847f74e07f848f0074
- Reported last draw #3979, 27 October 2026.

A future download may include newer draws; never invent the next result or
assume the number has been officially published.

## Windows PowerShell invocation (after this PR is reviewed/merged)

Use Python 3.11 and the installed trusted LREI package. Set $old to the
preserved 2026-10-30 original and $new to a **later independently captured**
raw source file, then run:

    $old = "$HOME\Downloads\LREI-source-20261030-175209\operator-source-original.csv"
    $new = "<FULL PATH TO LATER CAPTURE>\operator-source-original.csv"
    python -m lrei.lottery.source_snapshot_delta --previous-source "$old" --current-source "$new" --expected-previous-sha256 3f6ff3b40bcf4ac26407fe09cdea6ac5c23cac78fffccc847f74e07f848f0074 --report "$HOME\Downloads\LREI-private-delta-review.json"

The report path must not exist beforehand: the command uses exclusive-create
to preserve old reviews.

## Outcomes and fail-closed conditions

- **NO_NEW_ROWS_CHECK_FRESHNESS**: same known modern draws and first-tier
  winner counts, but no evidence of current freshness.
- **NEW_ROWS_REQUIRES_HUMAN_REVIEW**: every prior row unchanged; newly
  contiguous draw IDs present. This is NOT approval for publication.
- **HISTORICAL_MISSING_OR_CHANGED_STOP_REVIEW**: old draw missing or date,
  six main numbers, strong, or regular/Double first-tier winner counts
  changed. Exit 2 and review any possible operator correction.
- Wrong source header, numbers, dates, duplicate/missing modern IDs, invalid
  jackpot winner counts or old-source digest mismatch: exit 2.
- All report flags for source provenance, signed binding protocol, data
  promotion and financial advantage remain **false**.

The parser requires the actual 12-column original Windows-1255 archive
(including its blank trailing field), and filters contemporary LREI history
with BOTH ID #2833 onward and date on/after 10 October 2016. This is the
LREI rolling research window, **NOT** the 2011 start of 6/37 gameplay.
Historical records like ID 6801 from 1968 must not be treated as newer.

The tool compares the complete modern record sequence from both raw files.
It does not change the training data, 4-day freshness threshold, official
source/rights/protocol acceptance gate, or NO PLAY decision.
