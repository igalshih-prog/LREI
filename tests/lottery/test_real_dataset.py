from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader


def test_real_lottery_dataset_loads():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    assert len(dataset) == 4533

    latest = dataset.latest()

    assert latest.draw_id
    assert len(latest.numbers) == 6
    assert all(1 <= number <= 37 for number in latest.numbers)


def test_real_lottery_dataset_has_valid_draws():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    for draw in dataset:
        assert len(draw.numbers) == 6
        assert len(set(draw.numbers)) == 6
        assert all(1 <= number <= 37 for number in draw.numbers)
