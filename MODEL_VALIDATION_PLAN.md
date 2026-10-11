# LREI Model Validation Protocol

## Purpose

This protocol separates software correctness, portfolio optimization, and evidence for a historical predictive signal. A passing test establishes that code behaved as expected; it does not establish that a model predicts a fair random draw.

## 1. Keep prediction and coverage as separate objectives

- **Signal models (Regular, Pro, Elite, Smart historical selection):** evaluate whether model-generated lines performed differently from an equal-size random baseline on strictly later draws. Treat a positive historical difference as an observation, not a claim of better future odds.
- **Coverage 4+:** evaluate the mathematical portfolio property directly. Four-or-more-match events are disjoint when no pair of tickets shares more than one main number. A valid 14-ticket portfolio satisfying that constraint reaches the exact maximum 4+-main-number coverage for 14 lines under a uniform 6-of-37 draw.
- **Any-prize coverage (3+):** calculate the exact union of 6/37 draw outcomes covered by a fixed portfolio, then compare candidate-construction procedures on equal-size portfolios. A greedy search over a finite pool is an approximation to global optimization, not a proof of a global optimum.
- Never describe the coverage modes as predicting which numbers will be drawn.

## 2. Enforce the same evaluation budget

For every model comparison:

1. Evaluate exactly 14 valid, distinct tickets per model and per target draw.
2. Keep candidate-pool size and relevant compute settings aligned across candidate-generation variants. If this is impossible, report the budget difference explicitly.
3. Compare each model against multiple independently generated random 14-ticket portfolios, not a single convenient random sample.
4. Score main-number matches independently from strong-number matches and prize tiers. Use the official prize evaluator for actual-prize outcomes.

The theoretical random expectation for a six-number ticket is `36/37 = 0.9730` main-number matches per ticket. Historical averages above or below this value are expected to fluctuate.

## 3. Correct chronological walk-forward evaluation

For each target draw:

1. Train feature calculations and candidate models only on draws strictly earlier than the target.
2. Choose settings using an earlier calibration window; never use the target result to select weights, the model, a seed, or a ticket.
3. Generate one fixed portfolio for a model at each calibration origin and score that same portfolio across every draw in that validation block. Do not generate a new random portfolio separately for each validation draw in a block.
4. Keep validation blocks chronological and non-overlapping when reporting stability across origins.
5. Make random generation reproducible with explicit seeds. Pair model comparisons on the same target draws.

## 4. Report uncertainty, not just the highest average

Every predictive comparison should report:

- the number of target draws and walk-forward origins;
- mean main-number matches per ticket for the candidate and random baselines;
- the paired per-draw difference;
- a 95% confidence interval for that paired difference;
- portfolio-level outcomes such as best ticket reaching 4+, 5+, or 6/6 and actual prize outcomes, when relevant;
- the result at each origin, not only the pooled mean.

Because neighbouring walk-forward recommendations share much of their training history, prefer a paired block bootstrap (for example, five-draw blocks) for final uncertainty estimates. A per-draw bootstrap may be kept as a quick diagnostic, but should not be the only uncertainty estimate.

## 5. Promotion gate for experimental features

Keep a new signal or adaptive weight opt-in unless all of the following hold:

- the comparison is leakage-free and uses an equal 14-ticket budget;
- the method beats the conservative baseline on a pre-specified primary metric;
- the paired 95% confidence interval supports a positive difference;
- the direction of the effect is consistent across several non-overlapping origins;
- the result is not dependent on one seed or one small window;
- the feature does not materially damage portfolio validity, diversity, or actual-prize evaluation.

The current rolling historical dataset has been inspected by numerous experiments; its recent tail is therefore a development/validation set, not a truly untouched final holdout. Avoid selecting settings based on this tail and then describing the same tail as independent confirmation. The strongest final test of a predictive claim is performance on future draws that were not available when the settings were chosen.

## 6. Multiple comparisons and research discipline

Testing many features, strengths, candidate pools, and scoring metrics increases the chance that one variant appears best by accident. Record the hypothesis and primary metric before each experiment. Use ablations to explain an effect, not to search the same holdout endlessly for a winning combination. If many variants are tested, disclose that fact and use a fresh evaluation window before promotion.

## 7. Current evidence-based direction

- Preserve the exact Coverage 4+ mode as the mathematically justified portfolio objective.
- Preserve Any-prize coverage as an exact-coverage calculation over a finite candidate pool, with greedy selection clearly described as approximate.
- Keep frequency, recency, EWMA, consensus, momentum, gap, learned-signal, and adaptive candidate-allocation layers experimental unless the promotion gate is met.
- Prioritise cleaner evaluation, reproducibility, data validation, and fair baseline comparisons over adding more features.
- Never promise a winning combination. In a fair lottery, historical modelling cannot guarantee or establish a higher jackpot probability for one valid set of 14 distinct lines.
