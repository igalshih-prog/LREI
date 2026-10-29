"""Pre-registered-in-repository future candidate SCREENING, never validation.

No future first-party or binding-protocol records are available yet.
This function does not load the old lottery CSV or turn an uploaded CSV
into verified player-choice data. Caller-supplied source labels are NOT
cryptographic source proof. RESEARCH ONLY / NO PLAY.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from .reviewed_tier_diagnostics import REVIEWED_DRAWS

_PROTOCOL = "p3-strong-choice-forward-screen-v1"
_TIERS = {
    "6+strong", "6", "5+strong", "5",
    "4+strong", "4", "3+strong", "3",
}
_PRODUCTS = {"regular", "double"}


def _required_protocol(protocol: dict[str, Any]) -> tuple[int, date, int]:
    """Reject silent relaxation of the committed research design."""
    if not isinstance(protocol, dict):
        raise ValueError("protocol object required")
    gate = protocol.get("forward_entry_gate")
    endpoint = protocol.get("primary_descriptive_endpoint")
    old = protocol.get("historical_analysis")
    claims = protocol.get("claims_authorized")
    if (
        protocol.get("schema_version") != 1
        or protocol.get("protocol_id") != _PROTOCOL
        or protocol.get("protocol_date_israel") != "2026-10-29"
        or protocol.get("status")
        != "protocol_frozen_for_future_screening_NOT_REGISTERED_INDEPENDENTLY"
        or not isinstance(gate, dict)
        or not isinstance(endpoint, dict)
        or not isinstance(old, dict)
        or not isinstance(claims, dict)
        or old.get("exploratory_reviewed_draw_ids") != list(REVIEWED_DRAWS)
        or old.get("secondary_reported_draw_already_public_before_freeze") != 3979
        or old.get("hypothesis_selected_with_knowledge_of_2026_exploratory_results")
        is not True
        or gate.get("minimum_draw_id") != 3980
        or gate.get("minimum_draw_date_israel") != "2026-10-30"
        or gate.get("human_independent_source_review_required") is not True
        or gate.get("raw_first_party_source_sha256_required") is not True
        or gate.get("official_binding_protocol_review_required") is not True
        or gate.get("source_validation_implemented_by_this_protocol") is not False
        or endpoint.get("product") != "regular"
        or endpoint.get("main_matches_exactly") != 3
        or endpoint.get("drawn_strong_comparison") != [4, 1]
        or endpoint.get("group_minimum_unique_draws") != 20
        or endpoint.get("direction") != "strong_4_greater_than_strong_1"
        or endpoint.get("statistic")
        != "difference_of_unweighted_per_draw_strong_match_fraction_means"
        or endpoint.get("include_all_eligible_valid_draws") is not True
        or endpoint.get("missing_prize_tiers_not_imputed") is not True
        or endpoint.get("uniform_independent_reference_strong_fraction") != 1 / 7
        or any(claims.get(key) is not False for key in (
            "statistical_significance",
            "player_popularity_verified",
            "source_provenance_verified",
            "expected_value_verified",
            "authorized_for_play",
        ))
    ):
        raise ValueError("committed source and hypothesis gates must not change")
    return 3980, date.fromisoformat("2026-10-30"), 20


def _screen_draw(raw: dict[str, Any], min_id: int, min_date: date) -> int:
    if not isinstance(raw, dict):
        raise ValueError("draw candidate must be a JSON object")
    draw_id = raw.get("draw_id")
    if type(draw_id) is not int or draw_id < min_id:
        raise ValueError("candidate predates the sealed prospective lower bound")
    raw_date = raw.get("draw_date")
    if type(raw_date) is not str:
        raise ValueError("draw_date must be a full ISO local date")
    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ValueError("invalid prospective draw date") from exc
    if parsed_date.isoformat() != raw_date or parsed_date < min_date:
        raise ValueError("candidate draw date predates prospective lower bound")

    strong = raw.get("strong_number")
    main = raw.get("main_numbers")
    if type(strong) is not int or not 1 <= strong <= 7:
        raise ValueError("invalid drawn strong number")
    if (
        not isinstance(main, list)
        or len(main) != 6
        or any(type(number) is not int or not 1 <= number <= 37 for number in main)
        or len(set(main)) != 6
    ):
        raise ValueError("invalid main-number draw outcome")

    # Only a website DISPLAY record can pass this preliminary structural
    # screen. It CANNOT self-certify by changing its source_status string.
    if raw.get("source_status") != "operator_site_display_only_not_binding":
        raise ValueError("cannot claim provenance using a source-status label")
    source = raw.get("source_url")
    if not isinstance(source, str):
        raise ValueError("official-looking source URL is required but not proof")
    url = urlsplit(source)
    if (
        url.scheme != "https"
        or url.hostname not in {"www.pais.co.il", "pais.co.il"}
        or url.username is not None
        or url.password is not None
        or url.port not in (None, 443)
    ):
        raise ValueError("source must reference an official HTTPS host")

    games = raw.get("games")
    if not isinstance(games, dict) or set(games) != _PRODUCTS:
        raise ValueError("complete regular and Double tier tables required")
    for game in _PRODUCTS:
        rows = games[game]
        if not isinstance(rows, list) or len(rows) != 8:
            raise ValueError("exactly eight complete tiers per game required")
        tiers: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("bad tier row")
            tier = row.get("tier")
            winners = row.get("winning_entries")
            if (
                not isinstance(tier, str)
                or tier not in _TIERS
                or tier in tiers
                or type(winners) is not int
                or winners < 0
            ):
                raise ValueError("invalid or duplicated winning tier")
            tiers.add(tier)
        if tiers != _TIERS:
            raise ValueError("missing winning tier")
    return strong


def screen_future_draws(
    records: Sequence[dict[str, Any]], protocol: dict[str, Any]
) -> dict[str, Any]:
    """Screen chronology/shape ONLY; never infer current player choices.

    Even a full count does NOT imply source approval or research readiness.
    """
    min_id, min_date, required_per_group = _required_protocol(protocol)
    if not isinstance(records, (list, tuple)):
        raise ValueError("future records must be an ordered sequence")
    seen: set[int] = set()
    counts = {str(i): 0 for i in range(1, 8)}
    last_id = min_id - 1
    last_date: str | None = None
    for record in records:
        strong = _screen_draw(record, min_id, min_date)
        draw_id = record["draw_id"]
        if draw_id in seen or draw_id <= last_id:
            raise ValueError("duplicate or out-of-order prospective draw ID")
        if last_date is not None and record["draw_date"] <= last_date:
            raise ValueError("duplicate or out-of-order prospective draw date")
        seen.add(draw_id)
        last_id = draw_id
        last_date = record["draw_date"]
        counts[str(strong)] += 1
    return {
        "schema_version": 1,
        "protocol_id": _PROTOCOL,
        "status": "candidate_structure_screened_SOURCE_REVIEW_REQUIRED",
        "candidate_draw_count": len(records),
        "observed_drawn_strong_counts": counts,
        "minimum_support_per_primary_group": required_per_group,
        "primary_group_counts_screened_only": {
            "4": counts["4"], "1": counts["1"]
        },
        "primary_sample_size_gate_passed_on_screened_only": (
            counts["4"] >= required_per_group
            and counts["1"] >= required_per_group
        ),
        "source_review_completed": False,
        "raw_first_party_source_verified": False,
        "binding_protocol_verified": False,
        "independently_registered_before_draws": False,
        "outcome_based_hypothesis_fit_performed": False,
        "prospective_holdout_validated": False,
        "statistical_significance_claim": None,
        "player_popularity_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }


def screen_future_json_file(path: Path, protocol_file: Path) -> dict[str, Any]:
    """Read-only interface: candidate JSON array and committed protocol."""
    records = json.loads(path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))
    return screen_future_draws(records, protocol)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="NO PLAY: future structure screen")
    parser.add_argument("--candidate-json", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(
        screen_future_json_file(args.candidate_json, args.protocol), indent=2
    ))


if __name__ == "__main__":
    main()
