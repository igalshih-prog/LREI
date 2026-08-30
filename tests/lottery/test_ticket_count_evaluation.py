from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_ticket_count_evaluation():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    backtester = LotteryBacktester()

    ticket_counts = (10, 20, 50, 100)
    seeds = range(10)

    print()
    print("=" * 70)
    print("LREI TICKET COUNT EVALUATION")
    print("=" * 70)
    print(f"Dataset draws: {len(dataset)}")
    print(f"Seeds per ticket count: {len(seeds)}")
    print()

    results = []

    for ticket_count in ticket_counts:
        lrei_averages = []
        baseline_averages = []

        for seed in seeds:
            result = backtester.run(
                dataset=dataset,
                train_size=1000,
                test_size=1,
                ticket_count=ticket_count,
                seed=seed,
            )

            lrei_averages.append(result.average_matches)

            baseline_averages.append(
                result.baseline_average_matches
            )

        lrei_average = (
            sum(lrei_averages)
            / len(lrei_averages)
        )

        baseline_average = (
            sum(baseline_averages)
            / len(baseline_averages)
        )

        advantage = (
            lrei_average
            - baseline_average
        )

        results.append(
            (
                ticket_count,
                lrei_average,
                baseline_average,
                advantage,
            )
        )

        print(f"TICKETS PER MODEL: {ticket_count}")
        print(
            f"LREI average:   "
            f"{lrei_average:.4f}"
        )
        print(
            f"Random average: "
            f"{baseline_average:.4f}"
        )
        print(
            f"LREI advantage: "
            f"{advantage:+.4f}"
        )
        print("-" * 70)

    print()
    print("FINAL SUMMARY")
    print("=" * 70)

    for (
        ticket_count,
        lrei_average,
        baseline_average,
        advantage,
    ) in results:
        print(
            f"{ticket_count:>3} tickets | "
            f"LREI={lrei_average:.4f} | "
            f"Random={baseline_average:.4f} | "
            f"Diff={advantage:+.4f}"
        )

    print("=" * 70)

    assert len(results) == 4

    for (
        ticket_count,
        lrei_average,
        baseline_average,
        advantage,
    ) in results:
        assert ticket_count > 0
        assert lrei_average >= 0.0
        assert baseline_average >= 0.0
