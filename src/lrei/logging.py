"""Logging configuration for command-line and library entry points."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure the package logger without changing unrelated loggers."""
    logger = logging.getLogger("lrei")
    logger.setLevel(level)

    if logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
