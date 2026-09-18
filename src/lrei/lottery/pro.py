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
    affinity_prior_strength: float = 0.0
    number_signal_strength: float = 1.0


class ProRecommendationEngine:
    """Build recommendations from multiple historical windows and combinations."""

    def __init__(self, config: ProConfig | None = None) -> None:
        self.config = config or ProConfig()
        if self.config.candidate_count < self.config.max_tickets:
            raise ValueError("candidate_count must cover max_tickets")
        if self.config.ewma_half_life <= 0:
            raise ValueError("ewma_half_life must be positive")
        if self.config.affinity_prior_strength < 0:
            raise ValueError("affinity_prior_strength must be non-negative")
        if not 0.0 <= self.config.number_signal_strength <= 1.0:
            raise ValueError("number_signal_strength must be between 0 and 1")
        self.generator = TicketGenerator()
        self.optimizer = LotteryOptimizer(
            OptimizerConfig(
                max_overlap=self.config.max_overlap,
                max_tickets=self.config.max_tickets,
            )
        )

    def recommend(self, dataset: LotteryDataset, seed: int | None = None) -> RecommendationResult:
        if len(dataset) == 0:
            raise ValueError("Dataset is empty")
        frequencies = self._frequency(dataset)
        recent_3 = self._window_frequency(dataset, 3)
        recent_1 = self._window_frequency(dataset, 1)
        recent_draws = self._recent_draw_frequency(dataset, 60)
        ewma = self._ewma_frequency(dataset, self.config.ewma_half_life) if self.config.use_ewma else {}
        scores = self._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma)
        pair_counts = self._combination_counts(dataset, 2)
        triple_counts = self._combination_counts(dataset, 3)
        structure = self._structure_profile(dataset)
        rng = random.Random(seed)
        generated = [self._generate_candidate(scores, pair_counts, triple_counts, structure, rng) for _ in range(self.config.candidate_count)]
        recommended = self._select_portfolio(generated, scores, frequencies, pair_counts, triple_counts, structure)
        if len(recommended) < self.config.max_tickets:
            expanded = generated + [self._generate_candidate(scores, pair_counts, triple_counts, structure, rng) for _ in range(self.config.candidate_count)]
            recommended = self._select_portfolio(expanded, scores, frequencies, pair_counts, triple_counts, structure)
        recommended = tuple(recommended[: self.config.max_tickets])
        if len(recommended) != self.config.max_tickets:
            raise ValueError("Pro optimizer could not produce the configured number of tickets")
        strong_scores = self._strong_scores(dataset)
        generated_with_strong = tuple(RecommendedTicket(numbers=t, strong_number=self.generator.generate_strong_number(scores=strong_scores, rng=rng) if strong_scores else None) for t in generated)
        recommended_with_strong = tuple(RecommendedTicket(numbers=t, strong_number=self.generator.generate_strong_number(scores=strong_scores, rng=rng) if strong_scores else None) for t in recommended)
        return RecommendationResult(
            scores=scores,
            generated_tickets=tuple(generated),
            recommended_tickets=recommended,
            strong_scores=strong_scores,
            generated_tickets_with_strong=generated_with_strong,
            recommended_tickets_with_strong=recommended_with_strong,
        )

    @staticmethod
    def _frequency(dataset):
        counts = Counter()
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
    def _window_frequency(cls, dataset, years):
        dated = [(draw, cls._parse_date(draw.date)) for draw in dataset]
        valid = [d for _, d in dated if d is not None]
        if valid:
            latest = max(valid)
            start = cls._subtract_years(latest, years)
            window = [draw for draw, d in dated if d is not None and start <= d <= latest]
            if window:
                return cls._frequency(LotteryDataset(window))
        fraction = 0.30 if years == 3 else 0.10
        size = max(1, round(len(dataset) * fraction))
        return cls._frequency(LotteryDataset(dataset.draws[-size:]))

    @staticmethod
    def _recent_draw_frequency(dataset, draw_count):
        return ProRecommendationEngine._frequency(LotteryDataset(dataset.draws[-min(len(dataset), draw_count):]))

    @staticmethod
    def _ewma_frequency(dataset, half_life):
        numbers = sorted({n for draw in dataset for n in draw.numbers})
        alpha = 1.0 - math.exp(-math.log(2.0) / half_life)
        values = {n: 0.0 for n in numbers}
        for draw in dataset:
            present = set(draw.numbers)
            for n in numbers:
                values[n] = (1.0 - alpha) * values[n] + alpha * (1.0 if n in present else 0.0)
        return values

    @staticmethod
    def _rank_normalise(values, numbers):
        ordered = sorted(numbers, key=lambda n: (values.get(n, 0.0), n))
        denominator = max(1, len(ordered) - 1)
        return {n: i / denominator for i, n in enumerate(ordered)}

    @staticmethod
    def _scale_normalise(values, numbers):
        observed = [float(values.get(n, 0.0)) for n in numbers]
        if not observed:
            return {}
        low, high = min(observed), max(observed)
        if high <= low:
            return {n: 0.5 for n in numbers}
        return {n: (float(values.get(n, 0.0)) - low) / (high - low) for n in numbers}

    def _individual_scores(self, frequencies, recent_3, recent_1, recent_draws, ewma=None):
        numbers = sorted(frequencies)
        normalise = self._rank_normalise if self.config.use_rank_normalization else self._scale_normalise
        a, b, c, d = (normalise(x, numbers) for x in (frequencies, recent_3, recent_1, recent_draws))
        e = normalise(ewma, numbers) if ewma else {}
        result = []
        for n in numbers:
            if self.config.use_ewma:
                score = 0.50 * a.get(n, 0) + 0.23 * b.get(n, 0) + 0.12 * c.get(n, 0) + 0.07 * d.get(n, 0) + 0.08 * e.get(n, 0)
            else:
                score = 0.55 * a.get(n, 0) + 0.25 * b.get(n, 0) + 0.12 * c.get(n, 0) + 0.08 * d.get(n, 0)
            score = 0.5 + self.config.number_signal_strength * (score - 0.5)
            result.append(NumberScore(number=n, score=score))
        return tuple(result)

    @staticmethod
    def _combination_counts(dataset, size):
        counts = Counter()
        for draw in dataset:
            for combo in combinations(sorted(draw.numbers), size):
                counts[combo] += 1
        return dict(counts)

    @staticmethod
    def _structure_profile(dataset):
        sums, odds, lows, consecutive = [], [], [], []
        for draw in dataset:
            n = sorted(draw.numbers)
            sums.append(float(sum(n)))
            odds.append(float(sum(x % 2 for x in n)))
            lows.append(float(sum(x <= 18 for x in n)))
            consecutive.append(float(sum(b == a + 1 for a, b in zip(n, n[1:]))))
        def avg(v): return sum(v) / len(v) if v else 0.0
        def sd(v):
            if len(v) < 2: return 8.0
            m = avg(v)
            return max(math.sqrt(sum((x - m) ** 2 for x in v) / len(v)), 8.0)
        return {"sum_mean": avg(sums), "sum_std": sd(sums), "odd_mean": avg(odds), "low_mean": avg(lows), "consecutive_mean": avg(consecutive), "sum_values": tuple(sums)}

    @staticmethod
    def _percentile(values, fraction):
        if not values: return 0.0
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))]

    @classmethod
    def _structure_score(cls, ticket, profile):
        n = sorted(ticket)
        odd = sum(x % 2 for x in n)
        low = sum(x <= 18 for x in n)
        total = sum(n)
        consecutive = sum(b == a + 1 for a, b in zip(n, n[1:]))
        score = math.exp(-abs(total - float(profile["sum_mean"])) / (float(profile["sum_std"]) * 1.6))
        score *= math.exp(-abs(odd - float(profile["odd_mean"])) / 1.7)
        score *= math.exp(-abs(low - float(profile["low_mean"])) / 1.7)
        score *= math.exp(-abs(consecutive - float(profile["consecutive_mean"])) / 1.8)
        score *= 1.08 if cls._percentile(profile["sum_values"], 0.10) <= total <= cls._percentile(profile["sum_values"], 0.90) else 0.82
        bands = [sum(start <= x <= end for x in n) for start, end in ((1, 10), (11, 20), (21, 30), (31, 37))]
        score *= 1.0 if max(bands) <= 3 else 0.72
        if odd in (0, 6) or low in (0, 6): score *= 0.55
        run = longest = 1
        for a, b in zip(n, n[1:]):
            run = run + 1 if b == a + 1 else 1
            longest = max(longest, run)
        if longest >= 4: score *= 0.55
        elif longest == 3: score *= 0.82
        return score

    @staticmethod
    def _affinity_score(ticket, pair_counts, triple_counts, frequencies, draw_count, prior_strength=0.0):
        if draw_count <= 0: return 0.0
        pair_lifts, triple_lifts = [], []
        for left, right in combinations(ticket, 2):
            count = pair_counts.get((left, right), 0)
            expected = (frequencies.get(left, 0) / draw_count) * (frequencies.get(right, 0) / draw_count)
            if expected <= 0: continue
            if prior_strength > 0:
                rate = (count + prior_strength * expected) / (draw_count + prior_strength)
                lift = rate / expected
                support = min(1.0, (count + prior_strength) / (25.0 + prior_strength))
            else:
                lift = (count / draw_count) / expected
                support = min(1.0, count / 25.0)
            pair_lifts.append(1.0 + support * (min(lift, 3.0) - 1.0))
        for combo in combinations(ticket, 3):
            count = triple_counts.get(combo, 0)
            expected = 1.0
            for n in combo: expected *= frequencies.get(n, 0) / draw_count
            if expected <= 0: continue
            if prior_strength > 0:
                rate = (count + prior_strength * expected) / (draw_count + prior_strength)
                lift = rate / expected
                support = min(1.0, (count + prior_strength) / (5.0 + prior_strength))
            else:
                lift = (count / draw_count) / expected
                support = min(1.0, count / 5.0)
            triple_lifts.append(1.0 + support * (min(lift, 3.0) - 1.0))
        pair = sum(pair_lifts) / len(pair_lifts) if pair_lifts else 1.0
        triple = sum(triple_lifts) / len(triple_lifts) if triple_lifts else 1.0
        return 0.65 * min(pair / 2.0, 1.5) + 0.35 * min(triple / 2.0, 1.5)

    @classmethod
    def _candidate_score(cls, ticket, score_map, pair_counts, triple_counts, frequencies, draw_count, profile, prior_strength=0.0):
        number_score = sum(score_map.get(n, 0.0) for n in ticket) / len(ticket)
        affinity = cls._affinity_score(ticket, pair_counts, triple_counts, frequencies, draw_count, prior_strength)
        return 0.58 * number_score + 0.22 * affinity + 0.20 * cls._structure_score(ticket, profile)

    def _portfolio_objective(self, selected, base):
        if not selected:
            return 0.0
        unique_count = len(set().union(*(set(t) for t in selected)))
        pair_overlaps = [self.optimizer.overlap(left, right) for left, right in combinations(selected, 2)]
        mean_overlap = sum(pair_overlaps) / len(pair_overlaps) if pair_overlaps else 0.0
        return sum(base[t] for t in selected) + 0.035 * unique_count - 0.018 * mean_overlap

    def _refine_portfolio(self, selected, candidates, base):
        """Improve the greedy portfolio with one deterministic local-swap pass."""
        current = list(selected)
        if len(current) < self.config.max_tickets:
            return tuple(current)
        ranked_candidates = sorted(candidates, key=lambda t: (base[t], tuple(-n for n in t)), reverse=True)
        shortlist = ranked_candidates[: min(300, len(ranked_candidates))]
        current_score = self._portfolio_objective(current, base)
        for index in range(len(current)):
            incumbent = current[index]
            best_ticket = incumbent
            best_score = current_score
            others = current[:index] + current[index + 1:]
            for candidate in shortlist:
                if candidate == incumbent or candidate in others:
                    continue
                if not self.optimizer.is_compatible(candidate, others):
                    continue
                trial = others + [candidate]
                trial_score = self._portfolio_objective(trial, base)
                if trial_score > best_score + 1e-12:
                    best_ticket = candidate
                    best_score = trial_score
            if best_ticket != incumbent:
                current[index] = best_ticket
                current_score = best_score
        return tuple(current)

    def _select_portfolio(self, generated, scores, frequencies, pair_counts, triple_counts, structure):
        candidates = list(dict.fromkeys(tuple(sorted(t)) for t in generated))
        score_map = {x.number: x.score for x in scores}
        draw_count = max(1, round(sum(frequencies.values()) / 6))
        base = {t: self._candidate_score(t, score_map, pair_counts, triple_counts, frequencies, draw_count, structure, self.config.affinity_prior_strength) for t in candidates}
        selected, selected_numbers = [], set()
        while len(selected) < self.config.max_tickets:
            compatible = [t for t in candidates if t not in selected and self.optimizer.is_compatible(t, selected)]
            if not compatible: break
            def value(t):
                new = len(set(t) - selected_numbers)
                overlap = sum(self.optimizer.overlap(t, prior) for prior in selected) / len(selected) if selected else 0.0
                return base[t] + 0.035 * new - 0.018 * overlap
            best = max(compatible, key=lambda t: (value(t), tuple(-n for n in t)))
            selected.append(best)
            selected_numbers.update(best)
        return self._refine_portfolio(selected, candidates, base)

    @staticmethod
    def _strong_scores(dataset):
        counts = Counter(draw.strong_number for draw in dataset if draw.strong_number is not None)
        if not counts: return ()
        maximum = max(counts.values())
        return tuple(NumberScore(number=n, score=c / maximum) for n, c in sorted(counts.items()))

    @staticmethod
    def _parse_date(value):
        if not value: return None
        text = value.strip()[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try: return datetime.strptime(text, fmt).date()
            except ValueError: pass
        return None

    def _generate_candidate(self, scores, pair_counts, triple_counts, structure, rng):
        selected = []
        score_map = {x.number: x.score for x in scores}
        pair_max = max(pair_counts.values(), default=1)
        triple_max = max(triple_counts.values(), default=1)
        for _ in range(6):
            weights = []
            for n in score_map:
                if n in selected: continue
                weight = max(score_map[n], 0.0001)
                if selected:
                    pair_bonus = sum(pair_counts.get(tuple(sorted((n, other))), 0) for other in selected) / len(selected)
                    weight *= 1.0 + 0.35 * pair_bonus / pair_max
                if len(selected) >= 2:
                    pair = tuple(sorted((selected[-2], selected[-1])))
                    weight *= 1.0 + 0.15 * triple_counts.get(tuple(sorted((n, *pair))), 0) / triple_max
                weights.append((n, weight))
            target, cumulative = rng.random() * sum(w for _, w in weights), 0.0
            chosen = weights[-1][0]
            for n, w in weights:
                cumulative += w
                if target < cumulative:
                    chosen = n
                    break
            selected.append(chosen)
        ticket = tuple(sorted(selected))
        if rng.random() < 0.72 and self._structure_score(ticket, structure) < 0.28:
            return self._generate_candidate(scores, pair_counts, triple_counts, structure, rng)
        return ticket
