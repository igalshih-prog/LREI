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
- Historical structural profile
- 14-ticket portfolio optimization
- Strong-number evaluation
- Chronological walk-forward backtesting
- Random-baseline comparison
- Bootstrap confidence intervals for paired benchmarks
- Ablation testing
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

The purpose of these additional layers is to test whether more sophisticated historical modeling improves empirical backtest behavior. They do not change the mathematical randomness of a fair lottery draw.

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

The repository currently includes a rolling **10-calendar-year** lottery dataset ending with draw 3965 on 13-09-2026.

The current file contains **1,141 draws**, covering the period from 13-09-2016 through 13-09-2026.

The main lottery numbers are 1–37, with six main numbers per draw and a separate strong number.

## Benchmarking

The repository contains separate benchmarks for:

- Regular vs Pro
- Pro vs multiple random baselines
- Elite Pro vs Pro vs multiple random baselines
- Pro signal/feature ablations

Benchmarks report metrics such as average hits per ticket, best-ticket hits, coverage-related behavior, paired differences, and bootstrap confidence intervals where applicable.

All benchmark conclusions should be interpreted as historical empirical measurements, not guarantees about future draws.
