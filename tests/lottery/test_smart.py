from pathlib import Path
from statistics import mean
import random

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.smart import SmartConfig, SmartRecommendationEngine
from lrei.lottery.pro import ProRecommendationEngine
from lrei.lottery.elite import EliteProConfig, EliteProRecommendationEngine


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
        elite = EliteProRecommendationEngine(
            EliteProConfig(
                candidate_count=60,
                max_tickets=14,
                adaptive_weights=False,
                adaptive_candidate_weights=False,
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
        stability = 0.0 if len(blocks) == 1 else mean((v - mean(blocks)) ** 2 for v in blocks) ** 0.5
        weighted[name] = weighted_mean - engine.config.stability_penalty * stability
    assert max(weighted, key=weighted.get) == "pro"

def test_smart_robust_walk_forward_against_models_and_random():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(30, max(24, len(draws) // 35))
    start = len(draws) - holdout
    config = SmartConfig(
        calibration_draws=6,
        calibration_candidate_count=40,
        calibration_origins=2,
        recency_decay=0.85,
        stability_penalty=0.10,
    )
    smart_scores = []
    elite_scores = []
    pro_scores = []
    random_scores = []
    smart_vs_elite = []
    smart_vs_random = []
    selections = {"regular": 0, "pro": 0, "elite": 0}

    import random

    rng = random.Random(20261007)

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[:start + offset])
        engine = SmartRecommendationEngine(config)
        smart = engine.recommend(history, seed=203000 + offset)
        selected, _ = engine.select_model(history, seed=203000 + offset)
        selections[selected] += 1

        elite = EliteProRecommendationEngine().recommend(history, seed=203000 + offset)
        pro = ProRecommendationEngine(
            __import__("lrei.lottery.pro", fromlist=["ProConfig"]).ProConfig(
                candidate_count=60,
                max_tickets=14,
            )
        ).recommend(history, seed=203000 + offset)

        random_tickets = tuple(
            tuple(sorted(rng.sample(range(1, 38), 6)))
            for _ in range(14)
        )
        actual = set(target.numbers)

        smart_scores.append(mean(len(set(ticket) & actual) for ticket in smart.recommended_tickets))
        elite_scores.append(mean(len(set(ticket) & actual) for ticket in elite.recommended_tickets))
        pro_scores.append(mean(len(set(ticket) & actual) for ticket in pro.recommended_tickets))
        random_scores.append(mean(len(set(ticket) & actual) for ticket in random_tickets))
        smart_vs_elite.append(smart_scores[-1] - elite_scores[-1])
        smart_vs_random.append(smart_scores[-1] - random_scores[-1])

    print("Smart robust walk-forward diagnostic:")
    print(f"  holdout={holdout}")
    print(f"  Smart={mean(smart_scores):.4f}")
    print(f"  Elite={mean(elite_scores):.4f}")
    print(f"  Pro={mean(pro_scores):.4f}")
    print(f"  Random={mean(random_scores):.4f}")
    def bootstrap_ci(values, seed=20261008, samples=5000):
        bootstrap_rng = random.Random(seed)
        estimates = [mean(values[bootstrap_rng.randrange(len(values))] for _ in values) for _ in range(samples)]
        estimates.sort()
        return estimates[int(0.025 * (len(estimates) - 1))], estimates[int(0.975 * (len(estimates) - 1))]

    smart_elite_ci = bootstrap_ci(smart_vs_elite)
    smart_random_ci = bootstrap_ci(smart_vs_random, seed=20261009)
    print(f"  Smart-Elite={mean(smart_vs_elite):+.4f}")
    print(f"  Smart-Random={mean(smart_vs_random):+.4f}")
    print(f"  Smart-Elite 95% CI=[{smart_elite_ci[0]:+.4f}, {smart_elite_ci[1]:+.4f}]")
    print(f"  Smart-Random 95% CI=[{smart_random_ci[0]:+.4f}, {smart_random_ci[1]:+.4f}]")
    print(f"  selections={selections}")

    assert len(smart_scores) == holdout
    assert sum(selections.values()) == holdout
    assert all(0 <= value <= 6 for value in smart_scores)
    assert all(0 <= value <= 6 for value in random_scores)


def test_smart_tail_metric_is_opt_in_and_validated():
    base = SmartConfig()
    assert base.selection_metric == "mean"
    assert base.tail_weight_4 == 0.50
    assert base.tail_weight_5 == 1.00
    assert base.tail_weight_6 == 2.00

    for kwargs in (
        {"selection_metric": "invalid"},
        {"tail_weight_4": -0.1},
        {"tail_weight_5": -0.1},
        {"tail_weight_6": -0.1},
    ):
        try:
            SmartConfig(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")


def test_smart_tail_metric_walk_forward_diagnostic():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(40, len(draws) // 18))
    start = len(draws) - holdout
    variants = {
        "mean": SmartConfig(
            calibration_draws=8,
            calibration_candidate_count=60,
            calibration_origins=3,
            selection_metric="mean",
        ),
        "tail": SmartConfig(
            calibration_draws=8,
            calibration_candidate_count=60,
            calibration_origins=3,
            selection_metric="tail",
            tail_weight_4=0.50,
            tail_weight_5=1.00,
            tail_weight_6=2.00,
        ),
    }
    results = {name: [] for name in variants}
    tail_rates = {name: {threshold: [] for threshold in (4, 5, 6)} for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws[:start + offset])
        actual = set(target.numbers)
        for name, config in variants.items():
            result = SmartRecommendationEngine(config).recommend(
                history, seed=204000 + offset
            )
            hits = [len(set(ticket) & actual) for ticket in result.recommended_tickets]
            results[name].append(mean(hits))
            for threshold in tail_rates[name]:
                tail_rates[name][threshold].append(
                    mean(hit >= threshold for hit in hits)
                )

    print("Smart selection metric diagnostic:")
    for name in variants:
        print(
            f"  {name}: mean={mean(results[name]):.4f}, "
            + ", ".join(
                f"{threshold}+={mean(tail_rates[name][threshold]):.4f}"
                for threshold in tail_rates[name]
            )
        )

    assert all(len(values) == holdout for values in results.values())
    assert all(
        len(values) == holdout
        for thresholds in tail_rates.values()
        for values in thresholds.values()
    )
