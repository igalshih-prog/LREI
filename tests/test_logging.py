"""Ensure repeated CLI invocations never retain a closed output stream."""

import io
import logging

from lrei.logging import configure_logging


def test_logging_rebinds_closed_stderr_without_duplicate_records(monkeypatch):
    logger = logging.getLogger("lrei")
    old_handlers = logger.handlers[:]
    old_level, old_propagate = logger.level, logger.propagate
    logger.handlers = []
    first, second = io.StringIO(), io.StringIO()
    try:
        monkeypatch.setattr("sys.stderr", first)
        configure_logging("DEBUG")
        logger.info("first invocation")
        first.close()
        monkeypatch.setattr("sys.stderr", second)
        configure_logging("INFO")
        configure_logging("INFO")
        logger.info("second invocation")
        assert second.getvalue().count("second invocation") == 1
        assert "Logging error" not in second.getvalue()
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate


def test_direct_library_logging_after_cli_capture_closes(monkeypatch):
    logger = logging.getLogger("lrei")
    old_handlers = logger.handlers[:]
    old_level, old_propagate = logger.level, logger.propagate
    logger.handlers = []
    first, second = io.StringIO(), io.StringIO()
    try:
        monkeypatch.setattr("sys.stderr", first)
        configure_logging("INFO")
        first.close()
        monkeypatch.setattr("sys.stderr", second)
        # No second configure call: a library client may log directly.
        logging.getLogger("lrei.database").info("direct library call")
        assert second.getvalue().count("direct library call") == 1
        assert "Logging error" not in second.getvalue()
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate
