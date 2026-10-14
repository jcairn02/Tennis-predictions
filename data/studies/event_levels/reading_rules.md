# Reading rules — event-levels study

Written 8 Oct 2026, while experiment A's fits ran and before any experiment score was computed (`score.py` had not
been written). The descriptive part (`blend.py`) had already been run; its Elo diagnostics read results of 2013–2024.

## Units and intervals

* Milli-log-loss per match (mLL). **+ = the named arm (second) is better** than the base (first).
* 95% intervals over four-week blocks plus the seeds' variance (training_window's `paired`). An interval spanning 0
  is a **tie**.
* Seasons 2020–2024 for experiment A, 2022–2024 for B; debut-season matches out (the decided rule). Nothing from
  2025–2026 is read.

## Experiment A: segmenting the current model by level

For each target level L (GS, 1000s, 500s, 250s), scored on L's matches only:

1. **Primary:** `own_L`, `w25_L`, `w50_L` against the current model (`exp`, both stages as decided: one stage 2 fitted
   on every level). A segmented or down-weighted version is called **better than pooling** only if
   (a) it beats `exp` with an interval above 0, **and**
   (b) it also beats `exp_L` (the current model with its stage 2 fitted on L's matches only), so the gain is not just a
   per-level recalibration.
2. **If only `exp_L` beats `exp`**, the reading is: keep pooled training, recalibrate per level.
3. **Size control:** `own_L` against `size_L` (same number of rows, drawn from every level). + = L's own rows are
   worth more than the same number of mixed rows (level purity helps); − = mixed rows are worth more.
4. **Is a level useful?** `drop_L` against the current model:
   * on the **other levels' matches** (both with stage 2 fitted on those matches): − = L's rows help the other levels
     (useful); + = L's rows hurt them; tie = no detectable effect.
   * on **L's own matches** (both with stage 2 fitted on L's matches): − = L's own rows matter for L; tie = the other
     levels carry what L needs.
5. **Multiplicity.** About 30 primary intervals. One or two isolated intervals excluding 0 are expected by chance; a
   reading needs either a consistent pattern across levels (the dose: own < w25 < w50 < pool or its reverse) or a
   result that survives in both 2020–21 and 2022–24.

6. **Exploratory, added after part 1 was read (the realisation by level: Slams 1.54, 1000s 0.84, 500s 0.79, 250s
   1.16), before it was computed:** `exp_2pL`, the current model's forecasts re-sized per level without refitting:
   logit q = a_tour logit p_close + c_tour (eta − logit p_close) + b spd_L, fitted on L's matches of 2019 .. Y − 1
   (training_window's two-part recalibration, per level). Compared with `exp` on L's matches. Because the pattern that
   motivated it was seen on the same seasons, a gain here is a lead, not a finding.

## Experiment B: Challenger rows

1. **Do lower-level rows hurt the current model?** `omtch` (the current model's rows plus every Challenger match, price
   missing for those) against `exp` with the same seeds (0–1) and the same calibration window (2021 .. Y − 1), on
   main-tour matches. − = the Challenger rows hurt; + = they help; tie = no detectable effect. Read at both stages.
2. The same question without prices: `nmtch` against `nmt`, on main-tour matches.
3. **Separate Challenger model?** On Challenger matches: `nch` (Challenger rows only) against `nmtch` (pooled).
   + for `nmtch` = pooling helps the Challenger forecast; − = a separate model is better; tie = either.
   `nmt` against `nch` says how far a main-tour-only model transfers down.
4. **Reproduction:** `nmt`'s main-tour forecasts must equal the stored no-odds fits (seeds 0–1) within 1e-4; a larger
   difference is reported, not silently accepted.
5. No market price exists for Challenger matches before 2025 in the project's data, so B says nothing about an edge on
   Challenger markets; only whether a model is a better forecaster.

## Experiment C: the history composition as an input (added 8 Oct 2026 after part 4's first read)

Added after the part-4 test below was first computed on 2020–2024 (β for the close +0.18 [+0.09, +0.27]), before any
experiment-C fit was run or scored. Because the lead was found on the same seasons, C's 2020–2024 score is **not a
confirmation**: it says whether TabPFN can use the signal at all. The replication is the close's β on 2013–2019,
which the lead was not found on.

1. **Primary:** `hist1` (the 58 inputs plus `low_share_diff`, the current model's rows and settings) against the
   current model, both stages (each with its own stage 2 fitted as decided), main-tour matches 2020–2024, both tours.
   + = the new input helps.
2. Read also by tour and by level, and against the close and Pinnacle. β of `hist1`'s forecast should move toward 0
   if the model absorbed the signal.
3. A better result here makes the input a **candidate** for the owner, to be confirmed on matches the lead was not
   found on (the sealed holdout or prospective matches). A tie means TabPFN cannot use it beside the price.

4. **Exploratory C2, added after C's primary read (a tie, +0.06), before C2 was computed.** The share as a walk-forward
   term in stage 2 instead of a TabPFN input, as the decided speed adjustment is used:
   logit q = s_tour eta + b spd_L + g low_share_diff (missing = 0), the four coefficients fitted jointly by maximum
   likelihood on the current model's own forecasts of 2019 .. Y − 1 (debut seasons out); b shrunk as decided
   (τ = 0.05), g not shrunk. Compared with the current model (both stages) on 2020–2024, both tours, and by tour and
   level. Same caveat as C: the lead was found on these seasons, so a gain is a candidate, not a confirmation.

## Players between levels (model and market)

On main-tour matches 2020–2024: logistic of the result on the forecast's log-odds (slope fitted) plus β × (A's share of
last year's matches below the main tour − B's), for the current model, the recalibrated close and Pinnacle.
β > 0 = the forecast under-rates the player with more lower-level history; a β excluding 0 **for the close** is a
lead for a new input (to be built and scored against both stages), not a finding of edge by itself.
