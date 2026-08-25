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

    # Strong-number metrics.
    strong_number_match: int
    baseline_strong_number_match: int


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
        """Return the highest main-number match."""

        if not self.cases:
            return 0

        return max(
            case.best_match
            for case in self.cases
        )

    @property
    def total_matches(self) -> int:
        """Return total main-number matches."""

        return sum(
            case.total_matches
            for case in self.cases
        )

    @property
    def average_matches(self) -> float:
        """Return average main-number matches."""

        if not self.cases:
            return 0.0

        return (
            self.total_matches
            / self.case_count
        )

    @property
    def baseline_best_match(self) -> int:
        """Return the highest baseline main-number match."""

        if not self.cases:
            return 0

        return max(
            case.baseline_best_match
            for case in self.cases
        )

    @property
    def baseline_total_matches(self) -> int:
        """Return total baseline main-number matches."""

        return sum(
            case.baseline_total_matches
            for case in self.cases
        )

    @property
    def baseline_average_matches(self) -> float:
        """Return average baseline main-number matches."""

        if not self.cases:
            return 0.0

        return (
            self.baseline_total_matches
            / self.case_count
        )

    @property
    def strong_number_hits(self) -> int:
        """Return number of correct strong-number predictions."""

        return sum(
            case.strong_number_match
            for case in self.cases
        )

    @property
    def baseline_strong_number_hits(self) -> int:
        """Return correct strong-number baseline predictions."""

        return sum(
            case.baseline_strong_number_match
            for case in self.cases
        )

    @property
    def strong_number_accuracy(self) -> float:
        """Return strong-number prediction accuracy."""

        if not self.cases:
            return 0.0

        return (
            self.strong_number_hits
            / self.case_count
        )

    @property
    def baseline_strong_number_accuracy(
        self,
    ) -> float:
        """Return baseline strong-number accuracy."""

        if not self.cases:
            return 0.0

        return (
            self.baseline_strong_number_hits
            / self.case_count
        )


class LotteryBacktester:
    """Evaluate recommendations chronologically."""

    def __init__(
        self,
        engine: RecommendationEngine | None = None,
        baseline: RandomBaseline | None = None,
    ) -> None:
        self.engine = (
            engine
            or RecommendationEngine()
        )

        self.baseline = (
            baseline
            or RandomBaseline()
        )

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

        if (
            train_size + test_size
            > len(dataset)
        ):
            raise BacktestError(
                "train_size + test_size exceeds "
                "dataset size"
            )

        walk_forward = WalkForwardDataset(
            dataset=dataset,
            train_size=train_size,
            test_size=test_size,
        )

        cases: list[BacktestCase] = []

        for split_index, (
            train,
            test,
        ) in enumerate(
            walk_forward.splits()
        ):
            statistics = (
                self._statistics_from_dataset(
                    train
                )
            )

            result = (
                self.engine.recommend(
                    statistics=statistics,
                    ticket_count=ticket_count,
                    seed=(
                        seed + split_index
                        if seed is not None
                        else None
                    ),
                )
            )

            recommended_tickets = (
                result.recommended_tickets
            )

            baseline_tickets = (
                self.baseline.generate_tickets(
                    count=len(
                        recommended_tickets
                    ),
                    seed=(
                        seed + 10_000 + split_index
                        if seed is not None
                        else None
                    ),
                )
            )

            recommended_with_strong = (
                result.recommended_tickets_with_strong
            )

            for test_draw in test:
                actual_numbers = set(
                    test_draw.numbers
                )

                # -------------------------
                # Main numbers
                # -------------------------

                best_match = 0
                total_matches = 0

                for ticket in (
                    recommended_tickets
                ):
                    matches = len(
                        set(ticket)
                        & actual_numbers
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
                        set(ticket)
                        & actual_numbers
                    )

                    baseline_best_match = max(
                        baseline_best_match,
                        matches,
                    )

                    baseline_total_matches += (
                        matches
                    )

                # -------------------------
                # Strong number
                # -------------------------

                strong_number_match = 0

                actual_strong = (
                    test_draw.strong_number
                )

                if (
                    actual_strong is not None
                    and recommended_with_strong
                ):
                    for recommendation in (
                        recommended_with_strong
                    ):
                        if (
                            recommendation.strong_number
                            == actual_strong
                        ):
                            strong_number_match += 1

                # Random strong-number baseline.
                #
                # RandomBaseline historically generates
                # only main-number tickets, so for now we
                # calculate the expected random strong
                # probability from the valid strong range.
                baseline_strong_number_match = 0

                if actual_strong is not None:
                    baseline_strong_number_match = (
                        self._random_strong_matches(
                            actual_strong=actual_strong,
                            ticket_count=len(
                                baseline_tickets
                            ),
                            seed=(
                                seed
                                + 20_000
                                + split_index
                                if seed is not None
                                else None
                            ),
                        )
                    )

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
                        strong_number_match=(
                            strong_number_match
                        ),
                        baseline_strong_number_match=(
                            baseline_strong_number_match
                        ),
                    )
                )

        return BacktestResult(
            cases=tuple(cases)
        )

    @staticmethod
    def _random_strong_matches(
        actual_strong: int,
        ticket_count: int,
        seed: int | None,
    ) -> int:
        """
        Generate a deterministic random strong-number baseline.

        The current lottery format uses strong numbers 1-7.
        """

        if ticket_count <= 0:
            return 0

        import random

        rng = random.Random(seed)

        matches = 0

        for _ in range(ticket_count):
            predicted = rng.randint(1, 7)

            if predicted == actual_strong:
                matches += 1

        return matches

    @staticmethod
    def _statistics_from_dataset(
        dataset: LotteryDataset,
    ):
        from .statistics import LotteryStatistics

        return LotteryStatistics.from_dataset(
            dataset
        )
