"""Research-only tests of conditional strong-match fractions and identification."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from lrei.lottery.conditional_strong_audit import (
    UNIFORM_STRONG_MATCH_FRACTION,
    audit_reviewed_strong_observations,
    conditional_strong_audit,
    implied_manual_strong_rate,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "prize_observations"


def fixture(draw_id: int = 3951) -> dict:
    return json.loads((DATA / f"{draw_id}.json").read_text(encoding="utf-8"))


def test_six_real_observations_keep_products_and_dates_separate() -> None:
    result = audit_reviewed_strong_observations(DATA)
    assert result["reviewed_draw_ids"] == list(range(3949, 3955))
    assert len(result["draws"]) == 6
    assert [row["drawn_strong_number"] for row in result["draws"]] == [
        6, 7, 4, 4, 7, 6
    ]
    assert result["statistical_significance_claim"] is None
    assert result["independent_validation"] is False
    for row in result["draws"]:
        assert row["uniform_independent_strong_baseline"] == pytest.approx(1 / 7)
        assert set(row["by_product_and_main_matches"]) == {"regular", "double"}
        assert row["authorized_for_play"] is False
        assert row["total_entries_verified"] is False
        assert row["manual_entry_share_verified"] is False
        for product in ("regular", "double"):
            assert set(row["by_product_and_main_matches"][product]) == {
                "3", "4", "5", "6"
            }


def test_actual_draw_3951_strong_four_reference_fraction() -> None:
    raw = fixture(3951)
    old = deepcopy(raw)
    result = conditional_strong_audit(raw)
    x = result["by_product_and_main_matches"]["regular"]["3"]
    assert x["strong_winning_entries"] == 20970
    assert x["without_strong_winning_entries"] == 117040
    assert x["observed_entries_in_match_class"] == 138010
    assert x["observed_strong_fraction"] == pytest.approx(20970 / 138010)
    assert x["difference_from_uniform_percentage_points"] == pytest.approx(
        100 * (20970 / 138010 - 1 / 7)
    )
    assert raw == old


def test_draw_3952_four_and_draw_3949_six_are_only_descriptive() -> None:
    four = conditional_strong_audit(fixture(3952))
    six = conditional_strong_audit(fixture(3949))
    four_k3 = four["by_product_and_main_matches"]["regular"]["3"]
    six_k3 = six["by_product_and_main_matches"]["regular"]["3"]
    assert four_k3["observed_strong_fraction"] > 1 / 7
    assert six_k3["observed_strong_fraction"] < 1 / 7
    assert four["manual_number_distribution_verified"] is False


def test_zero_winning_entries_does_not_imply_zero_player_volume() -> None:
    result = conditional_strong_audit(fixture(3949))
    six_match = result["by_product_and_main_matches"]["regular"]["6"]
    assert six_match["observed_entries_in_match_class"] == 0
    assert six_match["observed_strong_fraction"] is None
    assert six_match["difference_from_uniform_percentage_points"] is None
    assert result["total_entries_verified"] is False


def test_hypothetical_mixture_shows_nonidentification() -> None:
    observed = (1 - 0.25) / 7 + 0.25 * 0.20
    assert implied_manual_strong_rate(observed, 0.25) == pytest.approx(0.20)
    assert implied_manual_strong_rate(observed, 0.50) != pytest.approx(0.20)
    assert implied_manual_strong_rate(UNIFORM_STRONG_MATCH_FRACTION, 0.75) == (
        pytest.approx(1 / 7)
    )


@pytest.mark.parametrize(
    "observed,share",
    [(-0.1, 0.5), (1.1, 0.5), (0.1, 0), (0.1, -0.2),
     (0.1, 1.1), (float("nan"), 0.3), (0.1, float("inf")),
     (True, 0.25), (0.15, True)],
)
def test_invalid_mixture_inputs_fail_closed(
    observed: float, share: float
) -> None:
    with pytest.raises(ValueError):
        implied_manual_strong_rate(observed, share)


def test_impossible_mixture_returns_none_not_fake_probability() -> None:
    assert implied_manual_strong_rate(0.5, 0.1) is None


@pytest.mark.parametrize("invalid", [0, 8, True, 4.5])
def test_invalid_strong_drawn_number_rejected(invalid: object) -> None:
    data = fixture()
    data["strong_number"] = invalid
    with pytest.raises(ValueError):
        conditional_strong_audit(data)


def test_invalid_duplicate_draw_numbers_rejected() -> None:
    data = fixture()
    data["main_numbers"][0] = data["main_numbers"][1]
    with pytest.raises(ValueError):
        conditional_strong_audit(data)


@pytest.mark.parametrize("invalid", ["2026-02-30", "not a date", "2026-8-1", None])
def test_invalid_date_rejected(invalid: object) -> None:
    data = fixture()
    data["draw_date"] = invalid
    with pytest.raises(ValueError):
        conditional_strong_audit(data)


def test_no_unreviewed_source_promotion() -> None:
    data = fixture()
    data["source_status"] = "official_independently_verified"
    with pytest.raises(ValueError):
        conditional_strong_audit(data)


def test_reviewed_file_missing_or_mismatched_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        audit_reviewed_strong_observations(tmp_path)
    data = fixture(3949)
    data["draw_id"] = 3950
    (tmp_path / "3949.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="identity mismatch"):
        audit_reviewed_strong_observations(tmp_path)
