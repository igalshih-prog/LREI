"""P3: scenario comparison is retrospective, separate and fail-closed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lrei.lottery.conditional_scenario_comparison import (
    compare_hypothetical_strong_scenario,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "prize_observations"
MAIN = [1.0] * 37
STRONG = [1.0] * 7
SHARES = {"regular": 0.5, "double": 0.5}


def test_uniform_scenario_matches_exact_seventh_in_all_strata() -> None:
    report = compare_hypothetical_strong_scenario(DATA, MAIN, STRONG, SHARES)
    assert report["reviewed_draw_ids"] == list(range(3949, 3955))
    assert len(report["draws"]) == 6
    assert report["chronological_holdout_validated"] is False
    assert report["statistical_significance_claim"] is None
    assert report["source_data_used_for_model_fitting"] is False
    assert report["independently_verified_observations"] is False
    for draw in report["draws"]:
        assert set(draw["by_product"]) == {"regular", "double"}
        for product in ("regular", "double"):
            for stratum in draw["by_product"][product]["by_main_match_count"].values():
                assert stratum["assumed_model_strong_fraction"] == pytest.approx(1 / 7)
    for field in (
        "manual_entry_share_verified",
        "manual_selection_distribution_verified",
        "player_popularity_verified",
        "total_entries_verified",
        "expected_value_verified",
        "authorized_for_play",
    ):
        assert report[field] is False


def test_actual_3951_observation_and_product_specific_hypotheses() -> None:
    strong = STRONG.copy()
    strong[3] = 2.0  # arbitrary toy preference for drawn strong 4
    output = compare_hypothetical_strong_scenario(
        DATA, MAIN, strong, {"regular": 0.0, "double": 1.0}
    )
    draw = next(d for d in output["draws"] if d["draw_id"] == 3951)
    regular = draw["by_product"]["regular"]["by_main_match_count"]["3"]
    double = draw["by_product"]["double"]["by_main_match_count"]["3"]
    assert regular["observed_strong_fraction"] == pytest.approx(20970 / 138010)
    assert regular["assumed_model_strong_fraction"] == pytest.approx(1 / 7)
    assert double["assumed_model_strong_fraction"] == pytest.approx(2 / 8)
    assert double["observed_strong_fraction"] == pytest.approx(
        17306 / (17306 + 95710)
    )
    assert regular["observed_minus_model_percentage_points"] == pytest.approx(
        100 * (20970 / 138010 - 1 / 7)
    )


def test_nonuniform_main_selection_changes_conditional_manual_share() -> None:
    main = MAIN.copy()
    main[3] = 2.5
    main[6] = 1.8
    strong = STRONG.copy()
    strong[3] = 2
    out = compare_hypothetical_strong_scenario(
        DATA, main, strong, {"regular": 0.3, "double": 0.3}
    )
    draw = next(d for d in out["draws"] if d["draw_id"] == 3951)
    by_k = draw["by_product"]["regular"]["by_main_match_count"]
    # The overall mixture share does NOT equal manual share within each k.
    assert by_k["3"]["assumed_model_strong_fraction"] != pytest.approx(
        by_k["5"]["assumed_model_strong_fraction"]
    )


def test_zero_winner_stratum_is_missing_not_zero_probability() -> None:
    out = compare_hypothetical_strong_scenario(DATA, MAIN, STRONG, SHARES)
    row = out["draws"][0]["by_product"]["regular"]["by_main_match_count"]["6"]
    assert row["observed_entries_in_match_class"] == 0
    assert row["observed_strong_fraction"] is None
    assert row["observed_minus_model_percentage_points"] is None
    assert row["assumed_model_strong_fraction"] == pytest.approx(1 / 7)


@pytest.mark.parametrize(
    "shares",
    [
        {"regular": 0.5},
        {"regular": 0.5, "double": 0.5, "extra": 0.5},
        {"regular": 0.5, "double": -0.1},
        {"regular": 0.5, "double": 1.1},
        {"regular": 0.5, "double": True},
        {"regular": 0.5, "double": float("nan")},
    ],
)
def test_bad_product_shares_fail_closed(shares: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        compare_hypothetical_strong_scenario(DATA, MAIN, STRONG, shares)


def test_bad_weights_fail_closed() -> None:
    with pytest.raises(ValueError):
        compare_hypothetical_strong_scenario(
            DATA, MAIN[:-1], STRONG, SHARES
        )


def test_missing_and_mismatched_observations_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compare_hypothetical_strong_scenario(tmp_path, MAIN, STRONG, SHARES)
    raw = json.loads((DATA / "3949.json").read_text(encoding="utf-8"))
    raw["draw_id"] = 3950
    (tmp_path / "3949.json").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="identity mismatch"):
        compare_hypothetical_strong_scenario(tmp_path, MAIN, STRONG, SHARES)


def test_unverified_source_cannot_be_promoted(tmp_path: Path) -> None:
    for draw_id in range(3949, 3955):
        raw = json.loads(
            (DATA / f"{draw_id}.json").read_text(encoding="utf-8")
        )
        if draw_id == 3953:
            raw["source_status"] = "operator_verified"
        (tmp_path / f"{draw_id}.json").write_text(
            json.dumps(raw), encoding="utf-8"
        )
    with pytest.raises(ValueError, match="unreviewed source status"):
        compare_hypothetical_strong_scenario(tmp_path, MAIN, STRONG, SHARES)
