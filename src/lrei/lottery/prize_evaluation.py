"""Evaluate actual Israeli Lotto prize tiers for ticket portfolios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .dataset import LotteryDrawRecord
from .recommendation import RecommendedTicket


@dataclass(frozen=True)
class TicketPrizeResult:
    """Actual prize-tier outcome for one ticket against one draw."""

    main_matches: int
    strong_match: bool
    prize_tier: int | None

    @property
    def won(self) -> bool:
        return self.prize_tier is not None


@dataclass(frozen=True)
class PortfolioPrizeResult:
    """Prize-tier outcomes for all tickets in a portfolio."""

    tickets: tuple[TicketPrizeResult, ...]

    @property
    def any_prize(self) -> bool:
        return any(ticket.won for ticket in self.tickets)

    @property
    def winning_ticket_count(self) -> int:
        return sum(ticket.won for ticket in self.tickets)

    @property
    def best_prize_tier(self) -> int | None:
        tiers = [ticket.prize_tier for ticket in self.tickets if ticket.prize_tier is not None]
        return min(tiers) if tiers else None

    @property
    def prize_tier_counts(self) -> dict[int, int]:
        counts = {tier: 0 for tier in range(1, 9)}
        for ticket in self.tickets:
            if ticket.prize_tier is not None:
                counts[ticket.prize_tier] += 1
        return counts


def _validate_main_numbers(numbers: tuple[int, ...], label: str) -> None:
    if len(numbers) != 6:
        raise ValueError(f"{label} must contain exactly six main numbers")
    if any(type(number) is not int for number in numbers):
        raise ValueError(f"{label} main numbers must be integers")
    if len(set(numbers)) != 6:
        raise ValueError(f"{label} main numbers must be unique")
    if any(number < 1 or number > 37 for number in numbers):
        raise ValueError(f"{label} main numbers must be between 1 and 37")


def _validate_strong_number(number: int | None, label: str) -> None:
    if number is not None and (type(number) is not int or not 1 <= number <= 7):
        raise ValueError(f"{label} strong number must be between 1 and 7")


def _validate_complete_draw(draw: LotteryDrawRecord) -> None:
    """A real prize tier cannot be graded without an actual strong result.

    Draw archives may represent a pending/partial draw with strong_number=None,
    but treating that omission as a non-strong match would silently demote
    otherwise winning tickets into an incorrect payout tier.
    """
    _validate_main_numbers(tuple(draw.numbers), "Draw")
    if type(draw.strong_number) is not int or not 1 <= draw.strong_number <= 7:
        raise ValueError("Draw strong number must be an integer between 1 and 7")


def evaluate_ticket_prize(
    ticket: RecommendedTicket,
    draw: LotteryDrawRecord,
) -> TicketPrizeResult:
    """Return the prize tier (1–8) the ticket would win on the supplied draw.

    Tier 1 is 6+strong, tier 2 is 6 without strong, and tiers 3–8 follow
    the published 5/4/3-main-match and strong-number prize table.
    Fewer than three main-number matches is not a prize, even if strong matches.
    """
    _validate_main_numbers(tuple(ticket.numbers), "Ticket")
    _validate_complete_draw(draw)
    _validate_strong_number(ticket.strong_number, "Ticket")

    main_matches = len(set(ticket.numbers) & set(draw.numbers))
    strong_match = (
        ticket.strong_number is not None
        and draw.strong_number is not None
        and ticket.strong_number == draw.strong_number
    )

    if main_matches < 3:
        prize_tier = None
    elif main_matches == 6:
        prize_tier = 1 if strong_match else 2
    elif main_matches == 5:
        prize_tier = 3 if strong_match else 4
    elif main_matches == 4:
        prize_tier = 5 if strong_match else 6
    else:
        prize_tier = 7 if strong_match else 8

    return TicketPrizeResult(
        main_matches=main_matches,
        strong_match=bool(strong_match),
        prize_tier=prize_tier,
    )


def evaluate_portfolio_prizes(
    tickets: Iterable[RecommendedTicket],
    draw: LotteryDrawRecord,
) -> PortfolioPrizeResult:
    """Evaluate every ticket in a portfolio against one complete historical draw.

    Validate before iterating tickets; even an empty portfolio cannot certify
    an incomplete draw as a successful no-prize evaluation.
    """
    _validate_complete_draw(draw)
    return PortfolioPrizeResult(
        tickets=tuple(evaluate_ticket_prize(ticket, draw) for ticket in tickets)
    )
