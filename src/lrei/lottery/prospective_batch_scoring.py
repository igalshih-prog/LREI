"""Score four frozen P1 paper portfolios against a reported later result.

This is an offline audit, not an authenticated Github timestamp or an official
operator-protocol verification. Scores remain PROVISIONAL regardless of a URL.
Never submits a ticket, calculates cash returns, or claims predictive edge.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .dataset import LotteryDrawRecord, parse_draw_date
from .five_plus import five_plus_metrics
from .prize_evaluation import evaluate_portfolio_prizes
from .prospective_batch import CONTROL_SEEDS, _hash
from .prospective_ledger import verify_snapshot
from .recommendation import RecommendedTicket

ARMS = ("smart", *(f"random_seed_{seed}" for seed in CONTROL_SEEDS))
ISRAEL = ZoneInfo("Asia/Jerusalem")
PRIMARY = "paired_any_3plus_main_portfolio_rate"


def _when(value: str, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} requires an offset-aware ISO-8601 timestamp")
    try:
        date_time = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be ISO-8601") from exc
    if date_time.tzinfo is None or date_time.utcoffset() is None:
        raise ValueError(f"{label} requires a UTC offset")
    return date_time.astimezone(timezone.utc)


def _https(url: str, label: str, github: bool = False) -> None:
    if not isinstance(url, str) or any(char.isspace() for char in url):
        raise ValueError(f"{label} requires an HTTPS URL")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or (github and parsed.hostname != "github.com")
    ):
        raise ValueError(f"{label} requires a plain HTTPS URL")


def _digest_ok(record: dict[str, Any], label: str) -> None:
    sha = record.get("record_sha256")
    if (
        not isinstance(sha, str)
        or not re.fullmatch("[0-9a-f]{64}", sha)
        or sha != _hash({k: v for k, v in record.items() if k != "record_sha256"})
    ):
        raise ValueError(f"{label} SHA-256 integrity failure")


def _ticket_rows(record: dict[str, Any], label: str) -> tuple[RecommendedTicket, ...]:
    rows = record.get("tickets")
    if not isinstance(rows, list) or len(rows) != 14 or record.get("ticket_count") != 14:
        raise ValueError(f"{label} must contain fourteen tickets")
    seen: set[tuple[int, ...]] = set()
    tickets = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{label}: invalid ticket object")
        main, strong = row.get("main"), row.get("strong")
        if (
            not isinstance(main, list) or len(main) != 6
            or any(type(n) is not int or not 1 <= n <= 37 for n in main)
            or len(set(main)) != 6
            or type(strong) is not int or not 1 <= strong <= 7
        ):
            raise ValueError(f"{label}: invalid Lotto ticket")
        numbers = tuple(sorted(main))
        if numbers in seen:
            raise ValueError(f"{label}: repeated six-number ticket")
        seen.add(numbers)
        tickets.append(RecommendedTicket(numbers=numbers, strong_number=strong))
    return tuple(tickets)


def score_reported_draw(
    batch: dict[str, Any],
    result: dict[str, Any],
    publication: dict[str, Any],
    *,
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Check all four original portfolios, never cherry-pick a random seed."""
    if not all(isinstance(x, dict) for x in (batch, result, publication)):
        raise ValueError("batch, result and publication must be JSON objects")
    manifest = batch.get("manifest")
    controls = batch.get("controls")
    smart = batch.get("smart")
    if not isinstance(manifest, dict) or not isinstance(controls, dict) or not isinstance(smart, dict):
        raise ValueError("missing paper batch manifest, Smart or controls")
    _digest_ok(manifest, "manifest")
    if not verify_snapshot(smart):
        raise ValueError("Smart snapshot SHA-256 integrity failure")
    if set(controls) != set(ARMS[1:]) or set(manifest.get("control_record_sha256", {})) != set(ARMS[1:]):
        raise ValueError("all three preregistered random controls are required")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("primary_analysis_metric") != PRIMARY
        or manifest.get("ticket_count_per_portfolio") != 14
        or manifest.get("smart_objective") != "coverage_5plus"
        or manifest.get("random_control_seeds") != list(CONTROL_SEEDS)
        or manifest.get("random_control_count") != 3
        or manifest.get("contains_actual_draw_result") is not False
        or manifest.get("money_wagered_ils") != 0
        or manifest.get("predictive_advantage_established") is not False
        or smart.get("record_sha256") != manifest.get("smart_record_sha256")
    ):
        raise ValueError("paper batch pre-registration does not match expected contract")

    draw_id = manifest.get("target_draw_id")
    date_local = manifest.get("target_draw_date_local")
    if type(draw_id) is not int or draw_id < 2 or not isinstance(date_local, str):
        raise ValueError("invalid target draw identity")
    parsed_date = parse_draw_date(date_local)
    if parsed_date is None or parsed_date.isoformat() != date_local:
        raise ValueError("invalid target draw date")
    planned_at = _when(manifest.get("target_draw_at_utc"), "target draw time")
    if planned_at.astimezone(ISRAEL).date() != parsed_date:
        raise ValueError("planned draw time is on a different Israeli calendar day")
    if result.get("draw_id") != draw_id or result.get("draw_date_local") != date_local:
        raise ValueError("reported outcome differs from predeclared draw")
    mains, strong = result.get("main"), result.get("strong")
    if (
        not isinstance(mains, list) or len(mains) != 6
        or any(type(n) is not int or not 1 <= n <= 37 for n in mains)
        or len(set(mains)) != 6
        or type(strong) is not int or not 1 <= strong <= 7
    ):
        raise ValueError("invalid reported draw main and strong numbers")
    reported_at = _when(result.get("reported_draw_at_utc"), "reported draw time")
    if reported_at.astimezone(ISRAEL).date() != parsed_date:
        raise ValueError("reported draw time differs from local date")
    _https(result.get("source_url"), "candidate result source")
    published_at = _when(publication.get("published_at_utc"), "publication time")
    _https(publication.get("url"), "GitHub publication link", github=True)
    if publication.get("kind") not in {"github_commit", "github_actions_artifact"}:
        raise ValueError("unrecognized GitHub publication type")
    if published_at >= min(reported_at, planned_at):
        raise ValueError("claimed publication was not before both actual and scheduled draw")
    now = evaluated_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("evaluation time requires a UTC offset")
    now = now.astimezone(timezone.utc)
    if now <= reported_at:
        raise ValueError("cannot score before reported draw occurs")

    common = {
        key: manifest.get(key)
        for key in ("target_draw_at_utc", "target_draw_date_local",
                    "source_commit", "dataset_sha256", "latest_draw")
    }
    latest = common["latest_draw"]
    if (
        not isinstance(latest, dict)
        or latest.get("id") != str(draw_id - 1)
        or not isinstance(latest.get("date"), str)
        or parse_draw_date(latest["date"]) is None
        or parse_draw_date(latest["date"]) >= parsed_date
        or not isinstance(common["source_commit"], str)
        or not re.fullmatch("[0-9a-f]{40}", common["source_commit"])
        or not isinstance(common["dataset_sha256"], str)
        or not re.fullmatch("[0-9a-f]{64}", common["dataset_sha256"])
    ):
        raise ValueError("same-source training cutoff is missing or nonconsecutive")

    docs = {"smart": smart, **controls}
    draw = LotteryDrawRecord(str(draw_id), tuple(mains), date_local, strong)
    scored: dict[str, Any] = {}
    for name in ARMS:
        item = docs[name]
        if not isinstance(item, dict):
            raise ValueError(f"{name}: missing frozen record")
        _digest_ok(item, name)
        if any(item.get(field) != value for field, value in common.items()):
            raise ValueError(f"{name}: source/history/target differs from frozen manifest")
        if item.get("schema_version") != 1:
            raise ValueError(f"{name}: unsupported snapshot schema")
        created_at = _when(item.get("created_at_utc"), f"{name} creation time")
        if created_at > published_at or created_at >= reported_at:
            raise ValueError(f"{name}: snapshot not created before publication and draw")
        if name == "smart":
            if (
                item.get("mode") != "smart"
                or item.get("objective") != "coverage_5plus"
                or item.get("seed") != manifest.get("smart_seed")
            ):
                raise ValueError("Smart objective/seed differs from pre-registration")
        else:
            seed = int(name.rsplit("_", 1)[1])
            if (
                item.get("seed") != seed
                or item.get("expected_next_draw_id") != str(draw_id)
                or item.get("record_sha256") != manifest["control_record_sha256"][name]
                or item.get("real_money_spent_ils") != 0
            ):
                raise ValueError(f"{name}: random baseline was replaced")
        tickets = _ticket_rows(item, name)
        outcomes = evaluate_portfolio_prizes(tickets, draw)
        coverage = five_plus_metrics(ticket.numbers for ticket in tickets)
        overlap = max(len(set(a.numbers) & set(b.numbers)) for a, b in combinations(tickets, 2))
        if name == "smart" and (coverage["is_optimal"] is not True or overlap > 1):
            raise ValueError("Smart 5+ no longer attains its promised coverage")
        hit_three = sum(t.main_matches >= 3 for t in outcomes.tickets)
        scored[name] = {
            "record_sha256": item["record_sha256"],
            "ticket_count": 14,
            "three_plus_tickets": hit_three,
            "any_three_plus_main": hit_three > 0,
            "any_four_plus_main": any(t.main_matches >= 4 for t in outcomes.tickets),
            "any_five_plus_main": any(t.main_matches >= 5 for t in outcomes.tickets),
            "best_main_matches": max(t.main_matches for t in outcomes.tickets),
            "assumed_prize_tier_counts": {
                str(tier): count for tier, count in outcomes.prize_tier_counts.items()
            },
            "maximum_pairwise_main_overlap": overlap,
            "exact_five_plus_probability_fair_main_draw": coverage["probability"],
            "attains_maximum_five_plus_probability": coverage["is_optimal"],
        }

    control_wins = {
        name: scored[name]["any_three_plus_main"] for name in ARMS[1:]
    }
    body = {
        "schema_version": 1,
        "status": "PROVISIONAL_USER_SUPPLIED_RESULT_NOT_OFFICIALLY_VERIFIED",
        "draw": {
            "id": draw_id, "local_date": date_local, "main": sorted(mains),
            "strong": strong, "reported_draw_at_utc":
                reported_at.isoformat().replace("+00:00", "Z"),
            "candidate_source_url": result["source_url"],
        },
        "publication_claim": publication,
        "independent_github_publication_time_verified": False,
        "independent_operator_draw_result_verified": False,
        "commission_approved_protocol_verified": False,
        "no_real_money_wagered": True,
        "positive_expected_value_or_predictive_edge_established": False,
        "preregistered_primary_metric": PRIMARY,
        "frozen_batch_sha256": manifest["record_sha256"],
        "common_training_commit": common["source_commit"],
        "common_training_dataset_sha256": common["dataset_sha256"],
        "portfolios": scored,
        "one_draw_observation_only": {
            "smart_any_three_plus": scored["smart"]["any_three_plus_main"],
            "all_three_random_controls_any_three_plus": control_wins,
            "random_controls_with_three_plus": sum(control_wins.values()),
            "do_not_interpret_as_statistical_evidence": True,
        },
        "scored_at_utc": now.isoformat().replace("+00:00", "Z"),
    }
    return {**body, "report_sha256": _hash(body)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, required=True)
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--publication-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        def read(path: Path) -> dict[str, Any]:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("input root must be an object")
            return value

        paper = {
            "manifest": read(args.batch_dir / "manifest.json"),
            "smart": read(args.batch_dir / "smart_14.json"),
            "controls": {
                name: read(args.batch_dir / f"{name}_14.json")
                for name in ARMS[1:]
            },
        }
        scored = score_reported_draw(
            paper, read(args.result_json), read(args.publication_json)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(scored, stream, sort_keys=True, indent=2, ensure_ascii=False)
            stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Paper score refused: {exc}\n")
    print(json.dumps({
        "status": scored["status"],
        "report_sha256": scored["report_sha256"],
        "official_verification": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
