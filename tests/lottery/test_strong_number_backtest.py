from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.statistics import LotteryStatistics


def load_real_dataset():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"
    return CsvDatasetLoader().load(data_file)


def test_real_dataset_has_strong_number_statistics():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    assert statistics.total_strong_numbers > 0
    assert len(statistics.strong_number_frequency) > 0


def test_real_dataset_strong_number_frequencies_are_valid():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    assert statistics.total_strong_numbers > 0

    total_frequency = sum(
        item.frequency
        for item in statistics.strong_number_frequency
    )

    assert abs(total_frequency - 1.0) < 1e-9


def test_real_dataset_strong_number_counts_are_positive():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    for item in statistics.strong_number_frequency:
        assert item.number > 0
        assert item.count > 0
        assert item.frequency > 0.0


def test_real_backtest_runs_with_strong_numbers():
    dataset = load_real_dataset()
    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    assert result is not None


def test_real_backtest_is_reproducible():
    dataset = load_real_dataset()
    backtester = LotteryBacktester()

    first = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    second = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    assert first == second
