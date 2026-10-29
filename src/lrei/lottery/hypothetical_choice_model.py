"""An intentionally simplified, mathematically coherent choice-bias scenario.

A manual six-number set S is assigned probability proportional to the
*product* of user-supplied positive number weights for members of S.
This is a modeling ASSUMPTION, not Polin's fitted population distribution;
pair/form/geometric dependencies and strong/main correlations are absent.

The strong number is independently weighted over 1..7. An assumed fraction
of entries may follow this manual law and the rest are uniform machine picks.
No crowd parameters, entry volumes or EV are estimated from source data.
"""

from __future__ import annotations

from math import fsum, isfinite
from typing import Any, Sequence

from .uniform_tier_reference import uniform_tier_probability

_MIN_WEIGHT = 1e-6
_MAX_WEIGHT = 1e6


def _validated_weights(
    weights: Sequence[float], size: int, label: str
) -> list[float]:
    if not isinstance(weights, (list, tuple)) or len(weights) != size:
        raise ValueError(f"{label} must have exactly {size} weights")
    if any(
        type(weight) not in (int, float)
        or not isfinite(weight)
        or not _MIN_WEIGHT <= weight <= _MAX_WEIGHT
        for weight in weights
    ):
        raise ValueError(f"{label} weights must be finite positive numbers")
    return [float(weight) for weight in weights]


def _symmetric_polynomials(weights: Sequence[float]) -> list[float]:
    """Elementary symmetric sums through order six, in O(6 * len(weights))."""
    sums = [1.0] + [0.0] * 6
    for weight in weights:
        for k in range(6, 0, -1):
            sums[k] += weight * sums[k - 1]
    return sums


def hypothetical_manual_match_profile(
    main_weights: Sequence[float],
    strong_weights: Sequence[float],
    winning_main: Sequence[int],
    winning_strong: int,
) -> dict[str, dict[str, float]]:
    """Return a normalized 14-cell match profile under *assumed* weights.

    Exactly k main matches for k=0..6, with/without strong. These are
    probabilities of a *player-chosen entry* matching the FIXED draw, not
    probabilities of any upcoming balls being drawn.
    """
    main = _validated_weights(main_weights, 37, "main")
    power = _validated_weights(strong_weights, 7, "strong")
    if (
        not isinstance(winning_main, (list, tuple))
        or len(winning_main) != 6
        or any(type(n) is not int or not 1 <= n <= 37 for n in winning_main)
        or len(set(winning_main)) != 6
    ):
        raise ValueError("winning_main must be six distinct integers 1..37")
    if type(winning_strong) is not int or not 1 <= winning_strong <= 7:
        raise ValueError("winning_strong must be an integer 1..7")
    win = set(winning_main)
    win_e = _symmetric_polynomials([main[n - 1] for n in win])
    lose_e = _symmetric_polynomials(
        [main[n - 1] for n in range(1, 38) if n not in win]
    )
    denominator = _symmetric_polynomials(main)[6]
    strong_hit = power[winning_strong - 1] / fsum(power)
    results: dict[str, dict[str, float]] = {}
    for k in range(7):
        main_hit_probability = win_e[k] * lose_e[6 - k] / denominator
        results[str(k)] = {
            "strong": main_hit_probability * strong_hit,
            "without_strong": main_hit_probability * (1 - strong_hit),
        }
    return results


def hypothetical_player_mix_profile(
    main_weights: Sequence[float],
    strong_weights: Sequence[float],
    winning_main: Sequence[int],
    winning_strong: int,
    assumed_manual_fraction_all_entries: float,
) -> dict[str, Any]:
    """Convex mix of uniform and hypothetical product-weighted manual entry laws.

    Unlike the k-match stratum share in conditional_strong_audit, this
    fraction f is assumed across ALL entries; it remains unidentifiable
    from published winner counts alone.
    """
    fraction = assumed_manual_fraction_all_entries
    if (
        type(fraction) not in (int, float)
        or not isfinite(fraction)
        or not 0 <= fraction <= 1
    ):
        raise ValueError("assumed manual fraction must be finite in [0,1]")
    manual = hypothetical_manual_match_profile(
        main_weights, strong_weights, winning_main, winning_strong
    )
    cells: dict[str, dict[str, float]] = {}
    for k in range(7):
        manual_k = manual[str(k)]
        cells[str(k)] = {
            "strong": (
                fraction * manual_k["strong"]
                + (1 - fraction) * uniform_tier_probability(k, True)
            ),
            "without_strong": (
                fraction * manual_k["without_strong"]
                + (1 - fraction) * uniform_tier_probability(k, False)
            ),
        }
    return {
        "status": "hypothetical_player_behavior_sensitivity_only",
        "assumed_manual_fraction_all_entries": float(fraction),
        "tier_probability_profile": cells,
        "source_data_used_for_fitting": False,
        "manual_entry_share_verified": False,
        "manual_selection_distribution_verified": False,
        "player_popularity_verified": False,
        "total_entries_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }
