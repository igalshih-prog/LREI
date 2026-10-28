"""Read-only per-tier uniform-null diagnostics; not verified ticket volume."""

from __future__ import annotations

from typing import Any

from .uniform_tier_reference import (
    uniform_reference_entry_ratio,
    uniform_tier_probability,
)

_TIERS = {
    "6+strong": (6, True),
    "6": (6, False),
    "5+strong": (5, True),
    "5": (5, False),
    "4+strong": (4, True),
    "4": (4, False),
    "3+strong": (3, True),
    "3": (3, False),
}
_EXPECTED_SOURCE = "operator_site_display_only_not_binding"


def inspect_uniform_reference_tiers(observation: dict[str, Any]) -> dict[str, Any]:
    """Compare winner counts with uniform-reference expectations per product.

    Never combine products or collapse tiers into an alleged sales estimate.
    Reject unreviewed source status and incomplete or malformed observations.
    """
    if observation.get("source_status") != _EXPECTED_SOURCE:
        raise ValueError("unreviewed source status")
    draw_id = observation.get("draw_id")
    if type(draw_id) is not int or draw_id <= 0:
        raise ValueError("invalid draw_id")
    games = observation.get("games")
    if not isinstance(games, dict) or set(games) != {"regular", "double"}:
        raise ValueError("regular and double game data required")
    diagnostics: dict[str, dict[str, float]] = {}
    for product in ("regular", "double"):
        rows = games[product]
        if not isinstance(rows, list) or len(rows) != len(_TIERS):
            raise ValueError("all eight prize tiers required")
        counts: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("malformed prize row")
            tier = row.get("tier")
            winners = row.get("winning_entries")
            if tier not in _TIERS or tier in counts:
                raise ValueError("unknown or duplicate tier")
            if type(winners) is not int or winners < 0:
                raise ValueError("invalid winning_entries")
            counts[tier] = winners
        if set(counts) != set(_TIERS):
            raise ValueError("missing prize tier")
        diagnostics[product] = {
            tier: uniform_reference_entry_ratio(
                counts[tier], uniform_tier_probability(*_TIERS[tier])
            )
            for tier in _TIERS
        }
    return {
        "schema_version": 1,
        "draw_id": draw_id,
        "status": "uniform_null_reference_only",
        "uniform_reference_ratios_by_product": diagnostics,
        "total_entries_verified": False,
        "player_popularity_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }
