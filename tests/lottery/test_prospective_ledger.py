"""Fast P1 checks: no old historical benchmark is re-executed."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from lrei.lottery.prospective_ledger import (
    build_snapshot, parse_target_datetime, verify_snapshot, write_snapshot,
)


NOW = datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)
TARGET = datetime(2026, 10, 15, 18, 0, tzinfo=timezone.utc)
SHA = "f949eb8e3b5d8cca82997ec4cf0d6b48d907baef"


def sample(tmp_path, *, draws_date="10-10-26", tickets=None, now=NOW, target=TARGET, sha=SHA):
    data_file = tmp_path / "lottery.csv"
    data_file.write_text("synthetic-test-data\n", encoding="utf8")
    dataset = SimpleDataset(draws_date)
    if tickets is None:
        tickets = [SimpleNamespace(numbers=tuple(range(index + 1, index + 7)), strong_number=(index % 7) + 1) for index in range(14)]
    return build_snapshot(
        dataset_file=data_file, dataset=dataset, tickets=tickets,
        mode="smart", objective="coverage_any_prize", seed=42,
        source_commit=sha, target_draw_at=target, generated_count=250,
        created_at=now,
    )


class SimpleDataset:
    def __init__(self, last_date):
        self.record = SimpleNamespace(draw_id="3973", date=last_date)

    def __len__(self):
        return 1141

    def latest(self):
        return self.record


def test_record_valid_and_checksum_verified(tmp_path):
    record = sample(tmp_path)
    assert record["ticket_count"] == 14
    assert record["latest_draw"] == {"id": "3973", "date": "2026-10-10"}
    assert record["target_draw_at_utc"] == "2026-10-15T18:00:00Z"
    assert verify_snapshot(record)
    record["tickets"][0]["main"][0] = 37
    assert not verify_snapshot(record)


def test_exclusive_write_cannot_overwrite_prior_record(tmp_path):
    record = sample(tmp_path)
    folder = tmp_path / "records"
    path = write_snapshot(record, folder)
    assert json.loads(path.read_text(encoding="utf8")) == record
    with pytest.raises(FileExistsError):
        write_snapshot(record, folder)
    assert json.loads(path.read_text(encoding="utf8")) == record


def test_reject_modified_digest(tmp_path):
    record = sample(tmp_path)
    record["seed"] = 5
    with pytest.raises(ValueError, match="digest"):
        write_snapshot(record, tmp_path / "records")


@pytest.mark.parametrize("invalid", [
    [SimpleNamespace(numbers=(1, 2, 3, 4, 5, 5), strong_number=1)],
    [SimpleNamespace(numbers=(0, 2, 3, 4, 5, 6), strong_number=1)],
    [SimpleNamespace(numbers=(1, 2, 3, 4, 5, 6), strong_number=8)],
    [SimpleNamespace(numbers=(1, 2, 3, 4, 5, 6), strong_number=None)],
])
def test_invalid_ticket_rejected(tmp_path, invalid):
    with pytest.raises(ValueError, match="ticket"):
        sample(tmp_path, tickets=invalid)


def test_duplicate_main_lines_rejected(tmp_path):
    tickets = [SimpleNamespace(numbers=(1, 2, 3, 4, 5, 6), strong_number=(i % 7) + 1) for i in range(14)]
    with pytest.raises(ValueError, match="distinct"):
        sample(tmp_path, tickets=tickets)


@pytest.mark.parametrize("latest_date", ["01-10-26", "17-10-26", "20-10-26"])
def test_stale_and_future_history_rejected(tmp_path, latest_date):
    with pytest.raises(ValueError, match="future-dated|four days|precede"):
        sample(tmp_path, draws_date=latest_date)


def test_target_must_be_future_and_strictly_after_history(tmp_path):
    with pytest.raises(ValueError, match="future"):
        sample(tmp_path, target=NOW)
    with pytest.raises(ValueError, match="precede"):
        sample(tmp_path, draws_date="16-10-26")


def test_invalid_source_commit_rejected(tmp_path):
    with pytest.raises(ValueError, match="Git SHA"):
        sample(tmp_path, sha="not-commit")


def test_timezone_required_and_normalized():
    assert parse_target_datetime("2026-10-15T21:00:00+03:00") == TARGET
    assert parse_target_datetime("2026-10-15T18:00:00Z") == TARGET
    with pytest.raises(ValueError, match="timezone"):
        parse_target_datetime("2026-10-15T21:00:00")


def test_local_draw_date_is_not_replaced_by_utc_date(tmp_path):
    # Israel 00:30 on the 15th is still the 14th in UTC. History from
    # the 14th is valid, while a local draw on the 15th is not.
    target = datetime(2026, 10, 15, 0, 30, tzinfo=timezone(timedelta(hours=3)))
    created = datetime(2026, 10, 14, 20, 0, tzinfo=timezone.utc)
    record = sample(tmp_path, draws_date="14-10-26", now=created, target=target)
    assert record["target_draw_date_local"] == "2026-10-15"
    assert record["target_draw_at_utc"].startswith("2026-10-14")
    assert verify_snapshot(record)
    with pytest.raises(ValueError, match="precede target draw date"):
        sample(tmp_path, draws_date="15-10-26", now=created, target=target)


def test_freshness_boundary_uses_target_local_calendar(tmp_path):
    target = datetime(2026, 10, 15, 0, 30, tzinfo=timezone(timedelta(hours=3)))
    # Local creation: Oct 15 at 00:15; UTC creation: Oct 14 at 21:15.
    created = datetime(2026, 10, 14, 21, 15, tzinfo=timezone.utc)
    assert verify_snapshot(sample(
        tmp_path, draws_date="11-10-26", now=created, target=target,
    ))
    with pytest.raises(ValueError, match="four days old"):
        sample(tmp_path, draws_date="10-10-26", now=created, target=target)
