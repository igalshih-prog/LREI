# P3 — Explicit provenance of the Polin evidence in LREI

**2026-10-30. Research only / NO PLAY.** This document distinguishes **research data** from **published findings**, and both from **invented sensitivity assumptions**.

## Sources and access rights

| Item | Researcher had | LREI actually has | Permissible use in LREI |
| --- | --- | --- | --- |
| Polin, Ben Isaac & Aharon, *Patterns in manually selected numbers in the Israeli lottery* (2021), [peer-reviewed published article](https://doi.org/10.1017/S193029750000807X) | ~115 million **manually chosen Lotto entries** across 118 drawings in 2018 | The **published article**, not the raw manual-ticket records | Hypothesis directions; context; no numeric 2026 calibration |
| Polin & Ben Isaac (2023), *A longitudinal analysis of the hot hand and gambler's fallacy biases*, [peer-reviewed published article](https://doi.org/10.1017/jdm.2023.23) | Access to 2018 player-choice study data under a restricted arrangement | The **published article**, not any private rows | Behavioral biases as context; no release of underlying data |
| Correspondence with Dr. Polin (October 2026) | Researcher explained data-access restrictions and uncertainty | High-level methodological guidance supplied in private email | Define unknowns and limits; no redistribution of email contents or claims that the proprietary data were supplied |
| LREI reviewed **2026 operator-display** prize observations #3949–3954 | Not part of the researcher's 2018 private played-ticket files | Six **published prize-tier counts** retained in repo, not independently source-attested | Retrospective descriptive checks only |
| User's uploaded historical results archive (last checked through #3978) | Not a dataset of played guesses | Winning **draw outcomes**, internally content-reconciled, still quarantined for source attestation | Audit historical winning outcomes; NEVER infer who chose which numbers or approve an anti-crowd EV model |

### What the 2021 paper actually established in its 2018 sample

- The manually selected **main** number 7 was highest-ranked and 37 lowest-ranked in all 118 draws.
- Strong numbers 4 and 5 were popular in the manual selections; strong number 1 consistently unpopular.
- The first row of the physical number form was favored relative to the last row; participation and selection uniformity were related to advertised jackpot size. About **33,000 additional manual guesses per extra NIS 1 million announced grand prize** was a historical association, **not a transferable or causal 2026 formula**.
- The original 115 million lines lack unique player/form identifiers in the published study. Neither participant independence nor the complete distribution of chosen **six-number combinations** is available to our code. A frequently chosen individual number does not directly identify a frequently chosen *complete line*.
- The paper mentions an operator-reported ~50% manual share, but the paper does **not** itself supply the total number of machine-generated entries for each draw. No assumed 50% is used as an empirical 2026 parameter.

Verified source: https://dlab.sauder.ubc.ca/sjdm/journal/21/210322/jdm210322.html .

## Implementation: directional constraints without fake frequencies

`lrei.lottery.published_2018_choice_directions.published_direction_sensitivity(strength, hypothetical_uniformization)` produces **hypothetical**, strictly positive player-choice weights that can be passed into the already reviewed and normalized `hypothetical_player_mix_profile` (PR #85).

With an arbitrary effective scale `a = strength * (1 - hypothetical_uniformization)`, the toy model assigns:

- Main values 1–6 weight `exp(a/3)`; 7 weight `exp(a)`.
- Main values 8–27 weight `1`; 28–36 weight `exp(-a/3)`; 37 weight `exp(-a)`.
- Strong 4 and 5 weight `exp(a)`; strong 1 weight `exp(-a)`; all other strong numbers weight `1`.

**The exponential law, coefficients, and values of `strength` and `hypothetical_uniformization` were invented by LREI as controlled sensitivity inputs.** They are **not** estimates from Polin's research, the 2018 underlying rows, the operator, or the six 2026 draw observations. The function bounds both parameters, records metadata/flags, and at `a=0` recovers uniform player choice exactly.

The uniformization parameter allows a thought experiment inspired by the historical qualitative direction that some selection distortions shrank when jackpots increased. **It is not measured jackpot size, and no NIS-to-weight transformation exists or is inferred here.**

Example (all numbers marked hypothetical; **not a recommended bet**):

```python
from lrei.lottery.published_2018_choice_directions import (
    published_direction_sensitivity,
)
from lrei.lottery.hypothetical_choice_model import (
    hypothetical_player_mix_profile,
)

hypothesis = published_direction_sensitivity(
    strength=0.8, hypothetical_uniformization=0.25,
)
toy_profile = hypothetical_player_mix_profile(
    hypothesis["main_weights"], hypothesis["strong_weights"],
    winning_main=[4, 7, 13, 18, 29, 35], winning_strong=4,
    assumed_manual_fraction_all_entries=0.5,
)
assert hypothesis["historical_private_ticket_rows_accessed"] is False
assert toy_profile["source_data_used_for_fitting"] is False
assert toy_profile["authorized_for_play"] is False
```

The guessed 0.8, 0.25 and 0.5 have **no empirically determined meaning**. The six chosen main numbers in the example are not recommendations or a future-draw forecast; they are a fixed arbitrary outcome to condition the model on. This toy mathematical comparison has no validated statistical or monetary value.

## What is needed to go beyond published directional hypotheses

1. **Legally available, traceably sourced** aggregate player-choice data for the right time period, including manual share and choice distribution, or rigorous externally justified bounds.
2. Independently verified current draw/protocol sources and the outstanding **14 complete** payout tables (#3955–3968). Do not promote PR #44 or turn the last user-uploaded results CSV into player-choice evidence.
3. Frozen forward-only evaluation under the PR #89 protocol and an independent test of draw-level support, stability, jackpot participation confounding, and withheld outcome leakage. At least 20 *separate* strong-4 and strong-1 future draws are required by the proposed coverage protocol before even a descriptive comparison; this does not imply inferential statistical power.
4. Clear rejection of claims that human biases improve the odds of the physical winning balls, or that we established positive Israeli 2026 net EV.

**Bottom line:** yes, Polin's **publicly reported 2018 empirical results** materially inform *which hypothesis directions we test*. **No, LREI has not ingested or fitted on the 115 million confidential played-ticket lines.** All unobserved selection intensities and 2026 behaviors remain **unidentified**. **NO PLAY.**
