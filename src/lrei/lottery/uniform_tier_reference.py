"""Exact uniform-reference Lotto prize-tier probabilities; research only.

These probabilities assume a uniformly chosen 6/37 main set and 1/7 strong
number, independently of a fixed winning outcome. They do not estimate
player behavior, total sales, payout, or expected return.
"""

from __future__ import annotations

from math import comb

MAIN_POOL = 37
MAIN_PICK = 6
STRONG_POOL = 7


def uniform_tier_probability(main_matches: int, strong_match: bool) -> float:
    """Return exact uniform-reference probability of one disjoint match class.

    Invalid counts and non-boolean strong flags are rejected rather than
    silently coerced. This is NOT a model of human ticket selections.
    """
    if type(main_matches) is not int or not 0 <= main_matches <= MAIN_PICK:
        raise ValueError("main_matches must be an integer in [0, 6]")
    if type(strong_match) is not bool:
        raise ValueError("strong_match must be bool")
    main_count = comb(MAIN_PICK, main_matches) * comb(
        MAIN_POOL - MAIN_PICK, MAIN_PICK - main_matches
    )
    strong_count = 1 if strong_match else STRONG_POOL - 1
    return main_count * strong_count / (
        comb(MAIN_POOL, MAIN_PICK) * STRONG_POOL
    )


def uniform_reference_entry_ratio(winners: int, probability: float) -> float:
    """Diagnostic W/p under a uniform null; NEVER verified entries or sales."""
    if type(winners) is not int or winners < 0:
        raise ValueError("winners must be a nonnegative integer")
    if not 0 < probability <= 1:
        raise ValueError("probability must be in (0, 1]")
    return winners / probability
