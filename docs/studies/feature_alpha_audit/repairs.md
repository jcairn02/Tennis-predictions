# Repaired tennis feature study

2 October 2026. Implemented corrections and a fresh feature rebuild following the [original audit](README.md). Research evidence, not a model or betting decision. [HTML version](repairs.html); [measured comparisons](../../../data/studies/feature_alpha_audit/repairs/repair_results.csv).

**The defects are fixed in code and the shortlisted features have been rebuilt. The men's recent statistics profile retains a positive point estimate, but its repaired uncertainty interval includes zero.** Its gain beyond calibrated Pinnacle is +0.355 [-0.251, +0.961] milli-log-loss on 16,333 matches. Beyond Pinnacle plus ratings, load, age and surface context, the profile contributes +0.364 [-0.224, +0.953]. These are exploratory, historically selected comparisons; the intervals do not correct for the earlier feature search.

A positive gain means better predictions. +1 milli-log-loss means reducing mean natural-log loss by 0.001; it is not a percentage-point increase in accuracy or a betting return. Brackets below are paired 95% intervals clustered into four-week calendar blocks, with week-cluster sensitivity retained in the CSV.

## What was fixed

| Defect | Implemented correction | Verification / scope |
| --- | --- | --- |
| Overlapping tournaments could expose future results | Both history and targets now require accepted provider match dates. Every selected rating and statistic is rebuilt from raw rows in match-day order. | A future-result mutation in an overlapping tournament cannot change protected earlier Elo, serve/return, adjperf or IOS values; later forecasts must respond. |
| Current scores determined forecast format | Forecast format and box-history eligibility come from event, tour, year and scheduled round. Unsupported editions are excluded from box history and iid probability conversion; future scores cannot classify earlier history. | 121 recorded best-of disagreements; 247 unsupported evaluation matches excluded by event metadata across the original pool. [Rule sources](format_rules.md). |
| Split player identities | Canonicalize unambiguous normalized full names against Sackmann identity records, with demographic and opposing-player collision checks. | 305 player rows corrected in the full input table; unresolved conflicts are recorded. |
| Match tiebreaks counted as games | Reconstruct certain historical deciding match tiebreaks separately from ordinary games. Preserve ambiguous two-game-margin advantage sets. | 7,650 historical score records corrected; this does not determine forecast format. |
| Invalid box counts and durations | Negative primitive counts invalidate both players' box statistics; impossible derived ratios and implausible durations are missing. | 1 paired boxes invalidated; 137 durations masked. |
| Full-sample scaling and overstated evidence | Fit scaling within training seasons; compare raw and recalibrated baselines separately; use paired calendar clusters. A negative gain cannot clear the evidence threshold. | Shuffled thresholds are labelled descriptive heuristics, not conditional null tests or family-wise error control. Shared scorers are repaired. |
| Simulation interpreted as a forecasting ceiling | Removed the claims that perfect pre-match information has a demonstrated low ceiling or that failed tested features close the pre-match route. | The original simulation remains conditional on its iid and denoising assumptions. |

## The chronology repair has a coverage cost

The rebuild accepts 78,714 of 872,704 original matches (9.0%). A date is accepted only with a trusted identity join, matching set scores and round, no reassigned provider date, and a plausible gap from the event start. Undated matches are omitted from both history and targets; no artificial finish dates are assigned. The surviving history is main-tour matches. Challenger, qualifying and ITF coverage has not been repaired by inventing timestamps.

| Date check | Matches |
| --- | --- |
| no match day | 793,035 |
| accepted | 78,714 |
| score identity not confirmed | 852 |
| date was reassigned | 63 |
| round identity not confirmed | 21 |
| untrusted identity link | 19 |

Only earlier days and strictly earlier rounds of the same event on the same day may contribute. A previous day's result is assumed available by the next day; exact match-end and quote timestamps remain unavailable. Retrospective source concordance establishes record identity, not a timestamped pre-match join process. This corrects the demonstrated event-start ordering leak within the accepted cohort, not all historical data availability questions. Reduced history also changes workload, surface familiarity and player warm-up. Changes in model performance cannot be attributed solely to removal of leakage.

## Closing-line comparisons after rebuilding

| Market | Men, 2019 onward | Matches | Gain [95% interval] |
| --- | --- | --- | --- |
| Average | Profile beyond recalibrated line | 16,333 | +0.396 [-0.243, +1.036] |
| Average | Profile forecast versus raw line | 16,333 | +0.786 [-0.104, +1.676] |
| Average | Profile with raw line as fixed offset | 16,333 | +0.694 [-0.127, +1.514] |
| Average | Ratings + load + age + surface | 16,333 | +0.193 [-0.098, +0.483] |
| Average | Profile beyond line + context | 16,333 | +0.411 [-0.206, +1.029] |
| Average | Profile + context together | 16,333 | +0.604 [-0.115, +1.323] |
| Pinnacle | Profile beyond recalibrated line | 16,333 | +0.355 [-0.251, +0.961] |
| Pinnacle | Profile forecast versus raw line | 16,333 | +0.408 [-0.269, +1.085] |
| Pinnacle | Profile with raw line as fixed offset | 16,333 | +0.433 [-0.235, +1.101] |
| Pinnacle | Ratings + load + age + surface | 16,333 | +0.214 [-0.053, +0.481] |
| Pinnacle | Profile beyond line + context | 16,333 | +0.364 [-0.224, +0.953] |
| Pinnacle | Profile + context together | 16,333 | +0.578 [-0.106, +1.263] |

The same profile versus calibrated Pinnacle in 2022 onward: +0.273 [-0.597, +1.143] on 10,243 matches. The scored main comparison runs from 2019-01-01 to 2026-01-13. Average and Pinnacle comparisons use identical complete-case matches. Ridge selection uses predictions from the prior two calendar seasons only; each validation regression is itself trained on earlier seasons. The 16 statistics and feature constants are frozen from the prior studies, so this is a corrected replication, not a newly tuned model search.

The original pre-2019 feature constants, population priors and exposure scales remain frozen. Their tuning was not rerun on corrected histories; all scored seasons here follow that tuning period. The repairs rebuild observations, rating states, features and forecast fits. Inner penalty validation before 2019 therefore inherits feature constants estimated through 2018; it is not a fully nested retuning of the feature generator. They do not claim that the old constants are optimal for the reduced history universe.

## What adds beyond Elo on the repaired cohort

| Sequential comparison, 2019 onward | Men | Women |
| --- | --- | --- |
| Serve/return strength | +12.329 [+10.103, +14.555] | +11.733 [+9.281, +14.185] |
| Add recent adjusted points | +0.777 [+0.173, +1.381] | +1.142 [+0.423, +1.861] |
| Add short-memory IOS | -0.013 [-0.091, +0.066] | -0.052 [-0.139, +0.035] |
| Add games-weighted Elo | +0.278 [-0.363, +0.920] | +0.540 [+0.149, +0.931] |
| Add load, age and surface context | +4.618 [+3.108, +6.127] | +3.914 [+2.735, +5.093] |
| Full combination versus Elo | +17.989 [+15.289, +20.689] | +17.277 [+14.617, +19.936] |

The full Elo-based combination versus raw Pinnacle on its available market subset is ATP -24.170 [-28.158, -20.183] (16,362 matches); WTA -16.804 [-19.838, -13.771] (15,003 matches). This is distinct from fitting the market itself as an input.

Every ladder row uses the same eligible matches within each tour and expanding season-by-season training. A sequential gain measures only the addition to the row immediately before it; it is not the feature's standalone value. The recent-window ladder, absolute losses, market-subset comparisons and exact row counts are in the measured CSV. The promising next research remains a player's performance relative to their own expected serve/return level, and partially pooled player-by-surface ratings. Those changes have not been silently mixed into this bug-fix replication.

A larger serve/return gain than in the original study is not evidence that its alpha increased. Removing undated lower-level history changes the Elo comparator and the other ratings as well. The conditional feature additions above are interpretable within this restricted cohort; cross-study differences are not controlled timing experiments.

| Rebuilt forecast versus cached original on identical match IDs | Matches | Change [95% interval] |
| --- | --- | --- |
| Men: Pinnacle + profile | 16,333 | -0.523 [-0.946, -0.099] |
| Men: full Elo combination | 18,174 | -14.440 [-17.342, -11.538] |
| Women: full Elo combination | 16,654 | -9.756 [-12.437, -7.075] |

Negative values in this last table mean the rebuilt forecast performs worse than the archived forecast on the same targets. The comparison combines corrected chronology, format, identities, reduced history and changed fitting cohorts. It cannot quantify how much of the original score came from leakage.

## Verification and reproduction

361 tests passed; 0 skipped; no failures or errors. Regressions cover outcome-independent format, future-overlap isolation with responsive later controls, identity collisions, invalid data, training-only scaling, side symmetry and paired clustered uncertainty. All 168 original numerical evidence files remain unchanged. The 235-file pre-repair source/report archive matches its original hashes. [Verification evidence](../../../data/studies/feature_alpha_audit/repairs/verification.json).

```bash
./python.sh src/eda/feature_alpha_audit/repair_history.py
./python.sh src/eda/feature_alpha_audit/repair_features.py
./python.sh src/eda/feature_alpha_audit/repair_score.py
./python.sh -m pytest test/predictability_diagnostic test/ufc_ideas test/feature_alpha_audit -p no:cacheprovider --basetemp=data/studies/feature_alpha_audit/repairs/pytest_rebuild --junitxml=data/studies/feature_alpha_audit/repairs/test_results.xml
./python.sh src/eda/predictability_diagnostic/render_report.py
./python.sh src/eda/ufc_ideas/render_report.py
./python.sh src/eda/feature_alpha_audit/verify_repairs.py
./python.sh src/eda/feature_alpha_audit/repair_report.py
./python.sh src/eda/feature_alpha_audit/render_report.py
./python.sh src/eda/feature_alpha_audit/check_report.py --document docs/studies/feature_alpha_audit/repairs.html --output-dir data/studies/feature_alpha_audit/repairs
```

Run from the repository root using the project's tennis environment through Git Bash. On this Windows machine, prepend C:/Users/zerom/miniforge3/envs/tennis/Library/bin to PATH for the numerical DLLs. Use a new writable pytest temporary directory if the shown one already exists. The shim and environment files were not changed. Original study outputs are historical; running their older full-pool builders does not supply missing match dates. Use the repair sequence above for the corrected shortlist. Weak feature families were not rerun.

The remaining limit is data coverage and publication timing, not an unimplemented test. No untouched holdout, executable closing-price history or measured after-cost betting edge is created by these repairs. [Source register and usage restrictions](sources.md).
