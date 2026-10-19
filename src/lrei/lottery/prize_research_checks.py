"""P3-A.2 research-only source evidence: official rule notices, secondary leads.

These checks separate 1) a directly retrieved Mifal HaPais public rule
announcement, 2) manually or index-reviewed operator draw prize tables,
and 3) THIRD-PARTY historical summaries without prize-tier counts.

Secondary leads MUST NOT be added to prize_observations or used to compute
EV, winning ticket sales, taxation or co-winner popularity.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .dataset import LotteryDataset, parse_draw_date
from .prize_data import PrizeDataError, validate_prize_observation

SECONDARY_SOURCE = "https://www.paisresults.co.il/index.php"
RULE_SOURCE = "https://www.pais.co.il/news/news.aspx?newsId=3133"
LEADS_PURPOSE = "secondary_research_leads_only_never_verified_prize_observations"
LEADS_STATUS = "unverified_secondary_summary_no_tier_payouts"


def _load_json(path: Path | str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrizeDataError("missing or invalid source evidence JSON") from exc


def _date_iso(value: Any) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise PrizeDataError("date must be YYYY-MM-DD")
    try:
        d = date.fromisoformat(value)
    except ValueError as exc:
        raise PrizeDataError("invalid calendar date") from exc
    if d.isoformat() != value:
        raise PrizeDataError("date must use canonical YYYY-MM-DD")
    return d


def _positive_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise PrizeDataError(f"{label} must be a nonnegative integer")
    return value


def validate_secondary_leads(
    record: Any, history: LotteryDataset
) -> dict[str, Any]:
    """Confirm that public index leads match our independently stored draws.

    No part of this is evidence that the monetary fields are operator-
    authenticated; a matching six-number draw is NOT source verification.
    """
    header = {
        "schema_version", "purpose", "status", "source_url", "source_type",
        "source_checked_date_utc", "raw_source_archived", "raw_source_sha256",
        "coverage_window", "draws",
    }
    if not isinstance(record, dict) or set(record) != header:
        raise PrizeDataError("invalid secondary source-leads header")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise PrizeDataError("unexpected research-leads schema")
    if record["purpose"] != LEADS_PURPOSE or record["status"] != LEADS_STATUS:
        raise PrizeDataError("secondary data must remain clearly unverified")
    if record["source_url"] != SECONDARY_SOURCE or record["source_type"] != "independent_third_party_not_the_lottery_operator":
        raise PrizeDataError("not a documented independent secondary source")
    if record["raw_source_archived"] is not False or record["raw_source_sha256"] is not None:
        raise PrizeDataError("cannot claim unarchived raw source checksums")
    reviewed = _date_iso(record["source_checked_date_utc"])
    if record["coverage_window"] != [3955, 3968]:
        raise PrizeDataError("secondary source-lead window changed unexpectedly")
    draws = record["draws"]
    if not isinstance(draws, list) or len(draws) != 14:
        raise PrizeDataError("must account for all fourteen missing draws")
    needed = {
        "draw_id", "draw_date", "main_numbers", "strong_number",
        "reported_regular_first_prize_ils", "reported_all_prizes_ils",
        "regular_eight_tier_table", "double_eight_tier_table",
        "operator_source_verified", "approved_protocol_verified",
        "ticket_sales_ils", "tax_paid_ils",
    }
    count = 0
    for expected, row in zip(range(3955, 3969), draws):
        if not isinstance(row, dict) or set(row) != needed:
            raise PrizeDataError("secondary draw fields missing or unexpected")
        if type(row["draw_id"]) is not int or row["draw_id"] != expected:
            raise PrizeDataError("secondary leads must have each consecutive draw ID once")
        recorded_date = _date_iso(row["draw_date"])
        if recorded_date > reviewed:
            raise PrizeDataError("review date cannot precede draw")
        found = [d for d in history if d.draw_id == str(expected)]
        if len(found) != 1:
            raise PrizeDataError("missing or duplicated draw in historical results")
        archive = found[0]
        # JSON booleans and floats may compare equal to Python integers
        # (True == 1, 1.0 == 1). Never let malformed secondary-source
        # numbers pass by equality, or crash on a non-iterable/null value.
        main = row["main_numbers"]
        if (
            not isinstance(main, list)
            or len(main) != 6
            or any(type(number) is not int or not 1 <= number <= 37 for number in main)
            or len(set(main)) != 6
            or main != sorted(main)
        ):
            raise PrizeDataError("secondary main_numbers must be six sorted distinct integers in 1..37")
        if (
            tuple(main) != tuple(sorted(archive.numbers))
            or type(row["strong_number"]) is not int
            or row["strong_number"] != archive.strong_number
            or recorded_date != parse_draw_date(archive.date)
        ):
            raise PrizeDataError("secondary lead disagrees with archived draw outcome")
        for key in ("reported_regular_first_prize_ils", "reported_all_prizes_ils"):
            if _positive_integer(row[key], key) == 0:
                raise PrizeDataError(f"{key}: source-reported monetary amount must be positive")
        for key in ("regular_eight_tier_table", "double_eight_tier_table", "ticket_sales_ils", "tax_paid_ils"):
            if row[key] is not None:
                raise PrizeDataError(f"{key}: no verified value; MUST remain null")
        if row["operator_source_verified"] is not False or row["approved_protocol_verified"] is not False:
            raise PrizeDataError("secondary source MUST NOT claim official verification")
        count += 1
    return {
        "secondary_lead_count": count,
        "missing_operator_prize_tier_draw_ids": list(range(3955, 3969)),
        "operator_verified_count": 0,
        "source_raw_bytes_available": False,
        "eligible_for_prize_economics": False,
        "secondary_monetary_values_are_unverified": True,
    }


def validate_special_rule_notice(
    record: Any, observation: Any
) -> dict[str, Any]:
    """Validate sourced public 3953 allocation notice, NOT implied ticket sales."""
    mandatory = {
        "schema_version", "draw_id", "notice_date", "draw_date",
        "source_url", "authority", "source_review_method",
        "original_html_archived", "original_html_sha256", "notice_context",
        "first_prize_regular_ils", "first_prize_double_advertised_ils",
        "second_prize_regular_ils", "second_prize_double_advertised_ils",
        "approx_percent_of_total_draw_receipts_by_tier",
        "eighth_prize_ils", "receipts_amount_ils",
        "rule_operational_since_draw", "rule_end_draw", "rule_end_reason",
    }
    if not isinstance(record, dict) or set(record) != mandatory:
        raise PrizeDataError("rule notice missing fields or contains unsupported claims")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise PrizeDataError("invalid rule notice schema")
    if (type(record["draw_id"]) is not int or record["draw_id"] != 3953
        or record["source_url"] != RULE_SOURCE
        or record["authority"] != "Mifal HaPais statutory public notice"
        or record["source_review_method"] != "official_notice_page_text_read_without_archived_html"
        or record["original_html_archived"] is not False
        or record["original_html_sha256"] is not None):
        raise PrizeDataError("rule notice source, status or draw ID is invalid")
    if _date_iso(record["notice_date"]) != date(2026, 8, 5):
        raise PrizeDataError("wrong special-rule publication date")
    if _date_iso(record["draw_date"]) != date(2026, 8, 8):
        raise PrizeDataError("wrong affected lottery date")
    prize_amounts = {
        "first_prize_regular_ils": 40_000_000,
        "first_prize_double_advertised_ils": 80_000_000,
        "second_prize_regular_ils": 750_000,
        "second_prize_double_advertised_ils": 1_500_000,
    }
    for key, expected in prize_amounts.items():
        if type(record[key]) is not int or record[key] != expected:
            raise PrizeDataError(f"{key} mismatch with operator announcement")
    eighth = record["eighth_prize_ils"]
    if (
        not isinstance(eighth, dict)
        or set(eighth) != {"regular", "double"}
        or any(type(value) is not int for value in eighth.values())
        or eighth != {"regular": 15, "double": 30}
    ):
        raise PrizeDataError("tier-eight special fixed payout mismatch")
    if record["receipts_amount_ils"] is not None:
        raise PrizeDataError("draw receipts were not provided; do not infer sales")
    percentages = {
        "3": "2.7", "4": "2.4", "5": "3.21",
        "6": "6.45", "7": "10.5",
    }
    if not isinstance(record["approx_percent_of_total_draw_receipts_by_tier"], dict):
        raise PrizeDataError("special distribution rates missing")
    if record["approx_percent_of_total_draw_receipts_by_tier"] != percentages:
        raise PrizeDataError("special distributions must match the published notice")
    if (
        type(record["rule_operational_since_draw"]) is not int
        or record["rule_operational_since_draw"] != 3953
        or type(record["rule_end_draw"]) is not int
        or record["rule_end_draw"] != 3953
        or not isinstance(record["rule_end_reason"], str)
        or not record["rule_end_reason"].strip()
        or not isinstance(record["notice_context"], str)
        or not record["notice_context"].strip()
    ):
        raise PrizeDataError("invalid operator rule window")
    prize = validate_prize_observation(observation)
    if prize["draw_id"] != 3953:
        raise PrizeDataError("special rule cannot be attached to another draw")
    if "newsId=3133" not in (prize["special_rules_note"] or ""):
        raise PrizeDataError("related prize observation must cite its rule notice")
    if prize["games"]["regular"][0]["winning_entries"] < 1:
        raise PrizeDataError("expected observed regular jackpot winner for termination")
    if prize["games"]["regular"][-1]["payout_per_winning_entry_ils"] != 15:
        raise PrizeDataError("wrong regular special tier-eight payout in draw")
    if prize["games"]["double"][-1]["payout_per_winning_entry_ils"] != 30:
        raise PrizeDataError("wrong Double special tier-eight payout in draw")
    return {
        "draw_id": 3953,
        "source_is_operator_rule_announcement": True,
        "gross_receipts_known": False,
        "special_tier_rates_approximate": True,
        "rule_stopped_after_first_prize_winner": True,
        "eligible_for_positive_ev_claim": False,
    }


def load_secondary_leads(path: str | Path, history: LotteryDataset) -> dict[str, Any]:
    return validate_secondary_leads(_load_json(path), history)


def load_special_rule_notice(path: str | Path, observation_path: str | Path) -> dict[str, Any]:
    return validate_special_rule_notice(_load_json(path), _load_json(observation_path))
