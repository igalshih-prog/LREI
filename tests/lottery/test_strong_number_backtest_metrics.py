from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_strong_number_backtest_metrics_exist():
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

    assert result.case_count > 0

    assert result.match_count_at_least(1) >= 0
    assert result.match_count_at_least(2) >= 0
    assert result.match_count_at_least(3) >= 0

    assert result.baseline_match_count_at_least(1) >= 0
    assert result.baseline_match_count_at_least(2) >= 0
    assert result.baseline_match_count_at_least(3) >= 0


def test_strong_number_backtest_is_reproducible():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    backtester = LotteryBacktester()

    result_1 = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    result_2 = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    assert result_1.cases == result_2.cases


def test_strong_number_metrics_are_non_negative():
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

    assert result.match_count_at_least(1) >= 0
    assert result.match_count_at_least(2) >= 0
    assert result.match_count_at_least(3) >= 0

    assert result.baseline_match_count_at_least(1) >= 0
    assert result.baseline_match_count_at_least(2) >= 0
    assert result.baseline_match_count_at_least(3) >= 0
