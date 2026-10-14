"""Offline candidate capture checks. Synthetic rendering; not an authentic page."""

import hashlib
import html
from pathlib import Path

import pytest

from lrei.lottery.prize_data import PrizeDataError, load_observation
from lrei.lottery.source_capture_check import inspect_captured_operator_page

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "prize_observations" / "3950.json"
CAPTURE_TIME = "2026-10-14T06:00:00Z"
TIERS = ("6 + חזק", "6", "5 + חזק", "5", "4 + חזק", "4", "3 + חזק", "3")


def _synthetic_rendering():
    """Made-up HTML formatting using known payout facts, NOT original HTML."""
    obs = load_observation(SAMPLE)
    text = ["תוצאות הגרלה מס' 3950 לתאריך 28/07/2026 שעה 23:17"]
    for title, game in [("טבלת זכיות לוטו", "regular"), ("טבלת זכיות דאבל לוטו", "double")]:
        text.append(title)
        text.append("מס' ניחושים כמות זכיות גובה הפרס")
        for label, row in zip(TIERS, obs["games"][game]):
            text.append(f"מס' ניחושים {label} כמות זכיות {row['winning_entries']:,} גובה הפרס {row['payout_per_winning_entry_ils']:,} ₪")
    text.append("תוצאות הגרלה אקסטרא מס' 3950 טבלת זכיות אקסטרא")
    return " ".join(text)


def _audit(raw=None, mode="text/plain", observation=None, capture=CAPTURE_TIME):
    return inspect_captured_operator_page(
        _synthetic_rendering().encode() if raw is None else raw,
        content_type=mode,
        observation=load_observation(SAMPLE) if observation is None else observation,
        captured_at_utc=capture,
    )


def test_16_rows_match_and_true_bytes_are_hashed_not_fabricated():
    raw = _synthetic_rendering().encode("utf-8")
    report = _audit(raw)
    assert report["matched_payout_rows"] == 16
    assert report["regular_rows_match"] and report["double_rows_match"]
    assert report["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["source_bytes"] == len(raw)
    assert report["human_source_review_required"] is True
    assert report["source_authenticity_independently_verified"] is False
    assert report["approved_draw_protocol_verified"] is False
    assert report["candidate_only_not_economic_evidence"] is True


def test_html_visible_text_is_accepted_without_executing_scripts():
    content = _synthetic_rendering()
    tags = "<html><body><script>var x = 'fake';</script><style>invalid</style>"
    tags += "<section><p>" + html.escape(content) + "</p></section></body></html>"
    report = _audit(tags.encode(), "text/html")
    assert report["matched_payout_rows"] == 16
    assert report["content_type"] == "text/html"


def test_wrong_payout_or_count_rejected():
    content = _synthetic_rendering()
    assert "כמות זכיות 242 גובה הפרס 601 ₪" in content
    for modified in [
        content.replace("כמות זכיות 242 גובה הפרס 601 ₪", "כמות זכיות 242 גובה הפרס 602 ₪"),
        content.replace("כמות זכיות 242 גובה הפרס 601 ₪", "כמות זכיות 243 גובה הפרס 601 ₪"),
    ]:
        with pytest.raises(PrizeDataError, match="disagree"):
            _audit(modified.encode())


def test_source_table_rows_are_not_inferred_from_headline_prize():
    content = _synthetic_rendering().replace(
        "מס' ניחושים 5 + חזק כמות זכיות 35 גובה הפרס 5,577 ₪", ""
    )
    with pytest.raises(PrizeDataError, match="exactly eight"):
        _audit(content.encode())


def test_duplicate_rows_fail_closed():
    content = _synthetic_rendering()
    row = "מס' ניחושים 5 כמות זכיות 242 גובה הפרס 601 ₪"
    with pytest.raises(PrizeDataError, match="exactly eight"):
        _audit(content.replace(row, row + " " + row).encode())


def test_game_sections_cannot_be_swapped():
    content = _synthetic_rendering().replace("טבלת זכיות לוטו", "PLACEHOLDER")
    content = content.replace("טבלת זכיות דאבל לוטו", "טבלת זכיות לוטו")
    content = content.replace("PLACEHOLDER", "טבלת זכיות דאבל לוטו")
    with pytest.raises(PrizeDataError, match="canonical order"):
        _audit(content.encode())


def test_must_be_exactly_correct_draw_and_date():
    content = _synthetic_rendering()
    for bad, message in [
        (content.replace("הגרלה מס' 3950", "הגרלה מס' 3951", 1), "identifier"),
        (content.replace("28/07/2026", "29/07/2026"), "date"),
        (content.replace("תוצאות הגרלה מס' 3950", ""), "identifier"),
    ]:
        with pytest.raises(PrizeDataError, match=message):
            _audit(bad.encode())


def test_capture_date_is_not_generated_by_the_tool():
    with pytest.raises(PrizeDataError, match="predate"):
        _audit(capture="2026-07-27T08:00:00Z")
    for bad in ["2026-10-14", "2026-10-14T99:99:99Z", "2026-10-14T06:00:00+03:00"]:
        with pytest.raises(PrizeDataError, match="UTC|capture"):
            _audit(capture=bad)


def test_wrong_content_type_and_non_utf8_rejected():
    with pytest.raises(PrizeDataError, match="only locally saved"):
        _audit(mode="application/pdf")
    with pytest.raises(PrizeDataError, match="UTF-8"):
        _audit(b"\xff\xfe\x00")


def test_hard_failure_on_oversized_capture_and_embedded_null():
    with pytest.raises(PrizeDataError, match="6 MiB"):
        _audit(b"*" * (6 * 1024 * 1024 + 1))
    with pytest.raises(PrizeDataError, match="NUL"):
        _audit(_synthetic_rendering().encode() + b"\x00")


def test_transcription_source_must_be_operator_source():
    record = load_observation(SAMPLE)
    record["source_url"] = "https://www.paisresults.co.il/"
    with pytest.raises(PrizeDataError, match="requires matching pais"):
        _audit(observation=record)


def test_source_html_without_complete_double_table_rejected():
    content = _synthetic_rendering()
    content = content[:content.index("טבלת זכיות דאבל לוטו")]
    with pytest.raises(PrizeDataError, match="not found"):
        _audit(content.encode())
