"""Run the LREI lottery recommendation engine on real lottery data."""

from __future__ import annotations

from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.statistics import LotteryStatistics


def main() -> None:
    """Load real lottery data and print recommended tickets."""

    root = Path(__file__).resolve().parents[3]

    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    statistics = LotteryStatistics.from_dataset(dataset)

    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=statistics,
        ticket_count=50,
        seed=42,
    )

    print()
    print("=" * 70)
    print("LREI LOTTERY RECOMMENDATIONS")
    print("=" * 70)

    print(f"Dataset draws: {len(dataset)}")
    print(f"Generated tickets: {len(result.generated_tickets)}")
    print(
        f"Recommended tickets: "
        f"{len(result.recommended_tickets)}"
    )

    print()
    print("TOP NUMBER SCORES")
    print("-" * 70)

    for score in result.scores[:10]:
        print(
            f"Number {score.number:>2} | "
            f"Score: {score.score:.6f}"
        )

    print()
    print("STRONG NUMBER SCORES")
    print("-" * 70)

    if result.strong_scores:
        for score in result.strong_scores[:10]:
            print(
                f"Strong {score.number:>2} | "
                f"Score: {score.score:.6f}"
            )
    else:
        print("No strong-number data available.")

    print()
    print("=" * 70)
    print("RECOMMENDED LOTTERY TICKETS")
    print("=" * 70)

    tickets = result.recommended_tickets_with_strong

    if not tickets:
        print("No recommended tickets were generated.")
        return

    for index, ticket in enumerate(tickets[:14], start=1):
        numbers = " - ".join(
            f"{number:02d}"
            for number in sorted(ticket.numbers)
        )

        if ticket.strong_number is not None:
            print(
                f"Ticket {index:02d}: "
                f"{numbers} "
                f"| Strong: {ticket.strong_number}"
            )
        else:
            print(
                f"Ticket {index:02d}: "
                f"{numbers}"
            )

    print("=" * 70)


if __name__ == "__main__":
    main()
