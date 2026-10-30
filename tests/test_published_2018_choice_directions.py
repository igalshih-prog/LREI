"""Public 2018 published qualitative directions, not private LREI calibration."""

from __future__ import annotations

from math import isclose

import pytest

from lrei.lottery.hypothetical_choice_model import (
    hypothetical_manual_match_profile,
    hypothetical_player_mix_profile,
)
from lrei.lottery.published_2018_choice_directions import (
    HISTORICAL_STUDY_YEAR,
    PUBLICATION_DOI,
    published_direction_sensitivity,
)
from lrei.lottery.uniform_tier_reference import uniform_tier_probability

DRAW_MAIN = [4, 7, 13, 18, 29, 35]


def test_directional_2018_ranks_are_explicitly_hypothetical() -> None:
    profile = published_direction_sensitivity(1.0, 0.0)
    main = profile["main_weights"]
    strong = profile["strong_weights"]
    assert len(main) == 37 and len(strong) == 7
    assert main[6] > max(main[:6] + main[7:])
    assert main[36] < min(main[:36])
    assert sum(main[:7]) / 7 > sum(main[27:]) / 10
    assert strong[3] == strong[4] == max(strong)
    assert strong[0] == min(strong)
    assert profile["historical_study_year"] == HISTORICAL_STUDY_YEAR == 2018
    assert profile["historical_publication_doi"] == PUBLICATION_DOI
    assert profile["toy_weight_formula_is_not_publication_model"] is True
    assert profile["historical_private_ticket_rows_accessed"] is False
    assert profile["observed_2018_frequency_magnitudes_used"] is False
    assert profile["observed_2026_frequency_magnitudes_used"] is False
    assert profile["manual_entry_share_verified"] is False
    assert profile["player_popularity_verified"] is False
    assert profile["expected_value_verified"] is False
    assert profile["authorized_for_play"] is False


@pytest.mark.parametrize(
    "strength,dilution",
    [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (3.0, 1.0)],
)
def test_zero_effect_is_exact_uniform_reference(
    strength: float, dilution: float
) -> None:
    profile = published_direction_sensitivity(strength, dilution)
    assert profile["main_weights"] == [1.0] * 37
    assert profile["strong_weights"] == [1.0] * 7
    match_profile = hypothetical_manual_match_profile(
        profile["main_weights"], profile["strong_weights"], DRAW_MAIN, 4
    )
    for k in range(7):
        assert match_profile[str(k)]["strong"] == pytest.approx(
            uniform_tier_probability(k, True)
        )
        assert match_profile[str(k)]["without_strong"] == pytest.approx(
            uniform_tier_probability(k, False)
        )


def test_toy_manual_weights_and_mixture_produce_normalized_probabilities() -> None:
    scenario = published_direction_sensitivity(0.8, 0.25)
    profile = hypothetical_player_mix_profile(
        scenario["main_weights"],
        scenario["strong_weights"],
        DRAW_MAIN,
        4,
        0.5,  # explicitly arbitrary manual share, NOT paper's population share
    )
    assert sum(
        sum(categories.values())
        for categories in profile["tier_probability_profile"].values()
    ) == pytest.approx(1.0)
    assert profile["source_data_used_for_fitting"] is False
    assert profile["player_popularity_verified"] is False
    assert profile["authorized_for_play"] is False


def test_hypothetical_uniformization_shrinks_distortions_monotonically() -> None:
    full = published_direction_sensitivity(1.0, 0.0)
    middle = published_direction_sensitivity(1.0, 0.5)
    uniform = published_direction_sensitivity(1.0, 1.0)
    for key in ("main_weights", "strong_weights"):
        for a, b, c in zip(full[key], middle[key], uniform[key]):
            assert isclose(c, 1.0)
            assert abs(b - 1) <= abs(a - 1) + 1e-12
    assert full["strong_weights"][3] > middle["strong_weights"][3] > 1
    assert full["strong_weights"][0] < middle["strong_weights"][0] < 1


def test_arbitrary_weight_magnitude_not_derived_from_prize_or_2018_sales() -> None:
    # The same historical ranking is compatible with many distinct
    # scenario effects; therefore the published rank cannot identify
    # a numeric 2026 popularity probability or actual played-ticket volume.
    weak = published_direction_sensitivity(0.1, 0.0)
    strong = published_direction_sensitivity(2.0, 0.0)
    assert weak["main_weights"][6] != strong["main_weights"][6]
    assert weak["strong_weights"][3] != strong["strong_weights"][3]
    assert weak["source"] == strong["source"]
    assert weak["2026_player_preference_estimated"] is False
    assert strong["2026_player_preference_estimated"] is False


@pytest.mark.parametrize(
    "strength,dilution",
    [
        (-0.01, 0.3), (3.01, 0.2), (True, 0.5),
        (float("nan"), 0.5), (float("inf"), 0.5),
        (1.0, -0.01), (1.0, 1.01), (1.0, True),
        (1.0, float("nan")), (1.0, float("inf")),
    ],
)
def test_invalid_hypothetical_parameters_rejected(
    strength: float, dilution: float
) -> None:
    with pytest.raises(ValueError):
        published_direction_sensitivity(strength, dilution)
