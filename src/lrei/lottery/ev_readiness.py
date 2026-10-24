"""Fail-closed research gate for any monetary expected-value calculation.

This gate does NOT evaluate ticket profits or independently authenticate sources.
It requires separately reviewed current draw provenance, full prize coverage,
game rules, ticket costs, tax and prize-sharing inputs before EV is attempted.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EVReadinessEvidence:
    operator_draw_source_verified: bool = False
    draw_freshness_verified: bool = False
    operator_prize_tiers_verified: bool = False
    all_eight_tiers_regular_and_double: bool = False
    ticket_cost_rule_verified: bool = False
    tax_rule_verified: bool = False
    co_winner_model_validated: bool = False


def assess_ev_readiness(evidence: EVReadinessEvidence) -> dict:
    """Return explicit missing requirements and NO PLAY; never infer profits."""
    if type(evidence) is not EVReadinessEvidence:
        raise ValueError("typed EVReadinessEvidence required")
    fields = (
        "operator_draw_source_verified",
        "draw_freshness_verified",
        "operator_prize_tiers_verified",
        "all_eight_tiers_regular_and_double",
        "ticket_cost_rule_verified",
        "tax_rule_verified",
        "co_winner_model_validated",
    )
    if any(type(getattr(evidence, field)) is not bool for field in fields):
        raise ValueError("EV evidence flags must be literal booleans")
    missing = [field for field in fields if not getattr(evidence, field)]
    return {
        "schema_version": 1,
        "status": "BLOCKED_MISSING_EVIDENCE" if missing else "PREREQUISITES_ASSERTED_REQUIRES_INDEPENDENT_REVIEW",
        "missing_requirements": missing,
        "evidence_flags_are_claims_not_automated_source_verification": True,
        "monetary_ev_ils": None,
        "claimed_positive_expected_value": False,
        "financial_play_authorized": False,
        "decision": "NO PLAY",
    }
