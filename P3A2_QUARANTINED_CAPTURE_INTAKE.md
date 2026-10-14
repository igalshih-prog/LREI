# P3-A.2: quarantined source-capture intake for missing draws

**Status:** 6 fully transcribed public-operator results-page observations out
of a 20-draw target window. **14 (#3955–3968) still missing full tables**.

## Why this stage is needed

The merged original-page verifier from PR #15 can compare a downloaded
results page **against a prize observation that already exists**. For the
remaining 14 missing drawings that observation does not yet exist. This
tool bridges the gap *without claiming source authentication or inventing
prize values*.

## Workflow after obtaining locally saved permitted operator page

1. Save the original, legitimately obtained operator results-page HTML
   (or accurately copied UTF-8 visible text) in a private source archive,
   with a trustworthy capture timestamp. Do not commit personal data.
2. Run a **quarantined draft extraction**:

```bash
python -m lrei.lottery.prize_capture_intake \
  --source-file ./original_operator_draw_3955.html \
  --content-type text/html \
  --draw-id 3955 \
  --captured-at-utc 2026-10-14T07:00:00Z \
  --historical-csv data/lottery.csv
```

The file path and timestamp shown are **examples**, not a file that has
been downloaded or an asserted capture time. Use the actual saved
source file and actual UTC timestamp.

3. The tool outputs **candidate-only JSON**, on standard output, with
   a real hash of the exact supplied bytes, 16 payout-tier rows, public
   draw heading and date checks, and main/strong numbers independently
   looked up in the historical CSV. **These main/strong numbers are
   reference-only and have NOT been extracted and authenticated from the
   supplied page.**
4. A human verifies the page source, the actual main and strong numbers,
   all sixteen payouts and winner-entry counts, prize announcements,
   special prize rules and any source/legal disclaimers.
5. Only after reviewing those facts, separately create the canonical
   `data/prize_observations/<id>.json` and link a truthful entry in the
   P3-A.2 source manifest. Re-run all focused + full CI.
6. Never label candidate output as an authenticated draw protocol, as a
   positive expected-value forecast or as evidence of unusual player
   selection behavior.

## Scope/limitations

- Runs **offline**. No fetching/scraping, network traffic, source
  automation or writing to the production data directory.
- Requires a locally supplied captured page with the recognizable
  `מס' ניחושים / כמות זכיות / גובה הפרס` tier format. **Actual
  operator page HTML may differ**, so a candidate should be rejected
  rather than normalized speculatively.
- Matching an independently stored drawn date and draw number is not a
  cryptographic authentication of the source and does not validate the
  six main numbers shown in the page.
- Test inputs are *synthetically rendered* from prior draw #3950 data
  solely to validate parsing logic. No synthetic page is saved as
  official source evidence.
- Candidate payout rows have no derived financial value or net profit:
  ticket sales, taxes, rule version and advertised aggregate prizes
  remain **null**.
- The public site warns that its display is informative; legally
  binding outcomes are in commission-approved draw protocols.
- No new official prize-tier source was acquired in this PR, so the
  complete dataset continues to be **6/20**.

## Acceptance gates

- Candidate parser passes all regression tests (including duplicate
  headings, invalid date, wrong game, incomplete tier list and illegal
  future self-certification).
- Both focused and full GitHub CI success on the same PR head.
- Human-reviewed original source required for each future promotion.
- A separate, future independent test of candidate extraction using
  *actually retained operator HTML* is needed before relying on this
  parser to collect further official draws.

See [MASTER #7](https://github.com/igalshih-prog/LREI/issues/7) and
[P3-A.2 #9](https://github.com/igalshih-prog/LREI/issues/9).
