# Stage B: opponent-adjusted statistics, IOS ratings and who they were earned against

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: built 2 Oct 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md); the report section is Stage B in [report.html](report.html).

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/ufc_ideas/`: from `stageB_summary.json` (which carries the three parts' summaries and the rundown's headline tables) unless another file is named (`stageB_ranking.csv`, `stageB_vs_ratings_ranking.csv`, `stageB_adj_tuning.csv`, `stageB_ios_tuning.csv`). Improvements are in milli-log-loss (thousandths of log loss per match; a coin scores 693), positive is better; "given Elo" is the walk-forward gain over surface Elo alone on every scored season (men 2013–2026, women's box-score rows 2019–2026).

## The owner's question

> "Adjusted performance/defense stats and ios_ridge stats … Find the priors that work best for tennis for all of these stats. What's key is we need to find the significance on WHO these stats were generated on. If a player is coming up JUST short vs studs and crushing newbies, Elo isn't capturing this."

## In short

* **Observed. adjperf works in tennis, as a measure of current form.** Its best row, total points won averaged with a two-week half-life, gains **3.19** on Elo for the men (95% range 2.85–3.54) and **3.32** for the women (2.51–4.12): second, among this run's rows, only to the earlier study's serve and return ratings through the iid model, re-scored here (3.61 and 4.58), and ahead of the earlier study's best history form (the points matchup over the last 52 weeks, 1.55 and 1.59). In 2019–2026 it gains 3.88 (men) and 3.32 (women). The same feature over a whole career is worse than Elo alone (−0.14 and −0.08).
* **Observed. The priors that work for tennis:** a very short memory for the player's average (half-life h3 = 2 weeks; the Brief's grid stopped at 26 weeks, where the in-sample gain on total points was 1.199 against 2.693 for the men and 0.821 against 2.615 for the women), equal weight for every match (weighting by points or games lost on every grid), and almost any setting for the opponent's norm. **Inferred:** what adjperf adds to Elo is how well a player has played in the last few matches against what those opponents usually allow; Elo knows those results but not how well they were played.
* **Observed. adjdef is adjperf seen from the other side.** In tennis adjdef on a serve statistic is exactly adjperf on the matching return statistic (11 pairs; largest per-match difference 7.1e-15), so 33 of the 90 adjperf and adjdef columns are the same feature twice and are scored once. adjdef on the four statistics without a mirror adds at most 0.77 (men) and 0.87 (women), on break points faced per service game.
* **Observed. IOS, tuned as the Brief asked (on the next match's statistic), forecasts the statistic as well as the online ratings but carries less of the winner.** Serve points won: 2.640 against Stage 3's 2.649 milli-log-loss per point better than the surface average (men, 2019–2026) and 2.403 against 2.438 (women), on exactly Stage 3's points. Its points matchup gains 1.08 and 2.21 on Elo, against the online ratings' 3.61 and 4.58. With a shorter memory (diagnostics added after the first rundown, not tuned) the same matchup gains **3.72** for the men (4 weeks; 3.30–4.13) and **5.02** for the women (13 weeks; 4.16–5.88), the largest gains on Elo of this stage. **Inferred:** forecasting a statistic wants a long memory; predicting the winner beside Elo wants a short one.
* **Observed. Who the statistics were earned against: a population effect, not a player trait.** Within a player's season, the opponent-adjusted z of total points falls by 0.19 (men) and 0.17 (women) per 100 Elo points of the opponent. But a player's own gap between strong and weak opponents is almost all chance: its spread beyond chance is 0.11 (men) and 0.08 (women) against 0.41 and 0.45 of chance, and it carries from one season to the next at r = 0.08 and 0.09 (a player's level against strong opponents carries at 0.53 and 0.52). Splitting by opponent strength loses information: the best split row (against weak opponents, last 52 weeks: 1.43 and 0.74) is below the unsplit 52-week adjperf (1.78 and 1.91), and the contrast, the slope and the interaction rows gain between −0.46 and 0.25 on Elo. **Inferred:** in these data Elo is not missing a stable "comes up just short against the strong, crushes the weak" trait.
* **Observed. Given the closing odds, nothing clear.** The largest gains are 0.27 (men: adjperf of total points against the bottom third, last 52 weeks; 0.09–0.44) and 0.23 (women: adjperf of aces, decayed; 0.02–0.44), both above the family-wide line given the market and both "small" (under 1). The two-week adjperf of total points adds 0.14 (men) and −0.07 (women), the short-memory IOS matchups 0.13 and 0.01.
* **Observed. Beyond the ratings.** With Elo and the ratings through the iid model both in the model (refitted each season), the two-week adjperf of total points still adds 0.70 (men; 0.57–0.82) and 1.48 (women; 0.99–1.98), and of serve points 0.83 and 1.43; the short-memory IOS matchups add 0.50 (men) and 0.64 (women); the tuned IOS matchup makes it worse (−0.74 and −0.28).
* **Observed. No leak.** The three probes cut by date, event and round moved 0 of 247,920, 3,420,626 and 244,189 protected matches or player-rows; Part 1's deliberately leaky control moved at 32.
* **Found:** one box score with impossible break-point counts (W15 Malta 2025), and tournament dates that are not Mondays for 3% of matches (the as-of rule's "week"). Reported below, not fixed.
* **For the owner:** seven decisions, [at the end](#decisions-for-the-owner).

## What was built

| File | What it holds |
|---|---|
| `stageB_adj.parquet` (84 MB) | Per box-score player-match (573,142): the per-match z of every statistic, adjperf and adjdef, at the frozen constants |
| `stageB_adj_features.parquet` (129 MB) \| Per pool match: `adjperf_<s>|<form>` and `adjdef_<s>\|<form>` (15 statistics, three forms), A − B |
| `stageB_adj_tuning.csv` \| Every adjperf setting scored: 3,600 per tour and statistic for serve, return and total points won (the Brief's 800 flagged `in_brief_grid`) |
| `stageB_ios.parquet` (96 MB) | Per match of the table (872,704): A's and B's pre-match IOS offence (O) and defence (D) of eight statistics |
| `stageB_ios_features.parquet` \| Per pool match: `ios_O_<s>|single`, `ios_D_<s>\|single`, the points and games matchups, and three diagnostic points matchups |
| `stageB_ios_tuning.csv` | Every IOS setting: 72 per statistic and tour (the Brief's 40 flagged) |
| `stageB_split_features.parquet` (54 MB) | Per pool match: the opponent-strength features, and the recency diagnostic of adjperf |
| `stageB_features.parquet` (232 MB) \| The pool, the earlier study's ten re-scored columns, every Stage B feature and `p_ratings` |
| `stageB_ranking.csv`, `stageB_results.csv`, `stageB_null_copies.csv`, `stageB_results.json` | The harness's rundown of every row |
| `stageB_vs_ratings_*` (the same four) | Question (b), the leading rows against the ratings through the iid model |
| `stageB_catalog.json` | One entry per scored row, and one per alias |
| `stageB_adj_summary.json`, `stageB_ios_summary.json`, `stageB_split_summary.json` | Each part's constants, grids' flatness, diagnostics, probe and timings |
| `stageB_summary.json` | Everything the write-up and the report quote |

Code in `src/eda/ufc_ideas/`, run from the repository root in this order (times measured with the other stages running beside):

* `stageB_common.py`: shared pieces (the statistics, the step-1 pair index, as-of sums, the tuning score).
* `stageB_adjperf.py`: Part 1, adjperf and adjdef; 23 minutes (one process, two BLAS threads).
* `stageB_ios.py`: Part 2, the IOS ridge; 16 minutes (five worker processes).
* `stageB_split.py`: Part 3, who the statistics were earned against; 6 minutes.
* `stageB_rundown.py`: the harness and the direct questions; 9 minutes (five worker processes).
* `report_stageB.py`: the report section.

Tests: `test/ufc_ideas/test_stageB.py` (10 tests, all passing): the time rule of the step-1 history, its weighted moments, steps 1–3 and the mirror identity on a hand-made history against a row-by-row reading, the IOS solve against a dense least squares, its incremental step and time rule, the recency diagnostic and the opponent-strength split.

Five Parquet files are over 50 MB (sizes in the table); git ignores Parquet, and they are not yet listed in `data/LARGE_FILES.md`, which this stage may not edit.

## Terms used here

**Tennis.** A *serve point* is a point a player serves; *serve points won* is the share they win, *return points won* the share of the opponent's serve points they win, *total points won* the share of all points. A *hold* is a service game won, a *break* a return game won. A *break point* is a point that would give the returner the game; the server *saves* it, the returner *converts* it. An *ace* is a serve the returner does not touch; a *double fault* is two missed serves, a lost point. *First serves in* is the share of first serves that land; *first-serve* and *second-serve points won* are the shares won after each. The *surface* is hard, clay or grass. The *main tour* is the Grand Slam to 250 main draws; below are the Challenger (men) and WTA 125 (women) events and the ITF events. A *round robin* is a group stage whose matches are played together. *Surface Elo* is the earlier study's Elo rating on the match's surface (retirements counted).

**This stage, and the UFC terms.**

* **adjperf** (adjusted performance): a player's statistic in a match, scored against what that opponent usually *allows* on it.
* **adjdef** (adjusted defence): how far the player held the opponent *below the opponent's own usual* value of the statistic.
* **z**: the match's value (on the log-odds scale) minus the opponent's norm, divided by the opponent's MAD, clipped to ±4.
* **MAD** (mean absolute deviation): the opponent's average distance from their own weighted mean, a measure of how much they vary from match to match.
* **Steps 1–3** (the UFC layer-2 pipeline): 1, the opponent's norm and MAD from the opponent's earlier matches; 2, the per-match z; 3, the player's average of z over their earlier matches.
* **K1, K3** (the UFC "K prior"): the shrinkage, in typical matches, toward the tour's average (step 1) or toward 0 (step 3). With few matches a player's value stays near the prior.
* **h1, h3**: half-lives, in weeks: a match counts half as much after h weeks (∞ is no decay).
* **τ** (the UFC exposure exponent): weights each match by its units (serve points, games…) to the power τ; 0 counts every match the same.
* **The forms**: *last 52 weeks* (no decay, the last year only), *decayed* (half-life h3), *career*.
* **IOS** (implied offensive and defensive skill): per statistic, every match's log-odds value ≈ the server's offence O minus the returner's defence D, solved jointly over every earlier week by ridge regression; **κ** is the ridge, in typical matches, pulling every rating toward the average. A higher D holds servers down, so a player's D on serve points won is their return rating.
* **Snapshot**: a solve of the ridge with the observations of earlier weeks; one per tournament date. The **incremental step** adds the same event's earlier rounds to each player's own O and D, everything else held at the snapshot.
* **Mirror**: a return statistic is the same quantity as a serve statistic seen from the other player (return points won is one minus the opponent's serve points won).
* **Strong, weak**: an opponent whose pre-match surface Elo is above (strong) or at or below (weak) the median of main-tour players in 2010–2018; the **thirds** split at its terciles.
* **The harness's terms** (the earlier study's, unchanged): *walk-forward* (each season fitted on earlier seasons), *given Elo* (added to surface Elo), *given the market* (added to the closing odds), the *null band* (20 shuffled copies), the *family-wide line* and the *reading* (finding, possible, no sign, worse).

## The design and the time rule

**Data.** The earlier study's player-match table (`stage4_features.load_rows`, two rows per match), the Stage 4 pool of 255,123 evaluation-level matches (side A random), and as history every completed standard-format match with a box score at any level from 2010: 573,142 player-matches. Each match's statistic is read as (x + ½) / (d + 1) on the log-odds scale (the log scale for break points faced per service game) and centred on the tour's average on its surface (Stage 3's averages, 2010–2018, as Stage 4 used them).

**Part 1, adjperf and adjdef.** For 15 statistics, steps 1–3 as defined above, the UFC pipeline's `features/v4/layer2.py` rebuilt for tennis. The opponent's norm in step 1 is the weighted mean over the opponent's earlier matches of what their opponents produced against them (adjperf) or what they produced themselves (adjdef), shrunk with K1; their MAD likewise, shrunk toward the population's MAD (player-seasons of 2010–2018, each around its own mean). Step 1 needs each target's own mean before the deviations, so it runs on an explicit index of 88,315,944 (target, earlier match) pairs, built and read in chunks; its sums equal the earlier study's as-of helper to 3e-13. The MAD floor (0.05) never binds; 3,230 of the men's 394,968 and 1,178 of the women's 178,174 total-points z sit at the ±4 clip.

**Part 2, IOS.** For eight serve-side statistics (serve points won, aces, double faults, first serves in, first- and second-serve points won, holds, break points saved; the return side is the same observations seen from the returner), the UFC `add_ios_ridge_stats` rebuilt: a Jacobi-preconditioned conjugate gradient, warm-started, on the sparse normal equations, with running totals kept in time-scaled units so that a snapshot costs only its new observations and the solve (9.5 to 17.1 iterations per snapshot on average; every snapshot converged).

**Part 3, who against.** Part 1's per-match adjperf z of total, serve and return points won, averaged separately over matches against strong and weak opponents (and thirds), the player's own strong-minus-weak contrast, the within-player slope of z on the opponent's Elo, results above Elo's expectation against strong and weak opponents, and the interaction with this match's opponent's strength.

**The time rule.** A feature for a match uses only the player's (or the opponent's) earlier weeks and the same event's earlier rounds; never the match itself, another match of the same round, or another event of the same week. Part 1's pair index takes exactly those rows (tested on a round robin, two events of one week and an earlier round); IOS snapshots use earlier weeks only, and the incremental step only the same event's earlier rounds (tested); Part 3 uses the earlier study's as-of helper. Each part has its own probe (below).

## The priors chosen, and how flat the grids are

**adjperf** was tuned per tour on serve, return and total points won, by the in-sample log-loss improvement of a logistic regression on [Elo, the feature] over Elo alone on the evaluation matches of 2013–2018, in two steps (step 1's constants with step 3 at a 52-week half-life and K3 = 5, then step 3's), then frozen. The constants follow the skill a row measures: serve skill (adjperf on a serve statistic, adjdef on a return statistic) takes serve points' constants, return skill return points', the whole match total points'.

**Observed** (`stageB_adj_tuning.csv`; gain in milli-log-loss on Elo, in-sample, decayed form):

| Tour | Statistic | h1 (weeks) | K1 | τ | h3 (weeks) | K3 | Gain | Rank of 3,600 | The Brief's grid: h3, K3 | Gain |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| ATP | serve points won | 104 | 2 | 0 | 2 | 10 | 2.312 | 8 | 26, 2 | 0.684 |
| ATP | return points won | 52 | 2 | 0 | 2 | 160 | 1.092 | 3 | 26, 10 | 0.229 |
| ATP | total points won | 104 | 2 | 0 | 2 | 10 | 2.693 | 2 | 26, 10 | 1.199 |
| WTA | serve points won | 26 | 2 | 0 | 2 | 20 | 2.106 | 9 | 26, 2 | 0.724 |
| WTA | return points won | ∞ | 10 | 0 | 2 | 160 | 1.110 | 40 | 26, 2 | 0.109 |
| WTA | total points won | ∞ | 20 | 0 | 2 | 20 | 2.615 | 27 | 26, 2 | 0.821 |

* **Observed. The Brief's grid chose its own edge every time** (h3 = 26 weeks, its shortest, for every tour and statistic; K1 and K3 at their smallest for most). Extended twice (disclosed in the code), the choice moved to h3 = 2 weeks for every tour and statistic; 1 week was tried and is worse.
* **Observed. The step-3 half-life matters most** (the best gain at each h3, the other constants free; men's total points): 2.524 at 1 week, 2.697 at 2, 2.569 at 4, 2.091 at 8, 1.684 at 13, 1.213 at 26, 0.914 at 52, 0.736 at 104, 0.641 at 208 and 0.545 with no decay.
* **Observed. Weighting by units hurts:** τ = 0 beats τ = 1 on every grid (2.697 against 2.466 here).
* **Observed. The opponent's norm hardly matters:** from 2.626 to 2.697 across h1 and from 2.617 to 2.697 across K1. **Inferred:** in tennis how recently a player played matters far more than how the opponent's norm is set.
* **Observed. Return points won take the largest K3 tried (160)** on both tours; there the shrunk average is close to its limit, a decayed sum of z (for the men 1.091 at K3 = 40, 1.094 at 160).
* **Observed. Flatness.** Of the 3,600 settings per statistic, 67 to 236 lie within 0.1 milli-log-loss of the best; the two-step choice ranks between 2nd and 40th of 3,600.

**IOS** was tuned per statistic and tour on the next match's log loss per unit of the statistic (2013–2018, observations to 2018, weekly snapshots: a run takes 1–2.5 s, so the four-weekly fallback the Brief allowed was not needed).

**Observed** (`stageB_ios_tuning.csv`; milli-log-loss per unit better than the tour's surface average; the tuning window and 2019–2026, with the incremental step):

| Statistic | ATP: h (weeks), κ, τ | 2013–18 | 2019–26 | WTA: h, κ, τ | 2013–18 | 2019–26 |
|---|---|---:|---:|---|---:|---:|
| serve points won | 52, 1, 1 | 3.185 | 2.641 | 52, 1, 1 | 2.258 | 2.398 |
| aces | 26, 1, 0 | 7.822 | 7.614 | 52, 1, 0 | 6.596 | 6.567 |
| double faults | 52, 3, 0 | 1.412 | 1.618 | 52, 3, 1 | 2.427 | 2.461 |
| first serves in | 26, 3, 1 | 2.463 | 2.744 | 26, 3, 1 | 4.155 | 4.321 |
| first-serve points won | 52, 1, 1 | 4.515 | 4.081 | 104, 3, 1 | 3.918 | 4.163 |
| second-serve points won | 104, 3, 1 | 2.164 | 1.736 | 104, 10, 1 | 1.386 | 1.579 |
| holds | 104, 1, 1 | 14.481 | 11.977 | 104, 3, 1 | 10.138 | 12.926 |
| break points saved | ∞, 30, 1 | 1.664 | 1.384 | 208, 30, 1 | 1.275 | 1.421 |

* **Observed. Every IOS choice lies inside the grid.** The Brief's grid chose its edges for most statistics, so it was extended (h = 13 weeks, κ = 0.3 and 100); no extended value was chosen, so the constants are the Brief's grid's own choices.
* **Observed. κ matters:** for the men's serve points won the gain falls from 3.185 at κ = 1 to 2.007 at κ = 100; for their break points saved κ = 0.3 is 1.603 worse than the average and κ = 30 is best. Weighting by units (τ = 1) helps a little for most statistics.
* **Observed. Memory:** half-lives of 26–52 weeks for the serve style (aces, first serves in, double faults), 52–104 for serve and return skill and holds, 208–∞ for break points saved, as Stage 3 found for the same forecasts.
* **Observed. The incremental step helps:** with it, the men's serve points won score 2.641 per point in 2019–2026 against 2.579 from the weekly snapshot alone, and aces 7.614 against 7.369.

## The rundown given Elo

**Observed.** 127 rows per tour (254 in all): 48 adjperf (45 forms and statistics, 3 recency diagnostics), 12 adjdef, 21 IOS (16 single ratings, 2 matchups, 3 diagnostics), 36 opponent-split and the earlier study's 10. The family-wide line given Elo is 6.92 standard deviations of the shuffled copies (men) and 6.30 (women). Readings given Elo: 58 findings, 9 possible, 11 no sign, 49 worse (men); 53, 21, 24 and 29 (women).

### Which channel adds most, statistic by statistic

**Observed.** Each cell is the best form's gain on Elo; bold is the statistic's winner. For a return statistic, "IOS own" is the D rating of its serve mirror (returning well is holding servers down) and "IOS allowed" is the mirror's O.

| Statistic | ATP: Stage 4 adjusted | adjperf | adjdef | IOS own | IOS allowed | WTA: Stage 4 adjusted | adjperf | adjdef | IOS own | IOS allowed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| serve points won | −0.13 | **2.78** | 1.17 | −0.22 | −0.07 | 0.15 | **2.97** | 1.08 | 0.70 | 0.20 |
| first-serve points won | −0.12 | **1.75** | 0.94 | −0.23 | 0.15 | 0.10 | **1.90** | 0.91 | 0.08 | −0.26 |
| second-serve points won | −0.08 | **1.46** | 0.74 | −0.42 | −0.21 | 0.16 | **1.66** | 0.38 | 0.26 | 0.07 |
| aces per serve point | −0.02 | **0.86** | 0.44 | 0.18 | 0.58 | 0.01 | **0.73** | 0.06 | 0.22 | −0.08 |
| double faults per serve point | −0.14 | **0.18** | 0.00 | −0.07 | 0.01 | −0.01 | **0.25** | 0.00 | 0.00 | 0.02 |
| first serves in | −0.01 | **0.02** | 0.00 | 0.00 | −0.08 | 0.13 | **0.16** | −0.01 | 0.08 | −0.02 |
| service games held | −0.15 | **1.82** | 0.86 | −0.69 | −0.39 | 0.05 | **2.48** | 1.00 | 0.83 | 0.25 |
| break points saved | −0.10 | **0.11** | 0.07 | −0.37 | −0.05 | −0.02 | **0.44** | 0.08 | −0.10 | −0.06 |
| break points faced per service game | −0.10 | **1.94** | 0.77 | – | – | 0.00 | **1.63** | 0.87 | – | – |
| return points won | 0.12 | 1.17 | **2.78** | −0.07 | −0.22 | 0.04 | 1.08 | **2.97** | 0.20 | 0.70 |
| return games won (breaks) | 0.05 | 0.86 | **1.82** | −0.39 | −0.69 | −0.03 | 1.00 | **2.48** | 0.25 | 0.83 |
| break points converted | −0.02 | 0.07 | **0.11** | −0.05 | −0.37 | −0.02 | 0.08 | **0.44** | −0.06 | −0.10 |
| return points won against the first serve | 0.15 | 0.94 | **1.75** | 0.15 | −0.23 | −0.02 | 0.91 | **1.90** | −0.26 | 0.08 |
| return points won against the second serve | 0.03 | 0.74 | **1.46** | −0.21 | −0.42 | −0.01 | 0.38 | **1.66** | 0.07 | 0.26 |
| total points won | 0.27 | **3.19** | 3.19 | – | – | 0.29 | **3.32** | 3.32 | – | – |

* **Observed. adjperf wins every serve statistic and total points won on both tours** (10 of 15 statistics). The five return statistics are won by "adjdef", which for them is exactly the mirror serve statistic's adjperf; adjperf proper on return statistics adds 0.07–1.17 (men) and 0.08–1.08 (women). Serve-side adjperf carries more than return-side adjperf: serve points 2.78 and 2.97 against return points 1.17 and 1.08.
* **Observed. Stage 4's opponent-adjusted form** (career, restated against a typical opponent with Stage 3's ratings) gains between −0.15 and 0.29 here: beaten by adjperf for every statistic.
* **Observed. IOS single ratings** add little on Elo (−0.69 to 0.58 for the men, −0.26 to 0.83 for the women); the points matchup through the iid model does better (1.08 and 2.21), the games matchup −0.51 and 1.67 (`stageB_ranking.csv`).
* **Inferred.** The channel that wins is the one that weights the latest matches most; the career forms lose (adjperf of total points over a career: −0.14 and −0.08; of serve points −0.27 and −0.23).

### The ten strongest rows per tour

**Observed** (`top10_given_elo`):

| # | Men | Given Elo | 95% range | 2019–26 | 2022–26 | Given market |
|---:|---|---:|---|---:|---:|---:|
| 1 | IOS points matchup (diagnostic: h 4 weeks) | 3.72 | 3.30 to 4.13 | 4.95 | 4.49 | 0.13 |
| 2 | Serve and return ratings through the iid model (earlier study) | 3.61 | 3.04 to 4.18 | 4.28 | 4.11 | −0.06 |
| 3 | IOS points matchup (diagnostic: h 13 weeks) | 3.42 | 2.92 to 3.92 | 5.12 | 4.56 | 0.10 |
| 4 | adjperf: total points won (decayed) | 3.19 | 2.85 to 3.54 | 3.88 | 3.49 | 0.14 |
| 5 | adjperf: serve points won (decayed) | 2.78 | 2.45 to 3.12 | 3.31 | 3.27 | 0.20 |
| 6 | adjperf: total points won (decayed, earlier weeks) | 2.09 | 1.81 to 2.38 | 2.74 | 2.47 | 0.11 |
| 7 | adjperf: break points faced per service game (decayed) | 1.94 | 1.65 to 2.23 | 2.30 | 2.41 | 0.13 |
| 8 | adjperf: service games held (decayed) | 1.82 | 1.55 to 2.08 | 2.20 | 2.22 | −0.03 |
| 9 | adjperf: total points won (last 52 weeks) | 1.78 | 1.42 to 2.15 | 2.95 | 2.68 | 0.06 |
| 10 | adjperf: first-serve points won (decayed) | 1.75 | 1.48 to 2.02 | 2.04 | 2.12 | 0.14 |

| # | Women | Given Elo | 95% range | 2022–26 | Given market |
|---:|---|---:|---|---:|---:|
| 1 | IOS points matchup (diagnostic: h 13 weeks) | 5.02 | 4.16 to 5.88 | 4.42 | 0.01 |
| 2 | IOS points matchup (diagnostic: h 4 weeks) | 4.58 | 3.75 to 5.42 | 3.95 | 0.01 |
| 3 | Serve and return ratings through the iid model (earlier study) | 4.58 | 3.64 to 5.52 | 4.06 | −0.01 |
| 4 | adjperf: total points won (decayed) | 3.32 | 2.51 to 4.12 | 2.85 | −0.07 |
| 5 | adjperf: serve points won (decayed) | 2.97 | 2.21 to 3.73 | 2.85 | 0.11 |
| 6 | adjperf: service games held (decayed) | 2.48 | 1.80 to 3.16 | 2.36 | −0.01 |
| 7 | IOS points matchup through the iid model (as tuned) | 2.21 | 1.52 to 2.90 | 2.05 | −0.01 |
| 8 | IOS points matchup (diagnostic: κ 10) | 1.93 | 1.26 to 2.59 | 1.90 | −0.01 |
| 9 | adjperf: total points won (last 52 weeks) | 1.91 | 1.26 to 2.56 | 1.50 | −0.01 |
| 10 | adjperf: first-serve points won (decayed) | 1.90 | 1.29 to 2.52 | 1.72 | 0.10 |

Every one of the twenty is a finding: it clears the family-wide line given Elo and gains in at least three eras; all but one (the men's 52-week total points, 3 of 4) gain in every era scored (four for the men, three for the women, whose box-score rows start in 2019). The women's 2019–2026 window is all their scored seasons, so their table leaves it out.

**The IOS diagnostics** were added after the first rundown showed the tuned IOS trailing the online ratings given Elo while forecasting serve points as well; only the memory (4 or 13 weeks) or the ridge (κ = 10) was changed from the tuned constants, and nothing was tuned on the results. They forecast serve points worse (2019–2026: 1.440 and 2.365 per point for the men at 4 and 13 weeks, against 2.641 tuned) and alone they are weaker (31.88 better than a coin for the men's 4-week matchup, against 72.81 tuned), but they add far more to Elo. **Inferred:** the winner beside Elo is helped by the part of a player's level that moves from week to week, which a forecast of the statistic smooths away.

**The recency diagnostic** (adjperf of the decayed form with the same event's earlier rounds left out, on the same matches): total points 2.09 (men) and 1.83 (women) against 3.19 and 3.32; serve points 1.74 and 1.79 against 2.78 and 2.97. **Inferred:** a good part of the two-week adjperf's gain comes from the same event's earlier rounds, and the larger part from the weeks before.

**How new is it?** (`correlations`, evaluation matches, Pearson). The two-week adjperf of total points correlates 0.24 (men) and 0.22 (women) with Elo's log-odds, 0.25 and 0.22 with the earlier study's games-weighted Elo, 0.25 and 0.23 with the sets played over the last 14 days and 0.43 and 0.35 with the ratings through the iid model. The tuned IOS matchup correlates 0.92 and 0.94 with the ratings through the iid model and 0.83 and 0.84 with Elo.

### The earlier study's rows, re-scored in this run

**Observed** (`earlier_rows`): every re-scored row reproduces the earlier study's own figure to the third decimal (`earlier_reproduced`, 20 of 20).

| Row | ATP given Elo | 2022–26 | Reading | WTA given Elo | 2022–26 | Reading |
|---|---:|---:|---|---:|---:|---|
| Serve and return ratings through the iid model | 3.61 | 4.11 | finding | 4.58 | 4.06 | finding |
| Serve against return: points (last 52 weeks) | 1.55 | 2.26 | finding | 1.59 | 1.20 | finding |
| Total points won (last 52 weeks) | 1.33 | 2.05 | finding | 1.39 | 1.04 | finding |
| Serve rating | 1.15 | 1.38 | finding | 1.87 | 1.59 | finding |
| Return rating | 0.66 | 0.62 | finding | 0.84 | 0.75 | finding |
| Serve points won (last 52 weeks) | 0.56 | 0.79 | finding | 0.89 | 0.65 | finding |
| Serve against return: points (opponent-adjusted) | 0.23 | 0.14 | possible | 0.45 | 0.67 | possible |
| Return points won (last 52 weeks) | 0.21 | 0.37 | finding | 0.09 | 0.09 | possible |
| Return points won (opponent-adjusted) | 0.12 | 0.00 | finding | 0.04 | 0.08 | possible |
| Serve points won (opponent-adjusted) | −0.13 | −0.02 | worse | 0.15 | 0.28 | possible |

## Given the market

**Observed** (`top10_given_market`): no row gains 1 milli-log-loss on the closing odds.

| Row | Tour | Given market | 95% range | Clears the line | 2022–26 | Given Elo |
|---|---|---:|---|---|---:|---:|
| adjperf total points won, against the bottom third (last 52 weeks) | ATP | 0.27 | 0.09 to 0.44 | yes | 0.44 | 1.18 |
| adjperf: serve points won (decayed) | ATP | 0.20 | −0.13 to 0.53 | no | 0.43 | 2.78 |
| adjperf total points won, against weak opponents (last 52 weeks) | ATP | 0.16 | −0.01 to 0.34 | no | 0.27 | 1.43 |
| adjperf: aces per serve point (decayed) | WTA | 0.23 | 0.02 to 0.44 | yes | 0.22 | 0.73 |
| adjperf: second-serve points won (decayed) | WTA | 0.13 | −0.05 to 0.31 | no | 0.19 | 1.66 |
| adjperf: serve points won (decayed) | WTA | 0.11 | −0.20 to 0.42 | no | 0.25 | 2.97 |

* The leaders given Elo add little or nothing on the market: the two-week adjperf of total points 0.14 (men) and −0.07 (women), the 4-week IOS matchup 0.13 (men), the 13-week 0.01 (women).
* **Inferred:** the market already prices a player's recent form. The two rows above the line given the market (a men's split row, the women's aces) are small, of the size the earlier study found for its load and ranking rows, and not the rows that lead given Elo.

## Who the statistics were earned against

**Observed** (`split`). The line between strong and weak opponents is a pre-match surface Elo of 2,067 (men) and 2,072 (women), the median of main-tour players in 2010–2018 (terciles 1,992 and 2,136; 2,002 and 2,141); 19% (men) and 35% (women) of the box-score matches are against strong opponents.

**A population effect.** Within a player-season (2010–2018), the opponent-adjusted z of total points falls 0.19 (men) and 0.17 (women) per 100 Elo points of the opponent (`population_slope`).

**Not a player trait.** Per player-season (2013–2026, five or more matches against each group), the gap between the mean z against strong and against weak opponents:

| Tour | Statistic | Player-seasons | Mean gap (z) | Observed sd | Chance sd | True sd | Gap, season to season (r) | Against the strong, season to season (r) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ATP | total points | 3,438 | −0.55 | 0.43 | 0.41 | 0.11 | 0.08 | 0.53 |
| WTA | total points | 2,564 | −0.60 | 0.46 | 0.45 | 0.08 | 0.09 | 0.52 |
| ATP | serve points | 3,438 | −0.48 | 0.43 | 0.43 | 0.07 | 0.05 | 0.61 |
| WTA | serve points | 2,564 | −0.50 | 0.50 | 0.48 | 0.12 | 0.06 | 0.59 |
| ATP | return points | 3,438 | −0.48 | 0.44 | 0.44 | 0.06 | 0.02 | 0.54 |
| WTA | return points | 2,564 | −0.51 | 0.49 | 0.48 | 0.07 | 0.01 | 0.46 |

"Chance sd" is the spread the gaps would have from match-to-match noise alone; "true sd" what is left of the observed spread beyond it (the method of moments).

* **Observed.** Nearly every player does worse, in opponent-adjusted terms, against strong opponents than against weak ones (mean gap −0.48 to −0.60 z). The individual gap barely varies beyond chance, and it barely repeats between seasons, while a player's level against strong opponents repeats.
* **Inferred.** The mean gap is a property of the one-step adjustment, not of players: an opponent's "allowed" norm is set by whom that opponent usually plays, so a strong opponent's norm is made against stronger players than the average player, and a weak opponent's against weaker ones.

**The features, given Elo and given the market** (`split_rows`; total points, last 52 weeks unless named):

| Row | ATP given Elo | Reading | Given market | WTA given Elo | Reading | Given market |
|---|---:|---|---:|---:|---|---:|
| adjperf against strong opponents | 0.29 | finding | −0.04 | 0.68 | finding | −0.04 |
| adjperf against weak opponents | 1.43 | finding | 0.16 | 0.74 | finding | −0.01 |
| strong minus weak (the player's own contrast) | −0.03 | worse | 0.07 | −0.03 | no sign | −0.01 |
| strong minus weak (difference of the two shrunk means) | 0.13 | finding | 0.14 | −0.16 | worse | −0.02 |
| adjperf against the top third | 0.15 | finding | −0.09 | 0.48 | finding | −0.05 |
| adjperf against the bottom third | 1.18 | finding | 0.27 | 0.43 | finding | −0.01 |
| top third minus bottom third | −0.01 | no sign | 0.05 | −0.03 | no sign | −0.02 |
| slope on the opponent's Elo | −0.08 | worse | 0.02 | 0.03 | possible | 0.01 |
| strong-minus-weak gap when the opponent is strong | 0.02 | possible | 0.01 | 0.02 | no sign | −0.05 |
| the same, career | 0.17 | finding | −0.04 | 0.25 | finding | −0.01 |
| wins above Elo against strong opponents | 0.02 | possible | −0.01 | −0.02 | no sign | −0.07 |
| wins above Elo against weak opponents | −0.34 | worse | −0.06 | −0.13 | worse | −0.02 |
| strong minus weak (own contrast), career | −0.25 | worse | −0.01 | −0.32 | worse | 0.04 |
| slope on the opponent's Elo, career | −0.20 | worse | −0.02 | −0.06 | worse | −0.02 |

* **Observed.** The split rows that gain are the plain averages over one group (against weak opponents most), and each is below the unsplit 52-week adjperf of total points (1.78 men, 1.91 women). The contrasts (from −0.46 to 0.13 over their 20 rows), the slope (−0.20 to 0.03) and the wins above Elo against weak opponents (−0.34 and −0.13) add nothing or worse; the interaction gains 0.17 (men) and 0.25 (women) in its career form, small findings, and 0.02 over the last 52 weeks. Readings: 10 findings, 4 possible, 2 no sign and 20 worse of 36 (men); 9, 3, 8 and 16 (women).
* **Observed.** The player's own contrast and the difference of the two separately shrunk means correlate 0.84 (last 52 weeks) and 0.87 (career) for the men (`contrast_vs_naive_corr`); the second was kept as a reference row, since shrinking both means toward 0 makes the difference of a player with few strong opponents equal minus their mean against the weak.
* **Inferred. The answer to the owner's question.** Who the statistics were earned against matters, and the per-match z already weighs it: that is why adjperf beats raw recent statistics and Stage 4's adjusted forms. But a player's particular pattern ("just short against studs, crushing newbies") is not a lasting trait in these data, so a feature built on it adds nothing to Elo; the gain comes from recent form, measured against each opponent.

## Does anything add to the ratings through the iid model?

**Observed** (`vs_ratings`; `stageB_vs_ratings_ranking.csv`). The three strongest adjperf, adjdef and IOS rows per tour given Elo, the tuned IOS points matchup and the best IOS diagnostic, scored again two ways: through the harness with the ratings through the iid model as the only base (as the Brief asked), and with Elo and the ratings both in the model, refitted each season, against the same model without the row (the harness's walk and its shuffled copies).

| Tour | Row | Given Elo | Given the ratings | 95% range | Given Elo and the ratings | 95% range | Copies' best |
|---|---|---:|---:|---|---:|---|---:|
| ATP | adjperf: total points won (decayed) | 3.19 | −0.02 | −0.06 to 0.01 | 0.70 | 0.57 to 0.82 | 0.01 |
| ATP | adjperf: serve points won (decayed) | 2.78 | 0.08 | 0.04 to 0.12 | 0.83 | 0.69 to 0.97 | 0.02 |
| ATP | adjperf: total points won (decayed, earlier weeks) | 2.09 | −0.02 | −0.05 to 0.00 | 0.17 | 0.10 to 0.24 | 0.01 |
| ATP | IOS points matchup (as tuned) | 1.08 | 1.49 | 1.09 to 1.89 | −0.74 | −0.94 to −0.53 | 0.01 |
| ATP | IOS points matchup (diagnostic: h 4 weeks) | 3.72 | 0.01 | −0.09 to 0.12 | 0.50 | 0.40 to 0.61 | 0.01 |
| WTA | adjperf: total points won (decayed) | 3.32 | 0.40 | 0.09 to 0.71 | 1.48 | 0.99 to 1.98 | 0.07 |
| WTA | adjperf: serve points won (decayed) | 2.97 | 0.54 | 0.21 to 0.86 | 1.43 | 0.95 to 1.90 | 0.03 |
| WTA | adjperf: service games held (decayed) | 2.48 | 0.47 | 0.19 to 0.75 | 1.30 | 0.79 to 1.81 | 0.05 |
| WTA | IOS points matchup (as tuned) | 2.21 | 0.22 | −0.22 to 0.66 | −0.28 | −0.40 to −0.17 | 0.07 |
| WTA | IOS points matchup (diagnostic: h 13 weeks) | 5.02 | 0.06 | −0.02 to 0.15 | 0.64 | 0.44 to 0.84 | 0.04 |

"Copies' best" is the largest gain of 20 shuffled copies of the row given Elo and the ratings.

* **Observed.** Given Elo and the ratings together, the two-week adjperf rows still add 0.70–0.83 (men) and 1.30–1.48 (women), well above their copies; the short-memory IOS matchups add 0.50 and 0.64; the tuned IOS matchup, which correlates 0.92–0.94 with the ratings, makes the model worse.
* **Observed.** Given the ratings alone the picture differs: the men's adjperf rows add nothing (−0.02 to 0.08), the tuned IOS matchup 1.49. **Inferred:** the ratings already hold the men's recent form when they stand alone, and the tuned IOS restores some of what Elo would add; the joint model, which a combined test would use, is the relevant one.
* A first version of the joint test used one fixed season-by-season blend of Elo and the ratings as a single base; a fixed blend can be mis-weighted, which a feature then corrects, so it was replaced by the refit before anything was reported.

## The mirror: adjdef is adjperf seen from the other side

**Observed** (`adjperf.mirror`, `mirror_feature_checks`). For each of the 11 statistics with a mirror, adjdef was built through its own code path and compared with adjperf on the mirror: per-match z correlation 1.000000 on every pair, largest difference 7.1e-15; the stored features differ by at most 7.5e-09 (float32). **Inferred (and shown in the test `test_mirror_identity`):** it is an identity, not a near-match. adjdef of p on serve points won is (o's own serve norm − o's serve rate in the match) / o's MAD; o's serve rate is one minus p's return rate, and o's own serve norm is minus o's allowed return norm, so the expression is p's return adjperf exactly, with the same weights and the same priors. So 33 columns are aliases (`stageB_catalog.json`), and only adjdef on aces, double faults, first serves in and break points faced per game is new (best 0.77 men, 0.87 women).

## IOS beside Stage 3's online ratings

**Observed** (`ios.stage3_comparison`). Log loss per serve point, milli-log-loss better than the surface average, on exactly Stage 3's scoring set (the same matches and serve points; its surface-average log loss recomputed to the same value); Stage 3's figures are read from its JSON; 2013–2018 is in-sample for both.

| Tour | Window | Matches | IOS | Stage 3 | IOS minus Stage 3 |
|---|---|---:|---:|---:|---:|
| ATP | 2013–2018 | 59,559 | 3.184 | 3.083 | 0.101 |
| ATP | 2019–2026 | 87,532 | 2.640 | 2.649 | −0.009 |
| ATP | 2022–2026 | 62,397 | 2.716 | 2.724 | −0.008 |
| WTA | 2013–2018 | 20,844 | 2.272 | 2.315 | −0.043 |
| WTA | 2019–2026 | 33,244 | 2.403 | 2.438 | −0.035 |
| WTA | 2022–2026 | 22,946 | 2.452 | 2.464 | −0.012 |

* **Observed. As a forecast of serve points the batch solve is the same as the online ratings**: within 0.01 per point for the men out of sample, 0.01–0.04 worse for the women.
* **Observed. As a predictor of the winner given Elo it is not, as tuned** (1.08 and 2.21 against 3.61 and 4.58), **and it is with a short memory** (3.72 and 5.02, the diagnostics above).

## Probes and checks

* **Observed. Probes cut by date, event and round** (the earlier study's method: at 4 cut matches in 2026, on the slice from 2023, everything the cut may not see redrawn and the features rebuilt; a tolerance of 1e-9, the earlier study's, for the as-of sums' last bits):
  * Part 1: 0 of 247,920 protected matches changed (largest difference 6.7e-16); 37,434 later ones changed; a deliberately leaky control (the career form counting the match's own z) changed at 32.
  * IOS (serve points and holds, both tours, 4 cuts each): 0 of 3,420,626 protected player-rows changed (largest difference 2.2e-16).
  * Part 3: 0 of 244,189 protected matches changed (largest difference 1.1e-15); 41,698 later ones changed.
* **Observed. The earlier study's rows reproduce** to the third decimal (20 of 20).
* **Observed. IOS's solver:** every weekly snapshot converged (relative residual 1e-8); a test checks it against a dense least squares to 1e-7.
* **Tests:** 10, all passing (above).

## Problems found in the earlier study's data or code (reported, not fixed)

1. **A box score with impossible break-point counts** (`data_checks.counts_outside_0_to_d`): `wta|2025-W-ITF-MLT-2025-1|R16|wta:222061|wta:269267` (W15 Malta, 27 Oct 2025) records break points saved −1 of 5, and the opponent's converted 6 of 5. It is the only box score with a count outside 0..d among the 16 stored rates. A per-match log-odds value cannot be formed from it, and in a first IOS run it turned every later snapshot of the women's break points saved into missing values. Stage B leaves it out of those two statistics (as a missing box score would be); Stages 3 and 4 summed it as it is. It belongs with the Stage 0 audit's break counts that do not add up (P2).
2. **"Dates are tournament Mondays"** (`common.py`) **does not hold for 3% of matches** (`data_checks`): 26,019 of 872,704 matches carry another weekday (Grand Slams, two-week 1000s, team events), and the men's 1,164 distinct dates fall in 845 calendar weeks (the women's 1,055 in 844). The time rule compares dates, so an event that starts in the second week of a two-week event treats all of it as earlier, its late rounds included; 12,014 player-events start one to six days after the same player's earlier event (21,504 matches). A player's own history cannot leak this way (they cannot be in both events), and Stage 3's ratings and Stage 1's Elo follow the same rule. For the IOS joint solve, the late rounds of a two-week event reach other players' ratings through common opponents a few days early. **Inferred:** a small effect, the same for every rating and feature built on the as-of rule; not measured.
3. The earlier study's re-scored rows reproduce its numbers: no problem found in the harness.

## Limitations

* **In-sample constants, and grids extended after a first look.** Every constant was tuned on 2013–2018 (the women's box scores of those years have holes, the Brief's note). adjperf's grid was extended twice after its choices sat on the grid's edge, still on 2013–2018 only. The IOS diagnostics were added after the first rundown had been read (all seasons), with two memories and one ridge tried, none tuned. 2019–2026 is the clean window, and every table gives it.
* **adjperf's opponent norm is one step.** An opponent's "allowed" norm is set by whom that opponent usually plays, so a z mixes the player's skill with the opponent's league (the mean gap above). IOS solves everyone jointly.
* **IOS is least squares on per-match log-odds**, (x + ½) / (d + 1), not a binomial model, and has no newcomer prior: an unseen player is average, where Stage 3's ratings start a newcomer's serve below their return.
* **Strength is Elo's.** Strong and weak are read from surface Elo, a results-based rating; its errors enter the split.
* **The very short memory.** With a two-week half-life the decayed adjperf is mostly the last few matches. The probe shows no leak; Stage 4's "one match later" check was not repeated here.
* **Ranges treat matches as independent**, as in the earlier study; the shuffled copies are the more robust guard.
* **Two-week events and the time rule** (problem 2).

## Decisions for the owner

1. **The extended grids.** adjperf's best memory (h3 = 2 weeks) lies outside the Brief's grid (26 weeks at the shortest), and so do K1 = 2 and K3 = 0.5–160. Accept the extended choices, or hold to the Brief's grid (its own choices gain less in-sample: for total points won 1.199 against 2.693 for the men, 0.821 against 2.615 for the women)?
2. **What adjperf is.** In tennis it works as a measure of current form (the last few matches against what each opponent allows), not of long-run skill. Carry the two-week adjperf of total points won (and of serve points won) into Stage D's combined test, beside the ratings through the iid model, recent load and the games-weighted Elo?
3. **adjdef.** For every statistic with a mirror it is adjperf on the mirror, exactly; only aces, double faults, first serves in and break points faced per game are new. Keep adjdef only for those four, or drop it?
4. **IOS.** Keep the constants tuned on the next match's statistic (memory 26–208 weeks), or tune IOS on the winner as adjperf was (the diagnostics point to 4–13 weeks)? Keep the incremental step for the same event's earlier rounds?
5. **The opponent split.** No lasting "comes up short against the strong" trait was found. Close it, or test it again on a joint scale (IOS ratings in place of the one-step norm)?
6. **The bad box score** (problem 1): drop it in Stage 0?
7. **Two-week events and the time rule** (problem 2): keep the earlier study's rule, or use day-level match dates where a source has them?

## Suggestions (not applied)

* **Stage D:** the two-week adjperf and the short-memory IOS matchup with the ratings through the iid model, the games-weighted Elo and the load features in one model, against Elo and against the market.
* **Tune IOS on the winner given Elo** (as adjperf was), on 2013–2018, rather than on the statistic; the diagnostics suggest memories of 4–13 weeks.
* **A lag check for the two-week features** (Stage 4's "one match later"), to show how much of their gain is the latest match.
* **A two-step or iterated opponent norm** (the opponent's allowed rate restated for whom they played), or adjperf computed against IOS expectations, so that every z sits on one scale.
* **IOS with a binomial likelihood and a newcomer prior.**
