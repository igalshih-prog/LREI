"""Export lottery recommendation results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .recommendation import RecommendationResult


def export_recommendations(
    result: RecommendationResult,
    output_path: Path,
) -> Path:
    """Export recommendation results to a JSON file."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "generated_ticket_count": len(
            result.generated_tickets
        ),
        "recommended_ticket_count": len(
            result.recommended_tickets
        ),
        "recommended_tickets": [
            {
                "numbers": list(ticket.numbers),
                "strong_number": ticket.strong_number,
            }
            for ticket in result.recommended_tickets_with_strong
        ],
        "top_number_scores": [
            {
                "number": score.number,
                "score": score.score,
            }
            for score in result.scores[:10]
        ],
        "strong_number_scores": [
            {
                "number": score.number,
                "score": score.score,
            }
            for score in result.strong_scores[:10]
        ],
    }

    if not result.recommended_tickets_with_strong:
        payload["recommended_tickets"] = [
            {
                "numbers": list(ticket),
                "strong_number": None,
            }
            for ticket in result.recommended_tickets
        ]

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path
