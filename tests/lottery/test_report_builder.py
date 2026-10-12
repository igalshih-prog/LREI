"""Exercise the public report builder instead of reimplementing it in tests."""

from lrei.lottery.backtesting import BacktestCase, BacktestResult
from lrei.lottery.report import LotteryReportBuilder, format_report


def test_report_builder_uses_real_strong_number_fields():
    result = BacktestResult((
        BacktestCase("1", 100, 50, 14, 3, 14, 2, 12, strong_match=3, baseline_strong_match=1),
        BacktestCase("2", 101, 50, 14, 2, 10, 3, 14, strong_match=1, baseline_strong_match=3),
    ))
    report = LotteryReportBuilder().build(result, dataset_draws=102)
    assert report.strong_total_matches == report.baseline_strong_total_matches == 4
    assert report.strong_average_matches == report.baseline_strong_average_matches == 2.0
    assert report.strong_average_advantage == 0.0
    assert "STRONG NUMBER" in format_report(report)


def test_report_builder_handles_empty_backtest():
    report = LotteryReportBuilder().build(BacktestResult(()), dataset_draws=0)
    assert report.strong_average_matches == report.baseline_strong_average_matches == 0.0
    assert report.test_cases == 0
