"""Source-capture regression tests with synthetic bytes and zero network access."""

from datetime import datetime, timezone
import json

import pytest

from lrei.lottery.dataset import LotteryDataset, LotteryDrawRecord
from lrei.lottery.official_draw_source import OfficialCsvAuditError
from lrei.lottery import operator_full_window_capture as module

AT = datetime(2026, 1, 6, 12, tzinfo=timezone.utc)
SOURCE_URL = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"

HEADER = "הגרלה,תאריך,1,2,3,4,5,6,המספר החזק/נוסף"
ROWS = [
    "8000,01/01/2026,1,4,7,10,13,16,1",
    "8001,03/01/2026,2,5,8,11,14,17,2",
    "8002,05/01/2026,3,6,9,12,15,18,3",
]


def history():
    return LotteryDataset([
        LotteryDrawRecord("8000", (1, 4, 7, 10, 13, 16), "01-01-26", 1),
        LotteryDrawRecord("8001", (2, 5, 8, 11, 14, 17), "03-01-26", 2),
        LotteryDrawRecord("8002", (3, 6, 9, 12, 15, 18), "05-01-26", 3),
    ])


def raw(rows=ROWS):
    return (HEADER + "\n" + "\n".join(rows) + "\n").encode("cp1255")


def fake_capture(monkeypatch, bytes_=None, final_url=SOURCE_URL):
    calls = []

    def fake_download():
        calls.append(True)
        return (raw() if bytes_ is None else bytes_, final_url, "text/csv")

    monkeypatch.setattr(module, "download_operator_csv", fake_download)
    return calls


def test_one_tls_operator_capture_completes_all_rows_but_does_not_approve_release(monkeypatch):
    calls = fake_capture(monkeypatch)
    report = module.capture_full_window(history(), captured_at_utc=AT)
    assert len(calls) == 1
    assert report["source_record_count"] == 3
    assert report["window_first_draw_id"] == 8000
    assert report["window_last_draw_id"] == 8002
    assert report["window_draw_count"] == report["compared_draw_count"] == 3
    assert report["mismatched_or_missing_draw_count"] == 0
    assert report["download_performed_by_tool_over_tls"] is True
    assert report["original_response_bytes_published"] is False
    assert report["candidate_history_verified_against_this_response"] is True
    assert report["historical_download_provenance_of_user_upload_proven"] is False
    assert report["legally_binding_commission_protocol_verified"] is False
    assert report["dataset_promotion_approved"] is False
    assert report["full_prize_tier_payouts_verified"] is False
    assert report["eligible_for_economic_or_predictive_advantage_claim"] is False
    assert report["raw_operator_response_bytes"] == len(raw())
    import hashlib
    assert report["raw_operator_response_sha256"] == hashlib.sha256(raw()).hexdigest()


@pytest.mark.parametrize("altered,reason", [
    ([ROWS[0], ROWS[1], ROWS[2].replace(",18,3", ",19,3")], "differs"),
    ([ROWS[0], ROWS[2]], "lacks"),
    ([ROWS[0], ROWS[1], ROWS[1], ROWS[2]], "duplicate"),
])
def test_never_accepts_a_partial_conflicting_or_duplicate_window(monkeypatch, altered, reason):
    fake_capture(monkeypatch, raw(altered))
    with pytest.raises(OfficialCsvAuditError, match=reason):
        module.capture_full_window(history(), captured_at_utc=AT)


def test_network_redirect_outside_operator_domain_rejected(monkeypatch):
    fake_capture(monkeypatch, final_url="https://pais.co.il.attacker.invalid/bad.csv")
    with pytest.raises(OfficialCsvAuditError, match="first-party"):
        module.capture_full_window(history(), captured_at_utc=AT)


def test_a_web_page_is_not_accepted_as_csv(monkeypatch):
    fake_capture(monkeypatch, b"<html>blocked</html>")
    with pytest.raises(OfficialCsvAuditError, match="HTML"):
        module.capture_full_window(history(), captured_at_utc=AT)


def test_network_timeout_never_falls_back_to_fabricated_data(monkeypatch):
    calls = []

    def denied():
        calls.append(1)
        raise OfficialCsvAuditError("first-party CSV download unavailable: timed out")

    monkeypatch.setattr(module, "download_operator_csv", denied)
    with pytest.raises(OfficialCsvAuditError, match="unavailable"):
        module.capture_full_window(history(), captured_at_utc=AT)
    assert len(calls) == 1


def test_naive_clock_rejected_before_any_network_traffic(monkeypatch):
    calls = fake_capture(monkeypatch)
    with pytest.raises(OfficialCsvAuditError, match="UTC offset"):
        module.capture_full_window(
            history(), captured_at_utc=datetime(2026, 1, 6, 12)
        )
    assert calls == []


def test_cli_writes_single_audit_and_will_not_replace_an_existing_report(
    tmp_path, monkeypatch
):
    calls = fake_capture(monkeypatch)
    csv_file = tmp_path / "candidate.csv"
    csv_file.write_text(
        "draw_id\tnumbers\tdate\tstrong_number\n"
        "8000\t1,4,7,10,13,16\t01-01-26\t1\n"
        "8001\t2,5,8,11,14,17\t03-01-26\t2\n"
        "8002\t3,6,9,12,15,18\t05-01-26\t3\n",
        encoding="utf-8",
    )
    out = tmp_path / "reports" / "first-party.json"
    monkeypatch.setattr(
        "sys.argv", [
            "operator_full_window_capture",
            "--historical-csv", str(csv_file),
            "--report", str(out),
        ],
    )
    module.main()
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["compared_draw_count"] == 3
    assert result["dataset_promotion_approved"] is False
    assert len(calls) == 1
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    assert len(calls) == 2
    assert json.loads(out.read_text(encoding="utf-8")) == result


def test_cli_timeout_writes_only_non_attesting_failure_artifact(tmp_path, monkeypatch):
    csv_file = tmp_path / "candidate.csv"
    csv_file.write_text(
        "draw_id\tnumbers\tdate\tstrong_number\n"
        "8000\t1,4,7,10,13,16\t01-01-26\t1\n"
        "8001\t2,5,8,11,14,17\t03-01-26\t2\n"
        "8002\t3,6,9,12,15,18\t05-01-26\t3\n",
        encoding="utf-8",
    )
    success = tmp_path / "audit" / "success.json"
    failure = tmp_path / "audit" / "failure.json"

    def timed_out():
        raise OfficialCsvAuditError("first-party CSV download unavailable: <urlopen error timed out>")

    monkeypatch.setattr(module, "download_operator_csv", timed_out)
    monkeypatch.setattr(
        "sys.argv",
        ["operator_full_window_capture", "--historical-csv", str(csv_file),
         "--report", str(success), "--failure-report", str(failure)],
    )
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    assert not success.exists()
    report = json.loads(failure.read_text(encoding="utf-8"))
    assert report["status"] == "capture_refused_NO_SOURCE_ATTESTATION"
    assert report["failure_stage"] == "operator_capture_and_compare"
    assert report["failure_code"] == "first_party_download_timeout"
    assert report["successful_full_window_match_verified"] is False
    assert report["source_provenance_verified"] is False
    assert report["dataset_promotion_approved"] is False
    assert "raw_operator_response_sha256" not in report
    original = failure.read_bytes()
    with pytest.raises(SystemExit) as again:
        module.main()
    assert again.value.code == 2
    assert failure.read_bytes() == original


def test_mismatch_failure_artifact_never_claims_verified_source(tmp_path, monkeypatch):
    csv_file = tmp_path / "candidate.csv"
    csv_file.write_text(
        "draw_id\tnumbers\tdate\tstrong_number\n"
        "8000\t1,4,7,10,13,16\t01-01-26\t1\n"
        "8001\t2,5,8,11,14,17\t03-01-26\t2\n"
        "8002\t3,6,9,12,15,18\t05-01-26\t3\n",
        encoding="utf-8",
    )
    fake_capture(monkeypatch, raw([ROWS[0], ROWS[2]]))
    good = tmp_path / "success.json"
    refused = tmp_path / "failure.json"
    monkeypatch.setattr(
        "sys.argv",
        ["operator_full_window_capture", "--historical-csv", str(csv_file),
         "--report", str(good), "--failure-report", str(refused)],
    )
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    assert not good.exists()
    result = json.loads(refused.read_text(encoding="utf-8"))
    assert result["failure_code"] == "full_window_capture_rejected"
    assert result["source_provenance_verified"] is False
    assert result["dataset_promotion_approved"] is False


def local_candidate_csv(tmp_path):
    path = tmp_path / "candidate.csv"
    path.write_text(
        "draw_id\tnumbers\tdate\tstrong_number\n"
        "8000\t1,4,7,10,13,16\t01-01-26\t1\n"
        "8001\t2,5,8,11,14,17\t03-01-26\t2\n"
        "8002\t3,6,9,12,15,18\t05-01-26\t3\n",
        encoding="utf-8",
    )
    return path


def test_pinned_candidate_uses_exact_file_bytes_and_retains_no_approval(tmp_path, monkeypatch):
    import hashlib
    candidate = local_candidate_csv(tmp_path)
    expected = hashlib.sha256(candidate.read_bytes()).hexdigest()
    calls = fake_capture(monkeypatch)
    report = module.capture_pinned_candidate(candidate, expected_sha256=expected)
    assert len(calls) == 1
    assert report["candidate_snapshot_sha256"] == expected
    assert report["candidate_snapshot_bytes"] == len(candidate.read_bytes())
    assert report["candidate_snapshot_pinned_for_comparison"] is True
    assert report["dataset_promotion_approved"] is False
    assert report["historical_download_provenance_of_user_upload_proven"] is False


def test_pinned_candidate_wrong_sha_refused_before_network(tmp_path, monkeypatch):
    candidate = local_candidate_csv(tmp_path)
    calls = fake_capture(monkeypatch)
    with pytest.raises(OfficialCsvAuditError, match="differs from expected"):
        module.capture_pinned_candidate(candidate, expected_sha256="0" * 64)
    assert calls == []



@pytest.mark.parametrize("bad_digest", [
    "",
    "ABCDEF" + "0" * 58,
    "0" * 63,
    "0" * 65,
    "g" * 64,
])
def test_pinned_candidate_rejects_malformed_digest_before_network(
    tmp_path, monkeypatch, bad_digest
):
    candidate = local_candidate_csv(tmp_path)
    calls = fake_capture(monkeypatch)
    with pytest.raises(OfficialCsvAuditError, match="64 lowercase hex"):
        module.capture_pinned_candidate(candidate, expected_sha256=bad_digest)
    assert calls == []


def test_pinned_candidate_changes_during_network_capture_refused(tmp_path, monkeypatch):
    import hashlib
    candidate = local_candidate_csv(tmp_path)
    expected = hashlib.sha256(candidate.read_bytes()).hexdigest()
    calls = []

    def change_source_file_mid_capture():
        calls.append(True)
        candidate.write_text("replaced locally while network request ran\n", encoding="utf-8")
        return raw(), SOURCE_URL, "text/csv"

    monkeypatch.setattr(module, "download_operator_csv", change_source_file_mid_capture)
    with pytest.raises(OfficialCsvAuditError, match="changed during operator source capture"):
        module.capture_pinned_candidate(candidate, expected_sha256=expected)
    assert len(calls) == 1


def test_pinned_cli_does_not_emit_success_if_candidate_modified_mid_capture(
    tmp_path, monkeypatch
):
    import hashlib
    candidate = local_candidate_csv(tmp_path)
    expected = hashlib.sha256(candidate.read_bytes()).hexdigest()

    def change_candidate():
        candidate.write_text("replaced while fetching\n", encoding="utf-8")
        return raw(), SOURCE_URL, "text/csv"

    monkeypatch.setattr(module, "download_operator_csv", change_candidate)
    success = tmp_path / "success.json"
    failure = tmp_path / "failure.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "operator_full_window_capture",
            "--historical-csv", str(candidate),
            "--report", str(success),
            "--failure-report", str(failure),
            "--expected-candidate-sha256", expected,
        ],
    )
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    assert not success.exists()
    rejected = json.loads(failure.read_text(encoding="utf-8"))
    assert rejected["status"] == "capture_refused_NO_SOURCE_ATTESTATION"
    assert rejected["failure_code"] == "candidate_changed_during_capture"
    assert rejected["source_provenance_verified"] is False
    assert rejected["dataset_promotion_approved"] is False



def test_pinned_capture_refuses_oversize_sparse_candidate_before_network(
    tmp_path, monkeypatch
):
    candidate = tmp_path / "oversize.csv"
    with candidate.open("wb") as stream:
        stream.truncate(8 * 1024 * 1024 + 1)
    calls = fake_capture(monkeypatch)
    with pytest.raises(OfficialCsvAuditError, match="1–8 MiB"):
        module.capture_pinned_candidate(candidate, expected_sha256="0" * 64)
    assert calls == []
