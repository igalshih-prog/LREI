"""Uniform-reference combinatorics: no ticket-sales or player-preference inference."""

from math import comb, isclose

import pytest

from lrei.lottery.uniform_tier_reference import (
    uniform_reference_entry_ratio,
    uniform_tier_probability,
)


def test_all_disjoint_match_classes_partition_probability() -> None:
    total = sum(
        uniform_tier_probability(k, strong)
        for k in range(7)
        for strong in (False, True)
    )
    assert isclose(total, 1.0, abs_tol=1e-14)


def test_jackpot_exact_probability() -> None:
    assert uniform_tier_probability(6, True) == pytest.approx(
        1 / (comb(37, 6) * 7)
    )


def test_strong_split_is_one_to_six() -> None:
    for k in range(7):
        assert uniform_tier_probability(k, False) == pytest.approx(
            6 * uniform_tier_probability(k, True)
        )


@pytest.mark.parametrize("bad", [-1, 7, 1.5, True, "3"])
def test_invalid_main_count_rejected(bad: object) -> None:
    with pytest.raises(ValueError):
        uniform_tier_probability(bad, True)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [0, 1, "true", None])
def test_invalid_strong_flag_rejected(bad: object) -> None:
    with pytest.raises(ValueError):
        uniform_tier_probability(3, bad)  # type: ignore[arg-type]


def test_reference_ratio_not_rounded_or_called_sales() -> None:
    assert uniform_reference_entry_ratio(4, 0.2) == pytest.approx(20)
    assert uniform_reference_entry_ratio(0, 0.2) == 0


@pytest.mark.parametrize("winners,prob", [(-1, 0.5), (True, 0.5), (2, 0), (2, 1.1)])
def test_invalid_reference_ratio_rejected(winners: object, prob: float) -> None:
    with pytest.raises(ValueError):
        uniform_reference_entry_ratio(winners, prob)  # type: ignore[arg-type]
