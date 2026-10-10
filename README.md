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

Smart is a separate model-selection layer. Before producing the current recommendation, it uses only earlier draws to compare Regular, Pro, and Elite on a short chronological validation window, then runs the selected model on the full available history. It still returns exactly **14 recommended tickets**.

Smart is deliberately separate from Elite production behavior until its own walk-forward benchmark demonstrates a stable advantage.


The latest clean walk-forward model-selection diagnostic found:

- Regular vs Pro: Pro was lower on that validation window.
- Elite Pro remained close to Regular.
- Adaptive candidate allocation showed only a small, statistically uncertain difference from the conservative allocation.

A separate conservative meta-selector diagnostic showed a positive historical delta when selecting among Regular/Pro/Elite using prior validation draws. LREI is therefore adding this as a separate **Smart** mode for further walk-forward validation rather than silently replacing Elite production behavior.

These are empirical backtest observations only. They are **not evidence of guaranteed predictive advantage**.

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

The repository currently includes a rolling **10-calendar-year** lottery dataset ending with draw 3972 on 06-10-2026.

The current file contains **1,141 consecutive draws**, covering the period from 08-10-2016 through 06-10-2026. When refreshing the file, add newly published draws and remove the oldest draws outside the rolling 10-year window; the test suite checks chronology, contiguous draw IDs, and data freshness.

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
