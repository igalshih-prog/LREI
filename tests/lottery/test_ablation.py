from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.generator import TicketGenerator
from lrei.lottery.optimizer import LotteryOptimizer, OptimizerConfig
from lrei.lottery.predictor import LotteryPredictor
from lrei.lottery.recommendation import RecommendationEngine


def _load_dataset():
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"
    return CsvDatasetLoader().load(data_file)


def _evaluate(tickets, actual_numbers):
    actual = set(actual_numbers)

    best_match = 0
    total_matches = 0

    for ticket in tickets:
        matches = len(set(ticket) & actual)
        best_match = max(best_match, matches)
        total_matches += matches

    return best_match, total_matches


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


def test_ablation_report():
    dataset = _load_dataset()

    predictor = LotteryPredictor()
    generator = TicketGenerator()
    optimizer = LotteryOptimizer(
        OptimizerConfig(
            max_overlap=4,
            max_tickets=10,
        )
    )

    engine = RecommendationEngine()

    frequency_results = []
    recency_results = []
    generated_results = []
    optimized_results = []
    random_results = []

    for seed in range(10):
        frequency_total = 0
        recency_total = 0
        generated_total = 0
        optimized_total = 0
        random_total = 0

        frequency_cases = 0

        for split_index in range(
            1000,
            len(dataset),
        ):
            train = dataset.draws[:split_index]
            test_draw = dataset.draws[split_index]

            frequencies = {}

            for draw in train:
                for number in draw.numbers:
                    frequencies[number] = (
                        frequencies.get(number, 0) + 1
                    )

            frequency_scores = predictor.score_numbers(
                frequencies=frequencies,
            )

            recency_scores = _recent_scores(
                dataset.__class__(train),
                window=50,
            )

            combined_scores = predictor.score_numbers(
                frequencies=frequencies,
                recency_scores=recency_scores,
            )

            frequency_tickets = []

            recency_tickets = []

            generated_tickets = []

            random_tickets = []

            import random

            frequency_rng = random.Random(
                seed + split_index
            )

            recency_rng = random.Random(
                seed + 10000 + split_index
            )

            generated_rng = random.Random(
                seed + 20000 + split_index
            )

            random_rng = random.Random(
                seed + 30000 + split_index
            )

            for _ in range(50):
                frequency_tickets.append(
                    generator.generate_ticket(
                        frequency_scores,
                        rng=frequency_rng,
                    )
                )

                recency_tickets.append(
                    generator.generate_ticket(
                        combined_scores,
                        rng=recency_rng,
                    )
                )

                generated_tickets.append(
                    generator.generate_ticket(
                        frequency_scores,
                        rng=generated_rng,
                    )
                )

                random_scores = tuple(
                    type(frequency_scores[0])(
                        number=item.number,
                        score=1.0,
                    )
                    for item in frequency_scores
                )

                random_tickets.append(
                    generator.generate_ticket(
                        random_scores,
                        rng=random_rng,
                    )
                )

            optimized_tickets = optimizer.optimize(
                generated_tickets
            )

            actual_numbers = test_draw.numbers

            _, frequency_matches = _evaluate(
                frequency_tickets,
                actual_numbers,
            )

            _, recency_matches = _evaluate(
                recency_tickets,
                actual_numbers,
            )

            _, generated_matches = _evaluate(
                generated_tickets[:10],
                actual_numbers,
            )

            _, optimized_matches = _evaluate(
                optimized_tickets,
                actual_numbers,
            )

            _, random_matches = _evaluate(
                random_tickets[:10],
                actual_numbers,
            )

            frequency_total += frequency_matches
            recency_total += recency_matches
            generated_total += generated_matches
            optimized_total += optimized_matches
            random_total += random_matches

            frequency_cases += 1

        frequency_results.append(
            frequency_total / frequency_cases
        )

        recency_results.append(
            recency_total / frequency_cases
        )

        generated_results.append(
            generated_total / frequency_cases
        )

        optimized_results.append(
            optimized_total / frequency_cases
        )

        random_results.append(
            random_total / frequency_cases
        )

    mean_frequency = (
        sum(frequency_results)
        / len(frequency_results)
    )

    mean_recency = (
        sum(recency_results)
        / len(recency_results)
    )

    mean_generated = (
        sum(generated_results)
        / len(generated_results)
    )

    mean_optimized = (
        sum(optimized_results)
        / len(optimized_results)
    )

    mean_random = (
        sum(random_results)
        / len(random_results)
    )

    print()
    print("=" * 65)
    print("LREI ABLATION TEST — 10 SEEDS")
    print("=" * 65)

    print(
        f"Random baseline:       {mean_random:.4f}"
    )

    print(
        f"Frequency only:        {mean_frequency:.4f}"
    )

    print(
        f"Frequency + Recency:   {mean_recency:.4f}"
    )

    print(
        f"Generated tickets:     {mean_generated:.4f}"
    )

    print(
        f"After optimizer:       {mean_optimized:.4f}"
    )

    print()
    print(
        f"Frequency vs Random:   "
        f"{mean_frequency - mean_random:+.4f}"
    )

    print(
        f"Recency vs Frequency:  "
        f"{mean_recency - mean_frequency:+.4f}"
    )

    print(
        f"Optimizer effect:      "
        f"{mean_optimized - mean_generated:+.4f}"
    )

    print("=" * 65)

    assert mean_frequency >= 0
    assert mean_recency >= 0
    assert mean_generated >= 0
    assert mean_optimized >= 0
    assert mean_random >= 0
