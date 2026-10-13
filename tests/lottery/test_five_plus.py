"""Fast mathematical regression tests for the Smart 5+ objective."""

from itertools import combinations
from math import comb
import random
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from lrei.cli import app
from lrei.lottery.dataset import LotteryDataset
from lrei.lottery.five_plus import (
    MAX_FIVE_PLUS_OUTCOMES, MAX_FIVE_PLUS_PROBABILITY,
    TOTAL_MAIN_DRAWS, five_plus_metrics,
)
from lrei.lottery.smart import SmartConfig, SmartRecommendationEngine


def fourteen_lines():
    """Deterministic valid portfolio with <=3 shared main numbers per pair."""
    rng = random.Random(42)
    result = []
    while len(result) < 14:
        proposed = tuple(sorted(rng.sample(range(1, 38), 6)))
        if all(len(set(proposed) & set(existing)) <= 3 for existing in result):
            result.append(proposed)
    return tuple(result)


def test_five_plus_bound_is_exactly_one_in_888():
    assert TOTAL_MAIN_DRAWS == comb(37, 6) == 2_324_784
    assert MAX_FIVE_PLUS_OUTCOMES == 14 * (1 + 6 * 31) == 2618
    assert MAX_FIVE_PLUS_PROBABILITY == pytest.approx(1 / 888)
    assert 14 / (7 * TOTAL_MAIN_DRAWS) == pytest.approx(1 / 1_162_392)


def test_any_valid_portfolio_with_max_pair_intersection_three_reaches_bound():
    tickets = fourteen_lines()
    assert max(len(set(a) & set(b)) for a, b in combinations(tickets, 2)) == 3
    result = five_plus_metrics(tickets)
    assert result["is_optimal"] is True
    assert result["covered_draws"] == result["max_covered_draws"] == 2618
    assert result["probability"] == result["max_probability"] == pytest.approx(1 / 888)
    assert result["with_matching_strong_probability"] == pytest.approx(1 / 6216)


def test_overlapping_five_plus_events_are_counted_only_once():
    tickets = list(fourteen_lines())
    original = tickets[0]
    tickets[1] = tuple(sorted((*original[:4], 34, 37)))
    assert len(set(tickets[0]) & set(tickets[1])) == 4
    result = five_plus_metrics(tickets)
    assert result["is_optimal"] is False
    assert result["covered_draws"] < 2618
    assert result["with_matching_strong_probability"] is None


@pytest.mark.parametrize("bad", [True, 0, 38, 1.5, "7"])
def test_invalid_main_numbers_are_not_accepted(bad):
    portfolio = list(fourteen_lines())
    portfolio[0] = (bad, 8, 9, 15, 16, 18)
    with pytest.raises(ValueError):
        five_plus_metrics(portfolio)


def test_reject_non_unique_lines_and_wrong_budget():
    tickets = list(fourteen_lines())
    with pytest.raises(ValueError, match="14"):
        five_plus_metrics(tickets[:-1])
    tickets[1] = tickets[0]
    with pytest.raises(ValueError, match="distinct"):
        five_plus_metrics(tickets)


def test_five_plus_and_four_plus_use_same_coverage_engine_without_recalibration(monkeypatch):
    import lrei.lottery.smart as smart_module

    called = []
    expected = object()

    class FakeCoverageEngine:
        def recommend(self, dataset, seed):
            called.append(seed)
            return expected

    monkeypatch.setattr(smart_module, "CoverageRecommendationEngine", FakeCoverageEngine)
    for objective in ("coverage_4plus", "coverage_5plus"):
        engine = SmartRecommendationEngine(SmartConfig(objective=objective))
        assert engine.select_model(LotteryDataset()) == ("coverage", {"coverage": 1.0})
        assert engine.recommend(LotteryDataset(), seed=77) is expected
    assert called == [77, 77]


def test_cli_exposes_new_five_hit_objective_without_untested_prediction_claim():
    result = CliRunner().invoke(app, ["recommend", "--help"])
    assert result.exit_code == 0
    assert "coverage_5plus" in result.output


def test_snapshot_schema_accepts_explicit_five_plus_objective(tmp_path):
    from datetime import datetime, timezone
    from lrei.lottery.prospective_ledger import build_snapshot

    data_file = tmp_path / "data.csv"
    data_file.write_bytes(b"synthetic")
    class FakeDataset:
        def __len__(self):
            return 1141
        def latest(self):
            return SimpleNamespace(draw_id="3973", date="10-10-26")

    lines = [
        SimpleNamespace(numbers=line, strong_number=index % 7 + 1)
        for index, line in enumerate(fourteen_lines())
    ]
    record = build_snapshot(
        dataset_file=data_file, dataset=FakeDataset(), tickets=lines,
        mode="smart", objective="coverage_5plus", seed=42,
        source_commit="a" * 40,
        created_at=datetime(2026, 10, 13, 7, 0, tzinfo=timezone.utc),
        target_draw_at=datetime(2026, 10, 15, 18, 0, tzinfo=timezone.utc),
        generated_count=1000,
    )
    assert record["objective"] == "coverage_5plus"



def test_cli_reports_five_hit_limit_and_strong_separately(monkeypatch):
    import lrei.cli as cli_module
    from lrei.lottery.recommendation import RecommendedTicket

    lines = fourteen_lines()
    tickets = tuple(
        RecommendedTicket(numbers=line, strong_number=(index % 7) + 1)
        for index, line in enumerate(lines)
    )

    class FakeSmart:
        def __init__(self, config):
            self.config = config

        def recommend(self, dataset, seed):
            assert seed == 42
            return SimpleNamespace(
                generated_tickets=lines,
                recommended_tickets=lines,
                recommended_tickets_with_strong=tickets,
                scores=(),
                strong_scores=(),
            )

    monkeypatch.setattr(cli_module, "SmartRecommendationEngine", FakeSmart)
    result = CliRunner().invoke(
        app, ["recommend", "--mode", "smart", "--objective", "coverage_5plus", "--seed", "42"],
    )
    assert result.exit_code == 0, result.output
    assert "Exact 5+ main-number coverage: 0.1126%" in result.output
    assert "Proven 5+ maximum attained: True" in result.output
    assert "5+ main AND strong-number coverage: 0.0161%" in result.output
    assert "1 in 6,216" in result.output
