from pathlib import Path
from itertools import combinations

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.pro import ProRecommendationEngine


def test_pro_portfolio_quality_invariants():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    result = ProRecommendationEngine().recommend(dataset, seed=20260916)

    tickets = result.recommended_tickets
    assert len(tickets) == 14
    assert len(set(tickets)) == 14
    assert len(result.generated_tickets) == 2000

    for ticket in tickets:
        assert len(ticket) == 6
        assert len(set(ticket)) == 6
        assert all(1 <= number <= 37 for number in ticket)

    overlaps = [
        len(set(left) & set(right))
        for left, right in combinations(tickets, 2)
    ]
    assert overlaps
    assert max(overlaps) <= 4

    # The portfolio should cover the full number range rather than collapsing
    # onto only a small set of historically frequent numbers.
    covered = set().union(*map(set, tickets))
    assert len(covered) >= 30


def test_pro_is_reproducible_for_same_seed():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = ProRecommendationEngine()

    first = engine.recommend(dataset, seed=424242)
    second = engine.recommend(dataset, seed=424242)

    assert first.recommended_tickets == second.recommended_tickets
    assert first.generated_tickets == second.generated_tickets


def test_pro_coverage_is_stable_across_seeds():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = ProRecommendationEngine()
    coverages = []
    for seed in (1, 7, 42, 99, 20260918):
        result = engine.recommend(dataset, seed=seed)
        covered = set().union(*map(set, result.recommended_tickets))
        coverages.append(len(covered))
    assert min(coverages) >= 30
    assert max(coverages) <= 37


def test_pro_portfolio_selector_ablation():
    """Compare selector tradeoffs on a small fixed walk-forward sample."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset
    from lrei.lottery.pro import ProConfig

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(20, max(12, len(draws) // 50))
    start = len(draws) - holdout

    variants = {
        "current": (0.035, 0.018),
        "coverage_light": (0.020, 0.018),
        "coverage_strong": (0.050, 0.018),
        "overlap_strong": (0.035, 0.030),
        "balanced": (0.025, 0.025),
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[: start + offset])
        for name, (coverage, overlap) in variants.items():
            engine = ProRecommendationEngine(ProConfig(
                candidate_count=300,
                max_tickets=14,
                portfolio_coverage_weight=coverage,
                portfolio_overlap_penalty=overlap,
            ))
            result = engine.recommend(history, seed=91000 + offset)
            actual = set(target.numbers)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    print("Pro portfolio selector ablation:")
    for name, values in results.items():
        print(f"  {name}: {mean(values):.4f}")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_pro_candidate_generation_ablation():
    """Compare candidate-generation settings on a small walk-forward sample."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset
    from lrei.lottery.pro import ProConfig

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(24, max(16, len(draws) // 48))
    start = len(draws) - holdout

    variants = {
        "current": (0.35, 0.15, 0.72, 0.28),
        "pair_light": (0.15, 0.08, 0.72, 0.28),
        "pair_strong": (0.55, 0.25, 0.72, 0.28),
        "gate_light": (0.35, 0.15, 0.45, 0.24),
        "gate_strong": (0.35, 0.15, 0.88, 0.30),
        "no_gate": (0.35, 0.15, 0.00, 0.28),
    }
    results = {name: [] for name in variants}
    diversity = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[: start + offset])
        for name, (pair, triple, gate_probability, gate_threshold) in variants.items():
            engine = ProRecommendationEngine(ProConfig(
                candidate_count=200,
                max_tickets=14,
                pair_bonus_strength=pair,
                triple_bonus_strength=triple,
                structural_gate_probability=gate_probability,
                structural_gate_threshold=gate_threshold,
            ))
            result = engine.recommend(history, seed=92000 + offset)
            actual = set(target.numbers)
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

            unique_pool = set(result.generated_tickets)
            covered_numbers = set().union(*map(set, result.generated_tickets))
            sample = list(unique_pool)[:300]
            overlaps = [
                len(set(left) & set(right))
                for left, right in combinations(sample, 2)
            ]
            diversity[name].append((
                len(unique_pool) / len(result.generated_tickets),
                len(covered_numbers),
                mean(overlaps) if overlaps else 0.0,
            ))

    print("Pro candidate-generation ablation:")
    for name, values in results.items():
        ratio = mean(item[0] for item in diversity[name])
        coverage = mean(item[1] for item in diversity[name])
        overlap = mean(item[2] for item in diversity[name])
        print(
            f"  {name}: hits={mean(values):.4f} "
            f"unique_ratio={ratio:.4f} coverage={coverage:.2f} "
            f"mean_pool_overlap={overlap:.4f}"
        )

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_pro_candidate_pool_diversity_diagnostic():
    """Measure whether the candidate generator is creating a sufficiently broad pool."""
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    history = type(dataset)(draws=draws[:-20])
    engine = ProRecommendationEngine()
    result = engine.recommend(history, seed=20260918)

    unique_pool = list(set(result.generated_tickets))
    unique_candidates = len(unique_pool)
    covered_candidates = len(set().union(*map(set, result.generated_tickets)))
    duplicate_ratio = 1.0 - unique_candidates / len(result.generated_tickets)
    pool_overlaps = [
        len(set(left) & set(right))
        for left, right in combinations(unique_pool[:500], 2)
    ]
    mean_overlap = sum(pool_overlaps) / len(pool_overlaps) if pool_overlaps else 0.0

    print("Pro candidate-pool diversity:")
    print(f"  generated: {len(result.generated_tickets)}")
    print(f"  unique: {unique_candidates}")
    print(f"  duplicate ratio: {duplicate_ratio:.4f}")
    print(f"  number coverage: {covered_candidates}")
    print(f"  mean overlap (first 500 unique): {mean_overlap:.4f}")

    assert unique_candidates > 0
    assert 1 <= covered_candidates <= 37
    assert 0.0 <= duplicate_ratio < 1.0
    assert 0.0 <= mean_overlap <= 6.0


def test_pro_structural_gate_has_bounded_retries():
    """Extreme gate settings must not recurse without a bound."""
    from lrei.lottery.pro import ProConfig

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = ProRecommendationEngine(ProConfig(
        candidate_count=20,
        max_tickets=14,
        structural_gate_probability=1.0,
        structural_gate_threshold=1.0,
    ))

    result = engine.recommend(dataset, seed=20260919)

    assert len(result.generated_tickets) == 20
    assert len(result.recommended_tickets) == 14

def test_pro_number_signal_calibration_diagnostic():
    """Measure whether Pro number scores retain signal on unseen draws."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(24, max(16, len(draws) // 48))
    start = len(draws) - holdout
    top_k = 10
    top_hits = []
    middle_hits = []
    bottom_hits = []

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[: start + offset])
        result = ProRecommendationEngine().recommend(history, seed=93000 + offset)
        ranked = sorted(result.scores, key=lambda item: (-item.score, item.number))
        actual = set(target.numbers)
        top_hits.append(len({item.number for item in ranked[:top_k]} & actual))
        bottom_hits.append(len({item.number for item in ranked[-top_k:]} & actual))
        middle = ranked[top_k:-top_k]
        middle_hits.append(
            len({item.number for item in middle} & actual)
        )

    print("Pro number-signal calibration:")
    print(f"  top_{top_k}_mean_hits={mean(top_hits):.4f}")
    print(f"  middle_mean_hits={mean(middle_hits):.4f}")
    print(f"  bottom_{top_k}_mean_hits={mean(bottom_hits):.4f}")

    assert len(top_hits) == holdout
    assert all(0 <= value <= top_k for value in top_hits)
    assert all(0 <= value <= top_k for value in bottom_hits)


def test_pro_affinity_prior_robust_walk_forward_diagnostic():
    """Compare Bayesian affinity priors on a longer unseen holdout."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset
    from lrei.lottery.pro import ProConfig

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {
        "prior_0": 0.0,
        "prior_5": 5.0,
        "prior_15": 15.0,
        "prior_30": 30.0,
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, prior in variants.items():
            config = ProConfig(
                candidate_count=200,
                max_tickets=14,
                affinity_prior_strength=prior,
            )
            result = ProRecommendationEngine(config).recommend(history, seed=99000 + offset)
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    print("Pro affinity-prior robust diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())
