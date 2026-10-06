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

    def __post_init__(self) -> None:
        if self.calibration_draws < 1:
            raise ValueError("calibration_draws must be positive")
        if self.calibration_candidate_count < 14:
            raise ValueError("calibration_candidate_count must be at least 14")
        if self.min_history_draws < self.calibration_draws + 20:
            raise ValueError("min_history_draws is too small for calibration")
        if self.selection_margin < 0:
            raise ValueError("selection_margin must be non-negative")


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

    @staticmethod
    def _mean_hits(result: RecommendationResult, target) -> float:
        actual = set(target.numbers)
        return mean(
            len(set(ticket) & actual)
            for ticket in result.recommended_tickets
        )

    def select_model(self, dataset: LotteryDataset, seed: int | None = None) -> tuple[str, dict[str, float]]:
        if len(dataset) < self.config.min_history_draws:
            return "elite", {}

        validation = dataset.draws[-self.config.calibration_draws:]
        train = LotteryDataset(dataset.draws[:-self.config.calibration_draws])
        if len(train) < 20:
            return "elite", {}

        models = self._models()
        scores = {name: [] for name in models}

        for draw_index, target in enumerate(validation):
            for model_index, (name, model) in enumerate(models.items()):
                if name == "regular":
                    result = model.recommend(
                        LotteryStatistics.from_dataset(train),
                        ticket_count=14,
                        seed=(seed or 0) + draw_index * 101 + model_index,
                    )
                else:
                    result = model.recommend(
                        train,
                        seed=(seed or 0) + draw_index * 101 + model_index,
                    )
                scores[name].append(self._mean_hits(result, target))

        means = {name: mean(values) for name, values in scores.items()}
        best_name = max(means, key=means.get)
        elite_score = means["elite"]

        # A non-Elite model must beat Elite by the configured margin before
        # Smart switches away from the stronger default.
        if best_name != "elite" and means[best_name] <= elite_score + self.config.selection_margin:
            best_name = "elite"

        return best_name, means

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
