"""Reporting utilities for lottery backtesting results."""

from __future__ import annotations

from dataclasses import dataclass

from .backtesting import BacktestResult


@dataclass(frozen=True)
class LotteryReport:
    """Human-readable summary of a lottery backtest."""

    dataset_draws: int
    test_cases: int

    lrei_best_match: int
    lrei_total_matches: int
    lrei_average_matches: float

    baseline_best_match: int
    baseline_total_matches: int
    baseline_average_matches: float

    strong_total_matches: int
    strong_average_matches: float

    baseline_strong_total_matches: int
    baseline_strong_average_matches: float

    @property
    def average_advantage(self) -> float:
        """Return the LREI advantage over the random baseline."""
        return (
            self.lrei_average_matches
            - self.baseline_average_matches
        )

    @property
    def total_advantage(self) -> int:
        """Return the total LREI advantage over the random baseline."""
        return (
            self.lrei_total_matches
            - self.baseline_total_matches
        )

    @property
    def strong_average_advantage(self) -> float:
        """Return the strong-number advantage over the random baseline."""
        return (
            self.strong_average_matches
            - self.baseline_strong_average_matches
        )

    @property
    def strong_total_advantage(self) -> int:
        """Return the total strong-number advantage."""
        return (
            self.strong_total_matches
            - self.baseline_strong_total_matches
        )


class LotteryReportBuilder:
    """Build reports from lottery backtesting results."""

    def build(
        self,
        result: BacktestResult,
        dataset_draws: int,
    ) -> LotteryReport:
        """Build a structured report from a backtest result."""

        return LotteryReport(
            dataset_draws=dataset_draws,
            test_cases=result.case_count,

            lrei_best_match=result.best_match,
            lrei_total_matches=result.total_matches,
            lrei_average_matches=result.average_matches,

            baseline_best_match=result.baseline_best_match,
            baseline_total_matches=result.baseline_total_matches,
            baseline_average_matches=(
                result.baseline_average_matches
            ),

            strong_total_matches=(
                result.strong_total_matches
            ),
            strong_average_matches=(
                result.strong_average_matches
            ),

            baseline_strong_total_matches=(
                result.baseline_strong_total_matches
            ),
            baseline_strong_average_matches=(
                result.baseline_strong_average_matches
            ),
        )


def format_report(report: LotteryReport) -> str:
    """Format a lottery report as readable text."""

    lines = [
        "=" * 60,
        "LREI LOTTERY BACKTEST REPORT",
        "=" * 60,
        f"Dataset draws: {report.dataset_draws}",
        f"Test cases: {report.test_cases}",
        "",
        "LREI",
        f"Best match: {report.lrei_best_match}",
        f"Total matches: {report.lrei_total_matches}",
        (
            "Average matches: "
            f"{report.lrei_average_matches:.4f}"
        ),
        "",
        "RANDOM BASELINE",
        f"Best match: {report.baseline_best_match}",
        (
            "Total matches: "
            f"{report.baseline_total_matches}"
        ),
        (
            "Average matches: "
            f"{report.baseline_average_matches:.4f}"
        ),
        "",
        "COMPARISON",
        (
            "Average advantage: "
            f"{report.average_advantage:+.4f}"
        ),
        (
            "Total advantage: "
            f"{report.total_advantage:+d}"
        ),
        "",
        "STRONG NUMBER",
        (
            "LREI correct predictions: "
            f"{report.strong_total_matches}"
        ),
        (
            "LREI average correct predictions: "
            f"{report.strong_average_matches:.4f}"
        ),
        (
            "Random correct predictions: "
            f"{report.baseline_strong_total_matches}"
        ),
        (
            "Random average correct predictions: "
            f"{report.baseline_strong_average_matches:.4f}"
        ),
        (
            "Strong-number advantage: "
            f"{report.strong_average_advantage:+.4f}"
        ),
        (
            "Strong-number total advantage: "
            f"{report.strong_total_advantage:+d}"
        ),
        "=" * 60,
    ]

    return "\n".join(lines)
