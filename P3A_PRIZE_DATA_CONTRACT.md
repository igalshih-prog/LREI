# P3-A: Prize observations — separate from lottery result outcomes

This module is the **first data-contract prototype only**, developed on an
isolated draft PR while release gates #4 and #5 remain open. It is NOT
deployed as a prize-value calculator and it makes no winning prediction.

## Information recorded per draw

- Draw ID, date, six sorted main numbers and strong number, cross-checked
  with the independent internal draw-results archive when present.
- Source URL to the exact draw page on **www.pais.co.il**.
- Eight exact prize tiers **each** for normal Lotto and Double Lotto,
  recording the published number of **winning entries**, *not unique
  winners*, and payout per winning entry in whole ILS.
- Announced first and second prizes for normal/double separately, and
  published overall total prizes paid (may also include **Extra** game
  prizes; do not sum normal+double and expect this total to match).
- **Explicit null values** for unavailable sales, taxes, rule notices and
  payouts. No implied sales figures; no imputed taxes, no profitability
  claim.

### Critical source disclaimer

Mifal HaPais's archive says displayed website results are provided for
convenience and are **not legally binding**; the authoritative result is
the draw protocol approved by the supervisory commission.

The field \`source_status\` is therefore fixed to
\`operator_site_display_only_not_binding\`. Manual transcription from
the public page is a data provenance reference, **not** an authenticated
copy of the authoritative approved protocol.

### Concrete reference source

The single initial worked example is
[draw #3950, 28 July 2026](https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3950),
transcribed into \`data/prize_observations/3950.json\` with two eight-tier
tables. Its six main numbers, strong number and date match the existing
\`data/lottery.csv\` record. Its sales and tax inputs are **null**, so
no estimated expected return is produced.

## Programmatic validation

\`\`\`python
from pathlib import Path
from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.prize_data import load_observation, prize_summary

archive = CsvDatasetLoader().load(Path("data/lottery.csv"))
record = load_observation(Path("data/prize_observations/3950.json"), archive)
summary = prize_summary(record)  # descriptive only, never projected profit
\`\`\`

Run:

\`\`\`bash
python -m pytest -q tests/lottery/test_prize_data.py
\`\`\`

The schema refuses missing tiers, imaginary financial metrics, invalid
strong/main numbers, untrusted source hosts, mismatched draw IDs and
result/date inconsistencies with the independent historical outcome CSV.

## Next work after #4/#5 release gates

1. Expand to a consecutive sample of independently checked official draw
   display pages, storing retrieval time, ingestion program version, input
   bytes/hash, exceptions and rule version in an audit index.
2. Investigate lawful bulk access/API or formal request to the operator
   for actual **ticket volume and prize-rule history**, not guessed counts.
3. Build a reproducible economics calculation, explicitly separating fixed
   from pari-mutuel prizes, participation, tax and variable rules.
4. Only then run out-of-time tests for improved **financial** decision value
   vs normal Smart 5+ and random baseline.

Production remains **NO BUY / PAPER RESEARCH ONLY** until independent
financial evidence exists. P3-A cannot change the fair-game chance of >=5
main matches with 14 lines (1/888).
