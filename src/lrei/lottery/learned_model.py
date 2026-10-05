"""Small dependency-free walk-forward learned signal model for research."""

from __future__ import annotations

import math
from statistics import mean
from typing import Iterable


def _sigmoid(value: float) -> float:
    value = max(-30.0, min(30.0, value))
    return 1.0 / (1.0 + math.exp(-value))


def _feature_vector(history, number: int, ewma_half_life: float = 36.0) -> tuple[float, ...]:
    draws = list(history.draws)
    n = len(draws)
    recent_window = min(20, n)
    previous_window = min(20, max(1, n - recent_window))

    recent = draws[-recent_window:]
    previous = draws[-recent_window - previous_window:-recent_window] if n > recent_window else ()

    total_rate = sum(number in draw.numbers for draw in draws) / max(1, n)
    recent_rate = sum(number in draw.numbers for draw in recent) / max(1, len(recent))
    previous_rate = sum(number in draw.numbers for draw in previous) / max(1, len(previous))
    momentum = recent_rate - previous_rate

    alpha = 1.0 - math.exp(-math.log(2.0) / ewma_half_life)
    ewma = 0.0
    for draw in draws:
        ewma = (1.0 - alpha) * ewma + alpha * (1.0 if number in draw.numbers else 0.0)

    gap = 0
    for draw in reversed(draws):
        if number in draw.numbers:
            break
        gap += 1
    gap_signal = math.exp(-gap / 20.0)

    return total_rate, recent_rate, momentum, ewma, gap_signal


def _standardize(rows: list[tuple[float, ...]]) -> tuple[list[tuple[float, ...]], tuple[float, ...], tuple[float, ...]]:
    if not rows:
        return [], (), ()
    width = len(rows[0])
    means = tuple(mean(row[i] for row in rows) for i in range(width))
    scales = tuple(
        math.sqrt(mean((row[i] - means[i]) ** 2 for row in rows)) or 1.0
        for i in range(width)
    )
    normalized = [
        tuple((row[i] - means[i]) / scales[i] for i in range(width))
        for row in rows
    ]
    return normalized, means, scales


def _normalize(row: tuple[float, ...], means: tuple[float, ...], scales: tuple[float, ...]) -> tuple[float, ...]:
    return tuple((row[i] - means[i]) / scales[i] for i in range(len(row)))


def _fit_logistic(
    rows: list[tuple[float, ...]],
    labels: list[float],
    *,
    epochs: int = 250,
    learning_rate: float = 0.08,
    l2: float = 1.0,
) -> tuple[float, tuple[float, ...]]:
    if not rows:
        return 0.0, ()
    width = len(rows[0])
    bias = 0.0
    weights = [0.0] * width
    count = float(len(rows))

    for _ in range(epochs):
        grad_bias = 0.0
        grad = [0.0] * width
        for row, label in zip(rows, labels):
            prediction = _sigmoid(bias + sum(w * x for w, x in zip(weights, row)))
            error = prediction - label
            grad_bias += error
            for index, x in enumerate(row):
                grad[index] += error * x
        bias -= learning_rate * grad_bias / count
        for index in range(width):
            grad[index] = grad[index] / count + l2 * weights[index]
            weights[index] -= learning_rate * grad[index]
    return bias, tuple(weights)


def predict_number_scores(
    history,
    *,
    training_draws: int = 120,
    ewma_half_life: float = 36.0,
    shrinkage: float = 0.50,
) -> dict[int, float]:
    """Fit on historical next-draw outcomes and return 0..1 number scores.

    Every training row is built only from history available before its target
    draw, so the method is suitable for chronological walk-forward evaluation.
    """
    draws = list(history.draws)
    if len(draws) < 35:
        return {}

    numbers = sorted({number for draw in draws for number in draw.numbers})
    start = max(20, len(draws) - training_draws)
    rows: list[tuple[float, ...]] = []
    labels: list[float] = []

    for target_index in range(start, len(draws)):
        train_history = type(history)(draws=draws[:target_index])
        target = set(draws[target_index].numbers)
        for number in numbers:
            rows.append(_feature_vector(train_history, number, ewma_half_life))
            labels.append(1.0 if number in target else 0.0)

    normalized_rows, means, scales = _standardize(rows)
    bias, weights = _fit_logistic(normalized_rows, labels)

    raw = {}
    for number in numbers:
        features = _feature_vector(history, number, ewma_half_life)
        normalized = _normalize(features, means, scales)
        raw[number] = _sigmoid(bias + sum(w * x for w, x in zip(weights, normalized)))

    low = min(raw.values())
    high = max(raw.values())
    if high <= low:
        calibrated = {number: 0.5 for number in numbers}
    else:
        calibrated = {number: (value - low) / (high - low) for number, value in raw.items()}

    baseline = {number: 0.5 for number in numbers}
    return {
        number: (1.0 - shrinkage) * baseline[number] + shrinkage * calibrated[number]
        for number in numbers
    }
