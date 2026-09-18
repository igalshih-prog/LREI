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

def test_pro_portfolio_selector_ablation():
    """Compare selector tradeoffs on a small fixed walk-forward sample."""
    from statistics import mean
    from lrei.lottery.dataset import LotteryDataset
    from lrei.lottery.pro import ProConfig

    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(20, max(12, len(draws) // 50))
    start = len(draws) - holdout

    variants = {
        "current": (0.035, 0.018),
        "coverage_light": (0.020, 0.018),
        "coverage_strong": (0.050, 0.018),
        "overlap_strong": (0.035, 0.030),
        "balanced": (0.025, 0.025),
    }
    results = {name: [] for name in variants}

    for offset, target in enumerate(draws[start:]):
        history = LotteryDataset(draws=draws[: start + offset])
        for name, (coverage, overlap) in variants.items():
            engine = ProRecommendationEngine(ProConfig(
                candidate_count=300,
                max_tickets=14,
                portfolio_coverage_weight=coverage,
                portfolio_overlap_penalty=overlap,
            ))
            result = engine.recommend(history, seed=91000 + offset)
            actual = set(target.numbers)
            results[name].append(mean(len(set(ticket) & actual) for ticket in result.recommended_tickets))

    print("Pro portfolio selector ablation:")
    for name, values in results.items():
        print(f"  {name}: {mean(values):.4f}")

    assert all(len(values) == holdout for values in results.values())
    assert all(all(0 <= value <= 6 for value in values) for values in results.values())