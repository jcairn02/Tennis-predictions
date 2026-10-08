# Stage 2: the shot-level features against Elo and the closing odds

**Status: built 2 Oct 2026, waiting for the owner's review.** A study stage, not a decision. The statistics are [Stage 1](stage1.md)'s; the Brief is in the [README](README.md).

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Improvements are in milli-log-loss, positive is better, as in the earlier studies: "given Elo" and "given the odds" are the shared harness's walk-forward gains over surface Elo alone and over the closing odds alone. The tables are generated from the stage's files (`data/studies/shot_level/stage2_tables.md`, by `src/eda/shot_level/stage2_tables.py`, from `stage2_ranking.csv`, `stage2_results.csv`, `stage2_clustered.csv`, `stage2_summary.json`, `stage2_feature_list.json`, `stage2_constants.json` and `stage2_leak_probe.json`).

## In short

* **Observed. 141 pre-match features.** They come from Stage 1's 25 statistics in three kinds and three memories:
  * the player's own rate, what opponents managed against the player, and the rate above what each opponent usually allowed;
  * a two-week half-life, the last 52 weeks, the career;

  plus the change in first-serve speed and a long-rally interaction. Each exists on 20,367–30,082 of the 31,683 men's and 32,178 women's matches with odds, and the leak probe is clean.
* **Observed. Against the closing odds, nothing.** None of the 280 single rows clears the family-wide line. The best are 0.06 milli-log-loss (men: the change in first-serve speed) and 0.08 (women: first serves out wide), and both ranges span zero.
* **Observed. The profiles do worse than the odds alone.**
  * the 10-input profiles: −0.06 to −0.75;
  * on top of the odds and the 16-input box-score profile of the UFC study's Stage D: −0.32 to −1.30.

  The shot-level statistics add nothing the box scores lack.
* **Observed. Against Elo, a little.** 6 men's and 8 women's rows clear the family-wide line, all under one milli-log-loss:
  * the men's serve-speed profile, 0.63, and first-serve speed alone, 0.36;
  * the women's opponent-adjusted winners per point, 0.37, and holds right after breaking, 0.37.

  In the full list of features tried, the best shot-level rows rank 82nd (men) and 116th (women) given Elo. The list's best combined models reach about 10.
* **Observed. One direction is worth a second look: the men's serve speed.** The three-input speed profile adds 0.24 to the odds in 2022–2026, with a week-clustered range of 0.07 to 0.41. Season by season it is positive in every year from 2022 and absent before, and the change in first-serve speed carries most of it. It is one row among about 300, so it is not established.
* **Inferred. Style is measurable, stable and independent of the odds, and it does not say who wins.** Stage 1 found the statistics to be traits. The odds and Elo explain a median 3% of a feature, so the information is new. But that new part does not predict the result beyond the odds, and adds little beyond Elo.
* **Inferred, for finding or buying data.** These results do not support buying more shot-level data of these kinds for pre-match markets. The features already exist on most matches with odds and add nothing there. Recent serve-speed data, as a fatigue or injury signal, is the one place they point.

## The features

**How they are built** (`src/eda/shot_level/stage2_features.py`; the UFC study's Stage B machinery, simplified):

* **Earlier matches only.** Each player's earlier matches are summed under the predictability diagnostic's time rule: earlier events, and earlier rounds of the same event.
* **Three memories:** a two-week half-life (the memory of the men's box-score lead), the last 52 weeks, and the career.
* **Surface.** Each match's count is centred on the tour's average on its surface, so a clay-heavy history is not read as a style.
* **Shrinkage.** The player's value is the shrunk average excess, with Stage 1's K.
* **Three kinds:**
  * **own:** the player's statistic;
  * **conceded:** what opponents did against the player, for statistics where that is a skill (how often opponents' serve-plus-one beat them, the winners they gave away);
  * **opponent-adjusted:** each earlier match's count is measured against what that opponent usually allowed, as of that match.
* **Scales.** Every feature is A − B; shares on the log-odds scale, speeds in km/h.
* **Constants fixed in advance.** No constant was tuned on results: the memories were set beforehand, and K comes from Stage 1.

| | Men | Women |
|---|---:|---:|
| Features | 141 | 141 |
| Matches with odds where a feature exists (fewest to most) | 22,402–30,082 | 20,367–29,644 |
| Evaluation matches where a feature exists (fewest to most) | 36,104–81,398 | 27,759–45,887 |
| Leak probe: cuts; features changed before or at a cut; leaky control changed at a cut | 4; 0; 8 | (both tours) |

* **Observed.** A match has a feature when both players have an earlier match carrying it in the memory, as in the earlier studies. With the Slam feeds, that is most main-tour matches.
* **Inferred.** For many players that history is their last Slams, months old. Under the two-week memory such players sit near the average, which is why those forms score little alone.

## The rundown

**How it was scored** (`src/eda/shot_level/stage2_rundown.py`). The ufc_ideas harness, unchanged: the earlier studies' pool and walk-forward fits, 20 shuffled copies per row, and the family-wide line. Results are ranked by the gain on the odds.

* **The profiles were fixed before any score was read:** the core statistics together in each kind and memory, then speed, the point sequence, style, and everything over 52 weeks.
* **Two more bases for the main profiles:**
  * **odds + box score:** the closing odds together with the UFC study's 16-input box-score profile (Stage D: adjperf on twelve statistics with the two-week memory, adjdef on four), for each tour;
  * **Elo + box score:** surface Elo with the same profile.

  Each base is itself a walk-forward forecast, so a gain over it is what shot data adds to box scores on the same matches.
* **Intervals clustered by calendar week**, the feature-alpha audit's method, are added for the profiles and the strongest rows (`stage2_summary.py`).

**Observed. Counts:**

| | Men | Women |
|---|---:|---:|
| Single rows scored | 140 | 140 |
| Profiles | 9 | 9 |
| Constant (no spread) | 3 | 6 |
| Positive given the odds | 8 | 14 |
| Clearing the family-wide line given the odds | 0 | 0 |
| Clearing the family-wide line given Elo | 6 | 8 |

**Observed. The best single rows given the odds** (one of each mirror pair: holds conceded after breaking are breaks back missed, and score alike):

| Tour | Feature | Memory | Alone | Given Elo (95% range) | Given the odds (95% range) | Matches with odds |
|---|---|---|---:|---:|---:|---:|
| Men | Change in first-serve speed, own | 2 weeks minus 52 weeks | 0.28 | -0.06 (-0.23 to 0.11) | 0.06 (-0.02 to 0.15) | 23,369 |
| Men | Serve points won under pressure (excess), own | 2-week half-life | -0.08 | -0.02 (-0.06 to 0.02) | 0.02 (-0.05 to 0.10) | 30,018 |
| Men | Errors per point, opponent-adjusted | 2-week half-life | 0.56 | -0.04 (-0.10 to 0.03) | 0.01 (-0.06 to 0.09) | 29,978 |
| Men | Net points won, own | career | 2.34 | -0.01 (-0.03 to 0.01) | 0.01 (-0.07 to 0.08) | 29,994 |
| Men | First serves in under pressure (excess), own | career | 0.42 | 0.04 (-0.05 to 0.14) | 0.01 (-0.21 to 0.23) | 29,936 |
| Women | First serves out wide, own | 2-week half-life | 1.78 | 0.25 (-0.00 to 0.49) | 0.08 (-0.09 to 0.26) | 25,594 |
| Women | Long-rally points won (9+ shots), opponent-adjusted | 52 weeks | 4.52 | -0.11 (-0.21 to -0.02) | 0.08 (-0.23 to 0.39) | 22,459 |
| Women | Winners per point, opponent-adjusted | 52 weeks | 6.71 | 0.37 (0.12 to 0.63) | 0.05 (-0.08 to 0.18) | 28,023 |
| Women | Long-rally points won (9+ shots), own | 52 weeks | 3.52 | -0.13 (-0.24 to -0.02) | 0.04 (-0.26 to 0.34) | 22,459 |
| Women | Holds right after breaking, opponent-adjusted | 52 weeks | 11.14 | 0.05 (-0.13 to 0.23) | 0.03 (-0.14 to 0.20) | 27,489 |

**Observed. The best single rows given Elo:**

| Tour | Feature | Memory | Alone | Given Elo (95% range) | Given the odds (95% range) | Matches with odds |
|---|---|---|---:|---:|---:|---:|
| Men | First-serve speed, own | 52 weeks | 3.78 | 0.36 (0.05 to 0.67) | -0.01 (-0.06 to 0.03) | 23,369 |
| Men | First-serve speed, own | 2-week half-life | 2.35 | 0.34 (0.15 to 0.53) | -0.03 (-0.10 to 0.04) | 27,355 |
| Men | Winners per point, opponent-adjusted | 52 weeks | 2.35 | 0.18 (-0.01 to 0.37) | -0.02 (-0.15 to 0.10) | 28,897 |
| Men | Winners / (winners + errors), conceded | 52 weeks | 4.08 | 0.16 (-0.01 to 0.32) | -0.16 (-0.25 to -0.07) | 28,897 |
| Men | Rally points won (5+ shots), own | 2-week half-life | 1.56 | 0.16 (-0.05 to 0.36) | -0.09 (-0.30 to 0.11) | 28,166 |
| Women | Winners per point, opponent-adjusted | 52 weeks | 6.71 | 0.37 (0.12 to 0.63) | 0.05 (-0.08 to 0.18) | 28,023 |
| Women | Holds right after breaking, opponent-adjusted | 2-week half-life | 3.54 | 0.37 (0.13 to 0.61) | -0.00 (-0.07 to 0.07) | 29,321 |
| Women | Breaks back right after being broken, conceded | 2-week half-life | 3.20 | 0.35 (0.11 to 0.60) | 0.01 (-0.05 to 0.07) | 29,321 |
| Women | Winners per point, own | 52 weeks | 3.81 | 0.27 (0.06 to 0.49) | 0.01 (-0.11 to 0.12) | 28,023 |
| Women | Winners / (winners + errors), conceded | career | 5.38 | 0.27 (0.02 to 0.52) | -0.07 (-0.17 to 0.02) | 29,644 |

**Observed. The profiles** (the harness's alone and given-Elo scores with its ranges; given the odds and the two box-score bases with week-clustered ranges, from `stage2_clustered.csv`):

| Tour | Profile | Inputs | Alone | Given Elo | Given the odds (week-clustered 95%) | Odds, 2022–2026 | Given the odds + box-score profile | Given Elo + box-score profile |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Men | speed (52 weeks) | 3 | 4.28 | 0.63 (0.33 to 0.94) | 0.07 (-0.07 to 0.20) | 0.24 (0.07 to 0.41) | – | – |
| Men | core def (52 weeks) | 8 | 12.08 | 0.46 (0.10 to 0.83) | -0.28 (-0.54 to -0.02) | -0.13 (-0.41 to 0.14) | – | – |
| Men | core off (52 weeks) | 10 | 7.10 | 0.02 (-0.32 to 0.37) | -0.36 (-0.72 to -0.00) | -0.31 (-0.69 to 0.07) | -0.90 (-1.46 to -0.34) | -0.11 (-0.49 to 0.28) |
| Men | core adj (52 weeks) | 10 | 8.79 | 0.12 (-0.24 to 0.48) | -0.37 (-0.77 to 0.02) | -0.35 (-0.75 to 0.05) | -1.30 (-1.96 to -0.65) | -0.19 (-0.65 to 0.26) |
| Men | style (52 weeks) | 6 | 4.02 | -0.37 (-0.66 to -0.07) | -0.38 (-0.87 to 0.11) | -0.31 (-0.61 to -0.00) | – | – |
| Men | sequence (52 weeks) | 6 | 12.85 | -0.08 (-0.40 to 0.24) | -0.60 (-0.96 to -0.24) | -0.38 (-0.75 to -0.01) | – | – |
| Men | core off (2-week half-life) | 10 | 1.86 | -0.11 (-0.43 to 0.21) | -0.66 (-1.13 to -0.20) | -0.31 (-0.78 to 0.16) | -1.12 (-1.65 to -0.59) | -0.41 (-0.66 to -0.17) |
| Men | core adj (2-week half-life) | 10 | 2.56 | -0.09 (-0.39 to 0.21) | -0.68 (-1.11 to -0.24) | -0.21 (-0.69 to 0.28) | -1.10 (-1.61 to -0.59) | -0.42 (-0.68 to -0.16) |
| Men | all off (52 weeks) | 25 | 30.02 | -1.12 (-2.45 to 0.20) | -3.24 (-4.50 to -1.97) | -1.04 (-1.76 to -0.31) | -4.31 (-5.86 to -2.76) | – |
| Women | core adj (52 weeks) | 10 | 14.16 | 0.24 (-0.33 to 0.82) | -0.06 (-0.62 to 0.51) | 0.29 (-0.38 to 0.97) | -0.32 (-1.18 to 0.55) | -0.07 (-0.79 to 0.65) |
| Women | speed (52 weeks) | 3 | 3.91 | 0.03 (-0.30 to 0.36) | -0.19 (-0.37 to -0.02) | -0.08 (-0.28 to 0.13) | – | – |
| Women | sequence (52 weeks) | 5 | 14.56 | -0.21 (-0.43 to 0.01) | -0.23 (-0.54 to 0.08) | -0.06 (-0.42 to 0.30) | – | – |
| Women | core off (52 weeks) | 10 | 11.33 | 0.17 (-0.35 to 0.69) | -0.25 (-0.79 to 0.28) | -0.03 (-0.67 to 0.61) | -0.73 (-1.63 to 0.16) | -0.26 (-1.02 to 0.49) |
| Women | core def (52 weeks) | 8 | 12.14 | -0.36 (-0.71 to -0.01) | -0.44 (-0.87 to -0.01) | -0.18 (-0.72 to 0.37) | – | – |
| Women | core adj (2-week half-life) | 10 | 3.57 | -0.27 (-0.68 to 0.15) | -0.68 (-1.07 to -0.29) | -0.07 (-0.50 to 0.36) | -1.06 (-1.78 to -0.33) | -0.81 (-1.32 to -0.29) |
| Women | core off (2-week half-life) | 10 | 2.90 | -0.24 (-0.68 to 0.20) | -0.75 (-1.23 to -0.26) | -0.13 (-0.62 to 0.36) | -1.22 (-2.05 to -0.38) | -0.94 (-1.56 to -0.31) |
| Women | style (52 weeks) | 6 | 4.10 | -0.89 (-1.44 to -0.34) | -0.97 (-1.51 to -0.43) | -0.41 (-0.77 to -0.04) | – | – |
| Women | all off (52 weeks) | 24 | 19.76 | -4.25 (-6.53 to -1.98) | -5.59 (-7.46 to -3.72) | -1.01 (-2.08 to 0.05) | -3.64 (-5.24 to -2.03) | – |

* **Observed.** The many-input profiles lose to the odds by about what their shuffled copies lose: their noise band. That is the cost of fitting 10 to 25 inputs with no penalty. A ridge fit would bring them toward zero, not above it, since no single input gains. *Confirmed in [Stage 3](stage3.md#d-the-profiles-without-the-fitting-cost): refitted with a ridge penalty, every profile lands at −0.16 to 0.09 given the odds.*
* **Observed. The men's speed profile, season by season given the odds** (`stage2_results.csv`):
  * 2014–2021: −0.70, 0.05, 0.04, −0.22, −0.13, −0.04, −0.07 (no men's odds file for 2018);
  * 2022–2026: 0.12, 0.10, 0.30, 0.37, 0.33.

  The change in first-serve speed alone gives 0.10, 0.06, 0.12, 0.33 and 0.05 in 2022–2026, and 0.14 over those seasons (range −0.00 to 0.28, week-clustered; `stage2_clustered.csv`).
* **Inferred.** Speed data is dense from 2022 (Infosys's tour-level files and the Slams; Stage 0). The pattern fits a recent drop in serve speed as a fatigue or injury signal that the closing odds price only in part. It is the one row worth a targeted, pre-registered test (below), not a finding.
* **Observed. The women's first serves out wide (two-week memory)** gives 0.31 in 2022–2026 (0.03 to 0.59), but its seasons swing: −0.31 in 2021, −0.22 in 2022, 0.37, 0.56, 0.28 and 0.62 after. **Inferred:** with about 300 rows tested, a few such ranges are expected by chance.

## The list of every feature tried

**Observed** (`stage2_feature_list.csv`: every row the shared harness has scored in the predictability diagnostic, the UFC study and this study, the same pool and fits):

| | Men | Women |
|---|---:|---:|
| Rows in the list (every study) | 507 | 504 |
| Of which shot-level | 150 | 150 |
| Best shot-level row given the odds: gain, rank | 0.07, 65 | 0.08, 30 |
| Best shot-level row given Elo: gain, rank | 0.63, 82 | 0.37, 116 |
| Top row of the list given the odds | 0.54 | 0.37 |
| Top row of the list given Elo | 9.94 | 9.86 |
| Shot-level rows in the top 50 given the odds | 0 | 3 |
| Shot-level rows in the top 50 given Elo | 0 | 0 |

## How independent of the market are they?

**Observed** (`stage2_summary.json`, `redundancy`: R² of each A − B feature on the log-odds of the closing odds and of surface Elo, on the matches with odds; no result is read):

| | Men | Women |
|---|---:|---:|
| Median share of a feature the odds and Elo explain (R²) | 0.03 | 0.03 |
| 90th percentile | 0.15 | 0.12 |
| Largest | 0.22 | 0.25 |

* **Inferred.** This answers the owner's question directly: the shot-level statistics are almost entirely independent of the odds and Elo. Holds after breaking and rally points won are the most market-like, at 0.22–0.25.
* **Inferred.** Independence is necessary for a gain on the odds, not sufficient. Here the independent part does not predict the result.

## What was built

| File | What it holds |
|---|---|
| `stage2_features.parquet` (103.5 MB) | The pool with every shot-level feature (A − B) |
| `stage2_frame.parquet` (134.5 MB) | The scored frame: the features, the Stage D box-score profile, and the two bases built from it |
| `stage2_constants.json` | The surface and tour averages, K per statistic and tour, the split-half details, the catalogue, the coverage |
| `stage2_leak_probe.json` | The probe: 4 cuts, no feature before or at a cut changed, the leaky control changed at the cut |
| `stage2_ranking.csv`, `_results.csv`, `_null_copies.csv`, `_results.json`, `stage2_catalog.json` | The harness's rundown of 300 rows, and every row's inputs |
| `stage2_clustered.csv`, `stage2_summary.json` | The week-clustered ranges; the best row per statistic, the counts, the redundancy |
| `stage2_feature_list.csv`, `.json` | Every scored row of every study, ranked |
| `stage1_tables.md`, `stage2_tables.md` | The write-ups' tables |

Code in `src/eda/shot_level/`: `stage2_features.py` (about 2½ minutes, and the probe 3½), `stage2_rundown.py` (about 4 minutes with 5 workers), `stage2_summary.py`, `stage2_list.py`, `stage2_tables.py` (seconds). Tests: `test/shot_level/test_stage2.py`. They cover the empirical-Bayes constant on simulated players, the three memories' time rule on a hand-made history, and that the walk-forward base ignores later seasons' results. 30 tests pass in the study.

## Limitations

* **The earlier studies' time rule and harness, not the feature-alpha audit's repaired ones.** That keeps these rows comparable with the list. The audit's rule counts only matches with a confirmed day and would score fewer of them (Stage 0). With no gain on the odds here, it is unlikely to change the reading. The speed lead should be retested under it.
* **Unpenalised profiles.** See above; the single rows carry the reading. Stage 3 measures the cost (about 0.5 milli-log-loss for 10 inputs) and refits the profiles with a penalty.
* **Many rows.** About 300 rows were scored, with no selection among memories or kinds. The family-wide line guards the multiple comparisons, and the single positive ranges are read with that in mind.
* **History is mostly Slams.** Recent shot-level history is thin for many players (Stage 0: 13-week coverage 34% for the men's rally lengths, 15% for the women's), so the two-week forms test recent form only where data is dense.
* **No ball tracking.** Court Vision is not decoded (Stage 1).

## Decisions for the owner

1. **Close the shot-level style statistics as pre-match features against the odds?** The suggestion is yes for rally length, endings, net play, placement, return depth, the wing and the point sequence: they add nothing to the odds, alone or together.
2. **Test the men's serve-speed change on its own, pre-registered?** One feature: the recent drop in first-serve speed against the player's own norm, scored under the audit's repaired rule from 2022. Forward data needs a source with serve speeds: the Slam feeds carry them; TDI's weekly capture does not.
3. **Data acquisition.** The suggestion is no purchase of shot-level data for pre-match use on this evidence. Whether point-level data helps in-play markets is a different question, not tested here; the common point table would serve it.
4. **Keep the point table and statistics as infrastructure?** They are rebuildable in a few minutes and tested.
