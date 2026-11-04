"""Fail-closed cross-check of *reported* capture and local delta metadata.

These files are user-computer reports, not operator raw bytes, independently
attested HTTPS sessions, binding draw protocols, source rights, or permission
to promote lottery results. Passing is METADATA ONLY / NO PLAY.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

CAPTURE_PATTERN = re.compile(r"p1-(\d+)-user-windows-https-capture-report-(\d{8})\.json\Z")
DELTA_PATTERN = re.compile(r"p1-(\d+)-local-powershell-byte-continuity-(\d{8})\.json\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
OPERATOR_CSV = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"


class ReportChainError(ValueError):
    """Two untrusted quarantine reports disagree or claim unauthorized approval."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportChainError(message)


def obj(value: Any, context: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{context} must be an object")
    return value


def positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def valid_sha(value: Any) -> bool:
    return type(value) is str and SHA256.fullmatch(value) is not None


def verify_pair(capture: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Cross-check two reported JSON metadata records, never their absent CSV bytes."""
    cap, dlt = obj(capture, "capture"), obj(delta, "delta")
    require(cap.get("schema_version") == dlt.get("schema_version") == 1, "schema mismatch")
    reported_state = cap.get("status")
    match = re.fullmatch(
        r"QUARANTINED_USER_UPLOADED_(\d+)_REPORT_ONLY_NOT_INDEPENDENT_ATTESTATION",
        reported_state if type(reported_state) is str else "",
    )
    require(match is not None, "capture quarantine state not recognized")
    require(dlt.get("status") ==
            "QUARANTINED_LOCAL_POWERSHELL_BYTE_CONTINUITY_REPORT_NOT_PROVENANCE",
            "delta quarantine state not recognized")
    require(cap.get("record_date_israel") == dlt.get("review_date_israel"),
            "review dates disagree")

    http = obj(cap.get("reported_first_party_http"), "HTTP")
    archive = obj(cap.get("reported_original_archive"), "archive")
    predecessor = obj(cap.get("predecessor_comparison_reported"), "predecessor")
    age = obj(cap.get("age_gate_at_reported_capture"), "age")
    handling = obj(cap.get("dataset_handling"), "handling")
    comp = obj(dlt.get("reported_comparison"), "delta comparison")
    scope = obj(dlt.get("validation_scope"), "delta review scope")
    disposition = obj(dlt.get("research_disposition"), "disposition")

    require(http.get("http_status_reported") == 200, "HTTP result not 200")
    require(http.get("requested_url") == http.get("final_url") == OPERATOR_CSV,
            "operator URL mismatch")
    require(http.get("redirect_chain") == [OPERATOR_CSV], "unverified redirect")
    require(http.get("final_url_is_first_party_https_reported") is True,
            "no reported first-party HTTPS")
    require(http.get("tls_certificate_validation_disabled_reported") is False,
            "TLS verification disabled")
    require(http.get("independent_network_attestation") is False,
            "unjustified independent network attestation")
    for value in (
        archive.get("raw_response_sha256_reported"),
        predecessor.get("previous_raw_sha256_reported"),
        comp.get("old_sha256"),
        comp.get("new_sha256"),
    ):
        require(valid_sha(value), "digest is not a lowercase SHA-256")
    require(archive["raw_response_sha256_reported"] == comp["new_sha256"],
            "new-source hash mismatch")
    require(predecessor["previous_raw_sha256_reported"] == comp["old_sha256"],
            "predecessor hash mismatch")
    require(comp["old_sha256"] != comp["new_sha256"], "unchanged digest")

    old_size, new_size, added_size = (
        comp.get("old_bytes"), comp.get("new_bytes"), comp.get("new_row_bytes")
    )
    require(all(positive_int(n) for n in (old_size, new_size, added_size)),
            "invalid source sizes")
    require(new_size - old_size == added_size, "byte difference not one row")
    require(archive.get("raw_response_bytes_reported") == new_size,
            "new archive size mismatch")
    require(predecessor.get("raw_archival_byte_delta_reported_vs_predecessor")
            == added_size, "row size disagrees with capture report")

    start_id, latest_id = (
        archive.get("modern_first_draw_id_reported"),
        archive.get("modern_last_draw_id_reported"),
    )
    previous_id, new_id = (
        predecessor.get("previous_last_draw_id"), comp.get("new_draw_id")
    )
    count = archive.get("modern_draw_count_reported")
    require(all(positive_int(n) for n in
                (start_id, latest_id, previous_id, new_id, count)),
            "invalid draw IDs/count")
    require(new_id == latest_id == previous_id + 1, "draw sequence mismatch")
    require(int(match.group(1)) == latest_id, "quarantine state draw mismatch")
    require(count == latest_id - start_id + 1, "contiguous ID count mismatch")
    require(predecessor.get("compared_prior_modern_rows_reported") == count - 1,
            "prior rows inconsistent")
    require(predecessor.get("historical_differences_reported") == [],
            "historical changes reported")
    require(predecessor.get("only_added_draw_ids_reported") == [new_id],
            "added draw IDs disagree")
    require(comp.get("status") == "ONE_NEW_DRAW_ROW_BYTE_EXACT_MATCH",
            "local comparison not exact match")
    require(comp.get("prior_archive_bytes_unchanged_reported") is True,
            "prior archive not reported unchanged")
    require(comp.get("size_delta_equals_reported_added_row_length") is True,
            "row length assertion missing")
    require(comp.get("prior_and_current_digests_match_user_capture_report_chain")
            is True, "local digest chain assertion missing")

    try:
        latest_date = date.fromisoformat(archive["modern_latest_draw_date_israel_reported"])
        review_date = date.fromisoformat(cap["record_date_israel"])
        captured = datetime.strptime(
            http["captured_at_utc"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, KeyError) as exc:
        raise ReportChainError("invalid draw, review or capture date") from exc
    require(comp.get("reported_new_row_date") == latest_date.isoformat(),
            "new draw date mismatch")
    require(captured.astimezone(ZoneInfo("Asia/Jerusalem")).date() == review_date,
            "capture UTC does not match Israel-local review date")
    observed_age = (review_date - latest_date).days
    require(observed_age >= 0 and
            age.get("israel_local_age_days_reported") == observed_age,
            "source age at capture inconsistent")
    require(age.get("limit_days") == 4 and
            age.get("reported_source_content_recency_ok") is (observed_age <= 4),
            "source age limit/status inconsistent")
    require(age.get("approved_main_dataset_freshness_ok") is False,
            "main incorrectly declared fresh")

    # Source-file review is explicitly negative; sizes must match its key.
    raw_review_keys = [
        key for key in scope if re.fullmatch(
            r"actual_(\d+)_and_(\d+)_raw_csv_bytes_received_or_rehashed_in_this_review",
            key
        )
    ]
    require(len(raw_review_keys) == 1, "missing raw-byte review scope")
    size_match = re.fullmatch(r"actual_(\d+)_and_(\d+)_.*", raw_review_keys[0])
    require(size_match is not None and
            (int(size_match.group(1)), int(size_match.group(2)))
            == (old_size, new_size), "raw-byte scope sizes inconsistent")
    require(scope[raw_review_keys[0]] is False,
            "unjustified raw-byte independent review")

    for mapping, key in (
        (archive, "raw_source_bytes_received_for_this_review"),
        (archive, "raw_source_digest_independently_recomputed"),
        (predecessor, "predecessor_raw_full_archive_byte_reconciliation_completed_in_this_review"),
        (handling, "data_promotion_approved"),
        (handling, "legally_binding_draw_protocol_verified"),
        (handling, "source_rights_and_permission_verified"),
        (handling, "independent_human_source_promotion_approval"),
        (scope, "original_https_server_session_independently_attested"),
        (scope, "verified_operator_binding_draw_protocol"),
        (scope, "source_reuse_rights_verified"),
        (scope, "independent_human_promotion_approval"),
        (disposition, "promotion_to_main_permitted"),
        (disposition, "candidate_data_csv_modified"),
        (disposition, "main_approved_csv_modified"),
    ):
        require(mapping.get(key) is False, f"{key}: quarantine boundary violated")
    require(handling.get("no_dataset_changes") is True, "data-change claim")
    pr_number = handling.get("candidate_pr")
    require(positive_int(pr_number), "candidate PR missing")
    require(disposition.get(f"keep_pr{pr_number}_draft") is True,
            "draft quarantine flag missing")
    require(disposition.get("research_only_no_play") is True,
            "research-only flag missing")

    return {
        "status": "QUARANTINED_METADATA_CHAIN_COHERENT_NOT_SOURCE_ATTESTATION",
        "latest_reported_draw_id": latest_id,
        "latest_reported_date": latest_date.isoformat(),
        "reported_original_sha256": comp["new_sha256"],
        "reported_new_source_bytes": new_size,
        "reported_added_row_bytes": added_size,
        "approved_main_dataset_updated": False,
        "legal_provenance_or_protocol_verified": False,
        "eligible_for_promotion_or_play": False,
    }


def check_directory(directory: Path) -> dict[str, Any]:
    """Pair same-draw/same-day quarantine records; reject partial pairs."""
    require(directory.is_dir(), "audit evidence directory missing")
    matched: dict[tuple[int, str], dict[str, Path]] = {}
    for path in directory.iterdir():
        capture_match = CAPTURE_PATTERN.fullmatch(path.name)
        delta_match = DELTA_PATTERN.fullmatch(path.name)
        match = capture_match or delta_match
        if match is None:
            continue
        require(path.is_file(), "evidence item is not a file")
        key = (int(match.group(1)), match.group(2))
        kind = "capture" if capture_match else "delta"
        matched.setdefault(key, {})[kind] = path

    checked = []
    for (draw_id, ymd), pair in sorted(matched.items()):
        require(set(pair) == {"capture", "delta"},
                f"incomplete quarantine pair for {draw_id} on {ymd}")
        try:
            with pair["capture"].open(encoding="utf-8") as f:
                capture = json.load(f)
            with pair["delta"].open(encoding="utf-8") as f:
                delta = json.load(f)
        except (OSError, ValueError) as exc:
            raise ReportChainError("unreadable quarantine JSON") from exc
        require(isinstance(capture, dict) and isinstance(delta, dict),
                "JSON root must be an object")
        result = verify_pair(capture, delta)
        require(result["latest_reported_draw_id"] == draw_id,
                "filename draw ID mismatch")
        require(capture["record_date_israel"].replace("-", "") == ymd,
                "filename review date mismatch")
        checked.append(result)
    return {
        "status": "METADATA_CHAIN_CHECK_ONLY_NO_SOURCE_ATTESTATION",
        "checked_pairs": checked,
        "pair_count": len(checked),
        "eligible_for_promotion_or_play": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path,
                        default=Path("audit-evidence"))
    args = parser.parse_args()
    try:
        report = check_directory(args.audit_dir)
    except ReportChainError as exc:
        parser.exit(2, f"P1 quarantine metadata check refused: {exc}\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
