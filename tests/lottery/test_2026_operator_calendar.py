"""P1: operator-published 2026 schedule vs EXISTING draw-date archive.

This is a schedule-completeness check, NOT authentication of draw results.
Notices are operator website announcements; original notice bytes, winning
numbers, payout tiers, ticket sales and legally binding protocols are NOT
verified by this unit test.

Extra Thursdays: https://www.pais.co.il/news/news.aspx?newsId=3105
Holiday postponements: https://www.pais.co.il/news/news.aspx?newsId=3116
"""

from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from lrei.lottery.dataset import CsvDatasetLoader, parse_draw_date


ROOT = Path(__file__).resolve().parents[2]

# Published 31 Dec 2025. Scheduled only: subject to any later notices.
EXTRA_THURSDAYS_2026 = tuple(
    date.fromisoformat(text)
    for text in (
        "2026-01-08", "2026-01-29", "2026-02-19", "2026-03-12",
        "2026-03-26", "2026-05-14", "2026-06-04", "2026-06-25",
        "2026-07-16", "2026-08-13", "2026-09-03", "2026-10-15",
        "2026-11-19", "2026-12-10",
    )
)

# Operator's holiday notice published 23 Mar 2026: shifted regular draws.
POSTPONED_DRAWS_2026 = {
    3914: date(2026, 4, 9),   # Thursday instead of holiday-week Tuesday
    3918: date(2026, 4, 23),  # Thursday instead of holiday-week Tuesday
    3928: date(2026, 5, 24),  # Sunday instead of Shavuot Saturday
}


def calendar_discrepancies(draws, cutoff: date):
    """Report schedule/date discrepancies, never any outcome verification.

    Limit schedule assertions to dates on or before the actual CSV cutoff.
    Later operator announcements are expectations, NOT data rows to invent.
    """
    draws = tuple(draws)
    counts = Counter(parse_draw_date(draw.date) for draw in draws)
    id_index = {}
    for draw in draws:
        id_index.setdefault(str(draw.draw_id), []).append(draw)

    problems = []
    checked_extras = 0
    for planned_day in EXTRA_THURSDAYS_2026:
        if planned_day <= cutoff:
            checked_extras += 1
            if counts[planned_day] != 1:
                problems.append(f"extra Thursday {planned_day}: {counts[planned_day]} records")

    for draw_id, planned_day in POSTPONED_DRAWS_2026.items():
        if planned_day <= cutoff:
            found = id_index.get(str(draw_id), [])
            if len(found) != 1 or parse_draw_date(found[0].date) != planned_day:
                problems.append(f"postponed draw {draw_id}: archive/date mismatch")

    # A Thursday not in either notice needs an additional source explanation;
    # it must not silently be classified as an ordinary Tue/Sat draw.
    explained = set(EXTRA_THURSDAYS_2026) | {
        d for d in POSTPONED_DRAWS_2026.values() if d.weekday() == 3
    }
    unusual_thursdays = sorted(
        day for day, count in counts.items()
        if count and day.year == 2026 and day <= cutoff
        and day.weekday() == 3 and day not in explained
    )
    problems.extend(f"unsourced Thursday {d}" for d in unusual_thursdays)
    return {
        "checked_published_extra_thursdays": checked_extras,
        "checked_published_postponements": sum(
            d <= cutoff for d in POSTPONED_DRAWS_2026.values()
        ),
        "discrepancies": problems,
        "operator_outcome_or_payout_authenticity_verified": False,
        "data_freshness_verified": False,
    }


def test_existing_archive_matches_operator_2026_extra_and_holiday_notices():
    archive = CsvDatasetLoader().load(ROOT / "data" / "lottery.csv")
    cutoff = parse_draw_date(archive.latest().date)
    assert cutoff is not None
    report = calendar_discrepancies(archive, cutoff)
    # Expected count grows with a future VERIFIED CSV update. Do not lock
    # the archive permanently at draw #3973 / 10 October 2026.
    assert report["checked_published_extra_thursdays"] == sum(
        day <= cutoff for day in EXTRA_THURSDAYS_2026
    )
    assert report["checked_published_postponements"] == sum(
        day <= cutoff for day in POSTPONED_DRAWS_2026.values()
    )
    assert report["discrepancies"] == []
    assert report["operator_outcome_or_payout_authenticity_verified"] is False
    assert report["data_freshness_verified"] is False


@pytest.mark.parametrize("missing_id", [3914, 3918, 3928, 3955, 3962])
def test_losing_an_existing_scheduled_draw_is_detected(missing_id):
    archive = CsvDatasetLoader().load(ROOT / "data" / "lottery.csv")
    changed = [d for d in archive if d.draw_id != str(missing_id)]
    report = calendar_discrepancies(changed, date(2026, 10, 10))
    assert report["discrepancies"]


def test_a_wrong_calendar_day_cannot_pass_as_the_same_postponed_draw():
    archive = CsvDatasetLoader().load(ROOT / "data" / "lottery.csv")
    # Do not alter production CSV: use a minimal fake object carrying a changed
    # date but the identical ID to prove calendar validation is independent.
    altered = []
    for row in archive:
        if row.draw_id == "3918":
            altered.append(type("FakeDraw", (), {"draw_id": "3918", "date": "22-04-26"})())
        else:
            altered.append(row)
    report = calendar_discrepancies(altered, date(2026, 10, 10))
    assert any("postponed draw 3918" in x for x in report["discrepancies"])


def test_future_notice_not_misrepresented_as_already_verified_result():
    archive = CsvDatasetLoader().load(ROOT / "data" / "lottery.csv")
    historical_cutoff = date(2026, 10, 10)
    # Take the historical snapshot instead of assuming the checked-in
    # archive still ends at #3973. This regression must survive later,
    # independently reviewed data updates without relaxing calendar checks.
    old_archive = tuple(
        draw for draw in archive
        if parse_draw_date(draw.date) <= historical_cutoff
    )
    as_of_old_csv = calendar_discrepancies(old_archive, historical_cutoff)
    assert not any("2026-10-15" in x for x in as_of_old_csv["discrepancies"])

    # An as-of date after the announced extra Thursday exposes the missing
    # row in that same old snapshot; it never invents winning numbers.
    as_of_later = calendar_discrepancies(old_archive, date(2026, 10, 19))
    missing_notice = "extra Thursday 2026-10-15: 0 records"
    assert missing_notice in as_of_later["discrepancies"]
    assert as_of_later["data_freshness_verified"] is False

    # A synthetic calendar-only entry demonstrates that a newer candidate
    # can satisfy the schedule expectation without authenticating its result.
    # This entry is NOT a real draw or source proof.
    extra_schedule_only = type(
        "CalendarOnly", (), {"draw_id": "synthetic", "date": "15-10-26"}
    )()
    with_extra = calendar_discrepancies(
        (*old_archive, extra_schedule_only), date(2026, 10, 19)
    )
    assert missing_notice not in with_extra["discrepancies"]
    assert with_extra["operator_outcome_or_payout_authenticity_verified"] is False
    assert with_extra["data_freshness_verified"] is False
