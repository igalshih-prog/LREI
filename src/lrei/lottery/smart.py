"""Smart model-selection layer for LREI lottery recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .dataset import LotteryDataset
from .elite import EliteProConfig, EliteProRecommendationEngine
from .pro import ProConfig, ProRecommendationEngine
from .recommendation import RecommendationEngine, RecommendationResult
from .statistics import LotteryStatistics


@dataclass(frozen=True)
class SmartConfig:
    """Configuration for chronological Regular/Pro/Elite model selection."""

    calibration_draws: int = 12
    calibration_candidate_count: int = 200
    min_history_draws: int = 60
    selection_margin: float = 0.0
    calibration_origins: int = 3
    recency_decay: float = 0.85
    stability_penalty: float = 0.10
    selection_metric: str = "mean"
    tail_weight_4: float = 0.50
    tail_weight_5: float = 1.00
    tail_weight_6: float = 2.00

    def __post_init__(self) -> None:
        if self.calibration_draws < 1:
            raise ValueError("calibration_draws must be positive")
        if self.calibration_candidate_count < 14:
            raise ValueError("calibration_candidate_count must be at least 14")
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
        if self.selection_metric not in {"mean", "tail", "jackpot"}:
            raise ValueError("selection_metric must be 'mean', 'tail', or 'jackpot'")
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
            for draw_index, target in enumerate(validation):
                for model_index, (name, model) in enumerate(models.items()):
                    model_seed = (seed or 0) + origin_index * 10000 + draw_index * 101 + model_index
                    if name == "regular":
                        result = model.recommend(
                            LotteryStatistics.from_dataset(train),
                            ticket_count=14,
                            seed=model_seed,
                        )
                    else:
                        result = model.recommend(train, seed=model_seed)
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

    def recommend(self, dataset: LotteryDataset, seed: int | None = None) -> RecommendationResult:
        selected, _ = self.select_model(dataset, seed=seed)
        if selected == "regular":
            return RecommendationEngine().recommend(
                LotteryStatistics.from_dataset(dataset),
                ticket_count=14,
                seed=seed,
            )
        if selected == "pro":
            return ProRecommendationEngine().recommend(dataset, seed=seed)
        return EliteProRecommendationEngine().recommend(dataset, seed=seed)
