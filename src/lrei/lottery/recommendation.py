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
class RecommendationResult:
    """Final recommendation result."""

    scores: tuple[NumberScore, ...]
    generated_tickets: tuple[tuple[int, ...], ...]
    recommended_tickets: tuple[tuple[int, ...], ...]


class RecommendationEngine:
    """Coordinate statistics, prediction, generation, and optimization."""

    def __init__(
        self,
        predictor: LotteryPredictor | None = None,
        generator: TicketGenerator | None = None,
        optimizer: LotteryOptimizer | None = None,
    ) -> None:
        self.predictor = predictor or LotteryPredictor()
        self.generator = generator or TicketGenerator()
        self.optimizer = optimizer or LotteryOptimizer(
            OptimizerConfig(max_overlap=4, max_tickets=10)
        )

    def recommend(
        self,
        statistics: LotteryStatistics,
        ticket_count: int = 50,
        seed: int | None = None,
    ) -> RecommendationResult:
        """Generate and optimize lottery ticket recommendations."""

        if ticket_count <= 0:
            raise ValueError("ticket_count must be positive")

        frequencies = statistics.frequencies()

        scores = self.predictor.score_numbers(
            frequencies=frequencies,
        )

        rng = random.Random(seed)

        generated: list[tuple[int, ...]] = []

        for _ in range(ticket_count):
            generated.append(
                self.generator.generate_ticket(
                    scores=scores,
                    rng=rng,
                )
            )

        recommended = self.optimizer.optimize(generated)

        if not recommended:
            raise RecommendationError(
                "Optimizer returned no recommended tickets"
            )

        return RecommendationResult(
            scores=tuple(scores),
            generated_tickets=tuple(generated),
            recommended_tickets=recommended,
        )
