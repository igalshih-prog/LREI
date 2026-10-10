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
    """Compare exact prize-tier main-number coverage across overlap limits and random."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    variants = {"overlap_2": 2, "overlap_3": 3, "overlap_4": 4}
    thresholds = (4, 5, 6)
    elite_coverage = {
        name: {threshold: [] for threshold in thresholds}
        for name in variants
    }
    random_coverage = {threshold: [] for threshold in thresholds}
    rng = random.Random(20261009)

    for seed in range(8):
        for name, max_overlap in variants.items():
            engine = EliteProRecommendationEngine(
                EliteProConfig(
                    candidate_count=300,
                    max_overlap=max_overlap,
                    max_tickets=14,
                    adaptive_weights=False,
                    adaptive_candidate_weights=False,
                )
            )
            portfolio = engine.recommend(dataset, seed=30000 + seed).recommended_tickets
            assert len(portfolio) == 14
            assert len(set(portfolio)) == 14
            for threshold in thresholds:
                elite_coverage[name][threshold].append(
                    portfolio_coverage(portfolio, threshold=threshold)["probability"]
                )

        random_portfolio = _random_portfolio(rng)
        assert len(random_portfolio) == 14
        for threshold in thresholds:
            random_coverage[threshold].append(
                portfolio_coverage(random_portfolio, threshold=threshold)["probability"]
            )

    print("Exact portfolio coverage under uniformly random 6/37 main-number draws:")
    for name in variants:
        four = elite_coverage[name][4]
        five = elite_coverage[name][5]
        print(
            f"  {name}: 4+={mean(four):.6%}, 5+={mean(five):.6%}, "
            f"6/6-main={mean(elite_coverage[name][6]):.8%}"
        )
        print(
            f"    minus random: 4+={mean(a - b for a, b in zip(four, random_coverage[4])):+.6%}, "
            f"5+={mean(a - b for a, b in zip(five, random_coverage[5])):+.6%}"
        )
    print(
        f"  random: 4+={mean(random_coverage[4]):.6%}, "
        f"5+={mean(random_coverage[5]):.6%}, "
        f"6/6-main={mean(random_coverage[6]):.8%}"
    )

    expected_main_number_six_of_six_probability = 14 / comb(37, 6)
    assert len(random_coverage[4]) == 8
    assert all(
        abs(value - expected_main_number_six_of_six_probability) < 1e-15
        for name in variants
        for value in elite_coverage[name][6]
    )
    assert all(
        abs(value - expected_main_number_six_of_six_probability) < 1e-15
        for value in random_coverage[6]
    )

    # Full jackpot includes the separate 1-in-7 strong number.
    full_jackpot_probability = 14 / (comb(37, 6) * 7)
    print(
        f"  theoretical 6/6 + strong-number probability for 14 distinct lines: "
        f"1 in {1 / full_jackpot_probability:,.0f}"
    )
