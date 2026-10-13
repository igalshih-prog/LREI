"""Basic Streamlit runtime smoke: launch the real app, not just compile it.

UI-level generation and downloading still require a manual browser test.
"""

from pathlib import Path

import pytest

# Streamlit is an optional dependency; the dedicated UI CI job installs it.
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_streamlit_launches_with_default_dataset_and_objective_selectors():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    screen = AppTest.from_file(str(app_path), default_timeout=45).run()
    assert not screen.exception
    assert screen.title[0].value == "🎯 LREI"
    assert int(str(screen.metric[0].value).replace(",", "")) == 1141
    assert screen.radio[0].value == "Smart"

    assert not screen.exception
    assert len(screen.selectbox) == 1
    assert screen.selectbox[0].value == "מקסום כיסוי ל־5+ (וגם 4+) — 14 טורים"

    screen.selectbox[0].set_value(
        "מקסום כיסוי ל־4+ במספרים הראשיים"
    ).run()
    assert not screen.exception
    screen.selectbox[0].set_value(
        "מקסום הסיכוי לזכייה כלשהי (3+ ראשיים)"
    ).run()
    assert not screen.exception
    assert screen.button[0].label.startswith("🎲 צור 14 טורים")

    screen.radio[0].set_value("Pro").run()
    assert not screen.exception
    assert len(screen.selectbox) == 0
