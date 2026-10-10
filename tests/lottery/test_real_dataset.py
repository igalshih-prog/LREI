from datetime import datetime, timezone
from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader


def test_real_lottery_dataset_loads():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    assert len(dataset) > 0

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


def test_real_lottery_dataset_is_chronological_contiguous_and_fresh():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"
    dataset = CsvDatasetLoader().load(data_file)

    draw_ids = [int(draw.draw_id) for draw in dataset]
    assert all(right == left + 1 for left, right in zip(draw_ids, draw_ids[1:]))

    dates = [datetime.strptime(draw.date, "%d-%m-%y").date() for draw in dataset]
    assert dates == sorted(dates)

    latest_date = dates[-1]
    today_utc = datetime.now(timezone.utc).date()
    age_days = (today_utc - latest_date).days
    assert 0 <= age_days <= 14, (
        f"Lottery data is {age_days} days old (latest draw: {latest_date}); "
        "refresh data/lottery.csv before relying on recent-window analysis."
    )

    assert all(draw.strong_number is not None and 1 <= draw.strong_number <= 7 for draw in dataset)
