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
    """Select a diverse subset of lottery tickets."""

    def __init__(self, config: OptimizerConfig | None = None) -> None:
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

    def is_compatible(
        self,
        candidate: Sequence[int],
        selected: Iterable[Sequence[int]],
    ) -> bool:
        """Check whether candidate satisfies the overlap constraint."""

        for ticket in selected:
            if self.overlap(candidate, ticket) > self.config.max_overlap:
                return False

        return True

    def optimize(
        self,
        tickets: Iterable[Sequence[int]],
    ) -> tuple[tuple[int, ...], ...]:
        """Return a diverse deterministic subset of tickets."""

        normalized: list[tuple[int, ...]] = []

        for ticket in tickets:
            normalized_ticket = tuple(sorted(ticket))

            if not normalized_ticket:
                raise OptimizerError("Tickets cannot be empty")

            if len(set(normalized_ticket)) != len(normalized_ticket):
                raise OptimizerError(
                    f"Ticket contains duplicate numbers: {normalized_ticket}"
                )

            if normalized_ticket not in normalized:
                normalized.append(normalized_ticket)

        selected: list[tuple[int, ...]] = []

        for ticket in normalized:
            if len(selected) >= self.config.max_tickets:
                break

            if self.is_compatible(ticket, selected):
                selected.append(ticket)

        return tuple(selected)
