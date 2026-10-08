# Stage 2: anatomy of a win

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: built 30 Sep 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md); the report section is "Anatomy of a win" in [report.html](report.html). Stages 0 and 1, the Stage 0 audit and the owner's entry after Stage 1 were read first.

**None of this is a pre-match forecast.** Every number uses each match's own statistics, so it says how matches are won, not how to predict them.

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/predictability_diagnostic/`: from `stage2_results.json` unless another file is named (`stage2_pbp_results.json` for the point-by-point part, or a CSV).

## In short

* **Observed.** Winning more points almost always wins the match, by a thin margin. A man who wins 51.7% of the points in a best-of-three match wins about 90% of the time (51.5% at best of five; a woman 51.8%). Still, **4.36% of men's and 3.86% of women's matches went to the player who won fewer points.**
* **The pure-luck replay.** Every match was played again, point by point, as if each point were an independent draw at the serve rates the two players showed that day (rates de-noised; see [the replay](#the-pure-luck-replay)). The replay has no skill on big points and no streaks. It reproduces the real share of matches won with fewer points (4.36% for the men, 3.71% against 3.86% for the women), the spread of points shares and the plug-in floor. **Most of what looks like clutch play is what pure luck produces.**
* **Observed.** Given the points share, **tiebreaks explain a lot and break points little**. Adding tiebreak over-performance to a logistic regression on the points share improves its log loss by 40.9 milli-log-loss (men) and 24.9 (women); break points add 2.9 and 0.2. Pure luck gives 46.6 and 29.9, and 3.0 and 0.4.
* **Inferred. The randomness floor the stage asked for is far too optimistic,** because the serve rates are measured on the very points that decided the match. On the 2022–2026 matches with odds it scores 0.237 (men) and 0.194 (women). A forecaster who knew each player's true rates for the day would score about **0.426 and 0.421** (from the replay).
  * With that floor, a coin's 693 milli-log-loss splits into **108 known before the match** (the closing odds), **160 (men) and 165 (women) for how each player played on the day, and 426 and 421 of scoring luck**: 16%, 23–24% and 61%.
  * The plug-in floor puts 349 and 392 on the day and only 237 and 194 on luck.
* **Observed.** Over-performance on big points barely carries over:
  * **Box score.** Between two random halves of a player's matches, break points won above expectation correlate at 0.05 (men) and 0.02 (women), tiebreaks at 0.06, against 0.89 and 0.87 for serve points won (25+ matches a half).
  * **Beyond luck.** Only the men's break-point record persists beyond pure luck, weakly: 0.11 with 50+ matches a half, about one fifth signal on a hundred-match record.
  * **Point by point** (Grand Slams, the optional part). Big-point play *on return* persists beyond luck for both tours (0.21 and 0.19 against 0.01 and −0.01, 10+ matches a half). It is tentative.
* **Observed.** Servers do slightly worse on big points than pure luck gives: 0.7 points fewer break points saved (men; 0.6 women), and 0.3 and 0.2 points on importance-weighted serve points.
* **Observed.** The points edge is made after the serve lands. First serves in play account for 55% (men) and 60% (women) of its variation and second serves in play 37% and 32%. Aces are 7% and 5% (10% on men's grass), double faults 5% and 4%, and first-serve percentage 3% and 2%.
* **For the owner.** Seven decisions, [at the end](#decisions-for-the-owner).

## What was built

| File | What it holds |
|---|---|
| `stage2_matches.parquet` (32.2 MB) | One row per analysed match (180,176). It holds the match's serve rates and points share, the iid chance (the plug-in floor), and expected and actual break points and tiebreaks. It also holds the six points-edge components, the Stage 1 baselines, and the replay's true rates, result and plug-in chance. |
| `stage2_slam_final_set_rules.csv` (hand-made) | The deciding-set rule of each Grand Slam, draw and year, with its evidence, source URL and access date |
| `stage2_slam_rules_check.csv` | Each Slam × draw × year since 2010: how its deciding sets ended, against the rule |
| `stage2_points_curve.csv` | (a) share of player-matches won by points-share bin, real and replay |
| `stage2_fewer_points.csv` | (a) share of matches won with fewer points, by tour, best of, surface, level and era |
| `stage2_beyond_points.csv` | (b) every regression, real and replay, with its gain over the base and a 95% range |
| `stage2_floor_cells.csv`, `stage2_floor_calibration.csv` | (c) the floors against Elo and the market by tour, window, best of and level; the plug-in floor's calibration |
| `stage2_persistence.csv` | (d) split-half correlations, real and five replays |
| `stage2_components.csv` | (e) the points edge by component, tour and surface |
| `stage2_match_impact.csv` | (f) every per-match rate's match impact, by tour and best of (for the summary's chart) |
| `stage2_pbp_points.parquet`, `stage2_pbp_players.parquet`, `stage2_pbp_results.json` | The optional point-by-point part |
| `stage2_results.json` | Everything quoted here, apart from the point-by-point part |

Code in `src/eda/predictability_diagnostic/`:

* `stage2_iid.py`: the iid model, the Grand Slam rules lookup and a point-by-point simulator.
* `stage2_anatomy.py`: (a)–(f) and the replay; about 1½ minutes.
* `stage2_pbp.py`: the optional part; about 1½ minutes.
* `report_stage2.py`: the report section.

Tests: `test/predictability_diagnostic/test_stage2.py` (54 tests; 167 in the study, all passing). **Shared helpers kept out of `common.py`** (Stage 3 may run beside this stage), noted here as the prompt asked:

* `stage2_anatomy.oof_logit`, the out-of-fold logistic regression without an intercept;
* `stage2_anatomy.denoised_rates`, the de-noised serve rates;
* the whole of `stage2_iid.py`.

`stage2_pbp.py` imports them.

## Terms used here

* **Points share**: the share of all the points in a match that a player won, serving and returning. The **points edge** is that share minus 50%.
* **Serve rate**: the share of points on their own serve a player won in the match. Its average by surface is 60.3–66.3% for the men and 54.5–58.5% for the women (`twin.prior`).
* **Break point**: a point that gives the receiver the server's game (a **break**) if the receiver wins it. The server **saves** it by winning it.
* **Tiebreak**: at six games all, a race to 7 points won by two decides the set. Grand Slam deciding sets have their own rules, below.
* **Best of three / five**, **deciding set**: the first to two sets or three. The deciding set is the one played at one set all or two all.
* **The iid model**: every point an independent draw (independent and identically distributed). The server wins it with their serve rate whatever the score. From two serve rates it gives the exact chance of holding serve, winning a tiebreak, a set and the match.
* **Expected**: what the iid model says a player should have won. Break points saved = break points faced × the serve rate; tiebreaks = the model's chance of winning one, from the two serve rates. **Over-performance** = actual minus expected.
* **Plug-in floor**: the iid model's chance that a player wins, fed the serve rates measured in that match.
* **Log loss, milli-log-loss**: as in Stage 1. The average of minus the natural log of the probability given to the winner; a coin scores 0.693, lower is better, 0.001 is one milli-log-loss.
* **Split-half correlation**: each player's matches split into two random halves; the correlation, across players, between a measure in one half and in the other. Stable traits correlate highly, luck does not.

## The matches

**Observed** (`population.steps`):

| Step | ATP | WTA |
|---|---:|---:|
| Evaluation matches (Stage 0) | 155,130 | 60,321 |
| WTA from 2019 (the Brief's window for box-score evaluation) | 155,130 | 34,645 |
| Completed (retirements set aside) | 149,909 | 33,640 |
| With a box score that passed Stage 0's checks | 147,091 | 33,244 |
| Standard format (Next Gen short sets and match tiebreaks left out) | 146,972 | 33,216 |
| A complete score (the winner took 2 of 3 or 3 of 5 sets, every set written) | 146,972 | 33,205 |
| Every point and break-point count readable | **146,971** | **33,205** |

* **Retirements** (5,221 men's and 1,005 women's) are set aside and reported apart where they matter: their box scores cover part of a match that something else decided. This is decision 1.
* **Best of three or five is read from the score**, from the winner's sets. The source records 47 men's Wimbledon matches of the last qualifying round (Q3) as best of three although their scores show best of five: 16 in 2019, 16 in 2022 and 15 in 2024. The analysed matches: 140,293 men's best of three, 6,678 best of five, and 33,205 women's.

### Grand Slam deciding sets

The rule for each Slam, draw and year is the hand-made `stage2_slam_final_set_rules.csv`, with its evidence and sources (accessed 30 Sep 2026):

| Slam | Main draw | Qualifying |
|---|---|---|
| Australian Open | advantage set to 2018; a 10-point tiebreak at 6-6 from 2019 ([WTA](https://www.wtatennis.com/news/1437627/australian-open-introduces-10-point-final-set-tiebreaks)) | advantage to 2017; **a tiebreak at 6-6 in 2018 (found in the scores; length not found, 7 points assumed)**; 10 points at 6-6 from 2019 |
| Roland Garros | advantage set to 2021; 10 points at 6-6 from 2022 ([ESPN](https://www.espn.com/tennis/story/_/id/33516267/grand-slams-test-10-point-tiebreak-final-set-all-four-majors)) | advantage to 2016; **a 7-point tiebreak at 6-6 in 2017–2021 (found in the scores; the [2017 draw sheet](https://en.wikipedia.org/wiki/2017_French_Open_%E2%80%93_Men%27s_singles_qualifying) shows one won 8-6)**; 10 points at 6-6 from 2022 |
| Wimbledon | advantage set to 2018; a 7-point tiebreak at 12-12 in 2019 and 2021 ([Sky Sports](https://www.skysports.com/tennis/news/12110/11529373/wimbledon-introduce-final-set-tie-breaks-from-2019): "all events"); 10 points at 6-6 from 2022 | as the main draw |
| US Open | a 7-point tiebreak at 6-6 to 2021; 10 points at 6-6 from 2022 | as the main draw |

* **Observed** (`stage2_slam_rules_check.csv`). Against every completed Grand Slam score since 2010 that reached a deciding set, the rules hold in all 133 Slam × draw × year cells: no long deciding set under a tiebreak rule, no 7-6 under an advantage rule. Deciding-set tiebreaks average 4.0 points for the loser under the 7-point rules and 6.6 under the 10-point ones, which fits their lengths.
* **No simplification was needed.** The iid model plays each rule exactly: advantage sets, a tiebreak to 7 or 10 at 6-6, a tiebreak at 12-12. Analysed matches under each deciding-set rule: men 3,228 advantage, 5,184 ten-point, 471 at 12-12, 138,088 standard; women 368, 4,939, 473 and 27,425.
* Every other evaluation event plays a 7-point tiebreak at 6-6 in every set.

### The iid model, checked

`stage2_iid.py` gives the exact chance of holding serve, winning a tiebreak, a set and the match from two serve rates. The tests check it four ways:

* against a brute-force walk over every score (a game to 1e-12, every set rule to 1e-9);
* against itself with the server reversed. Who serves first does not change the chance of winning a tiebreak or a set (to 1e-12), so sets are independent draws (Newton and Keller's result);
* against a point-by-point simulation of the same rules (60,000 matches per format);
* against the textbook value: a server winning 60% of points holds 73.57% of games.

## 1. Points to wins

**Observed** (`a_points_to_wins`, `stage2_fewer_points.csv`):

| | Men, best of 3 | Men, best of 5 | Women |
|---|---:|---:|---:|
| Matches | 140,293 | 6,678 | 33,205 |
| Each point of share multiplies the odds of winning by | 3.77 | 4.46 | 3.37 |
| Points share for a 75% chance | 50.83% | 50.73% | 50.90% |
| Points share for a 90% chance | 51.66% | 51.47% | 51.81% |
| Winners' average share | 55.63% | 54.97% | 56.03% |
| Won by the player with fewer points | 4.36% | 4.54% | 3.86% |
| Pure luck (the replay) | 4.35% | 4.49% | 3.71% |
| Log loss of the points share alone (cross-validated) | 0.117 | 0.115 | 0.118 |
| … in the replay | 0.118 | 0.113 | 0.103 |

* About 1% of matches end with the points level (1.07% men, 1.04% women).
* **By surface (men):** grass 5.07%, hard 4.47%, clay 4.15%; women hard 4.03%, grass 4.01%, clay 3.50%.
* **By level:** the men's 500s, 250s and 1000s are highest (5.19%, 5.05%, 5.02%) and Challenger qualifying lowest (3.55%); the women's 500s 5.24%, Grand Slams 3.00%.
* **2022–2026:** 4.48% and 3.69%.
* **Retirements:** the player who advanced had won fewer points in 8.01% of men's (5,108 with a box score) and 8.28% of women's (990).

**Inferred.**
* Winning with fewer points is what independent points produce at these serve rates; it does not need clutch play to explain it.
* The serve-dominated surface (grass) produces it most: holds are many and a few points decide.
* One difference: **for the women, the points share decides a little less than pure luck predicts** (log loss 0.118 against 0.103). For the men it does not (0.117 against 0.118). Something beyond independent points shapes women's matches more; streaks of form within a match are one candidate. Not tested here.

## 2. Break points and tiebreaks

Given the points share, how much do break points and tiebreaks explain? The over-performance inputs:

* **Break points:** saves above the serve rate plus conversions above the return rate, in break points. A player's conversions over-perform by exactly what the opponent's saves under-perform.
* **Tiebreaks:** tiebreaks won above the model's chance from the two serve rates, using a 10-point tiebreak where the deciding-set rule says so.

**Observed** (`stage2_beyond_points.csv`; logistic regressions without an intercept, five-fold cross-validated; milli-log-loss better than the points share alone, with a 95% range):

| | Men | Women | Men, pure luck | Women, pure luck |
|---|---:|---:|---:|---:|
| Points share alone (log loss) | 0.117 | 0.118 | 0.118 | 0.103 |
| + break points | 2.9 (2.5 to 3.3) | 0.2 (−0.01 to 0.51) | 3.0 | 0.4 |
| + tiebreaks | 40.9 (39.6 to 42.3) | 24.9 (22.7 to 27.1) | 46.6 | 29.9 |
| + both | 45.5 (44.1 to 46.9) | 25.6 (23.4 to 27.9) | 51.6 | 31.0 |

* On top of the iid model's chance instead of the points share, break points add 23.0 (men) and 4.5 (women), tiebreaks 46.3 and 26.1, and both 73.9 and 31.9. Pure luck gives 21.9, 6.0; 51.9, 31.2; 79.2, 39.1.
  * *Inferred:* the points share already carries much of the break-point information. A player who faces many break points serves many points in long games, and the points share weighs that; the iid chance does not.
* Men's best of five: break points 2.2, tiebreaks 34.9, both 39.2 (pure luck 3.6, 36.1, 41.5).

**Against expectation** (`b_beyond_points.descriptive`):

| | Saved | Expected | Pure luck: saved | Expected |
|---|---:|---:|---:|---:|
| Men, all servers | 59.25% | 58.41% | 59.77% | 58.19% |
| Men, winners | 67.78% | 64.18% | 67.75% | 63.72% |
| Men, losers | 54.19% | 54.97% | 54.99% | 54.89% |
| Women, all servers | 54.17% | 53.36% | 54.45% | 53.08% |

* **The measure is biased, and the replay shows it.** Measured against their serve rate in the match, servers seem to save more break points than expected; pure luck shows more still. A player who faces many break points has usually had an unlucky day on serve, which drags the rate they are measured against below their true rate. The tests confirm it on simulated matches: against the true rate the bias vanishes.
* **Against the replay, real servers save 0.7 points fewer break points than pure luck gives (men; women 0.6).** **Inferred:** a small pressure effect.
* **Tiebreaks.** Winners won 80.2% of the tiebreaks they played against 59.7% expected (men; women 80.4% against 59.1%). Pure luck gives 79.1% against 59.8%.
* **Matches won with fewer points.** The winner was ahead of expectation on break points or tiebreaks in 87.6% (men) and 77.4% (women); pure luck gives 90.2% and 80.3%.
* **Tiebreaks per match.** Real matches play fewer than the replay: 0.379 against 0.427 for the men (32.5% of matches have one, against 35.5%) and 0.241 against 0.274 for the women.

**Inferred.**
* Tiebreaks, not break points, carry what the points share misses: a tiebreak settles a whole set on a dozen points.
* They do so about as much as pure luck predicts, a little less, as real matches have fewer of them.
* Winners look clutch because winning tiebreaks is much of how matches are won (selection), not because of a skill the data can see.

## 3. The randomness floor

### The plug-in floor, as asked

For each match the iid model gives the chance that A wins from the two players' serve rates in the match, under the match's format and deciding-set rule. **Observed** (`c_floor.cells`, `stage2_floor_cells.csv`):

| Matches | Window | Plug-in floor | Surface Elo | Market |
|---|---|---:|---:|---:|
| Men, with odds | 2022–2026 (11,877) | 0.237 | 0.607 | 0.585 |
| Women, with odds | 2022–2026 (10,886) | 0.194 | 0.604 | 0.585 |
| Men, with odds | 2013–2026 (30,618) | 0.230 | 0.594 | 0.575 |
| Women, with odds | 2019–2026 (16,552) | 0.200 | 0.604 | 0.585 |
| Men, every evaluation match | 2013–2026 (146,971) | 0.213 | 0.598 | – |
| Women, every evaluation match | 2019–2026 (33,205) | 0.190 | 0.595 | – |

Elo is Stage 1's surface Elo with retirements counted, closed as the rating by the owner's entry after Stage 1. Taken at face value, on the 2022–2026 matches with odds:

* a coin's 693.1 milli-log-loss splits into 107.7 known before the match, 348.6 (men) and 391.8 (women) for how the players played on the day, and 236.8 and 193.7 of scoring luck.

### Why it is too optimistic, and the better floor

**Inferred.** The rates are measured on the very points that decided the match, so a player who won by luck also shows a higher rate. Three measurements show the effect:

* **The plug-in chances are far too timid** as a forecast of the real result. Refitting them needs their log-odds multiplied by 2.23 (men) and 2.44 (women). In the replay, where everything is iid by construction, the same refit needs 2.23 and 2.76.
* **The replay's own plug-in floor** is 0.226 (men) and 0.197 (women) on the 2022–2026 matches with odds, close to the real 0.237 and 0.194.
* **In the replay the true rates are known.** A forecaster who knew them would score **0.426 (men) and 0.421 (women)** (the average binary entropy of the iid chance at the true rates). That is the floor the stage asked for: the best anyone could do knowing how each player would play that day.

**The split, 2022–2026, matches with odds** (milli-log-loss; percent of a coin's 693.1):

| | Known before the match (coin − market) | How each player played on the day (market − floor) | Scoring luck (the floor) |
|---|---:|---:|---:|
| Men | 107.7 (16%) | 159.9 (23%; 95% range 152.7–167.1) | 425.5 (61%) |
| Women | 107.7 (16%) | 164.9 (24%; 157.3–172.5) | 420.5 (61%) |

* **2013–2026 (women 2019–2026), with odds:** the market is 152.5 (men) and 167.4 (women) above the corrected floor.
* **Every evaluation match:** surface Elo is 177.8 and 182.5 above it.
* **Best of five holds less luck.** On the men's matches with odds of 2013–2026, the corrected floor is 0.359 at best of five against 0.438 at best of three, and the market 0.488 against 0.596.
* **By level** (every evaluation match, `stage2_floor_cells.csv`): men's Grand Slams 0.358, men's 250s 0.441, women's Challenger / 125 qualifying 0.382, women's 500s 0.429.
* **Taking the measured rates as true** (no de-noising) would give a floor of 0.348 (men) and 0.314 (women). A replay at those rates does not look like the real matches (next section), so the corrected floor is the better estimate.

**Inferred.** Most of a tennis match's uncertainty is scoring luck that no forecast can remove. The room for a pre-match forecast to improve on the market is bounded by the "on the day" share, about 160 milli-log-loss on these matches. Even that is generous: it would take knowing each player's true serve and return rates for the day in advance.

## 4. Does it carry over?

Each player's matches (every analysed match of the player) were split into two random halves 50 times. Each measure was correlated across players between the halves. **Observed** (`stage2_persistence.csv`, `d_persistence.rows`; pure luck is the mean of five replays):

| At least … matches in each half | Measure | Men | 95% range | Pure luck | Women | 95% range | Pure luck |
|---|---|---:|---|---:|---:|---|---:|
| 25 (1,110 men, 351 women; for tiebreaks, which need 5 a half, 1,090 and 322) | Serve points won | 0.89 | 0.88 to 0.90 | 0.77 | 0.87 | 0.84 to 0.89 | 0.69 |
| 25 | Break points saved above expectation | 0.07 | 0.01 to 0.13 | −0.02 | 0.04 | −0.06 to 0.14 | 0.05 |
| 25 | Break points converted above expectation | 0.02 | −0.04 to 0.08 | −0.02 | −0.02 | −0.12 to 0.09 | −0.01 |
| 25 | Break points, both ways | 0.05 | −0.01 to 0.11 | −0.02 | 0.02 | −0.08 to 0.12 | 0.00 |
| 25 | Tiebreaks above expectation | 0.06 | 0.00 to 0.12 | −0.02 | 0.06 | −0.05 to 0.16 | 0.01 |
| 50 (807 men, 235 women) | Break points saved | 0.09 | 0.02 to 0.16 | −0.01 | 0.12 | −0.01 to 0.24 | −0.01 |
| 50 | Break points, both ways | 0.11 | 0.04 to 0.18 | 0.00 | 0.05 | −0.08 to 0.17 | −0.04 |
| 50 | Tiebreaks | 0.06 | −0.01 to 0.13 | 0.01 | 0.04 | −0.09 to 0.16 | 0.01 |

(The replay's serve-point correlation is lower than the real one because it draws each match's true rates independently around the measured ones. Serve points won is the yardstick of a stable trait; the real figure is the one to read.)

**Inferred.**
* **For the women** nothing can be told apart from luck.
* **For the men** a small part of break-point play persists beyond luck: 0.11 between halves of 50+ matches against 0.00 in the replays. On a hundred-match record that is about 20% signal (Spearman–Brown) and 80% luck.
* **Tiebreak over-performance** is not clearly above luck.
* **Persistence near zero means luck**, which cannot be a pre-match feature. A break-point record could only enter heavily shrunk, and probably only for the men.

## 5. Which points make the edge

A player's return points against the first serve are the opponent's first-serve points lost. In a match, serving well and returning well are therefore one contest seen from either side: the A − B difference in first-serve points won *is* the difference in return points won against first serves. The components are the two players' difference on each kind of point.

**The exact split.** Per player, serve points won = fi × fw + (1 − fi) × sw, where:

* fi = first serves in;
* fw = aces + (1 − aces) × first serves in play won;
* sw = (1 − double faults) × second serves in play won.

By the midpoint rule, which is exact for differences of products, the points edge splits into six parts that add up to it exactly (largest error 1.7e-16):

* **aces**;
* **first serves in play** (points starting with a first serve in that is not an ace);
* **first serves in** (landing more first serves, which win more often than second serves);
* **second serves in play**;
* **double faults**;
* **serve-point count** (who served more points).

Aces are counted against first serves: the source does not say which serve an ace came on. In the Grand Slam point-by-point files that record the serve number (37 editions, 103,908 aces), 3.99% come on second serves (`stage2_pbp_results.json`, `file_notes`). So the ace part is slightly overstated and the second-serve part understated. 24 matches are left out: 11 with no second serve in play, and 13 whose counts are impossible (more second-serve points won than second serves in play).

**Observed** (`stage2_components.csv`): winners' points per 100 played, and each part's share of the variation of the points edge across matches.

| | Men: winners' points | Share of variation | Women: winners' points | Share of variation |
|---|---:|---:|---:|---:|
| Edge (winners) | 5.60 | 100% | 6.03 | 100% |
| First serves in play | 3.06 | 54.7% | 3.59 | 59.6% |
| Second serves in play | 2.02 | 36.6% | 1.92 | 32.0% |
| Aces | 0.39 | 7.0% | 0.31 | 5.0% |
| Double faults | 0.24 | 4.5% | 0.24 | 4.2% |
| First serves in | 0.19 | 3.2% | 0.12 | 1.9% |
| Serve-point count | −0.29 | −6.0% | −0.15 | −2.8% |

* **By surface (men):** aces are 10.1% on grass, 8.3% on hard and 5.2% on clay; first serves in play 55.1%, 53.3% and 56.3%.
* **Serve-point count runs against the edge**: winners serve fewer points, as their service games are shorter.
* **A regression of the points share** on the six differences (rates, not weighted) explains 97.6% of its variation (men; women 97.7%). Its Shapley split agrees: first serves in play 48.4%, second serves in play 33.7%, aces 7.2%, double faults 4.4%, serve count 3.4%, first serves in 3.0% (men).

**Inferred.** The edge is made in the exchange once the serve is in play, far more than by aces, double faults or the first-serve percentage.

## 6. Match impact of each statistic

For every per-match rate in `stage0_match_players`, a one-input logistic regression of the result on its A − B difference in the same match, cross-validated. The summary's chart is to use this table: `stage2_match_impact.csv`, by tour and by best of. It gives each rate's impact on every match (a missing difference read as none) and where the rate exists. **Observed**, milli-log-loss better than a coin, every analysed match:

| Rate | Men | Women |
|---|---:|---:|
| Sets won (decides the match by definition) | 693.1 | 693.1 |
| Games won | 619.3 | 625.4 |
| Total points won | 576.2 | 574.9 |
| Hold rate (= break rate) | 557.6 | 559.5 |
| Serve points won (= return points won) | 525.6 | 558.5 |
| The iid chance from both serve rates (reference) | 480.2 | 502.7 |
| First-serve points won | 348.7 | 384.6 |
| Break points faced per service game | 273.2 | 260.0 |
| Second-serve points won | 247.2 | 238.1 |
| Break points saved (= converted) | 85.9 | 84.6 |
| Tiebreaks won (227.7 and 216.3 on the 32.5% and 22.1% of matches with one) | 74.1 | 47.7 |
| Aces per serve point | 64.9 | 56.7 |
| Double faults per serve point | 34.2 | 24.5 |
| First serves in | 14.8 | 6.5 |

* **A rate and its mirror are the same number** seen from the other player. A player's return points won are the opponent's serve points lost; the break rate is the opponent's hold rate turned over; break points converted are the opponent's saves turned over. The CSV marks them (`same_as`).
* **The hold rate exists** in 99.44% of men's and 97.85% of women's matches (service games are missing in the rest). Break-point rates are missing where no break point was faced.

## 7. Big points, point by point (the optional part)

The prompt asked, optionally, to repeat (b) and (d) on the Grand Slam point-by-point files, weighting each point by its importance. Done in `stage2_pbp.py`; numbers from `stage2_pbp_results.json`.

* **The data.** Jeff Sackmann's `slam_pointbypoint` files, 49 editions: the Australian Open and Roland Garros 2011–2021, Wimbledon 2011–2024 (no 2020) and the US Open 2011–2024. Main-draw singles only; men best of five, women best of three.
* **The replay check.** Each match was replayed from its point winners and servers under its deciding-set rule. It was checked against the file at every point: the set, the score of the game, the games where written (eight editions leave them blank), and who serves.
  * 4,985 of 5,336 men's and 4,963 of 5,172 women's matches pass: 1,824,960 points, 925 men and 909 women by name.
  * Most of the rest end before the match does (276 and 160: retirements, or files cut short).
* **Importance**: P(win the match | win the point) − P(win the match | lose it). It comes from the score alone, with both players at their tour's average serve rate in these files (63.9% men, 57.0% women), so a point's weight does not depend on how the match then went.
  * The tests check that the chance is consistent point by point, and that from the first point it equals the exact match chance under every rule.
* **Big-point play ("clutch")**: a player's importance-weighted share of points won minus their plain share, on serve and on return, in the same match.
  * One player's return clutch is the other's serve clutch turned over.
  * The measure is not exactly zero under pure luck: both shares are ratios over a path the results shape. **Point-by-point pure-luck replays** of the same matches (three, de-noised rates, the same weights) are the benchmark.

**Observed.**
* **Importance is concentrated.** The most important tenth of points carries 31.2% of all importance (men) and 25.8% (women).
* **Break points** are 8.27% of men's points and 17.76% of the importance (2.1 times an average point); women 11.35% and 16.72% (1.5 times). Tiebreak points are 2.8 and 2.5 times an average point.
* **On serve, players win slightly fewer big points** than their serve points overall: −0.62 points per 100 (men, 95% range −0.70 to −0.53) and −0.33 (women). Pure luck gives −0.34 and −0.16, so the shortfall beyond luck is −0.27 and −0.16: the same small pressure effect as the break points.
* **Adding the big-point difference to the points share** improves the log loss by 102.0 milli-log-loss (men, 91.8 to 112.3) and 91.7 (women). Pure luck gives 117.3 and 88.9: as with tiebreaks, big points decide close matches about as much as luck predicts.
* **Persistence across a player's Grand Slam matches** (50 random splits):

| At least … matches in each half | Measure | Men | 95% range | Pure luck | Women | 95% range | Pure luck |
|---|---|---:|---|---:|---:|---|---:|
| 10 (131 men, 134 women) | Serve points won (yardstick) | 0.78 | 0.70 to 0.84 | 0.59 | 0.71 | 0.62 to 0.79 | 0.42 |
| 10 | Big points on serve | 0.09 | −0.08 to 0.26 | 0.04 | −0.04 | −0.21 to 0.13 | −0.01 |
| 10 | Big points on return | 0.21 | 0.04 to 0.37 | 0.01 | 0.19 | 0.02 to 0.35 | −0.01 |
| 10 | Big points, both | 0.27 | 0.10 to 0.42 | 0.06 | 0.10 | −0.08 to 0.26 | 0.08 |
| 20 (46 men, 62 women) | Big points on return | 0.45 | 0.19 to 0.66 | 0.09 | 0.32 | 0.08 to 0.53 | 0.00 |
| 20 | Big points, both | 0.51 | 0.26 to 0.70 | 0.29 | 0.27 | 0.03 to 0.49 | 0.06 |

**Inferred.**
* **Pure luck alone makes big-point play look persistent** for players with many matches (0.29 for the men at 20+ a half): they win most of their matches, and winners win the big points. That is why the replays, not zero, are the benchmark.
* **On serve, nothing beyond luck.** On return, big-point play persists beyond luck on both tours. This is the one place in Stage 2 where play on big points looks like more than luck.
* **It is tentative**:
  * it rests on 131 men and 134 women with many Grand Slam matches;
  * it covers Grand Slams only;
  * it could also come from form that swings within matches, which the replays do not model (their rates are fixed for the match).

## The pure-luck replay

How it is built (`stage2_anatomy.twin`, `denoised_rates`):

* **De-noising.** A serve rate measured on n points carries binomial noise of variance p(1 − p)/n, so measured rates are more spread out than true ones. Per tour and surface, the variance of true rates is that of measured rates less the average noise: 61.6% of it for men's hard courts, 60.2% on grass, 56.1–59.7% for the women (`twin.prior`). Each measured rate is shrunk toward the group's mean by the true share of its variance, and a true rate is drawn from that normal posterior (empirical Bayes).
* **The replay.** Each analysed match is replayed point by point (`stage2_iid.simulate`) at those rates, with its players, format and deciding-set rule. The replay's box scores go through the same analyses.

**Does it look like the real matches?** (`twin.fit`, all analysed matches):

| | Men real | Replay | At measured rates | Women real | Replay | At measured rates |
|---|---:|---:|---:|---:|---:|---:|
| Plug-in floor, log loss | 0.213 | 0.218 | 0.174 | 0.190 | 0.192 | 0.146 |
| Spread of the points share (SD, points) | 7.05 | 6.93 | 8.67 | 7.56 | 7.44 | 9.38 |
| Matches won with fewer points | 4.36% | 4.36% | 3.51% | 3.86% | 3.71% | 2.74% |
| Tiebreaks per match | 0.379 | 0.427 | 0.373 | 0.241 | 0.274 | 0.222 |
| Break points per match | 13.50 | 13.55 | 12.91 | 16.85 | 17.05 | 15.88 |

**Observed.**
* The replay matches the real matches on the plug-in floor, the spread of points shares, the share won with fewer points and the number of break points.
* It plays more tiebreaks than real matches.
* Replaying at the measured rates (no de-noising) gives matches that are too lopsided, which is why the replay draws true rates.

## Problems found in earlier work (reported, not fixed)

1. **Stage 0: a box score kept with an unreadable count.** One Tennis My Life box score (Prague 2026, `atp|2026-600|R32|atp:200266|atp:209322`) has a break-point count that does not read as a number. Stage 0's check treats any written count as present. Stage 2 leaves it out.
2. **Stage 0 (from Sackmann): best of five recorded as three.** 47 men's Wimbledon matches of the last qualifying round in 2019, 2022 and 2024 (16, 16 and 15) are recorded as best of three, though their scores show best of five. In the other years the record agrees with the scores. Stage 0 keeps the source's `best_of`; Stage 1's Elo does not use it; Stage 2 reads best-of from the score.
3. **Sackmann's point-by-point files.**
   * Eight editions (the Australian Open and Roland Garros 2018–2021) leave the games columns blank.
   * Three (Roland Garros 2020, the Australian Open and Roland Garros 2021) write "GAME" for a game's last point.
   * 436 matches end early (276 men's, 160 women's) and 124 disagree with the replay on the score, games or server (75 and 49) (`file_notes`, `matches`).
4. **The Stage 0 audit's P2** (break counts that do not add up in 0.37% of men's and 1.67% of women's evaluation box scores) feeds the break-point measures here; not corrected.

## Decisions for the owner

1. **Retirements.** Stage 2 sets them aside (5,221 men's, 1,005 women's) and reports them only where they say something: 8.01% (men) and 8.28% (women) of those with a box score went to the player who won fewer points. Their box scores cover part of a match a retirement decided. Agree?
2. **The floor.** The plug-in floor the stage asked for (0.237 and 0.194 on the 2022–2026 matches with odds) is far below a corrected floor from the pure-luck replay (0.426 and 0.421). With the corrected floor, a coin's uncertainty splits 16% known before, 23–24% on the day, 61% luck. Adopt the corrected floor and this split as the study's reading for the summary? It rests on the iid model and the de-noising, and the replay matches the real data on the measures above.
3. **Deciding-set rules found only in the scores.** Roland Garros qualifying 2017–2021 (a 7-point tiebreak at 6-6) and Australian Open qualifying 2018 (a tiebreak at 6-6, length assumed 7 points). Accept, or confirm against the tournaments' records? They matter only for qualifying matches that reach a deciding set in those draws.
4. **Best of five at Wimbledon's last qualifying round** (problem 2). Correct `best_of` in Stage 0 from the score, so that later stages inherit it?
5. **The unreadable box-score count** (problem 1): drop that box score in Stage 0?
6. **For the Stage 4 candidate list** (the owner approves it before anything is computed). Which of these should be on it?
   * **Suggestion:** the men's break-point record, heavily shrunk (persistent but about 20% signal on 100 matches).
   * **Suggestion:** return play on big points from point-by-point data (tentative; Grand Slams only).
   * **Suggestion:** match length (best of five), already suggested in Stage 1.
   * **Leave off** (suggestion): tiebreak record and big-point play on serve, which are indistinguishable from luck.
7. **The women's points share decides less than pure luck predicts** (section 1). Investigate (within-match form, momentum) in a later stage, or leave it as an observation?

## Suggestions (not applied)

* **For the owner's aim of an edge from point-by-point data.** The point-by-point files show that big-point play on return may be a trait, and that a day's serve and return rates leave most of a match to scoring luck.
  * Any pre-match feature from point data would have to predict the *day's* rates better than the market does.
  * The "on the day" share bounds what that could gain: about 160 milli-log-loss on these matches, a ceiling no forecast reaches.
* **More point-by-point coverage.** The Grand Slam files stop at the 2024 Wimbledon and US Open, and hold no Australian Open or Roland Garros after 2021. Repository studies on point feeds (`docs/studies/official_point_feeds/`, `ao_rg_points/`) may extend them; not examined here.

## Limitations

* **Everything in-match.** Nothing here is a forecast; the regressions explain results with the match's own events.
* **The iid model** assumes each player wins each point on serve with one probability for the whole match. Real points are not quite like that: real matches play fewer tiebreaks than the replay, and the women's points share decides less than it predicts.
* **The de-noising** uses a normal prior per tour and surface, drawn independently for the two players of a match. The corrected floor inherits that choice. Taking the measured rates as true would put the floor at 0.348 (men) instead of 0.426, and the replay at those rates does not reproduce the real data.
* **Break points** are Sackmann's counts, as kept by Stage 0 (the audit's P2 applies). Aces are counted against first serves (3.99% are not, in the point-by-point files).
* **The WTA** is analysed from 2019, as the Brief sets for box scores, so its persistence results rest on fewer players (351 with 25+ matches a half).
* **Players are identified** by Stage 0's ids in the box-score part (Stage 1's women's split identities of 2026 split a few players) and by name in the point-by-point part.
* **95% ranges** treat matches, and players, as independent; they are somewhat too narrow.
