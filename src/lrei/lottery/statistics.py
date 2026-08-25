"""Statistical analysis engine for lottery draw datasets."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from lrei.lottery.dataset import LotteryDataset


@dataclass(frozen=True)
class NumberFrequency:
    """Frequency information for a single lottery number."""

    number: int
    count: int
    frequency: float


@dataclass(frozen=True)
class LotteryStatistics:
    """Statistical analysis calculated from a lottery dataset."""

    draw_count: int
    number_frequency: tuple[NumberFrequency, ...]
    total_numbers: int
    minimum_number: int | None
    maximum_number: int | None

    # Strong-number statistics.
    strong_number_frequency: tuple[NumberFrequency, ...] = ()
    total_strong_numbers: int = 0

    @classmethod
    def from_dataset(
        cls,
        dataset: LotteryDataset,
    ) -> "LotteryStatistics":
        """Calculate statistics from the supplied historical dataset."""

        main_counter: Counter[int] = Counter()
        strong_counter: Counter[int] = Counter()

        for draw in dataset:
            main_counter.update(draw.numbers)

            if draw.strong_number is not None:
                strong_counter.update([draw.strong_number])

        total_numbers = sum(main_counter.values())
        total_strong_numbers = sum(
            strong_counter.values()
        )

        frequencies = tuple(
            NumberFrequency(
                number=number,
                count=count,
                frequency=(
                    count / total_numbers
                    if total_numbers > 0
                    else 0.0
                ),
            )
            for number, count in sorted(
                main_counter.items()
            )
        )

        strong_frequencies = tuple(
            NumberFrequency(
                number=number,
                count=count,
                frequency=(
                    count / total_strong_numbers
                    if total_strong_numbers > 0
                    else 0.0
                ),
            )
            for number, count in sorted(
                strong_counter.items()
            )
        )

        return cls(
            draw_count=len(dataset),
            number_frequency=frequencies,
            total_numbers=total_numbers,
            minimum_number=(
                min(main_counter)
                if main_counter
                else None
            ),
            maximum_number=(
                max(main_counter)
                if main_counter
                else None
            ),
            strong_number_frequency=(
                strong_frequencies
            ),
            total_strong_numbers=(
                total_strong_numbers
            ),
        )

    def frequency_for(
        self,
        number: int,
    ) -> NumberFrequency | None:
        """Return frequency information for one main number."""

        for item in self.number_frequency:
            if item.number == number:
                return item

        return None

    def strong_frequency_for(
        self,
        number: int,
    ) -> NumberFrequency | None:
        """Return frequency information for one strong number."""

        for item in self.strong_number_frequency:
            if item.number == number:
                return item

        return None

    def most_frequent(
        self,
        limit: int = 10,
    ) -> tuple[NumberFrequency, ...]:
        """Return the most frequently occurring main numbers."""

        if limit <= 0:
            return ()

        return tuple(
            sorted(
                self.number_frequency,
                key=lambda item: (
                    -item.count,
                    item.number,
                ),
            )[:limit]
        )

    def least_frequent(
        self,
        limit: int = 10,
    ) -> tuple[NumberFrequency, ...]:
        """Return the least frequently occurring main numbers."""

        if limit <= 0:
            return ()

        return tuple(
            sorted(
                self.number_frequency,
                key=lambda item: (
                    item.count,
                    item.number,
                ),
            )[:limit]
        )

    def most_frequent_strong(
        self,
        limit: int = 7,
    ) -> tuple[NumberFrequency, ...]:
        """Return the most frequent strong numbers."""

        if limit <= 0:
            return ()

        return tuple(
            sorted(
                self.strong_number_frequency,
                key=lambda item: (
                    -item.count,
                    item.number,
                ),
            )[:limit]
        )

    def least_frequent_strong(
        self,
        limit: int = 7,
    ) -> tuple[NumberFrequency, ...]:
        """Return the least frequent strong numbers."""

        if limit <= 0:
            return ()

        return tuple(
            sorted(
                self.strong_number_frequency,
                key=lambda item: (
                    item.count,
                    item.number,
                ),
            )[:limit]
        )
