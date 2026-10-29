# P3 scenario engine: published directions, no fabricated 2026 calibration

Date: 2026-10-29. Status: **hypothetical modeling tool only, RESEARCH ONLY / NO PLAY**.

## Why build this?

Polin, Ben Isaac & Aharon (2021) directly observed ~115 million **manually selected entries** in Israel in 2018, not merely winning outcomes. Number **7** was the most popular, **37** least popular, power/strong **4 and 5** most popular, power **1** least popular, with form-position effects. Higher advertised prizes were associated with more manual entries and somewhat less concentrated manual-number marginals. Source: https://doi.org/10.1017/S193029750000807X and https://dlab.sauder.ubc.ca/sjdm/journal/21/210322/jdm210322.html . None of the 2018 marginal preferences is an observed value for 2026.

Dr. Polin's 2026-10-29 non-confidential email confirms that two crucial inputs are absent from public prize tables: **total manual-entry share** and the **distribution of manually selected combinations**. A well-defined sensitivity model can express what different assumptions imply, but cannot identify the true inputs.

## Mathematically coherent simplified scenario

Instead of guessing an arbitrary independently specified eight-tier probability table, the module defines a normalized probability law for a player's **manually selected six-number set** `S`:

`Q_main(S) = product(w_i for i in S) / e_6(w_1,...,w_37)` for `|S|=6`, where `w_i>0` are **assumed** weights and `e_6` is the sixth elementary symmetric polynomial. Independently, manual strong-number probability is `Q_strong(s) = u_s / sum(u_1,...,u_7)`.

For fixed **already drawn** main set `D`, exact `k`-main-match probability is

`Q_main(k | D) = e_k(w_D) * e_(6-k)(w_not_D) / e_6(w_all)`.

The model calculates these quantities using O(6 * 37) dynamic programming, with 14 disjoint categories `k=0..6` and strong hit/non-hit; they sum to 1. No Monte Carlo noise.

A *hypothetical* fraction `f` of all entries may be manual, while the rest are uniform machine-generated:

`P_model(k,s | D) = (1-f) * P_uniform(k,s) + f * Q_manual(k,s | D)`.

The model **does not fit f or w or u** from the prize data, and in particular **does not infer sales or co-winner volumes**. The fractions here refer to **all entries**, unlike the match-stratum shares `f_k` in PR #84. Those are different objects and cannot be substituted for each other.

This product-of-number-weights selection law is a **toy structural model**. It cannot represent player-preferred **pairs, complete combination patterns, birthdays as date bundles, form-shape correlations, copied tickets or dependence between strong and main choices**. Individually unpopular numbers need not form an unpopular six-number combination; see McHale & Baker (2012), https://doi.org/10.1111/j.1740-9713.2012.00540.x .

## Illustrative toy scenario (NOT a data fit)

- Start with all `main_weights = [1.0] * 37`, `strong_weights = [1.0] * 7`.
- Assign `main_weights[6] = 1.7` (number 7), `main_weights[36] = 0.5` (number 37), `strong_weights[3] = 1.6` (strong 4), `strong_weights[0] = 0.8` (strong 1).
- Call `hypothetical_player_mix_profile(main_weights, strong_weights, winning_main, winning_strong, assumed_manual_fraction_all_entries=0.5)`.
- The weights 1.7, 0.5, 1.6, 0.8 and the 50% fraction are deliberately invented **scenario inputs**, not purported observations. Do not publish the model outputs as population frequencies, ticket advice, 2018 estimates or 2026 forecasts.

Verification tests ensure (a) all-ones weights exactly recover hypergeometric probabilities, (b) category probabilities sum to 1, (c) scaling weights does not change the normalized law, (d) f=0 is the uniform null, f=1 is the manual scenario and intermediate f is a convex mix, (e) malformed weights and draws fail closed, and (f) no model output is authorized for financial prediction or play.

## Research gate before any real-world use

1. Obtain licensed player-choice data or independently verified aggregate denominators and prize-tier counts. Keep `#44` NO MERGE and source gates `#57`/`#18` unchanged.
2. Fit a **separately justified** preference model with interactions, strong/main coupling and jackpot-dependent participation. Record how every parameter was observed or constrained. Do not claim calibration from only six 2026 reviewed draws.
3. Freeze the model *before* additional chronologically future verified draws, then test on those held-out observations separately by regular and Double products, with draw-clustered uncertainty. Never treat repeated entries as independent players.
4. Only if external denominators, prize-sharing rules, payout amounts, applicable tax and costs become verified can an independent net-value study even be considered. Maintain **NO PLAY** otherwise.

The physical draw probabilities are unchanged by any assumptions about human selections. Unpopular numbers can affect sharing *conditional on winning* under some assumptions, never the probability that the numbers are drawn. Historical UK claims about higher expected winnings are not an Israeli 2026 result (Cox, Daniell & Nicole 1998: https://doi.org/10.1111/1467-9884.00160).
