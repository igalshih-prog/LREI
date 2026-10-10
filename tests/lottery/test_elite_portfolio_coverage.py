import random
from math import comb
from pathlib import Path
from statistics import mean

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.elite import EliteProRecommendationEngine, EliteProConfig
from lrei.lottery.portfolio_coverage import portfolio_coverage


def _random_portfolio(rng, count=14):
    tickets = set()
    while len(tickets) < count:
        tickets.add(tuple(sorted(rng.sample(range(1, 38), 6))))
    return tuple(sorted(tickets))


def test_elite_exact_portfolio_coverage_diagnostic():
    """Compare Elite portfolio coverage with random portfolios under a uniform draw model."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    elite = EliteProRecommendationEngine(
        EliteProConfig(candidate_count=200, max_tickets=14, adaptive_weights=False,
                       adaptive_candidate_weights=False)
    )
    rng = random.Random(20261009)
    elite_four, random_four = [], []
    elite_five, random_five = [], []
    elite_six, random_six = [], []

    for seed in range(8):
        elite_portfolio = elite.recommend(dataset, seed=seed + 30000).recommended_tickets
        random_portfolio = _random_portfolio(rng)
        elite_four.append(portfolio_coverage(elite_portfolio, threshold=4)["probability"])
        random_four.append(portfolio_coverage(random_portfolio, threshold=4)["probability"])
        elite_five.append(portfolio_coverage(elite_portfolio, threshold=5)["probability"])
        random_five.append(portfolio_coverage(random_portfolio, threshold=5)["probability"])
        elite_six.append(portfolio_coverage(elite_portfolio, threshold=6)["probability"])
        random_six.append(portfolio_coverage(random_portfolio, threshold=6)["probability"])

    print("Elite exact portfolio-coverage diagnostic (theoretical uniform draws):")
    print(f"  Elite 4+ coverage={mean(elite_four):.6%}")
    print(f"  Random 4+ coverage={mean(random_four):.6%}")
    print(f"  Elite 5+ coverage={mean(elite_five):.6%}")
    print(f"  Random 5+ coverage={mean(random_five):.6%}")
    print(f"  Elite 4+ minus random={mean(a - b for a, b in zip(elite_four, random_four)):+.6%}")
    print(f"  Elite 5+ minus random={mean(a - b for a, b in zip(elite_five, random_five)):+.6%}")
    print(f"  Elite exact 6/6 coverage={mean(elite_six):.8%}")
    print(f"  Random exact 6/6 coverage={mean(random_six):.8%}")

    expected_main_number_six_of_six_probability = 14 / comb(37, 6)
    assert len(elite_four) == len(random_four) == 8
    assert all(0.0 <= value <= 1.0 for value in elite_four + random_four + elite_five + random_five + elite_six + random_six)
    # This metric counts exact matches of all six main numbers only; the
    # separate strong number is intentionally outside this function.
    # With 14 unique main-number tickets, each portfolio covers 14 outcomes.
    assert all(
        abs(value - expected_main_number_six_of_six_probability) < 1e-15
        for value in elite_six + random_six
    )
