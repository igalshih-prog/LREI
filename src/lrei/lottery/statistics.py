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

    @classmethod
    def from_dataset(cls, dataset: LotteryDataset) -> "LotteryStatistics":
        """Calculate statistics from the supplied historical dataset."""

        counter: Counter[int] = Counter()

        for draw in dataset:
            counter.update(draw.numbers)

        total_numbers = sum(counter.values())

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
            for number, count in sorted(counter.items())
        )

        return cls(
            draw_count=len(dataset),
            number_frequency=frequencies,
            total_numbers=total_numbers,
            minimum_number=min(counter) if counter else None,
            maximum_number=max(counter) if counter else None,
        )

    def frequency_for(self, number: int) -> NumberFrequency | None:
        """Return frequency information for one number."""

        for item in self.number_frequency:
            if item.number == number:
                return item

        return None

    def most_frequent(self, limit: int = 10) -> tuple[NumberFrequency, ...]:
        """Return the most frequently occurring numbers."""

        if limit <= 0:
            return ()

        return tuple(
            sorted(
                self.number_frequency,
                key=lambda item: (-item.count, item.number),
            )[:limit]
        )

    def least_frequent(self, limit: int = 10) -> tuple[NumberFrequency, ...]:
        """Return the least frequently occurring numbers."""

        if limit <= 0:
            return ()

        return tuple(
            sorted(
                self.number_frequency,
                key=lambda item: (item.count, item.number),
            )[:limit]
        )
