"""Regression checks for secondary-only Lotto aggregate figures."""

import copy
import json
from pathlib import Path

import pytest

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.prize_data import PrizeDataError
from lrei.lottery.prize_aggregate_crosscheck import (
    audit_secondary_aggregate_files, compare_unverified_aggregate_sources,
)

ROOT = Path(__file__).resolve().parents[2]
CROSSCHECK = ROOT / "data" / "prize_leads" / "lotto_only_aggregate_crosscheck_3955_3958.json"
LEADS = ROOT / "data" / "prize_leads" / "pending_3955_3968.json"
HISTORY = ROOT / "data" / "lottery.csv"


def archive():
    return CsvDatasetLoader().load(HISTORY)


def inputs():
    return (json.loads(CROSSCHECK.read_text(encoding="utf-8")),
            json.loads(LEADS.read_text(encoding="utf-8")))


def test_four_secondary_summaries_have_paired_aggregates_but_no_paid_tier_rows():
    result = audit_secondary_aggregate_files(CROSSCHECK, LEADS, archive())
    assert result["compared_draws"] == 4
    assert [d["draw_id"] for d in result["summary"]] == list(range(3955, 3959))
    assert [d["secondary_lotto_only_total_ils"] for d in result["summary"]] == [
        4496223, 20428062, 13995056, 5981873
    ]
    assert [d["unexplained_source_total_difference_ils"] for d in result["summary"]] == [
        452305, 474645, 600835, 540075
    ]
    assert result["eligible_for_prize_observation"] is False
    assert result["eligible_for_expected_value"] is False
    assert result["source_authenticity_verified"] is False
    assert result["missing_eight_tier_tables_still"] == list(range(3955, 3969))
    assert result["must_not_label_residual_as_extra_tax_or_profit"] is True
    assert all(d["regular_eight_tier_table"] is None
               and d["double_eight_tier_table"] is None
               and d["operator_verified"] is False
               for d in result["summary"])


@pytest.mark.parametrize("mutator,reason", [
    (lambda c, l: c["reported_lotto_only_total_for_draws"].pop(), "four distinct"),
    (lambda c, l: c["reported_lotto_only_total_for_draws"][1].update(draw_id=3955), "consecutive"),
    (lambda c, l: c["reported_lotto_only_total_for_draws"][0].update(draw_id=True), "consecutive"),
    (lambda c, l: c["reported_lotto_only_total_for_draws"][0].update(draw_date="2026-08-14"), "draw date"),
    (lambda c, l: c["reported_lotto_only_total_for_draws"][0].update(reported_lotto_only_ils=-5), "positive"),
    (lambda c, l: c["reported_lotto_only_total_for_draws"][0].update(reported_lotto_only_ils=7000000), "negative"),
    (lambda c, l: c.update(source_url="https://www.pais.co.il/"), "third party"),
    (lambda c, l: c.update(source_status="official"), "third party"),
    (lambda c, l: c.update(raw_source_sha256="fake"), "no archive"),
    (lambda c, l: c.update(raw_source_archived=True), "no archive"),
    (lambda c, l: c.update(authoritative_protocol_verified=True), "no archive"),
    (lambda c, l: c.update(eight_tier_tables_available=True), "no archive"),
    (lambda c, l: c.update(purpose="approved_for_EV"), "secondary research"),
    (lambda c, l: c["reported_lotto_only_total_for_draws"][0].update(synthetic_per_tier_winners=15), "fields"),
    (lambda c, l: l["draws"][0].update(approved_protocol_verified=True), "MUST NOT claim"),
])
def test_secondary_accounting_never_upgraded_to_official(mutator, reason):
    crosscheck, leads = inputs()
    mutator(crosscheck, leads)
    with pytest.raises(PrizeDataError, match=reason):
        compare_unverified_aggregate_sources(crosscheck, leads, archive())
