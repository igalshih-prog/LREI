"""Append-only P3 *source-evidence events*, never draw observations.

Events preserve the original discovery ledger as an immutable first-seen
snapshot. User-reported first-party-style captures, GitHub hashes and local
delta reports do NOT independently certify provenance or bind lottery draws.
RESEARCH ONLY / NO PLAY.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .p3_forward_missingness import summarize_ledger

EVENT_STATUS = "source_blocked_evidence_events_only"
EVENT_KIND = "user_reported_capture_and_local_delta"
EVENT_DISPOSITION = "QUARANTINED_NOT_ADMITTED"
EVENT_FIELDS = {
    "event_id", "draw_id", "recorded_date_israel", "kind",
    "evidence_urls", "missing_gates", "disposition",
    "independently_attested_source", "binding_protocol_reviewed",
    "source_rights_reviewed", "admitted_as_draw_observation",
    "outcome_values_stored",
}
SHA = re.compile(r"[a-f0-9]{40}\Z")
EVENT_ID = re.compile(r"p3e-([0-9]+)-([0-9]{8})-capture-delta\Z")


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("P3 source-evidence event REFUSED: " + message)


def summarize_events(
    events: dict[str, Any],
    ledger: dict[str, Any],
    protocol: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cross-check discovery IDs and non-admission; reject old-event rewrites."""
    discovery = summarize_ledger(ledger, protocol)
    _check(
        type(events) is dict
        and set(events) == {"schema_version", "protocol_id", "status", "events"}
        and type(events["schema_version"]) is int
        and events["schema_version"] == 1
        and events["protocol_id"] == discovery["protocol_id"]
        and events["status"] == EVENT_STATUS
        and type(events["events"]) is list,
        "invalid event-log schema",
    )
    if previous is not None:
        _check(type(previous) is dict, "invalid previous event log")
        summarize_events(previous, ledger, protocol)
        earlier = previous["events"]
        _check(
            events["events"][: len(earlier)] == earlier,
            "append-only: earlier source-evidence event modified or removed",
        )

    known = {entry["draw_id"]: entry for entry in ledger["entries"]}
    identifiers: set[str] = set()
    last_event_date: date | None = None
    for event in events["events"]:
        _check(type(event) is dict and set(event) == EVENT_FIELDS,
               "event must contain only auditable metadata fields")
        draw_id = event["draw_id"]
        _check(type(draw_id) is int and draw_id in known,
               "event draw must exist in original source-blocked ledger")
        _check(event["kind"] == EVENT_KIND and
               event["disposition"] == EVENT_DISPOSITION,
               "event cannot self-attest source or admit data")
        for field in (
            "independently_attested_source",
            "binding_protocol_reviewed",
            "source_rights_reviewed",
            "admitted_as_draw_observation",
            "outcome_values_stored",
        ):
            _check(event[field] is False, field + " is not verified")

        day_text = event["recorded_date_israel"]
        _check(type(day_text) is str, "event date missing")
        try:
            recorded_date = date.fromisoformat(day_text)
        except ValueError as exc:
            raise ValueError("P3 source-evidence event REFUSED: invalid date") from exc
        _check(
            day_text == recorded_date.isoformat()
            and day_text >= known[draw_id]["draw_date_israel"]
            and (last_event_date is None or recorded_date >= last_event_date),
            "event date precedes draw or earlier evidence event",
        )
        last_event_date = recorded_date
        match = EVENT_ID.fullmatch(event["event_id"]) if type(event["event_id"]) is str else None
        _check(
            match is not None
            and int(match.group(1)) == draw_id
            and match.group(2) == day_text.replace("-", ""),
            "event identifier/date mismatch",
        )
        _check(event["event_id"] not in identifiers, "repeated event ID")
        identifiers.add(event["event_id"])

        gates = event["missing_gates"]
        _check(
            type(gates) is list
            and gates == known[draw_id]["missing_gates"],
            "all existing missing source gates must remain unchanged",
        )

        urls = event["evidence_urls"]
        _check(type(urls) is list and len(urls) == 2 and
               all(type(u) is str and len(u) <= 2048 for u in urls),
               "expected two bounded metadata-only GitHub evidence URLs")
        git_refs: set[str] = set()
        for url, evidence_tag in zip(
            urls, ("user-windows-https-capture-report", "local-powershell-byte-continuity")
        ):
            try:
                parsed = urlsplit(url)
                parts = parsed.path.split("/")
                valid = (
                    parsed.scheme == "https"
                    and parsed.hostname == "github.com"
                    and parsed.username is None
                    and parsed.password is None
                    and parsed.port in (None, 443)
                    and not parsed.query and not parsed.fragment
                    and len(parts) == 8
                    and parts[:5] == ["", "igalshih-prog", "LREI", "blob", parts[4]]
                    and SHA.fullmatch(parts[4]) is not None
                    and parts[5] == "audit-evidence"
                    and parts[6] == ""
                )
            except (ValueError, AttributeError):
                valid = False
            # Format is /OWNER/REPO/blob/COMMIT/audit-evidence/FILENAME
            # -> split gives 7 components, not 8.
            if not valid:
                try:
                    parts = parsed.path.split("/")
                    valid = (
                        parsed.scheme == "https"
                        and parsed.hostname == "github.com"
                        and parsed.username is None and parsed.password is None
                        and parsed.port in (None, 443)
                        and not parsed.query and not parsed.fragment
                        and len(parts) == 7
                        and parts[:4] == ["", "igalshih-prog", "LREI", "blob"]
                        and SHA.fullmatch(parts[4]) is not None
                        and parts[5] == "audit-evidence"
                    )
                except (ValueError, AttributeError):
                    valid = False
            _check(valid, "evidence must be an immutable GitHub audit-file link")
            git_refs.add(parts[4])
            expected = (
                f"p1-{draw_id}-{evidence_tag}-"
                f"{day_text.replace('-', '')}.json"
            )
            _check(parts[-1] == expected,
                   "evidence file does not match event draw/date/kind")
        _check(len(git_refs) == 1, "evidence links must reference one immutable commit")

    return {
        "schema_version": 1,
        "status": "SOURCE_EVIDENCE_LOG_COHERENT_NOT_ATTESTED",
        "evidence_events_tracked": len(events["events"]),
        "candidate_draws_discovered": discovery["candidate_draws_tracked"],
        "independently_admitted_draws": 0,
        "source_provenance_verified": False,
        "binding_draw_protocol_verified": False,
        "source_rights_verified": False,
        "observations_ingested_from_events": False,
        "authorized_for_play": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--previous-events", type=Path)
    parser.add_argument("--bootstrap-single-event", action="store_true")
    args = parser.parse_args()
    try:
        records = json.loads(args.events.read_text(encoding="utf-8"))
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
        previous = (
            json.loads(args.previous_events.read_text(encoding="utf-8"))
            if args.previous_events else None
        )
        result = summarize_events(records, ledger, protocol, previous)
        if args.bootstrap_single_event:
            _check(previous is None and result["evidence_events_tracked"] == 1,
                   "new bootstrap log must contain exactly one event")
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
