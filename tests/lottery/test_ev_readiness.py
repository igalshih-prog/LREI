"""Research-only evidence gate tests, not authentic source attestations."""
from dataclasses import replace

import pytest

from lrei.lottery.ev_readiness import EVReadinessEvidence, assess_ev_readiness


def test_default_missing_sources_fail_closed_without_monetary_output():
    report = assess_ev_readiness(EVReadinessEvidence())
    assert report["status"] == "BLOCKED_MISSING_EVIDENCE"
    assert len(report["missing_requirements"]) == 7
    assert report["monetary_ev_ils"] is None
    assert report["decision"] == "NO PLAY"
    assert report["financial_play_authorized"] is False


@pytest.mark.parametrize("field", list(EVReadinessEvidence.__dataclass_fields__))
def test_each_independent_missing_dependency_prevents_readiness(field):
    all_claims = EVReadinessEvidence(**{
        name: True for name in EVReadinessEvidence.__dataclass_fields__
    })
    report = assess_ev_readiness(replace(all_claims, **{field: False}))
    assert report["missing_requirements"] == [field]
    assert report["monetary_ev_ils"] is None
    assert report["decision"] == "NO PLAY"


def test_even_asserted_prerequisites_are_not_approval_or_proof():
    claimed = EVReadinessEvidence(**{
        name: True for name in EVReadinessEvidence.__dataclass_fields__
    })
    report = assess_ev_readiness(claimed)
    assert report["missing_requirements"] == []
    assert report["status"] == "PREREQUISITES_ASSERTED_REQUIRES_INDEPENDENT_REVIEW"
    assert report["financial_play_authorized"] is False
    assert report["claimed_positive_expected_value"] is False
    assert report["evidence_flags_are_claims_not_automated_source_verification"] is True


@pytest.mark.parametrize("invalid", [None, {}, True, 7])
def test_untyped_evidence_is_rejected(invalid):
    with pytest.raises(ValueError, match="typed EVReadinessEvidence"):
        assess_ev_readiness(invalid)


def test_numeric_truthy_claim_is_not_accepted_as_boolean():
    evidence = replace(EVReadinessEvidence(), tax_rule_verified=1)
    with pytest.raises(ValueError, match="literal booleans"):
        assess_ev_readiness(evidence)
