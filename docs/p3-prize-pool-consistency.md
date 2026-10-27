# P3-A — five-tier prize-pool consistency diagnostic (research only)

**NO PLAY.** No verified sales, ticket-choice distribution, realized returns
or financial EV can be inferred. Every indicator shares the same nonbinding
prize-page transcription; the five numbers are **not independent evidence**.
The percentages are described by the operator as **approximate**.

- Normal tiers 3–7: 1.8%, 1.6%, 2.14%, 4.3%, 7%. Source: normal
  column C in 2025 operator statutory notice
  https://www.pais.co.il/news/news.aspx?newsId=3052 and the 2019
  general rules https://www.pais.co.il/news/news.aspx?newsId=2612 .
- Special boosted draw **#3953**: 2.7%, 2.4%, 3.21%, 6.45%, 10.5%.
  Source: 5 August 2026 draw-specific notice
  https://www.pais.co.il/news/news.aspx?newsId=3133 .
- The *only* eligible JSON observations are exact matches to the six
  checked-in `data/prize_observations/3949.json`–`3954.json` records, with
  matching eighth-tier amounts and an explicit notice for #3953. The tool
  compares a canonical digest of the caller-provided record against the
  matching **local repository fixture** and refuses modified counts or
  payouts. It also refuses use when those repository fixtures are missing.
  This is local content identity, **not official-source attestation**.
  All other draws and unreviewed rules fail closed.

| Draw | Regime | Median of five approximate indicators, NIS |
|---|---|---:|
| 3949 | normal | 24,280,750 |
| 3950 | normal | 26,969,875 |
| 3951 | normal | 29,864,889 |
| 3952 | normal | 36,837,664 |
| 3953 | bonus_150pct | 36,754,667 |
| 3954 | normal | 14,246,419 |

Usage: import `prize_pool_consistency` from
`lrei.lottery.p3_prize_pool_consistency` and provide a complete original
`prize_data.validate_prize_observation`-compatible JSON observation.
The function is read-only: no input mutation, extra source data ingestion,
ticket sales fields, empirical confidence intervals, data promotion, payout
forecasts or player-combination popularity modeling.

To reproduce: `python -m pytest -q tests/lottery/test_p3_prize_pool_consistency.py`.

The current P3-A authenticated historical prize-source gate stays **6/20**;
the missing #3955–#3968 original records and P1 live source provenance
remain external dependencies. Approximate diagnostic convergence cannot
waive these gates, and is not evidence of a favorable wager.
