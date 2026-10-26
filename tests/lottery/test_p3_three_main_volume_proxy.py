"""P3-A math and original *informational* site-display fixtures only."""
from copy import deepcopy
from fractions import Fraction
from math import comb
import json
from pathlib import Path

import pytest

from lrei.lottery.prize_data import PrizeDataError
from lrei.lottery.prize_tier_odds import TOTAL_MAIN_OUTCOMES, main_match_outcomes
from lrei.lottery.p3_three_main_volume_proxy import (
    EXACT_THREE_MAIN_PROBABILITY,
    three_main_entry_volume_proxy,
)

ROOT = Path(__file__).resolve().parents[2]


def observation(identifier=3954):
    return json.loads(
        (ROOT / "data" / "prize_observations" / f"{identifier}.json").read_text(
            encoding="utf-8"
        )
    )


def test_exact_probability_is_main_only_without_any_strong_assumptions():
    assert EXACT_THREE_MAIN_PROBABILITY == Fraction(22475, 581196)
    assert EXACT_THREE_MAIN_PROBABILITY == Fraction(
        comb(6, 3) * comb(31, 3), comb(37, 6)
    )
    assert main_match_outcomes(3) == comb(6, 3) * comb(31, 3)
    assert TOTAL_MAIN_OUTCOMES == comb(37, 6)


@pytest.mark.parametrize("identifier", range(3949, 3955))
def test_existing_nonbinding_operator_display_observations_remain_no_play(identifier):
    obs = observation(identifier)
    report = three_main_entry_volume_proxy(obs)
    assert report["draw_id"] == identifier
    assert report["decision"] == "NO PLAY"
    assert report["actual_operator_ticket_sales_verified"] is False
    assert report["operator_source_provenance_verified"] is False
    assert report["eligible_for_monetary_expected_value"] is False
    assert report["usable_as_co_winner_popularity_prediction"] is False
    assert report["valid_draw_specific_confidence_interval_available"] is False
    for game in ("regular", "double"):
        expected = sum(
            tier["winning_entries"]
            for tier in obs["games"][game]
            if tier["tier"] in {"3+strong", "3"}
        )
        entry = report["games"][game]
        assert entry["observed_exactly_three_main_winning_entries"] == expected
        assert entry["inverse_probability_entry_count_proxy_rounded"] == round(
            Fraction(expected) / EXACT_THREE_MAIN_PROBABILITY
        )
        assert obs["ticket_sales_ils"] is None  # not silently filled


def test_3954_real_fixture_values_and_strong_popularity_independence():
    observed = observation()
    report = three_main_entry_volume_proxy(observed)
    assert report["games"]["regular"] == {
        "observed_exactly_three_main_winning_entries": 72679,
        "observed_3_plus_strong": 10249,
        "observed_3_without_strong": 62430,
        "inverse_probability_entry_count_proxy_rounded": 1879455,
    }
    assert report["games"]["double"]["inverse_probability_entry_count_proxy_rounded"] == 1197742
    # Altering the observed strong/no-strong split without changing their sum
    # leaves the volume proxy unchanged. This does not certify any preference.
    changed = deepcopy(observed)
    changed["games"]["regular"][6]["winning_entries"] += 500
    changed["games"]["regular"][7]["winning_entries"] -= 500
    alt = three_main_entry_volume_proxy(changed)
    assert alt["games"]["regular"]["inverse_probability_entry_count_proxy_rounded"] == 1879455
    assert alt["games"]["regular"]["observed_3_plus_strong"] != 10249


@pytest.mark.parametrize("bad", [None, "fake", [], {}, True])
def test_invalid_or_unauthenticated_shape_never_yields_volume(bad):
    with pytest.raises(PrizeDataError):
        three_main_entry_volume_proxy(bad)


def test_missing_tier_or_invalid_counts_fail_closed():
    bad = observation()
    bad["games"]["regular"][6]["winning_entries"] = -1
    with pytest.raises(PrizeDataError):
        three_main_entry_volume_proxy(bad)
    bad = observation()
    bad["games"]["double"].pop()
    with pytest.raises(PrizeDataError):
        three_main_entry_volume_proxy(bad)


def test_no_deceptive_single_draw_confidence_interval():
    # If all N participants copy ONE exact line, the realised exact-three
    # count is either 0 or N. Its unbiased inverse estimate is highly noisy.
    n = 1000
    p = EXACT_THREE_MAIN_PROBABILITY
    assert (1 - p) * 0 + p * Fraction(n, 1) / p == n
    assert (1 - p) > Fraction(19, 20)  # >95% zero in this extreme case
