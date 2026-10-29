"""Draw-level descriptive grouping; reject false independent-ticket inference."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from lrei.lottery.conditional_strong_audit import (
    audit_reviewed_strong_observations,
)
from lrei.lottery.reviewed_strong_draw_profile import (
    summarize_conditional_strong_draws,
    summarize_reviewed_strong_draws,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "prize_observations"


def test_real_draws_coverage_and_missing_strong_numbers() -> None:
    output = summarize_reviewed_strong_draws(DATA)
    assert output["reviewed_draw_ids"] == list(range(3949, 3955))
    assert output["draw_ids_by_drawn_strong"] == {
        "1": [], "2": [], "3": [],
        "4": [3951, 3952],
        "5": [], "6": [3949, 3954], "7": [3950, 3953],
    }
    assert output["unobserved_drawn_strong_numbers"] == [1, 2, 3, 5]
    assert output["statistical_significance_claim"] is None
    assert output["chronological_holdout_validated"] is False
    assert output["ticket_entry_independence_assumed"] is False
    assert output["source_provenance_verified"] is False
    assert output["player_popularity_verified"] is False
    assert output["expected_value_verified"] is False
    assert output["authorized_for_play"] is False


def test_mean_of_draw_fractions_not_pooled_ticket_share() -> None:
    report = summarize_reviewed_strong_draws(DATA)
    by_strength = report["per_draw_unweighted_means_by_product_k_and_strong"]
    regular_three = by_strength["regular"]["3"]
    expected = (
        20970 / (20970 + 117040)
        + 25813 / (25813 + 146703)
    ) / 2
    assert regular_three["4"]["mean_of_draw_fractions"] == pytest.approx(expected)
    assert regular_three["4"]["draw_count_with_nonzero_match_class"] == 2
    pooled = (20970 + 25813) / (
        20970 + 117040 + 25813 + 146703
    )
    assert regular_three["4"]["mean_of_draw_fractions"] != pytest.approx(
        pooled, abs=1e-5
    )
    assert regular_three["1"]["mean_of_draw_fractions"] is None
    assert regular_three["1"]["draw_count_with_nonzero_match_class"] == 0


def test_four_vs_six_seven_retrospective_direction_on_both_products() -> None:
    report = summarize_reviewed_strong_draws(DATA)
    contrast = report["exploratory_strong_4_vs_6_or_7_by_product_and_k"]
    for product in ("regular", "double"):
        for k in ("3", "4"):
            cell = contrast[product][k]
            assert cell["drawn_strong_4_draw_count"] == 2
            assert cell["drawn_strong_6_or_7_draw_count"] == 4
            assert cell["observed_4_minus_6_or_7_percentage_points"] > 0
            assert cell["is_exploratory_and_not_a_hypothesis_test"] is True
    assert contrast["regular"]["3"][
        "observed_4_minus_6_or_7_percentage_points"
    ] == pytest.approx(1.0802, abs=0.001)
    assert contrast["double"]["4"][
        "observed_4_minus_6_or_7_percentage_points"
    ] == pytest.approx(1.0007, abs=0.001)


def test_does_not_modify_existing_audit_data() -> None:
    input_audit = audit_reviewed_strong_observations(DATA)
    original = deepcopy(input_audit)
    summarize_conditional_strong_draws(input_audit)
    assert input_audit == original


def test_missing_first_party_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        summarize_reviewed_strong_draws(tmp_path)


def test_zero_denominator_does_not_turn_into_zero_fraction() -> None:
    audit = audit_reviewed_strong_observations(DATA)
    cell = audit["draws"][2]["by_product_and_main_matches"]["regular"]["5"]
    cell["strong_winning_entries"] = 0
    cell["without_strong_winning_entries"] = 0
    cell["observed_strong_fraction"] = None
    summary = summarize_conditional_strong_draws(audit)
    assert summary["per_draw_unweighted_means_by_product_k_and_strong"][
        "regular"
    ]["5"]["4"]["draw_count_with_nonzero_match_class"] == 1


@pytest.mark.parametrize(
    "mutation",
    ["top_status", "source", "authorization", "missing", "duplicate",
     "date", "fraction", "negative", "missing_product", "bad_strong"],
)
def test_corrupted_audit_rejected(mutation: str) -> None:
    audit = audit_reviewed_strong_observations(DATA)
    if mutation == "top_status":
        audit["status"] = "approved"
    elif mutation == "source":
        audit["draws"][0]["source_status"] = "official_source_verified"
    elif mutation == "authorization":
        audit["authorized_for_play"] = True
    elif mutation == "missing":
        audit["draws"].pop()
    elif mutation == "duplicate":
        audit["draws"][1]["draw_id"] = 3949
    elif mutation == "date":
        audit["draws"][1]["draw_date"] = audit["draws"][0]["draw_date"]
    elif mutation == "fraction":
        audit["draws"][0]["by_product_and_main_matches"]["regular"]["3"][
            "observed_strong_fraction"
        ] = 0.5
    elif mutation == "negative":
        audit["draws"][0]["by_product_and_main_matches"]["regular"]["3"][
            "strong_winning_entries"
        ] = -1
    elif mutation == "missing_product":
        del audit["draws"][0]["by_product_and_main_matches"]["double"]
    else:
        audit["draws"][0]["drawn_strong_number"] = True
    with pytest.raises(ValueError):
        summarize_conditional_strong_draws(audit)
