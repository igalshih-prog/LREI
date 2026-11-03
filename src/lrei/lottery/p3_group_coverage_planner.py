"""Exact hypothetical P3 group coverage for independently selected strong values."""
from __future__ import annotations
import argparse
import json
from math import isfinite
from pathlib import Path

def trajectory(horizon: int, minimum: int = 20, acceptance_rate: float = 1.0) -> list[float]:
    """P(two mutually exclusive strong categories each have >= minimum accepted draws)."""
    if type(horizon) is not int or not 0 <= horizon <= 5000:
        raise ValueError("horizon must be an integer in 0..5000")
    if type(minimum) is not int or not 1 <= minimum <= 100:
        raise ValueError("minimum must be an integer in 1..100")
    if (isinstance(acceptance_rate, bool) or not isinstance(acceptance_rate, (int, float))
            or not isfinite(acceptance_rate) or not 0 <= acceptance_rate <= 1):
        raise ValueError("acceptance rate must be a finite fraction in 0..1")
    p = acceptance_rate / 7
    other = 1 - 2 * p
    states = [[0.0] * (minimum + 1) for _ in range(minimum + 1)]
    states[0][0] = 1.0
    curve = [0.0]
    for _ in range(horizon):
        new = [[0.0] * (minimum + 1) for _ in range(minimum + 1)]
        for i, row in enumerate(states):
            for j, mass in enumerate(row):
                if mass:
                    new[i][j] += mass * other
                    new[min(i + 1, minimum)][j] += mass * p
                    new[i][min(j + 1, minimum)] += mass * p
        states = new
        curve.append(min(1.0, max(0.0, states[minimum][minimum])))
    return curve

def report(protocol: dict, acceptance_rate: float = 1.0,
           confidence: float = .9, horizon: int = 600) -> dict:
    endpoint = protocol.get("primary_descriptive_endpoint", {})
    if (protocol.get("protocol_id") != "p3-strong-choice-forward-screen-v1"
            or endpoint.get("drawn_strong_comparison") != [4, 1]
            or endpoint.get("group_minimum_unique_draws") != 20):
        raise ValueError("Unexpected frozen P3 protocol")
    if (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
            or not isfinite(confidence) or not 0 < confidence < 1):
        raise ValueError("confidence must be strictly between zero and one")
    curve = trajectory(horizon, 20, acceptance_rate)
    count = next((n for n, p in enumerate(curve) if p >= confidence), None)
    return {
        "status": "hypothetical_group_coverage_research_only",
        "assumed_acceptance_rate": acceptance_rate,
        "target_probability": confidence,
        "minimum_scheduled_draws_within_horizon": count,
        "target_reached_within_horizon": count is not None,
        "checkpoints": {str(n): curve[n] for n in (140, 160, 180, 191, 203) if n <= horizon},
        "assumes_uniform_independent_physical_draws": True,
        "assumes_independent_source_acceptance": True,
        "not_statistical_test_power": True,
        "official_source_verified": False,
        "prospective_study_completed": False,
        "financial_value_verified": False,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="P3 hypothetical research sample coverage")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--acceptance-rate", type=float, default=1.0)
    parser.add_argument("--confidence", type=float, default=.9)
    parser.add_argument("--horizon", type=int, default=600)
    args = parser.parse_args()
    try:
        result = report(json.loads(args.protocol.read_text(encoding="utf-8")),
                        args.acceptance_rate, args.confidence, args.horizon)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
