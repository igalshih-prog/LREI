import pytest

from lrei.lottery.dataset import (
    CsvDatasetLoader,
    DatasetError,
    DatasetStatistics,
    InvalidDrawError,
    LotteryDataset,
    LotteryDrawRecord,
    WalkForwardDataset,
)


def test_lottery_draw_record_valid():
    draw = LotteryDrawRecord(
        draw_id="draw-001",
        numbers=(1, 7, 15, 22, 31, 37),
        date="2026-07-30",
    )

    assert draw.draw_id == "draw-001"
    assert draw.numbers == (1, 7, 15, 22, 31, 37)
    assert draw.date == "2026-07-30"


def test_lottery_draw_record_rejects_empty_id():
    with pytest.raises(InvalidDrawError):
        LotteryDrawRecord(
            draw_id="",
            numbers=(1, 2, 3),
        )


def test_lottery_draw_record_rejects_empty_numbers():
    with pytest.raises(InvalidDrawError):
        LotteryDrawRecord(
            draw_id="draw-001",
            numbers=(),
        )


def test_lottery_draw_record_rejects_duplicate_numbers():
    with pytest.raises(InvalidDrawError):
        LotteryDrawRecord(
            draw_id="draw-001",
            numbers=(1, 2, 2, 3),
        )


def test_lottery_draw_record_rejects_non_positive_numbers():
    with pytest.raises(InvalidDrawError):
        LotteryDrawRecord(
            draw_id="draw-001",
            numbers=(1, 0, 3),
        )


def test_lottery_dataset_basic_operations():
    draw1 = LotteryDrawRecord(
        draw_id="draw-001",
        numbers=(1, 2, 3),
    )

    draw2 = LotteryDrawRecord(
        draw_id="draw-002",
        numbers=(4, 5, 6),
    )

    dataset = LotteryDataset([draw1])

    assert len(dataset) == 1
    assert dataset[0] == draw1
    assert dataset.latest() == draw1

    updated = dataset.append(draw2)

    assert len(dataset) == 1
    assert len(updated) == 2
    assert updated.latest() == draw2


def test_empty_dataset_latest_raises():
    dataset = LotteryDataset()

    with pytest.raises(DatasetError):
        dataset.latest()


def test_dataset_statistics():
    dataset = LotteryDataset(
        [
            LotteryDrawRecord(
                draw_id="draw-001",
                numbers=(1, 10, 20),
            ),
            LotteryDrawRecord(
                draw_id="draw-002",
                numbers=(5, 15, 25),
            ),
        ]
    )

    statistics = DatasetStatistics.from_dataset(dataset)

    assert statistics.draw_count == 2
    assert statistics.number_count == 6
    assert statistics.minimum == 1
    assert statistics.maximum == 25


def test_empty_dataset_statistics():
    statistics = DatasetStatistics.from_dataset(
        LotteryDataset()
    )

    assert statistics.draw_count == 0
    assert statistics.number_count == 0
    assert statistics.minimum is None
    assert statistics.maximum is None


def test_csv_dataset_loader(tmp_path):
    csv_file = tmp_path / "draws.csv"

    csv_file.write_text(
        "draw_id,numbers,date\n"
        "draw-001,\"1,2,3,4,5,6\",2026-07-28\n"
        "draw-002,\"7,8,9,10,11,12\",2026-07-29\n",
        encoding="utf-8",
    )

    dataset = CsvDatasetLoader().load(csv_file)

    assert len(dataset) == 2
    assert dataset[0].draw_id == "draw-001"
    assert dataset[0].numbers == (1, 2, 3, 4, 5, 6)
    assert dataset[0].date == "2026-07-28"
    assert dataset[1].numbers == (7, 8, 9, 10, 11, 12)


def test_csv_dataset_loader_supports_semicolon_separator():
    loader = CsvDatasetLoader()

    numbers = loader._parse_numbers("1;2;3;4;5;6")

    assert numbers == (1, 2, 3, 4, 5, 6)


def test_csv_dataset_loader_missing_file(tmp_path):
    loader = CsvDatasetLoader()

    with pytest.raises(DatasetError):
        loader.load(tmp_path / "missing.csv")


def test_csv_dataset_loader_invalid_numbers(tmp_path):
    csv_file = tmp_path / "invalid.csv"

    csv_file.write_text(
        "draw_id,numbers,date\n"
        "draw-001,\"1,abc,3\",2026-07-30\n",
        encoding="utf-8",
    )

    with pytest.raises(DatasetError):
        CsvDatasetLoader().load(csv_file)


def test_walk_forward_dataset():
    draws = [
        LotteryDrawRecord(
            draw_id=f"draw-{index}",
            numbers=(index, index + 1, index + 2),
        )
        for index in range(1, 6)
    ]

    dataset = LotteryDataset(draws)

    walk_forward = WalkForwardDataset(
        dataset=dataset,
        train_size=3,
        test_size=1,
    )

    splits = list(walk_forward.splits())

    assert len(splits) == 2

    train1, test1 = splits[0]
    train2, test2 = splits[1]

    assert len(train1) == 3
    assert len(test1) == 1
    assert test1[0].draw_id == "draw-4"

    assert len(train2) == 4
    assert len(test2) == 1
    assert test2[0].draw_id == "draw-5"


def test_walk_forward_rejects_invalid_sizes():
    dataset = LotteryDataset(
        [
            LotteryDrawRecord(
                draw_id="draw-001",
                numbers=(1, 2, 3),
            )
        ]
    )

    with pytest.raises(ValueError):
        WalkForwardDataset(dataset, train_size=0)

    with pytest.raises(ValueError):
        WalkForwardDataset(dataset, train_size=1, test_size=0)

    with pytest.raises(DatasetError):
        WalkForwardDataset(dataset, train_size=1, test_size=1)
