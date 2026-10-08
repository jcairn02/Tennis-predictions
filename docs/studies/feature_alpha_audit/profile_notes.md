# Men's opponent-adjusted individual-statistic profile: audit and retest

Research notes, 2 October 2026. These are retrospective diagnostics of an already selected lead, not an untouched holdout, a production choice, or evidence of executable betting returns. Positive gains below mean lower log loss, in milli-log-loss (mLL; 1 mLL = 0.001 log loss).

## What survives the retest

The original 16-input, two-week profile result reproduces: **+0.510094 mLL** over seasonally calibrated average bookmaker probabilities on **31,661** scored matches. Clustering its paired differences by tournament-start week widens the 95% interval to **[-0.114, 1.134]**. The original headline's point estimate was not a scoring error.

On identical rows with both average and Pinnacle probabilities, train-only scaling and prior-season-only ridge selection leave a small men's signal. The post-tuning interval, 2019–2026, contains **16,776** scored matches:

| Model and comparator | Average odds: gain | Pinnacle: gain | Pinnacle 95% four-week interval |
|---|---:|---:|---:|
| Unpenalized profile versus calibrated market | 0.883 | 0.816 | [0.073, 1.558] |
| Ridge profile versus calibrated market | 0.862 | 0.794 | [0.126, 1.462] |
| Ridge profile versus raw market | 1.311 | 0.868 | [0.145, 1.591] |
| Profile with the market coefficient fixed at 1 versus raw market | 1.225 | 0.900 | [0.189, 1.611] |
| Profile added to market + serve/return rating + recent sets | 0.613 | 0.567 | [0.002, 1.133] |
| Profile added to the preceding controls + age quadratic + surface familiarity | 0.560 | 0.509 | [-0.084, 1.102] |

The last row is a separately recorded follow-up diagnostic requested after the initial retest. Its Pinnacle weekly interval is [-0.027, 1.046]. Plausible additional controls and longer dependence blocks leave the extra contribution uncertain. This is the appropriate stopping point for claims of independent alpha from these data.

Ridge did not unlock a large improvement: its full-profile point estimates are slightly below the unpenalized fit's. The uncentered training-only RMS scale preserves side symmetry. A model with no intercept and signed features satisfies P(A beats B) = 1 − P(B beats A). A synthetic test verifies this by refitting after swapping outcomes, market signs and feature signs. The saved maximum complement error, 2.22e-16, is only an arithmetic check of sigmoid symmetry. The inherited feature builder explicitly returns each player's value minus the other's. The raw feature history was not rebuilt by this scoring retest.

## Sample and uncertainty qualifications

**The Pinnacle comparison is effectively through 2025.** The archived 2026 ATP odds table contains 1,786 average probabilities, but only **71** Pinnacle probabilities; their linked match dates are **4–13 January 2026**. In 2025, Pinnacle dates extend through 16 November. A label such as “2022–2026” therefore must not be read as current-season validation. There are no 2018 complete profile rows in the inherited feature sample.

The profile's inherited hyperparameters and population constants use 2010–2018. Post-2018 is the primary diagnostic interval here, but those later outcomes had already informed which profile to investigate. Every confidence interval is **pointwise and conditional on historical selection**; none corrects the previous studies' many candidate searches or these follow-up analyses. Tournament-start-week and four-week clusters address some shared-event and adjacent-week dependence, but are not guarantees that players' successive observations are independent.

| Pinnacle ridge profile versus calibrated market | Matches | Gain | 95% weekly interval | 95% four-week interval |
|---|---:|---:|---:|---:|
| 2019–2026 | 16,776 | 0.794 | [0.167, 1.420] | [0.126, 1.462] |
| 2019–2025 | 16,705 | 0.828 | [0.200, 1.456] | [0.158, 1.497] |
| 2022–2026 | 10,503 | 0.846 | [0.047, 1.645] | [-0.067, 1.759] |
| 2022–2025 | 10,432 | 0.901 | [0.099, 1.703] | [-0.015, 1.817] |

The 2022–2026 raw-Pinnacle gain is +0.959, with a four-week interval of [-0.069, 1.987]. Beyond the rating/load controls it is +0.545 [-0.184, 1.274], and beyond the expanded context controls +0.453 [-0.322, 1.229]. Removing the tiny 2026 slice does not remove the older positive pattern, but does not make the recent-window four-week interval exclude zero.

**The market alone must be an explicit comparator.** Seasonal slope calibration adds +0.449 to raw average odds and +0.074 to raw Pinnacle odds in the same post-2018 sample. Comparing the profile directly to raw odds includes this calibration effect. The fixed-offset test and the calibrated-market baseline separate the interpretations. These stored bookmaker probabilities are not independently verified timestamped executable closing quotes.

## Calendar-week feature sensitivity

The separate frozen-feature rebuild maps every tournament date to its preceding/same Monday, including Sundays backwards. The model scorer then refits original and rebuilt profiles on exactly the same eligible observations, with the same nested ridge and uncertainty procedure. The intersection removes one 2010 training row relative to the main retest (36,633 to 36,632 training-inclusive rows); it removes no post-2018 scored observations. That accounts for the very small differences between the original-profile comparator here and the main table.

| Pinnacle comparison, 2019–2026, 16,776 matches | Original dates: gain | Calendar-week dates: gain | Calendar-week 95% four-week interval |
|---|---:|---:|---:|
| Ridge profile versus calibrated market | 0.794 | 0.707 | [0.030, 1.384] |
| Profile with fixed market offset versus raw market | 0.900 | 0.810 | [0.088, 1.532] |
| Profile beyond market + rating + recent sets | 0.568 | 0.518 | [-0.052, 1.087] |

For 2022–2026, the normalized profile's gain beyond calibrated Pinnacle is +0.759 [-0.168, 1.686] in four-week blocks. The calendar change modestly weakens the headline; it does not erase it. Its extra contribution beyond ratings and load becomes uncertain even in the broader interval. This sensitivity changes history eligibility and decay ages together. It does **not** recover actual match times, repair fortnight-event overlaps, establish when statistics became available, or rebuild the inherited market, Elo, and context inputs. It must not be called a fully chronological correction.

Evidence: `profile_chronology_results.csv`, `profile_chronology_predictions.parquet`, and `profile_chronology_coefficients.json`; input `chronology_calendar_week_features.parquet`. The feature rebuild and its own tests are documented in [method notes](method_notes.md).

## What might carry the effect

The group-drop tests were fixed before the new model scores: omit serve style (aces, double faults, first serves in, including corresponding defence inputs), omit games/break-point statistics, or omit the four extra defence inputs. All use the same rows and the same prior-season ridge-selection procedure.

| Contribution measured by full profile versus omitted group, Pinnacle 2019–2026 | Gain | 95% weekly interval |
|---|---:|---:|
| Serve-style inputs | 0.308 | [-0.040, 0.656] |
| Games/break-point inputs | 0.149 | [-0.230, 0.528] |
| Four additional defence inputs | 0.219 | [-0.084, 0.522] |

No group has a precisely identified marginal contribution. There is no defensible “winning statistic” from these ablations. In the 2025 Pinnacle fit, recent first/second-serve point-winning and ace residuals have positive coefficients, while holds have a negative conditional coefficient (-0.079 per training RMS). A possible mechanism is correcting the market's assessment of recent results using point performance and conversion luck. This is an inference from correlated coefficients, not a demonstrated causal mechanism or a validated new feature. The short half-life and strong shrinkage can also encode recent activity; the conditioning checks were included for that reason.

By level, the 2019+ Pinnacle ridge gain is +1.780 at Masters 1000 events (3,837 matches; four-week interval [0.390, 3.169]), +0.698 at majors (3,386; [-0.537, 1.933]), +0.810 at 250s (6,732; [-0.220, 1.840]), and -0.723 at 500s (2,717; [-2.662, 1.215]). Finals have only 104 matches. The Masters concentration repeats the selected historical finding; it is not independent evidence for a betting filter, and events spanning multiple weeks make chronology especially relevant.

Annual Pinnacle ridge gains over calibration are -0.280 (2019), +2.162 (2020), +1.000 (2021), +0.883 (2022), +0.293 (2023), +1.068 (2024), +1.388 (2025), and -7.234 (the 71 matches of early 2026). The tiny last slice cannot establish a regime change. No claim of a positive gain in every recent season is warranted on this matched sample.

## Reproduction and evidence

Code: [`profile_retest.py`](../../../src/eda/feature_alpha_audit/profile_retest.py). Tests: [`test_profile_retest.py`](../../../test/feature_alpha_audit/test_profile_retest.py), **4 passed**. They verify prior-only penalty selection, future-feature invariance of forecasts/scales, side-swap symmetry, and cluster uncertainty that does not falsely shrink when the same observations are repeated within a cluster.

For each target season, all fits use earlier seasons. The ridge grid is 0, 0.0001, 0.001, 0.01, 0.1 on mean loss; the market slope is unpenalized. Selection uses available validation losses within the preceding two calendar seasons, each predicted with its own earlier training set and scale. Because 2018 is absent, the 2019 penalty choice uses only 2017 validation observations; the 2020 choice similarly has only 2019 observations. It does not always have two complete validation seasons. A fixed 0.01 is used before 300 prior validation rows exist. Each model and its baseline share the same rows. The original all-average sample is reproduced separately. Four-week intervals use fixed, non-overlapping 28-day calendar blocks anchored on Monday 4 January 2010, a follow-up dependence sensitivity.

All evidence files are in `data/studies/feature_alpha_audit/`: `profile_plan.json`, `profile_reproduction.csv`, `profile_results.csv`, `profile_predictions.parquet`, `profile_coefficients.json`, `profile_metadata.json`; expanded conditioning is in `profile_context_plan.json`, `profile_context_results.csv`, `profile_context_predictions.parquet`, and `profile_context_coefficients.json`. Results carry both the comparator and the scoring sample, annual and level rows, and event/week/four-week intervals.

Use the project's `./python.sh`. In this Windows session, the Conda environment's `Library/bin` also had to be prepended to PATH for its numerical DLLs; the shim was not changed. Run the main script normally, add `--context` for the separate expanded conditioning test, or use `--chronology-features data/studies/feature_alpha_audit/chronology_calendar_week_features.parquet` for the paired feature-date sensitivity. Inherited source artifacts are preserved.
