# P1 — candidate Lotto historical window through draw 3975 (NOT operator-authenticated)

**Release status: QUARANTINE / DRAFT PR ONLY / NO DATA PROMOTION / NO PLAY.**

## Inputs, original file integrity and known limitations

- A conversation attachment named `Lotto (1)(1).csv` was supplied on **17 October 2026**. Its observed in-session file bytes were **183,520** bytes; SHA-256 `9d3015c90c96713b0171a78dc6249dcc2d95a51168f0efb8303105a09e1ab31a`.
- Parsed as **Windows-1255 (cp1255)** CSV with 12 header columns (the final column empty), and **4,551 data records**. No duplicate numeric draw IDs in that attachment. Parsing/validation of the current target draw-ID window **2833–3975** found no missing IDs or illegal 6/37, strong 1–7 records.
- The **download source URL, HTTP status, response headers, operator response TLS session, first-party acquisition timestamp, and binding committee-approved protocols were NOT independently recorded or verified for these bytes**. User-supplied file name and matching content do not establish origin. Do not set `operator_source_provenance_verified=true`.
- Prior direct first-party Github Actions attempt [run #39030543514](https://github.com/igalshih-prog/LREI/actions/runs/39030543514) failed on the **network timeout** before any live content was obtained. It did not find a discrepancy in this or another uploaded file.

## Exact reproducible normalization and dataset preservation

Keep LREI's existing 1,141-row rolling window, sorted increasing by numeric draw ID. Parse source date using `%d/%m/%Y`; normalize to `%d-%m-%y`; sort the six main integers numerically; use zero-padded two-digit main numbers separated by commas; store strong as an integer in the established tab-separated schema. The new window is **2835..3975** inclusive, with exact output Git blob SHA-1:

`0bdb0eaf554c4240aba88a67820011b1f1e5b076`.

Normalized output length **38,829 bytes**; normalized SHA-256:

`656131fd15ab6e1f2be1fd210f096060177d50dcd514d5027cc8a6b9b37a0464`.

The independent in-session normalization reproduced exact Git blobs of previously reviewed windows:

- Existing main draws **2833–3973**: **`3f3d4c28e8973861fa7b1eb54773096c3f0fb459`**, exactly equal to `main` before this PR.
- Existing draft PR #25 draws **2834–3974**: **`2c538bd31a8653e4d2de39c14e9feef867a2abf3`**, exactly equal to its recorded source-gated dataset.
- Candidate now stages **2835–3975**, latest draw 3975 (15 October 2026) **18,22,24,25,27,28 + strong 5**. Draw 3974 (13 October 2026) **03,04,18,19,34,35 + strong 2**.

A successful byte-for-byte normalization equivalence demonstrates internal consistency and backward overlap with the earlier provided archive. **It does NOT independently verify real-world winning numbers.**

## Independent operator-source gate / release decision

- [ ] Obtain **original direct first-party operator archive response** through an authorized HTTPS browser or manual GitHub source-capture; keep the true raw source bytes privately if permitted, and the exact effective URL, UTC time, HTTP response headers/status, size and SHA-256. No TLS downgrade or `verify=False`.
- [ ] Compare all **1,141** candidate-window rows against **the same newly obtained first-party bytes** using `operator_full_window_capture` when direct HTTPS works. The Actions manual workflow on `main` currently supports `main` and `source-gated-pr25` selection, **not this new candidate branch**; do not claim a new-branch live comparison was performed.
- [ ] If direct fetch remains blocked, perform an **offline content comparison** against a separately retained operator-downloaded export and explicitly require independent/human source provenance review; preserve both origin and legal-status qualifications.
- [ ] Reconcile PR #25's pre-frozen prospective draw 3975 artifact and paper-score record with **verified** draw 3975, preserving the original pre-draw model output/commit/time. Retrospective promotion or changing frozen picks is forbidden.
- [ ] Re-run focused data/full fast/slow CI for the actual final head. Keep separate status for `code_tests_passed`, `operator_source_verified`, `dataset_recency_ok` and `eligible_for_financial_claim`. Passing only code tests is insufficient.
- [ ] Do not merge to `main` before a documented source review. The existing production freshness fail-closed gate for `main` remains a truthful RED until official recent draws can be trusted.
- [ ] P3-A.2 payouts 3955–3968 remain **6/20** prior audited public-page observations, with 14 missing; the ordinary lottery results export does **not** supply verified 16 regular/Double count+payout rows per missing draw. The [formal FOI request](https://github.com/igalshih-prog/LREI/blob/main/P3A2_FORMAL_FOI_DATA_REQUEST_HE.md) remains unsubmitted. Do not infer cash EV or any predictive edge.

**This file records a candidate dataset preparation, not a live first-party operator authenticity result or permission to play.**
