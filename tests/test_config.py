"""Tests for environment-backed application configuration."""

from pathlib import Path

import pytest

from lrei.config import Settings


def test_settings_honor_environment_values(tmp_path: Path) -> None:
    database_path = tmp_path / "custom.sqlite3"

    settings = Settings.from_environment(
        {
            "LREI_DATA_DIR": str(tmp_path),
            "LREI_DATABASE": str(database_path),
            "LREI_LOG_LEVEL": "debug",
        }
    )

    assert settings.data_dir == tmp_path
    assert settings.database_path == database_path
    assert settings.log_level == "DEBUG"


def test_settings_reject_invalid_log_level() -> None:
    with pytest.raises(ValueError, match="LREI_LOG_LEVEL"):
        Settings.from_environment({"LREI_LOG_LEVEL": "verbose"})
