# P3: Leave-one-draw-out and rule-regime sensitivity on **existing** data

**29 October 2026; research only; no ticket or financial recommendation.**

## Why this is necessary now

PR #87 found retrospective positive differences between drawn strong **4** and drawn strong **6/7** among the six previously reviewed *operator-display* prize-tier observations #3949–3954. The researcher Polin's publicly published **2018** analysis suggests manual preferences, including strong 4 and 5, and jackpot-dependent participation (https://doi.org/10.1017/S193029750000807X). The user's uploaded historical result archive is already inspected and remains available via the quarantined #44 integrity record; asking for the same data again does not help. The result archive contains **drawn balls, not played numbers**.

A robust scientific workflow must also reveal how easily a post-hoc observation changes when individual draws are removed. These six draws have only **two** strong-4 outcomes, **two** strong-6 and **two** strong-7 outcomes, announced regular first prizes ranging from **NIS 5m to 40m**, and a special prize-allocation notice for draw #3953. They are not a sufficient sample to estimate current crowd preferences or resolve these confounders.

## Clearly descriptive procedure

For each product `regular` / `double` and number of main matches `k in {3,4,5}`:

1. Use the validated **per-draw** strong-hit fraction `r_d = winners(k+strong) / [winners(k+strong)+winners(k)]`, when denominator is nonzero.
2. Calculate **difference of per-draw arithmetic means** (strong-drawn 4 group minus strong-drawn 6-or-7 group), in percentage points, with no ticket pooling.
3. Recalculate after **removing each of the six draws one at a time**. Report the six specific contrasts, min/max and whether all six are positive. Removing one strong-4 draw leaves **one** supporting strong-4 draw: any same-sign result is merely descriptive, not replication or causal identification.
4. Also recompute after excluding only the **special-rule** draw (#3953), only the **lowest announced first-prize** draw (#3954), and both. These exclusions were **chosen after data inspection**, not preregistered. They do not statistically adjust for prizes, payout rules, date, participant mix or selection bias.
5. Never calculate p-values, confidence intervals, fitted manual-entry shares, product-level economic value, a claim that entries are independent, or prospective-validation status.

This read-only code obtains the six existing official-display *information* files through the strict source and identity gates of PRs #84/#87:

`python -m lrei.lottery.draw_omission_sensitivity --directory data/prize_observations`

No new source data, external raw upload, network connection, first-party provenance promotion, speculative jackpot value, or data-file mutation is involved.

## Actual retrospective calculations from six audited observation files

Values in **percentage points**, equal-weighted by draw. These are descriptive results, *not* estimates of improved winning probability:

| Product / main matches | All six draws, 4 minus 6/7 | Min when removing one draw | Max when removing one draw | Exclude rule-change #3953 | Exclude smallest-announced-prize #3954 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Regular, k=3 | +1.080 | +0.964 | +1.196 | +1.040 | +1.115 |
| Regular, k=4 | +1.988 | +1.491 | +2.485 | +2.051 | +2.052 |
| Regular, k=5 | +1.547 | +0.935 | +1.988 | +1.863 | +1.988 |
| Double, k=3 | +1.004 | +0.565 | +1.442 | +0.931 | +1.067 |
| Double, k=4 | +1.001 | +0.407 | +1.594 | +1.065 | +0.923 |
| Double, k=5 | +4.908 | +3.958 | +6.320 | +5.003 | +4.204 |

The k=5 winner entry strata are much smaller and more variable; no inference from apparently larger values is permitted. Six leave-one-out results **all remaining positive** is not six independent discoveries and cannot distinguish the effect of a number from confounded differences in jackpot/participation, product regimes, ticket duplication, or independent source changes.

## What would genuinely move the research forward

- P1 #57: live first-party verified and independently reviewed official historical-results capture, including genuinely **newer** draws; the Oct 24 quarantined candidate #44 is no longer operationally fresh. The official operator email confirmed the public archive route https://www.pais.co.il/lotto/archive.aspx but did not attest prior file origin. **Never bypass** the four-day freshness gate.
- P3-A #18: acquire and retain source evidence for all 14 missing official *eight regular plus eight Double tier* winner/payout tables #3955–3968 (currently 6/20 reviewed), without inventing any values. The historical result CSV alone does not contain winner choices or all prize-tier payouts.
- Freeze a prospective hypothesis before obtaining source-verified future observations **beyond the latest already inspected public draws**, and evaluate at the draw level across all seven drawn-strong outcomes. A valid hypothesis evaluation must specify a separate chronological holdout, exception regimes and minimum sample requirements.
- Only independently verified played-ticket distributions, entry volumes, jackpot sharing, costs/taxes and payout mechanics could support eventual credible **conditional monetary** analysis. Player choices cannot change the physical fair draw odds.

**No promotion of PR #44. No claims of verified 2026 manual number preferences, elevated win chances or positive EV. RESEARCH ONLY / NO PLAY.**
