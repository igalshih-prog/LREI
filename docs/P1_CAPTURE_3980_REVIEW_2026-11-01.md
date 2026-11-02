# P1 Windows first-party capture #3980 — review checkpoint (2026-11-01)

Status: **RESEARCH ONLY / NO PLAY / NOT ATTESTED / NOT APPROVED FOR PROMOTION**.

## Evidence supplied by operator-side Windows capture

The operator-side Windows PowerShell v4 capture was run from trusted `main` after local fast-forward to `7e3eacb3e76fcc06b0e6ba4e02cd6fec4274992c`. The user supplied the resulting **capture-report.json**, not the raw source bytes. The following are **claims recorded in that report**, not independent attestations.

| Field | Reported value |
| --- | --- |
| schema | `lrei-windows-rolling-https-source-review-v4` |
| script SHA-256 | `5b297b1dcd2ade79b13dcb055751d926e554ece264f4b0ccfd5b8f06b47403f3` |
| capture time UTC | `2026-11-01T19:35:00Z` |
| requested/final URL | `https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx` |
| HTTP / content type | `200` / `application/text` |
| raw response bytes | `183730` |
| raw SHA-256 | `5d3cfe5e69abefddb606d9a0de74b8c76d4350e129bdc7d7780b549b4d70714b` |
| archive rows | `4556` |
| modern window | `2833..3980`, `1148` rows |
| latest modern draw | `3980`, `2026-10-31` |
| Israel-local content age | `1` day; `source_recency_ok=true` at capture time |
| previous raw SHA-256 | `3f6ff3b40bcf4ac26407fe09cdea6ac5c23cac78fffccc847f74e07f848f0074` |
| prior modern rows checked | `1147` |
| reported historical differences | `[]` |
| added draw IDs | `[3980]` |
| final first-party HTTPS / TLS disabled | `true` / `false` |
| status | `NEW_DRAW_ROWS_MATCH_PRIOR_HISTORY_REQUIRES_HUMAN_REVIEW` |

The capture explicitly reports `legally_binding_draw_protocol_verified=false`, `provenance_independently_attested=false`, and `dataset_promotion_approved=false`.

## Review boundary

1. The JSON is a **user-provided capture report**, not independently inspected raw bytes or a signed draw protocol. The SHA-256 is a fingerprint for later verification, not proof of authenticity.
2. Keep `operator-source-original.csv` in the private Windows evidence directory. Do **not** commit it or replace `data/lottery.csv` based on this checkpoint.
3. Before any source promotion, human reviewer must verify the raw file digest, review the authoritative protocol and rights, inspect draw #3980 and any revisions, and explicitly authorize the change under the existing freshness policy.
4. PR #44 remains draft/quarantined; do not merge it because this newer capture exists. Its historical snapshot ends before #3980.
5. Do not relabel the new draw as a pre-frozen prospective prediction; maintain the previously frozen evaluation protocol and prospective timestamp gates.
6. Source freshness is **time-dependent**; the reported one-day age applies only at the capture time, not indefinitely.
7. No evidence of predictive advantage or validated economic return is implied.

## Next review inputs

- Independently recomputed digest of the private raw source file.
- Authoritative legally binding draw protocol for #3980 and independent provenance decision.
- Full 8 regular + 8 double prize-tier observations for outstanding historical draws, with provenance.
- CI verification for any subsequent code or dataset changes.

This document records evidence only. It makes no data, prediction, model-weight, CI-gate, or dataset-promotion change.
