# P3-A.2: private operator prize-page capture pilot (source-blocked research)

> **RESEARCH ONLY / NO PLAY / NO SOURCE ATTESTATION.** This is a *new optional path* to acquire the 14 actual **operator-page originals** for the historical #3955–#3968 cohort when our research browser repeatedly times out. It may not solve reuse rights, signed supervisory-committee protocols or independent TLS/network attestation. Do not bypass blocking, crawl around access controls or continue if the operator's applicable conditions prohibit the intended retrieval/use.

## Why this new path exists

The operator's informational per-draw page `https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId=<draw>` includes **eight Regular and eight Double prize tiers** (winner count and payout per winning entry) for a verified example **#3954**. Its current [archive](https://www.pais.co.il/lotto/archive.aspx) has pages for historical draws, but a direct research-browser request for #3955/#3956/#3957/#3958/#3964 timed out or returned access failure. These are **network-access failures**, not evidence the pages do not exist.

A **newly found external research site**, [Sikui](https://sikui.vercel.app/about/), explicitly says it compiled regular, double and Extra prize tiers from each first-party individual-draw page **since January 2018**, so the entire #3955–#3968 study window is likely retrievable. This claim is a **lead**, not the underlying first-party bytes, a republication licence, or independently attested proof. The existing secondary [Lottery Reminder 2026-08 archive](https://israel.lottery-reminder.com/lotto/archive/2026/08) and [2026-09 archive](https://israel.lottery-reminder.com/lotto/archive/2026/09) cover all 14 as an alternative public comparator, but may share one upstream feed.

Do not confuse the four-digit lottery **outcome CSV** (contains dates, numbers and two top-tier winner counts) with the missing **224 Regular+Double tier rows**. Those rows are **14 × (8 Regular + 8 Double)** and cannot be generated from the outcomes CSV.

## Reuse existing strict code instead of inventing data

The trusted `main` code already implements [`lrei.lottery.prize_capture_intake`](../src/lrei/lottery/prize_capture_intake.py) (offline, strict 16-tier extraction from stored original bytes, output **quarantined**) and [`lrei.lottery.source_capture_check`](../src/lrei/lottery/source_capture_check.py) (compare against separately checked observations). This PR adds only a private **one-shot Windows page capture front-end** and static safety tests, not an alternative data importer or a way to turn an unofficial page into a signed draw protocol.

## Running safely on the Windows machine already used for the official results CSV

From the trusted checkout root **on Windows PowerShell 5.1** (verify `git status` and that you're on the reviewed `main` branch), run the following **one-page pilot only**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\LREI_capture_pais_p3_prizes_v1.ps1"
```

Default is exactly **#3955**; no retries, no third-party redirects, default TLS certificate validation, 30-second timeout, 6-MiB page cap. Save the private directory under `Downloads/LREI-P3-private-*`. It produces private `draw-3955-operator-original.html`, a possibly parsed `draw-3955-quarantine-candidate.json`, parser stderr and `private-capture-manifest.json`. **Only the manifest is suitable for sharing for initial triage**, not the HTML or full tier dataset, unless rights and necessity have been reviewed. A parser failure does **not** infer zeros or silently fill prize tiers; preserve the original HTML locally for a reviewed adapter change.

Only after a clean pilot and a separate check of acceptable use, the optional **full 14-page** run is:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\LREI_capture_pais_p3_prizes_v1.ps1" -FullCohort
```

The script uses one public operator URL per draw in ascending order with a fixed 3-second pause, zero parallel fetching, no retries, no changed user-agent secrets and no TLS bypass; it **does not** authenticate the source/session independently, certify a protocol, obtain rights, modify any repository dataset, add an approved observation, change the four-day stale-dataset gate, or authorize a winning/prediction claim. The per-draw private artifacts are never published or sent automatically.

## Gate after pilot

- **If 1/1 captured and 16/16 tiers extracted:** review the `private-capture-manifest.json`, confirm draw/date/current source hashing, check top-level page against independently archived draw numbers; then decide on full cohort collection and separately required permissions, signed protocols or evidence policy.
- **If HTTP 403/timeout/redirect:** stop; do not bypass blocking or rotate hosts. Secondary links remain research leads.
- **If original HTML fetched but parser refused:** maintain original bytes and fail-closed. Add a reviewed, *synthetic-test-covered* adapter only after inspecting the saved page privately, never infer missing tiers.
- **If all 14 pages yield candidates:** that is at most **224/224 candidate secondary-like values extracted from purported first-party page bytes**, **not 224/224 admitted records**. Preserve explicit zero admitted until independent provenance and use-rights gates are met. The source pages themselves state that only the supervising committee's accepted protocol has legally binding results.

The official [site terms — especially section 3](https://pais.co.il/info/Term-Of-Use.aspx) expressly allow **viewing/downloading for personal, non-commercial use**, while restricting republication, sharing, copying for commercial or public purposes and other uses without prior written authorization. The [operator's archive disclaimer](https://www.pais.co.il/lotto/archive.aspx) also says that web-displayed results are informational; only committee-approved protocols are binding. This **private personal audit only** does not establish the research project's right to publicly redistribute the pages, source data or derived bulk tables. A third party's public display does not grant such permission. Do not run any retrieval that conflicts with the site's current terms or access controls.