"""Quarantined candidate intake: NO automatic official-source promotion."""

import hashlib
import html
import json
from pathlib import Path

import pytest

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.prize_data import PrizeDataError, load_observation, validate_prize_observation
from lrei.lottery.prize_capture_intake import extract_quarantined_prize_candidate

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "lottery.csv"
OBS = ROOT / "data" / "prize_observations" / "3950.json"
TIERS = ("6 + חזק", "6", "5 + חזק", "5", "4 + חזק", "4", "3 + חזק", "3")


def archive():
    return CsvDatasetLoader().load(ARCHIVE)


def synthetic_original_style_text():
    """Synthesized from stored observation to test code, NOT real source bytes."""
    data = load_observation(OBS)
    out = ["תוצאות הגרלה מס' 3950 לתאריך 28/07/2026 שעה 23:17"]
    for title, game in (("טבלת זכיות לוטו", "regular"), ("טבלת זכיות דאבל לוטו", "double")):
        out.append(title)
        for label, tier in zip(TIERS, data["games"][game]):
            out.append(
                f"מס' ניחושים {label} כמות זכיות {tier['winning_entries']:,} "
                f"גובה הפרס {tier['payout_per_winning_entry_ils']:,} ₪"
            )
    out.append("תוצאות הגרלה אקסטרא מס' 3950")
    return " ".join(out)


def extract(s=None, *, dt="2026-10-14T06:00:00Z", draw=3950, content_type="text/plain"):
    raw = synthetic_original_style_text().encode("utf-8") if s is None else s
    return extract_quarantined_prize_candidate(
        raw, content_type=content_type, draw_id=draw,
        captured_at_utc=dt, history=archive()
    )


def test_quarantine_returns_exact_16_tiers_but_never_claims_production_approval():
    source = synthetic_original_style_text().encode()
    actual = extract(source)
    old = load_observation(OBS)
    assert actual["draw_id"] == old["draw_id"] == 3950
    assert actual["candidate_tiers"] == old["games"]
    assert sum(len(g) for g in actual["candidate_tiers"].values()) == 16
    assert actual["candidate_source"]["sha256_of_actual_supplied_bytes"] == hashlib.sha256(source).hexdigest()
    assert actual["candidate_source"]["supplied_byte_count"] == len(source)
    assert actual["archive_reference_only"]["main_numbers"] == old["main_numbers"]
    assert actual["archive_reference_only"]["strong_number"] == old["strong_number"]
    assert actual["archive_reference_only"]["numbers_verified_from_captured_page"] is False
    assert actual["status"] == "quarantined_operator_page_capture_pending_human_review"
    assert actual["candidate_source"]["source_authenticity_independently_verified"] is False
    assert actual["candidate_source"]["approved_draw_protocol_verified"] is False
    assert actual["auto_promoted_to_prize_observations"] is False
    assert actual["eligible_for_expected_value"] is False
    assert all(value is None for value in actual["missing_inputs"].values())
    # Deliberately not a production-ready observation.
    with pytest.raises(PrizeDataError):
        validate_prize_observation(actual)


def test_actual_capture_bytes_change_hash_even_if_text_semantics_remain_same():
    a = synthetic_original_style_text().encode()
    b = (synthetic_original_style_text() + " ").encode()
    assert extract(a)["candidate_tiers"] == extract(b)["candidate_tiers"]
    assert extract(a)["candidate_source"]["sha256_of_actual_supplied_bytes"] != extract(b)["candidate_source"]["sha256_of_actual_supplied_bytes"]


def test_offline_html_capture_is_processed_without_interpreting_script_body():
    content = synthetic_original_style_text()
    source = ("<html><body><script>const x=99999;</script><p>"
              + html.escape(content)
              + "</p></body></html>").encode()
    assert extract(source, content_type="text/html")["candidate_tiers"] == load_observation(OBS)["games"]


@pytest.mark.parametrize("mutator,reason", [
    (lambda s: s.replace("תוצאות הגרלה מס' 3950", "תוצאות הגרלה מס' 3951", 1), "heading"),
    (lambda s: s.replace("28/07/2026", "29/07/2026"), "date"),
    (lambda s: s.replace("טבלת זכיות דאבל לוטו", "לא נמצאה טבלה"), "tables"),
    (lambda s: s.replace("טבלת זכיות לוטו", "טבלת זכיות דאבל לוטו"), "tables"),
    (lambda s: s + " תוצאות הגרלה מס' 3950", "heading"),
    (lambda s: s.replace("מס' ניחושים 5 + חזק כמות זכיות 35 גובה הפרס 5,577 ₪", ""), "eight"),
])
def test_incomplete_or_ambiguous_original_page_is_rejected(mutator, reason):
    damaged = mutator(synthetic_original_style_text())
    with pytest.raises(PrizeDataError, match=reason):
        extract(damaged.encode())


def test_capture_timestamp_must_be_explicit_valid_and_after_draw():
    for bad in ("2026-07-27T05:00:00Z", "2026-10-14", "2026-10-14T33:00:00Z",
                "2026-10-14T10:00:00+03:00"):
        with pytest.raises(PrizeDataError, match="capture"):
            extract(dt=bad)


def test_wrong_draw_id_not_allowed_even_if_observation_data_exists():
    with pytest.raises(PrizeDataError, match="heading"):
        extract(draw=3951)
    with pytest.raises(PrizeDataError, match="exactly once"):
        extract(draw=99999)
    with pytest.raises(PrizeDataError, match="positive"):
        extract(draw=False)


def test_detects_single_corrupted_tier_and_does_not_repair_it():
    source = synthetic_original_style_text()
    broken = source.replace(
        "כמות זכיות 242 גובה הפרס 601 ₪",
        "כמות זכיות 242 גובה הפרס 602 ₪",
    )
    out = extract(broken.encode())
    assert out["candidate_tiers"]["regular"][3]["payout_per_winning_entry_ils"] == 602
    assert out["auto_promoted_to_prize_observations"] is False
    assert out["eligible_for_expected_value"] is False


def test_invalid_utf8_and_unsupported_types_are_rejected():
    with pytest.raises(PrizeDataError, match="UTF-8"):
        extract(b"\xff")
    with pytest.raises(PrizeDataError, match="locally saved"):
        extract(content_type="application/pdf")
