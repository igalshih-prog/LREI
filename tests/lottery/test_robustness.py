from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_backtest_robustness_across_seeds():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    backtester = LotteryBacktester()

    lrei_averages = []
    baseline_averages = []
    lrei_totals = []
    baseline_totals = []
    lrei_best_matches = []
    baseline_best_matches = []

    for seed in range(10):
        result = backtester.run(
            dataset=dataset,
            train_size=1000,
            test_size=1,
            ticket_count=50,
            seed=seed,
        )

        lrei_averages.append(result.average_matches)
        baseline_averages.append(
            result.baseline_average_matches
        )

        lrei_totals.append(result.total_matches)
        baseline_totals.append(
            result.baseline_total_matches
        )

        lrei_best_matches.append(result.best_match)
        baseline_best_matches.append(
            result.baseline_best_match
        )

    mean_lrei = sum(lrei_averages) / len(lrei_averages)
    mean_baseline = (
        sum(baseline_averages)
        / len(baseline_averages)
    )

    average_difference = mean_lrei - mean_baseline

    lrei_wins = sum(
        l > b
        for l, b in zip(
            lrei_averages,
            baseline_averages,
        )
    )

    baseline_wins = sum(
        b > l
        for l, b in zip(
            lrei_averages,
            baseline_averages,
        )
    )

    ties = 10 - lrei_wins - baseline_wins

    print()
    print("=" * 60)
    print("LREI ROBUSTNESS TEST — 10 SEEDS")
    print("=" * 60)

    for index, seed in enumerate(range(10)):
        print(
            f"Seed {seed}: "
            f"LREI={lrei_averages[index]:.4f} | "
            f"Random={baseline_averages[index]:.4f} | "
            f"Diff="
            f"{lrei_averages[index] - baseline_averages[index]:+.4f}"
        )

    print()
    print(f"Mean LREI average: {mean_lrei:.4f}")
    print(
        f"Mean Random average: "
        f"{mean_baseline:.4f}"
    )
    print(
        f"Mean difference: "
        f"{average_difference:+.4f}"
    )

    print()
    print(f"LREI wins: {lrei_wins}/10")
    print(f"Random wins: {baseline_wins}/10")
    print(f"Ties: {ties}/10")

    print()
    print(
        f"Best LREI match: "
        f"{max(lrei_best_matches)}"
    )
    print(
        f"Best Random match: "
        f"{max(baseline_best_matches)}"
    )

    print("=" * 60)

    assert len(lrei_averages) == 10
    assert len(baseline_averages) == 10
    assert all(value >= 0 for value in lrei_averages)
    assert all(
        value >= 0
        for value in baseline_averages
    )
