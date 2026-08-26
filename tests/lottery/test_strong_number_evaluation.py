from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.statistics import LotteryStatistics


def test_strong_number_frequency_ranking_is_available():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    ranked = statistics.most_frequent_strong(limit=7)

    assert len(ranked) > 0

    counts = [item.count for item in ranked]

    assert counts == sorted(counts, reverse=True)


def test_strong_number_frequency_ranking_is_reproducible():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    statistics_1 = LotteryStatistics.from_dataset(dataset)
    statistics_2 = LotteryStatistics.from_dataset(dataset)

    ranking_1 = statistics_1.most_frequent_strong(limit=7)
    ranking_2 = statistics_2.most_frequent_strong(limit=7)

    assert ranking_1 == ranking_2


def test_strong_number_statistics_cover_all_observed_values():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    observed = set()

    for draw in dataset:
        if draw.strong_number is not None:
            observed.add(draw.strong_number)

    calculated = {
        item.number
        for item in statistics.strong_number_frequency
    }

    assert observed == calculated


def test_strong_number_frequencies_are_normalized():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    total_frequency = sum(
        item.frequency
        for item in statistics.strong_number_frequency
    )

    assert abs(total_frequency - 1.0) < 1e-9
