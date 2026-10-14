# Round 1, the statistics and machine-learning architect: is the design wrong, and what would be better?

12 Oct 2026 · Claude Opus 5.5, a subagent of session `6483c720-30a3-46ff-9519-287690b6f9d8` · For the lead's synthesis, not the owner's report.

* **Outcomes read: none.** Two outcome-free scripts were run (§ 6). Every edge quoted comes from a named published report.
* **Labels:** *observed*, *inferred*, *suggestion*. Gains are in mLL; **+ = the first-named model, or the change, better**. Earlier "ties" are written here as "unresolved".

## 0. In brief

* **The current model already follows the professional's advice, implicitly.** TabPFN with the close as an input learns E[y | close, x], so its departure from the close is an estimate of what the close misses, given 56 statistics.
  * *Observed:* that departure is 96% additive (tabpfn_thinking).
  * *Observed:* it is right-sized against Pinnacle, realisation 0.98–1.02 on 2020–24 (training_window, close_drift).
  * *Observed:* it is estimated far better than any explicit anchored model tried: the stack is worse by 1.15 (meta_stack); ridge, GAM and boosting on the same inputs are about 1.3 worse for men (tabpfn_thinking).
  * So, on 2020–24, putting the close in a non-linear model trained on a decade of lines is not the mistake.
* **What the implicit form lacks** (*inferred*):
  * **visibility:** which families' nudges still come true;
  * **recency by family:** no date input, no row weights;
  * **a route for weak or sparse signals:** TabPFN used 8% of the serve-speed signal as a column (+0.07). As a walk-forward nudge the same signal gained +0.41 [+0.04, +0.78] (serve_speed_tabpfn).
* **Re-architecture has a low ceiling** (§ 1.3). Re-weighting what the model already knows adds at most ½·E[w·d_f²]·(r_f − 1)² per family. That is ≲ 0.3 mLL unless a family is badly mis-sized. Most future edge must come from new information or earlier prices.
* **Recommended** (§ 4):
  * keep TabPFN as the estimator of the residual's direction;
  * add an explicit **recency layer**: dynamic, shrunk weights per family and per nudge, with a realisation monitor.
* **Testing:** admit statistics by coefficient tests on clusters. A single statistic's typical true effect (about 0.01–0.03 mLL) is far below what even five seasons resolve (about 0.2) (§ 3).

## 1. What the current design does, mechanically

### 1.1 How TabPFN treats the close

* **How it learns.** TabPFN approximates a Bayesian posterior predictive from 2013..Y−1 rows (about 60,000 for 2026).
  * It is not told that `odds_logit` is a probability: it learns the close's mapping from the rows. That is easy, since the close leads a no-odds model by about 9 mLL (close_drift).
  * It takes no offset, no row weights and no time index. Attention is by similarity of inputs, not of dates.
* **How much it trusts the close** (*observed*, § 6; 16-seed mean, uncalibrated).
  * Its raw log-odds regress on the close's with a slope of **1.14–1.19** in every season and tour, 2019–2026.
  * The decided calibration slope (0.909 men, 0.896 women, tabpfn_thinking58) brings the effective weight to about 1.06: the close's own slope (1.03 Pinnacle, 1.09–1.11 average).
  * *Inferred:* about 1/0.9 of the raw stretch is the softmax temperature 0.9 inherited from the UFC project, undone by the calibration.
  * Given the model, the close needs no extra weight: −0.02 [−0.13, +0.10] (meta_stack E2).
* **The model's own view grows with its context** (*observed*). σ⊥ is the SD of the raw log-odds' part not linear in the close:

  | | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to 28 Jul) |
  |---|---|---|---|---|---|---|---|---|
  | Men, σ⊥ | 0.094 | 0.107 | 0.118 | 0.121 | 0.118 | 0.125 | 0.129 | 0.137 |
  | Women, σ⊥ | 0.086 | 0.091 | 0.099 | 0.108 | 0.111 | 0.115 | 0.113 | 0.119 |

  * The training context grew from 28k to 60k rows over the same seasons, and smaller random draws move less (training_window).
  * Seed noise left in the 16-seed mean is 0.0045 log-odds, worth about 0.002 mLL: immaterial.

### 1.2 Can it represent "the close plus a small residual"? How do eras enter?

* **In function, yes.** The adjustment is 65% linear, 96% additive and 2% interaction (tabpfn_thinking, men).
* **Its advantage is estimation.** TabPFN's own linear part gains +0.94. Linear and ridge fits on the same rows recover +0.09 to +0.65.
  * The estimation tax, tr(J⁻¹K)/(2n) ≈ k/(2n), is about 0.6 mLL for 47 coefficients on 40,000 rows, against an edge of about 1.5.
  * TabPFN's prior is the better shrinkage.
* **Era changes enter only two ways:**
  * through the pooled rows: a 2025 forecast weighs 2014 like 2024;
  * through the walk-forward calibration slope, which tracked the women's drift from 0.964 to 0.912 (surface_ios).
* **So a market change is followed slowly.** If the market began to price a family in 2023, post-change rows are about a quarter of the 2026 context.
* **Weak or new signals present in a minority of rows look like noise.** Speed was in about 24% of the training rows; 8% of its signal was captured.

### 1.3 The identity that bounds every design

Notation: ĉ is the recalibrated close's log-odds, η the model's, d = η − ĉ, w = p(1 − p).

To second order, **G = LL(close) − LL(model) ≈ ½·E[w·d²]·(2r − 1)**, where r = E[(y − p)·d] / E[w·d²] is the realisation. Scaling d by k gives ½·E[w·d²]·(2kr − k²), largest at k = r.

* **Re-sizing is worth ½·E[w·d²]·(r − 1)²:** 0.06 mLL on 2020–24 (training_window: 1.44 actual, 1.50 at the best size).
* **The informative spread σ_d·r is invariant:** 0.163 for the expanding window, 0.161 for the last 5 seasons, 0.148 for the last 3, 0.162 for decay4. Shorter windows add moves, not information.
* **The noise of a comparison.** Calibrated on the observed edge, E[w·d²] ≈ 0.0019, so a match's log-loss difference against the close has an SD of about 45 mLL (§ 3).
* **What the growing spread predicts for 2025–26** (*inferred*, rough).
  * Scaling the men's 2020–24 edge (+1.28, pinnacle_first) by σ⊥² predicts about +1.5 for 2025 and +1.7 for 2026.
  * Published: +2.31 [+0.20, +4.41] and +3.57 [+0.78, +6.35]. Pooled, the excess is about +1.3 at z ≈ 1.5: unresolved, P ≈ 0.93.
  * A learning curve plus luck explains the recent edge. Under-reaction (r ≈ 1.3–1.6 in 2025–26) would also fit. The lead's C2 tells them apart.

### 1.4 Where the owner's worry is answered

| Worry | Status | Evidence |
|---|---|---|
| A non-linear model mis-weights the close | **Answered, 2020–24** | Effective weight equals the close's own; extra weight on the close ≈ 0; the stack (−1.15) and anchored linear models are worse |
| A decade-long window teaches stale trust | **Answered, 2020–24, as one global scale** | r ≈ 1.0 against Pinnacle with no trend (p = 0.64); recent windows over-react; recency at a fixed size −0.02 to −0.14, unresolved |
| Stale *directions*: which statistics the recent close misses | **Open** | Families pooled over 2013..Y−1. The form family's lead against the close appeared only from 2020 (feature_provenance): the kind of shift a pooled model follows slowly |
| 2025–26 | **Open** | No realisation or family read yet. 2026 is fed BetOnline's line (94% of rows, § 6), not the Pinnacle closes it trained on |
| Weak or sparse signals | **Answered against the incumbent** | Speed: column +0.07, nudge +0.41 |

## 2. The design space, ranked

Expected effects are judgments for 2025–26 against the close, relative to the current model (+ = the alternative better).

| # | Design | Expected effect | Cost and risk | Evidence |
|---|---|---|---|---|
| 1 | **Nudge layer** for signals TabPFN under-uses: stage 2 generalised, hierarchical shrinkage by family, dynamic | Speed is already in (+0.31 to +0.41, men 2024–26). Each further family 0 to +0.5. Candidate: arrivals from lower levels (the close under-rates them, β +0.13 [+0.07, +0.19]; as an input or term +0.06/+0.08, unresolved) | CPU; low risk (shrunk to 0) | serve_speed_tabpfn, event_levels |
| 2 | **Family realisation layer:** decompose d by family; give each a dynamic weight k_f,t ≈ 1 | 0 to +0.3 (the § 1.3 bound). Mainly protection against decay, and visibility | CPU, plus 20 fits (2014–18); risk of over-reaction if the process noise is large | training_window: no drift in r; meta_stack: weights mean-revert |
| 3 | **TabPFN on the residual:** `TabPFNRegressor` (installed, tabpfn 9.1.0) on y − p̂_close, symmetrised; or inputs orthogonalised on the close | −0.5 to +0.5, centre about −0.1 (it may over-shrink at R² ≈ 0.003) | 64 fits, about 1 GPU hour | Untested |
| 4 | **Condition on the market's own uncertainty:** both books' prices, their dispersion, the open→close move, as inputs or scale terms; at the least, an anchor slope per source | 0 to +0.3 | About 32 fits; live, both books must be recorded | bet_timing: the average as a training input +0.34 to +0.42 |
| 5 | **Season index as a TabPFN input** | −0.3 to +0.2 | 32 fits; risk of over-reaction | training_window: decay4 −0.06, last3 −0.38 |
| 6 | **Two-part or context recalibration** | 0 to +0.1. +0.2 to +0.5 only if 2025–26 has r ≈ 1.5, and a walk-forward fit lags | Trivial | Two-part −0.07 [−0.32, +0.17], unresolved; context slopes +0.12 to +0.31 alone (market_anchoring); pair_strength: ten forms, all unresolved |
| 7 | **An anchored GLM or GAM replacing TabPFN** | Men −1.3 to −0.5; women about 0 | Loses the estimator | tabpfn_thinking: ridge +0.19/+0.65 and GAM +0.21, against TabPFN's +1.57 |
| 8 | **Residual boosting** from the close's base margin | As a replacement −1.0 to −0.3; in a blend 0 to +0.2 | sklearn 1.9.1's `GradientBoostingClassifier(init=…)` can start from the recalibrated close now (`HistGradientBoosting` cannot). LightGBM or XGBoost would need a separate environment, the owner's call | Boosting with the odds as a feature: +0.30 men, −0.55 women |
| 9 | **Line-move model** (logit close − logit open) | 0 at the close, by construction | Data on disk: `bet_timing/frame.parquet` (BetOnline 2018–26), `odds_sources/sources.parquet` | BetOnline moves 1% toward the model; Polymarket 29–45% at 24–48 h (bet_timing) |
| — | **Rejected:** meta-stack (−1.15); recent-only windows (−0.09 to −0.38) | | | |

**Notes on the ranking.**
* #1 and #2 make up § 4. #1 has the one positive precedent; #2 answers "the most recent close" directly.
* #3 is the one new TabPFN variant worth a pre-registered test on 2020–24 (the structural kind, resolution about ±0.3).
* #4's anchor slope per source matters for diagnosing 2026.
* #9 belongs to early venues, and to the practitioner.

## 3. Testing "not priced by the most recent close"

### 3.1 The estimands

For a standardised, antisymmetric candidate z:
* **Beyond the close** (the diagnosis): β_C in logit P = a_τ·c + β_C·z.
* **Beyond the model** (admission): β_M in logit P = s·η_final + β_M·z.
* **The most recent close:** β at the end of the development seasons, discounted or filtered (§ 4). The pooled decade's β is not it.

Reuse `src/eda/feature_interactions/screen.py`, and add the era split. It already has:
* free slopes per tour × season on η, plus a cubic;
* sandwich SEs over four-week blocks and players;
* the discovery and replication z combined;
* weighted Holm and BH;
* placebos.

### 3.2 Power

* **Observed:** about **2,300–2,700 main-tour matches per tour per season** in the instance (2021–2025), not the brief's 4,000–4,500. Both tours give about 5,100 a year, and w̄ = 0.205.
* **A nudge.** A coefficient of β per SD is worth G ≈ 100·β² mLL.
  * The coefficient test needs **n ≈ 3,900/G** matches for 80% power (two-sided 5%).
  * A log-loss test of the same nudge needs 4× as many, since its t is half as large.
  * A TabPFN column needs more again, because capture is below 1.

| Window (matches) | Whole-model edge: 95% half-width / 80% MDE | Nudge, coefficient test: MDE (G) | Nudge, log-loss test: MDE (G) | SE of r |
|---|---|---|---|---|
| One tour-season (2,600) | ±1.7 / 2.5 | 1.5 | 6.0 | 0.45 |
| Both tours, rolling 12 months (5,100) | ±1.2 / 1.8 | 0.77 | 3.1 | 0.3 |
| H-exposed (8,593) | ±0.95 / 1.4 | 0.45 | 1.8 | 0.25 |
| 2020–2024 (22,265) | ±0.6 / 0.85 | 0.18 | 0.7 | 0.15 |

* **The whole edge.** A rolling 12 months confirms an edge of the 2020–24 size (+1.46) about 65% of the time; men alone, about 50%.
* **Single statistics are invisible.** The project's prior: true single-input effects at the close spread about 0.012 mLL around −0.028 (review_statistics, finding 3).
  * So test clusters top-down (framework § 11; hierarchical testing), and confirm bundles, not members.
  * A cluster of about 10 related statistics might reach 0.2–0.5.
* **A cheaper screening target.** A match's points-won share carries **1.4–1.8×** the result's information about a point-level strength shift (simulated, § 6). A screen on the share's residual against the close's implied share needs about 40% fewer matches. Signals that act through big points escape it, so confirm on the result.

### 3.3 Windows, monitoring, decay, exposure

* **Windows:**
  * constants: ≤ 2018;
  * discovery: 2014–21;
  * replication: 2022–24, as a joint z;
  * the "recent" estimate: discounted to end-2024;
  * H-exposed: rehearsal only. It has been read about 20 times, and the lead's scan reads it again: log the look;
  * confirmation: sealed matches from 29 Jul 2026, one look per round;
  * optional era checks: men's 2018 and the 2005–12 backcast.
* **Monitoring:**
  * season-end looks with O'Brien–Fleming spending, costing a few percent more matches;
  * for harm, a one-sided CUSUM on u_i = (y_i − q_i)·d_i, whose mean (r − 1)·E[w·d²] turns negative under over-reaction;
  * for continuous looks, anytime-valid confidence sequences for score differences (Choe & Ramdas; Henzi & Ziegel; cited from memory). They are about 1.3–1.6× wider.
* **Decay:**
  * The whole model's r falling to 0 shows within a season (z ≈ 3); a fall to 0.5 takes 2–3 seasons.
  * A family with σ_f ≈ 0.05 has an SE of 0.6–0.8 per season, so its full decay takes 2.5–4 seasons to see. Monitor clusters, not statistics.
* **Exposure:**
  * a ledger per candidate, near-copies included (`feature_universe/menu.csv` flags 367 of 606 columns as already related to 2025–26 results);
  * Tweedie or s·m_K corrections for the winner;
  * known-null placebos;
  * a family whose value appears only in 2020+ (form, age) is a lead until sealed matches confirm it.

## 4. Recommended architecture: anchor, residual learner, recency layer, monitor

**A. Anchor.** The close's log-odds, with its slope per tour and **per source** (Pinnacle, BetOnline, average), walk-forward on 2019..Y−1. BetOnline's archived closes cover 2018–2026, so its slope can be fitted beyond the matches where it was the input.

**B. Residual learner (unchanged).** TabPFN on (c, 56 inputs), 2013..Y−1, 16 seeds, the decided calibration. Add 2014–18 forecasts of the current instance (20 fits) so that C and D can be tuned before 2019.

**C. Decomposition (no outcomes).** For each season, fit an additive surrogate (one ridge spline per input) to d = s·η − ĉ.
* This is distillation: the target is TabPFN's output, not y, and R² ≈ 0.95 is expected.
* Grouped by the process log's family table, it gives d = Σ_f d_f + d_rest.

**D. Recency layer.** Monthly steps:

  logit q_i = â·c_i + Σ_f k_f,t·d_f,i + k_rest,t·d_rest,i + Σ_j b_j,t·z_j,i

* **The states:** θ_t = θ_t−1 + ω_t, with ω ~ N(0, diag(q)).
* **The priors:** k_f,0 = 1, and b_j,0 = 0 under a hierarchical prior by family.
* **The fit:** a dynamic GLM (Laplace or extended Kalman update, about 100 lines of numpy and scipy). Each month is forecast from θ_t|t−1, so the layer is strictly walk-forward.
* **The process noise q:** fitted by one-step-ahead likelihood on 2014–2022, with a memory floor of about two seasons.
* **A simpler twin:** walk-forward weighted fits with weights 0.5^(age/h), h ∈ {2, 4, 8, ∞} seasons (the tuning kind: ties go to ∞, today's rule).
* **Speed** is b_speed. Today's stage 2 is the static special case.

**E. Monitor.** Each month:
* each k_f,t with its band;
* the whole-model r and its CUSUM;
* alarms: k_f < 0.5 with P > 0.9, and r < 0.8 in two consecutive seasons.

That table is the owner's "what the recent close misses".

**Admitting a statistic.**
1. Gates from framework § 11: a mechanism (who misprices it), bet-time existence, the leak probe, a stable definition, not a near-copy, a cluster.
2. β_M and β_C on unexposed seasons with the screen harness: BH q ≤ 0.10 for the bundle, clean placebos.
3. The discounted estimate at end-2024 above 0 with P ≥ 0.9, and no negative era trend.
4. It enters D as a shrunk, dynamic b_j, never directly into TabPFN.
5. Its cluster is confirmed as a bundle on sealed matches. A proven family can be offered to TabPFN at the next selection round.

**Comparing it with the current model.**
* **The kind:** structural. The comparison decides, together with the realisation gate.
* **The scoring:** the layer runs per seed on the same stored fits, scored with `compare.py`'s recipe (`walk_forward`, `close_forecast`, `paired`, the seed term paired). That needs the `--base` or `--layer` adaptation the framework lists, or a fork of `indoor_fill/score.py`.
* **The primary:** both stages, both tours, 2020–24, read with `adoption_read.py --kind structural`. H-exposed is reported as exposed.
* **What it can see:** moving forecasts by σ_Δ ≈ 0.03, the layer reads at SE ≈ 0.09 (±0.18), against a plausible effect on 2020–24 of 0 to +0.2. So the prospective reading decides.

**Abandon it if:**
* on 2020–24 it is worse by more than 0.10 with the interval below 0, or its own moves realise below 0.8;
* q ≈ 0 for every family on 2014–22 and it reads within ±0.05 of the static rule. Then keep only the monitor. My prior is about 60% for this, since meta_stack's weights mean-revert;
* the first season-end look on sealed matches crosses the harm boundary.

Drop arm #3 if it is worse beyond its resolution.

**Stop architecture work altogether if** every family's k_f is about 1 in every era, 2025–26 included, and r ≈ 1. The model is then information-limited: spend the effort on new data and on early prices, where its edge is +2 to +5 (bet_timing).

## 5. What the lead's numbers settle

* **C2, the 2025–26 realisation.** About 1 means learning curve plus luck (§ 1.3). About 1.3–1.6 means under-reaction, which D's dynamic scale would address.
* **C2/C4, family realisations by era.** These are the empirical k_f,t. A family below 0.5 in 2023–26 is decay.
* **C3, split by odds source.** A 2026 gain concentrated in BetOnline-fed matches means the anchor needs a slope per source. The edge is then partly Pinnacle's information that BetOnline's line lacks: bettable at BetOnline, but not an edge against the sharpest close.
* **Optional:** arms of the close plus one family (about 2 GPU hours) test a transparent alternative to C. Combine their disagreements walk-forward; if that matches the full model within ±0.3, the per-family design comes free.

## 6. How this memo was made

* **Read:**
  * CLAUDE.md, the brief, the lead's process log, the studies index;
  * the reports of training_window, close_drift, meta_stack, market_anchoring, tabpfn_thinking, pinnacle_first, feature_provenance, clean_holdout_rebuild and the adoption framework with its statistics review;
  * parts of serve_speed_tabpfn, bet_timing, lean_review and feature_interactions;
  * the code of `compare.py`, `model_rebuild/fits.py`, the TabPFN runtime and its inference config, `forecasts.py` and `screen.py`.
* **Ran:**
  * `data/studies/edge_anatomy/team/architect/descriptives.py` → `descriptives.txt`. It reads prices, inputs and stored forecasts for 2019 – 28 Jul 2026, never `a_won`.
  * `point_share_information.py` → `point_share_information.txt`. An iid point-model simulation that reads no data.
* **Limits:**
  * § 1.3 is a second-order identity.
  * The power figures assume independent matches; clustering widens them by about 10–20%.
  * σ⊥ stands in for the calibrated disagreement.
  * § 2's effects are judgments.
  * The literature in § 3.3 is unchecked.
