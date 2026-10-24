"""Synthetic combinatorial identities only; no draws or operator payouts."""
from fractions import Fraction
from math import comb

import pytest

from lrei.lottery.prize_tier_odds import (
    TOTAL_MAIN_OUTCOMES,
    TOTAL_OUTCOMES,
    exact_single_line_no_prize_probability,
    exact_single_line_tier_probabilities,
    main_match_outcomes,
)


def test_main_match_outcomes_partition_all_fair_draws():
    assert TOTAL_MAIN_OUTCOMES == comb(37, 6)
    assert TOTAL_OUTCOMES == 7 * comb(37, 6)
    assert sum(main_match_outcomes(k) for k in range(7)) == TOTAL_MAIN_OUTCOMES


def test_all_eight_tiers_have_exact_fair_draw_probabilities():
    tiers = exact_single_line_tier_probabilities()
    assert set(tiers) == set(range(1, 9))
    for k in (6, 5, 4, 3):
        strong = 1 + 2 * (6 - k)
        assert tiers[strong] == Fraction(comb(6, k) * comb(31, 6 - k), TOTAL_OUTCOMES)
        assert tiers[strong + 1] == 6 * tiers[strong]
    assert tiers[1] == Fraction(1, TOTAL_OUTCOMES)
    assert sum(tiers.values(), Fraction(0)) + exact_single_line_no_prize_probability() == 1
    assert exact_single_line_no_prize_probability() == Fraction(
        sum(main_match_outcomes(k) for k in range(3)), TOTAL_MAIN_OUTCOMES
    )


@pytest.mark.parametrize("invalid", [None, True, False, -1, 7, 2.0, "3"])
def test_invalid_main_match_counts_fail_closed(invalid):
    with pytest.raises(ValueError, match="integer in 0..6"):
        main_match_outcomes(invalid)


def test_exact_probabilities_are_stable_immutable_rationals():
    first = exact_single_line_tier_probabilities()
    first[1] = Fraction(0)
    assert exact_single_line_tier_probabilities()[1] == Fraction(1, TOTAL_OUTCOMES)
    assert all(isinstance(v, Fraction) for v in exact_single_line_tier_probabilities().values())
