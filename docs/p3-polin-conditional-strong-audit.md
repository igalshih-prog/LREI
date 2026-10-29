# P3: Polin evidence into a conditional strong-match audit (research only)

Date: 2026-10-29. **Status: exploratory / NO PLAY.** This is an operationalization of *published* findings and the researcher's non-confidential methodological guidance, not a replication of NDA-restricted ticket data.

## Evidence hierarchy

1. **Published (2018 manual-ticket population):** Polin, Ben Isaac & Aharon (2021) examined ~115 million manually chosen Lotto entries across 118 draws. Main number **7** was the most selected and **37** the least selected in every draw; power/strong **4 and 5** were preferred, **1** least selected. Top rows were preferred to bottom rows. They found an *association* of ~33,000 additional manually selected lines per extra NIS 1 million advertised grand prize, and manual number selections became somewhat more uniform as the jackpot grew. None of these are verified **2026** parameters.
   - Public peer-reviewed paper: https://doi.org/10.1017/S193029750000807X
   - Accessible text: https://dlab.sauder.ubc.ca/sjdm/journal/21/210322/jdm210322.html
2. **Researcher email (2026-10-29):** Dr. Polin confirmed strong evidence for non-uniform manual choice patterns and highlighted two inaccessible inputs: manual share and distribution of manual guesses. He did **not** provide new licensed datasets, 2026 calibrations, or permission to distribute any NDA data.
3. **Local operator-display observations:** Only draw IDs **3949–3954** are present in the source-gated reviewed set. Their status remains `operator_site_display_only_not_binding` (not independent verification). Other draw records remain quarantined.

## Key derivation: a ratio that does not require total ticket volume

Fix the realized draw's six main numbers and strong number. Under the strict *independent, uniform* strong-choice null, among entries with exactly `k` main-number matches, the fraction also having the strong number is

`p_k = W[k+strong] / (W[k+strong] + W[k]) = 1/7`, for `k in {3,4,5,6}`.

This cancels the total entry denominator **as a reference identity**. It does **not** cancel possible manual choice biases, duplicated tickets, conditional main/strong correlations, product effects, source errors, and dependence between entries. Sampling-based confidence intervals would require assumptions about these mechanisms that we have **not validated**, so the first-stage audit displays descriptive fractions only, with no significance or winner-popularity ranking.

Run the read-only diagnostic:

`python -m lrei.lottery.conditional_strong_audit --directory data/prize_observations`

It reads exactly six files, emits JSON to stdout, fails closed on source/identity/data errors, separates regular and double, and never writes to source datasets or produces betting recommendations.

## Six-source exploratory calculation: regular Lotto, exactly 3 main matches

| Draw | Drawn strong | Strong-winning entries | Without-strong entries | Observed strong fraction | Uniform null |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3949 | 6 | 15,989 | 98,768 | 13.93% | 14.29% |
| 3950 | 7 | 20,744 | 126,570 | 14.08% | 14.29% |
| 3951 | 4 | 20,970 | 117,040 | 15.19% | 14.29% |
| 3952 | 4 | 25,813 | 146,703 | 14.96% | 14.29% |
| 3953 | 7 | 24,601 | 152,673 | 13.88% | 14.29% |
| 3954 | 6 | 10,249 | 62,430 | 14.10% | 14.29% |

The direction for strong 4 is compatible with the **historical** qualitative claim, **not** proof that 4 was more popular among 2026 manual picks. There are only six draws and the only observed strong numbers here are **4, 6 and 7**. This sample cannot test claimed preferences for strong **1 or 5**, nor establish stability; it has not been preregistered as a prospective holdout.

## Identification: two missing quantities, infinite solutions

If among winning entries with exactly `k` main matches, a hypothetical fraction `f_k` came from manual selection and their hypothetical conditional strong hit probability is `q_k`, then:

`p_observed,k = (1 - f_k) / 7 + f_k * q_k`

**Only if** the automated component is uniform and independent and the two groups are correctly defined. Importantly, `f_k` is the manual fraction **inside the k-match stratum**, *not* the manual fraction among all entries. The unknown `f_k` and `q_k` are not separately identifiable from one observed fraction.

For draw 3951, regular Lotto k=3, `p_observed = 20970 / 138010 = 0.1519455`. Three **illustrative and mutually inconsistent** scenarios fit it exactly:

| Assumed manual fraction *within k=3 winners* | Implied manual strong-4 rate among that stratum |
| ---: | ---: |
| 25% | 17.92% |
| 50% | 16.10% |
| 75% | 15.50% |

These are **not estimated real-world proportions**. The diagnostic helper `implied_manual_strong_rate` computes hypothetical constraints and rejects impossible combinations. Nothing in current winner-count data identifies a real manual share, a real manual-number distribution or an individually unpopular six-number combination.

## Next research gates

- Seek **source independently verified** public winner counts for additional chronological draws, especially strong numbers 1 and 5, without unquarantining unverified files.
- Pre-register a *future* prediction for match-class strong fractions using only published historical hypotheses; analyze at **draw-level**, not ticket-level pseudo-replication. Entries may be duplicated and not independent.
- Stratify by regular/double product, main-match class and announced jackpot regime; study whether high jackpots weaken selection bias (2018 hypothesis) **only** when independently comparable repeated draws and verified jackpot definitions are available. Do not transplant the 2018 33k-per-million slope to 2026.
- Build a selection model only after identifying or bounding manual entry fractions, conditional main/strong dependencies, and combination preference patterns; isolated number rarity is not guaranteed to imply rare *combinations* (McHale & Baker, 2012, https://doi.org/10.1111/j.1740-9713.2012.00540.x).
- Compare models on frozen, chronological held-out data only, and calculate no financial EV until payout rules, participation denominators, taxes, co-winner mechanisms and independent source provenance are verified.

**Source constraints:** no NDA data; no promotion of #44; #57 and #18 acceptance gates still stand. **RESEARCH ONLY / NO PLAY.**
