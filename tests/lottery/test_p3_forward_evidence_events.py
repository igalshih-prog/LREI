"""Synthetic/metadata-only P3 evidence event integrity checks. Never play."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from lrei.lottery.p3_forward_evidence_events import summarize_events

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data/p3_forward_missingness/source_evidence_events.json"
LEDGER = ROOT / "data/p3_forward_missingness/source_blocked_candidates.json"
PROTOCOL = ROOT / "research/protocols/p3-strong-choice-forward-screen-v1.json"


def load():
    return (
        json.loads(EVENTS.read_text(encoding="utf-8")),
        json.loads(LEDGER.read_text(encoding="utf-8")),
        json.loads(PROTOCOL.read_text(encoding="utf-8")),
    )


def test_real_event_metadata_not_admitted_and_discovery_unchanged():
    events, ledger, protocol = load()
    result = summarize_events(events, ledger, protocol)
    assert result["evidence_events_tracked"] == 1
    assert result["candidate_draws_discovered"] == 2
    assert result["independently_admitted_draws"] == 0
    assert result["observations_ingested_from_events"] is False
    assert result["authorized_for_play"] is False
    e = events["events"][0]
    assert e["draw_id"] == 3981
    assert e["recorded_date_israel"] == "2026-11-04"
    assert e["missing_gates"] == ledger["entries"][1]["missing_gates"]
    raw = json.dumps(events)
    assert '"main_numbers"' not in raw
    assert '"strong_number"' not in raw
    assert '"winning_entries"' not in raw


def test_append_only_no_rewrite_or_delete():
    events, ledger, protocol = load()
    baseline = copy.deepcopy(events)
    assert summarize_events(events, ledger, protocol, baseline)["evidence_events_tracked"] == 1
    edited = copy.deepcopy(events)
    edited["events"][0]["recorded_date_israel"] = "2026-11-05"
    with pytest.raises(ValueError, match="append-only"):
        summarize_events(edited, ledger, protocol, baseline)
    edited = copy.deepcopy(events)
    edited["events"] = []
    with pytest.raises(ValueError, match="append-only"):
        summarize_events(edited, ledger, protocol, baseline)


@pytest.mark.parametrize(("field", "value"), [
    ("independently_attested_source", True),
    ("binding_protocol_reviewed", True),
    ("source_rights_reviewed", True),
    ("admitted_as_draw_observation", True),
    ("outcome_values_stored", True),
    ("disposition", "ADMITTED"),
    ("draw_id", 3982),
    ("recorded_date_israel", "2026-11-03"),
    ("missing_gates", []),
    ("event_id", "p3e-3981-20261103-capture-delta"),
    ("main_numbers", [1, 2, 3, 4, 5, 6]),
    ("winning_entries", 500),
])
def test_false_approval_or_outcome_payload_refused(field, value):
    events, ledger, protocol = load()
    changed = copy.deepcopy(events)
    changed["events"][0][field] = value
    with pytest.raises(ValueError):
        summarize_events(changed, ledger, protocol)


@pytest.mark.parametrize("url", [
    "http://github.com/igalshih-prog/LREI/blob/x/audit-evidence/f.json",
    "https://example.com/report.json",
    "https://github.com/igalshih-prog/LREI/blob/main/audit-evidence/p1-3981-user-windows-https-capture-report-20261104.json",
    "https://user:password@github.com/igalshih-prog/LREI/blob/" + "b"*40 + "/audit-evidence/p1-3981-user-windows-https-capture-report-20261104.json",
    "https://github.com/igalshih-prog/LREI/blob/" + "b"*40 + "/audit-evidence/p1-3981-user-windows-https-capture-report-20261104.json",
])
def test_untrusted_mutable_or_mismatched_evidence_url_refused(url):
    events, ledger, protocol = load()
    events["events"][0]["evidence_urls"][0] = url
    with pytest.raises(ValueError):
        summarize_events(events, ledger, protocol)


def test_duplicate_event_rejected():
    events, ledger, protocol = load()
    events["events"].append(copy.deepcopy(events["events"][0]))
    with pytest.raises(ValueError, match="repeated"):
        summarize_events(events, ledger, protocol)


def test_synthetic_new_event_cannot_point_to_missing_draw():
    events, ledger, protocol = load()
    e = copy.deepcopy(events["events"][0])
    e["event_id"] = "p3e-3982-20261105-capture-delta"
    e["draw_id"] = 3982
    e["recorded_date_israel"] = "2026-11-05"
    events["events"].append(e)
    with pytest.raises(ValueError, match="exist"):
        summarize_events(events, ledger, protocol)


def test_frozen_protocol_unchanged_by_event():
    events, ledger, protocol = load()
    changed = copy.deepcopy(protocol)
    changed["forward_entry_gate"]["minimum_draw_id"] = 3979
    with pytest.raises(ValueError, match="gates"):
        summarize_events(events, ledger, changed)
