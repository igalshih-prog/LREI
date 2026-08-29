from pathlib import Path

from lrei.lottery.backtesting import LotteryBacktester
from lrei.lottery.dataset import CsvDatasetLoader


def test_multi_seed_evaluation():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)

    backtester = LotteryBacktester()

    seeds = range(10)

    lrei_averages = []
    baseline_averages = []

    for seed in seeds:
        result = backtester.run(
            dataset=dataset,
            train_size=1000,
            test_size=1,
            ticket_count=50,
            seed=seed,
        )

        lrei_averages.append(
            result.average_matches
        )

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

    print()
    print("=" * 65)
    print("LREI MULTI-SEED EVALUATION")
    print("=" * 65)
    print(f"Dataset draws: {len(dataset)}")
    print(f"Seeds tested: {len(seeds)}")
    print(f"Tickets per model: 50")
    print()

    print("LREI")
    print(f"Average matches: {lrei_average:.4f}")
    print()

    print("RANDOM BASELINE")
    print(f"Average matches: {baseline_average:.4f}")
    print()

    print("COMPARISON")
    print(f"LREI advantage: {advantage:+.4f}")
    print("=" * 65)

    assert len(lrei_averages) == 10
    assert len(baseline_averages) == 10
    assert lrei_average >= 0.0
    assert baseline_average >= 0.0
