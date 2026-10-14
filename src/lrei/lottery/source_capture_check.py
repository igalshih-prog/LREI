"""P3-A.2: offline first-party page capture validation and real source hashing.

This module NEVER fetches from the lottery operator. It checks a *locally
supplied* capture of a specific draw's informational official results page.

The expected text layout is deliberately strict: fail closed if a table is
ambiguous or if any of the sixteen tier labels, entry counts or payouts do
not match the recorded observation. HTML exports that use a different
rendering format require a new independently tested adapter, NOT guessing.

Matching text and an actual raw-byte SHA256 do not prove the downloaded
document's authenticity or replace the legally approved draw protocol.
They do make transcription verification independently reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .prize_data import (
    PRIZE_TIER_LABELS,
    PrizeDataError,
    load_observation,
    validate_prize_observation,
)

MAX_CAPTURE_BYTES = 6 * 1024 * 1024
_ROW_PATTERN = re.compile(
    r"מס['׳]\s*ניחושים\s*"
    r"(6\s*\+\s*חזק|6|5\s*\+\s*חזק|5|4\s*\+\s*חזק|4|3\s*\+\s*חזק|3)\s*"
    r"כמות\s*זכיות\s*([0-9][0-9,]*)\s*"
    r"גובה\s*הפרס\s*([0-9][0-9,]*)\s*₪"
)
_OFFICIAL_HEADING = re.compile(r"תוצאות\s+הגרלה\s+מס['׳]?\s*(\d+)")
_REGULAR_HEADING = "טבלת זכיות לוטו"
_DOUBLE_HEADING = "טבלת זכיות דאבל לוטו"
_EXTRA_HEADING = "תוצאות הגרלה אקסטרא"


class _PageText(HTMLParser):
    """Visible source text only; never execute or download assets."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignore_depth = 0
        self._pieces: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._ignore_depth:
            self._ignore_depth += 1
        elif tag in {"script", "style", "noscript", "template"}:
            self._ignore_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self._ignore_depth:
            self._ignore_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignore_depth and data.strip():
            self._pieces.append(data)

    @property
    def text(self) -> str:
        return " ".join(self._pieces)


def _flat_text(raw: bytes, content_type: str) -> str:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_CAPTURE_BYTES:
        raise PrizeDataError("source capture must contain 1–6 MiB of raw bytes")
    try:
        decoded = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise PrizeDataError("source capture must be UTF-8; do not guess encoding") from exc
    if "\x00" in decoded:
        raise PrizeDataError("source capture contains binary/NUL data")
    if content_type == "text/html":
        parser = _PageText()
        parser.feed(decoded)
        value = parser.text
    elif content_type == "text/plain":
        value = decoded
    else:
        raise PrizeDataError("only locally saved text/html or text/plain captures are accepted")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _rows_from_section(text: str, *, game: str) -> list[dict[str, Any]]:
    matches = list(_ROW_PATTERN.finditer(text))
    if len(matches) != len(PRIZE_TIER_LABELS):
        raise PrizeDataError(
            f"{game}: capture must contain exactly eight recognizable payout rows; got {len(matches)}"
        )
    rows: list[dict[str, Any]] = []
    for expected, match in zip(PRIZE_TIER_LABELS, matches):
        label = re.sub(r"\s+", "", match.group(1)).replace("חזק", "strong")
        if label != expected:
            raise PrizeDataError(f"{game}: prize tier order mismatch at {expected}")
        count = int(match.group(2).replace(",", ""))
        award = int(match.group(3).replace(",", ""))
        rows.append({
            "tier": expected,
            "winning_entries": count,
            "payout_per_winning_entry_ils": award,
        })
    return rows


def inspect_captured_operator_page(
    raw: bytes,
    *,
    content_type: str,
    observation: dict[str, Any],
    captured_at_utc: str,
) -> dict[str, Any]:
    """Compare all 16 rows to a supplied, separately auditable observation.

    This is a *candidate* evidence report, not an authenticated certificate.
    Retain the raw bytes separately to enable future SHA256 verification.
    """
    observation = validate_prize_observation(observation)
    if not isinstance(captured_at_utc, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", captured_at_utc
    ):
        raise PrizeDataError("captured_at_utc must be supplied as YYYY-MM-DDTHH:MM:SSZ")
    try:
        capture_time = datetime.strptime(captured_at_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PrizeDataError("invalid UTC capture time") from exc
    date_part = observation["draw_date"]
    if capture_time.date().isoformat() < date_part:
        raise PrizeDataError("a capture cannot predate the drawing")
    text = _flat_text(raw, content_type)
    headings = _OFFICIAL_HEADING.findall(text)
    if len(headings) != 1 or headings[0] != str(observation["draw_id"]):
        raise PrizeDataError("operator page must show exactly the expected draw identifier")
    yyyy, mm, dd = date_part.split("-")
    if not re.search(r"\b" + re.escape(f"{dd}/{mm}/{yyyy}") + r"\b", text):
        raise PrizeDataError("operator page date disagrees with archived draw")
    regular_pos = text.find(_REGULAR_HEADING)
    double_pos = text.find(_DOUBLE_HEADING)
    if regular_pos < 0 or double_pos <= regular_pos:
        raise PrizeDataError("regular and double prize tables not found in canonical order")
    if text.count(_REGULAR_HEADING) != 1 or text.count(_DOUBLE_HEADING) != 1:
        raise PrizeDataError("ambiguous duplicate regular/double prize-table headings")
    extra_pos = text.find(_EXTRA_HEADING, double_pos)
    regular = _rows_from_section(text[regular_pos + len(_REGULAR_HEADING):double_pos], game="regular")
    double = _rows_from_section(
        text[double_pos + len(_DOUBLE_HEADING):extra_pos if extra_pos >= 0 else len(text)],
        game="double",
    )
    for game, rows in (("regular", regular), ("double", double)):
        if rows != observation["games"][game]:
            raise PrizeDataError(
                f"{game}: captured operator page payout rows disagree with stored observation"
            )
    return {
        "candidate_schema_version": 1,
        "draw_id": observation["draw_id"],
        "source_url": observation["source_url"],
        "captured_at_utc": captured_at_utc,
        "content_type": content_type,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_bytes": len(raw),
        "matched_payout_rows": 16,
        "regular_rows_match": True,
        "double_rows_match": True,
        "source_authenticity_independently_verified": False,
        "approved_draw_protocol_verified": False,
        "human_source_review_required": True,
        "candidate_only_not_economic_evidence": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline check of a locally saved operator results-page capture (no web calls)."
    )
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--content-type", choices=["text/html", "text/plain"], required=True)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--captured-at-utc", required=True)
    args = parser.parse_args()
    try:
        source_bytes = args.source_file.read_bytes()
        observation = load_observation(args.observation)
        report = inspect_captured_operator_page(
            source_bytes,
            content_type=args.content_type,
            observation=observation,
            captured_at_utc=args.captured_at_utc,
        )
    except (OSError, PrizeDataError) as exc:
        parser.exit(2, f"Capture audit failed: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
