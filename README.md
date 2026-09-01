# LREI

## Lottery Recommendation & Evaluation Intelligence

LREI is a Python-based lottery recommendation and evaluation system.

The project analyzes historical lottery draws, scores numbers using historical patterns, generates lottery tickets, applies optimization, and evaluates the results against a random baseline using chronological backtesting.

## Main Features

- Historical lottery dataset analysis
- Number frequency analysis
- Recency analysis
- Number scoring
- Lottery ticket generation
- Ticket optimization
- Strong number evaluation
- Chronological backtesting
- Random baseline comparison
- Reproducible evaluation using seeds
- Ablation testing
- Multiple ticket-count evaluation
- SQLite persistence layer
- Command-line interface
- Automated testing with GitHub Actions

## Evaluation Philosophy

LREI does not claim to predict future lottery results with certainty.

The purpose of the system is to evaluate whether its recommendation strategy performs differently from a comparable random baseline when tested on historical data.

The evaluation process uses chronological backtesting to avoid training on future draws.

## Dataset

The project includes a historical lottery dataset containing:

- 4,533 lottery draws

The dataset is used for historical analysis and backtesting.

## Backtesting

LREI performs chronological evaluation.

For each test case:

1. Historical draws before the test draw are used as training data.
2. The recommendation engine scores lottery numbers.
3. Tickets are generated.
4. Tickets are optimized.
5. The recommended tickets are compared with the actual future draw.
6. A random baseline is evaluated using the same ticket-count conditions.
7. Results are aggregated across all test cases.

## Strong Number Evaluation

LREI also evaluates strong-number recommendations.

Historical results are compared against a random strong-number baseline.

Example evaluation output:

```text
LREI STRONG NUMBER
Correct predictions: 6435
Average correct predictions: 1.8214

RANDOM STRONG NUMBER
Correct predictions: 5059
Average correct predictions: 1.4319

LREI advantage: +0.3895
