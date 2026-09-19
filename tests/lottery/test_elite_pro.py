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
