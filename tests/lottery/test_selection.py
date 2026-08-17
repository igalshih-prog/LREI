import pytest

from lrei.lottery.selection import (
    SelectionError,
    SelectionResult,
    TicketSelector,
)


def test_select_returns_selection_result():
    selector = TicketSelector()

    tickets = [
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
    ]

    result = selector.select(tickets)

    assert isinstance(result, SelectionResult)
    assert result.tickets == (
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
    )


def test_select_removes_duplicate_tickets():
    selector = TicketSelector()

    tickets = [
        (1, 2, 3, 4, 5, 6),
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
    ]

    result = selector.select(tickets)

    assert result.tickets == (
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
    )


def test_select_enforces_ticket_diversity():
    selector = TicketSelector()

    tickets = [
        (1, 2, 3, 4, 5, 6),
        (1, 2, 3, 4, 5, 7),
        (8, 9, 10, 11, 12, 13),
    ]

    result = selector.select(tickets)

    assert result.tickets == (
        (1, 2, 3, 4, 5, 6),
        (8, 9, 10, 11, 12, 13),
    )


def test_select_sorts_ticket_numbers():
    selector = TicketSelector()

    tickets = [
        (6, 5, 4, 3, 2, 1),
    ]

    result = selector.select(tickets)

    assert result.tickets == (
        (1, 2, 3, 4, 5, 6),
    )


def test_select_rejects_empty_input():
    selector = TicketSelector()

    with pytest.raises(SelectionError):
        selector.select([])


def test_select_rejects_when_no_tickets_remain():
    selector = TicketSelector()

    with pytest.raises(SelectionError):
        selector.select(
            [
                (),
            ]
        )


def test_select_returns_tuple_of_tickets():
    selector = TicketSelector()

    result = selector.select(
        [
            (1, 2, 3, 4, 5, 6),
            (7, 8, 9, 10, 11, 12),
        ]
    )

    assert isinstance(result.tickets, tuple)
    assert all(isinstance(ticket, tuple) for ticket in result.tickets)
