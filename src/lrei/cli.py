"""Typer command-line interface for LREI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from lrei.config import Settings
from lrei.database import Database
from lrei.logging import configure_logging

app = typer.Typer(
    help="Manage local LREI data.",
    no_args_is_help=True,
)

DatabaseOption = Annotated[
    Path | None,
    typer.Option(
        "--database",
        "-d",
        help="Override the configured database path.",
    ),
]


def _database(database_path: Path | None) -> Database:
    settings = Settings.from_environment()
    configure_logging(settings.log_level)

    return Database(
        database_path or settings.database_path
    )


@app.command("init-db")
def initialize_database(
    database: DatabaseOption = None,
) -> None:
    """Create the database schema."""

    selected_database = _database(database)
    selected_database.initialize()

    typer.echo(
        f"Initialized database: {selected_database.path}"
    )


@app.command()
def add(
    message: Annotated[
        str,
        typer.Argument(help="Message to store."),
    ],
    database: DatabaseOption = None,
) -> None:
    """Add a new entry."""

    entry = _database(database).add_entry(message)

    typer.echo(
        f"Added entry {entry.id}: {entry.message}"
    )


@app.command("list")
def list_entries(
    database: DatabaseOption = None,
) -> None:
    """List entries from newest to oldest."""

    entries = _database(database).list_entries()

    for entry in entries:
        typer.echo(
            f"{entry.id}\t"
            f"{entry.created_at}\t"
            f"{entry.message}"
        )


@app.command()
def config() -> None:
    """Show the resolved runtime configuration."""

    settings = Settings.from_environment()

    typer.echo(f"data_dir={settings.data_dir}")
    typer.echo(
        f"database_path={settings.database_path}"
    )
    typer.echo(f"log_level={settings.log_level}")


def main() -> None:
    """Run the LREI command-line application."""

    app()
