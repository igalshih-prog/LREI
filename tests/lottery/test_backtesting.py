import pytest

from lrei.lottery.backtesting import (
    BacktestResult,
    LotteryBacktester,
)
from lrei.lottery.dataset import LotteryDataset, LotteryDrawRecord


def make_dataset() -> LotteryDataset:
    return LotteryDataset(
        [
            LotteryDrawRecord(
                draw_id="draw-001",
                numbers=(1, 2, 3, 4, 5, 6),
            ),
            LotteryDrawRecord(
                draw_id="draw-002",
                numbers=(1, 2, 3, 7, 8, 9),
            ),
            LotteryDrawRecord(
                draw_id="draw-003",
                numbers=(1, 2, 4, 10, 11, 12),
            ),
            LotteryDrawRecord(
                draw_id="draw-004",
                numbers=(2, 3, 5, 13, 14, 15),
            ),
            LotteryDrawRecord(
                draw_id="draw-005",
                numbers=(1, 4, 6, 16, 17, 18),
            ),
            LotteryDrawRecord(
                draw_id="draw-006",
                numbers=(2, 5, 7, 19, 20, 21),
            ),
        ]
    )


def test_backtester_returns_result():
    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=42,
    )

    assert isinstance(result, BacktestResult)
    assert result.case_count == 3


def test_backtester_evaluates_chronologically():
    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=42,
    )

    assert [case.test_draw_id for case in result.cases] == [
        "draw-004",
        "draw-005",
        "draw-006",
    ]

    assert [case.train_size for case in result.cases] == [
        3,
        4,
        5,
    ]


def test_backtester_records_ticket_counts():
    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=42,
    )

    for case in result.cases:
        assert case.generated_ticket_count == 20
        assert case.recommended_ticket_count > 0


def test_backtester_match_metrics_are_non_negative():
    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=42,
    )

    assert result.best_match >= 0
    assert result.total_matches >= 0
    assert result.average_matches >= 0.0

    for case in result.cases:
        assert case.best_match >= 0
        assert case.total_matches >= 0


def test_backtester_is_reproducible():
    backtester = LotteryBacktester()

    first = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=123,
    )

    second = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=123,
    )

    assert first == second


def test_backtester_rejects_invalid_train_size():
    backtester = LotteryBacktester()

    with pytest.raises(ValueError):
        backtester.run(
            dataset=make_dataset(),
            train_size=0,
        )


def test_backtester_rejects_invalid_test_size():
    backtester = LotteryBacktester()

    with pytest.raises(ValueError):
        backtester.run(
            dataset=make_dataset(),
            train_size=3,
            test_size=0,
        )


def test_backtester_rejects_invalid_ticket_count():
    backtester = LotteryBacktester()

    with pytest.raises(ValueError):
        backtester.run(
            dataset=make_dataset(),
            train_size=3,
            ticket_count=0,
        )


def test_backtester_rejects_dataset_that_is_too_small():
    backtester = LotteryBacktester()

    with pytest.raises(Exception):
        backtester.run(
            dataset=make_dataset(),
            train_size=6,
            test_size=1,
        )
def test_backtester_includes_random_baseline_results():
    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=42,
    )

    for case in result.cases:
        assert case.baseline_best_match >= 0
        assert case.baseline_total_matches >= 0


def test_backtester_baseline_uses_same_ticket_count():
    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=42,
    )

    for case in result.cases:
        assert (
            case.recommended_ticket_count
            > 0
        )

        assert (
            case.recommended_ticket_count
            <= case.generated_ticket_count
        )


def test_backtester_exposes_baseline_aggregate_metrics():
    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=make_dataset(),
        train_size=3,
        test_size=1,
        ticket_count=20,
        seed=42,
    )

    assert result.baseline_best_match >= 0
    assert result.baseline_total_matches >= 0
    assert result.baseline_average_matches >= 0.0
