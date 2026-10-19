# P1 — Operator-announced 2026 Lotto calendar reconciliation (research only)

**Reviewed 19 October 2026.** This is a cross-check of **published draw
DATES** against the dates already listed in `data/lottery.csv`. It does
**not** verify numbers drawn, strong numbers, payout tables, commission
protocols, actual game sales or official archive-download provenance.
The operator website publishes informational results that are not a legally
binding substitute for the approved draw protocols.

## Two independent operator announcement leads

1. [Mifal HaPais notice #3105 (31 Dec 2025)](https://www.pais.co.il/news/news.aspx?newsId=3105)
   announces **14 extra Thursday Lotto drawings during 2026**, over and above
   regular Tuesday/Saturday draws. The dates are enumerated in
   `tests/lottery/test_2026_operator_calendar.py`. We observed the text from
   the publicly indexed official domain; original HTML bytes are **not archived**
   or hashed in this repository.
2. [Mifal HaPais holiday schedule notice #3116 (23 Mar 2026)](https://www.pais.co.il/news/news.aspx?newsId=3116)
   explicitly lists rescheduled draws **#3914 on 9 Apr**, **#3918 on 23 Apr**,
   and **#3928 on Sun 24 May**. These are **reschedules of regular draws**,
   *not* three additional Thursday draws from the separate 14-draw notice.
   We likewise have no independently archived original HTML bytes.

## Existing CSV matches through its current cutoff

The checked-in draw CSV currently ends at **#3973, 10 October 2026**.
For the eleven operator-announced Thursday drawings at or before that date,
exactly one corresponding archive date was present:

| Announced extra date (2026) | Observed archive draw ID |
|---|---:|
| 8 Jan | 3886 |
| 29 Jan | 3893 |
| 19 Feb | 3900 |
| 12 Mar | 3905 |
| 26 Mar | 3910 |
| 14 May | 3925 |
| 4 Jun | 3932 |
| 25 Jun | 3939 |
| 16 Jul | 3946 |
| 13 Aug | 3955 |
| 3 Sep | 3962 |

All three rescheduled dates match their stated operator-announcement draw IDs
in the existing CSV:

| Shifted draw | Officially announced date |
|---|---|
| 3914 | Thursday 9 April 2026 |
| 3918 | Thursday 23 April 2026 |
| 3928 | Sunday 24 May 2026 |

The other **two Thursdays** observed in the 2026 CSV prior to the cutoff
(April 9 and April 23) are thus accounted for by the second notice; they are
not unexplained entries and must not be mislabeled as suspicious or missing.

The three remaining extra-Thursday dates **15 Oct, 19 Nov and 10 Dec 2026**
are **outside that CSV cutoff**. The published notice does not authenticate
that their drawings actually occurred or establish results for them.
The test automatically expands its checked period if the archived CSV is later
updated, without filling any outcome data or weakening source provenance.

## Test contract and limits

Run:
```bash
python -m pytest -q tests/lottery/test_2026_operator_calendar.py
```

The regression test checks operator-announced dates up to the CSV's own
last draw date, validates exact matching postponed draw IDs/dates, and flags
other unexpected Thursday dates for further notice review. Mutation tests
confirm missing records and changed dates are caught. It deliberately
sets `operator_outcome_or_payout_authenticity_verified=False` and
`data_freshness_verified=False`.

A future amendment to the published operator schedule requires an explicit
source-reviewed test update. Calendar consistency is **necessary but NOT
sufficient** for accepting a candidate historical source or computing
financial value.

**P3-A.2 unchanged:** Only 6/20 prize observations have been recorded;
14 complete 16-tier payout tables for #3955–3968 are still missing
(224 unverified rows), and no independent first-party source has filled
them. [Draft PR #30](https://github.com/igalshih-prog/LREI/pull/30)
must remain quarantined until complete independent raw-source/provenance
review. Lottery Operational Freshness stays RED until a real verified
draw update, and financial decision stays **NO PLAY**.

[MASTER #7](https://github.com/igalshih-prog/LREI/issues/7) ·
[Dataset provenance blocker #18](https://github.com/igalshih-prog/LREI/issues/18).
