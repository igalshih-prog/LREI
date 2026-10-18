"""P3-A.2 audit regression tests: source integrity and visible incomplete window."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.prize_data import PrizeDataError, load_observation
from lrei.lottery.prize_series_audit import audit_prize_series

ROOT = Path(__file__).resolve().parents[2]
RECORDS = ROOT / "data" / "prize_observations"
MANIFEST = ROOT / "data" / "prize_audit" / "3949-3968.manifest.json"
HISTORY = ROOT / "data" / "lottery.csv"


def historic():
    return CsvDatasetLoader().load(HISTORY)


def test_six_real_consecutive_draws_are_individually_crosschecked():
    dataset = historic()
    observed = [load_observation(RECORDS / f"{n}.json", dataset) for n in (3949, 3950, 3951, 3952, 3953, 3954)]
    assert [o["draw_id"] for o in observed] == [3949, 3950, 3951, 3952, 3953, 3954]
    assert [o["strong_number"] for o in observed] == [6, 7, 4, 4, 7, 6]
    assert [o["draw_date"] for o in observed] == ["2026-07-25", "2026-07-28", "2026-08-01", "2026-08-04", "2026-08-08", "2026-08-11"]
    assert len([r for o in observed for r in o["games"]["regular"]]) == 48
    assert len([r for o in observed for r in o["games"]["double"]]) == 48


def test_audit_does_not_pretend_six_observations_are_twenty():
    summary = audit_prize_series(RECORDS, MANIFEST, historic())
    assert summary["window_start_draw_id"] == 3949
    assert summary["window_end_draw_id"] == 3968
    assert summary["expected_draws"] == 20
    assert summary["observed_draws"] == summary["source_audits"] == 6
    assert summary["missing_draw_ids"] == list(range(3955, 3969))
    assert summary["series_complete"] is False
    assert summary["review_method_counts"] == {"indexed_operator_page_text": 1, "manual_operator_page_comparison": 5}
    assert summary["source_raw_bytes_available"] is False
    assert summary["approved_protocols_verified"] is False
    assert summary["official_sales_data_available"] is False
    assert summary["eligible_for_financial_prediction"] is False
    assert summary["missing_prize_tier_rows"] == 14 * 16 == 224
    assert summary["source_manifest_sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert summary["p3_economic_readiness"]["decision"] == "NO_PLAY"
    assert summary["p3_economic_readiness"]["data_readiness_ok"] is False
    assert summary["p3_economic_readiness"]["source_authenticity_verified"] is False
    assert "missing_16_tier_prize_tables" in summary["p3_economic_readiness"]["blocking_reasons"]


def test_payout_reconciliation_does_not_mislabel_extra_as_lotto():
    result = audit_prize_series(RECORDS, MANIFEST, historic())
    examples = result["accounting"]
    assert examples["3949"]["known_regular_lotto_payout_ils"] + examples["3949"]["known_double_lotto_payout_ils"] == 6_681_465
    assert examples["3949"]["operator_all_games_total_ils"] == 7_646_745
    assert examples["3949"]["operator_total_minus_lotto_sum_ils"] == 965_280
    assert examples["3950"]["operator_total_minus_lotto_sum_ils"] == 984_305
    assert examples["3951"]["operator_total_minus_lotto_sum_ils"] == 1_157_330
    assert examples["3952"]["operator_total_minus_lotto_sum_ils"] == 1_264_505
    assert examples["3953"]["operator_total_minus_lotto_sum_ils"] == 1_472_520
    assert examples["3954"]["operator_total_minus_lotto_sum_ils"] == 521_520
    assert examples["3954"]["known_regular_lotto_payout_ils"] == 1_734_564
    assert examples["3954"]["known_double_lotto_payout_ils"] == 2_088_288
    jackpot = load_observation(RECORDS / "3953.json", historic())
    assert jackpot["games"]["regular"][0]["winning_entries"] == 1
    assert jackpot["games"]["regular"][0]["payout_per_winning_entry_ils"] == 40_000_000
    assert all(len(o["observation_sha256"]) == 64 for o in examples.values())


def sandbox(tmp_path):
    directory = tmp_path / "records"
    directory.mkdir()
    for n in (3949, 3950, 3951, 3952, 3953, 3954):
        (directory / f"{n}.json").write_bytes((RECORDS / f"{n}.json").read_bytes())
    manifest_file = tmp_path / "audit.json"
    manifest_file.write_bytes(MANIFEST.read_bytes())
    return directory, manifest_file


def change_manifest(path, fn):
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_duplicate_source_audit_cannot_pass(tmp_path):
    directory, manifest = sandbox(tmp_path)
    change_manifest(manifest, lambda doc: doc["sources"].append(copy.deepcopy(doc["sources"][0])))
    with pytest.raises(PrizeDataError, match="source audit"):
        audit_prize_series(directory, manifest, historic())


def test_fabricated_raw_source_hash_cannot_pass(tmp_path):
    directory, manifest = sandbox(tmp_path)
    change_manifest(manifest, lambda doc: doc["sources"][0].update(raw_source_sha256="a"*64))
    with pytest.raises(PrizeDataError, match="raw source not archived"):
        audit_prize_series(directory, manifest, historic())


def test_indexed_source_requires_explicit_source_access_note(tmp_path):
    directory, manifest = sandbox(tmp_path)
    change_manifest(manifest, lambda doc: doc["sources"][-1].update(review_notes="Looked at the page"))
    with pytest.raises(PrizeDataError, match="indexed operator-page review"):
        audit_prize_series(directory, manifest, historic())


def test_review_method_cannot_claim_unrecorded_verification_mode(tmp_path):
    directory, manifest = sandbox(tmp_path)
    change_manifest(manifest, lambda doc: doc["sources"][-1].update(review_method="approved_protocol"))
    with pytest.raises(PrizeDataError, match="audit method"):
        audit_prize_series(directory, manifest, historic())


def test_approved_protocol_cannot_be_claimed_without_proof(tmp_path):
    directory, manifest = sandbox(tmp_path)
    change_manifest(manifest, lambda doc: doc["sources"][0].update(approved_protocol_verified=True))
    with pytest.raises(PrizeDataError, match="approved draw protocol"):
        audit_prize_series(directory, manifest, historic())


def test_mismatched_provenance_draw_page_is_rejected(tmp_path):
    directory, manifest = sandbox(tmp_path)
    change_manifest(manifest, lambda doc: doc["sources"][1].update(source_url="https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=9999"))
    with pytest.raises(PrizeDataError, match="URL"):
        audit_prize_series(directory, manifest, historic())


def test_source_review_before_draw_is_rejected(tmp_path):
    directory, manifest = sandbox(tmp_path)
    change_manifest(manifest, lambda doc: doc["sources"][0].update(reviewed_on_utc_date="2026-07-24"))
    with pytest.raises(PrizeDataError, match="before the draw"):
        audit_prize_series(directory, manifest, historic())


def test_observation_corruption_is_rejected(tmp_path):
    directory, manifest = sandbox(tmp_path)
    path = directory / "3951.json"
    record = json.loads(path.read_text())
    record["games"]["double"].pop()
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(PrizeDataError, match="eight prize tiers"):
        audit_prize_series(directory, manifest, historic())


def test_filename_draw_id_mismatch_rejected(tmp_path):
    directory, manifest = sandbox(tmp_path)
    (directory / "3951.json").rename(directory / "3952.json")
    with pytest.raises(PrizeDataError, match="filename disagrees"):
        audit_prize_series(directory, manifest, historic())


def test_unexpected_draw_and_duplicate_alias_fail_closed(tmp_path):
    directory, manifest = sandbox(tmp_path)
    (directory / "03949.json").write_bytes((directory / "3949.json").read_bytes())
    with pytest.raises(PrizeDataError, match="canonical numeric"):
        audit_prize_series(directory, manifest, historic())
    (directory / "03949.json").unlink()
    (directory / "3973.json").write_bytes((directory / "3951.json").read_bytes())
    with pytest.raises(PrizeDataError, match="outside declared"):
        audit_prize_series(directory, manifest, historic())


def test_true_gap_is_exposed_not_counted_as_a_success(tmp_path):
    directory, manifest = sandbox(tmp_path)
    (directory / "3951.json").unlink()
    # Audit metadata now falsely claims a source for a missing observation.
    with pytest.raises(PrizeDataError, match="exactly one source audit"):
        audit_prize_series(directory, manifest, historic())
    # Remove orphan metadata: the gap is reported, never silently filled.
    change_manifest(manifest, lambda doc: doc.update(sources=[source for source in doc["sources"] if source["draw_id"] != 3951]))
    report = audit_prize_series(directory, manifest, historic())
    assert report["observed_draws"] == 5
    assert report["missing_draw_ids"] == [3951, *range(3955, 3969)]


@pytest.mark.parametrize("bad", [True, 0, "1", 2])
def test_wrong_manifest_schema_rejected(tmp_path, bad):
    directory, manifest = sandbox(tmp_path)
    change_manifest(manifest, lambda doc: doc.update(schema_version=bad))
    with pytest.raises(PrizeDataError, match="schema"):
        audit_prize_series(directory, manifest, historic())


def test_prize_readiness_report_cli_exclusive_write_and_no_play(tmp_path):
    output = tmp_path / "p3a-readiness.json"
    command = [
        sys.executable, "-m", "lrei.lottery.prize_series_audit",
        "--observations-dir", str(RECORDS),
        "--manifest", str(MANIFEST),
        "--historical-csv", str(HISTORY),
        "--report", str(output),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
    assert output.read_bytes().endswith(b"\\n")
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["observed_draws"] == 6
    assert result["missing_prize_tier_rows"] == 224
    assert result["p3_economic_readiness"]["decision"] == "NO_PLAY"
    assert result["source_manifest_sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode == 2
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_strict_incomplete_prize_report_still_written(tmp_path):
    output = tmp_path / "strict.json"
    result = subprocess.run(
        [
            sys.executable, "-m", "lrei.lottery.prize_series_audit",
            "--observations-dir", str(RECORDS),
            "--manifest", str(MANIFEST),
            "--historical-csv", str(HISTORY),
            "--report", str(output),
            "--require-complete",
        ],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["p3_economic_readiness"]["decision"] == "NO_PLAY"
