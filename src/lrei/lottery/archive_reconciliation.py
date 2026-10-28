"""Offline full-window reconciliation of a supplied Pais-style Lotto CSV.

Only content can be established from bytes provided by a user. This verifier
does NOT authenticate the download's origin or a legally approved protocol,
and it cannot establish a prediction made before the draw.
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
from .official_draw_source import MAX_SOURCE_BYTES, OfficialCsvAuditError

EXPECTED_FIELDS = (
    "הגרלה", "תאריך", "1", "2", "3", "4", "5", "6", "המספר החזק/נוסף",
)


def reconcile_uploaded_archive(
    raw: bytes, historical: LotteryDataset, *, reviewed_at_utc: datetime | None = None
) -> dict[str, Any]:
    """Require every rolling-window history row to equal the supplied raw export.

    Older operator rows may obey historic rules (e.g. a 49-number game or a
    differently defined extra number). Validate strict 6/37 + strong 1–7
    only for the current comparison window, not for 1960s material.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise OfficialCsvAuditError("archive source must contain 1–8 MiB of bytes")
    if b"\x00" in raw or raw[:128].lstrip().lower().startswith((b"<html", b"<!doctype html")):
        raise OfficialCsvAuditError("archive source is HTML or binary, not CSV")
    try:
        if raw.startswith(b"\xef\xbb\xbf"):
            decoded = raw.decode("utf-8-sig", errors="strict")
            encoding = "utf-8-sig"
        else:
            decoded = raw.decode("cp1255", errors="strict")
            encoding = "cp1255"
    except UnicodeDecodeError as exc:
        raise OfficialCsvAuditError("unsupported archive text encoding") from exc

    historical_rows = list(historical)
    if not historical_rows:
        raise OfficialCsvAuditError("local historical dataset is empty")
    expected: dict[int, tuple[str, tuple[int, ...], int]] = {}
    previous_date = None
    for draw in historical_rows:
        if not str(draw.draw_id).isdigit():
            raise OfficialCsvAuditError("local history has nonnumeric draw ID")
        draw_id = int(draw.draw_id)
        date = parse_draw_date(draw.date)
        if date is None:
            raise OfficialCsvAuditError(f"local draw {draw_id} has invalid date")
        numbers = tuple(sorted(draw.numbers))
        if (
            len(numbers) != 6 or len(set(numbers)) != 6
            or any(not 1 <= number <= 37 for number in numbers)
            or type(draw.strong_number) is not int
            or not 1 <= draw.strong_number <= 7
        ):
            raise OfficialCsvAuditError(f"local draw {draw_id} violates current Lotto rules")
        if expected and (draw_id != next(reversed(expected)) + 1 or date < previous_date):
            raise OfficialCsvAuditError("local history has an ID gap or nonchronological dates")
        expected[draw_id] = (date.isoformat(), numbers, draw.strong_number)
        previous_date = date

    first_id, last_id = next(iter(expected)), next(reversed(expected))
    observed: dict[int, tuple[str, tuple[int, ...], int]] = {}
    # Historic draw numbers in the 1960s can be numerically larger than
    # current IDs, so date must ALSO be current before declaring a later draw.
    newer_source_ids: set[int] = set()
    source_records = 0
    try:
        reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
        header = next(reader)
        if tuple(field.strip() for field in header[:9]) != EXPECTED_FIELDS:
            raise OfficialCsvAuditError("operator archive header does not match expected 9 fields")
        for line_no, row in enumerate(reader, start=2):
            if not row or not any(value.strip() for value in row):
                continue
            source_records += 1
            if len(row) < 9 or not re.fullmatch(r"[0-9]+", row[0].strip()):
                raise OfficialCsvAuditError(f"archive line {line_no}: invalid ID or column count")
            draw_id = int(row[0].strip())
            if draw_id not in expected:
                if draw_id > last_id:
                    try:
                        outside_date = datetime.strptime(
                            row[1].strip(), "%d/%m/%Y"
                        ).date()
                    except ValueError as exc:
                        raise OfficialCsvAuditError(
                            f"archive line {line_no}: invalid date for higher draw ID"
                        ) from exc
                    if outside_date >= previous_date:
                        newer_source_ids.add(draw_id)
                continue
            if draw_id in observed:
                raise OfficialCsvAuditError(f"duplicate draw {draw_id} in supplied archive")
            try:
                date = datetime.strptime(row[1].strip(), "%d/%m/%Y").date()
                mains = tuple(sorted(int(value.strip()) for value in row[2:8]))
                strong = int(row[8].strip())
            except ValueError as exc:
                raise OfficialCsvAuditError(f"archive draw {draw_id}: invalid values") from exc
            if (
                len(set(mains)) != 6
                or any(not 1 <= number <= 37 for number in mains)
                or not 1 <= strong <= 7
            ):
                raise OfficialCsvAuditError(f"archive draw {draw_id}: invalid 6/37 + strong result")
            actual = (date.isoformat(), mains, strong)
            if actual != expected[draw_id]:
                raise OfficialCsvAuditError(f"archive draw {draw_id} differs from local history")
            observed[draw_id] = actual
    except (csv.Error, StopIteration) as exc:
        raise OfficialCsvAuditError("malformed or empty operator-style archive") from exc

    missing = sorted(set(expected) - set(observed))
    if missing:
        raise OfficialCsvAuditError(
            f"supplied archive lacks {len(missing)} expected draws; first missing: {missing[0]}"
        )
    reviewed = reviewed_at_utc or datetime.now(timezone.utc)
    if reviewed.tzinfo is None or reviewed.utcoffset() is None:
        raise OfficialCsvAuditError("reviewed_at_utc must be timezone-aware")
    reviewed = reviewed.astimezone(timezone.utc)
    if reviewed.date() < previous_date:
        raise OfficialCsvAuditError("audit cannot predate the latest draw")
    return {
        "schema_version": 1,
        "status": "complete_window_content_match_origin_unverified",
        "source_encoding": encoding,
        "raw_source_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_source_bytes": len(raw),
        "source_record_count": source_records,
        "source_newer_draw_count": len(newer_source_ids),
        "source_latest_newer_draw_id": (
            max(newer_source_ids) if newer_source_ids else None
        ),
        "window_first_draw_id": first_id,
        "window_last_draw_id": last_id,
        "window_draw_count": len(expected),
        "compared_draw_count": len(observed),
        "mismatched_or_missing_draw_count": 0,
        "reviewed_at_utc": reviewed.isoformat().replace("+00:00", "Z"),
        "download_origin_independently_verified": False,
        "operator_protocol_legally_verified": False,
        "counts_as_prospective_model_evidence": False,
        "eligible_for_expected_value_claim": False,
        "requires_human_source_review": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile all locally stored draw IDs against a supplied archive CSV."
    )
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--historical-csv", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = args.source_file.read_bytes()
        history = CsvDatasetLoader().load(args.historical_csv)
        report = reconcile_uploaded_archive(raw, history)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
    except (OSError, OfficialCsvAuditError, ValueError) as exc:
        parser.exit(2, f"Offline archive reconciliation rejected: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
