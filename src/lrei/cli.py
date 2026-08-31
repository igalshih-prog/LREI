"""Typer command-line interface for LREI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from lrei.config import Settings
from lrei.database import Database
from lrei.logging import configure_logging
from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.recommender import RecommendationEngine

app = typer.Typer(
    help="Manage local LREI data and lottery recommendations.",
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
        typer.Argument(
            help="Message to store.",
        ),
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

    for entry in _database(database).list_entries():
        typer.echo(
            f"{entry.id}\t"
            f"{entry.created_at}\t"
            f"{entry.message}"
        )


@app.command()
def config() -> None:
    """Show the resolved runtime configuration."""

    settings = Settings.from_environment()

    typer.echo(
        f"data_dir={settings.data_dir}"
    )

    typer.echo(
        f"database_path={settings.database_path}"
    )

    typer.echo(
        f"log_level={settings.log_level}"
    )


@app.command("recommend")
def recommend(
    data_file: Annotated[
        Path,
        typer.Option(
            "--data",
            "-f",
            help="Path to the lottery CSV data file.",
        ),
    ] = Path("data/lottery.csv"),
    ticket_count: Annotated[
        int,
        typer.Option(
            "--tickets",
            "-t",
            help="Number of tickets to generate.",
        ),
    ] = 10,
    seed: Annotated[
        int | None,
        typer.Option(
            "--seed",
            help="Random seed for reproducible results.",
        ),
    ] = 42,
) -> None:
    """Generate lottery recommendations from historical data."""

    if not data_file.exists():
        raise typer.BadParameter(
            f"Data file does not exist: {data_file}"
        )

    if ticket_count <= 0:
        raise typer.BadParameter(
            "Ticket count must be greater than zero."
        )

    dataset = CsvDatasetLoader().load(data_file)

    if len(dataset) == 0:
        raise typer.BadParameter(
            "Lottery dataset is empty."
        )

    statistics = dataset.statistics()

    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=statistics,
        ticket_count=ticket_count,
        seed=seed,
    )

    typer.echo()
    typer.echo("=" * 60)
    typer.echo("LREI LOTTERY RECOMMENDATIONS")
    typer.echo("=" * 60)
    typer.echo(f"Dataset draws: {len(dataset)}")
    typer.echo(
        f"Generated tickets: "
        f"{len(result.generated_tickets)}"
    )
    typer.echo(
        f"Recommended tickets: "
        f"{len(result.recommended_tickets)}"
    )
    typer.echo("=" * 60)
    typer.echo()

    typer.echo("RECOMMENDED TICKETS")
    typer.echo("-" * 60)

    if result.recommended_tickets_with_strong:
        for index, ticket in enumerate(
            result.recommended_tickets_with_strong,
            start=1,
        ):
            numbers = " ".join(
                f"{number:02d}"
                for number in ticket.numbers
            )

            if ticket.strong_number is not None:
                typer.echo(
                    f"{index:02d}. "
                    f"{numbers} "
                    f"| Strong: "
                    f"{ticket.strong_number:02d}"
                )
            else:
                typer.echo(
                    f"{index:02d}. {numbers}"
                )

    else:
        for index, ticket in enumerate(
            result.recommended_tickets,
            start=1,
        ):
            numbers = " ".join(
                f"{number:02d}"
                for number in ticket
            )

            typer.echo(
                f"{index:02d}. {numbers}"
            )

    typer.echo()
    typer.echo("=" * 60)

    if result.scores:
        typer.echo("TOP NUMBER SCORES")
        typer.echo("-" * 60)

        for score in sorted(
            result.scores,
            key=lambda item: item.score,
            reverse=True,
        )[:10]:
            typer.echo(
                f"{score.number:02d} "
                f"| Score: {score.score:.4f}"
            )

    if result.strong_scores:
        typer.echo()
        typer.echo("TOP STRONG NUMBER SCORES")
        typer.echo("-" * 60)

        for score in sorted(
            result.strong_scores,
            key=lambda item: item.score,
            reverse=True,
        )[:10]:
            typer.echo(
                f"{score.number:02d} "
                f"| Score: {score.score:.4f}"
            )

    typer.echo()
    typer.echo("=" * 60)


def main() -> None:
    """Run the LREI command-line application."""

    app()
