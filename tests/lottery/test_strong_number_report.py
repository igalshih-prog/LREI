from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_strong_number_report():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    print()
    print("=" * 60)
    print("LREI STRONG NUMBER BACKTEST")
    print("=" * 60)
    print(f"Dataset draws: {len(dataset)}")
    print(f"Test cases: {result.case_count}")
    print()

    print("LREI STRONG NUMBER")
    print(
        f"Correct predictions: "
        f"{result.strong_total_matches}"
    )
    print(
        f"Best result: "
        f"{result.strong_best_match}"
    )
    print(
        f"Average: "
        f"{result.strong_average_matches:.4f}"
    )
    print()

    print("RANDOM STRONG NUMBER")
    print(
        f"Correct predictions: "
        f"{result.baseline_strong_total_matches}"
    )
    print(
        f"Best result: "
        f"{result.baseline_strong_best_match}"
    )
    print(
        f"Average: "
        f"{result.baseline_strong_average_matches:.4f}"
    )
    print()

    print("COMPARISON")
    difference = (
        result.strong_average_matches
        - result.baseline_strong_average_matches
    )

    print(f"LREI advantage: {difference:+.4f}")
    print("=" * 60)

    assert result.case_count > 0
    assert result.strong_total_matches >= 0
    assert result.baseline_strong_total_matches >= 0
