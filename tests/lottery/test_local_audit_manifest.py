"""Offline tests for local first-party-audit input fingerprinting (no network)."""

import hashlib
import json
import subprocess

import pytest

from lrei.lottery import local_audit_manifest as module


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def make_repo(path, files):
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.name", "LREI test")
    git(path, "config", "user.email", "lrei-test@example.invalid")
    for name, data in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")
    git(path, "add", ".")
    git(path, "commit", "-qm", "synthetic initial")
    git(path, "branch", "-M", "main")
    return path


@pytest.fixture
def inputs(tmp_path):
    trusted = make_repo(
        tmp_path / "trusted",
        {
            "pyproject.toml": "[project]\nname = 'lrei-test'\n",
            "src/lrei/lottery/dummy.py": "PASS = True\n",
        },
    )
    csv = "draw_id\tdate\tstrong_number\n1\t01-01-26\t2\n"
    candidate = make_repo(tmp_path / "candidate", {"data/lottery.csv": csv})
    return (
        trusted,
        candidate,
        git(candidate, "rev-parse", "HEAD"),
        hashlib.sha256(csv.encode("utf-8")).hexdigest(),
    )


def fingerprint(trusted, candidate, commit, digest):
    return module.fingerprint_inputs(
        trusted_repo=trusted,
        candidate_repo=candidate,
        expected_candidate_commit=commit,
        expected_candidate_sha256=digest,
    )


def test_clean_matching_inputs_do_not_claim_source_provenance(inputs):
    result = fingerprint(*inputs)
    assert result["candidate_csv_sha256"] == inputs[3]
    assert result["candidate_checkout_commit_sha"] == inputs[2]
    assert result["trusted_checker_commit_sha"] == git(inputs[0], "rev-parse", "HEAD")
    assert result["candidate_matches_expected_commit_and_digest"] is True
    assert result["operator_source_provenance_verified"] is False
    assert result["candidate_matches_operator"] is False
    assert result["dataset_promotion_approved"] is False
    assert result["requires_human_review"] is True
    assert "path" not in result


def test_modified_candidate_working_file_refused(inputs):
    (inputs[1] / "data/lottery.csv").write_text("modified\n", encoding="utf-8")
    with pytest.raises(module.LocalInputAuditError, match="uncommitted"):
        fingerprint(*inputs)


def test_wrong_expected_hash_refused(inputs):
    with pytest.raises(module.LocalInputAuditError, match="SHA-256 differs"):
        fingerprint(*inputs[:3], "0" * 64)


def test_wrong_commit_refused(inputs):
    with pytest.raises(module.LocalInputAuditError, match="commit differs"):
        fingerprint(inputs[0], inputs[1], "1" * 40, inputs[3])


def test_modified_trusted_code_refused(inputs):
    (inputs[0] / "src/lrei/lottery/dummy.py").write_text("PASS = False\n", encoding="utf-8")
    with pytest.raises(module.LocalInputAuditError, match="trusted source"):
        fingerprint(*inputs)


def test_untrusted_checkout_on_main_not_accepted_as_trusted(inputs):
    git(inputs[0], "checkout", "-qb", "feature")
    with pytest.raises(module.LocalInputAuditError, match="on main"):
        fingerprint(*inputs)


def test_same_repository_for_both_roles_refused(inputs):
    with pytest.raises(module.LocalInputAuditError, match="separate Git roots"):
        fingerprint(inputs[0], inputs[0], inputs[2], inputs[3])


def test_cli_writes_once_without_overwriting_prior_evidence(inputs, tmp_path, monkeypatch):
    out = tmp_path / "evidence" / "input-manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "local_audit_manifest",
            "--trusted-repo", str(inputs[0]),
            "--candidate-repo", str(inputs[1]),
            "--expected-candidate-commit", inputs[2],
            "--expected-candidate-sha256", inputs[3],
            "--report", str(out),
        ],
    )
    module.main()
    assert json.loads(out.read_text(encoding="utf-8"))["dataset_promotion_approved"] is False
    first = out.read_bytes()
    with pytest.raises(SystemExit) as failure:
        module.main()
    assert failure.value.code == 2
    assert out.read_bytes() == first
