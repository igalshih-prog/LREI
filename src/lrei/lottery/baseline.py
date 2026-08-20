"""Random baseline for lottery backtesting."""

from __future__ import annotations

import random
from dataclasses import dataclass


class BaselineError(Exception):
    """Base exception for baseline errors."""


@dataclass(frozen=True)
class RandomBaseline:
    """Generate reproducible random lottery tickets."""

    main_number_count: int = 6
    min_number: int = 1
    max_number: int = 37

    def __post_init__(self) -> None:
        if self.main_number_count <= 0:
            raise ValueError("main_number_count must be positive")

        if self.min_number <= 0:
            raise ValueError("min_number must be positive")

        if self.max_number < self.min_number:
            raise ValueError("max_number must be >= min_number")

        if self.main_number_count > (
            self.max_number - self.min_number + 1
        ):
            raise ValueError(
                "main_number_count cannot exceed the available number range"
            )

    def generate_ticket(
        self,
        rng: random.Random,
    ) -> tuple[int, ...]:
        """Generate one uniformly random valid ticket."""

        numbers = rng.sample(
            range(self.min_number, self.max_number + 1),
            self.main_number_count,
        )

        return tuple(sorted(numbers))

    def generate_tickets(
        self,
        count: int,
        seed: int | None = None,
    ) -> tuple[tuple[int, ...], ...]:
        """Generate multiple reproducible random tickets."""

        if count <= 0:
            raise ValueError("count must be positive")

        rng = random.Random(seed)

        return tuple(
            self.generate_ticket(rng)
            for _ in range(count)
        )
