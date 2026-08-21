"""Walk-forward backtesting for lottery recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from .baseline import RandomBaseline
from .dataset import LotteryDataset, WalkForwardDataset
from .recommendation import RecommendationEngine


class BacktestError(Exception):
    """Base exception for backtesting errors."""


@dataclass(frozen=True)
class BacktestCase:
    """Result for one walk-forward test case."""

    train_size: int
    test_size: int
    generated_ticket_count: int
    recommended_ticket_count: int
    test_draw_id: str

    best_match: int
    total_matches: int

    baseline_best_match: int
    baseline_total_matches: int


@dataclass(frozen=True)
class BacktestResult:
    """Aggregate results from a walk-forward backtest."""

    cases: tuple[BacktestCase, ...]

    @property
    def case_count(self) -> int:
        """Return the number of evaluated test cases."""

        return len(self.cases)

    @property
    def best_match(self) -> int:
        """Return the highest match from the recommendation engine."""

        if not self.cases:
            return 0

        return max(
            case.best_match
            for case in self.cases
        )

    @property
    def total_matches(self) -> int:
        """Return total matches from the recommendation engine."""

        return sum(
            case.total_matches
            for case in self.cases
        )

    @property
    def average_matches(self) -> float:
        """Return average matches per test case."""

        if not self.cases:
            return 0.0

        return self.total_matches / self.case_count

    @property
    def baseline_best_match(self) -> int:
        """Return the highest match from the random baseline."""

        if not self.cases:
            return 0

        return max(
            case.baseline_best_match
            for case in self.cases
        )

    @property
    def baseline_total_matches(self) -> int:
        """Return total matches from the random baseline."""

        return sum(
            case.baseline_total_matches
            for case in self.cases
        )

    @property
    def baseline_average_matches(self) -> float:
        """Return average baseline matches per test case."""

        if not self.cases:
            return 0.0

        return (
            self.baseline_total_matches
            / self.case_count
        )

    def match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        """Return cases where recommendation reaches a match threshold."""

        if threshold <= 0:
            raise ValueError(
                "threshold must be positive"
            )

        return sum(
            1
            for case in self.cases
            if case.best_match >= threshold
        )

    def baseline_match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        """Return baseline cases reaching a match threshold."""

        if threshold <= 0:
            raise ValueError(
                "threshold must be positive"
            )

        return sum(
            1
            for case in self.cases
            if case.baseline_best_match >= threshold
        )


class LotteryBacktester:
    """Evaluate recommendations using chronological walk-forward testing."""

    def __init__(
        self,
        engine: RecommendationEngine | None = None,
        baseline: RandomBaseline | None = None,
    ) -> None:
        self.engine = engine or RecommendationEngine()
        self.baseline = baseline or RandomBaseline()

    def run(
        self,
        dataset: LotteryDataset,
        train_size: int,
        test_size: int = 1,
        ticket_count: int = 50,
        seed: int | None = None,
    ) -> BacktestResult:
        """Run a chronological walk-forward backtest."""

        if train_size <= 0:
            raise ValueError(
                "train_size must be positive"
            )

        if test_size <= 0:
            raise ValueError(
                "test_size must be positive"
            )

        if ticket_count <= 0:
            raise ValueError(
                "ticket_count must be positive"
            )

        if train_size + test_size > len(dataset):
            raise BacktestError(
                "train_size + test_size exceeds dataset size"
            )

        walk_forward = WalkForwardDataset(
            dataset=dataset,
            train_size=train_size,
            test_size=test_size,
        )

        cases: list[BacktestCase] = []

        for split_index, (train, test) in enumerate(
            walk_forward.splits()
        ):
            statistics = self._statistics_from_dataset(
                train
            )

            result = self.engine.recommend(
                statistics=statistics,
                ticket_count=ticket_count,
                seed=(
                    seed + split_index
                    if seed is not None
                    else None
                ),
            )

            recommended_tickets = (
                result.recommended_tickets
            )

            baseline_tickets = (
                self.baseline.generate_tickets(
                    count=len(recommended_tickets),
                    seed=(
                        seed + 10_000 + split_index
                        if seed is not None
                        else None
                    ),
                )
            )

            for test_draw in test:
                actual_numbers = set(
                    test_draw.numbers
                )

                best_match = 0
                total_matches = 0

                for ticket in recommended_tickets:
                    matches = len(
                        set(ticket) & actual_numbers
                    )

                    best_match = max(
                        best_match,
                        matches,
                    )
                    total_matches += matches

                baseline_best_match = 0
                baseline_total_matches = 0

                for ticket in baseline_tickets:
                    matches = len(
                        set(ticket) & actual_numbers
                    )

                    baseline_best_match = max(
                        baseline_best_match,
                        matches,
                    )
                    baseline_total_matches += matches

                cases.append(
                    BacktestCase(
                        train_size=len(train),
                        test_size=len(test),
                        generated_ticket_count=len(
                            result.generated_tickets
                        ),
                        recommended_ticket_count=len(
                            recommended_tickets
                        ),
                        test_draw_id=test_draw.draw_id,
                        best_match=best_match,
                        total_matches=total_matches,
                        baseline_best_match=(
                            baseline_best_match
                        ),
                        baseline_total_matches=(
                            baseline_total_matches
                        ),
                    )
                )

        return BacktestResult(
            cases=tuple(cases)
        )

    @staticmethod
    def _statistics_from_dataset(
        dataset: LotteryDataset,
    ):
        from .statistics import LotteryStatistics

        return LotteryStatistics.from_dataset(
            dataset
        )
