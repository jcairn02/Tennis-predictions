# Stage 1: how predictable is tennis?

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: built 30 Sep 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md); the report section is "How predictable is tennis?" in [report.html](report.html). Stage 0 and its [audit](audit_stage0.md) were read first. How the audit's findings bear on this stage is set out under [Problems found in earlier work](#problems-found-in-earlier-work-reported-not-fixed).

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/predictability_diagnostic/`: from `stage1_results.json` unless another file is named (`stage1_odds_summary.json`, `stage1_baselines_summary.json`, or a CSV).

## In short

* **Observed.** Scored by log loss (a coin scores 0.693; lower is better) on the evaluation matches of 2022–2026, surface Elo gets **0.615 for the men and 0.601 for the women**. The closing odds get **0.589 and 0.591** on the tour-level main draws that have odds; surface Elo gets 0.611 and 0.609 on the same matches.
* **Observed.** So the **room between a rating and the market** is **22.5 milli-log-loss for the men (95% range 19.1–25.8) and 18.8 for the women (15.5–22.1)** in 2022–2026, and 19.7 and 16.7 over 2013–2026. On matches with odds, surface Elo covers 78% (men) and 82% (women) of the distance from a coin to the market. The ranking alone covers about half of it (48% and 52%).
* **Observed.** The order market, surface Elo, ranking holds in every season on both tours. The room is wider after the tuning years (2019–2026: 23.0 and 19.1) than in them (2013–2018: 15.0 and 13.8).
* **Observed.** Counting retirements as results beats skipping them. Skipping makes surface Elo 1.6 (men) and 1.8 (women) milli-log-loss worse in 2022–2026, and overall Elo is still 1.2 and 1.3 worse on completed matches alone. Counted is the default kept (owner, 30 Sep 2026).
* **Observed.** For the men, surface Elo is over-confident at best of three and under-confident at best of five. Its favourites won 1.9 points less often than it said at best of three and 2.9 points more at best of five. Its room to the market is 25.1 at best of five against 18.4 at best of three. **Inferred:** Elo does not know how long a match is.
* **Observed.** 99.93% of tennis-data.co.uk's rows since 2010 link to a Stage 0 match, against 95.83% with `scan.py`'s method as it stands. Inside the weeks tennis-data covers, 99.5% of men's and 99.2% of women's tour-level evaluation matches have odds.
* **Found in earlier work, reported, not fixed.** 64 established women appear under a second id in Stage 0's rows from 25 May 2026, a problem the audit missed; it inflates the women's 2026 room from 24.4 to 33.8. Four "WTA 250" events look like WTA 125s. There are errors in tennis-data.co.uk, and flaws in `scan.py`'s tennis-data link.
* **For the owner.** Four decisions remain, [at the end](#decisions-for-the-owner). The three about Elo's details were closed at the suggested defaults on 30 Sep 2026 ([README](README.md#owner-decisions)).

## What was built

| File | What it holds |
|---|---|
| `stage1_odds.parquet` (3.3 MB) | One row per Stage 0 main-draw match at the levels tennis-data.co.uk could hold (92,745), keyed by `match_id`, linked or not. It holds the link method and the tennis-data row (file, row, date, round, names, comment); whether set scores, round and both rankings agree; each book's odds for A and B (average, Pinnacle, maximum, Bet365); the overround; and `p_avg_a` and `p_ps_a`, the normalised market probabilities that A wins |
| `stage1_odds_unlinked.parquet` | The 59 tennis-data rows of 2010 on that no Stage 0 match took, with the reason |
| `stage1_baselines.parquet` (74.6 MB) | One row per match (all 872,704), keyed by `match_id`. It holds `p_coin`, `p_rank` and `p_points` (evaluation matches); for each retirement rule (`_ret` counted, `_noret` skipped), each player's pre-match overall and surface Elo and rated-match counts (`elo_a_ret`, `elo_surf_b_noret`, `n_a_ret` and so on) and `p_elo_*`, `p_elo_surf_*` (every match); and `p_market`, `p_pinnacle` (evaluation matches with odds). Every probability is that side A wins |
| `stage1_elo_tuning.csv`, `stage1_elo_weights.csv` | The K grid and the surface-weight grid, with log loss over 2013–2018 |
| `stage1_rank_fits.csv` | The rank and points regressions: one coefficient per tour, season and input, with the training seasons and the rank given to unranked players |
| `stage1_logloss_cells.csv` | Tour × level × best of × surface × era: 199 cells with every baseline's log loss, on all matches and on the matches with odds, with the room and a directional-only flag |
| `stage1_calibration.csv` | Calibration bins, 2022–2026 |
| `stage1_odds_summary.json`, `stage1_baselines_summary.json`, `stage1_results.json` | Everything quoted here |

Code in `src/eda/predictability_diagnostic/`: `stage1_odds.py`, `stage1_baselines.py`, `stage1_results.py` and `report_stage1.py` (the report section). The page shell gained the series colours and chart styles. Tests: `test/predictability_diagnostic/test_stage1.py` (27 tests; 113 in the study, all passing). Run times: the odds 6 seconds, the baselines 5½ minutes (the tuning grid), the results 8 seconds, the report under a second. `stage1_baselines.parquet` is over 50 MB and is listed in [data/LARGE_FILES.md](../../../data/LARGE_FILES.md).

## Terms used here

* **Log loss.** For each match, minus the natural log of the probability the forecaster gave the player who won, averaged over matches. A coin (always 50%) scores ln 2 = 0.693; giving the winner 70% scores 0.357 on that match, giving them 30% scores 1.204. Lower is better. One **milli-log-loss** is 0.001.
* **Evaluation matches.** Set by the Brief and built in Stage 0: singles at the Grand Slams, Tour Finals, 1000s, 500s, 250s, Challenger / WTA 125, and their qualifying, 2013–2026, completed or retired (the player who advanced won). There are 155,130 men's and 60,321 women's.
* **Matches with odds**, or the market subset. Evaluation matches that have closing odds, which exist only for tour-level main draws (Grand Slams, Finals, 1000s, 500s and 250s): 31,683 men's and 32,178 women's. Every comparison with the market is made on these same matches.
* **Room.** Surface Elo's log loss minus the market's, on the same matches: how much a statistic added to a rating would have to gain to price matches as well as the closing odds.
* **Retirement.** A player stops during the match; the opponent advances and is recorded as the winner.
* **Best of three / five.** The first to win two sets, or three. Men's Grand Slam main draws are best of five; everything else here is best of three.
* **Favourite.** The player a baseline gives more than 50%. **Calibration** asks whether favourites given 70% win about 70% of the time.

## 1. Closing odds

### The source

tennis-data.co.uk publishes one workbook per tour and season: tour-level main-draw results with several bookmakers' odds. The dump holds ATP 2010–2017 and 2019–2026 (**there is no ATP 2018 file**) and WTA 2010–2026, all captured on 3 August 2026, 79,728 rows (ATP 39,915, WTA 39,813). Provider claims, from its notes (`data/raw/public_dump/tennis_data_couk/docs/notes.txt`): `AvgW`/`AvgL` are "average odds … as shown by Oddsportal.com", `PSW`/`PSL` are Pinnacle's, and "betting odds for matches generally represent the most recent before play starts". That the odds are closing odds is the provider's claim; this study does not verify it.

### Linking

**`scan.py`'s method, as it stands** (`scan_py_method` in the odds summary). Its tennis-data link (`measure_tennis_data`) reads tennis-data's "Surname I." names and every "surname span + first initial" form of the Stage 0 names as an ordered winner > loser pair. It takes the same tour, the match day from 7 days before to 20 days after the tournament's Monday, and the nearest week wins. Run on the Stage 0 matches, it links 76,406 rows (95.83%), leaves 31 ambiguous and 3,291 unlinked. merge_feasibility reported 95.0% on its provisional table.

**What Stage 1 changes, and why.** The method's own functions are reused (`td_key`, `td_variants`, `link`, `resolve`, `statuses`), with these corrections, as Stage 0 made for Tennis My Life:

1. **The nearest week misreads rematches.** A Saturday or Sunday final is one day before the next event's Monday and six after its own, so a pair who meet at events a week apart are linked to the wrong match. Run as it stands, the method gives 151 Stage 0 matches two rows each (302 rows), and 115 of its links agree on neither the set scores nor the round. Stage 1 ranks candidates by identical set scores, then an agreeing round, then the nearest date (`pick()`, as Stage 0's). It gives each Stage 0 match at most one row, and it requires identical set scores or an agreeing round. tennis-data numbers its early rounds ("1st Round"), so they are read against each event's own early rounds (a 128 draw's first round is R128, a 32 draw's R32).
2. **Names that differ between the sources.** A second pass links a row by one identical player on the same side, identical set scores and an agreeing (or unreadable) round, when exactly one Stage 0 match fits. It is the one-player anchor `scan.py` uses for Tennis My Life. The names it bridges are married names and other forms: tennis-data's "Gavrilova D." is Sackmann's "Daria Saville", "Zakopalova K." is "Klara Koukalova", "Kozlova K." is "Kateryna Baindl", "Makarova E." is "Kate Makarova", "Ramos-Vinolas A." is "Albert Ramos".
3. **Winner and loser exchanged.** `scan.py` counts these but does not link them; a third pass does. Most are retirements that tennis-data credits to the player who retired. A few are finals of the 2026 file whose result tennis-data had not yet recorded when it was captured (their comment is blank). The result used is always Stage 0's; the odds go to each player by name.
4. **Misdated rows.** A row dated more than a month before its file's season, or after it, takes the file's year. The ATP 2013 file dates Beijing and Tokyo 2013 in October 2012 (62 rows), and one WTA 2026 row is dated 2029.

| tennis-data rows, 2010 on | Rows |
|---|---:|
| Linked by the name pair | 76,495 |
| Linked by the one-player anchor | 3,155 |
| Linked with winner and loser exchanged | 19 |
| No name pair in the window | 57 |
| No date | 2 |
| **Linked** | **79,669 (99.93%)** |

**Checks on the links** (`verification_by_pass`). Each source gives both players' rankings at the tournament's start, so rankings test identity:

| Pass | Links | Identical set scores | Round agrees | Both rankings agree (within 3 places or 10%), where known |
|---|---:|---:|---:|---:|
| Name pair | 76,495 | 75,642 | 76,474 | 75,409 of 76,230 |
| One-player anchor | 3,155 | 3,155 | 3,155 | 3,072 of 3,140 |
| Winner exchanged | 19 | 13 (read the other way) | 19 | 18 of 19 |

**Observed.** A handful of anchor links pair names that are different people: "Mchale C." in tennis-data where Sackmann has Ana Ivanovic, with rankings 81 and 21. The sources then disagree about who played a match with identical scores and opponent. These are within the 68 anchor links whose rankings disagree.

**Unlinked, both sides kept.** The 59 unlinked tennis-data rows are in `stage1_odds_unlinked.parquet`. On the Stage 0 side, every main-draw match at the linked levels stays in `stage1_odds.parquet`, with its odds missing where no row linked (13,139 of 92,745, most of them team events, which tennis-data does not cover).

### Quotes

* **Observed.** Odds of 0 or 1.00 are not quotes and are treated as missing: 4 `AvgW`, 12 `PSW`, 1 `PSL`, 49 `B365W` and 6 `B365L` values.
* **Observed.** A pair of quotes is also not coherent when its overround lies outside 1.00–1.20. The **overround** is the sum of the two implied probabilities (1/odds). The median linked pair's is 1.058, and 98% lie between 1.043 and 1.070. Outside the range sit swapped or garbled values: Djokovic v Ruud, Rome 2020, average odds 5.05 and 17.00 where Pinnacle had 1.19 and 5.49. That removes 34 average pairs (27 below 1, 7 above 1.2) and 28 Pinnacle pairs.
* The market probability is 1/odds of each player **normalised to sum to one**, from the average close; Pinnacle's the same way.

### What has odds

**Observed** (`stage1_odds_summary.json`):
* Tour-level evaluation matches with a market probability: 31,683 of 34,834 men's (91.0%) and 32,178 of 32,848 women's (98.0%). Leaving out the men's 2018 season (2,639 matches) and the weeks from 27 July 2026, which the capture of 3 August misses or holds in part (420 and 483 matches), the figures are 99.5% and 99.2%.
* Events with no odds at all: every Next Gen ATP Finals (2017, 2019, 2021–2025, 15 matches each), and six WTA events filed as 250s: Bol 2016 and 2017, Zhengzhou 2017, Limoges 2019, Linz 2020, Cluj-Napoca 2021. Another 106 matches lack odds inside events that have them.
* Challengers, WTA 125s and all qualifying have no odds in any public file (the dump report), so they are scored by the other baselines only.

### Pinnacle

**Observed.** Pinnacle's odds thin out from October 2025. The last are in January 2026 on both tours: 71 of 238 linked men's rows and 101 of 265 women's that month, none from February. On the evaluation matches that have both (29,757 men's, 30,302 women's), the market average is 0.7 milli-log-loss worse than Pinnacle for the men (95% range 0.3–1.1) and 0.6 worse for the women (0.2–1.0). The two probabilities correlate at 0.998 and differ by 1.2 and 1.1 points on average. **Inferred:** the average is a fair continuous stand-in for the sharpest single book, at a cost of under one milli-log-loss.

## 2. The baselines

Every baseline gives the probability that side A wins, made before the match from earlier matches only. Side A is set by a hash of the match id (Stage 0), so it carries no information.

### Coin and ranking

* **Coin:** 0.5.
* **Ranking** and **ranking points.** A player's rank and points as of the tournament's start, from Stage 0 (Sackmann's files). One-input logistic regressions: on log(rank B) − log(rank A), and separately on log(1 + points A) − log(1 + points B). Each is fitted per tour and season on evaluation-level matches (completed or retired) of the seasons before it only: 2013 is fitted on 2010–2012, 2026 on 2010–2025. There is no intercept: side A is random, so the probability is one half when the inputs are level. The coefficients are steady: 0.79–0.86 (men) and 0.65–0.73 (women) for rank, 0.58–0.69 and 0.65–0.73 for points (`stage1_rank_fits.csv`).
* **Unranked players** (`stage1_baselines_summary.json`). An unranked player is given the rank one below the lowest rank seen on the tour in earlier seasons (men 1,977 in 2013 and 2,268 from 2016; women 1,245 in 2013 and 1,596 from 2023) and 0 points; a ranked player with no points recorded also gets 0 points. **Observed:** 5,508 men's and 1,114 women's evaluation player rows are unranked, in 5,261 and 1,074 matches (247 and 40 with both players unranked, which the ranking scores as even). Most are wildcards (Stage 0).

### Elo: the inherited scaffold, checked

`src/ratings/elo.py` implements FiveThirtyEight's tennis Elo: K = k0 / (n + offset)<sup>shape</sup>, with n the player's earlier rated matches (defaults 250, 5, 0.4). It keeps overall and per-surface tables, each updated with its own expectation, and blends them on the rating scale. **Checked:** its formulas are right, and are reused. The tests show the study's pass equals `elo.py`'s `SurfaceBlendElo.fit` to 1e-12 wherever no two matches are simultaneous. **Not used:** its `fit` updates row by row. A round robin's later matches then see its earlier ones, and one event of a week sees another. A test shows it: after one round-robin win the scaffold gives the player's second match more than 50%, where under the Brief's rule both are unseen. It also raises on an unknown surface and leaves retirements and walkovers to the caller.

### Elo as run here

* **History.** Every singles match of Stage 0 from 2010, at every level, team events and ITF included: 872,704 matches. Players arriving from the lower levels bring ratings, and every player starts at 1,500.
* **The time rule.** A player's rating for a match is their rating at the start of its week plus what their earlier rounds of the same event added. A round's updates wait for the next round of that event, and an event's reach the player's other events only after the week. This is exactly the Brief's rule (earlier events and earlier rounds of the same event only). **Walkovers** and matches of status "other" never move ratings.
* **Surface Elo.** Each player has a rating per surface (hard, clay, grass, carpet), moved only by matches on it. The prediction uses (1 − w) × overall + w × surface; when the surface is unknown (183 matches) it uses the overall rating alone.
* **Two retirement rules**, as asked: retirements counted as results (`_ret`) and skipped (`_noret`).

### Tuning

The K constants were tuned on the overall Elo's log loss over the evaluation matches of 2013–2018 only (64,208 men's, 25,676 women's). The grid had 270 settings per tour and rule (k0 from 150 to 1,200, offset from 0.5 to 10, shape from 0.3 to 0.8). The surface weight was then tuned on the same matches, 0 to 1 in steps of 0.05. Everything was then frozen. A first grid (k0 up to 400, offset from 1, shape up to 0.6) put the best at its corner for every tour and rule, so it was widened.

| Tour | Retirements | k0 | offset | shape | w | Log loss 2013–18 | FiveThirtyEight's K |
|---|---|---:|---:|---:|---:|---:|---:|
| ATP | counted | 600 | 2 | 0.6 | 0.30 | 0.5904 | 0.5926 |
| ATP | skipped | 1,200 | 10 | 0.7 | 0.30 | 0.5919 | 0.5937 |
| WTA | counted | 600 | 1 | 0.6 | 0.25 | 0.6019 | 0.6040 |
| WTA | skipped | 600 | 1 | 0.6 | 0.25 | 0.6030 | 0.6049 |

**Observed.** The best settings lie along a flat valley: a larger k0 trades against a larger shape, and 15–20 settings per tour and rule come within one milli-log-loss of the best. ATP with retirements skipped sits on the grid's edge, 0.01 milli-log-loss better than the best setting inside it (600, 2, 0.6). The four choices differ mainly for newcomers. K for a player with no rated match ranges from 239 to 600, but after 10 matches it is 135–147, after 100 matches 37–45, and after 500 matches 14–15. FiveThirtyEight's is 131, 85, 39 and 21. Tuning gained 2.1 milli-log-loss over FiveThirtyEight's constants on both tours. The surface blend gains a further 3.6 (men) and 2.8 (women) over the tuning years. **Inferred:** a newcomer's large K compensates for every player starting at 1,500, far above an ITF debutant's level.

### No look-ahead

* **Tests** (`test_stage1.py`): the pass equals the scaffold where nothing is simultaneous. On a hand-made history, its rated-match counts equal the Stage 0 as-of helper's, and its ratings follow the rule (qualifying before the main draw, round robins blind to each other, two events of a week blind to each other). On random histories with round robins and overlapping events, every sampled rating equals a fresh pass over only the matches the rule lets that match see, under both retirement rules.
* **A probe cut by date, event and round** (the audit's P3: the Stage 0 probe cuts by the table's order, which cannot see leaks between simultaneous matches). At each cut, every result the rule does not let the cut see is flipped at random and the pass re-run. On the real history (6 cuts per tour and rule, 24 in all), 0 of 9,647,948 protected pre-match ratings changed (`stage1_baselines_summary.json`). The same probe catches a row-by-row Elo like the scaffold's (a test).
* **The rank regressions**: a test flips a later season's results and checks that earlier seasons' probabilities do not move.

## 3. How predictable is tennis?

### Headline

Log loss (lower is better; a coin 0.693). The left block is every evaluation match; the right block is the matches with odds only. Room is surface Elo minus the market, in milli-log-loss, with a 95% range from the per-match differences.

| Tour | Window | Matches | Ranking | Points | Elo | Surface Elo | With odds | Ranking | Surface Elo | Market | Room |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ATP | 2013–2026 | 155,130 | 0.633 | 0.633 | 0.608 | 0.605 | 31,683 | 0.631 | 0.599 | 0.579 | 19.7 (17.7–21.8) |
| ATP | 2013–2018 (tuning) | 64,208 | 0.619 | 0.619 | 0.590 | 0.587 | 13,019 | 0.611 | 0.580 | 0.565 | 15.0 (12.2–17.9) |
| ATP | 2019–2026 | 90,922 | 0.643 | 0.644 | 0.621 | 0.617 | 18,664 | 0.645 | 0.612 | 0.589 | 23.0 (20.2–25.8) |
| ATP | 2022–2026 (headline) | 64,887 | 0.641 | 0.639 | 0.619 | 0.615 | 12,352 | 0.643 | 0.611 | 0.589 | 22.5 (19.1–25.8) |
| WTA | 2013–2026 | 60,321 | 0.634 | 0.634 | 0.603 | 0.600 | 32,178 | 0.639 | 0.609 | 0.592 | 16.7 (14.8–18.6) |
| WTA | 2013–2018 (tuning) | 25,676 | 0.632 | 0.629 | 0.602 | 0.599 | 14,794 | 0.637 | 0.607 | 0.593 | 13.8 (11.2–16.4) |
| WTA | 2019–2026 | 34,645 | 0.636 | 0.637 | 0.604 | 0.601 | 17,384 | 0.640 | 0.610 | 0.591 | 19.1 (16.4–21.8) |
| WTA | 2022–2026 (headline) | 23,998 | 0.635 | 0.637 | 0.605 | 0.601 | 11,467 | 0.640 | 0.609 | 0.591 | 18.8 (15.5–22.1) |

**Observed.**
* Elo is 25.0 (men) and 30.8 (women) milli-log-loss better than the ranking over 2013–2026, and surface Elo a further 3.8 and 3.0 better than overall Elo.
* On the matches with odds of 2022–2026, the ranking is 50.1 (men) and 53.1 (women) milli-log-loss better than a coin, ranking points 58.3 and 53.7, Elo 77.1 and 80.9, surface Elo 81.7 and 83.8, and the market 104.2 and 102.6.
* **Tuning years.** 2013–2018 chose Elo's constants. Tuning gained 2.1 milli-log-loss there, so later seasons are the fairer test of Elo; the report shades the tuning years in its season chart.

### By level, 2013–2026

| Level | ATP matches | Ranking | Elo | Surface Elo | With odds | Market | Room | WTA matches | Ranking | Elo | Surface Elo | With odds | Market | Room |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Grand Slams | 6,951 | 0.549 | 0.531 | 0.524 | 6,312 | 0.497 | 25.2 | 6,965 | 0.597 | 0.564 | 0.560 | 6,830 | 0.545 | 17.1 |
| Tour Finals | 315 | 0.610 | 0.588 | 0.585 | 179 | 0.554 | 17.4* | 285* | 0.684 | 0.650 | 0.647 | 285 | 0.647 | 0.2* |
| 1000s | 7,883 | 0.644 | 0.617 | 0.613 | 7,122 | 0.593 | 17.6 | 8,048 | 0.650 | 0.614 | 0.612 | 7,848 | 0.599 | 14.5 |
| 500s | 5,625 | 0.631 | 0.600 | 0.598 | 5,191 | 0.579 | 17.4 | 5,444 | 0.657 | 0.627 | 0.624 | 5,367 | 0.608 | 17.3 |
| 250s | 14,060 | 0.670 | 0.640 | 0.634 | 12,879 | 0.612 | 19.2 | 12,106 | 0.644 | 0.626 | 0.624 | 11,848 | 0.606 | 18.0 |
| Grand Slam qualifying | 6,041 | 0.668 | 0.649 | 0.636 | – | – | – | 5,025 | 0.660 | 0.621 | 0.616 | – | – | – |
| Tour qualifying | 12,953 | 0.607 | 0.585 | 0.580 | – | – | – | 13,886 | 0.615 | 0.580 | 0.577 | – | – | – |
| Challenger / WTA 125 | 73,768 | 0.646 | 0.625 | 0.622 | – | – | – | 7,219 | 0.641 | 0.613 | 0.610 | – | – | – |
| Challenger / 125 qualifying | 27,534 | 0.605 | 0.569 | 0.566 | – | – | – | 1,343 | 0.610 | 0.552 | 0.547 | – | – | – |

\* Under 300 matches (with odds, for the room): directional only. The full tour × level × best of × surface × era cross is `stage1_logloss_cells.csv`: 199 cells, 133 with at least 300 matches, 65 with at least 300 matches with odds. The report has the same by best of, surface and era.

**Observed.**
* The men's Grand Slams are the most predictable level (surface Elo 0.524, the market 0.497), and men's Grand Slam qualifying the least (0.636).
* For the women, the most predictable level with at least 300 matches is Challenger / 125 qualifying (0.547), and the least are the 500s and 250s (0.624 each).
* Qualifying below the Grand Slams is more predictable than the main draw above it, on both tours.

### Best of five

**Observed.** The men's Grand Slam main draws are the only best-of-five matches. There surface Elo scores 0.527, against 0.608 at best of three (2013–2026). On the men's matches with odds of 2013–2026:
* at best of five, surface Elo's favourites won 73.8% where it gave them 70.9% on average (2.9 points more);
* at best of three, they won 65.3% against 67.1% (1.9 points less);
* the market's favourites won 2.0 and 0.4 points more than their price at best of five and three;
* the room is 25.1 milli-log-loss at best of five (95% range 20.4–29.9) against 18.4 at best of three (16.2–20.6).

**Inferred:** a longer match lets the stronger player's edge accumulate, but Elo gives one probability whatever the length, and learns mostly from best-of-three matches. **Suggestion** (for the Stage 4 candidate list, not applied): match length as an input.

### By season

**Observed.** In every season on both tours, on the matches with odds, the market is below surface Elo and surface Elo below the ranking; on all evaluation matches, surface Elo is below the ranking. A season's room, from 2019, ranges from 18.8 to 40.4 milli-log-loss for the men and from 15.0 to 33.8 for the women. The men's largest is 2020, the women's 2026 (see the Stage 0 problem below). On the matches with odds, from 2013–2018 to 2019–2026:
* the men's market went from 0.565 to 0.589 and surface Elo from 0.580 to 0.612;
* the women's market went from 0.593 to 0.591 and surface Elo from 0.607 to 0.610.

**Inferred:** the wider room after 2018 is not mainly the tuning years flattering Elo, since tuning moved Elo by 2.1 milli-log-loss. Later seasons have been harder for a rating than for the market, above all for the men.

### The room between Elo and the market, by level and era

Surface Elo minus the market, milli-log-loss, on the same matches (* under 300 matches: directional only; a negative room means Elo did better):

| Level | ATP 2013–16 | 2017–19 | 2020–21 | 2022–26 | WTA 2013–16 | 2017–19 | 2020–21 | 2022–26 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Grand Slams | 21.1 | 22.9 | 32.9 | 26.8 | 19.3 | 13.1 | 21.4 | 16.1 |
| Tour Finals | 23.3* | −15.2* | 46.0* | 13.8* | −7.4* | −24.0* | 4.0* | 39.0* |
| 1000s | 9.3 | 13.8 | 13.9 | 25.9 | 9.9 | 18.2 | 20.8 | 14.5 |
| 500s | 16.6 | 14.7 | 41.7 | 13.2 | 13.7 | 15.5 | 24.4 | 18.6 |
| 250s | 15.6 | 15.0 | 25.4 | 22.4 | 13.4 | 15.5 | 20.5 | 24.0 |

**Inferred.** This is the most room any statistic could fill *if the closing price is taken as the ceiling*. It is not a hard ceiling: the market is itself an estimate, and a statistic it underweights could in principle beat it. The 2020–21 cells (the seasons cut short in 2020, when ratings went months without results) are among the widest on both tours.

### How often the favourite won (descriptive)

**Observed.** Over all evaluation matches of 2013–2026, the better-ranked player won 63.9% of men's and 64.3% of women's matches (251 and 40 matches with no favourite left out). Surface Elo's favourite won 66.5% and 67.0%. On the matches with odds, the market's favourite won 69.0% and 67.7%; in 2022–2026, 68.0% and 67.7%. At the men's Grand Slams the market's favourite won 75.8%; the report's table has every level. How often a favourite wins says nothing about how well the probabilities were set; that is what log loss scores.

### Calibration, 2022–2026

**Observed** (`stage1_calibration.csv`, and the report's chart):
* In every band of the favourite's probability with at least 100 matches (bands 5 points wide), the share the favourite won is within 2.9 points of surface Elo's average probability for the men and 2.2 for the women. It is within 3.6 and 4.0 of the market's.
* Over all the matches with odds, surface Elo's favourites won 2.0 points less often than it said (men) and 0.2 less (women). The market's won 0.6 and 0.5 points more than their price.

**Inferred:**
* Neither is far from the diagonal, so the market's lead comes from separating likely winners from likely losers more sharply, not from Elo being systematically too bold or too timid. The men's best-of-three over-confidence above is the exception.
* The market's small lean is the direction of the favourite–longshot bias (outsiders' odds a little too short, favourites' a little too long).

### Retirements, both ways

Skipping retirements rather than counting them (milli-log-loss; positive means skipping is worse):

| Tour | Window | Elo | Surface Elo | Elo, completed matches only | Retirements among evaluation matches |
|---|---|---:|---:|---:|---:|
| ATP | 2013–2026 | +1.6 (1.3 to 1.8) | +1.4 (1.1 to 1.6) | +1.0 | 3.37% |
| ATP | 2022–2026 | +1.9 (1.4 to 2.3) | +1.6 (1.2 to 2.1) | +1.2 | 3.44% |
| WTA | 2013–2026 | +1.4 (1.1 to 1.8) | +1.4 (1.0 to 1.8) | +0.9 | 2.81% |
| WTA | 2022–2026 | +1.8 (1.2 to 2.4) | +1.8 (1.2 to 2.4) | +1.3 | 2.97% |

**Observed.** Counting is better in every window, on both tours, even on completed matches alone. Across the 61 tour × level × era cells with at least 300 matches, the rules differ by at most 4.9 milli-log-loss. **Inferred:** a retirement still says something about who was winning, or who is fit. **Suggestion:** count them.

## Problems found in earlier work (reported, not fixed)

1. **Stage 0: established women under a second id (new; confirmed).** Tennis My Life's rows alone cover the weeks from 25 May 2026. In them, 64 women carry a WTA id that Sackmann's rows never use, although the same name has a Sackmann id: Daria Snigur, Ekaterina Alexandrova, Jaqueline Cristian, Katie Boulter, Leylah Fernandez, Panna Udvardy, Paula Badosa and Qinwen Zheng among them (`split_identities`). That is 122 player rows in 77 matches, 76 of them evaluation matches and 71 with odds. Elo meets each as a newcomer.
   * **Effect:** without those matches the women's room is 24.4 rather than 33.8 milli-log-loss in 2026, 17.3 rather than 18.8 in 2022–2026, and 16.1 rather than 16.7 over 2013–2026 (`split_identity_sensitivity`).
   * The audit counted these 125 women's rows among "an id Sackmann's rows do not hold" and inferred "players newer than its files". For 122 of them that reading is wrong. Its C2 counted only the men's side.
   * The men's split ids (the audit's C2: 121 players, 183 matches, 129 evaluation) touch no match with odds and move the men's 2013–2026 Elo log loss by under 0.1 milli-log-loss.
2. **Stage 0, possible (inferred from the tour calendars, not verified).** Bol 2016 and 2017, Zhengzhou 2017 and Limoges 2019 are filed as WTA 250s, but were WTA 125 events. That is 123 main-draw evaluation matches plus their qualifying. tennis-data.co.uk, which lists tour-level events, has none of them; Linz 2020 and Cluj-Napoca 2021, which it also lacks, were 250s. This adds to the audit's P1.
3. **The Stage 0 audit's findings, as they bear on Stage 1.**
   * C1: the 101 repeated rows are counted twice in Elo's history, and the later copy of the 2025 Billie Jean King Cup Finals sees its own result. None is an evaluation match except the 4 at Champaign 2025.
   * C2: see item 1.
   * C3 (match tiebreaks read as sets): no effect, since Elo uses only who won.
   * P1: the level tables inherit the seven questioned event-seasons.
   * P3: answered here by the probe cut by date, event and round.
   * P4: players twice in one knockout round are treated as simultaneous, as the rule says.
4. **`src/eda/merge_feasibility/scan.py`'s tennis-data link.** The nearest week gives 151 Stage 0 matches two rows each and links pairs to the next week's event. 115 of its links agree on neither set scores nor round. It has no anchor for names that differ, and no handling of misdated rows. merge_feasibility read 95.0% of rows as linked on its own table; the same method links 95.83% of rows to Stage 0's. Stage 1 corrects these in its own code; `scan.py` and merge_feasibility's results are unchanged.
5. **tennis-data.co.uk.**
   * No ATP 2018 file.
   * The ATP 2013 file dates Beijing and Tokyo 2013 in October 2012 (62 rows); one WTA 2026 row is dated 2029.
   * 34 average-odds pairs and 28 Pinnacle pairs are incoherent (overround outside 1.00–1.20).
   * 19 rows credit a match to the other player, mostly retirements.
   * 2026 finals appear before their result was recorded.
   * Pinnacle's odds end in January 2026.
   * The 2021 WTA workbook labels 26 rows `WTA251`…`WTA276` (known from the dump report; harmless here).
6. **`src/ratings/elo.py`**: its row-by-row fit breaks the Brief's time rule for round robins and same-week events (section 2). Its formulas are sound.

## Decisions for the owner

**Closed on 30 Sep 2026** ([README](README.md#owner-decisions)): Elo is a rough, exploratory baseline, and its details are not to be worked further. Its three items take the defaults suggested here:
* retirements counted (counting is better by 1.1–1.9 milli-log-loss in every window, and by 0.7–1.3 on completed matches alone);
* surface Elo as the rating (2.8–4.0 better than overall Elo in every window);
* the tuned constants frozen as chosen.

Both retirement rules stay saved in `stage1_baselines.parquet`. Still open:

1. **The women's split identities (a Stage 0 fix).** Resolve a Tennis My Life WTA id that Sackmann never uses by the exact name, as the audit suggested for the men's codes, then re-run Stages 0 and 1. **Suggestion:** yes, before Stages 2–3. Any per-player history, point-level or not, splits the same way, and the headline window holds all 76 affected evaluation matches.
2. **The odds data rules.** Approve, or change:
   * the one-player anchor (3,155 links) and the exchanged-winner pass (19);
   * re-dating 63 misdated rows;
   * treating pairs with an overround outside 1.00–1.20 as missing (34 average pairs).
3. **The Next Gen ATP Finals** (Stage 0's open decision 2). 121 evaluation matches with no odds. Surface Elo scores 0.599 on them, and they raise the men's Tour Finals cell from 0.576 to 0.585. Keep in evaluation, or leave out?
4. **The WTA 125 events filed as 250s** (problem 2, with the audit's P1). Confirm against the WTA's records and relabel in Stage 0?

## Suggestions (not applied)

* Match length (best of three or five) as an input, for the Stage 4 candidate list.
* A second odds source for the men's 2018 season and for August–September 2026 (the data map lists candidates), if the market comparison matters in those windows.

## Limitations

* **The closing odds are the provider's claim.** The average's panel of bookmakers is OddsPortal's and changes over time. The normalisation is proportional; other ways of removing the margin shift the market's log loss slightly.
* **The market covers tour-level main draws only.** The room is measured there; Challengers and qualifying have no market to compare with.
* **95% ranges treat matches as independent.** A player's matches are not, so the ranges are somewhat too narrow.
* **Rankings are as of the tournament's start** (Sackmann), so late rounds of a two-week event use a two-week-old ranking.
* **Elo starts every player at 1,500**, in one pool from ITF to Grand Slams, and ignores time between matches (the 2020 break shows). It also ignores match length (section 3).
* **Stage 0's known problems** (above) are in the history Elo learns from. Only the women's split identities move a headline number measurably.
