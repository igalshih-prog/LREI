"""Synthetic/offline checks for the official-number CSV audit gate.

No synthetic bytes are labeled as a real operator download or draw protocol.
"""

from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from lrei.lottery.dataset import LotteryDataset, LotteryDrawRecord
from lrei.lottery.official_draw_source import (
    OFFICIAL_CSV_URL,
    OfficialCsvAuditError,
    download_operator_csv,
    inspect_official_csv,
)


def history(strong=2):
    return LotteryDataset([
        LotteryDrawRecord(
            "3974", (3, 4, 18, 19, 34, 35),
            date="13-10-26", strong_number=strong
        )
    ])


def raw_csv(*, strong=2, number_line=None):
    header = (
        "מספר הגרלה,תאריך,מספר 1,מספר 2,מספר 3,מספר 4,"
        "מספר 5,מספר 6,מספר חזק\n"
    )
    previous = "3973,10/10/2026,1,4,7,22,32,34,2\n"
    target = number_line or f"3974,13/10/2026,3,4,18,19,34,35,{strong}\n"
    return (header + previous + target).encode("cp1255")


def inspect(data, **kwargs):
    return inspect_official_csv(
        data, history(), expected_draw_id=3974,
        captured_at_utc=datetime(2026, 10, 15, 12, tzinfo=timezone.utc),
        **kwargs,
    )


def test_valid_csv_matches_but_offline_source_not_authenticated():
    data = raw_csv()
    result = inspect(data)
    import hashlib
    assert result["source_sha256"] == hashlib.sha256(data).hexdigest()
    assert result["draw_date"] == "2026-10-13"
    assert result["main"] == [3, 4, 18, 19, 34, 35]
    assert result["strong"] == 2
    assert result["source_encoding"] == "cp1255"
    assert result["direct_https_download_performed_by_tool"] is False
    assert result["legally_binding_protocol_verified"] is False
    assert result["human_source_review_required"] is True
    assert result["counted_as_prospective_prediction"] is False


@pytest.mark.parametrize("data, message", [
    (raw_csv(strong=3), "disagrees"),
    (raw_csv(number_line="3974,13/10/2026,3,4,18,19,34,36,2\n"), "disagrees"),
    (raw_csv(number_line="3974,14/10/2026,3,4,18,19,34,35,2\n"), "disagrees"),
    (raw_csv(number_line="3974,13/10/2026,3,4,18,19,34,34,2\n"), "invalid Lotto"),
    (raw_csv(number_line="3974,13/10/2026,3,4,18,19,34,35,8\n"), "invalid Lotto"),
    (raw_csv(number_line="3975,13/10/2026,3,4,18,19,34,35,2\n"), "exactly one"),
    (raw_csv() + b"3974,13/10/2026,3,4,18,19,34,35,2\n", "exactly one"),
    (b"<html>request blocked</html>", "HTML"),
    (b"", "1"),
    (raw_csv(number_line="3974,13/10/2026,3,4,18\n"), "expected ID"),
    (raw_csv(number_line="3974,not-a-date,3,4,18,19,34,35,2\n"), "invalid date"),
])
def test_fail_closed_on_missing_conflicting_or_malformed_rows(data, message):
    with pytest.raises(OfficialCsvAuditError, match=message):
        inspect(data)


def test_non_pais_source_url_rejected():
    with pytest.raises(OfficialCsvAuditError, match="first-party"):
        inspect(raw_csv(), source_url="https://pais.co.il.evil.example/fake.csv")


def test_future_dated_capture_rejected():
    with pytest.raises(OfficialCsvAuditError, match="cannot predate"):
        inspect_official_csv(
            raw_csv(), history(), expected_draw_id=3974,
            captured_at_utc=datetime(2026, 10, 12, tzinfo=timezone.utc),
        )


def test_wrong_local_history_or_target_id_rejected():
    with pytest.raises(OfficialCsvAuditError, match="disagrees"):
        inspect_official_csv(raw_csv(), history(1), expected_draw_id=3974)
    with pytest.raises(OfficialCsvAuditError, match="latest draw"):
        inspect_official_csv(raw_csv(), history(), expected_draw_id=3973)


def test_direct_download_rejects_external_redirect(monkeypatch):
    class FakeResponse:
        headers = {"Content-Type": "text/csv"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def geturl(self):
            return "https://untrusted.invalid/export.csv"

        def read(self, count):
            raise AssertionError("must reject redirect before reading data")

    def fake_urlopen(request, *, timeout, context):
        assert request.full_url == OFFICIAL_CSV_URL
        assert timeout > 0 and context is not None
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(OfficialCsvAuditError, match="first-party"):
        download_operator_csv()


def test_offline_cli_produces_unverified_report_without_network(tmp_path, monkeypatch):
    from lrei.lottery import official_draw_source

    csv_path = tmp_path / "original.csv"
    csv_path.write_bytes(raw_csv())
    historical = tmp_path / "lottery.csv"
    historical.write_text(
        "draw_id\tnumbers\tdate\tstrong_number\n"
        "3974\t03,04,18,19,34,35\t13-10-26\t2\n",
        encoding="utf-8",
    )
    result = tmp_path / "report.json"
    raw_copy = tmp_path / "archive-copy.csv"
    monkeypatch.setattr(
        "sys.argv",
        [
            "official-draw-source", "--source-file", str(csv_path),
            "--historical-csv", str(historical),
            "--draw-id", "3974", "--report", str(result),
            "--raw-copy", str(raw_copy),
        ],
    )
    official_draw_source.main()
    saved = json.loads(result.read_text(encoding="utf-8"))
    assert saved["direct_https_download_performed_by_tool"] is False
    assert saved["source_url"] == OFFICIAL_CSV_URL
    assert raw_copy.read_bytes() == csv_path.read_bytes()
    with pytest.raises(SystemExit):
        official_draw_source.main()  # exclusive write rejects overwrite



def test_offline_inspector_cannot_forge_a_tls_download_attestation():
    # Previously this public API accepted True from a caller holding only
    # user-supplied bytes. A local CSV match is never first-party provenance.
    with pytest.raises(OfficialCsvAuditError, match="cannot attest"):
        inspect(raw_csv(), direct_https_download=True)


def test_download_cli_sets_capture_flag_only_after_downloader_returns(
    tmp_path, monkeypatch
):
    from lrei.lottery import official_draw_source

    historical = tmp_path / "history.csv"
    historical.write_text(
        "draw_id\\tnumbers\\tdate\\tstrong_number\\n"
        "3974\\t03,04,18,19,34,35\\t13-10-26\\t2\\n",
        encoding="utf-8",
    )
    report = tmp_path / "network-audit.json"
    calls = []

    def fake_download():
        calls.append(True)
        return raw_csv(), OFFICIAL_CSV_URL, "text/csv"

    monkeypatch.setattr(official_draw_source, "download_operator_csv", fake_download)
    monkeypatch.setattr(
        "sys.argv",
        [
            "official-draw-source", "--download",
            "--historical-csv", str(historical),
            "--draw-id", "3974", "--report", str(report),
        ],
    )
    official_draw_source.main()
    assert calls == [True]
    saved = json.loads(report.read_text(encoding="utf-8"))
    assert saved["direct_https_download_performed_by_tool"] is True
    assert saved["legally_binding_protocol_verified"] is False
    assert saved["human_source_review_required"] is True

    # When a real source request fails, there is no success report to read.
    def denied():
        raise OfficialCsvAuditError("first-party CSV download unavailable: timed out")

    monkeypatch.setattr(official_draw_source, "download_operator_csv", denied)
    failed_report = tmp_path / "failed-source.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "official-draw-source", "--download",
            "--historical-csv", str(historical),
            "--draw-id", "3974", "--report", str(failed_report),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        official_draw_source.main()
    assert exc.value.code == 2
    assert not failed_report.exists()
