from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.elite import EliteProConfig, EliteProRecommendationEngine


DATASET = CsvDatasetLoader().load(Path("data/lottery.csv"))


def test_elite_pro_generates_fourteen_diverse_tickets():
    engine = EliteProRecommendationEngine(EliteProConfig(candidate_count=90, max_tickets=14))
    result = engine.recommend(DATASET, seed=4242)

    assert len(result.generated_tickets) == 90
    assert len(result.recommended_tickets) == 14
    assert len(set(result.recommended_tickets)) == 14
    assert all(len(ticket) == 6 for ticket in result.recommended_tickets)
    assert all(len(set(ticket)) == 6 for ticket in result.recommended_tickets)
    assert all(1 <= n <= 37 for ticket in result.recommended_tickets for n in ticket)
    for index, ticket in enumerate(result.recommended_tickets):
        for other in result.recommended_tickets[index + 1 :]:
            assert engine.optimizer.overlap(ticket, other) <= 4


def test_elite_pro_is_reproducible():
    config = EliteProConfig(candidate_count=90, max_tickets=14)
    first = EliteProRecommendationEngine(config).recommend(DATASET, seed=99)
    second = EliteProRecommendationEngine(config).recommend(DATASET, seed=99)
    assert first.recommended_tickets == second.recommended_tickets
    assert first.scores == second.scores


def test_elite_pro_adaptive_weights_are_normalized_and_use_history_only():
    config = EliteProConfig(candidate_count=90, max_tickets=14, calibration_draws=20, adaptive_shrinkage=1.0)
    engine = EliteProRecommendationEngine(config)
    variants = (
        (engine._engine(config, True, False), None),
        (engine._engine(config, False, False), None),
        (engine._engine(config, True, True), None),
    )

    weights = engine._adaptive_weights(DATASET, variants)

    assert len(weights) == 3
    assert all(weight >= 0.0 for weight in weights)
    assert abs(sum(weights) - 1.0) < 1e-12


def test_elite_pro_adaptation_can_be_disabled():
    config = EliteProConfig(
        candidate_count=90,
        max_tickets=14,
        adaptive_weights=False,
        rank_weight=0.45,
        raw_weight=0.30,
        ewma_weight=0.25,
    )
    engine = EliteProRecommendationEngine(config)
    variants = (
        (engine._engine(config, True, False), None),
        (engine._engine(config, False, False), None),
        (engine._engine(config, True, True), None),
    )

    assert engine._adaptive_weights(DATASET, variants) == (0.45, 0.30, 0.25)


def test_elite_pro_rejects_invalid_adaptive_settings():
    for kwargs in (
        {"calibration_draws": -1},
        {"calibration_top_k": 0},
        {"calibration_top_k": 38},
        {"adaptive_shrinkage": -0.1},
        {"adaptive_shrinkage": 1.1},
    ):
        try:
            EliteProConfig(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")


def test_elite_pro_propagates_number_signal_strength():
    config = EliteProConfig(candidate_count=90, max_tickets=14, number_signal_strength=0.75)
    rank_engine = EliteProRecommendationEngine._engine(config, True, False)
    raw_engine = EliteProRecommendationEngine._engine(config, False, False)
    ewma_engine = EliteProRecommendationEngine._engine(config, True, True)

    assert rank_engine.config.number_signal_strength == 0.75
    assert raw_engine.config.number_signal_strength == 0.75
    assert ewma_engine.config.number_signal_strength == 0.75


def test_elite_pro_coverage_is_stable_across_seeds():
    config = EliteProConfig(candidate_count=120, max_tickets=14)
    engine = EliteProRecommendationEngine(config)
    for seed in (1, 7, 42, 99):
        result = engine.recommend(DATASET, seed=seed)
        covered = set().union(*map(set, result.recommended_tickets))
        assert len(covered) >= 30


def test_elite_propagates_candidate_generation_settings():
    config = EliteProConfig(
        candidate_count=90,
        max_tickets=14,
        pair_bonus_strength=0.21,
        triple_bonus_strength=0.09,
        structural_gate_probability=0.61,
        structural_gate_threshold=0.24,
    )
    rank_engine = EliteProRecommendationEngine._engine(config, True, False)
    raw_engine = EliteProRecommendationEngine._engine(config, False, False)
    ewma_engine = EliteProRecommendationEngine._engine(config, True, True)

    for engine in (rank_engine, raw_engine, ewma_engine):
        assert engine.config.pair_bonus_strength == 0.21
        assert engine.config.triple_bonus_strength == 0.09
        assert engine.config.structural_gate_probability == 0.61
        assert engine.config.structural_gate_threshold == 0.24


def test_elite_candidate_pool_diversity_diagnostic():
    config = EliteProConfig(candidate_count=300, max_tickets=14)
    engine = EliteProRecommendationEngine(config)
    result = engine.recommend(DATASET, seed=20260918)

    unique_candidates = len(set(result.generated_tickets))
    covered_candidates = len(set().union(*map(set, result.generated_tickets)))

    print("Elite candidate-pool diversity:")
    print(f"  generated: {len(result.generated_tickets)}")
    print(f"  unique: {unique_candidates}")
    print(f"  number coverage: {covered_candidates}")

    assert unique_candidates > 0
    assert 1 <= covered_candidates <= 37

def test_elite_weighting_ablation_diagnostic():
    """Compare fixed/adaptive ensemble settings without changing production defaults."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    holdout = min(24, max(16, len(draws) // 48))
    start = len(draws) - holdout
    variants = {
        "current": dict(adaptive_weights=True, adaptive_shrinkage=0.50, calibration_draws=30, calibration_top_k=10),
        "fixed": dict(adaptive_weights=False),
        "adaptive_light": dict(adaptive_weights=True, adaptive_shrinkage=0.25, calibration_draws=30, calibration_top_k=10),
        "adaptive_strong": dict(adaptive_weights=True, adaptive_shrinkage=0.75, calibration_draws=30, calibration_top_k=10),
        "short_calibration": dict(adaptive_weights=True, adaptive_shrinkage=0.50, calibration_draws=15, calibration_top_k=10),
        "broad_top_k": dict(adaptive_weights=True, adaptive_shrinkage=0.50, calibration_draws=30, calibration_top_k=15),
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in variants.items():
            config = EliteProConfig(candidate_count=300, max_tickets=14, **kwargs)
            result = EliteProRecommendationEngine(config).recommend(history, seed=94000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    print("Elite weighting ablation:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())

def test_elite_candidate_allocation_ablation_diagnostic():
    """Compare candidate-source allocations without changing the default 1/3 mix."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    holdout = min(16, max(12, len(draws) // 70))
    start = len(draws) - holdout
    variants = {
        "equal": (1.0, 1.0, 1.0),
        "rank_heavy": (2.0, 1.0, 1.0),
        "raw_heavy": (1.0, 2.0, 1.0),
        "ewma_heavy": (1.0, 1.0, 2.0),
        "rank_ewma": (1.5, 0.5, 1.5),
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, weights in variants.items():
            config = EliteProConfig(
                candidate_count=300,
                max_tickets=14,
                candidate_rank_weight=weights[0],
                candidate_raw_weight=weights[1],
                candidate_ewma_weight=weights[2],
            )
            result = EliteProRecommendationEngine(config).recommend(history, seed=95000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    print("Elite candidate-source allocation ablation:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_adaptive_candidate_weights_are_normalized_and_can_be_disabled():
    base = EliteProConfig(
        candidate_count=90,
        max_tickets=14,
        adaptive_candidate_weights=True,
        candidate_calibration_draws=20,
        candidate_calibration_candidate_count=30,
        candidate_adaptive_shrinkage=0.50,
    )
    engine = EliteProRecommendationEngine(base)
    variants = (
        (engine._engine(base, True, False), None),
        (engine._engine(base, False, False), None),
        (engine._engine(base, True, True), None),
    )
    weights = engine._adaptive_candidate_weights(DATASET, variants)
    assert len(weights) == 3
    assert all(weight >= 0.0 for weight in weights)
    assert abs(sum(weights) - 1.0) < 1e-12

    fixed = EliteProConfig(candidate_count=90, max_tickets=14)
    fixed_engine = EliteProRecommendationEngine(fixed)
    fixed_variants = (
        (fixed_engine._engine(fixed, True, False), None),
        (fixed_engine._engine(fixed, False, False), None),
        (fixed_engine._engine(fixed, True, True), None),
    )
    assert fixed_engine._adaptive_candidate_weights(DATASET, fixed_variants) == (1.0 / 3.0,) * 3


def test_elite_rejects_invalid_candidate_adaptation_settings():
    for kwargs in (
        {"candidate_calibration_draws": -1},
        {"candidate_calibration_candidate_count": 13},
        {"candidate_adaptive_shrinkage": -0.1},
        {"candidate_adaptive_shrinkage": 1.1},
    ):
        try:
            EliteProConfig(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")
