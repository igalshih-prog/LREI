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
        strong_min_number: int = 1,
        strong_max_number: int = 7,
    ) -> None:
        if main_number_count <= 0:
            raise ValueError(
                "main_number_count must be positive"
            )

        if min_number <= 0:
            raise ValueError(
                "min_number must be positive"
            )

        if max_number < min_number:
            raise ValueError(
                "max_number must be >= min_number"
            )

        available_numbers = (
            max_number - min_number + 1
        )

        if main_number_count > available_numbers:
            raise ValueError(
                "main_number_count cannot exceed "
                "the available number range"
            )

        if strong_min_number <= 0:
            raise ValueError(
                "strong_min_number must be positive"
            )

        if strong_max_number < strong_min_number:
            raise ValueError(
                "strong_max_number must be >= "
                "strong_min_number"
            )

        self.main_number_count = main_number_count
        self.min_number = min_number
        self.max_number = max_number
        self.strong_min_number = strong_min_number
        self.strong_max_number = strong_max_number

    def generate_ticket(
        self,
        scores: Sequence[NumberScore],
        rng: random.Random | None = None,
    ) -> tuple[int, ...]:
        """Generate one main-number ticket."""

        if len(scores) < self.main_number_count:
            raise GeneratorError(
                "Not enough scored numbers to generate a ticket"
            )

        random_generator = (
            rng if rng is not None else random.Random()
        )

        candidates: list[tuple[int, float]] = []

        for item in scores:
            if not (
                self.min_number
                <= item.number
                <= self.max_number
            ):
                raise GeneratorError(
                    f"Number {item.number} is outside "
                    "the valid range"
                )

            if item.score < 0:
                raise GeneratorError(
                    f"Score cannot be negative: {item.score}"
                )

            candidates.append(
                (item.number, float(item.score))
            )

        numbers = [
            number
            for number, _ in candidates
        ]

        if len(set(numbers)) != len(numbers):
            raise GeneratorError(
                "Duplicate candidate numbers are not allowed"
            )

        return self._weighted_sample_without_replacement(
            candidates=candidates,
            count=self.main_number_count,
            rng=random_generator,
        )

    def generate_strong_number(
        self,
        scores: Sequence[NumberScore],
        rng: random.Random | None = None,
    ) -> int:
        """Generate one strong number using weighted sampling."""

        if not scores:
            raise GeneratorError(
                "No scored strong numbers available"
            )

        random_generator = (
            rng if rng is not None else random.Random()
        )

        candidates: list[tuple[int, float]] = []

        for item in scores:
            if not (
                self.strong_min_number
                <= item.number
                <= self.strong_max_number
            ):
                raise GeneratorError(
                    f"Strong number {item.number} is outside "
                    "the valid range"
                )

            if item.score < 0:
                raise GeneratorError(
                    f"Score cannot be negative: {item.score}"
                )

            candidates.append(
                (item.number, float(item.score))
            )

        numbers = [
            number
            for number, _ in candidates
        ]

        if len(set(numbers)) != len(numbers):
            raise GeneratorError(
                "Duplicate strong candidate numbers "
                "are not allowed"
            )

        selected = self._weighted_sample_without_replacement(
            candidates=candidates,
            count=1,
            rng=random_generator,
        )

        return selected[0]

    def generate_ticket_with_strong(
        self,
        scores: Sequence[NumberScore],
        strong_scores: Sequence[NumberScore],
        rng: random.Random | None = None,
    ) -> tuple[tuple[int, ...], int]:
        """Generate six main numbers and one strong number."""

        random_generator = (
            rng if rng is not None else random.Random()
        )

        ticket = self.generate_ticket(
            scores=scores,
            rng=random_generator,
        )

        strong_number = self.generate_strong_number(
            scores=strong_scores,
            rng=random_generator,
        )

        return ticket, strong_number

    def generate_tickets(
        self,
        scores: Sequence[NumberScore],
        count: int,
        seed: int | None = None,
    ) -> tuple[tuple[int, ...], ...]:
        """Generate multiple reproducible main-number tickets."""

        if count <= 0:
            raise ValueError(
                "count must be positive"
            )

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

    def generate_tickets_with_strong(
        self,
        scores: Sequence[NumberScore],
        strong_scores: Sequence[NumberScore],
        count: int,
        seed: int | None = None,
    ) -> tuple[tuple[tuple[int, ...], int], ...]:
        """Generate multiple reproducible tickets with strong numbers."""

        if count <= 0:
            raise ValueError(
                "count must be positive"
            )

        rng = random.Random(seed)

        tickets: list[
            tuple[tuple[int, ...], int]
        ] = []

        for _ in range(count):
            tickets.append(
                self.generate_ticket_with_strong(
                    scores=scores,
                    strong_scores=strong_scores,
                    rng=rng,
                )
            )

        return tuple(tickets)

    @staticmethod
    def _weighted_sample_without_replacement(
        candidates: Sequence[tuple[int, float]],
        count: int,
        rng: random.Random,
    ) -> tuple[int, ...]:
        if count <= 0:
            raise GeneratorError(
                "count must be positive"
            )

        if len(candidates) < count:
            raise GeneratorError(
                "Not enough candidates"
            )

        remaining = list(candidates)
        selected: list[int] = []

        for _ in range(count):
            total_weight = sum(
                weight
                for _, weight in remaining
            )

            if total_weight <= 0:
                chosen_index = rng.randrange(
                    len(remaining)
                )
            else:
                target = (
                    rng.random()
                    * total_weight
                )

                cumulative = 0.0
                chosen_index = (
                    len(remaining) - 1
                )

                for index, (_, weight) in enumerate(
                    remaining
                ):
                    cumulative += weight

                    if target < cumulative:
                        chosen_index = index
                        break

            number, _ = remaining.pop(
                chosen_index
            )

            selected.append(number)

        return tuple(sorted(selected))
