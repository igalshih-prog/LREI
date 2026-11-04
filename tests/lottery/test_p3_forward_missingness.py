"""Source-blocked discovery register tests, never prize observation fixtures."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from lrei.lottery.p3_forward_missingness import summarize_ledger

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "data/p3_forward_missingness/source_blocked_candidates.json"
PROTOCOL = ROOT / "research/protocols/p3-strong-choice-forward-screen-v1.json"


def load():
    return json.loads(LEDGER.read_text(encoding="utf-8")), json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_real_discovery_metadata_is_never_admitted():
    ledger, protocol = load()
    result = summarize_ledger(ledger, protocol)
    assert result["candidate_draws_tracked"] == 2
    assert result["last_candidate_draw_id"] == 3981
    assert result["non_admitted_draws"] == 2
    assert result["independently_admitted_draws"] == 0
    assert result["accepted_primary_group_strong_4"] == 0
    assert result["accepted_primary_group_strong_1"] == 0
    assert result["candidate_outcomes_consumed"] is False
    assert result["authorized_for_play"] is False
    assert "main_numbers" not in json.dumps(ledger)
    assert "reported_strong_number" not in json.dumps(ledger)


def test_append_only_rejects_rewrite_or_deletion():
    ledger, protocol = load()
    previous = copy.deepcopy(ledger)
    assert summarize_ledger(ledger, protocol, previous)["candidate_draws_tracked"] == 2
    edited = copy.deepcopy(ledger)
    edited["entries"][0]["draw_date_israel"] = "2026-11-01"
    with pytest.raises(ValueError, match="append-only"):
        summarize_ledger(edited, protocol, previous)
    edited = copy.deepcopy(ledger)
    edited["entries"].pop(0)
    with pytest.raises(ValueError, match="append-only"):
        summarize_ledger(edited, protocol, previous)


def test_draw_id_gap_and_duplicate_rejected():
    ledger, protocol = load()
    for bad_id in [3980, 3982, True]:
        edited = copy.deepcopy(ledger)
        edited["entries"][1]["draw_id"] = bad_id
        with pytest.raises(ValueError, match="contiguous"):
            summarize_ledger(edited, protocol)


def test_future_date_and_order_enforced():
    ledger, protocol = load()
    for bad_date in ["2026-10-29", "2026-10-31", "2026-11-31", "03/11/2026"]:
        edited = copy.deepcopy(ledger)
        edited["entries"][1]["draw_date_israel"] = bad_date
        with pytest.raises(ValueError, match="date|ascending"):
            summarize_ledger(edited, protocol)


def test_no_self_certification_or_outcome_injection():
    ledger, protocol = load()
    modifications = [
        {"disposition": "ACCEPTED"},
        {"source_state": "official"},
        {"main_numbers": [1, 2, 3, 4, 5, 6]},
        {"missing_gates": []},
    ]
    for fields in modifications:
        edited = copy.deepcopy(ledger)
        edited["entries"][0].update(fields)
        with pytest.raises(ValueError):
            summarize_ledger(edited, protocol)


def test_insecure_and_credentialed_url_rejected():
    ledger, protocol = load()
    for bad in ["http://example.org/results", "https://name:pass@example.org/", "file:///tmp/data", "https://example.org:8443/results"]:
        edited = copy.deepcopy(ledger)
        edited["entries"][1]["evidence_urls"] = [bad]
        with pytest.raises(ValueError, match="HTTPS"):
            summarize_ledger(edited, protocol)


def test_frozen_protocol_cannot_be_relaxed():
    ledger, protocol = load()
    relaxed = copy.deepcopy(protocol)
    relaxed["forward_entry_gate"]["minimum_draw_id"] = 3979
    with pytest.raises(ValueError, match="gates"):
        summarize_ledger(ledger, relaxed)


def test_empty_ledger_reports_zero_without_guessing():
    ledger, protocol = load()
    ledger["entries"] = []
    result = summarize_ledger(ledger, protocol)
    assert result["candidate_draws_tracked"] == 0
    assert result["last_candidate_draw_id"] is None
    assert result["independently_admitted_draws"] == 0
