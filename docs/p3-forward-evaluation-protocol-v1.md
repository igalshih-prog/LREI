# P3 — Frozen forward-screening protocol v1 (not external preregistration)

**Research only / NO PLAY. Proposed on 29 October 2026, before future study observations are accepted.**

## Why this is necessary

The retrospective six-draw observations #3949–3954, the archived user-supplied draw-outcome CSV through #3978, and the independently reported already-public draw #3979 are **known before this protocol**. PRs #84–#88 inspected these historical observations extensively, including strong-4 versus strong-6/7 patterns and jackpot confounding. None of these draws may later be labeled *out-of-sample future validation*, even if a later source-verification step upgrades their provenance.

This **repository commit** documents a proposed method before *future accepted observations* are inspected; it is not independently registered or timestamp-attested by an external preregistration service. The hypothesis is historically inspired by Polin, Ben Isaac & Aharon (2021), https://doi.org/10.1017/S193029750000807X , **and informed by 2026 exploratory data**. The latter creates discovery bias. Publishing a forward plan mitigates future flexibility but cannot make prior exploratory data confirmatory.

## Frozen method and chronological boundary

Canonical specification: `research/protocols/p3-strong-choice-forward-screen-v1.json`. The PR/merge Git commits contain the versioned text. Once draws are eligible, **do not alter the primary outcome or lower boundary silently**; any v2 would need its own published protocol and a later untouched cohort.

- Candidate future IDs **3980 or higher** AND operator draw dates **2026-10-30 or later**. Both restrictions must pass. This excludes **all** old studied draws, including already-public #3979, even if a later operator document authenticates them.
- Strictly distinct, ascending draw IDs, six distinct 1..37 main results, drawn strong 1..7, and full prize-tier counts for **both regular and Double** (eight tiers each) are mandatory for **structural screening**.
- The primary *descriptive* endpoint is **regular Lotto, exactly three main matches**. For each independently reviewed draw with a nonzero count in this class, define `r_d = W(3+strong) / [W(3+strong) + W(3)]`. Report the **unweighted per-draw mean for draws with drawn strong 4**, minus the analogous mean for **drawn strong 1**, in percentage points. Under uniform independent player strong-choice the reference fraction is 1/7; this physical null is NOT a claim about realized player behavior.
- Prior literature suggests historic strong-4 preference and historic strong-1 avoidance, but the directional contrast `mean(r | drawn strong=4) > mean(r | drawn strong=1)` remains **a future-only observational hypothesis**, not causal and not a validated 2026 preference. Group sizes and missing zero-denominator strata must be reported.
- Require **at least 20 unique reviewed draws with strong 4 and 20 with strong 1** before even considering the primary descriptive summary adequately covered. This is **a minimum information floor, not a statistical-power proof or permission to assert significance**. It may take many months because the drawn strong outcome is random. Do not substitute 20 ticket entries for 20 draws.
- Secondary exploratory analyses may examine regular and Double k=3,4,5, all seven strong outcomes, jackpot regime, special payout notices and counterfactual selection models. They cannot overwrite or retroactively select the primary endpoint.
- **No hypothesis fitting on candidate draws**. No significance claim, p-value, causal effect, win-probability improvement or net expected value until a separately justified methodology and independent human source review exist.

## Source and timing gates that cannot be automated away

The current screen function `lrei.lottery.p3_forward_screen` is **structural only**. It reads a caller-supplied JSON array and checks chronological and prize-count shape. It **does not** contact Mifal HaPais, validate the real operator's original bytes or identify whether an observation is a genuine draw. The source-status string `operator_site_display_only_not_binding` and URLs to the operator are not source authentication. An attacker can type an official-looking URL, and a successful screen must never certify the source.

Before any future observation enters a substantive forward research set:

1. Obtain a **genuinely new** HTTPS first-party export or individual first-party results/prize-tier page with TLS certificate verification and original response metadata; retain the real SHA-256 of the actual bytes and the capture UTC time. An old user upload, no matter how internally consistent, does not satisfy source acquisition proof.
2. Independently verify authoritative draw/protocol identity and its legally binding status, subject to the applicable permissions. Preserve an auditable human source-review record and use immutable repository/archival timestamps. A status flag alone is insufficient.
3. Cross-check the draw outcome against the archived winning history, complete 8+8 winner/payout tiers, product and payout-rule exceptions. Ensure that the draw was **not already inspected before protocol freeze**. Distinguish published informational prize data from commission-approved binding protocols.
4. Freeze the protocol BEFORE the evaluated draw occurs, not merely before data are eventually entered. The current commit proposes the prospective boundary; no past observations are automatically grandfathered.
5. Preserve all consecutively eligible independently reviewed draws (report omissions and missing sources) to avoid cherry-picking. Do not count missing payout tables as zero winners.

The tool deliberately outputs `source_review_completed=false`, `raw_first_party_source_verified=false`, `binding_protocol_verified=false`, `independently_registered_before_draws=false`, `prospective_holdout_validated=false`, and `authorized_for_play=false` **even if a synthetic test supplies 40 apparently complete records**.

Example local structure screen (only on researcher-controlled, legally usable candidate JSON; **never run fake fixtures as real data**):

```bash
python -m lrei.lottery.p3_forward_screen \
  --candidate-json /private/staged-future-observations.json \
  --protocol research/protocols/p3-strong-choice-forward-screen-v1.json
```

No such real future file is committed or asserted to exist. Test files generate **fabricated numbers for unit testing only**, not research inputs.

## What the currently available data *can* and *cannot* support

- **Existing history:** 4,554 rows in the user's last original archive, a 1,146-row candidate through #3978 (content-checked, source capture unverified), and six retrospective operator-display prize observations. No re-upload requested.
- **P1 #57:** stale main at #3973 as of Oct 29, scheduled operational freshness #15 RED by policy. The candidate #44 through #3978 is also aged beyond the four-day gate and source-unverified. Neither should be promoted without a new first-party capture.
- **P3-A #18:** 14 of the desired 20 draw-specific complete prize observations (#3955–#3968) still absent. Mifal HaPais public enquiries directed us to https://www.pais.co.il/lotto/archive.aspx and the program page, **without supplying full missing payout tables or a source-authenticated export**.
- **Academically meaningful next progress** is better source coverage and chronology. No amount of fitting synthetic number weights or repeatedly leaving out one of six old draws will eliminate missing independent provenance or participant-selection data.

**Acceptance condition for PR:** green exact-head CI and maintained source/no-play gates. Merging only freezes this research plan; it **does not** greenlight operational freshness, data ingestion, financial recommendation, or a claim that the future research already succeeded.
