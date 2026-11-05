# P3 forward candidate discovery and source missingness (not observations)

**RESEARCH ONLY / NO PLAY.** Implements [Issue #106](https://github.com/igalshih-prog/LREI/issues/106) without editing the frozen P3 protocol, historic payout observations, actual draw-outcome dataset, or model code.

The JSON file `data/p3_forward_missingness/source_blocked_candidates.json` starts with the two candidate draw identifiers documented in Issue #106 as of 4 November 2026: #3980 (31 October) and #3981 (3 November). **Dates and IDs are source leads, not first-party authenticated or legally binding draw facts.** No winning numbers or payout values are ingested, including third-party-reported strong numbers. Linked sources may all share an upstream source.

Every entry explicitly retains four *unsatisfied* source gates, including authentic HTTPS raw bytes and metadata, binding draw-protocol review, complete Regular/Double 8+8 tier data, and permission plus independent human review. An accepted state is impossible under this discovery-only schema. This is intentional: neither filling a source URL nor passing CI can certify source provenance. Do not confuse its `independently_admitted_draws: 0` with a statement that zero real draws occurred; it means **none are admissible for this analysis**.

## Dated follow-up evidence events — 4 November 2026

Do **not** rewrite the first-seen `#3981` entry in `source_blocked_candidates.json`: that row is a frozen discovery snapshot, and the ledger's append-only integrity gate intentionally rejects edits. Later user-computer source-report leads belong in the separate append-only `data/p3_forward_missingness/source_evidence_events.json`.

The first event, `p3e-3981-20261104-capture-delta`, links to two **immutable GitHub commit** metadata records in [quarantined PR #44](https://github.com/igalshih-prog/LREI/pull/44): a user-uploaded Windows HTTPS-style capture report and a subsequent local byte-continuity report. These reports state that #3981 (3 November) was newly appended and the earlier archive bytes matched on the user's machine. The original source bytes and independent server/TLS attestation have **not** been re-verified by the event checker, and the website's binding committee protocol has not been reviewed. These are evidence *leads*, not admitted winning numbers or payout amounts.

Verify this supplemental log and its future append-only additions with:

```bash
python -m lrei.lottery.p3_forward_evidence_events \
  --events data/p3_forward_missingness/source_evidence_events.json \
  --ledger data/p3_forward_missingness/source_blocked_candidates.json \
  --protocol research/protocols/p3-strong-choice-forward-screen-v1.json
python -m pytest -q tests/lottery/test_p3_forward_evidence_events.py
```

The PR workflow compares existing events to the previous base-branch file; only the **first-ever** event may use the one-event bootstrap. All events must reference the same immutable GitHub commit for their paired metadata, preserve all four missing research gates and set every authentication/admission/playing claim to **false**. An empty or invalid source-verification path never qualifies a draw for the frozen P3 20+20 future-observation groups. Independent first-party protocol, lawful source-use rights, full Regular/Double prize tiers and human approval are still required before any separate admission decision.

## Reproduce

```bash
python -m lrei.lottery.p3_forward_missingness \
  --ledger data/p3_forward_missingness/source_blocked_candidates.json \
  --protocol research/protocols/p3-strong-choice-forward-screen-v1.json
python -m pytest -q tests/lottery/test_p3_forward_missingness.py
```

The checker enforces the sealed start (#3980 and Israel-local 2026-10-30), contiguous increasing IDs and local dates, a metadata-only schema, nonempty HTTPS source leads where claims exist, and explicit unmet source gates. Future draw IDs must be appended in chronological order; if one is undiscovered, research should document the gap in Issue #106 and not silently skip it or manufacture dates. Use `--previous-ledger older.json` before proposing updates to reject deletion or modification of any previous entry; Git review should separately check the committed diff. **Never add a source-confirmation flag or winning outcomes to this discovery-only schema.** Source promotion requires a separate human-reviewed, provenance-attested acceptance workflow.

The output counts discovered candidates by source-state but **never** counts either primary strong group toward the frozen 20+20 floor. It cannot certify independent provenance, research findings, player-choice behavior, causation, statistics, expected return, or real lottery play. The historical P3 prize cohort remains 6/20 with 224 missing tier entries and P1 candidate PR #44 remains quarantined.
