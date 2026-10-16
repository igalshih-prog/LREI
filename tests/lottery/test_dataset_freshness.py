"""Frozen-clock checks for operational draw recency.

No real-world draw date is hardcoded as a success condition: production will
report red whenever the checked CSV is genuinely stale.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from lrei.lottery.dataset_freshness import MAX_HISTORY_AGE_DAYS, inspect_freshness


class History:
    def __init__(self, draw_id="3973", date="13-10-26"):
        self.row = SimpleNamespace(draw_id=draw_id, date=date)

    def __len__(self):
        return 1

    def latest(self):
        return self.row


# UTC Oct 16 at 21:30 is local Israel Oct 17 at 00:30.
LOCAL_MIDNIGHT = datetime(2026, 10, 16, 21, 30, tzinfo=timezone.utc)


def test_freshness_uses_israel_calendar_not_utc_calendar():
    report = inspect_freshness(History(date="13-10-26"), checked_at=LOCAL_MIDNIGHT)
    assert report["today_israel"] == "2026-10-17"
    assert report["age_days"] == 4
    assert report["max_age_days"] == MAX_HISTORY_AGE_DAYS == 4
    assert report["status"] == "freshness_gate_passed"
    assert report["data_recency_ok"] is True
    assert report["operator_source_provenance_verified"] is False
    assert report["authorized_for_financial_prediction"] is False


@pytest.mark.parametrize("date,age,status,ready", [
    ("12-10-26", 5, "stale_dataset", False),
    ("13-10-26", 4, "freshness_gate_passed", True),
    ("17-10-26", 0, "freshness_gate_passed", True),
    ("18-10-26", -1, "future_dated_dataset", False),
])
def test_calendar_age_boundary_cannot_be_bypassed(date, age, status, ready):
    report = inspect_freshness(History(date=date), checked_at=LOCAL_MIDNIGHT)
    assert report["age_days"] == age
    assert report["status"] == status
    assert report["data_recency_ok"] is ready


def test_old_main_dataset_explicitly_red_under_a_frozen_reference_clock():
    report = inspect_freshness(
        History("3973", "10-10-26"),
        checked_at=datetime(2026, 10, 16, 12, tzinfo=timezone.utc),
    )
    assert report["latest_draw_id"] == "3973"
    assert report["age_days"] == 6
    assert report["data_recency_ok"] is False
    assert report["status"] == "stale_dataset"


def test_wrong_clock_and_invalid_draw_date_fail_closed():
    with pytest.raises(ValueError, match="explicit timezone"):
        inspect_freshness(History(), checked_at=datetime(2026, 10, 16, 21, 30))
    with pytest.raises(ValueError, match="valid date"):
        inspect_freshness(History(date="missing"), checked_at=LOCAL_MIDNIGHT)


def test_utc_offset_equivalence_for_the_same_instant():
    plus_three = LOCAL_MIDNIGHT.astimezone(timezone(timedelta(hours=3)))
    utc = inspect_freshness(History(), checked_at=LOCAL_MIDNIGHT)
    israel_offset = inspect_freshness(History(), checked_at=plus_three)
    assert utc == israel_offset


def test_empty_dataset_rejected():
    class Empty:
        def __len__(self):
            return 0

        def latest(self):
            raise RuntimeError("must not reach")
    with pytest.raises(ValueError, match="empty"):
        inspect_freshness(Empty(), checked_at=LOCAL_MIDNIGHT)


def test_cli_exit_nonzero_and_preserves_auditable_staleness_report(tmp_path):
    # A real command invocation must visibly fail, not just set an in-memory flag.
    archive = tmp_path / "stale.csv"
    archive.write_text(
        'draw_id,numbers,date,strong_number\\n'
        '3973,"1,2,3,4,5,6",10-10-20,7\\n',
        encoding="utf-8",
    )
    report_path = tmp_path / "audit" / "recency.json"
    invoked = subprocess.run(
        [
            sys.executable, "-m", "lrei.lottery.dataset_freshness",
            "--dataset", str(archive), "--report", str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert invoked.returncode == 2
    assert "stale" in invoked.stderr.lower()
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "stale_dataset"
    assert report["data_recency_ok"] is False
    assert report["operator_source_provenance_verified"] is False
    assert report["authorized_for_financial_prediction"] is False


def test_operational_workflow_keeps_recency_red_separate_from_pr_checks():
    path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "lotto-dataset-freshness.yml"
    text = path.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" in text
    assert "\\n  pull_request:" not in text
    assert "python -m lrei.lottery.dataset_freshness" in text
    assert "if: always()" in text
