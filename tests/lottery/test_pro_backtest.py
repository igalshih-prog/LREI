from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.pro import ProRecommendationEngine
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.statistics import LotteryStatistics


def _load_chronological() -> LotteryDataset:
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    return LotteryDataset(reversed(dataset.draws))


def _score(recommended, actual):
    actual_numbers = set(actual.numbers)
    matches = [len(set(ticket) & actual_numbers) for ticket in recommended]
    return max(matches, default=0), sum(matches)


def test_print_regular_vs_pro_historical_backtest():
    dataset = _load_chronological()
    train_size = max(1000, len(dataset) - 250)
    test_draws = dataset.draws[train_size:]

    regular = RecommendationEngine()
    pro = ProRecommendationEngine()

    regular_best = []
    regular_total = []
    pro_best = []
    pro_total = []
    regular_strong = 0
    pro_strong = 0

    for index, actual in enumerate(test_draws):
        training = LotteryDataset(dataset.draws[: train_size + index])
        statistics = LotteryStatistics.from_dataset(training)
        seed = 10000 + index

        regular_result = regular.recommend(statistics=statistics, ticket_count=14, seed=seed)
        pro_result = pro.recommend(dataset=training, seed=seed)

        rb, rt = _score(regular_result.recommended_tickets, actual)
        pb, pt = _score(pro_result.recommended_tickets, actual)
        regular_best.append(rb)
        regular_total.append(rt)
        pro_best.append(pb)
        pro_total.append(pt)

        if actual.strong_number is not None:
            regular_strong += sum(
                1
                for ticket in regular_result.recommended_tickets_with_strong
                if ticket.strong_number == actual.strong_number
            )
            pro_strong += sum(
                1
                for ticket in pro_result.recommended_tickets_with_strong
                if ticket.strong_number == actual.strong_number
            )

    print("\n=== REGULAR vs PRO (historical only) ===")
    print(f"Dataset draws: {len(dataset)}")
    print(f"Test draws: {len(test_draws)}")
    print("Tickets per draw: 14")
    print(f"Regular average total main-number matches: {sum(regular_total)/len(regular_total):.4f}")
    print(f"Pro average total main-number matches:     {sum(pro_total)/len(pro_total):.4f}")
    print(f"Regular average best ticket:                {sum(regular_best)/len(regular_best):.4f}")
    print(f"Pro average best ticket:                    {sum(pro_best)/len(pro_best):.4f}")
    for threshold in (3, 4, 5, 6):
        print(f"Regular best >= {threshold}: {sum(x >= threshold for x in regular_best)}")
        print(f"Pro best >= {threshold}:     {sum(x >= threshold for x in pro_best)}")
    print(f"Regular strong-number matches: {regular_strong}")
    print(f"Pro strong-number matches:     {pro_strong}")

    assert len(test_draws) > 0
