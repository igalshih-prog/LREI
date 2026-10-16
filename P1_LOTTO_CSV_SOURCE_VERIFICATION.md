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
