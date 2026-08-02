"""Tests for the Typer command-line interface."""

from pathlib import Path

from typer.testing import CliRunner

from lrei.cli import app

runner = CliRunner()


def test_cli_can_add_and_list_entries(tmp_path: Path) -> None:
    database_path = tmp_path / "lrei.sqlite3"

    add_result = runner.invoke(app, ["add", "Hello", "--database", str(database_path)])
    list_result = runner.invoke(app, ["list", "--database", str(database_path)])

    assert add_result.exit_code == 0
    assert "Added entry 1: Hello" in add_result.stdout
    assert list_result.exit_code == 0
    assert "Hello" in list_result.stdout


def test_cli_displays_resolved_configuration(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["config"],
        env={"LREI_DATA_DIR": str(tmp_path), "LREI_LOG_LEVEL": "WARNING"},
    )

    assert result.exit_code == 0
    assert f"data_dir={tmp_path}" in result.stdout
    assert "log_level=WARNING" in result.stdout
