import random
from pathlib import Path
from statistics import mean

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.pro import ProConfig, ProRecommendationEngine
from lrei.lottery.predictor import NumberScore


def _hits(tickets, actual):
    actual_set = set(actual)
    return mean(len(set(ticket) & actual_set) for ticket in tickets)


def _rankless_scores(engine, frequencies, recent_3, recent_1, recent_draws):
    numbers = sorted(frequencies)

    def normalise(values):
        maximum = max(values.values(), default=1)
        return {number: values.get(number, 0) / maximum for number in numbers}

    all_values = normalise(frequencies)
    three_values = normalise(recent_3)
    one_values = normalise(recent_1)
    recent_values = normalise(recent_draws)
    return tuple(
        NumberScore(
            number=number,
            score=(
                0.60 * all_values[number]
                + 0.20 * three_values[number]
                + 0.12 * one_values[number]
                + 0.08 * recent_values[number]
            ),
        )
        for number in numbers
    )


def test_pro_scoring_ablation_smoke():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = 20
    first_test_index = len(draws) - holdout

    variants = {
        "rank_blend": ProRecommendationEngine(ProConfig(candidate_count=300)),
        "frequency_blend": ProRecommendationEngine(ProConfig(candidate_count=300)),
    }
    original = variants["frequency_blend"]._individual_scores
    variants["frequency_blend"]._individual_scores = lambda a, b, c, d: _rankless_scores(
        variants["frequency_blend"], a, b, c, d
    )

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
