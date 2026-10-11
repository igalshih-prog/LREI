"""Statistical utilities for chronological lottery-model evaluation."""

from __future__ import annotations

import math
import random
from statistics import mean
from typing import Sequence


def paired_block_bootstrap_ci(
    paired_differences: Sequence[float],
    *,
    block_size: int = 5,
    samples: int = 5000,
    confidence: float = 0.95,
    seed: int = 20261011,
) -> tuple[float, float]:
    """Return a moving-block bootstrap CI for the mean paired difference.

    The differences must be ordered chronologically and contain one already-
    paired difference per target draw (candidate minus baseline). Consecutive
    blocks preserve short-range dependence better than resampling each draw
    independently. For non-contiguous validation origins, call this separately
    per origin or combine origin-level summaries instead.
    """
    values = tuple(float(value) for value in paired_differences)
    if not values:
        raise ValueError("paired_differences must not be empty")
    if block_size < 1:
        raise ValueError("block_size must be positive")
    if samples < 1:
        raise ValueError("samples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("paired_differences must contain only finite values")

    size = len(values)
    block = min(block_size, size)
    last_start = size - block
    rng = random.Random(seed)
    estimates: list[float] = []

    for _ in range(samples):
        resampled: list[float] = []
        while len(resampled) < size:
            start = rng.randint(0, last_start)
            resampled.extend(values[start : start + block])
        estimates.append(mean(resampled[:size]))

    estimates.sort()
    tail = (1.0 - confidence) / 2.0
    lower_index = int(tail * (samples - 1))
    upper_index = int((1.0 - tail) * (samples - 1))
    return estimates[lower_index], estimates[upper_index]
