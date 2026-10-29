"""Leave-one-DRAW-out descriptive sensitivity; six reviewed operator displays.

This is NOT cross-validation, prospective evaluation, or a valid frequentist
randomization test: the hypothesis was chosen after viewing these outcomes.
Draws differ in jackpot and prize rules; entries are not independent people.
RESEARCH ONLY / NO PLAY.
"""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path
from typing import Any

from .conditional_strong_audit import audit_reviewed_strong_observations
from .reviewed_strong_draw_profile import summarize_reviewed_strong_draws

_PRODUCTS = ("regular", "double")
_MATCH_CLASSES = (3, 4, 5)
_COMPARISON_STRONG_NUMBERS = (6, 7)


def _descriptive_contrast(
    draws: list[dict[str, Any]],
    product: str,
    k: int,
    excluded_draws: set[int],
) -> dict[str, Any]:
    """Equal-weight per-draw difference: strong 4 minus strong 6/7."""
    four: list[float] = []
    others: list[float] = []
    for draw in draws:
        if draw["draw_id"] in excluded_draws:
            continue
        strong = draw["drawn_strong_number"]
        cell = draw["by_product_and_main_matches"][product][str(k)]
        fraction = cell["observed_strong_fraction"]
        if fraction is None:
            continue
        if strong == 4:
            four.append(fraction)
        elif strong in _COMPARISON_STRONG_NUMBERS:
            others.append(fraction)
    delta = (
        100 * (sum(four) / len(four) - sum(others) / len(others))
        if four and others
        else None
    )
    return {
        "strong_4_supporting_draws": len(four),
        "strong_6_or_7_supporting_draws": len(others),
        "unweighted_draw_mean_difference_percentage_points": delta,
        "is_causal_effect": False,
        "is_statistically_significant_claim": False,
    }


def audit_draw_omission_sensitivity(directory: Path) -> dict[str, Any]:
    """Test whether post-hoc contrast moves when one draw is left out.

    Both source-gated readers MUST accept the same six reviewed draw files.
    The grouping/contrast remains retrospective, never a holdout prediction.
    """
    audited = audit_reviewed_strong_observations(directory)
    context_report = summarize_reviewed_strong_draws(directory)
    draws = audited["draws"]
    prize_context = context_report["advertised_prize_context_by_draw"]
    if (
        len(draws) != 6
        or set(prize_context) != {str(row["draw_id"]) for row in draws}
        or context_report.get("authorized_for_play") is not False
        or context_report.get("source_provenance_verified") is not False
    ):
        raise ValueError("reviewed source context unavailable")

    special = {
        int(draw_id)
        for draw_id, context in prize_context.items()
        if context["special_prize_rule_notice_present"]
    }
    first_prizes = {
        int(draw_id): context["advertised_regular_first_ils"]
        for draw_id, context in prize_context.items()
    }
    # Entirely descriptive choice after inspecting the observations.
    min_first = min(first_prizes.values())
    lowest = {draw_id for draw_id, value in first_prizes.items() if value == min_first}
    scenarios = {
        "no_exclusions": set(),
        "exclude_special_prize_rule_draws": special,
        "exclude_lowest_advertised_prize_draws": lowest,
        "exclude_both_contextual_extremes": special | lowest,
    }

    products: dict[str, dict[str, Any]] = {}
    ids = [row["draw_id"] for row in draws]
    for product in _PRODUCTS:
        by_k: dict[str, Any] = {}
        for k in _MATCH_CLASSES:
            scenario_results = {
                name: _descriptive_contrast(draws, product, k, excluded)
                for name, excluded in scenarios.items()
            }
            omissions = [
                {
                    "excluded_draw_id": draw_id,
                    **_descriptive_contrast(draws, product, k, {draw_id}),
                }
                for draw_id in ids
            ]
            deltas = [
                cell["unweighted_draw_mean_difference_percentage_points"]
                for cell in omissions
            ]
            finite_deltas = [
                delta for delta in deltas
                if delta is not None and isfinite(delta)
            ]
            baseline = scenario_results["no_exclusions"]
            by_k[str(k)] = {
                "context_exclusion_scenarios": scenario_results,
                "leave_one_draw_out": omissions,
                "leave_one_draw_out_delta_min_pp": (
                    min(finite_deltas) if finite_deltas else None
                ),
                "leave_one_draw_out_delta_max_pp": (
                    max(finite_deltas) if finite_deltas else None
                ),
                "leave_one_draw_out_all_positive": (
                    len(finite_deltas) == len(ids)
                    and all(delta > 0 for delta in finite_deltas)
                ),
                "baseline_delta_pp": baseline[
                    "unweighted_draw_mean_difference_percentage_points"
                ],
                "hypothesis_selected_after_seeing_data": True,
                "no_inferential_stability_claim": True,
            }
        products[product] = by_k

    return {
        "schema_version": 1,
        "status": "six_draw_omission_and_jackpot_sensitivity_DESCRIPTIVE_ONLY",
        "reviewed_draw_ids": ids,
        "operator_display_only": True,
        "special_prize_rule_excluded_draw_ids": sorted(special),
        "lowest_advertised_prize_excluded_draw_ids": sorted(lowest),
        "advertised_regular_first_prize_min_ils": min_first,
        "product_and_main_match_count": products,
        "source_provenance_verified": False,
        "manual_entry_share_verified": False,
        "player_popularity_verified": False,
        "chronological_holdout_validated": False,
        "statistical_significance_claim": None,
        "p_values_reported": False,
        "draws_independent_proven": False,
        "ticket_entries_independent_proven": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Six-draw omission sensitivity; research only, NO PLAY"
    )
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_draw_omission_sensitivity(args.directory), indent=2))


if __name__ == "__main__":
    main()
