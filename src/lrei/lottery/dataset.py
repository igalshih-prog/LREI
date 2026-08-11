"""Lottery dataset models, validation, and CSV loading."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


class DatasetError(Exception):
    """Base exception for lottery dataset errors."""


class InvalidDrawError(DatasetError):
    """Raised when a lottery draw is invalid."""


@dataclass(frozen=True)
class LotteryDrawRecord:
    """A single lottery draw."""

    draw_id: str
    numbers: tuple[int, ...]
    date: str | None = None

    def __post_init__(self) -> None:
        if not self.draw_id:
            raise InvalidDrawError("draw_id cannot be empty")

        if not self.numbers:
            raise InvalidDrawError("A draw must contain at least one number")

        if any(not isinstance(number, int) for number in self.numbers):
            raise InvalidDrawError("All lottery numbers must be integers")

        if any(number <= 0 for number in self.numbers):
            raise InvalidDrawError("Lottery numbers must be positive")

        if len(set(self.numbers)) != len(self.numbers):
            raise InvalidDrawError("Lottery numbers must be unique")


class LotteryDataset:
    """Collection of validated lottery draws."""

    def __init__(self, draws: Iterable[LotteryDrawRecord] = ()) -> None:
        self._draws = tuple(draws)

    def __iter__(self) -> Iterator[LotteryDrawRecord]:
        return iter(self._draws)

    def __len__(self) -> int:
        return len(self._draws)

    def __getitem__(self, index: int) -> LotteryDrawRecord:
        return self._draws[index]

    @property
    def draws(self) -> tuple[LotteryDrawRecord, ...]:
        return self._draws

    def append(self, draw: LotteryDrawRecord) -> "LotteryDataset":
        return LotteryDataset((*self._draws, draw))

    def latest(self) -> LotteryDrawRecord:
        if not self._draws:
            raise DatasetError("Dataset is empty")
        return self._draws[-1]


@dataclass(frozen=True)
class DatasetStatistics:
    """Basic statistics about a lottery dataset."""

    draw_count: int
    number_count: int
    minimum: int | None
    maximum: int | None

    @classmethod
    def from_dataset(cls, dataset: LotteryDataset) -> "DatasetStatistics":
        numbers = [
            number
            for draw in dataset
            for number in draw.numbers
        ]

        return cls(
            draw_count=len(dataset),
            number_count=len(numbers),
            minimum=min(numbers) if numbers else None,
            maximum=max(numbers) if numbers else None,
        )


class CsvDatasetLoader:
    """Load lottery draws from a CSV file."""

    def __init__(
        self,
        draw_id_column: str = "draw_id",
        numbers_column: str = "numbers",
        date_column: str = "date",
        separator: str = ",",
    ) -> None:
        self.draw_id_column = draw_id_column
        self.numbers_column = numbers_column
        self.date_column = date_column
        self.separator = separator

    def load(self, path: str | Path) -> LotteryDataset:
        file_path = Path(path)

        if not file_path.exists():
            raise DatasetError(f"Dataset file not found: {file_path}")

        draws: list[LotteryDrawRecord] = []

        try:
            with file_path.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)

                if reader.fieldnames is None:
                    raise DatasetError("CSV file has no header")

                required = {
                    self.draw_id_column,
                    self.numbers_column,
                }

                missing = required - set(reader.fieldnames)

                if missing:
                    raise DatasetError(
                        f"Missing CSV columns: {', '.join(sorted(missing))}"
                    )

                for row_number, row in enumerate(reader, start=2):
                    try:
                        draw_id = (row[self.draw_id_column] or "").strip()
                        raw_numbers = (row[self.numbers_column] or "").strip()
                        date = (
                            (row.get(self.date_column) or "").strip()
                            or None
                        )

                        numbers = self._parse_numbers(raw_numbers)

                        draws.append(
                            LotteryDrawRecord(
                                draw_id=draw_id,
                                numbers=numbers,
                                date=date,
                            )
                        )

                    except (KeyError, ValueError, InvalidDrawError) as exc:
                        raise DatasetError(
                            f"Invalid row {row_number}: {exc}"
                        ) from exc

        except OSError as exc:
            raise DatasetError(
                f"Could not read dataset file: {file_path}"
            ) from exc

        return LotteryDataset(draws)

    @staticmethod
    def _parse_numbers(value: str) -> tuple[int, ...]:
        if not value:
            raise InvalidDrawError("numbers cannot be empty")

        parts = [
            part.strip()
            for part in value.replace(";", ",").split(",")
            if part.strip()
        ]

        try:
            numbers = tuple(int(part) for part in parts)
        except ValueError as exc:
            raise InvalidDrawError(
                "numbers must contain integers"
            ) from exc

        return numbers


class WalkForwardDataset:
    """Create chronological train/test splits without shuffling."""

    def __init__(
        self,
        dataset: LotteryDataset,
        train_size: int,
        test_size: int = 1,
    ) -> None:
        if train_size <= 0:
            raise ValueError("train_size must be positive")

        if test_size <= 0:
            raise ValueError("test_size must be positive")

        if train_size + test_size > len(dataset):
            raise DatasetError(
                "train_size + test_size exceeds dataset size"
            )

        self.dataset = dataset
        self.train_size = train_size
        self.test_size = test_size

    def splits(self) -> Iterator[tuple[LotteryDataset, LotteryDataset]]:
        start = self.train_size

        while start + self.test_size <= len(self.dataset):
            train = LotteryDataset(self.dataset.draws[:start])
            test = LotteryDataset(
                self.dataset.draws[start:start + self.test_size]
            )

            yield train, test
            start += self.test_size
