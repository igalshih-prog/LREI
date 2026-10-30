"""Published 2018 selection DIRECTION hypotheses as hypothetical weights.

Polin, Ben Isaac & Aharon (2021), doi:10.1017/S193029750000807X:
manual main 7 was most frequent, 37 least; strong 4 and 5 most
frequent, 1 least, with top-of-form vs bottom-of-form effects.
This module has NO access to their 115 million private ticket lines and
DOES NOT import their estimated frequency distribution or fit 2026 data.

The exponential formula and both scenario parameters are invented by
LREI for SENSITIVITY ANALYSIS ONLY. They are not researcher estimates.
RESEARCH ONLY / NO PLAY.
"""

from __future__ import annotations

from math import exp, isfinite
from typing import Any

PUBLICATION_DOI = "10.1017/S193029750000807X"
HISTORICAL_STUDY_YEAR = 2018


def published_direction_sensitivity(
    strength: float, hypothetical_uniformization: float
) -> dict[str, Any]:
    """Produce positive toy weights aligned with *qualitative* 2018 directions.

    strength is a hypothetical 0..3 log-weight contrast. The explicit
    hypothetical_uniformization factor 0..1 shrinks every weight toward
    1 as the factor grows; it is NOT derived from any advertised prize or
    participant count. Real crowd behavior may involve full-combination
    interactions, strong/main dependence, copying, and ticket duplicates.
    """
    for label, value, high in (
        ("strength", strength, 3.0),
        ("hypothetical_uniformization", hypothetical_uniformization, 1.0),
    ):
        if (
            type(value) not in (int, float)
            or not isfinite(value)
            or not 0 <= value <= high
        ):
            raise ValueError(f"{label} must be finite and in [0, {high}]")

    effect = float(strength) * (1.0 - float(hypothetical_uniformization))
    main = [1.0] * 37
    strong = [1.0] * 7

    # The first and last groups are historical form-position directions.
    # The coefficients below are ARBITRARY, not extracted frequencies.
    for number in range(1, 8):
        main[number - 1] = exp(effect / 3)
    for number in range(28, 38):
        main[number - 1] = exp(-effect / 3)
    main[7 - 1] = exp(effect)  # top 7, from published 2018 rank
    main[37 - 1] = exp(-effect)  # bottom 37, from published 2018 rank

    strong[1 - 1] = exp(-effect)
    strong[4 - 1] = exp(effect)
    strong[5 - 1] = exp(effect)

    return {
        "schema_version": 1,
        "status": "published_2018_directions_hypothetical_2026_UNFITTED",
        "historical_publication_doi": PUBLICATION_DOI,
        "historical_study_year": HISTORICAL_STUDY_YEAR,
        "source": "peer_reviewed_publication_qualitative_directions_only",
        "main_weights": main,
        "strong_weights": strong,
        "assumed_log_strength": float(strength),
        "assumed_uniformization": float(hypothetical_uniformization),
        "toy_weight_formula_is_not_publication_model": True,
        "historical_private_ticket_rows_accessed": False,
        "observed_2018_frequency_magnitudes_used": False,
        "observed_2026_frequency_magnitudes_used": False,
        "2026_player_preference_estimated": False,
        "manual_entry_share_verified": False,
        "player_popularity_verified": False,
        "expected_value_verified": False,
        "authorized_for_play": False,
    }
