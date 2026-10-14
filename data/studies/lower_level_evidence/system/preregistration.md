# Pre-registration: the level-evidence system (men first)

Written 9 October 2026, 20:01 UTC, by the lead, before any parameter of this run was fitted, any arm built or any score
read. Its SHA-256 is in `preregistration.sha256`. Later additions are separate dated files with their own hashes; this
text never changes. The team's specification is `docs/studies/lower_level_evidence/system/SPEC.md`.

## The hypothesis

**The relationship.** Lower-level evidence (TQ, GSQ, CH, CHQ) informs the main-tour model best when each observation
goes through three steps:
1. **It is translated into main-tour terms:** T = γ · (the opponent's strength gap to the main-tour reference) + δ_L.
   * γ is the statistic's opponent dependence, measured inside the main tour.
   * δ_L is used only where the statistic's class allows it.
2. **It is counted at an exchange rate w.**
3. **It updates a player who starts from the newcomer prior of his tier,** if the statistic-level evidence keeps that
   prior.

All three are fitted walk-forward and applied the same way in every input family.

**Not in the model for now.** ITF and ITFQ box scores get w = 0 in every box-score family until training-period
parameters exist (P7).

**The primary claim:** SYS beats the frozen reference of 8 Oct 2026 for men, on both stages.

## The arms

The layer applies to men only unless stated.

| Arm | Definition |
|---|---|
| REF | `data/studies/current_best_model/reference_2026-10-08/frozen/instance` |
| SYS | translate on; w fitted per statistic, tour and level; w_results fitted; prior as role B's frozen method says; ITF box scores excluded |
| SYS_w0 | SYS with w = 0 |
| SYS_w50 | SYS with w = 0.5 |
| SYS_w100 | SYS with w = 1 |
| SEP_ALL | no translation; w = 0 and w_results = 0 for every lower-level observation; prior pool |
| SYS_NOCLASS | SYS with the classes ignored |
| SYS_S2 | SYS plus `in_box_low_share_h2w_diff` and `in_box_low_share_365d_diff` (R_S2's two columns) |
| R_S2 | `data/studies/lower_level_evidence/candidates/R_S2` |
| SYS_PLACEBO | SYS's per-match change vector (every changed input together), permuted across matches within tour × season, seed 20261009 |
| SYS_BOTH | SYS on both tours, with women's parameters |
| REF_noITF | the reference with ITF and ITFQ box scores at w = 0 in every box-score family; nothing else changed |
| Optional | SYS_w25, SYS_w75, fitted last if time allows |

**SYS's internals are fixed by a dated addition at checkpoint 1,** before any SYS-family arm is built. The addition
records:
* the hashes of the classes;
* the parameters;
* the estimator's code;
* the layer's code.

## Scoring

* **The tool:** `src/eda/current_best_model/compare.py` on each arm (both stages: the per-tour calibration slopes and
  stage 2's b̃, refitted walk-forward on 2019 .. Y − 1); seeds 0–3.
* **The unit:** mLL per match. + means the first-named model is better.
* **Intervals:** four-week blocks plus the paired seed variance.
* **The labels:** "better" or "worse" when the 95% interval clears 0; otherwise "unresolved" with P(better) = Φ(est/SE).

## Dev: 2020–2024 (fits 2019–2024)

**The selection rule.**
1. **SYS is selected**, unless a challenger beats SYS for men with P(better than SYS) ≥ 0.90.
   * The challengers: SYS_w0, SYS_w50, SYS_w100, SEP_ALL, SYS_NOCLASS, SYS_S2 and R_S2.
   * The qualifying challenger with the largest point gain over SYS is then selected.
2. **REF is selected (no change)** if the arm selected under step 1 has P(better than REF) < 0.50 for men on dev.
3. **Women:** no selection.

## The holdout: 2025–2026

* **Fits:** every arm is fitted on seasons 2025 and 2026, seeds 0–3.
* **When it opens:** once, after three things:
  1. the dev readings and the selection are written down;
  2. the red team's checkpoint 2 passes;
  3. the lead writes `holdout_unlock.json` holding this file's hash.

**The primary:** SELECTED against REF, men, both stages, 2025–2026.

**The decomposition** (both tours):
* SELECTED against REF_noITF;
* REF_noITF against REF.

**Secondary, read with no separate decision:**
* every arm against REF;
* the dose curve (SYS_w0, SYS_w50, SYS, SYS_w100);
* SYS against SYS_NOCLASS, SYS_PLACEBO and R_S2; SYS_S2 against SYS;
* SYS_BOTH, women;
* the strata:
  * the less-exposed side has fewer than 10 main-tour results in 365 days;
  * the 365-day box-score share gap is 0.5 or more;
  * falsification: both sides have 20+ main-tour results and both shares are under 0.10;
* each season;
* 2020–2026 pooled, for the primary and the dose curve.

## The recommendation (guiding; the owner decides)

* **Recommend SELECTED for men** in either case:
  * the holdout primary is better;
  * or it is unresolved with P(better) ≥ 0.80, and the pooled 2020–2026 primary is better, and no secondary is worse.
* **Holdout primary worse:** recommend REF.
* **Otherwise:** report it as unresolved, with P(better).
