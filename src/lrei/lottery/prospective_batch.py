"""Prepare immutable, equal-budget pre-draw paper portfolios.

This does not submit Lotto tickets, independently verify the stated draw
schedule, or publish evidence by itself. Publish the output *before* the
actual draw with a GitHub-hosted timestamp or another trusted record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .dataset import CsvDatasetLoader, LotteryDataset, parse_draw_date
from .five_plus import five_plus_metrics
from .prospective_ledger import build_snapshot, parse_target_datetime, verify_snapshot
from .smart import SmartConfig, SmartRecommendationEngine

CONTROL_SEEDS = (1042, 1043, 1044)
MINIMUM_LEAD = timedelta(minutes=60)


def _hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _schedule_url(value: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError("schedule reference must be a plain public HTTPS URL")


def build_paper_batch(
    *,
    historical: LotteryDataset,
    dataset_file: Path,
    source_commit: str,
    target_draw_id: int,
    target_draw_at: datetime,
    schedule_reference_url: str,
    schedule_reviewed: bool,
    now: datetime | None = None,
    smart_seed: int = 42,
    control_seeds: tuple[int, ...] = CONTROL_SEEDS,
) -> dict[str, Any]:
    """Create 1 Smart + 3 preregistered random controls, each with 14 lines."""
    if type(target_draw_id) is not int or target_draw_id <= 1:
        raise ValueError("target draw ID must be an integer greater than one")
    if type(schedule_reviewed) is not bool or not schedule_reviewed:
        raise ValueError("a human must confirm the target draw schedule first")
    _schedule_url(schedule_reference_url)
    if target_draw_at.tzinfo is None or target_draw_at.utcoffset() is None:
        raise ValueError("target draw requires an explicit local UTC offset")
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("creation time must be timezone-aware")
    now = now.astimezone(timezone.utc)
    target_utc = target_draw_at.astimezone(timezone.utc)
    if target_utc - now < MINIMUM_LEAD:
        raise ValueError("draw deadline is past or fewer than 60 minutes away")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source code must be a full Git commit SHA")
    if type(smart_seed) is not int:
        raise ValueError("Smart seed must be an integer")
    if (
        len(control_seeds) != 3
        or any(type(seed) is not int for seed in control_seeds)
        or len(set(control_seeds)) != 3
    ):
        raise ValueError("three distinct fixed random control seeds are required")
    if len(historical) == 0:
        raise ValueError("an empty historical dataset cannot be used")

    latest = historical.latest()
    if str(latest.draw_id) != str(target_draw_id - 1):
        raise ValueError("latest historical draw must be exactly target ID minus one")
    latest_date = parse_draw_date(latest.date)
    if latest_date is None or latest_date >= target_draw_at.date():
        raise ValueError("historical data must precede the target local draw date")
    local_creation = now.astimezone(target_draw_at.tzinfo).date()
    age = (local_creation - latest_date).days
    if not 0 <= age <= 4:
        raise ValueError("latest historical draw is future-dated or over four local days old")
    if not Path(dataset_file).is_file():
        raise ValueError("local dataset bytes are missing")
    dataset_sha256 = hashlib.sha256(Path(dataset_file).read_bytes()).hexdigest()

    smart_result = SmartRecommendationEngine(
        SmartConfig(objective="coverage_5plus")
    ).recommend(historical, seed=smart_seed)
    smart_tickets = smart_result.recommended_tickets_with_strong
    smart = build_snapshot(
        dataset_file=dataset_file,
        dataset=historical,
        tickets=smart_tickets,
        mode="smart",
        objective="coverage_5plus",
        seed=smart_seed,
        source_commit=source_commit,
        target_draw_at=target_draw_at,
        generated_count=len(smart_result.generated_tickets),
        created_at=now,
    )
    if not verify_snapshot(smart):
        raise ValueError("Smart snapshot digest verification failed")
    smart_metrics = five_plus_metrics(t["main"] for t in smart["tickets"])
    if not smart_metrics["is_optimal"]:
        raise ValueError("Smart 5+ no longer attains the exact coverage ceiling")
    if any(
        len(set(a["main"]) & set(b["main"])) > 1
        for a, b in combinations(smart["tickets"], 2)
    ):
        raise ValueError("Smart 5+ pairwise overlap invariant failed")

    control_records: dict[str, dict[str, Any]] = {}
    for seed in control_seeds:
        rng = random.Random(seed)
        lines: list[dict[str, Any]] = []
        seen: set[tuple[int, ...]] = set()
        while len(lines) < 14:
            main = tuple(sorted(rng.sample(range(1, 38), 6)))
            if main in seen:
                continue
            seen.add(main)
            lines.append({"main": list(main), "strong": rng.randint(1, 7)})
        control = {
            "schema_version": 1,
            "experiment": "P1_uniform_random_14_lines_paper_control",
            "created_at_utc": _iso(now),
            "target_draw_at_utc": _iso(target_draw_at),
            "target_draw_date_local": target_draw_at.date().isoformat(),
            "expected_next_draw_id": str(target_draw_id),
            "source_commit": source_commit,
            "dataset_sha256": dataset_sha256,
            "latest_draw": smart["latest_draw"],
            "seed": seed,
            "ticket_count": 14,
            "tickets": lines,
            "real_money_spent_ils": 0,
            "counts_as_predictive_advantage": False,
            "operator_result_independently_verified": False,
        }
        control["record_sha256"] = _hash(control)
        control_records[f"random_seed_{seed}"] = control

    manifest = {
        "schema_version": 1,
        "status": "paper_snapshot_prepared_external_publication_pending",
        "created_at_utc": _iso(now),
        "target_draw_id": target_draw_id,
        "target_draw_date_local": target_draw_at.date().isoformat(),
        "target_draw_at_utc": _iso(target_draw_at),
        "schedule_reference_url_user_supplied": schedule_reference_url,
        "schedule_human_reviewed_not_independently_authenticated": True,
        "dataset_sha256": dataset_sha256,
        "latest_draw": smart["latest_draw"],
        "source_commit": source_commit,
        "primary_analysis_metric": "paired_any_3plus_main_portfolio_rate",
        "secondary_metrics": ["any_4plus_main", "any_5plus_main", "best_main_matches"],
        "smart_objective": "coverage_5plus",
        "smart_seed": smart_seed,
        "random_control_seeds": list(control_seeds),
        "random_control_count": len(control_seeds),
        "ticket_count_per_portfolio": 14,
        "smart_reported_generated_count": smart["reported_generated_count"],
        "smart_record_sha256": smart["record_sha256"],
        "control_record_sha256": {
            name: value["record_sha256"] for name, value in control_records.items()
        },
        "contains_actual_draw_result": False,
        "official_source_provenance_verified": False,
        "independent_pre_draw_publication_verified": False,
        "money_wagered_ils": 0,
        "predictive_advantage_established": False,
    }
    manifest["record_sha256"] = _hash(manifest)
    return {"smart": smart, "controls": control_records, "manifest": manifest}


def write_paper_batch(batch: dict[str, Any], directory: Path) -> Path:
    """Create a NEW directory; never replace or modify existing evidence."""
    manifest = batch["manifest"]
    if _hash({k: v for k, v in manifest.items() if k != "record_sha256"}) != manifest["record_sha256"]:
        raise ValueError("paper batch manifest has an invalid SHA-256")
    if not verify_snapshot(batch["smart"]):
        raise ValueError("Smart snapshot has an invalid SHA-256")
    for record in batch["controls"].values():
        if _hash({k: v for k, v in record.items() if k != "record_sha256"}) != record["record_sha256"]:
            raise ValueError("random control has an invalid SHA-256")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    items = {
        "manifest.json": manifest,
        "smart_14.json": batch["smart"],
        **{f"{name}_14.json": record for name, record in batch["controls"].items()},
    }
    for filename, obj in items.items():
        path = directory / filename
        with path.open("x", encoding="utf-8") as stream:
            json.dump(obj, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
    return directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--target-draw-id", type=int, required=True)
    parser.add_argument("--target-draw-at", required=True)
    parser.add_argument("--schedule-reference-url", required=True)
    parser.add_argument("--schedule-reviewed", action="store_true", required=True)
    parser.add_argument("--smart-seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        target = datetime.fromisoformat(args.target_draw_at.replace("Z", "+00:00"))
        if target.tzinfo is None or target.utcoffset() is None:
            raise ValueError("target time requires an explicit timezone offset")
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        # Dirty code or data changes make the published commit SHA ambiguous.
        subprocess.run(["git", "diff", "--quiet"], check=True)
        subprocess.run(["git", "diff", "--cached", "--quiet"], check=True)
        batch = build_paper_batch(
            historical=CsvDatasetLoader().load(args.dataset),
            dataset_file=args.dataset,
            source_commit=source_commit,
            target_draw_id=args.target_draw_id,
            target_draw_at=target,
            schedule_reference_url=args.schedule_reference_url,
            schedule_reviewed=args.schedule_reviewed,
            smart_seed=args.smart_seed,
        )
        saved = write_paper_batch(batch, args.output_dir)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Prospective paper batch refused: {exc}\n")
    print(f"Paper batch prepared at {saved}")
    print("No external publication or official schedule authenticity verified yet.")
    print(f"Manifest SHA-256: {batch['manifest']['record_sha256']}")


if __name__ == "__main__":
    main()
