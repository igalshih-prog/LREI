import random
from pathlib import Path
from statistics import mean

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.pro import ProRecommendationEngine


def _hits(tickets, actual):
    actual_set = set(actual)
    return [len(set(ticket) & actual_set) for ticket in tickets]


def _random_portfolio(rng, max_number=37, ticket_size=6, ticket_count=14):
    return tuple(
        tuple(sorted(rng.sample(range(1, max_number + 1), ticket_size)))
        for _ in range(ticket_count)
    )


def _bootstrap_ci(values, seed=20260917, samples=5000):
    rng = random.Random(seed)
    if not values:
        return 0.0, 0.0
    estimates = []
    for _ in range(samples):
        resample = [values[rng.randrange(len(values))] for _ in values]
        estimates.append(mean(resample))
    estimates.sort()
    lower = estimates[int(0.025 * (len(estimates) - 1))]
    upper = estimates[int(0.975 * (len(estimates) - 1))]
    return lower, upper


def test_pro_against_multiple_random_baselines_walk_forward():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    assert len(draws) > 200

    # Larger holdout than the initial smoke test. Several independent random
    # portfolios per target reduce the noise of any single random sample.
    holdout = min(100, max(50, len(draws) // 12))
    first_test_index = len(draws) - holdout
    random_portfolios_per_draw = 5

    pro_average_hits = []
    random_average_hits = []
    paired_differences = []
    pro_best_hits = []
    random_best_hits = []

    baseline_rng = random.Random(20260916)
    pro_engine = ProRecommendationEngine()

    for index, target in enumerate(draws[first_test_index:]):
        history = LotteryDataset(draws=draws[: first_test_index + index])
        pro = pro_engine.recommend(history, seed=5000 + index)
        pro_hits = _hits(pro.recommended_tickets[:14], target.numbers)

        random_results = []
        for _ in range(random_portfolios_per_draw):
            portfolio = _random_portfolio(baseline_rng)
            random_results.append(_hits(portfolio, target.numbers))

        random_flat = [hit for result in random_results for hit in result]
        pro_mean = mean(pro_hits)
        random_mean = mean(random_flat)

        pro_average_hits.append(pro_mean)
        random_average_hits.append(random_mean)
        paired_differences.append(pro_mean - random_mean)
        pro_best_hits.append(max(pro_hits))
        random_best_hits.append(mean(max(result) for result in random_results))

    positive_draws = sum(value > 0 for value in paired_differences)
    tied_draws = sum(value == 0 for value in paired_differences)
    difference_ci = _bootstrap_ci(paired_differences)

    expected_random_mean = 6.0 * 6.0 / 37.0

    print(f"Walk-forward draws: {holdout}")
    print(f"Theoretical random mean hits / ticket: {expected_random_mean:.4f}")
    print(f"Random portfolios per draw: {random_portfolios_per_draw}")
    print(f"Pro mean hits / ticket: {mean(pro_average_hits):.4f}")
    print(f"Random mean hits / ticket: {mean(random_average_hits):.4f}")
    print(f"Mean paired difference: {mean(paired_differences):+.4f}")
    print(f"95% bootstrap CI for paired difference: [{difference_ci[0]:+.4f}, {difference_ci[1]:+.4f}]")
    print(f"Draws where Pro > random mean: {positive_draws}/{holdout}")
    print(f"Draws tied: {tied_draws}/{holdout}")
    print(f"Pro best-ticket hits: {mean(pro_best_hits):.4f}")
    print(f"Random best-ticket hits: {mean(random_best_hits):.4f}")

    assert len(pro_average_hits) == holdout
    assert len(random_average_hits) == holdout
    assert len(paired_differences) == holdout
    assert all(0 <= value <= 6 for value in pro_average_hits)
    assert all(0 <= value <= 6 for value in random_average_hits)
    assert all(value == value for value in paired_differences)
