# P3 prospective group-coverage planner (hypothetical only)

This research-only helper quantifies the **number of future independently reviewed draws** expected to meet the existing frozen P3 floor: at least **20 unique draws with drawn strong 4** and **20 with drawn strong 1**. It does not select numbers, analyze past or future winning outcomes, imply research power, validate source rights, estimate financial returns or authorize play.

### Mathematical assumptions

On each scheduled draw, the strong outcome is assumed uniform on 1..7 and independent across draws. The hypothetical probability of a draw having complete usable **8 regular + 8 Double** prize-source records is a fixed independent fraction q. Thus accepted-strong-4 and accepted-strong-1 are **mutually exclusive** per draw, each with probability q/7, and all other outcomes together have probability 1-2q/7.

The exact distribution is computed by a finite-state multinomial recurrence, capping the two group counts at 20. This is **not** the product of two independent binomial tails. It is *sample availability probability*, **not statistical power**; real source availability may be nonrandom, correlated with draws, or zero without permissions. No empirical q is claimed.

### Reproduce

From the repository root:

```bash
python -m lrei.lottery.p3_group_coverage_planner --protocol research/protocols/p3-strong-choice-forward-screen-v1.json --acceptance-rate 1.0 --confidence 0.9 --horizon 600
python -m lrei.lottery.p3_group_coverage_planner --protocol research/protocols/p3-strong-choice-forward-screen-v1.json --acceptance-rate 0.8 --confidence 0.9 --horizon 600
python -m pytest -q tests/lottery/test_p3_group_coverage_planner.py
```

| Hypothetical independent acceptance fraction q | Scheduled draws to at least 90% probability |
|---|---:|
| 1.0 | 191 |
| 0.9 | 213 |
| 0.8 | 240 |
| 0.5 | 386 |

At q=1.0 the probability of both groups passing is 26.17% by draw 140, 58.29% by draw 160, 82.64% by draw 180, 90.36% by draw 191 and 95.27% by draw 203. A planning horizon too short to reach the threshold returns `null`, **not** a guessed count. None of these are odds of winning a lottery prize.

### Scientific limits

The existing frozen protocol at `research/protocols/p3-strong-choice-forward-screen-v1.json` is read-only. This tool checks its group identity and minimum (4 versus 1, 20 in each) before calculation, but does not alter it. It cannot make #3955–#3968 historically observed draws prospective or fill the 224 missing source-licensed prize-tier entries. Informational sources are not committee-signed legal draw protocols. The external provenance and rights gates remain blocked and must be independently reviewed. **RESEARCH ONLY / NO PLAY.**
