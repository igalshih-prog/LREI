"""Exercise real Smart 5+ ticket generation in Streamlit's headless runtime.

This is not a browser test: file-upload/download interactions still need an
actual browser E2E check. It deliberately does not forecast a future draw.
"""
from itertools import combinations
from pathlib import Path
import re

import pytest

AppTest = pytest.importorskip(
    "streamlit.testing.v1", reason="Streamlit is an optional UI dependency"
).AppTest

APP = Path(__file__).resolve().parents[2] / "app.py"
TICKET_PATTERN = re.compile(
    r"\*\*טור (\d{2}):\*\* ((?:\d{2} - ){5}\d{2}) \| ⭐ Strong: ([1-7])"
)


def test_smart_five_plus_click_produces_fourteen_valid_distinct_lines():
    screen = AppTest.from_file(str(APP), default_timeout=180).run()
    assert not screen.exception
    assert screen.radio[0].value == "Smart"
    assert screen.selectbox[0].value == "מקסום כיסוי ל־5+ (וגם 4+) — 14 טורים"

    screen.button[0].click().run()
    assert not screen.exception, "Smart generation crashed after clicking the UI"

    lines = [
        element.value
        for element in screen.markdown
        if element.value.startswith("**טור ")
    ]
    assert len(lines) == 14
    main_lines = []
    for index, line in enumerate(lines, 1):
        match = TICKET_PATTERN.fullmatch(line.strip())
        assert match is not None, f"Invalid rendered ticket: {line!r}"
        assert int(match.group(1)) == index
        numbers = tuple(int(part) for part in match.group(2).split(" - "))
        strong = int(match.group(3))
        assert numbers == tuple(sorted(set(numbers)))
        assert len(numbers) == 6 and all(1 <= number <= 37 for number in numbers)
        assert 1 <= strong <= 7
        main_lines.append(numbers)

    assert len(set(main_lines)) == 14
    # The default Smart 5+ objective promises optimal 4+/5+ disjoint coverage.
    assert all(
        len(set(left) & set(right)) <= 1
        for left, right in combinations(main_lines, 2)
    )
    assert any(
        metric.label == "טורים מומלצים"
        and str(metric.value).replace(",", "") == "14"
        for metric in screen.metric
    )
    assert any(metric.label == "לפחות 5/6 ראשיים" for metric in screen.metric)


def test_streamlit_warns_research_only_even_when_it_renders_normally():
    screen = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not screen.exception
    # The banner applies to the repository's default CSV and never treats
    # valid local contents or green CI as proof of first-party provenance.
    assert len(screen.warning) >= 1
