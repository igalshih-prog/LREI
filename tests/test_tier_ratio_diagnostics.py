"""Research-only tier ratio diagnostics: enforce missing-data and provenance gates."""

from copy import deepcopy

import pytest

from lrei.lottery.tier_ratio_diagnostics import inspect_uniform_reference_tiers

TIERS = ["6+strong", "6", "5+strong", "5", "4+strong", "4", "3+strong", "3"]


def observation() -> dict:
    return {
        "draw_id": 3949,
        "source_status": "operator_site_display_only_not_binding",
        "games": {
            name: [
                {"tier": tier, "winning_entries": index * 3}
                for index, tier in enumerate(TIERS)
            ]
            for name in ("regular", "double")
        },
    }


def test_read_only_and_never_claims_verified_sales() -> None:
    data = observation()
    before = deepcopy(data)
    result = inspect_uniform_reference_tiers(data)
    assert data == before
    assert result["status"] == "uniform_null_reference_only"
    assert result["uniform_reference_ratios_by_product"]["regular"]["6+strong"] == 0
    for key in (
        "total_entries_verified",
        "player_popularity_verified",
        "expected_value_verified",
        "authorized_for_play",
    ):
        assert result[key] is False


@pytest.mark.parametrize("mutation", ["source", "missing", "duplicate", "negative", "bool", "product"])
def test_bad_or_incomplete_observations_rejected(mutation: str) -> None:
    data = observation()
    if mutation == "source":
        data["source_status"] = "verified"
    elif mutation == "missing":
        data["games"]["regular"].pop()
    elif mutation == "duplicate":
        data["games"]["regular"][0]["tier"] = "3"
    elif mutation == "negative":
        data["games"]["regular"][0]["winning_entries"] = -1
    elif mutation == "bool":
        data["games"]["regular"][0]["winning_entries"] = True
    else:
        data["games"].pop("double")
    with pytest.raises(ValueError):
        inspect_uniform_reference_tiers(data)


def test_regular_and_double_are_not_pooled() -> None:
    data = observation()
    data["games"]["double"][-1]["winning_entries"] = 900
    result = inspect_uniform_reference_tiers(data)
    ratios = result["uniform_reference_ratios_by_product"]
    assert ratios["regular"]["3"] != ratios["double"]["3"]
