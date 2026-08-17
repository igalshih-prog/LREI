"""Final ticket selection layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .optimizer import LotteryOptimizer


class SelectionError(Exception):
    """Base exception for final ticket selection errors."""


@dataclass(frozen=True)
class SelectionResult:
    """Final selected lottery tickets."""

    tickets: tuple[tuple[int, ...], ...]


class TicketSelector:
    """Select the final tickets from optimized candidates."""

    def __init__(
        self,
        optimizer: LotteryOptimizer | None = None,
    ) -> None:
        self.optimizer = optimizer or LotteryOptimizer()

    def select(
        self,
        tickets: Sequence[Sequence[int]],
    ) -> SelectionResult:
        """Return the final optimized ticket selection."""

        if not tickets:
            raise SelectionError("No tickets were provided")

        optimized = self.optimizer.optimize(tickets)

        if not optimized:
            raise SelectionError(
                "No tickets remained after optimization"
            )

        return SelectionResult(
            tickets=optimized,
        )
