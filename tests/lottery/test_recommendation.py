import pytest

from lrei.lottery.recommendation import (
    RecommendationEngine,
    RecommendationError,
)
from lrei.lottery.statistics import LotteryStatistics


def make_statistics() -> LotteryStatistics:
    return LotteryStatistics(
        frequencies={
            1: 10,
            2: 9,
            3: 8,
            4: 7,
            5: 6,
            6: 5,
            7: 4,
            8: 3,
            9: 2,
            10: 1,
        }
    )


def test_recommendation_engine_returns_result():
    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=make_statistics(),
        ticket_count=20,
        seed=42,
    )

    assert result.scores
    assert result.generated_tickets
    assert result.recommended_tickets


def test_recommendation_engine_generates_requested_number_of_candidates():
    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=make_statistics(),
        ticket_count=25,
        seed=42,
    )

    assert len(result.generated_tickets) == 25


def test_recommendation_engine_tickets_are_valid():
    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=make_statistics(),
        ticket_count=20,
        seed=42,
    )

    for ticket in result.recommended_tickets:
        assert len(ticket) == 6
        assert len(set(ticket)) == 6
        assert ticket == tuple(sorted(ticket))
        assert all(1 <= number <= 37 for number in ticket)


def test_recommendation_engine_is_reproducible():
    engine = RecommendationEngine()

    first = engine.recommend(
        statistics=make_statistics(),
        ticket_count=20,
        seed=12345,
    )

    second = engine.recommend(
        statistics=make_statistics(),
        ticket_count=20,
        seed=12345,
    )

    assert first.scores == second.scores
    assert first.generated_tickets == second.generated_tickets
    assert first.recommended_tickets == second.recommended_tickets


def test_recommendation_engine_rejects_non_positive_ticket_count():
    engine = RecommendationEngine()

    with pytest.raises(ValueError):
        engine.recommend(
            statistics=make_statistics(),
            ticket_count=0,
            seed=42,
        )


def test_recommendation_engine_returns_no_more_than_optimizer_limit():
    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=make_statistics(),
        ticket_count=100,
        seed=42,
    )

    assert len(result.recommended_tickets) <= 10
