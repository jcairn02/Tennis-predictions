# Tour pooling: the design, declared before any result was read

9 October 2026 · Written for the owner and the study's agents · **Pre-registered:** written, and the fits started, before any candidate's forecast was scored. Changes after the first score are logged at the end. The full timeline, judgment calls and threats to validity are in [audit_trail.md](audit_trail.md).

## The owner's questions (9 Oct 2026)

1. **Split.** Train a men's model on men's matches and a women's model on women's matches. Compare them season by season from 2022 (expanding window) with the current single model trained on both.
2. **A men/women input.** If the model has none, add one and see whether it helps.
   * **It already has one:** `tour` (0 = men, 1 = women) is one of the 58 inputs. So the test runs the other way: drop it and see what it was worth.
3. **Borrowing.** Predict women mainly from women's matches, but borrow men's matches at lower weight where they help; the same for men. Find when the other tour's data helps and when it hurts, and compose one or two models that borrow selectively.

## The target and the yardstick

* **The target:** bets at the close. The model is fed the Pinnacle-first close, as the current instance is. Main-tour matches, both stages.
  * Early prices (Polymarket hours before the start) are not tested here.
* **The seasons, as asked:** each season from 2022 to 2026, each trained on 2013 .. Y − 1.
  * **2026 runs to 28 Jul 2026.** Events from 29 Jul 2026 are the proposed sealed holdout ([clean holdout](../clean_holdout_rebuild/README.md)): their results are never read. The fits predict them; nothing scores them.
  * 2025 to 28 Jul 2026 is the holdout's exposed part, read about 20 times before. This study reads it again, and its report records the look. The [lean ledger](../adoption_framework/lean_ledger.md)'s look table counts looks at the sealed matches only; this study makes none.
  * Also reported: 2020–2024, the decided comparison's default window.
* **The yardstick: the current instance**, `data/studies/current_best_model/pinnacle_first_2026-10-09/` (one model on both tours, `tour` an input), seeds 0–3, read only. The frozen reference is reported too, for the record.
* **The scoring is `compare.py`'s recipe, unchanged** (`src/eda/current_best_model/compare.py`: `walk_forward`, `forecasts`, `paired`, `close_forecast`).
  * Each model is the mean of its seeds 0–3.
  * The per-tour calibration slopes and stage 2's speed coefficient b are fitted walk-forward on 2019 .. Y − 1, debut seasons out, b shrunk (τ 0.05), on each model's own forecasts.
  * Paired log loss in mLL per match. **+ = the candidate has the lower log loss (better).** 95% intervals over four-week blocks plus the seed term, paired by seed.
  * **Reading:** "better" or "worse" when the interval clears 0, otherwise "unresolved" with P(better).
  * `compare.py`'s own command line compares against the frozen reference only, and its loader requires a fit trained on every frame match of 2013 .. Y − 1. The study's scorer therefore calls `compare.py`'s functions with the current instance as the base and its own checked loader for the candidates.

## The arms (every arm: seeds 0–3, seasons 2019–2026; code in `src/eda/tour_pooling/common.py`)

| Arm | Models | Training rows for season Y (from 2013 .. Y − 1) | Inputs |
|---|---|---|---|
| **pooled** (the yardstick) | one for both tours | every match | 58, `tour` among them |
| **split** (question 1) | one per tour | its own tour's matches | 58 (`tour` constant) |
| **notour** (question 2) | one for both tours | every match | 57: `tour` dropped |
| **borrow25** | one per tour | its own tour's, plus a random 25% of the other tour's | 58 |
| **borrow50** | one per tour | its own tour's, plus a random 50% of the other tour's | 58 |
| **borrowsim** | one per tour | its own tour's, plus 50% of the other tour's in expectation, drawn by similarity (below) | 58 |
| **aligned** | one for both tours | every match | 58; the 39 box-score statistics in units of their own tour's spread (below) |

* **"Lower weight" without weights.** TabPFN takes no sample weights; it learns from the rows it is shown. A tour's model gives the other tour less say by being shown fewer of its rows (as the training-window study's decay arm did).
  * pooled, borrow50, borrow25 and split form a dose: 100%, 50%, 25% and 0% of the other tour's matches.
  * Draws are new per season and seed: `default_rng([20261009, Y, seed, arm code, tour code])`.
* **borrowsim: borrow the other tour's matches that look like ours.**
  * A classifier learns to tell the two tours' matches apart from what a match looks like, unchanged when A and B swap: each |difference| input, the price's |log-odds|, each pair as (min, max), and the context except `tour`.
  * It is fitted on the training seasons' inputs only, never a result, with 5-fold out-of-fold probabilities.
  * Each other-tour match is kept with probability min(1, κ r), where r = p_own(x) / p_other(x) is the density ratio. κ is set so that half the other tour's matches are kept on average.
  * The other tour's most "own-like" matches are borrowed; the most foreign ones are left out.
* **aligned: translate before borrowing.** One model on every match, but each tour's box-score statistics are divided by that tour's own SD over the training rows: `form_*`, `formdef_*`, `iosO_*`, `iosD_*`, `prod_*`, `adjperf_tpw_2w` and `ios_points_short`, 39 inputs.
  * The reason: an ace-rate gap means more where aces are rarer, so a one-SD edge should mean the same in both tours.
  * The ratings, the price, age, workload, the surface-season pairs and the context keep their common scales.
  * Scaling a difference commutes with the swap, so the symmetrisation is unchanged.

## The composites (no new fits)

* **blend: let past seasons set the borrowing.** For each tour, a walk-forward stack of the own-tour model and the pooled model: logit q = a_T · η_split + c_T · η_pooled (+ b · `spd_L` for men).
  * The coefficients are fitted on 2019 .. Y − 1 (debut seasons out) by the same maximum likelihood as the calibration; b is shrunk as in the template.
  * a near 0 means "use the pooled model"; c near 0 means "use the own-tour model".
* **select: let past seasons pick the arm.** For each tour and season Y, the arm with the lowest both-stage log loss on that tour's scored seasons 2020 .. Y − 1. The candidates are pooled, split, borrow25, borrow50, borrowsim and aligned.

## The declared readings

* **Primary, one per question:** both stages, both tours, 2022 to 28 Jul 2026, against the current instance:
  * question 1: split;
  * question 2: notour, where + means dropping `tour` helps. The value of the input is the negative of that reading;
  * question 3: blend and select, the declared composites.
* **Flags, not verdicts:**
  * men and women separately;
  * each season 2022–2026;
  * the window 2020–2024;
  * each borrowing arm;
  * the stage-1 readings.
* **The search is stated.** 4 borrowing arms plus 2 composites. The best of them is corrected for the winner's luck: sel = s · m_K, with K = 6 and m = 1.27 ([adoption framework](../adoption_framework/README.md) § 4).

## When does the other tour's data help? (exploratory: flags only)

* **The comparison:** pooled against split, on both stages, by tour and by segment. The segments, declared now:
  * level;
  * surface;
  * best of;
  * round (early rounds against quarter-finals on);
  * season;
  * the favourite's strength (thirds of |price log-odds|, per tour);
  * missing inputs (none, 1–10, more than 10: box scores absent);
  * the surface season (either player's first match on the surface this season, or not).
* **The reading.** Paired, with block intervals; Benjamini–Hochberg across the segments. A segment that reads better or worse is a lead, never a verdict (a 13-cell table shows a cell at P ≈ 0.95 about once by chance).
* **One gated composite** may be built from these leads. If it is, it is reported as found in the scored seasons, needing confirmation outside them.

## Gates before any suggestion

* **Realisation:** the slope of the result on each model's disagreement with the calibrated close (`training_window/score.realisation`). A model that moves further than it is right gets a slope well below 1.
* **Leaks:**
  * no fit trains on a row of the predicted season or later (asserted in `common.job_data`);
  * borrowsim's classifier and aligned's SDs read the training seasons' inputs only.
* **Bet-time existence:** every arm uses the same 58 inputs as the template (or a subset). Nothing new is needed live.

## How a suggestion will be weighed ([adoption framework](../adoption_framework/README.md))

* **Structural:** training rows and models. τ is 0.1–0.3.
* **Cost:**
  * split and the borrowing arms run two models instead of one, about the same GPU time, but double the upkeep: c ≈ 0.01;
  * borrowsim also runs a classifier;
  * notour is one input fewer: c = 0.
* **Verdicts on the declared primaries only,** with B · (est − sel) against c, and the suggestion line.

## Compute

* **Fits:** seeds 0–3 × 2019–2026, one fit at a time on the shared card, started with `run_when_free.sh` (`src/eda/tour_pooling/queue.sh`).
  * A full-size fit takes 15–52 s and peaks near 8 GB. Half-size fits take roughly a third of that.
* **Order:** split, notour, borrow50, borrow25, then borrowsim and aligned once their tests pass. Roughly 1.5–2 GPU hours in all.

## The team

* **Lead (the main session):** the design, the fit runner, the synthesis and the report.
* **Statistician:** the scorer (`compare.py`'s recipe on the current instance), the composites, the realisation and the winner's-luck correction.
* **Tennis and market analyst:** the segment analysis (when borrowing helps or hurts, and why), and what borrowsim actually borrows.
* **Red team:** the runner's and the scorer's code, leaks, sealed matches, selection, and the claims.

## Changes made before the affected arms were fitted or scored

* **9 Oct 2026, borrowsim's similarity inputs** (before any borrowsim fit or any score).
  * **The problem.** The first sampler used every input except `tour`, and separated the tours perfectly: out-of-fold AUC 1.000 for 2019, found by the lead and the analyst independently. So every other-tour match got the same inclusion probability (0.5), and the arm was a random half, a copy of borrow50.
  * **Two causes:**
    * `indoor` is recorded for men only: missing on all 32,507 women's matches, so its missingness names the tour;
    * the box-score statistics are on tour-specific scales: men's gaps run about twice as wide, AUC 0.65–0.82 each.
  * **Now:** the sampler reads the match's situation in units both tours share:
    * |A − B| of the price's log-odds, the Elo and rating gaps, the surface offset, age and sets in 14 days;
    * (min, max) of the surface-season pairs;
    * surface, level, best of and round.
  * **Result:** AUC 0.88 (2022). Inclusion is now selective: about a quarter of the other tour's matches always borrowed, a quarter almost never; effective sample about 60% of the other tour's matches.
  * The first version's 2019 cache is kept in `data/studies/tour_pooling/borrow_sim/` as the record. The new one is `borrow_sim_situation/`.
* **A caveat for question 2, found by the same check.** Dropping `tour` does not make the model blind to the tour: `indoor`'s missingness and the box-score scales still identify it. notour therefore measures the value of the explicit flag, given the model can recognise the tour anyway. A tour-blind model would also need those removed, which is not a production option, so none is fitted.
  * The red team proposed two arms for the literal answer: `noindoor` and `notour_noindoor`. They are declined: neither is a production option, and the box-score scales would still name the tour.
* **9 Oct 2026, after the red team's first review** (`data/studies/tour_pooling/review/red_team_1.md`). Made after split's first score, before any fit of the arms they touch. borrow50's 29 fits already on disk keep exactly the same draws (checked).
  * **borrowsim's similarity, third version** (the analyst's finding). The surface layoff's days were fractional on about a quarter of women's 2013–18 matches: the match clock's estimated days for undated matches. So the draw partly selected on dating precision. The days are now rounded to whole days, and the cache is `borrow_sim_v3/`.
    * A cache is used only if its record names the version, today's features and the instance's frame.
    * Each borrowsim fit stores its cache's SHA-256.
  * **What borrowsim borrows, declared before its fits** (red team S1, analyst):
    * no Grand Slam match of the other tour (about 2 expected of about 6,450 per model), because best of five is men-only and best of three at a Slam women-only;
    * otherwise about 63% of the other tour's matches, tilted toward closer prices.

    So borrowsim against borrow50 mostly reads "leave out the other tour's Slams". The analyst reports it by Slam and non-Slam, and by season.
  * **Coupled draws** (red team S2):
    * borrow25's rows are a random half of borrow50's, so the dose is nested.
    * borrowsim keeps an other-tour match when u < pi, with u uniform, below 0.5 exactly on borrow50's matches and above it elsewhere. So borrowsim differs from borrow50 only where pi differs from 0.5, and their contrast isolates the selection.
  * **A size control, `sizectl`** (red team N3): one model per tour, trained on a random draw from both tours' matches, as many as its own tour has. It separates the two things a split changes:
    * pooled against sizectl: more rows at the same mix;
    * sizectl against split: the mix at the same size.
  * **A reproduction:** the pooled job (2022, seed 0) rebuilt by this runner must equal the instance's stored fit (red team N8).
  * **A control for the blend** (red team S4): the same blend with the split model replaced by pooled seeds 4–7. It shows how much of any blend gain is plain seed averaging (8 fits against the yardstick's 4).
  * **Not changed:** the blend's declared unconstrained form (red team S3). Its fitted weights already sit inside [0, 1], with the own-tour share 0.13–0.5.

## Changes after the first score

* **9 Oct 2026, two post-hoc controls** (lead, after the first blend reading; labelled "post-hoc control" in `scores.csv`; outside the select candidates and the winner's-luck family):
  * `pooled8`: the instance's seeds 0–7, equal weights;
  * `avg_split_pooled`: the even average, in log-odds, of the own-tour model and the instance.

  The reason: blend_control's weights were unidentified (seed sets 0–3 and 4–7 are near-duplicates), so plain averaging was not isolated.
* **Scoring runs.** Five full runs read 2025 to 28 Jul 2026, plus two partial ones:
  * three by the statistician, as the arms arrived;
  * an interim run once borrowsim was complete, so the report could be written while aligned fitted;
  * the final run.

  No reading changed between runs except by adding arms. select and the winner's luck were scored only in the final run, when all six candidates were complete.
