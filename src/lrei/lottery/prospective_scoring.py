"""Deterministic post-draw evaluation of immutable pre-draw snapshots.

Official winning numbers must be supplied and independently checked by the
operator; source_url is provenance metadata, not proof of source authenticity.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .dataset import LotteryDrawRecord, parse_draw_date
from .prize_evaluation import evaluate_portfolio_prizes
from .prospective_ledger import parse_target_datetime, verify_snapshot
from .recommendation import RecommendedTicket


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def score_snapshot(
    snapshot: dict[str, Any],
    draw: LotteryDrawRecord,
    *,
    source_url: str,
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Score a frozen 14-ticket record only after the specified draw has occurred."""
    if not verify_snapshot(snapshot) or snapshot.get("schema_version") != 1:
        raise ValueError("pre-draw snapshot checksum or schema is invalid")
    now = _utc(evaluated_at or datetime.now(timezone.utc), "evaluated_at")
    target = parse_target_datetime(snapshot["target_draw_at_utc"])
    if now < target:
        raise ValueError("target draw is still in the future")
    parsed_url = urlsplit(source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("draw results require an HTTPS source URL")
    draw_date = parse_draw_date(draw.date)
    if draw_date is None:
        raise ValueError("actual draw must have a valid date")
    expected_date = snapshot.get("target_draw_date_local")
    if expected_date is None:
        raise ValueError("snapshot must contain a local target draw date")
    if draw_date.isoformat() != expected_date:
        raise ValueError("actual draw date does not match pre-registered target date")
    latest_id = str(snapshot["latest_draw"]["id"])
    if draw.draw_id == latest_id:
        raise ValueError("cannot evaluate an already-included historical draw")
    if latest_id.isdecimal() and draw.draw_id.isdecimal() and int(draw.draw_id) <= int(latest_id):
        raise ValueError("actual draw ID must follow the frozen historical data")

    rows = snapshot["tickets"]
    if len(rows) != 14 or snapshot["ticket_count"] != 14:
        raise ValueError("snapshot must contain 14 tickets")
    tickets = tuple(
        RecommendedTicket(numbers=tuple(row["main"]), strong_number=row["strong"])
        for row in rows
    )
    if len({tuple(sorted(ticket.numbers)) for ticket in tickets}) != 14:
        raise ValueError("snapshot must contain distinct main lines")
    outcome = evaluate_portfolio_prizes(tickets, draw)
    results = tuple({
        "ticket": index,
        "main_matches": value.main_matches,
        "strong_match": value.strong_match,
        "prize_tier": value.prize_tier,
    } for index, value in enumerate(outcome.tickets, 1))
    payload = {
        "schema_version": 1,
        "evaluated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "snapshot_sha256": snapshot["record_sha256"],
        "result_source_url_user_supplied": source_url,
        "source_independently_verified": False,
        "draw": {
            "id": draw.draw_id,
            "date": draw_date.isoformat(),
            "main": list(sorted(draw.numbers)),
            "strong": draw.strong_number,
        },
        "any_prize": outcome.any_prize,
        "winning_ticket_count": outcome.winning_ticket_count,
        "best_prize_tier": outcome.best_prize_tier,
        "best_main_matches": max(item.main_matches for item in outcome.tickets),
        "at_least_3_main": any(item.main_matches >= 3 for item in outcome.tickets),
        "at_least_4_main": any(item.main_matches >= 4 for item in outcome.tickets),
        "at_least_5_main": any(item.main_matches >= 5 for item in outcome.tickets),
        "at_least_6_main": any(item.main_matches == 6 for item in outcome.tickets),
        "prize_tier_counts": {str(k): v for k, v in outcome.prize_tier_counts.items()},
        "tickets": list(results),
    }
    return {**payload, "result_sha256": _hash(payload)}


def write_score(scored: dict[str, Any], directory: Path) -> Path:
    """Store a separate scored record without mutating the frozen prediction."""
    if not isinstance(scored, dict) or not isinstance(scored.get("result_sha256"), str):
        raise ValueError("invalid scored record")
    payload = {k: v for k, v in scored.items() if k != "result_sha256"}
    if _hash(payload) != scored["result_sha256"]:
        raise ValueError("scored record checksum mismatch")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"scored-{scored['snapshot_sha256'][:16]}-{scored['result_sha256'][:16]}.json"
    path = folder / name
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(fd, "wb") as destination:
            destination.write((json.dumps(scored, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf8"))
            destination.flush()
            os.fsync(destination.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path
