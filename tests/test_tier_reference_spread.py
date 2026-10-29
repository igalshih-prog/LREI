"""Check that tier spread remains descriptive, isolated and fail-closed."""

from copy import deepcopy

import pytest

from lrei.lottery.tier_reference_spread import describe_reference_spread

TIERS = ["6+strong", "6", "5+strong", "5", "4+strong", "4", "3+strong", "3"]


def report() -> dict:
    return {
        "status": "uniform_null_reference_only",
        "draw_id": 3949,
        "uniform_reference_ratios_by_product": {
            "regular": dict(zip(TIERS, range(8))),
            "double": dict(zip(TIERS, range(10, 18))),
        },
    }


def test_spread_by_product_is_descriptive_only() -> None:
    data = report()
    original = deepcopy(data)
    result = describe_reference_spread(data)
    assert data == original
    assert result["spread_by_product"]["regular"]["range_uniform_reference_ratio"] == 7
    assert result["spread_by_product"]["double"]["minimum_uniform_reference_ratio"] == 10
    assert result["authorized_for_play"] is False
    assert result["total_entries_verified"] is False
    assert result["player_popularity_verified"] is False
    assert result["expected_value_verified"] is False


@pytest.mark.parametrize("mutation", ["status", "missing", "nan", "negative", "bool"])
def test_rejects_incomplete_or_invalid_input(mutation: str) -> None:
    data = report()
    if mutation == "status":
        data["status"] = "verified"
    elif mutation == "missing":
        del data["uniform_reference_ratios_by_product"]["double"]
    elif mutation == "nan":
        data["uniform_reference_ratios_by_product"]["regular"]["3"] = float("nan")
    elif mutation == "negative":
        data["uniform_reference_ratios_by_product"]["regular"]["3"] = -1
    else:
        data["uniform_reference_ratios_by_product"]["regular"]["3"] = True
    with pytest.raises(ValueError):
        describe_reference_spread(data)
