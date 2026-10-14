# P3-A.2 — reproducible original-source capture gate

**Why:** The original operator's public archive has downloadable CSV
**draw outcomes**, but no confirmed downloadable archive of **both complete
eight-tier winning-entry/payout tables**. Draws 3955 and 3956 still time
out via the available public search/fetch method, so we cannot honestly
claim their tier amounts or infer them from total prizes. The audited
historical payout sample **remains 6/20** (#3949–3954).

Official archival landing page: https://www.pais.co.il/lotto/archive.aspx
Original draw page structure: https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=3950

## New tool

An offline, network-free source-evidence candidate gate:
`src/lrei/lottery/source_capture_check.py`.

When an authorized researcher obtains a permitted *original operator
results page* (saved UTF-8 HTML or copied UTF-8 visible text), it can:

- Calculate a **real SHA-256 of exact retained input bytes**, not a
  made-up or retrospective web-source checksum.
- Require canonical draw heading and matching draw date.
- Detect both normal and Double Lotto tables, each with exactly eight
  rows in official tier order.
- Compare every published **winner-entry count and prize paid** with the
  separately recorded observation, refusing a missing, duplicate,
  incorrect, or swapped row.
- Require the operator's exact draw-results URL already stored in the
  validated prize observation.
- Require the researcher to provide an actual capture UTC timestamp;
  the tool does **not** guess when the page was fetched.
- Keep `source_authenticity_independently_verified=false`,
  `approved_draw_protocol_verified=false`,
  `human_source_review_required=true`.
  A matching downloaded/copy-pasted string does not authenticate its
  origin, nor convert a public convenience display into a binding draw
  protocol.

**It never fetches a site, scrapes dynamically, automatically promotes
third-party leads, updates the production audit manifest, or estimates
positive expected value.**

## Example after obtaining a legitimate source file

```bash
python -m lrei.lottery.source_capture_check \
  --source-file ./operator_results_3950.html \
  --content-type text/html \
  --observation data/prize_observations/3950.json \
  --captured-at-utc 2026-10-14T06:00:00Z
```

The timestamp **above is only an example**: replace with the
researcher's accurate collection time. The example file does not exist
in the repository and has not been presented as captured evidence.

The output is a **candidate report** with exact input byte count and
SHA-256, not an automatic certification. Preserve source bytes and
check them independently before adding evidence to the audit manifest.
If the page is not accessible, keep the draw missing and record why.

## Deliberate fail-closed parser

The text extraction uses only the Python standard library and accepts
the operator's displayed row format of
`מס' ניחושים / כמות זכיות / גובה הפרס`. If actual saved HTML differs,
the script rejects it instead of silently taking numbers from unrelated
page sections. A future separate parser adapter must be tested against
*retained* actual source pages to support other markup formats.

The regression fixture intentionally synthesizes a sample plaintext
rendering of published draw #3950; it is **NOT original official HTML
nor a source archive**. All tests check code behavior only.

## Next research activities

1. Seek permitted official export or original HTML/source records for
   each of #3955–3968 with all sixteen payout tiers, one draw at a time.
2. Keep separate actual source hashes and evidence-grade statuses.
3. Complete **20/20 full source-referenced observations** and prove the
   audit's `--require-complete` path, then move to P3-B and validate
   participation/payout assumptions.
4. Consider specific consent/terms before programmatic collection.
   Manual review is not replaced by a checksum.

[MASTER #7](https://github.com/igalshih-prog/LREI/issues/7) •
[P3-A.2 #9](https://github.com/igalshih-prog/LREI/issues/9).
