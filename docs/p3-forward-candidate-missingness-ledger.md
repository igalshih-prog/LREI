# P3 forward candidate discovery and source missingness (not observations)

**RESEARCH ONLY / NO PLAY.** Implements [Issue #106](https://github.com/igalshih-prog/LREI/issues/106) without editing the frozen P3 protocol, historic payout observations, actual draw-outcome dataset, or model code.

The JSON file `data/p3_forward_missingness/source_blocked_candidates.json` starts with the two candidate draw identifiers documented in Issue #106 as of 4 November 2026: #3980 (31 October) and #3981 (3 November). **Dates and IDs are source leads, not first-party authenticated or legally binding draw facts.** No winning numbers or payout values are ingested, including third-party-reported strong numbers. Linked sources may all share an upstream source.

Every entry explicitly retains four *unsatisfied* source gates, including authentic HTTPS raw bytes and metadata, binding draw-protocol review, complete Regular/Double 8+8 tier data, and permission plus independent human review. An accepted state is impossible under this discovery-only schema. This is intentional: neither filling a source URL nor passing CI can certify source provenance. Do not confuse its `independently_admitted_draws: 0` with a statement that zero real draws occurred; it means **none are admissible for this analysis**.

## Reproduce

```bash
python -m lrei.lottery.p3_forward_missingness \
  --ledger data/p3_forward_missingness/source_blocked_candidates.json \
  --protocol research/protocols/p3-strong-choice-forward-screen-v1.json
python -m pytest -q tests/lottery/test_p3_forward_missingness.py
```

The checker enforces the sealed start (#3980 and Israel-local 2026-10-30), contiguous increasing IDs and local dates, a metadata-only schema, nonempty HTTPS source leads where claims exist, and explicit unmet source gates. Future draw IDs must be appended in chronological order; if one is undiscovered, research should document the gap in Issue #106 and not silently skip it or manufacture dates. Use `--previous-ledger older.json` before proposing updates to reject deletion or modification of any previous entry; Git review should separately check the committed diff. **Never add a source-confirmation flag or winning outcomes to this discovery-only schema.** Source promotion requires a separate human-reviewed, provenance-attested acceptance workflow.

The output counts discovered candidates by source-state but **never** counts either primary strong group toward the frozen 20+20 floor. It cannot certify independent provenance, research findings, player-choice behavior, causation, statistics, expected return, or real lottery play. The historical P3 prize cohort remains 6/20 with 224 missing tier entries and P1 candidate PR #44 remains quarantined.
