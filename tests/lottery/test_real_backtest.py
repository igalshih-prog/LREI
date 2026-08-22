from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_real_lottery_backtest_runs():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    assert result.case_count == len(dataset) - 1000
    assert result.case_count > 0

    assert result.best_match >= 0
    assert result.total_matches >= 0
    assert result.average_matches >= 0.0

    assert result.baseline_best_match >= 0
    assert result.baseline_total_matches >= 0
    assert result.baseline_average_matches >= 0.0


def test_real_lottery_backtest_produces_recommendations():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    assert result.cases

    for case in result.cases:
        assert case.generated_ticket_count == 50
        assert case.recommended_ticket_count > 0
        assert case.best_match >= 0
        assert case.total_matches >= 0
        assert case.baseline_best_match >= 0
        assert case.baseline_total_matches >= 0


def test_real_lottery_backtest_threshold_metrics():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    backtester = LotteryBacktester()

    result = backtester.run(
        dataset=dataset,
        train_size=1000,
        test_size=1,
        ticket_count=50,
        seed=42,
    )

    assert result.match_count_at_least(1) >= 0
    assert result.match_count_at_least(2) >= 0
    assert result.match_count_at_least(3) >= 0

    assert result.baseline_match_count_at_least(1) >= 0
    assert result.baseline_match_count_at_least(2) >= 0
    assert result.baseline_match_count_at_least(3) >= 0
