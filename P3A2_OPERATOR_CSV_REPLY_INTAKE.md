# LREI P3-A.2 — complete reply-CSV quarantine intake

**Current payout evidence status: 6 of 20 operator-display result-page
observations available; remaining 14 historical draws (#3955–3968)
lack official complete 16-tier published prize tables.**

This change is only preparation for receiving an authorized official
data export. **No email request has been sent. No operator reply
has been received. No new winnings are asserted.**

## Purpose

The public operator archives give drawn numbers but publicly accessible
bulk results were insufficient to verify paid prize counts and prize
per winning entry in both regular and Double Lotto. Direct web requests
for the historic 3955/3956 result pages timed out.

The merged request worksheet is at:

`data/prize_request_templates/3955-3968_blank_16_tiers.csv`

It includes exactly 14 draws × 2 game types × 8 prize tiers = **224
blank-value rows**. That document contains **no authentic payout data**
and should never pass a completed-response validator.

Once a source is obtained through an authorized channel, keep the
actual attached CSV bytes in a private review folder with all
confidential response/contact metadata protected.

## Usage (ONLY after actually receiving the source file)

```bash
python -m lrei.lottery.prize_official_reply_intake \
  --reply-csv /private/path/actual-reply-3955-3968.csv \
  --historical-csv data/lottery.csv \
  --received-at-utc 2026-10-14T12:00:00Z
```

**The path and timestamp shown above are examples, not an asserted
received file or date.** Replace them with the actual original file and
accurate collection time.

The parser checks:
- Required header names and ordering, no duplicated/unexpected columns.
- Exactly 224 rows in draw/game/tier order, with distinct IDs 3955–3968.
- Actual ISO dates independently checked against lottery.csv.
- All counts and award amounts must be explicit nonnegative integers;
  blanks, formulas, floats, negative values and excessive inputs fail.
- Cannot report winning rows with zero paid amount.
- Suspicious all-zero-draw placeholder values are rejected.
- Actual SHA-256 of *input bytes* (UTF-8 BOM included in hash), byte
  length and researcher-supplied UTC received timestamp.

The returned JSON contains every row as a **quarantined review
candidate**, with:
- `source_sender_verified=false`
- `source_authenticity_verified=false`
- `approved_draw_protocol_verified=false`
- `ready_for_production_prize_observations=false`
- `eligible_for_expected_value=false`
- `has_enough_data_for_profit_claim=false`

**The parser never writes a production observation or audit manifest,
never contacts the operator, and never assumes matching structure
proves official provenance.** The command writes JSON to standard
output; save it only to an appropriate restricted evidence area.

## Human approval gate

An authorized reviewer must verify the original actual source, lawful
retention permission, provenance, the separately logged UTC collection
time, each of 16 published counts/awards per draw, source-file identity,
date, winning 6 numbers + strong number, any special prize rules,
reported aggregate and advertised first/second prizes.

Only afterward prepare separate canonical records under
`data/prize_observations` and the required full source audit manifest,
followed by focused and full CI. The operator display itself warns that
it is not the legally binding approved draw protocol.

## Tests

```bash
python -m pytest -q tests/lottery/test_prize_official_reply_intake.py
```

The tests synthesize clearly **fake filled amounts** in memory solely
to exercise shape validation and error handling. They **do not**
constitute historical or official source records.

After source acquisition, continue MASTER P3-A.2 until all 20 draw
records are credible and independently reviewed, before attempting
P3-B economic evaluation and always supporting a no-play outcome.

[MASTER #7](https://github.com/igalshih-prog/LREI/issues/7) •
[P3-A.2 #9](https://github.com/igalshih-prog/LREI/issues/9) •
[Official data access blocker #18](https://github.com/igalshih-prog/LREI/issues/18)
