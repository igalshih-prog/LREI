"""Synthetic source-report metadata only; never authenticates Lotto draws."""
from __future__ import annotations

import json

import pytest

from lrei.lottery.p1_report_chain_gate import (
    ReportChainError,
    check_directory,
    verify_pair,
)

OLD = "5d3cfe5e69abefddb606d9a0de74b8c76d4350e129bdc7d7780b549b4d70714b"
NEW = "0034509bdfa510c3978abcff14baee705f6bebf85701c7e6978ac07ecc171560"
URL = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"


def examples():
    capture = {
        "schema_version": 1,
        "status": "QUARANTINED_USER_UPLOADED_3981_REPORT_ONLY_NOT_INDEPENDENT_ATTESTATION",
        "record_date_israel": "2026-11-04",
        "reported_first_party_http": {
            "requested_url": URL, "final_url": URL, "redirect_chain": [URL],
            "captured_at_utc": "2026-11-04T15:13:00Z",
            "http_status_reported": 200,
            "final_url_is_first_party_https_reported": True,
            "tls_certificate_validation_disabled_reported": False,
            "independent_network_attestation": False,
        },
        "reported_original_archive": {
            "raw_response_sha256_reported": NEW,
            "raw_response_bytes_reported": 183772,
            "modern_first_draw_id_reported": 2833,
            "modern_last_draw_id_reported": 3981,
            "modern_latest_draw_date_israel_reported": "2026-11-03",
            "modern_draw_count_reported": 1149,
            "raw_source_bytes_received_for_this_review": False,
            "raw_source_digest_independently_recomputed": False,
        },
        "predecessor_comparison_reported": {
            "previous_raw_sha256_reported": OLD,
            "previous_last_draw_id": 3980,
            "compared_prior_modern_rows_reported": 1148,
            "historical_differences_reported": [],
            "only_added_draw_ids_reported": [3981],
            "raw_archival_byte_delta_reported_vs_predecessor": 42,
            "predecessor_raw_full_archive_byte_reconciliation_completed_in_this_review": False,
        },
        "age_gate_at_reported_capture": {
            "israel_local_age_days_reported": 1, "limit_days": 4,
            "reported_source_content_recency_ok": True,
            "approved_main_dataset_freshness_ok": False,
        },
        "dataset_handling": {
            "candidate_pr": 44, "no_dataset_changes": True,
            "data_promotion_approved": False,
            "legally_binding_draw_protocol_verified": False,
            "source_rights_and_permission_verified": False,
            "independent_human_source_promotion_approval": False,
        },
    }
    delta = {
        "schema_version": 1,
        "status": "QUARANTINED_LOCAL_POWERSHELL_BYTE_CONTINUITY_REPORT_NOT_PROVENANCE",
        "review_date_israel": "2026-11-04",
        "reported_comparison": {
            "status": "ONE_NEW_DRAW_ROW_BYTE_EXACT_MATCH",
            "old_sha256": OLD, "new_sha256": NEW,
            "old_bytes": 183730, "new_bytes": 183772, "new_row_bytes": 42,
            "new_draw_id": 3981, "reported_new_row_date": "2026-11-03",
            "prior_archive_bytes_unchanged_reported": True,
            "size_delta_equals_reported_added_row_length": True,
            "prior_and_current_digests_match_user_capture_report_chain": True,
        },
        "validation_scope": {
            "actual_183730_and_183772_raw_csv_bytes_received_or_rehashed_in_this_review": False,
            "original_https_server_session_independently_attested": False,
            "verified_operator_binding_draw_protocol": False,
            "source_reuse_rights_verified": False,
            "independent_human_promotion_approval": False,
        },
        "research_disposition": {
            "keep_pr44_draft": True,
            "candidate_data_csv_modified": False,
            "main_approved_csv_modified": False,
            "promotion_to_main_permitted": False,
            "research_only_no_play": True,
        },
    }
    return capture, delta


def test_valid_metadata_pair_is_explicitly_not_attestation():
    capture, delta = examples()
    report = verify_pair(capture, delta)
    assert report["latest_reported_draw_id"] == 3981
    assert report["reported_added_row_bytes"] == 42
    assert report["eligible_for_promotion_or_play"] is False
    assert report["legal_provenance_or_protocol_verified"] is False


@pytest.mark.parametrize("mutate", [
    lambda c,d: d["reported_comparison"].update(new_sha256="a"*64),
    lambda c,d: c["predecessor_comparison_reported"].update(previous_raw_sha256_reported="a"*64),
    lambda c,d: d["reported_comparison"].update(new_row_bytes=41),
    lambda c,d: c["reported_original_archive"].update(modern_draw_count_reported=1148),
    lambda c,d: c["predecessor_comparison_reported"].update(historical_differences_reported=[3977]),
    lambda c,d: d["reported_comparison"].update(new_draw_id=3982),
    lambda c,d: c["reported_first_party_http"].update(redirect_chain=["https://example.com",URL]),
    lambda c,d: c["reported_first_party_http"].update(tls_certificate_validation_disabled_reported=True),
    lambda c,d: c["reported_first_party_http"].update(independent_network_attestation=True),
    lambda c,d: c["age_gate_at_reported_capture"].update(israel_local_age_days_reported=0),
    lambda c,d: c["age_gate_at_reported_capture"].update(approved_main_dataset_freshness_ok=True),
    lambda c,d: d["validation_scope"].update(verified_operator_binding_draw_protocol=True),
    lambda c,d: d["research_disposition"].update(promotion_to_main_permitted=True),
    lambda c,d: d["research_disposition"].update(keep_pr44_draft=False),
])
def test_false_or_inconsistent_reports_fail_closed(mutate):
    capture, delta = examples()
    mutate(capture, delta)
    with pytest.raises(ReportChainError):
        verify_pair(capture, delta)


def test_directory_pair_and_empty_dir_never_attest(tmp_path):
    assert check_directory(tmp_path)["pair_count"] == 0
    capture, delta = examples()
    (tmp_path/"p1-3981-user-windows-https-capture-report-20261104.json").write_text(
        json.dumps(capture), encoding="utf-8")
    (tmp_path/"p1-3981-local-powershell-byte-continuity-20261104.json").write_text(
        json.dumps(delta), encoding="utf-8")
    result = check_directory(tmp_path)
    assert result["pair_count"] == 1
    assert result["eligible_for_promotion_or_play"] is False


def test_missing_pair_fails_closed(tmp_path):
    capture, _ = examples()
    (tmp_path/"p1-3981-user-windows-https-capture-report-20261104.json").write_text(
        json.dumps(capture), encoding="utf-8")
    with pytest.raises(ReportChainError, match="incomplete"):
        check_directory(tmp_path)


def test_filename_draw_identity_not_self_attestation(tmp_path):
    capture, delta = examples()
    (tmp_path/"p1-3982-user-windows-https-capture-report-20261104.json").write_text(
        json.dumps(capture), encoding="utf-8")
    (tmp_path/"p1-3982-local-powershell-byte-continuity-20261104.json").write_text(
        json.dumps(delta), encoding="utf-8")
    with pytest.raises(ReportChainError, match="filename draw ID"):
        check_directory(tmp_path)
