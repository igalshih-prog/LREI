from datetime import datetime
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


def test_real_lottery_dataset_is_chronological_contiguous_and_has_valid_strong():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"
    dataset = CsvDatasetLoader().load(data_file)

    draw_ids = [int(draw.draw_id) for draw in dataset]
    assert all(right == left + 1 for left, right in zip(draw_ids, draw_ids[1:]))

    dates = [datetime.strptime(draw.date, "%d-%m-%y").date() for draw in dataset]
    assert dates == sorted(dates)

    # Wall-clock freshness is a *separate operational red/green gate*:
    # python -m lrei.lottery.dataset_freshness --dataset data/lottery.csv
    # Do not let a stale but unchanged CSV make unrelated code regressions red.
    # The runtime prospective batch still fails closed on both latest draw ID
    # and <=4 Israel-local calendar days before allowing any forecast.

    assert all(draw.strong_number is not None and 1 <= draw.strong_number <= 7 for draw in dataset)
