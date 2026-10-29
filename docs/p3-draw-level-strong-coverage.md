# P3: Draw-level replication and coverage audit for conditional strong matches

**29 October 2026 — exploratory, source-gated, research only. NO PLAY.**

## Decision: extract defensible information from the data already in the repository

We already have a user-supplied historical CSV fully checked for **content/row integrity**, and six source-gated **operator-display** prize observations (#3949–3954) with all eight regular + eight Double prize-tier counts. **Do not ask for a duplicate archive upload**. The unmerged quarantined candidate #44 extends the winning-outcome archive to #3978, but its independent operator acquisition provenance is not verified and it is already stale as of Oct 29. Drawing outcomes **are not player selections**; we cannot infer player preferences from the historical draw CSV.

This audit works solely with the six reviewed winner-count observations, and with the published 2018 research of Polin, Ben Isaac & Aharon (2021), https://doi.org/10.1017/S193029750000807X , as historical context. The researcher's 2026-10-29 non-confidential email identified two unknowns: how many selections were manual and their full distribution. The published report finds historically favored strong numbers 4/5 and disfavored 1; no 2026 transfer is authorized by that evidence.

## Scientifically sound unit of observation

For fixed observed draw `d`, lottery product `p`, main match class `k`:

`r(d,p,k) = winners(k+strong) / (winners(k+strong) + winners(k))`.

An entry with 3 main matches and the strong number is in a different disjoint tier from 3 matches without strong. Under **uniform independent player strong-number selection**, the theoretical conditional reference is `1/7`. It is **not** the expected empirical ratio under unknown human choice conditional on the realized draw.

When summarizing across multiple draws with the same drawn strong number, report a **simple unweighted mean of per-draw fractions** (each draw counted at most once). Do **not** pool ticket counts or treat entries, products, or match tiers as independent experiments. Zero observed entries in a match class produce `null` rather than zero preference; no confidence intervals or p-values are justified from six non-independently-verified draws and unknown ticket dependence.

The new Python CLI uses only the source-gated audit of PR #84:

`python -m lrei.lottery.reviewed_strong_draw_profile --directory data/prize_observations`

It separately reports regular and Double and **k=3,4,5**. The k=6 category is too sparse for useful grouping (zero denominators), and k=5 is marked as sparse/descriptive only. No data files are modified.

## Actual six-draw descriptive observation

**Exactly two reviewed draws per observed strong number**: strong **4** on draws #3951/#3952, **6** on #3949/#3954, **7** on #3950/#3953. The dataset contains **no** draw with strong **1, 2, 3 or 5**. Thus it cannot test the historical claim that strong 1 was least popular or strong 5 was popular.

Unweighted across two draws, the *observed entry-share of matching strong* within the exact k=3 main-match category is:

| Drawn strong | Regular | Double |
| ---: | ---: | ---: |
| 4 | 15.08% | 14.87% |
| 6 | 14.02% | 13.90% |
| 7 | 13.98% | 13.84% |
| independent-uniform reference | 14.29% | 14.29% |

For strong **4** compared with the four draws with strong **6 or 7**, the exploratory *difference between equally weighted per-draw means* is approximately:

| Main matches k | Regular difference (percentage points) | Double difference (percentage points) |
| ---: | ---: | ---: |
| 3 | +1.08 | +1.00 |
| 4 | +1.99 | +1.00 |

## Existing advertised-prize and special-regime confounders

The same six operator-display observations also contain **advertised** top-prize figures (not actual sales, payouts, or the number of manual tickets). They vary substantially:

| Draw | Drawn strong | Advertised regular first prize (ILS) | Special rule noted |
| ---: | ---: | ---: | :--- |
| 3949 | 6 | 30,000,000 | no |
| 3950 | 7 | 32,000,000 | no |
| 3951 | 4 | 35,000,000 | no |
| 3952 | 4 | 40,000,000 | no |
| 3953 | 7 | 40,000,000 | **yes**: secondary-prize allocation notice |
| 3954 | 6 | 5,000,000 | no |

This difference in jackpot regimes may itself affect participation and selected-number distributions, as the historical paper suggests; the announced secondary-prize regime for #3953 adds a further contextual distinction. Six observational draws cannot statistically separate a strong-number preference from jackpot participation, payout-regime, temporal, or selection effects. The read-only report explicitly exposes the numbers and flags **`jackpot_and_rule_confounding_not_adjusted=true`**. No model coefficients are fitted and no relative profitability is inferred.

These contrasts arose from **already inspected data** and are NOT preregistered, statistically significant, independently reproduced, or evidence that a particular choice will earn more money. Regular and Double winners are not guaranteed to be independent groups. Other strong numbers and participation dynamics are unobserved here, and winner-entry counts may include duplicates. If the operator-display pages change, an independently archived original would be necessary for source comparison.

## Enforced data-coverage and reporting gates

The code:
- Requires precisely the six reviewed draw IDs in order, distinct dates, valid drawn strong numbers, both products and count-derived fractions; no ingestion of any quarantined #3955–3968 or candidate #44 data.
- Reports **zero coverage** explicitly for strong 1, 2, 3 and 5; never silently imputes their rates.
- Computes simple draw-level means, not sales-weighted or entry-pooled estimates. Preserves each grouping's number of supporting draws and range.
- Rejects corrupted counts, duplicates, missing source-status flags and altered fractions rather than reporting apparent preference.
- Hard-sets no source provenance attestation, no fitted 2026 player popularity, no valid chronological holdout, no claim of significance or financial benefit, and `authorized_for_play=false`.

## High-value next steps, contingent on genuinely NEW evidence

1. **P1 source authenticity:** main historical draw results currently stale, and the user's last uploaded file is already reconciled by content; do not ask for it again. Obtain a timestamped independent first-party TLS capture of an **actually newer** operator response, not another copy of an existing file. Retain raw SHA-256 and have a human review applicable binding draw protocols. Operator public enquiries explicitly referred us to https://www.pais.co.il/lotto/archive.aspx ; this is a public navigation lead, **not** cryptographic proof of the upload's original acquisition.
2. **P3-A prize-tier coverage:** the official public archive does not itself establish full 8+8 tier payout histories. Obtain the missing #3955–3968 page originals or legally releasable source documents. Until then, the reviewed set remains 6/20.
3. **Prospective falsification:** freeze a *forward-only* hypothesis and source/version requirements BEFORE examining unseen independent verified later draws, including strong 1 and 5. Evaluate at draw level and test sensitivity to jackpot regime; 2018 participant biases and jackpot-related uniformity change are **hypotheses**, not 2026 fitted parameters.
4. **Conditional financial value:** cannot proceed without verified ticket-choice/denominator distributions, prize-sharing rules, actual payouts, costs and taxes. A fair draw's physical probabilities are unaffected by player preferences.

**Current decisions:** PR #44 remains DRAFT/NO MERGE; P1 #57 and P3 #18 source gates remain OPEN; operational freshness stays RED until independently validated current data. **RESEARCH ONLY / NO PLAY.**
