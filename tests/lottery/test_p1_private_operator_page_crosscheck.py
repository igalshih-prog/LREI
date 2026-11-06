"""Synthetic-only tests for private 8-draw operator CSV ↔ HTML content check."""

import json
from pathlib import Path

import pytest

from lrei.lottery import p1_private_operator_page_crosscheck as audit
from lrei.lottery.p1_private_operator_page_crosscheck import (
    PrivateSourceError, inspect_operator_page, private_crosscheck,
)

TIERS = ("6 + חזק", "6", "5 + חזק", "5",
         "4 + חזק", "4", "3 + חזק", "3")
OUTCOME = ("2026-10-13", (1, 5, 12, 22, 31, 37), 4, 1, 2)


def fake_operator_html(draw_id=3974, *, total_bump=0,
                       date="13/10/2026", mains=(1, 5, 12, 22, 31, 37),
                       strong=4, reg_winners=1, dbl_winners=2):
    """All numbers/payouts in this fake text are invented test fixtures."""
    parts = [
        f"תוצאות הגרלה מס' {draw_id} לתאריך {date} שעה 23:15",
        f"{strong} המספר החזק",
        " ".join(str(n) for n in mains),
        "הגרלת הלוטו",
    ]
    regular_paid = 0
    double_paid = 0
    for name, first in (("טבלת זכיות לוטו", reg_winners),
                        ("טבלת זכיות דאבל לוטו", dbl_winners)):
        parts.append(name)
        for idx, tier in enumerate(TIERS):
            winners = first if idx == 0 else idx * 3
            award = 10 + idx if name == "טבלת זכיות לוטו" else 20 + idx
            paid = winners * award
            if name == "טבלת זכיות לוטו":
                regular_paid += paid
            else:
                double_paid += paid
            parts.append(
                f"מס' ניחושים {tier} כמות זכיות {winners} גובה הפרס {award} ₪"
            )
    parts.append(f"תוצאות הגרלה אקסטרא מס' {draw_id}")
    parts.append("טבלת זכיות אקסטרא")
    extra_paid = 0
    for idx, tier in enumerate(("6", "5", "4", "3", "2")):
        n, award = idx + 1, 110 + idx
        extra_paid += n * award
        parts.append(
            f"מס' ניחושים {tier} כמות זכיות {n} גובה הפרס {award} ₪"
        )
    parts.append(
        "סך כל הפרסים שחולקו בהגרלה זו היה: "
        + str(regular_paid + double_paid + extra_paid + total_bump) + " ₪"
    )
    # Test HTML resembles the public page layout but is NOT real source.
    return ("<html><body>" + "".join(f"<p>{t}</p>" for t in parts)
            + "</body></html>").encode("utf-8")


def test_8_fields_and_three_game_accounting_match_offline():
    result = inspect_operator_page(fake_operator_html(), draw_id=3974, expected=OUTCOME)
    assert result["draw_date_main_strong_match"] is True
    assert result["regular_double_first_prize_counts_match"] is True
    assert result["all_games_source_arithmetic_match"] is True
    assert result["regular_double_tiers_checked"] == 16
    assert result["extra_tiers_checked"] == 5
    assert result["source_authenticity_independently_attested"] is False
    assert result["dataset_admission_approved"] is False


@pytest.mark.parametrize("change,why", [
    ({"date": "14/10/2026"}, "date differs"),
    ({"mains": (1, 5, 12, 22, 31, 36)}, "main numbers"),
    ({"strong": 5}, "strong disagree"),
    ({"reg_winners": 2}, "winner counts"),
    ({"dbl_winners": 3}, "winner counts"),
    ({"total_bump": 1}, "arithmetic mismatch"),
])
def test_first_party_content_disagreement_fails_closed(change, why):
    raw = fake_operator_html(**change)
    with pytest.raises(PrivateSourceError, match=why):
        inspect_operator_page(raw, draw_id=3974, expected=OUTCOME)


@pytest.mark.parametrize("transform,why", [
    (lambda x: x.replace("המספר החזק", "המספר הלא חזק"), "layout"),
    (lambda x: x.replace("טבלת זכיות דאבל לוטו", "טבלת זכיות לוטו"), "sections"),
    (lambda x: x.replace("תוצאות הגרלה מס' 3974", "תוצאות הגרלה מס' 3975"), "heading"),
    (lambda x: x.replace("טבלת זכיות אקסטרא", "אקסטרא חסר"), "Extra table heading"),
    (lambda x: x.replace("סך כל הפרסים שחולקו בהגרלה זו היה:", "ללא סך פרסים"),
     "all-games total"),
])
def test_missing_or_ambiguous_operator_rendering_refused(transform, why):
    raw = transform(fake_operator_html().decode("utf-8")).encode("utf-8")
    with pytest.raises((PrivateSourceError, ValueError), match=why):
        inspect_operator_page(raw, draw_id=3974, expected=OUTCOME)


def test_eight_private_realistic_mock_pages_and_manifest_no_source_values(
    tmp_path, monkeypatch
):
    # Simulate separately parsed original CSV without opening a real source.
    monkeypatch.setattr(
        audit, "_source_csv",
        lambda path, digest: {draw: OUTCOME for draw in audit.IDS},
    )
    requests = []
    sleeps = []

    def fake_fetch(draw):
        requests.append(draw)
        return fake_operator_html(draw_id=draw)

    result = private_crosscheck(
        csv_path=Path("synthetic-not-used.csv"), csv_sha256="0" * 64,
        private_root=tmp_path, fetch_page=fake_fetch, sleep=sleeps.append,
    )
    assert requests == list(audit.IDS)
    assert sleeps == [3] * 7
    assert result["draws_checked"] == 8
    assert result["regular_double_tiers_reparsed"] == 128
    assert result["extra_tiers_reparsed"] == 40
    assert result["first_prize_winner_counts_matched"] == 16
    assert result["page_accounting_matches"] == 8
    assert result["research_only_no_play"] is True
    assert result["dataset_admission_approved"] is False
    assert "main_numbers" not in json.dumps(result)
    saved = Path(result["private_evidence_directory"])
    assert len(list(saved.iterdir())) == 9
    report = json.loads((saved / "private-capture-manifest.json").read_text(encoding="utf-8"))
    assert report["completed_draws"] == 8
    assert report["source_attested_by_independent_party"] is False
    assert report["dataset_promotion_approved"] is False


def test_failure_aborts_first_bad_page_without_retry_or_data_promotion(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(audit, "_source_csv",
                        lambda path, digest: {draw: OUTCOME for draw in audit.IDS})
    visited = []

    def flaky_fetch(draw):
        visited.append(draw)
        return fake_operator_html(draw_id=draw, total_bump=1 if draw == 3975 else 0)

    with pytest.raises(PrivateSourceError, match="arithmetic mismatch"):
        private_crosscheck(csv_path=Path("synthetic.csv"), csv_sha256="0" * 64,
                           private_root=tmp_path, fetch_page=flaky_fetch,
                           sleep=lambda _: None)
    assert visited == [3974, 3975]
    dirs = list(tmp_path.iterdir())
    assert len(dirs) == 1
    report = json.loads((dirs[0] / "private-capture-manifest.json").read_text())
    assert report["completed_draws"] == 1
    assert report["status"] == "PARTIAL_OR_REFUSED_KEEP_PRIVATE"
    assert report["dataset_promotion_approved"] is False
    assert (dirs[0] / "draw-3974-operator-original.html").is_file()
    assert not (dirs[0] / "draw-3975-operator-original.html").exists()


def test_wrong_study_range_cannot_be_repurposed():
    with pytest.raises(PrivateSourceError, match="fixed reviewed range"):
        inspect_operator_page(fake_operator_html(), draw_id=3990, expected=OUTCOME)
