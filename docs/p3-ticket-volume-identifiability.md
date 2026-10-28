# P3: Ticket-volume identifiability from published prize counts (research only)

Date: 2026-10-28. Status: **methodological specification, not a validated estimator**.

## Question and scope
Can the number of submitted Lotto lines per draw be inferred from the counts of winning entries at each prize tier? This document separates a mathematical identity from empirical identification. It does **not** use the researcher's unpublished manuscript or NDA-protected data.

## Uniform-line reference probabilities
For an independently uniformly selected six-number set from 37 and strong number from 1–7, relative to a fixed winning outcome, the exact probability of matching exactly `k` main numbers and strong indicator `s` is

`p(k,s) = C(6,k) C(31,6-k) / C(37,6) * (1/7 if s=1 else 6/7)`.

This holds for a uniformly randomized lottomat line *if* the generator is fair. It is **not** the probability of a tier for a human-selected population conditional on a particular realized draw.

For the standard non-overlapping prize tiers (k = 3, 4, 5, 6, each with s=0 or 1), define `p_t` using the formula. If `N` independent uniform lines were submitted, `E[W_t | N] = N p_t`; a single-tier method-of-moments estimate would be `N_hat_t = W_t/p_t`. Sampling uncertainty is substantial for rare tiers, and tier counts are jointly multinomial, not independent.

## Identification limitations
- Public winning-entry counts do **not** identify manual-vs-lottomat entry volumes, their per-combination preferences, and total sales simultaneously. A single draw's observed counts cannot identify all of these without external constraints.
- The fair lottomat assumption must be explicit. Even if fair, human choices can produce realized-draw-dependent tier counts. `W_t/p_t` is a *uniform-reference diagnostic*, **not verified sales**.
- Separate regular and Double Lotto lines. They may have different payouts and participation; never pool their counts as unique players. A person can submit multiple lines and a winning entry is not a unique participant.
- Do not infer monetary ticket sales by multiplying estimated lines by an assumed price without verified game rules and draw-specific product mix.
- Special prize regimes, rollover, Extra, promotional changes, corrections and prize-table scope require separate handling. Zero jackpot winners is uninformative as a point estimate of zero entries.
- The researcher's emailed approximate 30%/24% prize-share figures describe an unpublished study, not a verified per-draw calibration or a proxy for 2026 ticket shares.

## Safe analysis plan
1. **Input gate:** use only the six already reviewed operator-display observations (#3949–3954), retaining `operator_site_display_only_not_binding`; do not promote their authority. Keep #3955–3968 quarantined pending source validation.
2. **Preflight:** validate exact tier names, nonnegative integer winner counts, disjoint tier definitions, dates, and regular/Double separation. Preserve source metadata.
3. **Diagnostics:** compute `W_t/p_t` separately for sufficiently populated tiers and each product; show disagreement across tiers, rather than force a single `N`. Derive uncertainty using a multinomial likelihood only under the explicit uniform null. Prefer high-count tiers for stable descriptive diagnostics; never call confidence intervals valid under unknown human-choice bias.
4. **Sensitivity:** compare the uniform-null baseline to a range of hypothetical manual-share and selection-bias scenarios; label all scenarios assumptions, not fitted 2026 facts. Check whether the observed tier counts can distinguish scenarios; report non-identifiability when they cannot.
5. **Holdout and stop rule:** do not claim predictive or financial validity until independent, authorized, source-verified payout tables and independently observed ticket-volume denominators are available for chronological held-out testing. Never fit and score on the same draw.
6. **Outputs:** research-only diagnostics with explicit `total_entries_verified=false`, `player_popularity_verified=false`, `expected_value_verified=false`, and `authorized_for_play=false`. No modification of `data/lottery.csv`, prize observations, or P1 freshness policy.

## Example of why naive inference fails
Two different populations can produce the same number of winners at a particular tier: a larger population that rarely chooses combinations near the realized result, or a smaller population that happens to favor those combinations. Public tier counts alone cannot disambiguate these explanations. A useful method must expose that uncertainty, not conceal it.

## External dependency
Ask the academic researcher only for already-public methodological references or data that he explicitly confirms are permitted to share after NDA review. The source-provenance and prize-tier acceptance gates in issues #57 and #18 remain open. PR #44 remains DRAFT/NO MERGE. **RESEARCH ONLY / NO PLAY.**
