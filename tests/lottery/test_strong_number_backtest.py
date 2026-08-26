from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_real_backtest_generates_strong_numbers():
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

    for case in result.cases:
        assert case.recommended_ticket_count > 0


def test_real_dataset_has_strong_number_in_recommendations():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    statistics = backtester_statistics(dataset)

    assert statistics.total_strong_numbers > 0
    assert len(statistics.strong_number_frequency) > 0


def backtester_statistics(dataset):
    from lrei.lottery.statistics import LotteryStatistics

    return LotteryStatistics.from_dataset(dataset)
