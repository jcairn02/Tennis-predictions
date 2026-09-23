> HISTORICAL LLM RESEARCH — unapproved seed material, preserved from the inherited one-shot output. Claims of verification, decisions, phases, deadlines, and exclusions below are the prior LLM's assertions, not current project policy or an approved roadmap. Paths below describe the old repository layout; start at the archive index.

# src/models/ — planned interfaces (stubs)

Implemented in the Phase 3 milestone (see docs/roadmap.md). Plan:

1. `lr_baseline.py` — logistic regression on a handful of difference features
   (blended-Elo diff, serve/return diffs, fatigue diff, rank-points diff). Walk-forward
   (expanding window) evaluation: log loss, calibration curve, and loss vs the
   devigged Pinnacle close. This is the honest yardstick every later model must beat.
2. `gbm.py` — LightGBM on the full feature frame, same walk-forward harness.
3. `autogluon_runner.py` — port the UFC v2.5 AutoGluon setup once features stabilize
   (presets, time-budget, leaderboard export). Pin autogluon in environment.yml then.
4. `calibrate.py` — out-of-fold Platt/temperature scaling fit on walk-forward
   predictions only (never on the training fold).

Evaluation contract (all models): chronological splits only, no shuffling; report
log loss / Brier / calibration slope AND market-relative metrics (CLV of hypothetical
flat bets, ROI at EV>threshold) per era-year, not pooled.
