"""Retrospective scenario-vs-observed strong fractions: RESEARCH ONLY / NO PLAY.

This combines the source-gated reviewed-draw audit with a completely
hypothetical player-choice mixture. No parameter calibration, sales
estimation, pooled significance tests, or held-out validation is performed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .conditional_strong_audit import conditional_strong_audit
from .hypothetical_choice_model import hypothetical_player_mix_profile
from .reviewed_tier_diagnostics import REVIEWED_DRAWS

_PRODUCTS = ("regular", "double")
_MAIN_MATCH_CLASSES = (3, 4, 5, 6)


def compare_hypothetical_strong_scenario(
    directory: Path,
    main_weights: Sequence[float],
    strong_weights: Sequence[float],
    assumed_manual_fraction_by_product: Mapping[str, float],
) -> dict[str, Any]:
    """Describe differences in conditional strong rates without fitting.

    The arbitrary weights are shared across products, but the assumed
    overall manual-entry share can differ for regular vs Double. For each
    product and main-match class the implied manual fraction *within the
    stratum* is computed implicitly by the normalized mixture model.
    Observed zero-denominator strata are represented as null.
    """
    if (
        not isinstance(assumed_manual_fraction_by_product, dict)
        or set(assumed_manual_fraction_by_product) != set(_PRODUCTS)
    ):
        raise ValueError("separate manual fractions required for both products")

    rows: list[dict[str, Any]] = []
    for draw_id in REVIEWED_DRAWS:
        raw = json.loads((directory / f"{draw_id}.json").read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("draw_id") != draw_id:
            raise ValueError(f"draw identity mismatch: {draw_id}")
        observed = conditional_strong_audit(raw)
        products: dict[str, dict[str, Any]] = {}
        for product in _PRODUCTS:
            assumed_share = assumed_manual_fraction_by_product[product]
            hypothetical = hypothetical_player_mix_profile(
                main_weights,
                strong_weights,
                raw["main_numbers"],
                raw["strong_number"],
                assumed_share,
            )
            model_cells = hypothetical["tier_probability_profile"]
            by_k: dict[str, dict[str, Any]] = {}
            for k in _MAIN_MATCH_CLASSES:
                prob_cells = model_cells[str(k)]
                probability = prob_cells["strong"] / (
                    prob_cells["strong"] + prob_cells["without_strong"]
                )
                actual = observed["by_product_and_main_matches"][product][str(k)]
                actual_share = actual["observed_strong_fraction"]
                by_k[str(k)] = {
                    "observed_strong_fraction": actual_share,
                    "assumed_model_strong_fraction": probability,
                    "observed_minus_model_percentage_points": (
                        100 * (actual_share - probability)
                        if actual_share is not None
                        else None
                    ),
                    "observed_entries_in_match_class": actual[
                        "observed_entries_in_match_class"
                    ],
                }
            products[product] = {
                "assumed_manual_fraction_all_entries": hypothetical[
                    "assumed_manual_fraction_all_entries"
                ],
                "by_main_match_count": by_k,
            }
        rows.append(
            {
                "draw_id": draw_id,
                "draw_date": observed["draw_date"],
                "drawn_strong_number": observed["drawn_strong_number"],
                "by_product": products,
            }
        )
    return {
        "schema_version": 1,
        "status": "retrospective_hypothetical_scenario_comparison_only",
        "reviewed_draw_ids": list(REVIEWED_DRAWS),
        "draws": rows,
        "assumed_weights_not_fitted": True,
        "source_data_used_for_model_fitting": False,
        "independently_verified_observations": False,
        "chronological_holdout_validated": False,
        "statistical_significance_claim": None,
        "manual_entry_share_verified": False,
        "manual_selection_distribution_verified": False,
        "player_popularity_verified": False,
        "total_entries_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }
