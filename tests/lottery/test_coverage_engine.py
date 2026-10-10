from itertools import combinations
from math import comb
from pathlib import Path

import pytest

from lrei.lottery.coverage_engine import CoverageConfig, CoverageRecommendationEngine
from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.portfolio_coverage import portfolio_coverage


@pytest.mark.slow
def test_coverage_engine_builds_fourteen_tickets_at_exact_4plus_bound():
    dataset = CsvDatasetLoader().load(Path("data/lottery.csv"))
    result = CoverageRecommendationEngine().recommend(dataset, seed=20261010)
    portfolio = result.recommended_tickets

    assert len(portfolio) == 14
    assert len(set(portfolio)) == 14
    assert all(len(ticket) == 6 and len(set(ticket)) == 6 for ticket in portfolio)
    assert all(
        len(set(left) & set(right)) <= 1
        for left, right in combinations(portfolio, 2)
    )

    # With pairwise overlap <= 1, no draw can hit 4+ numbers on two tickets.
    one_ticket_4plus = (
        comb(6, 4) * comb(31, 2)
        + comb(6, 5) * comb(31, 1)
        + 1
    )
    expected = 14 * one_ticket_4plus / comb(37, 6)
    actual = portfolio_coverage(portfolio, threshold=4)["probability"]
    assert abs(actual - expected) < 1e-15


def test_coverage_config_rejects_settings_that_break_exact_4plus_coverage():
    with pytest.raises(ValueError):
        CoverageConfig(candidate_count=13)
    with pytest.raises(ValueError):
        CoverageConfig(max_tickets=13)
    with pytest.raises(ValueError):
        CoverageConfig(max_overlap=2)
