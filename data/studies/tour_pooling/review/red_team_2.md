# Red team 2: audit of the report draft (`docs/studies/tour_pooling/README.md`, 16:45)

9 Oct 2026 · **Checked against:**
* `scores/` (summary.json of 23:35 UTC: aligned not yet scored, select pending);
* `segments/segments.md` and `segments.csv`, `money/roi.csv`;
* `borrow_report/borrow_report.md`, `design.md`.

**Also run:** the test folder (`OMP_NUM_THREADS=2`) and a fit count. **Not checked:** the `{{placeholders}}`. **Sealed:** no result from 29 Jul 2026 on was read; the forecast table holds none.

**Numbers: the draft is accurate.** Every quoted number matches its source at the draft's rounding, with signs right:
* every W1 and W2 reading, by tour and by season;
* the size decomposition: net = purer − more, exactly;
* the edge against the close: 1.157 [0.557, 1.757]; men 1.429, women 0.863;
* every money cell;
* the women's segment cells: the "pooled vs split" sign (+ = pooled better) is correctly turned into "the men's data helps / hurts";
* the winner's-luck arithmetic: 0.0464 × 1.27 = 0.059 and 0.0789 × 1.54 = 0.122;
* the reproduction (max |diff| 0.0), the decided comparison (9.3e-14), 23,758 matches, the 385 fits;
* "142 passed, 1 expected failure" (re-run: 142 passed, 1 xfailed).

The problems below are framing, provenance and the one recommendation.

## Blockers (fix before the owner reads it)

**R1. The provenance claims are not true yet.**
* **Quotes:** "The design was declared before any result was read: design.md, with every later change logged at its end"; "eight declared in advance, and two added after the first results"; "plus two after-the-fact controls".
* **What's wrong:**
  * `design.md` § "Changes after the first score" reads **"(none yet)"**.
  * The 50/50 average (`avg_split_pooled`) and `pooled8` are labelled in summary.json "post-hoc control (lead, after the first blend reading)", and are logged nowhere.
  * The 14:57 amendments (borrow25 nested, borrowsim v3 and coupled, sizectl, blend_control) are filed under "Changes **before** the first score", yet the entry itself says "Made after split's first score".
  * The draft never says which two designs came "after the first results". It calls the 50/50 average a "control", but the report now recommends it.
* **Fix:**
  * Log both groups in design.md, under the right heading:
    * amended after split's first score, before the touched arms' fits;
    * post hoc after the first blend reading.
  * Name the designs in each class in the README.
  * Call the 50/50 average a post-hoc **candidate**, not a control.

**R2. The women's 50/50 shadow recommendation is the garden of forking paths, and its decision rule can't work.**
* **Quotes:** "the women-only signal shows up every way we looked"; "When to decide: on the sealed matches from 29 Jul 2026 … or after about a season of live matches".
* **The forks taken after seeing results:**
  * built as a control after the first blend reading, then promoted to a candidate;
  * the arm to average (split), the weights (fixed 50/50), and the tour (women: +0.13, where men read +0.01).
* **The four "ways we looked" are mostly one signal:**
  * three of them (two models +0.14, blend +0.07, 50/50 +0.13) are functions of the **same** women's split forecasts on the **same** 11,417 matches;
  * the fourth (no flag −0.17) is about the pooled model's own flag. If anything, it says today's model already uses the tour.
* **Omitted:** the 50/50 women's gain by season (mLL per match, + = better than today's model):

  | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to 28 Jul) |
  |---|---|---|---|---|---|---|
  | −0.20 | −0.04 | +0.17 | +0.18 | +0.15 | −0.24 | +0.47 |

  * 2026 (1,672 matches, 15% of W1) supplies 56% of W1's gain.
  * Without 2026, 2022–25 reads about +0.06.
* **Winner's luck:** the correction is applied to the both-tours average (+0.066), not to the women-only figure the recommendation rests on.
  * Women: +0.125 − 1.54 × 0.110 = **−0.04** (K = 10).
  * With the tour choice included (K ≈ 20, m ≈ 1.87): **−0.08**.
* **The decision rule can't decide** (adoption framework § 8: "A part worth ±0.1 needs a decade or more").
  * One season of women's matches (≈ 2,450) gives an SE of about 0.24 mLL.
  * The sealed women's matches so far (453) give an SE of about 0.55.
  * At the observed size, a 95% interval clears 0 only after about 14 seasons.
  * Spending sealed matches (cost class "hard to undo") on a post-hoc part with a corrected gain below 0 is poor value.
* **Fix:**
  * Log it as a lean (lean ledger, or the rejected-ideas ledger), with its season profile and the women-only correction.
  * If it is shadowed at all, say "to bank live evidence, not to decide". Drop the decision date and the sealed-match option.

## Should-fix

* **S1. Equivalence claims.**
  * **Quotes:** "The differences are tiny"; "practically interchangeable"; "**a near-exact tie**".
  * **What's wrong:** "tie" is banned by the project rule (CLAUDE.md; adoption framework § 7). The point estimates sit within ±0.07 (6% of the edge), but the intervals do not: split [−0.29, +0.34] spans ±25–30% of the edge, and borrow25 [−0.17, +0.26]. "Equivalent" needs a 90% interval inside ±δ.
  * **Fix:** "unresolved: the estimates are within 6% of our edge, but the data can't rule out ±0.3 mLL for split".
* **S2. The definition of P(better).**
  * **Quote:** "P(better) is the chance, on this data, that the design really is better".
  * **What's wrong:** framework § 7 defines it as "the flat-prior reading of that one test … not the chance that the change helps". It also ignores that ten designs were tried.
  * **Fix:** use the framework's wording.
* **S3. "That says how small these effects are, not that the test is weak."**
  * **What's wrong:** it says both. A 0.1-mLL effect is undetectable here (SE 0.05–0.16).
  * **Fix:** "small effects, and a test that cannot resolve effects this small".
* **S4. Unresolved leans stated as fact.**
  * **Quotes:** "Dropping the other tour's matches helps a little, because a tour's own matches are worth more row for row"; "The women's matches … are worth more to the men's forecasts as extra data than they cost".
  * **What's wrong:**
    * The purer-data effect is +0.19 [−0.15, +0.54], P 0.86. For women it reverses in 2020–24 (sizectl vs split +0.16: the mixed model better).
    * The men's net is −0.08 [−0.44, +0.27] (P 0.68 that one model is better).
    * Only "more data helps men" is resolved.
  * **Fix:** "leans" and "for men", and drop "because".
* **S5. The money headline.**
  * **Quote:** "Today's model **makes** +1.4% per unit staked at Pinnacle's close".
  * **What's wrong:**
    * It is a backtest on the seasons that chose the inputs, at archived closes. The caveat exists only in § 4.
    * It is the 4-seed version (`money.py`); production averages 16 seeds.
  * **Fix:** "backtests at +1.4% (the inputs were chosen on these seasons; expect less)".
* **S6. "Pinnacle's closing price."**
  * **Quotes:** "beats Pinnacle's closing price by +1.16"; "edge over Pinnacle's closing price".
  * **What's wrong:** the yardstick is the Pinnacle-first input, recalibrated per tour. About 18% of the scored matches use BetOnline's close (August to December 2025 and most of 2026) and about 1% the books' average.
  * **Fix:** "the closing price the model is fed (Pinnacle's to Sep 2025, BetOnline's after), recalibrated".
* **S7. The winner's-luck table.**
  * **The blend is not the declared best:** borrow25 reads +0.047 against the blend's +0.037, with aligned and select pending. Take the best of the six from the final run's `winners_luck`.
  * **K is inconsistent:** the text says "the best of about ten designs", the blend row uses K = 6.
  * **The women-only row is missing:** see R2.
* **S8. Pre-written conclusions for arms not yet scored.**
  * **Where:** the at-a-glance table already says "Decline" for aligned and select. The summary already says "Selective borrowing changed nothing measurable. That covers … translating the statistics to a common scale, and two learned combinations", and "None beat today's model clearly".
  * **Fix:** write these after the final run, and change them if aligned or select reads differently.
* **S9. "None … lost to it clearly."**
  * **What's wrong:** the size control is one of the ten designs and lost clearly for men: W1 −0.31 [−0.60, −0.02]; W2 −0.39 [−0.68, −0.10].
  * **Fix:** "on both tours combined" (sizectl's both-tours upper bound is +0.009).
* **S10. The realisation gate.**
  * **Quote:** "realisation 0.98–1.10".
  * **What's wrong:**
    * That is W1, both tours, only. By tour the range is 0.89 (notour, women) to 1.14 (notour, men), and W2 split reads 0.94.
    * The recommended 50/50 average has **no** realisation row (`realisation.csv` lacks `avg_split_pooled`).
  * **Fix:** give the per-tour range, and compute the 50/50's realisation.
* **S11. The blend's weights.**
  * **Quote:** "Each weight is uncertain by ±0.3–0.5".
  * **What's wrong:** those are standard errors (0.34–0.55). The 95% range is about ±0.7–1.1, so the weights are essentially unidentified (red team 1, S3). Also, men's w in 2022–26 is 0.18–0.29: "a fifth to three-tenths".
  * **Fix:** say "SE", and give the 95% range.
* **S12. The blend control is computed but not reported.**
  * blend_control against today's model reads −0.03 [−0.16, +0.10], and the blend against blend_control +0.07 [−0.09, +0.22].
  * One line would show that the blend's lean is not plain seed averaging.
* **S13. § 3.3, the leans.**
  * **The windows overlap:** "Consistent leans" across W1 and W2 is partly built in, since the two windows share 2022–24 (segments.md's caveat).
  * **One "unresolved" lean is not:** "heavy favourites" is listed under "all unresolved", but it is the one cell that clears 0.
  * **The other side is missing:** for men, the women's data leans *helpful* on heavy favourites (W2 +0.57, P 0.97).
  * **One clause has no support:** "and where a tour's own data is thin" has no segment behind it. Drop it.
* **S14. "Picking 'similar' matches adds nothing."**
  * **What's wrong:** W2 leans worse: −0.09 [−0.21, +0.04], P(better) 0.09.
  * **Fix:** "no measurable gain; leans worse in 2020–24".
* **S15. Attribution and facts.**
  * **"Every one was fixed or declared":** red team 1's S7 (runtime and fingerprint checks in the scorer) is in neither `score.py` nor `design.md`; only the tests cover it.
  * **"Two problems in the similarity sampler that would have made it a disguised random draw":** v1 (a random half) was found by the lead and the analyst (`design.md`). v2 was the analyst's finding, and it selected on dating precision; it was not random.
  * **§ 6, "it fooled our first similarity sampler":** it was the second.
  * **§ 6, "That alone makes men's form inputs spread 1.6–1.9 times wider":** the analyst marks the size match as *inference* (`borrow_report.md`, § 1). Present it as inference.

## Notes

* **N1.** "return per bet" should read **per unit staked**.
* **N2.** "the same settings": 4 seeds per model (production uses 16).
* **N3.** "exact reproduction of today's fits": one fit, 2022 seed 0. The fingerprints of the tested fits match too.
* **N4.** The 50/50 row in the at-a-glance table covers both tours and says "Shadow-run", but the recommendation is women-only. Align the two.
* **N5.** In § 4, quote the women's 50/50 at both books: Pinnacle +0.22 [−0.41, +0.88]; BetOnline +0.10 [−0.76, +0.97].
* **N6.** The three money cells that clear 0 are all men's at BetOnline (borrow50 +0.83, blend +0.70, 50/50 +0.87): 3 of 60, about chance.

## Does it answer the owner's three questions?

* **Q1, split season by season from 2022: yes**, plainly ("Don't split"; the per-season table).
  * Add the men's and women's rows by season. The women's split lean is 2026's +0.80 after 2025's −0.58 (segments.md, sign flipped).
* **Q2, the men/women input: yes, and honestly.** It exists, removing it leans worse for women (P 0.03), and the indoor proxy caveat is stated.
* **Q3, selective borrowing: mostly.**
  * The dose, borrowsim, the blend and the segments are answered plainly. Aligned and select are pending.
  * "Where it helps and hurts" is correctly called leads, but its inference over-reaches (S13).
  * The only "composed model" carried forward (the 50/50 average) is post hoc and not decision-grade (R2).
