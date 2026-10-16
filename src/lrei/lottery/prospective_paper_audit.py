"""Read-only P1 draw scoring of externally timestamped paper portfolios.

Accepts a candidate result without authenticating the external source.
Rechecks content digests, 14-line legality, training cutoff, local draw date
and EXTERNAL publication time. A user-supplied URL is never proof that a
draw result or snapshot was genuine. No monetary value is inferred here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .dataset import LotteryDrawRecord, parse_draw_date
from .prize_evaluation import evaluate_portfolio_prizes
from .recommendation import RecommendedTicket

def _digest(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()

def _utc_time(s: str, field: str) -> datetime:
    if not isinstance(s,str) or not s:
        raise ValueError(field + " must be a UTC timestamp")
    try:
        v=datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError(field + " is not ISO-8601") from exc
    if v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(field + " must be offset-aware")
    return v.astimezone(timezone.utc)

def _valid_url(value: str) -> None:
    parsed=urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("source / artifact references require ordinary HTTPS links")

def _check_portfolio(record: dict[str, Any], *, expected_draw_id: int,
                     actual_draw_date: str, actual_draw_at: datetime,
                     publication: dict[str, str]) -> tuple[RecommendedTicket,...]:
    raw_hash=record.get("record_sha256")
    if not isinstance(raw_hash,str) or len(raw_hash)!=64 or _digest({k:v for k,v in record.items() if k!="record_sha256"})!=raw_hash:
        raise ValueError("portfolio SHA256 mismatch")
    if record.get("ticket_count") != 14 or len(record.get("tickets",())) != 14:
        raise ValueError("each frozen portfolio requires exactly 14 tickets")
    if record.get("schema_version")!=1:
        raise ValueError("unsupported prospective portfolio schema")
    expected_date=(record.get("target_draw_date_local") or record.get("draw_date_local"))
    if expected_date != actual_draw_date:
        raise ValueError("frozen portfolio targeted a different local draw date")
    declared_id=record.get("expected_next_draw_id",record.get("draw_id_expected"))
    if declared_id is not None and str(declared_id) != str(expected_draw_id):
        raise ValueError("frozen portfolio targeted a different draw ID")
    prev=record.get("latest_draw",record.get("dataset_last_draw"))
    if not isinstance(prev,dict) or int(prev.get("id",prev.get("draw_id",0))) != expected_draw_id-1:
        raise ValueError("training cutoff is not the immediately preceding draw")
    if prev.get("date",prev.get("draw_date"))>=actual_draw_date:
        raise ValueError("training includes target or later results")
    created=_utc_time(record.get("created_at_utc"),"created_at_utc")
    published=_utc_time(publication.get("published_at_utc"),"published_at_utc")
    if created>published:
        raise ValueError("publication must be no earlier than creation")
    if published>=actual_draw_at or created>=actual_draw_at:
        raise ValueError("cannot score a record that was not externally published before the draw")
    if publication.get("kind") not in ("github_actions_artifact","github_commit"):
        raise ValueError("publication method is not an accepted independent record")
    _valid_url(publication.get("url",""))
    if not record.get("source_commit") or not isinstance(record.get("source_commit"),str) or len(record["source_commit"])!=40:
        raise ValueError("training code commit is missing")
    digest=record.get("dataset_sha256",record.get("source_dataset_sha256"))
    if not isinstance(digest,str) or len(digest)!=64:
        raise ValueError("training dataset SHA256 is missing")
    normalized=[]
    seen=set()
    for item in record["tickets"]:
        numbers=item["main"]
        strong=item["strong"]
        if (not isinstance(numbers,list) or len(numbers)!=6 or
            any(type(n)!=int or n<1 or n>37 for n in numbers) or
            len(set(numbers))!=6 or
            type(strong)!=int or not 1<=strong<=7):
            raise ValueError("ticket has invalid main/strong numbers")
        line=tuple(sorted(numbers))
        if line in seen:
            raise ValueError("duplicate main ticket")
        seen.add(line)
        normalized.append(RecommendedTicket(numbers=line,strong_number=strong))
    return tuple(normalized)

def score_paper_study(
    portfolios: dict[str,dict[str,Any]],
    publications: dict[str,dict[str,str]],
    *,
    draw_id: int,
    draw_date: str,
    main: tuple[int,...],
    strong: int,
    draw_at_utc: str,
    secondary_source_urls: list[str],
    evaluated_at_utc: str|None=None,
) -> dict[str,Any]:
    """Provisional score only: NEVER elevate unverified third-party results."""
    if len(portfolios)<2 or set(portfolios)!=set(publications):
        raise ValueError("each named portfolio needs independent publication metadata")
    if type(draw_id)!=int or draw_id<=0:
        raise ValueError("draw ID must be positive")
    parsed_date=parse_draw_date(draw_date)
    if parsed_date is None or parsed_date.isoformat()!=draw_date:
        raise ValueError("actual local draw date must be ISO")
    actual=_utc_time(draw_at_utc,"draw_at_utc")
    now=_utc_time(evaluated_at_utc or datetime.now(timezone.utc).isoformat(),"evaluated_at_utc")
    if now<=actual:
        raise ValueError("cannot score before the reported draw")
    if len(secondary_source_urls)<2 or len(set(secondary_source_urls))!=len(secondary_source_urls):
        raise ValueError("require multiple distinct secondary result-source URLs")
    for u in secondary_source_urls: _valid_url(u)
    if len(main)!=6 or any(type(v)!=int or v<1 or v>37 for v in main) or len(set(main))!=6:
        raise ValueError("invalid drawn main numbers")
    if type(strong)!=int or not 1<=strong<=7:
        raise ValueError("invalid drawn strong number")
    result=LotteryDrawRecord(str(draw_id),tuple(main),draw_date,strong)
    scored={}
    source_commits=set()
    dataset_hashes=set()
    for name,record in sorted(portfolios.items()):
        if not isinstance(record,dict):
            raise ValueError("portfolio must be a JSON object")
        tickets=_check_portfolio(record,expected_draw_id=draw_id,actual_draw_date=draw_date,
                                  actual_draw_at=actual,publication=publications[name])
        source_commits.add(record["source_commit"])
        dataset_hashes.add(record.get("dataset_sha256",record.get("source_dataset_sha256")))
        prize=evaluate_portfolio_prizes(tickets,result)
        scored[name]={
            "frozen_record_sha256":record["record_sha256"],
            "external_publication":publications[name],
            "ticket_count":14,
            "best_main_matches":max(t.main_matches for t in prize.tickets),
            "main_3plus_tickets":sum(t.main_matches>=3 for t in prize.tickets),
            "main_4plus_tickets":sum(t.main_matches>=4 for t in prize.tickets),
            "main_5plus_tickets":sum(t.main_matches>=5 for t in prize.tickets),
            "main_6plus_tickets":sum(t.main_matches==6 for t in prize.tickets),
            "matching_strong_tickets":sum(t.strong_match for t in prize.tickets),
            "any_prize_under_assumed_rules":prize.any_prize,
            "tier_counts_under_assumed_rules":{str(k):v for k,v in prize.prize_tier_counts.items()},
            "tickets":[{"index":idx,"main_matches":t.main_matches,"strong_match":t.strong_match,
                        "assumed_prize_tier":t.prize_tier}
                       for idx,t in enumerate(prize.tickets,1)],
        }
    if len(source_commits)!=1 or len(dataset_hashes)!=1:
        raise ValueError("compared portfolios must freeze exactly the same training version")
    body={
        "schema_version":1,
        "status":"provisional_secondary_only_NOT_officially_verified",
        "draw":{"id":draw_id,"date":draw_date,"main":list(sorted(main)),
                "strong":strong,"earliest_secondary_reported_draw_at_utc":draw_at_utc},
        "secondary_source_urls":secondary_source_urls,
        "results_independently_verified_from_official_operator":False,
        "commission_approved_protocol_verified":False,
        "real_money_wagered":False,
        "eligible_for_expected_value_or_profit_claim":False,
        "predictive_advantage_established":False,
        "pre_draw_source_commit":next(iter(source_commits)),
        "pre_draw_dataset_sha256":next(iter(dataset_hashes)),
        "evaluated_at_utc":now.isoformat().replace("+00:00","Z"),
        "portfolios":scored,
    }
    return {**body,"report_sha256":_digest(body)}

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smart",type=Path,required=True)
    parser.add_argument("--random",type=Path,required=True)
    parser.add_argument("--grid",type=Path,required=True)
    parser.add_argument("--publication-manifest",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        record={n:json.loads(p.read_text(encoding="utf8")) for n,p in [
            ("smart",args.smart),("random",args.random),("grid",args.grid)]}
        manifest=json.loads(args.publication_manifest.read_text(encoding="utf8"))
        result=score_paper_study(
            record,manifest["publications"],
            draw_id=manifest["draw"]["id"],
            draw_date=manifest["draw"]["date"],
            main=tuple(manifest["draw"]["main"]),
            strong=manifest["draw"]["strong"],
            draw_at_utc=manifest["draw"]["earliest_secondary_reported_draw_at_utc"],
            secondary_source_urls=manifest["secondary_source_urls"],
        )
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x",encoding="utf8") as f:
            f.write(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:
        parser.exit(2,f"Paper audit rejected: {exc}\n")
    print(json.dumps({
        "status":result["status"],
        "report_sha256":result["report_sha256"],
        "scores":{name:{"best":v["best_main_matches"],"three_plus":v["main_3plus_tickets"]}
                  for name,v in result["portfolios"].items()},
    },ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
