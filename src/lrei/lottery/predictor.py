"""Lottery number scoring and prediction support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class NumberScore:
    """Score assigned to one lottery number."""

    number: int
    score: float


class LotteryPredictor:
    """Deterministic statistical scorer for lottery numbers.

    This class does not claim to predict future lottery results.
    It converts historical statistics into comparable scores.
    """

    def __init__(
        self,
        frequency_weight: float = 0.7,
        recency_weight: float = 0.3,
    ) -> None:
        if frequency_weight < 0:
            raise ValueError("frequency_weight must be non-negative")

        if recency_weight < 0:
            raise ValueError("recency_weight must be non-negative")

        if frequency_weight == 0 and recency_weight == 0:
            raise ValueError(
                "At least one predictor weight must be greater than zero"
            )

        self.frequency_weight = frequency_weight
        self.recency_weight = recency_weight

    def score_numbers(
        self,
        frequencies: Mapping[int, int],
        recency_scores: Mapping[int, float] | None = None,
    ) -> tuple[NumberScore, ...]:
        """Return deterministic scores for all numbers in the input."""

        if not frequencies:
            return ()

        recency_scores = recency_scores or {}

        max_frequency = max(frequencies.values())

        if max_frequency <= 0:
            max_frequency = 1

        total_weight = self.frequency_weight + self.recency_weight

        scores: list[NumberScore] = []

        for number in sorted(frequencies):
            frequency = frequencies[number]

            if frequency < 0:
                raise ValueError(
                    f"Frequency cannot be negative: {frequency}"
                )

            frequency_score = frequency / max_frequency
            recency_score = float(recency_scores.get(number, 0.0))

            score = (
                self.frequency_weight * frequency_score
                + self.recency_weight * recency_score
            ) / total_weight

            scores.append(
                NumberScore(
                    number=number,
                    score=score,
                )
            )

        return tuple(scores)

    def rank_numbers(
        self,
        frequencies: Mapping[int, int],
        recency_scores: Mapping[int, float] | None = None,
    ) -> tuple[NumberScore, ...]:
        """Return numbers ordered from highest score to lowest score."""

        scored = self.score_numbers(
            frequencies=frequencies,
            recency_scores=recency_scores,
        )

        return tuple(
            sorted(
                scored,
                key=lambda item: (-item.score, item.number),
            )
        )
