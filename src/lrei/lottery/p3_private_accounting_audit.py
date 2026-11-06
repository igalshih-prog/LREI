"""Read-only P3 check: original page's ALL-GAMES payout total reconciles.

For PRIVATE, noncommercial source review only. No network, no writing, no
source license/attestation, no draw-protocol approval, no dataset promotion.
Never print or publish raw pages, individual prize tiers, or payout totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .dataset import CsvDatasetLoader, LotteryDataset
from .prize_capture_intake import extract_quarantined_prize_candidate
from .prize_data import PrizeDataError
from .source_capture_check import MAX_CAPTURE_BYTES, _flat_text

FIRST, LAST = 3956, 3968
EXPECTED_IDS = list(range(FIRST, LAST + 1))
EXTRA_HEADING = "טבלת זכיות אקסטרא"
EXTRA_ROW = re.compile(
    r"מס['׳]\s*ניחושים\s*(6|5|4|3|2)\s*"
    r"כמות\s*זכיות\s*([0-9][0-9,]*)\s*"
    r"גובה\s*הפרס\s*([0-9][0-9,]*)\s*₪"
)
ALL_GAMES_TOTAL = re.compile(
    r"סך\s+כל\s+הפרסים\s+שחולקו\s+בהגרלה\s+זו\s+היה\s*:\s*"
    r"([0-9][0-9,]*)\s*₪"
)


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise PrizeDataError(reason)


def _read_bounded(path: Path) -> bytes:
    length = path.stat().st_size
    _require(1000 <= length <= MAX_CAPTURE_BYTES, "private page size is out of bounds")
    with path.open("rb") as stream:
        raw = stream.read(MAX_CAPTURE_BYTES + 1)
    _require(len(raw) == length, "private page changed during read")
    return raw


def page_accounting_totals(raw: bytes) -> dict[str, int]:
    """Read all five Extra payouts and the advertised whole-draw total.

    This is arithmetic performed on ONE informational operator-page copy,
    not an independent external certificate or a ticket-sales estimate.
    """
    visible = _flat_text(raw, "text/html")
    _require(visible.count(EXTRA_HEADING) == 1, "Extra table heading is missing or duplicated")
    extra_text = visible.split(EXTRA_HEADING, 1)[1]
    rows = list(EXTRA_ROW.finditer(extra_text))
    _require(len(rows) == 5, "Extra table must contain exactly five labeled rows")
    _require([row.group(1) for row in rows] == ["6", "5", "4", "3", "2"],
             "Extra prize tiers are missing, duplicated or out of order")
    extra_paid = 0
    for row in rows:
        count = int(row.group(2).replace(",", ""))
        payout = int(row.group(3).replace(",", ""))
        _require(count == 0 or payout > 0, "Extra winner has a nonpositive payout")
        extra_paid += count * payout
    totals = ALL_GAMES_TOTAL.findall(visible)
    _require(len(totals) == 1, "operator's all-games total is missing or ambiguous")
    return {"extra_paid": extra_paid, "all_games_paid": int(totals[0].replace(",", ""))}


def audit_one_private_page(
    *, draw_id: int, record: dict[str, Any], raw: bytes,
    candidate: dict[str, Any], history: LotteryDataset,
) -> None:
    """Compare preserved original, quarantine candidate, and source headline."""
    url = f"https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId={draw_id}"
    digest = hashlib.sha256(raw).hexdigest()
    metadata = candidate.get("candidate_source", {})
    _require(type(record.get("draw_id")) is int and record["draw_id"] == draw_id,
             f"#{draw_id}: manifest ID mismatch")
    _require(record.get("http_status") == 200 and record.get("final_response_url") == url,
             f"#{draw_id}: source response metadata mismatch")
    _require(record.get("status") == "16_TIERS_QUARANTINED_PENDING_HUMAN_REVIEW",
             f"#{draw_id}: manifest not quarantined")
    _require(record.get("parsed_tiers") == 16, f"#{draw_id}: manifest tier count mismatch")
    _require(record.get("raw_source_bytes") == len(raw)
             and record.get("raw_source_sha256") == digest,
             f"#{draw_id}: manifest does not match original bytes")
    _require(candidate.get("draw_id") == draw_id
             and candidate.get("status") == "quarantined_operator_page_capture_pending_human_review",
             f"#{draw_id}: candidate ID/status mismatch")
    _require(metadata.get("operator_page_claimed_url") == url
             and metadata.get("supplied_byte_count") == len(raw)
             and metadata.get("sha256_of_actual_supplied_bytes") == digest,
             f"#{draw_id}: candidate does not match original bytes")
    _require(candidate.get("auto_promoted_to_prize_observations") is False
             and candidate.get("eligible_for_expected_value") is False
             and metadata.get("approved_draw_protocol_verified") is False
             and metadata.get("source_authenticity_independently_verified") is False,
             f"#{draw_id}: ungrounded approval")
    fresh = extract_quarantined_prize_candidate(
        raw, content_type="text/html", draw_id=draw_id,
        captured_at_utc=metadata["captured_at_utc_supplied_by_researcher"],
        history=history,
    )
    _require(fresh["candidate_tiers"] == candidate.get("candidate_tiers"),
             f"#{draw_id}: re-extracted prize rows disagree")
    games_total = 0
    for game in ("regular", "double"):
        rows = fresh["candidate_tiers"][game]
        _require(len(rows) == 8, f"#{draw_id}: {game} tiers incomplete")
        for row in rows:
            count = row["winning_entries"]
            payout = row["payout_per_winning_entry_ils"]
            _require(type(count) is int and type(payout) is int and
                     count >= 0 and payout >= 0 and (count == 0 or payout > 0),
                     f"#{draw_id}: invalid {game} prize row")
            games_total += count * payout
    totals = page_accounting_totals(raw)
    _require(games_total + totals["extra_paid"] == totals["all_games_paid"],
             f"#{draw_id}: three-games payout does not match source headline")


def audit_private_cohort(folder: Path, history: LotteryDataset) -> dict[str, Any]:
    """Run 13-draw offline accounting with no output containing source values."""
    manifest = json.loads((folder / "private-capture-manifest.json").read_text(encoding="utf-8-sig"))
    _require(manifest.get("schema") == "lrei-p3-private-operator-page-batch-v1",
             "unsupported manifest schema")
    _require(manifest.get("status") == "ALL_CANDIDATES_QUARANTINED_NO_ADMISSION"
             and manifest.get("draw_ids_requested") == EXPECTED_IDS
             and manifest.get("pages_captured") == 13
             and manifest.get("draws_with_sixteen_tiers_quarantined") == 13
             and manifest.get("rows_approved_for_production") == 0
             and manifest.get("source_use_rights_verified") is False
             and manifest.get("binding_committee_protocol_verified") is False,
             "manifest coverage or provenance flags are invalid")
    records = manifest.get("captures")
    _require(isinstance(records, list) and len(records) == 13,
             "expected 13 source records")
    for i, draw_id in enumerate(EXPECTED_IDS):
        raw = _read_bounded(folder / f"draw-{draw_id}-operator-original.html")
        candidate = json.loads(
            (folder / f"draw-{draw_id}-quarantine-candidate.json").read_text(encoding="utf-8-sig")
        )
        audit_one_private_page(draw_id=draw_id, record=records[i], raw=raw,
                               candidate=candidate, history=history)
    return {
        "status": "PRIVATE_ACCOUNTING_MATCH_SOURCE_DISPLAY_ONLY",
        "draws_checked": 13,
        "regular_double_tiers_rechecked": 208,
        "extra_tiers_checked": 65,
        "all_games_totals_matched": 13,
        "public_data_republished": False,
        "source_authenticity_independently_verified": False,
        "approved_protocol_verified": False,
        "dataset_promotion_approved": False,
        "eligible_for_monetary_expected_value": False,
        "decision": "RESEARCH ONLY / NO PLAY",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--historical-csv", type=Path, required=True)
    args = parser.parse_args()
    try:
        history = CsvDatasetLoader().load(args.historical_csv)
        result = audit_private_cohort(args.private_dir, history)
    except (OSError, ValueError, KeyError, TypeError, PrizeDataError) as exc:
        parser.exit(2, f"Private P3 accounting REFUSED: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
