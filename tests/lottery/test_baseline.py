import pytest

from lrei.lottery.baseline import RandomBaseline


def test_random_baseline_generates_valid_ticket():
    baseline = RandomBaseline()

    tickets = baseline.generate_tickets(
        count=10,
        seed=42,
    )

    assert len(tickets) == 10

    for ticket in tickets:
        assert len(ticket) == 6
        assert len(set(ticket)) == 6
        assert ticket == tuple(sorted(ticket))
        assert all(1 <= number <= 37 for number in ticket)


def test_random_baseline_is_reproducible():
    baseline = RandomBaseline()

    first = baseline.generate_tickets(
        count=10,
        seed=123,
    )

    second = baseline.generate_tickets(
        count=10,
        seed=123,
    )

    assert first == second


def test_random_baseline_different_seeds_can_differ():
    baseline = RandomBaseline()

    first = baseline.generate_tickets(
        count=10,
        seed=123,
    )

    second = baseline.generate_tickets(
        count=10,
        seed=456,
    )

    assert first != second


def test_random_baseline_rejects_invalid_count():
    baseline = RandomBaseline()

    with pytest.raises(ValueError):
        baseline.generate_tickets(count=0)


def test_random_baseline_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        RandomBaseline(main_number_count=0)

    with pytest.raises(ValueError):
        RandomBaseline(min_number=0)

    with pytest.raises(ValueError):
        RandomBaseline(min_number=38, max_number=37)

    with pytest.raises(ValueError):
        RandomBaseline(
            main_number_count=38,
            min_number=1,
            max_number=37,
        )


def test_random_baseline_supports_custom_range():
    baseline = RandomBaseline(
        main_number_count=3,
        min_number=1,
        max_number=10,
    )

    tickets = baseline.generate_tickets(
        count=5,
        seed=42,
    )

    for ticket in tickets:
        assert len(ticket) == 3
        assert all(1 <= number <= 10 for number in ticket)
