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


def test_exact_combinatorial_tiers_agree_with_real_prize_evaluator():
    """Cross-check two independently implemented P3 mechanisms.

    For each possible main match count, a representative synthetic draw
    should map to the same strong/non-strong tier used by the exact
    combinatorial distribution. No real lottery outcomes are read.
    """
    from lrei.lottery.dataset import LotteryDrawRecord
    from lrei.lottery.prize_evaluation import evaluate_ticket_prize
    from lrei.lottery.recommendation import RecommendedTicket

    ticket = RecommendedTicket(numbers=(1, 2, 3, 4, 5, 6), strong_number=7)
    probs = exact_single_line_tier_probabilities()
    for matches in range(7):
        numbers = (*range(1, matches + 1), *range(7, 13 - matches))
        assert len(numbers) == 6
        for strong in (7, 1):
            draw = LotteryDrawRecord(
                draw_id="synthetic-only", numbers=numbers, strong_number=strong
            )
            outcome = evaluate_ticket_prize(ticket, draw)
            assert outcome.main_matches == matches
            assert outcome.strong_match is (strong == 7)
            if matches < 3:
                assert outcome.prize_tier is None
            else:
                expected = 1 + 2 * (6 - matches) + (strong != 7)
                assert outcome.prize_tier == expected
                assert probs[expected] > 0


def test_exact_tier_distribution_yields_theoretical_any_prize_probability():
    """Single-line win probability is a sum of disjoint tier probabilities."""
    tiers = exact_single_line_tier_probabilities()
    expected = Fraction(
        sum(main_match_outcomes(k) for k in range(3, 7)),
        TOTAL_MAIN_OUTCOMES,
    )
    assert sum(tiers.values(), Fraction(0)) == expected
    assert 0 < expected < 1


@pytest.mark.parametrize("ticket_strong", range(1, 8))
def test_all_seven_strong_draw_outcomes_preserve_tier_partition(ticket_strong):
    """Guard every strong-number position, not just representative 1 and 7.

    Each fixed 6/37 line faces seven equiprobable strong outcomes. Exactly
    one must map to the odd-numbered strong tier and six to the adjacent tier.
    This is an exhaustive synthetic check over all legal strong choices.
    """
    from lrei.lottery.dataset import LotteryDrawRecord
    from lrei.lottery.prize_evaluation import evaluate_ticket_prize
    from lrei.lottery.recommendation import RecommendedTicket

    ticket = RecommendedTicket(numbers=(1, 2, 3, 4, 5, 6), strong_number=ticket_strong)
    odds = exact_single_line_tier_probabilities()
    for matches in range(7):
        numbers = (*range(1, matches + 1), *range(7, 13 - matches))
        resulting_tiers = [
            evaluate_ticket_prize(
                ticket,
                LotteryDrawRecord(
                    draw_id="synthetic-strong-partition",
                    numbers=numbers,
                    strong_number=draw_strong,
                ),
            ).prize_tier
            for draw_strong in range(1, 8)
        ]
        if matches < 3:
            assert resulting_tiers == [None] * 7
        else:
            tier = 1 + 2 * (6 - matches)
            assert resulting_tiers.count(tier) == 1
            assert resulting_tiers.count(tier + 1) == 6
            assert odds[tier + 1] == 6 * odds[tier]
