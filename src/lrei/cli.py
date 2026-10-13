"""Typer command-line interface for LREI."""

from __future__ import annotations

from pathlib import Path
import subprocess
from datetime import datetime, timezone
from typing import Annotated, Literal

import typer

from lrei.config import Settings
from lrei.database import Database
from lrei.logging import configure_logging
from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.pro import ProRecommendationEngine
from lrei.lottery.elite import EliteProRecommendationEngine
from lrei.lottery.smart import SmartConfig, SmartRecommendationEngine
from lrei.lottery.statistics import LotteryStatistics
from lrei.lottery.any_prize_coverage_engine import AnyPrizeCoverageRecommendationEngine
from lrei.lottery.portfolio_coverage import portfolio_coverage
from lrei.lottery.prospective_ledger import build_snapshot, parse_target_datetime, write_snapshot

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
    ] = 14,
    seed: Annotated[
        int,
        typer.Option(
            "--seed",
            help="Random seed for reproducible results.",
        ),
    ] = 42,
    mode: Annotated[
        Literal["regular", "pro", "elite", "smart"],
        typer.Option(
            "--mode",
            help="Recommendation engine: regular, pro, elite, or smart.",
        ),
    ] = "elite",
    objective: Annotated[
        Literal["coverage_any_prize", "coverage_4plus", "historical"],
        typer.Option(
            "--objective",
            help="Smart-only objective: coverage_any_prize (default), coverage_4plus, or historical model selection.",
        ),
    ] = "coverage_any_prize",
    snapshot_dir: Annotated[
        Path | None,
        typer.Option("--snapshot-dir", help="Write a hashed pre-draw JSON snapshot, never overwriting existing records."),
    ] = None,
    target_draw_at: Annotated[
        str | None,
        typer.Option("--target-draw-at", help="Future target draw time, ISO-8601 with timezone (requires --snapshot-dir)."),
    ] = None,
) -> None:
    """Generate lottery recommendations from historical data."""

    if tickets <= 0:
        raise typer.BadParameter(
            "Number of tickets must be greater than zero."
        )

    if (snapshot_dir is None) != (target_draw_at is None):
        raise typer.BadParameter("--snapshot-dir and --target-draw-at must be provided together")

    target_time = None
    if target_draw_at is not None:
        try:
            target_time = parse_target_datetime(target_draw_at)
        except ValueError as exc:
            raise typer.BadParameter(str(exc), param_hint="--target-draw-at") from exc
        if target_time <= datetime.now(timezone.utc):
            raise typer.BadParameter("target draw must be in the future", param_hint="--target-draw-at")

    root = Path(__file__).resolve().parents[2]

    data_file = root / "data" / "lottery.csv"

    if not data_file.exists():
        raise typer.BadParameter(
            f"Lottery data file not found: {data_file}"
        )

    source_commit = None
    if snapshot_dir is not None:
        try:
            source_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root, check=True, capture_output=True, text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise typer.BadParameter(
                "cannot record source Git commit; run from a Git checkout",
                param_hint="--snapshot-dir",
            ) from exc

    dataset = CsvDatasetLoader().load(data_file)

    statistics = LotteryStatistics.from_dataset(dataset)

    smart_objective = None
    if mode == "smart":
        smart_engine = SmartRecommendationEngine(SmartConfig(objective=objective))
        result = smart_engine.recommend(dataset, seed=seed)
        smart_objective = smart_engine.config.objective
    elif mode == "elite":
        result = EliteProRecommendationEngine().recommend(
            dataset,
            seed=seed,
        )
    elif mode == "pro":
        result = ProRecommendationEngine().recommend(
            dataset,
            seed=seed,
        )
    else:
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
    typer.echo(f"Engine mode: {mode}")
    typer.echo(f"Dataset draws: {len(dataset)}")
    typer.echo(
        f"Generated tickets: "
        f"{len(result.generated_tickets)}"
    )
    typer.echo(
        f"Recommended tickets: "
        f"{len(result.recommended_tickets)}"
    )

    if mode == "smart" and smart_objective == "coverage_any_prize":
        probability = AnyPrizeCoverageRecommendationEngine.coverage_probability(
            result.recommended_tickets
        )
        typer.echo(f"Exact 3+ main-number coverage: {probability:.2%}")
        typer.echo(
            "This is the exact probability under a uniform 6-of-37 draw model; "
            "it is not a prediction of winning numbers."
        )
    elif mode == "smart" and smart_objective == "coverage_4plus":
        coverage = portfolio_coverage(result.recommended_tickets, threshold=4)
        probability = float(coverage["probability"])
        typer.echo(f"Exact 4+ main-number coverage: {probability:.2%}")
        typer.echo(
            "This is the exact probability under a uniform 6-of-37 draw model; "
            "it is not a prediction of winning numbers."
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

    if mode == "smart":
        typer.echo()
        typer.echo(f"Smart objective: {smart_objective}")
        if smart_objective == "coverage_any_prize":
            typer.echo(
                "Portfolio goal: maximize exact coverage of 6/37 draws with "
                "at least one ticket matching 3+ main numbers."
            )
            typer.echo(
                "This optimizes portfolio coverage; it does not predict the "
                "winning numbers or improve jackpot odds."
            )
        elif smart_objective == "coverage_4plus":
            typer.echo(
                "Portfolio goal: maximize the probability of at least one "
                "ticket matching 4+ main numbers."
            )
            typer.echo(
                "This optimizes portfolio structure; it does not predict "
                "the winning numbers or improve jackpot odds."
            )

    # Coverage objectives use deliberately flat number scores and random
    # strong numbers, so presenting them as ranked predictions would mislead.
    if mode != "smart" or smart_objective == "historical":
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

    if snapshot_dir is not None:
        try:
            record = build_snapshot(
                dataset_file=data_file,
                dataset=dataset,
                tickets=result.recommended_tickets_with_strong,
                mode=mode,
                objective=smart_objective,
                seed=seed,
                source_commit=source_commit,
                target_draw_at=target_time,
                generated_count=len(result.generated_tickets),
            )
            snapshot_path = write_snapshot(record, snapshot_dir)
        except (OSError, ValueError) as exc:
            raise typer.BadParameter(
                f"could not save pre-draw record: {exc}",
                param_hint="--snapshot-dir",
            ) from exc
        typer.echo()
        typer.echo(f"Pre-draw snapshot: {snapshot_path}")
        typer.echo(f"Record SHA-256: {record['record_sha256']}")

    typer.echo()
    typer.echo("=" * 70)


def main() -> None:
    """Run the LREI command-line application."""

    app()
