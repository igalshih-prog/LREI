"""Quarantine reply-CSV regression tests. All filled rows are SYNTHETIC.

NO test fixture is an actual response from Mifal HaPais, and passing tests
must not be misconstrued as authenticating any lottery prize payment.
"""

import csv
import hashlib
import io
from pathlib import Path

import pytest

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.prize_data import PrizeDataError
from lrei.lottery.prize_official_reply_intake import (
    quarantine_official_payout_csv,
    quarantine_partial_payout_csv,
)

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "data/prize_request_templates/3955-3968_blank_16_tiers.csv"
ARCHIVE = ROOT / "data/lottery.csv"
WHEN = "2026-10-14T12:00:00Z"
HEAD = (
    "draw_id", "draw_date", "game", "tier",
    "winning_entries", "payout_per_winning_entry_ils",
)


def history():
    return CsvDatasetLoader().load(ARCHIVE)


def rows():
    with TEMPLATE.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert tuple(reader.fieldnames or ()) == HEAD
        result = list(reader)
    # Deliberately fake shape-valid values only for unit testing.
    # Real response data must be independently verified before acceptance.
    for row in result:
        row["winning_entries"] = "1" if row["tier"] == "3" else "0"
        row["payout_per_winning_entry_ils"] = "10" if row["tier"] == "3" else "0"
    return result


def encode(records, headers=HEAD):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(headers), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode("utf-8")


def check(raw, stamp=WHEN):
    return quarantine_official_payout_csv(raw, historical=history(), received_at_utc=stamp)


def test_synthetic_complete_csv_remains_quarantined():
    raw = encode(rows())
    result = check(raw)
    assert result["status"] == "quarantined_completed_request_csv_not_authenticated"
    assert result["draw_count"] == 14
    assert result["tier_row_count"] == len(result["candidate_rows"]) == 224
    assert result["source_evidence"]["sha256_of_received_bytes"] == hashlib.sha256(raw).hexdigest()
    assert result["source_evidence"]["actual_received_byte_count"] == len(raw)
    assert result["source_evidence"]["source_sender_verified"] is False
    assert result["source_evidence"]["source_authenticity_verified"] is False
    assert result["source_evidence"]["approved_draw_protocol_verified"] is False
    assert result["requires_human_source_and_payout_review"] is True
    assert result["ready_for_production_prize_observations"] is False
    assert result["eligible_for_expected_value"] is False
    assert result["has_enough_data_for_profit_claim"] is False
    assert result["candidate_rows"][0]["draw_id"] == 3955
    assert result["candidate_rows"][-1]["draw_id"] == 3968


@pytest.mark.parametrize("mutator,pattern", [
    (lambda v: v.pop(), "exactly 224"),
    (lambda v: v.insert(1, dict(v[0])), "exactly 224"),
    (lambda v: v[1].update(draw_id="3957"), "out-of-order"),
    (lambda v: v[8].update(game="regular"), "out-of-order"),
    (lambda v: v[2].update(tier="5"), "out-of-order"),
    (lambda v: v[0].update(draw_date="2026-08-14"), "draw date"),
    (lambda v: v[0].update(winning_entries=""), "complete numeric"),
    (lambda v: v[0].update(payout_per_winning_entry_ils=""), "complete numeric"),
    (lambda v: v[0].update(winning_entries="-1"), "complete numeric"),
    (lambda v: v[0].update(winning_entries="3.5"), "complete numeric"),
    (lambda v: v[0].update(winning_entries="=1+1"), "complete numeric"),
    (lambda v: v[0].update(payout_per_winning_entry_ils="N/A"), "complete numeric"),
    (lambda v: v[0].update(winning_entries="999999999"), "outside safe"),
    (lambda v: v[0].update(payout_per_winning_entry_ils="9999999999"), "outside safe"),
    (lambda v: v[7].update(payout_per_winning_entry_ils="0"), "zero payout"),
    (lambda v: v[0].update(extra_field="99"), "headers"),
])
def test_reject_tampered_incomplete_or_extra_tiers(mutator, pattern):
    data = rows()
    mutator(data)
    if data and "extra_field" in data[0]:
        fields = list(HEAD) + ["extra_field"]
    else:
        fields = list(HEAD)
    with pytest.raises(PrizeDataError, match=pattern):
        check(encode(data, fields))


def test_all_zero_draw_cannot_be_mistaken_for_populated_worksheet():
    data = rows()
    for line in data[:16]:
        line["winning_entries"] = "0"
        line["payout_per_winning_entry_ils"] = "0"
    with pytest.raises(PrizeDataError, match="possible placeholder"):
        check(encode(data))


def test_blank_template_is_explicitly_rejected():
    with pytest.raises(PrizeDataError, match="complete numeric"):
        check(TEMPLATE.read_bytes())


def test_edited_headers_or_duplicate_header_rejected():
    raw = encode(rows())
    with pytest.raises(PrizeDataError, match="headers"):
        check(raw.replace(b"winning_entries", b"prize_count", 1))
    with pytest.raises(PrizeDataError, match="headers"):
        check(raw.replace(b"draw_date", b"draw_id", 1))


def test_real_sha256_is_based_on_exact_raw_bytes():
    a = encode(rows())
    b = b"\xef\xbb\xbf" + a
    assert check(a)["candidate_rows"] == check(b)["candidate_rows"]
    assert check(a)["source_evidence"]["sha256_of_received_bytes"] != check(b)["source_evidence"]["sha256_of_received_bytes"]


@pytest.mark.parametrize("stamp", [
    "2026-10-14", "2026-10-14T99:99:99Z", "2026-08-01T00:00:00Z",
    "2026-10-14T16:00:00+03:00",
])
def test_impossible_or_predraw_capture_time_rejected(stamp):
    with pytest.raises(PrizeDataError, match="UTC|historical draw"):
        check(encode(rows()), stamp)


def test_invalid_bytes_and_oversize_rejected():
    with pytest.raises(PrizeDataError, match="UTF-8"):
        check(b"\xff")
    with pytest.raises(PrizeDataError, match="NUL"):
        check(encode(rows()) + b"\x00")
    with pytest.raises(PrizeDataError, match="2 MiB"):
        check(b"A" * (2 * 1024 * 1024 + 1))



def partial(data, when=WHEN):
    return quarantine_partial_payout_csv(
        encode(data), historical=history(), received_at_utc=when
    )


def test_one_draw_full_sixteen_rows_can_be_quarantined_but_not_promoted():
    result = partial(rows()[:16])
    assert result["draw_ids_in_reply"] == [3955]
    assert result["draw_count_in_reply"] == 1
    assert result["tier_row_count"] == 16
    assert result["missing_draw_ids"] == list(range(3956, 3969))
    assert result["complete_target_window"] is False
    assert result["source_evidence"]["source_authenticity_verified"] is False
    assert result["source_evidence"]["approved_draw_protocol_verified"] is False
    assert result["auto_promoted_to_verified_observations"] is False
    assert result["eligible_for_expected_value"] is False
    assert result["requires_human_review"] is True
    with pytest.raises(PrizeDataError, match="exactly 224"):
        check(encode(rows()[:16]))  # original default strict path remains unchanged


def test_nonconsecutive_drawing_batches_keep_missing_ids_visible():
    data = rows()
    result = partial(data[:16] + data[32:48])
    assert result["draw_ids_in_reply"] == [3955, 3957]
    assert result["missing_draw_ids"] == [3956, *range(3958, 3969)]
    assert result["tier_row_count"] == 32
    assert result["source_evidence"]["sha256_of_actual_received_bytes"] == hashlib.sha256(
        encode(data[:16] + data[32:48])
    ).hexdigest()


def test_full_csv_in_partial_mode_is_still_unverified():
    result = partial(rows())
    assert result["draw_ids_in_reply"] == list(range(3955, 3969))
    assert result["complete_target_window"] is True
    assert result["source_evidence"]["source_sender_verified"] is False
    assert result["auto_promoted_to_verified_observations"] is False
    assert result["eligible_for_expected_value"] is False


@pytest.mark.parametrize("mutate,reason", [
    (lambda d: d.pop(), "whole 16-tier"),
    (lambda d: d.insert(1, dict(d[0])), "whole 16-tier"),
    (lambda d: d[0].update(draw_date="2026-08-14"), "out-of-order"),
    (lambda d: d[0].update(draw_id="3954"), "ascending"),
    (lambda d: d[0].update(tier="5+strong"), "out-of-order"),
    (lambda d: d[1].update(game="double"), "out-of-order"),
    (lambda d: d[1].update(winning_entries=""), "complete numeric"),
    (lambda d: d[1].update(winning_entries="=2+2"), "complete numeric"),
    (lambda d: d[7].update(payout_per_winning_entry_ils="0"), "zero payout"),
    (lambda d: d[0].update(extra_field="x"), "header mismatch"),
])
def test_partial_reply_fail_closed(mutate, reason):
    data = rows()[:16]
    mutate(data)
    head = list(HEAD) + (["extra_field"] if "extra_field" in data[0] else [])
    with pytest.raises(PrizeDataError, match=reason):
        raw = encode(data, head)
        quarantine_partial_payout_csv(
            raw, historical=history(), received_at_utc=WHEN
        )


def test_partial_duplicate_draw_blocks_and_out_of_order_draw_rejected():
    data = rows()
    with pytest.raises(PrizeDataError, match="unique ascending"):
        partial(data[:16] + data[:16])
    with pytest.raises(PrizeDataError, match="unique ascending"):
        partial(data[16:32] + data[:16])


def test_partial_all_zero_and_blank_request_rejected():
    data = rows()[:16]
    for record in data:
        record["winning_entries"] = "0"
        record["payout_per_winning_entry_ils"] = "0"
    with pytest.raises(PrizeDataError, match="all-zero placeholder"):
        partial(data)
    with pytest.raises(PrizeDataError, match="complete numeric"):
        quarantine_partial_payout_csv(
            TEMPLATE.read_bytes(), historical=history(), received_at_utc=WHEN
        )


def test_partial_garbled_source_or_invalid_timestamp_rejected():
    with pytest.raises(PrizeDataError, match="UTF-8"):
        quarantine_partial_payout_csv(
            b"\xff", historical=history(), received_at_utc=WHEN
        )
    with pytest.raises(PrizeDataError, match="UTC"):
        partial(rows()[:16], when="2026-10-14")
