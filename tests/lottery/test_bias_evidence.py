"""Focused prospective-only checks for the pre-registered P2 bias hypothesis."""

from datetime import datetime, timedelta, timezone
from itertools import combinations
from math import comb, exp, log
from pathlib import Path
import json

import pytest
from typer.testing import CliRunner

from lrei.lottery.bias_evidence import (
    PROTOCOL, EVIDENCE_LOG_THRESHOLD, elementary_symmetric, freeze_bias_model,
    score_future_draw, verify_frozen_model, verify_evidence_record, write_immutable,
)
from lrei.lottery.dataset import LotteryDataset, LotteryDrawRecord
import lrei.cli as cli


SHA = "a" * 40
CREATED = datetime(2026, 10, 13, 7, tzinfo=timezone.utc)
FIRST_AT = datetime(2026, 10, 13, 21, tzinfo=timezone(timedelta(hours=3)))
SECOND_AT = datetime(2026, 10, 15, 21, tzinfo=timezone(timedelta(hours=3)))
AFTER = datetime(2026, 10, 16, tzinfo=timezone.utc)
SOURCE = "https://www.pais.co.il/lotto/official-results-placeholder"


def archive():
    return LotteryDataset(
        LotteryDrawRecord(
            draw_id=str(3000 + j),
            numbers=tuple(sorted(((j * 7 + i) % 37) + 1 for i in range(6))),
            date="10-10-26",
            strong_number=1 + j % 7,
        )
        for j in range(120)
    )


def frozen(tmp_path):
    data = tmp_path / "training.csv"
    data.write_bytes(b"synthetic-training")
    return freeze_bias_model(archive(), data, SHA, created_at=CREATED)


def actual(which=0):
    return LotteryDrawRecord(
        draw_id=str(3120 + which),
        numbers=(1, 2, 3, 4, 5, 6) if which == 0 else (8, 9, 10, 11, 12, 13),
        date="13-10-26" if which == 0 else "15-10-26",
        strong_number=1 if which == 0 else 2,
    )


def score(model, which=0, previous=None, **kwargs):
    return score_future_draw(
        model, actual(which),
        draw_occurred_at=FIRST_AT if which == 0 else SECOND_AT,
        source_url=SOURCE,
        evaluated_at=AFTER,
        previous=previous,
        **kwargs,
    )


def test_elementary_symmetric_is_exact_partition_function():
    # Enumerate a genuinely distinct smaller game to independently check DP.
    weights = (1.0, 1.1, 2.2, 3.3, 0.7)
    norm = elementary_symmetric(weights, degree=2)
    brute = sum(w[i] * w[j] for i, j in combinations(range(5), 2))
    assert norm == pytest.approx(brute)
    increments = [comb(5, 2) * weights[i] * weights[j] / norm for i, j in combinations(range(5), 2)]
    assert sum(increments) / comb(5, 2) == pytest.approx(1.0)


def test_freeze_fixes_one_alternative_without_consuming_future_draw(tmp_path):
    model = frozen(tmp_path)
    assert verify_frozen_model(model)
    assert model["protocol"] == PROTOCOL
    assert model["training_draw_count"] == 120
    assert model["cutoff_draw_id"] == "3119"
    assert model["primary_null"] == "independent_uniform_6_of_37_main_draws"
    assert model["fixed_evidence_threshold"] == 20.0
    assert len(model["weights"]) == 37
    assert sum(model["number_counts"]) == 720
    assert "cumulative_log_e" not in model


def test_scoring_first_and_next_draw_is_consecutive_and_exact(tmp_path):
    model = frozen(tmp_path)
    first = score(model)
    second = score(model, which=1, previous=first)
    assert verify_evidence_record(first) and verify_evidence_record(second)
    assert first["draw_number"] == 1 and second["draw_number"] == 2
    assert second["previous_record_sha256"] == first["record_sha256"]
    assert first["source_independently_verified"] is False
    assert second["cumulative_log_e"] == pytest.approx(
        first["log_likelihood_ratio_increment"] + second["log_likelihood_ratio_increment"]
    )
    assert second["peak_log_e"] >= second["cumulative_log_e"]
    assert second["anytime_valid_evidence_threshold_ever_reached"] == (
        second["peak_log_e"] >= EVIDENCE_LOG_THRESHOLD
    )
    weights = model["weights"]
    normalizer = elementary_symmetric(weights, degree=6)
    independent = log(comb(37, 6)) - log(normalizer) + sum(log(weights[i]) for i in range(6))
    assert first["log_likelihood_ratio_increment"] == pytest.approx(independent)


def test_model_or_previous_record_tampering_fails(tmp_path):
    model = frozen(tmp_path)
    model["weights"][0] *= 3
    assert not verify_frozen_model(model)
    with pytest.raises(ValueError, match="tampered"):
        score(model)
    model = frozen(tmp_path)
    first = score(model)
    first["cumulative_log_e"] = 1000000
    with pytest.raises(ValueError, match="previous"):
        score(model, which=1, previous=first)


def test_cannot_start_at_second_draw_or_repeat_first(tmp_path):
    model = frozen(tmp_path)
    with pytest.raises(ValueError, match="exactly 3120"):
        score(model, which=1)
    first = score(model)
    with pytest.raises(ValueError, match="exactly 3121"):
        score(model, which=0, previous=first)


@pytest.mark.parametrize("bad_time", [
    CREATED - timedelta(seconds=1),
    CREATED,
    datetime(2099, 10, 13, 21, tzinfo=timezone.utc),
])
def test_future_draw_gate_rejects_wrong_timing(tmp_path, bad_time):
    model = frozen(tmp_path)
    with pytest.raises(ValueError, match="after|before|date"):
        score_future_draw(
            model, actual(0), draw_occurred_at=bad_time,
            evaluated_at=AFTER, source_url=SOURCE,
        )


def test_local_day_and_result_integrity_and_https_are_mandatory(tmp_path):
    model = frozen(tmp_path)
    wrong_date = LotteryDrawRecord("3120", (1, 2, 3, 4, 5, 6), date="15-10-26", strong_number=1)
    with pytest.raises(ValueError, match="local date"):
        score_future_draw(model, wrong_date, draw_occurred_at=FIRST_AT, source_url=SOURCE, evaluated_at=AFTER)
    with pytest.raises(ValueError, match="HTTPS"):
        score_future_draw(model, actual(), draw_occurred_at=FIRST_AT, source_url="http://example.org", evaluated_at=AFTER)
    missing_strong = LotteryDrawRecord("3120", (1, 2, 3, 4, 5, 6), date="13-10-26")
    with pytest.raises(ValueError, match="strong"):
        score_future_draw(model, missing_strong, draw_occurred_at=FIRST_AT, source_url=SOURCE, evaluated_at=AFTER)


def test_write_immutable_never_overwrites_and_preserves_evidence_chain(tmp_path):
    model = frozen(tmp_path)
    frozen_path = write_immutable(model, tmp_path / "audit")
    original = frozen_path.read_bytes()
    with pytest.raises(FileExistsError):
        write_immutable(model, tmp_path / "audit")
    result = score(model)
    path = write_immutable(result, tmp_path / "audit")
    assert json.loads(path.read_text())["previous_record_sha256"] is None
    assert frozen_path.read_bytes() == original
    with pytest.raises(FileExistsError):
        write_immutable(result, tmp_path / "audit")


def test_train_history_must_be_recent_and_consecutive(tmp_path):
    path = tmp_path / "training.csv"
    path.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="old"):
        freeze_bias_model(archive(), path, SHA, created_at=datetime(2026, 11, 1, tzinfo=timezone.utc))
    draws = list(archive().draws)
    damaged = LotteryDataset(draws[:30] + draws[31:])
    with pytest.raises(ValueError, match="consecutive"):
        freeze_bias_model(damaged, path, SHA, created_at=CREATED)


def test_cli_freeze_serializes_model_without_fake_future_outcomes(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "CsvDatasetLoader", lambda: type(
        "Loader", (), {"load": lambda self, path: archive()}
    )())
    monkeypatch.setattr(
        cli.subprocess, "run",
        lambda *args, **kwargs: type("Git", (), {"stdout": SHA + "\n"})(),
    )
    monkeypatch.setattr(
        cli, "freeze_bias_model",
        lambda dataset, file, sha: freeze_bias_model(
            dataset, tmp_path / "source.csv", sha, created_at=CREATED,
        ),
    )
    (tmp_path / "source.csv").write_bytes(b"training")
    result = CliRunner().invoke(cli.app, ["bias-freeze", "--output-dir", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    records = list((tmp_path / "out").glob("*.json"))
    assert len(records) == 1
    assert verify_frozen_model(json.loads(records[0].read_text()))


def test_cli_future_input_cannot_be_counted_before_draw(tmp_path):
    model = frozen(tmp_path)
    path = write_immutable(model, tmp_path / "frozen")
    result = CliRunner().invoke(cli.app, [
        "bias-score", "--frozen", str(path), "--draw-id", "3120",
        "--draw-date", "13-10-99", "--draw-at", "2099-10-13T21:00:00+03:00",
        "--main", "1,2,3,4,5,6", "--strong", "1", "--source-url", SOURCE,
        "--output-dir", str(tmp_path / "result"),
    ])
    assert result.exit_code != 0
    assert "before it takes place" in result.output
    assert not (tmp_path / "result").exists()
