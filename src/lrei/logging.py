"""Logging configuration for command-line and library entry points."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure the package logger without changing unrelated loggers."""
    logger = logging.getLogger("lrei")
    logger.setLevel(level)

    # CliRunner replaces and then closes stderr after each invocation. Rebind
    # our handler on every call so later commands never log to a closed stream.
    for existing in tuple(logger.handlers):
        if getattr(existing, "_lrei_owned", False):
            logger.removeHandler(existing)
            existing.close()
    handler = logging.StreamHandler()
    handler._lrei_owned = True
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
