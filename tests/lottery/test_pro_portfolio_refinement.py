from lrei.lottery.pro import ProRecommendationEngine, ProConfig


def test_local_swap_never_decreases_portfolio_objective():
    engine = ProRecommendationEngine(ProConfig(candidate_count=20, max_tickets=3))
    selected = (
        (1, 2, 3, 10, 20, 30),
        (4, 5, 6, 11, 21, 31),
        (7, 8, 9, 12, 22, 32),
    )
    candidates = list(selected) + [
        (1, 4, 7, 13, 23, 33),
        (2, 5, 8, 14, 24, 34),
        (3, 6, 9, 15, 25, 35),
    ]
    base = {ticket: float(index) / 10.0 for index, ticket in enumerate(candidates)}
    before = engine._portfolio_objective(selected, base)
    refined = engine._refine_portfolio(selected, candidates, base)
    after = engine._portfolio_objective(refined, base)
    assert after + 1e-12 >= before
    assert len(refined) == 3
    assert len(set(refined)) == 3
    for index, ticket in enumerate(refined):
        for other in refined[index + 1 :]:
            assert engine.optimizer.overlap(ticket, other) <= 4


def test_local_swap_preserves_fourteen_ticket_configuration():
    engine = ProRecommendationEngine(ProConfig(candidate_count=20, max_tickets=14))
    tickets = [tuple(range(start, start + 6)) for start in range(1, 15)]
    base = {ticket: 1.0 - index * 0.001 for index, ticket in enumerate(tickets)}
    refined = engine._refine_portfolio(tickets, tickets, base)
    assert len(refined) == 14
    assert len(set(refined)) == 14
