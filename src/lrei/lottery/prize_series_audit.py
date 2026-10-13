"""Strict, offline review of operator-linked prize observations (P3-A.2).

This does not fetch websites. A public results page is informational and is
not the legally binding approved lottery draw protocol. We record explicitly
whether a raw source was archived, verified, or merely reviewed manually.

A missing page / prize tier / real sales data must never be silently invented.
The audit is descriptive only; it cannot estimate financial expected value.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from .dataset import LotteryDataset
from .prize_data import (
    GAME_TYPES,
    PrizeDataError,
    canonical_sha256,
    load_observation,
)

REVIEW_METHOD = "manual_operator_page_comparison"
_MANIFEST_KEYS = {
    "schema_version", "window_start_draw_id", "window_end_draw_id",
    "purpose", "sources",
}
_SOURCE_KEYS = {
    "draw_id", "source_url", "reviewed_on_utc_date", "draw_time_local",
    "review_method", "raw_source_sha256", "raw_source_archived",
    "approved_protocol_verified", "rule_version", "review_notes",
}
PURPOSE = "retrospective_financial_data_research_not_prospective_holdout"


def _valid_ymd(value: Any, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise PrizeDataError(f"{label} must be YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise PrizeDataError(f"{label} is not a valid date") from exc


def _valid_hhmm(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise PrizeDataError("draw_time_local must be HH:MM")


def _check_source(row: Any, observations: dict[int, dict[str, Any]]) -> None:
    if not isinstance(row, dict) or set(row) != _SOURCE_KEYS:
        raise PrizeDataError("source audit must contain exactly the audit fields")
    identifier = row["draw_id"]
    if type(identifier) is not int or identifier not in observations:
        raise PrizeDataError("source audit must match an existing observation")
    record = observations[identifier]
    if row["source_url"] != record["source_url"]:
        raise PrizeDataError("source audit URL must match the exact observation URL")
    _valid_ymd(row["reviewed_on_utc_date"], "reviewed_on_utc_date")
    if row["reviewed_on_utc_date"] < record["draw_date"]:
        raise PrizeDataError("source cannot be reviewed before the draw")
    _valid_hhmm(row["draw_time_local"])
    if row["review_method"] != REVIEW_METHOD:
        raise PrizeDataError("audit must use a documented manual comparison method")
    if row["raw_source_archived"] is not False or row["raw_source_sha256"] is not None:
        raise PrizeDataError(
            "raw source not archived here; never assert a hash without retained bytes"
        )
    if row["approved_protocol_verified"] is not False:
        raise PrizeDataError("an approved draw protocol has not been verified")
    if row["rule_version"] is not None:
        raise PrizeDataError("do not claim a validated rule version without evidence")
    if row["review_notes"] is not None and (
        not isinstance(row["review_notes"], str) or not row["review_notes"].strip()
    ):
        raise PrizeDataError("review_notes must be meaningful text or null")


def audit_prize_series(
    observations_dir: Path | str,
    manifest_file: Path | str,
    historical: LotteryDataset | None = None,
) -> dict[str, Any]:
    """Audit the FULL declared window, explicitly reporting all missing draws.

    Incomplete series returns a report, not a falsely successful dataset.
    Malformed records, unexpected draw IDs and unmatched provenance fail closed.
    """
    directory = Path(observations_dir)
    try:
        manifest = json.loads(Path(manifest_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrizeDataError("cannot read series manifest") from exc
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
        raise PrizeDataError("series manifest fields missing or unexpected")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or manifest["purpose"] != PURPOSE:
        raise PrizeDataError("invalid audit schema or retrospective-only purpose")
    first, last = manifest["window_start_draw_id"], manifest["window_end_draw_id"]
    if type(first) is not int or type(last) is not int or first < 1 or last < first:
        raise PrizeDataError("invalid consecutive audit window")
    if last - first + 1 > 1000:
        raise PrizeDataError("audit window too broad")

    observations: dict[int, dict[str, Any]] = {}
    if not directory.is_dir():
        raise PrizeDataError("observation directory missing")
    for path in sorted(directory.glob("*.json")):
        if not re.fullmatch(r"[1-9][0-9]*\.json", path.name):
            raise PrizeDataError("observation file needs canonical numeric draw ID")
        identifier = int(path.stem)
        if not first <= identifier <= last:
            raise PrizeDataError("observation outside declared consecutive window")
        if identifier in observations:
            raise PrizeDataError("duplicate draw observation")
        obs = load_observation(path, historical)
        if obs["draw_id"] != identifier:
            raise PrizeDataError("observation filename disagrees with draw_id")
        observations[identifier] = obs

    sources = manifest["sources"]
    if not isinstance(sources, list) or len(sources) != len(observations):
        raise PrizeDataError("every stored observation needs exactly one source audit")
    audited: set[int] = set()
    for row in sources:
        _check_source(row, observations)
        identifier = row["draw_id"]
        if identifier in audited:
            raise PrizeDataError("duplicate source audit for draw")
        audited.add(identifier)

    missing = [n for n in range(first, last + 1) if n not in observations]
    accounting: dict[str, Any] = {}
    for identifier, observation in sorted(observations.items()):
        regular = sum(
            item["winning_entries"] * item["payout_per_winning_entry_ils"]
            for item in observation["games"][GAME_TYPES[0]]
            if item["payout_per_winning_entry_ils"] is not None
        )
        double = sum(
            item["winning_entries"] * item["payout_per_winning_entry_ils"]
            for item in observation["games"][GAME_TYPES[1]]
            if item["payout_per_winning_entry_ils"] is not None
        )
        reported = observation["total_prizes_paid_ils"]
        # The operator total can include Extra or other non-Lotto payments.
        # We can record its residual but NEVER label it "Extra winnings" without data.
        accounting[str(identifier)] = {
            "known_regular_lotto_payout_ils": regular,
            "known_double_lotto_payout_ils": double,
            "operator_all_games_total_ils": reported,
            "operator_total_minus_lotto_sum_ils": reported - regular - double if reported is not None else None,
            "observation_sha256": canonical_sha256(observation),
        }
    return {
        "audit_schema_version": 1,
        "window_start_draw_id": first,
        "window_end_draw_id": last,
        "expected_draws": last - first + 1,
        "observed_draws": len(observations),
        "source_audits": len(audited),
        "missing_draw_ids": missing,
        "series_complete": not missing,
        "source_raw_bytes_available": False,
        "approved_protocols_verified": False,
        "official_sales_data_available": all(x["ticket_sales_ils"] is not None for x in observations.values()) and bool(observations),
        "eligible_for_financial_prediction": False,
        "accounting": accounting,
        "purpose": PURPOSE,
    }


def main() -> None:
    """Run an offline, no-network audit, with intentionally visible gaps."""
    import argparse
    from .dataset import CsvDatasetLoader

    parser = argparse.ArgumentParser(
        description="Audit historical lottery prize tables and report gaps without imputing data."
    )
    parser.add_argument("--observations-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--historical-csv", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true",
                        help="Exit nonzero if at least one draw is missing.")
    options = parser.parse_args()
    try:
        archive = CsvDatasetLoader().load(options.historical_csv)
        report = audit_prize_series(options.observations_dir, options.manifest, archive)
    except (PrizeDataError, OSError, ValueError) as exc:
        parser.exit(2, f"Prize audit failed: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    if options.require_complete and not report["series_complete"]:
        parser.exit(1, "Prize series is incomplete; see missing_draw_ids above.\n")


if __name__ == "__main__":
    main()
