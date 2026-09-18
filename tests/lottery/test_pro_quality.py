from pathlib import Path
from itertools import combinations

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.pro import ProRecommendationEngine


def test_pro_portfolio_quality_invariants():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    result = ProRecommendationEngine().recommend(dataset, seed=20260916)

    tickets = result.recommended_tickets
    assert len(tickets) == 14
    assert len(set(tickets)) == 14
    assert len(result.generated_tickets) == 2000

    for ticket in tickets:
        assert len(ticket) == 6
        assert len(set(ticket)) == 6
        assert all(1 <= number <= 37 for number in ticket)

    overlaps = [
        len(set(left) & set(right))
        for left, right in combinations(tickets, 2)
    ]
    assert overlaps
    assert max(overlaps) <= 4

    # The portfolio should cover the full number range rather than collapsing
    # onto only a small set of historically frequent numbers.
    covered = set().union(*map(set, tickets))
    assert len(covered) >= 30


def test_pro_is_reproducible_for_same_seed():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = ProRecommendationEngine()

    first = engine.recommend(dataset, seed=424242)
    second = engine.recommend(dataset, seed=424242)

    assert first.recommended_tickets == second.recommended_tickets
    assert first.generated_tickets == second.generated_tickets


def test_pro_coverage_is_stable_across_seeds():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = ProRecommendationEngine()
    coverages = []
    for seed in (1, 7, 42, 99, 20260918):
        result = engine.recommend(dataset, seed=seed)
        covered = set().union(*map(set, result.recommended_tickets))
        coverages.append(len(covered))
    assert min(coverages) >= 30
    assert max(coverages) <= 37
