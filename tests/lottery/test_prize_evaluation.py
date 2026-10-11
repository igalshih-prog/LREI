import pytest

from lrei.lottery.dataset import LotteryDrawRecord
from lrei.lottery.prize_evaluation import (
    evaluate_portfolio_prizes,
    evaluate_ticket_prize,
)
from lrei.lottery.recommendation import RecommendedTicket


TICKET_NUMBERS = (1, 2, 3, 4, 5, 6)


def _draw(numbers, strong=7):
    return LotteryDrawRecord(
        draw_id="test-draw",
        numbers=tuple(numbers),
        strong_number=strong,
    )


@pytest.mark.parametrize(
    ("draw_numbers", "draw_strong", "expected_matches", "expected_tier"),
    [
        ((1, 2, 3, 4, 5, 6), 7, 6, 1),
        ((1, 2, 3, 4, 5, 6), 1, 6, 2),
        ((1, 2, 3, 4, 5, 12), 7, 5, 3),
        ((1, 2, 3, 4, 5, 12), 1, 5, 4),
        ((1, 2, 3, 4, 12, 13), 7, 4, 5),
        ((1, 2, 3, 4, 12, 13), 1, 4, 6),
        ((1, 2, 3, 12, 13, 14), 7, 3, 7),
        ((1, 2, 3, 12, 13, 14), 1, 3, 8),
    ],
)
def test_ticket_prize_evaluation_maps_all_eight_tiers(
    draw_numbers, draw_strong, expected_matches, expected_tier
):
    ticket = RecommendedTicket(numbers=TICKET_NUMBERS, strong_number=7)
    result = evaluate_ticket_prize(ticket, _draw(draw_numbers, draw_strong))

    assert result.main_matches == expected_matches
    assert result.strong_match is (draw_strong == 7)
    assert result.prize_tier == expected_tier
    assert result.won


def test_fewer_than_three_main_matches_is_not_a_prize_even_if_strong_matches():
    ticket = RecommendedTicket(numbers=TICKET_NUMBERS, strong_number=7)
    result = evaluate_ticket_prize(
        ticket, _draw((1, 2, 12, 13, 14, 15), strong=7)
    )

    assert result.main_matches == 2
    assert result.strong_match
    assert result.prize_tier is None
    assert not result.won


def test_missing_strong_number_uses_the_non_strong_prize_tier():
    ticket = RecommendedTicket(numbers=TICKET_NUMBERS, strong_number=None)
    result = evaluate_ticket_prize(ticket, _draw(TICKET_NUMBERS, strong=7))

    assert result.main_matches == 6
    assert not result.strong_match
    assert result.prize_tier == 2


def test_portfolio_prize_summary_counts_winners_and_best_tier():
    tickets = (
        RecommendedTicket(numbers=TICKET_NUMBERS, strong_number=7),
        RecommendedTicket(numbers=(1, 2, 3, 4, 5, 12), strong_number=7),
        RecommendedTicket(numbers=(1, 2, 3, 12, 13, 14), strong_number=1),
        RecommendedTicket(numbers=(20, 21, 22, 23, 24, 25), strong_number=7),
    )
    result = evaluate_portfolio_prizes(tickets, _draw(TICKET_NUMBERS, strong=7))

    assert result.any_prize
    assert result.winning_ticket_count == 3
    assert result.best_prize_tier == 1
    assert result.prize_tier_counts == {
        1: 1, 2: 0, 3: 1, 4: 0, 5: 0, 6: 0, 7: 0, 8: 1
    }


def test_portfolio_without_prizes_reports_no_winner():
    tickets = (
        RecommendedTicket(numbers=(20, 21, 22, 23, 24, 25), strong_number=7),
        RecommendedTicket(numbers=(26, 27, 28, 29, 30, 31), strong_number=7),
    )
    result = evaluate_portfolio_prizes(tickets, _draw(TICKET_NUMBERS, strong=7))

    assert not result.any_prize
    assert result.winning_ticket_count == 0
    assert result.best_prize_tier is None
    assert sum(result.prize_tier_counts.values()) == 0


@pytest.mark.parametrize(
    "numbers",
    [
        (1, 2, 3, 4, 5),
        (1, 2, 3, 4, 5, 5),
        (1, 2, 3, 4, 5, 38),
    ],
)
def test_invalid_ticket_main_numbers_are_rejected(numbers):
    ticket = RecommendedTicket(numbers=numbers, strong_number=7)
    with pytest.raises(ValueError):
        evaluate_ticket_prize(ticket, _draw(TICKET_NUMBERS))


@pytest.mark.parametrize("strong", [0, 8])
def test_invalid_strong_number_is_rejected(strong):
    ticket = RecommendedTicket(numbers=TICKET_NUMBERS, strong_number=strong)
    with pytest.raises(ValueError, match="strong number"):
        evaluate_ticket_prize(ticket, _draw(TICKET_NUMBERS))


def test_invalid_draw_main_numbers_are_rejected():
    ticket = RecommendedTicket(numbers=TICKET_NUMBERS, strong_number=7)
    with pytest.raises(ValueError, match="Draw"):
        evaluate_ticket_prize(ticket, _draw((1, 2, 3, 4, 5, 38)))


def test_empty_portfolio_reports_no_prize():
    result = evaluate_portfolio_prizes((), _draw(TICKET_NUMBERS))

    assert not result.any_prize
    assert result.winning_ticket_count == 0
    assert result.best_prize_tier is None
