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
    strong_number: int | None = None


@dataclass(frozen=True)
class RecommendationResult:
    """Final recommendation result."""

    scores: tuple[NumberScore, ...]
    generated_tickets: tuple[tuple[int, ...], ...]
    recommended_tickets: tuple[tuple[int, ...], ...]

    strong_scores: tuple[NumberScore, ...] = ()

    generated_tickets_with_strong: tuple[
        RecommendedTicket, ...
    ] = ()

    recommended_tickets_with_strong: tuple[
        RecommendedTicket, ...
    ] = ()


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
            if predictor is not None
            else LotteryPredictor()
        )

        self.generator = (
            generator
            if generator is not None
            else TicketGenerator()
        )

        self.optimizer = (
            optimizer
            if optimizer is not None
            else LotteryOptimizer(
                OptimizerConfig(
                    max_overlap=4,
                    max_tickets=14,
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

        if not frequencies:
            raise RecommendationError(
                "Statistics does not contain number frequency data"
            )

        scores = self.predictor.score_numbers(
            frequencies=frequencies,
        )

        if not scores:
            raise RecommendationError(
                "Predictor returned no number scores"
            )

        rng = random.Random(seed)
        generated: list[tuple[int, ...]] = []
        recommended: tuple[tuple[int, ...], ...] = ()

        # The public recommendation target is 14 tickets.  The optimizer
        # may reject candidates because of the overlap constraint, so keep
        # generating fresh candidates until the full portfolio is possible.
        target_tickets = min(
            self.optimizer.config.max_tickets,
            14,
        )

        batch_size = max(ticket_count, target_tickets * 10)

        for _ in range(5):
            for _ in range(batch_size):
                generated.append(
                    self.generator.generate_ticket(
                        scores=scores,
                        rng=rng,
                    )
                )

            recommended = self.optimizer.optimize(generated)

            if len(recommended) >= target_tickets:
                recommended = recommended[:target_tickets]
                break

        if len(recommended) != target_tickets:
            raise RecommendationError(
                "Optimizer could not produce the required "
                f"{target_tickets} recommended tickets"
            )

        strong_scores = self._score_strong_numbers(
            statistics
        )

        generated_with_strong: list[
            RecommendedTicket
        ] = []

        recommended_with_strong: list[
            RecommendedTicket
        ] = []

        if strong_scores:
            for ticket in generated:
                strong_number = (
                    self.generator.generate_strong_number(
                        scores=strong_scores,
                        rng=rng,
                    )
                )

                generated_with_strong.append(
                    RecommendedTicket(
                        numbers=ticket,
                        strong_number=strong_number,
                    )
                )

            for ticket in recommended:
                strong_number = (
                    self.generator.generate_strong_number(
                        scores=strong_scores,
                        rng=rng,
                    )
                )
                recommended_with_strong.append(
                    RecommendedTicket(
                        numbers=ticket,
                        strong_number=strong_number,
                    )
                )

        else:
            generated_with_strong = [
                RecommendedTicket(
                    numbers=ticket,
                    strong_number=None,
                )
                for ticket in generated
            ]

            recommended_with_strong = [
                RecommendedTicket(
                    numbers=ticket,
                    strong_number=None,
                )
                for ticket in recommended
            ]

        return RecommendationResult(
            scores=tuple(scores),
            generated_tickets=tuple(generated),
            recommended_tickets=tuple(recommended),
            strong_scores=tuple(strong_scores),
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
        """Score strong numbers when available."""

        strong_frequency = getattr(
            statistics,
            "strong_number_frequency",
            (),
        )

        if not strong_frequency:
            return ()

        frequencies = {
            item.number: item.count
            for item in strong_frequency
        }

        if not frequencies:
            return ()

        return tuple(
            self.predictor.score_numbers(
                frequencies=frequencies,
            )
        )
