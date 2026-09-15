from lrei.lottery.dataset import LotteryDataset, LotteryDrawRecord
from lrei.lottery.pro import ProRecommendationEngine


def make_dataset() -> LotteryDataset:
    draws = []
    for index in range(80):
        year = 2016 + (index // 12)
        month = (index % 12) + 1
        draws.append(
            LotteryDrawRecord(
                draw_id=f"draw-{index:03d}",
                numbers=tuple(
                    ((index + offset * 3) % 37) + 1
                    for offset in range(6)
                ),
                date=f"{year:04d}-{month:02d}-15",
                strong_number=(index % 7) + 1,
            )
        )
    return LotteryDataset(draws)


def test_pro_returns_14_valid_tickets():
    result = ProRecommendationEngine().recommend(
        dataset=make_dataset(),
        seed=42,
    )

    assert len(result.recommended_tickets) == 14
    for ticket in result.recommended_tickets:
        assert len(ticket) == 6
        assert len(set(ticket)) == 6
        assert ticket == tuple(sorted(ticket))
        assert all(1 <= number <= 37 for number in ticket)


def test_pro_respects_overlap_limit():
    result = ProRecommendationEngine().recommend(
        dataset=make_dataset(),
        seed=42,
    )

    tickets = result.recommended_tickets
    for index, first in enumerate(tickets):
        for second in tickets[index + 1 :]:
            assert len(set(first) & set(second)) <= 4


def test_pro_is_reproducible():
    dataset = make_dataset()
    first = ProRecommendationEngine().recommend(
        dataset=dataset,
        seed=12345,
    )
    second = ProRecommendationEngine().recommend(
        dataset=dataset,
        seed=12345,
    )

    assert first.scores == second.scores
    assert first.generated_tickets == second.generated_tickets
    assert first.recommended_tickets == second.recommended_tickets


def test_pro_date_window_uses_calendar_years():
    dataset = LotteryDataset(
        [
            LotteryDrawRecord(
                draw_id="old",
                numbers=(1, 2, 3, 4, 5, 6),
                date="2021-01-01",
            ),
            LotteryDrawRecord(
                draw_id="recent-3",
                numbers=(7, 8, 9, 10, 11, 12),
                date="2023-07-01",
            ),
            LotteryDrawRecord(
                draw_id="recent-1",
                numbers=(13, 14, 15, 16, 17, 18),
                date="2025-07-01",
            ),
            LotteryDrawRecord(
                draw_id="latest",
                numbers=(19, 20, 21, 22, 23, 24),
                date="2026-07-01",
            ),
        ]
    )

    engine = ProRecommendationEngine()
    three_year = engine._window_frequency(dataset, years=3)
    one_year = engine._window_frequency(dataset, years=1)

    assert 1 not in three_year
    assert 7 in three_year
    assert 13 in three_year
    assert 19 in three_year

    assert 7 not in one_year
    assert 13 in one_year
    assert 19 in one_year
