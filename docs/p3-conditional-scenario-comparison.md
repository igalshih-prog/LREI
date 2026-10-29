# P3: Compare hypothetical choice scenarios to the six reviewed draws

**Date:** 2026-10-29. **RESEARCH ONLY / NO PLAY.** This integrates the PR #84 source-gated conditional strong audit and the PR #85 normalized hypothetical selection model. No new source data, no parameter inference, no source promotion, no financial predictions.

## Question

For a **fixed realized draw**, how does the share of strong-number matches among tickets matching exactly `k` main numbers differ under alternative assumed selection patterns?

The model uses assumptions about:
- `main_weights`: 37 strictly positive **hypothetical** marginal preferences.
- `strong_weights`: 7 strictly positive **hypothetical** preferences, independent of the main-number selection *within the manual component*.
- `assumed_manual_fraction_by_product`: distinct assumed manual fractions **across all entries** in regular Lotto and Double Lotto. They are **not observed**; the manual fraction *within* the exactly-`k` main-match class is generally different.

For each draw `D`, each product, and `k=3,4,5,6`, the conditional model fraction is

`q_model(D,k) = P_model(k,strong|D) / (P_model(k,strong|D) + P_model(k,no-strong|D))`.

Compare with the published winner-entry fraction

`q_observed(D,k) = W(k+strong) / (W(k+strong)+W(k))`, when the observed denominator is nonzero.

The output is `100 * (q_observed - q_model)` **percentage points**, not an effect size adjusted for uncertainty, a hypothesis-test statistic, or an inferred change in jackpot sharing. A zero-winner match class has `null` observed fraction/difference, never zero inferred interest.

## Why this is useful

- **Uniform benchmark:** setting all selection weights to 1 yields a model fraction of `1/7` in every match class and product, regardless of the assumed mixture share.
- **Strong preference:** with all main weights uniform, `strong_weights[3] = 2` is an invented toy example that makes a *manual* strong-4 conditional rate of `2/8`. With zero manual share regular remains at `1/7`; with 100% assumed manual Double is `2/8`. Nothing about those arbitrary numbers is calibrated to real players.
- **Main/strong composition:** when the main-number weights are nonuniform, the fraction of manual tickets **among exactly-k matches** depends on the realized main result. Thus a single assumed overall manual share generally implies **different conditional strong rates for k=3 versus k=5**, even when strong and main choices are independent *within* the two mixture components. This is why manually inserting the same `f_k` in every stratum would be misleading.
- **Product stratification:** observed regular/Double winner counts remain distinct; their assumed mixture shares can differ. The model currently shares the hypothetical main/strong preference weights across products. No evidence is claimed that these product populations actually have identical patterns.

## Reproducible interface

Import `compare_hypothetical_strong_scenario` from `lrei.lottery.conditional_scenario_comparison` and call with directory `Path("data/prize_observations")`, lists of 37 and 7 positive weights, and a dict such as `{"regular":0.0,"double":1.0}`. The latter shares are arbitrary *scenario boundaries*, not operator-reported values.

Exactly the six reviewed, operator-display-only draws #3949–3954 are processed in chronological order; all other draws remain excluded. Source ID, date, main and strong number, complete eight-tier winner counts, and product separation are checked using the existing fail-closed audit. Data are read-only.

## Identification, validation and stopping rules

**This is retrospective scenario exploration, not a held-out test.** It uses the already-inspected six draws (strong outcomes 4, 6 and 7 only). There is no likelihood fit, no selection of a best-fitting hypothesis, no aggregated p-value, and no treatment of ticket entries as independent players. No independent verification exists for the operator-display observation files.

Dr. Polin explained on 2026-10-29 that manual-entry shares and the distribution of manually chosen numbers are missing from public prize tables. Their 2018 paper documented preferences for main **7 over 37** and strong **4/5 over 1**, and a relationship between jackpot size and participation/choice spread; these are **historical hypotheses, not 2026 measured weights**. The scenario engine does not solve this identification problem. Source: https://doi.org/10.1017/S193029750000807X .

Before claiming prospective validity, preregister externally justified weights and mixture assumptions, verify independently sourced future chronological observations that cover all strong numbers, assess draw-clustered uncertainty, compare to uniform baselines, and require non-leaky holdout evaluation. To investigate sharing **conditional on an actual jackpot**, further verified population/combinations data and prize payout/tax/product regime information would be necessary.

PR #44 remains **NO MERGE**; source acceptance gates #57 and #18 remain unchanged. This tool cannot recommend Lotto lines, estimate sales, infer player popularity from the draw history, or calculate credible EV. **NO PLAY.**
