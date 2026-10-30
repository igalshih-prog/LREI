# LREI P3 — Jackpot-winner counts in the first-party CSV (exploratory, not a prediction)

**Audit date:** 2026-10-30. **Research only / NO PLAY.** This is a descriptive check of two additional numeric fields in the user-supplied official-site CSV. It does **not** fulfill the pre-frozen future-only strong-preference protocol, which requires *lower-tier 3-main winner counts*, nor does it enable monetary expected value.

## Reproducible source and scope

- User-supplied unmodified `Lotto (1)(5).csv`: **183,688 bytes**, SHA-256 `3f6ff3b40bcf4ac26407fe09cdea6ac5c23cac78fffccc847f74e07f848f0074`; Windows-1255, 4,555 archive rows, includes historical rule eras. User Windows HTTPS source-content capture dated 2026-10-30T17:52:09Z corroborates this exact SHA-256 and first-party `https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx`. **Signed draw protocols and formal research-use rights review are still pending.**
- For the **LREI repository-window** audit only, use **BOTH** date cutoff `date >= 2016-10-10` AND bounded IDs **2833–3979**. This gives **1,147 contiguous valid 6/37+strong 1–7 draw rows**, latest 27 October 2026. **Correction:** October 2016 is the beginning of LREI's selected ten-year training window, **NOT the beginning of the current lottery rule format**; that 6/37 + strong 1–7 format begins at draw **#2255, 17 May 2011**. See the independent full-format sensitivity audit below. Do not alter the algorithm's frozen historical window to retrofit this retrospective analysis. The original raw archive reuses different ID ranges for older lotteries: a naive `ID >= 2833` includes **2,757 records**, including **1,610 unrelated older records**. The current repository's `archive_reconciliation.py` already guards against this legacy numbering hazard; do not add redundant code or silently use the 2,757-row sample.
- Fields used verbatim from the original Hebrew header: `המספר החזק/נוסף` (strong result), `מספר_זוכים_לוטו` and `מספר_זוכים_דאבל_לוטו` (top-prize winner counts only). They are **not** a dataset of filled ticket combinations, manual ticket counts, ticket sales or 8+8 prize tiers.
- Known control: first-tier regular and Double winner counts for the six archived draws #3949–#3954 agree with the already retained six `data/prize_observations/*.json` observations (12/12 top-tier comparisons).
- Full audit, source-independent local SHA checks, exact-group results and reproducible randomization method are in the private downloadable research audit `LREI_jackpot_winners_2016-2026_audit.json`. No original raw response or third-party prize tables copied to GitHub.

## Complete descriptive results

Total **148 regular + 76 Double = 224** first-tier winning entries across **1,147** LREI-window draws. **186 draws** had ≥1 top-tier winner; **961** had none; **26** had two or more top-tier winners.

| Drawn strong | Number of draws | Regular jackpot winners | Double jackpot winners | Combined jackpot winners | Combined winners / draw |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 157 | 19 | 9 | 28 | 0.1783 |
| 2 | 160 | 18 | 15 | 33 | 0.2063 |
| 3 | 165 | 25 | 7 | 32 | 0.1939 |
| 4 | 149 | 16 | 9 | 25 | 0.1678 |
| 5 | 177 | 27 | 15 | 42 | 0.2373 |
| 6 | 178 | 20 | 10 | 30 | 0.1685 |
| 7 | 161 | 23 | 11 | 34 | 0.2112 |
| **Total** | **1,147** | **148** | **76** | **224** | **0.1953** |

As a crude *exploratory* association screen, compare average first-tier winner counts per **draw** by drawn strong. This is not the project's preregistered primary endpoint:
- **Strong 4 vs strong 1:** 25/149 vs 28/157, count-rate ratio **0.9408**; approximate conditional-Poisson exact 95% RR interval **[0.5261, 1.6736]**, two-sided conditional p **0.891**; **50,000 calendar-year-stratified strong-label permutations**, fixed seed `20261030`, two-sided p **0.846**.
- **Strong 5 vs strong 1:** 42/177 vs 28/157, rate ratio **1.3305**; RR interval **[0.8055, 2.2289]**, conditional p **0.281**; same year-stratified permutation p **0.282**.
- Background check: frequencies with which each strong result was drawn show no striking deviation from 1/7 (chi-square p **0.669**); this is not a measure of the players' strong-number selections.

**Neither comparison is statistically persuasive**, and even a statistically persuasive jackpot count difference would not determine **which six-main-plus-strong combinations** players picked, due to sparse prize-first winners, variation in ticket volume, jackpot regimes, manual vs automatic choices and prize-sharing. In particular, this historical jackpot screen does **not** reproduce or refute the published 2018 manual-ticket-choice study because the underlying data and estimand are entirely different.

## Research decision

- **Positive:** an additional two columns were validated and summarized using a properly restricted contemporary draw cohort. This is a useful external-data integrity and descriptive baseline.
- **Negative/limitations:** 224 first-tier winner entries over 1,147 draws are too sparse and confounded to identify 2026 per-combination popularity, validate anti-crowd returns or justify a predictor. This does not satisfy #18's missing 14 × 16 paid tier rows.
- **No action on model weights, no retroactive preregistration, no financial EV, no play**, and no promotion of PR #44 into `main` solely on this descriptive audit.

## Correction and independent full-game-format sensitivity check — #2255–#3979 (2011–2026)

**What changed:** In the initial write-up the phrase “current-era date cutoff 2016” was imprecise: **the game’s 6/37 + 1–7 strong-number format starts on 17 May 2011, draw #2255**, not in October 2016. This was independently crosschecked with [a dated 16 May 2011 description of the next draw as the first using 7 strong choices](https://isrlotto.blogspot.com/search/label/%D7%94%D7%92%D7%A8%D7%9C%D7%AA%20%D7%94%D7%9C%D7%95%D7%98%D7%95%2017.05) and [historical lottery-format timeline](https://sikui.vercel.app/history/). These third-party references establish a historical regime boundary, **not approval of payout figures or their reuse**.

**Method:** Re-parse exactly the *same user-supplied raw Windows-1255 CSV*, original SHA-256 `3f6ff3b40bcf4ac26407fe09cdea6ac5c23cac78fffccc847f74e07f848f0074`; select **both** IDs #2255–#3979 **and** dates 2011-05-17 through 2026-10-27, require 1,725 ascending consecutive IDs with distinct 6-of-37 numbers and strong 1–7. No missing or invalid rows. This is a **retrospective robustness check**, **not** an additional preregistered independent sample or a change to LREI's 1,147-row training archive.

| Sample | Draws | Regular first-tier winner entries | Double first-tier winner entries | Total first-tier entries | Draws with ≥1 first-tier entry |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing 2016-10-10 to 2026-10-27 (#2833–3979) | 1,147 | 148 | 76 | 224 | 186 |
| Newly added older part 2011-05-17 through #2832 | 578 | 74 | 44 | 118 | 102 |
| **Full 2011-05-17 to 2026-10-27 (#2255–3979)** | **1,725** | **222** | **120** | **342** | **288** |

In the full format period **1,437 draws** had no top-prize winners and **41 draws** had two or more combined top-tier winner entries. The literal original CSV top-tier winner columns were used; **NOT** a substitute for all 8+8 payout tiers or ticket-choice records.

| Drawn strong | Draws | Regular first-tier entries | Double first-tier entries | Combined | Entries/draw |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 238 | 32 | 12 | 44 | 0.1849 |
| 2 | 244 | 25 | 27 | 52 | 0.2131 |
| 3 | 253 | 36 | 16 | 52 | 0.2055 |
| 4 | 232 | 30 | 14 | 44 | 0.1897 |
| 5 | 261 | 39 | 19 | 58 | 0.2222 |
| 6 | 262 | 33 | 16 | 49 | 0.1870 |
| 7 | 235 | 27 | 16 | 43 | 0.1830 |
| **Total** | **1,725** | **222** | **120** | **342** | **0.1983** |

**Frozen exploratory contrasts recomputed, no fishing for replacement benchmarks:** Using each drawn-strong cohort’s total first-tier entries per draw, compare **4 vs 1** and **5 vs 1**. Exact conditional Poisson-rate intervals via a binomial conditional on sum of counts, plus two-sided **50,000** within-calendar-year permutations of the strong label (seed 20261030, add-one finite-simulation correction):

| Comparison | 2016+ rate ratio (original) | Full 2011+ rate ratio | Full exact 95% RR interval | Full exact conditional p | Full year-stratified permutation p |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strong 4 / strong 1 | 0.941 | **1.026** | [0.660, 1.595] | 0.916 | 0.915 |
| Strong 5 / strong 1 | 1.331 | **1.202** | [0.798, 1.821] | 0.374 | 0.398 |

**Material insight:** the tiny 4-vs-1 estimate even reverses direction when an additional 578 same-rules historical draws are included. No estimate is statistically persuasive. Drawn-strong frequencies across 1..7 in this full 1,725-draw window: chi-squared **3.708**, df=6, p **0.716** (physical-outcome sanity check only; not player choice).

**Preregistered/prospective distinction preserved:** The project's *prospective* endpoint is lower-tier regular-`3` and `3+strong` counts on **genuinely future** source-reviewed draws, unlike this retrospectively examined first-prize count analysis. No 2026 player-selection distribution, ticket-level volume, causality, sharing probability or net monetary expected value is identified; **NO PLAY**, no model weight change, no main update and no prize-data promotion.

**Reproduction** (without redistributing the raw licensed source): Decode the user's original file as CP1255, `csv.DictReader` over the exact 12-column operator archive, parse `הגרלה`, `תאריך` (`%d/%m/%Y`), `1`..`6`, `המספר החזק/נוסף`, `מספר_זוכים_לוטו`, `מספר_זוכים_דאבל_לוטו`; select both ID and date; sum first-tier columns per drawn-strong result. For Poisson-rate conditional exact p use `scipy.stats.binomtest(x_a, x_a+x_b, n_a/(n_a+n_b))` and transform Clopper–Pearson proportion limits to rate ratios. For year-stratified null, shuffle drawn-strong labels independently within each of the 2011–2026 calendar-year cohorts and compare absolute differences of first-tier entries per draw over 50,000 repetitions; observed rates and sample sizes must remain fixed in the permutations. Private local full audit has SHA-256 `9c1fe42767f280ebda95793e8441176bc258c0313a8299ce0348112b40134e5c`; it contains **aggregate-only research results**, not original record rows.
