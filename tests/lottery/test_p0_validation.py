"""Regression checks for real-data parsing and fair validation portfolios."""

import random
from datetime import date
from pathlib import Path

import pytest

from lrei.lottery.baseline import RandomBaseline
from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import (
    CsvDatasetLoader, DatasetError, LotteryDataset, LotteryDrawRecord, parse_draw_date,
)
from lrei.lottery.pro import ProRecommendationEngine
from lrei.lottery.statistics import LotteryStatistics
from lrei.lottery.portfolio_coverage import portfolio_coverage
from lrei.lottery.any_prize_coverage_engine import AnyPrizeCoverageRecommendationEngine


@pytest.mark.parametrize("value", ["10-10-26", "2026-10-10", "10/10/2026", "10-10-2026", "2026/10/10"])
def test_supported_dates_represent_the_same_calendar_day(value):
    assert parse_draw_date(value) == date(2026, 10, 10)


def test_repository_dates_use_calendar_windows_in_pro():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = ProRecommendationEngine()
    assert all(engine._parse_date(draw.date) is not None for draw in dataset)
    for years in (1, 3):
        cutoff = engine._subtract_years(parse_draw_date(dataset.latest().date), years)
        expected = {}
        for draw in dataset:
            if parse_draw_date(draw.date) >= cutoff:
                for number in draw.numbers:
                    expected[number] = expected.get(number, 0) + 1
        assert engine._window_frequency(dataset, years) == expected


@pytest.mark.parametrize("text, message", [
    ("", "no header"),
    ("draw_id,numbers\n", "no draws"),
    ('draw_id,numbers\n1,"1,2,3,4,5,6"\n1,"7,8,9,10,11,12"\n', "Duplicate draw_id"),
    ('draw_id,numbers,date\n1,"1,2,3,4,5,6",31-02-26\n', "Invalid draw date"),
    ('draw_id,numbers,date\n1,"1,2,3,4,5,6",11-10-26\n2,"7,8,9,10,11,12",10-10-26\n', "chronological"),
    ('draw_id,numbers\n1,"1,2,3,4,5,6",extra\n', "header"),
    ('draw_id,numbers,date\n1,"1,2,3,4,5,6"\n', "header"),
    ('draw_id,numbers,numbers\n1,"1,2,3,4,5,6","7,8,9,10,11,12"\n', "duplicate columns"),
])
def test_invalid_csv_fails_with_dataset_error(tmp_path, text, message):
    path = tmp_path / "invalid.csv"
    path.write_text(text)
    with pytest.raises(DatasetError, match=message):
        CsvDatasetLoader().load(path)


def test_tab_delimited_custom_id_column_and_bom(tmp_path):
    path = tmp_path / "draws.csv"
    path.write_text('\ufeffid\tnumbers\tdate\n1\t1,2,3,4,5,6\t10-10-26\n')
    assert len(CsvDatasetLoader(draw_id_column="id").load(path)) == 1


def test_random_baseline_is_unique_and_rejects_impossible_budget():
    baseline = RandomBaseline(main_number_count=2, max_number=4)
    tickets = baseline.generate_tickets(6, seed=42)
    assert len(tickets) == len(set(tickets)) == 6
    with pytest.raises(ValueError, match="distinct"):
        baseline.generate_tickets(7, seed=42)


def test_backtester_random_universe_includes_unobserved_main_and_strong_numbers():
    stats = LotteryStatistics.from_dataset(LotteryDataset([
        LotteryDrawRecord("1", (10, 11, 12, 13, 14, 15), strong_number=3),
    ]))
    backtester = LotteryBacktester()
    tickets = backtester._generate_random_tickets(stats, 14, random.Random(42))
    assert len(tickets) == len(set(tickets)) == 14
    assert any(number < 10 or number > 15 for ticket in tickets for number in ticket)
    assert backtester._random_strong_matches(stats, 7, 100, random.Random(42)) > 0


def test_backtester_keeps_main_and_strong_portfolio_fixed_inside_block():
    class RecordingBacktester(LotteryBacktester):
        baseline_calls = 0

        def _generate_random_tickets(self, *args, **kwargs):
            self.baseline_calls += 1
            return super()._generate_random_tickets(*args, **kwargs)

    draws = [LotteryDrawRecord(str(i), tuple(range(i * 6 + 1, i * 6 + 7)), strong_number=3) for i in range(3)]
    draws += [LotteryDrawRecord(str(i), (1, 2, 3, 4, 5, 6), strong_number=3) for i in range(3, 5)]
    backtester = RecordingBacktester()
    result = backtester.run(LotteryDataset(draws), train_size=3, test_size=2, seed=42)
    assert backtester.baseline_calls == 1
    left, right = result.cases
    assert left.baseline_total_matches == right.baseline_total_matches
    assert left.baseline_best_match == right.baseline_best_match
    assert left.baseline_strong_match == right.baseline_strong_match
    assert left.total_matches == right.total_matches
    assert left.strong_match == right.strong_match


@pytest.mark.parametrize("bad", [True, 1.5, "1"])
def test_exact_coverage_rejects_noninteger_main_numbers(bad):
    ticket = (bad, 2, 3, 4, 5, 6)
    with pytest.raises(ValueError, match="integers"):
        portfolio_coverage([ticket])
    with pytest.raises(ValueError, match="integers"):
        AnyPrizeCoverageRecommendationEngine.covered_draw_count([ticket])
