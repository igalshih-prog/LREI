"""Pre-draw, content-hashed records for prospective lottery evaluation.

A local checksum detects accidental edits; a third-party timestamped commit or
external record is needed to *prove* a record predates the target draw.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .dataset import parse_draw_date


def parse_target_datetime(value: str) -> datetime:
    """Parse an explicit offset-aware future draw time into UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("target draw time must be ISO-8601 with a UTC offset") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("target draw time must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_snapshot(
    *,
    dataset_file: Path,
    dataset: Any,
    tickets: Iterable[Any],
    mode: str,
    objective: str | None,
    seed: int,
    source_commit: str,
    target_draw_at: datetime,
    generated_count: int,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Validate and hash a prediction record without adding target outcomes."""
    now = created_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("created_at must have a timezone")
    now = now.astimezone(timezone.utc)
    if target_draw_at.tzinfo is None or target_draw_at.utcoffset() is None:
        raise ValueError("target_draw_at must have a timezone")
    target = target_draw_at.astimezone(timezone.utc)
    if target <= now:
        raise ValueError("target draw must be strictly in the future")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source_commit must be a 40-character Git SHA")
    if mode not in {"regular", "pro", "elite", "smart"}:
        raise ValueError("unsupported recommendation mode")
    if mode == "smart":
        if objective not in {"coverage_any_prize", "coverage_4plus", "historical"}:
            raise ValueError("smart objective must be explicit")
    elif objective is not None:
        raise ValueError("objective only applies to smart mode")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not isinstance(generated_count, int) or generated_count < 14:
        raise ValueError("generated_count must be at least 14")
    if not len(dataset):
        raise ValueError("cannot snapshot an empty dataset")
    latest = dataset.latest()
    latest_date = parse_draw_date(latest.date)
    if latest_date is None:
        raise ValueError("latest historical draw must have a valid date")
    if latest_date >= target.date():
        raise ValueError("historical dataset must precede target draw date")
    age = (now.date() - latest_date).days
    if not 0 <= age <= 4:
        raise ValueError("historical data is future-dated or more than four days old")
    data_path = Path(dataset_file)
    data_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()

    valid_tickets: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    for ticket in tickets:
        original = tuple(ticket.numbers)
        if len(original) != 6 or any(type(n) is not int or not 1 <= n <= 37 for n in original):
            raise ValueError("each ticket must contain six integers in 1..37")
        main = tuple(sorted(original))
        if len(set(main)) != 6 or main in seen:
            raise ValueError("all tickets must have six unique numbers and distinct main lines")
        strong = ticket.strong_number
        if type(strong) is not int or not 1 <= strong <= 7:
            raise ValueError("each ticket must include a strong number in 1..7")
        seen.add(main)
        valid_tickets.append({"main": list(main), "strong": strong})
    if len(valid_tickets) != 14:
        raise ValueError("a prospective snapshot requires exactly 14 tickets")

    payload = {
        "schema_version": 1,
        "created_at_utc": now.isoformat().replace("+00:00", "Z"),
        "target_draw_at_utc": target.isoformat().replace("+00:00", "Z"),
        "source_commit": source_commit,
        "dataset_sha256": data_hash,
        "latest_draw": {"id": str(latest.draw_id), "date": latest_date.isoformat()},
        "draw_count": len(dataset),
        "mode": mode,
        "objective": objective,
        "seed": seed,
        "reported_generated_count": generated_count,
        "ticket_count": 14,
        "tickets": valid_tickets,
    }
    return {**payload, "record_sha256": _digest(payload)}


def verify_snapshot(record: dict[str, Any]) -> bool:
    """Check integrity only; this is not a trusted third-party timestamp."""
    if not isinstance(record, dict) or not isinstance(record.get("record_sha256"), str):
        return False
    payload = {key: value for key, value in record.items() if key != "record_sha256"}
    return _digest(payload) == record["record_sha256"]


def write_snapshot(record: dict[str, Any], directory: Path) -> Path:
    """Create an individual JSON record with exclusive, no-overwrite writes."""
    if not verify_snapshot(record):
        raise ValueError("snapshot content digest is invalid")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = record["created_at_utc"].replace(":", "").replace("-", "")
    path = folder / f"predraw-{stamp}-{record['record_sha256'][:16]}.json"
    data = (json.dumps(record, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(fd, "wb") as destination:
            destination.write(data)
            destination.flush()
            os.fsync(destination.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path
