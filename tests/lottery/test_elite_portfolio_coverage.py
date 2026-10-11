import random
from itertools import combinations
from math import comb
from pathlib import Path
from statistics import mean

import pytest

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.elite import EliteProRecommendationEngine, EliteProConfig
from lrei.lottery.portfolio_coverage import portfolio_coverage

pytestmark = pytest.mark.slow


def _random_portfolio(rng, count=14):
    tickets = set()
    while len(tickets) < count:
        tickets.add(tuple(sorted(rng.sample(range(1, 38), 6))))
    return tuple(sorted(tickets))


def _random_compatible_portfolio(rng, count=14, max_overlap=1, max_attempts=250000):
    """Generate a random portfolio subject to the same overlap constraint."""
    tickets = []
    failed_attempts = 0
    while len(tickets) < count:
        candidate = tuple(sorted(rng.sample(range(1, 38), 6)))
        if all(
            len(set(candidate) & set(existing)) <= max_overlap
            for existing in tickets
        ):
            tickets.append(candidate)
            failed_attempts = 0
        else:
            failed_attempts += 1
            if failed_attempts >= max_attempts:
                raise RuntimeError(
                    "Could not construct a random compatible portfolio "
                    f"with max_overlap={max_overlap}"
                )
    return tuple(tickets)


def _bootstrap_ci(values, seed=20261010, samples=5000):
    rng = random.Random(seed)
    estimates = [mean(values[rng.randrange(len(values))] for _ in values) for _ in range(samples)]
    estimates.sort()
    return estimates[int(0.025 * (samples - 1))], estimates[int(0.975 * (samples - 1))]


def test_elite_exact_portfolio_coverage_diagnostic():
    """Compare exact prize-tier main-number coverage across overlap limits and random."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    variants = {"overlap_1": 1, "overlap_2": 2, "overlap_3": 3, "overlap_4": 4}
    thresholds = (4, 5, 6)
    elite_coverage = {
        name: {threshold: [] for threshold in thresholds}
        for name in variants
    }
    random_coverage = {threshold: [] for threshold in thresholds}
    for seed in range(16):
        for name, max_overlap in variants.items():
            engine = EliteProRecommendationEngine(
                EliteProConfig(
                    candidate_count=1000,
                    max_overlap=max_overlap,
                    max_tickets=14,
                    adaptive_weights=False,
                    adaptive_candidate_weights=False,
                )
            )
            portfolio = engine.recommend(dataset, seed=30000 + seed).recommended_tickets
            assert len(portfolio) == 14
            assert len(set(portfolio)) == 14
            assert all(len(set(left) & set(right)) <= max_overlap for left, right in combinations(portfolio, 2))
            for threshold in thresholds:
                elite_coverage[name][threshold].append(
                    portfolio_coverage(portfolio, threshold=threshold)["probability"]
                )

        random_portfolio = _random_portfolio(random.Random(40000 + seed))
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
    assert len(random_coverage[4]) == 16
    assert all(
        abs(value - expected_main_number_six_of_six_probability) < 1e-15
        for name in variants
        for value in elite_coverage[name][6]
    )
    assert all(
        abs(value - expected_main_number_six_of_six_probability) < 1e-15
        for value in random_coverage[6]
    )

    # With pairwise ticket overlap at most one, no six-number draw can match
    # four or more numbers in two different lines. Thus 4+ coverage reaches
    # the exact combinatorial maximum: 14 disjoint single-ticket event sets.
    one_ticket_4plus = comb(6, 4) * comb(31, 2) + comb(6, 5) * comb(31, 1) + 1
    max_4plus_probability = 14 * one_ticket_4plus / comb(37, 6)
    assert all(abs(value - max_4plus_probability) < 1e-15 for value in elite_coverage["overlap_1"][4])

    # With ticket overlap at most three, 5+ events cannot overlap between lines.
    one_ticket_5plus = comb(6, 5) * comb(31, 1) + 1
    max_5plus_probability = 14 * one_ticket_5plus / comb(37, 6)
    for name in ("overlap_1", "overlap_2", "overlap_3"):
        assert all(abs(value - max_5plus_probability) < 1e-15 for value in elite_coverage[name][5])

    for name in variants:
        paired = [a - b for a, b in zip(elite_coverage[name][4], random_coverage[4])]
        ci = _bootstrap_ci(paired, seed=20261010 + variants[name])
        print(f"    4+ difference vs random: {mean(paired):+.6%}, seed-bootstrap CI=[{ci[0]:+.6%}, {ci[1]:+.6%}]")

    # Full jackpot includes the separate 1-in-7 strong number.
    full_jackpot_probability = 14 / (comb(37, 6) * 7)
    print(
        f"  theoretical 6/6 + strong-number probability for 14 distinct lines: "
        f"1 in {1 / full_jackpot_probability:,.0f}"
    )


def test_elite_any_prize_coverage_diagnostic():
    """Compare exact chance of any prize (3+ main hits) across overlap caps."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    variants = {"overlap_1": 1, "overlap_2": 2, "overlap_3": 3, "overlap_4": 4}
    coverage = {name: [] for name in variants}
    random_coverage = []
    constrained_random_coverage = []

    for seed in range(6):
        for name, max_overlap in variants.items():
            engine = EliteProRecommendationEngine(
                EliteProConfig(
                    candidate_count=1000,
                    max_overlap=max_overlap,
                    max_tickets=14,
                    adaptive_weights=False,
                    adaptive_candidate_weights=False,
                )
            )
            portfolio = engine.recommend(dataset, seed=51000 + seed).recommended_tickets
            assert len(portfolio) == 14
            assert len(set(portfolio)) == 14
            assert all(
                len(set(left) & set(right)) <= max_overlap
                for left, right in combinations(portfolio, 2)
            )
            coverage[name].append(
                portfolio_coverage(portfolio, threshold=3)["probability"]
            )

        random_portfolio = _random_portfolio(random.Random(52000 + seed))
        random_coverage.append(
            portfolio_coverage(random_portfolio, threshold=3)["probability"]
        )

        constrained_portfolio = _random_compatible_portfolio(
            random.Random(53000 + seed), max_overlap=1
        )
        assert len(constrained_portfolio) == 14
        assert len(set(constrained_portfolio)) == 14
        assert all(
            len(set(left) & set(right)) <= 1
            for left, right in combinations(constrained_portfolio, 2)
        )
        constrained_random_coverage.append(
            portfolio_coverage(constrained_portfolio, threshold=3)["probability"]
        )

    print("Exact probability of at least one prize (3+ main hits) under uniform 6/37 draws:")
    print(f"  random, unconstrained: {mean(random_coverage):.6%}")
    print(f"  random, max_overlap=1: {mean(constrained_random_coverage):.6%}")
    for name, values in coverage.items():
        paired = [value - baseline for value, baseline in zip(values, random_coverage)]
        ci = _bootstrap_ci(paired, seed=20261020 + variants[name])
        print(
            f"  {name}: {mean(values):.6%}, "
            f"delta vs random={mean(paired):+.6%}, "
            f"paired bootstrap 95% CI=[{ci[0]:+.6%}, {ci[1]:+.6%}]"
        )

    elite_vs_constrained_random = [
        elite - baseline
        for elite, baseline in zip(coverage["overlap_1"], constrained_random_coverage)
    ]
    constrained_ci = _bootstrap_ci(elite_vs_constrained_random, seed=20261030)
    print(
        f"  overlap_1 LREI - constrained random="
        f"{mean(elite_vs_constrained_random):+.6%}, "
        f"paired bootstrap 95% CI=[{constrained_ci[0]:+.6%}, {constrained_ci[1]:+.6%}]"
    )

    assert len(random_coverage) == 6
    assert len(constrained_random_coverage) == 6
    assert all(len(values) == 6 for values in coverage.values())
    assert all(0.0 <= value <= 1.0 for value in random_coverage + constrained_random_coverage)
    assert all(0.0 <= value <= 1.0 for values in coverage.values() for value in values)
