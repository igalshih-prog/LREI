# P1 Lotto CSV source verification — CI and release gate

This project deliberately separates **deterministic code correctness** from
**external data provenance**. A red HTTP timeout from the lottery operator is
not a failing parser regression. Conversely, green unit tests are **not**
confirmation that a downloaded file is genuine or legally binding.

## Workflows

- Pull requests run `P1 Lotto CSV source parser (offline)`: tests the
  local parser without contacting external websites.
- `optional-first-party-capture` is intentionally restricted to a
  manually triggered workflow dispatch. Direct operator HTTPS download may
  fail because of operator availability, network blocking, or timeout.
- A dispatch success records only a candidate raw-file match. It is not a
  commission-approved draw protocol or permission to auto-merge.
- A failed dispatch means **no first-party network evidence was acquired**.
  Do not mark it as successful, skip provenance review, or fabricate a hash.

Until the workflow file is on the repository default branch, direct manual
CLI verification is the supported immediate route for the PR.

## Offline verification of a user-supplied CSV

Download the full results export using the operator's archive page in a
trusted browser and retain the original bytes, original URL, download time,
and download method. Never reconstruct a supposed raw operator file from
a CSV in this repository.

For a CSV stored outside this public repository:

```bash
python -m lrei.lottery.official_draw_source \
  --source-file "/path/to/Lotto(3).csv" \
  --historical-csv data/lottery.csv \
  --draw-id 3974 \
  --report /secure/audit/draw_3974_report.json
```

The report includes the SHA-256 digest of the actual source bytes, draw
identity/date/numbers/strong consistency, plus
`direct_https_download_performed_by_tool=false` and
`legally_binding_protocol_verified=false`. It **does not establish the
file's origin**. It is acceptable to record an offline content match with
an explicitly unverified acquisition provenance, but **not** to set
`source_authenticity_verified=true` solely based on metadata or a checksum.

## Recorded upload — 15 October 2026

A user-provided file called `Lotto(3).csv` was inspected locally:

- Raw size: **183,478 bytes**.
- SHA-256: `befd18352e7acf3c5692e2200ab683ac0e434b90ec1050b6fe0bd4c737143f93`.
- Encoding: Windows-1255; 4,550 CSV data records.
- The file contains exactly one row for draw **3974**, dated
  **13/10/2026**, main **03,04,18,19,34,35**, strong **2**.
- Conversion of draws 2834–3974 into LREI's tab-delimited ascending
  format produces an exact Git blob identity:
  `2c538bd31a8653e4d2de39c14e9feef867a2abf3`
  (the file in this PR). Every one of the 1,141 rows matches.
- Extra archive winner-count columns do not provide all 16
  regular/Double Lotto prize-tier payouts.

This is a **content match, not proof of download provenance**. The raw
user-uploaded file is not published here. The first-party GitHub runner's
direct CSV download timed out in
[Actions run 38763991842](https://github.com/igalshih-prog/LREI/actions/runs/38763991842);
that red run accurately records an unresolved source-access check.

## Release decision

Keep draft PR #25 unmerged until all current-code CI checks pass **and**
operator-source provenance has been independently checked and reviewed.
Store the acquisition evidence in an authorized safe location. An
informational source check does not verify the legally binding approved
draw protocol. The already published draw 3974 cannot be counted as a
prospective prediction. P3-A.2 remains 6/20 audited payout observations.


## 17 October 2026 — code-only independent release (separate from PR #25)

This source-audit checker is being extracted for independent CI/review, **without** the unverified draw #3974 CSV update in [PR #25](https://github.com/igalshih-prog/LREI/pull/25). Its new workflow, `P1 Operator Lotto CSV source audit (manual, code only)`, separates:
- PR-time **offline synthetic parser tests**, which do not claim first-party publication.
- **manual** `workflow_dispatch` source capture after code lands on `main`. The operator request uses trusted `main` code, and checks the last draw ID actually found in either `main`'s history or a *read-only candidate copy* of PR #25's history. Candidate branch code is NEVER executed and candidate data is NEVER merged by this workflow.
- A successful capture may provide a genuine HTTPS response location, timestamp, byte count and SHA256 in a temporary audit artifact, **not** commission-approved protocol or automatic permission to promote data. Operator rights/reuse still require human review. Original raw response is not uploaded to public artifacts by default.
- If direct HTTPS capture times out, the manual job MUST remain **RED**. No synthetic or secondary result is substituted.

To preserve a legally authorized raw response for later independently reproducible verification, retrieve/store the original bytes in a permitted private location and record the exact checksum together with acquisition details. The success of an offline parser never upgrades the recorded source gate to green.

## 17 October 2026 — full-window authenticated network-response audit

Following the independently merged source parser [PR #28](https://github.com/igalshih-prog/LREI/pull/28), the manual-only workflow has been upgraded from checking **only the candidate's latest draw** to reconciling **every draw in the candidate's historical window against a single first-party TLS download**. This is a fail-closed requirement: if even one ID is missing, duplicated, date/strong/main mismatched, or the operator host redirects outside the permitted domain, the workflow returns RED.

After a successful first-party request, the `operator_full_window_capture` tool records the effective operator HTTPS URL, response MIME, post-response UTC capture timestamp, real byte count and SHA-256, CSV source row count, target first/last draw IDs and number compared. It publishes a **report only**, not original operator CSV bytes, as a 30-day Actions artifact. The candidate file in PR #25 is read-only for the comparison; its source code is not executed and it is never merged automatically.

**Manual operation after code has been merged to main:**
1. Open [GitHub Actions: P1 Operator Lotto CSV source audit](https://github.com/igalshih-prog/LREI/actions/workflows/p1-operator-csv-audit.yml).
2. Choose **Run workflow**, branch `main`, and select `source-gated-pr25` to compare every one of the 1,141 uploaded candidate history rows against the operator's **newly acquired** response. Alternatively choose `main` to audit the currently committed older window.
3. Inspect the `optional-real-operator-capture` job. A timeout, access refusal, HTML payload or mismatch is **RED**; the offline test being green does not override it.
4. If it completes, download the **audit report**, verify SHA/URL/IDs/row counts, and separately review operator source rights and whether an approved committee protocol is available.

The JSON must still mark `historical_download_provenance_of_user_upload_proven=false`, `legally_binding_commission_protocol_verified=false` and `dataset_promotion_approved=false`. A live operator export agreeing with candidate bytes gives strong present-time content corroboration **but does not prove how the old user-uploaded file was originally acquired**. No payout amount, official prize table, true expected value or predictive advantage is established by this workflow.
