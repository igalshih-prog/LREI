"""P1 real Streamlit script execution smoke, without claiming a browser E2E pass.

Runs the actual app.py in Streamlit's supported headless AppTest harness.
Only checks startup and changing the mode, not ticket generation or download.
The app's default CSV must remain available. Requires pip install -e '.[ui]'.
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "app.py"


def test_app_starts_with_archived_csv_and_no_uncaught_exception():
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    assert at.title and "LREI" in at.title[0].value
    assert len(at.radio) == 1
    assert at.radio[0].value == "Smart"
    assert "Regular" in at.radio[0].options
    assert "Pro" in at.radio[0].options
    assert "Coverage" in at.radio[0].options
    assert len(at.button) >= 1
    assert "צור 14 טורים" in at.button[0].label


def test_all_four_modes_render_without_running_engines():
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    for mode in ("Regular", "Pro", "Coverage", "Smart"):
        at.radio[0].set_value(mode).run()
        assert not at.exception, f"Mode {mode} failed to render"
        assert mode in at.button[0].label
    assert at.selectbox


def test_smart_coverage_objective_copy_is_visible():
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    assert at.radio[0].value == "Smart"
    assert len(at.selectbox) == 1
    assert any("5+" in opt for opt in at.selectbox[0].options)
    at.selectbox[0].set_value("מקסום הסיכוי לזכייה כלשהי (3+ ראשיים)").run()
    assert not at.exception
    assert any("2,324,784" in info.value for info in at.info)
