# P1/P3 secondary-public-source triangulation — 5 November 2026

> **RESEARCH ONLY / NO PLAY / SECONDARY EVIDENCE ONLY / NOT A DATA-ADMISSION DECISION.** This is a human-reviewed read-only cross-check of published *facts* against existing GitHub content, not original operator HTTPS bytes, an independently signed committee-approved protocol, a third-party licence, or proof of independent upstream feeds. **Do not merge quarantined PR #44 based on this note.**

## Exact materials and comparison scope

- Approved main commit: [`db4c1e1f083388d06a43396855f37b2a49cab018`](https://github.com/igalshih-prog/LREI/commit/db4c1e1f083388d06a43396855f37b2a49cab018), `data/lottery.csv`, Git blob `3f3d4c28e8973861fa7b1eb54773096c3f0fb459`. This file includes `#2833–#3973` only.
- Quarantined DRAFT PR [#44](https://github.com/igalshih-prog/LREI/pull/44) at immutable head [`b3a10f11a0fba9d66c548d6ceb74caae669fa88f`](https://github.com/igalshih-prog/LREI/commit/b3a10f11a0fba9d66c548d6ceb74caae669fa88f), `data/lottery.csv`, Git blob `a751eb4675a0c492dbbc723682898243a3f63805`, **through #3980**, not #3981.
- Public non-operator source displays inspected 2026-11-05: [Sikui historical archive](https://sikui.vercel.app/history/), [Lotto Yashir results](https://www.lottoyashir.co.il/lotto/results) and [Lottery Reminder Lotto results](https://israel.lottery-reminder.com/lotto). They may all ultimately derive from the **same official CSV**; three web domains do **not** mean three independent provenance attestations.
- Compared six sorted main-number integers **and** the strong integer, keyed to draw ID and date. No bulk prize-tier dataset was copied. URL availability, exact raw bytes, TLS chain, legal binding protocols, website reproduction rights and published source correction histories **were not** independently verified by this check.

## Read-only reported results — 21 of 21 numerical draw tuples match

| Cohort | Git object | IDs | Result | Correct interpretation |
| --- | --- | --- | --- | --- |
| Historical prize-study draws, **outcomes only** | approved main | **#3955–#3968** (14) | **14/14** matching public historical result entries | Verifies only numbers/strong used to *identify* these draws, **not** their missing 16 payout tiers |
| Newer candidate outcomes, quarantined | PR #44 | **#3974–#3980** (7) | **7/7** matching public result entries | Public content corroboration, **NOT** independent official-source approval or permission to merge |
| **Total** | two different, unchanged Git files | **21 distinct draws** | **21/21**, no mismatch detected | Nonbinding and potentially common-upstream observations |

The seven PR #44 candidate outcomes manually cross-checked against the cited public displays:

| Draw | Local Israel date | Six main numbers | Strong |
| --- | --- | --- | --- |
| 3974 | 2026-10-13 | 03,04,18,19,34,35 | 2 |
| 3975 | 2026-10-15 | 18,22,24,25,27,28 | 5 |
| 3976 | 2026-10-17 | 02,07,15,25,29,37 | 7 |
| 3977 | 2026-10-20 | 03,06,24,25,29,30 | 5 |
| 3978 | 2026-10-24 | 14,24,25,27,29,33 | 3 |
| 3979 | 2026-10-27 | 02,06,07,13,22,35 | 5 |
| 3980 | 2026-10-31 | 01,03,16,21,32,36 | 1 |

The `#3955–#3968` local draw outcomes were already present in main; their external match does **not** provide any of the **224 missing prize tier records**. `#3981` is **absent** from PR #44; do not pretend this range extends to it.

### Reproduction without downloading any website or modifying a dataset

Compare the seven pinned public factual tuples above with the immutable Git candidate:

```bash
git show b3a10f11a0fba9d66c548d6ceb74caae669fa88f:data/lottery.csv | grep -E '^397[4-9][[:space:]]|^3980[[:space:]]'
```

The local CSV is tab-delimited: `draw_id`, `numbers`, `date`, `strong_number`; the 14 older rows can similarly be displayed from `main` with `grep -E '^39(5[5-9]|6[0-8])[[:space:]]'`. A match to a web display establishes only agreement of published content. This report stores no source-copy evidence and its fact checks are **not CI source authorization tests**.

## Additional *outside-PR* prize-tier accounting example: draw #3981

The [Sikui 3981 results](https://sikui.vercel.app/results/), [Lottery Reminder #3981 page](https://israel.lottery-reminder.com/lotto/3981), and [Lotto Ishi #3981 detail page](https://lottoishi.co.il/g/lotto-3981/) display **matching winner count and award per win in all 8 Regular + 8 Double tiers** (16/16 spot-reviewed tier pairs across **three secondary websites**). Lotto Ishi and Lottery Reminder additionally display matching **five Extra prize tiers** (5/5 counts and amounts). This is separate from the historical missing #3955–#3968 cohort and separate from PR #44. Using the visible **Lottery Reminder** Extra 5-tier amounts, an arithmetic check gives:

| Component | Sum of winner count × payout (NIS) |
| --- | ---: |
| Regular 8 tiers | 1,733,546 |
| Double 8 tiers | 2,256,674 |
| Extra 5 tiers | 570,620 |
| **All-game total** | **4,560,840** |

The arithmetic `1,733,546 + 2,256,674 + 570,620 = 4,560,840` matches the headline *secondary* all-game prize total shown by [Pais Results](https://www.paisresults.co.il/), Sikui and Lotto Ishi. **The Extra tier calculation uses a single secondary site for its input**; the same-source arithmetic equality and secondary display agreement do not establish true origin or independent feed validation. No #3981 tier rows were copied into `data/prize_observations/` or promoted.

## Explicit decision (not an admission)

- Approved `main/data/lottery.csv` remains **last #3973 (2026-10-10)**. The scheduled **four-day** operational freshness gate is correctly RED at this date; do not weaken it.
- Private Windows user reports describe a later **#3981** original operator-style CSV at 183,772 bytes and SHA-256 `0034509bdfa510c3978abcff14baee705f6bebf85701c7e6978ac07ecc171560`; the user separately reported a matching local `Get-FileHash`. Those reports do **not** contain the actual original raw bytes and cannot independently attest TLS/source, approved protocols or rights.
- **Zero of the 224 missing historical prize tiers are independently authenticated and rights-cleared.** Public prize-table displays remain leads. Research on `#3981` 16 tiers does not retroactively fill `#3955–#3968` nor count as a frozen prospective P3 observation.
- No number-prediction advantage has been established. **Do not modify models, data admissions, four-day freshness, test expectations or wagering policy from this secondary-only corroboration.**
- In a later lawful/private raw-file review, use **existing** `archive_reconciliation.py` and `source_snapshot_delta.py` on the retained original CSV, then independent human review of the operator's protocol and source-use terms. **No replacement parser or data import is authorized by this document.**

RESEARCH ONLY / NO PLAY.
