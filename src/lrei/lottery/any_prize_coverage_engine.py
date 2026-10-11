"""Greedy portfolio construction for the probability of winning any prize.

For Israeli Lotto, any prize requires at least three matching main numbers.
This engine does not predict which numbers will be drawn. It samples a pool of
valid tickets and greedily maximizes the exact union of 3+-match draw outcomes
represented by those tickets.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Iterable, Sequence

from .dataset import LotteryDataset
from .predictor import NumberScore
from .recommendation import RecommendationResult, RecommendedTicket


MAX_NUMBER = 37
DRAW_SIZE = 6
ANY_PRIZE_THRESHOLD = 3
TOTAL_DRAWS = comb(MAX_NUMBER, DRAW_SIZE)


@dataclass(frozen=True)
class AnyPrizeCoverageConfig:
    """Bounded settings for exact any-prize coverage selection."""

    candidate_count: int = 100
    max_tickets: int = 14

    def __post_init__(self) -> None:
        if self.candidate_count < self.max_tickets:
            raise ValueError("candidate_count must cover max_tickets")
        if self.candidate_count > 500:
            raise ValueError("candidate_count must not exceed 500")
        if self.max_tickets != 14:
            raise ValueError("any-prize coverage is defined for exactly 14 tickets")


class AnyPrizeCoverageRecommendationEngine:
    """Greedily maximize exact portfolio coverage for at least 3/6 main hits."""

    def __init__(self, config: AnyPrizeCoverageConfig | None = None) -> None:
        self.config = config or AnyPrizeCoverageConfig()
        self._choose = self._build_choose_table()

    @staticmethod
    def _build_choose_table() -> tuple[tuple[int, ...], ...]:
        """Precompute binomial coefficients used by the combination rank."""
        rows = []
        for n in range(MAX_NUMBER):
            row = []
            for k in range(DRAW_SIZE + 1):
                row.append(comb(n, k) if k <= n else 0)
            rows.append(tuple(row))
        return tuple(rows)

    @classmethod
    def _draw_rank(
        cls, draw: Sequence[int], choose: tuple[tuple[int, ...], ...]
    ) -> int:
        """Map a sorted 6-number draw to a unique colexicographic integer ID."""
        return sum(choose[number - 1][position] for position, number in enumerate(draw, 1))

    @classmethod
    def _coverage_mask(
        cls,
        ticket: Sequence[int],
        choose: tuple[tuple[int, ...], ...] | None = None,
    ) -> int:
        """Encode all 6/37 draws with 3+ matches as a compact integer bit mask."""
        numbers = tuple(sorted(ticket))
        if len(numbers) != DRAW_SIZE or len(set(numbers)) != DRAW_SIZE:
            raise ValueError("each ticket must contain exactly six unique numbers")
        if any(not isinstance(number, int) or not 1 <= number <= MAX_NUMBER for number in numbers):
            raise ValueError("ticket numbers must be integers between 1 and 37")

        choose_table = choose or cls._build_choose_table()
        outside = tuple(number for number in range(1, MAX_NUMBER + 1) if number not in numbers)
        mask_bytes = bytearray((TOTAL_DRAWS + 7) // 8)
        for matched_count in range(ANY_PRIZE_THRESHOLD, DRAW_SIZE + 1):
            needed = DRAW_SIZE - matched_count
            for matched in combinations(numbers, matched_count):
                for remainder in combinations(outside, needed):
                    draw = sorted((*matched, *remainder))
                    rank = cls._draw_rank(draw, choose_table)
                    mask_bytes[rank >> 3] |= 1 << (rank & 7)
        return int.from_bytes(mask_bytes, "little")

    @classmethod
    def covered_draw_count(cls, tickets: Iterable[Sequence[int]]) -> int:
        """Return the exact number of 6/37 outcomes with at least one 3+ hit."""
        choose = cls._build_choose_table()
        covered = 0
        for ticket in tickets:
            covered |= cls._coverage_mask(ticket, choose)
        return covered.bit_count()

    @classmethod
    def coverage_probability(cls, tickets: Iterable[Sequence[int]]) -> float:
        """Return exact P(at least one ticket matches 3+ main numbers)."""
        return cls.covered_draw_count(tickets) / TOTAL_DRAWS

    def _select_candidate_pool(
        self, candidates: Sequence[tuple[int, ...]]
    ) -> tuple[tuple[tuple[int, ...], ...], int, tuple[int, ...]]:
        """Greedily select tickets and return exact covered count plus cached masks."""
        if len(candidates) < self.config.max_tickets:
            raise ValueError("candidate pool must cover max_tickets")
        masks = tuple(self._coverage_mask(ticket, self._choose) for ticket in candidates)
        remaining = list(range(len(candidates)))
        selected: list[tuple[int, ...]] = []
        covered = 0

        while len(selected) < self.config.max_tickets:
            best_index = max(
                remaining,
                key=lambda index: ((masks[index] & ~covered).bit_count(), -index),
            )
            selected.append(candidates[best_index])
            covered |= masks[best_index]
            remaining.remove(best_index)

        return tuple(selected), covered.bit_count(), masks

    def recommend(
        self, dataset: LotteryDataset, seed: int | None = None
    ) -> RecommendationResult:
        """Build 14 tickets; historical frequencies are deliberately not used."""
        if len(dataset) == 0:
            raise ValueError("Dataset is empty")

        rng = random.Random(seed)
        candidates: list[tuple[int, ...]] = []
        seen: set[tuple[int, ...]] = set()
        attempts = 0
        max_attempts = self.config.candidate_count * 100
        while len(candidates) < self.config.candidate_count and attempts < max_attempts:
            attempts += 1
            ticket = tuple(sorted(rng.sample(range(1, MAX_NUMBER + 1), DRAW_SIZE)))
            if ticket not in seen:
                seen.add(ticket)
                candidates.append(ticket)
        if len(candidates) != self.config.candidate_count:
            raise ValueError("Could not build a unique candidate ticket pool")

        selected, _, _ = self._select_candidate_pool(candidates)

        strong_scores = tuple(
            NumberScore(number=number, score=1.0 / 7.0)
            for number in range(1, 8)
        )
        generated_with_strong = tuple(
            RecommendedTicket(numbers=ticket, strong_number=rng.randint(1, 7))
            for ticket in candidates
        )
        recommended_with_strong = tuple(
            RecommendedTicket(numbers=ticket, strong_number=rng.randint(1, 7))
            for ticket in selected
        )
        # Flat number scores are intentional: this objective optimizes portfolio
        # structure, not the prediction of individual lottery numbers.
        scores = tuple(
            NumberScore(number=number, score=0.5)
            for number in range(1, MAX_NUMBER + 1)
        )

        return RecommendationResult(
            scores=scores,
            generated_tickets=tuple(candidates),
            recommended_tickets=tuple(selected),
            strong_scores=strong_scores,
            generated_tickets_with_strong=generated_with_strong,
            recommended_tickets_with_strong=recommended_with_strong,
        )
