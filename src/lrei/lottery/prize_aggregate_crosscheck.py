"""Cross-check secondary aggregate lottery sums without imputing any prize rows.

A cross-source total agreement/disagreement cannot certify a primary
operator payout table. The two source sites are non-authoritative research
leads; preserve missing sixteen tier rows and never calculate ticket EV.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .dataset import LotteryDataset, parse_draw_date
from .prize_data import PrizeDataError
from .prize_research_checks import SECONDARY_SOURCE, validate_secondary_leads

CROSSCHECK_PURPOSE = "secondary_only_crosscheck_of_aggregate_figures_never_eight_tier_prize_observations"
LOTTO_ONLY_SOURCE = "https://lottohistory.co.il/"
CROSSCHECK_HEADER = {
    "schema_version", "purpose", "source_url", "source_status",
    "retrieved_date_utc", "raw_source_archived", "raw_source_sha256",
    "reported_lotto_only_total_for_draws", "all_game_total_source",
    "all_game_source_status", "eight_tier_tables_available",
    "authoritative_protocol_verified",
}
DRAW_FIELDS = {"draw_id", "draw_date", "reported_lotto_only_ils"}


def _read_json(path: Path | str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrizeDataError("invalid or missing secondary aggregate source file") from exc


def compare_unverified_aggregate_sources(
    crosscheck: Any,
    leads: Any,
    history: LotteryDataset,
) -> dict[str, Any]:
    """Require sound labels, exact continuity and consistent independent draws.

    A positive residual is an unexplained difference between THIRD-PARTY
    presentations, not proof of Extra, taxes, game sales or real earnings.
    """
    if not isinstance(crosscheck, dict) or set(crosscheck) != CROSSCHECK_HEADER:
        raise PrizeDataError("invalid secondary Lotto-only aggregate crosscheck fields")
    if type(crosscheck["schema_version"]) is not int or crosscheck["schema_version"] != 1:
        raise PrizeDataError("wrong source crosscheck schema")
    if crosscheck["purpose"] != CROSSCHECK_PURPOSE:
        raise PrizeDataError("source crosscheck must be exclusively secondary research")
    if (
        crosscheck["source_url"] != LOTTO_ONLY_SOURCE
        or crosscheck["source_status"] != "third_party_archival_page_not_lottery_operator"
        or crosscheck["all_game_total_source"] != SECONDARY_SOURCE
        or crosscheck["all_game_source_status"] != "another_third_party_not_operator"
    ):
        raise PrizeDataError("source must be explicitly labeled as a third party")
    if (
        crosscheck["raw_source_archived"] is not False
        or crosscheck["raw_source_sha256"] is not None
        or crosscheck["eight_tier_tables_available"] is not False
        or crosscheck["authoritative_protocol_verified"] is not False
    ):
        raise PrizeDataError("no archive, full prize table, or official protocol verified")
    try:
        retrieved = date.fromisoformat(crosscheck["retrieved_date_utc"])
    except (TypeError, ValueError) as exc:
        raise PrizeDataError("crosscheck review date must be a real ISO date") from exc
    if retrieved.isoformat() != crosscheck["retrieved_date_utc"]:
        raise PrizeDataError("noncanonical source review date")
    proof = validate_secondary_leads(leads, history)
    if proof["operator_verified_count"] != 0:
        raise PrizeDataError("source leads must remain unverified")
    recorded = crosscheck["reported_lotto_only_total_for_draws"]
    if not isinstance(recorded, list) or len(recorded) != 4:
        raise PrizeDataError("four distinct consecutive aggregate leads required")
    lookup = {d["draw_id"]: d for d in leads["draws"]}
    result: list[dict[str, Any]] = []
    for expected_id, obj in zip(range(3955, 3959), recorded):
        if not isinstance(obj, dict) or set(obj) != DRAW_FIELDS:
            raise PrizeDataError("invalid Lotto-only lead fields")
        if type(obj["draw_id"]) is not int or obj["draw_id"] != expected_id:
            raise PrizeDataError("aggregate leads must be consecutive 3955-3958")
        match = lookup[expected_id]
        if obj["draw_date"] != match["draw_date"]:
            raise PrizeDataError("aggregated source draw date disagrees with independent archive")
        payout = obj["reported_lotto_only_ils"]
        if type(payout) is not int or payout <= 0:
            raise PrizeDataError("unverified reported amount must be a positive integer")
        all_games = match["reported_all_prizes_ils"]
        if type(all_games) is not int or all_games <= 0:
            raise PrizeDataError("invalid unverified all-games amount")
        if payout > all_games:
            raise PrizeDataError("unexpected negative secondary-source accounting residual")
        result.append({
            "draw_id": expected_id,
            "secondary_lotto_only_total_ils": payout,
            "secondary_all_games_total_ils": all_games,
            "unexplained_source_total_difference_ils": all_games - payout,
            "regular_eight_tier_table": None,
            "double_eight_tier_table": None,
            "operator_verified": False,
        })
    return {
        "schema_version": 1,
        "status": "secondary_source_accounting_crosscheck_unverified",
        "compared_draws": len(result),
        "summary": result,
        "eligible_for_prize_observation": False,
        "eligible_for_expected_value": False,
        "source_bytes_retrieved": False,
        "source_authenticity_verified": False,
        "missing_eight_tier_tables_still": list(range(3955, 3969)),
        "must_not_label_residual_as_extra_tax_or_profit": True,
    }


def audit_secondary_aggregate_files(
    crosscheck: Path | str,
    secondary_leads: Path | str,
    history: LotteryDataset,
) -> dict[str, Any]:
    return compare_unverified_aggregate_sources(
        _read_json(crosscheck), _read_json(secondary_leads), history
    )
