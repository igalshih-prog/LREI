"""Typer command-line interface for LREI."""

from __future__ import annotations

from pathlib import Path
import json
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
from lrei.lottery.five_plus import five_plus_metrics
from lrei.lottery.prospective_ledger import build_snapshot, parse_target_datetime, write_snapshot
from lrei.lottery.prospective_scoring import score_snapshot, write_score
from lrei.lottery.dataset import LotteryDrawRecord
from lrei.lottery.bias_evidence import (
    freeze_bias_model, score_future_draw, write_immutable,
)

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
            help="Regular-mode generated candidate count. All modes recommend exactly 14 lines; other modes ignore this option.",
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
        Literal["coverage_any_prize", "coverage_4plus", "coverage_5plus", "historical"],
        typer.Option(
            "--objective",
            help="Smart objective: coverage_any_prize (default), coverage_4plus, coverage_5plus (same optimal lines as 4+), or historical.",
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

    if mode != "regular" and tickets != 14:
        typer.echo("Note: --tickets changes candidate generation only in Regular mode; this engine outputs 14 recommended lines.")

    if (snapshot_dir is None) != (target_draw_at is None):
        raise typer.BadParameter("--snapshot-dir and --target-draw-at must be provided together")

    target_time = None
    if target_draw_at is not None:
        try:
            parse_target_datetime(target_draw_at)
            target_time = datetime.fromisoformat(target_draw_at.replace("Z", "+00:00"))
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
    elif mode == "smart" and smart_objective in {"coverage_4plus", "coverage_5plus"}:
        if smart_objective == "coverage_4plus":
            coverage = portfolio_coverage(result.recommended_tickets, threshold=4)
            probability = float(coverage["probability"])
            typer.echo(f"Exact 4+ main-number coverage: {probability:.2%}")
        five = five_plus_metrics(result.recommended_tickets)
        typer.echo(f"Exact 5+ main-number coverage: {five['probability']:.4%}")
        typer.echo(f"Maximum possible with 14 lines: {five['max_probability']:.4%}")
        typer.echo(f"Proven 5+ maximum attained: {five['is_optimal']}")
        if five["with_matching_strong_probability"] is not None:
            typer.echo(
                "Exact 5+ main AND strong-number coverage: "
                f"{five['with_matching_strong_probability']:.4%} (1 in 6,216)"
            )
        typer.echo(
            "These are exact probabilities under a uniform 6-of-37 draw model; "
            "they are not predictions of winning numbers."
        )
        typer.echo(
            "The 5+ maximum is just 1 chance in 888 per fair draw, not a guarantee. "
            "Smart 4+ already reaches it. No combination selection can raise "
            "this probability with the same 14 valid unique lines."
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
        elif smart_objective in {"coverage_4plus", "coverage_5plus"}:
            typer.echo(
                "Portfolio goal: maximize the probability of at least one "
                "ticket hitting 4+ or 5+ main numbers. The same 14-line "
                "portfolio is mathematically optimal for both thresholds."
            )
            typer.echo(
                "The 5+ goal does not guarantee five hits, predict the draw "
                "or improve jackpot odds."
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



@app.command("score-snapshot")
def score_snapshot_command(
    snapshot_file: Annotated[Path, typer.Argument(help="Frozen pre-draw JSON record.")],
    draw_id: Annotated[str, typer.Option("--draw-id", help="Official result draw ID.")],
    draw_date: Annotated[str, typer.Option("--draw-date", help="Official date, e.g. 13-10-26.")],
    main: Annotated[str, typer.Option("--main", help="Six official main numbers, comma-separated.")],
    strong: Annotated[int, typer.Option("--strong", help="Official strong number (1–7).")],
    source_url: Annotated[str, typer.Option("--source-url", help="HTTPS source for independently checked official result.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Destination for separate, no-overwrite scored JSON.")],
) -> None:
    """Score a frozen record after the target draw; never edit the prediction."""
    try:
        frozen = json.loads(snapshot_file.read_text(encoding="utf-8"))
        numbers = tuple(int(piece.strip()) for piece in main.split(","))
        draw = LotteryDrawRecord(
            draw_id=draw_id, numbers=numbers, date=draw_date, strong_number=strong,
        )
        scored = score_snapshot(frozen, draw, source_url=source_url)
        result_path = write_score(scored, output_dir)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(f"cannot score snapshot: {exc}") from exc
    typer.echo(f"Scored result: {result_path}")
    typer.echo(f"Record SHA-256: {scored['result_sha256']}")
    typer.echo(f"Any prize: {scored['any_prize']}")
    typer.echo(f"Best main matches: {scored['best_main_matches']}")
    typer.echo(f"Best prize tier: {scored['best_prize_tier']}")
    typer.echo("Result source URL is user-supplied and has not been independently verified.")




@app.command("bias-freeze")
def bias_freeze(
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory for a single frozen, hashed model JSON.")],
) -> None:
    """Freeze ONE frequency-bias hypothesis for future draws; not a predictor."""
    root = Path(__file__).resolve().parents[2]
    data_file = root / "data" / "lottery.csv"
    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip()
        dataset = CsvDatasetLoader().load(data_file)
        model = freeze_bias_model(dataset, data_file, git_commit)
        saved = write_immutable(model, output_dir)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise typer.BadParameter(f"could not freeze hypothesis: {exc}") from exc
    typer.echo(f"Frozen audit model: {saved}")
    typer.echo(f"Record SHA-256: {model['record_sha256']}")
    typer.echo("CRITICAL: Publish this JSON with an independently verifiable timestamp before using any future result.")
    typer.echo("The old 1,141 historical draws are training data, NOT evidence of a predictive advantage.")


@app.command("bias-score")
def bias_score(
    frozen_file: Annotated[Path, typer.Option("--frozen", help="Pre-published frozen model JSON.")],
    draw_id: Annotated[str, typer.Option("--draw-id", help="Next consecutive official draw ID.")],
    draw_date: Annotated[str, typer.Option("--draw-date", help="Draw's official local date.")],
    draw_at: Annotated[str, typer.Option("--draw-at", help="Actual draw time, with timezone offset.")],
    main: Annotated[str, typer.Option("--main", help="Six official main numbers separated by commas.")],
    strong: Annotated[int, typer.Option("--strong", help="Official strong number.")],
    source_url: Annotated[str, typer.Option("--source-url", help="Externally verified official HTTPS results page.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory for immutable evidence JSON.")],
    previous_score: Annotated[Path | None, typer.Option("--previous-score", help="Previous consecutive result record, required from draw 2 onwards.")] = None,
) -> None:
    """Append one post-draw result to the fixed anytime-valid hypothesis test."""
    try:
        frozen = json.loads(frozen_file.read_text(encoding="utf-8"))
        previous = (
            json.loads(previous_score.read_text(encoding="utf-8"))
            if previous_score is not None else None
        )
        numbers = tuple(int(value.strip()) for value in main.split(","))
        draw = LotteryDrawRecord(draw_id=draw_id, date=draw_date, numbers=numbers, strong_number=strong)
        actual_time = datetime.fromisoformat(draw_at.replace("Z", "+00:00"))
        evidence = score_future_draw(
            frozen, draw, draw_occurred_at=actual_time,
            source_url=source_url, previous=previous,
        )
        path = write_immutable(evidence, output_dir)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(f"could not score future bias evidence: {exc}") from exc
    typer.echo(f"Immutable evidence: {path}")
    typer.echo(f"Draws scored prospectively: {evidence['draw_number']}")
    typer.echo(f"Cumulative log e-value: {evidence['cumulative_log_e']:+.6f}")
    typer.echo(f"Evidence threshold ever reached: {evidence['anytime_valid_evidence_threshold_ever_reached']}")
    typer.echo("This tests a frozen possible bias; it does NOT demonstrate greater 5+ win odds.")
    typer.echo("The supplied official-source URL is metadata, not independently authenticated.")



def main() -> None:
    """Run the LREI command-line application."""

    app()
