# P1 — Independent-network first-party Lotto source capture (Windows)

**Status: diagnostic/research only. NO PLAY.** This procedure does not approve dataset promotion or prove that any user-uploaded historical file originally came from the operator. Official results may require legally binding draw protocols and human review.

## Why this procedure exists

In GitHub Actions workflow run [#39828460962](https://github.com/igalshih-prog/LREI/actions/runs/39828460962), DNS for `www.pais.co.il` succeeded but TCP/443 timed out. An additional [Windows-hosted attempt #40220138736](https://github.com/igalshih-prog/LREI/actions/runs/40220138736) on 25 Oct 2026 pinned the candidate CSV hash successfully, then DNS succeeded while TCP/443 and the direct first-party download timed out. Its [real refusal/diagnostic artifact](https://github.com/igalshih-prog/LREI/actions/runs/40220138736/artifacts/12608447480) contains no source-attestation report. These failures **do not prove** the operator blocked GitHub's IP ranges. More GitHub-hosted re-runs do not establish source provenance.

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
git clone -c core.autocrlf=false https://github.com/igalshih-prog/LREI.git
Set-Location LREI
# Preserve raw committed candidate CSV bytes on Windows (avoid checkout CRLF conversion).
git config core.autocrlf false
git fetch origin main data/lotto-3976-user-upload-quarantine-20261020
git checkout main
git pull --ff-only origin main

# Create a SEPARATE detached data checkout; do not execute its Python files.
git worktree add --detach ..\LREI-candidate 83285d80fed17fae87a39ab13fe83b087aeb0593

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

**Current quarantined candidate snapshot (25 Oct 2026):** PR #44 commit
`83285d80fed17fae87a39ab13fe83b087aeb0593`, latest candidate draw #3978 (24 Oct 2026),
1,146 rows (#2833–#3978), CSV SHA-256
`1ef641629969d3bb490c2fb0f08dc725c2af21055ec264a4fba789d86fbf8fd5` (38,999 bytes). Verify the exact candidate commit and hash
**before contacting** the operator. Do not silently substitute the previous
#3976 candidate. This hash is an **integrity guard, not provenance proof**.

Earlier 22 Oct 2026 snapshot: commit `5cd4db461ef061e62729e04ed990f9f106ab2574`,
SHA-256 `76527a113d094362cb5595e0cf4719a8bcb6c3f16a988cd75e5ca0e418342b56`, through draw #3976. It remains a **historical
comparison fingerprint only**, not the current target.

## Offline input manifest (before any network request)

Use the trusted `main` package to create a JSON manifest that **refuses** a
modified candidate working file, an unexpected candidate commit/hash, or local
changes to trusted lottery source code. It compares the on-disk CSV with the
**committed Git blob** and never contacts the operator.

For the current pinned PR #44 snapshot, run this command from the
trusted `LREI` directory before running any HTTPS probe:

```powershell
.\.venv\Scripts\python.exe -m lrei.lottery.local_audit_manifest --trusted-repo . --candidate-repo ..\LREI-candidate --expected-candidate-commit 83285d80fed17fae87a39ab13fe83b087aeb0593 --expected-candidate-sha256 1ef641629969d3bb490c2fb0f08dc725c2af21055ec264a4fba789d86fbf8fd5 --report audit-evidence\local-input-manifest.json
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

A failed command may exit with code 2. Save its JSON output and the exit code, without interpreting a successful DNS lookup as a successful HTTPS download. IPv6 may not be available in the environment. Windows Git can convert LF to CRLF; the setup forces `core.autocrlf=false` **before** either checkout, as confirmed necessary by [failed Windows run #40220038806](https://github.com/igalshih-prog/LREI/actions/runs/40220038806). If the pinned bytes still disagree, stop and inspect the checkout rather than bypass the digest.

## Controlled official-URL capture against the candidate

Run the trusted checker from the `main` checkout (it makes its **own first-party HTTPS request**):

```powershell
.\.venv\Scripts\python.exe -m lrei.lottery.operator_full_window_capture --historical-csv ..\LREI-candidate\data\lottery.csv --expected-candidate-sha256 1ef641629969d3bb490c2fb0f08dc725c2af21055ec264a4fba789d86fbf8fd5 --report audit-evidence\operator-full-window-report.json --failure-report audit-evidence\operator-full-window-failure.json
```

The pinned candidate SHA-256 must match the input manifest produced above. The checker makes a private frozen snapshot of those bytes, parses and compares that snapshot, and refuses a success report if the original CSV changes while the HTTPS request is in flight. A checksum match is **not** proof of first-party source provenance.

The exact source endpoint is `https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx`. The verifier accepts only first-party HTTPS URLs, uses standard certificate verification and compares **the full candidate draw window**. Never use a third-party download instead, bypass a failed comparison, or merge the candidate because local download succeeded.

- **Exit 0 and success JSON:** only a first-party HTTPS response/full-window match for those bytes at that point in time, with `dataset_promotion_approved=false` and `requires_human_review=true`. It is **not** proof of the candidate upload's historic download provenance or an approved draw protocol.
- **Exit 2 and failure JSON:** refused/unsupported; no source attestation. Preserve the files and do not merge.
- **No JSON:** check the CLI error and record why even a failure artifact could not be produced. Do not generate fake success evidence.

After the capture, accept only an actual `capture_exit_code=0` **and** a real `operator-full-window-report.json` with last ID **3978**, 1,146 compared rows, zero mismatches, and `dataset_promotion_approved=false` for **research corroboration only**. A workflow or diagnostic success flag alone is not evidence of a downloaded operator CSV. Keep the log, offline input manifest, candidate CSV SHA-256, checker version, and any subsequent JSON artifacts together. Do not publish ID documents or credentials.

## Preserve independent-network evidence (PowerShell)

Use the same trusted Python executable described above. Save the diagnostic output
and exit code before running the capture; do not copy a green status from the
GitHub code checks into a source-attestation report.

```powershell
$python = ".\\.venv\\Scripts\\python.exe"
& $python -m lrei.lottery.operator_https_diagnostic 1> audit-evidence\\operator-network-diagnostic.json 2> audit-evidence\\operator-network-stderr.txt
$diagnosticExit = $LASTEXITCODE
"diagnostic_exit_code=$diagnosticExit" | Set-Content -Encoding ascii audit-evidence\\operator-network-exit.txt

& $python -m lrei.lottery.operator_full_window_capture --historical-csv ..\\LREI-candidate\\data\\lottery.csv --expected-candidate-sha256 1ef641629969d3bb490c2fb0f08dc725c2af21055ec264a4fba789d86fbf8fd5 --report audit-evidence\\operator-full-window-report.json --failure-report audit-evidence\\operator-full-window-failure.json 1> audit-evidence\\capture-stdout.txt 2> audit-evidence\\capture-stderr.txt
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
