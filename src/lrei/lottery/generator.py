"""Deterministic lottery ticket generation."""

from __future__ import annotations

import random
from typing import Sequence

from .predictor import NumberScore


class GeneratorError(Exception):
    """Base exception for lottery ticket generation errors."""


class TicketGenerator:
    """Generate valid lottery tickets from scored candidate numbers."""

    def __init__(
        self,
        main_number_count: int = 6,
        min_number: int = 1,
        max_number: int = 37,
    ) -> None:
        if main_number_count <= 0:
            raise ValueError("main_number_count must be positive")

        if min_number <= 0:
            raise ValueError("min_number must be positive")

        if max_number < min_number:
            raise ValueError("max_number must be >= min_number")

        available_numbers = max_number - min_number + 1

        if main_number_count > available_numbers:
            raise ValueError(
                "main_number_count cannot exceed the available number range"
            )

        self.main_number_count = main_number_count
        self.min_number = min_number
        self.max_number = max_number

    def generate_ticket(
        self,
        scores: Sequence[NumberScore],
        rng: random.Random | None = None,
    ) -> tuple[int, ...]:
        """Generate one ticket using weighted sampling without replacement."""

        if len(scores) < self.main_number_count:
            raise GeneratorError(
                "Not enough scored numbers to generate a ticket"
            )

        random_generator = rng if rng is not None else random.Random()

        candidates: list[tuple[int, float]] = []

        for item in scores:
            if not (
                self.min_number
                <= item.number
                <= self.max_number
            ):
                raise GeneratorError(
                    f"Number {item.number} is outside the valid range"
                )

            if item.score < 0:
                raise GeneratorError(
                    f"Score cannot be negative: {item.score}"
                )

            candidates.append((item.number, float(item.score)))

        numbers = [number for number, _ in candidates]

        if len(set(numbers)) != len(numbers):
            raise GeneratorError("Duplicate candidate numbers are not allowed")

        selected: list[int] = []
        remaining = candidates.copy()

        for _ in range(self.main_number_count):
            total_weight = sum(weight for _, weight in remaining)

            if total_weight <= 0:
                chosen_index = random_generator.randrange(len(remaining))
            else:
                target = random_generator.random() * total_weight
                cumulative = 0.0
                chosen_index = len(remaining) - 1

                for index, (_, weight) in enumerate(remaining):
                    cumulative += weight

                    if target < cumulative:
                        chosen_index = index
                        break

            number, _ = remaining.pop(chosen_index)
            selected.append(number)

        return tuple(sorted(selected))

    def generate_tickets(
        self,
        scores: Sequence[NumberScore],
        count: int,
        seed: int | None = None,
    ) -> tuple[tuple[int, ...], ...]:
        """Generate multiple reproducible tickets."""

        if count <= 0:
            raise ValueError("count must be positive")

        rng = random.Random(seed)

        tickets: list[tuple[int, ...]] = []

        for _ in range(count):
            tickets.append(
                self.generate_ticket(
                    scores=scores,
                    rng=rng,
                )
            )

        return tuple(tickets)
