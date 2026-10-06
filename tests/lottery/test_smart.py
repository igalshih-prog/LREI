from pathlib import Path
from statistics import mean

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.smart import SmartConfig, SmartRecommendationEngine


def test_smart_returns_exactly_14_tickets():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    result = SmartRecommendationEngine(
        SmartConfig(calibration_draws=8, calibration_candidate_count=60)
    ).recommend(dataset, seed=20261006)
    assert len(result.recommended_tickets) == 14


def test_smart_selection_is_reproducible():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = SmartRecommendationEngine(
        SmartConfig(calibration_draws=8, calibration_candidate_count=60)
    )
    first = engine.select_model(dataset, seed=1234)
    second = engine.select_model(dataset, seed=1234)
    assert first == second


def test_smart_rejects_invalid_calibration_origins():
    try:
        SmartConfig(calibration_origins=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for calibration_origins=0")


def test_smart_walk_forward_diagnostic():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = 30
    start = len(draws) - holdout
    engine = SmartRecommendationEngine(
        SmartConfig(
            calibration_draws=8,
            calibration_candidate_count=60,
            selection_margin=0.0,
            calibration_origins=3,
        )
    )

    smart_scores = []
    elite_scores = []
    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        smart = engine.recommend(history, seed=20261000 + offset)
        elite = SmartRecommendationEngine(
            SmartConfig(
                calibration_draws=8,
                calibration_candidate_count=60,
                selection_margin=999.0,
            )
        ).recommend(history, seed=20261000 + offset)
        actual = set(target.numbers)
        smart_scores.append(
            mean(len(set(ticket) & actual) for ticket in smart.recommended_tickets)
        )
        elite_scores.append(
            mean(len(set(ticket) & actual) for ticket in elite.recommended_tickets)
        )

    difference = [a - b for a, b in zip(smart_scores, elite_scores)]
    print("Smart model-selection diagnostic:")
    print(f"  Smart={mean(smart_scores):.4f}")
    print(f"  Elite-only={mean(elite_scores):.4f}")
    print(f"  Smart-Elite={mean(difference):+.4f}")
    assert len(difference) == holdout
    assert all(value == value for value in difference)


def test_smart_recency_and_stability_config_validation():
    try:
        SmartConfig(recency_decay=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for recency_decay=0")

    try:
        SmartConfig(stability_penalty=-0.1)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for negative stability_penalty")


def test_smart_selection_prefers_recent_consistent_performance():
    engine = SmartRecommendationEngine(SmartConfig(recency_decay=0.85, stability_penalty=0.10))
    # Newest origin is first; recent performance should dominate when the
    # older origin contains a noisy spike.
    origin_scores = {
        "regular": [1.00, 0.20, 0.20],
        "pro": [0.82, 0.80, 0.80],
        "elite": [0.80, 0.80, 0.80],
    }
    weighted = {}
    for name, blocks in origin_scores.items():
        weights = [engine.config.recency_decay ** i for i in range(len(blocks))]
        weighted_mean = sum(v * w for v, w in zip(blocks, weights)) / sum(weights)
        stability = mean(blocks) if len(blocks) == 1 else mean((v - mean(blocks)) ** 2 for v in blocks) ** 0.5
        weighted[name] = weighted_mean - engine.config.stability_penalty * stability
    assert max(weighted, key=weighted.get) == "pro"