"""Exact theoretical coverage metrics for a portfolio of lottery tickets."""

from __future__ import annotations

from itertools import combinations
from math import comb
from typing import Iterable, Sequence


def portfolio_coverage(
    tickets: Iterable[Sequence[int]],
    *,
    threshold: int = 4,
    max_number: int = 37,
    draw_size: int = 6,
) -> dict[str, int | float]:
    """Count exact draw outcomes where at least one ticket matches threshold+ numbers.

    This measures coverage under a uniform draw model. It does not predict which
    numbers will be drawn and does not use historical frequencies.
    """
    if max_number < draw_size:
        raise ValueError("max_number must be at least draw_size")
    if not 1 <= threshold <= draw_size:
        raise ValueError("threshold must be between 1 and draw_size")

    normalized: list[tuple[int, ...]] = []
    for ticket in tickets:
        values = tuple(sorted(ticket))
        if len(values) != draw_size or len(set(values)) != draw_size:
            raise ValueError(f"each ticket must contain {draw_size} unique numbers")
        if any(number < 1 or number > max_number for number in values):
            raise ValueError(f"ticket numbers must be between 1 and {max_number}")
        if values not in normalized:
            normalized.append(values)

    covered: set[tuple[int, ...]] = set()
    universe = set(range(1, max_number + 1))
    for ticket in normalized:
        outside = sorted(universe.difference(ticket))
        for matched_count in range(threshold, draw_size + 1):
            for matched in combinations(ticket, matched_count):
                needed = draw_size - matched_count
                for remainder in combinations(outside, needed):
                    covered.add(tuple(sorted((*matched, *remainder))))

    total = comb(max_number, draw_size)
    return {
        "ticket_count": len(normalized),
        "threshold": threshold,
        "covered_draws": len(covered),
        "total_draws": total,
        "probability": len(covered) / total,
    }
