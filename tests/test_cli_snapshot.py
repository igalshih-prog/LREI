"""Focused CLI tests for the opt-in prospective snapshot path."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from typer.testing import CliRunner

import lrei.cli as cli
from lrei.lottery.prospective_ledger import build_snapshot, verify_snapshot
from lrei.lottery.recommendation import RecommendationResult, RecommendedTicket


runner = CliRunner()


def test_snapshot_requires_target_and_directory():
    missing_target = runner.invoke(cli.app, ["recommend", "--snapshot-dir", "records"])
    assert missing_target.exit_code != 0
    assert "provided together" in missing_target.output

    missing_directory = runner.invoke(
        cli.app, ["recommend", "--target-draw-at", "2099-01-01T21:00:00+03:00"]
    )
    assert missing_directory.exit_code != 0
    assert "provided together" in missing_directory.output


def test_snapshot_rejects_missing_timezone_without_generating_tickets(tmp_path):
    result = runner.invoke(
        cli.app, [
            "recommend", "--snapshot-dir", str(tmp_path),
            "--target-draw-at", "2099-01-01T21:00:00",
        ],
    )
    assert result.exit_code != 0
    assert "timezone" in result.output
    assert list(tmp_path.iterdir()) == []


def test_cli_saves_valid_snapshot_without_running_historical_benchmarks(tmp_path, monkeypatch):
    tickets = tuple(
        RecommendedTicket(
            numbers=tuple(range(i + 1, i + 7)),
            strong_number=(i % 7) + 1,
        )
        for i in range(14)
    )
    recommendation = RecommendationResult(
        scores=(),
        generated_tickets=tuple(ticket.numbers for ticket in tickets),
        recommended_tickets=tuple(ticket.numbers for ticket in tickets),
        recommended_tickets_with_strong=tickets,
    )
    monkeypatch.setattr(
        cli, "EliteProRecommendationEngine",
        lambda: SimpleNamespace(recommend=lambda dataset, seed: recommendation),
    )
    monkeypatch.setattr(
        cli.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="f949eb8e3b5d8cca82997ec4cf0d6b48d907baef\n"
        ),
    )
    frozen = datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        cli, "build_snapshot",
        lambda **kwargs: build_snapshot(**kwargs, created_at=frozen),
    )
    folder = tmp_path / "snapshots"
    response = runner.invoke(
        cli.app,
        [
            "recommend", "--mode", "elite", "--seed", "42",
            "--snapshot-dir", str(folder),
            "--target-draw-at", "2099-01-01T21:00:00+03:00",
        ],
    )
    assert response.exit_code == 0, response.output
    assert "Pre-draw snapshot:" in response.output
    paths = list(folder.glob("*.json"))
    assert len(paths) == 1
    record = json.loads(paths[0].read_text(encoding="utf-8"))
    assert verify_snapshot(record)
    assert record["source_commit"] == "f949eb8e3b5d8cca82997ec4cf0d6b48d907baef"
    assert record["seed"] == 42
    assert record["ticket_count"] == 14
    assert record["mode"] == "elite"


def test_cli_documents_fixed_fourteen_ticket_contract():
    output = runner.invoke(cli.app, ["recommend", "--help"])
    assert output.exit_code == 0
    # Rich uses ANSI markup and wraps descriptions to terminal width.
    import re
    plain = re.sub(r"\x1b\[[0-9;]*m", "", output.output)
    assert "Regular-mode" in plain
    assert "14" in plain
