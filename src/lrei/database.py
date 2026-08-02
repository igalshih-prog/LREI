"""SQLite persistence layer for LREI entries."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("lrei.database")


@dataclass(frozen=True, slots=True)
class Entry:
    """A persisted LREI entry."""

    id: int
    message: str
    created_at: str


class Database:
    """Own and initialize a SQLite database used by the application."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the schema if it does not already exist."""
        with self._connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY,
                    message TEXT NOT NULL CHECK (length(message) > 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """)
        logger.info("database initialized at %s", self.path)

    def add_entry(self, message: str) -> Entry:
        """Store a non-empty message and return the resulting entry."""
        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("message must not be empty")

        self.initialize()
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO entries (message) VALUES (?)", (normalized_message,)
            )
            row = connection.execute(
                "SELECT id, message, created_at FROM entries WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()

        if row is None:  # Defensive: the insert and read use one transaction.
            raise RuntimeError("stored entry could not be retrieved")
        return Entry(id=int(row[0]), message=str(row[1]), created_at=str(row[2]))

    def list_entries(self) -> list[Entry]:
        """Return entries ordered from newest to oldest."""
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, message, created_at FROM entries ORDER BY id DESC"
            ).fetchall()

        return [
            Entry(id=int(row[0]), message=str(row[1]), created_at=str(row[2]))
            for row in rows
        ]
