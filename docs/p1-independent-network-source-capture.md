# P1 — Independent-network first-party Lotto source capture (Windows)

**Status: diagnostic/research only. NO PLAY.** This procedure does not approve dataset promotion or prove that any user-uploaded historical file originally came from the operator. Official results may require legally binding draw protocols and human review.

**28 October 2026 freshness warning:** the pinned historical PR #44 comparison
snapshot stops at draw **#3978**, while a further draw **#3979** dated
27 October has been reported by secondary sources. The exact-commit/hash
commands in this guide reproduce the **older candidate only**; they do
not constitute a current up-to-date dataset certification. The checker
now explicitly rejects a pinned candidate if its freshly downloaded
operator CSV contains later current-format draw IDs/dates, even if all
older rows compare perfectly. Obtain a freshly reviewed replacement
candidate using trusted operator bytes before asserting recency.
Do not quietly substitute third-party download content or remove this gate.

## UPDATE — 31 October 2026: current source state and next-draw capture (do not run historical pinned commands as if current)

- Current user Windows first-party HTTPS response was captured **2026-10-30 17:52:09 UTC**, final URL `https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx`, HTTP 200, Windows certificate verification enabled. Its raw **183,688-byte** response SHA-256 **`3f6ff3b40bcf4ac26407fe09cdea6ac5c23cac78fffccc847f74e07f848f0074`** agrees with a previously uploaded original CSV by independently computed checksum. This is **source-content corroboration via a user-supplied report**, not a signed third-party network attestation. Preserve the original raw source locally, privately; no protocol or license approval follows from hash equality.
- The current **DRAFT / NO MERGE [PR #44](https://github.com/igalshih-prog/LREI/pull/44)** contains **#2833–#3979**, 1,147 contiguous modeled rows, ending **27 October 2026**; candidate CSV Git blob **`fd1ee320d048afac033f9ea28a4f55da7da195e8`**, SHA-256 **`6843c2e21dc261a00c6bd323638c637bc6a117a6ad5dc1f7bcc303939227ed63`**. PR latest commit **`d23fd21f3ce7cb558921458e2a821bbf86a14c0c`** passed exact-head [Tests #871](https://github.com/igalshih-prog/LREI/actions/runs/41124546059), [UI #63](https://github.com/igalshih-prog/LREI/actions/runs/41124546052) and [browser #8](https://github.com/igalshih-prog/LREI/actions/runs/41124546154), total **7/7** checks. **Passing CI proves code behavior only, not authoritative draw results.**
- The legacy instructions **below are reproducible for the old pinned #3978 snapshot** `83285d80...`, and are intentionally retained as historic evidence. **Do not use the old pinned SHA, #3978 stop condition or the prior `LREI_capture_pais_3979.ps1` exact-match helper to claim that a post-#3979 download failed.** A new draw naturally changes the raw response digest.
- For each **future operator-published draw** (e.g., #3980 when actually published), retain a **new first-party HTTPS byte-for-byte response** from Windows with the **final URL, redirects restricted to `pais.co.il` / `www.pais.co.il`, normal TLS validation, UTC time, SHA-256 and size**, in a new evidence directory. Review source CSV header and 6/37+strong 1–7 draw IDs **jointly with dates**: old 1960s IDs may be numerically higher than modern IDs. Require complete historical overlap with the separately retained last captured source, and list only genuinely new rows. If a past row changed, stop for explicit operator correction review, do not silently rewrite training data.
- The new-capture helper prepared on 31 October is **`LREI_capture_pais_latest.ps1`**, a **standalone uncommitted Windows PowerShell script available as a conversation artifact**; it is **not verified by this repository's Python CI and has not been runtime-tested on Windows**. Review the script's bytes and security behavior before running. No script alone supplies independent signed attestation or replaces operator-approved protocols. Upload only `capture-report.json` first; keep `operator-source-original.csv` private unless a specific comparison needs it.
- **Four-day freshness** remains checked against **current Israel-local calendar date**. A last result from 27 October is *four days old on 31 October*: an updated source may be required immediately after the next draw. Leave `MAX_HISTORY_AGE_DAYS=4` unchanged. **`main` still ends at #3973** and does not inherit candidate freshness until a separate approved, reviewed merge.
- The operator explicitly states on the [public archive](https://www.pais.co.il/lotto/archive.aspx) that online posted results are **nonbinding**, while committee-approved draw protocols are binding. Therefore the existing signed-protocol and rights gate is unresolved, as are P3's 14 missing full 8+8 prize-tier tables. **RESEARCH ONLY / NO PLAY / NO EV CLAIM.**

### After the next verified draw is published

1. Capture new raw bytes from the operator URL and a tamper-evident report, **not** from a third-party mirror. Use a new directory. Do not open the response in Excel or rewrite its encoding.
2. Confirm every earlier modern draw in the previous preserved snapshot is unchanged, and verify the new IDs/dates/results; stop on disagreements. Ensure the source is not newer than the proposed draft candidate and still within four days at review time.
3. Update only an explicitly quarantined candidate **after** source-content review and preserve the exact raw digest. Re-run full CI on the **new exact head**. Keep any candidate DRAFT until operator protocol/rights review and an explicit human promotion decision. Do not auto-merge.
4. Do not infer lower-tier prize observations, manual-player choices, ticket prices, taxes or positive net EV from the downloaded CSV; those require different primary evidence.

---

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
# Fetch the current quarantined PR #44 HEAD explicitly, not an obsolete
# #3976 data branch. The ref is for obtaining candidate BYTES only.
git fetch origin main
git fetch origin +refs/pull/44/head:refs/remotes/origin/pr-44-source-candidate
git checkout main
git pull --ff-only origin main

# Refuse an unexpected PR revision: this procedure is pinned to one commit.
$candidateHead = git rev-parse refs/remotes/origin/pr-44-source-candidate
if ($LASTEXITCODE -ne 0 -or $candidateHead -ne "83285d80fed17fae87a39ab13fe83b087aeb0593") {
    throw "PR #44 changed; STOP and re-review commit, CSV hash and source policy."
}

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

This standalone diagnostic invocation is illustrative; when collecting evidence, run only the comprehensive block below, which already captures this diagnostic and its exit code. A failed command may exit with code 2. Save its JSON output and the exit code, without interpreting a successful DNS lookup as a successful HTTPS download. IPv6 may not be available in the environment. Windows Git can convert LF to CRLF; the setup forces `core.autocrlf=false` **before** either checkout, as confirmed necessary by [failed Windows run #40220038806](https://github.com/igalshih-prog/LREI/actions/runs/40220038806). If the pinned bytes still disagree, stop and inspect the checkout rather than bypass the digest.

## Controlled official-URL capture against the candidate

Run the **single, complete** PowerShell block under **Preserve independent-network evidence** below from the trusted `main` checkout, after the offline manifest succeeds. It executes the trusted `lrei.lottery.operator_full_window_capture` checker exactly once and saves both its native exit code and either a success report or an explicit refusal. Do **not** run a standalone capture first and then the preservation block: the report files are opened in exclusive-create mode and a second attempt with identical output paths will fail rather than overwrite the first evidence.

The pinned candidate SHA-256 must match the input manifest produced above. The checker makes a private frozen snapshot of those bytes, parses and compares that snapshot, and refuses a success report if the original CSV changes while the HTTPS request is in flight. A checksum match is **not** proof of first-party source provenance.

The exact source endpoint is `https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx`. The verifier accepts only first-party HTTPS URLs, uses standard certificate verification and compares **the full candidate draw window**. Never use a third-party download instead, bypass a failed comparison, or merge the candidate because local download succeeded.

- **Exit 0 and success JSON:** only a first-party HTTPS response/full-window match for those bytes at that point in time, with `dataset_promotion_approved=false` and `requires_human_review=true`. It is **not** proof of the candidate upload's historic download provenance or an approved draw protocol.
- **Exit 2 and failure JSON:** refused/unsupported; no source attestation. Preserve the files and do not merge.
- **No JSON:** check the CLI error and record why even a failure artifact could not be produced. Do not generate fake success evidence.

For historical reproducibility, the pinned PR #44 snapshot still expects
last ID **3978** and 1,146 compared rows. However, if the live operator
response includes a later current-format draw (for example #3979),
the checker MUST refuse with `candidate_stale_vs_operator_source`,
exit 2, and no success or raw-copy artifact. **Do not interpret a match to
older rows as an up-to-date source window**. For a newly reviewed candidate,
accept only an actual `capture_exit_code=0`, an equal source/candidate
latest draw, zero mismatches and `dataset_promotion_approved=false`
for **research corroboration only**. A workflow or diagnostic success flag alone is not evidence of a downloaded operator CSV. Keep the log, offline input manifest, candidate CSV SHA-256, checker version, and any subsequent JSON artifacts together. Do not publish ID documents or credentials.

## Preserve independent-network evidence (PowerShell)

Use the same trusted Python executable described above. Save the diagnostic output
and exit code before running the capture; do not copy a green status from the
GitHub code checks into a source-attestation report.

```powershell
$python = ".\\.venv\\Scripts\\python.exe"
& $python -m lrei.lottery.operator_https_diagnostic 1> audit-evidence\\operator-network-diagnostic.json 2> audit-evidence\\operator-network-stderr.txt
$diagnosticExit = $LASTEXITCODE
"diagnostic_exit_code=$diagnosticExit" | Set-Content -Encoding ascii audit-evidence\\operator-network-exit.txt

& $python -m lrei.lottery.operator_full_window_capture --historical-csv ..\\LREI-candidate\\data\\lottery.csv --expected-candidate-sha256 1ef641629969d3bb490c2fb0f08dc725c2af21055ec264a4fba789d86fbf8fd5 --report audit-evidence\\operator-full-window-report.json --failure-report audit-evidence\\operator-full-window-failure.json --raw-copy audit-evidence\\operator-source-original.csv 1> audit-evidence\\capture-stdout.txt 2> audit-evidence\\capture-stderr.txt
$captureExit = $LASTEXITCODE
"capture_exit_code=$captureExit" | Set-Content -Encoding ascii audit-evidence\\operator-capture-exit.txt
```

Capture errors and nonzero exit codes are meaningful evidence. Do not rerun into
the same report paths: successful and failure reports are intentionally created
without overwriting existing evidence. Use a new empty evidence directory for
each further attempt. Retain the input manifest, exact candidate commit and hash,
network diagnostic, both exit codes, stdout/stderr, the **private** original
`operator-source-original.csv` (created only after a full-window match), and
either the success report or the refusal artifact. Independently hash the saved
raw file and require it to equal the success report's
`raw_operator_response_sha256`. The raw file must **not be committed** to GitHub.
A successful live capture corroborates only that response at the capture time;
it does **not** prove that an older uploaded file came from the operator or
that any binding draw protocols were reviewed. Review sensitive logs before sharing; never
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
