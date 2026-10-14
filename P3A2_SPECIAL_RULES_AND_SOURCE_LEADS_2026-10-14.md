# P3-A.2 — rule provenance and pending-source leads (2026-10-14)

This research stage is still **6 / 20 full eight-tier operator-source observations**,
with **14 incomplete 3955–3968**. This change does NOT upgrade any pending
draw into the verified `data/prize_observations` dataset.

## New high-confidence finding: draw 3953 had different prize rules

The operator published an actual **statutory notice on 5 August 2026**:
https://www.pais.co.il/news/news.aspx?newsId=3133

It explicitly says that after draw 3952 failed to produce a first-prize
winner, the prize allocation for draw 3953 (8 August 2026) changed:
- Tier 1: announced 40m ILS regular / up to 80m Double.
- Tier 2: announced 750k regular / up to 1.5m Double.
- Tiers 3–7: **approximate** shares of **total draw receipts**:
  respectively 2.7%, 2.4%, 3.21%, 6.45%, and 10.5%.
- Tier 8: fixed 15 ILS regular / 30 ILS Double.
- The notice applies until another notice or a first-prize win; draw
  **3953 had a regular first-prize winner**, confirming this stop condition.

The structured note lives at `data/prize_rule_notices/3953.json`.
The record `data/prize_observations/3953.json` now links this notice in
`special_rules_note`. We **do not** have the underlying total receipts,
so applying the announced approximate tier percentages to make up gross
ticket sales or to infer expected winnings would be invalid. Published
winner counts and payouts are observations, not a validated forecast.

The notice was read as operator-site text. The source HTML and the
legally approved drawing protocol were NOT archived or verified.
Its issue date is anchored to the public operator notice, not inferred.

## Fourteen missing draw IDs: unverified research leads only

`data/prize_leads/pending_3955_3968.json` contains *third-party* public
summary leads for the missing window, using:
https://www.paisresults.co.il/index.php

This is **not** the operator's official site and the page explicitly says
its displayed lottery results are not legally binding. Each entry contains
already-cross-checkable date, six drawn numbers, strong number, a
**source-reported** regular first-prize amount, and a **source-reported**
all-games payout total.

The lead records intentionally have:
- `regular_eight_tier_table: null`
- `double_eight_tier_table: null`
- `operator_source_verified: false`
- `approved_protocol_verified: false`
- `ticket_sales_ils: null`
- `tax_paid_ils: null`

They are **research leads, not source-verified prize observations**.
They must not contribute to coverage counts in the 20-draw audit, EV,
positive-return recommendations, or training player-choice popularity.
This distinction is regression-checked in `prize_research_checks.py`.

The indexed original operator draw URLs for 3955 and 3956 either timed
out or lacked the full 16 paid-tier rows in available retrievals. We
therefore preserved all 14 gaps instead of inventing the missing tier
tables from their total winnings.

## Completion criteria and next data acquisition

1. Obtain original operator archive pages / authorized official exports
   for #3955–3968, or trustworthy documentation that provides **all 16
   tier count+payout pairs** for each.
2. Retrieve and retain source bytes+real hash where legal and supported,
   independently verify dates, rule version and promo eligibility.
3. Promote a lead to `data/prize_observations/<draw_id>.json` only if
   the full table is verifiable. Update the audit manifest accordingly.
4. Run the full project CI + focused provenance regression before merge.
5. Begin P3-B payout modeling only when the 20-draw operator-referenced
   payout sample and assumptions are sufficient. No real-money wagers.

**Do not confuse a known jackpot or aggregate draw payout with a
net-positive expected ticket value.**
