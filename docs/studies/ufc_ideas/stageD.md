# Stage D: together

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: built 2 Oct 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md); the report section is Stage D in [report.html](report.html).

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/ufc_ideas/`: `stageD_profile_summary.json` and `stageD_profile_ranking.csv` (part 2), `stageD_summary.json` and `stageD_ranking.csv` (part 1). Improvements are in milli-log-loss, positive is better; "given Elo" and "given the odds" are the shared harness's walk-forward gains over surface Elo alone and over the closing odds alone; the women's rows are scored from 2019 because every model holds box-score inputs.

Stage D has two parts. Part 2 was added after the owner's question of 2 Oct 2026 ("offensive/defensive ratings of individual statistics within a match ... are more orthogonal to the market") and is the lead result; part 1 is the combination the earlier study suggested.

## In short

* **Observed. The profile of individual statistics is the one thing in either study that gains on the closing odds, for the men.** The 2-week adjperf profile (twelve individual statistics plus adjdef on the four with no mirror, 16 inputs) adds 0.51 milli-log-loss to the odds over all scored seasons (95% range −0.05 to 1.07) and 0.92 in 2022–2026, clearing the family-wide line of the run. With the points-won aggregates added it gains 0.54 (−0.20 to 1.28; 1.13 in 2022–2026). The previous best against the odds, in the earlier study, was a single row at 0.32.
  * Alone the profile is 16.7 better than a coin, against 73.3 for the two points-won aggregates: it carries little of who wins, which is what makes it independent of a win rating. Given Elo it adds 3.97, as much as the points-won aggregates (3.45).
  * **Inferred:** a lead, not an edge. Half a milli-log-loss is about half a percent of the way from a coin flip to the odds, and the range reaches zero.
* **Observed. It is recent form, not traits.** The same statistics over 52 weeks give −0.09 given the odds; the IOS offence and defence profile (long memories, 26 to 208 weeks) gives −0.06; the serve-style IOS profile (aces, double faults, first serves in) −0.03. The weapon-times-liability products add nothing for the men (−0.21 with, −0.06 without, on the IOS profile).
* **Observed. The women show nothing against the odds** in any profile: the adjperf profile 0.02 (−0.51 to 0.54), both profiles together −0.31, with the products 0.29 (−0.57 to 1.14).
* **Observed. Everything together adds about ten milli-log-loss to Elo and a third of one to the odds.** The "everything" model (Bradley–Terry, the ratings through the iid model, the games-weighted Elo, the 2-week adjperf of total points, the short-memory IOS matchup, sets over 14 days, the first matches on a surface, age and the credit for opponents lost to; 10 inputs) adds 9.35 (men; 95% range 8.59 to 10.11) and 9.86 (women; 8.27 to 11.44) given Elo, and 0.31 and 0.32 given the odds. With MESR it adds 0.42 and 0.37 to the odds on the matches where both players have an odds history.
* **Observed. On the ladder** (main-tour matches with odds, 2022–2026; a coin flip 0%, the bookmakers 100%): Elo alone 78% (men) and 82% (women); Elo refitted each season 79% and 83%; Elo + the earlier study's three 86% and 90%; Elo + everything 90% and 92%. The raw Bradley–Terry rating is at 77% and 76%, below Elo.
* **Observed. No model that excludes the points-won aggregates and the ratings gets near the odds alone**: the Stages A–C model (6 inputs) is −0.05 and −0.18 given the odds.

## Part 2: the individual statistics together (`stageD_profile.py`)

**Inputs** (Stage B's columns, every one at Stage B's frozen constants; A − B differences):

* adjperf, 2-week half-life ("decayed") and the last 52 weeks, on aces, double faults, first serves in, first-serve points won, second-serve points won, service games held, break points saved, break points faced per service game, breaks, break points converted, return points against the first serve and against the second serve; adjdef (decayed) on the four without a mirror (aces, double faults, first serves in, break points faced per game);
* IOS offence (O) and defence (D) on aces, double faults, first serves in, first-serve points won, second-serve points won, holds and break points saved;
* the products: per statistic, A's offence × B's lack of defence minus B's offence × A's lack of defence, from the per-player ratings of `stageB_ios.parquet`;
* for comparison, the two points-won aggregates: the 2-week adjperf of total points won and the IOS points matchup.

**The models** and their scores (milli-log-loss; given the odds with its 95% range; `stageD_profile_ranking.csv`):

| Model (inputs) | Men, given the odds | Men 2022–26 | Men, given Elo | Women, given the odds | Women 2022–26 | Women, given Elo |
|---|---:|---:|---:|---:|---:|---:|
| adjperf profile, decayed, with adjdef (16) | 0.51 (−0.05 to 1.07) | 0.92 | 3.97 | 0.02 (−0.51 to 0.54) | −0.02 | 3.53 |
| adjperf profile, 52 weeks (12) | −0.09 (−0.46 to 0.28) | 0.32 | 1.92 | −0.33 (−0.78 to 0.13) | −0.43 | 1.57 |
| IOS profile (14) | −0.06 (−0.48 to 0.36) | 0.24 | 1.29 | −0.17 (−0.42 to 0.08) | −0.06 | 1.17 |
| IOS serve style: aces, double faults, first serves in (6) | −0.03 (−0.37 to 0.31) | 0.06 | 0.77 | 0.02 (−0.14 to 0.18) | 0.02 | 0.06 |
| IOS serve skill: first- and second-serve points, holds, break points saved (8) | −0.11 (−0.34 to 0.12) | 0.01 | 0.67 | −0.13 (−0.34 to 0.07) | −0.03 | 1.17 |
| IOS profile + 7 products (21) | −0.21 (−0.67 to 0.26) | 0.11 | 1.27 | 0.11 (−0.48 to 0.71) | 0.17 | 1.54 |
| both profiles (30) | 0.39 (−0.33 to 1.11) | 1.07 | 4.05 | −0.31 (−0.97 to 0.36) | −0.27 | 3.49 |
| both profiles + products (37) | 0.26 (−0.49 to 1.01) | 0.92 | 4.05 | 0.29 (−0.57 to 1.14) | 0.42 | 3.84 |
| both profiles + the points-won aggregates (32) | 0.54 (−0.20 to 1.28) | 1.13 | 4.46 | −0.26 (−0.96 to 0.44) | −0.43 | 4.53 |
| the points-won aggregates alone (2) | 0.20 (−0.12 to 0.52) | 0.33 | 3.45 | −0.07 (−0.38 to 0.24) | −0.14 | 4.44 |

Given the earlier study's ratings through the iid model instead of Elo, the IOS profile adds 3.00 (men) and −0.33 (women), the adjperf profile 0.30 and 0.34, both profiles 3.30 and 0.47.

**How to read "clears the line" here.** The 20 shuffled copies of a 30-input model lose against the odds (their best copy scores −0.61 for the men), because an unpenalised fit on 30 useless inputs costs log loss out of sample. A real profile that clears the line is therefore about a milli-log-loss better than noise of its size, but what matters is its own gain and range, which are the numbers in the table.

**Observed, on the scored matches.** The men's profiles are scored on 31,661 matches with odds, the women's on 17,304 (the women's box-score rows start in 2019).

**Observed. The men's lead by season, era and level** (`stageD_profile_results.csv`, the adjperf profile given the odds; the Tour Finals' 179 matches are directional only):

| | 2013 | 2014 | 2015 | 2016 | 2017 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| milli-log-loss better than the odds | −0.10 | −0.05 | +0.95 | −1.09 | −0.19 | +0.17 | +2.10 | +1.18 | +1.01 | +0.39 | +1.26 | +0.83 | +1.21 |

* By era: 2013–16 −0.07, 2017–19 −0.01, 2020–21 +1.49 (0.05 to 2.93), 2022–26 +0.92 (0.09 to 1.75). The gain is positive in every season from 2020 on and absent before; whether that is the 16-input walk-forward fit maturing, a change in the odds data, or chance, is not established here.
* By level: Grand Slams +0.29 (−0.84 to 1.43), 1000s +1.56 (0.35 to 2.76), 500s −0.48 (−1.91 to 0.94), 250s +0.35 (−0.56 to 1.26).
* With the points-won aggregates added: 2022–26 +1.13 (0.05 to 2.21), Grand Slams +1.57 (0.03 to 3.11), 1000s +2.04 (0.48 to 3.60), 250s −0.48.
* The women's profile: 2022–26 −0.02; seasons between −0.75 and +0.96 with no run of one sign.

## Part 1: the best inputs of both studies together (`stageD_rundown.py`)

**The models** (`stageD_catalog.json` lists each one's inputs per tour) and their scores (`stageD_ranking.csv`):

| Model (inputs) | Men, given Elo | Men 2022–26 | Men, given the odds | Women, given Elo | Women 2022–26 | Women, given the odds |
|---|---:|---:|---:|---:|---:|---:|
| the earlier study's three: ratings, points matchup 52 weeks, sets over 14 days (3) | 5.15 | 5.79 | 0.28 (−0.09 to 0.66) | 6.44 | 6.19 | 0.29 (−0.16 to 0.74) |
| ratings + 2-week adjperf of total points + load (3) | 5.80 | 6.63 | 0.26 | 7.54 | 6.73 | 0.22 |
| ratings + short-memory IOS matchup + load (3) | 5.51 | 6.37 | 0.27 | 7.65 | 6.89 | 0.29 |
| the three point-level measures (3) | 4.79 | 5.65 | 0.10 | 5.81 | 5.09 | −0.05 |
| Stages A–C only: BT, adjperf, IOS, credit, quality of wins, grinder (6) | 4.55 | 5.39 | −0.05 | 6.28 | 5.52 | −0.18 |
| everything (10) | 9.35 | 10.16 | 0.31 (−0.13 to 0.76) | 9.86 | 8.93 | 0.32 (−0.22 to 0.86) |
| everything + MESR (11) | 9.94 | 12.08 | 0.42 (−0.05 to 0.90) | 9.85 | 8.98 | 0.37 (−0.18 to 0.92) |

Given Stage A's Bradley–Terry rating instead of Elo, the three-input models add 5.9 to 7.2 (men) and 6.5 to 8.6 (women): BT holds less of them than Elo does.

**The ladder** (`stageD_summary.json`, `ladder`; main-tour matches with odds, 2022–2026: 12,352 men's and 11,467 women's):

| Forecast | Men | Women |
|---|---:|---:|
| Elo rating, as it is | 78% | 82% |
| Bradley–Terry rating, as it is | 77% | 76% |
| Elo refitted each season | 79% | 83% |
| Elo + the earlier study's three | 86% | 90% |
| Elo + everything | 90% | 92% |
| Bradley–Terry + everything | 90% | 92% |
| Bookmakers' closing prices | 100% | 100% |

**Inferred.** Elo plus everything gets nine tenths of the way to the bookmakers on the matches they price, and the last tenth is where the odds stay ahead. Closing the ladder is not beating the odds.

## What was built

| File | What it holds |
|---|---|
| `stageD_profile_features.parquet` (110.5 MB) | The pool with the profile inputs and the seven products |
| `stageD_profile_ranking.csv`, `_results.csv`, `_null_copies.csv`, `_results.json` | The harness's rundown of the ten profile models, both tours |
| `stageD_profile_catalog.json`, `stageD_profile_summary.json` | The models' inputs; the headline table and the family-wide lines |
| `stageD_features.parquet` | The pool with the inputs of part 1 |
| `stageD_ranking.csv`, `_results.csv`, `_null_copies.csv`, `_results.json` | The harness's rundown of the seven combination models |
| `stageD_catalog.json`, `stageD_summary.json` | The models' inputs; the headline table, the ladder, the family-wide lines |

Code: `src/eda/ufc_ideas/stageD_profile.py` (about 4 minutes with 5 workers), `stageD_rundown.py` (under a minute), `report_stageD.py`. Nothing was tuned in this stage; the tests of the inputs are the earlier stages' and the harness's (`test/ufc_ideas/test_common.py`).

## Limitations

* **Unpenalised fits with up to 37 inputs.** The walk-forward's early seasons fit many coefficients on few matches; the shuffled copies show what that costs (up to 0.8 milli-log-loss for the women's 37-input model), and the gains quoted are net of it. A ridge-penalised fit would likely raise every many-input model a little.
* **The inputs were chosen after the stages' results were read** (the strongest row of each family), so part 1's gains given Elo are optimistic by the usual selection; part 2's profiles were fixed before scoring (every statistic, no selection), except that the 2-week half-life is Stage B's tuned choice.
* **The closing line is the average of the books in tennis-data.co.uk**, not Pinnacle's; the earlier study's audit found Pinnacle's line slightly sharper on the men's side.
* **The women's rows start in 2019** and have about half the men's matches with odds, so their ranges are wide.

## Decisions for the owner

1. Pursue the men's individual-statistic profile against the odds, and in which order: the ridge fit, Pinnacle's line, by level and season, which statistics carry it?
2. Carry forward as the pre-match baseline: surface Elo, the ratings through the iid model and the 2-week adjperf profile (the suggestion), or everything?
3. Close the long-memory IOS ratings and the matchup products as market features?
