import random
from math import comb
from pathlib import Path
from statistics import mean

import pytest

from lrei.lottery.any_prize_coverage_engine import (
    AnyPrizeCoverageConfig,
    AnyPrizeCoverageRecommendationEngine,
    TOTAL_DRAWS,
)
from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.portfolio_coverage import portfolio_coverage


TICKET_A = (1, 2, 3, 4, 5, 6)
TICKET_B = (1, 7, 8, 9, 10, 11)


def test_ticket_mask_count_matches_exact_single_ticket_combinatorics():
    count = AnyPrizeCoverageRecommendationEngine._coverage_mask(TICKET_A).bit_count()
    expected = sum(comb(6, matches) * comb(31, 6 - matches) for matches in range(3, 7))

    assert count == expected
    assert count == portfolio_coverage([TICKET_A], threshold=3)["covered_draws"]


def test_bitmask_union_matches_exact_two_ticket_coverage():
    actual = AnyPrizeCoverageRecommendationEngine.covered_draw_count(
        [TICKET_A, TICKET_B]
    )
    expected = portfolio_coverage([TICKET_A, TICKET_B], threshold=3)["covered_draws"]

    assert actual == expected


def test_any_prize_engine_returns_fourteen_valid_unique_tickets():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = AnyPrizeCoverageRecommendationEngine(
        AnyPrizeCoverageConfig(candidate_count=18, max_tickets=14)
    )
    result = engine.recommend(dataset, seed=20261011)

    assert len(result.generated_tickets) == 18
    assert len(result.recommended_tickets) == 14
    assert len(set(result.recommended_tickets)) == 14
    assert all(len(ticket) == 6 and len(set(ticket)) == 6 for ticket in result.recommended_tickets)
    assert all(1 <= number <= 37 for ticket in result.recommended_tickets for number in ticket)
    assert all(score.score == 0.5 for score in result.scores)
    assert len(result.recommended_tickets_with_strong) == 14
    assert all(
        ticket.strong_number is not None and 1 <= ticket.strong_number <= 7
        for ticket in result.recommended_tickets_with_strong
    )


def test_any_prize_config_bounds_candidate_pool_and_ticket_count():
    for config in (
        {"candidate_count": 13},
        {"candidate_count": 501},
        {"max_tickets": 13},
    ):
        try:
            AnyPrizeCoverageConfig(**config)
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for {config}")


@pytest.mark.slow
def test_exact_any_prize_coverage_beats_random_portfolios_from_same_pool():
    """Compare greedy exact coverage against random 14-line selections from the same pool."""
    rng = random.Random(20261011)
    candidate_count = 100
    candidates = []
    seen = set()
    while len(candidates) < candidate_count:
        ticket = tuple(sorted(rng.sample(range(1, 38), 6)))
        if ticket not in seen:
            seen.add(ticket)
            candidates.append(ticket)

    engine = AnyPrizeCoverageRecommendationEngine(
        AnyPrizeCoverageConfig(candidate_count=candidate_count, max_tickets=14)
    )
    selected, covered_count, masks = engine._select_candidate_pool(candidates)
    greedy_probability = covered_count / TOTAL_DRAWS

    baseline_rng = random.Random(20261012)
    random_probabilities = []
    for _ in range(200):
        chosen_indices = baseline_rng.sample(range(candidate_count), 14)
        covered = 0
        for index in chosen_indices:
            covered |= masks[index]
        random_probabilities.append(covered.bit_count() / TOTAL_DRAWS)

    random_mean = mean(random_probabilities)
    print("Exact any-prize coverage comparison:")
    print(f"  candidate pool={candidate_count}; recommended tickets={len(selected)}")
    print(f"  greedy exact 3+ coverage={greedy_probability:.4%}")
    print(f"  random 14-of-same-pool mean={random_mean:.4%}")
    print(f"  delta={greedy_probability - random_mean:+.4%}")

    assert len(selected) == 14
    assert greedy_probability > random_mean


@pytest.mark.slow
def test_any_prize_candidate_pool_size_ablation():
    """Compare exact greedy coverage across nested pool sizes and same-pool random portfolios."""
    rng = random.Random(20261013)
    pool_sizes = (100, 250, 500)
    candidate_count = max(pool_sizes)
    candidates = []
    seen = set()
    while len(candidates) < candidate_count:
        ticket = tuple(sorted(rng.sample(range(1, 38), 6)))
        if ticket not in seen:
            seen.add(ticket)
            candidates.append(ticket)

    engine = AnyPrizeCoverageRecommendationEngine(
        AnyPrizeCoverageConfig(candidate_count=candidate_count, max_tickets=14)
    )
    # Each mask describes every 6/37 outcome for which that ticket has 3+ hits.
    # Reuse masks for nested prefixes so the comparison isolates pool size.
    masks = tuple(engine._coverage_mask(ticket, engine._choose) for ticket in candidates)
    baseline_rng = random.Random(20261014)
    baseline_trials = 100
    results = {}

    for size in pool_sizes:
        selected, covered_count, _ = engine._select_candidate_pool(
            candidates[:size], masks[:size]
        )
        greedy_probability = covered_count / TOTAL_DRAWS
        random_probabilities = []
        for _ in range(baseline_trials):
            chosen = baseline_rng.sample(range(size), 14)
            covered = 0
            for index in chosen:
                covered |= masks[index]
            random_probabilities.append(covered.bit_count() / TOTAL_DRAWS)
        random_mean = mean(random_probabilities)
        results[size] = (greedy_probability, random_mean)
        print(
            f"  pool={size}: greedy={greedy_probability:.4%}, "
            f"same-pool random={random_mean:.4%}, "
            f"delta={greedy_probability - random_mean:+.4%}"
        )

    print("Any-prize candidate-pool size ablation (exact 3+ main-hit coverage):")
    assert all(greedy > random_mean for greedy, random_mean in results.values())
    assert all(0.0 < greedy <= 1.0 for greedy, _ in results.values())
    assert all(0.0 < random_mean <= 1.0 for _, random_mean in results.values())
