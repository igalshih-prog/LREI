"""Typer command-line interface for LREI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from lrei.config import Settings
from lrei.database import Database
from lrei.logging import configure_logging
from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.statistics import LotteryStatistics

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


@app.command("recommend")
def recommend(
    tickets: Annotated[
        int,
        typer.Option(
            "--tickets",
            "-t",
            help="Number of lottery tickets to generate.",
        ),
    ] = 50,
    seed: Annotated[
        int,
        typer.Option(
            "--seed",
            help="Random seed for reproducible results.",
        ),
    ] = 42,
) -> None:
    """Generate lottery recommendations from historical data."""

    if tickets <= 0:
        raise typer.BadParameter(
            "Number of tickets must be greater than zero."
        )

    root = Path(__file__).resolve().parents[2]

    data_file = root / "data" / "lottery.csv"

    if not data_file.exists():
        raise typer.BadParameter(
            f"Lottery data file not found: {data_file}"
        )

    dataset = CsvDatasetLoader().load(data_file)

    statistics = LotteryStatistics.from_dataset(dataset)

    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=statistics,
        ticket_count=tickets,
        seed=seed,
    )

    typer.echo()
    typer.echo("=" * 70)
    typer.echo("LREI LOTTERY RECOMMENDATIONS")
    typer.echo("=" * 70)
    typer.echo(f"Dataset draws: {len(dataset)}")
    typer.echo(
        f"Generated tickets: "
        f"{len(result.generated_tickets)}"
    )
    typer.echo(
        f"Recommended tickets: "
        f"{len(result.recommended_tickets)}"
    )

    typer.echo()
    typer.echo("RECOMMENDED LOTTERY TICKETS")
    typer.echo("-" * 70)

    recommended = result.recommended_tickets_with_strong

    if recommended:
        for index, ticket in enumerate(
            recommended,
            start=1,
        ):
            numbers = " - ".join(
                f"{number:02d}"
                for number in sorted(ticket.numbers)
            )

            if ticket.strong_number is not None:
                typer.echo(
                    f"Ticket {index:02d}: "
                    f"{numbers} "
                    f"| Strong: "
                    f"{ticket.strong_number}"
                )
            else:
                typer.echo(
                    f"Ticket {index:02d}: "
                    f"{numbers}"
                )
    else:
        for index, ticket in enumerate(
            result.recommended_tickets,
            start=1,
        ):
            numbers = " - ".join(
                f"{number:02d}"
                for number in sorted(ticket)
            )

            typer.echo(
                f"Ticket {index:02d}: {numbers}"
            )

    typer.echo()
    typer.echo("TOP NUMBER SCORES")
    typer.echo("-" * 70)

    for score in result.scores[:10]:
        typer.echo(
            f"Number {score.number:>2} | "
            f"Score: {score.score:.6f}"
        )

    if result.strong_scores:
        typer.echo()
        typer.echo("STRONG NUMBER SCORES")
        typer.echo("-" * 70)

        for score in result.strong_scores[:10]:
            typer.echo(
                f"Strong {score.number:>2} | "
                f"Score: {score.score:.6f}"
            )

    typer.echo()
    typer.echo("=" * 70)


def main() -> None:
    """Run the LREI command-line application."""

    app()
