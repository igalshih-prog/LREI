"""Pre-registered evidence test for a *possible* nonuniform main-number draw.

This is NOT a winning-number predictor or proof of an advantage. A single
alternative distribution is frozen from the historical archive before any
future outcome is seen. For each subsequent uniform independent 6/37 draw,
its likelihood-ratio increment has conditional expectation exactly one.
Therefore cumulative products are a nonnegative test martingale ("e-process").
Ville's inequality bounds the chance it ever reaches 20 by 5% under the null.
Never refit, select seeds, omit draws, or choose among variants retrospectively.

A local checksum provides file integrity, NOT independent proof of an
external pre-draw timestamp or official draw authenticity.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from .dataset import LotteryDrawRecord, parse_draw_date

PROTOCOL = "P2-main-number-frequency-LR-v1-beta-0.20"
FROZEN_BETA = 0.20  # single predetermined alternative; NEVER tune on future draws
DRAWS_IN_LINE = 6
NUMBER_MAX = 37
NULL_DRAWS = math.comb(NUMBER_MAX, DRAWS_IN_LINE)
EVIDENCE_LOG_THRESHOLD = math.log(20)


def _utc(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone")
    return value.astimezone(timezone.utc)


def _canonical_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(
        record, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "record_sha256": _canonical_hash(payload)}


def _verify(record: Any, kind: str) -> bool:
    if not isinstance(record, dict) or record.get("kind") != kind:
        return False
    checksum = record.get("record_sha256")
    if not isinstance(checksum, str) or not re.fullmatch("[0-9a-f]{64}", checksum):
        return False
    try:
        return _canonical_hash({k: v for k, v in record.items() if k != "record_sha256"}) == checksum
    except (ValueError, TypeError):
        return False


def elementary_symmetric(weights: Sequence[float], degree: int = 6) -> float:
    """Compute sum over unordered degree-sized subsets of product weights."""
    if degree < 0 or len(weights) < degree:
        raise ValueError("invalid elementary symmetric degree")
    coeff = [1.0] + [0.0] * degree
    for index, weight in enumerate(weights):
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("all alternative weights must be finite and positive")
        for k in range(min(index + 1, degree), 0, -1):
            coeff[k] += weight * coeff[k - 1]
    return coeff[degree]


def _valid_main(numbers: Sequence[int]) -> tuple[int, ...]:
    seq = tuple(numbers)
    if len(seq) != 6 or any(type(n) is not int or not 1 <= n <= 37 for n in seq):
        raise ValueError("draw needs six integer main numbers in 1..37")
    if len(set(seq)) != 6:
        raise ValueError("draw main numbers must be distinct")
    return seq


def freeze_bias_model(
    dataset: Any,
    dataset_file: Path,
    source_commit: str,
    *,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Freeze exactly one low-complexity alternative based on pre-existing data.

    The single beta=0.20 and trial threshold e>=20 are prespecified in code.
    The original historical archive is DEVELOPMENT data, not test evidence.
    """
    created = _utc(created_at or datetime.now(timezone.utc), "created_at")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source_commit must be a 40-character Git SHA")
    n = len(dataset)
    if n < 100:
        raise ValueError("need at least 100 earlier draws to freeze the model")
    last = dataset.latest()
    if not str(last.draw_id).isdigit():
        raise ValueError("draw IDs must be numeric for strict sequential scoring")
    last_date = parse_draw_date(last.date)
    if last_date is None:
        raise ValueError("last historical draw needs a valid date")
    age = (created.date() - last_date).days
    if not 0 <= age <= 4:
        raise ValueError("archive is future dated or more than four days old")

    count = [0] * 37
    prev_id: int | None = None
    for draw in dataset:
        line = _valid_main(draw.numbers)
        if not str(draw.draw_id).isdigit():
            raise ValueError("historical draw IDs must be numeric")
        identifier = int(draw.draw_id)
        if prev_id is not None and identifier != prev_id + 1:
            raise ValueError("training draw IDs must be consecutive")
        prev_id = identifier
        for number in line:
            count[number - 1] += 1

    p = 6 / 37
    mu = n * p
    sigma = math.sqrt(n * p * (1 - p))
    weights = [math.exp(FROZEN_BETA * ((value - mu) / sigma)) for value in count]
    dataset_hash = hashlib.sha256(Path(dataset_file).read_bytes()).hexdigest()
    payload = {
        "kind": "lrei_preregistered_main_bias_model",
        "schema_version": 1,
        "protocol": PROTOCOL,
        "created_at_utc": created.isoformat().replace("+00:00", "Z"),
        "source_commit": source_commit,
        "dataset_sha256": dataset_hash,
        "training_draw_count": n,
        "cutoff_draw_id": str(last.draw_id),
        "cutoff_draw_date": last_date.isoformat(),
        "beta": FROZEN_BETA,
        "fixed_evidence_threshold": 20.0,
        "number_counts": count,
        "weights": weights,
        "primary_null": "independent_uniform_6_of_37_main_draws",
        "primary_test": "sequential_product_likelihood_ratio",
        "intended_outcome": "test_nonuniformity_not_win_guarantee",
    }
    return _seal(payload)


def verify_frozen_model(model: Any) -> bool:
    """Check integrity and model-shape invariants, not a trusted timestamp."""
    if not _verify(model, "lrei_preregistered_main_bias_model"):
        return False
    try:
        if model["schema_version"] != 1 or model["protocol"] != PROTOCOL:
            return False
        if model["beta"] != FROZEN_BETA or model["fixed_evidence_threshold"] != 20.0:
            return False
        if not re.fullmatch("[0-9a-f]{40}", model["source_commit"]):
            return False
        if not re.fullmatch("[0-9a-f]{64}", model["dataset_sha256"]):
            return False
        n = model["training_draw_count"]
        counts = model["number_counts"]
        weights = model["weights"]
        if type(n) is not int or n < 100 or len(weights) != 37 or len(counts) != 37:
            return False
        if any(type(x) is not int or x < 0 for x in counts) or sum(counts) != 6 * n:
            return False
        p = 6 / 37
        mu = n * p
        sigma = math.sqrt(n * p * (1 - p))
        expected = [math.exp(FROZEN_BETA * ((x - mu) / sigma)) for x in counts]
        if any(type(x) is not float or x != y for x, y in zip(weights, expected)):
            return False
        elementary_symmetric(weights)
        if not str(model["cutoff_draw_id"]).isdigit():
            return False
        if parse_draw_date(model["cutoff_draw_date"]) is None:
            return False
        _utc(datetime.fromisoformat(model["created_at_utc"].replace("Z", "+00:00")), "created_at")
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    return True


def verify_evidence_record(record: Any) -> bool:
    return _verify(record, "lrei_preregistered_main_bias_evidence") and (
        record.get("schema_version") == 1
    )


def score_future_draw(
    model: dict[str, Any],
    draw: LotteryDrawRecord,
    *,
    draw_occurred_at: datetime,
    source_url: str,
    previous: dict[str, Any] | None = None,
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Append ONE next official-result input; never select or omit bad outcomes."""
    if not verify_frozen_model(model):
        raise ValueError("frozen model is invalid or tampered")
    target = _utc(draw_occurred_at, "draw_occurred_at")
    created = _utc(datetime.fromisoformat(model["created_at_utc"].replace("Z", "+00:00")), "created_at")
    now = _utc(evaluated_at or datetime.now(timezone.utc), "evaluated_at")
    if target <= created:
        raise ValueError("draw must occur after the frozen model creation")
    if now < target:
        raise ValueError("cannot score a draw before it takes place")
    draw_date = parse_draw_date(draw.date)
    if draw_date is None or draw_date != draw_occurred_at.date():
        raise ValueError("official draw date must match the target local date")
    if type(draw.strong_number) is not int or not 1 <= draw.strong_number <= 7:
        raise ValueError("official result must supply a valid strong number")
    line = _valid_main(draw.numbers)
    parsed_source = urlsplit(source_url)
    if parsed_source.scheme != "https" or not parsed_source.hostname:
        raise ValueError("official result requires HTTPS provenance URL")
    if not draw.draw_id.isdigit():
        raise ValueError("official result must have numeric draw ID")
    expected_id = int(model["cutoff_draw_id"]) + 1
    prior_log = 0.0
    prior_hash = None
    prior_peak_log = 0.0
    sequence = 1
    if previous is not None:
        if not verify_evidence_record(previous):
            raise ValueError("previous evidence record is invalid")
        if previous["model_sha256"] != model["record_sha256"]:
            raise ValueError("previous evidence uses a different frozen model")
        expected_id = int(previous["draw"]["id"]) + 1
        prior_log = float(previous["cumulative_log_e"])
        prior_hash = previous["record_sha256"]
        prior_peak_log = float(previous["peak_log_e"])
        sequence = int(previous["draw_number"]) + 1
        prior_time = datetime.fromisoformat(previous["draw_occurred_at_utc"].replace("Z", "+00:00"))
        if target <= prior_time:
            raise ValueError("draw time must follow previous evaluated draw")
    if int(draw.draw_id) != expected_id:
        raise ValueError(f"draw ID must be exactly {expected_id}; no cherry-picking or gaps")

    weights = model["weights"]
    normalizer = elementary_symmetric(weights, 6)
    log_increment = (
        math.log(NULL_DRAWS)
        + sum(math.log(weights[number - 1]) for number in line)
        - math.log(normalizer)
    )
    cumulative_log = prior_log + log_increment
    if not math.isfinite(cumulative_log):
        raise ValueError("cumulative log evidence is not finite")
    peak_log = max(prior_peak_log, cumulative_log)
    payload = {
        "kind": "lrei_preregistered_main_bias_evidence",
        "schema_version": 1,
        "protocol": PROTOCOL,
        "model_sha256": model["record_sha256"],
        "previous_record_sha256": prior_hash,
        "draw_number": sequence,
        "draw_occurred_at_utc": target.isoformat().replace("+00:00", "Z"),
        "evaluated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "result_source_url_user_supplied": source_url,
        "source_independently_verified": False,
        "draw": {
            "id": draw.draw_id,
            "date": draw_date.isoformat(),
            "main": list(sorted(line)),
            "strong": draw.strong_number,
        },
        "log_likelihood_ratio_increment": log_increment,
        "cumulative_log_e": cumulative_log,
        "peak_log_e": peak_log,
        "anytime_valid_evidence_threshold_ever_reached": peak_log >= EVIDENCE_LOG_THRESHOLD,
        "interpretation": "bias_evidence_not_5plus_winning_advantage",
    }
    return _seal(payload)


def write_immutable(record: dict[str, Any], directory: Path) -> Path:
    """Write a checksum-verified record without replacing any previous data."""
    kind = record.get("kind")
    if kind == "lrei_preregistered_main_bias_model":
        if not verify_frozen_model(record):
            raise ValueError("invalid frozen model")
        label = "frozen"
    elif kind == "lrei_preregistered_main_bias_evidence":
        if not verify_evidence_record(record):
            raise ValueError("invalid evidence record")
        label = "evidence"
    else:
        raise ValueError("unsupported audit record")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"p2-{label}-{record['record_sha256'][:20]}.json"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(
                (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
            )
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path
