# Pre-registration: residual screen of women's pressure pace

Written by the main session on 6 Oct 2026, after the tempo trait gate (`tempo_prereg.md`, `tempo_results.json`) and before any outcome was read for this screen. Its SHA-256 is recorded in `pace_screen_prereg.sha256` before the script runs; `src/eda/point_sequence/pace_screen.py` refuses to run if this file changes.

## Why

In the trait gate, women's pressure pace passed: real minus shuffled split-half reliability +0.750 [+0.683, +0.809]. The post-hoc checks there show it is a score-state tempo signature (game points and late non-pressure points show the same), not a pressure reaction. The auditor's plan (`debate/10_audit_scoped.md`, item B) sends a passing tempo statistic to a residual screen against the model, discovery 2020–21, replication 2022–24.

## Population

* Women's model-frame matches (`data/studies/surface_rating_race/model/model_frame.parquet`, main tour with closing odds).
* Both players must have a pre-match pressure pace:
  * at least 5 earlier logged matches (WTA umpire log, the tempo gate's population) in the 364 days before the match's best-estimate day (`obs`), or at earlier rounds of the same event;
  * the same history rule as `tempo_run.py`'s R² step.
* Windows by `obs`:
  * discovery: 1 Jan 2020 – 31 Dec 2021;
  * replication: 1 Jan 2022 – 31 Dec 2024.
* 2025–2026 is not read.

## Statistic

* **Feature.** Each player's pre-match pressure pace is the weighted mean X_P / D_P of the primary world (`tempo_player_matches.parquet`, world `primary|real`) over that history: the pressure-point gap minus the normal gap, in seconds.
* **Input.** x = (pace_A − pace_B), divided by its standard deviation in the discovery window.
* **Benchmarks.** The 54-input model's walk-forward forecast and the closing price, each recalibrated season by season with one slope per tour fitted on earlier seasons only. These are `diag_edge_split.prequential` on `meta_stack/walkforward.parquet`, as in `med_residual_screen.py`.
* **Fit.** β in logistic(a_won) = offset(logit benchmark) + β·x, no intercept.
  * Wald 95% interval; a four-week-block bootstrap as a check.
  * Positive β = the player who slows down more on pressure points (relative to her normal pace) wins more often than the benchmark says.
* **Gain.** The implied gain in mLL on the matches with the feature is the log loss of the benchmark minus that of the benchmark plus β·x. β is fitted on discovery only and applied to replication (positive = feature better).

## Pass rule

* Against the model: the discovery interval excludes 0, and the replication β has the same sign with its interval excluding 0.
* The market benchmark is reported, not gated.
* No direction is fixed in advance (two-sided).

## Secondary (reported, not gated)

* **Tempo level**, the pre-match mean own-serve gap, by the same procedure. It failed the new-information bar in the gate (R² with the 58 inputs 0.12–0.14).
* **The spec-literal world** (`spec|real`).

## What a result means

* **A null closes** women's tempo signatures as pre-match statistics. Point clocks for men (TDI's capture) are then not worth pursuing for this purpose.
* **A pass** is a point-derived statistic that the model's inputs and the close lack. It would justify men's point clocks and one pre-registered TabPFN arm (≤ 2024), decided by the owner.
