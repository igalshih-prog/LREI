import random
from pathlib import Path
from statistics import mean

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.pro import ProRecommendationEngine


def _hits(tickets, actual):
    actual_set = set(actual)
    return [len(set(ticket) & actual_set) for ticket in tickets]


def _random_portfolio(rng, max_number=37, ticket_size=6, ticket_count=14):
    return tuple(
        tuple(sorted(rng.sample(range(1, max_number + 1), ticket_size)))
        for _ in range(ticket_count)
    )


def test_pro_against_random_baseline_walk_forward():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    assert len(draws) > 200

    holdout = min(50, max(30, len(draws) // 20))
    first_test_index = len(draws) - holdout

    pro_average_hits = []
    random_average_hits = []
    pro_best_hits = []
    random_best_hits = []

    baseline_rng = random.Random(20260916)
    pro_engine = ProRecommendationEngine()

    for index, target in enumerate(draws[first_test_index:]):
        history = LotteryDataset(draws=draws[: first_test_index + index])
        pro = pro_engine.recommend(history, seed=5000 + index)
        pro_hits = _hits(pro.recommended_tickets[:14], target.numbers)

        random_portfolio = _random_portfolio(baseline_rng)
        random_hits = _hits(random_portfolio, target.numbers)

        pro_average_hits.append(mean(pro_hits))
        random_average_hits.append(mean(random_hits))
        pro_best_hits.append(max(pro_hits))
        random_best_hits.append(max(random_hits))

    print(f"Walk-forward draws: {holdout}")
    print(f"Pro mean hits / ticket: {mean(pro_average_hits):.4f}")
    print(f"Random mean hits / ticket: {mean(random_average_hits):.4f}")
    print(f"Pro best-ticket hits: {mean(pro_best_hits):.4f}")
    print(f"Random best-ticket hits: {mean(random_best_hits):.4f}")

    assert len(pro_average_hits) == holdout
    assert len(random_average_hits) == holdout
    assert all(0 <= value <= 6 for value in pro_average_hits)
    assert all(0 <= value <= 6 for value in random_average_hits)
