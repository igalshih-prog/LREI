"""Focused prospective batch correctness without lottery draws or paid tickets."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from lrei.lottery import prospective_batch as batch
from lrei.lottery.prospective_ledger import verify_snapshot


SOURCE = "a" * 40
NOW = datetime(2026, 10, 16, 7, 0, tzinfo=timezone.utc)
TARGET = datetime(2026, 10, 17, 23, 0, tzinfo=timezone(timedelta(hours=3)))
SOURCE_URL = "https://www.pais.co.il/lotto/archive.aspx"


class History:
    def __init__(self, id="3975", date="15-10-26"):
        self.record = SimpleNamespace(draw_id=id, date=date)

    def __len__(self):
        return 1141

    def latest(self):
        return self.record


def grid_lines():
    grid = tuple(tuple(r * 6 + c + 1 for c in range(6)) for r in range(6))
    tickets = (
        list(grid)
        + [tuple(grid[r][c] for r in range(6)) for c in range(6)]
        + [
            tuple(grid[r][r] for r in range(6)),
            tuple(grid[r][(r + 1) % 6] for r in range(6)),
        ]
    )
    assert len(tickets) == 14
    return tickets


@pytest.fixture
def stub_smart(monkeypatch):
    calls = []

    class FakeEngine:
        def __init__(self, config):
            assert config.objective == "coverage_5plus"
            calls.append(config.objective)

        def recommend(self, dataset, seed):
            assert len(dataset) == 1141
            lines = tuple(
                SimpleNamespace(numbers=main, strong_number=(i % 7) + 1)
                for i, main in enumerate(grid_lines())
            )
            return SimpleNamespace(
                recommended_tickets_with_strong=lines,
                generated_tickets=tuple(range(1000)),
            )

    monkeypatch.setattr(batch, "SmartRecommendationEngine", FakeEngine)
    return calls


def construct(tmp_path, **changes):
    csv = tmp_path / "data.csv"
    csv.write_bytes(b"synthetic-draw-cutoff-no-real-results")
    kwargs = {
        "historical": History(),
        "dataset_file": csv,
        "source_commit": SOURCE,
        "target_draw_id": 3976,
        "target_draw_at": TARGET,
        "schedule_reference_url": SOURCE_URL,
        "schedule_reviewed": True,
        "now": NOW,
    }
    kwargs.update(changes)
    return batch.build_paper_batch(**kwargs)


def test_reproducible_equal_ticket_budget_and_unverified_metadata(tmp_path, stub_smart):
    first = construct(tmp_path)
    second = construct(tmp_path)
    assert first == second
    assert stub_smart == ["coverage_5plus", "coverage_5plus"]
    assert verify_snapshot(first["smart"])
    assert first["smart"]["ticket_count"] == 14
    assert first["smart"]["reported_generated_count"] == 1000
    assert first["manifest"]["latest_draw"] == {"id": "3975", "date": "2026-10-15"}
    assert first["manifest"]["target_draw_id"] == 3976
    assert first["manifest"]["target_draw_date_local"] == "2026-10-17"
    assert first["manifest"]["money_wagered_ils"] == 0
    assert first["manifest"]["official_source_provenance_verified"] is False
    assert first["manifest"]["independent_pre_draw_publication_verified"] is False
    assert first["manifest"]["contains_actual_draw_result"] is False
    assert first["manifest"]["primary_analysis_metric"] == "paired_any_3plus_main_portfolio_rate"
    assert len(first["controls"]) == 3
    assert set(first["controls"]) == {"random_seed_1042", "random_seed_1043", "random_seed_1044"}
    assert len({
        tuple(ticket["main"])
        for record in first["controls"].values()
        for ticket in record["tickets"]
    }) >= 14
    for record in first["controls"].values():
        assert record["ticket_count"] == 14
        assert len({tuple(ticket["main"]) for ticket in record["tickets"]}) == 14
        assert all(1 <= t["strong"] <= 7 for t in record["tickets"])
        assert record["source_commit"] == first["smart"]["source_commit"]
        assert record["dataset_sha256"] == first["smart"]["dataset_sha256"]
        assert record["record_sha256"] == batch._hash({
            key: value for key, value in record.items() if key != "record_sha256"
        })


def test_write_is_exclusive_and_preserves_all_five_files(tmp_path, stub_smart):
    b = construct(tmp_path)
    output = tmp_path / "future" / "draw3976"
    saved = batch.write_paper_batch(b, output)
    files = sorted(p.name for p in saved.glob("*.json"))
    assert files == [
        "manifest.json", "random_seed_1042_14.json",
        "random_seed_1043_14.json", "random_seed_1044_14.json", "smart_14.json",
    ]
    assert json.loads((output / "smart_14.json").read_text()) == b["smart"]
    assert json.loads((output / "manifest.json").read_text()) == b["manifest"]
    with pytest.raises(FileExistsError):
        batch.write_paper_batch(b, output)
    assert json.loads((output / "manifest.json").read_text()) == b["manifest"]


def test_reject_modified_manifest_and_control(tmp_path, stub_smart):
    b = construct(tmp_path)
    b["manifest"]["source_commit"] = "b" * 40
    with pytest.raises(ValueError, match="manifest.*SHA"):
        batch.write_paper_batch(b, tmp_path / "notwritten")
    assert not (tmp_path / "notwritten").exists()
    b = construct(tmp_path)
    b["controls"]["random_seed_1042"]["tickets"][0]["strong"] = 7
    with pytest.raises(ValueError, match="control.*SHA"):
        batch.write_paper_batch(b, tmp_path / "notwritten")
    assert not (tmp_path / "notwritten").exists()


@pytest.mark.parametrize("changes,message", [
    ({"historical": History("3974")}, "target ID minus one"),
    ({"historical": History("3976")}, "target ID minus one"),
    ({"historical": History("3975", "17-10-26")}, "precede"),
    ({"historical": History("3975", "10-10-26")}, "four local days"),
    ({"target_draw_at": datetime(2026, 10, 16, 8, tzinfo=timezone.utc)}, "60 minutes"),
    ({"target_draw_at": datetime(2026, 10, 17, 23)}, "UTC offset"),
    ({"target_draw_at": NOW}, "60 minutes"),
    ({"now": datetime(2026, 10, 16, 8)}, "timezone-aware"),
    ({"source_commit": "bad"}, "Git commit SHA"),
    ({"schedule_reviewed": False}, "human must confirm"),
    ({"schedule_reference_url": "http://www.pais.co.il/"}, "HTTPS"),
    ({"schedule_reference_url": "https://www.pais.co.il@evil.invalid/"}, "HTTPS"),
    ({"control_seeds": (1042, 1042, 1044)}, "distinct"),
    ({"control_seeds": (1042,)}, "three distinct"),
    ({"control_seeds": (1042, 1043, True)}, "three distinct"),
    ({"target_draw_id": 3975}, "target ID minus one"),
    ({"target_draw_id": True}, "integer"),
])
def test_invalid_or_unverified_inputs_fail_before_generation(tmp_path, stub_smart, changes, message):
    with pytest.raises(ValueError, match=message):
        construct(tmp_path, **changes)
    assert not stub_smart


def test_60_minute_boundary(tmp_path, stub_smart):
    assert construct(
        tmp_path,
        now=TARGET.astimezone(timezone.utc) - timedelta(minutes=60),
    )["smart"]["ticket_count"] == 14
    with pytest.raises(ValueError, match="60 minutes"):
        construct(
            tmp_path,
            now=TARGET.astimezone(timezone.utc) - timedelta(minutes=59, seconds=59),
        )


def test_reject_generated_nonoptimal_smart(monkeypatch, tmp_path):
    class BadEngine:
        def __init__(self, config):
            pass

        def recommend(self, dataset, seed):
            # These tickets have unique main lines, but overlap in >=5
            # positions and cannot attain the disjoint 5+ coverage ceiling.
            lines = [
                SimpleNamespace(
                    numbers=(1, 2, 3, 4, 5, 6 + i), strong_number=1,
                )
                for i in range(14)
            ]
            return SimpleNamespace(
                recommended_tickets_with_strong=lines,
                generated_tickets=tuple(range(200)),
            )
    monkeypatch.setattr(batch, "SmartRecommendationEngine", BadEngine)
    with pytest.raises(ValueError, match="exact coverage ceiling"):
        construct(tmp_path)


def test_manual_workflow_is_not_a_cron_or_pull_request_draw_generator():
    workflow = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "p1-paper-prospective.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "workflow_dispatch" in text
    assert "\n  pull_request:" not in text
    assert "\n  schedule:" not in text
    assert "contents: write" in text
    assert "git push origin" in text
    assert "github.event.inputs" not in text or "env:" in text
