"""Synthetic, offline regression tests; success is not operator authenticity."""

import hashlib

import pytest

from lrei.lottery.archive_delta import compare_archive_updates
from lrei.lottery.official_draw_source import OfficialCsvAuditError


HEADER = (
    "הגרלה,תאריך,1,2,3,4,5,6,המספר החזק/נוסף,"
    "מספר_זוכים_לוטו,מספר_זוכים_דאבל_לוטו,\n"
)
FIRST = "3973,10/10/2026,01,04,07,22,32,34,2,0,0,\n"
SECOND = "3974,13/10/2026,03,04,18,19,34,35,2,0,0,\n"
THIRD = "3975,15/10/2026,18,22,24,25,27,28,5,1,0,\n"


def raw(*rows):
    return (HEADER + "".join(rows)).encode("cp1255")


def test_preserves_all_previous_columns_and_reports_no_authenticity():
    old, new = raw(SECOND, FIRST), raw(THIRD, SECOND, FIRST)
    report = compare_archive_updates(old, new)
    assert report["old_draw_count"] == 2
    assert report["new_draw_count"] == 3
    assert report["exact_common_rows"] == 2
    assert report["new_draw_ids"] == [3975]
    assert report["old_raw_sha256"] == hashlib.sha256(old).hexdigest()
    assert report["new_raw_sha256"] == hashlib.sha256(new).hexdigest()
    assert report["changed_common_rows_all_columns"] == 0
    assert report["download_origin_independently_verified"] is False
    assert report["operator_protocol_legally_verified"] is False
    assert report["eligible_for_dataset_promotion"] is False
    assert report["eligible_for_predictive_or_economic_claim"] is False


def test_reordered_archive_rows_are_content_equivalent():
    report = compare_archive_updates(
        raw(FIRST, SECOND), raw(THIRD, SECOND, FIRST)
    )
    assert report["new_draw_ids"] == [3975]
    assert report["exact_common_rows"] == 2


def test_same_archive_no_new_draws_is_reported_not_pretended_increment():
    report = compare_archive_updates(raw(FIRST), raw(FIRST))
    assert report["new_draw_ids"] == []
    assert report["exact_common_rows"] == 1


@pytest.mark.parametrize("modified", [
    SECOND.replace("35", "36"),
    SECOND.replace("13/10/2026", "14/10/2026"),
    SECOND.replace(",2,0,0,", ",3,0,0,"),
    SECOND.replace(",2,0,0,", ",2,1,0,"),
    SECOND.replace(",2,0,0,", ",2,0,1,"),
    SECOND.replace("03", "3", 1),
])
def test_any_changed_existing_field_rejected(modified):
    with pytest.raises(OfficialCsvAuditError, match="changed"):
        compare_archive_updates(raw(FIRST, SECOND), raw(FIRST, modified, THIRD))


def test_deleted_old_record_rejected():
    with pytest.raises(OfficialCsvAuditError, match="deleted"):
        compare_archive_updates(raw(FIRST, SECOND), raw(FIRST, THIRD))


def test_backfill_of_older_id_rejected_even_if_existing_rows_identical():
    old = raw(SECOND, THIRD)
    with pytest.raises(OfficialCsvAuditError, match="backfilled"):
        compare_archive_updates(old, raw(FIRST, SECOND, THIRD))


@pytest.mark.parametrize("data,match", [
    (raw(FIRST, FIRST), "duplicate"),
    (b"<html>not csv</html>", "HTML"),
    (b"\x00" + raw(FIRST), "binary"),
    ((HEADER + FIRST.replace("3973", "xxx")).encode("cp1255"), "malformed"),
    ((HEADER + FIRST.replace(",0,0,", ",0,")).encode("cp1255"), "columns"),
])
def test_invalid_csv_refused(data, match):
    with pytest.raises(OfficialCsvAuditError, match=match):
        compare_archive_updates(raw(FIRST), data)


def test_header_change_rejected_including_extra_columns():
    new = raw(FIRST).replace(
        "מספר_זוכים_לוטו".encode("cp1255"),
        "מספר_זוכים_חדש".encode("cp1255")
    )
    with pytest.raises(OfficialCsvAuditError, match="headers"):
        compare_archive_updates(raw(FIRST), new)



def test_appended_draw_id_gap_rejected():
    next_but_one = THIRD.replace("3975", "3976")
    with pytest.raises(OfficialCsvAuditError, match="gap"):
        compare_archive_updates(raw(FIRST, SECOND), raw(FIRST, SECOND, next_but_one))

def test_no_trust_in_same_named_or_claimed_source():
    # Even identical files cannot be promoted from offline content alone.
    report = compare_archive_updates(raw(FIRST), raw(FIRST))
    assert report["download_origin_independently_verified"] is False
    assert report["eligible_for_dataset_promotion"] is False
