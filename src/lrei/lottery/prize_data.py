"""P3-A: verified-shape archive of lottery prize-table observations.

A draw-results CSV tells us WHAT came out. This separate dataset records
published prize amounts and counts of winning entries (not unique people).
It does not infer ticket sales, taxes, individual ticket choices, expected
profit or binding official results. The site warns that its web display is
informational; approved draw protocols are authoritative.

Data files use plain JSON for reproducible, reviewable manual transcription.
Validation is strict: missing fields are NULL, not invented; normal and
double have separate eight-tier observations.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .dataset import LotteryDataset, parse_draw_date

PRIZE_TIER_LABELS = (
    "6+strong", "6", "5+strong", "5",
    "4+strong", "4", "3+strong", "3",
)
GAME_TYPES = ("regular", "double")
STATUS = "operator_site_display_only_not_binding"

class PrizeDataError(ValueError):
    """Source data is incomplete, inaccurate or not provenance-traceable."""


def _natural(value: Any, label: str, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if type(value) is not int or value < 0:
        raise PrizeDataError(f"{label} must be a non-negative integer" + (" or null" if nullable else ""))
    return value


def _validate_tiers(tiers: Any, game: str) -> None:
    if not isinstance(tiers, list) or len(tiers) != len(PRIZE_TIER_LABELS):
        raise PrizeDataError(f"{game} must have all eight prize tiers, in order")
    for expected, row in zip(PRIZE_TIER_LABELS, tiers):
        if not isinstance(row, dict) or set(row) != {
            "tier", "winning_entries", "payout_per_winning_entry_ils"
        } or row["tier"] != expected:
            raise PrizeDataError(f"{game} tier must be {expected!r} with canonical columns")
        _natural(row["winning_entries"], f"{game}.{expected}.winning_entries")
        _natural(
            row["payout_per_winning_entry_ils"],
            f"{game}.{expected}.payout_per_winning_entry_ils",
            nullable=True,
        )
        if row["winning_entries"] and row["payout_per_winning_entry_ils"] is None:
            raise PrizeDataError(f"{game}.{expected}: observed wins require published payout")
        # The CSV reply quarantine already refuses this inconsistent state.
        # A production observation must not silently turn actual winners into
        # zero prize payments; zero-winner rows may legitimately show 0/null.
        if row["winning_entries"] and row["payout_per_winning_entry_ils"] == 0:
            raise PrizeDataError(f"{game}.{expected}: winning entries cannot have zero payout")


def _valid_source(url: Any, draw_id: int) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
        return False
    try:
        if parsed.port is not None:
            return False
    except ValueError:
        return False
    if parsed.hostname not in {"pais.co.il", "www.pais.co.il"}:
        return False
    if parsed.path.lower() != "/lotto/currentlotto.aspx":
        return False
    qs = parse_qs(parsed.query, keep_blank_values=True)
    return qs == {"lotteryId": [str(draw_id)]}


def validate_prize_observation(record: Any, historical: LotteryDataset | None = None) -> dict[str, Any]:
    """Reject made-up/ambiguous fields, check result vs archive if supplied."""
    if not isinstance(record, dict):
        raise PrizeDataError("record must be a JSON object")
    required = {
        "schema_version", "draw_id", "draw_date", "main_numbers",
        "strong_number", "source_url", "source_status",
        "games", "advertised_prizes_ils", "total_prizes_paid_ils",
        "ticket_sales_ils", "tax_paid_ils", "special_rules_note",
    }
    if (
        set(record) != required
        or type(record["schema_version"]) is not int
        or record["schema_version"] != 1
    ):
        raise PrizeDataError("schema v1 fields missing or unexpected")
    draw_id = record["draw_id"]
    if type(draw_id) is not int or draw_id <= 0:
        raise PrizeDataError("draw_id must be a positive integer")
    if not isinstance(record["draw_date"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["draw_date"]):
        raise PrizeDataError("draw_date must use YYYY-MM-DD")
    try:
        parsed_date = date.fromisoformat(record["draw_date"])
    except (TypeError, ValueError) as exc:
        raise PrizeDataError("draw_date must be a valid ISO-8601 date") from exc
    main = record["main_numbers"]
    if not isinstance(main, list) or len(main) != 6 or any(
        type(v) is not int or not 1 <= v <= 37 for v in main
    ) or len(set(main)) != 6 or main != sorted(main):
        raise PrizeDataError("main_numbers must be sorted six distinct numbers in 1..37")
    strong = record["strong_number"]
    if type(strong) is not int or not 1 <= strong <= 7:
        raise PrizeDataError("strong_number must be in 1..7")
    if record["source_status"] != STATUS or not _valid_source(record["source_url"], draw_id):
        raise PrizeDataError("requires matching pais.co.il draw URL and nonbinding-site disclaimer")

    games = record["games"]
    if not isinstance(games, dict) or set(games) != set(GAME_TYPES):
        raise PrizeDataError("both regular and double games are mandatory")
    for game in GAME_TYPES:
        _validate_tiers(games[game], game)

    advertised = record["advertised_prizes_ils"]
    if not isinstance(advertised, dict) or set(advertised) != {
        "regular_first", "double_first", "regular_second", "double_second"
    }:
        raise PrizeDataError("advertised_prizes_ils must include four nominal prizes")
    for key, value in advertised.items():
        _natural(value, f"advertised_prizes_ils.{key}", nullable=True)
    for name in ("total_prizes_paid_ils", "ticket_sales_ils", "tax_paid_ils"):
        _natural(record[name], name, nullable=True)
    note = record["special_rules_note"]
    if note is not None and (not isinstance(note, str) or not note.strip()):
        raise PrizeDataError("special_rules_note must be meaningful or null")

    if historical is not None:
        matches = [draw for draw in historical if draw.draw_id == str(draw_id)]
        if len(matches) != 1:
            raise PrizeDataError("draw ID missing or duplicated in independent archive")
        archived = matches[0]
        if tuple(main) != tuple(sorted(archived.numbers)) or strong != archived.strong_number:
            raise PrizeDataError("prize table disagrees with historical main/strong results")
        if parse_draw_date(archived.date) != parsed_date:
            raise PrizeDataError("prize table disagrees with historical draw date")

    # Return a detached JSON-compatible structure; callers must not mutate it.
    return json.loads(json.dumps(record, ensure_ascii=False, allow_nan=False))


def canonical_sha256(record: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def load_observation(path: str | Path, historical: LotteryDataset | None = None) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrizeDataError("invalid or unreadable prize source file") from exc
    return validate_prize_observation(raw, historical)


def prize_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Descriptive accounting only, NOT a net-return or EV forecast."""
    row = validate_prize_observation(record)
    return {
        "draw_id": row["draw_id"],
        "regular_winning_entries": sum(x["winning_entries"] for x in row["games"]["regular"]),
        "double_winning_entries": sum(x["winning_entries"] for x in row["games"]["double"]),
        "reported_total_paid_ils": row["total_prizes_paid_ils"],
        "record_sha256": canonical_sha256(row),
        "sales_known": row["ticket_sales_ils"] is not None,
        "tax_known": row["tax_paid_ils"] is not None,
        "value_calculable": False,  # no EV inference from payouts alone
    }
