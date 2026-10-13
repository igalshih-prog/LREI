# Smart 5+ — final mathematical result (14 Israeli Lotto lines)

## Question

Can replacing Smart 4+ with a more advanced historical prediction model ensure
or materially improve the probability of hitting five (or six) **main** numbers
in at least one of 14 Lotto lines?

**No. The current Smart 4+ construction already reaches the exact combinatorial
maximum for this 14-line objective.** An explicit \`coverage_5plus\` objective
now selects that *same* optimal constructor, with correct 5+ metrics in the CLI
and Streamlit interface. The mode does not fit a new prediction model or claim
a new forecasting edge.

## Proof (uniform 6/37 main draw)

One fixed ticket of six distinct main numbers is hit in five or six main
numbers by exactly:

\`\`\`
C(6, 5) * C(37 - 6, 1) + C(6, 6) = 6 * 31 + 1 = 187
\`\`\`

outcomes out of \`C(37, 6) = 2,324,784\`.

For 14 valid tickets, the union of their sets of 5+ matching draws can cover
**no more than 14 * 187 = 2,618 outcomes**. This upper bound is attainable:
two tickets both matched 5+ by the same six-number draw would have to share
at least four numbers. Thus tickets with pairwise intersection at most **3**
have disjoint 5+ events.

The already validated Smart 4+ coverage engine is stronger: all ticket pairs
share **at most one** main number. Therefore:

* P(at least one 5+ main match) = 2618/2,324,784 = **1/888** = **0.1126126%**.
* P(at least one 5+ main match **and** matching strong number) =
  **1/(888*7) = 1/6216** under uniform independent strong 1–7.
* P(full first prize, six main + matching strong) for 14 distinct tickets =
  **14/(2,324,784*7) = 1/1,162,392**.
* This exact *same* portfolio also reaches the provable maximal P(at least
  one 4+ main match), 4.31300284%, because 4+ events cannot overlap when
  ticket pairs share at most one number.

A 5-main hit without a matching strong number may pay a smaller prize than the
5+strong tier. Prize amounts depend on the actual draw; mathematical coverage
does **not** establish positive expected financial return.

## Product decision

* Smart defaults to the explicit **5+ (and 4+) coverage** option in Streamlit,
  reflecting the requested preference for larger prize tiers.
* Smart 4+ remains available and is **not** an inferior option for 5+ coverage.
  It builds the same optimum by the same algorithm. Both objectives should
  show **0.1126%**, not suggest 5+ hits can be guaranteed.
* Smart 3+ remains an option for those prioritizing frequent small prizes.
* The CLI uses \`--mode smart --objective coverage_5plus --seed 42\`.
* Recommendations may be recorded via the existing optional pre-draw ledger
  and objectively scored after the scheduled draw.

## Stop rule

Do not claim improvements beyond the above proven 5+ probability while using
14 distinct fair-game tickets. An actual increase would require altering
constraints such as the *number* of paid lines, or evidence that the draws
are nonuniform and reliably predictable. No such predictive evidence was found
in the completed LREI evaluations. Do not tune on previously inspected data
to manufacture a signal.
