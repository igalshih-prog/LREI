"""Exact *single-line* fair-draw prize-tier odds, independent of payout data.

Not a 14-line portfolio probability, an observed payout, an expected-value
estimate, or evidence for prediction advantage. No external data is read.
"""
from __future__ import annotations

from fractions import Fraction
from math import comb

TOTAL_MAIN_OUTCOMES = comb(37, 6)
TOTAL_OUTCOMES = TOTAL_MAIN_OUTCOMES * 7


def main_match_outcomes(matches: int) -> int:
    """Number of equally likely six-number draws matching one fixed line."""
    if type(matches) is not int or not 0 <= matches <= 6:
        raise ValueError("matches must be an integer in 0..6")
    return comb(6, matches) * comb(31, 6 - matches)


def exact_single_line_tier_probabilities() -> dict[int, Fraction]:
    """Return probabilities of eight Israeli 6/37 + 1/7 prize tiers.

    Per main-match count 3..6, exactly one strong outcome matches and six
    do not. These events are disjoint; the remaining probability is no prize.
    """
    tiers: dict[int, Fraction] = {}
    for matches in (6, 5, 4, 3):
        base = main_match_outcomes(matches)
        strong_tier = 1 + 2 * (6 - matches)
        tiers[strong_tier] = Fraction(base, TOTAL_OUTCOMES)
        tiers[strong_tier + 1] = Fraction(6 * base, TOTAL_OUTCOMES)
    return tiers


def exact_single_line_no_prize_probability() -> Fraction:
    """Complement for fewer than three main-number matches."""
    return 1 - sum(exact_single_line_tier_probabilities().values(), Fraction(0))
