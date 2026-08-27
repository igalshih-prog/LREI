```python
from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.statistics import LotteryStatistics


def load_real_dataset():
    """Load the real lottery dataset used by the integration tests."""

    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    return CsvDatasetLoader().load(data_file)


def test_real_backtest_generates_strong_numbers():
    """The real-data backtest must generate recommendations."""

    dataset = load_real_dataset()
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
        assert case.generated_ticket_count > 0


def test_real_dataset_has_strong_number_statistics():
    """The real dataset must contain strong-number statistics."""

    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    assert statistics.total_strong_numbers > 0
    assert len(statistics.strong_number_frequency) > 0


def test_real_dataset_strong_number_frequencies_are_valid():
    """Strong-number frequencies must be internally consistent."""

    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    assert statistics.total_strong_numbers == dataset.strong_number_count

    total_frequency = sum(
        item.frequency
        for item in statistics.strong_number_frequency
    )

    assert abs(total_frequency - 1.0) < 1e-9


def test_real_dataset_strong_number_counts_are_positive():
    """Every observed strong number must have a positive count."""

    dataset = load_real_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    for item in statistics.strong_number_frequency:
        assert item.number > 0
        assert item.count > 0
        assert item.frequency > 0.0


def test_real_backtest_is_reproducible():
    """The same seed must produce the same backtest result."""

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
```
