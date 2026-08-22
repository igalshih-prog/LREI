from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_backtest_report(capsys):
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
    print("=" * 50)
    print("LREI REAL DATA BACKTEST")
    print("=" * 50)
    print(f"Dataset draws: {len(dataset)}")
    print(f"Test cases: {result.case_count}")
    print()
    print("LREI")
    print(f"Best match: {result.best_match}")
    print(f"Total matches: {result.total_matches}")
    print(f"Average matches: {result.average_matches:.4f}")
    print()
    print("RANDOM BASELINE")
    print(f"Best match: {result.baseline_best_match}")
    print(f"Total matches: {result.baseline_total_matches}")
    print(
        f"Average matches: "
        f"{result.baseline_average_matches:.4f}"
    )
    print()
    print("COMPARISON")
    print(
        f"Average difference: "
        f"{result.average_matches - result.baseline_average_matches:.4f}"
    )
    print(
        f"Total difference: "
        f"{result.total_matches - result.baseline_total_matches}"
    )
    print("=" * 50)

    assert result.case_count > 0
    assert result.best_match >= 0
    assert result.total_matches >= 0
    assert result.baseline_best_match >= 0
    assert result.baseline_total_matches >= 0
