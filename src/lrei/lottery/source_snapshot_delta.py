"""Offline, fail-closed comparison of two *untrusted* Pais archive exports.

Checks exact current-rules draw content, *including* both jackpot winner-count
fields. Neither SHA-256 nor this offline comparison attests HTTPS provenance,
committee-approved results, source rights, or permission for monetary claims.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE_ID = 2833
BASE_DATE = date(2016, 10, 10)
MAX_BYTES = 8 * 1024 * 1024
FIELDS = (
    "הגרלה", "תאריך", "1", "2", "3", "4", "5", "6", "המספר החזק/נוסף",
    "מספר_זוכים_לוטו", "מספר_זוכים_דאבל_לוטו", "",
)
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")


class SourceSnapshotError(ValueError):
    """A source snapshot was structurally invalid or its integrity pin failed."""


def parse_snapshot(raw: bytes) -> dict[str, Any]:
    """Return a strict canonical content map, not a provenance attestation."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise SourceSnapshotError("source bytes must be nonempty and within 8 MiB")
    if b"\0" in raw or raw[:128].lstrip().lower().startswith((b"<html", b"<!doctype")):
        raise SourceSnapshotError("source contains HTML or binary bytes")
    try:
        text = raw.decode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "cp1255")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = tuple(next(reader))
        if header != FIELDS:
            raise SourceSnapshotError("source header differs from expected 12 columns")
        modern = {}
        total_rows = 0
        for line, row in enumerate(reader, start=2):
            if not row:
                continue
            total_rows += 1
            if len(row) != 12 or row[11] != "":
                raise SourceSnapshotError(f"archive row {line} has an invalid column shape")
            if re.fullmatch(r"[0-9]+", row[0]) is None:
                raise SourceSnapshotError(f"archive row {line} has a bad draw ID")
            try:
                draw_id = int(row[0])
                draw_date = datetime.strptime(row[1], "%d/%m/%Y").date()
            except ValueError as exc:
                raise SourceSnapshotError(f"archive row {line} has a bad date") from exc
            # A 1960s ID can be numerically larger than contemporary draw IDs.
            if draw_id < BASE_ID or draw_date < BASE_DATE:
                continue
            if any(re.fullmatch(r"[0-9]{1,2}", v) is None for v in row[2:8]):
                raise SourceSnapshotError(f"draw {draw_id} has a malformed main number")
            mains = tuple(sorted(map(int, row[2:8])))
            if len(set(mains)) != 6 or any(not 1 <= n <= 37 for n in mains):
                raise SourceSnapshotError(f"draw {draw_id} violates 6/37 rules")
            if re.fullmatch(r"[1-7]", row[8]) is None:
                raise SourceSnapshotError(f"draw {draw_id} has an invalid strong number")
            if any(re.fullmatch(r"[0-9]+", v) is None for v in row[9:11]):
                raise SourceSnapshotError(f"draw {draw_id} has an invalid top-tier count")
            if draw_id in modern:
                raise SourceSnapshotError(f"duplicate modern draw {draw_id}")
            modern[draw_id] = (
                draw_date.isoformat(), mains, int(row[8]), int(row[9]), int(row[10])
            )
    except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
        raise SourceSnapshotError("source is not a decodable Pais CSV") from exc
    ids = sorted(modern)
    if not ids or ids[0] != BASE_ID or ids[-1] != BASE_ID + len(ids) - 1:
        raise SourceSnapshotError("current-era source has missing or out-of-range draw IDs")
    previous_date = date.min
    for draw_id in ids:
        draw_date = date.fromisoformat(modern[draw_id][0])
        if draw_date < previous_date:
            raise SourceSnapshotError(f"draw {draw_id} date goes backwards")
        previous_date = draw_date
    return {"draws": modern, "ids": ids, "last_date": previous_date, "raw_rows": total_rows}


def compare_snapshots(
    previous: bytes, current: bytes, *, expected_previous_sha256: str,
) -> dict[str, Any]:
    """A pinned previous capture is needed, but never constitutes source proof."""
    if type(expected_previous_sha256) is not str or not HEX_SHA.fullmatch(expected_previous_sha256):
        raise SourceSnapshotError("expected previous SHA-256 must be lowercase hex")
    previous_digest = hashlib.sha256(previous).hexdigest() if type(previous) is bytes else ""
    if previous_digest != expected_previous_sha256:
        raise SourceSnapshotError("previous capture SHA-256 does not match review pin")
    old = parse_snapshot(previous)
    new = parse_snapshot(current)
    old_ids, new_ids = old["ids"], new["ids"]
    missing = [i for i in old_ids if i not in new["draws"]]
    revised = [i for i in old_ids if i in new["draws"] and old["draws"][i] != new["draws"][i]]
    added = [i for i in new_ids if i > old_ids[-1]]
    if missing or revised:
        status = "HISTORICAL_MISSING_OR_CHANGED_STOP_REVIEW"
    elif added:
        status = "NEW_ROWS_REQUIRES_HUMAN_REVIEW"
    else:
        status = "NO_NEW_ROWS_CHECK_FRESHNESS"
    return {
        "schema_version": 1,
        "status": status,
        "previous_source_sha256": previous_digest,
        "current_source_sha256": hashlib.sha256(current).hexdigest(),
        "previous_raw_row_count": old["raw_rows"],
        "current_raw_row_count": new["raw_rows"],
        "previous_latest_draw_id": old_ids[-1],
        "current_latest_draw_id": new_ids[-1],
        "current_latest_draw_date": new["last_date"].isoformat(),
        "prior_modern_rows_checked": len(old_ids),
        "missing_prior_draw_ids": missing,
        "revised_prior_draw_ids": revised,
        "new_draw_ids": added,
        "original_download_provenance_proven": False,
        "operator_binding_protocol_verified": False,
        "dataset_promotion_approved": False,
        "eligible_for_economic_or_predictive_claim": False,
        "research_only_no_play": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two local first-party-style archives offline; does NOT authenticate source"
    )
    parser.add_argument("--previous-source", type=Path, required=True)
    parser.add_argument("--current-source", type=Path, required=True)
    parser.add_argument("--expected-previous-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = compare_snapshots(
            args.previous_source.read_bytes(), args.current_source.read_bytes(),
            expected_previous_sha256=args.expected_previous_sha256,
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2, sort_keys=True, ensure_ascii=False)
            file.write("\n")
    except (OSError, SourceSnapshotError) as exc:
        parser.exit(2, f"Source delta comparison REFUSED: {exc}\n")
    print(json.dumps(report, sort_keys=True))
    if report["status"] == "HISTORICAL_MISSING_OR_CHANGED_STOP_REVIEW":
        parser.exit(2, "Historical revisions detected; do not promote source\n")


if __name__ == "__main__":
    main()
