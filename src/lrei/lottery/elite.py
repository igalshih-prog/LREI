from __future__ import annotations

import random
from dataclasses import dataclass

from .dataset import LotteryDataset
from .pro import ProConfig, ProRecommendationEngine
from .predictor import NumberScore
from .recommendation import RecommendedTicket, RecommendationResult


@dataclass(frozen=True)
class EliteProConfig(ProConfig):
    """Configuration for the ensemble Pro engine."""

    rank_weight: float = 0.45
    raw_weight: float = 0.30
    ewma_weight: float = 0.25

    def __post_init__(self) -> None:
        # ProConfig has no __post_init__, so validate its runtime constraints here.
        if self.candidate_count < self.max_tickets:
            raise ValueError("candidate_count must cover max_tickets")
        if self.ewma_half_life <= 0:
            raise ValueError("ewma_half_life must be positive")
        if self.affinity_prior_strength < 0:
            raise ValueError("affinity_prior_strength must be non-negative")
        if self.rank_weight < 0 or self.raw_weight < 0 or self.ewma_weight < 0:
            raise ValueError("ensemble weights must be non-negative")
        if self.rank_weight + self.raw_weight + self.ewma_weight <= 0:
            raise ValueError("ensemble weights must have positive total")


class EliteProRecommendationEngine(ProRecommendationEngine):
    """Ensemble Pro engine combining rank, raw-frequency and EWMA signals."""

    def __init__(self, config: EliteProConfig | None = None) -> None:
        self.config = config or EliteProConfig()
        super().__init__(self.config)

    def recommend(self, dataset: LotteryDataset, seed: int | None = None) -> RecommendationResult:
        if len(dataset) == 0:
            raise ValueError("Dataset is empty")

        frequencies = self._frequency(dataset)
        recent_3 = self._window_frequency(dataset, 3)
        recent_1 = self._window_frequency(dataset, 1)
        recent_draws = self._recent_draw_frequency(dataset, 60)
        ewma = self._ewma_frequency(dataset, self.config.ewma_half_life)

        def variant(rank: bool, use_ewma: bool):
            return ProRecommendationEngine(ProConfig(
                candidate_count=self.config.candidate_count,
                max_overlap=self.config.max_overlap,
                max_tickets=self.config.max_tickets,
                use_rank_normalization=rank,
                use_ewma=use_ewma,
                ewma_half_life=self.config.ewma_half_life,
                affinity_prior_strength=self.config.affinity_prior_strength,
            ))

        rank_engine = variant(True, False)
        raw_engine = variant(False, False)
        ewma_engine = variant(True, True)

        rank_scores = rank_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {})
        raw_scores = raw_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {})
        ewma_scores = ewma_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma)

        total_weight = self.config.rank_weight + self.config.raw_weight + self.config.ewma_weight
        rank_map = {s.number: s.score for s in rank_scores}
        raw_map = {s.number: s.score for s in raw_scores}
        ewma_map = {s.number: s.score for s in ewma_scores}
        ensemble_scores = tuple(
            NumberScore(
                number=n,
                score=(
                    self.config.rank_weight * rank_map[n]
                    + self.config.raw_weight * raw_map[n]
                    + self.config.ewma_weight * ewma_map[n]
                ) / total_weight,
            )
            for n in sorted(rank_map)
        )

        pair_counts = self._combination_counts(dataset, 2)
        triple_counts = self._combination_counts(dataset, 3)
        structure = self._structure_profile(dataset)
        rng = random.Random(seed)

        candidates = []
        engines = ((rank_engine, rank_scores), (raw_engine, raw_scores), (ewma_engine, ewma_scores))
        per_variant = max(1, self.config.candidate_count // len(engines))
        for engine, scores in engines:
            for _ in range(per_variant):
                candidates.append(self._generate_candidate(scores, pair_counts, triple_counts, structure, rng))
        while len(candidates) < self.config.candidate_count:
            candidates.append(self._generate_candidate(ensemble_scores, pair_counts, triple_counts, structure, rng))
        candidates = candidates[: self.config.candidate_count]

        recommended = self._select_portfolio(
            candidates,
            ensemble_scores,
            frequencies,
            pair_counts,
            triple_counts,
            structure,
        )
        if len(recommended) < self.config.max_tickets:
            expanded = list(candidates)
            for _ in range(self.config.candidate_count):
                expanded.append(self._generate_candidate(ensemble_scores, pair_counts, triple_counts, structure, rng))
            recommended = self._select_portfolio(
                expanded,
                ensemble_scores,
                frequencies,
                pair_counts,
                triple_counts,
                structure,
            )
        recommended = tuple(recommended[: self.config.max_tickets])
        if len(recommended) != self.config.max_tickets:
            raise ValueError("Elite Pro optimizer could not produce the configured number of tickets")

        strong_scores = self._strong_scores(dataset)
        generated = tuple(candidates)
        generated_with_strong = tuple(
            RecommendedTicket(numbers=t, strong_number=self.generator.generate_strong_number(scores=strong_scores, rng=rng) if strong_scores else None)
            for t in generated
        )
        recommended_with_strong = tuple(
            RecommendedTicket(numbers=t, strong_number=self.generator.generate_strong_number(scores=strong_scores, rng=rng) if strong_scores else None)
            for t in recommended
        )
        return RecommendationResult(
            scores=ensemble_scores,
            generated_tickets=generated,
            recommended_tickets=recommended,
            strong_scores=strong_scores,
            generated_tickets_with_strong=generated_with_strong,
            recommended_tickets_with_strong=recommended_with_strong,
        )
