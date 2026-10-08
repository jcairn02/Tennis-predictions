# Stage C: strength of schedule, credit for old opponents, fatigue

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: built 2 Oct 2026; a study stage, not a decision.** The Brief, the scope and the rules are in the [README](README.md); the report section is `src/eda/ufc_ideas/report_stageC.py`. Nothing here chooses features, models, markets or a roadmap.

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/ufc_ideas/`: `stageC_summary.json` (which folds in `stageC_sos_part.json` and `stageC_fatigue_part.json`), `stageC_ranking.csv`, `stageC_results.csv` (eras, levels, seasons), `stageC_ratings_ranking.csv` and `stageC_fatigue_players.csv`.

## In short

The owner asked for two UFC ideas in tennis, strength of schedule and the retrospective credit for old opponents, and whether players fade as matches get long. Each was built for the earlier study's pool of 255,123 matches and scored by its harness, beside four of its Stage 4 rows. Milli-log-loss "better" means better than the baseline alone, over all scored seasons.

* **Observed. Strength of schedule does not help the men and helps the women a little.**
  * Men: every schedule row scores worse given Elo, by up to 2.55 milli-log-loss. The one exception, results above Elo's expectation against strong opponents, is level (0.00).
  * Women: the strength of the opponents a player beat (the UFC's "quality of wins") is 0.95 better (95% range 0.21 to 1.69), and 0.60 better in 2022–2026.
  * **Inferred:** the men's losses repeat the earlier study's warm-up artifact (its Stage 4, section 6). Strength proxies are over-weighted in the first walk-forward fits, while Elo is still young. The men's weight on the schedule falls from 0.635 per standard deviation in the 2013 fit to 0.135 in the 2026 fit.
* **Observed. The retrospective credit helps a little, through the opponents a player lost to.**
  * The old opponents' Elo now minus at the meeting, over the losses of the last 52 weeks, is 0.16 better given Elo for the men (0.01 to 0.30) and 0.41 for the women (0.22 to 0.60).
  * Taking out the meeting's own Elo change, as the UFC rule does, gives 0.14 (men) and 0.47 (women).
  * The same credit over the opponents a player beat adds nothing: 0.02 worse (men) and 0.11 worse (women).
* **Observed. Fatigue: no sign.** The late-match decline from the Grand Slam point-by-point files scores 0.03 worse given Elo for the men and 0.10 worse for the women, and its products with best of five, the expected length and recent load do no better. The one fatigue-family finding, the "grinder" contrast over the last 52 weeks (0.52 better for the men, 0.51 for the women), takes a negative sign; **inferred:** it measures recent dominance in lopsided matches, not stamina.
* **Observed. Given the closing odds, nothing.** No new row clears the family-wide line given the market; the largest gain is 0.18 (women, the opponents' Stage 3 ratings; −0.18 to 0.54).
* **Observed. The fatigue measures are barely traits.**
  * The late decline's split-half reliability is low. For the men it is 0.09 at most (10 matches per half, against 0.02 under pure luck), and its spread between players equals the pure-luck replays'. The women's reaches 0.17–0.19 at 5–8 matches per half against −0.03 to 0.00 under luck, on fewer than 300 players (directional).
  * The grinder's reliability is about twice its replay's (men 0.21 against 0.09 at 60 matches per half). But its correlation with player strength (−0.31 men, −0.38 women) is matched by the replays (−0.30 and −0.29; −0.33 and −0.38): mostly selection.
* **Observed. The checks pass.**
  * Two probes cut by date, event and round: 0 of 198,200 protected match-cuts moved; deliberately leaky controls moved at 105.
  * The four reference rows reproduce Stage 4 to 9.4e-17.
  * Elo's update is reproduced from Stage 1's stored ratings to 0.0002 points.
* **Problems found in the earlier study's data** (reported, not fixed): 287 evaluation-level events dated on another weekday than Monday, which the time rule treats as weeks of their own; 123 matches with implausible minutes.
* **For the owner:** six decisions, [at the end](#decisions-for-the-owner).

## What was built

| File | What it holds |
|---|---|
| `stageC_features.parquet` (49.1 MB) | The pool (255,123 matches; 182,440 men's, 72,683 women's), every Stage C column, the four reference columns, `p_ratings` and surface Elo's log-odds as a column |
| `stageC_ranking.csv`, `stageC_results.csv`, `stageC_null_copies.csv`, `stageC_results.json` | The harness's rundown: 48 rows (21 new and 4 reference per tour for the men, 19 and 4 for the women) |
| `stageC_ratings_ranking.csv`, `_results.csv`, `_null_copies.csv`, `_results.json` | The given-ratings rundown: 10 rows |
| `stageC_catalog.json` | One entry per scored column (26): id, name, family, description, constants |
| `stageC_summary.json` | Everything quoted here: constants and tuning grids, reliability (real and pure luck), selection diagnostics, probes, checks, coverage, timings |
| `stageC_fatigue_players.csv` | Per player (11,492): the late-decline and grinder traits at the end of the data, raw and shrunk, with their samples |
| `stageC_sos_part.*`, `stageC_fatigue_part.*` | The two feature scripts' outputs, which `stageC_rundown.py` folds together |

Code in `src/eda/ufc_ideas/`; the runtimes are the last full runs (`stageC_summary.json`, `timings`):

* `stageC_sos.py`: families 1 and 2, the tuning, the checks and the probe; 312 seconds.
* `stageC_fatigue.py`: family 3, its reliability, the replays and the probe; 116 seconds.
* `stageC_rundown.py`: the harness tasks, the given-ratings rundown, the catalog and the summary; 121 seconds with 5 workers in the last full run. `--summary-only` rebuilds the catalog and summary without rescoring.
* `report_stageC.py`: the report section.

Tests: `test/ufc_ideas/test_stageC.py`, 15 tests, all passing (`./python.sh -m pytest test/ufc_ideas/test_stageC.py`).

## Terms used here

**Tennis.**

* **Set, best of three or five.** A match is won by taking two sets of three, or three of five. In the pool only the men's Grand Slam main draws, the men's last qualifying round at Wimbledon and the Next Gen ATP Finals (five short sets) are best of five.
* **Serve point.** Every point has a server. A serve point won is a point won on one's own serve.
* **Grand Slams; main tour.** The four majors; main tour means the Grand Slam to 250 main draws, the only matches with closing odds.
* **Tennis week.** An event's main-draw week, Monday to Sunday. The data dates each event by one day, usually the Monday of that week; 287 evaluation-level events carry another weekday.

**From the UFC project.**

* **Strength of schedule (SoS).** How strong a player's opponents were: here the mean pre-match strength of the opponents met in the last 52 weeks. **Quality of wins** is the same over the opponents beaten.
* **Phantom prior.** K imaginary opponents of the tour's typical strength mixed into a player's mean: (sum + K × typical) / (n + K). A player with few matches sits near typical.
* **Retrospective credit, revaluation.** Credit for having met opponents who turned out to be good: an old opponent's rating now minus at the meeting. The UFC rule uses only the opponent's later bouts, strictly between the meeting and the match being predicted, and leaves out rematches.

**This study.**

* **Log loss, milli-log-loss.** Minus the log of the probability given to the winner, averaged; a coin scores 0.693; one milli-log-loss is 0.001. "Better" means a lower log loss than the baseline alone.
* **Given Elo, given the market.** The feature added to surface Elo (Stage 1's, retirements counted), or to the closing odds, in a logistic regression without an intercept fitted walk-forward by season, against the baseline alone.
* **Null band, family-wide line, finding.** Twenty copies of each feature shuffled within each season give its band. The line is the best standardised score any copy reaches across all the run's rows. A **finding** clears the line given Elo and is better than Elo in three eras or more; **possible** is above its own band only. These are the earlier study's rules.
* **Reliability (split-half).** Each player's matches are split into two random halves; the correlation, across players, of a measure in one half with the other. Near 0 means luck.
* **Pure-luck replay.** The same matches played again point by point with every point an independent draw at the day's de-noised serve rates (Stage 2's replay). It keeps the players, their strength and the formats, and has no fatigue and no momentum by construction.
* **Effective points.** For a measure that compares rates, the number of points a match's measure is worth: its chance variance is about p(1 − p) divided by it.
* **Late decline.** A player's serve points won in the third set onward minus in the first two, minus the opponent's same change. Positive: the player held up better than the opponent.
* **Grinder.** A player's points won above the Stage 3 ratings' expectation in long matches minus in short ones.

## 1. Strength of schedule

**Design** (`stageC_sos.py`).

* **The strengths.** For every earlier match of a player, the opponent's pre-match strength at that meeting. History is every singles level from 2010, completed or retired matches, as in the earlier study.
  * (a) Surface Elo: Stage 1's blend of overall and surface rating (weights 0.30 men, 0.25 women), on the log-odds scale (ln 10 / 400 per Elo point).
  * (b) The Stage 3 serve rating plus return rating.
  * (c) Stage A's Bradley–Terry rating: **skipped**. `data/studies/ufc_ideas/stageA_bt.parquet` did not exist when `stageC_sos.py` last ran (2 Oct 2026); the script reads it if present (decision 6).
* **The rows** (A − B), the last 52 weeks unless named:
  * opponents' surface Elo, also decayed (52-week half-life);
  * opponents' serve plus return ratings;
  * opponents beaten (quality of wins) and opponents lost to;
  * results above Elo's expectation, the sum of (won − Elo's pre-match probability) shrunk by (n + K);
  * the same against strong opponents only: blended Elo above the tour's 2010–2018 main-tour median.
* **Priors and lines** (`priors`). The tour's mean opponent strength over the played player-matches of 2010–2018: 9.77 (men) and 9.83 (women) on the log-odds scale for Elo, −0.097 and −0.071 for the rating sum. The strong-opponent line is 2,097.8 (men) and 2,101.2 (women) Elo points, the median over 47,210 and 44,396 main-tour player-matches.
* **An empty subset takes the prior.** A player with no win in the window gets the tour's typical opponent as their quality of wins: the limit of the shrunk mean as its count goes to zero. A row exists where both players have a played match in the window.
* **The time rule.** Every sum goes through the earlier study's as-of helpers (`common.asof_sums`, Stage 3's `lookback_sums` and `sums_before`): earlier events and earlier rounds of the same event, never the match itself, its own round or another event of its week. The tests check it against a row-by-row reading on a hand-made history with knockout events, a round robin and a second event in the same week.

**Results** (milli-log-loss; negative is worse; the full tables are in [section 5](#5-the-rundown)):

| Row | Men, given Elo (95% range) | 2022–26 | Women, given Elo (95% range) | 2022–26 | Reading, men / women |
|---|---:|---:|---:|---:|---|
| Quality of wins | −1.14 (−1.62 to −0.66) | −0.82 | 0.95 (0.21 to 1.69) | 0.60 | worse / finding |
| Opponents' surface Elo | −1.80 (−2.34 to −1.26) | −1.51 | 0.45 (−0.40 to 1.31) | 0.40 | worse / finding |
| Opponents lost to | −1.38 (−1.85 to −0.91) | −1.54 | 0.25 (−0.48 to 0.98) | 0.31 | worse / finding |
| Opponents' surface Elo, decayed | −2.55 (−3.03 to −2.06) | −1.54 | −0.97 (−1.84 to −0.09) | −0.31 | worse / worse |
| Opponents' serve + return ratings | −2.33 (−2.91 to −1.74) | −1.48 | −0.09 (−0.78 to 0.61), from 2019 | 0.24 | worse / worse |
| Results above Elo's expectation | −0.43 (−0.64 to −0.22) | 0.24 | −0.47 (−0.75 to −0.19) | 0.26 | worse / worse |
| … against strong opponents | 0.00 (−0.04 to 0.04) | 0.05 | −0.01 (−0.07 to 0.06) | 0.03 | possible / no sign |
| *Reference: level played over 52 weeks (Stage 4)* | −2.48 (−2.91 to −2.06) | −1.36 | −2.09 (−2.81 to −1.38) | −1.11 | worse / worse |

* **Observed.** Alone, the five opponent-strength rows are strong predictors: 42.74 to 50.20 better than a coin for the men, 33.29 to 65.24 for the women. They measure strength: strong players meet strong opponents.
* **Observed. The men's walk-forward fits** (`stageC_results.csv`, season rows), for the opponents' surface Elo:
  * the 2013 fit weights it 0.635 per standard deviation beside Elo's log-odds at 0.50; the 2026 fit 0.135 beside 0.79;
  * its season gains run +3.66 (2013), −5.53 (2017), −0.21 (2026).
  * Stage 4's reference row, the level played over 52 weeks, follows the same course: 0.392 to 0.073, +4.34 to −0.64.
* **Inferred.** The men's schedule rows behave as the earlier study's strength proxies do (its Stage 4, section 6): fitted heavily while Elo warms up from 1,500, then worse than Elo alone in most seasons. Even in 2022–2026 they stay worse (−0.82 to −1.54).
* **Observed. For the women**, three Elo-based schedule rows are findings, with positive signs: +0.135 per standard deviation for quality of wins, +0.131 for the opponents' Elo. The opponents' Elo row's 95% range crosses zero (−0.40 to 1.31).
  * **Inferred:** a feature this correlated with strength moves predictions a lot, so its per-match differences vary widely, while its shuffled copies barely move; the family-wide line is then easy to clear. Of the three, quality of wins is the one whose range excludes zero.
* **Observed. Results above Elo's expectation** score worse for both tours over all seasons, and better in 2022–2026 (0.24 men, 0.26 women): the same pattern as Stage 4's ranking-type rows.

## 2. Retrospective credit for old opponents

**Design** (`stageC_sos.py`). For each of a player's matches of the last 52 weeks under the time rule (an encounter with opponent O), O's strength now minus then, on the log-odds scale:

* **Then.** O's blended surface Elo before the meeting.
* **Now.** O's latest pre-match Elo at a match of an earlier tennis week than the match being predicted, read on the meeting's surface.
  * The overall part comes from O's latest such row; the surface part from O's latest such row on that surface.
  * Each part counts only if that row comes after the meeting under Elo's own rule (it "sees" the meeting). Otherwise O has no later evidence, and that part contributes zero.
* **Rematches.** A later meeting of the same two players before the reading is taken out of "now": its own Elo update for O, k(n) × (result − expectation) with Stage 1's frozen constants, is subtracted. **Observed:** 3,027,212 of the 27,607,816 encounter readings had one.
* **Later only** (the `_later` rows). The meeting's own Elo update for O is also subtracted.
  * A later rating mechanically contains the meeting itself: O lost points to the player when the player won, and gained them when the player lost. Without this, every win is debited and every loss credited.
  * This is the UFC rule (`retrospective_sos.py`: later bouts strictly between the meeting and the match, rematches excluded). The rows as specified keep the meeting's own change.
* **The rows.** Averaged over all encounters, those won and those lost, shrunk by (n + K) toward zero; A − B.
* **Size** (`pairs`). 27,607,816 (player-match, encounter) readings, 54.1 per pool player-match, 26,051,035 of them with later evidence. They are enumerated by searches over sorted per-player arrays, in chunks: no per-row look-back.
* **Tennis weeks.** Stage 0 dates 287 evaluation-level events on another weekday than Monday (see [problems](#problems-found-in-the-earlier-studys-data-or-code-reported-not-fixed)). An earlier date is therefore not always an earlier week, and the Brief's "never a rating that includes the pool match's week" needs weeks, not dates.
  * "Now" reads only rows dated before the Sunday that starts the pool match's tennis week. An event dated on a Sunday belongs to the following Monday's week.
  * **Observed:** an earlier-date rule would have read 299,480 readings (1.1%) from a row of the pool match's own tennis week.

**Checks** (`checks`).

* **Stage 1's Elo update reproduced.** Where a player's next match is in a later week with nothing else in between, the stored ratings differ by the computed update: 413,644 cases, largest error 0.00024 Elo points (float32 storage), median update 13.4 points.
* **A row-by-row reading.** The vectorised sums equal a row-by-row reading on 300 random pool player-matches: 0 count mismatches, largest difference 8.6e-12.
* **The tests** (hand-made histories) check:
  * the rule's three cases;
  * that "now" never reads the pool match's week, including the Monday-and-Wednesday and Sunday-and-Monday date cases;
  * the rematch and later-only arithmetic;
  * Elo's update against Stage 1's own pass.

**Results:**

| Row | Men, given Elo (95% range) | 2019–26 | 2022–26 | Women, given Elo (95% range) | 2019–26 | 2022–26 | Reading, men / women |
|---|---:|---:|---:|---:|---:|---:|---|
| Opponents lost to | 0.16 (0.01 to 0.30) | 0.19 | 0.07 | 0.41 (0.22 to 0.60) | 0.38 | 0.32 | finding / finding |
| Opponents lost to, later only | 0.14 (−0.01 to 0.30) | 0.01 | −0.12 | 0.47 (0.25 to 0.69) | 0.32 | 0.24 | finding / finding |
| All opponents, later only | 0.15 (−0.02 to 0.31) | 0.07 | −0.06 | 0.13 (−0.09 to 0.35) | 0.16 | −0.01 | finding / possible |
| All opponents | 0.10 (−0.10 to 0.31) | −0.31 | −0.39 | 0.34 (0.07 to 0.60) | 0.12 | 0.10 | possible / finding |
| Opponents beaten, later only | 0.01 (−0.12 to 0.14) | −0.04 | −0.11 | −0.03 (−0.18 to 0.13) | −0.03 | −0.14 | possible / worse |
| Opponents beaten | −0.02 (−0.14 to 0.10) | −0.12 | −0.13 | −0.11 (−0.29 to 0.07) | −0.17 | −0.21 | worse / worse |

* **Observed.** The credit over the losses gains in every era for the women: 0.44, 0.27, 0.94 and 0.32 for 2013–16 to 2022–26 (later only: 0.73, 0.28, 1.06, 0.24). For the men, 2013–16 is the exception: −0.03, then 0.35, 0.54 and 0.07.
* **Observed.** The signs are positive: +0.055 per standard deviation (men) and +0.073 (women) for the opponents lost to. A player whose recent conquerors have since risen wins more often than Elo says.
* **Observed.** The men's gains fade by 2022–2026, and the later-only ones by 2019–2026; the women's hold (0.24 to 0.38).
* **Inferred.** Elo charges a loss to a lower-rated opponent as an upset. When that opponent was in fact rising, the charge was too large, and the credit undoes part of it. The same correction on wins adds nothing.
  * One possible reason, not tested: established players lose to rising ones more often than they beat them.
* **Observed.** Given the market, the credit adds 0.11 at most (women, all opponents, 0.00 to 0.21) and clears no line.

## 3. Fatigue

### 3.1 Late-match decline (Grand Slam point by point)

**Design** (`stageC_fatigue.py`).

* **The data.** Stage 2's validated point sequences: 9,948 main-draw matches of 2011–2024, men best of five, women best of three. The players are linked to Stage 0 ids within each Slam's draw, as `stage4_features.pbp_history` does (`pbp_coverage`):
  * men: 9,947 of 9,970 player-matches, 514 players;
  * women: 9,758 of 9,926, 479 players.
* **The measure, per match.** d = (own serve-point win rate from the third set on − in the first two sets) − (the opponent's same change). Player 2's d is minus player 1's, so its mean over all player-matches is exactly zero.
* **Its weight.** The effective points u = 1 / (1/n own late + 1/n own early + 1/n opponent late + 1/n opponent early), 13.0 (men) and 10.1 (women) per match on average.
* **Where it exists.** In every men's match (9,947), but in only 3,031 women's: their third set is played only in three-set matches.
* **Variants, for the reliability only.**
  * The first 150 points against the rest: 8,786 men's and 3,183 women's player-matches.
  * For the men, the first two sets against the third alone. The third set is always played in best of five, so no match is selected by how it went.
  * The files hold no time stamps, so "after 2 hours" could not be built.
* **The trait** before a match: the u-weighted mean of d over earlier Slams (dated strictly before), shrunk toward zero. K comes from Stage 3's empirical-Bayes method (`stage3_traits.eb_constants`) on player-seasons of 2011–2018, or on careers where seasons show no spread.
* **Features (A − B):**
  * `late_decline|career`;
  * × 1[best of five] (men only; the source's recorded format, not read from the score);
  * × closeness = 1 − 2|p − 0.5|, with p the Stage 3 ratings' probability through the iid model (`expit(rating_matchup|single)`). It is 1 for an even match, which is expected to run long, and 0 for a certain one.

**A selection problem, measured.** The late segment ends when the match does, so the eventual winner's d is positive by construction. The pure-luck replays measure how much (`selection`; the match winner's mean d, points won per point):

| Measure | Men, real | Men, pure luck | Women, real | Women, pure luck |
|---|---:|---:|---:|---:|
| First two sets against the third onward | 0.040 | 0.024 | 0.141 | 0.118 |
| Against the third set alone (men) | 0.014 | 0.001 | – | – |
| First 150 points against the rest | 0.063 | 0.043 | 0.137 | 0.112 |

* **Observed.** Most of the winner's late edge is selection: 0.024 of the men's 0.040, 0.118 of the women's 0.141.
* **Observed.** Real winners still gain more late than pure luck gives, on every variant, including the third set alone, where nothing is selected (0.014 against 0.001).
* **Inferred.** Within-match level shifts exist that the iid model lacks: the eventual winner's level rises relative to the loser's late in matches. That could be fatigue, momentum or tactics. It is a within-match signal, which a pre-match feature can only use if it is a stable trait of players (next).

**Is it a trait?** (`reliability_decline`; split-half correlation; luck is the mean of three replays.)

| Matches per half | Men (players) | Men, pure luck | Women (players) | Women, pure luck |
|---:|---:|---:|---:|---:|
| 2 | 0.066 (342) | 0.005 | 0.039 (200) | 0.019 |
| 5 | 0.036 (237) | 0.039 | 0.174 (118) | −0.013 |
| 6 | 0.056 (217) | 0.029 | 0.190 (99) | 0.003 |
| 8 | 0.060 (180) | 0.020 | 0.187 (70) | −0.029 |
| 10 | 0.088 (154) | 0.016 | 0.144 (47) | 0.024 |
| 20 | 0.029 (72) | 0.044 | – | – |

* **Observed.** Every row except the men's at 2 matches rests on fewer than 300 players: directional only.
  * The men's correlations stay below 0.09. At 5 and at 20 matches per half they are at or below the replays' (0.036 against 0.039; 0.029 against 0.044).
  * The men's third-set-alone variant reaches 0.126 at 12 matches per half (133 players), against 0.009 under luck.
  * The women's are higher, at 0.17–0.19, on 70–118 players.
* **Observed. Empirical Bayes** (`K_decline`). For the men, the season-level spread between players gives K = 944 effective points (bootstrap 351 to no spread). The replays give 931, 1,162 and no spread: the same as real. For the women, seasons show no spread; careers give K = 808 (281 to no spread), and the replays no spread, 468 and no spread.
* **Observed. Strength.** Among players with 20+ matches, the raw trait correlates with the player's mean Elo at 0.21 (men, 154 players) and 0.29 (women, 47). The replays give 0.06, 0.28 and 0.17; and 0.12, 0.40 and 0.28.
* **Observed. As built,** the median reliability of the shrunk trait among players with 20+ matches is 0.35 (men) and 0.24 (women) (`players`).
  * Players with 30+ matches at the extremes (`stageC_fatigue_players.csv`): Gilles Simon +0.035, Gael Monfils +0.026, Kei Nishikori +0.022; Marcel Granollers −0.020. Serena Williams +0.029, Simona Halep +0.021; Sloane Stephens −0.006.
* **Inferred.** For the men, late decline is not a trait the data can tell from luck plus strength. For the women it may be, tentatively: a few dozen players, three-set matches only.

**Results:** no sign.

| Row | Men, given Elo (95% range) | Women, given Elo (95% range) | Men / women |
|---|---:|---:|---|
| Late decline, career | −0.03 (−0.10 to 0.04) | −0.10 (−0.42 to 0.22) | no sign / worse |
| × best of five (men) | 0.02 (−0.17 to 0.21) | – | no sign |
| × expected length (closeness) | −0.03 (−0.12 to 0.06) | −0.10 (−0.44 to 0.23) | no sign / no sign |
| Sets over 14 days × late decline | −0.04 (−0.11 to 0.03) | −0.03 (−0.24 to 0.19) | no sign / no sign |
| Minutes over 14 days × late decline | −0.02 (−0.08 to 0.05) | −0.06 (−0.27 to 0.16) | no sign / no sign |

Coverage: 49,792 of the men's 155,130 evaluation matches, and 15,636 of the women's 34,645 of 2019–2026 (both players need a Slam in the files).

### 3.2 The grinder (box scores and minutes)

**Design.**

* **Per player-match** (completed, standard format, a box score, minutes): the residual points r = total points won − (serve points × p_serve_own + return points × (1 − p_serve_opp)), over u = the points played. That is the iid points share at the Stage 3 ratings' pre-match expectation.
* **Long.** Minutes per set above the tour's 75th percentile of 2010–2018 (`long_line_minutes_per_set`): 46.0 (men, over 81,821 matches) and 46.5 (women, 12,649; the women's minutes are almost absent before 2016).
* **The contrast.** G = R_long / U_long − R_short / U_short. It is shrunk as a contrast: G × U / (U + K), with U = 1 / (1 / U_long + 1 / U_short).
* **Minutes read.** Only those implying 15 to 120 seconds per point (`grinder_rows`): 66 men's and 57 women's matches, of 190,825 and 68,704 with minutes and a box score, fall outside.
* **The constant** (`K_grinder`).
  * **Observed.** Player-seasons show no spread on either tour: the true variance is estimated below zero.
  * Careers (2010–2018) give K = 14,690 effective points (men; bootstrap 8,523 to 30,854) and 10,098 (women; 5,087 to no spread). These are used, a departure from Stage 3's season windows, stated here.
  * The iid replays show no spread on either window.
* **Features (A − B):** career; last 52 weeks; career × best of five (men).

**Is it a trait?** The replay plays every match again under the iid model at the day's de-noised rates. "Long" is read there as points per set above the replay's own 75th percentile of 2010–2018: 69.0 and 69.3 in the men's two replays, 69.0 in the women's.

| Matches per half | Men (players) | Men, replay | Women (players) | Women, replay |
|---:|---:|---:|---:|---:|
| 10 | 0.100 (2,045) | 0.051 | 0.128 (1,227) | 0.059 |
| 30 | 0.125 (1,393) | 0.060 | 0.275 (643) | 0.087 |
| 60 | 0.210 (889) | 0.086 | 0.277 (293, directional) | 0.105 |

* **Observed.** The real reliability is about twice the replay's on both tours.
* **Observed. Strength explains the trait's direction.** Among players with 100+ matches, G correlates with mean Elo at −0.31 (men, 1,023 players) and −0.38 (women, 351). The replays give −0.30 and −0.29; and −0.33 and −0.38 (`strength_correlation`).
  * The most negative shrunk values (200+ matches) are the strongest players: Rafael Nadal −0.025, Novak Djokovic −0.019, Daniil Medvedev −0.017; Iga Swiatek −0.027, Elise Mertens −0.016, Aryna Sabalenka −0.016.
* **Inferred.** A favourite's long matches are the ones in which they under-performed (long matches are close ones), so the best players look like "non-grinders" by selection, as the replays reproduce. What exceeds the replay may be style, such as clay-court players whose matches run long and who beat their all-surface rating on clay. It is not shown to be stamina.

**Results:**

| Row | Men, given Elo (95% range) | 2022–26 | Women, given Elo (95% range) | 2022–26 | Men / women |
|---|---:|---:|---:|---:|---|
| Grinder, last 52 weeks | 0.52 (0.34 to 0.71) | 0.95 | 0.51 (0.22 to 0.79) | 0.55 | finding / finding |
| Grinder, career | −0.19 (−0.39 to 0.00) | 0.06 | −0.11 (−0.21 to −0.01) | 0.00 | worse / no sign |
| Grinder × best of five (men) | −0.01 (−0.11 to 0.09) | 0.07 | – | – | no sign |

* **Observed.** The 52-week grinder takes negative signs (−0.076 and −0.073 per standard deviation). A player whose recent short matches went better than expected, relative to the long ones, wins more often than Elo says. Its gain grows over the eras for the men: −0.29, 0.47, 0.86, 0.95.
* **Inferred.** Short matches are lopsided ones. A high residual there is a margin of victory, so the 52-week grinder is close to the earlier study's margin features (the games-weighted Elo), not to fatigue.

### 3.3 Load × fatigue

Stage 4 found that more sets over the last 14 days means a player wins more often than Elo says: a player still in a draw has played more. The refinement multiplies each player's 14-day load (log of one plus sets, or minutes) by their late-decline trait. **Observed:** no sign on either tour (the table in 3.1). **Check:** the per-player 14-day loads reproduce Stage 4's `sets_14d|single` and `minutes_14d|single` exactly (the same missing values; largest difference 2.4e-7, float32 storage).

## 4. The constants chosen

Phantom opponents (families 1 and 2), chosen per row and tour from {0, 2, 5, 10, 20} by the in-sample gain given Elo on the evaluation matches of 2013–2018 (63,370 men's and 25,550 women's for the 52-week rows), then frozen (`K`, `tuning_grid`):

| Row | Men | Women | Row | Men | Women |
|---|---:|---:|---|---:|---:|
| Opponents' surface Elo | 20 | 20 | All opponents (credit) | 5 | 20 |
| … decayed | 0 | 20 | Opponents beaten | 0 | 5 |
| Serve + return ratings | 20 | 20 | Opponents lost to | 20 | 20 |
| Quality of wins | 20 | 5 | All, later only | 2 | 20 |
| Opponents lost to | 5 | 20 | Beaten, later only | 2 | 5 |
| Results above expectation | 20 | 0 | Lost to, later only | 20 | 20 |
| … against strong opponents | 2 | 5 | | | |

* **Observed.** 14 of the 26 choices are the grid's largest value (20) and 3 its smallest (0) (`derived.K_choices`). Several in-sample gains still rise at 20: the women's credit for losses goes 0.023, 0.062, 0.105, 0.154, 0.212 from K = 0 to 20.
  * **Inferred:** more shrinkage might help those rows. The grid is the one the brief set.
* **Fatigue constants** (effective points): late decline 944 (men, seasons) and 808 (women, careers); grinder 14,690 and 10,098 (careers).
* **Lines:** the strong-opponent line (section 1) and the long-match line (section 3.2).

## 5. The rundown

Every row, both tours; milli-log-loss better than the baseline alone (negative: worse); "band" is the best of the 20 shuffled copies; "line" marks a row above the family-wide line. Lines: given Elo 3.69 (men) and 6.80 (women) standard deviations of the copies; given the market 6.01 and 5.18. Readings of the new rows (`derived`): men 4 findings, 3 possible, 6 no sign, 8 worse; women 7, 1, 5, 6.

**Men** (155,130 evaluation matches; the rows exist on 153,565 unless noted):

| Row | Alone | Given Elo (95% range) | Band | Line | Eras + | 2022–26 | Given market (95% range) | Band | Reading |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| *Strength of schedule* | | | | | | | | | |
| Results above expectation, strong opponents | −0.02 | 0.00 (−0.04 to 0.04) | −0.00 | | 2 of 4 | 0.05 | 0.01 (−0.16 to 0.17) | −0.00 | possible |
| Results above expectation | −0.64 | −0.43 (−0.64 to −0.22) | 0.00 | | 2 of 4 | 0.24 | −0.04 (−0.10 to 0.01) | 0.00 | worse |
| Quality of wins | 43.41 | −1.14 (−1.62 to −0.66) | 0.00 | | 1 of 4 | −0.82 | −0.04 (−0.21 to 0.13) | 0.01 | worse |
| Opponents lost to | 50.20 | −1.38 (−1.85 to −0.91) | 0.01 | | 1 of 4 | −1.54 | 0.03 (−0.03 to 0.10) | 0.02 | worse |
| Opponents' surface Elo | 45.22 | −1.80 (−2.34 to −1.26) | 0.00 | | 0 of 4 | −1.51 | 0.02 (−0.10 to 0.14) | 0.03 | worse |
| Opponents' ratings | 42.74 | −2.33 (−2.91 to −1.74) | 0.00 | | 0 of 4 | −1.48 | 0.05 (−0.06 to 0.15) | 0.03 | worse |
| Opponents' surface Elo, decayed (154,403) | 45.65 | −2.55 (−3.03 to −2.06) | 0.04 | | 0 of 4 | −1.54 | 0.06 (−0.05 to 0.17) | 0.06 | worse |
| *Retrospective credit* | | | | | | | | | |
| Lost to | −0.28 | 0.16 (0.01 to 0.30) | 0.01 | yes | 3 of 4 | 0.07 | −0.03 (−0.07 to 0.01) | 0.03 | finding |
| All, later only | −0.52 | 0.15 (−0.02 to 0.31) | 0.01 | yes | 3 of 4 | −0.06 | −0.03 (−0.09 to 0.04) | 0.03 | finding |
| Lost to, later only | −0.17 | 0.14 (−0.01 to 0.30) | 0.01 | yes | 3 of 4 | −0.12 | −0.02 (−0.06 to 0.02) | 0.01 | finding |
| All opponents | −0.31 | 0.10 (−0.10 to 0.31) | 0.00 | yes | 2 of 4 | −0.39 | −0.02 (−0.09 to 0.04) | 0.03 | possible |
| Beaten, later only | −0.34 | 0.01 (−0.12 to 0.14) | 0.01 | | 3 of 4 | −0.11 | −0.02 (−0.08 to 0.05) | 0.03 | possible |
| Beaten | 1.16 | −0.02 (−0.14 to 0.10) | 0.00 | | 1 of 4 | −0.13 | 0.00 (−0.05 to 0.06) | 0.03 | worse |
| *Fatigue* | | | | | | | | | |
| Grinder, 52 weeks (148,476) | 5.85 | 0.52 (0.34 to 0.71) | 0.00 | yes | 3 of 4 | 0.95 | −0.09 (−0.24 to 0.05) | 0.12 | finding |
| Late decline × best of five (49,792) | 2.39 | 0.02 (−0.17 to 0.21) | 0.03 | | 2 of 4 | −0.11 | −0.01 (−0.18 to 0.17) | 0.04 | no sign |
| Grinder × best of five (151,212) | 2.06 | −0.01 (−0.11 to 0.09) | 0.00 | | 1 of 4 | 0.07 | −0.02 (−0.18 to 0.15) | −0.00 | no sign |
| Minutes over 14 days × late decline (42,444) | 2.95 | −0.02 (−0.08 to 0.05) | 0.02 | | 2 of 4 | 0.01 | −0.05 (−0.10 to 0.00) | 0.04 | no sign |
| Late decline × expected length (49,792) | 1.16 | −0.03 (−0.12 to 0.06) | 0.01 | | 2 of 4 | 0.00 | −0.04 (−0.14 to 0.06) | 0.03 | no sign |
| Late decline, career (49,792) | 4.06 | −0.03 (−0.10 to 0.04) | 0.01 | | 1 of 4 | −0.01 | −0.05 (−0.12 to 0.03) | 0.06 | no sign |
| Sets over 14 days × late decline (49,792) | 3.02 | −0.04 (−0.11 to 0.03) | 0.01 | | 1 of 4 | −0.04 | −0.04 (−0.12 to 0.04) | 0.02 | no sign |
| Grinder, career (151,212) | 9.93 | −0.19 (−0.39 to 0.00) | 0.01 | | 1 of 4 | 0.06 | −0.14 (−0.30 to 0.03) | 0.06 | worse |
| *Earlier study (reference rows)* | | | | | | | | | |
| Sets over the last 14 days (155,130) | 4.26 | 1.63 (1.41 to 1.84) | −0.00 | yes | 4 of 4 | 1.74 | 0.23 (−0.01 to 0.48) | 0.02 | finding |
| Matches played, 52 weeks (155,130) | 17.95 | 0.96 (0.77 to 1.15) | 0.01 | yes | 3 of 4 | 1.20 | −0.06 (−0.13 to −0.00) | 0.06 | finding |
| Elo's change over 12 months (152,159) | −0.11 | −0.30 (−0.44 to −0.16) | −0.00 | | 1 of 4 | −0.14 | −0.01 (−0.05 to 0.03) | 0.01 | worse |
| Level played over 52 weeks | 15.26 | −2.48 (−2.91 to −2.06) | 0.01 | | 0 of 4 | −1.36 | 0.10 (−0.04 to 0.25) | 0.01 | worse |

**Women** (60,321 evaluation matches from 2013; 34,645 from 2019 for the rows marked so; the Elo-based rows exist on 59,972 unless noted):

| Row | Alone | Given Elo (95% range) | Band | Line | Eras + | 2022–26 | Given market (95% range) | Band | Reading |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| *Strength of schedule* | | | | | | | | | |
| Quality of wins | 65.24 | 0.95 (0.21 to 1.69) | −0.00 | yes | 3 of 4 | 0.60 | 0.07 (−0.11 to 0.25) | 0.03 | finding |
| Opponents' surface Elo | 58.83 | 0.45 (−0.40 to 1.31) | −0.01 | yes | 3 of 4 | 0.40 | 0.04 (−0.17 to 0.25) | 0.05 | finding |
| Opponents lost to | 33.29 | 0.25 (−0.48 to 0.98) | 0.03 | yes | 3 of 4 | 0.31 | −0.02 (−0.20 to 0.16) | 0.08 | finding |
| Results above expectation, strong opponents | 0.13 | −0.01 (−0.07 to 0.06) | 0.03 | | 3 of 4 | 0.03 | −0.04 (−0.14 to 0.05) | 0.02 | no sign |
| Opponents' ratings (from 2019; 34,422) | 51.65 | −0.09 (−0.78 to 0.61) | 0.02 | | 2 of 3 | 0.24 | 0.18 (−0.18 to 0.54) | 0.13 | worse |
| Results above expectation | 0.81 | −0.47 (−0.75 to −0.19) | 0.02 | | 1 of 4 | 0.26 | −0.06 (−0.15 to 0.04) | 0.03 | worse |
| Opponents' surface Elo, decayed (60,197) | 57.16 | −0.97 (−1.84 to −0.09) | 0.03 | | 1 of 4 | −0.31 | 0.01 (−0.19 to 0.21) | 0.06 | worse |
| *Retrospective credit* | | | | | | | | | |
| Lost to, later only | 0.02 | 0.47 (0.25 to 0.69) | 0.00 | yes | 4 of 4 | 0.24 | 0.07 (−0.04 to 0.18) | 0.02 | finding |
| Lost to | 0.34 | 0.41 (0.22 to 0.60) | 0.01 | yes | 4 of 4 | 0.32 | 0.08 (−0.04 to 0.20) | 0.01 | finding |
| All opponents | −0.11 | 0.34 (0.07 to 0.60) | 0.01 | yes | 3 of 4 | 0.10 | 0.11 (0.00 to 0.21) | 0.04 | finding |
| All, later only | −0.47 | 0.13 (−0.09 to 0.35) | 0.02 | yes | 2 of 4 | −0.01 | 0.09 (−0.03 to 0.20) | 0.04 | possible |
| Beaten, later only | −0.23 | −0.03 (−0.18 to 0.13) | 0.05 | | 2 of 4 | −0.14 | 0.01 (−0.05 to 0.07) | 0.06 | worse |
| Beaten | 0.22 | −0.11 (−0.29 to 0.07) | 0.05 | | 2 of 4 | −0.21 | 0.02 (−0.04 to 0.08) | 0.06 | worse |
| *Fatigue (from 2019)* | | | | | | | | | |
| Grinder, 52 weeks (33,327) | 9.26 | 0.51 (0.22 to 0.79) | 0.11 | yes | 3 of 3 | 0.55 | −0.10 (−0.31 to 0.10) | 0.11 | finding |
| Sets over 14 days × late decline (15,596) | 2.71 | −0.03 (−0.24 to 0.19) | 0.17 | | 1 of 3 | 0.04 | −0.05 (−0.11 to 0.02) | 0.11 | no sign |
| Minutes over 14 days × late decline (13,294) | 3.01 | −0.06 (−0.27 to 0.16) | 0.17 | | 0 of 3 | −0.00 | −0.16 (−0.35 to 0.02) | 0.15 | no sign |
| Late decline, career (15,636) | 3.65 | −0.10 (−0.42 to 0.22) | 0.03 | | 1 of 3 | 0.13 | −0.19 (−0.35 to −0.03) | 0.01 | worse |
| Late decline × expected length (15,636) | 0.97 | −0.10 (−0.44 to 0.23) | −0.00 | | 1 of 3 | 0.21 | −0.23 (−0.41 to −0.06) | 0.00 | no sign |
| Grinder, career (33,950) | 13.97 | −0.11 (−0.21 to −0.01) | 0.01 | | 1 of 3 | 0.00 | 0.08 (−0.17 to 0.33) | 0.10 | no sign |
| *Earlier study (reference rows)* | | | | | | | | | |
| Sets over the last 14 days (60,270) | 1.48 | 1.87 (1.49 to 2.25) | −0.01 | yes | 4 of 4 | 2.11 | 0.29 (−0.06 to 0.64) | 0.01 | finding |
| Matches played, 52 weeks (60,321) | 8.91 | 0.65 (0.29 to 1.02) | 0.01 | yes | 3 of 4 | 0.73 | −0.05 (−0.12 to 0.02) | 0.03 | finding |
| Elo's change over 12 months (59,851) | 0.11 | −0.11 (−0.23 to 0.01) | 0.00 | | 1 of 4 | −0.01 | −0.03 (−0.09 to 0.03) | 0.04 | worse |
| Level played over 52 weeks | 35.34 | −2.09 (−2.81 to −1.38) | 0.01 | | 0 of 4 | −1.11 | 0.21 (−0.07 to 0.48) | 0.05 | worse |

**Given the market** (`derived`):

* **Observed.** No new row clears the family-wide line, and none gains 1 milli-log-loss.
* 4 men's and 6 women's new rows are above their own band, each gaining under 0.19: for example the women's credit over all opponents, 0.11 (0.00 to 0.21).
* Two rows are below their band: the men's 52-week grinder, −0.09, and the women's late decline × expected length, −0.23 (−0.41 to −0.06).
* Of the reference rows, sets over the last 14 days clears the line given the market on both tours (0.23 and 0.29), and the women's level played over 52 weeks does too (0.21), as in Stage 4.
* **Inferred.** What the new rows add to Elo, the closing odds already hold.

## 6. Added to the Stage 3 ratings instead of Elo

The two rows with the largest gain given Elo in each of the schedule and credit families, per tour, are added to the earlier study's strongest feature: the serve and return ratings through the iid model, `p_ratings` = expit(`rating_matchup|single`). They are scored against the ratings alone, in a separate rundown with its own band and line: 3.79 (men) and 4.27 (women). The women's are scored from 2019, where Stage 4 scored the ratings. Surface Elo's own log-odds is scored the same way beside them, as the reference for what any results-based strength adds to point-based ratings.

| Row | Men, given the ratings (95% range) | 2022–26 | Reading | Women, given the ratings (95% range) | 2022–26 | Reading |
|---|---:|---:|---|---:|---:|---|
| *Reference: surface Elo as a feature* | 15.11 (14.35 to 15.87) | 10.53 | finding | 13.42 (11.91 to 14.93) | 13.46 | finding |
| Credit, opponents lost to | 0.21 (0.09 to 0.32) | −0.05 | finding | 0.12 (−0.04 to 0.29) | 0.12 | possible |
| Credit, all opponents, later only | 0.14 (0.04 to 0.24) | −0.11 | finding | – | | |
| Credit, opponents lost to, later only | – | | | 0.10 (−0.08 to 0.28) | 0.09 | possible |
| Results above expectation, strong opponents | 0.08 (0.01 to 0.15) | 0.07 | finding | – | | |
| Results above expectation | 0.08 (0.01 to 0.14) | 0.16 | finding | – | | |
| Quality of wins | – | | | 3.78 (2.39 to 5.17) | 4.42 | possible |
| Opponents' surface Elo | – | | | 2.52 (1.10 to 3.94) | 3.31 | possible |

* **Observed.** For the men, the two best schedule rows given Elo were level or worse there (0.00 and −0.43), yet each adds 0.08 to the ratings. The credit adds 0.21 and 0.14, fading by 2022–2026.
* **Observed.** For the women, quality of wins adds 3.78 to the ratings, against 13.42 for Elo itself.
* **Inferred.** The ratings know points, not results: a results-based strength measure adds to them as Elo does. These rows are a partial stand-in for Elo, not a new kind of information.

## 7. Probes and checks

**The probe cut by date, event and round** (`stageC_sos.probe`, after `stage4_features.probe`).

* **What is redrawn.** At each cut match, everything the cut may not see:
  * results, statuses, box scores and minutes of its own round and later rounds of its event, of the week's other events and of later weeks;
  * the pre-match values (Elo, its counts, Elo's probability, the Stage 3 ratings and expectations, rankings, ages) of every match outside the protected set;
  * for the fatigue probe, every point-by-point record from the cut's week on.
* **The check.** Every column is rebuilt with the frozen constants. The protected matches are the earlier weeks, and the cut event's rounds up to and including the cut's. A deliberately leaky control, career wins counted with the match itself, must move.

| Probe | Slice | Cuts | Columns | Protected match-cuts checked | Moved | Later ones moved | Control moved | Largest protected difference |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Schedule and credit | both tours, 2025–2026 | 4 in 2026 | 13 | 97,620 | 0 | 37,840 of 38,848 | 19 | 3.6e-15 |
| Fatigue | both tours, 2023–2024 | 3 in January–June 2024, 1 at Wimbledon 2024 (952 point-by-point player-matches redrawn after each) | 8 | 100,580 | 0 | 48,061 of 49,720 | 86 | 3.5e-18 |

* **Observed.** No protected feature moved; the leaky controls were caught.
* **Other checks:**
  * the reference rows reproduce Stage 4's ranking to 9.4e-17 (`reference_check`);
  * the features through the probe's builder equal the tuned columns exactly;
  * the 14-day loads equal Stage 4's;
  * the set-counting simulator of the grinder's replay equals `stage2_iid.simulate` draw for draw (a test).

## Problems found in the earlier study's data or code (reported, not fixed)

1. **Tournament dates that are not Mondays** (`data_notes`).
   * 287 of the 4,976 evaluation-level events, holding 13,246 of the 215,451 evaluation matches, are dated on another weekday: 138 on a Sunday, 96 on a Tuesday, 36 on a Wednesday, 13 on a Thursday, 3 on a Saturday, 1 on a Friday.
   * The study's time rule (`common.asof_sums`, Stage 1's Elo pass, every Stage 4 feature) treats each date as a week. An event dated on a Sunday, such as a draw that starts on the Sunday, is then a different "week" from the Monday-dated events played the same days, and so are mid-week starts.
   * **Inferred:** a player's own history is barely affected, since a player plays one event at a time. Features that read other players' later ratings are: the earlier-date reading would have taken 299,480 of this stage's 27.6 million credit readings from the pool match's own tennis week. Stage C reads tennis weeks there; Stage 0's dates are unchanged.
2. **Implausible minutes in Stage 0.** 66 men's and 57 women's matches with a box score have minutes implying fewer than 15 or more than 120 seconds per point. Stage 4's minutes features use them as they are; the grinder leaves them out.
3. **The point-by-point table keeps no time stamps** (`stage2_pbp_points.parquet`), so a "late" segment by elapsed time cannot be built from it. The raw files' columns were not examined. A limitation of the derived table rather than an error.
4. **Earlier problems still feed every history here**, as Stage 4 listed them: the women's split identities of 2026, match tiebreaks read as sets (the audit's C3), and the format read from the score for the ratings' iid probability (used here for the closeness weight and the given-ratings base).

## Limitations

* **Stage A's Bradley–Terry rating** was not available, so the schedule on BT ratings was not built.
* **The constants are in-sample for 2013–2018.** The figures for 2019–2026 and 2022–2026 are the out-of-sample reading. 14 of 26 schedule and credit constants sit at the grid's top.
* **The credit reads Elo levels.**
  * Later rematches and the meeting's own update are removed to first order: Elo updates are not exactly additive.
  * "Now" is a pre-match value, without the opponent's latest result.
  * An opponent who played two events of one week can be read at either.
* **Late decline** rests on Grand Slam main draws only:
  * Australian Open and Roland Garros to 2021, Wimbledon and the US Open to 2024;
  * the women's third-set measure exists only in three-set matches;
  * its reliability rests on a few hundred players (men) and a few dozen (women).
* **The grinder's "long"** is realised length, an outcome. The replay reproduces the selection through points per set but not the pace of play, so the part of the trait above the replay may be playing style or surface.
* **The ratings-based rows** (the opponents' Stage 3 ratings; the fatigue rows) are scored for the women from 2019, the rest from 2013, so the two groups' women's figures are not on the same seasons.
* **Ranges and reliabilities** treat matches and players as independent, so they are somewhat too narrow. The shuffled copies are the more robust guard.

## Decisions for the owner

1. **The credit for opponents lost to.** It is the one new idea that adds to Elo on both tours: 0.16 and 0.41 better as specified, 0.14 and 0.47 from later matches only. The men's fades after 2021, and neither adds anything given the market. Results-only information is taken to be priced in (the owner's entry of 30 Sep 2026). Carry it to Stage D's combined test, or drop it?
2. **The date convention.** Normalise Stage 0's tournament dates to the tennis week's Monday (a Sunday date to the following Monday), so that every stage's time rule reads weeks? It touches every earlier table. Stage C applies the rule only where other players' later ratings are read.
3. **Fatigue as a pre-match family.** Nothing here adds to Elo or the market, and the measures are mostly selection. Close the family, or follow the one live signal in-play: real winners gain more late than pure luck gives, including in the third set alone, which is a within-match observation (section 3.1)?
4. **The grinder's constant** comes from career windows, because player-seasons show no spread (Stage 3's method on seasons gives none). Accept, or treat the grinder as noise?
5. **The phantom-opponent grid.** 14 of 26 choices are at its top (20). Widen it in a later round, or keep the brief's grid?
6. **The Bradley–Terry schedule row.** Rerun `stageC_sos.py`, then `stageC_rundown.py`, once `stageA_bt.parquet` exists: about 5 minutes and 2 minutes.

## Suggestions (not applied)

* **Suggestion. Score the credit as an Elo correction in the combined test.** Like Stage 4's luck correction, it says that Elo charged some losses too much. Use the later-only form, for the women first.
* **Suggestion. Use the women's quality of wins with the ratings, not with Elo.** Beside the ratings it adds what results-based strength adds (3.78 against Elo's 13.42). Beside Elo it adds 0.95. Stage D's combined model is where to judge it.
* **Suggestion. Read the late-match signal in-play.** The excess of real winners' late gains over the replays (men 0.040 against 0.024; third set alone 0.014 against 0.001) is about within-match dynamics. A live model with time-stamped points (`docs/studies/official_point_feeds/`) could test whether it predicts the rest of a match.
* **Suggestion. Rebuild the minutes features with the plausibility rule** (15–120 seconds per point) when Stage 0 is next rebuilt.
