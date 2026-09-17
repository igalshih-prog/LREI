from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.elite import EliteProConfig, EliteProRecommendationEngine


def test_elite_pro_generates_fourteen_diverse_tickets():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    engine = EliteProRecommendationEngine(EliteProConfig(candidate_count=90, max_tickets=14))
    result = engine.recommend(dataset, seed=4242)

    assert len(result.generated_tickets) == 90
    assert len(result.recommended_tickets) == 14
    assert len(set(result.recommended_tickets)) == 14
    assert all(len(ticket) == 6 for ticket in result.recommended_tickets)
    assert all(len(set(ticket)) == 6 for ticket in result.recommended_tickets)
    assert all(1 <= n <= 37 for ticket in result.recommended_tickets for n in ticket)
    for index, ticket in enumerate(result.recommended_tickets):
        for other in result.recommended_tickets[index + 1 :]:
            assert engine.optimizer.overlap(ticket, other) <= 4


def test_elite_pro_is_reproducible():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    config = EliteProConfig(candidate_count=90, max_tickets=14)
    first = EliteProRecommendationEngine(config).recommend(dataset, seed=99)
    second = EliteProRecommendationEngine(config).recommend(dataset, seed=99)
    assert first.recommended_tickets == second.recommended_tickets
    assert first.scores == second.scores
