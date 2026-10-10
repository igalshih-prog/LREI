"""Coverage-oriented portfolio construction for 14 lottery tickets.

This engine does not attempt to predict the next draw. It builds a portfolio
whose pairwise ticket overlap is at most one main number, which makes the
portfolio's >=4-main-number hit events disjoint and maximizes exact coverage
for that prize tier under a uniform 6-of-37 draw model.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .dataset import LotteryDataset
from .elite import EliteProConfig, EliteProRecommendationEngine
from .recommendation import RecommendationResult


@dataclass(frozen=True)
class CoverageConfig:
    """Settings for the exact-coverage 14-ticket mode."""

    candidate_count: int = 1000
    max_tickets: int = 14
    max_overlap: int = 1

    def __post_init__(self) -> None:
        if self.candidate_count < self.max_tickets:
            raise ValueError("candidate_count must cover max_tickets")
        if self.max_tickets != 14:
            raise ValueError("Coverage mode is defined for exactly 14 tickets")
        if self.max_overlap != 1:
            raise ValueError("max_overlap must be 1 to maximize 4+ main-number coverage")


class CoverageRecommendationEngine:
    """Construct 14 tickets with mathematically maximal >=4/6 main coverage."""

    def __init__(self, config: CoverageConfig | None = None) -> None:
        self.config = config or CoverageConfig()
        self._engine = EliteProRecommendationEngine(
            EliteProConfig(
                candidate_count=self.config.candidate_count,
                max_tickets=self.config.max_tickets,
                max_overlap=self.config.max_overlap,
                adaptive_weights=False,
                adaptive_candidate_weights=False,
            )
        )

    def recommend(
        self, dataset: LotteryDataset, seed: int | None = None
    ) -> RecommendationResult:
        result = self._engine.recommend(dataset, seed=seed)
        portfolio = result.recommended_tickets
        if len(portfolio) != 14 or len(set(portfolio)) != 14:
            raise ValueError("Coverage mode must produce exactly 14 unique tickets")
        if any(
            len(set(left) & set(right)) > 1
            for left, right in combinations(portfolio, 2)
        ):
            raise ValueError("Coverage mode could not satisfy max_overlap=1")
        return result
