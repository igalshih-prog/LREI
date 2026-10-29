"""Sensitivity is descriptive and respects original six audited source files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lrei.lottery.draw_omission_sensitivity import (
    audit_draw_omission_sensitivity,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "prize_observations"


def test_real_context_and_never_claims_inference_or_play() -> None:
    report = audit_draw_omission_sensitivity(DATA)
    assert report["reviewed_draw_ids"] == list(range(3949, 3955))
    assert report["special_prize_rule_excluded_draw_ids"] == [3953]
    assert report["lowest_advertised_prize_excluded_draw_ids"] == [3954]
    assert report["advertised_regular_first_prize_min_ils"] == 5_000_000
    assert report["statistical_significance_claim"] is None
    assert report["p_values_reported"] is False
    assert report["draws_independent_proven"] is False
    assert report["ticket_entries_independent_proven"] is False
    assert report["source_provenance_verified"] is False
    assert report["chronological_holdout_validated"] is False
    assert report["authorized_for_play"] is False
    assert report["expected_value_verified"] is False


def test_six_draw_omissions_keep_descriptive_positive_sign() -> None:
    report = audit_draw_omission_sensitivity(DATA)
    by_product = report["product_and_main_match_count"]
    assert set(by_product) == {"regular", "double"}
    for product in ("regular", "double"):
        for k in ("3", "4", "5"):
            cell = by_product[product][k]
            assert len(cell["leave_one_draw_out"]) == 6
            assert cell["leave_one_draw_out_all_positive"] is True
            assert cell["leave_one_draw_out_delta_min_pp"] > 0
            assert cell["leave_one_draw_out_delta_max_pp"] > 0
            assert cell["hypothesis_selected_after_seeing_data"] is True
            assert cell["no_inferential_stability_claim"] is True
            for omission in cell["leave_one_draw_out"]:
                if omission["excluded_draw_id"] in (3951, 3952):
                    assert omission["strong_4_supporting_draws"] == 1
                else:
                    assert omission["strong_4_supporting_draws"] == 2


def test_actual_regular_three_sensitivity_values() -> None:
    report = audit_draw_omission_sensitivity(DATA)
    regular_three = report["product_and_main_match_count"]["regular"]["3"]
    assert regular_three["baseline_delta_pp"] == pytest.approx(
        1.0802287482722384, abs=1e-10
    )
    assert regular_three["leave_one_draw_out_delta_min_pp"] == pytest.approx(
        0.9642882531039093, abs=1e-10
    )
    assert regular_three["leave_one_draw_out_delta_max_pp"] == pytest.approx(
        1.1961692434405646, abs=1e-10
    )
    scenes = regular_three["context_exclusion_scenarios"]
    assert scenes["exclude_special_prize_rule_draws"][
        "unweighted_draw_mean_difference_percentage_points"
    ] == pytest.approx(1.0398973052447968)
    assert scenes["exclude_lowest_advertised_prize_draws"][
        "unweighted_draw_mean_difference_percentage_points"
    ] == pytest.approx(1.1146797984657035)
    assert scenes["exclude_both_contextual_extremes"][
        "unweighted_draw_mean_difference_percentage_points"
    ] == pytest.approx(1.0714081590212698)


def test_real_double_four_is_sensitive_to_dropping_strong_four_draw() -> None:
    report = audit_draw_omission_sensitivity(DATA)
    cell = report["product_and_main_match_count"]["double"]["4"]
    assert cell["baseline_delta_pp"] == pytest.approx(1.0006356714050284)
    assert cell["leave_one_draw_out_delta_min_pp"] == pytest.approx(
        0.4074014822835814
    )
    assert cell["leave_one_draw_out_delta_max_pp"] == pytest.approx(
        1.5938698605264756
    )


def test_missing_files_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        audit_draw_omission_sensitivity(tmp_path)


@pytest.mark.parametrize(
    "mutation",
    ["source", "id", "prize", "count", "missing_tier"],
)
def test_corrupted_source_fails_closed(
    mutation: str, tmp_path: Path
) -> None:
    for draw_id in range(3949, 3955):
        raw = json.loads((DATA / f"{draw_id}.json").read_text(encoding="utf-8"))
        if draw_id == 3953:
            if mutation == "source":
                raw["source_status"] = "independently_verified"
            elif mutation == "id":
                raw["draw_id"] = 3952
            elif mutation == "prize":
                raw["advertised_prizes_ils"]["regular_first"] = None
            elif mutation == "count":
                raw["games"]["regular"][0]["winning_entries"] = -3
            else:
                raw["games"]["regular"].pop()
        (tmp_path / f"{draw_id}.json").write_text(
            json.dumps(raw), encoding="utf-8"
        )
    with pytest.raises(ValueError):
        audit_draw_omission_sensitivity(tmp_path)
