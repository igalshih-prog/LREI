"""One first-party HTTPS fetch and ALL-row Lotto CSV content reconciliation.

The download's original bytes are kept only in-process; the report records
their SHA-256 and first-party URL. This is not the legally binding committee
protocol, does not certify ownership of previously supplied files, and never
changes the candidate historical dataset.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .archive_reconciliation import reconcile_uploaded_archive
from .dataset import CsvDatasetLoader, DatasetError, LotteryDataset
from .official_draw_source import (
    OfficialCsvAuditError,
    _safe_official_url,
    download_operator_csv,
)


def capture_full_window(
    historical: LotteryDataset,
    *,
    captured_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Download ONCE and verify every candidate draw against those same bytes.

    Caller cannot pass arbitrary local bytes and call them a network capture:
    the fetch is performed by download_operator_csv within this function.
    """
    if (
        captured_at_utc is not None
        and (captured_at_utc.tzinfo is None or captured_at_utc.utcoffset() is None)
    ):
        raise OfficialCsvAuditError("capture timestamp requires a UTC offset")
    raw, final_url, mime = download_operator_csv()
    # Capture AFTER the response has been received (no guessed pre-request time).
    captured = captured_at_utc or datetime.now(timezone.utc)
    _safe_official_url(final_url)
    compared = reconcile_uploaded_archive(
        raw, historical, reviewed_at_utc=captured,
    )
    if (
        compared["mismatched_or_missing_draw_count"] != 0
        or compared["compared_draw_count"] != compared["window_draw_count"]
    ):
        raise OfficialCsvAuditError("candidate archive did not match entire source window")
    return {
        "schema_version": 1,
        "status": "first_party_https_full_window_match_HUMAN_REVIEW_REQUIRED",
        "source_host": "pais.co.il",
        "final_operator_url": final_url,
        "response_content_type": mime,
        "download_performed_by_tool_over_tls": True,
        "raw_operator_response_sha256": compared["raw_source_sha256"],
        "raw_operator_response_bytes": compared["raw_source_bytes"],
        "capture_at_utc": captured.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "window_first_draw_id": compared["window_first_draw_id"],
        "window_last_draw_id": compared["window_last_draw_id"],
        "source_record_count": compared["source_record_count"],
        "window_draw_count": compared["window_draw_count"],
        "compared_draw_count": compared["compared_draw_count"],
        "mismatched_or_missing_draw_count": 0,
        "candidate_history_verified_against_this_response": True,
        "original_response_bytes_published": False,
        "historical_download_provenance_of_user_upload_proven": False,
        "legally_binding_commission_protocol_verified": False,
        "dataset_promotion_approved": False,
        "full_prize_tier_payouts_verified": False,
        "eligible_for_economic_or_predictive_advantage_claim": False,
        "requires_human_review": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-csv", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        historical = CsvDatasetLoader().load(args.historical_csv)
        report = capture_full_window(historical)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
    except (OSError, ValueError, OfficialCsvAuditError, DatasetError) as exc:
        parser.exit(2, f"First-party full-window capture refused: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
