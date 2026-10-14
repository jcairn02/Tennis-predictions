9 October 2026 · The lead's independent position (round 1), written before reading the reviewer's in the [lean review](../README.md)'s debate (the session that ran it) · **Verbatim below.**

---

# Round 1 — the lead's independent position (written before reading the reviewer's)

Units: mLL per match; + = the named part (or change) better. No "tie": unresolved + P(better).
Incumbency carries little weight (the owner's instruction): the question is "would we put this in today?".

## 1. Stage 2, the speed adjustment — KEEP LIVE as a logged lean (item 7's terms), ~60%. Real alternative: shadow.

Why it went in (chain): (a) the men's speed-change signal replicated in the point-sequence study, +0.090 [+0.017, +0.162]
per SD 2022–24; (b) result-free mechanism: +0.33 pp first-serve points won per SD of speed state, beyond box-score form;
(c) the pre-registered primary (a TabPFN column) was unresolved, +0.07 [−0.05, +0.18], because TabPFN captures ~8%;
(d) the pre-registered secondary (the nudge) +0.41 [+0.04, +0.78] on men 2024–26; (e) 28-day memory +0.54 / +0.38
(today's sources) after two more outcome runs on the same seasons.

What still holds: (a)(b) — and the information replicated blind: the registered 14-day statistic on 2025–26,
+0.103 [+0.029, +0.178]. (c) holds. What does not: the *procedure's* realised record outside 2024–26 —
2020–24 −0.26 [−0.59, +0.06], P 0.05; by season −0.03, −0.04, +0.16, −1.26, +0.00. Its headline lives in 2025–26.

Why I still keep it: the realised loss is dominated by 2023, where a coefficient fitted on 2019–22 (b̃ 0.07) met a
season whose effect was negative (−0.05). The decision is forward-looking: E[gain] ≈ 240·(b̃·μ − b̃²/2) per men's match
(backfill §5's expansion). With b̃ 0.034 (2026) – 0.044 (2027): μ = 0.024 (RE 2019–24) gives ≈ +0.02 to +0.05;
μ ≈ 0.03 (my read of the blind replication) ≈ +0.08 to +0.10; μ = 0.044 (RE 2019–26) ≈ +0.23 to +0.28; μ = 0 gives
≈ −0.15 to −0.24. Positive unless μ < b̃/2 ≈ 0.02 — I put that at ~30%. The evidence about stage 2 on sealed matches
accrues identically live or in shadow (both stages are computed either way), and the collector runs either way, so
live vs shadow is purely the sign of E[gain] at the bet-time price: small positive. Stakes take no credit from it.

Strongest case against me (which the framework itself makes): a best-of-K secondary whose support comes from the
seasons that chose it, leaning worse outside them, is "a lead only — confirm on sealed matches", i.e. shadow. And the
live forecast gains a failure mode (radar breaks at a new event's first rounds, a silent collector).

Change worth considering: the cut-off/alarm as item 7, alarm tighter in the first season. I considered a smaller b̃
(halving it cuts a 2023-like season's loss from ≈ −0.77 to ≈ −0.33 while keeping most of the upside), but choosing b̃
after reading these seasons is outcome-tuning; I would not do it without a rule set in advance.

Flip me: a credible reason μ ≈ 0 going forward (e.g. the 2025–26 information effects are the 28-day variant's
selection artifact and the 14-day replication is itself fragile), or evidence the live speeds are worse than the
backtest's "today's sources".

## 2. Per-surface IOS profile — CHANGE to pooled (item 8's test and rule), ~70%. Do not drop the whole profile on
current evidence; run a cheap ablation to find out.

Why it went in: the long-memory profile entered the 53 on 2 Oct against a null linear result, no rationale recorded,
on the owner's per-statistic thesis; TabPFN-Thinking then leaned on it most (shuffle importance 0.62 men / 0.74 women —
importance, not marginal value). On 6 Oct the per-surface build was kept: neutral with the odds (+0.01 [−0.10, +0.13]),
+ without them (men +0.83 [+0.39, +1.27]), "we may bet early".

Does it hold: neutral with the odds — yes. + without the odds — no: once the offset Elo is in, +0.07 [−0.07, +0.21]
(that gain is what the offset Elo carries). Early bets — no support: 24 h −0.06 [−0.43, +0.31] (P 0.38), −0.02 alone.
Women: no match-level benefit anywhere; without odds worse in 2022–24 (−0.73 [−1.14, −0.32]).
So every positive reason is gone; what remains is a costlier build (1.7× compute, own refresh steps) with no measured
benefit at any price. Unresolved everywhere → the simpler/cheaper member (pooled). Item 8's rule does exactly this.
Keep the surface IOS for forecasting individual statistics, where it is better.

Dropping the whole long-memory profile (37 inputs): never tested inside TabPFN. Stage D found the per-statistic value
against the odds in recent form, not long-memory traits — so the owner's thesis does not specifically protect this
profile. A column-drop ablation is cheap (no chain rebuild). Proposed, pre-declared: both stages, both tours, 2020–24,
paired seeds; + = without the profile better; propose dropping it unless it is worse with P(better) ≤ 0.2. Caveat: the
target is early prices, which a close-only read cannot test, so a non-harmful close read would go to the owner as a
proposal, not as an automatic removal.

## 3. `ios_points_short` — REMOVE, unless a cheap ablation shows TabPFN needs it, ~60%.

Why it went in: Stage B's strongest single row given Elo (men 3.72, women 5.02 over all seasons), carried through
Stage D and the audit's ladder (+0.13 [+0.05, +0.20] men beyond adjusted points, 2022+), into the 53. Pre-2022 data
pick the same memories (so the memory itself is not the problem).

Does it hold: as prediction beyond Elo, yes; as unique information, no — after the chronology repairs its increment
beyond the two-week adjusted points is −0.013 [−0.091, +0.066] (men), −0.052 [−0.139, +0.035] (women). It is a
points-won aggregate, i.e. a priced-in control in the owner's thesis, and the model has four other strength controls of
that kind plus Elo. It also carries the joint-solve leaks the lower-level study names (pool-wide prior).

Recommendation: drop it (57 inputs), with a harm check first: the same pre-declared design as above; keep it only if
the 58-input model is better with P(better) ≥ 0.8 (equivalently: remove unless the ablation is worse with P(better) ≤
0.2). The bar follows the framework: a new input at the close needs B·est > c ≈ 0.01; with τ 0.03 and SE ≈ 0.04 that is
P ≈ 0.76–0.8, and the same bar applies symmetrically to keeping one.

Flip me: a TabPFN-level reading that it helps; or evidence the repaired cohort's −0.013 does not transfer to the
leak-proof construction the model actually uses.

## Summary
* Stage 2 — keep live as a logged lean (item 7), no stakes credit — 60% — positive forward EV unless μ < ~0.02; sealed
  evidence accrues either way.
* Per-surface IOS — change to pooled (item 8) — 70% — every reason it was kept is gone once the offset Elo is in; ties
  go to the cheaper build.
* `ios_points_short` — remove pending a harm check — 60% — redundant with the two-week adjusted points; a priced-in
  control.
