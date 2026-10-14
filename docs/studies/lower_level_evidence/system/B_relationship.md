# B: the relationship's numbers (translation, exchange rate, prior, results)

9 October 2026 · Role B (relationship estimator) of the level-evidence system · Research evidence, not a decision. The
owner decides; the lead and the red team audit at checkpoint 1.

## In short

* **Translating lower-level evidence is what matters, and doing it per match beats a constant offset** (Observed,
  2019–2024, walk-forward, mean over 19 statistics, milli-log-likelihood per unit, + = better than pooling as
  equivalent). The frozen method gains **+0.409 [+0.344, +0.474]** for men and **+0.190 [+0.152, +0.227]** for women,
  twice that for players with fewer than 10 main-tour matches in a year (+0.814, +0.399). Against role 08's constant
  offsets it is better by +0.074 (men) and +0.078 (women); against main-tour-only by +0.344 and +0.256.
* **"A Challenger match is worth 0.5–0.7 of a main-tour match" does not hold as a dose for all lower levels**
  (Observed). With the translation in place, a uniform weight of 0.5 is worse than 1 (men −0.013 [−0.022, −0.004]),
  0.75 and 1 read the same (−0.000, P(better) 0.46), and 0 is far worse (−0.327). The likelihood is flat between 0.75
  and 1.
* **For Challengers alone it holds** (Observed, season_used 2024, men, median over 19 statistics, bootstrap
  interval). A Challenger point is worth **0.63 [0.54, 0.79]** of a main-tour point, about **0.55** of a main-tour
  match. Qualifying is worth about one-for-one: tour qualifying 1.03 [0.87, 1.22], Slam qualifying 0.99 [0.73, 1.30].
  Women's WTA 125: 0.60 [0.51, 0.77]. But fitted per level and statistic, w adds only +0.006 [−0.000, +0.012] over
  w = 1 (unresolved, P 0.97): a second-order choice.
* **The opponent term explains most of the level shift; the residual δ is small** (Observed). Men's δ adds +0.027
  [+0.016, +0.038] after the Elo-gap translation; women's +0.003 (unresolved). Role A's classes neither help nor hurt
  (men −0.000, P 0.44).
* **The newcomer prior is not kept** (Observed; rule fixed at 21:17 UTC before any score). It helps men with little
  main-tour history (+0.105 [+0.009, +0.202]) but is worse overall (−0.085 [−0.108, −0.062]); women: unresolved for
  low exposure (P 0.86), worse overall (−0.068).
* **Results (Elo): w_results ≈ 1 except ITF** (Observed, raw Elo log loss of main-tour results 2019–2024). Men's ITF
  results are best at 0.25–0.5 (0.25: +1.05 [+0.47, +1.63] mLL), women's at 0.75 (+0.52 [+0.20, +0.83]); Challengers
  are flat between 0.75 and 1.25. The walk-forward choices are better for men (+0.90 [+0.29, +1.50] mLL) only when a
  down-weighted result also advances the rated-match count by w_results.
* **Frozen and delivered:** `params.parquet` (2013–2026, sha256 4c559abd…), the 2025–2026 rows produced by the frozen code and
  unread. ITF and ITFQ box scores get w = 0 until two training seasons of them exist.

## Keys

* **Labels.** *Observed* = computed here (file cited) or read in code (`path:line`). *Inferred* = my reasoning.
  *Suggestion* = a proposal for the lead or the owner.
* **Scores** are predictive log-likelihood gains in **milli per unit**: thousandths of the binomial log-likelihood per
  opportunity of the statistic (per point, game or break point; per service game for break points faced, Poisson). **+ =
  the first-named formulation predicts better.** They are statistic-level, not match-winner mLL.
* **Labels of scores** (the owner's rule of 9 Oct): "better" or "worse" when the 95% interval clears 0; otherwise
  "unresolved" with P(better) = Φ(estimate / SE). Intervals cluster by player (the target's). A statistic group's gain
  is the mean of its statistics' gains, its interval from the summed player influences.
* **Levels:** MAIN (250+ main draws; team events count as MAIN, the layer leaves them), TQ (tour qualifying), GSQ (Slam
  qualifying), CH (Challenger / WTA 125 main draws), CHQ (their qualifying), ITF, ITFQ.
* **w** is per unit of the statistic (a Challenger point against a main-tour point, at equal age). `w_per_match`
  converts it to matches with the levels' units per match.
* **Low exposure:** the target player had fewer than 10 main-tour results in the previous 365 days.
* **The holdout.** No 2025–2026 outcome was read for any estimate, choice or diagnostic. The 2025–2026 parameter rows
  were produced once, mechanically, by the frozen file (below), and their diagnostics are sealed unread.

## 1. The design

**The predictor** (`relationship.py`, `_core` and `design`; Observed). For a player's main-tour match (the target),
his statistic is predicted from his own box scores of the previous 730 days, strictly earlier in Stage 0's order, every
level, as a recency-weighted credibility average on the logit scale:

    eta = s[surface] + gamma (E_opp - E_ref)
          + [k mu + sum_main v (y - s - gamma g) + sum_L w_L sum_L v (y - s - T)] / [k + sum_main v + sum_L w_L sum_L v]

* y = logit((x + ½)/(d + 1)) per match (log for break points per game); v = d × 2^(−age/h); g = the row's opponent's
  pre-match Elo − E_ref; s = the main tour's surface offsets; k and μ the prior; T the lower row's translation.
* **The opponent term is in every formulation:** main-tour rows and the target are adjusted by role A's γ. This is the
  red team's first fix (07 S4: "no opponent term").
* **Recency** (the second fix): the half-life h is 52 weeks in F0–F5; F6 chooses it per season from {26, 52, 104, 208}
  on the fit window's own log-likelihood.
* **The prior** (the third): μ is fitted per statistic, tour and season (F0–F4), or the newcomer means of the player's
  home tier (F5).
* **Strength:** role A's checked copy of the reference's pre-match Elo (`classes/strength_elo.parquet`; it reproduces
  the frame's `in_elo_overall` to 1.4e-6 log-odds on all 67,226 matches). γ: role A's `classify.gamma(season_cutoff(Y))`,
  method A-classify-2026-10-09.2, per 100 Elo. Classes: A's final table, sha256 58e78622…
* **Every sum over a history is a sufficient statistic per target** (decayed window sums by cumulative sums,
  `TourStat.sums`), so a fit is a few-parameter L-BFGS-B problem with an analytic gradient: 21,852 dev fits in 25
  minutes on 3 workers.

**Walk-forward on the match clock** (Observed: `fit_mask`, `level_seasons`, `role08_offsets`, `strength_ref`).
* A season Y's parameters are fitted on main-tour targets of the trailing 6 seasons (from 2011) whose results were in
  by the season's cutoff (`lf + 1 ≤` the first main-tour match's `es`). The cutoffs equal role A's
  `season_cutoff` for every season 2013–2026 (`dev_checks.json`).
* Every constant a season reads (E_ref, surface offsets, role 08's offsets, the levels fitted, the newcomer means)
  comes from the same results.
* Scores: each season Y's main-tour targets, both players, predicted with season Y's parameters. 2015–2018 chose F6;
  2019–2024 is the reported period. The trailing window (6 seasons) was fixed before any score (role 03 measured δ
  drifting by era).

**The formulations** (Observed: `FORMULATIONS`).

| | Lower-level rows | Weight | Prior |
|---|---|---|---|
| F0 | pooled as equivalent: raw (surface-centred) | 1 | pool μ |
| F1 | left out | 0 | pool μ |
| F2 | minus role 08's constant same-season offset (refitted walk-forward, on this scale) | 1 | pool μ |
| F2b | minus a constant offset fitted by likelihood (no opponent gap) | 1 | pool μ |
| F3g | minus γ × the opponent gap (A's class: OPP), nothing for ENV | 1 | pool μ |
| F3 | F3g plus δ_L where A's class allows it | 1 | pool μ |
| F4 | F3, w fitted per statistic, tour and level, shrunk across statistics within the level | w | pool μ |
| F5 | F4 | w | newcomer mean of the home tier |
| F6 | the 2015–2018 choice among F3–F5, half-life chosen per season | | |
| F4nc, F5nc | every statistic translated by its own γ and δ at every level (classes ignored) | w | |

**The shrinkage across statistics** (`shrinkage`; Observed): per tour, season, half-life and level, a
DerSimonian–Laird between-statistic variance τ² and level mean w̄ from each statistic's free w and its
player-clustered sandwich SE; the shrunk fit then carries a N(w̄, τ²) prior on w. δ carries a weak N(0, 0.5²) prior
(inert unless a cell is degenerate).

**The data** (Observed, `targets_dev_key.parquet`). 2019–2024 scored targets: men 27,880 player-matches per statistic
(561 players; 12.5% low exposure), women 25,544 (586; 15.6%); 1.01 million target rows over the 19 statistics.

## 2. The formulations, walk-forward

**Mean over the 19 statistics, 2019–2024, gain over F0** (`contrasts.csv`; Observed):

| | Men, all | Men, low exposure | Women, all | Women, low exposure |
|---|---|---|---|---|
| F1 main tour only | +0.065 [−0.003, +0.132] unresolved, P 0.97 | **−0.355** [−0.628, −0.082] worse | **−0.066** [−0.113, −0.020] worse | **−0.310** [−0.495, −0.125] worse |
| F2 constant offsets | +0.335 [+0.276, +0.393] | +0.690 [+0.478, +0.901] | +0.112 [+0.078, +0.146] | +0.301 [+0.174, +0.427] |
| F3 gap + δ | +0.371 [+0.308, +0.434] | +0.761 [+0.524, +0.998] | +0.162 [+0.126, +0.198] | +0.393 [+0.249, +0.538] |
| F4 + w | +0.380 [+0.316, +0.444] | +0.773 [+0.532, +1.014] | +0.168 [+0.130, +0.205] | +0.401 [+0.256, +0.546] |
| F5 + newcomer prior | +0.295 [+0.232, +0.359] | +0.878 [+0.620, +1.136] | +0.100 [+0.059, +0.141] | +0.453 [+0.277, +0.629] |
| **The method (F4, h chosen)** | **+0.409 [+0.344, +0.474]** | **+0.814 [+0.567, +1.062]** | **+0.190 [+0.152, +0.227]** | **+0.399 [+0.251, +0.548]** |

Every F2–F5 and method cell is better (interval above 0).

**What each step adds** (paired contrasts, 2019–2024, mean over the 19 statistics):

| Contrast | Men, all | Men, low exposure | Women, all | Women, low exposure |
|---|---|---|---|---|
| F3 vs F2: per-match gap against constant offsets | +0.036 [+0.023, +0.049] better | +0.071 [+0.017, +0.125] better | +0.050 [+0.038, +0.062] better | +0.092 [+0.037, +0.147] better |
| F3 vs F2b: against offsets fitted for prediction | +0.038 [+0.025, +0.051] better | +0.104 [+0.043, +0.166] better | +0.050 [+0.038, +0.063] better | +0.128 [+0.076, +0.179] better |
| F3 vs F3g: the residual δ | +0.027 [+0.016, +0.038] better | +0.146 [+0.089, +0.203] better | +0.003, unresolved, P 0.80 | −0.020, unresolved, P 0.09 |
| F4 vs F3: the exchange rate | +0.009 [+0.002, +0.017] better | +0.012, unresolved, P 0.76 | +0.006 [+0.000, +0.011], unresolved, P 0.98 | +0.008, unresolved, P 0.80 |
| F4 vs F4free: the shrinkage | +0.002, unresolved, P 0.88 | +0.003, P 0.62 | −0.005, unresolved, P 0.07 | +0.005, P 0.65 |
| F4 vs F4nc: A's classes | −0.000, unresolved, P 0.44 | −0.013, P 0.13 | −0.003, P 0.15 | −0.009, P 0.28 |
| F5 vs F4: the newcomer prior | **−0.085 [−0.108, −0.062] worse** | **+0.105 [+0.009, +0.202] better** | **−0.068 [−0.088, −0.047] worse** | +0.052, unresolved, P 0.86 |
| The half-life chosen per season against 52 weeks (F4) | +0.029 [+0.016, +0.042] better | +0.042 [+0.002, +0.081] better | +0.022 [+0.010, +0.034] better | −0.002, unresolved, P 0.46 |
| The method vs F3 (w and h together) | +0.038 [+0.023, +0.053] better | +0.053 [+0.003, +0.103] better | +0.028 [+0.015, +0.041] better | +0.006, P 0.63 |

* **By statistic group** (men, 2019–2024, the method against F0; `contrasts.csv`): serve points +0.160, serve games
  +0.674, serve style +0.100, return +0.626, defence +0.403, total points +0.225; all better. Breaks (+1.69) and break
  points faced (+1.10, +1.24 for defence) gain most per unit; double faults conceded (`def_df`) is the one statistic a
  hair worse (−0.01).
* **Main tour only is not the answer** (Observed). For men it is unresolved overall (+0.065, P 0.97: raw return
  statistics from lower levels mislead, +0.419 for the return group), and worse for low-exposure players (−0.355).
  Translated and weighted, the lower levels beat ignoring them everywhere: the method against F1, men +0.344
  [+0.302, +0.387], low exposure +1.169 [+0.959, +1.380]; women +0.256, +0.709.
* **The selection seasons agree** (2015–2018, men, all): F3 +0.411, F4 +0.440, F5 +0.377, F4 vs F3 +0.029 [+0.018,
  +0.040], F5 vs F4 −0.064 [−0.098, −0.030]. The F6 rule picked F4 for men and F5 for women there (F5 led F4 by +0.001
  for women); the newcomer-prior rule then removed F5 (section 5).

## 3. The dose curve: is "0.5–0.7" right?

**One uniform w for every lower level and statistic, the method's half-life, gain against w = 1** (`dose_curve.csv`;
2019–2024; mean over the 19 statistics; Observed):

| Uniform w | Men, all | Men, low exposure | Women, all | Women, low exposure |
|---|---|---|---|---|
| 0 | −0.327 [−0.368, −0.286] worse | −1.174 [−1.381, −0.968] worse | −0.237 [−0.273, −0.200] worse | −0.725 [−0.858, −0.592] worse |
| 0.25 | −0.060 [−0.076, −0.044] worse | −0.127 [−0.206, −0.049] worse | −0.073 [−0.092, −0.055] worse | −0.152 [−0.226, −0.077] worse |
| **0.5** | **−0.013 [−0.022, −0.004] worse** | −0.014, unresolved, P 0.25 | **−0.019 [−0.030, −0.009] worse** | −0.014, unresolved, P 0.25 |
| 0.75 | −0.000 [−0.004, +0.004], unresolved, P 0.46 | +0.006, unresolved, P 0.75 | −0.001, unresolved, P 0.27 | +0.012, unresolved, P 0.91 |
| 1.25 | −0.006 [−0.009, −0.002] worse | −0.012, unresolved, P 0.03 | −0.007 [−0.011, −0.003] worse | −0.028 [−0.042, −0.014] worse |
| fitted per statistic and level | +0.006 [−0.000, +0.012], unresolved, P 0.97 | +0.005, P 0.62 | +0.008 [+0.003, +0.013] better | +0.014, P 0.96 |

* **The answer** (Observed, Inferred for the reading). Once lower-level evidence is translated, the predictive value is
  flat between w = 0.75 and 1 and falls off on both sides; a uniform 0.5 is worse than 1. "Worth about 0.5–0.7 of a
  main-tour match" does not hold as one number for all lower-level evidence.
* **It is close for Challengers alone, per point**, because qualifying is worth about one-for-one and dominates
  where it matters most: the matches just before a main draw (section 4).
* **The weight is a second-order choice.** Fitted per statistic and level, w adds +0.006 over w = 1 for men; the
  translation adds +0.371 over pooling. The first run's 0.5–0.8 came from an estimator with no opponent term and no
  recency (07 S4), where w absorbed the level shift and the recency of qualifying rounds.
* **The 2015–2018 seasons agree** (men: 0.5 −0.010, P 0.07; 0.75 +0.001, P 0.68; fitted +0.024 [+0.014, +0.033]
  better).

## 4. The parameters

**Men, season_used 2024** (fit window 2018–2023; `headline_men.csv`; Observed). w per unit, then δ in logit (T = γ ×
gap + δ is subtracted from the lower-level row). 95% intervals from 60 player-block bootstrap draws. "Barred": A's class
holds δ at 0 there.

| Statistic | w CH | w CHQ | w TQ | w GSQ | δ CH | δ CHQ | δ TQ | δ GSQ |
|---|---|---|---|---|---|---|---|---|
| Serve points won | 0.56 [0.41, 0.80] | 0.77 [0.34, 1.50] | 1.03 [0.87, 1.41] | 0.99 [0.67, 1.45] | −0.081 [−0.102, −0.064] | −0.032 [−0.091, +0.107] | barred | barred |
| Return points won | 0.57 [0.41, 0.79] | 0.71 [0.30, 1.46] | 1.03 [0.77, 1.30] | 0.70 [0.21, 1.13] | +0.012 [−0.007, +0.043] | barred | −0.046 [−0.093, −0.012] | +0.006 [−0.293, +0.120] |
| Total points won | 0.52 [0.42, 0.77] | 0.69 [0.32, 1.16] | 1.03 [0.84, 1.38] | 0.84 [0.48, 1.45] | barred | barred | −0.039 [−0.064, −0.015] | −0.044 [−0.125, −0.009] |
| Holds | 0.63 [0.46, 0.84] | 0.78 [0.41, 1.49] | 1.03 [0.87, 1.29] | 1.05 [0.74, 1.64] | −0.149 [−0.205, −0.101] | −0.099 [−0.296, +0.181] | barred | barred |
| Breaks | 0.69 [0.48, 0.96] | 0.95 [0.57, 1.71] | 1.02 [0.70, 1.26] | 0.87 [0.27, 1.52] | +0.015 [−0.028, +0.101] | barred | −0.169 [−0.333, −0.052] | +0.137 [−0.252, +0.400] |
| First-serve points won | 0.58 [0.43, 0.81] | 0.80 [0.41, 1.38] | 1.02 [0.83, 1.26] | 1.35 [0.95, 1.93] | −0.094 [−0.120, −0.071] | −0.110 [−0.184, −0.040] | barred | barred |
| Second-serve points won | 0.69 [0.47, 0.98] | 0.99 [0.61, 1.94] | 1.03 [0.79, 1.36] | 0.64 [0.28, 1.13] | −0.061 [−0.088, −0.038] | barred | barred | barred |
| Aces | 0.59 [0.48, 0.82] | 0.94 [0.59, 1.70] | 1.03 [0.94, 1.86] | 1.24 [0.88, 1.89] | −0.285 [−0.334, −0.240] | −0.120 [−0.316, +0.026] | barred | barred |
| Break points saved | 0.73 [0.53, 0.92] | 0.91 [0.53, 1.68] | 1.03 [0.90, 1.26] | 0.98 [0.19, 1.67] | barred | barred | barred | barred |
| Break points converted | 0.47 [0.25, 0.67] | 1.09 [0.77, 2.08] | 1.02 [0.75, 1.20] | 0.99 [0.13, 1.53] | barred | barred | −0.047 [−0.234, +0.136] | −0.029 [−0.285, +0.245] |

**By level** (`level_summary.csv`; median over the 19 statistics, its bootstrap interval; w per match):

| Level | Men, 2024 | per match | Men, 2019 | Women, 2024 | per match | Women, 2019 |
|---|---|---|---|---|---|---|
| CH | 0.63 [0.54, 0.79] | 0.55 | 0.60 [0.54, 0.72] | 0.60 [0.51, 0.77] | 0.60 | 0.79 [0.61, 1.09] |
| CHQ | 0.77 [0.50, 1.19] | 0.65 | 0.48 [0.25, 1.14] | not fitted | | not fitted |
| TQ | 1.03 [0.87, 1.22] | 0.90 | 0.90 [0.78, 1.12] | 0.92 [0.78, 1.02] | 0.90 | 0.88 [0.80, 1.03] |
| GSQ | 0.99 [0.73, 1.30] | 0.95 | 0.88 [0.65, 1.46] | 0.82 [0.71, 1.00] | 0.82 | 0.84 [0.71, 1.31] |

* **A men's Challenger point is worth about 0.6 of a main-tour point, a Challenger match about 0.55 of a main-tour
  match** (Observed). Every season since 2017 reads 0.60–0.64 per point (0.72 in 2013).
  * Qualifying is worth about one-for-one. Its rows are the most recent evidence before a main draw.
  * Challenger qualifying moved from 0.25–0.53 (2018–2020) to 0.76–0.92 (2021–2024) as its box scores filled in
    (none before 2016; few in 2019–2020).
* **The shrinkage pools strongly** (Observed). The between-statistic SD of w is 0.22 at men's CH, 0.31 at CHQ, 0 at
  TQ in 2024: the statistics' own w are mostly noise around the level's.
* **δ is the level's conditions after the opponent gap** (Observed, men's Challengers).
  * Serve statistics are over-translated by the gap alone. Serve points −0.081 is about 1.8 points per 100 at a 65%
    rate; aces −0.285.
  * Challengers are more return-friendly and slower than their opponents' Elo implies, as role 03's level effects
    found.
  * Return statistics need no δ at Challengers (+0.012, +0.015, unresolved).
* **Era stability** (`era_stability.csv`; Observed). Season_used 2019 (window 2013–2018) against 2024 (2018–2023).
  * **w is stable.** Men: 1 of 19 statistics moves at CH (|z| > 1.96), none at TQ, GSQ or CHQ. Women: none at WTA 125
    or GSQ, 1 at TQ.
  * **δ drifts.** Men's Challenger serve δ moved from −0.037 to −0.081 (serve points, z −2.9) and from −0.025 to
    −0.149 (holds, z −3.2). Women's Slam-qualifying δ moved toward 0 (serve points −0.225 → +0.004, z +4.4).
  * Hence the walk-forward refit.
  * The brief asked for windows ending 2018 and 2024. The window ending 2024 is the 2025 row's; to keep that row
    unread, the comparison uses the window ending 2023.
* **Half-life** (Observed): the fit window prefers 26 weeks in 11 of 12 seasons (52 in 2020). That is the grid's
  shortest value; shorter was not tried.
* **Early, thin seasons: the fallbacks** (Observed: `fitted_levels`, `fit_years`).
  * Seasons 2013–2016 fit on 2–5 target seasons (from 2011).
  * A level enters only with 2 seasons of 100+ box-score matches and 30 fit targets with history at it:
    * men's CHQ from season_used 2018 (box scores from 2016);
    * women's WTA 125 from 2017;
    * women's CHQ never through 2024;
    * ITF and ITFQ never.
  * An unfitted level gets w = 0, the SPEC's rule for ITF applied to every level: no evidence enters before its
    relationship is estimated.
  * Women's holds, breaks and break points faced (both sides) have no rows for 2013–2015: no women's box score of any
    level carries service-game counts before 2015 (main tour) or 2016 (lower levels), so no observation needs them.
  * No look-ahead: a season never borrows a later season's fit.

## 5. The newcomer prior: not kept

**The rule** (written to `status.log` at 21:17 UTC, before any dev score was read): keep F5 for a tour only if F5
against F4 is better for that tour's low-exposure targets on 2019–2024 and not worse overall.

**The reading** (Observed, section 2's table):
* Men: low exposure better, +0.105 [+0.009, +0.202]; overall worse, −0.085 [−0.108, −0.062]. Not kept.
* Women: low exposure unresolved, +0.052 (P 0.86); overall worse, −0.068 [−0.088, −0.047]. Not kept.
* The harm sits in the defence statistics (men −0.336 [−0.443, −0.229]) and serve games (−0.076).

**Why** (Observed in `dev_fits.parquet`; the mechanism Inferred).
* The prior as specified is the average main-tour newcomer of the player's home tier: here, the maximum-likelihood
  level of main-tour targets whose player had fewer than 5 main-tour box scores in two years, by home tier.
* Main-tour-based and Q-based newcomers are rare for men, so those tiers fall back to the pooled newcomer mean.
* That mean is far from the regression target that suits established players. Men's serve points won, season 2022:
  newcomer mean +0.381 against F4's fitted μ +0.167 (logit); holds +0.922 against +0.414. Newcomers who reach main draws
  are selected on recent success.
* So the newcomer prior moves every established player's shrink target. It helps the players it was meant for and hurts
  everyone else.
* **Tier means fitted for prediction (F5ml) do better** (men +0.023 [+0.010, +0.036], women +0.060 [+0.036, +0.085];
  low-exposure women +0.103 [+0.004, +0.202]). But they are not newcomer means: men's aces, 2022, main-tour tier −1.39
  against the newcomer mean −2.75. They act as tier-specific selection terms scaled by the prior's weight, which would
  not transfer to the builders' own shrinkage constants.
* *Suggestion* (not run, post hoc): a prior that uses the newcomer mean only for players whose home tier is below the
  main tour, and the fitted pool target for main-tour-based players. It would need its own pre-registration and fresh
  seasons.

## 6. The results channel: w_results

**The grid** (`elo_grid.csv`; Observed). The reference's Elo, K schedule copied from Stage 1 (men K = 600/(n + 2)^0.6,
women 600/(n + 1)^0.6, retirements counted). Each level's results get K × w and advance the rated-match count by w;
the other levels stay at 1. The score is the raw Elo log loss of main-tour results, 2019–2024, in mLL against all at 1;
4-week blocks.

| w_results | Men CH | Men CHQ | Men TQ | Men GSQ | Men ITF | Women CH | Women TQ | Women ITF | Women ITFQ |
|---|---|---|---|---|---|---|---|---|---|
| 0 | −4.46 [−6.31, −2.61] | −0.86 | −1.58 | −0.65 | +0.64, P 0.89 | −0.75, P 0.08 | −2.25 | **−6.76 [−8.86, −4.67]** | −0.72 |
| 0.25 | −1.84 | −0.61 | −0.93 | −0.40 | **+1.05 [+0.47, +1.63]** | −0.35, P 0.18 | −1.31 | −0.26, P 0.32 | −0.44 |
| 0.5 | −0.66 [−1.30, −0.03] | −0.39 | −0.47 | −0.22, P 0.04 | +0.80 [+0.45, +1.15] | −0.11, P 0.33 | −0.66 | +0.61, P 0.96 | −0.24 |
| 0.75 | −0.14, P 0.17 | −0.19 | −0.16, P 0.05 | −0.08, P 0.08 | +0.43 [+0.26, +0.59] | +0.00, P 0.51 | −0.23 | **+0.52 [+0.20, +0.83]** | −0.10 |
| 1.25 | −0.10, P 0.20 | +0.17 [+0.10, +0.24] | +0.04, P 0.68 | +0.04, P 0.73 | −0.46 [−0.61, −0.31] | −0.11, P 0.18 | +0.07, P 0.77 | −0.76 [−1.05, −0.47] | +0.06, P 0.89 |

Unlabelled cells: the 95% interval clears 0 (worse when negative).

* **Lower-level results are needed** (Observed). Dropping a level (w = 0) is worse everywhere except three cells:
  * men's ITF: +0.64, unresolved, P 0.89;
  * men's ITF qualifying: +0.05 [+0.04, +0.06], better;
  * women's Challenger qualifying: flat, +0.02, P 0.65.
* **Challengers count about fully** (0.75–1.25 flat). **ITF results deserve a discount:** men about 0.25–0.5, women
  about 0.75.
* **The walk-forward choice** (`elo_w_results.csv`): per season and level, the grid value best on the trailing 6
  seasons. Its 2019–2024 score against all at 1: men **+0.90 [+0.29, +1.50] mLL, better**; women +0.21 [−0.44, +0.85],
  unresolved, P 0.74 (`elo_scores.csv`).
* **The count rule matters** (Observed). With the rated-match count advancing by 1 for a down-weighted result, the same
  choices are worse for men (−1.17 [−1.67, −0.67]): a player who arrives with many discounted results has a small K and
  an under-moved rating. C1's `elo_count` "weighted" is the right rule.
* **Caveats** (Inferred). This is Elo's own log loss, a priced-in control in the model (the owner's thesis), and one
  multiplier at a time; the model-level value is role D's.

## 7. Freezing, and the 2025–2026 rows

* **The method was chosen on evidence of 2024 and earlier** (sections 2–6): F4 for both tours, w shrunk, half-life
  per season, pool prior, w_results by the grid.
* **The freeze** (`method_freeze.json`, written by `relationship.py --freeze`; Observed) records the sha256 of:
  * `relationship.py`: `06a85f00a2051a53063bdc706d06d360e80e2bd11bf2532aa2abb600df982575`, equal to every 2013–2024 row's `code_sha256`;
  * role A's `classify.py` (γ), `common.py`, `classes.csv` (58e78622…) and the strength copy (4fa9a573…);
  * the 2013–2024 rows (`params_dev.parquet`, `90d6dff1…`) and `elo_w_results.csv` (`8d824ff6…`; rerun with the frozen file, byte-identical);
  * the method (F4, B = 60 draws, half-lives 26/52/104/208 weeks).
* **The 2025 and 2026 rows** came from one run of `relationship.py --mechanical` (23:02–23:10 UTC, exit 0; 556 rows, every one with `code_sha256` 06a85f00…, checked for count and hash only):
  * it refuses unless every hash above matches (`verify_frozen`; tested);
  * it fits season 2025 on results in by 29 Dec 2024 and season 2026 on results in by 3 Jan 2026. Role A's γ for 2026
    is read with `allow_holdout`, as A's interface provides for this purpose;
  * it writes the rows, prints only their count, and leaves its bootstrap draws in `holdout_sealed/`. Nobody read them.
* **`params.parquet`** = the 2013–2024 rows + the 2025–2026 rows: 3,808 rows, sha256 `4c559abd356f7c9f0f53c958c5d8293ae55d0cdfa62c4e9da689c94c91a801fb` (`params.sha256`).
* **The SYS_NOCLASS view** `params_noclass.parquet` (sha256 4018747d…) holds the same fit with the classes ignored in the
  standard columns, for a layer config that points `params` at it (`relationship_report.noclass_view`).
* **One deviation from the brief, to keep the holdout rows unread.** The era check compares windows ending 2018 and
  2023, not 2024: the window ending 2024 is the 2025 row's (section 4).

## 8. ITF-ready

* **The rule** (Observed: `fitted_levels`, `level_seasons`). A lower level is fitted for season Y only if the trailing
  window holds at least 2 seasons with 100 or more box-score matches of it, results in by the cutoff, and 30 fit
  targets with history at the level. Otherwise w = 0 and the row says `fitted` false. It is one rule for every level;
  for ITF and ITFQ it is the SPEC's "w = 0 until two training seasons of their box scores exist".
* **In the frozen tables** ITF has 29 women's box-score matches (2022) and none for men, so ITF and ITFQ are never fitted
  (2013–2026 rows). Their results enter Elo by the grid (section 6).
* **On a P7 Stage 0** with ITF box scores from 2018, the same code fits ITF from season_used 2020 (two seasons,
  2018–2019). `test_itf_box_scores_enter_only_after_two_fit_seasons` plants exactly that.
* **To run it:** `--stage0-dir`, `--timing` and `--strength` pointing at the candidate. The strength file must cover the
  new matches: the candidate's own Stage 1, copied as role A's `classify.py --strength` does.

## 9. For the engineers

**The table** (`system/relationship/params.parquet`, sha256 in `params.sha256`). One row per (season_used, tour, stat,
level):
* seasons 2013–2026, both tours;
* the 19 base statistics of role A, plus `results`;
* levels MAIN, TQ, GSQ, CH, CHQ, ITF, ITFQ.

| Column | Meaning | Units |
|---|---|---|
| `gamma` | role A's walk-forward γ (`classify.gamma(season_cutoff(Y))`) | logit (log for the two break-points-faced statistics) per 100 Elo of the observation's opponent (`gamma_unit`) |
| `strength_ref` | E_ref: the mean pre-match Elo of main-tour opponents in the 365 days before the season's cutoff | Elo points |
| `delta` | the residual level effect after γ; 0 where A's class bars it (`delta_allowed` false) | logit (log) |
| `w` | the exchange rate per unit, shrunk across statistics within the level; 1 at MAIN; 0 where the level is not fitted (`fitted` false) | main-tour units per lower-level unit |
| `w_lo`, `w_hi`, `delta_lo`, `delta_hi` | 2.5% and 97.5% quantiles of the player-block bootstrap (`boot_draws`) | as above |
| `prior_mu`, `prior_k` | the fitted pool prior (`prior_kind` "pool": the newcomer prior is not kept) | logit vs the reference opponent, surface-centred; units |
| `translate_mode` | "gap" (OPP: T = γ·gap + δ) or "raw" (ENV: T = δ) | |
| `w_noclass`, `delta_noclass`, `gamma_noclass` | the same fit with the classes ignored (SYS_NOCLASS) | |
| `w_free`, `w_level_mean`, `w_tau2` | w before the shrinkage; the level mean and between-statistic variance it shrank toward | |
| `w_joint` | one joint-solve observation's weight: the mean of the serve statistic's and its receiving side's w | |
| `w_per_match` | w × units per match at the level ÷ units per main-tour match | main-tour matches |
| `h_weeks`, `fit_through`, `code_sha256` | the half-life the season chose; the latest result used; the file that wrote the row | |

**Rows with `stat` = `results`** carry w_results per (season_used, tour, level), from the Elo grid's walk-forward
choice.

**The translation is in the logit of the rate per opportunity, per row and per perspective.** For a lower-level
observation of statistic s by player P at level L, against opponent O:

    T = gamma_s / 100 x (E_O - strength_ref) + delta_{s,L}        (the gamma term only when translate_mode is "gap")
    translated logit = logit((x + 1/2)/(d + 1)) - T,   then weight w_{s,L}

* **`points_52w` (C1, as built):** x ← x + d·(expit(logit(r) − T) − r), r = (x + ½)/(d + 1), then x, d ← w·x, w·d.
  This is the predictor's own scale (Observed: `relationship.observation`, `design`).
* **The forms' norms (C1).** A row in opponent O's norm is a statistic produced by O's opponent P against O. As an
  observation about O, it is O's "allowed" statistic, so it should use the mirror statistic's own row:
  * `def_ace`, `def_df`, `def_first_in`, `def_bp_faced_pg` for the four style statistics;
  * `rpw_first` for `first_won`, `rpw_second` for `second_won`, `rpw` for `spw`, `brk` for `hold`, `bp_conv` for
    `bp_saved`, with the sign flipped on the logit scale.
  * C1's default `producer_gamma = −1` (γ_producer = −γ_s) assumes the statistic depends only on the strength
    difference. Role A's measured mirrors are not symmetric (Observed, `classes.csv`, men): `spw` γ −0.060 against
    `rpw` −0.076; aces −0.075 against `def_ace` +0.101.
  * *Suggestion:* read the mirror's row (γ, δ and w). It is in the table.
* **The match's own value at a lower level (forms):** `delta` only, as C1 does.
* **The season convention.** Each season's row is fitted on results in by its first main-tour match. C1 applies each
  row's own season's parameters, with a floor season for 2010–2012 rows: use 2013. The predictor applied the target
  season's parameters to a target's whole history.
  * Both are leak-free. The parameters move slowly (section 4's era table), so the difference is second order
    (Inferred).

**The joint solves (C2) need the level term in the solve's own units.**
* **The supplied δ cannot be used as it is** (Inferred, agreeing with `C_layer_ios.md` §5 and `A_classes.md` §8–9). It
  is the residual after the Elo-gap term γ·(E_O − E_ref), while the solve's opponent term is the solved rating D_O.
* **Recommended (C2's form b):** a level fixed effect estimated inside the solve, unpenalised.
  * Refit it for each season on rows in by the season's cutoff (the match clock).
  * Only at the levels A's class allows.
  * ITF and ITFQ held out until two seasons of their box scores are in the window.
  * `translation.batch_fe` (first run) is the template.
* **w in a solve:** use `w_joint`. One row informs both the server's O and the returner's D, so it needs one weight.
  * Caveat (Inferred): w was fitted in a credibility average, not in a ridge solve. Role 03's λ arms found a solve's
    best discount milder than the raw-rate one.
* **The prior:** pool (the solve's own ridge target). The newcomer prior is not kept.

**The home-tier rule** (for C1's `prior_tier_rule`, should the newcomer prior be revisited; `own_history`,
`newcomer_means`).
* **Counts:** at a match, the player's strictly earlier played matches (completed or retired, Stage 0 order) of the
  previous 365 days, every level, ITF results included, counted by tier:
  * MT: main draws and team events;
  * Q: TQ and GSQ;
  * CH: CH and CHQ;
  * ITF: ITF and ITFQ.
* **The home tier** is the largest count. Ties go to the higher tier; no match gives "none".
* **A newcomer** has fewer than 5 main-tour box scores of the statistic in the previous 730 days.

**Elo (C1).** K × w_results for a lower-level result, and the rated-match count advances by w_results (C1's
`elo_count` "weighted", the same rule as `relationship.elo_pass_w`). At w_results = 1 it is the reference's pass
exactly (Observed: `elo_checks.json`, 1.2e-4 Elo, float32 storage).

## 10. Checks and tests

* **Tests:** `test/lower_level_evidence/test_relationship.py`, 18 pass and 1 skips until the 2025–2026 rows exist; after the 2025–2026 rows: 19 pass.
  * **Planted recovery:** five synthetic worlds whose target outcomes are drawn from the predictor's own formula. Each
    returns its planted k, μ, δ, w and γ (`planted_recovery.json`: k 300–308 for 300, μ 0.298–0.307 for 0.30, δ
    0.196–0.205 for 0.20, w 0.534–0.579 for 0.55, γ −0.0599 to −0.0601 for −0.0600 per 100 Elo). Also: the newcomer
    means; γ alone in a main-only fit.
  * **The window sums** equal a brute-force loop.
  * **The walk-forward fit never reads the future.** Every result not in by the season's cutoff is replaced at
    random; the season's parameters, surface offsets and newcomer means do not move (to 1e-10).
  * **Fit targets obey the clock.** A level needs two seasons of box scores, CH and planted ITF alike.
  * **The shrinkage** pools fully when statistics agree.
  * **A class that bars δ holds it at 0.**
  * **The Elo pass** with every multiplier at 1 is Stage 1's `elo_pass`; at 0 nobody moves.
  * **The holdout:** `load` and `elo_history` refuse seasons after 2024 outside the mechanical mode, and the mechanical
    mode refuses a file whose hash differs from the freeze. The stored 2025–2026 rows carry the frozen hash.
* **One fix found by the tests** (Observed). From a single start, one of the five planted worlds stalled in a poor
  optimum (k 29 instead of 300). Cold fits now take the better of two starts.
  * On real data, before the fix, 89 of 90 sampled fits were identical from five starts; the 90th was 1.1e-6 per unit
    worse.
  * The dev comparison ran before the fix. Its readings stand to that precision (Inferred from the 90-fit check). The
    parameters were all produced after it.
* **Convergence:** 21,852 dev fits, 0 unconverged (`dev_checks.json`) ; parameters: every fit converged, every point estimate lies inside its bootstrap interval, 60 draws each (`checks_params.json`).
* **The clock:** this module's season cutoffs equal role A's `season_cutoff` for 2013–2026.
* **Strength and γ:** role A's checked strength copy; γ method A-classify-2026-10-09.2; classes sha256 58e78622…

## Files and commands

| What | Where |
|---|---|
| Code (CLI: `--steps dev,tables,elo,params`, `--freeze`, `--mechanical`; `--stage0-dir`, `--timing`, `--strength`) | `src/eda/lower_level_evidence/relationship.py` |
| Report tables (reads the outputs only) | `src/eda/lower_level_evidence/relationship_report.py` |
| Tests | `test/lower_level_evidence/test_relationship.py` |
| The parameters, their hash; the frozen record | `system/relationship/params.parquet`, `params.sha256`; `method_freeze.json`; `READY_params.txt` |
| The 2013–2024 rows; the bootstrap draws; the points behind them | `params_dev.parquet`, `bootstrap_draws.parquet`, `params_points.parquet`, `params_round1.parquet` |
| Sealed, unread: the 2025–2026 rows' own outputs | `system/relationship/holdout_sealed/` |
| Formulations: per target (key columns), every fit, the contrasts, the dose curve | `targets_dev_key.parquet`, `dev_fits.parquet`, `dev_pass1.parquet`, `formulations.csv`, `contrasts.csv`, `dose_curve.csv`, `dev_checks.json`, `dev_gamma_used.csv` |
| Results channel | `elo_grid.csv`, `elo_w_results.csv`, `elo_scores.csv`, `elo_checks.json` |
| Summaries | `level_summary.csv`, `era_stability.csv`, `headline_men.csv`, `checks_params.json`, `planted_recovery.json` |

Run from the repository root (times on the shared machine, 3 workers):

```
./python.sh src/eda/lower_level_evidence/relationship.py --steps dev --work <scratch>      # 25 min
./python.sh src/eda/lower_level_evidence/relationship.py --steps tables --work <scratch>   # 1.5 min
./python.sh src/eda/lower_level_evidence/relationship.py --steps elo                       # 1 min
./python.sh src/eda/lower_level_evidence/relationship.py --steps params --method F4 --boot 60   # 76 min on the loaded machine
./python.sh src/eda/lower_level_evidence/relationship.py --freeze --method F4 --boot 60
./python.sh src/eda/lower_level_evidence/relationship.py --mechanical                      # 2025-2026 rows, unread
./python.sh src/eda/lower_level_evidence/relationship_report.py
./python.sh -m pytest test/lower_level_evidence/test_relationship.py -q
```

## What it does not show

* **No match-level effect.** These are likelihoods of the statistics, not of the match winner. Whether the system
  helps the model is role D's question; role 08 found a constant-offset version worth +0.08 mLL for men, and the share
  control as good.
* **The predictor stands in for the builders.** It is a credibility average with an Elo-gap opponent term, not the
  one-step forms (opponents' norms), `points_52w`'s iid match model or the IOS solve. Its w and δ are the best
  statistic-level estimates of the relationship; how they act inside each builder is for the arms to show.
* **w is identified weakly.** The likelihood is flat between 0.75 and 1. The per-level w are estimates of a gently
  sloped optimum, not sharp quantities, and the bootstrap intervals say so.
* **Selection is not separated.** Main-tour targets are players who reached main draws, often after a lower-level run.
  The forecasting fit folds that into δ and w, which is right for forecasting but not a structural "information"
  measure.
* **Elo's γ is fitted inside the main tour** (role A) and extrapolated to the larger gaps of lower-level matches;
  δ catches the average misfit, not its shape.
* **The newcomer prior was tested in one form.** Its failure is the form's (the fallback tiers), not necessarily the
  idea's (section 5).
* **The half-life sits at the grid's edge.** The fits chose 26 weeks, the shortest tried, in 11 of 12 seasons. A
  shorter one might fit better and would move w, which is measured at equal age.
* **The results channel** is Elo's own log loss, one level at a time, with the reference's K.
* **The bootstrap** resamples target players (Poisson weights), not the histories, and has 60 draws: the 2.5% and
  97.5% quantiles are rough.
* **ITF:** no ITF box-score parameter exists before P7. The rule that admits them is tested only on planted data.
* **Women** are fitted with the same code; their WTA 125 and qualifying samples are thinner, and women's Challenger
  qualifying is never fitted.
