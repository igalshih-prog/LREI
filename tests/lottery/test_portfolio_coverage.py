from math import comb

import pytest

from lrei.lottery.portfolio_coverage import portfolio_coverage


TICKET = (1, 2, 3, 4, 5, 6)


def test_exact_single_ticket_coverage_counts_match_combinatorics():
    four_plus = portfolio_coverage([TICKET], threshold=4)
    five_plus = portfolio_coverage([TICKET], threshold=5)
    jackpot = portfolio_coverage([TICKET], threshold=6)

    assert four_plus["covered_draws"] == comb(6, 4) * comb(31, 2) + comb(6, 5) * comb(31, 1) + 1
    assert five_plus["covered_draws"] == comb(6, 5) * comb(31, 1) + 1
    assert jackpot["covered_draws"] == 1
    assert four_plus["total_draws"] == comb(37, 6)


def test_duplicate_ticket_does_not_inflate_portfolio_coverage():
    single = portfolio_coverage([TICKET], threshold=4)
    duplicate = portfolio_coverage([TICKET, TICKET], threshold=4)

    assert duplicate["ticket_count"] == 1
    assert duplicate["covered_draws"] == single["covered_draws"]
    assert duplicate["probability"] == single["probability"]


def test_distinct_ticket_can_only_expand_or_preserve_coverage():
    single = portfolio_coverage([TICKET], threshold=4)
    pair = portfolio_coverage([TICKET, (7, 8, 9, 10, 11, 12)], threshold=4)

    assert pair["ticket_count"] == 2
    assert pair["covered_draws"] >= single["covered_draws"]
    assert pair["probability"] >= single["probability"]


@pytest.mark.parametrize("threshold", [0, 7])
def test_invalid_match_threshold_is_rejected(threshold):
    with pytest.raises(ValueError):
        portfolio_coverage([TICKET], threshold=threshold)


@pytest.mark.parametrize("ticket", [(1, 2, 3, 4, 5), (1, 2, 3, 4, 5, 5), (1, 2, 3, 4, 5, 38)])
def test_invalid_ticket_is_rejected(ticket):
    with pytest.raises(ValueError):
        portfolio_coverage([ticket], threshold=4)
