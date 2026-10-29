"""Draw-level descriptive strong-match profile; research only / NO PLAY.

Summarize *draws*, not independent ticket-level pseudo-observations.
Exactly six source-gated operator-display observations (#3949..#3954).
No statistical significance, independent validation, 2026 preferences,
sales estimates, payout optimization or play authorization.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .conditional_strong_audit import audit_reviewed_strong_observations
from .reviewed_tier_diagnostics import REVIEWED_DRAWS

_PRODUCTS = ("regular", "double")
_MATCH_CLASSES = (3, 4, 5)
_STRONG_NUMBERS = tuple(range(1, 8))


def summarize_conditional_strong_draws(audit: dict[str, Any]) -> dict[str, Any]:
    """Compute unweighted per-draw strong fractions by drawn strong number.

    This is intentionally not a pooled W+/W_total estimator. Lotto entries
    within and across draws may be duplicated or dependent, and the six
    observations are not independently source-verified. A group of only
    two draws per observed strong number is not enough for inference.
    """
    if (
        audit.get("status") != "six_reviewed_draws_exploratory_only"
        or audit.get("reviewed_draw_ids") != list(REVIEWED_DRAWS)
        or audit.get("authorized_for_play") is not False
        or audit.get("source_provenance_verified") is not False
    ):
        raise ValueError("source-gated six-draw audit required")
    draws = audit.get("draws")
    if not isinstance(draws, list) or len(draws) != len(REVIEWED_DRAWS):
        raise ValueError("all six reviewed draw records required")

    # Reject repeated/misaligned dates or IDs rather than silently weighting
    # the same draw more than once in a descriptive group.
    seen_dates: set[str] = set()
    buckets: dict[tuple[str, int, int], list[float]] = defaultdict(list)
    draw_ids_by_strong: dict[int, list[int]] = {
        strong: [] for strong in _STRONG_NUMBERS
    }
    for expected_id, record in zip(REVIEWED_DRAWS, draws):
        if not isinstance(record, dict) or record.get("draw_id") != expected_id:
            raise ValueError("missing or duplicate reviewed draw ID")
        draw_date = record.get("draw_date")
        if not isinstance(draw_date, str) or draw_date in seen_dates:
            raise ValueError("missing or duplicate draw date")
        seen_dates.add(draw_date)
        strong = record.get("drawn_strong_number")
        if type(strong) is not int or strong not in _STRONG_NUMBERS:
            raise ValueError("invalid drawn strong number")
        if (
            record.get("status") != "conditional_strong_observational_diagnostic_only"
            or record.get("source_status")
            != "operator_site_display_only_not_binding"
            or record.get("authorized_for_play") is not False
        ):
            raise ValueError("unreviewed source or unauthorized diagnostic")
        by_product = record.get("by_product_and_main_matches")
        if not isinstance(by_product, dict) or set(by_product) != set(_PRODUCTS):
            raise ValueError("both lottery products required")
        draw_ids_by_strong[strong].append(expected_id)
        for product in _PRODUCTS:
            by_k = by_product[product]
            if not isinstance(by_k, dict):
                raise ValueError("missing main-match classes")
            for k in _MATCH_CLASSES:
                cell = by_k.get(str(k))
                if not isinstance(cell, dict):
                    raise ValueError("missing main-match class")
                yes = cell.get("strong_winning_entries")
                no = cell.get("without_strong_winning_entries")
                rate = cell.get("observed_strong_fraction")
                if (
                    type(yes) is not int
                    or type(no) is not int
                    or yes < 0
                    or no < 0
                ):
                    raise ValueError("invalid winning-entry counts")
                # Require exact count-derived fraction, not a detached figure.
                expected_rate = yes / (yes + no) if yes + no else None
                if rate != expected_rate:
                    raise ValueError("strong fraction disagrees with entry counts")
                if rate is not None:
                    buckets[(product, k, strong)].append(rate)

    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    contrasts: dict[str, dict[str, dict[str, Any]]] = {}
    for product in _PRODUCTS:
        grouped[product] = {}
        contrasts[product] = {}
        for k in _MATCH_CLASSES:
            per_strong: dict[str, dict[str, Any]] = {}
            for strong in _STRONG_NUMBERS:
                observed = buckets[(product, k, strong)]
                per_strong[str(strong)] = {
                    "draw_count_with_nonzero_match_class": len(observed),
                    "mean_of_draw_fractions": (
                        sum(observed) / len(observed) if observed else None
                    ),
                    "minimum_draw_fraction": min(observed) if observed else None,
                    "maximum_draw_fraction": max(observed) if observed else None,
                }
            grouped[product][str(k)] = per_strong

            # 4-vs-6/7 is a retrospective exploratory summary because
            # only these three numbers happened to be drawn in the six files.
            four = buckets[(product, k, 4)]
            comparison = buckets[(product, k, 6)] + buckets[(product, k, 7)]
            contrast = (
                sum(four) / len(four) - sum(comparison) / len(comparison)
                if four and comparison
                else None
            )
            contrasts[product][str(k)] = {
                "drawn_strong_4_draw_count": len(four),
                "drawn_strong_6_or_7_draw_count": len(comparison),
                "observed_4_minus_6_or_7_percentage_points": (
                    100 * contrast if contrast is not None else None
                ),
                "is_exploratory_and_not_a_hypothesis_test": True,
            }

    return {
        "schema_version": 1,
        "status": "six_draw_descriptive_strong_coverage_only",
        "reviewed_draw_ids": list(REVIEWED_DRAWS),
        "source_status": "operator_site_display_only_not_binding",
        "draw_ids_by_drawn_strong": {
            str(n): draw_ids_by_strong[n] for n in _STRONG_NUMBERS
        },
        "unobserved_drawn_strong_numbers": [
            n for n in _STRONG_NUMBERS if not draw_ids_by_strong[n]
        ],
        "per_draw_unweighted_means_by_product_k_and_strong": grouped,
        "exploratory_strong_4_vs_6_or_7_by_product_and_k": contrasts,
        "draw_level_sample_too_small_for_inference": True,
        "tier_5_is_sparse_and_descriptive_only": True,
        "ticket_entry_independence_assumed": False,
        "source_provenance_verified": False,
        "manual_entry_share_verified": False,
        "player_popularity_verified": False,
        "chronological_holdout_validated": False,
        "statistical_significance_claim": None,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }


def summarize_reviewed_strong_draws(directory: Path) -> dict[str, Any]:
    """Read source-gated reviewed files; never touch candidate lottery CSV."""
    return summarize_conditional_strong_draws(
        audit_reviewed_strong_observations(directory)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Six reviewed draws; descriptive strong-choice check only"
    )
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summarize_reviewed_strong_draws(args.directory), indent=2))


if __name__ == "__main__":
    main()
