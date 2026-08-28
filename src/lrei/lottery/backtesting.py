"""Backtesting utilities for the lottery recommendation engine."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .dataset import LotteryDataset
from .recommendation import RecommendationEngine, RecommendedTicket
from .statistics import LotteryStatistics


@dataclass(frozen=True)
class BacktestCase:
    """One chronological backtest case."""

    train: LotteryDataset
    actual_numbers: tuple[int, ...]
    actual_strong_number: int | None


@dataclass(frozen=True)
class BacktestResult:
    """Aggregated results from a lottery backtest."""

    match_counts: tuple[int, ...]
    baseline_match_counts: tuple[int, ...]

    strong_match_counts: tuple[int, ...] = ()
    baseline_strong_match_counts: tuple[int, ...] = ()

    ticket_counts: tuple[int, ...] = ()

    @property
    def case_count(self) -> int:
        """Number of evaluated test cases."""
        return len(self.match_counts)

    @property
    def total_matches(self) -> int:
        """Total main-number matches."""
        return sum(self.match_counts)

    @property
    def baseline_total_matches(self) -> int:
        """Total main-number matches for the random baseline."""
        return sum(self.baseline_match_counts)

    @property
    def average_matches(self) -> float:
        """Average main-number matches per test case."""
        if not self.match_counts:
            return 0.0

        return self.total_matches / len(self.match_counts)

    @property
    def baseline_average_matches(self) -> float:
        """Average baseline matches per test case."""
        if not self.baseline_match_counts:
            return 0.0

        return (
            self.baseline_total_matches
            / len(self.baseline_match_counts)
        )

    @property
    def strong_total_matches(self) -> int:
        """Total strong-number matches."""
        return sum(self.strong_match_counts)

    @property
    def baseline_strong_total_matches(self) -> int:
        """Total baseline strong-number matches."""
        return sum(self.baseline_strong_match_counts)

    @property
    def strong_average_matches(self) -> float:
        """Average strong-number matches per test case."""
        if not self.strong_match_counts:
            return 0.0

        return (
            self.strong_total_matches
            / len(self.strong_match_counts)
        )

    @property
    def baseline_strong_average_matches(self) -> float:
        """Average baseline strong-number matches per test case."""
        if not self.baseline_strong_match_counts:
            return 0.0

        return (
            self.baseline_strong_total_matches
            / len(self.baseline_strong_match_counts)
        )

    def match_count_at_least(self, threshold: int) -> int:
        """Count cases with at least threshold main-number matches."""
        if threshold < 0:
            raise ValueError("threshold must be non-negative")

        return sum(
            count >= threshold
            for count in self.match_counts
        )

    def baseline_match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        """Count baseline cases with at least threshold matches."""
        if threshold < 0:
            raise ValueError("threshold must be non-negative")

        return sum(
            count >= threshold
            for count in self.baseline_match_counts
        )

    def strong_match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        """Count cases with at least threshold strong matches."""
        if threshold < 0:
            raise ValueError("threshold must be non-negative")

        return sum(
            count >= threshold
            for count in self.strong_match_counts
        )

    def baseline_strong_match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        """Count baseline cases with at least threshold strong matches."""
        if threshold < 0:
            raise ValueError("threshold must be non-negative")

        return sum(
            count >= threshold
            for count in self.baseline_strong_match_counts
        )


class LotteryBacktester:
    """Evaluate lottery recommendations chronologically."""

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
        """Run a chronological backtest."""

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
                "dataset must contain draws after train_size"
            )

        rng = random.Random(seed)

        match_counts: list[int] = []
        baseline_match_counts: list[int] = []

        strong_match_counts: list[int] = []
        baseline_strong_match_counts: list[int] = []

        ticket_counts: list[int] = []

        start = train_size
        end = min(
            len(dataset),
            train_size + test_size,
        )

        for index in range(start, end):
            train_draws = dataset[:index]
            actual_draw = dataset[index]

            statistics = LotteryStatistics.from_dataset(
                train_draws
            )

            case_seed = rng.randrange(
                0,
                2**32,
            )

            result = self.engine.recommend(
                statistics=statistics,
                ticket_count=ticket_count,
                seed=case_seed,
            )

            recommended_tickets = (
                result.recommended_tickets_with_strong
            )

            if not recommended_tickets:
                recommended_tickets = tuple(
                    RecommendedTicket(
                        numbers=ticket,
                        strong_number=None,
                    )
                    for ticket in result.recommended_tickets
                )

            actual_numbers = set(
                actual_draw.numbers
            )

            best_match = 0
            best_strong_match = 0

            for ticket in recommended_tickets:
                main_matches = len(
                    set(ticket.numbers)
                    & actual_numbers
                )

                if main_matches > best_match:
                    best_match = main_matches

                if (
                    ticket.strong_number is not None
                    and actual_draw.strong_number is not None
                    and ticket.strong_number
                    == actual_draw.strong_number
                ):
                    best_strong_match = 1

            match_counts.append(best_match)
            strong_match_counts.append(
                best_strong_match
            )
            ticket_counts.append(
                len(recommended_tickets)
            )

            baseline_best = self._random_baseline_best_match(
                actual_numbers=actual_numbers,
                dataset=train_draws,
                ticket_count=len(recommended_tickets),
                rng=rng,
            )

            baseline_match_counts.append(
                baseline_best
            )

            baseline_strong = self._random_baseline_strong_match(
                actual_strong_number=actual_draw.strong_number,
                statistics=statistics,
                rng=rng,
            )

            baseline_strong_match_counts.append(
                baseline_strong
            )

        return BacktestResult(
            match_counts=tuple(match_counts),
            baseline_match_counts=tuple(
                baseline_match_counts
            ),
            strong_match_counts=tuple(
                strong_match_counts
            ),
            baseline_strong_match_counts=tuple(
                baseline_strong_match_counts
            ),
            ticket_counts=tuple(ticket_counts),
        )

    @staticmethod
    def _random_baseline_best_match(
        actual_numbers: set[int],
        dataset: LotteryDataset,
        ticket_count: int,
        rng: random.Random,
    ) -> int:
        """Generate a random baseline and return its best match."""

        all_numbers: set[int] = set()

        for draw in dataset:
            all_numbers.update(draw.numbers)

        if not all_numbers:
            return 0

        if ticket_count <= 0:
            return 0

        sample_size = len(
            next(iter(dataset)).numbers
        )

        if sample_size > len(all_numbers):
            return 0

        best = 0

        population = tuple(
            sorted(all_numbers)
        )

        for _ in range(ticket_count):
            ticket = rng.sample(
                population,
                sample_size,
            )

            matches = len(
                set(ticket) & actual_numbers
            )

            if matches > best:
                best = matches

        return best

    @staticmethod
    def _random_baseline_strong_match(
        actual_strong_number: int | None,
        statistics: LotteryStatistics,
        rng: random.Random,
    ) -> int:
        """Evaluate a random strong-number baseline."""

        if actual_strong_number is None:
            return 0

        available = tuple(
            item.number
            for item in statistics.strong_number_frequency
        )

        if not available:
            return 0

        selected = rng.choice(
            available
        )

        return int(
            selected == actual_strong_number
        )
