"""Fail-closed, offline comparison of successive user-supplied Lotto archives.

Preserves *all* columns, including extra winners fields. A byte digest
proves only local file identity, NEVER its first-party download origin.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any

from .official_draw_source import MAX_SOURCE_BYTES, OfficialCsvAuditError


def _read_archive(raw: bytes) -> tuple[list[str], dict[int, tuple[str, ...]]]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise OfficialCsvAuditError("CSV must have 1 to 8 MiB of bytes")
    if b"\x00" in raw or raw[:128].lstrip().lower().startswith(
        (b"<html", b"<!doctype html")
    ):
        raise OfficialCsvAuditError("HTML or binary data is not an archive")
    try:
        decoded = (
            raw.decode("utf-8-sig", errors="strict")
            if raw.startswith(b"\xef\xbb\xbf")
            else raw.decode("cp1255", errors="strict")
        )
        reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
        header = next(reader)
        if len(header) < 9 or tuple(x.strip() for x in header[:9]) != (
            "הגרלה", "תאריך", "1", "2", "3", "4", "5", "6", "המספר החזק/נוסף"
        ):
            raise OfficialCsvAuditError("unexpected archive header")
        rows: dict[int, tuple[str, ...]] = {}
        for lineno, row in enumerate(reader, 2):
            if not row or not any(x.strip() for x in row):
                continue
            if len(row) != len(header) or not re.fullmatch(r"[0-9]+", row[0].strip()):
                raise OfficialCsvAuditError(f"row {lineno}: malformed ID or columns")
            draw_id = int(row[0])
            if draw_id in rows:
                raise OfficialCsvAuditError(f"duplicate source draw ID {draw_id}")
            rows[draw_id] = tuple(row)
    except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
        raise OfficialCsvAuditError("empty, corrupt or wrongly encoded CSV") from exc
    if not rows:
        raise OfficialCsvAuditError("empty archive")
    return header, rows


def compare_archive_updates(old: bytes, new: bytes) -> dict[str, Any]:
    """Require exact preservation of all previously supplied raw CSV records.

    This comparison validates only file-to-file continuity, not historical
    winning numbers, official host authenticity, payout accuracy, or permission
    to promote a new file into the live dataset.
    """
    old_header, old_rows = _read_archive(old)
    new_header, new_rows = _read_archive(new)
    if old_header != new_header:
        raise OfficialCsvAuditError("source headers or extra columns changed")
    old_ids, new_ids = set(old_rows), set(new_rows)
    missing = sorted(old_ids - new_ids)
    if missing:
        raise OfficialCsvAuditError(f"new archive deleted draw ID {missing[0]}")
    changed = sorted(i for i in old_ids if old_rows[i] != new_rows[i])
    if changed:
        raise OfficialCsvAuditError(
            f"previously supplied draw {changed[0]} changed in at least one column"
        )
    added = sorted(new_ids - old_ids)
    if any(i <= max(old_ids) for i in added):
        raise OfficialCsvAuditError("new archive backfilled an earlier draw ID")
    if added and added != list(range(max(old_ids) + 1, added[-1] + 1)):
        raise OfficialCsvAuditError("new archive has a gap in newly added draw IDs")
    return {
        "schema_version": 1,
        "status": "old_archive_rows_preserved_origin_unverified",
        "old_raw_sha256": hashlib.sha256(old).hexdigest(),
        "new_raw_sha256": hashlib.sha256(new).hexdigest(),
        "old_raw_bytes": len(old),
        "new_raw_bytes": len(new),
        "old_draw_count": len(old_rows),
        "new_draw_count": len(new_rows),
        "exact_common_rows": len(old_rows),
        "missing_old_rows": 0,
        "changed_common_rows_all_columns": 0,
        "new_draw_ids": added,
        "download_origin_independently_verified": False,
        "operator_protocol_legally_verified": False,
        "eligible_for_dataset_promotion": False,
        "eligible_for_predictive_or_economic_claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-source", type=Path, required=True)
    parser.add_argument("--new-source", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = compare_archive_updates(
            args.old_source.read_bytes(), args.new_source.read_bytes()
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as output:
            json.dump(report, output, ensure_ascii=False, sort_keys=True, indent=2)
            output.write("\n")
    except (OSError, OfficialCsvAuditError) as exc:
        parser.exit(2, f"Offline archive delta refused: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
