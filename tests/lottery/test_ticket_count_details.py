from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_ticket_count_details():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    backtester = LotteryBacktester()

    ticket_counts = (10, 20, 50, 100)

    print()
    print("=" * 70)
    print("LREI TICKET COUNT DETAILS")
    print("=" * 70)

    for ticket_count in ticket_counts:
        result = backtester.run(
            dataset=dataset,
            train_size=1000,
            test_size=1,
            ticket_count=ticket_count,
            seed=42,
        )

        generated_counts = [
            case.generated_ticket_count
            for case in result.cases
        ]

        recommended_counts = [
            case.recommended_ticket_count
            for case in result.cases
        ]

        print()
        print(f"REQUESTED TICKETS: {ticket_count}")
        print(
            f"Generated tickets per case: "
            f"min={min(generated_counts)}, "
            f"max={max(generated_counts)}, "
            f"average={sum(generated_counts) / len(generated_counts):.2f}"
        )
        print(
            f"Recommended tickets per case: "
            f"min={min(recommended_counts)}, "
            f"max={max(recommended_counts)}, "
            f"average={sum(recommended_counts) / len(recommended_counts):.2f}"
        )
        print(
            f"LREI average matches: "
            f"{result.average_matches:.4f}"
        )
        print(
            f"Random average matches: "
            f"{result.baseline_average_matches:.4f}"
        )
        print("-" * 70)

        assert min(generated_counts) == ticket_count
        assert max(generated_counts) == ticket_count
        assert min(recommended_counts) > 0
        assert max(recommended_counts) <= ticket_count

    print()
    print("=" * 70)
