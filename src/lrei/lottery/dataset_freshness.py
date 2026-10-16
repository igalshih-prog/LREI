"""Independent *operational* data-recency gate for Lotto draw history.

Repository structure/unit tests should not fail just because wall-clock time
advances. This separate gate stays RED when history is stale. It never asserts
that the CSV came from the operator or that a future draw may be predicted.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .dataset import CsvDatasetLoader, LotteryDataset, parse_draw_date

MAX_HISTORY_AGE_DAYS = 4
ISRAEL = ZoneInfo("Asia/Jerusalem")


def inspect_freshness(
    dataset: LotteryDataset,
    *,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    """Report actual age under the fixed four-day Israel-local policy.

    This report is intentionally separate from official-source authentication.
    """
    checked_at = checked_at or datetime.now(timezone.utc)
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("checked_at must include an explicit timezone")
    if not len(dataset):
        raise ValueError("cannot assess an empty draw dataset")
    latest = dataset.latest()
    latest_date = parse_draw_date(latest.date)
    if latest_date is None:
        raise ValueError("latest draw is missing a valid date")
    today_israel = checked_at.astimezone(ISRAEL).date()
    age_days = (today_israel - latest_date).days
    if age_days < 0:
        status = "future_dated_dataset"
    elif age_days > MAX_HISTORY_AGE_DAYS:
        status = "stale_dataset"
    else:
        status = "freshness_gate_passed"
    return {
        "schema_version": 1,
        "status": status,
        "latest_draw_id": str(latest.draw_id),
        "latest_draw_date_israel": latest_date.isoformat(),
        "checked_at_utc": checked_at.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "today_israel": today_israel.isoformat(),
        "age_days": age_days,
        "max_age_days": MAX_HISTORY_AGE_DAYS,
        "data_recency_ok": status == "freshness_gate_passed",
        "operator_source_provenance_verified": False,
        "authorized_for_financial_prediction": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check operational freshness of the current Lotto dataset."
    )
    parser.add_argument("--dataset", type=Path, default=Path("data/lottery.csv"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = inspect_freshness(CsvDatasetLoader().load(args.dataset))
        if args.report is not None:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Data freshness check error: {exc}\n")
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    if not result["data_recency_ok"]:
        parser.exit(
            2,
            "Lotto history is stale/future-dated: latest draw ID "
            f"{result['latest_draw_id']} dated "
            f"{result['latest_draw_date_israel']}; "
            "obtain authenticated latest results before research or forecasts.\n",
        )


if __name__ == "__main__":
    main()
