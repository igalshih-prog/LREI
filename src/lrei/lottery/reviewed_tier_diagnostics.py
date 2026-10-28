"""Read-only report over six reviewed prize observations; research only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .tier_ratio_diagnostics import inspect_uniform_reference_tiers

REVIEWED_DRAWS = tuple(range(3949, 3955))


def inspect_reviewed_observations(directory: Path) -> dict[str, Any]:
    """Fail closed if any reviewed file is missing, mismatched or malformed."""
    reports = []
    for draw_id in REVIEWED_DRAWS:
        path = directory / f"{draw_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("draw_id") != draw_id:
            raise ValueError(f"draw identity mismatch: {draw_id}")
        reports.append(inspect_uniform_reference_tiers(data))
    return {
        "schema_version": 1,
        "status": "reviewed_observations_uniform_null_diagnostics_only",
        "reviewed_draw_ids": list(REVIEWED_DRAWS),
        "draw_reports": reports,
        "total_entries_verified": False,
        "player_popularity_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }
