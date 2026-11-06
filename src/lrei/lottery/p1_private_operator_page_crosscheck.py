"""Private, fail-closed two-endpoint operator-results crosscheck (#3974–3981).

Compare a retained first-party-style original CSV to separately requested
individual operator draw HTML pages over normal HTTPS/TLS. The site itself
calls published results informational/nonbinding; even a full content match
DOES NOT authenticate a signed draw protocol, grant redistribution rights,
permit data promotion or establish a predictive advantage.

This is a one-time, personal/noncommercial source-verification aid.
NEVER commit raw HTML, CSV or private reports to a public repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

from .p3_private_accounting_audit import page_accounting_totals
from .prize_data import PrizeDataError
from .source_capture_check import (
    MAX_CAPTURE_BYTES, _DOUBLE_HEADING, _EXTRA_HEADING,
    _OFFICIAL_HEADING, _REGULAR_HEADING, _flat_text, _rows_from_section,
)
from .source_snapshot_delta import SourceSnapshotError, parse_snapshot, read_source_bounded

START = 3974
END = 3981
IDS = tuple(range(START, END + 1))
SOURCE_URL = "https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId={}"
TIER_LABELS = ("6+strong", "6", "5+strong", "5", "4+strong", "4", "3+strong", "3")
RESULT_MARKER = "הגרלת הלוטו"
STRONG_AND_NUMBERS = re.compile(
    r"\b([1-7])\s+המספר\s+החזק\s+"
    r"([0-9]{1,2}(?:\s+[0-9]{1,2}){5})\s+הגרלת\s+הלוטו\b"
)
DRAW_DATE = re.compile(r"(?<!\d)(\d{2}/\d{2}/\d{4})(?!\d)")
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")


class PrivateSourceError(ValueError):
    """The offline/online comparison could not establish a valid content match."""


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise PrivateSourceError(message)


def inspect_operator_page(
    raw: bytes, *, draw_id: int, expected: tuple[str, tuple[int, ...], int, int, int]
) -> dict[str, Any]:
    """Strict page identity, 6/37+strong, 2 top-tier counts and total accounting.

    Expectation is the independently obtained *CSV contents*, not a signed
    protocol. No report contains actual number selections or prize amounts.
    """
    _need(type(draw_id) is int and draw_id in IDS, "draw not in fixed reviewed range")
    visible = _flat_text(raw, "text/html")
    headings = _OFFICIAL_HEADING.findall(visible)
    _need(headings == [str(draw_id)], "draw heading absent/ambiguous/wrong")
    reg = visible.find(_REGULAR_HEADING)
    dbl = visible.find(_DOUBLE_HEADING)
    _need(reg >= 0 and dbl > reg and visible.count(_REGULAR_HEADING) == 1
          and visible.count(_DOUBLE_HEADING) == 1,
          "regular/double sections missing or duplicated")
    prefix = visible[:reg]
    _need(prefix.count(RESULT_MARKER) == 1, "outcome section absent/ambiguous")
    # Enforce date, main numbers and strong in the actual outcome section,
    # not in unrelated scripts/prize-tier rows elsewhere on the same page.
    dates = DRAW_DATE.findall(prefix)
    date_display = date.fromisoformat(expected[0]).strftime("%d/%m/%Y")
    _need(dates == [date_display], "draw date differs from operator CSV")
    selections = list(STRONG_AND_NUMBERS.finditer(prefix))
    _need(len(selections) == 1, "outcome strong/six-number layout changed or duplicated")
    strong = int(selections[0].group(1))
    mains = tuple(int(i) for i in selections[0].group(2).split())
    _need(len(mains) == 6 and len(set(mains)) == 6
          and mains == tuple(sorted(mains))
          and all(1 <= n <= 37 for n in mains) and 1 <= strong <= 7,
          "invalid six-of-37 outcome")
    _need((mains, strong) == (expected[1], expected[2]),
          "six main numbers or strong disagree with separate original CSV")
    extra = visible.find(_EXTRA_HEADING, dbl)
    _need(extra > dbl, "Extra heading missing or ordered incorrectly")
    regular_rows = _rows_from_section(visible[reg + len(_REGULAR_HEADING):dbl], game="regular")
    double_rows = _rows_from_section(visible[dbl + len(_DOUBLE_HEADING):extra], game="double")
    _need(tuple(row["tier"] for row in regular_rows) == TIER_LABELS
          and tuple(row["tier"] for row in double_rows) == TIER_LABELS,
          "prize tiers missing/duplicated/reordered")
    _need(regular_rows[0]["winning_entries"] == expected[3]
          and double_rows[0]["winning_entries"] == expected[4],
          "first-prize winner counts disagree with operator CSV")
    paid = 0
    for rows in (regular_rows, double_rows):
        for row in rows:
            n, p = row["winning_entries"], row["payout_per_winning_entry_ils"]
            _need(type(n) is int and type(p) is int and n >= 0 and p >= 0
                  and (n == 0 or p > 0),
                  "invalid payout/count in source page")
            paid += n * p
    amounts = page_accounting_totals(raw)
    _need(paid + amounts["extra_paid"] == amounts["all_games_paid"],
          "all-games source page arithmetic mismatch")
    return {
        "draw_id": draw_id,
        "page_original_sha256": hashlib.sha256(raw).hexdigest(),
        "page_original_bytes": len(raw),
        "draw_date_main_strong_match": True,
        "regular_double_first_prize_counts_match": True,
        "all_games_source_arithmetic_match": True,
        "regular_double_tiers_checked": 16,
        "extra_tiers_checked": 5,
        "source_authenticity_independently_attested": False,
        "signed_operator_protocol_verified": False,
        "dataset_admission_approved": False,
    }


def _https_page(draw_id: int) -> bytes:
    """One bounded request, standard certificate checks, NO redirects or retries."""
    _need(draw_id in IDS, "invalid draw")
    url = SOURCE_URL.format(draw_id)
    req = request.Request(url, headers={
        "User-Agent": "LREI-research-source-check/1.0 (personal noncommercial review)",
        "Accept": "text/html",
    })
    client = request.build_opener(
        _NoRedirect(),
        request.HTTPSHandler(context=ssl.create_default_context()),
    )
    with client.open(req, timeout=30) as response:
        _need(response.status == 200 and response.geturl() == url,
              "operator HTTPS response URL or status is unexpected")
        _need(response.headers.get_content_type().lower() == "text/html",
              "operator response is not HTML")
        header_bytes = response.headers.get("Content-Length")
        if header_bytes is not None:
            _need(int(header_bytes) <= MAX_CAPTURE_BYTES, "operator page too large")
        raw = response.read(MAX_CAPTURE_BYTES + 1)
    _need(1000 <= len(raw) <= MAX_CAPTURE_BYTES, "operator HTML too small or too large")
    return raw


def _source_csv(path: Path, expected_sha256: str) -> dict[int, tuple]:
    _need(HEX_SHA.fullmatch(expected_sha256) is not None,
          "source SHA-256 pin malformed")
    raw = read_source_bounded(path)
    _need(hashlib.sha256(raw).hexdigest() == expected_sha256,
          "original CSV source SHA-256 mismatch")
    snapshot = parse_snapshot(raw)
    _need(snapshot["ids"][-1] == END, "pinned source CSV latest draw differs from 3981")
    _need(all(i in snapshot["draws"] for i in IDS), "source CSV missing modern draws")
    return snapshot["draws"]


def private_crosscheck(
    *, csv_path: Path, csv_sha256: str, private_root: Path,
    fetch_page: Any = _https_page, sleep: Any = time.sleep,
) -> dict[str, Any]:
    """Fixed eight-page audit. Raw originals only in unique PRIVATE folder."""
    expected = _source_csv(csv_path, csv_sha256)
    if not private_root.is_dir():
        raise PrivateSourceError("private output parent directory is absent")
    folder = Path(tempfile.mkdtemp(prefix="LREI-P1-pages-private-", dir=private_root))
    records: list[dict[str, Any]] = []
    status = "PARTIAL_OR_REFUSED_KEEP_PRIVATE"
    try:
        for pos, draw_id in enumerate(IDS):
            if pos:
                sleep(3)
            raw = fetch_page(draw_id)
            checked = inspect_operator_page(raw, draw_id=draw_id, expected=expected[draw_id])
            # Do not retain any rejected bytes. Private file exclusive-create.
            with (folder / f"draw-{draw_id}-operator-original.html").open("xb") as out:
                out.write(raw)
            checked["source_url"] = SOURCE_URL.format(draw_id)
            checked["response_transport"] = "https_certificate_checked_by_python"
            records.append(checked)
        status = "EIGHT_OPERATOR_PAGES_CROSS_ENDPOINT_CONTENT_MATCH_ONLY"
        return {
            "status": status,
            "draws_checked": len(records),
            "all_draw_outcomes_matched": len(records),
            "first_prize_winner_counts_matched": 2 * len(records),
            "regular_double_tiers_reparsed": 16 * len(records),
            "extra_tiers_reparsed": 5 * len(records),
            "page_accounting_matches": len(records),
            "source_authenticity_independently_attested": False,
            "signed_operator_protocol_verified": False,
            "public_redistribution_rights_verified": False,
            "dataset_admission_approved": False,
            "eligible_for_monetary_or_predictive_claim": False,
            "research_only_no_play": True,
            "private_evidence_directory": str(folder),
        }
    finally:
        metadata = {
            "schema": "lrei-p1-private-cross-endpoint-v1",
            "status": status,
            "source_csv_sha256": csv_sha256,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "requested_draw_ids": list(IDS),
            "completed_draws": len(records),
            "records": records,
            "draw_committee_protocol_verified": False,
            "public_reuse_rights_verified": False,
            "source_attested_by_independent_party": False,
            "dataset_promotion_approved": False,
            "research_only_no_play": True,
        }
        with (folder / "private-capture-manifest.json").open("x", encoding="utf-8") as out:
            json.dump(metadata, out, ensure_ascii=False, indent=2, sort_keys=True)
            out.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = private_crosscheck(csv_path=args.source_csv,
                                    csv_sha256=args.source_sha256,
                                    private_root=args.private_root)
    except (PrivateSourceError, SourceSnapshotError, PrizeDataError, OSError, ValueError,
            KeyError, TypeError) as exc:
        parser.exit(2, f"Private cross-endpoint audit REFUSED: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
