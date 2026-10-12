from pathlib import Path
import random

from lrei.lottery.baseline import RandomBaseline

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.generator import TicketGenerator
from lrei.lottery.optimizer import LotteryOptimizer, OptimizerConfig
from lrei.lottery.predictor import LotteryPredictor


def _load_dataset():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"
    return CsvDatasetLoader().load(data_file)


def _recent_scores(train, window=50):
    recent = train.draws[-window:]

    counts = {}

    for draw in recent:
        for number in draw.numbers:
            counts[number] = counts.get(number, 0) + 1

    if not counts:
        return {}

    maximum = max(counts.values())

    if maximum <= 0:
        return {}

    return {
        number: count / maximum
        for number, count in counts.items()
    }


def _evaluate(tickets, actual_numbers):
    actual = set(actual_numbers)

    best_match = 0
    total_matches = 0

    for ticket in tickets:
        matches = len(set(ticket) & actual)

        best_match = max(best_match, matches)
        total_matches += matches

    return best_match, total_matches


def test_ablation_report():
    dataset = _load_dataset()

    predictor = LotteryPredictor(
        frequency_weight=0.7,
        recency_weight=0.3,
    )

    generator = TicketGenerator()

    optimizer = LotteryOptimizer(
        OptimizerConfig(
            max_overlap=4,
            max_tickets=14,
        )
    )

    ticket_count = 14
    seed_count = 10
    evaluation_window = 500

    start = max(1000, len(dataset) - evaluation_window)
    actual_cases = len(dataset) - start
    assert actual_cases > 0

    results = {
        "random": [],
        "frequency": [],
        "recency": [],
        "optimized": [],
    }

    for seed in range(seed_count):
        totals = {
            "random": 0,
            "frequency": 0,
            "recency": 0,
            "optimized": 0,
        }

        cases = 0

        for split_index in range(
            start,
            len(dataset),
        ):
            train = dataset.__class__(
                dataset.draws[:split_index]
            )

            test_draw = dataset.draws[split_index]

            frequencies = {}

            for draw in train:
                for number in draw.numbers:
                    frequencies[number] = (
                        frequencies.get(number, 0) + 1
                    )

            frequency_scores = (
                predictor.score_numbers(
                    frequencies=frequencies,
                    recency_scores=None,
                )
            )

            recent_scores = _recent_scores(
                train,
                window=50,
            )

            combined_scores = (
                predictor.score_numbers(
                    frequencies=frequencies,
                    recency_scores=recent_scores,
                )
            )

            frequency_rng = random.Random(
                seed * 100000 + split_index
            )

            recency_rng = random.Random(
                seed * 200000 + split_index
            )

            random_rng = random.Random(
                seed * 300000 + split_index
            )

            generated_rng = random.Random(
                seed * 400000 + split_index
            )

            frequency_tickets = [
                generator.generate_ticket(
                    scores=frequency_scores,
                    rng=frequency_rng,
                )
                for _ in range(ticket_count)
            ]

            recency_tickets = [
                generator.generate_ticket(
                    scores=combined_scores,
                    rng=recency_rng,
                )
                for _ in range(ticket_count)
            ]

            random_tickets = RandomBaseline().generate_tickets(
                count=ticket_count, seed=random_rng.getrandbits(64)
            )

            # Equal evaluated budget: let the optimizer select 14 from a
            # disclosed larger pool, rather than score however many survive.
            generated_tickets = [
                generator.generate_ticket(scores=frequency_scores, rng=generated_rng)
                for _ in range(140)
            ]
            optimized_tickets = optimizer.optimize(generated_tickets)
            for portfolio in (frequency_tickets, recency_tickets, random_tickets, optimized_tickets):
                assert len(portfolio) == 14
                assert len(set(portfolio)) == 14

            actual_numbers = test_draw.numbers

            _, frequency_matches = _evaluate(
                frequency_tickets,
                actual_numbers,
            )

            _, recency_matches = _evaluate(
                recency_tickets,
                actual_numbers,
            )

            _, random_matches = _evaluate(
                random_tickets,
                actual_numbers,
            )

            _, optimized_matches = _evaluate(
                optimized_tickets,
                actual_numbers,
            )

            totals["frequency"] += frequency_matches
            totals["recency"] += recency_matches
            totals["random"] += random_matches
            totals["optimized"] += optimized_matches

            cases += 1

        for name in results:
            results[name].append(
                totals[name] / cases
            )

    assert cases == actual_cases

    means = {
        name: sum(values) / len(values)
        for name, values in results.items()
    }

    print()
    print("=" * 65)
    print("LREI ABLATION TEST — FAIR COMPARISON")
    print("=" * 65)
    print(
        f"Evaluation cases per seed: {actual_cases}"
    )
    print(
        f"Tickets per model: {ticket_count}"
    )
    print(
        f"Seeds: {seed_count}"
    )
    print()
    print(
        f"Random baseline:       "
        f"{means['random']:.4f}"
    )
    print(
        f"Frequency only:        "
        f"{means['frequency']:.4f}"
    )
    print(
        f"Frequency + Recency:   "
        f"{means['recency']:.4f}"
    )
    print(
        f"After optimizer:       "
        f"{means['optimized']:.4f}"
    )
    print()
    print(
        f"Frequency vs Random:   "
        f"{means['frequency'] - means['random']:+.4f}"
    )
    print(
        f"Recency vs Frequency:  "
        f"{means['recency'] - means['frequency']:+.4f}"
    )
    print(
        f"Optimizer effect:      "
        f"{means['optimized'] - means['frequency']:+.4f}"
    )
    print("=" * 65)

    assert means["random"] >= 0
    assert means["frequency"] >= 0
    assert means["recency"] >= 0
    assert means["optimized"] >= 0
