import random
from pathlib import Path
from statistics import mean

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
                    candidate_calibration_candidate_count=100,
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
            random_counts[threshold].append(sum(hit >= threshold for hit in random_hits))

    print("Elite tail-hit robust diagnostic:")
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
