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
    return paired_origin_block_bootstrap_ci(
        [paired_differences], block_size=block_size, samples=samples,
        confidence=confidence, seed=seed,
    )


def paired_origin_block_bootstrap_ci(
    differences_by_origin: Sequence[Sequence[float]],
    *,
    block_size: int = 5,
    samples: int = 5000,
    confidence: float = 0.95,
    seed: int = 20261011,
) -> tuple[float, float]:
    """Bootstrap within each chronological origin without bridging time gaps.

    Preserve each origin's observed draw count and report the draw-weighted
    pooled mean interval. This is conditional on these development origins;
    it does not quantify generalization to new origins or future draws.
    """
    origins = tuple(tuple(float(value) for value in origin) for origin in differences_by_origin)
    if not origins or any(not origin for origin in origins):
        raise ValueError("paired_differences must not be empty in any origin")
    if block_size < 1:
        raise ValueError("block_size must be positive")
    if samples < 1:
        raise ValueError("samples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if any(not math.isfinite(value) for origin in origins for value in origin):
        raise ValueError("paired_differences must contain only finite values")

    rng = random.Random(seed)
    estimates: list[float] = []

    for _ in range(samples):
        resampled: list[float] = []
        for values in origins:
            size = len(values)
            block = min(block_size, size)
            origin_sample: list[float] = []
            while len(origin_sample) < size:
                start = rng.randint(0, size - block)
                origin_sample.extend(values[start : start + block])
            resampled.extend(origin_sample[:size])
        estimates.append(mean(resampled))

    estimates.sort()
    tail = (1.0 - confidence) / 2.0
    lower_index = int(tail * (samples - 1))
    upper_index = int((1.0 - tail) * (samples - 1))
    return estimates[lower_index], estimates[upper_index]
