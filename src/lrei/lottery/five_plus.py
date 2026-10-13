"""Exact 5+-main hit coverage and the 14-line combinatorial ceiling.

For a fair 6-of-37 lottery, a fixed six-number line is hit at least five
times by 1 + C(6, 5)*C(31, 1) = 187 possible main-number draws.

Two distinct lines must share four or more numbers to be hit five or more
times by the same six-number draw. Therefore any portfolio with pairwise
intersections <=3 has DISJOINT 5+ events and attains the union-bound maximum.
The existing Smart 4+ engine enforces the stronger intersection <=1 and
already reaches this ceiling; this module does not claim to predict draws.
"""

from __future__ import annotations

from itertools import combinations
from math import comb
from typing import Iterable, Sequence

from .portfolio_coverage import portfolio_coverage


TOTAL_MAIN_DRAWS = comb(37, 6)
OUTCOMES_PER_LINE_5PLUS = 1 + comb(6, 5) * comb(31, 1)
FIXED_PORTFOLIO_SIZE = 14
MAX_FIVE_PLUS_OUTCOMES = FIXED_PORTFOLIO_SIZE * OUTCOMES_PER_LINE_5PLUS
MAX_FIVE_PLUS_PROBABILITY = MAX_FIVE_PLUS_OUTCOMES / TOTAL_MAIN_DRAWS


def five_plus_metrics(tickets: Iterable[Sequence[int]]) -> dict[str, int | float | bool]:
    """Exact chance of >=5 main matches on ANY ticket; verify optimality.

    The upper bound assumes 14 distinct six-number tickets. Computation uses
    the disjoint-event theorem where possible; otherwise exact enumeration
    of at most 14*187 candidate outcomes. Strong numbers do not affect these
    main-number-hit probabilities.
    """
    normalized = []
    seen = set()
    for ticket in tickets:
        original = tuple(ticket)
        if len(original) != 6 or any(type(n) is not int or not 1 <= n <= 37 for n in original):
            raise ValueError("each line must contain six integers in 1..37")
        line = tuple(sorted(original))
        if len(set(line)) != 6:
            raise ValueError("each line must contain six distinct main numbers")
        if line in seen:
            raise ValueError("portfolio must contain distinct main lines")
        normalized.append(line)
        seen.add(line)
    if len(normalized) != FIXED_PORTFOLIO_SIZE:
        raise ValueError("5+ goal is defined for exactly 14 unique lines")

    optimal = all(
        len(set(left).intersection(right)) <= 3
        for left, right in combinations(normalized, 2)
    )
    if optimal:
        covered = MAX_FIVE_PLUS_OUTCOMES
    else:
        covered = int(portfolio_coverage(normalized, threshold=5)["covered_draws"])

    return {
        "ticket_count": FIXED_PORTFOLIO_SIZE,
        "covered_draws": covered,
        "max_covered_draws": MAX_FIVE_PLUS_OUTCOMES,
        "total_draws": TOTAL_MAIN_DRAWS,
        "probability": covered / TOTAL_MAIN_DRAWS,
        "max_probability": MAX_FIVE_PLUS_PROBABILITY,
        "is_optimal": covered == MAX_FIVE_PLUS_OUTCOMES,
        "with_matching_strong_probability": covered / (7 * TOTAL_MAIN_DRAWS)
        if optimal else float("nan"),
    }
