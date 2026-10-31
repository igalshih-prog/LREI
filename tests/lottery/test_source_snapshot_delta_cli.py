"""CLI exit codes and exclusive reports are part of the data-source safety contract."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HEAD = (
    "הגרלה,תאריך,1,2,3,4,5,6,המספר החזק/נוסף,"
    "מספר_זוכים_לוטו,מספר_זוכים_דאבל_לוטו,\r\n"
)
ROW_2833 = "2833,10/10/2016,01,04,07,22,32,34,2,0,0,\r\n"
ROW_2834 = "2834,13/10/2016,03,04,18,19,34,35,5,1,0,\r\n"


def _run(tmp_path: Path, current_rows: str, *, sha_override: str | None = None):
    old = (HEAD + ROW_2834 + ROW_2833).encode("cp1255")
    now = (HEAD + current_rows + ROW_2833).encode("cp1255")
    a, b, report = tmp_path / "old.csv", tmp_path / "new.csv", tmp_path / "delta.json"
    a.write_bytes(old)
    b.write_bytes(now)
    cmd = [sys.executable, "-m", "lrei.lottery.source_snapshot_delta",
           "--previous-source", str(a), "--current-source", str(b),
           "--expected-previous-sha256", sha_override or hashlib.sha256(old).hexdigest(),
           "--report", str(report)]
    env = os.environ.copy()
    source = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    return result, report, cmd, env


def test_cli_clean_comparison_exit_zero_and_exclusive_no_overwrite(tmp_path):
    result, report, cmd, env = _run(tmp_path, ROW_2834)
    assert result.returncode == 0
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "NO_NEW_ROWS_CHECK_FRESHNESS"
    second = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    assert second.returncode == 2
    assert "File exists" in second.stderr or "exists" in second.stderr


def test_cli_changed_winner_counts_exit_two_and_preserve_review_report(tmp_path):
    result, report, _, _ = _run(tmp_path, ROW_2834.replace(",5,1,0,", ",5,2,0,"))
    assert result.returncode == 2
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["status"] == "HISTORICAL_MISSING_OR_CHANGED_STOP_REVIEW"
    assert data["revised_prior_draw_ids"] == [2834]
    assert data["dataset_promotion_approved"] is False


def test_cli_reject_bad_expected_pin_without_success_report(tmp_path):
    result, report, _, _ = _run(tmp_path, ROW_2834, sha_override="0"*64)
    assert result.returncode == 2
    assert "SHA-256" in result.stderr
    assert not report.exists()
