import pytest

from lrei.lottery.optimizer import (
    LotteryOptimizer,
    OptimizerConfig,
    OptimizerError,
)


def test_overlap_counts_shared_numbers():
    optimizer = LotteryOptimizer()

    first = (1, 2, 3, 4, 5, 6)
    second = (4, 5, 6, 7, 8, 9)

    assert optimizer.overlap(first, second) == 3


def test_jaccard_similarity():
    optimizer = LotteryOptimizer()

    first = (1, 2, 3, 4, 5, 6)
    second = (4, 5, 6, 7, 8, 9)

    similarity = optimizer.jaccard_similarity(first, second)

    assert similarity == pytest.approx(3 / 9)


def test_identical_tickets_have_jaccard_similarity_one():
    optimizer = LotteryOptimizer()

    ticket = (1, 2, 3, 4, 5, 6)

    assert optimizer.jaccard_similarity(ticket, ticket) == pytest.approx(1.0)


def test_empty_tickets_have_jaccard_similarity_one():
    optimizer = LotteryOptimizer()

    assert optimizer.jaccard_similarity((), ()) == pytest.approx(1.0)


def test_is_compatible_accepts_low_overlap():
    optimizer = LotteryOptimizer(
        OptimizerConfig(max_overlap=4)
    )

    candidate = (1, 2, 3, 4, 5, 6)
    selected = (
        (1, 2, 3, 4, 7, 8),
    )

    assert optimizer.is_compatible(candidate, selected)


def test_is_compatible_rejects_high_overlap():
    optimizer = LotteryOptimizer(
        OptimizerConfig(max_overlap=4)
    )

    candidate = (1, 2, 3, 4, 5, 6)
    selected = (
        (1, 2, 3, 4, 5, 7),
    )

    assert not optimizer.is_compatible(candidate, selected)


def test_optimize_removes_duplicate_tickets():
    optimizer = LotteryOptimizer()

    tickets = [
        (1, 2, 3, 4, 5, 6),
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
    ]

    result = optimizer.optimize(tickets)

    assert result == (
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
    )


def test_optimize_enforces_max_overlap():
    optimizer = LotteryOptimizer(
        OptimizerConfig(max_overlap=4)
    )

    tickets = [
        (1, 2, 3, 4, 5, 6),
        (1, 2, 3, 4, 5, 7),
        (8, 9, 10, 11, 12, 13),
    ]

    result = optimizer.optimize(tickets)

    assert result == (
        (1, 2, 3, 4, 5, 6),
        (8, 9, 10, 11, 12, 13),
    )


def test_optimize_respects_max_tickets():
    optimizer = LotteryOptimizer(
        OptimizerConfig(max_overlap=0, max_tickets=2)
    )

    tickets = [
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
        (13, 14, 15, 16, 17, 18),
    ]

    result = optimizer.optimize(tickets)

    assert len(result) == 2


def test_optimize_sorts_tickets():
    optimizer = LotteryOptimizer()

    tickets = [
        (6, 5, 4, 3, 2, 1),
    ]

    result = optimizer.optimize(tickets)

    assert result == (
        (1, 2, 3, 4, 5, 6),
    )


def test_optimize_rejects_empty_ticket():
    optimizer = LotteryOptimizer()

    with pytest.raises(OptimizerError):
        optimizer.optimize(
            [
                (),
            ]
        )


def test_optimize_rejects_duplicate_numbers_inside_ticket():
    optimizer = LotteryOptimizer()

    with pytest.raises(OptimizerError):
        optimizer.optimize(
            [
                (1, 2, 2, 3, 4, 5),
            ]
        )


def test_optimizer_config_rejects_negative_overlap():
    with pytest.raises(ValueError):
        OptimizerConfig(max_overlap=-1)


def test_optimizer_config_rejects_non_positive_max_tickets():
    with pytest.raises(ValueError):
        OptimizerConfig(max_tickets=0)
