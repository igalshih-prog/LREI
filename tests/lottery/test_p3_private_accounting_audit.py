"""Synthetic-only, fail-closed P3 private all-games accounting tests."""

import hashlib
import json
from pathlib import Path

import pytest

from lrei.lottery.dataset import CsvDatasetLoader, parse_draw_date
from lrei.lottery.prize_capture_intake import extract_quarantined_prize_candidate
from lrei.lottery.prize_data import PrizeDataError
from lrei.lottery.p3_private_accounting_audit import (
    audit_private_cohort, audit_one_private_page, page_accounting_totals,
)

ROOT = Path(__file__).resolve().parents[2]
HISTORY = CsvDatasetLoader().load(ROOT / "data" / "lottery.csv")
TIERS = ("6 + חזק", "6", "5 + חזק", "5",
         "4 + חזק", "4", "3 + חזק", "3")
UTC = "2026-11-06T15:44:18Z"


def sample(draw_id=3956):
    """Everything generated here is fake test data, never actual prize results."""
    archive = next(x for x in HISTORY if x.draw_id == str(draw_id))
    date = parse_draw_date(archive.date).strftime("%d/%m/%Y")
    rows = [f"תוצאות הגרלה מס' {draw_id} לתאריך {date} שעה 23:15"]
    regular = 0
    double = 0
    for game, offset in (("regular", 50), ("double", 100)):
        rows.append("טבלת זכיות לוטו" if game == "regular" else "טבלת זכיות דאבל לוטו")
        for i, tier in enumerate(TIERS):
            count, award = i + 1, offset + i
            if game == "regular":
                regular += count * award
            else:
                double += count * award
            rows.append(
                f"מס' ניחושים {tier} כמות זכיות {count:,} גובה הפרס {award:,} ₪"
            )
    rows.extend([f"תוצאות הגרלה אקסטרא מס' {draw_id}", "טבלת זכיות אקסטרא"])
    extra_total = 0
    for i, tier in enumerate(("6", "5", "4", "3", "2")):
        count, award = i, 200 + i
        extra_total += count * award
        rows.append(
            f"מס' ניחושים {tier} כמות זכיות {count:,} גובה הפרס {award:,} ₪"
        )
    total = regular + double + extra_total
    rows.append(f"לארכיון תוצאות הגרלה סך כל הפרסים שחולקו בהגרלה זו היה: {total:,} ₪")
    raw = ("<html><body>" + " ".join(f"<p>{item}</p>" for item in rows) +
           "</body></html>").encode("utf-8")
    candidate = extract_quarantined_prize_candidate(
        raw, content_type="text/html", draw_id=draw_id,
        captured_at_utc=UTC, history=HISTORY,
    )
    record = {
        "draw_id": draw_id,
        "http_status": 200,
        "status": "16_TIERS_QUARANTINED_PENDING_HUMAN_REVIEW",
        "parsed_tiers": 16,
        "final_response_url": f"https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId={draw_id}",
        "raw_source_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_source_bytes": len(raw),
    }
    return raw, candidate, record, (regular, double, extra_total, total)


def test_single_page_all_three_game_sums_match_headline_without_publishing_values():
    raw, candidate, record, totals = sample()
    outcome = page_accounting_totals(raw)
    assert outcome["extra_paid"] == totals[2]
    assert outcome["all_games_paid"] == totals[3]
    assert audit_one_private_page(draw_id=3956, record=record, raw=raw,
                                  candidate=candidate, history=HISTORY) is None


def test_strict_thirteen_draw_private_cohort_only_prints_counts(tmp_path):
    records = []
    for draw_id in range(3956, 3969):
        raw, candidate, record, _ = sample(draw_id)
        (tmp_path / f"draw-{draw_id}-operator-original.html").write_bytes(raw)
        (tmp_path / f"draw-{draw_id}-quarantine-candidate.json").write_text(
            json.dumps(candidate, ensure_ascii=False), encoding="utf-8"
        )
        records.append(record)
    manifest = {
        "schema": "lrei-p3-private-operator-page-batch-v1",
        "status": "ALL_CANDIDATES_QUARANTINED_NO_ADMISSION",
        "draw_ids_requested": list(range(3956, 3969)),
        "pages_captured": 13,
        "draws_with_sixteen_tiers_quarantined": 13,
        "rows_approved_for_production": 0,
        "source_use_rights_verified": False,
        "binding_committee_protocol_verified": False,
        "captures": records,
    }
    (tmp_path / "private-capture-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    result = audit_private_cohort(tmp_path, HISTORY)
    assert result["draws_checked"] == 13
    assert result["regular_double_tiers_rechecked"] == 208
    assert result["extra_tiers_checked"] == 65
    assert result["all_games_totals_matched"] == 13
    assert result["dataset_promotion_approved"] is False
    assert result["source_authenticity_independently_verified"] is False
    assert result["eligible_for_monetary_expected_value"] is False
    assert "known_regular_lotto_payout_ils" not in result
    assert "prize_values" not in result
    assert len(list(tmp_path.iterdir())) == 27  # 13 pairs + existing manifest only


@pytest.mark.parametrize("change,error", [
    ("headline", "three-games payout"),
    ("extra", "three-games payout"),
    ("duplicated_extra_heading", "heading is missing or duplicated"),
    ("missing_extra_tier", "exactly five"),
    ("duplicate_extra_tier", "exactly five"),
    ("missing_total", "all-games total"),
])
def test_accounting_discrepancies_refuse_without_guessing(change, error):
    raw, candidate, record, totals = sample()
    source = raw.decode()
    original = f"סך כל הפרסים שחולקו בהגרלה זו היה: {totals[3]:,} ₪"
    if change == "headline":
        source = source.replace(original, f"סך כל הפרסים שחולקו בהגרלה זו היה: {totals[3] + 1:,} ₪")
    elif change == "extra":
        source = source.replace("מס' ניחושים 5 כמות זכיות 1 גובה הפרס 201 ₪",
                                "מס' ניחושים 5 כמות זכיות 2 גובה הפרס 201 ₪")
    elif change == "duplicated_extra_heading":
        source = source.replace("טבלת זכיות אקסטרא", "טבלת זכיות אקסטרא טבלת זכיות אקסטרא")
    elif change == "missing_extra_tier":
        source = source.replace("מס' ניחושים 2 כמות זכיות 4 גובה הפרס 204 ₪", "")
    elif change == "duplicate_extra_tier":
        source = source.replace("מס' ניחושים 2 כמות זכיות 4 גובה הפרס 204 ₪",
                                "מס' ניחושים 2 כמות זכיות 4 גובה הפרס 204 ₪ " * 2)
    elif change == "missing_total":
        source = source.replace(original, "")
    damaged = source.encode()
    if change in ("headline", "extra"):
        record["raw_source_sha256"] = hashlib.sha256(damaged).hexdigest()
        record["raw_source_bytes"] = len(damaged)
        candidate["candidate_source"]["sha256_of_actual_supplied_bytes"] = record["raw_source_sha256"]
        candidate["candidate_source"]["supplied_byte_count"] = len(damaged)
        with pytest.raises(PrizeDataError, match=error):
            audit_one_private_page(draw_id=3956, record=record, raw=damaged,
                                   candidate=candidate, history=HISTORY)
    else:
        with pytest.raises(PrizeDataError, match=error):
            page_accounting_totals(damaged)


@pytest.mark.parametrize("bad", [
    "raw_hash", "candidate_hash", "source_url", "promoted", "tier_payout"
])
def test_tampered_original_or_candidate_is_refused(bad):
    raw, candidate, record, _ = sample()
    if bad == "raw_hash":
        record["raw_source_sha256"] = "0" * 64
    elif bad == "candidate_hash":
        candidate["candidate_source"]["sha256_of_actual_supplied_bytes"] = "0" * 64
    elif bad == "source_url":
        record["final_response_url"] = "https://unofficial.example.com/lotto"
    elif bad == "promoted":
        candidate["auto_promoted_to_prize_observations"] = True
    elif bad == "tier_payout":
        candidate["candidate_tiers"]["regular"][4]["payout_per_winning_entry_ils"] += 1
    with pytest.raises(PrizeDataError):
        audit_one_private_page(draw_id=3956, record=record, raw=raw,
                               candidate=candidate, history=HISTORY)
