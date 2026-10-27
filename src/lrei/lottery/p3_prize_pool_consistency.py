"""Read-only P3-A prize-tier pool consistency check; NO PLAY.

Five approximate operator allocation rates cannot certify ticket sales, chosen
player combinations, source provenance or monetary expected value.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from .prize_data import (
    PrizeDataError, canonical_sha256, load_observation,
    validate_prize_observation,
)

# Strict allowlist, never generalize the 2026 draw-specific regimes to
# unreviewed rows. Details and operator notice URLs in accompanying docs.
REVIEWED_REGIMES = {
    3949: "normal", 3950: "normal", 3951: "normal",
    3952: "normal", 3953: "bonus_150pct", 3954: "normal",
}
NORMAL_NOTICE = "https://www.pais.co.il/news/news.aspx?newsId=3052"
BONUS_NOTICE = "https://www.pais.co.il/news/news.aspx?newsId=3133"
RATES = {
    "normal": (
        Fraction(18, 1000), Fraction(16, 1000), Fraction(214, 10000),
        Fraction(43, 1000), Fraction(7, 100),
    ),
    "bonus_150pct": (
        Fraction(27, 1000), Fraction(24, 1000), Fraction(321, 10000),
        Fraction(645, 10000), Fraction(105, 1000),
    ),
}
EIGHTH_TIER_PAYOUTS = {"normal": (10, 20), "bonus_150pct": (15, 30)}
# Fail closed if the research repository's original six fixtures are absent.
# We do not trust caller-provided data merely because its draw ID is known.
OBSERVATION_ROOT = Path(__file__).resolve().parents[3] / "data" / "prize_observations"


def prize_pool_consistency(observation: Any) -> dict[str, Any]:
    """Return five descriptive implied-receipt indicators, not official sales.

    These indicators share the *same* payout source and thus cannot constitute
    independent sales measurements or justify a draw-level confidence interval.
    """
    row = validate_prize_observation(observation)
    draw = row["draw_id"]
    regime = REVIEWED_REGIMES.get(draw)
    if regime is None:
        raise PrizeDataError("no independently reviewed percentage regime for draw")

    note = row["special_rules_note"]
    if regime == "bonus_150pct":
        if not isinstance(note, str) or BONUS_NOTICE not in note:
            raise PrizeDataError("bonus draw requires its published source notice")
    elif note is not None:
        raise PrizeDataError("cannot assume baseline rates for special-rule draw")

    regular = row["games"]["regular"]
    double = row["games"]["double"]
    eighth = (
        regular[7]["payout_per_winning_entry_ils"],
        double[7]["payout_per_winning_entry_ils"],
    )
    if eighth != EIGHTH_TIER_PAYOUTS[regime]:
        raise PrizeDataError("tier-eight payments contradict reviewed regime")

    # Enforce the documented six-fixture scope, not merely their draw IDs.
    # Schema-valid but altered payout/count data must not produce indicators.
    # This establishes local fixture equality only, NOT official provenance.
    original = load_observation(OBSERVATION_ROOT / f"{draw}.json")
    if canonical_sha256(row) != canonical_sha256(original):
        raise PrizeDataError("prize observation differs from reviewed repository fixture")

    indicators: list[dict[str, Any]] = []
    for idx, rate in zip(range(2, 7), RATES[regime]):
        paid = 0
        for tier_list in (regular, double):
            count = tier_list[idx]["winning_entries"]
            payout = tier_list[idx]["payout_per_winning_entry_ils"]
            if payout is None and count == 0:
                payout = 0
            if payout is None:
                raise PrizeDataError("published tier payment missing")
            paid += count * payout
        if paid <= 0:
            raise PrizeDataError("zero-paid tier cannot supply receipts indicator")
        indicators.append({
            "tier_number": idx + 1,
            "reported_payout_total_ils": paid,
            "announced_approx_percentage": float(rate * 100),
            "implied_receipts_indicator_ils": round(Fraction(paid, 1) / rate),
        })

    values = sorted(v["implied_receipts_indicator_ils"] for v in indicators)
    median = values[2]
    return {
        "schema_version": 1,
        "status": "P3_A_DESCRIPTIVE_ACCOUNTING_ONLY",
        "draw_id": draw,
        "draw_date": row["draw_date"],
        "source_status": row["source_status"],
        "reviewed_rule_regime": regime,
        "published_rule_notice_url": (
            BONUS_NOTICE if regime == "bonus_150pct" else NORMAL_NOTICE
        ),
        "tier_indicators": indicators,
        "median_indicator_ils": median,
        "minimum_indicator_ils": values[0],
        "maximum_indicator_ils": values[-1],
        "indicator_range_percent_of_median": round(
            100 * (values[-1] - values[0]) / median, 2
        ),
        "indicator_is_operator_verified_sales": False,
        "indicators_are_independent_observations": False,
        "confidence_interval_valid": False,
        "operator_source_provenance_verified": False,
        "usable_for_player_combination_popularity": False,
        "eligible_for_monetary_expected_value": False,
        "dataset_promotion_approved": False,
        "decision": "NO PLAY",
    }
