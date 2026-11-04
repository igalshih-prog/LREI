"""Source-gated prospective P3 missingness ledger, never research admission.

The ledger contains only discovery metadata, NOT winning outcomes, prize values,
or proof of authenticity. RESEARCH ONLY / NO PLAY.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .p3_forward_screen import _required_protocol

LEDGER_STATUS = "source_blocked_discovery_only"
_ENTRY_STATES = {"third_party_only", "quarantined_upload_and_third_party", "no_source_found"}
_MISSING_GATES = frozenset({
    "new_first_party_raw_bytes_and_tls_review",
    "binding_draw_protocol_review",
    "complete_regular_and_double_8_plus_8_prize_tiers",
    "source_rights_and_independent_human_approval",
})
_ENTRY_KEYS = frozenset({
    "draw_id", "draw_date_israel", "source_state", "evidence_urls",
    "missing_gates", "disposition",
})


def summarize_ledger(ledger: dict[str, Any], protocol: dict[str, Any],
                     previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fail-closed audit of known candidate IDs; never certify provenance.

    The optional previous ledger prevents silent deletion/editing of old rows;
    it is not a substitute for Git review of new commits.
    """
    minimum_id, minimum_date, group_floor = _required_protocol(protocol)
    if (
        type(ledger) is not dict
        or set(ledger) != {"schema_version", "protocol_id", "status", "entries"}
        or type(ledger["schema_version"]) is not int
        or ledger["schema_version"] != 1
        or ledger["protocol_id"] != protocol["protocol_id"]
        or ledger["status"] != LEDGER_STATUS
        or type(ledger["entries"]) is not list
    ):
        raise ValueError("invalid source-blocked discovery ledger schema")
    if previous is not None:
        if type(previous) is not dict or previous.get("entries") is None:
            raise ValueError("invalid previous ledger")
        # Validate old ledger independently so altered baselines cannot count.
        summarize_ledger(previous, protocol)
        older = previous["entries"]
        if ledger["entries"][:len(older)] != older:
            raise ValueError("append-only ledger: existing draw rows changed or removed")

    last_date: date | None = None
    counts = {"third_party_only": 0, "quarantined_upload_and_third_party": 0,
              "no_source_found": 0}
    for index, entry in enumerate(ledger["entries"]):
        if type(entry) is not dict or set(entry) != _ENTRY_KEYS:
            raise ValueError("candidate entry schema must contain only discovery metadata")
        draw_id = entry["draw_id"]
        if type(draw_id) is not int or draw_id != minimum_id + index:
            raise ValueError("draw IDs must be contiguous from frozen prospective boundary")
        date_text = entry["draw_date_israel"]
        if type(date_text) is not str:
            raise ValueError("known Israel-local calendar date required for each entry")
        try:
            local_date = date.fromisoformat(date_text)
        except ValueError as exc:
            raise ValueError("invalid Israel-local calendar date") from exc
        if local_date.isoformat() != date_text or local_date < minimum_date:
            raise ValueError("candidate date predates frozen boundary or is not ISO date")
        if last_date is not None and local_date <= last_date:
            raise ValueError("future candidate dates must be strictly ascending")
        last_date = local_date

        state = entry["source_state"]
        if type(state) is not str or state not in _ENTRY_STATES:
            raise ValueError("source state cannot self-authorize an observation")
        if entry["disposition"] != "NOT_ADMITTED_SOURCE_GATED":
            raise ValueError("only non-admitted discovery records may enter this ledger")
        if (type(entry["missing_gates"]) is not list
                or len(entry["missing_gates"]) != len(_MISSING_GATES)
                or any(type(g) is not str for g in entry["missing_gates"])
                or set(entry["missing_gates"]) != _MISSING_GATES):
            raise ValueError("all four independent source gates must remain explicit")
        urls = entry["evidence_urls"]
        if (type(urls) is not list or len(urls) > 10
                or any(type(url) is not str for url in urls)
                or len(set(urls)) != len(urls)):
            raise ValueError("evidence URLs must be a distinct short list")
        if state != "no_source_found" and not urls:
            raise ValueError("a reported secondary source needs a source lead")
        if state == "no_source_found" and urls:
            raise ValueError("no_source_found cannot contain source evidence")
        for url in urls:
            if len(url) > 2048:
                raise ValueError("source URL exceeds maximum length")
            try:
                parsed = urlsplit(url)
                valid = (parsed.scheme == "https" and bool(parsed.hostname)
                         and parsed.username is None and parsed.password is None
                         and parsed.port in (None, 443))
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("source leads must be HTTPS links without credentials")
        counts[state] += 1

    n = len(ledger["entries"])
    return {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "status": LEDGER_STATUS,
        "frozen_minimum_draw_id": minimum_id,
        "first_candidate_draw_id": minimum_id if n else None,
        "last_candidate_draw_id": minimum_id + n - 1 if n else None,
        "candidate_draws_tracked": n,
        "source_state_counts": counts,
        "non_admitted_draws": n,
        "independently_admitted_draws": 0,
        "accepted_primary_group_strong_4": 0,
        "accepted_primary_group_strong_1": 0,
        "group_minimum_per_strong": group_floor,
        "candidate_outcomes_consumed": False,
        "payout_data_consumed": False,
        "source_authenticity_verified": False,
        "binding_protocol_verified": False,
        "source_rights_verified": False,
        "prospective_research_conclusion_authorized": False,
        "financial_value_verified": False,
        "authorized_for_play": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="NO PLAY: P3 discovery missingness audit")
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--previous-ledger", type=Path)
    args = parser.parse_args()
    try:
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
        previous = (json.loads(args.previous_ledger.read_text(encoding="utf-8"))
                    if args.previous_ledger else None)
        result = summarize_ledger(ledger, protocol, previous)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
