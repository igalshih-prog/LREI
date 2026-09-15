"""Pro lottery recommendation engine using multi-window historical signals."""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import combinations

from .dataset import LotteryDataset
from .generator import TicketGenerator
from .optimizer import LotteryOptimizer, OptimizerConfig
from .predictor import NumberScore
from .recommendation import RecommendedTicket, RecommendationResult


@dataclass(frozen=True)
class ProConfig:
    """Configuration for the Pro recommendation engine."""

    candidate_count: int = 800
    max_overlap: int = 4
    max_tickets: int = 14


class ProRecommendationEngine:
    """Build recommendations from multiple historical windows and combinations."""

    def __init__(self, config: ProConfig | None = None) -> None:
        self.config = config or ProConfig()
        if self.config.candidate_count < self.config.max_tickets:
            raise ValueError("candidate_count must cover max_tickets")
        self.generator = TicketGenerator()
        self.optimizer = LotteryOptimizer(
            OptimizerConfig(
                max_overlap=self.config.max_overlap,
                max_tickets=self.config.max_tickets,
            )
        )

    def recommend(
        self,
        dataset: LotteryDataset,
        seed: int | None = None,
    ) -> RecommendationResult:
        """Generate up to the configured number of Pro tickets."""
        if len(dataset) == 0:
            raise ValueError("Dataset is empty")

        frequencies = self._frequency(dataset)
        recent_3 = self._window_frequency(dataset, years=3)
        recent_1 = self._window_frequency(dataset, years=1)
        recent_draws = self._recent_draw_frequency(dataset, 60)

        individual_scores = self._individual_scores(
            frequencies=frequencies,
            recent_3=recent_3,
            recent_1=recent_1,
            recent_draws=recent_draws,
        )

        pair_counts = self._combination_counts(dataset, 2)
        triple_counts = self._combination_counts(dataset, 3)

        rng = random.Random(seed)
        generated: list[tuple[int, ...]] = []

        for _ in range(self.config.candidate_count):
            generated.append(
                self._generate_candidate(
                    scores=individual_scores,
                    pair_counts=pair_counts,
                    triple_counts=triple_counts,
                    rng=rng,
                )
            )

        recommended = self.optimizer.optimize(generated)

        if len(recommended) < self.config.max_tickets:
            expanded = list(generated)
            for _ in range(self.config.candidate_count):
                expanded.append(
                    self._generate_candidate(
                        scores=individual_scores,
                        pair_counts=pair_counts,
                        triple_counts=triple_counts,
                        rng=rng,
                    )
                )
            recommended = self.optimizer.optimize(expanded)

        recommended = tuple(recommended[: self.config.max_tickets])
        if not recommended:
            raise ValueError("Pro optimizer returned no tickets")

        strong_scores = self._strong_scores(dataset)
        generated_with_strong = [
            RecommendedTicket(
                numbers=ticket,
                strong_number=(
                    self.generator.generate_strong_number(
                        scores=strong_scores,
                        rng=rng,
                    )
                    if strong_scores
                    else None
                ),
            )
            for ticket in generated
        ]

        recommended_set = set(recommended)
        recommended_with_strong = tuple(
            item
            for item in generated_with_strong
            if item.numbers in recommended_set
        )

        return RecommendationResult(
            scores=individual_scores,
            generated_tickets=tuple(generated),
            recommended_tickets=recommended,
            strong_scores=strong_scores,
            generated_tickets_with_strong=tuple(generated_with_strong),
            recommended_tickets_with_strong=recommended_with_strong,
        )

    @staticmethod
    def _frequency(dataset: LotteryDataset) -> dict[int, int]:
        counts: Counter[int] = Counter()
        for draw in dataset:
            counts.update(draw.numbers)
        return dict(counts)

    @staticmethod
    def _subtract_years(value: date, years: int) -> date:
        """Subtract whole calendar years while handling February 29."""
        try:
            return value.replace(year=value.year - years)
        except ValueError:
            return value.replace(
                year=value.year - years,
                month=2,
                day=28,
            )

    @classmethod
    def _window_frequency(
        cls,
        dataset: LotteryDataset,
        years: int,
    ) -> dict[int, int]:
        """Count numbers inside a real calendar window when dates are available."""
        dated_draws = [
            (draw, cls._parse_date(draw.date))
            for draw in dataset
        ]
        valid_dates = [
            draw_date
            for _, draw_date in dated_draws
            if draw_date is not None
        ]

        if valid_dates:
            latest_date = max(valid_dates)
            start_date = cls._subtract_years(latest_date, years)
            window_draws = [
                draw
                for draw, draw_date in dated_draws
                if draw_date is not None
                and start_date <= draw_date <= latest_date
            ]
            if window_draws:
                return cls._frequency(
                    LotteryDataset(window_draws)
                )

        # Fallback for legacy datasets that have no usable dates.
        fallback_fraction = 0.30 if years == 3 else 0.10
        size = max(1, round(len(dataset) * fallback_fraction))
        return cls._frequency(
            LotteryDataset(dataset.draws[-size:])
        )

    @staticmethod
    def _recent_draw_frequency(
        dataset: LotteryDataset,
        draw_count: int,
    ) -> dict[int, int]:
        size = min(len(dataset), draw_count)
        return ProRecommendationEngine._frequency(
            LotteryDataset(dataset.draws[-size:])
        )

    @staticmethod
    def _normalise(
        values: dict[int, float],
    ) -> dict[int, float]:
        if not values:
            return {}
        maximum = max(values.values())
        if maximum <= 0:
            return {number: 0.0 for number in values}
        return {
            number: value / maximum
            for number, value in values.items()
        }

    def _individual_scores(
        self,
        frequencies: dict[int, int],
        recent_3: dict[int, int],
        recent_1: dict[int, int],
        recent_draws: dict[int, int],
    ) -> tuple[NumberScore, ...]:
        all_values = self._normalise(
            {number: float(value) for number, value in frequencies.items()}
        )
        three_values = self._normalise(
            {number: float(value) for number, value in recent_3.items()}
        )
        one_values = self._normalise(
            {number: float(value) for number, value in recent_1.items()}
        )
        recent_values = self._normalise(
            {number: float(value) for number, value in recent_draws.items()}
        )

        scores: list[NumberScore] = []
        for number in sorted(frequencies):
            score = (
                0.35 * all_values.get(number, 0.0)
                + 0.25 * three_values.get(number, 0.0)
                + 0.25 * one_values.get(number, 0.0)
                + 0.15 * recent_values.get(number, 0.0)
            )
            scores.append(NumberScore(number=number, score=score))
        return tuple(scores)

    @staticmethod
    def _combination_counts(
        dataset: LotteryDataset,
        size: int,
    ) -> dict[tuple[int, ...], int]:
        counts: Counter[tuple[int, ...]] = Counter()
        for draw in dataset:
            for combo in combinations(sorted(draw.numbers), size):
                counts[combo] += 1
        return dict(counts)

    @staticmethod
    def _strong_scores(
        dataset: LotteryDataset,
    ) -> tuple[NumberScore, ...]:
        counts: Counter[int] = Counter(
            draw.strong_number
            for draw in dataset
            if draw.strong_number is not None
        )
        if not counts:
            return ()
        maximum = max(counts.values())
        return tuple(
            NumberScore(
                number=number,
                score=count / maximum,
            )
            for number, count in sorted(counts.items())
        )

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None

        text = value.strip()
        formats = (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
        )
        for fmt in formats:
            try:
                return date.fromisoformat(text[:10]) if fmt == "%Y-%m-%d" else date.fromisoformat(
                    date.strptime(text[:10], fmt).isoformat()
                )
            except ValueError:
                continue
        return None

    def _generate_candidate(
        self,
        scores: tuple[NumberScore, ...],
        pair_counts: dict[tuple[int, ...], int],
        triple_counts: dict[tuple[int, ...], int],
        rng: random.Random,
    ) -> tuple[int, ...]:
        selected: list[int] = []
        score_map = {item.number: item.score for item in scores}
        pair_max = max(pair_counts.values(), default=1)
        triple_max = max(triple_counts.values(), default=1)

        for _ in range(6):
            weights: list[tuple[int, float]] = []
            for number in score_map:
                if number in selected:
                    continue
                weight = max(score_map[number], 0.0001)
                if selected:
                    pair_bonus = sum(
                        pair_counts.get(tuple(sorted((number, other))), 0)
                        for other in selected
                    ) / len(selected)
                    pair_bonus /= pair_max
                    weight *= 1.0 + 0.45 * pair_bonus
                if len(selected) >= 2:
                    triple_bonus = sum(
                        triple_counts.get(
                            tuple(sorted((number, selected[-2], selected[-1]))),
                            0,
                        )
                    ) / triple_max
                    weight *= 1.0 + 0.20 * triple_bonus
                weights.append((number, weight))

            total = sum(weight for _, weight in weights)
            target = rng.random() * total
            cumulative = 0.0
            chosen = weights[-1][0]
            for number, weight in weights:
                cumulative += weight
                if target < cumulative:
                    chosen = number
                    break
            selected.append(chosen)

        return tuple(sorted(selected))
