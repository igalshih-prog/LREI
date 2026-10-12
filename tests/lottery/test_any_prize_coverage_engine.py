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
        {"local_swap_passes": -1},
        {"local_swap_passes": 11},
    ):
        try:
            AnyPrizeCoverageConfig(**config)
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for {config}")


def test_local_swap_refinement_never_reduces_exact_coverage():
    """Every accepted local swap must preserve or improve union coverage."""
    rng = random.Random(20261015)
    candidates = []
    seen = set()
    while len(candidates) < 22:
        ticket = tuple(sorted(rng.sample(range(1, 38), 6)))
        if ticket not in seen:
            seen.add(ticket)
            candidates.append(ticket)

    # Small synthetic masks exercise selection without rebuilding millions of
    # real draw outcomes; exact production masks are tested above.
    mask_rng = random.Random(20261016)
    masks = tuple(mask_rng.getrandbits(256) for _ in candidates)
    baseline = AnyPrizeCoverageRecommendationEngine(
        AnyPrizeCoverageConfig(candidate_count=len(candidates), local_swap_passes=0)
    )
    refined = AnyPrizeCoverageRecommendationEngine(
        AnyPrizeCoverageConfig(candidate_count=len(candidates), local_swap_passes=2)
    )
    baseline_tickets, baseline_count, _ = baseline._select_candidate_pool(candidates, masks)
    refined_tickets, refined_count, _ = refined._select_candidate_pool(candidates, masks)

    assert len(baseline_tickets) == len(refined_tickets) == 14
    assert len(set(refined_tickets)) == 14
    assert refined_count >= baseline_count


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
    print(f"  greedy+local-swap exact 3+ coverage={greedy_probability:.4%}")
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
            f"  pool={size}: greedy+local-swap={greedy_probability:.4%}, "
            f"same-pool random={random_mean:.4%}, "
            f"delta={greedy_probability - random_mean:+.4%}"
        )

    print("Any-prize candidate-pool size ablation (exact 3+ main-hit coverage):")
    assert all(greedy > random_mean for greedy, random_mean in results.values())
    assert all(0.0 < greedy <= 1.0 for greedy, _ in results.values())
    assert all(0.0 < random_mean <= 1.0 for _, random_mean in results.values())


@pytest.mark.slow
def test_any_prize_candidate_pool_size_multi_seed_diagnostic():
    """Test whether larger candidate pools improve exact coverage across independent pools."""
    pool_sizes = (100, 250, 500)
    seeds = tuple(20261020 + offset for offset in range(10))
    greedy_by_size = {size: [] for size in pool_sizes}
    random_by_size = {size: [] for size in pool_sizes}
    local_swap_deltas = []

    for pool_seed in seeds:
        rng = random.Random(pool_seed)
        candidates = []
        seen = set()
        while len(candidates) < max(pool_sizes):
            ticket = tuple(sorted(rng.sample(range(1, 38), 6)))
            if ticket not in seen:
                seen.add(ticket)
                candidates.append(ticket)

        engine = AnyPrizeCoverageRecommendationEngine(
            AnyPrizeCoverageConfig(candidate_count=max(pool_sizes), max_tickets=14)
        )
        masks = tuple(engine._coverage_mask(ticket, engine._choose) for ticket in candidates)

        for size in pool_sizes:
            _, covered_count, _ = engine._select_candidate_pool(
                candidates[:size], masks[:size]
            )
            greedy_by_size[size].append(covered_count / TOTAL_DRAWS)
            if size == 100:
                no_swap_engine = AnyPrizeCoverageRecommendationEngine(
                    AnyPrizeCoverageConfig(candidate_count=100, max_tickets=14, local_swap_passes=0)
                )
                _, greedy_only_count, _ = no_swap_engine._select_candidate_pool(
                    candidates[:size], masks[:size]
                )
                local_swap_deltas.append((covered_count - greedy_only_count) / TOTAL_DRAWS)

            baseline_rng = random.Random(pool_seed + 1_000_000 + size)
            random_coverage = []
            for _ in range(100):
                chosen = baseline_rng.sample(range(size), 14)
                covered = 0
                for index in chosen:
                    covered |= masks[index]
                random_coverage.append(covered.bit_count() / TOTAL_DRAWS)
            random_by_size[size].append(mean(random_coverage))

    def seed_bootstrap_ci(values, bootstrap_seed):
        bootstrap_rng = random.Random(bootstrap_seed)
        estimates = [
            mean(values[bootstrap_rng.randrange(len(values))] for _ in values)
            for _ in range(5000)
        ]
        estimates.sort()
        return (
            estimates[int(0.025 * (len(estimates) - 1))],
            estimates[int(0.975 * (len(estimates) - 1))],
        )

    print("Any-prize candidate-pool multi-seed diagnostic (10 independent pools):")
    swap_ci = seed_bootstrap_ci(local_swap_deltas, 20261299)
    print(
        f"  local-swap vs greedy-only at pool=100: mean_delta={mean(local_swap_deltas):+.4%}, "
        f"improved_pools={sum(value > 0 for value in local_swap_deltas)}/{len(local_swap_deltas)}, "
        f"seed-bootstrap_CI=[{swap_ci[0]:+.4%}, {swap_ci[1]:+.4%}]"
    )
    for size in pool_sizes:
        greedy = greedy_by_size[size]
        random_mean = random_by_size[size]
        delta = [left - right for left, right in zip(greedy, random_mean)]
        ci = seed_bootstrap_ci(delta, 20261100 + size)
        print(
            f"  pool={size}: greedy_mean={mean(greedy):.4%}, "
            f"range=[{min(greedy):.4%}, {max(greedy):.4%}], "
            f"same-pool_random_mean={mean(random_mean):.4%}, "
            f"mean_delta={mean(delta):+.4%}, seed-bootstrap_CI=[{ci[0]:+.4%}, {ci[1]:+.4%}]"
        )

    for larger, smaller in ((250, 100), (500, 100), (500, 250)):
        paired = [
            big - small
            for big, small in zip(greedy_by_size[larger], greedy_by_size[smaller])
        ]
        ci = seed_bootstrap_ci(paired, 20261200 + larger)
        print(
            f"  pool {larger} - {smaller}: mean={mean(paired):+.4%}, "
            f"positive_pools={sum(value > 0 for value in paired)}/{len(paired)}, "
            f"seed-bootstrap_CI=[{ci[0]:+.4%}, {ci[1]:+.4%}]"
        )

    assert all(len(values) == len(seeds) for values in greedy_by_size.values())
    assert all(0.0 < value <= 1.0 for values in greedy_by_size.values() for value in values)
    assert all(0.0 < value <= 1.0 for values in random_by_size.values() for value in values)
