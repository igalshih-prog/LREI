# P2 — Preregistered prospective test of an actual lottery bias

**Status: experimental research tool, not a prediction advantage.**

## Why this stage exists

P0/P1 found **no demonstrated forecasting edge**. Exact Smart 4+/5+ already
reaches the highest possible chance of >=5 main matches with **14** tickets
for a fair, independent 6-of-37 draw: **1/888**. Re-ranking the same number
sets cannot improve that maximum under the fair-game null.

For any actual improvement, a persistent nonuniformity in future draws (or
another independently verifiable opportunity outside uniform prediction)
would have to be demonstrated first. Merely choosing "hot" numbers based on
the 1,141 known archive draws does not demonstrate anything about the future.

## Pre-registered single-hypothesis design (frozen 13 Oct 2026)

* Null: independent and uniformly distributed unordered 6/37 main-number
  draws, with strong number irrelevant to the primary evidence measure.
* One fixed alternative only: 37 positive number weights extracted from the
  archived 1,141 training draws, using \`w_i = exp(0.20 * z_i)\`, where
  \`z_i = (historical_count_i - n*(6/37)) /
        sqrt(n*(6/37)*(31/37))\`. The coefficient \`0.20\` is fixed in
  source code, **not fitted** using the future evaluation draws.
* Alternative for an unordered six-number draw \`S\`:
  \`P_alt(S) = product(w_i for i in S)/e6(w)\`, where \`e6(w)\`
  sums six-number products over every possible subset. Under the null,
  \`P_null(S) = 1/C(37,6)\`.
* For each **consecutive** draw that occurs after the model is frozen,
  calculate \`LR(S) = P_alt(S) / P_null(S)\` and accumulate
  \`E_t = LR(S_1)*...*LR(S_t)\`.
* The single prespecified evidence threshold is **E >= 20**, equivalently
  log E >= log(20). Since each likelihood-ratio increment has null
  conditional mean 1, \`E_t\` is a nonnegative martingale; under the null,
  the probability of **ever** crossing 20 is at most **5%**, even with
  continuous inspection. Track the *historical maximum*, not only current E.
* On the first 200 new independently verified draws, report all observations
  regardless of the result; if no threshold crossing occurs, record **no
  demonstrated bias**. Crossing the threshold would justify independent
  review of the data/source and a *new* confirmatory study — it is not a
  guaranteed win or proof of profitable numbers.
* Additional models, alternative beta values, retroactive omissions, multiple
  chosen subsets of draws, and post-hoc switching of stopping rules are
  **not part of this single-hypothesis trial**. Treat any such future
  experiment as exploratory and establish a new externally timestamped
  protocol; do not cite the 5% bound for a selected winner among alternatives.

## Operational commands

Freeze the model **once**, from the current CSV in the checked-out commit:

\`\`\`bash
lrei bias-freeze --output-dir audit/bias-p2
\`\`\`

Publish the exact generated \`p2-frozen-*.json\` **externally and before the
first target draw** (e.g., a public timestamped GitHub commit, permanent
artifact or trusted timestamp service). The JSON records the historical
cutoff, CSV SHA-256, code commit, 37 frozen weights, fixed beta, protocol
and immutable SHA-256 content digest. Local timestamps or hashes are
**not** independent proof of advance registration.

After independently checking the real official next result, append **every
draw**, including draws that harm the hypothesis:

\`\`\`bash
lrei bias-score \
  --frozen audit/bias-p2/p2-frozen-RECORD.json \
  --draw-id OFFICIAL_NEXT_ID --draw-date DD-MM-YY \
  --draw-at "YYYY-MM-DDTHH:MM:SS+03:00" \
  --main "N1,N2,N3,N4,N5,N6" --strong OFFICIAL_STRONG \
  --source-url "https://OFFICIAL-VERIFIED-RESULT-PAGE" \
  --output-dir audit/bias-p2/results
\`\`\`

For the next draw, also pass
\`--previous-score audit/bias-p2/results/p2-evidence-PREVIOUS.json\`.
The input must advance the draw ID by exactly one, and the time must advance
after both model freeze and previous result. Scores form a hash-linked,
exclusive-create evidence chain; prior records are never overwritten.

The tool requires an HTTPS provenance URL but **does not retrieve or
authenticate the official results itself**. Verification against an
independently sourced official feed must happen outside the tool. GitHub
publication is required to prevent retrospective refitting/rewriting.

## Preliminary, NOT confirmatory, look at the archive

The 1,141 **already-inspected** archive records show the 37-number
frequency Pearson statistic \`Q=25.0394\`. Accounting for sampling six
different balls within a draw, the asymptotic adjusted chi-square statistic
is \`36/31*Q = 29.0781\` on 36 degrees of freedom, p≈0.787.
Seven strong-number counts [157,159,164,149,174,178,160] give
\`Q=3.7055\` on 6 degrees of freedom, p≈0.716.
These are descriptive, exploratory tests only. They show no compelling
marginal-frequency deviation, **not** proof of perfect randomness.
Historic data sources have not been independently reconciled row by row.

## Promotion gate to larger-prize recommendations

Even **E >= 20** proves neither the magnitude nor stability of a profitable
bias, and is NOT evidence that proposed tickets outperform the optimal
fair-game 5+ baseline.

Before switching production 14-line recommendations away from Smart 4+/5+:
1. Validate all source draw records against authoritative results.
2. Confirm a prospective predictive signal on new, external data without
   refitting on that confirmatory set.
3. Pre-register **one complete 14-ticket challenger per draw** before that
   draw, plus the existing Smart 5+ benchmark. Measure >=5-main AND strong,
   5-main alone, 4+, and net return after real ticket costs; use matched
   comparisons, report uncertainty and all origins.
4. Demonstrate material positive value on those outcomes, not just a good
   likelihood score. At P(5+ main)=1/888, a few hundred draws yield too few
   5+ observations to support a persuasive payout-advantage claim.

Until all gates are met, the research remains experimental, and the objective
of improving meaningful lottery winnings is **not** accomplished.
