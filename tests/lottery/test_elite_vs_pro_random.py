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

    expected_random_mean = 6.0 * 6.0 / 37.0

    print(f"Elite/Pro walk-forward draws: {holdout}")
    print(f"Theoretical random mean hits / ticket: {expected_random_mean:.4f}")
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

def test_elite_robust_baseline_walk_forward_diagnostic():
    """Use a longer holdout and repeated random portfolios for a less noisy Elite check."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    random_portfolios_per_draw = 5
    elite_means = []
    random_means = []
    paired = []

    engine = EliteProRecommendationEngine()
    baseline_rng = random.Random(20260920)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        elite = engine.recommend(history, seed=96000 + offset)
        elite_hits = _hits(elite.recommended_tickets, target.numbers)
        random_results = [
            _hits(_random_portfolio(baseline_rng), target.numbers)
            for _ in range(random_portfolios_per_draw)
        ]
        random_mean = mean(hit for result in random_results for hit in result)
        elite_mean = mean(elite_hits)
        elite_means.append(elite_mean)
        random_means.append(random_mean)
        paired.append(elite_mean - random_mean)

    ci = _bootstrap_ci(paired, seed=20260921)
    print("Elite robust baseline diagnostic:")
    print(f"  holdout={holdout}")
    print(f"  Elite mean hits/ticket={mean(elite_means):.4f}")
    print(f"  Random mean hits/ticket={mean(random_means):.4f}")
    print(f"  Elite-Random={mean(paired):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(paired) == holdout
    assert all(value == value for value in paired)


def test_elite_candidate_allocation_robust_walk_forward_diagnostic():
    """Compare equal vs EWMA-heavy candidate allocation on a longer holdout."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    variants = {
        "equal": (1.0, 1.0, 1.0),
        "ewma_heavy": (1.0, 1.0, 2.0),
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, weights in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                candidate_rank_weight=weights[0],
                candidate_raw_weight=weights[1],
                candidate_ewma_weight=weights[2],
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=97000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    difference = [ewma - equal for ewma, equal in zip(results["ewma_heavy"], results["equal"])]
    ci = _bootstrap_ci(difference, seed=20260922)

    print("Elite candidate-allocation robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  EWMA-heavy - equal={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_adaptive_candidate_allocation_robust_walk_forward_diagnostic():
    """Compare opt-in adaptive candidate allocation with equal allocation."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {
        "equal": False,
        "adaptive": True,
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, adaptive in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                adaptive_candidate_weights=adaptive,
                candidate_calibration_draws=20,
                candidate_calibration_candidate_count=100,
                candidate_adaptive_shrinkage=0.50,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=98000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    difference = [adaptive - equal for adaptive, equal in zip(results["adaptive"], results["equal"])]
    ci = _bootstrap_ci(difference, seed=20260923)

    print("Elite adaptive candidate-allocation robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  adaptive - equal={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)
