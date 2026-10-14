# Pre-registration: translating lower-level evidence in the 17 one-step forms and `points_52w` (role 08)

Written 9 Oct 2026, before any offset was estimated, any frame was built, any fit was made or any score was read.
Its SHA-256 (CRLF normalised to LF) is in `preregistration.sha256`; the scorer (`src/eda/lower_level_evidence/candidate_pairs.py`)
refuses to run if this file changed. Any later addition is dated and marked "added after the scores".

## The question

The current best model's 17 one-step forms (`adjperf_tpw_2w`, 12 `form_*`, 4 `formdef_*`) keep about 78% of the raw
level shift of a lower-level match, and `points_52w` pools raw 52-week serve and return counts as if every level were
the main tour (team reports 01 and 03). The remedy tested here: translate each lower-level match's contribution by a
per-statistic, per-tour, per-level offset before it enters (a) the 17 forms and (b) `points_52w`. Nothing else in the
model changes. The yardstick is the frozen reference of 8 Oct 2026 (`data/studies/current_best_model/reference_2026-10-08/`).

## The offsets (estimated on seasons 2010-2018 only; no 2019+ value enters them)

Buckets as `src/eda/lower_level_evidence/common.py` (Stage 0's `map_level`): MAIN, TQ, GSQ, CH, CHQ, ITF, ITFQ, TEAM.
"Season" is Stage 0's `year`.

**Forms, delta_z[statistic, channel, tour, bucket].** On the sandbox's own Stage B per-match z (`stageB_adjperf.Ctx.z`
at the build's frozen constants, after the clip at +-4, before any translation), for the 17 (statistic, channel) pairs
that feed the 17 inputs: adjperf on ace, df, first_in, first_won, second_won, hold, bp_saved, bp_faced_pg, brk, bp_conv,
rpw_first, rpw_second and tpw; adjdef on ace, df, first_in and bp_faced_pg.
* A player-season qualifies for (statistic, channel, tour, bucket) when the player has at least 3 box rows with a
  finite z of that statistic and channel at MAIN and at least 3 at the bucket in that season.
* delta_z = the mean over qualifying player-seasons of (the player's mean z at the bucket - his mean z at MAIN).
* Estimated for TQ, GSQ, CH and CHQ. Interval: 95%, player-clustered (sandwich, G/(G-1)).
* A cell with fewer than 100 qualifying player-seasons takes the both-tours estimate (the same rule over both tours'
  player-seasons) if that has at least 100, otherwise 0.
* ITF and ITFQ (box scores only in 2025-2026, the holdout) take CH's and CHQ's final values: a documented placeholder.
  TEAM and MAIN: 0.

**`points_52w`, delta_rate[spw | rpw, tour, bucket].** The same rule on raw rates (team report 03, section 1, restricted
to 2010-2018): per player-season, the rate pooled over the season's rows at the level (sum of x / sum of d), on the rows
Stage 4 admits to its histories (completed, standard format, numerator and denominator present, d > 0); at least 3 such
rows at MAIN and at the bucket; delta_rate = the mean over qualifying player-seasons of (rate at the bucket - rate at
MAIN), in points per point. The same fallbacks and placeholders.

The offsets are written with their counts and intervals to `data/studies/lower_level_evidence/candidates/offsets/`.
The rate offsets are estimated from the frozen Stage 0 before the build (Stage 0 is the sandbox's); the form offsets are
estimated inside the build, from the z the build computes, by the hook's first full-history call, which also writes the
untranslated z it used. Every later full-history call re-estimates and must reproduce the stored offsets.

## The translation (the hook: `src/eda/lower_level_evidence/translate_hooks.py`)

Switched on by the environment variable `LLE_TRANSLATE` (the path of a JSON config); unset, every hooked function returns
its input unchanged (the unpatched behaviour).
* **Forms.** In `stageB_adjperf.build`, after the per-match z of every (statistic, channel) are computed and before the
  decay-and-shrink step: z <- z - scale x delta_z[statistic, channel, tour, bucket of the row's match], for every box
  row (0 at MAIN and TEAM). The clip is not re-applied. The tuning (which reads `Ctx.z` directly) is untouched, so the
  constants are the reference build's.
* **`points_52w`.** In `stage4_features.history_sums`, for spw and rpw only: x <- x - scale x d x delta_rate[statistic,
  tour, bucket] on the rows the history admits. Every Stage 4 form of spw and rpw moves with it; only
  `mu_points|52 weeks` (`points_52w`) reaches the model.
* scale = 1 for the build (FP). The patches to the sandbox's copies are a few lines that import the hook, saved as
  `sandbox_patch.diff`. No decided file in the repository is edited.

## The build

`MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_lle`, `run_chain.py --setup --candidate`; the two sandbox patches; lanes 1 and 2
beside each other, then lane 3, then `--collect --out data/studies/lower_level_evidence/candidates/FP`. The IOS constants
version is pinned to `2026-10-08_reference` (`IOS_CONSTANTS_VERSION`) for every lane.

## The gates (recorded in `checks/` before any fit)

* **G1 reproduction.** FP's frame against `frozen/instance/model_frame.parquet`: the same 67,226 match ids in the same
  order, the same identifier columns (the label `a_won` compared on seasons <= 2024 only, by a filtered read), every
  input other than the 18 translated ones identical (largest difference 0, the same missing cells), and the 18 changed
  with the same missing cells. If anything else differs, its cause is found; no fit is made until G1 passes.
* **G2 invariance.** (a) Matches in which neither player has any earlier lower-level box score (TQ, GSQ, CH, CHQ, ITF,
  ITFQ; the career window, because the two-week form decays without a cut-off; `sides.parquet` `box_career_*`) have all
  17 forms unchanged: difference exactly 0. (b) Matches in which neither player has a lower-level box score in the
  previous 365 days (`box_365d_*`) have `points_52w` unchanged up to rounding: the 52-week sums are career sums minus the
  part older than 52 weeks, so a translated older match can move them by floating-point rounding; pass if no difference
  exceeds 2 float32 units in the last place of the value (the frame's inputs are float32 values), with the count of
  exact zeros reported.
* **G3 direction.** For each of the 18 inputs and each tour, the Pearson correlation, over the matches where the input
  exists in both frames, between its change (FP - reference) and the share difference (A's lower-level share minus B's,
  box-score channel, from `sides.parquet`; the forms: the two-week effective counts `box_h2w_*`; `points_52w`:
  `box_365d_*`). Expected sign: for a form, opposite to the sign of its evidence-weighted offset (the offsets of TQ, GSQ,
  CH, CHQ, ITF and ITFQ weighted by that tour's summed `box_h2w_*` counts over the frame's player rows); for
  `points_52w`, negative. Pass: the sign is as expected for every form-tour whose evidence-weighted offset is at least
  0.05 z units in absolute value, and for `points_52w` on both tours; the rest are reported.
* **G4 linearity** (only for FP_half). From the code, and on the full history: the 17 forms computed by the sandbox's
  Stage B code at scale 0, 0.5 and 1 satisfy form(0.5) = (form(0) + form(1)) / 2 to float64 rounding (max difference
  under 1e-9), and form(0) and form(1) reproduce the reference's and FP's columns. The same test for `points_52w` with the
  sandbox's Stage 4 code.
* **G5 the fit runner.** The 59-input arms are fitted by `src/eda/lower_level_evidence/candidate_fits.py`, a copy of
  `model_rebuild/fits.py` that also admits the one registered extra input. Before any 59-input fit, it must reproduce
  the reference's stored fit (season 2019, seed 0) from the reference frame: largest difference of the `td` block under
  1e-6.

## The arms (folders under `data/studies/lower_level_evidence/candidates/<arm>/`, each with `model_frame.parquet` and `model_inputs.json`)

Every arm frame other than FP (and FP_L, which is FP's file plus one column) is the reference's file with columns
replaced or added (pyarrow, so the label column passes through unread); F, P, FP_placebo and FP_half replace only
translated inputs.

| Arm | Frame | Role |
|---|---|---|
| **FP** | the collected frame: the 17 forms and `points_52w` translated | **primary** |
| F | the reference frame with FP's 17 forms | channel: forms |
| P | the reference frame with FP's `points_52w` | channel: `points_52w` |
| FP_half | the reference plus half of FP's change (only if G4 passes; if `points_52w` is not linear, its exact value at scale 0.5 from the sandbox's Stage 4 code, accepted only if the same computation reproduces the reference's and FP's columns at scales 0 and 1; if that is not feasible, FP_half is not built) | dose |
| FP_placebo | the reference plus FP's per-match change vector (all 18 inputs together; a missing change counts 0; a missing reference value stays missing) permuted across matches within tour x season, numpy `default_rng(20261009)` | placebo twin |
| R_L | the reference plus `low_share_diff` as a 59th input (kind diff) | exposure-gap control |
| FP_L | FP plus `low_share_diff` | exposure-gap control |

`low_share_diff` is event-levels' experiment C1 input: A's share minus B's share of the previous 365 days' played matches
(completed or retired) below the main tour (TQ, GSQ, CH, CHQ, ITF, ITFQ over all, team events in the total only),
`event_levels/blend.history` on the frozen reference's Stage 0, for all 67,226 frame matches; missing when either player
has no played match in the window. Checked equal to `data/studies/event_levels/universe_columns.parquet` on the matches
both hold (differences, if any, are listed with their cause).

## The fits

Per arm, seeds 0-3, seasons 2019-2024, the decided settings: `./python_tabpfn_local.sh src/eda/model_rebuild/fits.py
--out <arm> --seeds 0-3 --seasons 2019-2024` for the 58-input arms; `candidate_fits.py` (G5) for R_L and FP_L. Order: FP,
FP_placebo, F, P, R_L, FP_L, FP_half. No 2025-2026 season is fitted.

## The scores (2020-2024; results of seasons <= 2024 only)

`./python.sh src/eda/current_best_model/compare.py --candidate <arm>` for every arm (part 1, the input check, read
first). Then the paired readings below, with compare.py's own functions (`seed_table`, `walk_forward`, `forecasts`,
`close_forecast`, `paired`): each model's stage-2 coefficients refitted walk-forward on its own seeds 0-3 forecasts on
2019 .. Y - 1, scored on 2020-2024, debut seasons out, matches both frames hold, the reference's speed column for every
arm. mLL per match; **positive = the named candidate has the lower log loss (better)**; 95% intervals from four-week
blocks plus the seeds' variance (paired by seed); "better" / "worse" when the interval clears 0, otherwise "tie"
(compare.py writes "unresolved" for a tie).

**Primary.** FP vs the reference, both stages, both tours, 2020-2024 (compare.py's primary row).

**Secondary (pre-registered).**
* F vs the reference; P vs the reference (both stages, both tours).
* FP vs the reference, men and women.
* FP vs the reference within strata (from `data/studies/lower_level_evidence/composition/reference_2026-10-08/sides.parquet`,
  counts only):
  * exposure: the less-exposed side's main-tour results in the previous 365 days (`res_365d_MAIN`, the smaller of the
    two) under 10, and 10 or more;
  * share gap: the absolute difference of the two sides' 365-day lower-level box-score shares (`box_365d_*`, lower
    buckets over all 8) at least 0.5, and under 0.5; matches where either side has no box score in the window are left
    out of both (counted);
  * falsification: both sides with at least 20 main-tour results in 365 days and a 365-day lower-level box-score share
    under 0.10 (its inputs should barely move and its gain should be about 0).
* FP vs FP_placebo (both stages, both tours).
* FP_L vs R_L (both stages, both tours).

**Reported without a decision rule.** The per-season rows, stage 1 alone, each arm against its own calibrated close, the
falsification stratum, FP_half vs the reference, R_L vs the reference, FP_L vs the reference, FP_placebo vs the reference.

## The pre-registered reading

- Primary: FP vs the reference, both stages, both tours, 2020–2024 (compare.py's primary row).
- "Better" if the primary's 95% interval clears 0 on the better side, FP beats FP_placebo, and FP_L is not worse than R_L → suggest adoption.
- "Tie, recommend on mechanism" if the primary is a tie, the input check shows no unexpected uneven input, and no pre-registered secondary (F, P, the per-tour rows, the strata, FP_L vs R_L) is worse with an interval below 0 → suggest adopting on mechanism (lower-level evidence becomes informative but not equivalent before the ITF box scores arrive), as the product-centring study did.
- "Worse" if the primary is worse → do not adopt; use F, P, FP_half and FP_L to locate the harm.
- Also report, without a decision rule: the per-season rows, stage 1 alone, each arm against its own calibrated close, and the falsification stratum.
- Accepting a candidate is the owner's call; you only suggest.

**Operational definitions.**
* "FP beats FP_placebo": the paired FP-vs-FP_placebo reading is "better" (its 95% interval above 0).
* "FP_L is not worse than R_L": the paired FP_L-vs-R_L reading is not "worse" (its interval does not lie below 0).
* "An unexpected uneven input": any input outside the 18 flagged uneven or every-season by compare.py's part 1; or one of
  the 18 flagged uneven where a flagged tour-season's mean absolute share difference (`sides.parquet`, the input's own
  window) is below that tour's median over seasons 2013-2026 (a flag the lower-level evidence mix does not explain).
* If the primary is better but a "better" condition fails, the reading is not "Better"; it is reported as is, with the
  failed condition named, and no adoption is suggested on the score alone.

## The holdout

2025-2026 (events from 30 Dec 2024) is the proposed clean holdout. No outcome of a 2025-2026 match is read: fits cover
seasons 2019-2024, scores 2020-2024 (compare.py's default `--through 2024`). Inputs of 2025-2026 are built and counted
(the input check reads no result).

## Addition of 9 Oct 2026, 16:43 UTC (written before any score was read)

Requested by the lead from the red team's review (team report 07, items S2 and M1). Written before any candidate fit
existed and before any candidate score was read. Before it, the scorer had only been dry-run on the reference against
itself (0 exactly) and against its calibrated close (the published +1.37). The text above this heading is unchanged:
its SHA-256 stays in `preregistration.sha256`; the file with this addition is hashed in
`preregistration_addition.sha256`; the scorer checks both.

**1. One more control arm, R_S2.**
* Why. With one constant offset per statistic, tour and level, the translation moves each form by about delta times the
  player's shrunk lower-level share in the form's two-week window, and `points_52w` by delta times its 364-day share. FP
  is therefore, in effect, the reference re-centred by two share variables. The pre-registered control R_L uses
  event-levels' 365-day results share, which is not the share that drives 17 of the 18 changes.
* R_S2 = the reference plus two inputs, kind diff: `box_low_share_h2w_diff`, A's minus B's lower-level share of
  box-score evidence in the two-week-half-life window, and `box_low_share_365d_diff`, the same over 365 days. From
  `sides.parquet` (role 02): the box channel, windows h2w and 365d, lower = TQ + GSQ + CH + CHQ + ITF + ITFQ over all 8
  buckets; missing when a side has no box-score evidence in the window.
* Fitted after the pre-registered arms (seeds 0-3, 2019-2024) by `candidate_fits.py`, which admits these two registered
  extra inputs as it admits `low_share_diff` (G5 covers the runner).
* Reading. FP against R_S2, paired, both stages, both tours, 2020-2024 (also men and women). If FP's gain over the
  reference survives against R_S2 (FP vs R_S2 "better"), the translation carries more than the share signal; if not, it
  is the share signal in disguise. Also reported: R_S2 against the reference. The verdict rule above is unchanged; this
  reading is reported beside it and qualifies what the verdict means.

**2. Wording** (the owner's decision of 9 Oct 2026, `docs/decisions/2026-10-09-adoption-framework.md`). No comparison is
called a "tie": "better" or "worse" when the 95% interval clears 0, otherwise "unresolved", with P(better). The verdict
rule's "tie" branch above reads as "unresolved"; its logic is unchanged.
