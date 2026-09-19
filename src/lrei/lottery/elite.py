from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .dataset import LotteryDataset
from .pro import ProConfig, ProRecommendationEngine
from .predictor import NumberScore
from .recommendation import RecommendedTicket, RecommendationResult


@dataclass(frozen=True)
class EliteProConfig(ProConfig):
    """Configuration for the adaptive ensemble Pro engine."""

    rank_weight: float = 0.45
    raw_weight: float = 0.30
    ewma_weight: float = 0.25
    adaptive_weights: bool = True
    calibration_draws: int = 30
    calibration_top_k: int = 10
    adaptive_shrinkage: float = 0.50
    candidate_rank_weight: float = 1.0 / 3.0
    candidate_raw_weight: float = 1.0 / 3.0
    candidate_ewma_weight: float = 1.0 / 3.0

    def __post_init__(self) -> None:
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
        if self.calibration_draws < 0:
            raise ValueError("calibration_draws must be non-negative")
        if self.calibration_top_k < 1 or self.calibration_top_k > 37:
            raise ValueError("calibration_top_k must be between 1 and 37")
        if not 0.0 <= self.adaptive_shrinkage <= 1.0:
            raise ValueError("adaptive_shrinkage must be between 0 and 1")
        candidate_weights = (self.candidate_rank_weight, self.candidate_raw_weight, self.candidate_ewma_weight)
        if any(weight < 0 for weight in candidate_weights):
            raise ValueError("candidate ensemble weights must be non-negative")
        if sum(candidate_weights) <= 0:
            raise ValueError("candidate ensemble weights must have positive total")


class EliteProRecommendationEngine(ProRecommendationEngine):
    """Adaptive ensemble combining several historical prediction signals."""

    def __init__(self, config: EliteProConfig | None = None) -> None:
        self.config = config or EliteProConfig()
        super().__init__(self.config)

    @staticmethod
    def _engine(config: EliteProConfig, rank: bool, use_ewma: bool) -> ProRecommendationEngine:
        return ProRecommendationEngine(ProConfig(
            candidate_count=config.candidate_count,
            max_overlap=config.max_overlap,
            max_tickets=config.max_tickets,
            use_rank_normalization=rank,
            use_ewma=use_ewma,
            ewma_half_life=config.ewma_half_life,
            affinity_prior_strength=config.affinity_prior_strength,
            number_signal_strength=config.number_signal_strength,
            pair_bonus_strength=config.pair_bonus_strength,
            triple_bonus_strength=config.triple_bonus_strength,
            structural_gate_probability=config.structural_gate_probability,
            structural_gate_threshold=config.structural_gate_threshold,
        ))

    @staticmethod
    def _top_k_hits(scores, draw, k):
        predicted = {s.number for s in sorted(scores, key=lambda s: (-s.score, s.number))[:k]}
        return len(predicted.intersection(draw.numbers))

    def _adaptive_weights(self, dataset: LotteryDataset, engines) -> tuple[float, float, float]:
        """Calibrate weights from a trailing walk-forward validation slice."""
        default = (self.config.rank_weight, self.config.raw_weight, self.config.ewma_weight)
        if not self.config.adaptive_weights or len(dataset) < self.config.calibration_draws + 20:
            return default

        validation_size = min(self.config.calibration_draws, len(dataset) - 20)
        if validation_size <= 0:
            return default
        train = LotteryDataset(dataset.draws[:-validation_size])
        validation = dataset.draws[-validation_size:]
        if not train.draws:
            return default

        frequencies = self._frequency(train)
        recent_3 = self._window_frequency(train, 3)
        recent_1 = self._window_frequency(train, 1)
        recent_draws = self._recent_draw_frequency(train, 60)
        ewma = self._ewma_frequency(train, self.config.ewma_half_life)

        scores_by_variant = (
            engines[0][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
            engines[1][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
            engines[2][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma),
        )
        baseline = self.config.calibration_top_k * 6.0 / 37.0
        performance = []
        for scores in scores_by_variant:
            hits = sum(self._top_k_hits(scores, draw, self.config.calibration_top_k) for draw in validation)
            mean_hits = hits / len(validation)
            performance.append(max(0.05, mean_hits / max(baseline, 1e-9)))

        default_total = sum(default)
        prior = [x / default_total for x in default]
        performance_total = sum(performance)
        learned = [x / performance_total for x in performance]
        shrink = self.config.adaptive_shrinkage
        blended = [(1.0 - shrink) * p + shrink * l for p, l in zip(prior, learned)]
        total = sum(blended)
        return tuple(x / total for x in blended)

    def recommend(self, dataset: LotteryDataset, seed: int | None = None) -> RecommendationResult:
        if len(dataset) == 0:
            raise ValueError("Dataset is empty")

        frequencies = self._frequency(dataset)
        recent_3 = self._window_frequency(dataset, 3)
        recent_1 = self._window_frequency(dataset, 1)
        recent_draws = self._recent_draw_frequency(dataset, 60)
        ewma = self._ewma_frequency(dataset, self.config.ewma_half_life)

        rank_engine = self._engine(self.config, True, False)
        raw_engine = self._engine(self.config, False, False)
        ewma_engine = self._engine(self.config, True, True)
        engines = ((rank_engine, None), (raw_engine, None), (ewma_engine, None))
        weights = self._adaptive_weights(dataset, engines)

        rank_scores = rank_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {})
        raw_scores = raw_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {})
        ewma_scores = ewma_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma)

        rank_map = {s.number: s.score for s in rank_scores}
        raw_map = {s.number: s.score for s in raw_scores}
        ewma_map = {s.number: s.score for s in ewma_scores}
        ensemble_scores = tuple(
            NumberScore(
                number=n,
                score=weights[0] * rank_map[n] + weights[1] * raw_map[n] + weights[2] * ewma_map[n],
            )
            for n in sorted(rank_map)
        )

        pair_counts = self._combination_counts(dataset, 2)
        triple_counts = self._combination_counts(dataset, 3)
        structure = self._structure_profile(dataset)
        rng = random.Random(seed)

        candidates = []
        variant_specs = ((rank_engine, rank_scores), (raw_engine, raw_scores), (ewma_engine, ewma_scores))
        candidate_weights = (self.config.candidate_rank_weight, self.config.candidate_raw_weight, self.config.candidate_ewma_weight)
        total_candidate_weight = sum(candidate_weights)
        allocations = [int(self.config.candidate_count * weight / total_candidate_weight) for weight in candidate_weights]
        for index in range(self.config.candidate_count - sum(allocations)):
            allocations[index % len(allocations)] += 1
        for (engine, scores), count in zip(variant_specs, allocations):
            for _ in range(count):
                candidates.append(self._generate_candidate(scores, pair_counts, triple_counts, structure, rng))
        while len(candidates) < self.config.candidate_count:
            candidates.append(self._generate_candidate(ensemble_scores, pair_counts, triple_counts, structure, rng))
        candidates = candidates[:self.config.candidate_count]

        recommended = self._select_portfolio(candidates, ensemble_scores, frequencies, pair_counts, triple_counts, structure)
        if len(recommended) < self.config.max_tickets:
            expanded = list(candidates)
            for _ in range(self.config.candidate_count):
                expanded.append(self._generate_candidate(ensemble_scores, pair_counts, triple_counts, structure, rng))
            recommended = self._select_portfolio(expanded, ensemble_scores, frequencies, pair_counts, triple_counts, structure)
        recommended = tuple(recommended[:self.config.max_tickets])
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
