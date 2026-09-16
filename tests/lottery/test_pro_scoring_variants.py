from pathlib import Path
from statistics import mean

from lrei.lottery.dataset import CsvDatasetLoader, LotteryDataset
from lrei.lottery.pro import ProConfig, ProRecommendationEngine


def _hits(tickets, actual):
    actual_set = set(actual)
    return mean(len(set(ticket) & actual_set) for ticket in tickets)


def test_pro_rank_vs_raw_frequency_walk_forward():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    draws = list(dataset.draws)
    holdout = min(60, max(30, len(draws) // 18))
    first = len(draws) - holdout

    rank_engine = ProRecommendationEngine(ProConfig(use_rank_normalization=True))
    raw_engine = ProRecommendationEngine(ProConfig(use_rank_normalization=False))

    rank_scores = []
    raw_scores = []
    for index, target in enumerate(draws[first:]):
        history = LotteryDataset(draws=draws[: first + index])
        rank = rank_engine.recommend(history, seed=9000 + index)
        raw = raw_engine.recommend(history, seed=9000 + index)
        rank_scores.append(_hits(rank.recommended_tickets, target.numbers))
        raw_scores.append(_hits(raw.recommended_tickets, target.numbers))

    print(f"Scoring-variant walk-forward draws: {holdout}")
    print(f"Rank-normalized Pro: {mean(rank_scores):.4f}")
    print(f"Raw-frequency Pro:   {mean(raw_scores):.4f}")
    print(f"Raw minus rank:      {mean(raw_scores) - mean(rank_scores):+.4f}")

    assert len(rank_scores) == holdout
    assert len(raw_scores) == holdout
    assert all(0 <= value <= 6 for value in rank_scores)
    assert all(0 <= value <= 6 for value in raw_scores)
