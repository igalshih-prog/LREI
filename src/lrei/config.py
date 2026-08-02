"""Application configuration loaded from the environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir

_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for the LREI application."""

    data_dir: Path
    database_path: Path
    log_level: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Settings:
        """Create settings from LREI-prefixed environment variables."""
        values = os.environ if environment is None else environment
        data_dir = Path(
            values.get("LREI_DATA_DIR", user_data_dir("lrei", "LREI"))
        ).expanduser()
        database_path = Path(
            values.get("LREI_DATABASE", str(data_dir / "lrei.sqlite3"))
        ).expanduser()
        log_level = values.get("LREI_LOG_LEVEL", "INFO").upper()

        if log_level not in _LOG_LEVELS:
            allowed = ", ".join(sorted(_LOG_LEVELS))
            raise ValueError(f"LREI_LOG_LEVEL must be one of: {allowed}")

        return cls(
            data_dir=data_dir,
            database_path=database_path,
            log_level=log_level,
        )
