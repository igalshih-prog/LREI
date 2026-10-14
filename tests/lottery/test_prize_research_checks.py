"""Evidence separation: official special rules vs THIRD-PARTY partial leads."""

import copy
import json
from pathlib import Path

import pytest

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.prize_data import PrizeDataError
from lrei.lottery.prize_research_checks import (
    load_secondary_leads, load_special_rule_notice,
    validate_secondary_leads, validate_special_rule_notice,
)

ROOT = Path(__file__).resolve().parents[2]
LEADS = ROOT / "data" / "prize_leads" / "pending_3955_3968.json"
RULE = ROOT / "data" / "prize_rule_notices" / "3953.json"
OBSERVATION = ROOT / "data" / "prize_observations" / "3953.json"


def history():
    return CsvDatasetLoader().load(ROOT / "data" / "lottery.csv")


def leads():
    return json.loads(LEADS.read_text(encoding="utf-8"))


def rule():
    return json.loads(RULE.read_text(encoding="utf-8"))


def observation():
    return json.loads(OBSERVATION.read_text(encoding="utf-8"))


def test_exactly_14_missing_draws_researched_but_not_verified():
    report = load_secondary_leads(LEADS, history())
    assert report["secondary_lead_count"] == 14
    assert report["operator_verified_count"] == 0
    assert report["missing_operator_prize_tier_draw_ids"] == list(range(3955, 3969))
    assert report["source_raw_bytes_available"] is False
    assert report["secondary_monetary_values_are_unverified"] is True
    assert report["eligible_for_prize_economics"] is False
    data = leads()
    assert data["status"] == "unverified_secondary_summary_no_tier_payouts"
    assert all(x["regular_eight_tier_table"] is None and x["double_eight_tier_table"] is None for x in data["draws"])


def test_official_3953_special_rules_are_stored_as_rules_not_ev():
    report = load_special_rule_notice(RULE, OBSERVATION)
    assert report == {
        "draw_id": 3953,
        "source_is_operator_rule_announcement": True,
        "gross_receipts_known": False,
        "special_tier_rates_approximate": True,
        "rule_stopped_after_first_prize_winner": True,
        "eligible_for_positive_ev_claim": False,
    }
    data = rule()
    assert data["source_url"] == "https://www.pais.co.il/news/news.aspx?newsId=3133"
    assert data["notice_date"] == "2026-08-05"
    assert data["eighth_prize_ils"] == {"regular": 15, "double": 30}
    assert data["receipts_amount_ils"] is None


@pytest.mark.parametrize("mutate,reason", [
    (lambda d: d["draws"].pop(), "fourteen"),
    (lambda d: d["draws"][1].update(draw_id=3955), "consecutive"),
    (lambda d: d["draws"][0].update(draw_date="2026-09-01"), "disagrees"),
    (lambda d: d["draws"][2].update(main_numbers=[1,3,5,10,11,19]), "disagrees"),
    (lambda d: d["draws"][2].update(strong_number=4), "disagrees"),
    (lambda d: d["draws"][0].update(regular_eight_tier_table=[{"tier":"6+strong"}]), "MUST remain null"),
    (lambda d: d["draws"][1].update(double_eight_tier_table=[]), "MUST remain null"),
    (lambda d: d["draws"][1].update(operator_source_verified=True), "MUST NOT claim"),
    (lambda d: d["draws"][1].update(approved_protocol_verified=True), "MUST NOT claim"),
    (lambda d: d.update(raw_source_sha256="a"*64), "unarchived"),
    (lambda d: d["draws"][1].update(ticket_sales_ils=1000), "MUST remain null"),
    (lambda d: d["draws"][1].update(tax_paid_ils=100), "MUST remain null"),
    (lambda d: d.update(source_type="official_mifal_hapais"), "independent secondary"),
    (lambda d: d.update(status="verified_operator_prize_tiers"), "unverified"),
    (lambda d: d["draws"][0].update(reported_regular_first_prize_ils=0), "positive"),
    (lambda d: d["draws"][0].update(reported_all_prizes_ils=-1), "nonnegative"),
    (lambda d: d["draws"][0].update(fake_expected_profit_ils=1000), "fields"),
])
def test_secondary_source_never_upgraded_by_accident(mutate, reason):
    data = leads()
    mutate(data)
    with pytest.raises(PrizeDataError, match=reason):
        validate_secondary_leads(data, history())


@pytest.mark.parametrize("mutate,reason", [
    (lambda d: d.update(source_url="https://malicious.example/3133"), "source"),
    (lambda d: d.update(receipts_amount_ils=123), "receipts"),
    (lambda d: d["approx_percent_of_total_draw_receipts_by_tier"].update({"3":"27"}), "distributions"),
    (lambda d: d.update(eighth_prize_ils={"regular":10,"double":20}), "tier-eight"),
    (lambda d: d.update(original_html_sha256="fake"), "source"),
    (lambda d: d.update(rule_operational_since_draw=3952), "rule window"),
    (lambda d: d.update(notice_date="2026-08-09"), "publication date"),
])
def test_rule_document_fails_closed_for_unsupported_claims(mutate, reason):
    d = rule()
    mutate(d)
    with pytest.raises(PrizeDataError, match=reason):
        validate_special_rule_notice(d, observation())


def test_rule_does_not_transfer_to_another_observation():
    wrong = copy.deepcopy(observation())
    wrong["draw_id"] = 3954
    wrong["source_url"] = "https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3954"
    with pytest.raises(PrizeDataError, match="another draw"):
        validate_special_rule_notice(rule(), wrong)


def test_rule_eighth_tier_reconciliation_protects_payout_precision():
    wrong = copy.deepcopy(observation())
    wrong["games"]["double"][-1]["payout_per_winning_entry_ils"] = 20
    with pytest.raises(PrizeDataError, match="tier-eight"):
        validate_special_rule_notice(rule(), wrong)
