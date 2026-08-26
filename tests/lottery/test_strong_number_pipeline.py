from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.statistics import LotteryStatistics


def test_real_dataset_contains_strong_numbers():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    assert len(dataset) > 0
    assert statistics.total_strong_numbers > 0
    assert len(statistics.strong_number_frequency) > 0


def test_strong_number_statistics_are_valid():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    total = sum(
        item.count
        for item in statistics.strong_number_frequency
    )

    assert total == statistics.total_strong_numbers

    for item in statistics.strong_number_frequency:
        assert item.number > 0
        assert item.count > 0
        assert item.frequency > 0.0


def test_strong_number_frequencies_sum_to_one():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    frequency_sum = sum(
        item.frequency
        for item in statistics.strong_number_frequency
    )

    assert abs(frequency_sum - 1.0) < 1e-9


def test_strong_number_lookup_works():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    for item in statistics.strong_number_frequency:
        found = statistics.strong_frequency_for(item.number)

        assert found is not None
        assert found.number == item.number
        assert found.count == item.count
