from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.pro import ProRecommendationEngine
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.statistics import LotteryStatistics


def _hit_summary(tickets, actual):
    hits = [len(set(ticket) & set(actual)) for ticket in tickets]
    return (
        sum(hits) / len(hits),
        max(hits),
        int(any(h >= 3 for h in hits)),
        int(any(h >= 4 for h in hits)),
        int(any(h >= 5 for h in hits)),
    )


def test_regular_vs_pro_10_year_dataset():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    assert len(draws) > 200

    holdout = min(141, max(100, len(draws) // 8))
    first_test_index = len(draws) - holdout
    test_draws = draws[first_test_index:]

    regular_total = regular_best = regular_3 = regular_4 = regular_5 = 0.0
    pro_total = pro_best = pro_3 = pro_4 = pro_5 = 0.0

    for index, target in enumerate(test_draws):
        # Strict walk-forward: target is never included in its own history,
        # and every earlier test draw becomes available to later predictions.
        history = LotteryDataset(draws=draws[: first_test_index + index])
        statistics = LotteryStatistics.from_dataset(history)

        regular = RecommendationEngine().recommend(
            statistics,
            ticket_count=14,
            seed=1000 + index,
        )
        pro = ProRecommendationEngine().recommend(history)

        r = _hit_summary(regular.recommended_tickets[:14], target.numbers)
        p = _hit_summary(pro.recommended_tickets[:14], target.numbers)

        regular_total += r[0]
        regular_best += r[1]
        regular_3 += r[2]
        regular_4 += r[3]
        regular_5 += r[4]
        pro_total += p[0]
        pro_best += p[1]
        pro_3 += p[2]
        pro_4 += p[3]
        pro_5 += p[4]

    n = len(test_draws)
    print(f"Dataset draws: {len(draws)}")
    print(f"Test draws: {n}")
    print("Tickets per draw: 14")
    print(f"Regular average hits across 14: {regular_total / n:.4f}")
    print(f"Pro average hits across 14: {pro_total / n:.4f}")
    print(f"Regular best single ticket: {regular_best / n:.4f}")
    print(f"Pro best single ticket: {pro_best / n:.4f}")
    print(f"Regular draws with 3+: {int(regular_3)}")
    print(f"Pro draws with 3+: {int(pro_3)}")
    print(f"Regular draws with 4+: {int(regular_4)}")
    print(f"Pro draws with 4+: {int(pro_4)}")
    print(f"Regular draws with 5+: {int(regular_5)}")
    print(f"Pro draws with 5+: {int(pro_5)}")

    assert n > 0
