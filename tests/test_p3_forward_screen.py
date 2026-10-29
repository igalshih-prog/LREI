"""Only synthetic prospective screening records. No future source data exist."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest

from lrei.lottery.p3_forward_screen import (
    screen_future_draws,
    screen_future_json_file,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    ROOT / "research" / "protocols" / "p3-strong-choice-forward-screen-v1.json"
)
PAST = ROOT / "data" / "prize_observations" / "3954.json"
_TIERS = (
    "6+strong", "6", "5+strong", "5",
    "4+strong", "4", "3+strong", "3",
)


def _protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _synthetic(draw_id: int = 3980, strong: int = 4) -> dict:
    """FAKE fixture for testing validation only, NEVER research evidence."""
    return {
        "draw_id": draw_id,
        "draw_date": (
            date(2026, 10, 31) + timedelta(days=draw_id - 3980)
        ).isoformat(),
        "main_numbers": [1, 4, 8, 17, 22, 35],
        "strong_number": strong,
        "source_status": "operator_site_display_only_not_binding",
        "source_url": (
            "https://www.pais.co.il/lotto/currentlotto.aspx"
            f"?lotteryId={draw_id}"
        ),
        "games": {
            product: [
                {"tier": tier, "winning_entries": 100 + index}
                for index, tier in enumerate(_TIERS)
            ]
            for product in ("regular", "double")
        },
    }


def test_protocol_is_locked_and_explicit_about_historical_leakage() -> None:
    p = _protocol()
    assert p["forward_entry_gate"]["minimum_draw_id"] == 3980
    assert p["forward_entry_gate"]["minimum_draw_date_israel"] == "2026-10-30"
    assert p["historical_analysis"][
        "hypothesis_selected_with_knowledge_of_2026_exploratory_results"
    ] is True
    assert p["primary_descriptive_endpoint"]["drawn_strong_comparison"] == [4, 1]
    assert p["primary_descriptive_endpoint"]["group_minimum_unique_draws"] == 20
    assert p["claims_authorized"]["authorized_for_play"] is False


def test_empty_future_collection_is_unverified_and_not_a_holdout() -> None:
    report = screen_future_draws([], _protocol())
    assert report["candidate_draw_count"] == 0
    assert all(n == 0 for n in report["observed_drawn_strong_counts"].values())
    assert report["primary_sample_size_gate_passed_on_screened_only"] is False
    assert report["raw_first_party_source_verified"] is False
    assert report["source_review_completed"] is False
    assert report["independently_registered_before_draws"] is False
    assert report["prospective_holdout_validated"] is False
    assert report["statistical_significance_claim"] is None
    assert report["authorized_for_play"] is False


def test_synthetic_complete_records_do_not_prove_a_real_data_source() -> None:
    records = [_synthetic(3980, 4), _synthetic(3981, 1)]
    old = deepcopy(records)
    report = screen_future_draws(records, _protocol())
    assert records == old
    assert report["candidate_draw_count"] == 2
    assert report["primary_group_counts_screened_only"] == {"4": 1, "1": 1}
    assert report["primary_sample_size_gate_passed_on_screened_only"] is False
    assert report["source_review_completed"] is False
    assert report["player_popularity_verified"] is False
    assert report["authorized_for_play"] is False


def test_even_forty_fake_draws_cannot_pass_source_or_play_gates() -> None:
    records = [
        _synthetic(3980 + i, 4 if i % 2 == 0 else 1)
        for i in range(40)
    ]
    report = screen_future_draws(records, _protocol())
    assert report["primary_sample_size_gate_passed_on_screened_only"] is True
    assert report["primary_group_counts_screened_only"] == {"4": 20, "1": 20}
    assert report["source_review_completed"] is False
    assert report["raw_first_party_source_verified"] is False
    assert report["binding_protocol_verified"] is False
    assert report["prospective_holdout_validated"] is False
    assert report["authorized_for_play"] is False


def test_prior_inspected_real_draw_is_not_a_prospective_observation() -> None:
    historical = json.loads(PAST.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="predates"):
        screen_future_draws([historical], _protocol())


@pytest.mark.parametrize(
    "change",
    [
        "old_id", "old_date", "reordered", "duplicate", "bad_strong",
        "bad_main", "duplicate_main", "forged_source", "bad_url",
        "missing_product", "missing_tier", "duplicate_tier", "duplicate_date",
        "negative_winners", "bool_winners",
    ],
)
def test_corrupted_or_leaky_synthetic_records_rejected(change: str) -> None:
    records = [_synthetic(3980), _synthetic(3981, 1)]
    first = records[0]
    if change == "old_id":
        first["draw_id"] = 3979
    elif change == "old_date":
        first["draw_date"] = "2026-10-27"
    elif change == "reordered":
        records.reverse()
    elif change == "duplicate":
        records[1]["draw_id"] = 3980
    elif change == "bad_strong":
        first["strong_number"] = True
    elif change == "bad_main":
        first["main_numbers"][0] = 38
    elif change == "duplicate_main":
        first["main_numbers"][1] = first["main_numbers"][0]
    elif change == "forged_source":
        first["source_status"] = "legally_binding_protocol_verified"
    elif change == "bad_url":
        first["source_url"] = "https://pais.co.il.evil.test/archive"
    elif change == "missing_product":
        del first["games"]["double"]
    elif change == "missing_tier":
        first["games"]["double"].pop()
    elif change == "duplicate_tier":
        first["games"]["double"][0]["tier"] = "3"
    elif change == "duplicate_date":
        records[1]["draw_date"] = first["draw_date"]
    elif change == "negative_winners":
        first["games"]["regular"][0]["winning_entries"] = -4
    elif change == "bool_winners":
        first["games"]["regular"][0]["winning_entries"] = True
    with pytest.raises(ValueError):
        screen_future_draws(records, _protocol())


@pytest.mark.parametrize(
    "mutation",
    ["min_id", "min_date", "claim", "count", "selection_leak", "status"],
)
def test_modified_protocol_cannot_silently_weaken_research_gate(
    mutation: str,
) -> None:
    p = _protocol()
    if mutation == "min_id":
        p["forward_entry_gate"]["minimum_draw_id"] = 3955
    elif mutation == "min_date":
        p["forward_entry_gate"]["minimum_draw_date_israel"] = "2026-08-12"
    elif mutation == "claim":
        p["claims_authorized"]["authorized_for_play"] = True
    elif mutation == "count":
        p["primary_descriptive_endpoint"]["group_minimum_unique_draws"] = 1
    elif mutation == "selection_leak":
        p["historical_analysis"][
            "hypothesis_selected_with_knowledge_of_2026_exploratory_results"
        ] = False
    else:
        p["forward_entry_gate"]["source_validation_implemented_by_this_protocol"] = True
    with pytest.raises(ValueError, match="gates must not change"):
        screen_future_draws([], p)


def test_read_only_json_cli_helper(tmp_path: Path) -> None:
    candidate = tmp_path / "synthetic-only.json"
    candidate.write_text(json.dumps([_synthetic()]), encoding="utf-8")
    output = screen_future_json_file(candidate, PROTOCOL_PATH)
    assert output["candidate_draw_count"] == 1
    assert output["status"] == "candidate_structure_screened_SOURCE_REVIEW_REQUIRED"
