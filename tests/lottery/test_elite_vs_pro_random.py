import pytest
import random
from pathlib import Path
from statistics import mean

pytestmark = pytest.mark.slow

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.elite import EliteProConfig, EliteProRecommendationEngine
from lrei.lottery.pro import ProRecommendationEngine


def _hits(tickets, actual):
    actual_set = set(actual)
    return [len(set(ticket) & actual_set) for ticket in tickets]


def _random_portfolio(rng, max_number=37, ticket_size=6, ticket_count=14):
    return tuple(
        tuple(sorted(rng.sample(range(1, max_number + 1), ticket_size)))
        for _ in range(ticket_count)
    )



def _random_diversified_portfolio(rng, max_number=37, ticket_size=6, ticket_count=14, max_overlap=4):
    """Generate a random 14-ticket portfolio with the same overlap cap as Elite/Pro."""
    tickets = []
    attempts = 0
    while len(tickets) < ticket_count and attempts < 10000:
        attempts += 1
        ticket = tuple(sorted(rng.sample(range(1, max_number + 1), ticket_size)))
        if all(len(set(ticket) & set(other)) <= max_overlap for other in tickets):
            tickets.append(ticket)
    if len(tickets) != ticket_count:
        raise AssertionError("Could not build constrained random portfolio")
    return tuple(tickets)

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
    holdout = min(95, max(50, len(draws) // 12))
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
                candidate_calibration_candidate_count=75,
                candidate_calibration_origins=3,
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


def test_elite_number_signal_strength_robust_walk_forward_diagnostic():
    """Measure whether stronger historical number signals help on unseen draws."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    strengths = (0.0, 0.25, 0.40, 0.50, 0.60, 0.75)
    results = {strength: [] for strength in strengths}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for strength in strengths:
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                number_signal_strength=strength,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=99000 + offset)
            results[strength].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    baseline = results[0.0]
    for strength in strengths:
        difference = [value - base for value, base in zip(results[strength], baseline)]
        ci = _bootstrap_ci(difference, seed=20260924 + int(strength * 100))
        print(f"Elite number-signal strength {strength:.2f}: hits={mean(results[strength]):.4f}")
        if strength:
            print(f"  vs 0.00={mean(difference):+.4f}, 95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(value == value for values in results.values() for value in values)


def test_portfolio_hit_threshold_walk_forward_diagnostic():
    """Measure the frequency of 3+, 4+, and 5+ hit tickets on unseen draws."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    engines = {
        "elite": EliteProRecommendationEngine(),
        "pro": ProRecommendationEngine(),
    }
    counts = {name: {threshold: [] for threshold in (3, 4, 5)} for name in engines}
    counts["random"] = {threshold: [] for threshold in (3, 4, 5)}
    rng = random.Random(20260925)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, engine in engines.items():
            result = engine.recommend(history, seed=101000 + offset)
            hits = _hits(result.recommended_tickets[:14], target.numbers)
            for threshold in counts[name]:
                counts[name][threshold].append(int(max(hits) >= threshold))

        random_hits = [
            _hits(_random_portfolio(rng), target.numbers)
            for _ in range(5)
        ]
        for threshold in counts["random"]:
            counts["random"][threshold].append(
                mean(int(max(hits) >= threshold) for hits in random_hits)
            )

    print("Portfolio hit-threshold diagnostic:")
    for name, thresholds in counts.items():
        parts = [
            f"{threshold}+={mean(values):.4f}"
            for threshold, values in thresholds.items()
        ]
        print(f"  {name}: " + ", ".join(parts))

    assert all(len(values) == holdout for thresholds in counts.values() for values in thresholds.values())
    assert all(value == value for thresholds in counts.values() for values in thresholds.values() for value in values)


def test_elite_tail_focused_portfolio_selection_walk_forward_diagnostic():
    """Compare portfolio settings aimed at preserving multi-hit tail outcomes."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(200, max(100, len(draws) // 6))
    start = len(draws) - holdout
    variants = {
        "current": (4, 0.035, 0.018),
        "tighter_overlap": (3, 0.035, 0.018),
        "coverage_heavier": (4, 0.060, 0.018),
    }
    results = {
        name: {threshold: [] for threshold in (3, 4, 5)}
        for name in variants
    }

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, (max_overlap, coverage_weight, overlap_penalty) in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_overlap=max_overlap,
                max_tickets=14,
                portfolio_coverage_weight=coverage_weight,
                portfolio_overlap_penalty=overlap_penalty,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=102000 + offset)
            hits = _hits(result.recommended_tickets, target.numbers)
            for threshold in results[name]:
                results[name][threshold].append(int(max(hits) >= threshold))

    print("Elite tail-focused portfolio diagnostic:")
    for name, thresholds in results.items():
        print(
            f"  {name}: "
            + ", ".join(f"{threshold}+={mean(values):.4f}" for threshold, values in thresholds.items())
        )

    assert all(
        len(values) == holdout
        for thresholds in results.values()
        for values in thresholds.values()
    )
    assert all(
        value == value
        for thresholds in results.values()
        for values in thresholds.values()
        for value in values
    )


def test_elite_momentum_signal_robust_walk_forward_diagnostic():
    """Measure whether recent-vs-prior frequency momentum helps on unseen draws."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    strengths = (0.0, 0.10, 0.20, 0.30, 0.40)
    results = {strength: [] for strength in strengths}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for strength in strengths:
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                momentum_strength=strength,
                momentum_window=60,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=103000 + offset)
            results[strength].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    baseline = results[0.0]
    for strength in strengths:
        difference = [value - base for value, base in zip(results[strength], baseline)]
        ci = _bootstrap_ci(difference, seed=20260926 + int(strength * 100))
        print(f"Elite momentum strength {strength:.2f}: hits={mean(results[strength]):.4f}")
        if strength:
            print(f"  vs 0.00={mean(difference):+.4f}, 95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(value == value for values in results.values() for value in values)


def test_elite_portfolio_objective_robust_walk_forward_diagnostic():
    """Compare portfolio diversification settings on a longer walk-forward holdout."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    variants = {
        "current": (0.035, 0.018),
        "coverage_strong": (0.050, 0.018),
        "balanced": (0.025, 0.025),
        "overlap_strong": (0.035, 0.030),
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, (coverage, overlap_penalty) in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                portfolio_coverage_weight=coverage,
                portfolio_overlap_penalty=overlap_penalty,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=99000 + offset)
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    print("Elite portfolio-objective robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    for name in variants:
        if name != "current":
            difference = [value - current for value, current in zip(results[name], results["current"])]
            ci = _bootstrap_ci(difference, seed=20260924 + list(variants).index(name))
            print(f"  {name} - current={mean(difference):+.4f}, 95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_momentum_ablation_robust_walk_forward_diagnostic():
    """Measure whether a recent-vs-prior momentum signal adds stable walk-forward value."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    variants = {
        "off": 0.0,
        "light": 0.10,
        "medium": 0.20,
        "strong": 0.35,
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, strength in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                momentum_strength=strength,
                momentum_window=60,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=99000 + offset)
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    print("Elite momentum robust ablation:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    for name in ("light", "medium", "strong"):
        difference = [value - base for value, base in zip(results[name], results["off"])]
        ci = _bootstrap_ci(difference, seed=20260930 + len(name))
        print(f"  {name} - off={mean(difference):+.4f}")
        print(f"  {name} 95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_score_calibration_robust_walk_forward_diagnostic():
    """Measure whether empirical score-band calibration adds stable walk-forward value."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(70, max(50, len(draws) // 16))
    start = len(draws) - holdout
    variants = {
        "off": False,
        "calibrated": True,
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, enabled in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                score_calibration=enabled,
                score_calibration_draws=30,
                score_calibration_bins=5,
                score_calibration_shrinkage=0.75,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=99100 + offset)
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [calibrated - off for calibrated, off in zip(results["calibrated"], results["off"])]
    ci = _bootstrap_ci(difference, seed=20260931)

    print("Elite score-calibration robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  calibrated - off={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_adaptive_momentum_robust_walk_forward_diagnostic():
    """Compare learned momentum strength with fixed no-momentum baseline."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    results = {"off": [], "adaptive": []}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        configs = {
            "off": {"adaptive_momentum": False, "momentum_strength": 0.0},
            "adaptive": {
                "adaptive_momentum": True,
                "momentum_strength": 0.0,
                "momentum_candidates": (0.0, 0.10, 0.20, 0.30),
                "momentum_calibration_draws": 20,
            },
        }
        for name, params in configs.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                **params,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=104000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    difference = [adaptive - off for adaptive, off in zip(results["adaptive"], results["off"])]
    ci = _bootstrap_ci(difference, seed=20260932)

    print("Elite adaptive-momentum robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  adaptive - off={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_consensus_scoring_robust_walk_forward_diagnostic():
    """Compare opt-in cross-signal consensus scoring with the current baseline."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {"off": 0.0, "light": 0.25, "medium": 0.50}
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, strength in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                consensus_strength=strength,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=105000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    baseline = results["off"]
    for name, values in results.items():
        difference = [value - base for value, base in zip(values, baseline)]
        print(f"Elite consensus {name}: hits={mean(values):.4f}")
        if name != "off":
            ci = _bootstrap_ci(difference, seed=20260933 + int(variants[name] * 100))
            print(f"  vs off={mean(difference):+.4f}, 95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(value == value for values in results.values() for value in values)


def test_elite_feature_ablation_walk_forward_diagnostic():
    """Compare opt-in Elite features on a longer chronological holdout."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(70, max(45, len(draws) // 16))
    start = len(draws) - holdout
    variants = {
        "baseline": {},
        "consensus": {"consensus_strength": 0.50},
        "momentum": {"adaptive_momentum": True, "momentum_calibration_draws": 20},
        "score_calibration": {"score_calibration": True, "score_calibration_draws": 25},
        "adaptive_candidates": {"adaptive_candidate_weights": True, "candidate_calibration_draws": 20},
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                **kwargs,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=99000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    print("Elite feature ablation:")
    baseline_mean = mean(results["baseline"])
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}, delta={mean(values) - baseline_mean:+.4f}")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_signal_enhancement_robust_walk_forward_diagnostic():
    """Compare opt-in signal enhancements on a chronological holdout."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {
        "current": {},
        "momentum_adaptive": {
            "adaptive_momentum": True,
            "momentum_calibration_draws": 20,
        },
        "score_calibration": {
            "score_calibration": True,
            "score_calibration_draws": 30,
            "score_calibration_bins": 5,
        },
        "consensus": {
            "consensus_strength": 0.50,
        },
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in variants.items():
            config = EliteProConfig(candidate_count=200, max_tickets=14, **kwargs)
            result = EliteProRecommendationEngine(config).recommend(history, seed=99000 + offset)
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    baseline = results["current"]
    print("Elite signal-enhancement robust diagnostic:")
    for name, values in results.items():
        difference = [value - base for value, base in zip(values, baseline)]
        ci = _bootstrap_ci(difference, seed=20260924 + list(variants).index(name))
        print(f"  {name}: hits={mean(values):.4f}")
        if name != "current":
            print(f"    vs current={mean(difference):+.4f}")
            print(f"    95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_prize_tier_robust_walk_forward_diagnostic():
    """Measure whether Elite changes the distribution of high-hit tickets, not only the mean."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    random_portfolios_per_draw = 5
    tiers = (3, 4, 5, 6)
    elite_counts = {tier: [] for tier in tiers}
    random_counts = {tier: [] for tier in tiers}
    paired = {tier: [] for tier in tiers}
    engine = EliteProRecommendationEngine()
    baseline_rng = random.Random(20260934)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        elite = engine.recommend(history, seed=106000 + offset)
        elite_hits = _hits(elite.recommended_tickets, target.numbers)
        random_hits = [
            hit
            for _ in range(random_portfolios_per_draw)
            for hit in _hits(_random_portfolio(baseline_rng), target.numbers)
        ]
        for tier in tiers:
            elite_value = sum(hit >= tier for hit in elite_hits)
            random_value = sum(hit >= tier for hit in random_hits) / random_portfolios_per_draw
            elite_counts[tier].append(elite_value)
            random_counts[tier].append(random_value)
            paired[tier].append(elite_value - random_value)

    print("Elite prize-tier robust diagnostic:")
    for tier in tiers:
        ci = _bootstrap_ci(paired[tier], seed=20260940 + tier)
        print(
            f"  >= {tier} hits: Elite={mean(elite_counts[tier]):.4f}, "
            f"Random={mean(random_counts[tier]):.4f}, "
            f"delta={mean(paired[tier]):+.4f}, "
            f"95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]"
        )

    assert all(len(values) == holdout for values in paired.values())
    assert all(value == value for values in paired.values() for value in values)


def test_elite_multi_origin_robust_walk_forward_diagnostic():
    """Evaluate Elite across several historical origins to detect regime-specific overfitting."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = 40
    origins = [
        len(draws) - 40,
        len(draws) - 120,
        len(draws) - 200,
        len(draws) - 280,
    ]
    origins = [origin for origin in origins if origin >= 250 and origin + holdout <= len(draws)]
    elite_results = []
    random_results = []
    paired = []

    for origin_index, start in enumerate(origins):
        baseline_rng = random.Random(203000 + origin_index)
        for offset, target in enumerate(draws[start:start + holdout]):
            history = LotteryDataset(draws=draws[:start + offset])
            elite = EliteProRecommendationEngine().recommend(history, seed=107000 + origin_index * 100 + offset)
            elite_mean = mean(_hits(elite.recommended_tickets, target.numbers))
            random_mean = mean(
                hit
                for _ in range(5)
                for hit in _hits(_random_portfolio(baseline_rng), target.numbers)
            )
            elite_results.append(elite_mean)
            random_results.append(random_mean)
            paired.append(elite_mean - random_mean)

    ci = _bootstrap_ci(paired, seed=20260941)
    print("Elite multi-origin robust diagnostic:")
    print(f"  origins={len(origins)}, holdout_per_origin={holdout}")
    print(f"  Elite mean hits/ticket={mean(elite_results):.4f}")
    print(f"  Random mean hits/ticket={mean(random_results):.4f}")
    print(f"  Elite-Random={mean(paired):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(paired) == len(origins) * holdout
    assert all(value == value for value in paired)


def test_final_engine_comparison_robust_walk_forward():
    """Final apples-to-apples comparison of all production candidates."""
    from lrei.lottery.recommendation import RecommendationEngine
    from lrei.lottery.statistics import LotteryStatistics

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    names = ("regular", "pro", "elite", "elite_adaptive", "random")
    results = {name: [] for name in names}
    best_results = {name: [] for name in names}
    random_rng = random.Random(20260924)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        engines = {
            "regular": RecommendationEngine(),
            "pro": ProRecommendationEngine(),
            "elite": EliteProRecommendationEngine(),
            "elite_adaptive": EliteProRecommendationEngine(
                __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                    adaptive_candidate_weights=True,
                    candidate_calibration_draws=20,
                    candidate_calibration_candidate_count=120,
                )
            ),
        }
        for name, engine in engines.items():
            if name == "regular":
                result = engine.recommend(LotteryStatistics.from_dataset(history), ticket_count=14, seed=99000 + offset)
            else:
                result = engine.recommend(history, seed=99000 + offset)
            hits = _hits(result.recommended_tickets, target.numbers)
            results[name].append(mean(hits))
            best_results[name].append(max(hits))

        random_hits = _hits(_random_portfolio(random_rng), target.numbers)
        results["random"].append(mean(random_hits))
        best_results["random"].append(max(random_hits))

    print("FINAL engine comparison:")
    for name in names:
        print(f"  {name}: mean_hits={mean(results[name]):.4f}, best_ticket={mean(best_results[name]):.4f}")
    for name in ("regular", "pro", "elite", "elite_adaptive"):
        diff = [a - b for a, b in zip(results[name], results["random"])]
        ci = _bootstrap_ci(diff, seed=20260925 + names.index(name))
        print(f"  {name} - random={mean(diff):+.4f}, 95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_adaptive_candidate_allocation_long_robust_diagnostic():
    """Longer walk-forward check for adaptive candidate allocation."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(60, len(draws) // 12))
    start = len(draws) - holdout
    results = {"equal": [], "adaptive": []}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        configs = {
            "equal": dict(adaptive_candidate_weights=False),
            "adaptive": dict(
                adaptive_candidate_weights=True,
                candidate_calibration_draws=20,
                candidate_calibration_candidate_count=75,
                candidate_adaptive_shrinkage=0.50,
            ),
        }
        for name, options in configs.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=150,
                max_tickets=14,
                **options,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=99000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    difference = [adaptive - equal for adaptive, equal in zip(results["adaptive"], results["equal"])]
    ci = _bootstrap_ci(difference, seed=20260924)

    print("Elite adaptive candidate-allocation long robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  adaptive - equal={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_against_diversified_random_baseline_walk_forward():
    """Compare Elite with random portfolios subject to the same overlap constraint."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    elite_results = []
    random_results = []
    paired = []
    rng = random.Random(20260942)

    engine = EliteProRecommendationEngine()
    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        elite = engine.recommend(history, seed=108000 + offset)
        elite_mean = mean(_hits(elite.recommended_tickets, target.numbers))
        random_portfolios = [
            _random_diversified_portfolio(rng)
            for _ in range(5)
        ]
        random_mean = mean(
            hit
            for portfolio in random_portfolios
            for hit in _hits(portfolio, target.numbers)
        )
        elite_results.append(elite_mean)
        random_results.append(random_mean)
        paired.append(elite_mean - random_mean)

    ci = _bootstrap_ci(paired, seed=20260943)
    print("Elite vs diversified-random robust diagnostic:")
    print(f"  holdout={holdout}")
    print(f"  Elite mean hits/ticket={mean(elite_results):.4f}")
    print(f"  Diversified random mean hits/ticket={mean(random_results):.4f}")
    print(f"  Elite-random={mean(paired):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(paired) == holdout
    assert all(value == value for value in paired)


def test_elite_momentum_robust_baseline_diagnostic():
    """Measure the promising adaptive-momentum variant directly against random."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    random_portfolios_per_draw = 3
    variants = {
        "current": {},
        "momentum_adaptive": {"adaptive_momentum": True, "momentum_calibration_draws": 20},
    }
    results = {name: [] for name in variants}
    random_means = []
    paired = {name: [] for name in variants}

    baseline_rng = random.Random(20260925)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=120,
                max_tickets=14,
                **kwargs,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=99200 + offset)
            mean_hits = mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            results[name].append(mean_hits)

        random_results = [
            _hits(_random_portfolio(baseline_rng), target.numbers)
            for _ in range(random_portfolios_per_draw)
        ]
        random_mean = mean(hit for result in random_results for hit in result)
        random_means.append(random_mean)
        for name in variants:
            paired[name].append(results[name][-1] - random_mean)

    print("Elite momentum robust baseline diagnostic:")
    print(f"  holdout={holdout}")
    print(f"  Random mean hits/ticket={mean(random_means):.4f}")
    for name in variants:
        ci = _bootstrap_ci(paired[name], seed=20260925 + list(variants).index(name))
        print(f"  {name} mean hits/ticket={mean(results[name]):.4f}")
        print(f"  {name} - Random={mean(paired[name]):+.4f}")
        print(f"  {name} vs Random 95% CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert len(random_means) == holdout


def test_elite_tail_hit_robust_walk_forward_diagnostic():
    """Measure portfolio tail hits (3+, 4+, 5+, 6) against random portfolios."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    random_portfolios_per_draw = 5
    thresholds = (3, 4, 5, 6)
    elite_counts = {threshold: [] for threshold in thresholds}
    random_counts = {threshold: [] for threshold in thresholds}
    engine = EliteProRecommendationEngine()
    baseline_rng = random.Random(20260924)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        elite = engine.recommend(history, seed=99100 + offset)
        elite_hits = _hits(elite.recommended_tickets, target.numbers)
        random_results = [
            _hits(_random_portfolio(baseline_rng), target.numbers)
            for _ in range(random_portfolios_per_draw)
        ]
        random_hits = [hit for result in random_results for hit in result]

        for threshold in thresholds:
            elite_counts[threshold].append(sum(hit >= threshold for hit in elite_hits))
            # Normalize the five random portfolios back to the same 14-ticket
            # portfolio size as Elite before comparing tail-hit counts.
            random_counts[threshold].append(
                sum(hit >= threshold for hit in random_hits) / random_portfolios_per_draw
            )

    print("Elite tail-hit robust diagnostic (normalized to 14 tickets):")
    for threshold in thresholds:
        elite_rate = mean(elite_counts[threshold])
        random_rate = mean(random_counts[threshold])
        print(
            f"  {threshold}+ hits/draw: Elite={elite_rate:.4f} "
            f"Random={random_rate:.4f} difference={elite_rate-random_rate:+.4f}"
        )

    assert all(len(values) == holdout for values in elite_counts.values())
    assert all(len(values) == holdout for values in random_counts.values())
    assert all(all(value >= 0 for value in values) for values in elite_counts.values())


def test_elite_hit_tail_distribution_robust_diagnostic():
    """Measure 3+/4+/5+/6-hit portfolio rates against repeated random baselines."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    random_portfolios_per_draw = 5

    elite_rates = {threshold: [] for threshold in (3, 4, 5, 6)}
    random_rates = {threshold: [] for threshold in (3, 4, 5, 6)}
    paired = {threshold: [] for threshold in (3, 4, 5, 6)}

    engine = EliteProRecommendationEngine()
    baseline_rng = random.Random(20260925)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        elite = engine.recommend(history, seed=105000 + offset)
        elite_hits = _hits(elite.recommended_tickets, target.numbers)
        random_results = [
            _hits(_random_portfolio(baseline_rng), target.numbers)
            for _ in range(random_portfolios_per_draw)
        ]

        for threshold in (3, 4, 5, 6):
            elite_rate = sum(hit >= threshold for hit in elite_hits) / len(elite_hits)
            random_rate = mean(
                sum(hit >= threshold for hit in result) / len(result)
                for result in random_results
            )
            elite_rates[threshold].append(elite_rate)
            random_rates[threshold].append(random_rate)
            paired[threshold].append(elite_rate - random_rate)

    print("Elite hit-tail robust diagnostic:")
    for threshold in (3, 4, 5, 6):
        ci = _bootstrap_ci(paired[threshold], seed=20260925 + threshold)
        print(
            f"  {threshold}+: Elite={mean(elite_rates[threshold]):.4f}, "
            f"Random={mean(random_rates[threshold]):.4f}, "
            f"diff={mean(paired[threshold]):+.4f}, "
            f"95% CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]"
        )

    assert all(len(values) == holdout for values in paired.values())
    assert all(all(0.0 <= value <= 1.0 for value in values) for values in elite_rates.values())
    assert all(all(0.0 <= value <= 1.0 for value in values) for values in random_rates.values())


def test_elite_consensus_robust_walk_forward_diagnostic():
    """Compare production Elite with opt-in consensus on a long walk-forward holdout."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(60, len(draws) // 12))
    start = len(draws) - holdout
    results = {"current": [], "consensus": []}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        configs = {
            "current": EliteProRecommendationEngine(),
            "consensus": EliteProRecommendationEngine(
                __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                    consensus_strength=0.50,
                )
            ),
        }
        for name, engine in configs.items():
            result = engine.recommend(history, seed=99000 + offset)
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [b - a for a, b in zip(results["current"], results["consensus"])]
    ci = _bootstrap_ci(difference, seed=20260924)

    print("Elite consensus robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  consensus - current={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_tail_hit_rate_diagnostic():
    """Measure rare high-hit outcomes, not only average hits per ticket."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    variants = {
        "current": {},
        "consensus_light": {"consensus_strength": 0.25},
        "consensus_medium": {"consensus_strength": 0.50},
        "adaptive_candidates": {
            "adaptive_candidate_weights": True,
            "candidate_calibration_draws": 20,
            "candidate_calibration_candidate_count": 100,
        },
    }
    results = {
        name: {threshold: [] for threshold in (3, 4, 5, 6)}
        for name in variants
    }

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                **kwargs,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=106000 + offset)
            hits = [len(set(ticket) & actual) for ticket in result.recommended_tickets]
            best = max(hits)
            for threshold in results[name]:
                results[name][threshold].append(1 if best >= threshold else 0)

    print("Elite tail-hit diagnostic:")
    for name in variants:
        rates = {
            threshold: mean(results[name][threshold])
            for threshold in results[name]
        }
        print(
            f"  {name}: >=3={rates[3]:.4f}, >=4={rates[4]:.4f}, "
            f">=5={rates[5]:.4f}, =6={rates[6]:.4f}"
        )

    assert all(
        len(values) == holdout
        for variant in results.values()
        for values in variant.values()
    )


def test_elite_overlap_limit_tail_robust_walk_forward_diagnostic():
    """Test whether allowing tighter ticket overlap changes rare high-hit rates."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = (4, 5, 6)
    results = {limit: {threshold: [] for threshold in (3, 4, 5, 6)} for limit in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for limit in variants:
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=300,
                max_overlap=limit,
                max_tickets=14,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=107000 + offset)
            hits = [len(set(ticket) & actual) for ticket in result.recommended_tickets]
            for threshold in results[limit]:
                results[limit][threshold].append(1 if max(hits) >= threshold else 0)

    print("Elite overlap-limit tail diagnostic:")
    for limit in variants:
        rates = {threshold: mean(results[limit][threshold]) for threshold in results[limit]}
        print(
            f"  max_overlap={limit}: >=3={rates[3]:.4f}, >=4={rates[4]:.4f}, "
            f">=5={rates[5]:.4f}, =6={rates[6]:.4f}"
        )

    assert all(
        len(values) == holdout
        for variant in results.values()
        for values in variant.values()
    )


def test_clean_model_selection_regular_pro_elite_walk_forward():
    """Compare the currently supported production engines on the same holdout."""
    from lrei.lottery.recommendation import RecommendationEngine
    from lrei.lottery.statistics import LotteryStatistics
    from lrei.lottery.elite import EliteProConfig, EliteProRecommendationEngine

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    variants = {
        "regular": "regular",
        "pro": "pro",
        "elite_equal": "elite_equal",
        "elite_adaptive_candidates": "elite_adaptive_candidates",
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)

        engines = {
            "regular": RecommendationEngine(),
            "pro": ProRecommendationEngine(),
            "elite_equal": EliteProRecommendationEngine(EliteProConfig(
                candidate_count=200, max_tickets=14,
            )),
            "elite_adaptive_candidates": EliteProRecommendationEngine(EliteProConfig(
                candidate_count=200, max_tickets=14,
                adaptive_candidate_weights=True,
                candidate_calibration_draws=20,
                candidate_calibration_candidate_count=100,
                candidate_calibration_origins=3,
                candidate_adaptive_shrinkage=0.50,
            )),
        }

        for name, engine in engines.items():
            if name == "regular":
                result = engine.recommend(
                    LotteryStatistics.from_dataset(history),
                    ticket_count=50,
                    seed=110000 + offset,
                )
            else:
                result = engine.recommend(history, seed=110000 + offset)

            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    print("Clean production model selection:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    baseline = results["regular"]
    for name, values in results.items():
        if name == "regular":
            continue
        difference = [candidate - base for candidate, base in zip(values, baseline)]
        ci = _bootstrap_ci(difference, seed=20260930 + list(variants).index(name))
        print(f"  {name} - regular={mean(difference):+.4f}, 95% CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_ensemble_candidate_injection_robust_walk_forward_diagnostic():
    """Test whether injecting adjusted ensemble candidates improves portfolio hits."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    results = {"current": [], "ensemble_25": []}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, weight in (("current", 0.0), ("ensemble_25", 0.25)):
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                candidate_ensemble_weight=weight,
            )
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=120000 + offset
            )
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [
        injected - current
        for injected, current in zip(results["ensemble_25"], results["current"])
    ]
    ci = _bootstrap_ci(difference, seed=20260931)

    print("Elite ensemble-candidate injection robust diagnostic:")
    print(f"  current={mean(results['current']):.4f}")
    print(f"  ensemble_25={mean(results['ensemble_25']):.4f}")
    print(f"  ensemble_25-current={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_meta_model_selection_walk_forward_diagnostic():
    """Compare a trailing-performance model selector with fixed Elite."""
    from lrei.lottery.recommendation import RecommendationEngine
    from lrei.lottery.statistics import LotteryStatistics

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    calibration_draws = 20
    results = {"fixed_elite": [], "meta_selector": []}
    selections = {"regular": 0, "pro": 0, "elite": 0}

    def recommend_model(name, history, seed):
        if name == "regular":
            return RecommendationEngine().recommend(
                LotteryStatistics.from_dataset(history),
                ticket_count=50,
                seed=seed,
            )
        if name == "pro":
            from lrei.lottery.pro import ProConfig
            return ProRecommendationEngine(ProConfig(candidate_count=120, max_tickets=14)).recommend(history, seed=seed)
        return EliteProRecommendationEngine(__import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(candidate_count=120, max_tickets=14)).recommend(history, seed=seed)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)

        fixed = recommend_model("elite", history, 130000 + offset)
        results["fixed_elite"].append(
            mean(len(set(ticket) & actual) for ticket in fixed.recommended_tickets)
        )

        if len(history) < calibration_draws + 40:
            selected = "elite"
        else:
            validation = history.draws[-calibration_draws:]
            train = LotteryDataset(history.draws[:-calibration_draws])
            model_scores = {}
            for model_index, name in enumerate(("regular", "pro", "elite")):
                values = []
                for validation_index, validation_draw in enumerate(validation):
                    candidate = recommend_model(
                        name,
                        LotteryDataset(train.draws[: len(train.draws)]),
                        131000 + model_index * 1000 + offset * 31 + validation_index,
                    )
                    values.append(
                        mean(
                            len(set(ticket) & set(validation_draw.numbers))
                            for ticket in candidate.recommended_tickets
                        )
                    )
                model_scores[name] = mean(values)

            selected = max(model_scores, key=model_scores.get)

        selections[selected] += 1
        chosen = recommend_model(selected, history, 132000 + offset)
        results["meta_selector"].append(
            mean(len(set(ticket) & actual) for ticket in chosen.recommended_tickets)
        )

    difference = [
        meta - elite
        for meta, elite in zip(results["meta_selector"], results["fixed_elite"])
    ]
    ci = _bootstrap_ci(difference, seed=20261004)

    print("Elite meta-model selection diagnostic:")
    print(f"  fixed_elite={mean(results['fixed_elite']):.4f}")
    print(f"  meta_selector={mean(results['meta_selector']):.4f}")
    print(f"  meta-fixed_elite={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")
    print(f"  selections={selections}")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_meta_model_multi_origin_stability_diagnostic():
    """Stress-test meta model selection across multiple historical origins."""
    from lrei.lottery.recommendation import RecommendationEngine
    from lrei.lottery.statistics import LotteryStatistics

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = 40
    origins = [len(draws) - holdout, len(draws) - 2 * holdout, len(draws) - 3 * holdout]
    calibration_draws = 12
    results = {"fixed_elite": [], "meta_selector": []}
    selections = {"regular": 0, "pro": 0, "elite": 0}
    origin_differences = []

    def recommend_model(name, history, seed):
        if name == "regular":
            return RecommendationEngine().recommend(
                LotteryStatistics.from_dataset(history),
                ticket_count=50,
                seed=seed,
            )
        if name == "pro":
            from lrei.lottery.pro import ProConfig
            return ProRecommendationEngine(
                ProConfig(candidate_count=100, max_tickets=14)
            ).recommend(history, seed=seed)
        return EliteProRecommendationEngine(
            __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=100, max_tickets=14
            )
        ).recommend(history, seed=seed)

    for origin_index, start in enumerate(origins):
        local_fixed = []
        local_meta = []
        for offset, target in enumerate(draws[start:start + holdout]):
            history = LotteryDataset(draws=draws[:start + offset])
            actual = set(target.numbers)

            fixed = recommend_model("elite", history, 140000 + origin_index * 1000 + offset)
            local_fixed.append(
                mean(len(set(ticket) & actual) for ticket in fixed.recommended_tickets)
            )

            validation = history.draws[-calibration_draws:]
            train = LotteryDataset(history.draws[:-calibration_draws])
            model_scores = {}
            for model_index, name in enumerate(("regular", "pro", "elite")):
                values = []
                for validation_index, validation_draw in enumerate(validation):
                    candidate = recommend_model(
                        name,
                        train,
                        141000 + origin_index * 10000 + model_index * 1000 + offset * 31 + validation_index,
                    )
                    values.append(
                        mean(
                            len(set(ticket) & set(validation_draw.numbers))
                            for ticket in candidate.recommended_tickets
                        )
                    )
                model_scores[name] = mean(values)

            selected = max(model_scores, key=model_scores.get)
            selections[selected] += 1
            chosen = recommend_model(
                selected,
                history,
                142000 + origin_index * 1000 + offset,
            )
            local_meta.append(
                mean(len(set(ticket) & actual) for ticket in chosen.recommended_tickets)
            )

        results["fixed_elite"].extend(local_fixed)
        results["meta_selector"].extend(local_meta)
        origin_differences.append(mean(meta - fixed for meta, fixed in zip(local_meta, local_fixed)))

    difference = [
        meta - fixed
        for meta, fixed in zip(results["meta_selector"], results["fixed_elite"])
    ]
    ci = _bootstrap_ci(difference, seed=20261005)

    print("Elite meta-model multi-origin stability diagnostic:")
    print(f"  origins={len(origins)}, draws_per_origin={holdout}, calibration={calibration_draws}")
    print(f"  fixed_elite={mean(results['fixed_elite']):.4f}")
    print(f"  meta_selector={mean(results['meta_selector']):.4f}")
    print(f"  meta-fixed_elite={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")
    print(f"  origin_differences={[round(value, 4) for value in origin_differences]}")
    print(f"  selections={selections}")

    assert len(difference) == len(origins) * holdout
    assert all(value == value for value in difference)


def test_elite_learned_signal_model_robust_walk_forward_diagnostic():
    """Compare the opt-in learned historical signal with current Elite."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    results = {"current": [], "learned": []}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        configs = {
            "current": EliteProConfig(candidate_count=160, max_tickets=14),
            "learned": EliteProConfig(
                candidate_count=160,
                max_tickets=14,
                learned_signal_model=True,
                learned_model_draws=120,
                learned_model_shrinkage=0.50,
            ),
        }
        for name, config in configs.items():
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=150000 + offset
            )
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [learned - current for learned, current in zip(results["learned"], results["current"])]
    ci = _bootstrap_ci(difference, seed=20261006)

    print("Elite learned-signal robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  learned-current={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_tail_weight_robust_walk_forward_diagnostic():
    """Compare an opt-in tail-weighted portfolio objective with the current objective."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    variants = {
        "current": 0.0,
        "tail_light": 0.05,
        "tail_strong": 0.10,
    }
    results = {name: {threshold: [] for threshold in (3, 4, 5)} for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, tail_weight in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                portfolio_tail_weight=tail_weight,
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=152000 + offset)
            hits = [len(set(ticket) & actual) for ticket in result.recommended_tickets]
            for threshold in results[name]:
                results[name][threshold].append(int(max(hits) >= threshold))

    print("Elite tail-weight robust diagnostic:")
    for name, thresholds in results.items():
        print(
            f"  {name}: "
            + ", ".join(f"{threshold}+={mean(values):.4f}" for threshold, values in thresholds.items())
        )

    for name in ("tail_light", "tail_strong"):
        for threshold in (3, 4, 5):
            difference = [
                value - base
                for value, base in zip(results[name][threshold], results["current"][threshold])
            ]
            ci = _bootstrap_ci(difference, seed=20261007 + threshold)
            print(
                f"  {name} {threshold}+ vs current: "
                f"{mean(difference):+.4f}, 95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]"
            )

    assert all(
        len(values) == holdout
        for thresholds in results.values()
        for values in thresholds.values()
    )
    assert all(
        value == value
        for thresholds in results.values()
        for values in thresholds.values()
        for value in values
    )


def test_learned_logistic_signal_robust_walk_forward_diagnostic():
    """Compare a learned feature model with the exact six-number random baseline."""
    from lrei.lottery.learned_model import predict_number_scores

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    hits = []

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        scores = predict_number_scores(history, training_draws=120, ewma_half_life=36.0, shrinkage=0.50)
        top6 = sorted(scores, key=lambda number: (-scores[number], number))[:6]
        hits.append(len(set(top6) & set(target.numbers)))

    baseline = 6.0 * 6.0 / 37.0
    difference = [value - baseline for value in hits]
    ci = _bootstrap_ci(difference, seed=20261008)

    print("Learned logistic signal robust diagnostic:")
    print(f"  holdout={holdout}")
    print(f"  learned top-6 mean hits={mean(hits):.4f}")
    print(f"  random six-number baseline={baseline:.4f}")
    print(f"  learned - random mean={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(0 <= value <= 6 for value in hits)
    assert all(value == value for value in difference)


def test_elite_consensus_light_multi_origin_stability_diagnostic():
    """Stress-test Consensus light across three chronological origins."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = 30
    origins = [len(draws) - holdout, len(draws) - 2 * holdout, len(draws) - 3 * holdout]
    results = {"off": [], "light": []}
    origin_differences = []

    for origin_index, start in enumerate(origins):
        local_off = []
        local_light = []
        for offset, target in enumerate(draws[start:start + holdout]):
            history = LotteryDataset(draws=draws[:start + offset])
            actual = set(target.numbers)
            for name, strength in (("off", 0.0), ("light", 0.25)):
                config = EliteProConfig(
                    candidate_count=160,
                    max_tickets=14,
                    consensus_strength=strength,
                )
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=160000 + origin_index * 1000 + offset
                )
                value = mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
                if name == "off":
                    local_off.append(value)
                else:
                    local_light.append(value)

        results["off"].extend(local_off)
        results["light"].extend(local_light)
        origin_differences.append(mean(
            light - off for light, off in zip(local_light, local_off)
        ))

    difference = [
        light - off
        for light, off in zip(results["light"], results["off"])
    ]
    ci = _bootstrap_ci(difference, seed=20261010)

    print("Elite Consensus light multi-origin stability:")
    print(f"  origins={len(origins)}, draws_per_origin={holdout}")
    print(f"  off={mean(results['off']):.4f}")
    print(f"  light={mean(results['light']):.4f}")
    print(f"  light-off={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")
    print(f"  origin_differences={[round(value, 4) for value in origin_differences]}")

    assert len(difference) == len(origins) * holdout
    assert all(value == value for value in difference)


def test_elite_meta_portfolio_multi_model_walk_forward_diagnostic():
    """Blend Regular/Pro/Elite portfolios using trailing model performance."""
    from lrei.lottery.optimizer import LotteryOptimizer, OptimizerConfig
    from lrei.lottery.recommendation import RecommendationEngine
    from lrei.lottery.statistics import LotteryStatistics

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    calibration_draws = 20
    results = {"elite": [], "meta_portfolio": []}

    def recommend_model(name, history, seed):
        if name == "regular":
            return RecommendationEngine().recommend(
                LotteryStatistics.from_dataset(history),
                ticket_count=50,
                seed=seed,
            )
        if name == "pro":
            from lrei.lottery.pro import ProConfig
            return ProRecommendationEngine(ProConfig(candidate_count=120, max_tickets=14)).recommend(
                history, seed=seed
            )
        return EliteProRecommendationEngine(
            __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=120, max_tickets=14
            )
        ).recommend(history, seed=seed)

    optimizer = LotteryOptimizer(OptimizerConfig(max_overlap=4, max_tickets=14))

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        elite = recommend_model("elite", history, 140000 + offset)
        elite_mean = mean(len(set(ticket) & set(target.numbers)) for ticket in elite.recommended_tickets)
        results["elite"].append(elite_mean)

        if len(history) < calibration_draws + 40:
            weights = {"regular": 1.0, "pro": 1.0, "elite": 1.0}
        else:
            train = LotteryDataset(history.draws[:-calibration_draws])
            validation = history.draws[-calibration_draws:]
            model_scores = {}
            for model_index, name in enumerate(("regular", "pro", "elite")):
                values = []
                for validation_index, validation_draw in enumerate(validation):
                    candidate = recommend_model(
                        name,
                        train,
                        141000 + model_index * 1000 + offset * 31 + validation_index,
                    )
                    values.append(
                        mean(
                            len(set(ticket) & set(validation_draw.numbers))
                            for ticket in candidate.recommended_tickets
                        )
                    )
                model_scores[name] = mean(values)
            baseline = 6.0 * 6.0 / 37.0
            weights = {
                name: max(0.20, score / max(baseline, 1e-9))
                for name, score in model_scores.items()
            }

        portfolios = {
            name: recommend_model(name, history, 142000 + index * 10000 + offset)
            for index, name in enumerate(("regular", "pro", "elite"))
        }
        candidates = []
        for name, result in portfolios.items():
            weight = weights[name]
            candidates.extend(
                (tuple(ticket), weight)
                for ticket in result.recommended_tickets
            )

        # Allocate an initial quota from each model, then fill by weighted
        # quality and portfolio compatibility.
        total_weight = sum(weights.values())
        quotas = {
            name: max(1, round(14 * weights[name] / total_weight))
            for name in weights
        }
        while sum(quotas.values()) > 14:
            weakest = min(quotas, key=quotas.get)
            if quotas[weakest] > 1:
                quotas[weakest] -= 1
            else:
                break
        while sum(quotas.values()) < 14:
            strongest = max(quotas, key=quotas.get)
            quotas[strongest] += 1

        selected = []
        for name in ("regular", "pro", "elite"):
            source = portfolios[name].recommended_tickets
            for ticket in source:
                if len(selected) >= quotas[name]:
                    break
                if optimizer.is_compatible(ticket, selected):
                    selected.append(ticket)

        remaining = [
            (ticket, weight)
            for ticket, weight in candidates
            if ticket not in selected
        ]
        remaining.sort(key=lambda item: (item[1], tuple(-n for n in item[0])), reverse=True)
        for ticket, _ in remaining:
            if len(selected) >= 14:
                break
            if optimizer.is_compatible(ticket, selected):
                selected.append(ticket)

        assert len(selected) == 14
        results["meta_portfolio"].append(
            mean(len(set(ticket) & set(target.numbers)) for ticket in selected)
        )

    difference = [
        meta - elite
        for meta, elite in zip(results["meta_portfolio"], results["elite"])
    ]
    ci = _bootstrap_ci(difference, seed=20261005)

    print("Elite meta-portfolio multi-model diagnostic:")
    print(f"  Elite={mean(results['elite']):.4f}")
    print(f"  Meta-portfolio={mean(results['meta_portfolio']):.4f}")
    print(f"  Meta-portfolio - Elite={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_learned_signal_robust_walk_forward_diagnostic():
    """Measure whether the opt-in learned signal adds stable out-of-sample value."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(70, max(50, len(draws) // 16))
    start = len(draws) - holdout
    variants = {
        "current": {"learned_signal_model": False},
        "learned": {
            "learned_signal_model": True,
            "learned_model_draws": 120,
            "learned_model_shrinkage": 0.50,
        },
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                **kwargs,
            )
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=150000 + offset
            )
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [
        learned - current
        for learned, current in zip(results["learned"], results["current"])
    ]
    ci = _bootstrap_ci(difference, seed=20261005)

    print("Elite learned-signal robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  learned-current={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_gap_recency_robust_long_holdout_diagnostic():
    """Validate fixed gap-recency against the current Elite baseline on a longer holdout."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    results = {"current": [], "gap_recency": []}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in (
            ("current", {}),
            ("gap_recency", {"gap_strength": 0.20, "gap_mode": "recency"}),
        ):
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                **kwargs,
            )
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=160000 + offset
            )
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [
        gap - current
        for gap, current in zip(results["gap_recency"], results["current"])
    ]
    ci = _bootstrap_ci(difference, seed=20261006)

    print("Elite gap-recency robust long-holdout diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  gap_recency-current={mean(difference):+.4f}")
    print(f"  95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_jackpot_oriented_robust_diagnostic():
    """Compare Elite with random on high-hit outcomes, not only mean hits."""
    from statistics import mean

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(240, max(120, len(draws) // 5))
    start = len(draws) - holdout
    engine = EliteProRecommendationEngine()
    rng = random.Random(20261005)

    elite_best = []
    random_best = []
    elite_4plus = []
    random_4plus = []
    elite_5plus = []
    random_5plus = []
    elite_6 = []
    random_6 = []

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)

        elite_hits = _hits(
            engine.recommend(history, seed=130000 + offset).recommended_tickets,
            target.numbers,
        )
        random_hits = _hits(
            _random_portfolio(rng),
            target.numbers,
        )

        elite_best.append(max(elite_hits))
        random_best.append(max(random_hits))
        elite_4plus.append(sum(hit >= 4 for hit in elite_hits))
        random_4plus.append(sum(hit >= 4 for hit in random_hits))
        elite_5plus.append(sum(hit >= 5 for hit in elite_hits))
        random_5plus.append(sum(hit >= 5 for hit in random_hits))
        elite_6.append(sum(hit == 6 for hit in elite_hits))
        random_6.append(sum(hit == 6 for hit in random_hits))

    print("Elite jackpot-oriented robust diagnostic:")
    print(f"  holdout={holdout}")
    print(f"  Elite best-ticket mean={mean(elite_best):.4f}")
    print(f"  Random best-ticket mean={mean(random_best):.4f}")
    print(f"  Elite 4+ tickets/draw={mean(elite_4plus):.4f}")
    print(f"  Random 4+ tickets/draw={mean(random_4plus):.4f}")
    print(f"  Elite 5+ tickets/draw={mean(elite_5plus):.4f}")
    print(f"  Random 5+ tickets/draw={mean(random_5plus):.4f}")
    print(f"  Elite 6-hit tickets/draw={mean(elite_6):.4f}")
    print(f"  Random 6-hit tickets/draw={mean(random_6):.4f}")

    assert len(elite_best) == holdout
    assert len(random_best) == holdout
    assert all(0 <= value <= 6 for value in elite_best)
    assert all(0 <= value <= 6 for value in random_best)


def test_elite_tail_weight_jackpot_walk_forward_diagnostic():
    """Test portfolio tail-weight settings against the current jackpot-oriented baseline."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(180, max(100, len(draws) // 6))
    start = len(draws) - holdout
    variants = {
        "current": 0.0,
        "tail_light": 0.03,
        "tail_medium": 0.06,
        "tail_strong": 0.10,
    }
    thresholds = (4, 5, 6)
    results = {
        name: {threshold: [] for threshold in thresholds}
        for name in variants
    }

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)
        for name, tail_weight in variants.items():
            config = __import__("lrei.lottery.elite", fromlist=["EliteProConfig"]).EliteProConfig(
                candidate_count=200,
                max_tickets=14,
                portfolio_tail_weight=tail_weight,
            )
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=130500 + offset
            )
            hits = _hits(result.recommended_tickets, target.numbers)
            for threshold in thresholds:
                results[name][threshold].append(int(max(hits) >= threshold))

    print("Elite jackpot tail-weight diagnostic:")
    for name in variants:
        values = results[name]
        print(
            f"  {name}: "
            + ", ".join(
                f"{threshold}+={mean(values[threshold]):.4f}"
                for threshold in thresholds
            )
        )

    baseline = results["current"]
    for name in variants:
        if name == "current":
            continue
        for threshold in thresholds:
            difference = [
                candidate - current
                for candidate, current in zip(
                    results[name][threshold], baseline[threshold]
                )
            ]
            ci = _bootstrap_ci(
                difference,
                seed=20261050 + list(variants).index(name) * 10 + threshold,
            )
            print(
                f"  {name} {threshold}+ vs current="
                f"{mean(difference):+.4f}, "
                f"95% CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]"
            )

    assert all(
        len(values) == holdout
        for variant in results.values()
        for values in variant.values()
    )


def test_elite_against_constrained_random_jackpot_walk_forward():
    """Compare Elite with random portfolios using the same overlap constraint."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(180, max(100, len(draws) // 6))
    start = len(draws) - holdout
    random_portfolios_per_draw = 5
    rng = random.Random(20261060)

    elite_mean = []
    random_mean = []
    elite_best = []
    random_best = []
    elite_4plus = []
    random_4plus = []
    elite_5plus = []
    random_5plus = []
    elite_6 = []
    random_6 = []

    engine = EliteProRecommendationEngine()

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)
        elite_hits = _hits(
            engine.recommend(history, seed=140000 + offset).recommended_tickets,
            target.numbers,
        )
        random_results = [
            _hits(
                _random_diversified_portfolio(rng, max_overlap=4),
                target.numbers,
            )
            for _ in range(random_portfolios_per_draw)
        ]
        random_flat = [hit for result in random_results for hit in result]

        elite_mean.append(mean(elite_hits))
        random_mean.append(mean(random_flat))
        elite_best.append(max(elite_hits))
        random_best.append(mean(max(result) for result in random_results))
        elite_4plus.append(int(max(elite_hits) >= 4))
        random_4plus.append(mean(int(max(result) >= 4) for result in random_results))
        elite_5plus.append(int(max(elite_hits) >= 5))
        random_5plus.append(mean(int(max(result) >= 5) for result in random_results))
        elite_6.append(int(max(elite_hits) == 6))
        random_6.append(mean(int(max(result) == 6) for result in random_results))

    paired_mean = [e - r for e, r in zip(elite_mean, random_mean)]
    paired_best = [e - r for e, r in zip(elite_best, random_best)]
    paired_4 = [e - r for e, r in zip(elite_4plus, random_4plus)]
    paired_5 = [e - r for e, r in zip(elite_5plus, random_5plus)]
    paired_6 = [e - r for e, r in zip(elite_6, random_6)]

    print("Elite vs constrained-random jackpot diagnostic:")
    print(f"  holdout={holdout}, random_portfolios_per_draw={random_portfolios_per_draw}")
    print(f"  mean hits: Elite={mean(elite_mean):.4f}, random={mean(random_mean):.4f}, diff={mean(paired_mean):+.4f}")
    print(f"  best ticket: Elite={mean(elite_best):.4f}, random={mean(random_best):.4f}, diff={mean(paired_best):+.4f}")
    for label, values in (("4+", paired_4), ("5+", paired_5), ("6", paired_6)):
        ci = _bootstrap_ci(values, seed=20261070 + len(label))
        print(f"  {label}: diff={mean(values):+.4f}, 95% bootstrap CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert len(paired_mean) == holdout
    assert all(value == value for value in paired_mean + paired_best + paired_4 + paired_5 + paired_6)
