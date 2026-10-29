"""Review gate: only the six explicitly reviewed prize-tier observations."""

import json
from pathlib import Path

import pytest

from lrei.lottery.reviewed_tier_diagnostics import inspect_reviewed_observations

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "prize_observations"


def test_six_reviewed_real_observations() -> None:
    result = inspect_reviewed_observations(DATA)
    assert result["reviewed_draw_ids"] == [3949, 3950, 3951, 3952, 3953, 3954]
    assert len(result["draw_reports"]) == 6
    for report in result["draw_reports"]:
        assert set(report["uniform_reference_ratios_by_product"]) == {
            "regular",
            "double",
        }
        assert len(report["uniform_reference_ratios_by_product"]["regular"]) == 8
        assert report["authorized_for_play"] is False
        assert report["total_entries_verified"] is False
    assert result["expected_value_verified"] is False
    assert result["player_popularity_verified"] is False


def test_missing_draw_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inspect_reviewed_observations(tmp_path)


def test_mismatched_identity_fails_closed(tmp_path: Path) -> None:
    data = json.loads((DATA / "3949.json").read_text(encoding="utf-8"))
    data["draw_id"] = 3950
    (tmp_path / "3949.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="identity mismatch"):
        inspect_reviewed_observations(tmp_path)
