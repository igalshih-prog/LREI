# P1 — prospective pre-draw recommendation ledger

This is a continuation of the validated P0 branch, not a fresh optimization on
the already-inspected historical tail. The first P1 increment adds an opt-in,
content-hashed, exclusive-write local snapshot of 14 recommended lines **before
their target draw**.

## How to record

Run from a Git checkout with the current CSV, and supply the **actual known
future draw start time** with an explicit UTC offset (illustrative format only):

```bash
python -m lrei recommend \
  --mode smart --objective coverage_any_prize --tickets 14 --seed 42 \
  --snapshot-dir audit/prospective \
  --target-draw-at "YYYY-MM-DDTHH:MM:SS+03:00"
```

Substitute an actual future date/time. Do not reuse this example verbatim.
Other Smart objectives remain independent (`coverage_4plus` and
`historical`), and `regular`, `pro`, and `elite` can also be recorded.
The default recommendation behavior is unchanged when snapshot flags are absent.

Both snapshot options are required together. A snapshot **fails closed** when
the target time is in the past/has no timezone, the latest historical draw
is not strictly earlier than the target date, the latest data is over four days
old, the source Git SHA is unavailable, or there are not exactly 14 distinct,
valid 6/37 tickets each paired with a strong number in 1–7.

## Recorded fields

* UTC creation and proposed target times
* repository Git source commit SHA
* SHA-256 of the exact CSV bytes, latest included draw ID/date, row count
* mode, objective, seed and **reported output candidate count** (this is **not**
  the complete internal compute budget for every engine)
* 14 sorted unique main lines and their strong numbers
* SHA-256 checksum of the canonical JSON payload

Files are created with an exclusive `O_EXCL` open: the command cannot
overwrite an existing file of the same name. A hash mismatch will be rejected.
This protects against accidental overwrites and detects edits, but does not
make the local machine an append-only trust service.

## What this does not yet prove

A local file timestamp and self-computed SHA-256 **do not independently prove**
that the recommendation existed before the draw. To establish externally
auditable pre-draw evidence, publish the JSON in an independently timestamped
GitHub commit, trusted timestamping service, or equivalent external append-only
store **before the target draw**. Preserve its commit URL and content hash in
the subsequent result evaluation. Never change a published snapshot; create a
new one with a new identity for any subsequent prediction.

The current increment does **not** auto-publish snapshots, verify official
future draw results, or establish a predictive advantage. Those are separate
follow-ups in issue #2. Local test cases with injected historical clock values
are software regression tests, not genuine pre-draw forecasts.

The 3+ / 4+ metrics describe mathematical portfolio coverage under a uniform
draw model, not evidence of better jackpot odds.

## Verification and safety checks

```python
import json
from pathlib import Path
from lrei.lottery.prospective_ledger import verify_snapshot

record = json.loads(Path("audit/prospective/your-record.json").read_text())
assert verify_snapshot(record)
```

Fast focused regression suite:

```bash
python -m pytest -q tests/lottery/test_prospective_ledger.py tests/test_cli_snapshot.py
```

These tests are isolated from the already validated P0 historical benchmarks.


## After a future draw: score the frozen record

Only after the recorded draw occurs, independently obtain and verify its
**official** draw ID, date, six main numbers and strong number. Then run:

```bash
python -m lrei score-snapshot audit/prospective/predraw-YOUR-RECORD.json \
  --draw-id OFFICIAL_ID \
  --draw-date DD-MM-YY \
  --main "N1,N2,N3,N4,N5,N6" \
  --strong OFFICIAL_STRONG \
  --source-url "https://www.pais.co.il/YOUR-VERIFIED-RESULT-URL" \
  --output-dir audit/prospective-results
```

The placeholders are not actual winning numbers, IDs or dates. The command
checks the original snapshot hash, registered local target date, chronological
draw ID, complete official-result shape and whether the scheduled draw time
has passed. It then uses the existing official prize-tier evaluator to compute
the number of winning tickets, best tier, best main matches and 3+/4+/5+/6
main-number indicators. Results are saved as **separate**, SHA-256-hashed
JSON using exclusive-write creation. The original prediction stays unchanged.

**Important:** the URL is supplied by the operator; the tool does not fetch or
authenticate it. The scored record marks
`source_independently_verified=false`. A self-hashed local prediction also
does not prove advance publication. For reliable external verification, archive
the predraw file on GitHub (or a trusted timestamping service) *before* the draw
and cross-check the official result from its source afterwards.

This creates an auditable workflow without making any predictive claim, or
retroactively treating development/history tests as prospective evidence.
