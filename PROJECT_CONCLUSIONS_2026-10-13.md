# LREI — evidence-based conclusions and release boundary (13 Oct 2026)

## Final research conclusion

**No historical predictive edge has been demonstrated.** The matched 60-draw,
three-origin Elite-versus-constrained-random experiment produced a mean paired
difference of **−0.0014 main matches per ticket**, with a within-origin,
five-draw block-bootstrap 95% interval **[−0.0598, +0.0610]**. This is not
evidence of an advantage over random draws, and existing historical development
data must not be presented as a fresh untouched holdout.

What *is* supported: **mathematical portfolio coverage** across 14 distinct
six-number tickets. Exact seed-42 portfolios were scored against all
2,324,784 possible 6/37 main outcomes. Smart 3+ covered **50.530544%** and
Smart 4+ covered **50.373454%** of outcomes with at least one 3+ main match;
the Smart 4+ portfolio covered **4.313003%** of outcomes with at least one
4+ match and satisfies the 4+ disjoint-event upper bound. These are properties
of fixed example portfolios, not a proven globally optimal 3+ method or a
population-level model comparison.

For any 14 *distinct* valid main lines with a valid strong number per line,
the fair-game probability of first prize is **14/(7 × 2,324,784) = 1/1,162,392**.
Changing which 14 valid main combinations are used cannot improve that
jackpot probability. Smart 4+ **already** maximizes 5+ coverage as well:
**14×187/2,324,784 = 1/888** for any 5+ main hit. See
[Smart 5+ proof](SMART_5PLUS_PROOF_2026-10-13.md). Prioritize 5+/4+
coverage when the goal is larger prize tiers; 3+ is a separate objective.

## Engineering evidence / implementation completed

* P0 audit and fixes: 1,141 historical rows internally validated (through
  draw ID 3973 dated 10 Oct 2026), corrected DD-MM-YY calendar windows and
  fair 14-ticket baselines, chronological testing, source/date checks,
  stderr logging, strong-number reports, CI partitioning and exact coverage.
* P0 code at \`f949eb8e3b5d8cca82997ec4cf0d6b48d907baef\` had
  [346/346 green tests](https://github.com/igalshih-prog/LREI/actions/runs/38286096656)
  (251 fast + 95 slow).
* P1 code adds opt-in, local no-overwrite, content-hashed pre-draw records:
  \`lrei recommend --mode smart --objective coverage_any_prize
  --snapshot-dir DIR --target-draw-at ISO_WITH_OFFSET\`.
* P1 also adds **post-draw** \`lrei score-snapshot\`, validating the stored
  record/checksum, expected date, chronological ID, complete outcome and
  official-tier evaluation, and writing a separate scored JSON record. It
  never edits the original recommendation. Source URL is *user-supplied*
  provenance and is **not authenticated** by the program.
* Streamlit's 3+ coverage display uses the existing exact bitset routine
  instead of huge outcome sets. UI startup now selects Smart 5+ (which uses the proven 4+ optimal
  construction) while 3+ and historical modes remain available. A Streamlit
  \`AppTest\` smoke check covers app loading and selections.
* P1 validations are fast, target changes only, and do **not** rerun the P0
  research suite. The P1 CI evidence must be consulted for the final PR head.

## What has NOT been proven or fully deployed

1. No pre-draw outcome from an independently published, timestamped future
   snapshot has yet been evaluated. Local file timestamps or self-checksums
   are not independent evidence; publish snapshots externally *before* draws.
2. Uploaded/official historical source matching has not been independently
   reconciled for all 1,141 archive rows.
3. The Streamlit \`AppTest\` exercises app startup and selector state; full
   browser clicks for every model, file upload and download remain a manual
   deployment check.
4. GitHub manual \`workflow_dispatch\` must be tested after the restored
   workflow exists on default branch. Draft PRs do not themselves constitute
   a deployed main-branch release.
5. Individual source URL metadata alone does not authenticate a future draw.
6. This software cannot guarantee wins, cash profitability or stronger
   jackpot odds.

## Stop rule: end retrospective optimisation

Do not tune frequency, EWMA, momentum, adaptive or learned weights against the
same development tail. Freeze objectives and parameters for prospective
evaluation, compare fairly against an independent random baseline, and report
per-origin performance and uncertainty. Only revisit prediction models on
**new**, pre-recorded data with predefined primary metrics.

The immediate engineering completion criterion is a reviewed P0 merge,
reviewed P1 merge, main-branch CI, manual dispatch validation, and a separate
externally published pre-draw record when an actual future draw time and
official current data are available. Future scientific validation cannot be
prematurely marked complete on 13 Oct 2026.
