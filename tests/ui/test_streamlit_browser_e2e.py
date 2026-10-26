"""End-to-end real Chromium check of research-only Streamlit file IO.

Runs only with LREI_BROWSER_E2E=1 and the optional Playwright dependency.
Uses a truncated copy of our existing committed historical CSV as *test
input*, never a fabricated or certified new Lotto draw. No money is spent.
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "lottery.csv"


@pytest.mark.skipif(
    os.environ.get("LREI_BROWSER_E2E") != "1",
    reason="Explicit browser-E2E opt-in required; core CI stays browser-free",
)
def test_real_browser_upload_generate_and_download(tmp_path: Path) -> None:
    # Keep Playwright optional for the normal fast/slow test matrix.
    sync_api = pytest.importorskip("playwright.sync_api")
    with socket.socket() as bound:
        bound.bind(("127.0.0.1", 0))
        port = bound.getsockname()[1]

    # Exactly one original committed draw is deliberately omitted, letting the
    # browser assert it actually processed uploaded data rather than defaults.
    rows = HISTORY.read_bytes().splitlines(keepends=True)
    assert len(rows) > 1000
    uploaded = b"".join(rows[:-1])
    uploaded_draws = len(rows) - 2
    assert uploaded_draws > 1000

    logfile = tmp_path / "streamlit-browser-e2e.log"
    with logfile.open("wb") as log:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.headless=true",
                "--server.address=127.0.0.1",
                f"--server.port={port}",
                "--browser.gatherUsageStats=false",
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    pytest.fail("Streamlit terminated before health check: " + logfile.read_text(errors="replace")[-3500:])
                try:
                    with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except (OSError, URLError):
                    time.sleep(0.3)
            else:
                pytest.fail("Streamlit did not become healthy: " + logfile.read_text(errors="replace")[-3500:])

            with sync_api.sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    page = browser.new_page(accept_downloads=True)
                    page.set_default_timeout(30000)
                    page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded")
                    expect = sync_api.expect
                    expect(page.get_by_text("NO PLAY", exact=False).first).to_be_visible(timeout=30000)

                    page.locator('input[type="file"]').set_input_files(
                        {"name": "e2e-historical-subset.csv", "mimeType": "text/csv", "buffer": uploaded}
                    )
                    expect(
                        page.get_by_text(f"{uploaded_draws} הגרלות נותחו", exact=False)
                    ).to_be_visible(timeout=30000)
                    # Uploading plausible local data must NOT imply operator
                    # authentication or disable the NO PLAY notice.
                    expect(page.get_by_text("NO PLAY", exact=False).first).to_be_visible()

                    page.get_by_role("button", name=re.compile("צור 14 טורים")).click()
                    expect(page.locator("p").filter(has_text=re.compile(r"^טור 14:"))).to_be_visible(timeout=120000)
                    lines = page.locator("p").filter(
                        has_text=re.compile(r"^טור [0-9]{2}:")
                    ).all_text_contents()
                    assert len(lines) == 14, lines
                    seen: set[tuple[int, ...]] = set()
                    for idx, line in enumerate(lines, 1):
                        match = re.fullmatch(
                            r"טור ([0-9]{2}): ((?:[0-9]{2} - ){5}[0-9]{2}) \| ⭐ Strong: ([1-7])",
                            line.strip(),
                        )
                        assert match is not None, line
                        assert int(match.group(1)) == idx
                        numbers = tuple(int(n) for n in match.group(2).split(" - "))
                        assert numbers == tuple(sorted(set(numbers)))
                        assert all(1 <= n <= 37 for n in numbers)
                        assert numbers not in seen
                        seen.add(numbers)

                    with page.expect_download(timeout=30000) as downloaded:
                        page.get_by_role("button", name=re.compile("הורד את 14 הטורים")).click()
                    data = downloaded.value
                    assert data.suggested_filename == "lrei_tickets.txt"
                    target = tmp_path / data.suggested_filename
                    data.save_as(str(target))
                    output = target.read_text(encoding="utf-8").splitlines()
                    assert len(output) == 14
                    for idx, line in enumerate(output, 1):
                        assert re.fullmatch(
                            rf"Ticket {idx:02d}: (?:[0-9]{{2}} - ){{5}}[0-9]{{2}} \| Strong: [1-7]",
                            line,
                        ), line
                    # File reflects the just-rendered tickets exactly.
                    assert [
                        value.replace("טור ", "Ticket ").replace("⭐ Strong", "Strong")
                        for value in lines
                    ] == output
                finally:
                    browser.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
