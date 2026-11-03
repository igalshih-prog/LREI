"""Purely mathematical P3 sample coverage planning tests. No lottery results."""
import copy
import json
from pathlib import Path

import pytest

from lrei.lottery.p3_group_coverage_planner import trajectory, report

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "research/protocols/p3-strong-choice-forward-screen-v1.json"

def frozen_protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))

def test_exact_two_draw_mutually_exclusive_probability():
    # Two ordered ways of seeing one of each of two strong categories.
    curve = trajectory(2, minimum=1)
    assert curve[0] == 0.0 and curve[1] == 0.0
    assert curve[2] == pytest.approx(2 / 49, abs=1e-14)

def test_known_independently_calculated_probability_landmarks():
    curve = trajectory(203)
    for n, probability in [
        (140, .26171399807901224),
        (160, .5829187613078095),
        (180, .8263789910192361),
        (191, .9035767298580568),
        (203, .9526923581967466),
    ]:
        assert curve[n] == pytest.approx(probability, abs=1e-10)
    assert all(a <= b + 1e-12 for a, b in zip(curve, curve[1:]))

@pytest.mark.parametrize("acceptance, minimum", [
    (1.0, 191), (.9, 213), (.8, 240), (.5, 386),
])
def test_exact_90pct_required_draws_under_hypothetical_acceptance(acceptance, minimum):
    result = report(frozen_protocol(), acceptance_rate=acceptance, horizon=500)
    assert result["minimum_scheduled_draws_within_horizon"] == minimum
    assert result["not_statistical_test_power"] is True
    assert result["official_source_verified"] is False
    assert result["prospective_study_completed"] is False
    assert result["financial_value_verified"] is False

def test_no_assumed_source_coverage_fails_without_inventing_draws():
    result = report(frozen_protocol(), acceptance_rate=0, horizon=250)
    assert result["minimum_scheduled_draws_within_horizon"] is None
    assert result["target_reached_within_horizon"] is False
    assert all(value == 0 for value in result["checkpoints"].values())

def test_95pct_threshold_matches_exact_reference():
    assert report(frozen_protocol(), confidence=.95, horizon=220)[
        "minimum_scheduled_draws_within_horizon"
    ] == 203

@pytest.mark.parametrize("invalid", [True, -1, 1.1, float("inf"), float("nan"), "0.9"])
def test_invalid_acceptance_rejected(invalid):
    with pytest.raises(ValueError, match="acceptance rate"):
        trajectory(30, acceptance_rate=invalid)

def test_wrong_protocol_cannot_lower_the_frozen_minimum():
    changed = copy.deepcopy(frozen_protocol())
    changed["primary_descriptive_endpoint"]["group_minimum_unique_draws"] = 2
    with pytest.raises(ValueError, match="protocol"):
        report(changed)
    changed = copy.deepcopy(frozen_protocol())
    changed["protocol_id"] = "other-research"
    with pytest.raises(ValueError, match="protocol"):
        report(changed)

@pytest.mark.parametrize("value", [True, 0, 1, float("nan"), "0.9"])
def test_invalid_confidence_rejected(value):
    with pytest.raises(ValueError, match="confidence"):
        report(frozen_protocol(), confidence=value)

def test_no_draws_or_subminimum_draws_cannot_pass():
    assert trajectory(0) == [0]
    assert trajectory(39)[-1] == 0
