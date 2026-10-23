"""Offline input fingerprint manifest for separately hosted first-party Lotto audits.

Records Git commit identities and compares the candidate working file against
its committed Git blob. Never contacts the operator, authenticates uploaded
history, approves promotion, or modifies any dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CANDIDATE_RELATIVE_PATH = Path("data/lottery.csv")
MAX_CANDIDATE_BYTES = 8 * 1024 * 1024
TRUSTED_TRACKED_PATHS = ("src/lrei/lottery", "pyproject.toml")


class LocalInputAuditError(ValueError):
    """An input is unsuitable for a reproducible, offline fingerprint manifest."""


def _git(repo: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise LocalInputAuditError("Git checkout or requested revision unavailable") from exc
    return result.stdout


def _head(repo: Path) -> str:
    sha = _git(repo, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise LocalInputAuditError("expected an immutable forty-character Git commit")
    return sha


def _root(repo: Path) -> Path:
    return Path(
        _git(repo, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    ).resolve()


def fingerprint_inputs(
    *,
    trusted_repo: Path,
    candidate_repo: Path,
    expected_candidate_commit: str,
    expected_candidate_sha256: str,
) -> dict[str, Any]:
    """Check independent clean Git checkouts and fingerprint candidate bytes.

    The commit and digest must be specified by the operator of this command:
    they are comparison constraints, NOT evidence that the CSV came from Pais.
    """
    if re.fullmatch(r"[0-9a-f]{40}", expected_candidate_commit) is None:
        raise LocalInputAuditError("expected candidate commit must be a full SHA-1")
    if re.fullmatch(r"[0-9a-f]{64}", expected_candidate_sha256) is None:
        raise LocalInputAuditError("expected candidate hash must be SHA-256 hex")
    trusted = trusted_repo.resolve(strict=True)
    candidate = candidate_repo.resolve(strict=True)
    if trusted == candidate or _root(trusted) != trusted or _root(candidate) != candidate:
        raise LocalInputAuditError("trusted and candidate must be separate Git roots")
    trusted_head = _head(trusted)
    candidate_head = _head(candidate)
    if candidate_head != expected_candidate_commit:
        raise LocalInputAuditError("candidate commit differs from expected immutable revision")
    if _git(trusted, "symbolic-ref", "--quiet", "--short", "HEAD").decode().strip() != "main":
        raise LocalInputAuditError("trusted code must be checked out on main")
    if _git(trusted, "status", "--porcelain", "--untracked-files=all", "--", *TRUSTED_TRACKED_PATHS):
        raise LocalInputAuditError("trusted source code or package metadata has local changes")
    if _git(candidate, "status", "--porcelain", "--untracked-files=all", "--", str(CANDIDATE_RELATIVE_PATH).replace("\\", "/")):
        raise LocalInputAuditError("candidate CSV has uncommitted or untracked changes")
    path = candidate / CANDIDATE_RELATIVE_PATH
    raw = path.read_bytes()
    if not 0 < len(raw) <= MAX_CANDIDATE_BYTES:
        raise LocalInputAuditError("candidate CSV is empty or exceeds 8 MiB")
    # Detect Git working-tree normalization, smudge filters or changes by
    # comparing exact working bytes with immutable Git HEAD blob bytes.
    committed = _git(candidate, "show", "HEAD:data/lottery.csv")
    if raw != committed:
        raise LocalInputAuditError("candidate working bytes differ from committed Git blob")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_candidate_sha256:
        raise LocalInputAuditError("candidate SHA-256 differs from expected value")
    return {
        "schema_version": 1,
        "status": "LOCAL_INPUT_FINGERPRINTS_ONLY_NOT_SOURCE_ATTESTATION",
        "trusted_checker_commit_sha": trusted_head,
        "candidate_checkout_commit_sha": candidate_head,
        "candidate_csv_sha256": digest,
        "candidate_csv_bytes": len(raw),
        "candidate_matches_expected_commit_and_digest": True,
        "candidate_matches_operator": False,
        "operator_source_provenance_verified": False,
        "historical_download_provenance_of_user_upload_proven": False,
        "legally_binding_commission_protocol_verified": False,
        "dataset_promotion_approved": False,
        "eligible_for_economic_or_predictive_advantage_claim": False,
        "requires_human_review": True,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-repo", type=Path, required=True)
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--expected-candidate-commit", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = fingerprint_inputs(
            trusted_repo=args.trusted_repo,
            candidate_repo=args.candidate_repo,
            expected_candidate_commit=args.expected_candidate_commit,
            expected_candidate_sha256=args.expected_candidate_sha256,
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as target:
            json.dump(report, target, indent=2, ensure_ascii=False, sort_keys=True)
            target.write("\n")
    except (OSError, ValueError, LocalInputAuditError) as exc:
        parser.exit(2, f"Local input fingerprint check refused: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
