"""Offline quarantine intake for *new* operator-page payout observations.

This is the missing upstream stage for P3-A.2: verify an independently
obtained local copy of the operator's results page sufficiently to produce a
HUMAN-REVIEW candidate *without* requiring that the 16-tier observation
already exists. It NEVER writes to production prize_observations, never
downloads the page, and never authenticates a page or approved protocol.

Tests use SYNTHETIC operator-style text and do not certify the parser for
every possible layout of the actual operator website.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import CsvDatasetLoader, LotteryDataset, parse_draw_date
from .prize_data import PrizeDataError
from .source_capture_check import (
    _DOUBLE_HEADING,
    _EXTRA_HEADING,
    _OFFICIAL_HEADING,
    _REGULAR_HEADING,
    _flat_text,
    _rows_from_section,
)


def _capture_utc(when: Any, *, earliest: date) -> None:
    if not isinstance(when, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", when
    ):
        raise PrizeDataError("capture timestamp must be explicit UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        timestamp = datetime.strptime(when, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PrizeDataError("capture timestamp is not a valid UTC instant") from exc
    if timestamp.date() < earliest:
        raise PrizeDataError("capture date cannot precede the draw")


def extract_quarantined_prize_candidate(
    source_bytes: bytes,
    *,
    content_type: str,
    draw_id: int,
    captured_at_utc: str,
    history: LotteryDataset,
) -> dict[str, Any]:
    """Produce a quarantined payout candidate, never an official observation.

    Main/strong numbers supplied by the historical archive are only an
    independent reference, NOT verified as present on the captured page.
    The source text's draw ID, date and sixteen payout rows are checked.
    All other missing inputs stay null and the result deliberately cannot
    be passed to validate_prize_observation as-is.
    """
    if type(draw_id) is not int or draw_id < 1:
        raise PrizeDataError("draw_id must be a positive integer")
    matches = [item for item in history if item.draw_id == str(draw_id)]
    if len(matches) != 1:
        raise PrizeDataError("draw must exist exactly once in independent historical archive")
    historical = matches[0]
    draw_day = parse_draw_date(historical.date)
    _capture_utc(captured_at_utc, earliest=draw_day)
    visible = _flat_text(source_bytes, content_type)

    headings = _OFFICIAL_HEADING.findall(visible)
    if len(headings) != 1 or headings[0] != str(draw_id):
        raise PrizeDataError("capture draw heading absent, duplicated or mismatched")
    date_display = draw_day.strftime("%d/%m/%Y")
    if not re.search(r"(?<![0-9])" + re.escape(date_display) + r"(?![0-9])", visible):
        raise PrizeDataError("capture must contain the exact archived draw date")

    regular_at = visible.find(_REGULAR_HEADING)
    double_at = visible.find(_DOUBLE_HEADING)
    if (
        regular_at < 0
        or double_at <= regular_at
        or visible.count(_REGULAR_HEADING) != 1
        or visible.count(_DOUBLE_HEADING) != 1
    ):
        raise PrizeDataError("cannot unambiguously locate regular and Double Lotto prize tables")
    extra_at = visible.find(_EXTRA_HEADING, double_at)
    regular_text = visible[regular_at + len(_REGULAR_HEADING):double_at]
    double_text = visible[
        double_at + len(_DOUBLE_HEADING):extra_at if extra_at >= 0 else len(visible)
    ]
    regular = _rows_from_section(regular_text, game="regular")
    double = _rows_from_section(double_text, game="double")
    return {
        "candidate_schema_version": 1,
        "status": "quarantined_operator_page_capture_pending_human_review",
        "draw_id": draw_id,
        "draw_date": draw_day.isoformat(),
        "archive_reference_only": {
            "main_numbers": list(sorted(historical.numbers)),
            "strong_number": historical.strong_number,
            "numbers_verified_from_captured_page": False,
        },
        "candidate_tiers": {"regular": regular, "double": double},
        "candidate_source": {
            "operator_page_claimed_url": f"https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId={draw_id}",
            "captured_at_utc_supplied_by_researcher": captured_at_utc,
            "content_type": content_type,
            "sha256_of_actual_supplied_bytes": hashlib.sha256(source_bytes).hexdigest(),
            "supplied_byte_count": len(source_bytes),
            "source_authenticity_independently_verified": False,
            "approved_draw_protocol_verified": False,
        },
        "missing_inputs": {
            "advertised_first_and_second_prizes": None,
            "reported_all_games_total_prizes": None,
            "ticket_sales": None,
            "taxes": None,
            "applicable_rule_version": None,
        },
        "required_before_production_observation": [
            "Independently inspect stored original source bytes and their provenance",
            "Verify captured-page main and strong numbers against independent archive",
            "Verify all sixteen tier counts and prizes on original source",
            "Verify advertised 1st/2nd prizes and total or retain explicit nulls",
            "Document special prize rules and legally approved protocol status",
            "Human approval and separate entry through existing source-audit manifest",
        ],
        "auto_promoted_to_prize_observations": False,
        "eligible_for_expected_value": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quarantine candidate prize tiers from an existing locally saved source."
    )
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--content-type", choices=["text/html", "text/plain"], required=True)
    parser.add_argument("--draw-id", type=int, required=True)
    parser.add_argument("--captured-at-utc", required=True)
    parser.add_argument("--historical-csv", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = args.source_file.read_bytes()
        archive = CsvDatasetLoader().load(args.historical_csv)
        candidate = extract_quarantined_prize_candidate(
            raw,
            content_type=args.content_type,
            draw_id=args.draw_id,
            captured_at_utc=args.captured_at_utc,
            history=archive,
        )
    except (OSError, PrizeDataError, ValueError) as exc:
        parser.exit(2, f"Capture intake rejected: {exc}\n")
    print(json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
