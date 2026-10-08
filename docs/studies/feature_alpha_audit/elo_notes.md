# Focused retest: additive information beyond Elo

**Research, 2 October 2026.** These are exploratory historical checks of promising features already selected after inspecting the two studies. They do not create an untouched holdout or establish a betting edge. Original study files were not changed.

The evidence supports continuing with serve/return strength, short-term adjusted point performance, recent activity, surface transition and age. Testing them jointly finds substantially more improvement over Elo than the diagnostic's one-feature summary conveys. Most of short IOS overlaps adjusted recent point performance. The combined forecast still trails the bookmaker average on matched matches.

## What was tested

The fixed ladder uses existing feature columns: surface Elo; serve/return ratings through the iid match model; `adjperf_tpw|decayed` (the existing two-week half-life); the previously highlighted IOS diagnostics (ATP four weeks, WTA thirteen weeks); games-weighted Elo; and a context block consisting of sets played over fourteen days, the first three surface matches of the season, age and age squared.

For every model, the annual expanding logistic fit uses only earlier seasons. Training starts in 2013; evaluation starts in 2019, with 2022 onward also reported. Inputs are scaled by training-set RMS only. No intercept is fitted because inputs are differences between arbitrary sides A and B. Raw Elo and annually slope-calibrated Elo are both reported. All ladder models use the same complete-case training and evaluation rows, including the same rows for their baseline.

Excluding the original 2010–2012 regression-training rows avoids fitting the downstream combination to Elo's initial warm-up regime. This does **not** remove those years from rating histories or retune the original features. The original diagnostic itself identifies this distortion in [Stage 4, section 6](../predictability_diagnostic/stage4.md). A separate sensitivity restores the original training start.

The initial run used four-week IOS for both tours. Before examining the revised run, it was changed to the original studies' tour-specific shortlist. Individual context ablations were added after the first combined-context result to understand its attribution. These choices are disclosed in `elo_protocol.json`; the final configurations were not selected by maximizing the new table.

Uncertainty is a paired 95% calendar-week cluster-robust t interval. It allows matches within a tournament week to be dependent, but does not handle every form of serial player dependence or selection across the earlier studies. These are pointwise intervals, not a multiple-testing significance declaration.

## Results

Positive gains below mean lower log loss, in **milli-log-loss**: 1 means 0.001 lower log loss per match. The 2022–2026 common cohort contains 63,336 ATP and 23,379 WTA matches, about 97.6% and 97.4% of the eligible rows. The 2019–2026 common cohorts contain 88,968 and 33,779.

| Addition and its reference | ATP gain, 95% interval | WTA gain, 95% interval |
|---|---:|---:|
| Slope calibration versus raw Elo | 1.03 [0.80, 1.25] | 0.10 [−0.01, 0.21] |
| Serve/return matchup versus calibrated Elo | 4.74 [4.01, 5.48] | 3.12 [2.21, 4.02] |
| Adjusted recent points versus Elo + serve/return | 1.03 [0.59, 1.47] | 1.26 [0.37, 2.15] |
| Short IOS versus Elo + serve/return | 1.07 [0.72, 1.43] | 0.99 [0.56, 1.43] |
| Short IOS after also adding adjusted recent points | 0.13 [0.05, 0.20] | 0.25 [0.13, 0.36] |
| Games-weighted Elo after both recent-point features | 0.31 [−0.01, 0.62] | 0.93 [0.41, 1.45] |
| Context block after all the above | 4.90 [4.16, 5.64] | 3.93 [2.75, 5.12] |
| Full model versus calibrated Elo | **11.10 [9.94, 12.27]** | **9.49 [7.68, 11.29]** |

The two recent-point approaches are mostly alternative measurements of the same information. Their standalone increments should not be added. Games-weighted Elo is more convincing for women in this comparison; its men's increment is small and its interval crosses zero.

The context block also survives the stronger baseline. Adding each part separately to Elo + serve/return + adjusted recent points + short IOS + games-weighted Elo gives:

| Context addition | ATP | WTA |
|---|---:|---:|
| Sets over fourteen days | 1.10 [0.71, 1.48] | 2.00 [1.16, 2.84] |
| First three matches on a surface this season | 1.34 [0.90, 1.78] | 1.81 [0.97, 2.65] |
| Age and age squared | 3.11 [2.56, 3.66] | 1.11 [0.53, 1.68] |

These increments overlap. Age was not a wholly new discovery: the original all-level 2022–2026 diagnostic reports an ATP age gain of 2.88 over Elo. Its headline 1.42 pooled warm-up-era results with later ones. On the retest's common cohort, age alone over calibrated Elo gains 3.44 with training from 2013 and 3.10 with training from 2010. The large combined-context result is therefore not explained solely by dropping the warm-up regression rows.

On the 2022–2026 matched-odds subset, the full model improves calibrated Elo by 12.83 ATP and 10.34 WTA milli-log-loss. It nevertheless trails the **raw normalized bookmaker average** by 9.11 ATP and 6.92 WTA milli-log-loss (12,339 and 11,293 matches). This comparison does not fit the features on top of the market; it measures how close the standalone enriched Elo forecast gets. A separate market-conditional test is required to claim information beyond the line.

The 2019–2026 full-model gains over calibrated Elo are 11.86 ATP and 10.11 WTA on all common rows, and 13.65 and 10.71 on the matched-odds subset. Thus the overall conclusion is not unique to the 2022 onward reporting window.

## Source audit and limitations that matter for the shortlist

1. **Keep serve/return strength; its current representation is restrictive.** [stage3_ratings.py](../../../src/eda/predictability_diagnostic/stage3_ratings.py), lines 86–185, stores one serve and one return rating per player. The surface enters only through the tour/surface intercept (lines 221–243). There are no player-by-surface rating deviations, and the same drift increment is applied to serve and return uncertainty (lines 140–145). Tuning minimizes serve-point loss, rather than the final match target (lines 268–291). These are modeling restrictions, not demonstrated bugs. A pooled global-plus-surface rating and a small fast/slow-form component are reasonable targeted extensions of an already useful feature, with target-aligned chronological tuning. No claim of incremental market alpha follows from those suggestions.

2. **The diagnostic did not isolate recency from opponent adjustment.** In [stage4_features.py](../../../src/eda/predictability_diagnostic/stage4_features.py), `form_value`, lines 904–943, the adjusted form uses career sums while the 52-week/decayed forms use raw sums. Therefore “recent form beats opponent adjustment” compares different histories; it does not test a recent opponent-adjusted history against its recent raw counterpart. UFC's recent adjusted performance partially fills this gap, and the retest finds it adds about one milli-log-loss after serve/return ratings on both tours. The inferred adjustment slopes for other statistics also omit the player's own strength; the diagnostic already proposes a partial-slope correction. Do not rerun every weak statistic: focus on total, serve and return points.

3. **Workload and surface transition are useful proxies, with coarse definitions.** Activity uses tournament start dates and earlier rounds (stage4_features.py, lines 794–812 and 1164–1194), so “fourteen days” does not mean fourteen actual days before the match. Positive workload coefficients are not evidence that physical fatigue helps; these variables also describe recent participation, surviving draws and returning from inactivity. The surface flag is fewer than three matches in the **calendar season**, not actual days since a surface change. Retain the observed predictive signals, then investigate actual match dates, pre-event versus current-event activity, recovery time, surface changes and surface-specific uncertainty in a small joint test. The sources here do not establish any of those refinements as profitable.

4. **Format has a small known outcome dependency.** `best_of_five` defaults to reading whether either player won three sets (stage4_features.py, lines 194–205). IOS inherits that default in [stageB_ios.py](../../../src/eda/ufc_ideas/stageB_ios.py), lines 426–436. Some match-tiebreak formats are also inferred from scores. The original audit found a small effect for the diagnostic; that is not a complete repair of short IOS. The stored IOS per-player file holds the originally tuned path, not the short-diagnostic paths, so those forecasts cannot be rebuilt cheaply from that file alone. The main retest therefore uses the actual saved artifacts and explicitly is not a deployable reconstruction.

5. **The format sensitivity does not explain the gains.** In the full source table, 189 standard-format records read best-of-five from three sets won despite the recorded best-of not being five. A conservative sensitivity removes entire tournament editions containing any such override or any nonstandard format, from both fitting and scoring. That removes 1,997 complete-case rows over 2010–2026; 534 ATP evaluation rows in 2022 onward and no WTA rows in that reporting period, although WTA training changes. Context gains become 4.90 ATP and 3.94 WTA, versus 4.90 and 3.93. Full-model gains over calibrated Elo become 11.04 and 9.50, versus 11.10 and 9.49. This outcome-audited exclusion is a sensitivity, not a recommended deployment rule. It neither rewrites earlier rating histories nor fixes the original artifacts.

6. **A model-dependent luck replay is not an empirical bound on pre-match alpha.** [stage2_anatomy.py](../../../src/eda/predictability_diagnostic/stage2_anatomy.py), `denoised_rates`, lines 350–381, fits a tour/surface distribution of latent serve rates from realized match rates and binomial-noise subtraction, then draws those rates independently and replays iid points. It is useful for describing a stipulated scoring model. It does not identify which latent variation could have been forecast from additional pre-match data, and cannot establish that only live information is valuable. The summary's suggestion that one failed combined model would close the pre-match route is stronger than the evidence.

Keep tiebreak/clutch records and generic head-to-head low priority. Their weak repeatability and small or absent incremental results do not justify another large feature sweep. A small negative tiebreak coefficient can be an Elo luck correction without demonstrating a persistent clutch trait. Reliable serving style also need not improve a winner forecast by itself; matchup/condition interactions need their own evidence.

## Reproduction and artifacts

Run [elo_retest.py](../../../src/eda/feature_alpha_audit/elo_retest.py) with `./python.sh`. On this Windows machine, prepend `C:\Users\zerom\miniforge3\envs\tennis\Library\bin` to the subprocess PATH so the environment's numerical DLLs load; the project shim is unchanged. Tests: `./python.sh -m pytest test/feature_alpha_audit/test_elo_retest.py -q -p no:cacheprovider` — **3 passed**. They check future-label/scale isolation, A/B complement symmetry and uncertainty under duplicates within a week.

Files under `data/studies/feature_alpha_audit/`: `elo_protocol.json`, `elo_results.csv`, `elo_coverage.csv`, `elo_predictions.parquet`, `elo_coefficients.json`, `elo_summary.json`, `elo_sensitivities.csv` and `elo_format_audit.json`. The CSVs and saved per-match predictions are the numeric evidence; intervals in this note are rounded. Constants, source joins, tournament ordering, identity problems and feature-level upstream assumptions remain those of the two original studies.
