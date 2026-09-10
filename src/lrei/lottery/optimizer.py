"""Lottery ticket diversity optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


class OptimizerError(Exception):
    """Base exception for lottery optimization errors."""


@dataclass(frozen=True)
class OptimizerConfig:
    """Configuration for ticket diversity optimization."""

    max_overlap: int = 4
    max_tickets: int = 10

    def __post_init__(self) -> None:
        if self.max_overlap < 0:
            raise ValueError("max_overlap must be non-negative")

        if self.max_tickets <= 0:
            raise ValueError("max_tickets must be positive")


class LotteryOptimizer:
    """Select a diverse and well-distributed subset of lottery tickets."""

    def __init__(
        self,
        config: OptimizerConfig | None = None,
    ) -> None:
        self.config = config or OptimizerConfig()

    @staticmethod
    def overlap(
        first: Sequence[int],
        second: Sequence[int],
    ) -> int:
        """Return the number of shared numbers between two tickets."""

        return len(set(first) & set(second))

    @staticmethod
    def jaccard_similarity(
        first: Sequence[int],
        second: Sequence[int],
    ) -> float:
        """Return Jaccard similarity between two tickets."""

        first_set = set(first)
        second_set = set(second)

        union = first_set | second_set

        if not union:
            return 1.0

        return len(first_set & second_set) / len(union)

    @staticmethod
    def _ticket_spread_score(
        ticket: Sequence[int],
    ) -> float:
        """Score how broadly a ticket is distributed across its range."""

        if len(ticket) <= 1:
            return 0.0

        numbers = sorted(ticket)

        minimum = numbers[0]
        maximum = numbers[-1]

        if maximum == minimum:
            return 0.0

        gaps = [
            numbers[index + 1] - numbers[index]
            for index in range(len(numbers) - 1)
        ]

        average_gap = sum(gaps) / len(gaps)

        return average_gap / (maximum - minimum)

    @staticmethod
    def _coverage_score(
        candidate: Sequence[int],
        selected: Sequence[Sequence[int]],
    ) -> float:
        """Score how many new numbers a candidate adds to selected tickets."""

        if not candidate:
            return 0.0

        selected_numbers: set[int] = set()

        for ticket in selected:
            selected_numbers.update(ticket)

        candidate_numbers = set(candidate)

        if not selected_numbers:
            return float(len(candidate_numbers))

        new_numbers = (
            candidate_numbers - selected_numbers
        )

        return float(len(new_numbers))

    def is_compatible(
        self,
        candidate: Sequence[int],
        selected: Iterable[Sequence[int]],
    ) -> bool:
        """Check whether candidate satisfies the overlap constraint."""

        for ticket in selected:
            if (
                self.overlap(candidate, ticket)
                > self.config.max_overlap
            ):
                return False

        return True

    def _candidate_score(
        self,
        candidate: Sequence[int],
        selected: Sequence[Sequence[int]],
    ) -> tuple[float, float, float]:
        """Return a deterministic score for candidate selection."""

        coverage = self._coverage_score(
            candidate=candidate,
            selected=selected,
        )

        spread = self._ticket_spread_score(
            candidate
        )

        overlap_penalty = 0.0

        if selected:
            overlap_penalty = sum(
                self.overlap(candidate, ticket)
                for ticket in selected
            ) / len(selected)

        return (
            coverage,
            spread,
            -overlap_penalty,
        )

    def optimize(
        self,
        tickets: Iterable[Sequence[int]],
    ) -> tuple[tuple[int, ...], ...]:
        """Return a diverse deterministic subset of tickets."""

        normalized: list[tuple[int, ...]] = []

        for ticket in tickets:
            normalized_ticket = tuple(sorted(ticket))

            if not normalized_ticket:
                raise OptimizerError(
                    "Tickets cannot be empty"
                )

            if len(set(normalized_ticket)) != len(
                normalized_ticket
            ):
                raise OptimizerError(
                    "Ticket contains duplicate numbers: "
                    f"{normalized_ticket}"
                )

            if normalized_ticket not in normalized:
                normalized.append(
                    normalized_ticket
                )

        selected: list[tuple[int, ...]] = []

        while (
            len(selected)
            < self.config.max_tickets
        ):
            compatible = [
                ticket
                for ticket in normalized
                if ticket not in selected
                and self.is_compatible(
                    ticket,
                    selected,
                )
            ]

            if not compatible:
                break

            best_ticket = max(
                compatible,
                key=lambda ticket: (
                    self._candidate_score(
                        candidate=ticket,
                        selected=selected,
                    ),
                    tuple(
                        -number
                        for number in ticket
                    ),
                ),
            )

            selected.append(best_ticket)

        return tuple(selected)
