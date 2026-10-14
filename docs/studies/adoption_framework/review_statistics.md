# Review: statistics and decision theory

9 October 2026 · An independent review by a subagent given [review_brief.md](review_brief.md) and read-only access to the repository · **Verbatim below.**
* **Its scripts** ran from the session's scratch folder. Copies are in `src/eda/adoption_framework/` (`seed_term_check.py`, `seed_term_independent.py`, `decision_review.py`), with their printed outputs in `data/studies/adoption_framework/`. They read results of seasons ≤ 2024 only, plus the feature-interactions screen's stored gains.
* **Checked by the main session:**
  * the seed-term outputs: a model compared with itself gets ±0.087, and the backfill paired by seed gets [−0.006, +0.035];
  * the cited lines in `feature_provenance`, `line_sharpening` and `feature_interactions`.

---

**(1) Verdict**

Section 2's arithmetic checks out: every P(better), the threshold table, the Kelly ratios and the ±1.3 figure reproduce. Its main point also stands: "tie" throws information away, and a 95% interval is not a betting rule. Its replacement, tiers keyed to P ≳ 0.8, is not supported by its own model or by the project's record. In its own script the best rule at zero cost is always the sign. Once costs are added, the best bar ranges from P 0.5 to above 0.98, depending on cost and prior. The project's own results imply a prior so tight that a flat-prior 0.8 is worth about a third of its estimate. Three things it misses matter more than the threshold:
* compare.py's interval double-counts seed noise;
* everything is judged at the close, but the owner bets earlier;
* the edge appears only in the seasons where it was selected, so "revisit live" takes years unless the edge is large.

**(2) Findings, by severity**

Scores are mLL per match; **+ = the change (or model) better**.

1. **The interval double-counts seed noise (high; observed).**
   * `score.py:402–407` adds both arms' seed variances as if they were independent. Arms run with the same seed numbers share that noise: per-seed losses correlate +0.97 to +0.99, even between different fits (previous vs reference; my rerun, 2020–24 only).
   * A model compared with itself gets ±0.087 (the backfill's `scores.csv`, "stage 1" row).
   * With the seed term paired, the backfill's SE falls from 0.044 to 0.010: **+0.014 [−0.006, +0.035], P 0.92** (men also 0.92), against 0.63 and 0.70 in section 2. For previous vs reference the SEs fall 9–18%.
   * *Change:* seed term = var over seeds of (base − arm) ÷ number of seeds, then re-derive "SE ≈ 0.08". Precision is the cheapest lever. At SE 0.03 the 95% rule gains as much (+0.21) as the best rule at SE 0.08, with a seventh of the inflation.

2. **The wrong target (high; observed).**
   * Section 2 asks what helps "beyond the closing odds". The owner bets before the close, and both adoptions were justified that way (`2026-10-06-surface-ios-profile.md` lines 3 and 31; `2026-10-06-offset-elo.md` line 5).
   * The "94% lean toward harm" (offset Elo, women, at the close) was **+1.11 [+0.04, +2.18]** at the 24-hour price (`2026-10-06-offset-elo.md:44`).
   * Early-price data exist only for 2025–26, which is the proposed holdout. The framework must settle that conflict.
   * *Change:* declare the target price, the population and the seasons before each test.

3. **The prior at the close is near zero (high; observed, then inferred).**
   * The feature-interactions screen tested 28 additions against the model. Their forward gains on 2022–24 have SD 0.080 against a median SE of 0.067. That gives a spread of true effects of only 0.012 (DerSimonian–Laird) and a mean of −0.028 (`screen_results.csv`).
   * The nine with-close increments in the docs show no spread beyond noise (Q 4.5 on 8 df).
   * 116 domain ideas produced one screen pass, which then failed its final test: −0.27 [−0.64, +0.10] (`docs/studies/feature_interactions/README.md:28–32`).
   * With a prior spread τ = 0.05, section 2's readings move: backfill 0.70 → 0.65 (doc SE); offset Elo for women 0.06 → 0.30; Challenger 0.03 → 0.43. The Challenger one shows why τ must depend on the kind of change: with τ = 0.3 it is 0.17.

4. **The rules are written in P, while caveat 2 says expected value decides (high).**
   * The script charges the cost only to adopted nulls (`tie_reeval.py:43–45`). Charged to every adoption (0.02):
     * scenario A: P>0.8 gives +0.148, the sign rule +0.151;
     * scenario C ("most are duds", which caveat 3 itself calls realistic at the close): P>0.8 gives −0.003, the 95% rule +0.012.
   * The expected-value rule is: adopt when B·est > c (B is the shrinkage factor in section 3). In P terms its bar is:
     * 0.5 at zero cost;
     * about 0.81 at cost 0.02 with τ 0.05 and SE 0.08;
     * about 0.98 with τ 0.03.

5. **"The 95% rule overstates just as badly" (medium-high).**
   * True as a ratio (3.2× against 2.8×).
   * False in absolute mLL added to the edge used for stakes: +0.18 against +0.47 (scenario A), +0.12 against +0.43 (C).
   * "Only untouched matches fix this" goes too far. Shrinkage (Tweedie, which feature_interactions already uses) and the bootstrap in `02_contamination_and_forecast.md` §4 remove the expected selection bias.

6. **Live power (medium-high; observed, then inferred).**
   * ±1.28 per year against the average close is right. But the edge is +0.18 [−0.28, +0.64] in 2015–19 (`docs/studies/feature_provenance/README.md:38`). Against Polymarket's close in 2026 it was +0.21 [−2.58, +2.83] (`docs/studies/line_sharpening/README.md:301`), about ±2.3 per year at the venue.
   * Years for a true edge of 0.5 to reach z = 2: 6.8 against the average close, 22 against Polymarket.
   * Running two versions side by side live adds nothing new: the backtests are already paired. A live year adds about a fifth of what 2020–24 holds, so components of 0.05–0.1 need 7–30 years.
   * The backfill cannot be revisited live at all: live, it changes only one coefficient, b̃ for 2027 (0.0432 → 0.0444).
   * Live data is useful for the whole model and for alarms: a −1.3 season reaches z ≈ −2 within about a season.

7. **Kelly (medium).**
   * The ratios hold for small edges. Exact values: half the stake keeps 0.75–0.77 of the growth; double the stake gives −0.12 to +0.23.
   * Stakes come from each match's forecast, not from an aggregate edge. Full-Kelly growth per match equals LL(price) − LL(model) before costs. At Polymarket the costs exceeded it: −1.6% per $1 with the close as truth (`docs/studies/line_sharpening/README.md:302`).
   * *Shrinkage:* logit q_bet = logit p + λ̂(logit q − logit p). λ̂ is the realisation slope (the project's measure of whether the model's moves away from the price are right-sized), measured on untouched matches at the bet-time price.
   * The best stake multiplier is the expected ratio of true to estimated edge, minus a margin for tail risk (2.5× the stake gives −0.7 to −1.7 of the growth). Bet only where the shrunk edge beats the spread plus the fee.

8. **Tier 4 is applied selectively (medium; observed).** Stage 2 itself leans worse on 2020–24: −0.26 [−0.60, +0.07], men, P 0.06 (+ = the adjustment helps; my rerun). By season it was −0.03, −0.04, +0.16, −1.26, 0.00 (`docs/studies/infosys_atp_backfill/README.md:164–168`). Its support is 2024–26, which overlaps the holdout.

9. **Multiplicity, labels and selection (medium).**
   * "About once" is true only counting both tails; per tail it is 0.45–0.65 cells.
   * The "leans" band would tag 35% of cells where nothing is going on, about 4.6 per 13-cell table. Keep labels for the declared primary only.
   * The men's profile row is a logistic regression scored on a chosen 2022–26 window. Over all seasons it was 0.51 [−0.05, +1.07]; correcting for being the best of 6 gives P ≈ 0.81, and the repaired build gave +0.28.
   * The rebuild proposal's 1-SE bar (`03_rebuild_stages.md:124–131`) is applied to the best of about 20 families. With no real effects, that best one clears 1 SE 97% of the time, so it does not support P > 0.84 for a single test.
   * For "equivalent", use a 90% interval and tie δ to the cost bar, not to an edge that may be inflated.

10. **Missing (medium-low).**
    * Incumbency: a lucky change already in the model handicaps a similar challenger by (1 − ρ) times its luck, where ρ is how much their noise overlaps. That is 0.70 SE at P>0.8 and ρ 0.5.
    * Data fixes should be decided on data evidence, never vetoed by outcomes (`03_rebuild_stages.md:33` already says so).
    * Down-weighting is an option between keeping and dropping. The log-loss test asks whether the full change beats none; the encompassing test asks whether its direction is right. A down-weighted version often wins.

**(3) The owner's hypothesis**

It is correct in form. In this project the evidence runs against domain intuition at the close. The decision can be written as one inequality:

**B·(est − sel) − c > 0, where B = τ²/(τ² + s²).**

* est and s are the declared test's estimate and SE (seed-paired).
* B shrinks the estimate toward zero; τ is the typical size of true effects for that kind of change.
* sel corrects for picking a winner: s·√(1 − ρ)·m_K, with m_K = 0.56, 0.85, 1.03, 1.27 and 1.54 for K = 2, 3, 4, 6 and 10 variants.
* c is the cost bar.

*How the idea arose* sets τ, sel, and whether the seasons that suggested the idea may also confirm it:

| Kind of change | τ (mLL) | sel | Role of the outcome test |
|---|---|---|---|
| Verified data fix | — | — | bug check only |
| More of a data type already used, input check clean | 0.02 | 0 | harm check |
| New input with a mechanism, one declared primary test | 0.03 | 0 | decisive |
| Best of K variants | 0.03 | as above | decisive after the correction |
| Found by EDA on the scored seasons | 0.03 | at least 1.5·s | a lead only; confirm on 2015–19, the other tour, or sealed matches |
| Structural (training rows, learner, calibration) | 0.1–0.3 | per K | decisive, plus a check of the realisation slope |

*The cost of being wrong* sets c:
* 0 for a free, reversible change;
* about 0.01 for extra compute or complexity;
* about 0.05 for a new live feed;
* plus a margin if the change is hard to undo, its harm would go unnoticed live, or it widens the disagreement with the market (which raises stakes).

Two worked examples:
* **Backfill:** B 0.52 × 0.027 ≈ 0.014 > 0, so adopt.
* **Event share as a 59th input:** B 0.12 × 0.06 ≈ 0.007 < 0.01, so decline.

**(4) The framework should contain**

* For each test, a declared primary: the target price, the population and the seasons.
* The seed-paired SE, with 16 seeds for small changes.
* A report line for every test: the estimate, the interval, the flat P, B·est, sel and c, then the inequality.
* The tables above, with the owner able to tune them.
* A separate lane for data fixes, with no outcome veto.
* Down-weighting as an option.
* A periodic review of adopted parts that lean worse.
* A ledger of each adopted lean and its sel, subtracted from any claimed edge.
* Stakes sized only from λ̂ measured on untouched matches at the venue's bet-time price, with fractional Kelly.
* Live monitoring of the whole model, plus alarms for harm.

**It should leave out** a single universal P bar, "leans" labels on secondary cells, and P(better) read as "the chance it helps next season". It should also drop the expectation that live data will settle small components, and outcome tests for verified fixes.

My scripts and their outputs are in `C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions\1de31848-973c-4af8-87da-129379e1984b\scratchpad\review_stats\`. The seed checks are in `seed_term_check` and `seed_term_independent`, the decision model in `decision_review`; each has a `.py` and a `.out`. They read only 2020–24 results and wrote nothing in the repo.
