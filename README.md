# LREI

## Lottery Recommendation & Evaluation Intelligence

LREI is a Python-based lottery recommendation and evaluation system.

The project analyzes historical lottery draws, scores numbers using multiple historical signals, generates lottery tickets, applies portfolio optimization, and evaluates results with chronological backtesting against random baselines.

## Main Features

- Historical lottery dataset analysis
- Number frequency and recency analysis
- Rank-normalized and raw-frequency scoring
- EWMA time-decay signal
- Pair and triple co-occurrence affinity
- Recent momentum and gap/overdue signals
- Cross-signal consensus scoring
- Optional learned historical signal model
- Historical structural profile
- 14-ticket portfolio optimization
- Strong-number evaluation
- Chronological walk-forward backtesting
- Random-baseline comparison
- Bootstrap confidence intervals for paired benchmarks
- Ablation testing, including jackpot-oriented tail diagnostics
- Constrained-random portfolio baselines
- Reproducible evaluation using seeds
- Automated testing with GitHub Actions
- Streamlit application

## Recommendation Modes

### Regular

The baseline LREI engine uses the established frequency-based predictor, ticket generation, and diversity optimizer.

### Pro

Pro combines multiple historical signals, pair/triple affinity, structural constraints, candidate scoring, and a local portfolio-refinement step.

Pro always returns exactly **14 recommended tickets**.

### Elite Pro

Elite Pro is the advanced ensemble layer used by the application's Pro mode. It combines:

- rank-normalized frequency
- raw-frequency scaling
- EWMA recency
- adaptive walk-forward weighting
- the Pro candidate and portfolio-selection pipeline

Elite Pro also returns exactly **14 recommended tickets**.

Its candidate pool is an ensemble: candidate allocation can be weighted across rank, raw-frequency, and EWMA generators, while the final number scores use the adaptive ensemble weights. Elite currently keeps equal candidate-source allocation as the conservative production default; adaptive candidate allocation remains experimental because the latest longer walk-forward comparison was effectively neutral. Additional momentum, gap/overdue, consensus, learned-signal, pair/triple coverage, and tail-weight layers remain opt-in unless walk-forward diagnostics support promotion.

The purpose of these additional layers is to test whether more sophisticated historical modeling improves empirical backtest behavior. They do not change the mathematical randomness of a fair lottery draw.


### Smart mode

Smart offers three explicit objectives:

- **4+ main-number coverage:** uses the exact Coverage portfolio construction. Its 14 unique tickets share at most one main number per pair, making the events of hitting at least 4 of 6 main numbers disjoint. Under a uniform 6-of-37 draw model, this maximizes the probability of at least one 4+ main-number hit among 14 tickets.
- **Historical mean-match selection:** uses only earlier draws to compare Regular, Pro, and Elite by average main-number matches on a chronological validation window, then runs the selected model on the full available history.
- **Experimental actual-prize selection:** compares the models by a normalized score for the best prize tier in each historical validation draw: 1.0 for tier 1, decreasing to 0.125 for tier 8, and zero when no ticket wins. The strong number changes the tier score when relevant. This is a heuristic score, not a monetary expected-value calculation, and it is not established as a better predictor.

The prize evaluator maps all eight official prize tiers and measures the outcome of each ticket against a draw. Both historical objectives are walk-forward tests, not guarantees. All objectives return exactly **14 recommended tickets**. The coverage objective is a mathematically grounded portfolio-design choice, not a prediction of the winning numbers. It retains the same theoretical jackpot probability as any other set of 14 distinct valid lines.


The latest clean walk-forward model-selection diagnostic found:

- Regular vs Pro: Pro was lower on that validation window.
- Elite Pro remained close to Regular.
- Adaptive candidate allocation showed only a small, statistically uncertain difference from the conservative allocation.

A separate conservative meta-selector diagnostic showed a positive historical delta when selecting among Regular/Pro/Elite using prior validation draws. LREI is therefore adding this as a separate **Smart** mode for further walk-forward validation rather than silently replacing Elite production behavior.

These are empirical backtest observations only. They are **not evidence of guaranteed predictive advantage**.

### Coverage

Coverage is a separate, coverage-oriented mode that returns exactly **14 unique tickets** with no more than one main number shared by any pair of tickets. Under the uniform 6-of-37 draw model, this makes the events of hitting at least 4 main numbers on different tickets disjoint, so the portfolio achieves the mathematical maximum possible 4+-main-number coverage for 14 distinct lines.

The app also calculates exact coverage for **3+, 4+, 5+, and 6/6 main-number matches** for the 14 displayed tickets. The 3+ metric measures the probability that at least one line matches at least three main numbers, which is the lowest main-number match tier for a prize under the published Israeli Lotto prize table. It is a useful “any prize” indicator, while Coverage mode's construction specifically maximizes 4+ coverage; the two goals are not interchangeable. The strong number affects the prize tier, and its inclusion does not change the main-number coverage calculation.

These are exact combinatorial probabilities under a uniform 6-of-37 draw model, **not predictions of which numbers will be drawn**. The method does not increase the chance of matching all six main numbers (or the full jackpot with the strong number) beyond the chance from purchasing 14 distinct valid lines.

An exploratory six-seed comparison of 3+ coverage found that the Elite-guided portfolio with maximum overlap one (50.456594%) was effectively indistinguishable from random portfolios subject to the same overlap limit (50.460795%); the paired difference was -0.004201 percentage points, with a 95% bootstrap interval spanning zero. The measured advantage so far is therefore the portfolio's overlap structure—not evidence that historical number signals predict the draw. This is an early diagnostic, not a definitive large-sample study.

The Coverage correctness checks and overlap-cap comparisons run in a dedicated GitHub Actions workflow. Prize-tier reference: [published Israeli Lotto prize table](https://www.pais.co.il/download/files/Lotto-8306.pdf).


## Evaluation Philosophy

LREI does not claim to predict future lottery results with certainty.

A fair lottery gives every valid combination the same mathematical chance. Historical patterns can therefore be useful for engineering experiments and portfolio analysis, but a backtest cannot prove that a strategy will improve future lottery odds.

LREI uses chronological walk-forward evaluation:

1. Only draws before the target draw are used as history.
2. The recommendation engine scores the available history.
3. Tickets are generated.
4. The portfolio is optimized.
5. The recommendations are compared with the next unseen draw.
6. Random portfolios are evaluated under the same ticket-count conditions.
7. Results are aggregated across multiple target draws.

When benchmark results are close to the random baseline, LREI treats that as evidence against overclaiming predictive power rather than as proof of an advantage.

## Dataset

The repository currently includes a rolling **10-calendar-year** lottery dataset ending with draw 3973 on 10-10-2026.

The current file contains **1,141 consecutive draws**, covering the period from 10-10-2016 through 10-10-2026. When refreshing the file, add newly published draws and remove the oldest draws outside the rolling 10-year window; the test suite checks chronology, contiguous draw IDs, and data freshness.

The main lottery numbers are 1–37, with six main numbers per draw and a separate strong number.

## Benchmarking

The repository contains separate benchmarks for:

- Regular vs Pro
- Pro vs multiple random baselines
- Elite Pro vs Pro vs multiple random baselines
- Pro signal/feature ablations
- Elite candidate-allocation experiments, including longer walk-forward diagnostics
- Jackpot-oriented tail diagnostics (4+, 5+, and 6-hit outcomes)
- Constrained-random portfolio comparisons using the same overlap limit

Benchmarks report metrics such as average hits per ticket, best-ticket hits, coverage-related behavior, paired differences, and bootstrap confidence intervals where applicable.

All benchmark conclusions should be interpreted as historical empirical measurements, not guarantees about future draws.
