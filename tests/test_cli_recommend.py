from pathlib import Path

from typer.testing import CliRunner

from lrei.cli import app


runner = CliRunner()


def test_recommend_command_runs_successfully():
    result = runner.invoke(
        app,
        [
            "recommend",
            "--tickets",
            "10",
            "--seed",
            "42",
        ],
    )

    assert result.exit_code == 0
    assert "LREI LOTTERY RECOMMENDATIONS" in result.output
    assert "Dataset draws:" in result.output
    assert "Generated tickets: 10" in result.output
    assert "Recommended tickets:" in result.output
    assert "RECOMMENDED LOTTERY TICKETS" in result.output


def test_recommend_command_produces_ticket_output():
    result = runner.invoke(
        app,
        [
            "recommend",
            "--tickets",
            "10",
            "--seed",
            "42",
        ],
    )

    assert result.exit_code == 0
    assert "Ticket 01:" in result.output


def test_recommend_command_is_reproducible():
    first = runner.invoke(
        app,
        [
            "recommend",
            "--tickets",
            "10",
            "--seed",
            "123",
        ],
    )

    second = runner.invoke(
        app,
        [
            "recommend",
            "--tickets",
            "10",
            "--seed",
            "123",
        ],
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first.output == second.output


def test_recommend_command_rejects_zero_tickets():
    result = runner.invoke(
        app,
        [
            "recommend",
            "--tickets",
            "0",
        ],
    )

    assert result.exit_code != 0
    assert "greater than zero" in result.output


def test_recommend_command_rejects_negative_tickets():
    result = runner.invoke(
        app,
        [
            "recommend",
            "--tickets",
            "-10",
        ],
    )

    assert result.exit_code != 0
    assert "greater than zero" in result.output


def test_recommend_command_accepts_short_options():
    result = runner.invoke(
        app,
        [
            "recommend",
            "-t",
            "10",
            "--seed",
            "42",
        ],
    )

    assert result.exit_code == 0
    assert "Generated tickets: 10" in result.output


def test_recommend_command_uses_default_values():
    result = runner.invoke(
        app,
        [
            "recommend",
        ],
    )

    assert result.exit_code == 0
    assert "Generated tickets: 50" in result.output


def test_recommend_command_shows_number_scores():
    result = runner.invoke(
        app,
        [
            "recommend",
            "--tickets",
            "10",
            "--seed",
            "42",
        ],
    )

    assert result.exit_code == 0
    assert "TOP NUMBER SCORES" in result.output
    assert "Number" in result.output


def test_recommend_command_finishes_with_separator():
    result = runner.invoke(
        app,
        [
            "recommend",
            "--tickets",
            "10",
            "--seed",
            "42",
        ],
    )

    assert result.exit_code == 0

    assert (
        result.output.rstrip().endswith("=" * 70)
    )
