"""Exact six-of-37 weighted-set toy model, no calibration or betting advice."""

from __future__ import annotations

import json
from math import isclose
from pathlib import Path

import pytest

from lrei.lottery.hypothetical_choice_model import (
    hypothetical_manual_match_profile,
    hypothetical_player_mix_profile,
)
from lrei.lottery.uniform_tier_reference import uniform_tier_probability

MAIN = [1.0] * 37
POWER = [1.0] * 7
DRAW = [4, 7, 13, 18, 29, 35]


def _sum_profile(profile: dict[str, dict[str, float]]) -> float:
    return sum(sum(values.values()) for values in profile.values())


def test_all_uniform_weights_recover_exact_hypergeometric_baseline() -> None:
    profile = hypothetical_manual_match_profile(MAIN, POWER, DRAW, 4)
    assert set(profile) == {str(k) for k in range(7)}
    for k in range(7):
        assert profile[str(k)]["strong"] == pytest.approx(
            uniform_tier_probability(k, True), abs=1e-14
        )
        assert profile[str(k)]["without_strong"] == pytest.approx(
            uniform_tier_probability(k, False), abs=1e-14
        )
    assert _sum_profile(profile) == pytest.approx(1.0)


def test_weighted_scenario_stays_normalized_not_prediction_of_balls() -> None:
    main = MAIN.copy()
    power = POWER.copy()
    main[6] = 1.7  # 7; arbitrary illustrative magnitude, NOT 2018 fit
    main[36] = 0.5  # 37
    power[3] = 1.6  # strong 4
    power[0] = 0.8  # strong 1
    profile = hypothetical_manual_match_profile(main, power, DRAW, 4)
    assert _sum_profile(profile) == pytest.approx(1)
    alternative_draw = [4, 13, 18, 29, 35, 37]
    other = hypothetical_manual_match_profile(main, power, alternative_draw, 4)
    assert profile["6"]["strong"] > other["6"]["strong"]
    assert all(0 <= value <= 1 for c in profile.values() for value in c.values())


def test_scaling_all_weights_does_not_change_the_law() -> None:
    main = MAIN.copy()
    power = POWER.copy()
    main[6] = 1.3
    power[3] = 1.4
    first = hypothetical_manual_match_profile(main, power, DRAW, 4)
    second = hypothetical_manual_match_profile(
        [2 * weight for weight in main],
        [5 * weight for weight in power],
        DRAW,
        4,
    )
    for k in first:
        for category in first[k]:
            assert first[k][category] == pytest.approx(second[k][category])


def test_mix_endpoints_and_convex_interpolation() -> None:
    main = MAIN.copy()
    main[6] = 1.5
    power = POWER.copy()
    power[3] = 1.8
    manual = hypothetical_manual_match_profile(main, power, DRAW, 4)
    null = hypothetical_player_mix_profile(main, power, DRAW, 4, 0.0)
    all_manual = hypothetical_player_mix_profile(main, power, DRAW, 4, 1.0)
    half = hypothetical_player_mix_profile(main, power, DRAW, 4, 0.5)
    for k in range(7):
        for strong, category in ((True, "strong"), (False, "without_strong")):
            uniform = uniform_tier_probability(k, strong)
            assert null["tier_probability_profile"][str(k)][category] == (
                pytest.approx(uniform)
            )
            assert all_manual["tier_probability_profile"][str(k)][category] == (
                pytest.approx(manual[str(k)][category])
            )
            assert half["tier_probability_profile"][str(k)][category] == (
                pytest.approx((uniform + manual[str(k)][category]) / 2)
            )
    assert half["authorized_for_play"] is False
    assert half["source_data_used_for_fitting"] is False
    assert half["expected_value_verified"] is False
    assert half["manual_entry_share_verified"] is False


def test_real_draw_is_only_a_fixed_conditioning_outcome() -> None:
    path = Path(__file__).resolve().parents[1] / "data/prize_observations/3951.json"
    draw = json.loads(path.read_text(encoding="utf-8"))
    result = hypothetical_player_mix_profile(
        MAIN, POWER, draw["main_numbers"], draw["strong_number"], 0.4
    )
    assert result["status"] == "hypothetical_player_behavior_sensitivity_only"
    assert result["authorized_for_play"] is False
    assert isclose(_sum_profile(result["tier_probability_profile"]), 1, abs_tol=1e-12)


@pytest.mark.parametrize(
    "bad",
    [float("nan"), float("inf"), 0.0, -1.0, True, 1e-8, 1e7],
)
def test_invalid_weights_rejected(bad: object) -> None:
    main = MAIN.copy()
    main[0] = bad  # type: ignore[assignment]
    with pytest.raises(ValueError):
        hypothetical_manual_match_profile(main, POWER, DRAW, 4)


def test_wrong_weight_vector_length_rejected() -> None:
    with pytest.raises(ValueError):
        hypothetical_manual_match_profile(MAIN[:-1], POWER, DRAW, 4)
    with pytest.raises(ValueError):
        hypothetical_manual_match_profile(MAIN, POWER[:-1], DRAW, 4)


@pytest.mark.parametrize("bad", [0, 8, True, 2.5])
def test_invalid_strong_outcome_rejected(bad: object) -> None:
    with pytest.raises(ValueError):
        hypothetical_manual_match_profile(
            MAIN, POWER, DRAW, bad  # type: ignore[arg-type]
        )


def test_duplicate_main_outcome_rejected() -> None:
    with pytest.raises(ValueError):
        hypothetical_manual_match_profile(MAIN, POWER, [4, 4, 13, 18, 29, 35], 4)


@pytest.mark.parametrize("fraction", [-0.1, 1.1, True, float("nan"), float("inf")])
def test_unjustified_mixture_values_rejected(fraction: float) -> None:
    with pytest.raises(ValueError):
        hypothetical_player_mix_profile(MAIN, POWER, DRAW, 4, fraction)
