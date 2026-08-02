"""Tests for the public package interface."""

import lrei


def test_version_is_exposed() -> None:
    """The package exposes a semantic version string."""
    assert lrei.__version__ == "0.1.0"
