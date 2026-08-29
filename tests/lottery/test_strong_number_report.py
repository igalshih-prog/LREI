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

    strong_total = result.strong_match_count
    baseline_strong_total = (
        result.baseline_strong_match_count
    )

    strong_average = (
        strong_total / result.case_count
        if result.case_count > 0
        else 0.0
    )

    baseline_strong_average = (
        baseline_strong_total / result.case_count
        if result.case_count > 0
        else 0.0
    )

    print()
    print("=" * 60)
    print("LREI STRONG NUMBER BACKTEST")
    print("=" * 60)
    print(f"Dataset draws: {len(dataset)}")
    print(f"Test cases: {result.case_count}")
    print()

    print("LREI STRONG NUMBER")
    print(f"Correct predictions: {strong_total}")
    print(f"Average correct predictions: {strong_average:.4f}")
    print()

    print("RANDOM STRONG NUMBER")
    print(
        f"Correct predictions: "
        f"{baseline_strong_total}"
    )
    print(
        f"Average correct predictions: "
        f"{baseline_strong_average:.4f}"
    )
    print()

    print("COMPARISON")

    difference = (
        strong_average
        - baseline_strong_average
    )

    print(f"LREI advantage: {difference:+.4f}")
    print("=" * 60)

    assert result.case_count > 0
    assert strong_total >= 0
    assert baseline_strong_total >= 0
