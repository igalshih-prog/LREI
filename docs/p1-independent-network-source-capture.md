# P1 — Independent-network first-party Lotto source capture (Windows)

**Status: diagnostic/research only. NO PLAY.** This procedure does not approve dataset promotion or prove that any user-uploaded historical file originally came from the operator. Official results may require legally binding draw protocols and human review.

## Why this procedure exists

In GitHub Actions workflow run [#39828460962](https://github.com/igalshih-prog/LREI/actions/runs/39828460962), DNS for `www.pais.co.il` succeeded but TCP/443 to the selected IPv4 address timed out. The original HTTPS CSV download independently timed out. The same outcome does **not** prove that the operator blocked GitHub's IP ranges. Re-running unchanged CI from the same network does not establish source provenance.

This is a **separate network-path experiment**: run the repository's already trusted first-party HTTPS downloader from a personally controlled Windows machine/network. Do not download a CSV from search mirrors, screenshots, email attachments or any third-party domain and relabel it as operator evidence.

## Prerequisites

- Git and Python 3.11 installed; use PowerShell on your own Windows PC.
- Use the existing public repository and its trusted `main` code. Never install or execute code from the quarantined candidate branch.
- Keep the machine's certificate verification enabled. Do not disable TLS validation, add `verify=False`, disable firewalls or use undocumented proxies.
- The candidate file is **comparison data only**, never trusted evidence of its own origin.
- No payment, ID document or credentials are required to run this local diagnostic. This is separate from the official freedom-of-information request.

## Reproducible setup

From PowerShell in a directory you control:

```powershell
git clone https://github.com/igalshih-prog/LREI.git
Set-Location LREI
# Preserve raw committed candidate CSV bytes on Windows (avoid checkout CRLF conversion).
git config core.autocrlf false
git fetch origin main data/lotto-3976-user-upload-quarantine-20261020
git checkout main
git pull --ff-only origin main

# Create a SEPARATE detached data checkout; do not execute its Python files.
git worktree add --detach ..\LREI-candidate origin/data/lotto-3976-user-upload-quarantine-20261020

py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
New-Item -ItemType Directory -Force audit-evidence | Out-Null
```

Check the exact checked-out candidate and the code used:

```powershell
git rev-parse HEAD
git -C ..\LREI-candidate rev-parse HEAD
Get-FileHash ..\LREI-candidate\data\lottery.csv -Algorithm SHA256
```

At the original 2026-10-22 audit, the candidate was commit
`5cd4db461ef061e62729e04ed990f9f106ab2574` and its CSV SHA-256 was
`76527a113d094362cb5595e0cf4719a8bcb6c3f16a988cd75e5ca0e418342b56`.
These are **historical comparison fingerprints**, not official provenance attestations.
If hashes differ, record the difference and do not attribute results to the earlier candidate.

## Offline input manifest (before any network request)

Use the trusted `main` package to create a JSON manifest that **refuses** a
modified candidate working file, an unexpected candidate commit/hash, or local
changes to trusted lottery source code. It compares the on-disk CSV with the
**committed Git blob** and never contacts the operator.

For the previously quarantined PR #44 snapshot, run this command from the
trusted `LREI` directory before running any HTTPS probe:

```powershell
.\.venv\Scripts\python.exe -m lrei.lottery.local_audit_manifest --trusted-repo . --candidate-repo ..\LREI-candidate --expected-candidate-commit 5cd4db461ef061e62729e04ed990f9f106ab2574 --expected-candidate-sha256 76527a113d094362cb5595e0cf4719a8bcb6c3f16a988cd75e5ca0e418342b56 --report audit-evidence\local-input-manifest.json
```

The command returns **exit 2** rather than creating an approval report if the
working bytes or commit differ. Review `local-input-manifest.json` alongside
any subsequent capture report, and do not overwrite it. The manifest records
the trusted checkout commit and candidate fingerprints, **not** proof of
official operator publication, human review, or authorization to use the data.

## Independent network diagnostics

```powershell
.\.venv\Scripts\python.exe -m lrei.lottery.operator_https_diagnostic
```

A failed command may exit with code 2. Save its JSON output and the exit code, without interpreting a successful DNS lookup as a successful HTTPS download. IPv6 may not be available in the environment.

## Controlled official-URL capture against the candidate

Run the trusted checker from the `main` checkout (it makes its **own first-party HTTPS request**):

```powershell
.\.venv\Scripts\python.exe -m lrei.lottery.operator_full_window_capture --historical-csv ..\LREI-candidate\data\lottery.csv --expected-candidate-sha256 76527a113d094362cb5595e0cf4719a8bcb6c3f16a988cd75e5ca0e418342b56 --report audit-evidence\operator-full-window-report.json --failure-report audit-evidence\operator-full-window-failure.json
```

The pinned candidate SHA-256 must match the input manifest produced above. The checker makes a private frozen snapshot of those bytes, parses and compares that snapshot, and refuses a success report if the original CSV changes while the HTTPS request is in flight. A checksum match is **not** proof of first-party source provenance.

The exact source endpoint is `https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx`. The verifier accepts only first-party HTTPS URLs, uses standard certificate verification and compares **the full candidate draw window**. Never use a third-party download instead, bypass a failed comparison, or merge the candidate because local download succeeded.

- **Exit 0 and success JSON:** only a first-party HTTPS response/full-window match for those bytes at that point in time, with `dataset_promotion_approved=false` and `requires_human_review=true`. It is **not** proof of the candidate upload's historic download provenance or an approved draw protocol.
- **Exit 2 and failure JSON:** refused/unsupported; no source attestation. Preserve the files and do not merge.
- **No JSON:** check the CLI error and record why even a failure artifact could not be produced. Do not generate fake success evidence.

Keep the log, offline input manifest, candidate CSV SHA-256, checker version, and any subsequent JSON artifacts together. Do not publish ID documents or credentials.

## Preserve independent-network evidence (PowerShell)

Use the same trusted Python executable described above. Save the diagnostic output
and exit code before running the capture; do not copy a green status from the
GitHub code checks into a source-attestation report.

```powershell
$python = ".\\.venv\\Scripts\\python.exe"
& $python -m lrei.lottery.operator_https_diagnostic 1> audit-evidence\\operator-network-diagnostic.json 2> audit-evidence\\operator-network-stderr.txt
$diagnosticExit = $LASTEXITCODE
"diagnostic_exit_code=$diagnosticExit" | Set-Content -Encoding ascii audit-evidence\\operator-network-exit.txt

& $python -m lrei.lottery.operator_full_window_capture --historical-csv ..\\LREI-candidate\\data\\lottery.csv --expected-candidate-sha256 76527a113d094362cb5595e0cf4719a8bcb6c3f16a988cd75e5ca0e418342b56 --report audit-evidence\\operator-full-window-report.json --failure-report audit-evidence\\operator-full-window-failure.json 1> audit-evidence\\capture-stdout.txt 2> audit-evidence\\capture-stderr.txt
$captureExit = $LASTEXITCODE
"capture_exit_code=$captureExit" | Set-Content -Encoding ascii audit-evidence\\operator-capture-exit.txt
```

Capture errors and nonzero exit codes are meaningful evidence. Do not rerun into
the same report paths: successful and failure reports are intentionally created
without overwriting existing evidence. Use a new empty evidence directory for
each further attempt. Retain the input manifest, exact candidate commit and hash,
network diagnostic, both exit codes, stdout/stderr and either the success report
or the explicit refusal artifact. Review sensitive logs before sharing; never
publish ID documents, credentials, authentication tokens or private network data.

A successful *diagnostic* still does not authenticate results. Even a successful
full-window report does not automatically approve the dataset or change the
freshness gate, which remains tied to the actual Israel-local date.

## Decision gate

1. A reproducible full-window match is necessary for source corroboration, not sufficient for promotion.
2. Independently obtain and review the appropriate operator-approved protocol/rights as needed; economic work also requires verified full prize-tier payouts.
3. Only a separate human source review and explicitly satisfied freshness/provenance gates may authorize any dataset promotion. Never bypass the 4-Israeli-calendar-day recency gate.
4. PR #44 stays **draft and unmerged** until those conditions are met. Historic research has found **no demonstrated predictive advantage**. **NO PLAY**.

Useful artifacts: [manual failing run #39828460962](https://github.com/igalshih-prog/LREI/actions/runs/39828460962), [candidate manifest and refusal evidence](https://github.com/igalshih-prog/LREI/actions/runs/39828460962/artifacts/12448080996).
