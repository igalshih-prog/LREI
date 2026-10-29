"""Descriptive spread of uniform-null reference ratios; NOT a sales estimate."""

from __future__ import annotations

from math import isfinite
from typing import Any


def describe_reference_spread(report: dict[str, Any]) -> dict[str, Any]:
    """Report min/max disagreement across eight prize tiers, by product.

    A large spread can indicate the uniform null is inadequate for this
    realized draw; it cannot identify why. No pooled or fitted entry count.
    """
    if report.get("status") != "uniform_null_reference_only":
        raise ValueError("requires a uniform-null diagnostic report")
    products = report.get("uniform_reference_ratios_by_product")
    if not isinstance(products, dict) or set(products) != {"regular", "double"}:
        raise ValueError("both products required")
    expected = {
        "6+strong", "6", "5+strong", "5",
        "4+strong", "4", "3+strong", "3",
    }
    spread: dict[str, dict[str, float]] = {}
    for name in ("regular", "double"):
        tiers = products[name]
        if not isinstance(tiers, dict) or set(tiers) != expected:
            raise ValueError("eight complete tiers required")
        values = list(tiers.values())
        if any(
            type(value) not in (int, float)
            or not isfinite(value)
            or value < 0
            for value in values
        ):
            raise ValueError("nonfinite or invalid ratio")
        spread[name] = {
            "minimum_uniform_reference_ratio": float(min(values)),
            "maximum_uniform_reference_ratio": float(max(values)),
            "range_uniform_reference_ratio": float(max(values) - min(values)),
        }
    return {
        "status": "descriptive_uniform_null_spread_only",
        "draw_id": report.get("draw_id"),
        "spread_by_product": spread,
        "total_entries_verified": False,
        "player_popularity_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }
