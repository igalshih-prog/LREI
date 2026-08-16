import random

import pytest

from lrei.lottery.generator import GeneratorError, TicketGenerator
from lrei.lottery.predictor import NumberScore


def make_scores() -> tuple[NumberScore, ...]:
    return tuple(
        NumberScore(number=number, score=float(number))
        for number in range(1, 11)
    )


def test_generate_ticket_returns_six_numbers():
    generator = TicketGenerator()

    ticket = generator.generate_ticket(
        scores=make_scores(),
        rng=random.Random(42),
    )

    assert len(ticket) == 6
    assert len(set(ticket)) == 6
    assert all(1 <= number <= 37 for number in ticket)


def test_generate_ticket_is_sorted():
    generator = TicketGenerator()

    ticket = generator.generate_ticket(
        scores=make_scores(),
        rng=random.Random(42),
    )

    assert ticket == tuple(sorted(ticket))


def test_generate_ticket_is_reproducible_with_same_rng_seed():
    generator = TicketGenerator()

    first = generator.generate_ticket(
        scores=make_scores(),
        rng=random.Random(12345),
    )

    second = generator.generate_ticket(
        scores=make_scores(),
        rng=random.Random(12345),
    )

    assert first == second


def test_generate_tickets_is_reproducible_with_seed():
    generator = TicketGenerator()

    first = generator.generate_tickets(
        scores=make_scores(),
        count=5,
        seed=12345,
    )

    second = generator.generate_tickets(
        scores=make_scores(),
        count=5,
        seed=12345,
    )

    assert first == second


def test_generate_tickets_returns_requested_count():
    generator = TicketGenerator()

    tickets = generator.generate_tickets(
        scores=make_scores(),
        count=10,
        seed=42,
    )

    assert len(tickets) == 10

    for ticket in tickets:
        assert len(ticket) == 6
        assert len(set(ticket)) == 6
        assert ticket == tuple(sorted(ticket))


def test_generate_ticket_rejects_insufficient_candidates():
    generator = TicketGenerator()

    scores = (
        NumberScore(number=1, score=1.0),
        NumberScore(number=2, score=1.0),
        NumberScore(number=3, score=1.0),
    )

    with pytest.raises(GeneratorError):
        generator.generate_ticket(
            scores=scores,
            rng=random.Random(1),
        )


def test_generate_ticket_rejects_negative_score():
    generator = TicketGenerator()

    scores = (
        NumberScore(number=1, score=-1.0),
        NumberScore(number=2, score=1.0),
        NumberScore(number=3, score=1.0),
        NumberScore(number=4, score=1.0),
        NumberScore(number=5, score=1.0),
        NumberScore(number=6, score=1.0),
    )

    with pytest.raises(GeneratorError):
        generator.generate_ticket(
            scores=scores,
            rng=random.Random(1),
        )


def test_generate_ticket_rejects_number_outside_range():
    generator = TicketGenerator()

    scores = (
        NumberScore(number=0, score=1.0),
        NumberScore(number=2, score=1.0),
        NumberScore(number=3, score=1.0),
        NumberScore(number=4, score=1.0),
        NumberScore(number=5, score=1.0),
        NumberScore(number=6, score=1.0),
    )

    with pytest.raises(GeneratorError):
        generator.generate_ticket(
            scores=scores,
            rng=random.Random(1),
        )


def test_generate_ticket_rejects_duplicate_candidates():
    generator = TicketGenerator()

    scores = (
        NumberScore(number=1, score=1.0),
        NumberScore(number=1, score=1.0),
        NumberScore(number=2, score=1.0),
        NumberScore(number=3, score=1.0),
        NumberScore(number=4, score=1.0),
        NumberScore(number=5, score=1.0),
        NumberScore(number=6, score=1.0),
    )

    with pytest.raises(GeneratorError):
        generator.generate_ticket(
            scores=scores,
            rng=random.Random(1),
        )


def test_generate_tickets_rejects_non_positive_count():
    generator = TicketGenerator()

    with pytest.raises(ValueError):
        generator.generate_tickets(
            scores=make_scores(),
            count=0,
            seed=1,
        )
