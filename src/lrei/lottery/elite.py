from __future__ import annotations

import math
import random
from statistics import mean
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
    adaptive_candidate_weights: bool = False
    candidate_calibration_draws: int = 20
    candidate_calibration_candidate_count: int = 100
    candidate_adaptive_shrinkage: float = 0.50
    momentum_strength: float = 0.0
    momentum_window: int = 60
    score_calibration: bool = False
    score_calibration_draws: int = 30
    score_calibration_bins: int = 5
    score_calibration_shrinkage: float = 0.75

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
        if self.candidate_calibration_draws < 0:
            raise ValueError("candidate_calibration_draws must be non-negative")
        if self.candidate_calibration_candidate_count < self.max_tickets:
            raise ValueError("candidate_calibration_candidate_count must cover max_tickets")
        if not 0.0 <= self.candidate_adaptive_shrinkage <= 1.0:
            raise ValueError("candidate_adaptive_shrinkage must be between 0 and 1")
        if not 0.0 <= self.momentum_strength <= 1.0:
            raise ValueError("momentum_strength must be between 0 and 1")
        if self.momentum_window < 10:
            raise ValueError("momentum_window must be at least 10")
        if self.score_calibration_draws < 0:
            raise ValueError("score_calibration_draws must be non-negative")
        if self.score_calibration_bins < 2 or self.score_calibration_bins > 10:
            raise ValueError("score_calibration_bins must be between 2 and 10")
        if not 0.0 <= self.score_calibration_shrinkage <= 1.0:
            raise ValueError("score_calibration_shrinkage must be between 0 and 1")


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

    def _adaptive_candidate_weights(self, dataset: LotteryDataset, engines) -> tuple[float, float, float]:
        """Calibrate candidate-source weights from a trailing walk-forward slice."""
        default = (self.config.candidate_rank_weight, self.config.candidate_raw_weight, self.config.candidate_ewma_weight)
        if not self.config.adaptive_candidate_weights:
            return default
        if len(dataset) < self.config.candidate_calibration_draws + 20 or self.config.candidate_calibration_draws <= 0:
            return default
        validation_size = min(self.config.candidate_calibration_draws, len(dataset) - 20)
        train = LotteryDataset(dataset.draws[:-validation_size])
        validation = dataset.draws[-validation_size:]
        if not train.draws:
            return default
        frequencies = self._frequency(train)
        recent_3 = self._window_frequency(train, 3)
        recent_1 = self._window_frequency(train, 1)
        recent_draws = self._recent_draw_frequency(train, 60)
        ewma = self._ewma_frequency(train, self.config.ewma_half_life)
        pair_counts = self._combination_counts(train, 2)
        triple_counts = self._combination_counts(train, 3)
        structure = self._structure_profile(train)
        source_scores = (
            engines[0][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
            engines[1][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
            engines[2][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma),
        )
        rng = random.Random(13579 + len(dataset))
        performance = []
        for scores in source_scores:
            candidates = [self._generate_candidate(scores, pair_counts, triple_counts, structure, rng) for _ in range(self.config.candidate_calibration_candidate_count)]
            portfolio = self._select_portfolio(candidates, scores, frequencies, pair_counts, triple_counts, structure)
            if not portfolio:
                performance.append(0.05)
                continue
            mean_hits = mean(mean(len(set(ticket) & set(draw.numbers)) for ticket in portfolio) for draw in validation)
            performance.append(max(0.05, mean_hits / (6.0 * 6.0 / 37.0)))
        default_total = sum(default)
        prior = [x / default_total for x in default]
        performance_total = sum(performance)
        learned = [x / performance_total for x in performance]
        shrink = self.config.candidate_adaptive_shrinkage
        blended = [(1.0 - shrink) * p + shrink * l for p, l in zip(prior, learned)]
        total = sum(blended)
        return tuple(x / total for x in blended)

    def _calibrate_ensemble_scores(self, dataset: LotteryDataset, engines, current_scores):
        """Calibrate score bands against trailing walk-forward hit rates, with shrinkage."""
        if not self.config.score_calibration or self.config.score_calibration_draws <= 0:
            return current_scores
        if len(dataset) < self.config.score_calibration_draws + 25:
            return current_scores
        validation_size = min(self.config.score_calibration_draws, len(dataset) - 25)
        train_end = len(dataset) - validation_size
        train_draws = dataset.draws[:train_end]
        validation = dataset.draws[train_end:]
        if not train_draws:
            return current_scores
        history = LotteryDataset(train_draws)
        bins = [[] for _ in range(self.config.score_calibration_bins)]
        hits = [0 for _ in range(self.config.score_calibration_bins)]
        counts = [0 for _ in range(self.config.score_calibration_bins)]
        for offset, target in enumerate(validation):
            prefix = LotteryDataset(train_draws + tuple(validation[:offset]))
            frequencies = self._frequency(prefix)
            recent_3 = self._window_frequency(prefix, 3)
            recent_1 = self._window_frequency(prefix, 1)
            recent_draws = self._recent_draw_frequency(prefix, 60)
            ewma = self._ewma_frequency(prefix, self.config.ewma_half_life)
            variants = (
                engines[0][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
                engines[1][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
                engines[2][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma),
            )
            weights = self._adaptive_weights(prefix, engines)
            maps = [{s.number: s.score for s in scores} for scores in variants]
            for number in range(1, 38):
                score = sum(weights[i] * maps[i].get(number, 0.5) for i in range(3))
                rank = min(self.config.score_calibration_bins - 1, int(score * self.config.score_calibration_bins))
                counts[rank] += 1
                if number in target.numbers:
                    hits[rank] += 1
        baseline = 6.0 / 37.0
        rates = [
            (1.0 - self.config.score_calibration_shrinkage) * (hits[i] / counts[i] if counts[i] else baseline)
            + self.config.score_calibration_shrinkage * baseline
            for i in range(self.config.score_calibration_bins)
        ]
        max_rate = max(rates) if rates else baseline
        if max_rate <= 0:
            return current_scores
        scale = baseline / max_rate
        calibrated = tuple(
            NumberScore(
                number=s.number,
                score=max(0.0, min(1.0, rates[min(self.config.score_calibration_bins - 1, int(s.score * self.config.score_calibration_bins))] * scale))
            )
            for s in current_scores
        )
        return calibrated

    @staticmethod
    def _momentum_scores(dataset: LotteryDataset, window: int) -> dict[int, float]:
        """Compare recent appearance rates with the immediately preceding window."""
        if len(dataset) < window * 2:
            return {}
        recent = dataset.draws[-window:]
        previous = dataset.draws[-window * 2:-window]
        recent_counts = {}
        previous_counts = {}
        for draw in recent:
            for number in draw.numbers:
                recent_counts[number] = recent_counts.get(number, 0) + 1
        for draw in previous:
            for number in draw.numbers:
                previous_counts[number] = previous_counts.get(number, 0) + 1
        numbers = sorted(set(recent_counts) | set(previous_counts))
        raw = {n: recent_counts.get(n, 0) - previous_counts.get(n, 0) for n in numbers}
        low, high = min(raw.values()), max(raw.values())
        if high == low:
            return {n: 0.5 for n in numbers}
        return {n: (raw[n] - low) / (high - low) for n in numbers}

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
        base_ensemble = {
            n: weights[0] * rank_map[n] + weights[1] * raw_map[n] + weights[2] * ewma_map[n]
            for n in sorted(rank_map)
        }
        momentum = self._momentum_scores(dataset, self.config.momentum_window)
        if self.config.momentum_strength > 0.0 and momentum:
            base_ensemble = {
                n: (1.0 - self.config.momentum_strength) * score
                + self.config.momentum_strength * momentum.get(n, 0.5)
                for n, score in base_ensemble.items()
            }
        ensemble_scores = tuple(NumberScore(number=n, score=base_ensemble[n]) for n in sorted(base_ensemble))
        ensemble_scores = self._calibrate_ensemble_scores(dataset, engines, ensemble_scores)

        pair_counts = self._combination_counts(dataset, 2)
        triple_counts = self._combination_counts(dataset, 3)
        structure = self._structure_profile(dataset)
        rng = random.Random(seed)

        candidates = []
        variant_specs = ((rank_engine, rank_scores), (raw_engine, raw_scores), (ewma_engine, ewma_scores))
        candidate_weights = self._adaptive_candidate_weights(dataset, engines)
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
