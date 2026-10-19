"""Execute the actual PR #35 Actions summary snippet against frozen fixtures.

All fixtures are synthetic. These tests do not certify source provenance,
refresh any draw history, or authorize real-money predictions.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github" / "workflows" / "lotto-dataset-freshness.yml"
)
STEP_NAME = "      - name: Explain operational readiness without weakening the gate\n"
HEREDOC = "python - <<'PY'\n"


def _real_workflow_summary_code() -> str:
    """Extract the Python actually executed by GitHub, without YAML extras."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count(STEP_NAME) == 1
    step = workflow.split(STEP_NAME, 1)[1].split("\n      - name:", 1)[0]
    assert "        if: always()\n" in step
    assert "        run: |\n" in step
    block = step.split("        run: |\n", 1)[1]
    lines = block.splitlines()
    assert all(not line or line.startswith("          ") for line in lines)
    script = "\n".join(line[10:] if line else "" for line in lines).strip()
    assert script.startswith(HEREDOC) and script.endswith("\nPY")
    return script[len(HEREDOC):-len("\nPY")]


def _run_summary(tmp_path: Path, report: object = None, *, raw: str | None = None) -> str:
    if report is not None or raw is not None:
        data_path = tmp_path / "audit-output" / "lotto-data-readiness.json"
        data_path.parent.mkdir()
        data_path.write_text(
            raw if raw is not None else json.dumps(report), encoding="utf-8"
        )
    summary_path = tmp_path / "summary.md"
    completed = subprocess.run(
        [sys.executable, "-c", _real_workflow_summary_code()],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return summary_path.read_text(encoding="utf-8")


def _report(**updates: object) -> dict[str, object]:
    data: dict[str, object] = {
        "status": "stale_dataset",
        "latest_draw_id": "3973",
        "latest_draw_date_israel": "2026-10-10",
        "age_days": 8,
        "max_age_days": 4,
        "data_recency_ok": False,
        "operator_source_provenance_verified": False,
        "authorized_for_financial_prediction": False,
    }
    data.update(updates)
    return data


def test_stale_report_prints_real_draw_and_red_gate(tmp_path: Path) -> None:
    message = _run_summary(tmp_path, _report())
    assert "`stale_dataset`" in message
    assert "**3973** (2026-10-10)" in message
    assert "**8** calendar days (limit: 4)" in message
    assert "Recency gate: **FAIL**" in message
    assert "Operator provenance remains unverified" in message
    assert "Financial-prediction authorization: NO" in message
    assert "Do not relax the age limit" in message


def test_fresh_by_age_does_not_grant_source_or_prediction_authorization(
    tmp_path: Path,
) -> None:
    message = _run_summary(
        tmp_path,
        _report(status="freshness_gate_passed", age_days=4, data_recency_ok=True),
    )
    assert "Recency gate: **PASS**" in message
    assert "Operator provenance remains unverified" in message
    assert "Financial-prediction authorization: NO" in message


def test_missing_report_is_visibly_unverified(tmp_path: Path) -> None:
    message = _run_summary(tmp_path)
    assert "check unavailable" in message
    assert "**unverified**" in message
    assert "PASS" not in message


@pytest.mark.parametrize(
    "report,raw",
    [
        (None, "{broken json"),
        ([], None),
        ({"status": "stale_dataset"}, None),
        (_report(age_days="unknown"), None),
    ],
)
def test_invalid_reports_never_create_positive_readiness(
    tmp_path: Path, report: object, raw: str | None,
) -> None:
    message = _run_summary(tmp_path, report, raw=raw)
    assert "invalid report" in message
    assert "**unverified**" in message
    assert "Recency gate: **PASS**" not in message


def test_summary_is_after_required_gate_and_never_suppresses_failure() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    check = "python -m lrei.lottery.dataset_freshness"
    assert workflow.index(check) < workflow.index(STEP_NAME)
    assert "continue-on-error: true" not in workflow
    assert "\n  pull_request:" not in workflow
    assert "schedule:" in workflow
    assert "Retain real recency report even on a red readiness gate" in workflow
