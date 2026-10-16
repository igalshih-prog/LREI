"""Actual frozen-draw fixtures: integrity and fail-closed P1 audit regressions.

These are deterministic review tests using a RESULT ALREADY KNOWN from
secondary sites. They cannot count as new out-of-sample research evidence.
"""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lrei.lottery.prospective_paper_audit import score_paper_study

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/"audit"/"prospective"
FROZEN={
    "smart":EVIDENCE/"3975-2026-10-15-smart-5plus-artifact-copy.json",
    "random":EVIDENCE/"3975-2026-10-15-uniform-random-baseline.json",
    "grid":EVIDENCE/"3975-2026-10-15-grid-optimal-5plus-paper.json",
}
MANIFEST=EVIDENCE/"3975-2026-10-15-secondary-result-publication-manifest.json"
TEST_CLOCK="2026-10-16T04:30:00Z"

def study():
    records={k:json.loads(v.read_text(encoding="utf-8")) for k,v in FROZEN.items()}
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    return records,manifest

def evaluate(records=None,manifest=None):
    default_records,default_manifest=study()
    records=default_records if records is None else records
    m=default_manifest if manifest is None else manifest
    return score_paper_study(
        records,m["publications"],draw_id=m["draw"]["id"],
        draw_date=m["draw"]["date"],main=tuple(m["draw"]["main"]),
        strong=m["draw"]["strong"],
        draw_at_utc=m["draw"]["earliest_secondary_reported_draw_at_utc"],
        secondary_source_urls=m["secondary_source_urls"],
        evaluated_at_utc=TEST_CLOCK,
    )

def test_full_study_fixed_records_checksum_and_secondary_score():
    records,m=study()
    result=evaluate(records,m)
    assert result["status"]=="provisional_secondary_only_NOT_officially_verified"
    assert result["draw"]["main"]==[18,22,24,25,27,28]
    assert result["draw"]["strong"]==5
    assert result["results_independently_verified_from_official_operator"] is False
    assert result["eligible_for_expected_value_or_profit_claim"] is False
    assert result["predictive_advantage_established"] is False
    assert result["real_money_wagered"] is False
    assert result["portfolios"]["smart"]["frozen_record_sha256"]=="c5e72c2e67d31eb88bc1efdcb973a1ee84e233a9efa00491c0c1846313117313"
    assert result["portfolios"]["smart"]["best_main_matches"]==3
    assert result["portfolios"]["smart"]["main_3plus_tickets"]==2
    assert result["portfolios"]["smart"]["tier_counts_under_assumed_rules"]["8"]==2
    assert result["portfolios"]["random"]["main_3plus_tickets"]==1
    assert result["portfolios"]["random"]["tier_counts_under_assumed_rules"]["8"]==1
    assert result["portfolios"]["grid"]["main_3plus_tickets"]==0
    assert result["portfolios"]["grid"]["best_main_matches"]==2
    assert result["portfolios"]["grid"]["any_prize_under_assumed_rules"] is False
    assert len(result["report_sha256"])==64
    assert all(p["ticket_count"]==14 for p in result["portfolios"].values())

@pytest.mark.parametrize("key",["smart","random","grid"])
def test_any_tamper_rejected(key):
    records,manifest=study()
    records[key]["tickets"][0]["main"][0]=37
    with pytest.raises(ValueError,match="SHA256 mismatch"):
        evaluate(records,manifest)

@pytest.mark.parametrize("key",["smart","random","grid"])
def test_falsely_late_external_publication_rejected(key):
    records,manifest=study()
    manifest["publications"][key]["published_at_utc"]="2026-10-15T20:00:00Z"
    with pytest.raises(ValueError,match="not externally published before"):
        evaluate(records,manifest)

def test_draw_target_local_date_must_match_even_if_hash_valid():
    records,manifest=study()
    manifest["draw"]["date"]="2026-10-17"
    with pytest.raises(ValueError,match="different local draw date"):
        evaluate(records,manifest)

def test_wrong_draw_id_rejected():
    records,manifest=study()
    manifest["draw"]["id"]=3976
    with pytest.raises(ValueError,match="different draw ID|immediately preceding"):
        evaluate(records,manifest)

def test_two_sources_are_required():
    records,manifest=study()
    manifest["secondary_source_urls"]=manifest["secondary_source_urls"][:1]
    with pytest.raises(ValueError,match="multiple distinct"):
        evaluate(records,manifest)

def test_scoring_before_reported_draw_refused():
    records,manifest=study()
    with pytest.raises(ValueError,match="before the reported draw"):
        score_paper_study(
            records,manifest["publications"],draw_id=3975,
            draw_date="2026-10-15",main=(18,22,24,25,27,28),strong=5,
            draw_at_utc="2026-10-15T19:55:00Z",
            secondary_source_urls=manifest["secondary_source_urls"],
            evaluated_at_utc="2026-10-15T19:54:00Z",
        )

def test_frozen_training_sources_must_match():
    records,manifest=study()
    records["grid"]["source_commit"]="f"*40
    # An attacker might recompute the record checksum: still cannot alter
    # one model's training version without invalidating matched comparison.
    from lrei.lottery.prospective_paper_audit import _digest
    records["grid"]["record_sha256"]=_digest({k:v for k,v in records["grid"].items() if k!="record_sha256"})
    with pytest.raises(ValueError,match="same training version"):
        evaluate(records,manifest)

def test_missing_independent_published_timestamp_fails_closed():
    records,manifest=study()
    del manifest["publications"]["smart"]["published_at_utc"]
    with pytest.raises(ValueError,match="UTC timestamp"):
        evaluate(records,manifest)

def test_unverified_source_cannot_be_upgraded_via_input_manifest():
    records,manifest=study()
    manifest["source_disclaimer"]["official_operator_bytes_captured"]=True
    result=evaluate(records,manifest)
    assert result["results_independently_verified_from_official_operator"] is False

def test_real_money_and_payouts_never_claimed():
    result=evaluate()
    assert "profit" not in result["portfolios"]["smart"]
    assert "winning_money" not in result["portfolios"]["smart"]
    assert result["eligible_for_expected_value_or_profit_claim"] is False
