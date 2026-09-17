import random
from pathlib import Path
from statistics import mean

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.elite import EliteProRecommendationEngine
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
    estimates = []
    for _ in range(samples):
        resample = [values[rng.randrange(len(values))] for _ in values]
        estimates.append(mean(resample))
    estimates.sort()
    lower = estimates[int(0.025 * (len(estimates) - 1))]
    upper = estimates[int(0.975 * (len(estimates) - 1))]
    return lower, upper


def test_elite_against_pro_and_multiple_random_baselines_walk_forward():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    assert len(draws) > 200

    # Keep the same 50-draw chronological holdout used by the fast Pro smoke
    # benchmark, while adding Elite as the production candidate.
    holdout = min(50, max(30, len(draws) // 20))
    first_test_index = len(draws) - holdout
    random_portfolios_per_draw = 5

    elite_means = []
    pro_means = []
    random_means = []
    elite_best = []
    pro_best = []
    random_best = []
    elite_vs_random = []
    elite_vs_pro = []

    baseline_rng = random.Random(20260918)
    elite_engine = EliteProRecommendationEngine()
    pro_engine = ProRecommendationEngine()

    for index, target in enumerate(draws[first_test_index:]):
        history = LotteryDataset(draws=draws[: first_test_index + index])
        elite = elite_engine.recommend(history, seed=7000 + index)
        pro = pro_engine.recommend(history, seed=8000 + index)

        elite_hits = _hits(elite.recommended_tickets[:14], target.numbers)
        pro_hits = _hits(pro.recommended_tickets[:14], target.numbers)

        random_results = [
            _hits(_random_portfolio(baseline_rng), target.numbers)
            for _ in range(random_portfolios_per_draw)
        ]
        random_flat = [hit for result in random_results for hit in result]

        elite_mean = mean(elite_hits)
        pro_mean = mean(pro_hits)
        random_mean = mean(random_flat)

        elite_means.append(elite_mean)
        pro_means.append(pro_mean)
        random_means.append(random_mean)
        elite_best.append(max(elite_hits))
        pro_best.append(max(pro_hits))
        random_best.append(mean(max(result) for result in random_results))
        elite_vs_random.append(elite_mean - random_mean)
        elite_vs_pro.append(elite_mean - pro_mean)

    elite_random_ci = _bootstrap_ci(elite_vs_random)
    elite_pro_ci = _bootstrap_ci(elite_vs_pro, seed=20260919)

    print(f"Elite/Pro walk-forward draws: {holdout}")
    print(f"Random portfolios per draw: {random_portfolios_per_draw}")
    print(f"Elite mean hits / ticket: {mean(elite_means):.4f}")
    print(f"Pro mean hits / ticket:   {mean(pro_means):.4f}")
    print(f"Random mean hits / ticket:{mean(random_means):.4f}")
    print(f"Elite - Random: {mean(elite_vs_random):+.4f}")
    print(f"Elite - Pro:    {mean(elite_vs_pro):+.4f}")
    print(f"Elite vs Random 95% CI: [{elite_random_ci[0]:+.4f}, {elite_random_ci[1]:+.4f}]")
    print(f"Elite vs Pro 95% CI:    [{elite_pro_ci[0]:+.4f}, {elite_pro_ci[1]:+.4f}]")
    print(f"Elite best-ticket hits: {mean(elite_best):.4f}")
    print(f"Pro best-ticket hits:   {mean(pro_best):.4f}")
    print(f"Random best-ticket hits:{mean(random_best):.4f}")

    assert len(elite_means) == holdout
    assert len(pro_means) == holdout
    assert len(random_means) == holdout
    assert all(0 <= value <= 6 for value in elite_means)
    assert all(0 <= value <= 6 for value in pro_means)
    assert all(0 <= value <= 6 for value in random_means)
    assert all(value == value for value in elite_vs_random)
    assert all(value == value for value in elite_vs_pro)
