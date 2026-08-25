"""End-to-end lottery recommendation engine."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .generator import TicketGenerator
from .optimizer import LotteryOptimizer, OptimizerConfig
from .predictor import LotteryPredictor, NumberScore
from .statistics import LotteryStatistics


class RecommendationError(Exception):
    """Base exception for recommendation errors."""


@dataclass(frozen=True)
class RecommendedTicket:
    """One recommended lottery ticket."""

    numbers: tuple[int, ...]
    strong_number: int


@dataclass(frozen=True)
class RecommendationResult:
    """Final recommendation result."""

    scores: tuple[NumberScore, ...]
    strong_scores: tuple[NumberScore, ...]
    generated_tickets: tuple[tuple[int, ...], ...]
    recommended_tickets: tuple[tuple[int, ...], ...]
    generated_tickets_with_strong: tuple[
        RecommendedTicket, ...
    ]
    recommended_tickets_with_strong: tuple[
        RecommendedTicket, ...
    ]


class RecommendationEngine:
    """Coordinate statistics, prediction, generation, and optimization."""

    def __init__(
        self,
        predictor: LotteryPredictor | None = None,
        generator: TicketGenerator | None = None,
        optimizer: LotteryOptimizer | None = None,
    ) -> None:
        self.predictor = (
            predictor
            or LotteryPredictor()
        )

        self.generator = (
            generator
            or TicketGenerator()
        )

        self.optimizer = (
            optimizer
            or LotteryOptimizer(
                OptimizerConfig(
                    max_overlap=4,
                    max_tickets=10,
                )
            )
        )

    def recommend(
        self,
        statistics: LotteryStatistics,
        ticket_count: int = 50,
        seed: int | None = None,
    ) -> RecommendationResult:
        """Generate and optimize lottery ticket recommendations."""

        if ticket_count <= 0:
            raise ValueError(
                "ticket_count must be positive"
            )

        frequencies = {
            item.number: item.count
            for item in statistics.number_frequency
        }

        scores = self.predictor.score_numbers(
            frequencies=frequencies,
        )

        strong_scores = self._score_strong_numbers(
            statistics
        )

        rng = random.Random(seed)

        generated: list[
            tuple[int, ...]
        ] = []

        generated_with_strong: list[
            RecommendedTicket
        ] = []

        for _ in range(ticket_count):
            ticket = self.generator.generate_ticket(
                scores=scores,
                rng=rng,
            )

            strong_number = (
                self.generator.generate_strong_number(
                    scores=strong_scores,
                    rng=rng,
                )
            )

            generated.append(ticket)

            generated_with_strong.append(
                RecommendedTicket(
                    numbers=ticket,
                    strong_number=strong_number,
                )
            )

        recommended = self.optimizer.optimize(
            generated
        )

        if not recommended:
            raise RecommendationError(
                "Optimizer returned no recommended tickets"
            )

        recommended_set = set(recommended)

        recommended_with_strong: list[
            RecommendedTicket
        ] = []

        for item in generated_with_strong:
            if item.numbers in recommended_set:
                recommended_with_strong.append(item)

        if not recommended_with_strong:
            raise RecommendationError(
                "No strong-number recommendations "
                "remain after optimization"
            )

        return RecommendationResult(
            scores=tuple(scores),
            strong_scores=tuple(strong_scores),
            generated_tickets=tuple(generated),
            recommended_tickets=recommended,
            generated_tickets_with_strong=tuple(
                generated_with_strong
            ),
            recommended_tickets_with_strong=tuple(
                recommended_with_strong
            ),
        )

    def _score_strong_numbers(
        self,
        statistics: LotteryStatistics,
    ) -> tuple[NumberScore, ...]:
        """Score strong numbers independently."""

        strong_frequencies = (
            self._extract_strong_frequencies(
                statistics
            )
        )

        return self.predictor.score_numbers(
            frequencies=strong_frequencies,
        )

    @staticmethod
    def _extract_strong_frequencies(
        statistics: LotteryStatistics,
    ) -> dict[int, int]:
        """
        Extract strong-number frequencies.

        This method supports statistics implementations
        that expose strong-number frequency data.
        """

        for attribute_name in (
            "strong_number_frequency",
            "strong_frequency",
            "strong_frequencies",
        ):
            value = getattr(
                statistics,
                attribute_name,
                None,
            )

            if value is None:
                continue

            if isinstance(value, dict):
                return {
                    int(number): int(count)
                    for number, count in value.items()
                }

            result: dict[int, int] = {}

            for item in value:
                number = getattr(
                    item,
                    "number",
                    None,
                )

                count = getattr(
                    item,
                    "count",
                    None,
                )

                if number is not None and count is not None:
                    result[int(number)] = int(count)

            if result:
                return result

        raise RecommendationError(
            "Statistics does not contain strong-number "
            "frequency data"
        )
