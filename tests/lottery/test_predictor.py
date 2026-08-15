import pytest

from lrei.lottery.predictor import LotteryPredictor, NumberScore


def test_score_numbers_returns_scores():
    predictor = LotteryPredictor()

    scores = predictor.score_numbers(
        frequencies={
            1: 10,
            2: 5,
            3: 2,
        }
    )

    assert len(scores) == 3
    assert scores[0].number == 1
    assert scores[0].score == pytest.approx(1.0)


def test_score_numbers_is_deterministic():
    predictor = LotteryPredictor(
        frequency_weight=0.7,
        recency_weight=0.3,
    )

    frequencies = {
        1: 10,
        2: 5,
        3: 2,
    }

    recency_scores = {
        1: 0.5,
        2: 1.0,
        3: 0.2,
    }

    first = predictor.score_numbers(
        frequencies=frequencies,
        recency_scores=recency_scores,
    )

    second = predictor.score_numbers(
        frequencies=frequencies,
        recency_scores=recency_scores,
    )

    assert first == second


def test_rank_numbers_orders_by_score():
    predictor = LotteryPredictor()

    ranked = predictor.rank_numbers(
        frequencies={
            1: 2,
            2: 10,
            3: 5,
        }
    )

    assert [item.number for item in ranked] == [2, 3, 1]


def test_rank_numbers_uses_number_as_tiebreaker():
    predictor = LotteryPredictor()

    ranked = predictor.rank_numbers(
        frequencies={
            5: 10,
            2: 10,
            8: 5,
        }
    )

    assert [item.number for item in ranked] == [2, 5, 8]


def test_negative_frequency_is_rejected():
    predictor = LotteryPredictor()

    with pytest.raises(ValueError):
        predictor.score_numbers(
            frequencies={
                1: -1,
            }
        )


def test_empty_frequencies_return_empty_result():
    predictor = LotteryPredictor()

    scores = predictor.score_numbers({})

    assert scores == ()


def test_zero_weights_are_rejected():
    with pytest.raises(ValueError):
        LotteryPredictor(
            frequency_weight=0,
            recency_weight=0,
        )


def test_negative_weights_are_rejected():
    with pytest.raises(ValueError):
        LotteryPredictor(
            frequency_weight=-1,
            recency_weight=1,
        )


def test_number_score_is_immutable():
    score = NumberScore(
        number=7,
        score=0.5,
    )

    with pytest.raises(AttributeError):
        score.score = 1.0
