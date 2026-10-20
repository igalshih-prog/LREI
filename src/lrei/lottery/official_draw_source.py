"""Cross-check a local Lotto CSV row against the operator's archive export.

This is an offline verifier by default. An opt-in direct HTTPS download saves
the exact response bytes and their SHA-256. Neither mode authenticates a
commission-approved draw protocol or validates monetary prize tables.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .dataset import CsvDatasetLoader, LotteryDataset, parse_draw_date

OFFICIAL_CSV_URL = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"
OFFICIAL_HOSTS = frozenset({"www.pais.co.il", "pais.co.il"})
MAX_SOURCE_BYTES = 8 * 1024 * 1024


class OfficialCsvAuditError(ValueError):
    """Invalid operator export or mismatch against the local candidate row."""


def _safe_official_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in OFFICIAL_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise OfficialCsvAuditError("source must use a first-party HTTPS Pais host")


def download_operator_csv(url: str = OFFICIAL_CSV_URL) -> tuple[bytes, str, str]:
    """Make one TLS-verified first-party request; never turn off SSL verification."""
    _safe_official_url(url)
    request = urllib.request.Request(
        url, headers={"User-Agent": "LREI-source-audit/1.0"}
    )
    try:
        with urllib.request.urlopen(
            request, timeout=25, context=ssl.create_default_context()
        ) as response:
            final_url = response.geturl()
            _safe_official_url(final_url)
            raw = response.read(MAX_SOURCE_BYTES + 1)
            mime = response.headers.get("Content-Type", "unknown")
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise OfficialCsvAuditError(f"first-party CSV download unavailable: {exc}") from exc
    if not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise OfficialCsvAuditError("download was empty or exceeded the 8 MiB cap")
    return raw, final_url, mime


def inspect_official_csv(
    raw: bytes,
    historical: LotteryDataset,
    *,
    expected_draw_id: int,
    source_url: str = OFFICIAL_CSV_URL,
    direct_https_download: bool = False,
    captured_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Compare an exact operator-style CSV row with the local history cutoff.

    For offline files, the checksum proves file integrity but not its origin.
    Callers cannot self-attest a network capture by supplying a boolean. Only
    the download CLI can set the HTTPS capture flag after its own live fetch.
    """
    if direct_https_download:
        raise OfficialCsvAuditError(
            "offline inspector cannot attest a direct HTTPS download; "
            "use the trusted --download capture path"
        )
    _safe_official_url(source_url)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise OfficialCsvAuditError("source file must contain 1–8 MiB of bytes")
    if b"\x00" in raw or raw[:128].lstrip().lower().startswith(
        (b"<!doctype html", b"<html")
    ):
        raise OfficialCsvAuditError("received HTML or binary content instead of CSV")
    if not historical:
        raise OfficialCsvAuditError("historical comparison dataset is empty")
    if type(expected_draw_id) is not int or expected_draw_id <= 0:
        raise OfficialCsvAuditError("expected draw ID must be a positive integer")

    # The official archive export is traditionally Windows-1255; allow UTF-8
    # exports too, without guessing formats outside those two explicit cases.
    try:
        if raw.startswith(b"\xef\xbb\xbf"):
            decoded = raw.decode("utf-8-sig", errors="strict")
            encoding = "utf-8-sig"
        else:
            decoded = raw.decode("cp1255", errors="strict")
            encoding = "cp1255"
    except UnicodeDecodeError as exc:
        raise OfficialCsvAuditError("source CSV has an unsupported text encoding") from exc

    reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
    try:
        header = next(reader)
        if len(header) < 9 or header[0].strip().isdigit():
            raise OfficialCsvAuditError("source CSV header has an unexpected shape")
        candidates: list[tuple[str, tuple[int, ...], int]] = []
        for row_number, row in enumerate(reader, 2):
            if not row or all(not field.strip() for field in row):
                continue
            if len(row) < 9:
                raise OfficialCsvAuditError(
                    f"row {row_number}: expected ID, date, six mains and strong"
                )
            draw_id = row[0].strip()
            if not re.fullmatch(r"[0-9]+", draw_id):
                raise OfficialCsvAuditError(f"row {row_number}: invalid draw ID")
            if int(draw_id) != expected_draw_id:
                continue
            raw_date = row[1].strip()
            try:
                actual_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
                mains = tuple(int(v.strip()) for v in row[2:8])
                strong = int(row[8].strip())
            except ValueError as exc:
                raise OfficialCsvAuditError(
                    f"row {row_number}: invalid date or numbers"
                ) from exc
            if (
                len(set(mains)) != 6
                or any(not 1 <= n <= 37 for n in mains)
                or not 1 <= strong <= 7
            ):
                raise OfficialCsvAuditError(f"row {row_number}: invalid Lotto result")
            candidates.append((actual_date.isoformat(), tuple(sorted(mains)), strong))
    except (csv.Error, StopIteration) as exc:
        raise OfficialCsvAuditError("source CSV is empty or malformed") from exc

    if len(candidates) != 1:
        raise OfficialCsvAuditError(
            f"expected exactly one operator CSV row for draw {expected_draw_id}, got {len(candidates)}"
        )

    latest = historical.latest()
    if not str(latest.draw_id).isdecimal() or int(latest.draw_id) != expected_draw_id:
        raise OfficialCsvAuditError("dataset latest draw differs from audit target")
    date = parse_draw_date(latest.date)
    if date is None:
        raise OfficialCsvAuditError("local draw date is invalid")
    local_values = (
        date.isoformat(), tuple(sorted(latest.numbers)), latest.strong_number
    )
    if candidates[0] != local_values:
        raise OfficialCsvAuditError("operator CSV row disagrees with local data")

    captured = captured_at_utc or datetime.now(timezone.utc)
    if captured.tzinfo is None or captured.utcoffset() is None:
        raise OfficialCsvAuditError("capture time must include a timezone")
    captured = captured.astimezone(timezone.utc)
    if captured.date() < date:
        raise OfficialCsvAuditError("source capture cannot predate the draw")
    return {
        "schema_version": 1,
        "status": "candidate_operator_csv_row_matches_local_dataset",
        "draw_id": expected_draw_id,
        "draw_date": date.isoformat(),
        "main": list(local_values[1]),
        "strong": local_values[2],
        "source_url": source_url,
        "source_encoding": encoding,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_bytes": len(raw),
        "captured_at_utc": captured.isoformat().replace("+00:00", "Z"),
        "direct_https_download_performed_by_tool": direct_https_download,
        "source_host_uses_operator_domain": True,
        "verified_against_local_candidate": True,
        "legally_binding_protocol_verified": False,
        "human_source_review_required": True,
        "eligible_for_expected_value_claim": False,
        "counted_as_prospective_prediction": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-file", type=Path)
    source.add_argument("--download", action="store_true")
    parser.add_argument("--historical-csv", type=Path, required=True)
    parser.add_argument("--draw-id", type=int, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--raw-copy", type=Path)
    args = parser.parse_args()
    try:
        if args.download:
            raw, url, mime = download_operator_csv()
        else:
            raw = args.source_file.read_bytes()
            url, mime = OFFICIAL_CSV_URL, "locally-supplied"
        historical = CsvDatasetLoader().load(args.historical_csv)
        report = inspect_official_csv(
            raw, historical, expected_draw_id=args.draw_id,
            source_url=url,
        )
        # Set this attestation only inside the CLI after the actual live
        # download completed. The reusable offline inspector always returns
        # False and refuses caller-supplied True.
        report["direct_https_download_performed_by_tool"] = bool(args.download)
        report["http_content_type_or_local"] = mime
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as target:
            json.dump(report, target, indent=2, ensure_ascii=False, sort_keys=True)
            target.write("\n")
        if args.raw_copy is not None:
            args.raw_copy.parent.mkdir(parents=True, exist_ok=True)
            with args.raw_copy.open("xb") as target:
                target.write(raw)
    except (OSError, OfficialCsvAuditError, ValueError) as exc:
        parser.exit(2, f"Official CSV audit unavailable or rejected: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
