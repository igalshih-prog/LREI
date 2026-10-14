"""P3-A.2: quarantine a complete operator-style 14-draw payout CSV response.

Do NOT treat a syntactically valid CSV as authenticated or official.
This parser accepts only *fully filled* 224-row reply worksheets
for draws 3955–3968, computes SHA-256 of actual supplied bytes,
cross-checks draw IDs/dates against the independent history, and
produces a review-only candidate. It never writes prize_observations.

No lottery website requests, scraping, winnings prediction, EV or wagers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import CsvDatasetLoader, LotteryDataset, parse_draw_date
from .prize_data import GAME_TYPES, PRIZE_TIER_LABELS, PrizeDataError

FIRST_DRAW = 3955
LAST_DRAW = 3968
HEADER = (
    "draw_id", "draw_date", "game", "tier",
    "winning_entries", "payout_per_winning_entry_ils",
)
MAX_BYTES = 2 * 1024 * 1024
MAX_WINNING_ENTRIES = 100_000_000
MAX_INDIVIDUAL_PAYOUT_ILS = 1_000_000_000


def _parse_number(raw: Any, *, key: str, maximum: int) -> int:
    if not isinstance(raw, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)", raw):
        raise PrizeDataError(
            f"{key}: complete numeric amounts required (not blank, formula, float, or guessed null)"
        )
    number = int(raw)
    if number > maximum:
        raise PrizeDataError(f"{key}: outside safe input bounds")
    return number


def _timestamp(text: Any) -> None:
    if not isinstance(text, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text
    ):
        raise PrizeDataError("received-at must be explicit UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PrizeDataError("invalid received-at UTC timestamp") from exc


def quarantine_official_payout_csv(
    raw_bytes: bytes,
    *,
    historical: LotteryDataset,
    received_at_utc: str,
) -> dict[str, Any]:
    """Check complete request-template-shaped CSV and return candidate only.

    A syntactically passing CSV, even one with numbers, proves nothing
    about its original sender or the correctness of its monetary values.
    The returned rows are *not* validated operator observations.
    """
    _timestamp(received_at_utc)
    if not isinstance(raw_bytes, bytes) or not 0 < len(raw_bytes) <= MAX_BYTES:
        raise PrizeDataError("reply CSV must contain between 1 and 2 MiB of bytes")
    try:
        content = raw_bytes.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise PrizeDataError("reply CSV must have UTF-8 encoding") from exc
    if "\x00" in content:
        raise PrizeDataError("reply CSV contains binary/NUL data")
    parsed = csv.reader(io.StringIO(content, newline=""), strict=True)
    try:
        columns = next(parsed)
        if tuple(columns) != HEADER:
            raise PrizeDataError("reply CSV headers missing, reordered, or duplicated")
        rows = list(parsed)
    except (csv.Error, StopIteration) as exc:
        raise PrizeDataError("reply CSV is malformed or empty") from exc
    if len(rows) != (LAST_DRAW - FIRST_DRAW + 1) * len(GAME_TYPES) * len(PRIZE_TIER_LABELS):
        raise PrizeDataError("complete reply must have exactly 224 tier rows")

    reference: dict[int, Any] = {}
    for item in historical:
        identifier = int(item.draw_id)
        if FIRST_DRAW <= identifier <= LAST_DRAW:
            if identifier in reference:
                raise PrizeDataError("duplicate draw ID in independent historical archive")
            reference[identifier] = item
    if len(reference) != LAST_DRAW - FIRST_DRAW + 1:
        raise PrizeDataError("independent archive lacks expected 14 draw IDs")

    expected = (
        (draw_id, game, tier)
        for draw_id in range(FIRST_DRAW, LAST_DRAW + 1)
        for game in GAME_TYPES
        for tier in PRIZE_TIER_LABELS
    )
    output: list[dict[str, Any]] = []
    for row_no, (fields, (expected_id, expected_game, expected_tier)) in enumerate(
        zip(rows, expected), start=2
    ):
        if len(fields) != len(HEADER):
            raise PrizeDataError(f"row {row_no}: missing/extra CSV fields")
        draw_id, draw_date, game, tier, winners, payout = fields
        if (
            draw_id != str(expected_id)
            or game != expected_game
            or tier != expected_tier
        ):
            raise PrizeDataError(f"row {row_no}: duplicate, missing, or out-of-order tier")
        archive_date = parse_draw_date(reference[expected_id].date).isoformat()
        if draw_date != archive_date:
            raise PrizeDataError(f"row {row_no}: draw date disagrees with independent archive")
        if draw_date > received_at_utc[:10]:
            raise PrizeDataError("source cannot predate the historical draw")
        count = _parse_number(
            winners, key=f"row {row_no} winning_entries", maximum=MAX_WINNING_ENTRIES
        )
        amount = _parse_number(
            payout, key=f"row {row_no} payout_per_winning_entry_ils",
            maximum=MAX_INDIVIDUAL_PAYOUT_ILS,
        )
        if count > 0 and amount == 0:
            raise PrizeDataError(f"row {row_no}: winning entries cannot have zero payout")
        output.append({
            "draw_id": expected_id,
            "draw_date": draw_date,
            "game": game,
            "tier": tier,
            "winning_entries": count,
            "payout_per_winning_entry_ils": amount,
        })

    # These are input-shape checks, NOT lottery authenticity assertions.
    # Refuse implausible all-zero draw reports that might be filled placeholders.
    for draw_id in range(FIRST_DRAW, LAST_DRAW + 1):
        subset = [line for line in output if line["draw_id"] == draw_id]
        if sum(line["winning_entries"] for line in subset) == 0:
            raise PrizeDataError(
                f"draw {draw_id}: every winning count is zero; possible placeholder data"
            )
    return {
        "candidate_schema_version": 1,
        "status": "quarantined_completed_request_csv_not_authenticated",
        "window": {"first_draw": FIRST_DRAW, "last_draw": LAST_DRAW},
        "draw_count": LAST_DRAW - FIRST_DRAW + 1,
        "tier_row_count": len(output),
        "source_evidence": {
            "received_at_utc_supplied_by_operator_or_researcher": received_at_utc,
            "sha256_of_received_bytes": hashlib.sha256(raw_bytes).hexdigest(),
            "actual_received_byte_count": len(raw_bytes),
            "source_sender_verified": False,
            "source_authenticity_verified": False,
            "approved_draw_protocol_verified": False,
        },
        "candidate_rows": output,
        "requires_human_source_and_payout_review": True,
        "ready_for_production_prize_observations": False,
        "eligible_for_expected_value": False,
        "has_enough_data_for_profit_claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate filled 224-row CSV reply as unverified quarantine only."
    )
    parser.add_argument("--reply-csv", type=Path, required=True)
    parser.add_argument("--historical-csv", type=Path, required=True)
    parser.add_argument("--received-at-utc", required=True)
    args = parser.parse_args()
    try:
        report = quarantine_official_payout_csv(
            args.reply_csv.read_bytes(),
            historical=CsvDatasetLoader().load(args.historical_csv),
            received_at_utc=args.received_at_utc,
        )
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(2, f"Reply intake rejected: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
