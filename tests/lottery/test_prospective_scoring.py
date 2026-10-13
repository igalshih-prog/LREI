"""Focused tests for scoring future results without changing frozen predictions."""

import json
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from lrei.cli import app
from lrei.lottery.dataset import LotteryDrawRecord
from lrei.lottery.prospective_ledger import build_snapshot, write_snapshot, verify_snapshot
from lrei.lottery.prospective_scoring import score_snapshot, write_score


SHA = "f949eb8e3b5d8cca82997ec4cf0d6b48d907baef"
NOW = datetime(2026, 10, 13, 8, tzinfo=timezone.utc)
AFTER = datetime(2026, 10, 16, 8, tzinfo=timezone.utc)
SOURCE = "https://www.pais.co.il/lotto/example"


class FakeData:
    def __len__(self):
        return 1141

    def latest(self):
        return SimpleNamespace(draw_id="3973", date="10-10-26")


def record(tmp_path, target=None):
    path = tmp_path / "draws.csv"
    path.write_bytes(b"pre-draw-test-fixture")
    tickets = tuple(SimpleNamespace(
        numbers=tuple(range(i + 1, i + 7)), strong_number=(i % 7) + 1,
    ) for i in range(14))
    return build_snapshot(
        dataset_file=path, dataset=FakeData(), tickets=tickets, mode="smart",
        objective="coverage_any_prize", seed=42, generated_count=250,
        source_commit=SHA, created_at=NOW,
        target_draw_at=target or datetime(2026, 10, 15, 21, tzinfo=timezone(timedelta(hours=3))),
    )


def result():
    return LotteryDrawRecord("3974", (1, 2, 3, 4, 5, 6), date="15-10-26", strong_number=1)


def test_score_exact_prize_tiers_and_preserve_snapshot(tmp_path):
    frozen = record(tmp_path)
    original_hash = frozen["record_sha256"]
    scored = score_snapshot(frozen, result(), source_url=SOURCE, evaluated_at=AFTER)
    assert scored["snapshot_sha256"] == original_hash
    assert verify_snapshot(frozen)
    assert scored["best_main_matches"] == 6
    assert scored["best_prize_tier"] == 1
    assert scored["at_least_3_main"] and scored["at_least_4_main"] and scored["at_least_6_main"]
    assert scored["prize_tier_counts"]["1"] == 1
    assert scored["tickets"][0]["strong_match"] is True
    assert scored["source_independently_verified"] is False


def test_score_saved_without_overwriting_any_file(tmp_path):
    frozen = record(tmp_path)
    snapshot_path = write_snapshot(frozen, tmp_path / "snapshots")
    saved_original = snapshot_path.read_bytes()
    scored = score_snapshot(frozen, result(), source_url=SOURCE, evaluated_at=AFTER)
    destination = tmp_path / "results"
    path = write_score(scored, destination)
    assert json.loads(path.read_text())["result_sha256"] == scored["result_sha256"]
    with pytest.raises(FileExistsError):
        write_score(scored, destination)
    assert saved_original == snapshot_path.read_bytes()


def test_cannot_score_before_draw(tmp_path):
    with pytest.raises(ValueError, match="future"):
        score_snapshot(record(tmp_path), result(), source_url=SOURCE, evaluated_at=NOW)


@pytest.mark.parametrize("id,date", [
    ("3973", "15-10-26"), ("3972", "15-10-26"),
    ("wrong", "15-10-26"), ("3974", "16-10-26"),
])
def test_reject_wrong_result_identity(tmp_path, id, date):
    draw = LotteryDrawRecord(id, (1, 2, 3, 4, 5, 6), date=date, strong_number=1)
    with pytest.raises(ValueError):
        score_snapshot(record(tmp_path), draw, source_url=SOURCE, evaluated_at=AFTER)


def test_no_results_without_strong(tmp_path):
    draw = LotteryDrawRecord("3974", (1, 2, 3, 4, 5, 6), date="15-10-26")
    with pytest.raises(ValueError, match="strong"):
        score_snapshot(record(tmp_path), draw, source_url=SOURCE, evaluated_at=AFTER)


def test_reject_tampered_snapshot_and_bad_source(tmp_path):
    frozen = record(tmp_path)
    frozen["seed"] = 99
    with pytest.raises(ValueError, match="checksum"):
        score_snapshot(frozen, result(), source_url=SOURCE, evaluated_at=AFTER)
    frozen = record(tmp_path)
    with pytest.raises(ValueError, match="HTTPS"):
        score_snapshot(frozen, result(), source_url="http://example.com", evaluated_at=AFTER)


def test_timezone_boundary_preserves_local_date(tmp_path):
    target = datetime(2026, 10, 15, 0, 30, tzinfo=timezone(timedelta(hours=3)))
    frozen = record(tmp_path, target=target)
    assert frozen["target_draw_at_utc"].startswith("2026-10-14")
    assert frozen["target_draw_date_local"] == "2026-10-15"
    scored = score_snapshot(frozen, result(), source_url=SOURCE, evaluated_at=AFTER)
    assert scored["draw"]["date"] == "2026-10-15"


def test_cli_rejects_not_yet_occurred_draw(tmp_path):
    frozen = record(tmp_path, target=datetime(2099, 10, 15, 21, tzinfo=timezone(timedelta(hours=3))))
    snapshot = write_snapshot(frozen, tmp_path / "snapshots")
    response = CliRunner().invoke(app, [
        "score-snapshot", str(snapshot), "--draw-id", "3974",
        "--draw-date", "2099-10-15", "--main", "1,2,3,4,5,6", "--strong", "1",
        "--source-url", SOURCE, "--output-dir", str(tmp_path / "scores"),
    ])
    # A far-future registered draw cannot be scored yet.
    assert response.exit_code != 0
    assert "future" in response.output
