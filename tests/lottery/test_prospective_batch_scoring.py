"""Synthetic, source-agnostic tests for the real four-arm paper-score engine."""

import json
import random
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from lrei.lottery.prospective_batch import CONTROL_SEEDS, _hash
from lrei.lottery.prospective_batch_scoring import (
    ARMS, score_reported_draw, main as score_main,
)
from lrei.lottery.prospective_ledger import build_snapshot

NOW = datetime(2026, 10, 17, 17, 0, tzinfo=timezone.utc)
TARGET = datetime(2026, 10, 17, 23, 0, tzinfo=timezone(timedelta(hours=3)))
REPORTED = "2026-10-17T19:55:00Z"
PUBLICATION = {
    "kind": "github_commit",
    "url": "https://github.com/example/LREI/commit/" + "b" * 40,
    "published_at_utc": "2026-10-17T18:00:00Z",
}
RESULT = {
    "draw_id": 3976,
    "draw_date_local": "2026-10-17",
    "reported_draw_at_utc": REPORTED,
    "main": [3, 9, 15, 21, 27, 33],
    "strong": 5,
    "source_url": "https://example.org/secondary/unverified/3976",
}
SCORE_AT = datetime(2026, 10, 17, 21, 0, tzinfo=timezone.utc)


class FakeHistory:
    def __len__(self):
        return 1141

    def latest(self):
        return SimpleNamespace(draw_id="3975", date="15-10-26")


def grid_lines():
    grid = tuple(tuple(r * 6 + c + 1 for c in range(6)) for r in range(6))
    return (
        list(grid)
        + [tuple(grid[r][c] for r in range(6)) for c in range(6)]
        + [tuple(grid[r][r] for r in range(6))]
        + [tuple(grid[r][(r + 1) % 6] for r in range(6))]
    )


@pytest.fixture
def paper(tmp_path):
    history = FakeHistory()
    path = tmp_path / "synthetic_training.csv"
    path.write_bytes(b"synthetic training only, no real Lotto draws")
    tickets = [
        SimpleNamespace(numbers=row, strong_number=(i % 7) + 1)
        for i, row in enumerate(grid_lines())
    ]
    smart = build_snapshot(
        dataset_file=path,
        dataset=history,
        tickets=tickets,
        mode="smart",
        objective="coverage_5plus",
        seed=42,
        source_commit="a" * 40,
        target_draw_at=TARGET,
        generated_count=500,
        created_at=NOW,
    )
    controls = {}
    for seed in CONTROL_SEEDS:
        rng = random.Random(seed)
        used = set()
        lines = []
        while len(lines) != 14:
            numbers = tuple(sorted(rng.sample(range(1, 38), 6)))
            if numbers in used:
                continue
            used.add(numbers)
            lines.append({"main": list(numbers), "strong": rng.randint(1, 7)})
        entry = {
            "schema_version": 1,
            "experiment": "P1_uniform_random_14_lines_paper_control",
            "created_at_utc": smart["created_at_utc"],
            "target_draw_at_utc": smart["target_draw_at_utc"],
            "target_draw_date_local": smart["target_draw_date_local"],
            "expected_next_draw_id": "3976",
            "source_commit": smart["source_commit"],
            "dataset_sha256": smart["dataset_sha256"],
            "latest_draw": smart["latest_draw"],
            "seed": seed,
            "ticket_count": 14,
            "tickets": lines,
            "real_money_spent_ils": 0,
            "counts_as_predictive_advantage": False,
            "operator_result_independently_verified": False,
        }
        entry["record_sha256"] = _hash(entry)
        controls[f"random_seed_{seed}"] = entry

    manifest = {
        "schema_version": 1,
        "status": "paper_snapshot_prepared_external_publication_pending",
        "created_at_utc": smart["created_at_utc"],
        "target_draw_id": 3976,
        "target_draw_date_local": smart["target_draw_date_local"],
        "target_draw_at_utc": smart["target_draw_at_utc"],
        "schedule_reference_url_user_supplied": "https://www.pais.co.il/lotto/archive.aspx",
        "schedule_human_reviewed_not_independently_authenticated": True,
        "dataset_sha256": smart["dataset_sha256"],
        "latest_draw": smart["latest_draw"],
        "source_commit": smart["source_commit"],
        "primary_analysis_metric": "paired_any_3plus_main_portfolio_rate",
        "secondary_metrics": ["any_4plus_main", "any_5plus_main", "best_main_matches"],
        "smart_objective": "coverage_5plus",
        "smart_seed": 42,
        "random_control_seeds": list(CONTROL_SEEDS),
        "random_control_count": 3,
        "ticket_count_per_portfolio": 14,
        "smart_reported_generated_count": 500,
        "smart_record_sha256": smart["record_sha256"],
        "control_record_sha256": {
            name: row["record_sha256"] for name, row in controls.items()
        },
        "contains_actual_draw_result": False,
        "official_source_provenance_verified": False,
        "independent_pre_draw_publication_verified": False,
        "money_wagered_ils": 0,
        "predictive_advantage_established": False,
    }
    manifest["record_sha256"] = _hash(manifest)
    return {"manifest": manifest, "smart": smart, "controls": controls}


def score(paper, result=None, publication=None, evaluated_at=SCORE_AT):
    return score_reported_draw(
        paper,
        RESULT if result is None else result,
        PUBLICATION if publication is None else publication,
        evaluated_at=evaluated_at,
    )


def test_complete_frozen_four_arm_study_scores_as_unverified_only(paper):
    first = score(paper)
    assert first == score(paper)
    assert first["schema_version"] == 1
    assert first["status"] == "PROVISIONAL_USER_SUPPLIED_RESULT_NOT_OFFICIALLY_VERIFIED"
    assert first["independent_github_publication_time_verified"] is False
    assert first["independent_operator_draw_result_verified"] is False
    assert first["commission_approved_protocol_verified"] is False
    assert first["no_real_money_wagered"] is True
    assert first["positive_expected_value_or_predictive_edge_established"] is False
    assert first["preregistered_primary_metric"] == "paired_any_3plus_main_portfolio_rate"
    assert set(first["portfolios"]) == set(ARMS)
    assert first["one_draw_observation_only"]["do_not_interpret_as_statistical_evidence"]
    assert first["report_sha256"] == _hash({
        k: v for k, v in first.items() if k != "report_sha256"
    })
    for record in first["portfolios"].values():
        assert record["ticket_count"] == 14
        assert record["best_main_matches"] <= 6
        assert 0 <= record["three_plus_tickets"] <= 14
        assert 0 < record["exact_five_plus_probability_fair_main_draw"] <= 1 / 888
        assert sum(record["assumed_prize_tier_counts"].values()) <= 14
    assert first["portfolios"]["smart"]["attains_maximum_five_plus_probability"] is True
    assert first["portfolios"]["smart"]["maximum_pairwise_main_overlap"] <= 1


def test_removed_or_cherry_picked_random_controls_fail_closed(paper):
    del paper["controls"]["random_seed_1043"]
    with pytest.raises(ValueError, match="three"):
        score(paper)


def test_tampered_smart_and_control_fail_with_hash_error(paper):
    paper["smart"]["tickets"][0]["main"][0] = 37
    with pytest.raises(ValueError, match="SHA-256"):
        score(paper)
    paper["smart"]["tickets"][0]["main"][0] = 1
    paper["controls"]["random_seed_1042"]["tickets"][0]["strong"] = 7
    with pytest.raises(ValueError, match="SHA-256"):
        score(paper)


def test_tampered_manifest_or_primary_metric_cannot_be_scored(paper):
    paper["manifest"]["primary_analysis_metric"] = "cherry_picked"
    with pytest.raises(ValueError, match="SHA-256"):
        score(paper)
    paper["manifest"]["record_sha256"] = _hash({
        k: v for k, v in paper["manifest"].items() if k != "record_sha256"
    })
    with pytest.raises(ValueError, match="pre-registration"):
        score(paper)


@pytest.mark.parametrize("patch,error", [
    ({"draw_id": 3977}, "differs"),
    ({"draw_date_local": "2026-10-18"}, "differs"),
    ({"main": [1, 1, 2, 3, 4, 5]}, "invalid"),
    ({"main": [0, 2, 3, 4, 5, 6]}, "invalid"),
    ({"strong": 8}, "invalid"),
    ({"reported_draw_at_utc": "2026-10-18T19:55:00Z"}, "local date"),
    ({"reported_draw_at_utc": "2026-10-17T19:55:00"}, "UTC offset"),
    ({"source_url": "http://example.org/unverified"}, "HTTPS"),
    ({"source_url": "https://pais.co.il@evil.invalid/forged"}, "HTTPS"),
])
def test_invalid_result_refused(paper, patch, error):
    candidate = dict(RESULT)
    candidate.update(patch)
    with pytest.raises(ValueError, match=error):
        score(paper, result=candidate)


@pytest.mark.parametrize("patch,error", [
    ({"kind": "unknown"}, "unrecognized"),
    ({"url": "https://github.com.evil.invalid/fake"}, "HTTPS"),
    ({"url": "https://someone@github.com/repo"}, "HTTPS"),
    ({"published_at_utc": "2026-10-17T19:56:00Z"}, "not before"),
    ({"published_at_utc": "2026-10-17T20:01:00Z"}, "not before"),
    ({"published_at_utc": "2026-10-17T16:59:00Z"}, "before publication"),
    ({"published_at_utc": "2026-10-17T18:00:00"}, "UTC offset"),
])
def test_false_publication_or_invalid_claim_rejected(paper, patch, error):
    candidate = dict(PUBLICATION)
    candidate.update(patch)
    with pytest.raises(ValueError, match=error):
        score(paper, publication=candidate)


def test_training_cutoff_cannot_be_changed_even_with_valid_new_manifest_checksum(paper):
    paper["manifest"]["latest_draw"] = {"id": "3974", "date": "2026-10-13"}
    paper["manifest"]["record_sha256"] = _hash({
        k: v for k, v in paper["manifest"].items() if k != "record_sha256"
    })
    with pytest.raises(ValueError, match="nonconsecutive"):
        score(paper)


def test_no_scoring_before_draw_and_naive_evaluation_clock_refused(paper):
    with pytest.raises(ValueError, match="before"):
        score(paper, evaluated_at=datetime(2026, 10, 17, 19, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="UTC offset"):
        score(paper, evaluated_at=datetime(2026, 10, 17, 21))


def test_cli_writes_verified_digest_once_and_never_overwrites(tmp_path, paper, monkeypatch):
    folder = tmp_path / "predraw"
    folder.mkdir()
    (folder / "manifest.json").write_text(json.dumps(paper["manifest"]), encoding="utf-8")
    (folder / "smart_14.json").write_text(json.dumps(paper["smart"]), encoding="utf-8")
    for name, row in paper["controls"].items():
        (folder / f"{name}_14.json").write_text(json.dumps(row), encoding="utf-8")
    result_file = tmp_path / "candidate_result.json"
    result_file.write_text(json.dumps(RESULT), encoding="utf-8")
    publication_file = tmp_path / "user_claimed_publication.json"
    publication_file.write_text(json.dumps(PUBLICATION), encoding="utf-8")
    output = tmp_path / "scored" / "report.json"
    monkeypatch.setattr("sys.argv", [
        "p1-paper-score", "--batch-dir", str(folder),
        "--result-json", str(result_file),
        "--publication-json", str(publication_file),
        "--output", str(output),
    ])
    score_main()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["status"].startswith("PROVISIONAL_")
    assert data["no_real_money_wagered"] is True
    with pytest.raises(SystemExit) as error:
        score_main()
    assert error.value.code == 2


def test_report_never_contains_claimed_positive_monetary_return(paper):
    report = score(paper)
    assert report["positive_expected_value_or_predictive_edge_established"] is False
    assert report["independent_operator_draw_result_verified"] is False
    assert "profit_ils" not in json.dumps(report)
