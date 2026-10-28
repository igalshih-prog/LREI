"""Synthetic cases only: passing tests do not authenticate external archives."""

from datetime import datetime, timezone
import hashlib

import pytest

from lrei.lottery.archive_reconciliation import reconcile_uploaded_archive
from lrei.lottery.dataset import LotteryDataset, LotteryDrawRecord
from lrei.lottery.official_draw_source import OfficialCsvAuditError


def _historical():
    return LotteryDataset([
        LotteryDrawRecord("3972", (2, 4, 6, 13, 18, 25), "06-10-26", 6),
        LotteryDrawRecord("3973", (1, 4, 7, 22, 32, 34), "10-10-26", 2),
        LotteryDrawRecord("3974", (3, 4, 18, 19, 34, 35), "13-10-26", 2),
    ])


HEAD = (
    "הגרלה,תאריך,1,2,3,4,5,6,המספר החזק/נוסף,"
    "מספר_זוכים_לוטו,מספר_זוכים_דאבל_לוטו,\n"
)
ROW_3972 = "3972,06/10/2026,02,04,06,13,18,25,6,0,0,\n"
ROW_3973 = "3973,10/10/2026,01,04,07,22,32,34,2,0,0,\n"
ROW_3974 = "3974,13/10/2026,03,04,18,19,34,35,2,0,0,\n"
# A historical 1968 record can legally use an older game definition.
OLD_ROW = "6801,03/09/1968,3,14,18,22,25,33,42,,,\n"


def _raw(rows=None):
    rows = [ROW_3974, ROW_3973, ROW_3972, OLD_ROW] if rows is None else rows
    return (HEAD + "".join(rows)).encode("cp1255")


def _audit(raw=None, history=None):
    return reconcile_uploaded_archive(
        _raw() if raw is None else raw,
        _historical() if history is None else history,
        reviewed_at_utc=datetime(2026, 10, 15, 18, tzinfo=timezone.utc),
    )


def test_full_window_reconciles_without_attributing_source_origin():
    raw = _raw()
    report = _audit(raw)
    assert report["source_record_count"] == 4
    assert report["source_newer_draw_count"] == 0
    assert report["source_latest_newer_draw_id"] is None
    assert report["window_first_draw_id"] == 3972
    assert report["window_last_draw_id"] == 3974
    assert report["window_draw_count"] == 3
    assert report["compared_draw_count"] == 3
    assert report["mismatched_or_missing_draw_count"] == 0
    assert report["raw_source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["source_encoding"] == "cp1255"
    assert report["download_origin_independently_verified"] is False
    assert report["operator_protocol_legally_verified"] is False
    assert report["counts_as_prospective_model_evidence"] is False
    assert report["eligible_for_expected_value_claim"] is False


@pytest.mark.parametrize("wrong, message", [
    (ROW_3974.replace("34,35", "34,36"), "differs"),
    (ROW_3974.replace(",2,0,0,", ",3,0,0,"), "differs"),
    (ROW_3974.replace("13/10/2026", "14/10/2026"), "differs"),
    (ROW_3974.replace("34,35", "34,34"), "invalid 6/37"),
    (ROW_3974.replace(",2,0,0,", ",8,0,0,"), "invalid 6/37"),
    (ROW_3974.replace("13/10/2026", "invalid-date"), "invalid values"),
])
def test_mismatching_or_invalid_draw_fails_closed(wrong, message):
    with pytest.raises(OfficialCsvAuditError, match=message):
        _audit(_raw([wrong, ROW_3973, ROW_3972]))


def test_missing_and_duplicate_draws_rejected():
    with pytest.raises(OfficialCsvAuditError, match="lacks 1 expected"):
        _audit(_raw([ROW_3974, ROW_3972]))
    with pytest.raises(OfficialCsvAuditError, match="duplicate draw 3974"):
        _audit(_raw([ROW_3974, ROW_3974, ROW_3973, ROW_3972]))


def test_wrong_header_and_html_rejected():
    with pytest.raises(OfficialCsvAuditError, match="header"):
        _audit(("wrong,date,1,2,3,4,5,6,7\n" + ROW_3974).encode("utf-8"))
    with pytest.raises(OfficialCsvAuditError, match="HTML"):
        _audit(b"<html>not a source</html>")


def test_corrupt_local_history_detected_before_archive_comparison():
    bad_history = LotteryDataset([
        LotteryDrawRecord("3972", (2, 4, 6, 13, 18, 25), "06-10-26", 6),
        LotteryDrawRecord("3974", (3, 4, 18, 19, 34, 35), "13-10-26", 2),
    ])
    with pytest.raises(OfficialCsvAuditError, match="ID gap"):
        _audit(history=bad_history)


def test_no_backdating_or_timezone_naive_audit_timestamp():
    with pytest.raises(OfficialCsvAuditError, match="cannot predate"):
        reconcile_uploaded_archive(
            _raw(), _historical(),
            reviewed_at_utc=datetime(2026, 10, 12, tzinfo=timezone.utc),
        )
    with pytest.raises(OfficialCsvAuditError, match="timezone-aware"):
        reconcile_uploaded_archive(
            _raw(), _historical(),
            reviewed_at_utc=datetime(2026, 10, 15),
        )


def test_older_1968_rules_not_retroactively_rejected():
    raw = _raw([OLD_ROW, ROW_3972, ROW_3973, ROW_3974])
    result = _audit(raw)
    assert result["compared_draw_count"] == 3
    assert result["source_record_count"] == 4


def test_newer_draw_is_reported_offline_even_when_all_expected_rows_match():
    newer = "3975,16/10/2026,02,06,08,12,19,33,3,0,0,\n"
    result = _audit(_raw([newer, ROW_3974, ROW_3973, ROW_3972, OLD_ROW]))
    assert result["compared_draw_count"] == 3
    assert result["mismatched_or_missing_draw_count"] == 0
    assert result["source_newer_draw_count"] == 1
    assert result["source_latest_newer_draw_id"] == 3975
    assert result["download_origin_independently_verified"] is False


def test_new_draw_same_day_is_still_detected():
    new = "3975,13/10/2026,02,06,08,12,19,33,3,0,0,\n"
    result = _audit(_raw([new, ROW_3974, ROW_3973, ROW_3972]))
    assert result["source_newer_draw_count"] == 1


def test_1968_legacy_id_numerically_above_current_is_not_a_new_draw():
    result = _audit(_raw([OLD_ROW, ROW_3972, ROW_3973, ROW_3974]))
    assert result["source_newer_draw_count"] == 0
    assert result["source_latest_newer_draw_id"] is None
