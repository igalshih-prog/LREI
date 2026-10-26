"""P3-A research-only inference from the two EXACT-three-main prize tiers.

An inverse-probability estimate of an *entry count* is not operator-reported
sales, and a single draw does not support honest error bars without evidence
about dependence/correlation among other players' chosen ticket combinations.
No current/forecast lottery results, simulated payouts, taxes or monetary EV.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

from .prize_data import validate_prize_observation
from .prize_tier_odds import TOTAL_MAIN_OUTCOMES, main_match_outcomes

# This p is independent of both the ticket's six chosen main numbers and the
# strength-number chosen by the ticket holder, for a truly uniform fair draw.
EXACT_THREE_MAIN_PROBABILITY = Fraction(
    main_match_outcomes(3), TOTAL_MAIN_OUTCOMES
)


def three_main_entry_volume_proxy(observation: Any) -> dict[str, Any]:
    """Compute descriptive inverse-probability entry-count proxies.

    If N *fixed* ticket entries of any popularity/choice distribution are
    submitted independently of the upcoming fair draw, each entry's chance of
    matching exactly 3 out of 6 drawn main numbers is p3. Linearity of
    expectation means E[C_3 | submitted entries] = N*p3, even when players
    duplicate combinations and strong numbers are chosen nonuniformly.

    The realised C_3 from ONE draw is NOT N; its variability depends on
    unknown ticket overlaps and selection. Do not equate this with operator
    sales, ticket holders, tax receipts, or proven economic value.
    """
    row = validate_prize_observation(observation)
    result: dict[str, Any] = {}
    for game in ("regular", "double"):
        by_tier = {tier["tier"]: tier for tier in row["games"][game]}
        with_strong = by_tier["3+strong"]["winning_entries"]
        without_strong = by_tier["3"]["winning_entries"]
        count = with_strong + without_strong
        implied = Fraction(count, 1) / EXACT_THREE_MAIN_PROBABILITY
        result[game] = {
            "observed_exactly_three_main_winning_entries": count,
            "observed_3_plus_strong": with_strong,
            "observed_3_without_strong": without_strong,
            "inverse_probability_entry_count_proxy_rounded": round(implied),
        }
    return {
        "schema_version": 1,
        "draw_id": row["draw_id"],
        "draw_date": row["draw_date"],
        "source_status": row["source_status"],
        "status": "P3_A_EXPLORATORY_INVERSE_PROBABILITY_PROXY_ONLY",
        "fair_draw_probability_exactly_three_main_numerator":
            EXACT_THREE_MAIN_PROBABILITY.numerator,
        "fair_draw_probability_exactly_three_main_denominator":
            EXACT_THREE_MAIN_PROBABILITY.denominator,
        "games": result,
        "depends_on_uniform_player_number_selection": False,
        "requires_fair_draw_independent_of_submitted_entries": True,
        "valid_draw_specific_confidence_interval_available": False,
        "actual_operator_ticket_sales_verified": False,
        "operator_source_provenance_verified": False,
        "usable_as_co_winner_popularity_prediction": False,
        "eligible_for_monetary_expected_value": False,
        "decision": "NO PLAY",
    }
