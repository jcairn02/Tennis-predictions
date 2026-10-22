# PS10, return elasticity to server strength: the builder's memo

16 Oct 2026 · Serve/return-leads study, team member "elasticity builder" (a subagent of the lead, Claude, session `6483c720-30a3-46ff-9519-287690b6f9d8`) · Model: Claude Opus 5.5 (`claude-opus-5-5`) · Diagnostic and exploratory: nothing in production changes.

* **The brief, verbatim:** [briefs/02_elasticity_builder.md](../briefs/02_elasticity_builder.md).
* **Code:** `src/eda/serve_return_leads/elasticity.py` (new; no existing file edited).
* **Outputs:** `data/studies/serve_return_leads/elasticity/`.

This memo was written while working (the process-log rule). Sections 1–3 were written before any reading of results, section 3.4 before the points check; sections 5–7 after. The chronology (§ 8) gives the times.

**In short.**
* **Observed: the trait is real in the points, but weak.** Each returner's shrunk elasticity predicts his next match's return points by about its own size: men 2013–24 slope 1.01 (SE 0.15), unchanged with the population interaction held fixed. Its reliability is low: split-half 0.08–0.20, a median shrink factor of 0.06–0.18. It is unresolved in 2023–26 (slopes 0.54 and 0.24).
* **Observed: no reading beyond the close or the model.** All are unresolved; none reaches the bar fixed before reading.
  * Men 2013–24, beyond the close: +0.010 per RMS [−0.019, +0.039], P(β > 0) 0.76; orth +0.003, P 0.59.
  * Beyond the model, 2020–24: −0.001, P 0.48.
  * 2025–26: −0.011, P 0.35.
* **Inferred: the close carries most of it.** Calibrated in points and wholly unpriced, it would read about +0.062 in 2013–24; the observed reading is 3.5 SE below that.
* **Recommendation: do not register PS10 for the unseen check;** feature-pool verdict "not admitted" (§ 6).

## 1. Interpretation acted on

* **The question.** Does a returner gain more (or less) against big servers than the additive IOS rating predicts? Per returner j: the slope b_j of his return-point residuals (observed minus the IOS prediction) on the server's serve rating O. The matchup term at match m (A − B) is b_A·(O_B − Ō) − b_B·(O_A − Ō).
* **The sealed line.** No row of any table with a tournament date of 29 Jul 2026 or later is loaded by `elasticity.py`: the Stage 0, timing and rating reads filter inside the parquet read and then assert it. Match results (won or lost) are read only through `readings.py`.
* **Box scores as inputs.** The residual history uses the points of earlier matches (allowed by the brief). A separate points check (§ 5.1) reads the target match's own return points beyond the IOS prediction, on matches before 29 Jul 2026 only. It reads no won/lost result and is not a reading against the close; it tests whether the trait exists in the points at all.

**Readings set aside.**
* (a) Ō a single population constant. Set aside before any reading: the brief's Ō is read as the regression's centre, each returner's own weighted mean of the servers' (time-centred) O; reasons in § 2.
* (b) Shrinking toward the population mean slope instead of 0. The brief says toward 0; § 2 records the outcome-free check of the population slope that decides whether the two differ.
* (c) Several variants read against the close (half-lives, centrings). Not done: one registered construction, read once, plus the women's contrast the brief asks for.

## 2. The construction (fixed before any reading of results)

Every choice below was made before any won/lost result or any points-check number was computed; the chronology (§ 8) records what had been seen at each.

1. **The long table.** Each player's own matches at every level before 29 Jul 2026, one row per (match, player), in `screen.long_table`'s order; the `won` column is not loaded. Stage 0 (14 Oct), the match clock (14 Oct) and the ratings are read with `tournament_date < 29 Jul 2026` (or `match_id in` the sealed matches) inside the parquet read, then asserted.
2. **The ratings.** `surface_features.parquet` (the surface IOS of 6 Oct, built before the level layer): each match's pre-match `srf_O_eff_spw` (O + E_surface) and `srf_D_eff_spw` (D + F_surface) for both sides. They exist for the rating pool only: the main tour, Challengers / WTA 125 and their qualifying, 2010 on.
3. **The residual.** For returner j at an earlier match k against server i, with a box score under the IOS's own rule (completed, standard format, serve points > 0) and both ratings:
   * y_k = logit((x_k + ½)/(d_k + 1)) − μ_k, with x_k the server's serve points won (= d_k − j's return points won), d_k the points served, μ_k the tour's surface average of serve points won on the logit scale (Stage 3's 2010–18 constants, the solver's own centring);
   * **r_k = (O_i,k − D_j,k) − y_k.** Positive: j won more return points than the additive prediction.
   * Unit weight u_k = d_k (return points played; the IOS's τ = 1).
4. **The server's O, time-centred.** O~_k = O_i,k − M(es_k), M(t) = the tour's mean pre-match O_eff_spw over its main-draw tour-level matches with earliest start in [t − 364, t). Reason (outcome-free, § 8 at 14:21 and 14:28): the ITF box scores of 2025–26 lifted the rating scale (men's M 0.33 in 2024 to 0.41 in 2026; women's 0.23 to 0.39), and without centring a player's history would mix this drift into his slope.
5. **The slope.** At target match m, j's history = his residual rows with lf_k + 1 ≤ es_m (`timing.parquet`). Weighted least squares of r_k on O~_k **with an intercept** (the intercept absorbs a returner's general over- or under-performance of his D, which is a different lead), weights u_k · 2^(−(es_m − obs_k)/365 days). Outputs: b̂_j, the centre Ō_j (the weighted mean of O~ over the history), and v_j (the slope's variance per unit of s², assuming Var r_k = s²/u_k).
6. **Empirical Bayes, walk-forward.** At each 1 January S (2011–2026), per tour: every player's history released by S, split into alternate matches in his own order; each half's slope with the decay to S; players with ≥ 10 matches in each half.
   * s² (chance) = mean of (b_odd − b_even)²/(v_odd + v_even);
   * b̄ (the population slope) and τ² (the true spread between returners) = the precision-weighted mean and covariance of the halves.
   * A target reads the latest snapshot on or before its earliest start: **b*_j = λ_j (b̂_j − b̄), λ_j = τ²/(τ² + s² v_j).** τ² is floored at 0, which sets every b* of that tour-year to 0.
   * **Departure from the brief's letter ("shrink toward 0"):** the shrinkage is toward the population slope, and the elasticity is the returner's deviation from it. A slope shared by every returner is a property of the IOS link, not of a returner, and would add a multiple of the serve-rating difference (the serving trait T1, read separately) to x. Decided at 14:22, before b̄ was computed; b̄ turned out at −0.01 to −0.05 for the men (2014–26), a quarter to a half of τ.
7. **The matchup term.** term_j = b*_j (O~_opp,m − Ō_j); **x = term_A − term_B** = b_A (O_B − Ō_A) − b_B (O_A − Ō_B) on the time-centred scale. A returner without a usable history has b* = 0 (the prior). Ō is each returner's own centre, not one population constant: his D is fitted on his own opponents, so his residuals average about zero at his own opponent mix, and the slope predicts the extra residual relative to that point.
8. **Units.** x is in logits of return points. Through the read it is scaled per RMS in each window.
9. **The registered direction:** + (the brief's): the player whose returning gains more against the server he faces than the additive rating predicts beats the close.

## 3. What the points show before any result (observed, outcome-free)

### 3.1 The mapping and coverage (`check.json`)

* **Box score.** A player's return points won and played in Stage 0 equal the opponent's serve points played minus won, and played, on 569,412 of 569,412 box-score rows before 29 Jul 2026.
* **The solver's μ.** The cache's per-row centring equals the tour's surface average used here on 252,919 of 252,919 pool matches.
* **Calibration of the IOS prediction.** The observed serve-point logit y on (O_server − D_returner), weighted by points: slope 0.95–1.03 in every era from 2013 on both tours (0.82–0.91 in the 2010–12 warm-up); weighted mean residual within ±0.03. So the residual is measured on the solver's own scale, with the right sides.
* **Sides.** The 6 Oct pool's side A maps one-to-one onto today's Stage 0 ids (0 rows disagree, both tours); the frame's IOS inputs correlate 0.997–0.9996 with the pool's A − B.
* **Coverage.** Histories hold every box-score return row with ratings: 342,480 men's and 127,424 women's rows. Lost: ITF box scores (men 45,412 return rows, women 46,644; mostly 2025–26) and team events (3,644 and 3,356), which have no ratings in the pool. On the frame: x is defined on 34,289 of 34,289 men's rows (seasons 2013–26 before 29 Jul 2026, debut seasons out) and 31,993 of 32,033 women's; 33,845 men's matches have ≥ 20 history matches on both sides.

### 3.2 Reliability (`snapshots.csv`, `reliability.json`)

* **Men: weak but consistently above zero.**
  * Split-half correlation of the slopes (alternate matches), precision-weighted, at the 1 January snapshots 2013–2026: 0.08–0.20 (Spearman–Brown 0.14–0.34). Unweighted, over players with ≥ 10 matches per half: −0.08 to +0.03.
  * By volume (unweighted): ≥ 10 matches per half −0.06 to −0.02; ≥ 25: 0.05–0.09; ≥ 50: 0.03–0.08; ≥ 100 (225–556 players, median 160–190 matches per half): 0.11–0.19.
  * The true spread between returners τ = 0.08–0.13 (logits of return points per logit of server O), against the chance spread of a median player's full-history slope of 0.26–0.34. The median player's shrink factor λ: 0.06–0.18.
  * The chance variance per return point s² = 7.2–8.4 (binomial alone ≈ 4.2: overdispersion about 1.8×). Its median-based estimate agrees (6.7–8.5).
  * The population slope b̄: −0.01 to −0.05 from 2014.
* **Women: no stable trait.** Precision-weighted split-half r −0.01 to 0.14; τ² = 0 at 3 of 16 snapshots (2015, 2019, 2023), so b* = 0 throughout those seasons (2015 and 2023 frame rows all 0; 2019 98% 0). By volume (≥ 100 per half): −0.02 to +0.05.
* **The term's scale on the frame.** RMS of x for the men 0.012–0.020 logits of return points in 2013–16, 0.007–0.012 in 2017–26: uneven by a factor of about 2.5, because λ follows each year's τ². Women 0–0.017.
* **Redundancy.** R² of x on the model's 48 inputs: 0.034 (men), 0.041 (women). The largest correlations with single inputs: prod_bp_saved −0.08 (men), −0.11 (women).

### 3.3 The population question: do strong returners in general gain more against big servers?

The residual on O~, D~ and O~ × D~ (each returner's D time-centred like O), weighted by points, cluster-robust over four-week blocks (`reliability.json`, "population_interaction"):

| Men | 2013–16 | 2017–19 | 2020–22 | 2023–24 | 2025–26 |
|---|---|---|---|---|---|
| O~ × D~ coefficient (z) | +0.24 (5.4) | +0.16 (3.0) | +0.15 (2.5) | +0.08 (1.1) | +0.005 (0.07) |

* **Observed.** In the points, strong returners gained more against big servers than the additive rating predicts in 2013–22; the effect shrank to nothing by 2025–26. Women: no consistent sign (z −0.8 to +1.2).
* Also observed: the residual falls with the returner's own D in every era (z −2.6 to −7.8 for the men): high D ratings over-shoot a little on the next match's points.
* **Inferred.** A population interaction of this kind is what the model's prod_* matchup products carry. Its absence in the 2025–26 points makes a non-additive matchup an unlikely explanation for the close's 2025–26 under-rating of returners.

### 3.4 How the points check and the readings will be judged (written 14:39, before either was computed)

* **The points check (does the trait exist?).** Men, frame-level matches, 2013–24: the slope of each returner's own return residual at the target match on his term. "The trait shows in the next match's points" if the slope is > 0 with z ≥ 2; "calibrated" if its 95% interval holds 1.
* **The readings.** Registered direction + (the brief's). The windows `read` gives, raw and orth, beyond the close and beyond the model. The deciding window is the men's 2013–24, beyond the close: PS10 was never built, and these seasons did not motivate it. 2025–26 motivated it (edge anatomy's serving/returning asymmetry), so it is partly exposed and read as consistency, not proof.
* **The recommendation rule.** Recommend registering PS10 for the unseen check only if:
  * the points check passes;
  * the men's 2013–24 reading beyond the close has P(β > 0) ≥ 0.95, raw and orth;
  * and 2025–26 does not contradict it (P(β > 0) ≥ 0.5).
* **Otherwise** it is not worth the check. The check cannot resolve an effect that twelve seen seasons do not show: the study's timeline gives an SE per unit of about 0.065 on today's 416 unseen men's matches, and 0.023 by the end of 2027, against 0.016 for 2013–24. If the points check passes but the readings do not, PS10 is a real points trait that the close already prices (or that does not reach results): a pool candidate at most, not a betting lead.
* **Wording.** "Better" or "worse" only when the 95% interval clears 0; otherwise "unresolved", with P(β > 0).

### 3.5 Timing (`probe.json`, `probe_detail.csv`)

* **The probe.** `screen.timing_probe`: cuts 1 Jun 2016, 1 Mar 2019, 1 Sep 2022. Twelve columns of every match that may start on or after the cut were scrambled: the box score, both pre-match ratings, μ, the box flags and status.
* **Future rows.** 0 of 626,336, 915,844 and 1,249,296 rows that surely finished before the cut changed.
* **Own first rows** (each player's first match after the cut, his own facts scrambled). Per column:
  * the per-player values (b̂, v, Ō, the history count) changed 0 times;
  * b* changed 122, 118 and 217 times, every one at a target whose 1 January snapshot falls between the cut and its own earliest start (0 elsewhere).
* **Why b* moves there.** Its population constants pool every player's rows released by that 1 January. Each pooled row surely finished before the target could start, and the target's own match cannot be among them (lf ≥ es).
* **Verdict.** Leak-free under the timing rule. A future-only probe of the per-player values is exact.

## 4. The plan

1. Outcome-free checks: how the ratings map to the IOS prediction and to Stage 0's serve and return points; coverage.
2. Build the residuals and the walk-forward slopes; the split-half reliability and the empirical-Bayes constants (outcome-free).
3. The timing probe.
4. Freeze the values (hash), then the points check, then the readings: men, then women.
5. Report.

## 5. Results (after the freeze)

### 5.1 The points check (`points_check.csv`, `points_control.csv`)

The slope of each returner's own return-point residual at the target match on his term, frame-level matches before 29 Jul 2026, weighted by points, cluster-robust over four-week blocks. 1 = calibrated, 0 = no information.

| Men | Row slope (SE) | z | Match-level A − B slope (z) | Row slope, population interaction held fixed (z) |
|---|---|---|---|---|
| 2013–16 | 0.95 (0.20) | 4.8 | 1.14 (4.0) | 0.95 (4.8) |
| 2017–19 | 0.75 (0.40) | 1.8 | 0.73 (2.2) | 0.65 (1.6) |
| 2020–22 | 1.84 (0.36) | 5.1 | 2.53 (4.2) | 1.80 (5.0) |
| 2023–24 | 0.54 (0.51) | 1.1 | 1.23 (2.1) | 0.46 (0.9) |
| **2013–24** | **1.01 (0.15)** | **6.6** | 1.32 (6.1) | 1.01 (6.6) |
| 2025–26 | 0.24 (0.41) | 0.6 | 0.66 (1.0) | 0.27 (0.6) |

* **Women:** 2013–24 0.79 (0.27), z 3.0, match level 1.55 (z 4.5); 2025–26 1.39 (0.92), z 1.5.
* **Observed.** By the rule of § 3.4, the trait shows in the next match's points and the shrinkage is calibrated: men 2013–24 slope 1.01, 95% interval [0.71, 1.32].
* **Not the population pattern.** Holding the O~ × D~ interaction fixed leaves the slope unchanged, and the term correlates only 0.01–0.10 with that interaction.
* **By era.** Clear in 2013–16 and 2020–22; weaker in 2017–19 and 2023–24; unresolved in 2025–26 (its interval spans both 0 and 1).
* **The term is small.** Per returner, it moves the predicted share of return points by about 0.19 percentage points (RMS) in 2013–24: 0.26 in 2013–16, about 0.14 in 2017–26.

### 5.2 The readings (`readings.csv`, `readings_summary.csv`)

β per RMS of x; + = the registered direction. 95% intervals from t on G − 1, as `read`'s p. The model's forecast exists from 2020 only, so every "beyond the model" reading holds 2020 rows on.

| Men | Base | Raw β [95%] | P(β > 0) | Orth β [95%] | P(β > 0) |
|---|---|---|---|---|---|
| **2013–24** | **close** | **+0.010 [−0.019, +0.039]** | **0.76** | **+0.003 [−0.025, +0.032]** | **0.59** |
| 2020–24 | close | +0.001 [−0.044, +0.046] | 0.52 | −0.004 [−0.049, +0.041] | 0.43 |
| 2020–24 | model | −0.001 [−0.046, +0.044] | 0.48 | −0.003 [−0.048, +0.042] | 0.44 |
| 2025–26 | close | −0.011 [−0.070, +0.048] | 0.35 | −0.008 [−0.064, +0.047] | 0.38 |
| 2025–26 | model | −0.015 [−0.073, +0.044] | 0.31 | −0.006 [−0.060, +0.048] | 0.41 |

* **Men by era, beyond the close (raw; orth):** 2013–16 +0.025, P 0.83 (+0.017, 0.75); 2017–19 −0.010, 0.35 (−0.024, 0.20); 2020–22 +0.014, 0.67 (+0.009, 0.61); 2023–24 −0.017, 0.31 (−0.025, 0.22).
* **Women (the contrast):**
  * 2013–24 beyond the close: +0.015 [−0.017, +0.046], P 0.82; orth +0.005 [−0.025, +0.035], P 0.62.
  * 2020–24 beyond the model: +0.001 (P 0.52); orth −0.005 (P 0.41).
  * 2025–26 beyond the close: −0.008 (P 0.44); orth −0.022 (P 0.32).
* **Every reading is unresolved:** each 95% interval spans 0. Coverage: present on 100% of the men's rows; for the women 50–100% by window (b* = 0 in the zero-τ² seasons).
* **The compliance re-read of 2025–26** (`readings_strict_2025_26.csv`). It sets to no information the 31 men's and 30 women's matches dated 27–28 Jul 2026 that could start on or after 29 Jul: their pre-match ratings may hold box scores dated 29 Jul or later, through the solver's clock. Results:
  * men raw −0.010 (P 0.37), orth −0.007 (P 0.40);
  * beyond the model −0.013 (P 0.32), −0.005 (P 0.43);
  * women raw −0.013 (P 0.41), orth −0.028 (P 0.28).
  * No other window holds such a match.

### 5.3 What the readings could see (`implied_effect.json`, outcome-free)

* **The benchmark.** Suppose the term is calibrated in points (§ 5.1) and the close prices none of it. The iid match model (`stage2_iid.match_win`, each match's best-of, the IOS serve-point chances from the pre-match ratings) then turns it into a match log-odds shift. Men: 5.2 per unit of x, i.e. β per RMS of **+0.062 in 2013–24**, +0.050 in 2020–24 and +0.044 in 2025–26. Women: +0.040, +0.033, +0.027.
* **Observed against it.**
  * Men 2013–24 beyond the close: +0.010, 3.5 SE below +0.062 (orth 4.0 SE below).
  * Beyond the model, 2020–24: 2.3 SE below +0.050.
  * 2025–26: 1.9–2.1 SE below +0.044.
  * Women 2013–24: 1.6 SE (raw) and 2.3 SE (orth) below +0.040.
* **Inferred.** For the men, the readings rule out "the elasticity reaches results at its points size and the close prices none of it".
  * At the top of the 95% interval, at most about 63% of it is unpriced in 2013–24 (orth 52%). The point estimates are 16% (raw) and 5% (orth).
  * So either the close prices most of it, or point dominance reaches match results less than the iid model says. The iid model is a benchmark, not a measurement (§ 7).
  * In 2025–26 even the points trait is unresolved (slope 0.24), so an unpriced trait would there read nearer a quarter of +0.044.

## 6. Recommendation

**Do not register PS10 for the check on unseen matches.** By the rule fixed in § 3.4 before any reading:
* **The points check passes.** The trait is real in the 2013–24 points, and the shrinkage is calibrated.
* **The deciding reading fails.**
  * Men 2013–24, beyond the close: P(β > 0) 0.76 raw and 0.59 orth, against the bar of 0.95.
  * Beyond the model it sits at zero (P 0.48 and 0.44 in 2020–24).
  * 2025–26 leans the other way (P 0.35 and 0.38; compliance re-read 0.37 and 0.40).
* **The unseen check could not rescue it.** The study's timeline gives an SE per unit of about 0.065 on today's 416 unseen men's matches, and about 0.023 by the end of 2027. The twelve seen seasons give a point estimate of +0.010 (raw) or +0.003 (orth), with SE 0.015. A slot in the check would dilute R0's power and still could not confirm PS10.
* **What declining it forgoes.** We would not learn from PS10 if the close stopped pricing returner elasticity after July 2026. *Inferred:* little is lost. The trait's 2025–26 points signal is itself unresolved, and its population form (§ 3.3) is gone from the 2025–26 points.

**For the feature universe: recommended verdict "not admitted".** Reasons:
* a calibrated points trait whose match-level information the close carries (2013–24: 3.5 SE below the unpriced size), with nothing beyond the model (2020–24);
* a scale that depends on the season (λ follows each year's τ², a factor of about 2.5 between eras);
* for the women, no stable trait (τ² = 0 at 3 of 16 snapshots).

If the lead keeps every built, leak-free feature in the pool regardless, the card:
* definition § 2; coverage § 3.1; reliability § 3.2; timing § 3.5;
* bet-time availability: Stage 0 box scores, plus a spw surface IOS that the daily engine does not compute today;
* largest |r| with the model's inputs 0.11, R² on the 48 inputs 0.03–0.04;
* mechanism: additive serve/return models miss returners who hold up against big servers;
* cluster: the serve/return matchup, beside prod_*;
* results read: seen 2013 – 28 Jul 2026, both tours, raw and orth, close and model, here.

**For the edge-anatomy finding** (the close under-rated men's returning in 2025–26). *Inferred:* PS10 does not explain it. Its 2025–26 reading leans against it, and the 2025–26 points show no non-additive pattern: the population O~ × D~ coefficient is +0.005, and the per-returner slope 0.24 is unresolved. If that asymmetry is real, it lies in the level or memory of the additive ratings, or in luck: the leads the other builders test.

## 7. For a reviewer

**Claims mapped to their evidence.**

| Claim | Evidence |
|---|---|
| The residual is on the solver's scale, with the right sides | `check.json` (μ 252,919 of 252,919; calibration slopes 0.95–1.03; return points = opponent's serve points on 569,412 of 569,412); scratch side check (0 disagreements; § 8, 14:29) |
| The builder computes what it says | Brute-force check of 293 targets (3e-13 slopes, 3e-15 variances, exact counts; § 8, 14:32); values rebuilt in memory from the final code are identical to the frozen file (14:46) |
| Leak-free | `probe.json`, `probe_detail.csv` (§ 3.5) |
| A weak per-returner trait exists for the men | `snapshots.csv`, `reliability.json` (§ 3.2); `points_check.csv` (§ 5.1) |
| It is not the population interaction | `points_control.csv` (slope unchanged; correlation 0.01–0.10) |
| It is not a lead against the close or the model | `readings.csv`, `readings_summary.csv`, `readings_strict_2025_26.csv` (§ 5.2); `implied_effect.json` (§ 5.3) |

**Threats to validity, and where a flaw would hide.**
* **Ratings of 6 Oct.** They predate the level layer (10 Oct) and the 8 Oct corrections, while the box scores are today's. A corrected match's residual mixes the two. This adds noise; no sign is expected.
  * The pool has no ITF or team-event ratings, so the 2025–26 histories of players with many ITF matches are thinner.
* **The residual's variance model** (Var r ∝ 1/points). s² absorbs the 1.8× overdispersion on average, but long matches still count as more precise than they are. The points check's slope ≈ 1 says λ is right on average, not per player.
* **Construction choices**, all made on outcome-free scale checks before any reading: the time-centring M(t), each returner's own centre Ō_j, and the deviation from b̄ (instead of the brief's "toward 0").
  * The brief's literal formula, with one population Ō and shrinkage toward 0, was not read. It would add λ·b̄·(O~_opp − Ō) per side, a multiple of the serve-rating difference, plus a per-player constant times b*. Both are small: b* is small, and |b̄| is a quarter to a half of τ.
* **The benchmark** uses the iid match model. If real matches turn point dominance into wins less than iid, the benchmark falls, and § 5.3's "rules out" weakens accordingly. The pre-registered rule (§ 3.4) does not use the benchmark.
* **The points check reads seen matches' points.** These carry much of a result's information, though no won/lost result was read; all are before 29 Jul 2026. The points control and the benchmark were added after the points check, and the benchmark after the readings: diagnostics, not part of the rule.
* **61 seen matches** (events of 27–28 Jul 2026) could start after the seal. Their pre-match ratings may hold box scores dated 29 Jul or later through the solver's clock; the model's own IOS inputs share this. The compliance re-read (§ 5.2) changes no conclusion.
* **The decay half-life (365 days) and the snapshot minimum (10 matches per half)** were fixed, not tuned. A longer memory would raise the reliability of the per-player values and change λ. Such a variant was not read.

**What a re-design would do.**
* Put the elasticity inside the ratings: a returner-by-server-strength random slope in the IOS ridge system, rather than a second-step regression on noisy pre-match ratings.
* Measure "big server" with the statistic that defines it (aces, first-serve points won, or the radar's serve speed) rather than all serve points won.
* Weight each match by 1/(1/(d·p(1 − p)) + σ²_day), not by points.
* Add ITF and team box scores (they need ratings).
* Tune the memory on the points forecast (as the IOS constants were) before any result.

**Reviewer checklist.**
1. Every read in `elasticity.py` filters `tournament_date < 29 Jul 2026` (or `match_id in` the sealed matches) inside the parquet read and asserts it. The `won` column is never loaded, and results come only through `readings.read` (`step_read`, `step_read_strict`).
2. `values.parquet`'s SHA-256 equals `build.json`'s and this memo's; `_frozen_values()` refuses otherwise.
3. Orientation: x = term_A − term_B, aligned by `screen.at_frame` on the frame's A and B ids; the sign passed to `read` is +1.
4. § 3.4 was written before the points check (14:39:24) and the readings (14:41:43).
5. The probe's own-row changes are b* only, and only behind a later snapshot (`probe_detail.csv`).

Two checks were scratch scripts in the session's scratchpad, not in the repository. Their logic, for a re-run:
* **The side check (14:29).** For the pool matches before the seal, map the cache's player code at `pos_a`/`pos_b` to Stage 0's `player_a_id`/`player_b_id`; count codes with more than one id.
* **The brute-force check (14:30–14:32).** For 300 random main-tour targets, a direct weighted fit over the player's rows with `box_ok`, ratings and lf + 1 ≤ es, compared with `build()`.

**Reproduction** (Git Bash, from the repository root; `--build` rewrites `values.parquet`, which must reproduce the hash):

```
./python.sh src/eda/serve_return_leads/elasticity.py --check
./python.sh src/eda/serve_return_leads/elasticity.py --build
./python.sh src/eda/serve_return_leads/elasticity.py --reliability
./python.sh src/eda/serve_return_leads/elasticity.py --probe          # probe.json, then probe_detail.csv
./python.sh src/eda/serve_return_leads/elasticity.py --points
./python.sh src/eda/serve_return_leads/elasticity.py --points-control
./python.sh src/eda/serve_return_leads/elasticity.py --read
./python.sh src/eda/serve_return_leads/elasticity.py --read-strict
./python.sh src/eda/serve_return_leads/elasticity.py --implied
./python.sh src/eda/serve_return_leads/elasticity.py --summary
```

## 8. Chronology (PDT)

| When | What | Results seen |
|---|---|---|
| 16 Oct 14:12–14:19 | Read CLAUDE.md, the brief, `readings.py`, `common.py`, the study's process log, `screen.py` (`long_table`, `timing_probe`, `orthogonal_part`), `ios_time.py`, `ios_surface.py`, `surface_ios/build_features.py`, `build_cache.py`, `stageB_common.py`, the long list's PS10 row, Stage B's opponent-split finding (`docs/studies/ufc_ideas/stageB.md`: a player's strong-vs-weak gap is almost all chance, season-to-season r 0.08) | None (code and docs only) |
| 16 Oct 14:19–14:21 | Outcome-free checks on the 10 Oct frame (no result column loaded): `surface_features` covers 34,303 of 34,303 men's and 32,014 of 32,054 women's frame matches before 29 Jul 2026; its A − B first-serve-won and hold ratings correlate 0.997–0.9996 with the frame's IOS inputs (sides agree). Men's frame mean of O_eff_spw by season: 0.36 (2013), 0.37 (2016), 0.37 (2019), 0.31 (2022), 0.33 (2024), 0.39 (2025), 0.44 (2026); SD stable at 0.13–0.15. Stage 0 levels before the seal: ITF and team-event box scores (men 23,814 and 1,933) are outside the rating pool | Counts and rating levels only |
| 16 Oct 14:22–14:27 | Wrote `elasticity.py` (loader, time centring, residuals, slopes, snapshots, checks). **Decided before any value was computed:** H = 365 days; ≥ 10 matches per half for the snapshot estimates; the server's O time-centred by the tour's 52-week main-draw mean (reason: the level shift seen at 14:21); Ō = each returner's own weighted mean of O~ (the regression's centre); the empirical-Bayes prior mean = the population slope b̄ (the elasticity is the returner's deviation from it). On the brief's "shrink toward 0": when b̄ ≈ 0 the two agree; when it is not, a slope common to every returner is a property of the IOS link, not of a returner, and it would add a multiple of the serve-rating difference (the serving trait T1, read separately) to x. A departure from the brief's letter, recorded before b̄ was computed | None |
| 16 Oct 14:27–14:28 | `--check` (outcome-free; `check.json`): return points = opponent's serve points on 569,412 of 569,412 box rows; the solver's μ (cache, a per-surface constant) equals mine on 252,919 of 252,919 pool matches; IOS calibration, y on (O_srv − D_ret), weighted by points: slope 0.95–1.03 in every era from 2013 on both tours (0.82–0.91 in the 2010–12 warm-up), weighted mean residual within ±0.03; coverage of box-score return rows by the ratings: all levels but ITF (men 45,412 rows, women 46,644) and team events (3,644; 3,356), which have none; M(t) men 0.35–0.39 (2013–19), 0.29 (2021–22), 0.33 (2024), 0.36 (2025), 0.41 (2026); women 0.20–0.24 (2013–24), 0.28 (2025), 0.39 (2026). The match id's last two fields are not in side order (869,652 of 1,740,928 agree: about half) | Points and ratings only |
| 16 Oct 14:29 | Scratch check (outcome-free): the 6 Oct rating pool's side A (cache player codes) maps one-to-one onto today's Stage 0 ids: 0 of 361,402 men's and 0 of 144,436 women's rows disagree; 1 and 8 ids have two codes (identities merged since 6 Oct) | Ids only |
| 16 Oct 14:29–14:30 | `--build`, first run (outcome-free): the snapshot table (`snapshots.csv`; § 3) and the frame's coverage, scale and redundancy | Points-based reliability; no result |
| 16 Oct 14:30–14:32 | Brute-force check of 293 sampled targets against a direct weighted fit: slopes agreed to 2e-7, counts exactly, but v_j only to 0.8% (a running total across players made early sums the difference of huge totals). **Fixed** (per-player cumulative sums); re-check: slopes 3e-13, v 3e-15, counts exact | Values only |
| 16 Oct 14:33–14:34 | `--build` re-run with the fix: `values.parquet` SHA-256 `b4e447f1f4b763c1ccc9f373a845d8d0e208baf0fe4cae317ef5c074934f6d7e`; the snapshot table unchanged (it never used the running total) | Values only |
| 16 Oct 14:34–14:36 | `--probe` (`screen.timing_probe`, cuts 1 Jun 2016, 1 Mar 2019, 1 Sep 2022; 12 columns scrambled: the box score, both ratings, μ, the box flags, status): future rows changed **0** of 626,336, 915,844 and 1,249,296; own first rows changed 122 of 21,690, 118 of 17,659 and 217 of 12,777 (`probe.json`) | Values only |
| 16 Oct 14:35–14:36 | `--reliability` (outcome-free; `reliability.json`): split-half r of the slopes by volume, and the population O~ × D~ interaction in the points (§ 3) | Points only |
| 16 Oct 14:37 | Added `probe_detail` (the same scrambling, reported per column and by whether the target's empirical-Bayes snapshot falls after the cut), to test whether the own-row changes are b* reading population constants of a later snapshot rather than the target's own facts; running | — |
| 16 Oct 14:39 | Wrote § 3.4, how the points check and the readings will be judged, before either was computed | — |
| 16 Oct 14:39 | `probe_detail` (`probe_detail.csv`): b̂, v, Ō and the history count changed at **0** future rows and **0** own first rows at all three cuts; b* changed at 0 future rows, and at own first rows only where the target's snapshot falls after the cut (122 of 15,879; 118 of 10,931; 217 of 7,570), never where it falls before (0). **Read:** those b* values read population constants (s², τ², b̄) pooled from every player's rows released by a 1 January that lies between the cut and the target's earliest start; each such row surely finished before the target could start, and the target's own match can never be in it (lf ≥ es). Leak-free under the timing rule; the construction is final, and `values.parquet` (SHA-256 `b4e447f1…74934f6d7e`) is frozen from here | Values only |
| 16 Oct 14:39:24–14:40:04 | **`--points`** (`points_check.csv`): the target match's own return-point residuals (matches before 29 Jul 2026) on the frozen term; the first look at any target-match quantity. Numbers in § 5.1 | **Target-match points** (no won/lost) |
| 16 Oct 14:40:47–14:41:28 | Added and ran `--points-control` (`points_control.csv`): the same row slope with the population O~ × D~ interaction held fixed, because the per-returner slopes could carry the population pattern of § 3.3. A diagnostic added after seeing the points check, not part of § 3.4's rule | Target-match points |
| 16 Oct 14:41:43–14:42:09 | **`--read`** (`readings.csv`): `readings.read(seen_frame(tour), x, "PS10", sign=+1)`, men then women, every window, raw and orth, close and model. **The first and only read of won/lost results for PS10** (the frozen values) | **Results: seen matches, before 29 Jul 2026** |
| 16 Oct 14:42–14:44 | Added and ran `implied_effect` (`implied_effect.json`): the benchmark of § 5.3, outcome-free (pre-match ratings and the frozen term through the iid match model). Added after the readings, to state what they could see | None new |
| 16 Oct 14:44–14:45 | `--summary` (`readings_summary.csv`): t-based intervals and the benchmark beside each reading; a first version matched the 2013–24 beyond-the-model rows (2020–24 rows only) to the 2013–24 benchmark, corrected to 2020–24's | Arithmetic on the readings |
| 16 Oct 14:46 | Values rebuilt in memory from the final code: identical to the frozen file in every column | Values only |
| 16 Oct 14:47 | Outcome-free count: 31 men's and 30 women's seen frame matches (events of 27–28 Jul 2026) have an earliest start on or after 29 Jul 2026 | Counts only |
| 16 Oct 14:48:21–14:48:39 | **`--read-strict`** (`readings_strict_2025_26.csv`): the 2025–26 window re-read with those 61 matches set to no information, a compliance correction (their pre-match ratings may hold box scores dated 29 Jul or later through the solver's clock), not a variant | **Results: the 2025–26 window again** |
| 16 Oct 14:49– | Memo §§ 5–7 written | — |
