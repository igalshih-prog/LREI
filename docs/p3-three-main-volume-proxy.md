# P3-A research note — EXACT-three-main entry volume proxy

**Status:** Exploratory inverse-probability descriptive diagnostic ONLY. **NO PLAY.** This does **not** unlock P3-B, authenticate results, measure actual ticket sales or indicate profitable play.

## A distribution-robust mathematical fact

For a fixed legal six-number Lotto entry, assuming an independent fair 6/37 draw,

\[
p_3 = \frac{\binom{6}{3}\binom{31}{3}}{\binom{37}{6}}
= \frac{22,475}{581,196} \approx 3.8670\%.
\]

**Add BOTH tier 7 (3+strong) AND tier 8 (3 without strong)** to count exactly three matching main numbers, separately for regular Lotto and Double Lotto. This eliminates any dependence on the distribution of the strong numbers selected by players. For `N` entries chosen **arbitrarily** (including duplicated entries and correlated preferences), before an independent fair draw, linearity gives `E[C_3 | submitted entries] = N * p_3`. Thus `C_3 / p_3` is *unbiased across repeated fair-draw randomness at fixed submitted entries*, even if players do not choose their six numbers uniformly.

This result **does NOT mean one draw reliably reveals the total sales**. If 1,000 players copy precisely the same line, C3 will be 0 on about 96% of independent draws and 1,000 on the other ~4%; `C3/p3` remains unbiased but has enormous variance. Ticket correlations and clustered selections mean no reliable per-draw confidence interval can be constructed here without assumptions or observed ticket-choice data. This diagnostic therefore produces **no confidence interval, formal sales field, source-verification flag, economic EV estimate or financial authorization**.

## Existing data: six operator *informational-display* observations

Computed only from checked-in `data/prize_observations/3949.json`…`3954.json`, which are **nonbinding page transcriptions** and not archived operator source bytes or approved protocols. Rounded entry-count **proxies** are not independently reported sales, people, forms or revenue:

| Draw | Exact-three regular winners | Regular entry proxy | Exact-three Double winners | Double entry proxy |
|---|---:|---:|---:|---:|
| 3949 | 114,757 | 2,967,578 | 92,786 | 2,399,415 |
| 3950 | 147,314 | 3,809,491 | 114,219 | 2,953,665 |
| 3951 | 138,010 | 3,568,893 | 113,016 | 2,922,556 |
| 3952 | 172,516 | 4,461,206 | 146,638 | 3,792,010 |
| 3953 | 177,274 | 4,584,246 | 152,209 | 3,936,074 |
| 3954 | 72,679 | 1,879,455 | 46,317 | 1,197,742 |

These values change with outcomes and unknown line-selection correlations. **Do not treat the variation as observed sales growth or as a jackpot-return model**; price, tax and co-winner behavior remain separate unverified variables.

## Data and API contract

The function `lrei.lottery.p3_three_main_volume_proxy.three_main_entry_volume_proxy` takes **one complete, valid observation record** and produces a read-only dictionary with `inverse_probability_entry_count_proxy_rounded` for each game, plus unconditional explicit false flags for all official-volume/EV/readiness claims. It cannot silently create missing prize tiers or update the original `ticket_sales_ils: null`. All six original fixtures remain unchanged.

Scientific interpretation: this estimator identifies a useful *moment of the distribution over prospective outcomes*, **not** the player joint-ticket-choice distribution needed for anti-crowd jackpot sharing. Additional authenticated, source-licensed longitudinal entry counts and player-combination summaries remain the research priority. See MASTER #7, P3 #6, provenance #57 and official prize-tier blocker #18.
