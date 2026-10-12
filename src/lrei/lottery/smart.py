"""Smart model-selection layer for LREI lottery recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .dataset import LotteryDataset
from .elite import EliteProConfig, EliteProRecommendationEngine
from .any_prize_coverage_engine import (
    AnyPrizeCoverageConfig,
    AnyPrizeCoverageRecommendationEngine,
)
from .coverage_engine import CoverageRecommendationEngine
from .pro import ProConfig, ProRecommendationEngine
from .prize_evaluation import evaluate_portfolio_prizes
from .recommendation import RecommendationEngine, RecommendationResult, RecommendedTicket
from .statistics import LotteryStatistics


@dataclass(frozen=True)
class SmartConfig:
    """Configuration for chronological Regular/Pro/Elite model selection."""

    calibration_draws: int = 12
    calibration_candidate_count: int = 200
    recommendation_candidate_count: int = 2000
    coverage_candidate_count: int = 250
    min_history_draws: int = 60
    selection_margin: float = 0.0
    calibration_origins: int = 3
    recency_decay: float = 0.85
    stability_penalty: float = 0.10
    selection_metric: str = "mean"
    tail_weight_4: float = 0.50
    tail_weight_5: float = 1.00
    tail_weight_6: float = 2.00
    calibration_seed: int = 314159
    objective: str = "historical"

    def __post_init__(self) -> None:
        if self.calibration_draws < 1:
            raise ValueError("calibration_draws must be positive")
        if self.calibration_candidate_count < 14:
            raise ValueError("calibration_candidate_count must be at least 14")
        if self.recommendation_candidate_count < 14:
            raise ValueError("recommendation_candidate_count must be at least 14")
        if not 14 <= self.coverage_candidate_count <= 500:
            raise ValueError("coverage_candidate_count must be between 14 and 500")
        if self.min_history_draws < self.calibration_draws + 20:
            raise ValueError("min_history_draws is too small for calibration")
        if self.selection_margin < 0:
            raise ValueError("selection_margin must be non-negative")
        if self.calibration_origins < 1:
            raise ValueError("calibration_origins must be at least 1")
        if not 0.0 < self.recency_decay <= 1.0:
            raise ValueError("recency_decay must be in (0, 1]")
        if self.stability_penalty < 0:
            raise ValueError("stability_penalty must be non-negative")
        if self.selection_metric not in {"mean", "tail", "jackpot", "prize"}:
            raise ValueError("selection_metric must be 'mean', 'tail', 'jackpot', or 'prize'")
        if self.objective not in {"historical", "coverage_4plus", "coverage_any_prize"}:
            raise ValueError("objective must be 'historical', 'coverage_4plus', or 'coverage_any_prize'")
        if self.tail_weight_4 < 0 or self.tail_weight_5 < 0 or self.tail_weight_6 < 0:
            raise ValueError("tail weights must be non-negative")


class SmartRecommendationEngine:
    """Choose the strongest historical model, then run that model on full history.

    This is a model-selection layer, not a claim that lottery outcomes are
    predictable. Selection is strictly chronological: validation draws are
    always earlier than the target recommendation.
    """

    def __init__(self, config: SmartConfig | None = None) -> None:
        self.config = config or SmartConfig()

    def _models(self):
        return {
            "regular": RecommendationEngine(),
            "pro": ProRecommendationEngine(
                ProConfig(
                    candidate_count=self.config.calibration_candidate_count,
                    max_tickets=14,
                )
            ),
            "elite": EliteProRecommendationEngine(
                EliteProConfig(
                    candidate_count=self.config.calibration_candidate_count,
                    max_tickets=14,
                    adaptive_weights=False,
                    adaptive_candidate_weights=False,
                )
            ),
        }

    def _validation_score(self, result: RecommendationResult, target) -> float:
        if self.config.selection_metric == "prize":
            prize_tickets = getattr(result, "recommended_tickets_with_strong", ())
            if not prize_tickets:
                prize_tickets = tuple(
                    RecommendedTicket(numbers=tuple(ticket))
                    for ticket in result.recommended_tickets
                )
            prize_outcome = evaluate_portfolio_prizes(prize_tickets, target)
            if prize_outcome.best_prize_tier is None:
                return 0.0
            return (9.0 - prize_outcome.best_prize_tier) / 8.0

        actual = set(target.numbers)
        hits = [len(set(ticket) & actual) for ticket in result.recommended_tickets]
        mean_hits = mean(hits)
        if self.config.selection_metric == "mean":
            return mean_hits
        if self.config.selection_metric == "tail":
            return (
                mean_hits
                + self.config.tail_weight_4 * mean(hit >= 4 for hit in hits)
                + self.config.tail_weight_5 * mean(hit >= 5 for hit in hits)
                + self.config.tail_weight_6 * mean(hit == 6 for hit in hits)
            )
        best_hit = max(hits)
        return (
            best_hit
            + self.config.tail_weight_4 * float(best_hit >= 4)
            + self.config.tail_weight_5 * float(best_hit >= 5)
            + self.config.tail_weight_6 * float(best_hit == 6)
        )

    def select_model(self, dataset: LotteryDataset, seed: int | None = None) -> tuple[str, dict[str, float]]:
        if self.config.objective == "coverage_4plus":
            # This objective is solved analytically by the Coverage engine;
            # historical model selection would only add noise to a known optimum.
            return "coverage", {"coverage": 1.0}
        if self.config.objective == "coverage_any_prize":
            # Optimize exact 3+-match draw coverage rather than fitting a noisy
            # number predictor. The engine uses random candidate lines only.
            return "coverage_any_prize", {"coverage_any_prize": 1.0}
        if len(dataset) < self.config.min_history_draws:
            return "elite", {}

        block = self.config.calibration_draws
        minimum_train = 20
        max_origins = min(
            self.config.calibration_origins,
            max(1, (len(dataset) - minimum_train) // block),
        )
        if max_origins < 1:
            return "elite", {}

        models = self._models()
        scores = {name: [] for name in models}
        origin_scores = {name: [] for name in models}

        for origin_index in range(max_origins):
            origin = len(dataset) - origin_index * block
            validation_start = origin - block
            if validation_start < minimum_train:
                break
            train = LotteryDataset(dataset.draws[:validation_start])
            validation = dataset.draws[validation_start:origin]
            block_scores = {name: [] for name in models}
            # The training history is fixed for this validation block, so each
            # model should produce one portfolio per origin and that same
            # portfolio should be scored against every draw in the block.
            # Previously a fresh random portfolio was generated for each target,
            # adding Monte Carlo noise and repeating expensive model generation.
            for model_index, (name, model) in enumerate(models.items()):
                # Keep model selection independent of the caller's final-ticket seed.
                # Otherwise random candidate generation can change which model wins calibration.
                model_seed = self.config.calibration_seed + origin_index * 10000 + model_index
                if name == "regular":
                    result = model.recommend(
                        LotteryStatistics.from_dataset(train),
                        ticket_count=14,
                        seed=model_seed,
                    )
                else:
                    result = model.recommend(train, seed=model_seed)
                for target in validation:
                    value = self._validation_score(result, target)
                    scores[name].append(value)
                    block_scores[name].append(value)
            for name, values in block_scores.items():
                origin_scores[name].append(mean(values))

        if not all(scores.values()):
            return "elite", {}

        raw_means = {name: mean(values) for name, values in scores.items()}
        selection_scores = {}
        for name in models:
            blocks = origin_scores[name]
            weights = [self.config.recency_decay ** i for i in range(len(blocks))]
            total_weight = sum(weights)
            weighted_mean = sum(value * weight for value, weight in zip(blocks, weights)) / total_weight
            if len(blocks) > 1:
                block_mean = mean(blocks)
                stability = mean((value - block_mean) ** 2 for value in blocks) ** 0.5
            else:
                stability = 0.0
            selection_scores[name] = weighted_mean - self.config.stability_penalty * stability

        best_name = max(selection_scores, key=selection_scores.get)
        elite_score = selection_scores["elite"]

        # A non-Elite model must beat Elite by the configured margin before
        # Smart switches away from the stronger default.
        if best_name != "elite" and selection_scores[best_name] <= elite_score + self.config.selection_margin:
            best_name = "elite"

        return best_name, raw_means

    def _recommend_selected(self, selected: str, dataset: LotteryDataset, seed: int | None = None) -> RecommendationResult:
        if selected == "coverage":
            return CoverageRecommendationEngine().recommend(dataset, seed=seed)
        if selected == "coverage_any_prize":
            candidate_count = self.config.coverage_candidate_count
            return AnyPrizeCoverageRecommendationEngine(
                AnyPrizeCoverageConfig(candidate_count=candidate_count, max_tickets=14)
            ).recommend(dataset, seed=seed)
        if selected == "regular":
            return RecommendationEngine().recommend(
                LotteryStatistics.from_dataset(dataset),
                ticket_count=14,
                seed=seed,
            )
        if selected == "pro":
            return ProRecommendationEngine(
                ProConfig(candidate_count=self.config.recommendation_candidate_count, max_tickets=14)
            ).recommend(dataset, seed=seed)
        return EliteProRecommendationEngine(
            EliteProConfig(
                candidate_count=self.config.recommendation_candidate_count,
                max_tickets=14,
                adaptive_weights=False,
                adaptive_candidate_weights=False,
            )
        ).recommend(dataset, seed=seed)

    def recommend(self, dataset: LotteryDataset, seed: int | None = None) -> RecommendationResult:
        selected, _ = self.select_model(dataset, seed=seed)
        return self._recommend_selected(selected, dataset, seed=seed)
