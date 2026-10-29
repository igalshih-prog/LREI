"""Conditional strong-match audit of published prize tiers (RESEARCH ONLY).

For a fair, independent 1-of-7 strong selection, the strong-match fraction
among entries matching exactly k main numbers is 1/7, for each k. The ratio
does not require a ticket-sales denominator, but entry-level independence,
uniform machine picks, manual choice mix, and source provenance are not
verified. No inferential p-values or financial recommendations are produced.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from math import isfinite
from pathlib import Path
from typing import Any

from .reviewed_tier_diagnostics import REVIEWED_DRAWS
from .tier_ratio_diagnostics import inspect_uniform_reference_tiers

UNIFORM_STRONG_MATCH_FRACTION = 1 / 7
_AUDIT_TIERS = (3, 4, 5, 6)
_PRODUCTS = ("regular", "double")


def _validate_outcome(observation: dict[str, Any]) -> None:
    """Require a well-formed draw; upstream validates provenance/prize tiers."""
    strong = observation.get("strong_number")
    if type(strong) is not int or strong not in range(1, 8):
        raise ValueError("strong_number must be an integer 1..7")
    numbers = observation.get("main_numbers")
    if (
        not isinstance(numbers, list)
        or len(numbers) != 6
        or any(type(n) is not int or not 1 <= n <= 37 for n in numbers)
        or len(set(numbers)) != 6
    ):
        raise ValueError("six distinct main numbers in 1..37 required")
    raw_date = observation.get("draw_date")
    if not isinstance(raw_date, str):
        raise ValueError("draw_date must be ISO 8601")
    try:
        parsed = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ValueError("invalid draw_date") from exc
    if parsed.isoformat() != raw_date:
        raise ValueError("draw_date must be YYYY-MM-DD")


def conditional_strong_audit(observation: dict[str, Any]) -> dict[str, Any]:
    """Describe observed strong shares separately per draw, product and k.

    The published prize counts are winning *entries*, not unique players.
    This observational diagnostic cannot isolate manual vs machine selections.
    """
    inspect_uniform_reference_tiers(observation)
    _validate_outcome(observation)
    games = observation["games"]
    by_product: dict[str, dict[str, dict[str, Any]]] = {}
    for product in _PRODUCTS:
        counts = {row["tier"]: row["winning_entries"] for row in games[product]}
        per_k: dict[str, dict[str, Any]] = {}
        for k in _AUDIT_TIERS:
            strong_count = counts[f"{k}+strong"]
            nonstrong_count = counts[str(k)]
            denominator = strong_count + nonstrong_count
            fraction = strong_count / denominator if denominator else None
            per_k[str(k)] = {
                "strong_winning_entries": strong_count,
                "without_strong_winning_entries": nonstrong_count,
                "observed_entries_in_match_class": denominator,
                "observed_strong_fraction": fraction,
                "difference_from_uniform_percentage_points": (
                    100 * (fraction - UNIFORM_STRONG_MATCH_FRACTION)
                    if fraction is not None
                    else None
                ),
            }
        by_product[product] = per_k
    return {
        "schema_version": 1,
        "draw_id": observation["draw_id"],
        "draw_date": observation["draw_date"],
        "drawn_strong_number": observation["strong_number"],
        "status": "conditional_strong_observational_diagnostic_only",
        "uniform_independent_strong_baseline": UNIFORM_STRONG_MATCH_FRACTION,
        "by_product_and_main_matches": by_product,
        "source_status": observation["source_status"],
        "source_provenance_verified": False,
        "manual_entry_share_verified": False,
        "manual_number_distribution_verified": False,
        "total_entries_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }


def implied_manual_strong_rate(
    observed_fraction: float, assumed_manual_share_among_k_matches: float
) -> float | None:
    """An explicitly *hypothetical*, not fitted, two-component mixture.

    Observed = (1 - f_k)/7 + f_k * q_k where f_k is manual fraction
    *among entries matching k main numbers*, NOT manual fraction overall.
    Return None for incompatible hypothetical assumptions; without an
    external f_k the manual q_k is NOT identified from observed fractions.
    """
    p = observed_fraction
    f = assumed_manual_share_among_k_matches
    if (
        type(p) not in (int, float)
        or not isfinite(p)
        or not 0 <= p <= 1
        or type(f) not in (int, float)
        or not isfinite(f)
        or not 0 < f <= 1
    ):
        raise ValueError("finite observed fraction in [0,1] and f_k in (0,1] required")
    q = (p - (1 - f) * UNIFORM_STRONG_MATCH_FRACTION) / f
    if q < -1e-12 or q > 1 + 1e-12:
        return None
    return min(1.0, max(0.0, q))


def audit_reviewed_strong_observations(directory: Path) -> dict[str, Any]:
    """Read exactly six reviewed 2026 observations; reject missing/mismatched."""
    observations = []
    for draw_id in REVIEWED_DRAWS:
        raw = json.loads((directory / f"{draw_id}.json").read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("draw_id") != draw_id:
            raise ValueError(f"draw identity mismatch: {draw_id}")
        observations.append(conditional_strong_audit(raw))
    return {
        "schema_version": 1,
        "status": "six_reviewed_draws_exploratory_only",
        "reviewed_draw_ids": list(REVIEWED_DRAWS),
        "draws": observations,
        "source_provenance_verified": False,
        "manual_entry_share_verified": False,
        "manual_number_distribution_verified": False,
        "total_entries_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
        "statistical_significance_claim": None,
        "independent_validation": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research-only conditional strong-match audit; NO PLAY"
    )
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_reviewed_strong_observations(args.directory), indent=2))


if __name__ == "__main__":
    main()
