"""P3-A evidence schema tests. Fast; no network or future prediction."""

import copy
from pathlib import Path

import pytest

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.prize_data import (
    STATUS, PRIZE_TIER_LABELS, PrizeDataError, canonical_sha256,
    load_observation, prize_summary, validate_prize_observation,
)

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "prize_observations" / "3950.json"


def draw_record():
    return load_observation(SAMPLE)


def test_source_transcription_agrees_with_existing_archive_and_is_never_treated_as_official_protocol():
    historic = CsvDatasetLoader().load(ROOT / "data" / "lottery.csv")
    result = load_observation(SAMPLE, historical=historic)
    assert result["draw_id"] == 3950
    assert result["draw_date"] == "2026-07-28"
    assert result["main_numbers"] == [1, 8, 9, 19, 21, 23]
    assert result["strong_number"] == 7
    assert result["source_url"] == "https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3950"
    assert result["source_status"] == STATUS
    assert result["ticket_sales_ils"] is None and result["tax_paid_ils"] is None
    assert list(result["games"]) == ["regular", "double"]
    assert tuple(row["tier"] for row in result["games"]["regular"]) == PRIZE_TIER_LABELS
    assert tuple(row["tier"] for row in result["games"]["double"]) == PRIZE_TIER_LABELS
    assert result["games"]["regular"][3] == {
        "tier": "5", "winning_entries": 242, "payout_per_winning_entry_ils": 601
    }
    assert result["games"]["double"][3] == {
        "tier": "5", "winning_entries": 238, "payout_per_winning_entry_ils": 1202
    }


def test_prize_summary_is_descriptive_only_and_reproducible():
    p = draw_record()
    summary = prize_summary(p)
    assert summary["draw_id"] == 3950
    assert summary["regular_winning_entries"] == 159_364
    assert summary["double_winning_entries"] == 123_744
    assert summary["reported_total_paid_ils"] == 10_876_268
    assert summary["sales_known"] is False
    assert summary["tax_known"] is False
    assert summary["value_calculable"] is False
    assert summary["record_sha256"] == canonical_sha256(p)
    assert canonical_sha256(p) == canonical_sha256(copy.deepcopy(p))


@pytest.mark.parametrize("field,value", [
    ("draw_id", True),
    ("draw_id", -1),
    ("draw_date", "2026-02-31"),
    ("draw_date", "28-07-26"),
    ("main_numbers", [1, 8, 9, 19, 21, 21]),
    ("main_numbers", [1, 8, 9, 19, 21, 38]),
    ("main_numbers", [8, 1, 9, 19, 21, 23]),
    ("strong_number", 8),
    ("strong_number", False),
    ("source_url", "https://example.org/lotto/currentlotto.aspx?lotteryId=3950"),
    ("source_url", "http://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3950"),
    ("source_url", "https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3951"),
    ("source_status", "legally_binding_official_result"),
    ("ticket_sales_ils", 12.5),
    ("tax_paid_ils", -1),
    ("total_prizes_paid_ils", -1),
    ("special_rules_note", ""),
])
def test_invalid_metadata_rejected(field, value):
    record = draw_record()
    record[field] = value
    with pytest.raises(PrizeDataError):
        validate_prize_observation(record)


def test_games_must_include_16_distinct_tier_rows():
    record = draw_record()
    del record["games"]["double"]
    with pytest.raises(PrizeDataError, match="regular and double"):
        validate_prize_observation(record)
    record = draw_record()
    record["games"]["regular"][3]["tier"] = "4+strong"
    with pytest.raises(PrizeDataError, match="tier must"):
        validate_prize_observation(record)
    record = draw_record()
    del record["games"]["regular"][-1]
    with pytest.raises(PrizeDataError, match="eight prize tiers"):
        validate_prize_observation(record)


def test_nonzero_wins_must_have_known_payout_but_missing_no_winner_payout_is_allowed():
    record = draw_record()
    record["games"]["regular"][3]["payout_per_winning_entry_ils"] = None
    with pytest.raises(PrizeDataError, match="require published payout"):
        validate_prize_observation(record)
    record = draw_record()
    record["games"]["regular"][0]["payout_per_winning_entry_ils"] = None
    assert validate_prize_observation(record)["games"]["regular"][0]["payout_per_winning_entry_ils"] is None


def test_result_mismatch_does_not_enter_prize_dataset():
    historic = CsvDatasetLoader().load(ROOT / "data" / "lottery.csv")
    record = draw_record()
    record["main_numbers"] = [1, 8, 9, 19, 21, 24]
    with pytest.raises(PrizeDataError, match="disagrees"):
        validate_prize_observation(record, historical=historic)
    record = draw_record()
    record["draw_date"] = "2026-07-29"
    with pytest.raises(PrizeDataError, match="disagrees"):
        validate_prize_observation(record, historical=historic)


def test_unsupported_fields_are_not_silently_accepted():
    record = draw_record()
    record["projected_profit_ils"] = 100_000
    with pytest.raises(PrizeDataError, match="fields"):
        validate_prize_observation(record)
