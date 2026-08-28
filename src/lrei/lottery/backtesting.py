"""Chronological backtesting for lottery recommendations."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .dataset import LotteryDataset
from .recommendation import RecommendationEngine
from .statistics import LotteryStatistics


@dataclass(frozen=True)
class BacktestCase:
    """Results for one chronological test draw."""

    test_draw_id: str
    train_size: int

    generated_ticket_count: int
    recommended_ticket_count: int

    best_match: int
    total_matches: int
    average_matches: float

    baseline_best_match: int
    baseline_total_matches: int
    baseline_average_matches: float

    strong_match: int = 0
    baseline_strong_match: int = 0


@dataclass(frozen=True)
class BacktestResult:
    """Complete result of a chronological backtest."""

    cases: tuple[BacktestCase, ...]

    @property
    def case_count(self) -> int:
        return len(self.cases)

    @property
    def best_match(self) -> int:
        if not self.cases:
            return 0

        return max(
            case.best_match
            for case in self.cases
        )

    @property
    def total_matches(self) -> int:
        return sum(
            case.total_matches
            for case in self.cases
        )

    @property
    def average_matches(self) -> float:
        if not self.cases:
            return 0.0

        return (
            self.total_matches
            / self.case_count
        )

    @property
    def baseline_best_match(self) -> int:
        if not self.cases:
            return 0

        return max(
            case.baseline_best_match
            for case in self.cases
        )

    @property
    def baseline_total_matches(self) -> int:
        return sum(
            case.baseline_total_matches
            for case in self.cases
        )

    @property
    def baseline_average_matches(self) -> float:
        if not self.cases:
            return 0.0

        return (
            self.baseline_total_matches
            / self.case_count
        )

    @property
    def strong_total_matches(self) -> int:
        return sum(
            case.strong_match
            for case in self.cases
        )

    @property
    def baseline_strong_total_matches(self) -> int:
        return sum(
            case.baseline_strong_match
            for case in self.cases
        )

    def match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        if threshold < 0:
            raise ValueError(
                "threshold must be non-negative"
            )

        return sum(
            case.best_match >= threshold
            for case in self.cases
        )

    def baseline_match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        if threshold < 0:
            raise ValueError(
                "threshold must be non-negative"
            )

        return sum(
            case.baseline_best_match >= threshold
            for case in self.cases
        )

    def strong_match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        if threshold < 0:
            raise ValueError(
                "threshold must be non-negative"
            )

        return sum(
            case.strong_match >= threshold
            for case in self.cases
        )

    def baseline_strong_match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        if threshold < 0:
            raise ValueError(
                "threshold must be non-negative"
            )

        return sum(
            case.baseline_strong_match >= threshold
            for case in self.cases
        )


class LotteryBacktester:
    """Run chronological lottery backtests."""

    def __init__(
        self,
        engine: RecommendationEngine | None = None,
    ) -> None:
        self.engine = (
            engine
            if engine is not None
            else RecommendationEngine()
        )

    def run(
        self,
        dataset: LotteryDataset,
        train_size: int,
        test_size: int = 1,
        ticket_count: int = 50,
        seed: int | None = None,
    ) -> BacktestResult:
        """Run a chronological backtest.

        ``test_size`` is the number of draws evaluated at each
        chronological step. For the current project API, the
        complete remaining dataset is evaluated one draw at a
        time while the training window grows.
        """

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

        if len(dataset) <= train_size:
            raise ValueError(
                "dataset must contain at least one "
                "draw after train_size"
            )

        rng = random.Random(seed)

        cases: list[BacktestCase] = []

        for index in range(
            train_size,
            len(dataset),
        ):
            train_dataset = dataset[:index]
            test_draw = dataset[index]

            statistics = LotteryStatistics.from_dataset(
                train_dataset
            )

            recommendation_seed = rng.randrange(
                0,
                2**32,
            )

            result = self.engine.recommend(
                statistics=statistics,
                ticket_count=ticket_count,
                seed=recommendation_seed,
            )

            recommended = (
                result.recommended_tickets
            )

            generated_count = len(
                result.generated_tickets
            )

            recommended_count = len(
                recommended
            )

            actual_numbers = set(
                test_draw.numbers
            )

            main_match_counts = [
                len(
                    set(ticket)
                    & actual_numbers
                )
                for ticket in recommended
            ]

            if main_match_counts:
                best_match = max(
                    main_match_counts
                )
                total_matches = sum(
                    main_match_counts
                )
                average_matches = (
                    total_matches
                    / len(main_match_counts)
                )
            else:
                best_match = 0
                total_matches = 0
                average_matches = 0.0

            baseline_best_match = 0
            baseline_total_matches = 0

            population = tuple(
                sorted(
                    {
                        number
                        for draw in train_dataset
                        for number in draw.numbers
                    }
                )
            )

            numbers_per_ticket = len(
                test_draw.numbers
            )

            baseline_match_counts: list[int] = []

            if (
                population
                and len(population) >= numbers_per_ticket
            ):
                for _ in range(
                    max(recommended_count, 1)
                ):
                    baseline_ticket = rng.sample(
                        population,
                        numbers_per_ticket,
                    )

                    baseline_match_counts.append(
                        len(
                            set(baseline_ticket)
                            & actual_numbers
                        )
                    )

            if baseline_match_counts:
                baseline_best_match = max(
                    baseline_match_counts
                )
                baseline_total_matches = sum(
                    baseline_match_counts
                )
                baseline_average_matches = (
                    baseline_total_matches
                    / len(baseline_match_counts)
                )
            else:
                baseline_average_matches = 0.0

            strong_match = 0
            baseline_strong_match = 0

            actual_strong = getattr(
                test_draw,
                "strong_number",
                None,
            )

            if (
                actual_strong is not None
                and result.generated_tickets_with_strong
            ):
                strong_match = max(
                    (
                        int(
                            item.strong_number
                            == actual_strong
                        )
                        for item
                        in result.generated_tickets_with_strong
                        if item.strong_number is not None
                    ),
                    default=0,
                )

            strong_population = tuple(
                item.number
                for item
                in statistics.strong_number_frequency
            )

            if (
                actual_strong is not None
                and strong_population
            ):
                baseline_strong_match = int(
                    rng.choice(
                        strong_population
                    )
                    == actual_strong
                )

            cases.append(
                BacktestCase(
                    test_draw_id=test_draw.draw_id,
                    train_size=index,
                    generated_ticket_count=generated_count,
                    recommended_ticket_count=recommended_count,
                    best_match=best_match,
                    total_matches=total_matches,
                    average_matches=average_matches,
                    baseline_best_match=baseline_best_match,
                    baseline_total_matches=baseline_total_matches,
                    baseline_average_matches=baseline_average_matches,
                    strong_match=strong_match,
                    baseline_strong_match=baseline_strong_match,
                )
            )

        return BacktestResult(
            cases=tuple(cases)
        )
