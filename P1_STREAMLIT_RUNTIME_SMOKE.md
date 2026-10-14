# P1 — Streamlit app runtime smoke gate

This check addresses a documented P1 gap: compiling `app.py` does not
show that the Streamlit script actually starts.

The standalone GitHub workflow `P1 Streamlit UI smoke` installs the real
optional Streamlit dependency (`pip install -e '.[ui]' pytest`) and uses
the documented `streamlit.testing.v1.AppTest` runtime.

The tests execute `app.py` with the existing historical CSV, verify
its initial title/default Smart mode, switch through Regular, Pro,
Coverage and Smart, and display the Smart any-prize objective description.

This is **headless Streamlit script + widget simulation**, *not* a live
browser Selenium/Playwright test, not proof that generating a set of
14 tickets completes, not a file-upload or TXT-download end-to-end
verification, and not any predictive/financial advantage.
In particular, existing P1 browser workflow acceptance gates remain
open until those heavier checks can be run and evidenced.

Tests are isolated in `tests/ui` because base package installation
does not require Streamlit; the default `pytest tests/` must not
import an unavailable optional dependency. The dedicated CI workflow
triggers only for UI-relevant files.

Run:

```bash
python -m pip install -e '.[ui]' pytest
python -m pytest -q tests/ui/test_streamlit_app_smoke.py
```

P3 prize data is unchanged at **6/20** operator display observations
and 14 missing full official regular+Double Lotto tier tables. The
source-access dependency remains [issue #18](https://github.com/igalshih-prog/LREI/issues/18).
