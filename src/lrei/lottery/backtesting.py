"""Lottery backtesting utilities."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .dataset import LotteryDataset
from .recommendation import RecommendationEngine
from .statistics import LotteryStatistics


@dataclass(frozen=True)
class BacktestCase:
    """Result of evaluating one historical lottery draw."""

    test_draw_id: str
    train_size: int

    generated_ticket_count: int
    recommended_ticket_count: int

    best_match: int
    total_matches: int

    baseline_best_match: int
    baseline_total_matches: int

    strong_match: int = 0
    baseline_strong_match: int = 0


@dataclass(frozen=True)
class BacktestResult:
    """Aggregate result of a lottery backtest."""

    cases: tuple[BacktestCase, ...]

    @property
    def case_count(self) -> int:
        return len(self.cases)

    @property
    def best_match(self) -> int:
        if not self.cases:
            return 0

        return max(case.best_match for case in self.cases)

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
    def strong_match_count(self) -> int:
        return sum(
            case.strong_match
            for case in self.cases
        )

    @property
    def baseline_strong_match_count(self) -> int:
        return sum(
            case.baseline_strong_match
            for case in self.cases
        )

    def match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        """Count cases whose best match reaches threshold."""

        return sum(
            1
            for case in self.cases
            if case.best_match >= threshold
        )

    def baseline_match_count_at_least(
        self,
        threshold: int,
    ) -> int:
        """Count baseline cases reaching threshold."""

        return sum(
            1
            for case in self.cases
            if case.baseline_best_match >= threshold
        )


class LotteryBacktester:
    """Evaluate the recommendation engine on historical draws."""

    def __init__(
        self,
        recommendation_engine: (
            RecommendationEngine | None
        ) = None,
    ) -> None:
        self.recommendation_engine = (
            recommendation_engine
            or RecommendationEngine()
        )

    def run(
        self,
        dataset: LotteryDataset,
        train_size: int,
        test_size: int = 1,
        ticket_count: int = 50,
        seed: int | None = None,
    ) -> BacktestResult:
        """Run chronological walk-forward backtesting."""

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
                "dataset is too small for backtesting"
            )

        records = list(dataset)

        cases: list[BacktestCase] = []

        master_rng = random.Random(seed)

        for test_index in range(
            train_size,
            len(records),
            test_size,
        ):
            train_records = records[:test_index]

            if not train_records:
                continue

            test_records = records[
                test_index:
                min(
                    test_index + test_size,
                    len(records),
                )
            ]

            if not test_records:
                continue

            training_dataset = LotteryDataset(
                train_records
            )

            statistics = (
                LotteryStatistics.from_dataset(
                    training_dataset
                )
            )

            case_seed = master_rng.randint(
                0,
                2**31 - 1,
            )

            recommendation = (
                self.recommendation_engine.recommend(
                    statistics=statistics,
                    ticket_count=ticket_count,
                    seed=case_seed,
                )
            )

            recommended_tickets = (
                recommendation.recommended_tickets
            )

            generated_count = len(
                recommendation.generated_tickets
            )

            recommended_count = len(
                recommended_tickets
            )

            for test_draw in test_records:
                actual_numbers = set(
                    test_draw.numbers
                )

                ticket_matches = [
                    len(
                        set(ticket)
                        & actual_numbers
                    )
                    for ticket in recommended_tickets
                ]

                best_match = (
                    max(ticket_matches)
                    if ticket_matches
                    else 0
                )

                total_matches = sum(
                    ticket_matches
                )

                baseline_rng = random.Random(
                    case_seed
                    + hash(
                        test_draw.draw_id
                    ) % 1_000_000
                )

                baseline_tickets = (
                    self._generate_random_tickets(
                        statistics=statistics,
                        ticket_count=recommended_count,
                        rng=baseline_rng,
                    )
                )

                baseline_matches = [
                    len(
                        set(ticket)
                        & actual_numbers
                    )
                    for ticket in baseline_tickets
                ]

                baseline_best_match = (
                    max(baseline_matches)
                    if baseline_matches
                    else 0
                )

                baseline_total_matches = sum(
                    baseline_matches
                )

                strong_match = 0
                baseline_strong_match = 0

                actual_strong = getattr(
                    test_draw,
                    "strong_number",
                    None,
                )

                if (
                    actual_strong is not None
                    and recommendation
                    .recommended_tickets_with_strong
                ):
                    strong_match = sum(
                        1
                        for ticket in (
                            recommendation
                            .recommended_tickets_with_strong
                        )
                        if (
                            ticket.strong_number
                            == actual_strong
                        )
                    )

                    baseline_strong_match = (
                        self._random_strong_matches(
                            statistics=statistics,
                            actual_strong=actual_strong,
                            ticket_count=recommended_count,
                            rng=baseline_rng,
                        )
                    )

                cases.append(
                    BacktestCase(
                        test_draw_id=test_draw.draw_id,
                        train_size=len(
                            train_records
                        ),
                        generated_ticket_count=(
                            generated_count
                        ),
                        recommended_ticket_count=(
                            recommended_count
                        ),
                        best_match=best_match,
                        total_matches=(
                            total_matches
                        ),
                        baseline_best_match=(
                            baseline_best_match
                        ),
                        baseline_total_matches=(
                            baseline_total_matches
                        ),
                        strong_match=strong_match,
                        baseline_strong_match=(
                            baseline_strong_match
                        ),
                    )
                )

        return BacktestResult(
            cases=tuple(cases)
        )

    def _generate_random_tickets(
        self,
        statistics: LotteryStatistics,
        ticket_count: int,
        rng: random.Random,
    ) -> tuple[tuple[int, ...], ...]:
        """Generate random baseline tickets."""

        minimum = (
            statistics.minimum_number
        )

        maximum = (
            statistics.maximum_number
        )

        if minimum is None or maximum is None:
            return ()

        numbers_per_ticket = (
            self._numbers_per_ticket(
                statistics
            )
        )

        population = list(
            range(
                minimum,
                maximum + 1,
            )
        )

        if (
            len(population)
            < numbers_per_ticket
        ):
            return ()

        tickets: list[
            tuple[int, ...]
        ] = []

        for _ in range(ticket_count):
            ticket = tuple(
                sorted(
                    rng.sample(
                        population,
                        numbers_per_ticket,
                    )
                )
            )

            tickets.append(ticket)

        return tuple(tickets)

    def _numbers_per_ticket(
        self,
        statistics: LotteryStatistics,
    ) -> int:
        """Determine how many main numbers a ticket uses."""

        if statistics.draw_count <= 0:
            return 6

        if statistics.total_numbers <= 0:
            return 6

        estimated = round(
            statistics.total_numbers
            / statistics.draw_count
        )

        return max(1, estimated)

    def _random_strong_matches(
        self,
        statistics: LotteryStatistics,
        actual_strong: int,
        ticket_count: int,
        rng: random.Random,
    ) -> int:
        """Evaluate random strong-number selections."""

        strong_numbers = [
            item.number
            for item in getattr(
                statistics,
                "strong_number_frequency",
                (),
            )
        ]

        if not strong_numbers:
            return 0

        matches = 0

        for _ in range(ticket_count):
            selected = rng.choice(
                strong_numbers
            )

            if selected == actual_strong:
                matches += 1

        return matches
