import pytest
from pathlib import Path

pytestmark = pytest.mark.slow

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

    fixed = EliteProConfig(candidate_count=90, max_tickets=14, adaptive_candidate_weights=False)
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
        {"calibration_origins": 0},
        {"portfolio_pair_coverage_weight": -0.1},
        {"portfolio_triple_coverage_weight": -0.1},
        {"gap_mode": "invalid"},
        {"gap_calibration_draws": -1},
        {"gap_calibration_origins": 0},
        {"feature_stack_calibration_draws": -1},
        {"feature_stack_calibration_origins": 0},
        {"feature_stack_min_improvement": -0.1},
        {"feature_stack_min_origin_win_rate": 1.1},
        {"learned_model_draws": 19},
        {"learned_model_shrinkage": 1.1},
    ):
        try:
            EliteProConfig(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")


def test_elite_consensus_scoring_is_opt_in_and_validated():
    base = EliteProConfig(candidate_count=90, max_tickets=14)
    assert base.consensus_strength == 0.0
    for value in (-0.1, 1.1):
        try:
            EliteProConfig(consensus_strength=value)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError for invalid consensus_strength")

    configured = EliteProConfig(candidate_count=90, max_tickets=14, consensus_strength=0.4)
    first = EliteProRecommendationEngine(configured).recommend(DATASET, seed=4242)
    second = EliteProRecommendationEngine(configured).recommend(DATASET, seed=4242)
    assert first.recommended_tickets == second.recommended_tickets


def test_elite_adaptive_consensus_multi_origin_robust_diagnostic():
    """Compare opt-in adaptive consensus with the current scoring across multiple origins."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 20
    origins = [len(draws) - 60, len(draws) - 40, len(draws) - 20]
    results = {"current": [], "adaptive_consensus": []}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws[:start + offset])
            actual = set(target.numbers)
            for name, kwargs in (
                ("current", {}),
                ("adaptive_consensus", {
                    "adaptive_consensus": True,
                    "consensus_calibration_draws": 20,
                    "consensus_calibration_origins": 3,
                }),
            ):
                config = EliteProConfig(candidate_count=150, max_tickets=14, **kwargs)
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=99800 + start + offset
                )
                results[name].append(
                    mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
                )

    difference = [
        adaptive - current
        for adaptive, current in zip(results["adaptive_consensus"], results["current"])
    ]
    print("Elite adaptive-consensus multi-origin diagnostic:")
    print(f"  current={mean(results['current']):.4f}")
    print(f"  adaptive_consensus={mean(results['adaptive_consensus']):.4f}")
    print(f"  adaptive-current={mean(difference):+.4f}")

    assert len(difference) == block * len(origins)
    assert all(value == value for value in difference)


def test_elite_signal_enhancement_walk_forward_diagnostic():
    """Compare opt-in momentum, consensus, and score calibration against current Elite."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    holdout = min(50, max(30, len(draws) // 20))
    start = len(draws) - holdout
    variants = {
        "current": dict(),
        "momentum_adaptive": dict(adaptive_momentum=True, momentum_calibration_draws=20),
        "consensus": dict(consensus_strength=0.50),
        "score_calibration": dict(score_calibration=True, score_calibration_draws=30, score_calibration_bins=5),
        "momentum_consensus": dict(adaptive_momentum=True, momentum_calibration_draws=20, consensus_strength=0.50),
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in variants.items():
            config = EliteProConfig(candidate_count=200, max_tickets=14, **kwargs)
            result = EliteProRecommendationEngine(config).recommend(history, seed=99000 + offset)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    print("Elite signal-enhancement diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_model_selection_robust_walk_forward_diagnostic():
    """Compare candidate Elite configurations on a longer chronological holdout."""
    from statistics import mean
    from random import Random
    from lrei.lottery.dataset import LotteryDataset
    from lrei.lottery.elite import EliteProConfig

    draws = list(DATASET.draws)
    holdout = min(95, max(50, len(draws) // 12))
    start = len(draws) - holdout
    variants = {
        "current": {},
        "momentum_adaptive": {"adaptive_momentum": True, "momentum_calibration_draws": 20},
        "consensus": {"consensus_strength": 0.50},
        "score_calibration": {"score_calibration": True, "score_calibration_draws": 30, "score_calibration_bins": 5},
        "adaptive_candidates": {
            "adaptive_candidate_weights": True,
            "candidate_calibration_draws": 20,
            "candidate_calibration_candidate_count": 100,
            "candidate_adaptive_shrinkage": 0.50,
        },
        "momentum_consensus": {
            "adaptive_momentum": True,
            "momentum_calibration_draws": 20,
            "consensus_strength": 0.50,
        },
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, kwargs in variants.items():
            config = EliteProConfig(candidate_count=200, max_tickets=14, **kwargs)
            result = EliteProRecommendationEngine(config).recommend(history, seed=99100 + offset)
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    current = results["current"]
    print("Elite model-selection robust diagnostic:")
    for name, values in sorted(results.items(), key=lambda item: mean(item[1]), reverse=True):
        difference = [value - base for value, base in zip(values, current)]
        print(f"  {name}: hits={mean(values):.4f}, vs_current={mean(difference):+.4f}")

    def bootstrap_ci(values, seed=20260924, samples=5000):
        rng = Random(seed)
        estimates = []
        for _ in range(samples):
            estimates.append(mean(values[rng.randrange(len(values))] for _ in values))
        estimates.sort()
        return estimates[int(0.025 * (len(estimates) - 1))], estimates[int(0.975 * (len(estimates) - 1))]

    for name, values in results.items():
        if name == "current":
            continue
        difference = [value - base for value, base in zip(values, current)]
        ci = bootstrap_ci(difference, seed=20260924 + list(variants).index(name))
        print(f"    {name} 95% CI vs current=[{ci[0]:+.4f}, {ci[1]:+.4f}]")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_score_calibration_multi_origin_robust_diagnostic():
    """Check score calibration across three chronological origins, not only the latest holdout."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 30
    origins = [len(draws) - 90, len(draws) - 60, len(draws) - 30]
    results = {"current": [], "score_calibration": []}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws=draws[:start + offset])
            actual = set(target.numbers)
            for name, kwargs in (
                ("current", {}),
                ("score_calibration", {
                    "score_calibration": True,
                    "score_calibration_draws": 30,
                    "score_calibration_bins": 5,
                }),
            ):
                config = EliteProConfig(candidate_count=150, max_tickets=14, **kwargs)
                result = EliteProRecommendationEngine(config).recommend(history, seed=99500 + start + offset)
                results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    difference = [cal - current for cal, current in zip(results["score_calibration"], results["current"])]
    print("Elite score-calibration multi-origin robust diagnostic:")
    print(f"  current={mean(results['current']):.4f}")
    print(f"  calibrated={mean(results['score_calibration']):.4f}")
    print(f"  calibrated-current={mean(difference):+.4f}")

    assert len(difference) == block * len(origins)
    assert all(value == value for value in difference)


def test_elite_recent_affinity_multi_origin_robust_diagnostic():
    """Compare current all-history affinity with an opt-in recent-affinity blend."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 30
    origins = [len(draws) - 90, len(draws) - 60, len(draws) - 30]
    results = {"current": [], "recent_affinity": []}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws[:start + offset])
            actual = set(target.numbers)
            for name, weight in (("current", 0.0), ("recent_affinity", 0.35)):
                config = EliteProConfig(
                    candidate_count=150,
                    max_tickets=14,
                    affinity_recent_weight=weight,
                )
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=99600 + start + offset
                )
                results[name].append(
                    mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
                )

    difference = [
        recent - current
        for recent, current in zip(results["recent_affinity"], results["current"])
    ]
    print("Elite recent-affinity multi-origin robust diagnostic:")
    print(f"  current={mean(results['current']):.4f}")
    print(f"  recent_affinity={mean(results['recent_affinity']):.4f}")
    print(f"  recent-current={mean(difference):+.4f}")

    assert len(difference) == block * len(origins)
    assert all(value == value for value in difference)


def test_elite_momentum_multi_origin_robust_diagnostic():
    """Check adaptive momentum across three chronological origins."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 30
    origins = [len(draws) - 90, len(draws) - 60, len(draws) - 30]
    results = {"current": [], "momentum_adaptive": []}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws=draws[:start + offset])
            actual = set(target.numbers)
            for name, kwargs in (
                ("current", {}),
                ("momentum_adaptive", {
                    "adaptive_momentum": True,
                    "momentum_calibration_draws": 20,
                }),
            ):
                config = EliteProConfig(candidate_count=150, max_tickets=14, **kwargs)
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=99700 + start + offset
                )
                results[name].append(
                    mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
                )

    difference = [
        momentum - current
        for momentum, current in zip(
            results["momentum_adaptive"], results["current"]
        )
    ]
    print("Elite momentum multi-origin robust diagnostic:")
    print(f"  current={mean(results['current']):.4f}")
    print(f"  momentum_adaptive={mean(results['momentum_adaptive']):.4f}")
    print(f"  momentum-current={mean(difference):+.4f}")

    assert len(difference) == block * len(origins)
    assert all(value == value for value in difference)


def test_elite_top_model_multi_origin_robust_diagnostic():
    """Validate the strongest recent Elite variants across independent time origins."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 25
    origins = [len(draws) - 100, len(draws) - 75, len(draws) - 50]
    variants = {
        "current": {},
        "momentum_adaptive": {
            "adaptive_momentum": True,
            "momentum_calibration_draws": 20,
        },
        "consensus": {"consensus_strength": 0.50},
    }
    results = {name: [] for name in variants}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws=draws[:start + offset])
            actual = set(target.numbers)
            for name, kwargs in variants.items():
                config = EliteProConfig(candidate_count=120, max_tickets=14, **kwargs)
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=100000 + start + offset
                )
                results[name].append(
                    mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
                )

    print("Elite top-model multi-origin diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    for name in ("momentum_adaptive", "consensus"):
        difference = [
            candidate - current
            for candidate, current in zip(results[name], results["current"])
        ]
        print(f"  {name} - current={mean(difference):+.4f}")

    assert all(len(values) == block * len(origins) for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_candidate_calibration_origin_ablation_diagnostic():
    """Compare one-origin and multi-origin adaptive candidate calibration."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {
        "single_origin": 1,
        "multi_origin": 3,
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)
        for name, origins in variants.items():
            config = EliteProConfig(
                candidate_count=150,
                max_tickets=14,
                adaptive_candidate_weights=True,
                candidate_calibration_draws=20,
                candidate_calibration_candidate_count=75,
                candidate_calibration_origins=origins,
                candidate_adaptive_shrinkage=0.50,
            )
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=101000 + offset
            )
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [
        multi - single
        for multi, single in zip(results["multi_origin"], results["single_origin"])
    ]
    print("Elite candidate-calibration origin ablation:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  multi_origin - single_origin={mean(difference):+.4f}")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_number_signal_strength_multi_origin_robust_diagnostic():
    """Test score-signal strength across independent chronological origins."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 30
    origins = [len(draws) - 90, len(draws) - 60, len(draws) - 30]
    strengths = (0.0, 0.25, 0.50, 0.75)
    results = {strength: [] for strength in strengths}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws[:start + offset])
            actual = set(target.numbers)
            for strength in strengths:
                config = EliteProConfig(
                    candidate_count=150,
                    max_tickets=14,
                    number_signal_strength=strength,
                )
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=102000 + start + offset
                )
                results[strength].append(
                    mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
                )

    print("Elite number-signal strength multi-origin robust diagnostic:")
    for strength in strengths:
        print(f"  strength={strength:.2f}: hits={mean(results[strength]):.4f}")

    assert all(len(values) == block * len(origins) for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())


def test_elite_adaptive_candidate_weights_multi_origin_diagnostic():
    """Compare one-origin and three-origin candidate-source calibration."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {
        "one_origin": 1,
        "three_origins": 3,
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)
        for name, origins in variants.items():
            config = EliteProConfig(
                candidate_count=150,
                max_tickets=14,
                adaptive_candidate_weights=True,
                candidate_calibration_draws=20,
                candidate_calibration_candidate_count=75,
                candidate_calibration_origins=origins,
                candidate_adaptive_shrinkage=0.50,
            )
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=99700 + offset
            )
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [
        three - one
        for three, one in zip(results["three_origins"], results["one_origin"])
    ]
    print("Elite adaptive candidate multi-origin diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  three-origins - one-origin={mean(difference):+.4f}")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_signal_calibration_origin_ablation_diagnostic():
    """Compare one-origin and multi-origin Rank/Raw/EWMA calibration."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {
        "one_origin": 1,
        "three_origins": 3,
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)
        for name, origins in variants.items():
            config = EliteProConfig(
                candidate_count=150,
                max_tickets=14,
                calibration_draws=20,
                calibration_origins=origins,
            )
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=103000 + offset
            )
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
            )

    difference = [
        multi - single
        for multi, single in zip(results["three_origins"], results["one_origin"])
    ]
    print("Elite signal-calibration origin ablation:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  three-origins - one-origin={mean(difference):+.4f}")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_gap_signal_multi_origin_robust_diagnostic():
    """Compare recency/overdue gap signals against the current Elite baseline."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 30
    origins = [len(draws) - 90, len(draws) - 60, len(draws) - 30]
    variants = {
        "current": {},
        "gap_recency": {"gap_strength": 0.20, "gap_mode": "recency"},
        "gap_overdue": {"gap_strength": 0.20, "gap_mode": "overdue"},
        "gap_adaptive_recency": {
            "adaptive_gap": True,
            "gap_mode": "recency",
            "gap_calibration_draws": 20,
            "gap_calibration_origins": 3,
        },
        "gap_adaptive_overdue": {
            "adaptive_gap": True,
            "gap_mode": "overdue",
            "gap_calibration_draws": 20,
            "gap_calibration_origins": 3,
        },
    }
    results = {name: [] for name in variants}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws=draws[:start + offset])
            actual = set(target.numbers)
            for name, kwargs in variants.items():
                config = EliteProConfig(candidate_count=150, max_tickets=14, **kwargs)
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=104000 + start + offset
                )
                results[name].append(
                    mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
                )

    print("Elite gap-signal multi-origin diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    assert all(len(values) == block * len(origins) for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for value in results.values())


def test_elite_portfolio_pair_triple_coverage_walk_forward_diagnostic():
    """Compare pair/triple-aware portfolio construction with the current portfolio."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {
        "current": (0.0, 0.0),
        "pair_triple": (0.0020, 0.0008),
    }
    results = {name: [] for name in variants}
    pair_cover = {name: [] for name in variants}
    triple_cover = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        actual = set(target.numbers)
        for name, (pair_weight, triple_weight) in variants.items():
            config = EliteProConfig(
                candidate_count=150,
                max_tickets=14,
                portfolio_pair_coverage_weight=pair_weight,
                portfolio_triple_coverage_weight=triple_weight,
            )
            result = EliteProRecommendationEngine(config).recommend(
                history, seed=105000 + offset
            )
            tickets = result.recommended_tickets
            results[name].append(
                mean(len(set(ticket) & actual) for ticket in tickets)
            )
            pair_cover[name].append(
                len({
                    combo
                    for ticket in tickets
                    for combo in __import__("itertools").combinations(sorted(ticket), 2)
                })
            )
            triple_cover[name].append(
                len({
                    combo
                    for ticket in tickets
                    for combo in __import__("itertools").combinations(sorted(ticket), 3)
                })
            )

    difference = [
        pair_triple - current
        for pair_triple, current in zip(results["pair_triple"], results["current"])
    ]
    print("Elite pair/triple portfolio coverage diagnostic:")
    for name in variants:
        print(
            f"  {name}: hits={mean(results[name]):.4f}, "
            f"pairs={mean(pair_cover[name]):.2f}, "
            f"triples={mean(triple_cover[name]):.2f}"
        )
    print(f"  pair_triple - current={mean(difference):+.4f}")

    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_elite_feature_stack_multi_origin_diagnostic():
    """Compare adaptive feature layers and their combined stack on independent origins."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 20
    origins = [len(draws) - 80, len(draws) - 60, len(draws) - 40]
    variants = {
        "baseline": {},
        "momentum": {
            "adaptive_momentum": True,
            "momentum_calibration_draws": 20,
        },
        "gap": {
            "adaptive_gap": True,
            "gap_calibration_draws": 20,
            "gap_calibration_origins": 2,
        },
        "consensus": {
            "adaptive_consensus": True,
            "consensus_calibration_draws": 20,
            "consensus_calibration_origins": 2,
        },
        "all_adaptive": {
            "adaptive_momentum": True,
            "momentum_calibration_draws": 20,
            "adaptive_gap": True,
            "gap_calibration_draws": 20,
            "gap_calibration_origins": 2,
            "adaptive_consensus": True,
            "consensus_calibration_draws": 20,
            "consensus_calibration_origins": 2,
        },
    }
    results = {name: [] for name in variants}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws[:start + offset])
            actual = set(target.numbers)
            for name, kwargs in variants.items():
                config = EliteProConfig(
                    candidate_count=150,
                    max_tickets=14,
                    **kwargs,
                )
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=106000 + start + offset
                )
                results[name].append(
                    mean(
                        len(set(ticket) & actual)
                        for ticket in result.recommended_tickets
                    )
                )

    print("Elite feature-stack multi-origin diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")

    assert all(len(values) == block * len(origins) for values in results.values())
    assert all(
        all(0 <= value <= 6 for value in values)
        for values in results.values()
    )


def test_elite_consensus_config_regression():
    """Consensus settings must exist and remain opt-in by default."""
    from lrei.lottery.elite import EliteProConfig

    config = EliteProConfig()
    assert config.adaptive_consensus is False
    assert config.consensus_strength == 0.0
    assert config.consensus_calibration_draws > 0
    assert config.consensus_calibration_origins >= 1


def test_elite_adaptive_feature_stack_multi_origin_diagnostic():
    """Compare the opt-in meta-selector with a fixed baseline on independent origins."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    block = 20
    origins = [len(draws) - 80, len(draws) - 60, len(draws) - 40]
    results = {"baseline": [], "adaptive_stack": []}

    for start in origins:
        for offset, target in enumerate(draws[start:start + block]):
            history = LotteryDataset(draws[:start + offset])
            actual = set(target.numbers)
            configs = {
                "baseline": EliteProConfig(candidate_count=120, max_tickets=14),
                "adaptive_stack": EliteProConfig(
                    candidate_count=120,
                    max_tickets=14,
                    adaptive_feature_stack=True,
                    feature_stack_calibration_draws=20,
                    feature_stack_calibration_origins=3,
                ),
            }
            for name, config in configs.items():
                result = EliteProRecommendationEngine(config).recommend(
                    history, seed=121000 + start + offset
                )
                results[name].append(
                    mean(len(set(ticket) & actual) for ticket in result.recommended_tickets)
                )

    difference = [
        adaptive - baseline
        for adaptive, baseline in zip(results["adaptive_stack"], results["baseline"])
    ]
    print("Elite adaptive feature-stack diagnostic:")
    for name, values in results.items():
        print(f"  {name}: hits={mean(values):.4f}")
    print(f"  adaptive_stack - baseline={mean(difference):+.4f}")

    assert len(difference) == block * len(origins)
    assert all(value == value for value in difference)


def test_elite_candidate_ensemble_injection_is_normalized_and_opt_in():
    base = EliteProConfig(candidate_count=90, max_tickets=14)
    engine = EliteProRecommendationEngine(base)
    variants = (
        (engine._engine(base, True, False), None),
        (engine._engine(base, False, False), None),
        (engine._engine(base, True, True), None),
    )
    assert engine._candidate_allocations(DATASET, variants)[3] == 0.0

    injected = EliteProConfig(candidate_count=90, max_tickets=14, candidate_ensemble_weight=0.25)
    injected_engine = EliteProRecommendationEngine(injected)
    injected_variants = (
        (injected_engine._engine(injected, True, False), None),
        (injected_engine._engine(injected, False, False), None),
        (injected_engine._engine(injected, True, True), None),
    )
    weights = injected_engine._candidate_allocations(DATASET, injected_variants)
    assert len(weights) == 4
    assert abs(sum(weights) - 1.0) < 1e-12
    assert abs(weights[3] - 0.25) < 1e-12


def test_elite_feature_stack_stability_gate_defaults_and_validation():
    config = EliteProConfig()
    assert config.feature_stack_min_improvement == 0.01
    assert config.feature_stack_min_origin_win_rate == 0.60
    for kwargs in (
        {"feature_stack_min_improvement": -0.01},
        {"feature_stack_min_origin_win_rate": -0.1},
        {"feature_stack_min_origin_win_rate": 1.1},
    ):
        try:
            EliteProConfig(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")
def test_elite_production_profile_is_locked_to_validated_defaults():
    config = EliteProConfig()
    assert config.max_tickets == 14
    assert config.candidate_count >= 14
    assert config.adaptive_weights is True
    assert config.adaptive_candidate_weights is True
    assert config.candidate_calibration_origins >= 1
    assert config.candidate_ensemble_weight == 0.0
    assert config.adaptive_feature_stack is False
    assert config.momentum_strength == 0.0
    assert config.gap_strength == 0.0
    assert config.consensus_strength == 0.0


def test_elite_adaptive_strong_number_is_opt_in_and_validated():
    base = EliteProConfig(candidate_count=90, max_tickets=14)
    assert base.adaptive_strong_number is False
    for kwargs in (
        {"strong_calibration_draws": -1},
        {"strong_adaptive_shrinkage": -0.1},
        {"strong_adaptive_shrinkage": 1.1},
    ):
        try:
            EliteProConfig(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")


def test_elite_adaptive_strong_number_scores_are_valid():
    config = EliteProConfig(
        candidate_count=90,
        max_tickets=14,
        adaptive_strong_number=True,
        strong_calibration_draws=20,
        strong_adaptive_shrinkage=0.50,
    )
    scores = EliteProRecommendationEngine(config)._strong_scores_adaptive(DATASET)
    assert len(scores) == 7
    assert {item.number for item in scores} == set(range(1, 8))
    assert all(item.score >= 0.0 for item in scores)


def test_elite_adaptive_strong_number_walk_forward_diagnostic():
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset

    draws = list(DATASET.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    results = {"frequency": [], "adaptive": []}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = target.strong_number
        for name, adaptive in (("frequency", False), ("adaptive", True)):
            config = EliteProConfig(
                candidate_count=120,
                max_tickets=14,
                adaptive_strong_number=adaptive,
                strong_calibration_draws=20,
                strong_adaptive_shrinkage=0.50,
            )
            scores = EliteProRecommendationEngine(config)._strong_scores_adaptive(history)
            predicted = max(scores, key=lambda item: (item.score, -item.number)).number
            results[name].append(1 if predicted == actual else 0)

    difference = [adaptive - frequency for adaptive, frequency in zip(results["adaptive"], results["frequency"])]
    print("Elite strong-number diagnostic:")
    print(f"  frequency hit-rate={mean(results['frequency']):.4f}")
    print(f"  adaptive hit-rate={mean(results['adaptive']):.4f}")
    print(f"  adaptive-frequency={mean(difference):+.4f}")

    assert len(difference) == holdout
    assert all(value in (-1, 0, 1) for value in difference)
