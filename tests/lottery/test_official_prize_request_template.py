"""P3-A.2 request template must NEVER be mistaken for actual prizes."""

import csv
from pathlib import Path

from lrei.lottery.dataset import CsvDatasetLoader, parse_draw_date

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "data" / "prize_request_templates" / "3955-3968_blank_16_tiers.csv"
ARCHIVE = ROOT / "data" / "lottery.csv"
HEADERS = (
    "draw_id", "draw_date", "game", "tier",
    "winning_entries", "payout_per_winning_entry_ils",
)
TIERS = ("6+strong", "6", "5+strong", "5", "4+strong", "4", "3+strong", "3")


def test_explicit_224_blank_cells_and_no_imputed_prizes():
    with TEMPLATE.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        assert tuple(reader.fieldnames or ()) == HEADERS
        rows = list(reader)
    assert len(rows) == 14 * 2 * 8 == 224
    assert all(row["winning_entries"] == "" for row in rows)
    assert all(row["payout_per_winning_entry_ils"] == "" for row in rows)
    assert all(set(row) == set(HEADERS) and None not in row for row in rows)

    expected = [
        (str(n), game, tier)
        for n in range(3955, 3969)
        for game in ("regular", "double")
        for tier in TIERS
    ]
    actual = [(row["draw_id"], row["game"], row["tier"]) for row in rows]
    assert actual == expected
    assert len(actual) == len(set(actual))


def test_request_draw_dates_agree_with_independent_archive():
    history = CsvDatasetLoader().load(ARCHIVE)
    by_id = {d.draw_id: d for d in history}
    with TEMPLATE.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        existing = by_id[row["draw_id"]]
        assert row["draw_date"] == parse_draw_date(existing.date).isoformat()


def test_request_template_not_stored_as_a_prize_observation():
    assert "prize_observations" not in TEMPLATE.parts
    assert "prize_leads" not in TEMPLATE.parts
    assert TEMPLATE.name.endswith("_blank_16_tiers.csv")
