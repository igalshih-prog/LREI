import math
from pathlib import Path
from statistics import mean

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.pro import ProConfig, ProRecommendationEngine


def _hits(tickets, actual):
    actual_set = set(actual)
    return mean(len(set(ticket) & actual_set) for ticket in tickets)


def test_pro_scoring_ablation_smoke():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = 20
    first_test_index = len(draws) - holdout

    variants = {
        "rank_blend": ProRecommendationEngine(
            ProConfig(candidate_count=300, use_rank_normalization=True)
        ),
        "scaled_frequency_blend": ProRecommendationEngine(
            ProConfig(candidate_count=300, use_rank_normalization=False)
        ),
    }

    results = {name: [] for name in variants}
    for index, target in enumerate(draws[first_test_index:]):
        history = LotteryDataset(draws=draws[: first_test_index + index])
        for name, engine in variants.items():
            result = engine.recommend(history, seed=9000 + index)
            results[name].append(_hits(result.recommended_tickets, target.numbers))

    print(f"Ablation draws: {holdout}")
    for name, values in results.items():
        print(f"{name} mean hits / ticket: {mean(values):.4f}")

    assert all(len(values) == holdout for values in results.values())
    assert all(0 <= value <= 6 for values in results.values() for value in values)
    assert all(math.isfinite(value) for values in results.values() for value in values)
