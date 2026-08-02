"""Tests for SQLite persistence."""

from pathlib import Path

import pytest

from lrei.database import Database


def test_database_persists_and_lists_entries(tmp_path: Path) -> None:
    database = Database(tmp_path / "lrei.sqlite3")

    first_entry = database.add_entry("first")
    second_entry = database.add_entry("second")

    assert first_entry.id == 1
    assert second_entry.id == 2
    assert [entry.message for entry in database.list_entries()] == ["second", "first"]


def test_database_rejects_empty_messages(tmp_path: Path) -> None:
    database = Database(tmp_path / "lrei.sqlite3")

    with pytest.raises(ValueError, match="must not be empty"):
        database.add_entry("  ")
