from lrei.lottery.dataset import LotteryDataset, LotteryDrawRecord
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.selection import TicketSelector
from lrei.lottery.statistics import LotteryStatistics


def make_dataset() -> LotteryDataset:
    return LotteryDataset(
        [
            LotteryDrawRecord(
                draw_id="draw-001",
                numbers=(1, 2, 3, 4, 5, 6),
            ),
            LotteryDrawRecord(
                draw_id="draw-002",
                numbers=(1, 2, 3, 7, 8, 9),
            ),
            LotteryDrawRecord(
                draw_id="draw-003",
                numbers=(1, 2, 4, 10, 11, 12),
            ),
            LotteryDrawRecord(
                draw_id="draw-004",
                numbers=(2, 3, 5, 13, 14, 15),
            ),
            LotteryDrawRecord(
                draw_id="draw-005",
                numbers=(1, 4, 6, 16, 17, 18),
            ),
        ]
    )


def test_full_lottery_pipeline():
    dataset = make_dataset()

    statistics = LotteryStatistics.from_dataset(dataset)

    assert statistics.draw_count == 5
    assert statistics.total_numbers == 30

    engine = RecommendationEngine()

    recommendations = engine.recommend(
        statistics=statistics,
        ticket_count=30,
        seed=42,
    )

    assert recommendations.scores
    assert len(recommendations.generated_tickets) == 30
    assert recommendations.recommended_tickets

    selector = TicketSelector()

    final_result = selector.select(
        recommendations.recommended_tickets
    )

    assert final_result.tickets

    for ticket in final_result.tickets:
        assert len(ticket) == 6
        assert len(set(ticket)) == 6
        assert ticket == tuple(sorted(ticket))
        assert all(1 <= number <= 37 for number in ticket)


def test_full_pipeline_is_reproducible():
    dataset = make_dataset()
    statistics = LotteryStatistics.from_dataset(dataset)

    engine = RecommendationEngine()

    first = engine.recommend(
        statistics=statistics,
        ticket_count=30,
        seed=123,
    )

    second = engine.recommend(
        statistics=statistics,
        ticket_count=30,
        seed=123,
    )

    assert first.scores == second.scores
    assert first.generated_tickets == second.generated_tickets
    assert first.recommended_tickets == second.recommended_tickets
