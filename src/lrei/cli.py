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
    help="Manage local LREI data and lottery analysis.",
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
    """Create the configured database instance."""

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
            help="Message to store."
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

    entries = _database(database).list_entries()

    if not entries:
        typer.echo("No entries found.")
        return

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
    ] = 14,
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
            "tickets must be greater than zero"
        )

    root = Path(__file__).resolve().parents[2]

    data_file = root / "data" / "lottery.csv"

    if not data_file.exists():
        typer.echo(
            f"Lottery data file not found: {data_file}",
            err=True,
        )
        raise typer.Exit(code=1)

    dataset = CsvDatasetLoader().load(data_file)

    statistics = LotteryStatistics.from_dataset(
        dataset
    )

    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=statistics,
        ticket_count=max(tickets * 5, 50),
        seed=seed,
    )

    typer.echo()
    typer.echo("=" * 65)
    typer.echo("LREI LOTTERY RECOMMENDATIONS")
    typer.echo("=" * 65)

    typer.echo(f"Historical draws: {len(dataset)}")
    typer.echo(
        f"Generated candidates: "
        f"{len(result.generated_tickets)}"
    )
    typer.echo(
        f"Requested tickets: {tickets}"
    )

    typer.echo()
    typer.echo("RECOMMENDED TICKETS")
    typer.echo("-" * 65)

    selected = list(
        result.recommended_tickets_with_strong
    )[:tickets]

    if not selected:
        typer.echo(
            "No recommended tickets were generated."
        )
        raise typer.Exit(code=1)

    for index, ticket in enumerate(
        selected,
        start=1,
    ):
        numbers = " ".join(
            f"{number:02d}"
            for number in sorted(ticket.numbers)
        )

        strong = (
            str(ticket.strong_number)
            if ticket.strong_number is not None
            else "N/A"
        )

        typer.echo(
            f"Ticket {index:02d}: "
            f"{numbers} "
            f"| Strong: {strong}"
        )

    typer.echo("-" * 65)

    typer.echo()
    typer.echo("TOP MAIN NUMBERS")

    for score in result.scores[:10]:
        typer.echo(
            f"{score.number:02d} "
            f"(score: {score.score:.6f})"
        )

    if result.strong_scores:
        typer.echo()
        typer.echo("TOP STRONG NUMBERS")

        for score in result.strong_scores[:7]:
            typer.echo(
                f"{score.number} "
                f"(score: {score.score:.6f})"
            )

    typer.echo("=" * 65)


def main() -> None:
    """Run the LREI command-line application."""

    app()


if __name__ == "__main__":
    main()
