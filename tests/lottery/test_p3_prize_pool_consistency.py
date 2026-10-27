"""Read-only P3-A accounting tests; original informational data unchanged."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from lrei.lottery.p3_prize_pool_consistency import prize_pool_consistency
from lrei.lottery.prize_data import PrizeDataError

ROOT = Path(__file__).resolve().parents[2]


def observation(draw=3954):
    return json.loads(
        (ROOT / "data" / "prize_observations" / f"{draw}.json").read_text(
            encoding="utf-8"
        )
    )


@pytest.mark.parametrize("draw,expected", [
    (3949, 24280750), (3950, 26969875), (3951, 29864889),
    (3952, 36837664), (3953, 36754667), (3954, 14246419),
])
def test_existing_nonbinding_records_only_descriptive(draw, expected):
    record = observation(draw)
    original = deepcopy(record)
    result = prize_pool_consistency(record)
    assert record == original
    assert len(result["tier_indicators"]) == 5
    assert result["median_indicator_ils"] == expected
    assert result["indicator_is_operator_verified_sales"] is False
    assert result["indicators_are_independent_observations"] is False
    assert result["confidence_interval_valid"] is False
    assert result["operator_source_provenance_verified"] is False
    assert result["usable_for_player_combination_popularity"] is False
    assert result["eligible_for_monetary_expected_value"] is False
    assert result["dataset_promotion_approved"] is False
    assert result["decision"] == "NO PLAY"
    assert record["ticket_sales_ils"] is None


def test_boosted_3953_requires_exact_notice():
    record = observation(3953)
    record["special_rules_note"] = None
    with pytest.raises(PrizeDataError, match="bonus draw"):
        prize_pool_consistency(record)


def test_bonus_requires_boosted_tier_eight_amount():
    record = observation(3953)
    record["games"]["double"][7]["payout_per_winning_entry_ils"] = 20
    with pytest.raises(PrizeDataError, match="tier-eight"):
        prize_pool_consistency(record)


def test_baseline_refuses_unreviewed_special_rule():
    record = observation(3952)
    record["special_rules_note"] = "unreviewed change"
    with pytest.raises(PrizeDataError, match="special-rule"):
        prize_pool_consistency(record)


def test_invalid_entries_and_missing_tier_refused():
    record = observation(3954)
    record["games"]["regular"][2]["winning_entries"] = -1
    with pytest.raises(PrizeDataError):
        prize_pool_consistency(record)
    record = observation(3954)
    record["games"]["double"].pop()
    with pytest.raises(PrizeDataError):
        prize_pool_consistency(record)


def test_no_assumed_rules_for_draw_outside_reviewed_cohort():
    record = observation(3954)
    record["draw_id"] = 3955
    record["source_url"] = "https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3955"
    with pytest.raises(PrizeDataError, match="reviewed percentage regime"):
        prize_pool_consistency(record)


def test_bonus_draw_third_tier_arithmetic_is_not_sales():
    result = prize_pool_consistency(observation(3953))
    third = result["tier_indicators"][0]
    assert third["reported_payout_total_ils"] == 992376
    assert third["implied_receipts_indicator_ils"] == 36754667
    assert result["reviewed_rule_regime"] == "bonus_150pct"
    assert result["indicator_is_operator_verified_sales"] is False


def test_structurally_valid_winner_count_edit_is_refused():
    record = observation(3954)
    record["games"]["regular"][2]["winning_entries"] += 1
    with pytest.raises(PrizeDataError, match="differs from reviewed repository fixture"):
        prize_pool_consistency(record)


def test_structurally_valid_payout_edit_is_refused():
    record = observation(3954)
    record["games"]["double"][2]["payout_per_winning_entry_ils"] += 2
    with pytest.raises(PrizeDataError, match="differs from reviewed repository fixture"):
        prize_pool_consistency(record)


def test_missing_reviewed_fixture_fails_closed(monkeypatch, tmp_path):
    from lrei.lottery import p3_prize_pool_consistency as module

    monkeypatch.setattr(module, "OBSERVATION_ROOT", tmp_path / "missing")
    with pytest.raises(PrizeDataError, match="invalid or unreadable"):
        module.prize_pool_consistency(observation(3954))
