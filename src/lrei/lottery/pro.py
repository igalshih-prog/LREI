"""Pro lottery recommendation engine using multi-window historical signals."""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from itertools import combinations

from .dataset import LotteryDataset
from .generator import TicketGenerator
from .optimizer import LotteryOptimizer, OptimizerConfig
from .predictor import NumberScore
from .recommendation import RecommendedTicket, RecommendationResult


@dataclass(frozen=True)
class ProConfig:
    """Configuration for the Pro recommendation engine."""

    candidate_count: int = 2000
    max_overlap: int = 4
    max_tickets: int = 14
    use_rank_normalization: bool = True
    use_ewma: bool = False
    ewma_half_life: float = 36.0


class ProRecommendationEngine:
    """Build recommendations from multiple historical windows and combinations."""

    def __init__(self, config: ProConfig | None = None) -> None:
        self.config = config or ProConfig()
        if self.config.candidate_count < self.config.max_tickets:
            raise ValueError("candidate_count must cover max_tickets")
        if self.config.ewma_half_life <= 0:
            raise ValueError("ewma_half_life must be positive")
        self.generator = TicketGenerator()
        self.optimizer = LotteryOptimizer(
            OptimizerConfig(
                max_overlap=self.config.max_overlap,
                max_tickets=self.config.max_tickets,
            )
        )

    def recommend(self, dataset: LotteryDataset, seed: int | None = None) -> RecommendationResult:
        """Generate exactly the configured number of Pro tickets."""
        if len(dataset) == 0:
            raise ValueError("Dataset is empty")

        frequencies = self._frequency(dataset)
        recent_3 = self._window_frequency(dataset, years=3)
        recent_1 = self._window_frequency(dataset, years=1)
        recent_draws = self._recent_draw_frequency(dataset, 60)
        ewma = self._ewma_frequency(dataset, self.config.ewma_half_life) if self.config.use_ewma else {}
        individual_scores = self._individual_scores(
            frequencies, recent_3, recent_1, recent_draws, ewma
        )
        pair_counts = self._combination_counts(dataset, 2)
        triple_counts = self._combination_counts(dataset, 3)
        structure = self._structure_profile(dataset)

        rng = random.Random(seed)
        generated = [
            self._generate_candidate(individual_scores, pair_counts, triple_counts, structure, rng)
            for _ in range(self.config.candidate_count)
        ]
        recommended = self._select_portfolio(
            generated, individual_scores, frequencies, pair_counts, triple_counts, structure
        )

        if len(recommended) < self.config.max_tickets:
            expanded = list(generated)
            expanded.extend(
                self._generate_candidate(individual_scores, pair_counts, triple_counts, structure, rng)
                for _ in range(self.config.candidate_count)
            )
            recommended = self._select_portfolio(
                expanded, individual_scores, frequencies, pair_counts, triple_counts, structure
            )

        recommended = tuple(recommended[: self.config.max_tickets])
        if len(recommended) != self.config.max_tickets:
            raise ValueError("Pro optimizer could not produce the configured number of tickets")

        strong_scores = self._strong_scores(dataset)
        generated_with_strong = [
            RecommendedTicket(
                numbers=ticket,
                strong_number=self.generator.generate_strong_number(scores=strong_scores, rng=rng)
                if strong_scores else None,
            )
            for ticket in generated
        ]
        recommended_with_strong = tuple(
            RecommendedTicket(
                numbers=ticket,
                strong_number=self.generator.generate_strong_number(scores=strong_scores, rng=rng)
                if strong_scores else None,
            )
            for ticket in recommended
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
        try:
            return value.replace(year=value.year - years)
        except ValueError:
            return value.replace(year=value.year - years, month=2, day=28)

    @classmethod
    def _window_frequency(cls, dataset: LotteryDataset, years: int) -> dict[int, int]:
        dated_draws = [(draw, cls._parse_date(draw.date)) for draw in dataset]
        valid_dates = [draw_date for _, draw_date in dated_draws if draw_date is not None]
        if valid_dates:
            latest_date = max(valid_dates)
            start_date = cls._subtract_years(latest_date, years)
            window_draws = [
                draw for draw, draw_date in dated_draws
                if draw_date is not None and start_date <= draw_date <= latest_date
            ]
            if window_draws:
                return cls._frequency(LotteryDataset(window_draws))
        fallback_fraction = 0.30 if years == 3 else 0.10
        size = max(1, round(len(dataset) * fallback_fraction))
        return cls._frequency(LotteryDataset(dataset.draws[-size:]))

    @staticmethod
    def _recent_draw_frequency(dataset: LotteryDataset, draw_count: int) -> dict[int, int]:
        size = min(len(dataset), draw_count)
        return ProRecommendationEngine._frequency(LotteryDataset(dataset.draws[-size:]))

    @staticmethod
    def _ewma_frequency(dataset: LotteryDataset, half_life: float) -> dict[int, float]:
        """Compute an exponentially weighted occurrence signal over chronological draws."""
        numbers = sorted({number for draw in dataset for number in draw.numbers})
        if not numbers:
            return {}
        alpha = 1.0 - math.exp(-math.log(2.0) / half_life)
        values = {number: 0.0 for number in numbers}
        for draw in dataset:
            present = set(draw.numbers)
            for number in numbers:
                observation = 1.0 if number in present else 0.0
                values[number] = (1.0 - alpha) * values[number] + alpha * observation
        return values

    @staticmethod
    def _rank_normalise(values: dict[int, float], numbers: list[int]) -> dict[int, float]:
        """Convert each window to stable percentile-like ranks before blending."""
        if not numbers:
            return {}
        ordered = sorted(numbers, key=lambda number: (values.get(number, 0.0), number))
        denominator = max(1, len(ordered) - 1)
        return {number: index / denominator for index, number in enumerate(ordered)}

    @staticmethod
    def _scale_normalise(values: dict[int, float], numbers: list[int]) -> dict[int, float]:
        """Scale a frequency window to [0, 1] without mixing incompatible count scales."""
        if not numbers:
            return {}
        observed = [float(values.get(number, 0.0)) for number in numbers]
        minimum = min(observed)
        maximum = max(observed)
        if maximum <= minimum:
            return {number: 0.5 for number in numbers}
        span = maximum - minimum
        return {number: (float(values.get(number, 0.0)) - minimum) / span for number in numbers}

    def _individual_scores(self, frequencies, recent_3, recent_1, recent_draws, ewma=None):
        numbers = sorted(frequencies)
        normalise = self._rank_normalise if self.config.use_rank_normalization else self._scale_normalise
        all_values = normalise(frequencies, numbers)
        three_values = normalise(recent_3, numbers)
        one_values = normalise(recent_1, numbers)
        recent_values = normalise(recent_draws, numbers)
        ewma_values = normalise(ewma, numbers) if ewma else {}
        scores = []
        for number in numbers:
            if self.config.use_ewma:
                score = (
                    0.50 * all_values.get(number, 0.0)
                    + 0.23 * three_values.get(number, 0.0)
                    + 0.12 * one_values.get(number, 0.0)
                    + 0.07 * recent_values.get(number, 0.0)
                    + 0.08 * ewma_values.get(number, 0.0)
                )
            else:
                score = (
                    0.55 * all_values.get(number, 0.0)
                    + 0.25 * three_values.get(number, 0.0)
                    + 0.12 * one_values.get(number, 0.0)
                    + 0.08 * recent_values.get(number, 0.0)
                )
            scores.append(NumberScore(number=number, score=score))
        return tuple(scores)

    @staticmethod
    def _combination_counts(dataset: LotteryDataset, size: int) -> dict[tuple[int, ...], int]:
        counts: Counter[tuple[int, ...]] = Counter()
        for draw in dataset:
            for combo in combinations(sorted(draw.numbers), size):
                counts[combo] += 1
        return dict(counts)

    @staticmethod
    def _structure_profile(dataset: LotteryDataset) -> dict[str, float | tuple[float, ...]]:
        sums, odd_counts, low_counts, consecutive_counts = [], [], [], []
        for draw in dataset:
            numbers = sorted(draw.numbers)
            sums.append(float(sum(numbers)))
            odd_counts.append(float(sum(number % 2 for number in numbers)))
            low_counts.append(float(sum(number <= 18 for number in numbers)))
            consecutive_counts.append(float(sum(b == a + 1 for a, b in zip(numbers, numbers[1:]))))

        def mean(values):
            return sum(values) / len(values) if values else 0.0

        def stdev(values, fallback):
            if len(values) < 2:
                return fallback
            avg = mean(values)
            variance = sum((value - avg) ** 2 for value in values) / len(values)
            return max(math.sqrt(variance), fallback)

        return {
            "sum_mean": mean(sums),
            "sum_std": stdev(sums, 8.0),
            "odd_mean": mean(odd_counts),
            "low_mean": mean(low_counts),
            "consecutive_mean": mean(consecutive_counts),
            "sum_values": tuple(sums),
        }

    @staticmethod
    def _percentile(values, fraction):
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
        return ordered[index]

    @classmethod
    def _structure_score(cls, ticket, profile):
        numbers = sorted(ticket)
        odd_count = sum(number % 2 for number in numbers)
        low_count = sum(number <= 18 for number in numbers)
        total = sum(numbers)
        consecutive = sum(b == a + 1 for a, b in zip(numbers, numbers[1:]))
        sum_mean = float(profile["sum_mean"])
        sum_std = float(profile["sum_std"])
        odd_mean = float(profile["odd_mean"])
        low_mean = float(profile["low_mean"])
        consecutive_mean = float(profile["consecutive_mean"])
        sums = profile["sum_values"]
        score = math.exp(-abs(total - sum_mean) / (sum_std * 1.6))
        score *= math.exp(-abs(odd_count - odd_mean) / 1.7)
        score *= math.exp(-abs(low_count - low_mean) / 1.7)
        score *= math.exp(-abs(consecutive - consecutive_mean) / 1.8)
        lower_sum = cls._percentile(sums, 0.10)
        upper_sum = cls._percentile(sums, 0.90)
        score *= 1.08 if lower_sum <= total <= upper_sum else 0.82
        bands = [sum(1 for number in numbers if start <= number <= end) for start, end in ((1, 10), (11, 20), (21, 30), (31, 37))]
        score *= 1.0 if max(bands) <= 3 else 0.72
        if odd_count in (0, 6) or low_count in (0, 6):
            score *= 0.55
        run_length = longest_run = 1
        for left, right in zip(numbers, numbers[1:]):
            if right == left + 1:
                run_length += 1
                longest_run = max(longest_run, run_length)
            else:
                run_length = 1
        if longest_run >= 4:
            score *= 0.55
        elif longest_run == 3:
            score *= 0.82
        return score

    @staticmethod
    def _affinity_score(ticket, pair_counts, triple_counts, frequencies, draw_count):
        if draw_count <= 0:
            return 0.0
        pair_lifts, triple_lifts = [], []
        for left, right in combinations(ticket, 2):
            observed_count = pair_counts.get((left, right), 0)
            observed = observed_count / draw_count
            p_left = frequencies.get(left, 0) / draw_count
            p_right = frequencies.get(right, 0) / draw_count
            expected = p_left * p_right
            if expected > 0:
                raw_lift = observed / expected
                support = min(1.0, observed_count / 25.0)
                pair_lifts.append(1.0 + support * (min(raw_lift, 3.0) - 1.0))
        for combo in combinations(ticket, 3):
            observed_count = triple_counts.get(combo, 0)
            observed = observed_count / draw_count
            expected = 1.0
            for number in combo:
                expected *= frequencies.get(number, 0) / draw_count
            if expected > 0:
                raw_lift = observed / expected
                support = min(1.0, observed_count / 5.0)
                triple_lifts.append(1.0 + support * (min(raw_lift, 3.0) - 1.0))
        pair = sum(pair_lifts) / len(pair_lifts) if pair_lifts else 1.0
        triple = sum(triple_lifts) / len(triple_lifts) if triple_lifts else 1.0
        return 0.65 * min(pair / 2.0, 1.5) + 0.35 * min(triple / 2.0, 1.5)

    @classmethod
    def _candidate_score(cls, ticket, score_map, pair_counts, triple_counts, frequencies, draw_count, profile):
        number_score = sum(score_map.get(number, 0.0) for number in ticket) / len(ticket)
        affinity = cls._affinity_score(ticket, pair_counts, triple_counts, frequencies, draw_count)
        structure = cls._structure_score(ticket, profile)
        return 0.58 * number_score + 0.22 * affinity + 0.20 * structure

    def _select_portfolio(self, generated, scores, frequencies, pair_counts, triple_counts, structure):
        normalized = list(dict.fromkeys(tuple(sorted(ticket)) for ticket in generated))
        score_map = {item.number: item.score for item in scores}
        draw_count = max(1, round(sum(frequencies.values()) / 6))
        base_scores = {
            ticket: self._candidate_score(
                ticket, score_map, pair_counts, triple_counts, frequencies, draw_count, structure
            )
            for ticket in normalized
        }
        selected, selected_numbers = [], set()
        while len(selected) < self.config.max_tickets:
            compatible = [
                ticket for ticket in normalized
                if ticket not in selected and self.optimizer.is_compatible(ticket, selected)
            ]
            if not compatible:
                break

            def marginal(ticket):
                base = base_scores[ticket]
                new_numbers = len(set(ticket) - selected_numbers)
                overlap = sum(self.optimizer.overlap(ticket, prior) for prior in selected) / len(selected) if selected else 0.0
                return base + 0.035 * new_numbers - 0.018 * overlap

            best = max(compatible, key=lambda ticket: (marginal(ticket), tuple(-number for number in ticket)))
            selected.append(best)
            selected_numbers.update(best)
        return tuple(selected)

    @staticmethod
    def _strong_scores(dataset):
        counts = Counter(draw.strong_number for draw in dataset if draw.strong_number is not None)
        if not counts:
            return ()
        maximum = max(counts.values())
        return tuple(NumberScore(number=number, score=count / maximum) for number, count in sorted(counts.items()))

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        text = value.strip()[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _generate_candidate(self, scores, pair_counts, triple_counts, structure, rng):
        selected = []
        score_map = {item.number: item.score for item in scores}
        pair_max = max(pair_counts.values(), default=1)
        triple_max = max(triple_counts.values(), default=1)
        for _ in range(6):
            weights = []
            for number in score_map:
                if number in selected:
                    continue
                weight = max(score_map[number], 0.0001)
                if selected:
                    pair_bonus = sum(pair_counts.get(tuple(sorted((number, other))), 0) for other in selected) / len(selected)
                    weight *= 1.0 + 0.35 * (pair_bonus / pair_max)
                if len(selected) >= 2:
                    recent_pair = tuple(sorted((selected[-2], selected[-1])))
                    triple_bonus = triple_counts.get(tuple(sorted((number, *recent_pair))), 0) / triple_max
                    weight *= 1.0 + 0.15 * triple_bonus
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
        ticket = tuple(sorted(selected))
        if rng.random() < 0.72 and self._structure_score(ticket, structure) < 0.28:
            return self._generate_candidate(scores, pair_counts, triple_counts, structure, rng)
        return ticket
