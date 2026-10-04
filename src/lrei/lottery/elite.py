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
    calibration_origins: int = 1
    adaptive_shrinkage: float = 0.50
    candidate_rank_weight: float = 1.0 / 3.0
    candidate_raw_weight: float = 1.0 / 3.0
    candidate_ewma_weight: float = 1.0 / 3.0
    candidate_ensemble_weight: float = 0.0
    adaptive_candidate_weights: bool = True
    candidate_calibration_draws: int = 20
    candidate_calibration_candidate_count: int = 100
    candidate_calibration_origins: int = 1
    candidate_adaptive_shrinkage: float = 0.50
    momentum_strength: float = 0.0
    momentum_window: int = 60
    adaptive_momentum: bool = False
    momentum_candidates: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)
    momentum_calibration_draws: int = 20
    score_calibration: bool = False
    score_calibration_draws: int = 30
    score_calibration_bins: int = 5
    score_calibration_shrinkage: float = 0.75
    consensus_strength: float = 0.0
    adaptive_consensus: bool = False
    consensus_candidates: tuple[float, ...] = (0.0, 0.25, 0.50, 0.75)
    consensus_calibration_draws: int = 20
    consensus_calibration_origins: int = 3
    gap_strength: float = 0.0
    gap_mode: str = "recency"
    adaptive_gap: bool = False
    gap_candidates: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)
    gap_calibration_draws: int = 20
    gap_calibration_origins: int = 3
    adaptive_feature_stack: bool = False
    feature_stack_calibration_draws: int = 20
    feature_stack_calibration_origins: int = 3
    feature_stack_min_improvement: float = 0.01
    feature_stack_min_origin_win_rate: float = 0.60
    learned_signal_model: bool = False
    learned_model_draws: int = 120
    learned_model_shrinkage: float = 0.50

    def __post_init__(self) -> None:
        if self.candidate_count < self.max_tickets:
            raise ValueError("candidate_count must cover max_tickets")
        if self.ewma_half_life <= 0:
            raise ValueError("ewma_half_life must be positive")
        if self.affinity_prior_strength < 0:
            raise ValueError("affinity_prior_strength must be non-negative")
        if not 0.0 <= self.affinity_recent_weight <= 1.0:
            raise ValueError("affinity_recent_weight must be between 0 and 1")
        if self.rank_weight < 0 or self.raw_weight < 0 or self.ewma_weight < 0:
            raise ValueError("ensemble weights must be non-negative")
        if self.rank_weight + self.raw_weight + self.ewma_weight <= 0:
            raise ValueError("ensemble weights must have positive total")
        if self.calibration_draws < 0:
            raise ValueError("calibration_draws must be non-negative")
        if self.calibration_top_k < 1 or self.calibration_top_k > 37:
            raise ValueError("calibration_top_k must be between 1 and 37")
        if self.calibration_origins < 1:
            raise ValueError("calibration_origins must be at least 1")
        if not 0.0 <= self.adaptive_shrinkage <= 1.0:
            raise ValueError("adaptive_shrinkage must be between 0 and 1")
        candidate_weights = (self.candidate_rank_weight, self.candidate_raw_weight, self.candidate_ewma_weight)
        if any(weight < 0 for weight in candidate_weights):
            raise ValueError("candidate ensemble weights must be non-negative")
        if sum(candidate_weights) <= 0:
            raise ValueError("candidate ensemble weights must have positive total")
        if not 0.0 <= self.candidate_ensemble_weight <= 1.0:
            raise ValueError("candidate_ensemble_weight must be between 0 and 1")
        if self.candidate_calibration_draws < 0:
            raise ValueError("candidate_calibration_draws must be non-negative")
        if self.candidate_calibration_candidate_count < self.max_tickets:
            raise ValueError("candidate_calibration_candidate_count must cover max_tickets")
        if self.candidate_calibration_origins < 1:
            raise ValueError("candidate_calibration_origins must be at least 1")
        if not 0.0 <= self.candidate_adaptive_shrinkage <= 1.0:
            raise ValueError("candidate_adaptive_shrinkage must be between 0 and 1")
        if not 0.0 <= self.momentum_strength <= 1.0:
            raise ValueError("momentum_strength must be between 0 and 1")
        if self.momentum_window < 10:
            raise ValueError("momentum_window must be at least 10")
        if self.momentum_calibration_draws < 0:
            raise ValueError("momentum_calibration_draws must be non-negative")
        if not self.momentum_candidates or any(not 0.0 <= value <= 1.0 for value in self.momentum_candidates):
            raise ValueError("momentum_candidates must contain values between 0 and 1")
        if self.score_calibration_draws < 0:
            raise ValueError("score_calibration_draws must be non-negative")
        if self.score_calibration_bins < 2 or self.score_calibration_bins > 10:
            raise ValueError("score_calibration_bins must be between 2 and 10")
        if not 0.0 <= self.score_calibration_shrinkage <= 1.0:
            raise ValueError("score_calibration_shrinkage must be between 0 and 1")
        if not 0.0 <= self.consensus_strength <= 1.0:
            raise ValueError("consensus_strength must be between 0 and 1")
        if not self.consensus_candidates or any(not 0.0 <= value <= 1.0 for value in self.consensus_candidates):
            raise ValueError("consensus_candidates must contain values between 0 and 1")
        if self.consensus_calibration_draws < 0 or self.consensus_calibration_origins < 1:
            raise ValueError("consensus calibration settings are invalid")
        if not 0.0 <= self.gap_strength <= 1.0:
            raise ValueError("gap_strength must be between 0 and 1")
        if self.portfolio_pair_coverage_weight < 0:
            raise ValueError("portfolio_pair_coverage_weight must be non-negative")
        if self.portfolio_triple_coverage_weight < 0:
            raise ValueError("portfolio_triple_coverage_weight must be non-negative")
        if self.gap_mode not in ("recency", "overdue"):
            raise ValueError("gap_mode must be 'recency' or 'overdue'")
        if not self.gap_candidates or any(not 0.0 <= value <= 1.0 for value in self.gap_candidates):
            raise ValueError("gap_candidates must contain values between 0 and 1")
        if self.gap_calibration_draws < 0 or self.gap_calibration_origins < 1:
            raise ValueError("gap calibration settings are invalid")
        if self.feature_stack_calibration_draws < 0 or self.feature_stack_calibration_origins < 1:
            raise ValueError("feature stack calibration settings are invalid")
        if self.feature_stack_min_improvement < 0:
            raise ValueError("feature_stack_min_improvement must be non-negative")
        if not 0.0 <= self.feature_stack_min_origin_win_rate <= 1.0:
            raise ValueError("feature_stack_min_origin_win_rate must be between 0 and 1")
        if self.learned_model_draws < 30:
            raise ValueError("learned_model_draws must be at least 30")
        if not 0.0 <= self.learned_model_shrinkage <= 1.0:
            raise ValueError("learned_model_shrinkage must be between 0 and 1")


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
            affinity_recent_weight=config.affinity_recent_weight,
            number_signal_strength=config.number_signal_strength,
            portfolio_coverage_weight=config.portfolio_coverage_weight,
            portfolio_overlap_penalty=config.portfolio_overlap_penalty,
            portfolio_pair_coverage_weight=config.portfolio_pair_coverage_weight,
            portfolio_triple_coverage_weight=config.portfolio_triple_coverage_weight,
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
        """Calibrate signal weights from multiple trailing walk-forward origins."""
        default = (self.config.rank_weight, self.config.raw_weight, self.config.ewma_weight)
        if not self.config.adaptive_weights or self.config.calibration_draws <= 0:
            return default
        validation_size = self.config.calibration_draws
        minimum_train = 20
        if len(dataset) < validation_size + minimum_train:
            return default

        source_performance = [[], [], []]
        max_origins = min(
            self.config.calibration_origins,
            max(1, (len(dataset) - minimum_train) // validation_size),
        )
        for origin_index in range(max_origins):
            origin = len(dataset) - origin_index * validation_size
            if origin - validation_size < minimum_train:
                break
            train = LotteryDataset(dataset.draws[:origin - validation_size])
            validation = dataset.draws[origin - validation_size:origin]
            if not train.draws or not validation:
                continue

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
            for source_index, scores in enumerate(scores_by_variant):
                hits = sum(
                    self._top_k_hits(scores, draw, self.config.calibration_top_k)
                    for draw in validation
                )
                mean_hits = hits / len(validation)
                source_performance[source_index].append(
                    max(0.05, mean_hits / max(baseline, 1e-9))
                )

        if not all(source_performance):
            return default
        performance = [mean(values) for values in source_performance]
        default_total = sum(default)
        prior = [x / default_total for x in default]
        performance_total = sum(performance)
        if performance_total <= 0:
            return default
        learned = [x / performance_total for x in performance]
        shrink = self.config.adaptive_shrinkage
        blended = [(1.0 - shrink) * p + shrink * l for p, l in zip(prior, learned)]
        total = sum(blended)
        return tuple(x / total for x in blended)

    def _adaptive_candidate_weights(self, dataset: LotteryDataset, engines) -> tuple[float, float, float]:
        """Calibrate candidate-source weights while keeping Elite scoring fixed."""
        default = (
            self.config.candidate_rank_weight,
            self.config.candidate_raw_weight,
            self.config.candidate_ewma_weight,
        )
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
        number_weights = self._adaptive_weights(train, engines)
        rank_map = {s.number: s.score for s in source_scores[0]}
        raw_map = {s.number: s.score for s in source_scores[1]}
        ewma_map = {s.number: s.score for s in source_scores[2]}
        ensemble_scores = tuple(
            NumberScore(
                number=n,
                score=number_weights[0] * rank_map[n]
                + number_weights[1] * raw_map[n]
                + number_weights[2] * ewma_map[n],
            )
            for n in sorted(rank_map)
        )

        rng = random.Random(13579 + len(dataset))
        performance = []
        for scores in source_scores:
            candidates = [
                self._generate_candidate(
                    scores, pair_counts, triple_counts, structure, rng
                )
                for _ in range(self.config.candidate_calibration_candidate_count)
            ]
            portfolio = self._select_portfolio(
                candidates,
                ensemble_scores,
                frequencies,
                pair_counts,
                triple_counts,
                structure,
            )
            if not portfolio:
                performance.append(0.05)
                continue
            mean_hits = mean(
                mean(len(set(ticket) & set(draw.numbers)) for ticket in portfolio)
                for draw in validation
            )
            performance.append(max(0.05, mean_hits / (6.0 * 6.0 / 37.0)))

        default_total = sum(default)
        prior = [x / default_total for x in default]
        performance_total = sum(performance)
        learned = [x / performance_total for x in performance]
        shrink = self.config.candidate_adaptive_shrinkage
        blended = [(1.0 - shrink) * p + shrink * l for p, l in zip(prior, learned)]
        total = sum(blended)
        return tuple(x / total for x in blended)

    def _adaptive_momentum_strength(self, dataset: LotteryDataset) -> float:
        """Select momentum strength from a trailing walk-forward validation slice."""
        if not self.config.adaptive_momentum or self.config.momentum_calibration_draws <= 0:
            return self.config.momentum_strength
        if len(dataset) < self.config.momentum_calibration_draws + 25:
            return self.config.momentum_strength
        validation_size = min(self.config.momentum_calibration_draws, len(dataset) - 25)
        train_draws = dataset.draws[:-validation_size]
        validation = dataset.draws[-validation_size:]
        if not train_draws:
            return self.config.momentum_strength
        history = LotteryDataset(train_draws)
        frequencies = self._frequency(history)
        recent_3 = self._window_frequency(history, 3)
        recent_1 = self._window_frequency(history, 1)
        recent_draws = self._recent_draw_frequency(history, 60)
        ewma = self._ewma_frequency(history, self.config.ewma_half_life)
        rank_engine = self._engine(self.config, True, False)
        raw_engine = self._engine(self.config, False, False)
        ewma_engine = self._engine(self.config, True, True)
        engines = ((rank_engine, None), (raw_engine, None), (ewma_engine, None))
        variants = (
            rank_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
            raw_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
            ewma_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma),
        )
        weights = self._adaptive_weights(history, engines)
        maps = [{s.number: s.score for s in scores} for scores in variants]
        base = {n: sum(weights[i] * maps[i].get(n, 0.5) for i in range(3)) for n in maps[0]}
        pair_counts = self._combination_counts(history, 2)
        triple_counts = self._combination_counts(history, 3)
        structure = self._structure_profile(history)
        momentum = self._momentum_scores(history, self.config.momentum_window)
        rng = random.Random(24680 + len(dataset))
        results = {}
        for strength in self.config.momentum_candidates:
            adjusted = tuple(NumberScore(number=n, score=(1.0 - strength) * score + strength * momentum.get(n, 0.5)) for n, score in base.items())
            candidates = [self._generate_candidate(adjusted, pair_counts, triple_counts, structure, rng) for _ in range(min(100, self.config.candidate_count))]
            portfolio = self._select_portfolio(candidates, adjusted, frequencies, pair_counts, triple_counts, structure)
            results[strength] = mean(mean(len(set(ticket) & set(draw.numbers)) for ticket in portfolio) for draw in validation) if portfolio else 0.0
        return max(results, key=results.get)

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

    @staticmethod
    def _gap_scores(dataset: LotteryDataset, mode: str = "recency") -> dict[int, float]:
        numbers = sorted({n for draw in dataset for n in draw.numbers})
        if not numbers:
            return {}
        last_seen = {n: -1 for n in numbers}
        for index, draw in enumerate(dataset.draws):
            for n in draw.numbers:
                last_seen[n] = index
        latest = len(dataset.draws) - 1
        gaps = {n: latest - last_seen[n] for n in numbers}
        low, high = min(gaps.values()), max(gaps.values())
        if high == low:
            return {n: 0.5 for n in numbers}
        normalized = {n: (gaps[n] - low) / (high - low) for n in numbers}
        return {n: (1.0 - normalized[n]) if mode == "recency" else normalized[n] for n in numbers}

    def _adaptive_gap_strength(self, dataset: LotteryDataset) -> float:
        if not self.config.adaptive_gap or self.config.gap_calibration_draws <= 0:
            return self.config.gap_strength
        block = self.config.gap_calibration_draws
        minimum_train = 30
        if len(dataset) < block + minimum_train:
            return self.config.gap_strength
        origins = min(self.config.gap_calibration_origins, max(1, (len(dataset) - minimum_train) // block))
        results = {strength: [] for strength in self.config.gap_candidates}
        for origin_index in range(origins):
            end = len(dataset) - origin_index * block
            if end - block < minimum_train:
                break
            train = LotteryDataset(dataset.draws[:end - block])
            validation = dataset.draws[end - block:end]
            frequencies = self._frequency(train)
            recent_3 = self._window_frequency(train, 3)
            recent_1 = self._window_frequency(train, 1)
            recent_draws = self._recent_draw_frequency(train, 60)
            ewma = self._ewma_frequency(train, self.config.ewma_half_life)
            rank_engine = self._engine(self.config, True, False)
            raw_engine = self._engine(self.config, False, False)
            ewma_engine = self._engine(self.config, True, True)
            engines = ((rank_engine, None), (raw_engine, None), (ewma_engine, None))
            weights = self._adaptive_weights(train, engines)
            maps = [
                {s.number: s.score for s in rank_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {})},
                {s.number: s.score for s in raw_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {})},
                {s.number: s.score for s in ewma_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma)},
            ]
            base = {n: sum(weights[i] * maps[i].get(n, 0.5) for i in range(3)) for n in maps[0]}
            gap = self._gap_scores(train, self.config.gap_mode)
            for strength in self.config.gap_candidates:
                adjusted = {n: (1.0 - strength) * score + strength * gap.get(n, 0.5) for n, score in base.items()}
                ordered = sorted(adjusted, key=lambda n: (-adjusted[n], n))[:self.config.calibration_top_k]
                results[strength].extend(len(set(ordered) & set(draw.numbers)) for draw in validation)
        valid = {k: mean(v) for k, v in results.items() if v}
        return max(valid, key=valid.get) if valid else self.config.gap_strength

    def _adaptive_consensus_strength(self, dataset: LotteryDataset, engines, default_weights) -> float:
        """Select consensus strength from multiple trailing walk-forward origins."""
        if not self.config.adaptive_consensus or self.config.consensus_calibration_draws <= 0:
            return self.config.consensus_strength
        block = self.config.consensus_calibration_draws
        minimum_train = 40
        if len(dataset) < block + minimum_train:
            return self.config.consensus_strength
        origins = min(self.config.consensus_calibration_origins, max(1, (len(dataset) - minimum_train) // block))
        results = {strength: [] for strength in self.config.consensus_candidates}
        for origin_index in range(origins):
            end = len(dataset) - origin_index * block
            if end - block < minimum_train:
                break
            train = LotteryDataset(dataset.draws[:end - block])
            validation = dataset.draws[end - block:end]
            frequencies = self._frequency(train)
            recent_3 = self._window_frequency(train, 3)
            recent_1 = self._window_frequency(train, 1)
            recent_draws = self._recent_draw_frequency(train, 60)
            ewma = self._ewma_frequency(train, self.config.ewma_half_life)
            rank_engine = self._engine(self.config, True, False)
            raw_engine = self._engine(self.config, False, False)
            ewma_engine = self._engine(self.config, True, True)
            variants = (
                rank_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
                raw_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
                ewma_engine._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma),
            )
            maps = [{item.number: item.score for item in variant} for variant in variants]
            base = {n: sum(default_weights[i] * maps[i].get(n, 0.5) for i in range(3)) for n in maps[0]}
            for strength in self.config.consensus_candidates:
                adjusted = {}
                for n, score in base.items():
                    values = [maps[i].get(n, 0.5) for i in range(3)]
                    disagreement = max(values) - min(values)
                    consensus = max(0.0, min(1.0, score - 0.35 * disagreement))
                    adjusted[n] = (1.0 - strength) * score + strength * consensus
                ordered = sorted(adjusted, key=lambda n: (-adjusted[n], n))[:self.config.calibration_top_k]
                results[strength].extend(len(set(ordered) & set(draw.numbers)) for draw in validation)
        valid = {strength: mean(values) for strength, values in results.items() if values}
        return max(valid, key=valid.get) if valid else self.config.consensus_strength
    def _adaptive_feature_stack(self, dataset: LotteryDataset) -> str:
        """Select a feature combination from trailing multi-origin validation."""
        if not self.config.adaptive_feature_stack or self.config.feature_stack_calibration_draws <= 0:
            return "baseline"
        block = self.config.feature_stack_calibration_draws
        minimum_train = 50
        if len(dataset) < block + minimum_train:
            return "baseline"
        origins = min(
            self.config.feature_stack_calibration_origins,
            max(1, (len(dataset) - minimum_train) // block),
        )
        variants = ("baseline", "momentum", "gap", "consensus", "all_adaptive")
        results = {name: [] for name in variants}
        for origin_index in range(origins):
            end = len(dataset) - origin_index * block
            if end - block < minimum_train:
                break
            train = LotteryDataset(dataset.draws[:end - block])
            validation = dataset.draws[end - block:end]
            if not train.draws:
                continue
            # Keep this meta-diagnostic focused on feature-stack selection.
            # Nested candidates must not trigger their own adaptive calibrations,
            # otherwise calibration becomes recursive and can explode runtime.
            common = {"adaptive_weights": False, "adaptive_candidate_weights": False}
            configs = {
                "baseline": dict(common),
                "momentum": dict(common, adaptive_momentum=True, momentum_calibration_draws=block),
                "gap": dict(common, adaptive_gap=True, gap_calibration_draws=block, gap_calibration_origins=min(3, origins)),
                "consensus": dict(common, adaptive_consensus=True, consensus_calibration_draws=block, consensus_calibration_origins=min(3, origins)),
                "all_adaptive": dict(
                    common,
                    adaptive_momentum=True, momentum_calibration_draws=block,
                    adaptive_gap=True, gap_calibration_draws=block, gap_calibration_origins=min(3, origins),
                    adaptive_consensus=True, consensus_calibration_draws=block, consensus_calibration_origins=min(3, origins),
                ),
            }
            for name, kwargs in configs.items():
                cfg = EliteProConfig(
                    candidate_count=min(120, self.config.candidate_count),
                    max_tickets=self.config.max_tickets,
                    **kwargs,
                )
                result = EliteProRecommendationEngine(cfg).recommend(train, seed=120000 + end + origin_index)
                results[name].append(
                    mean(
                        mean(len(set(ticket) & set(draw.numbers)) for ticket in result.recommended_tickets)
                        for draw in validation
                    )
                )
        valid = {name: mean(values) for name, values in results.items() if values}
        if not valid or "baseline" not in valid:
            return "baseline"
        baseline_mean = valid["baseline"]
        eligible = []
        for name, score in valid.items():
            if name == "baseline" or score < baseline_mean + self.config.feature_stack_min_improvement:
                continue
            origin_wins = 0
            comparable_origins = 0
            for origin_index in range(origins):
                left = origin_index * block
                right = left + block
                base_values = results["baseline"][left:right]
                candidate_values = results[name][left:right]
                if not base_values or not candidate_values:
                    continue
                comparable_origins += 1
                if mean(candidate_values) > mean(base_values):
                    origin_wins += 1
            win_rate = origin_wins / comparable_origins if comparable_origins else 0.0
            if win_rate >= self.config.feature_stack_min_origin_win_rate:
                eligible.append((score, name))
        return max(eligible)[1] if eligible else "baseline"

    @staticmethod
    def _learned_feature_scores(dataset: LotteryDataset, window: int = 120) -> dict[int, float]:
        """Learn a simple out-of-sample feature signal from historical next-draw outcomes."""
        if len(dataset) < 31:
            return {}
        numbers = sorted({n for draw in dataset for n in draw.numbers})
        rows = []
        start = max(20, len(dataset) - window)
        for index in range(start, len(dataset)):
            history = LotteryDataset(dataset.draws[:index])
            target = set(dataset.draws[index].numbers)
            frequencies = ProRecommendationEngine._frequency(history)
            recent = ProRecommendationEngine._recent_draw_frequency(history, 20)
            previous = ProRecommendationEngine._recent_draw_frequency(LotteryDataset(history.draws[:-20]) if len(history) > 20 else history, 20)
            ewma = ProRecommendationEngine._ewma_frequency(history, 36.0)
            for number in numbers:
                f = frequencies.get(number, 0) / max(1, len(history))
                r = recent.get(number, 0) / max(1, min(20, len(history)))
                p = previous.get(number, 0) / max(1, min(20, len(history)))
                m = r - p
                e = ewma.get(number, 0.0)
                rows.append(((f, r, m, e), 1.0 if number in target else 0.0))
        if not rows:
            return {}
        means = [mean(row[0][i] for row in rows) for i in range(4)]
        scales = [math.sqrt(mean((row[0][i] - means[i]) ** 2 for row in rows)) or 1.0 for i in range(4)]
        weights = []
        for i in range(4):
            x = [(row[0][i] - means[i]) / scales[i] for row in rows]
            y = [row[1] for row in rows]
            x_mean = mean(x)
            y_mean = mean(y)
            covariance = mean((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
            weights.append(covariance)
        norm = sum(abs(weight) for weight in weights) or 1.0
        weights = [weight / norm for weight in weights]
        history = dataset
        frequencies = ProRecommendationEngine._frequency(history)
        recent = ProRecommendationEngine._recent_draw_frequency(history, 20)
        previous_history = LotteryDataset(history.draws[:-20]) if len(history) > 20 else history
        previous = ProRecommendationEngine._recent_draw_frequency(previous_history, 20)
        ewma = ProRecommendationEngine._ewma_frequency(history, 36.0)
        raw = {}
        for number in numbers:
            features = (
                frequencies.get(number, 0) / max(1, len(history)),
                recent.get(number, 0) / max(1, min(20, len(history))),
                recent.get(number, 0) / max(1, min(20, len(history))) - previous.get(number, 0) / max(1, min(20, len(history))),
                ewma.get(number, 0.0),
            )
            raw[number] = sum(weight * ((features[i] - means[i]) / scales[i]) for i, weight in enumerate(weights))
        low, high = min(raw.values()), max(raw.values())
        if high <= low:
            return {number: 0.5 for number in numbers}
        return {number: (raw[number] - low) / (high - low) for number in numbers}

    def _calibrate_ensemble_scores(self, dataset: LotteryDataset, engines, scores):
        """Optionally calibrate ensemble scores from trailing historical outcomes."""
        if not self.config.score_calibration or self.config.score_calibration_draws <= 0:
            return scores
        if len(dataset) < self.config.score_calibration_draws + 25:
            return scores

        validation_size = min(self.config.score_calibration_draws, len(dataset) - 25)
        train = LotteryDataset(dataset.draws[:-validation_size])
        validation = dataset.draws[-validation_size:]
        if not train.draws:
            return scores

        frequencies = self._frequency(train)
        recent_3 = self._window_frequency(train, 3)
        recent_1 = self._window_frequency(train, 1)
        recent_draws = self._recent_draw_frequency(train, 60)
        ewma = self._ewma_frequency(train, self.config.ewma_half_life)
        variants = (
            engines[0][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
            engines[1][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
            engines[2][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma),
        )
        weights = self._adaptive_weights(train, engines)
        maps = [{item.number: item.score for item in variant} for variant in variants]
        current_map = {item.number: item.score for item in scores}
        training_scores = {
            number: sum(weights[index] * maps[index].get(number, 0.5) for index in range(3))
            for number in current_map
        }
        bins = self.config.score_calibration_bins
        ordered = sorted(training_scores, key=lambda number: (training_scores[number], number))
        bin_rates = []
        for index in range(bins):
            left = (len(ordered) * index) // bins
            right = (len(ordered) * (index + 1)) // bins
            members = ordered[left:right] or ordered[-1:]
            hits = 0
            opportunities = 0
            for draw in validation:
                actual = set(draw.numbers)
                hits += sum(number in actual for number in members)
                opportunities += len(members)
            rate = hits / opportunities if opportunities else 6.0 / 37.0
            bin_rates.append(rate)

        baseline = 6.0 / 37.0
        max_rate = max(bin_rates) if bin_rates else baseline
        calibrated = {}
        shrink = self.config.score_calibration_shrinkage
        for number, score in current_map.items():
            rank = ordered.index(number) if number in ordered else 0
            bin_index = min(bins - 1, (rank * bins) // max(1, len(ordered)))
            rate = bin_rates[bin_index]
            normalized = 0.5 + 0.5 * ((rate - baseline) / max(abs(max_rate - baseline), 1e-9))
            normalized = max(0.0, min(1.0, normalized))
            calibrated[number] = (1.0 - shrink) * score + shrink * normalized
        return tuple(NumberScore(number=number, score=calibrated[number]) for number in sorted(calibrated))

    def _candidate_allocations(self, dataset: LotteryDataset, engines) -> tuple[float, float, float, float]:
        """Return normalized Rank/Raw/EWMA/ensemble candidate-source weights."""
        source = self._adaptive_candidate_weights(dataset, engines)
        ensemble_weight = self.config.candidate_ensemble_weight
        source_total = sum(source)
        if source_total <= 0:
            return (0.0, 0.0, 0.0, 1.0)
        scale = 1.0 - ensemble_weight
        return tuple(scale * weight / source_total for weight in source) + (ensemble_weight,)

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
        selected_stack = self._adaptive_feature_stack(dataset)
        if selected_stack != "baseline":
            stack_config = {
                "momentum": {"adaptive_momentum": True},
                "gap": {"adaptive_gap": True},
                "consensus": {"adaptive_consensus": True},
                "all_adaptive": {"adaptive_momentum": True, "adaptive_gap": True, "adaptive_consensus": True},
            }[selected_stack]
            selected_momentum = self._adaptive_momentum_strength(dataset) if stack_config.get("adaptive_momentum") else self.config.momentum_strength
            selected_gap = self._adaptive_gap_strength(dataset) if stack_config.get("adaptive_gap") else self.config.gap_strength
            selected_consensus = self._adaptive_consensus_strength(dataset, engines, weights) if stack_config.get("adaptive_consensus") else self.config.consensus_strength
        else:
            selected_momentum = self.config.momentum_strength
            selected_gap = self.config.gap_strength
            selected_consensus = self.config.consensus_strength
        momentum = self._momentum_scores(dataset, self.config.momentum_window)
        if selected_momentum > 0.0 and momentum:
            base_ensemble = {
                n: (1.0 - selected_momentum) * score
                + selected_momentum * momentum.get(n, 0.5)
                for n, score in base_ensemble.items()
            }
        if selected_gap > 0.0:
            gap = self._gap_scores(dataset, self.config.gap_mode)
            base_ensemble = {n: (1.0 - selected_gap) * score + selected_gap * gap.get(n, 0.5) for n, score in base_ensemble.items()}
        if selected_consensus > 0.0:
            signal_maps = (rank_map, raw_map, ewma_map)
            adjusted = {}
            for n, score in base_ensemble.items():
                values = [signal_maps[i].get(n, 0.5) for i in range(3)]
                disagreement = max(values) - min(values)
                consensus = max(0.0, min(1.0, score - 0.35 * disagreement))
                adjusted[n] = (1.0 - selected_consensus) * score + selected_consensus * consensus
            base_ensemble = adjusted
        ensemble_scores = tuple(NumberScore(number=n, score=base_ensemble[n]) for n in sorted(base_ensemble))
        ensemble_scores = self._calibrate_ensemble_scores(dataset, engines, ensemble_scores)
        if self.config.learned_signal_model:
            learned = self._learned_feature_scores(dataset, self.config.learned_model_draws)
            shrink = self.config.learned_model_shrinkage
            ensemble_scores = tuple(
                NumberScore(number=item.number, score=(1.0 - shrink) * item.score + shrink * learned.get(item.number, 0.5))
                for item in ensemble_scores
            )

        pair_counts = self._combination_counts(dataset, 2)
        triple_counts = self._combination_counts(dataset, 3)
        structure = self._structure_profile(dataset)
        rng = random.Random(seed)

        candidates = []
        variant_specs = ((rank_engine, rank_scores), (raw_engine, raw_scores), (ewma_engine, ewma_scores), (None, ensemble_scores))
        candidate_weights = self._candidate_allocations(dataset, engines)
        allocations = [int(self.config.candidate_count * weight) for weight in candidate_weights]
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
