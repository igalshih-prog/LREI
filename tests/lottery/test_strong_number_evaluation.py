from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.statistics import LotteryStatistics


def load_real_dataset():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"
    return CsvDatasetLoader().load(data_file)


def test_strong_number_statistics_exist():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    assert statistics.total_strong_numbers > 0
    assert statistics.strong_number_frequency


def test_strong_number_frequencies_sum_to_one():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    total = sum(
        item.frequency
        for item in statistics.strong_number_frequency
    )

    assert abs(total - 1.0) < 1e-9


def test_strong_number_frequency_data_is_valid():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    for item in statistics.strong_number_frequency:
        assert item.number > 0
        assert item.count > 0
        assert item.frequency > 0


def test_most_frequent_strong_numbers_returns_valid_data():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    result = statistics.most_frequent_strong(7)

    assert result
    assert len(result) <= 7

    counts = [item.count for item in result]

    assert counts == sorted(counts, reverse=True)


def test_least_frequent_strong_numbers_returns_valid_data():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    result = statistics.least_frequent_strong(7)

    assert result
    assert len(result) <= 7

    counts = [item.count for item in result]

    assert counts == sorted(counts)


def test_strong_frequency_lookup():
    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    first = statistics.strong_number_frequency[0]

    result = statistics.strong_frequency_for(first.number)

    assert result is not None
    assert result.number == first.number
    assert result.count == first.count
    assert result.frequency == first.frequency
