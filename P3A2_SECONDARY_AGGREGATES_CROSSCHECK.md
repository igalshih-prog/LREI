# P3-A.2 — 2 independent secondary payout totals are NOT paid-tier data

**Primary sample progress is unchanged: six operator-display prize records
of twenty draws; fourteen #3955–3968 still missing complete 16-tier tables.**

## Why compare two secondary sites at all?

One archived web view, https://lottohistory.co.il/, presents a
lottery-game-only aggregate for the following draw numbers.
Another independent site, https://www.paisresults.co.il/index.php,
presents a larger aggregate of total winnings. Neither is the legally
approved draw protocol nor the full operator prize tier table.

The two reported sets differ by:

| Draw | Secondary Lotto-only total (₪) | Other secondary overall reported total (₪) | **Unexplained** difference (₪) |
|---|---:|---:|---:|
| 3955 | 4,496,223 | 4,948,528 | 452,305 |
| 3956 | 20,428,062 | 20,902,707 | 474,645 |
| 3957 | 13,995,056 | 14,595,891 | 600,835 |
| 3958 | 5,981,873 | 6,521,948 | 540,075 |

The Lotto-only labeling is provisional and based on how the secondary
source presents the sum. The difference **must not automatically be
labeled Extra prizes, taxes, customer revenue, or net profit**.

Both sources were consulted on **14 Oct 2026**, but raw HTML bytes were
**not archived** and therefore there is no genuine raw-source checksum
or authoritative certification. The reported amounts are only
*research leads*. A match on date/number is not prize verification.

## Data integrity

Source evidence: `data/prize_leads/lotto_only_aggregate_crosscheck_3955_3958.json`
paired with the existing
`data/prize_leads/pending_3955_3968.json`.

The new offline cross-check module:
`src/lrei/lottery/prize_aggregate_crosscheck.py`
validates source labels, consecutive draw IDs, date alignment to
independently archived results, positive integers, nonnegative
difference and **explicitly null** payout tier tables.

All computed results say:

- `operator_verified: false`
- `eligible_for_prize_observation: false`
- `eligible_for_expected_value: false`
- `missing_eight_tier_tables_still: [3955, ..., 3968]`

This is an *accounting reconciliation of two public secondary reports*,
not validation of either report by the operator. It does not alter the
main `data/prize_observations` files or raise the 6/20 completion count.

## Next actual step, without shortcuts

Request the **16 winning-entry and per-entry paid amounts for each draw**
from Mifal HaPais using the official data request draft
`P3A2_OFFICIAL_DATA_REQUEST_HE.md`.
No such request has been sent in this project yet.

Use the merged offline source-capture/quarantine tools only after
obtaining legitimate operator source bytes. Run source integrity and
human verification before moving any record to the audited corpus.
The official site currently exposes draw outcomes CSV but no
confirmed downloadable complete 16-tier payout archive for the missing
dates, and attempts to open draw #3955/#3956 detail pages timed out.

No purchase suggestions or positive-EV claims follow from this work.
