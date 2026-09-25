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
