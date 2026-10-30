# LREI P3 — Jackpot-winner counts in the first-party CSV (exploratory, not a prediction)

**Audit date:** 2026-10-30. **Research only / NO PLAY.** This is a descriptive check of two additional numeric fields in the user-supplied official-site CSV. It does **not** fulfill the pre-frozen future-only strong-preference protocol, which requires *lower-tier 3-main winner counts*, nor does it enable monetary expected value.

## Reproducible source and scope

- User-supplied unmodified `Lotto (1)(5).csv`: **183,688 bytes**, SHA-256 `3f6ff3b40bcf4ac26407fe09cdea6ac5c23cac78fffccc847f74e07f848f0074`; Windows-1255, 4,555 archive rows, includes historical rule eras. User Windows HTTPS source-content capture dated 2026-10-30T17:52:09Z corroborates this exact SHA-256 and first-party `https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx`. **Signed draw protocols and formal research-use rights review are still pending.**
- Use **BOTH** current-era date cutoff `date >= 2016-10-10` AND bounded current-format IDs **2833–3979**. This gives **1,147 contiguous valid 6/37 draw rows**, latest 27 October 2026. The original raw archive reuses different ID ranges for older lotteries: a naive `ID >= 2833` includes **2,757 records**, including **1,610 unrelated older records**. The current repository's `archive_reconciliation.py` already guards against this legacy numbering hazard; do not add redundant code or silently use the 2,757-row sample.
- Fields used verbatim from the original Hebrew header: `המספר החזק/נוסף` (strong result), `מספר_זוכים_לוטו` and `מספר_זוכים_דאבל_לוטו` (top-prize winner counts only). They are **not** a dataset of filled ticket combinations, manual ticket counts, ticket sales or 8+8 prize tiers.
- Known control: first-tier regular and Double winner counts for the six archived draws #3949–#3954 agree with the already retained six `data/prize_observations/*.json` observations (12/12 top-tier comparisons).
- Full audit, source-independent local SHA checks, exact-group results and reproducible randomization method are in the private downloadable research audit `LREI_jackpot_winners_2016-2026_audit.json`. No original raw response or third-party prize tables copied to GitHub.

## Complete descriptive results

Total **148 regular + 76 Double = 224** first-tier winning entries across **1,147** current-era draws. **186 draws** had ≥1 top-tier winner; **961** had none; **26** had two or more top-tier winners.

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
