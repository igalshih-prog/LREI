"""All generated draw data in tests are synthetic, never real Lotto outcomes."""

from hashlib import sha256
import pytest

from lrei.lottery.source_snapshot_delta import SourceSnapshotError, compare_snapshots, parse_snapshot

HEADER = "הגרלה,תאריך,1,2,3,4,5,6,המספר החזק/נוסף,מספר_זוכים_לוטו,מספר_זוכים_דאבל_לוטו,\r\n"
OLDER = "6801,03/09/1968,3,14,18,22,25,33,2,,,\r\n"
BASE = "2833,10/10/2016,01,04,07,22,32,34,2,0,0,\r\n"
NEXT = "2834,13/10/2016,03,04,18,19,34,35,5,1,0,\r\n"
NEW = "2835,16/10/2016,02,06,08,12,19,33,3,0,0,\r\n"


def raw(*rows):
    return (HEADER + "".join(rows)).encode("cp1255")


def audit(old, new):
    return compare_snapshots(old, new, expected_previous_sha256=sha256(old).hexdigest())


def test_identical_valid_source_is_not_certificate():
    source = raw(NEXT, BASE, OLDER)
    report = audit(source, source)
    assert report["status"] == "NO_NEW_ROWS_CHECK_FRESHNESS"
    assert report["new_draw_ids"] == []
    assert report["prior_modern_rows_checked"] == 2
    assert report["original_download_provenance_proven"] is False
    assert report["operator_binding_protocol_verified"] is False
    assert report["dataset_promotion_approved"] is False


def test_one_new_draw_is_reported_without_authorizing_it():
    report = audit(raw(NEXT, BASE, OLDER), raw(NEW, NEXT, BASE, OLDER))
    assert report["status"] == "NEW_ROWS_REQUIRES_HUMAN_REVIEW"
    assert report["new_draw_ids"] == [2835]
    assert report["revised_prior_draw_ids"] == []
    assert report["current_latest_draw_date"] == "2016-10-16"


def test_historical_main_or_jackpot_revisions_are_detected():
    baseline = raw(NEXT, BASE)
    revised_main = NEXT.replace("34,35", "34,37")
    revised_winners = NEXT.replace(",5,1,0,", ",5,2,0,")
    for revised in (revised_main, revised_winners):
        report = audit(baseline, raw(NEW, revised, BASE))
        assert report["status"] == "HISTORICAL_MISSING_OR_CHANGED_STOP_REVIEW"
        assert report["revised_prior_draw_ids"] == [2834]
        assert report["new_draw_ids"] == [2835]


def test_missing_prior_rows_fail_closed():
    with pytest.raises(SourceSnapshotError, match="missing or out-of-range"):
        audit(raw(BASE, NEXT), raw(NEW, BASE))


def test_bad_prior_pin_fails_closed():
    with pytest.raises(SourceSnapshotError, match="SHA-256"):
        compare_snapshots(raw(BASE, NEXT), raw(BASE, NEXT), expected_previous_sha256="0"*64)


@pytest.mark.parametrize("bad", [
    NEXT.replace(",5,1,0,", ",9,1,0,"),
    NEXT.replace("34,35", "34,34"),
    NEXT.replace(",5,1,0,", ",5,-1,0,"),
    NEXT.replace("13/10/2016", "not-date"),
    NEXT.replace("2834", "2833"),
])
def test_bad_modern_source_rejected(bad):
    with pytest.raises(SourceSnapshotError):
        parse_snapshot(raw(BASE, bad))


def test_missing_middle_draw_rejected():
    with pytest.raises(SourceSnapshotError, match="missing or out-of-range"):
        parse_snapshot(raw(BASE, NEW))


def test_legacy_high_id_does_not_count_as_newer():
    report = audit(raw(NEXT, BASE, OLDER), raw(NEXT, BASE, OLDER))
    assert report["current_latest_draw_id"] == 2834
    assert report["current_raw_row_count"] == 3


def test_duplicate_modern_draw_rejected():
    with pytest.raises(SourceSnapshotError, match="duplicate modern"):
        parse_snapshot(raw(BASE, NEXT, NEXT))


def test_utf8_html_or_wrong_header_rejected():
    with pytest.raises(SourceSnapshotError, match="HTML"):
        parse_snapshot(b"<html>error</html>")
    with pytest.raises(SourceSnapshotError, match="header"):
        parse_snapshot(b"bad,date,1\n2833,10/10/2016,1\n")
