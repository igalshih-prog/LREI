# LREI P3-A.2 — retrospective prize evidence, with explicit gaps

**Status:** 3 of 20 consecutive target draws present, 17 missing.
This is a deliberately INCOMPLETE data-collection stage, **not an economic
advantage**, not a winning-number predictor, and not a prospective test.

## Operator-sourced pilot

| Draw | Date | Main numbers | Strong | Both 8-tier tables | Operator page |
|---|---|---|---|---|---|
| 3949 | 2026-07-25 | 8,14,20,25,26,34 | 6 | Manually reviewed | https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3949 |
| 3950 | 2026-07-28 | 1,8,9,19,21,23 | 7 | Manually reviewed | https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3950 |
| 3951 | 2026-08-01 | 12,14,16,18,32,33 | 4 | Manually reviewed | https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3951 |

All three are cross-checked against the existing 1,141-draw archive.
Published figures for regular/double ticket winnings and advertised prizes
were transcribed manually. **We have not archived the underlying HTML bytes.**
Therefore there is no claim of an HTML capture SHA-256, trusted source timestamp,
or legally approved draw protocol. The source manifest expressly records these
as \`null\`/\`false\`. Git commits establish the time of **our recorded
transcriptions**, not the authenticity of the operator's earlier source page.

**The page itself explicitly states that display results are informational,
not legally binding.** Only the supervisory committee's approved draw
protocol is legally binding.

This source display also lists separate **Extra** payouts. The reported
all-games total does NOT equal the two Lotto-tier table sums. For example,
draw 3949:
- Lotto+Double table aggregate: **6,681,465 ILS**
- Operator all-games total: **7,646,745 ILS**
- Difference: **965,280 ILS**

The residual is recorded as an **unattributed accounting difference**, NOT
automatically presumed to be Extra, refunds, taxes or net profit.

## Why we intentionally do not backfill the rest with guesses

The target window is draws **3949 through 3968**, inclusive. The manifest
tracks the complete expected sequence. The first 3 have human-reviewed
operator page values; draws **3952–3968** are explicitly reported as
missing until all **16 tier rows** and advertised totals are verified for
each. No fabricated zero counts, 2026 sales data, actual played combinations,
taxes or payout model assumptions.

## Run the full offline audit

\`\`\`bash
python -m lrei.lottery.prize_series_audit \
  --observations-dir data/prize_observations \
  --manifest data/prize_audit/3949-3968.manifest.json \
  --historical-csv data/lottery.csv
\`\`\`

Output includes observed count, 17 missing IDs, six+strong draw integrity
checks, SHA-256 of canonical **observation** records, per-game accounting,
gross published all-games total, source-manifest coverage, and conservative
\`eligible_for_financial_prediction: false\`.

Add \`--require-complete\` to fail the process until the full target window
is populated, rather than silently treating 3 draws as a 20-draw sample.

Run the regression suite:

\`\`\`bash
python -m pytest -q tests/lottery/test_prize_data.py tests/lottery/test_prize_series_audit.py
\`\`\`

## Next predeclared step

Obtain operator-approved bulk access/export or manually and transparently
verify each remaining consecutive draw **3952–3968**, with fixed row format,
source page and timestamps. For future improvement, archive original
authoritative files/HTML where permitted and store **actual** content hashes,
rather than inventing them. Keep the status visibly incomplete if original
records cannot be verified.

Before P3-B economic modelling, review how rule changes, game sales, co-winner
counts and tax affect final per-ticket payout. Published prize counts are NOT
the same as number of purchased tickets.

References:
- [MASTER PLAN #7](https://github.com/igalshih-prog/LREI/issues/7)
- [P3-A.2 tracking issue #9](https://github.com/igalshih-prog/LREI/issues/9)
- [Original P3 economics research #6](https://github.com/igalshih-prog/LREI/issues/6)
