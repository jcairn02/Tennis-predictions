# Stage 3: which statistics repeat

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: built 1 Oct 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md); the report section is "Which statistics repeat" in [report.html](report.html). Stages 0 and 1, the Stage 0 audit and the owner's entries were read first; Stage 2 had already been built and was used as it stands.

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/predictability_diagnostic/`: from `stage3_results.json` unless another file is named (`stage3_ratings_summary.json` for the ratings' tuning and checks, or a CSV).

## In short

* **Observed. A regular's season says a lot about how a player serves, and little about break points and tiebreaks.**
  * Reliability is the share of the spread between players' season rates that is the player rather than chance. Here it is measured for a typical season of a regular: 44 matches for the men, 37 for the women.
  * Serve style is mostly signal: aces 0.96 (men) and 0.95 (women), first serves in 0.93 and 0.95, double faults 0.90 and 0.92.
  * So are serve points won (0.81 and 0.78) and return points won (0.76 and 0.66).
  * Results are about half signal: games won 0.50 and 0.55, sets won 0.45 and 0.47.
  * Break points are mostly chance: saved 0.37 and 0.39, converted 0.34 and 0.29.
  * Tiebreaks won are chance: 0.06 and 0.06.
* **Observed. Opponent adjustment pays.** The serve and return ratings built here restate each match's serve and return points as if against a typical opponent:
  * Serve points won reach half signal after 3.3 matches (men) and 4.2 (women) instead of 8.3 and 9.4. Return points won after 4.9 and 6.9 instead of 14 and 18.
  * Season-to-season carry-over rises from 0.62 to 0.74 (men's serve) and from 0.42 to 0.64 (women's return).
* **Observed. How much of the tour average to mix in.** For serve points won, a player's own rate counts half after 466 serve points (men, about 6 matches) and 582 (women).
  * A match's serve rate varies about twice as much as the points' own luck explains, because of opponents, conditions and form. A binomial (beta-binomial) constant would shrink too little.
  * Estimated on 2010–2018 for Stage 4, the constants move little when every year is used: the median ratio is 1.03. 143 of 144 stay inside their bootstrap range.
* **Observed. The next match.** For serve points won in 2019–2026, the ratings, which also know who returns, capture 35% (men) and 34% (women) of what is not point luck. The player's own history alone captures 15% and 15%.
  * Career to date, the last 52 weeks and a decayed history are close to one another. Recency helps the serve style (best half-lives 13–26 weeks) and not serve or return skill (104–208 weeks; 208 is the longest tried).
  * For results, history at other levels misleads. Women's sets won forecast from the whole career is worse than the tour average (−3.74 milli-log-loss per set); from evaluation-level matches only it is better (+7.51).
* **Saved for Stage 4:**
  * the shrinkage constants (`stage3_shrinkage.csv`);
  * the reliability at a typical season (`stage3_persistence.csv`, for the summary's chart);
  * the serve and return ratings' pre-match values for every match (`stage3_ratings.parquet`).
* **For the owner.** Six decisions, [at the end](#decisions-for-the-owner).

## What was built

| File | What it holds |
|---|---|
| `stage3_ratings.parquet` (41.5 MB) | One row per match (all 872,704): A's and B's pre-match serve and return ratings, their standard deviations and the serve and return points they rest on, the surface's intercept, and each player's expected serve-point share against this opponent; whether the match moved the ratings |
| `stage3_rating_tuning.csv` | The ratings' grid: log loss per serve point, 2013–2018, per tour and setting |
| `stage3_ratings_summary.json` | The ratings' constants, tuning detail, out-of-sample scores, the probe, and the highest-rated players in 2026 |
| `stage3_reliability.csv` | Every split-half correlation: tour, surface, statistic, n, player-windows, the rate's units, 95% range |
| `stage3_shrinkage.csv` | The constants by statistic × tour × surface × years (Stage 4 uses 2010–2018; the adjusted rates 2013–2018), with bootstrap ranges and the binomial version |
| `stage3_persistence.csv` | Per statistic × tour × surface: the typical season, its reliability and 95% range, the Spearman–Brown k, the year-to-year carry-over, the shrinkage constant and the verdict (the summary's chart) |
| `stage3_carryover.csv` | Season to season and surface to surface, with ceilings |
| `stage3_forecast.csv` | The next-match forecasts: every form, tour, window and surface |
| `stage3_results.json` | Everything quoted here (the CSVs keep every row) |

Code in `src/eda/predictability_diagnostic/`:

* `stage3_ratings.py`: the ratings, their tuning and the probe; about 2 minutes.
* `stage3_traits.py`: reliability, shrinkage, carry-over, forecasts, the persistence table and the verdicts; about 2½ minutes.
* `report_stage3.py`: the report section.

Tests: `test/predictability_diagnostic/test_stage3.py` (27 tests; 194 in the study, all passing). **Shared helpers kept out of `common.py`** (Stage 2 could have run beside this stage), as the prompt asked: `stage3_traits.split_half`, `sb_fit`, `eb_constants`, `sums_before` and `lookback_sums`, and the whole of `stage3_ratings.py`.

## Terms used here

* **Rate**: a per-match statistic as a share, stored by Stage 0 as a count and a denominator: serve points won of serve points, aces per serve point, break points saved of break points faced, and so on. Its **units** are what the denominator counts: serve points, break points faced, tiebreaks, sets, games. Break points faced per service game is a count per game, not a share.
* **Reliability**: of a rate measured on a sample, the share of its spread across players that is real difference between them rather than chance. 1 is all player, 0 all chance.
* **Split-half correlation**: from each player's window (a season), two separate random sets of n matches; the rate on each, correlated across players. It is the reliability of a sample of n matches.
* **Spearman–Brown curve**: r = n / (n + k). It is what reliability does as the sample grows when one match carries a fixed share of signal. **k** is the sample at which reliability reaches 0.5: half signal, half noise. Twice k gives two-thirds signal, four times k four-fifths.
* **Regular, typical season**: a regular plays at least 20 evaluation-level matches in a season. A typical season is a regular's median: 44 matches for the men and 37 for the women over all surfaces. On one surface, it is the median among regulars who played on it: hard 22 and 22, clay 17 and 10, grass 4 and 4.
* **Shrinkage**: mixing the tour's average into a player's rate as (x + K × average) / (d + K), with x the player's count and d their units. **K**, the shrinkage constant, is the chance variation of one unit over the true spread between players. A player with d = K units gets half their own rate and half the average.
* **Carry-over**: the correlation of a player's shrunk rate in one season with the next, or on one surface with another in the same season. Its **ceiling** is what the correlation would be if the player's true rate never changed, given the noise of the two samples.
* **Serve and return ratings**: each player's serve and return strength on the log-odds scale. The chance that the server wins a serve point is 1 / (1 + e^−(μ + serve − return)), where μ is the tour's average on the surface.
* **Opponent-adjusted rate**: a match's serve (or return) points won restated as against a typical returner (server), using the opponent's rating before the match.
* **Log loss per point**: as Stage 1's log loss, but every point (game, set, tiebreak...) of the next match is scored with the forecast rate. Results are milli-log-loss per unit, better or worse than the tour's average on the surface.

## The matches

* **Measurements (items 1–3).** Completed matches in the standard format at the evaluation levels: Grand Slams, Finals, 1000s, 500s, 250s, Challenger / WTA 125, and their qualifying.
  * That is 352,340 men's and 141,202 women's player-matches from 2010 to 2026.
  * Reliability and carry-over use the evaluation years 2013–2026: 149,790 men's and 58,596 women's matches, 146,972 and 54,060 of them with a box score.
  * The shrinkage constants use 2010–2018, as the prompt asks, and 2010–2026 for comparison.
* **Forecasts (item 4).**
  * History is every completed singles match from 2010 at every level, the Brief's history: 891,686 and 771,754 player-matches.
  * Targets are evaluation matches, completed, scored on 2019–2026. The women's box-score rates are evaluated from 2019, as the Brief sets.
* **Retirements are left out throughout** (17,530 men's and 12,685 women's matches): their statistics cover part of a match that something else decided. This is decision 1, the same choice as Stage 2's.
* **When a rate counts.** A rate counts for a match where both its count and its denominator are written. A denominator of 0, such as no tiebreak played, is a match without the chance, and counts.
* **The unreadable box score.** One Tennis My Life box score (Prague 2026, the one Stage 2 reported) has an unreadable break-point count. Its hold, break and break-points-faced rates are left out.
* **Windows.** A player's matches are grouped by season. On grass, where a regular's season holds 4 matches, three seasons form a window (2010–12, 2013–15, …, 2025–26).
* **All surfaces.** Each match is measured against the tour's 2010–2018 average on its surface, so a player's mix of surfaces does not count as a trait. Carpet, rare after 2012, appears only there.

## 1. Reliability against sample size

For each n (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30 matches) the method is:

* Every player-window with at least 2n matches gives two random sets of n matches.
* The rate on one set is correlated across player-windows with the rate on the other, averaged over 20 random draws.
* A correlation needs 30 player-windows; under 300 it is directional only, as the Brief sets for groups.
* The sample is also given in the rate's units: the mean denominator of a set.
* The Spearman–Brown curve is fitted (weighted by player-windows) to the n's with 300+ player-windows, in matches and in units. `stage3_reliability.csv` has every point.

**Observed** (`reliability.fits`), all surfaces. k is the sample at which reliability reaches 0.5. The fixed population is player-seasons with 30+ matches, for every n up to 15.

| Statistic | Units | ATP k, matches | k, units | Fixed population | WTA k, matches | k, units | Fixed population |
|---|---|---:|---:|---:|---:|---:|---:|
| Aces per serve point | serve points | 1.9 | 139 | 1.9 | 2.1 | 152 | 2.1 |
| First serves in | serve points | 3.1 | 226 | 3.5 | 1.9 | 136 | 2.0 |
| Double faults per serve point | serve points | 3.8 | 283 | 4.8 | 2.6 | 187 | 2.9 |
| First-serve points won | first serves in | 5.9 | 269 | 6.7 | 5.9 | 263 | 6.1 |
| Serve points won | serve points | 8.3 | 617 | 9.7 | 9.4 | 674 | 10 |
| Serve points won, opponent-adjusted | serve points | 3.3 | 239 | 4.3 | 4.2 | 302 | 5.3 |
| Service games held | service games | 10 | 117 | 12 | 10 | 110 | 12 |
| Return points won | return points | 14 | 1,036 | 14 | 18 | 1,303 | 18 |
| Return points won, opponent-adjusted | return points | 4.9 | 361 | 6.2 | 6.9 | 494 | 8.3 |
| Return games won (breaks) | return games | 17 | 195 | 17 | 21 | 222 | 20 |
| Break points faced per service game | service games | 16 | 182 | 18 | 19 | 204 | 21 |
| Second-serve points won | second-serve points | 25 | 716 | 27 | 21 | 568 | 23 |
| Total points won | points | 27 | 4,072 | 33 | 24 | 3,403 | 28 |
| Games won | games | 33 | 773 | 38 | 27 | 580 | 32 |
| Sets won | sets | 43 | 103 | 46 | 35 | 83 | 42 |
| Break points saved | break points faced | 67 | 442 | 68 | 59 | 483 | 64 |
| Break points converted | break-point chances | 92 | 641 | 96 | 102 | 876 | 98 |
| Tiebreaks won | tiebreaks | 970 | 402 | 2,341 | 1,995 | 612 | 635 |

* **Observed.** Over all surfaces, the curve misses the measured points by at most 0.10. The largest misses are for games and sets won.
* **Observed. For results the measured k creeps up with n.** For the men's games won it is 9.4 matches at n = 1 and 49 at n = 30. For serve points won it is 4.6 at n = 1 and 10 from n = 25. On the fixed population it is larger than the main fit for most rates. **Inferred:** players who play many matches are those who win, so they are more alike in what winning shows.
* **Observed. Tiebreaks** need hundreds of tiebreaks for half signal, about 1,000 matches or more, which no career reaches. Their k is unstable: the correlations it rests on are close to 0.
* **Inferred.** The sample at which a rate becomes half signal ranks the rates the same way on both tours:
  1. serve style in a few matches;
  2. serve and return skill in about a month of a regular's play (opponent-adjusted, a week);
  3. results in most of a season;
  4. break points in more than a season;
  5. tiebreaks never.

## 2. Signal or noise in a season (the summary's chart)

**How it is read.** The reliability of a typical season is read off the measured curve, not the fitted one:

* take the split-half correlation r at half a typical season, among players who play at least a typical season;
* step it up to the whole season: 2r / (1 + r);
* the 95% range comes from r's range.

Reading the fitted curve instead (`reliability_typical_from_fit` in the CSV) gives values within 0.08 everywhere. They are higher for results, as the creep above predicts.

**The verdict rule.** It was set before looking, as a reading convention:

* **repeats**: a typical season is at least half signal (reliability 0.5 or more);
* **repeats weakly**: from 0.2 to 0.5;
* **mostly noise**: below 0.2;
* **borderline** (\*): the 95% range crosses one of the lines.

**Observed** (`persistence`, `stage3_persistence.csv`), all surfaces:

| Statistic | ATP verdict | Season | 95% range | Half signal (matches) | Season to season | WTA verdict | Season | 95% range | Half signal | Season to season |
|---|---|---:|---|---:|---:|---|---:|---|---:|---:|
| Aces per serve point | repeats | 0.96 | 0.95–0.96 | 1.9 | 0.79 | repeats | 0.95 | 0.94–0.95 | 2.1 | 0.79 |
| First serves in | repeats | 0.93 | 0.92–0.93 | 3.1 | 0.64 | repeats | 0.95 | 0.94–0.95 | 1.9 | 0.67 |
| Double faults per serve point | repeats | 0.90 | 0.89–0.91 | 3.8 | 0.60 | repeats | 0.92 | 0.92–0.93 | 2.6 | 0.64 |
| First-serve points won | repeats | 0.87 | 0.86–0.88 | 5.9 | 0.65 | repeats | 0.86 | 0.84–0.88 | 5.9 | 0.67 |
| Serve points won | repeats | 0.81 | 0.80–0.83 | 8.3 | 0.62 | repeats | 0.78 | 0.76–0.81 | 9.4 | 0.61 |
| Serve points won, opponent-adjusted | repeats | 0.91 | 0.90–0.92 | 3.3 | 0.74 | repeats | 0.88 | 0.86–0.89 | 4.2 | 0.70 |
| Service games held | repeats | 0.77 | 0.75–0.79 | 10 | 0.58 | repeats | 0.76 | 0.72–0.79 | 10 | 0.58 |
| Return points won | repeats | 0.76 | 0.75–0.78 | 14 | 0.54 | repeats | 0.66 | 0.62–0.70 | 18 | 0.42 |
| Return points won, opponent-adjusted | repeats | 0.88 | 0.87–0.89 | 4.9 | 0.72 | repeats | 0.81 | 0.78–0.83 | 6.9 | 0.64 |
| Return games won (breaks) | repeats | 0.73 | 0.71–0.75 | 17 | 0.52 | repeats | 0.63 | 0.58–0.68 | 21 | 0.44 |
| Break points faced per service game | repeats | 0.71 | 0.68–0.73 | 16 | 0.50 | repeats | 0.64 | 0.59–0.68 | 19 | 0.46 |
| Second-serve points won | repeats | 0.59 | 0.56–0.62 | 25 | 0.44 | repeats | 0.62 | 0.57–0.66 | 21 | 0.40 |
| Total points won | repeats | 0.55 | 0.52–0.59 | 27 | 0.44 | repeats | 0.58 | 0.52–0.63 | 24 | 0.45 |
| Games won | repeats\* | 0.50 | 0.46–0.54 | 33 | 0.42 | repeats\* | 0.55 | 0.49–0.60 | 27 | 0.44 |
| Sets won | repeats weakly | 0.45 | 0.40–0.49 | 43 | 0.41 | repeats weakly\* | 0.47 | 0.41–0.53 | 35 | 0.43 |
| Break points saved | repeats weakly | 0.37 | 0.32–0.42 | 67 | 0.33 | repeats weakly | 0.39 | 0.31–0.46 | 59 | 0.33 |
| Break points converted | repeats weakly | 0.34 | 0.29–0.39 | 92 | 0.24 | repeats weakly\* | 0.29 | 0.20–0.37 | 102 | 0.19 |
| Tiebreaks won | mostly noise | 0.06 | 0.00–0.13 | 970 | 0.07 | mostly noise | 0.06 | 0.00–0.17 | 1,995 | 0.01 |

**On one surface** a season is a smaller sample, so everything is less reliable. **Observed:**

| Statistic | ATP hard | Clay | Grass | WTA hard | Clay | Grass |
|---|---:|---:|---:|---:|---:|---:|
| Aces per serve point | 0.93 | 0.86 | 0.76 | 0.92 | 0.83 | 0.66 |
| First serves in | 0.85 | 0.87 | 0.56 | 0.92 | 0.86 | 0.68 |
| Double faults per serve point | 0.83 | 0.79 | 0.51\* | 0.88 | 0.81 | 0.60 |
| First-serve points won | 0.79 | 0.70 | 0.45\* | 0.79 | 0.62 | 0.41 |
| Serve points won | 0.71 | 0.63 | 0.36 | 0.67 | 0.52\* | 0.26\* |
| Serve points won, opponent-adjusted | 0.86 | 0.80 | 0.55\* | 0.81 | 0.70 | 0.44\* |
| Service games held | 0.66 | 0.59 | 0.23\* | 0.64 | 0.48\* | 0.24\* |
| Return points won | 0.63 | 0.51\* | 0.19\* | 0.53\* | 0.32 | 0.21\* |
| Return points won, opponent-adjusted | 0.81 | 0.74 | 0.44 | 0.73 | 0.57 | 0.42 |
| Return games won (breaks) | 0.59 | 0.48\* | 0.14\* | 0.50\* | 0.27\* | 0.18\* |
| Break points faced per service game | 0.59 | 0.48\* | 0.24\* | 0.52\* | 0.33 | 0.16\* |
| Second-serve points won | 0.44 | 0.43 | 0.12\* | 0.47\* | 0.37 | 0.12\* |
| Total points won | 0.39 | 0.36 | 0.18\* | 0.41 | 0.19\* | 0.14\* |
| Games won | 0.36 | 0.32 | 0.12\* | 0.37 | 0.18\* | 0.12\* |
| Sets won | 0.31 | 0.27 | 0.09 | 0.28\* | 0.08 | 0.07 |
| Break points saved | 0.23\* | 0.19\* | 0.06 | 0.27\* | 0.11\* | 0.01 |
| Break points converted | 0.20\* | 0.13 | 0.00 | 0.18\* | 0.10 | 0.08 |
| Tiebreaks won | 0.02 | 0.01 | 0.00 | 0.01 | 0.00 | 0.00\* |

The typical season on a surface is 22 matches on hard (both tours), 17 (men) and 10 (women) on clay, and 4 on grass.

## 3. Shrinkage: how much of the tour average to mix in

**How K is measured.** It is chance variation per unit over the true spread between players, estimated on player-windows (empirical Bayes, by the method of moments):

* **Chance variation** is measured from how much a player's matches vary within a window: Σ d (rate − window rate)² over the matches, divided by the matches less one.
  * It includes the points' own luck, plus the changing opponents, conditions and form.
  * A binomial model (the beta-binomial's constant, "binomial K") counts the points' luck alone. Break points faced per game is a count, so its chance is Poisson.
* **The true spread** is the spread of window rates less their chance part (the unbalanced one-way analysis of variance, weighted by units).
* **K in matches** is K over the units a match holds on average.
* **The range** comes from 200 bootstrap resamples of players.
* **The years.** Stage 4's constants are estimated on 2010–2018 only; the opponent-adjusted ones on 2013–2018, after the ratings' warm-up years.

**Observed** (`shrinkage`, `stage3_shrinkage.csv`), all surfaces, 2010–2018. "Chance ÷ binomial" is the measured chance variation over the binomial one. The ratio is K with every year (2010–2026) over K from 2010–2018.

| Statistic | Units | ATP average | K | K, matches | Binomial K | Chance ÷ binomial | Ratio, all years | WTA average | K | K, matches | Binomial K | Chance ÷ binomial | Ratio, all years |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Aces per serve point | serve points | 6.6% | 137 | 1.9 | 61 | 2.1 | 1.03 | 3.4% | 156 | 2.2 | 78 | 1.9 | 1.01 |
| First serves in | serve points | 60.8% | 225 | 3.1 | 140 | 1.5 | 0.99 | 62.1% | 131 | 1.8 | 90 | 1.4 | 1.01 |
| Double faults per serve point | serve points | 4.1% | 256 | 3.5 | 190 | 1.3 | 1.00 | 5.3% | 170 | 2.4 | 130 | 1.3 | 1.03 |
| First-serve points won | first serves in | 69.8% | 221 | 4.9 | 117 | 1.7 | 1.04 | 62.5% | 254 | 5.8 | 133 | 1.6 | 0.94 |
| Serve points won | serve points | 62.0% | 466 | 6.3 | 200 | 1.9 | 1.05 | 55.9% | 582 | 8.2 | 245 | 1.8 | 0.97 |
| Serve points won, opponent-adjusted (2013–2018) | serve points | 62.0% | 196 | 2.7 | 111 | 1.6 | 1.05 | 56.0% | 277 | 3.9 | 157 | 1.6 | 0.91 |
| Service games held | service games | 76.2% | 72 | 6.3 | 39 | 1.6 | 1.07 | 63.8% | 90 | 8.4 | 46 | 1.6 | 0.92 |
| Return points won | return points | 38.0% | 1,052 | 14 | 335 | 2.1 | 1.00 | 44.1% | 1,170 | 17 | 371 | 2.0 | 1.12 |
| Return points won, opponent-adjusted (2013–2018) | return points | 38.3% | 316 | 4.3 | 171 | 1.7 | 1.03 | 44.0% | 423 | 6.0 | 225 | 1.6 | 0.97 |
| Return games won (breaks) | return games | 23.8% | 245 | 21 | 86 | 1.8 | 0.95 | 36.2% | 245 | 23 | 84 | 1.7 | 1.05 |
| Break points faced per service game | service games | 0.583 | 119 | 10 | 40 | 2.2 | 1.06 | 0.784 | 156 | 15 | 59 | 1.8 | 1.03 |
| Second-serve points won | second-serve points | 49.9% | 460 | 16 | 278 | 1.3 | 1.06 | 45.0% | 439 | 16 | 272 | 1.3 | 1.02 |
| Total points won | points | 50.0% | 1,959 | 13 | 628 | 2.1 | 1.10 | 50.0% | 2,117 | 15 | 539 | 2.4 | 1.03 |
| Games won | games | 50.0% | 341 | 15 | 154 | 1.6 | 1.10 | 50.0% | 361 | 17 | 109 | 2.1 | 1.01 |
| Sets won | sets | 50.0% | 60 | 25 | 29 | 1.4 | 1.07 | 50.0% | 57 | 25 | 27 | 1.4 | 0.99 |
| Break points saved | break points faced | 59.2% | 246 | 37 | 183 | 1.1 | 1.07 | 53.7% | 370 | 44 | 256 | 1.1 | 0.92 |
| Break points converted | break-point chances | 40.8% | 1,016 | 152 | 441 | 1.1 | 0.81 | 46.3% | 791 | 94 | 412 | 1.1 | 1.14 |
| Tiebreaks won | tiebreaks | 50.0% | 429 | 1,152 | 336 | 1.0 | 0.83 | 50.0% | 569 | 2,543 | 335 | 1.0 | 0.63 |

**Observed.**

* **Chance is more than point luck where the opponent matters.** A match's serve or return rate varies 1.8–2.1 times as much as binomial chance, a match's total points share 2.1–2.4 times, and its ace rate 1.9–2.1 times.
* **Break points and tiebreaks behave as pure chance within a player** (1.0–1.1 times).
* **Bootstrap ranges** (2010–2018, units):
  * serve points won 419–517 (men) and 494–670 (women);
  * return points won 900–1,233 and 1,008–1,375;
  * break points saved 218–283 and 305–488.
  * For tiebreaks the upper end is "no signal": no true spread between players in some resamples.
* **With every year** the ratio has a median of 1.03 over the 34 all-surface constants other than tiebreaks, from 0.81 to 1.14. 143 of the 144 constants (both tours, all four surface groups) fall inside their 2010–2018 bootstrap range. The exception is the women's opponent-adjusted serve points on grass.
* The per-surface constants are in the CSV. A few have no detectable true spread ("no signal", K infinite); a forecast there is the tour's average. They are:
  * tiebreaks on the men's clay and grass and the women's hard courts;
  * on grass, the women's break points saved and the men's break points converted (2010–2018).

**Inferred.** A Stage 4 feature built on a player's history can use these constants as they are. The forecasts below show the choice is not delicate: halving or doubling K, or using the binomial K, moves the career forecast by a median 0.03 milli-log-loss per unit.

The split-half k of section 1 and K here measure the same thing in matches, on different populations:

* **Close** for the serve style and for serve and return points (aces 1.9 and 1.9 for the men, return points won 14 and 14).
* **K smaller** for results (games won 15 against 33). K comes from every player-window, k from players with at least 2n matches.

## 4. Carry-over

A player's shrunk rate (2010–2018 constants) in one season against the next, every pair of consecutive seasons 2013–2026 (11,516 men's and 5,115 women's player pairs for serve points). The ceiling is computed as E[R₁R₂] / √(E[R₁] E[R₂]), with R = d / (d + K) the reliability of each player's season. The ratio is the observed correlation over the ceiling; it is not read where the ceiling is under 0.3.

**Observed** (`carryover.year`), all surfaces:

| Statistic | ATP season to season | Ceiling | Ratio | WTA season to season | Ceiling | Ratio |
|---|---:|---:|---:|---:|---:|---:|
| Aces per serve point | 0.79 | 0.81 | 0.97 | 0.79 | 0.79 | 1.00 |
| First serves in | 0.64 | 0.77 | 0.83 | 0.67 | 0.80 | 0.84 |
| Double faults per serve point | 0.60 | 0.76 | 0.80 | 0.64 | 0.78 | 0.82 |
| First-serve points won | 0.65 | 0.72 | 0.90 | 0.67 | 0.68 | 0.99 |
| Serve points won | 0.62 | 0.69 | 0.89 | 0.61 | 0.63 | 0.96 |
| Serve points won, opponent-adjusted | 0.74 | 0.78 | 0.95 | 0.70 | 0.73 | 0.97 |
| Service games held | 0.58 | 0.69 | 0.83 | 0.58 | 0.62 | 0.94 |
| Return points won | 0.54 | 0.59 | 0.92 | 0.42 | 0.52 | 0.81 |
| Return points won, opponent-adjusted | 0.72 | 0.73 | 0.99 | 0.64 | 0.67 | 0.95 |
| Return games won (breaks) | 0.52 | 0.52 | 0.99 | 0.44 | 0.46 | 0.95 |
| Break points faced per service game | 0.50 | 0.63 | 0.78 | 0.46 | 0.54 | 0.87 |
| Second-serve points won | 0.44 | 0.57 | 0.77 | 0.40 | 0.52 | 0.78 |
| Total points won | 0.44 | 0.60 | 0.74 | 0.45 | 0.54 | 0.83 |
| Games won | 0.42 | 0.59 | 0.72 | 0.44 | 0.53 | 0.83 |
| Sets won | 0.41 | 0.50 | 0.83 | 0.43 | 0.46 | 0.95 |
| Break points saved | 0.33 | 0.42 | 0.79 | 0.33 | 0.34 | 0.97 |
| Break points converted | 0.24 | 0.19 | – | 0.19 | 0.22 | – |
| Tiebreaks won | 0.07 | 0.04 | – | 0.01 | 0.02 | – |

**Surface to surface, same season** (`carryover.surface`; correlation, with the ceiling in brackets; 8,050 men's and 3,976 women's players for hard–clay):

| Statistic | ATP hard–clay | Hard–grass | Clay–grass | WTA hard–clay | Hard–grass | Clay–grass |
|---|---:|---:|---:|---:|---:|---:|
| Aces per serve point | 0.72 (0.77) | 0.78 (0.81) | 0.72 (0.75) | 0.71 (0.73) | 0.71 (0.71) | 0.66 (0.66) |
| First serves in | 0.55 (0.73) | 0.55 (0.68) | 0.48 (0.65) | 0.68 (0.78) | 0.62 (0.72) | 0.58 (0.70) |
| Double faults per serve point | 0.56 (0.71) | 0.56 (0.68) | 0.51 (0.64) | 0.63 (0.75) | 0.57 (0.67) | 0.55 (0.65) |
| First-serve points won | 0.55 (0.64) | 0.59 (0.65) | 0.48 (0.57) | 0.59 (0.57) | 0.56 (0.53) | 0.51 (0.46) |
| Serve points won | 0.50 (0.60) | 0.55 (0.61) | 0.42 (0.54) | 0.52 (0.51) | 0.47 (0.43) | 0.40 (0.37) |
| Serve points won, opponent-adjusted | 0.69 (0.74) | 0.67 (0.74) | 0.57 (0.69) | 0.64 (0.66) | 0.58 (0.56) | 0.51 (0.52) |
| Service games held | 0.47 (0.61) | 0.49 (0.59) | 0.38 (0.52) | 0.49 (0.51) | 0.43 (0.42) | 0.38 (0.35) |
| Return points won | 0.37 (0.46) | 0.42 (0.35) | 0.27 (0.28) | 0.33 (0.35) | 0.35 (0.29) | 0.24 (0.21) |
| Return points won, opponent-adjusted | 0.62 (0.66) | 0.59 (0.63) | 0.46 (0.56) | 0.54 (0.56) | 0.52 (0.53) | 0.40 (0.44) |
| Return games won (breaks) | 0.34 (0.36) | 0.38 (0.22) | 0.23 (0.17) | 0.29 (0.23) | 0.34 (0.23) | 0.22 (0.13) |
| Break points faced per service game | 0.39 (0.51) | 0.43 (0.53) | 0.30 (0.44) | 0.33 (0.40) | 0.34 (0.36) | 0.27 (0.29) |
| Second-serve points won | 0.32 (0.43) | 0.30 (0.37) | 0.21 (0.31) | 0.36 (0.40) | 0.23 (0.24) | 0.19 (0.21) |
| Total points won | 0.29 (0.46) | 0.41 (0.41) | 0.19 (0.34) | 0.36 (0.33) | 0.39 (0.30) | 0.27 (0.20) |
| Games won | 0.27 (0.44) | 0.39 (0.35) | 0.18 (0.28) | 0.36 (0.31) | 0.37 (0.27) | 0.25 (0.18) |
| Sets won | 0.25 (0.33) | 0.37 (0.25) | 0.16 (0.19) | 0.32 (0.20) | 0.36 (0.22) | 0.22 (0.12) |
| Break points saved | 0.19 (0.27) | 0.18 (0.21) | 0.10 (0.16) | 0.18 (0.20) | – | – |
| Break points converted | 0.12 (0.09) | – | – | 0.12 (0.10) | 0.08 (0.10) | 0.07 (0.07) |
| Tiebreaks won | – | – | – | – | – | 0.03 (0.01) |

"–": a surface's constant found no true spread, so every player shrinks to the average and there is nothing to correlate.

**Inferred.**

* **Season to season, the aces, the adjusted serve and return rates and the break rate carry nearly all a stable rate would** (0.95–1.00 of their ceilings).
* **The rest of the serve style changes more between seasons** (first serves in, double faults: about 0.8 of the ceiling): players remodel a serve. That matches the forecasts' short half-lives for these rates.
* **The results change more too** (games won 0.72 and 0.83): players move between levels and opponents.
* **Across surfaces, the ace rate is close to one trait everywhere.** Serve and return points won carry more once adjusted for the opponent (men's hard–clay 0.50 → 0.69 and 0.37 → 0.62). Part of the raw rate is which opponents a player meets on each surface.
* **Results carry least across surfaces** (men's games won hard–clay 0.27 against a ceiling of 0.44): surface specialists.
* **The ceilings are rough where samples are small.** On grass a correlation sometimes exceeds its ceiling (the women's serve points, return games). There the constant from three-season windows, which also counts three years of change as chance, is too large for one season. Read those ratios only as "near 1".

## 4b. The next match from a player's history

For each target (an evaluation match, completed, 2019–2026), the player's rate in that match is forecast from their earlier matches.

**The history.** It follows the Brief's time rule (earlier events and earlier rounds of the same event). It covers every level from 2010, and each past match is measured against its own surface's tour average.

**The forms.** Each is shrunk toward the tour's average on the target's surface with the 2010–2018 all-surface constant:

* **Career to date.**
* **Last 52 weeks.** Matches of the 52 tournament weeks before, plus the same event's earlier rounds.
* **Decayed.** Each earlier match is weighted by ½ per half-life. The half-life is chosen per statistic on the men's 2013–2018 targets from 13, 26, 52, 104 and 208 weeks, and used for both tours.
* **Serve and return ratings** (serve, return and total points won only): the expected serve-point shares against this opponent (section 5).

**The variants** (in the CSV):

* career with K × 0.5, K × 2 and the binomial K;
* career from evaluation-level matches only;
* the 52 weeks not shrunk.

**The scores.**

* **Log loss.** The log loss of the next match's points (binomial; a Poisson count for break points faced per game), per unit, in milli-log-loss better than the tour's average on the surface.
* **Share of the non-chance variation captured.** The next match's squared error splits into the chance of its points and the rest (player, opponent, conditions, day). The share is how much of the rest a forecast removes. It is not read where the rest is under 5%.

**Observed** (`forecast`, `stage3_forecast.csv`), 2019–2026, all surfaces. The targets are 174,888 men's and 66,432 women's player-matches for serve points, and 175,548 and 67,204 for games won.

Milli-log-loss per unit better than the tour average (negative: worse):

| Statistic | Per | ATP career | 52 weeks | Decayed | Ratings | Career, evaluation levels | 52 weeks, not shrunk | WTA career | 52 weeks | Decayed | Ratings | Career, evaluation levels | 52 weeks, not shrunk |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Aces per serve point | serve point | 5.15 | 5.23 | 5.62 | – | 5.17 | 3.16 | 4.69 | 4.89 | 5.07 | – | 4.64 | 2.74 |
| First serves in | serve point | 2.29 | 2.65 | 2.87 | – | 2.26 | 2.43 | 3.80 | 4.30 | 4.58 | – | 3.75 | 4.08 |
| Double faults per serve point | serve point | 1.40 | 1.62 | 1.73 | – | 1.38 | 0.88 | 2.25 | 2.57 | 2.71 | – | 2.22 | 1.80 |
| First-serve points won | first serve in | 2.44 | 2.39 | 2.53 | – | 2.38 | 1.87 | 2.69 | 2.57 | 2.77 | – | 2.65 | 2.01 |
| Serve points won | serve point | 1.13 | 1.08 | 1.16 | 2.65 | 1.09 | 0.82 | 1.10 | 1.00 | 1.12 | 2.43 | 1.08 | 0.59 |
| Service games held | service game | 5.35 | 4.97 | 5.49 | – | 5.15 | −0.79 | 6.22 | 5.51 | 6.27 | – | 6.08 | −3.14 |
| Return points won | return point | 0.58 | 0.55 | 0.61 | 2.65 | 0.59 | 0.06 | 0.36 | 0.28 | 0.37 | 2.43 | 0.39 | −0.38 |
| Return games won (breaks) | return game | 2.50 | 2.36 | 2.67 | – | 2.55 | −8.55 | 2.06 | 1.59 | 2.04 | – | 2.20 | −8.99 |
| Break points faced per service game | service game | 4.49 | 4.02 | 4.63 | – | 4.37 | −1.12 | 3.40 | 2.80 | 3.46 | – | 3.31 | −2.11 |
| Second-serve points won | second-serve point | 0.57 | 0.50 | 0.60 | – | 0.54 | −0.28 | 0.74 | 0.64 | 0.77 | – | 0.72 | −0.40 |
| Total points won | point | 0.15 | 0.11 | 0.15 | 1.13 | 0.15 | −0.06 | 0.22 | 0.16 | 0.22 | 1.48 | 0.23 | −0.15 |
| Games won | game | 0.22 | 0.12 | 0.32 | – | 0.66 | −0.24 | −0.87 | −0.02 | 0.41 | – | 1.26 | −1.24 |
| Sets won | set | 2.19 | 1.59 | 2.81 | – | 5.05 | −20.30 | −3.74 | 0.84 | 2.72 | – | 7.51 | −23.64 |
| Break points saved | break point faced | 0.83 | 0.55 | 0.86 | – | 0.78 | −14.50 | 0.87 | 0.59 | 0.88 | – | 0.86 | −14.00 |
| Break points converted | break-point chance | 0.34 | 0.22 | 0.34 | – | 0.33 | −22.19 | 0.24 | 0.13 | 0.24 | – | 0.25 | −16.51 |
| Tiebreaks won | tiebreak | 0.43 | 0.13 | 0.38 | – | 0.46 | −166.37 | 0.19 | 0.02 | 0.14 | – | 0.21 | −352.01 |

Share of the next match's non-chance variation captured; "beyond point luck" is how much of the next match's squared error is not the chance of its points:

| Statistic | ATP beyond point luck | Career | 52 weeks | Decayed | Ratings | WTA beyond point luck | Career | 52 weeks | Decayed | Ratings | Half-life (weeks) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Aces per serve point | 67.5% | 43% | 45% | 47% | – | 63.8% | 43% | 44% | 46% | – | 26 |
| First serves in | 48.5% | 36% | 41% | 45% | – | 53.4% | 46% | 53% | 56% | – | 13 |
| Double faults per serve point | 36.9% | 36% | 42% | 45% | – | 43.2% | 42% | 49% | 51% | – | 26 |
| First-serve points won | 48.9% | 23% | 23% | 24% | – | 47.8% | 26% | 25% | 27% | – | 104 |
| Serve points won | 52.8% | 15% | 14% | 15% | 35% | 50.5% | 15% | 14% | 16% | 34% | 208 |
| Service games held | 43.5% | 16% | 15% | 16% | – | 42.9% | 17% | 15% | 18% | – | 208 |
| Return points won | 52.8% | 8% | 7% | 8% | 35% | 50.5% | 5% | 4% | 5% | 34% | 104 |
| Return games won (breaks) | 43.5% | 7% | 7% | 8% | – | 42.9% | 6% | 5% | 6% | – | 104 |
| Break points faced per service game | 56.5% | 8% | 7% | 8% | – | 46.6% | 8% | 7% | 8% | – | 208 |
| Second-serve points won | 25.6% | 9% | 8% | 10% | – | 23.9% | 13% | 11% | 13% | – | 208 |
| Total points won | 52.1% | 4% | 3% | 4% | 31% | 58.2% | 5% | 3% | 4% | 30% | 208 |
| Games won | 38.1% | 2% | 1% | 2% | – | 51.2% | −4% | 0% | 2% | – | 13 |
| Sets won | 30.1% | 2% | 2% | 3% | – | 30.4% | −4% | 1% | 3% | – | 13 |
| Break points saved | 10.2% | 10% | 7% | 11% | – | 10.9% | 12% | 8% | 12% | – | 208 |
| Break points converted | 10.2% | 4% | 3% | 4% | – | 10.9% | 3% | 2% | 3% | – | 208 |
| Tiebreaks won | 0.7% | – | – | – | – | 0.0% | – | – | – | – | 208 |

**Observed.**

* **The ratings forecast serve, return and total points far better than history alone.** For serve points they beat the tour average by 2.65 milli-log-loss per point (men; 95% range 2.59–2.71) and 2.43 (women; 2.35–2.52). History alone gives 1.13 (1.09–1.16) and 1.10 (1.05–1.15).
  * The serve-point and return-point forecasts score the same points, seen from either player, so their ratings scores are equal.
  * In 2022–2026: 2.72 and 2.46 against 1.18 and 1.11.
* **The three forms are close for every rate.**
  * Decayed is best or level for nearly all.
  * For the serve style the chosen half-lives are short (13–26 weeks), and recency adds 0.3–0.8 milli-log-loss per serve point over the career form.
  * For serve and return skill and break points the chosen half-lives are long (104 weeks for return points, 208, the longest tried, for serve points and break points), so the decayed form is nearly the career form.
* **The last 52 weeks, shrunk, is the weakest of the three for skill rates.** Not shrunk, it is far worse for rare events: tiebreaks 166.37 (men) and 352.01 (women) milli-log-loss per tiebreak worse than the average, break points converted 22.19 and 16.51 worse.
* **The constant hardly matters.** Halving or doubling K, or using the binomial K, moves the career forecast by a median 0.03 milli-log-loss per unit. The largest move is 1.27 per set, for the women's sets won.
* **History from other levels misleads for results.**
  * Women's games won from the whole career is 0.87 milli-log-loss per game worse than the average, and from evaluation-level matches only 1.26 better.
  * Women's sets won: −3.74 against +7.51.
  * Men's sets won: 2.19 against 5.05; men's games won 0.22 against 0.66.
  * For box-score rates the two histories are within 0.2 of each other: few box scores exist below the evaluation levels before 2025.
* **The next match's tiebreaks are almost all chance** (0.7% and 0.0% beyond point luck), and break points 10–11%.

**Inferred.**

* **Knowing the opponent matters more for a point rate than knowing the player better.** The opponent is half of every point.
* **Results rates measure the opposition as much as the player.** A player who won most of their games at ITF level wins fewer at the next level up, so a results rate is only comparable within a level. The audit's C3 (match tiebreaks read as sets in women's ITF scores of 2021–2024) adds phantom games to the same history; the two causes are not separated here.
* **The best forecast of a statistic is not necessarily the best predictor of who wins.** Stage 4 decides that.

## 5. Serve and return ratings: adjusting for the opponent

**The model** (`stage3_ratings.py`). The chance that the server wins a serve point is 1 / (1 + e^−(μ + S_server − R_returner)). μ is the tour's 2010–2018 serve-point share on the surface, on the log-odds scale: men 62.8% on hard, 60.4% on clay, 65.5% on grass; women 55.8%, 55.0%, 58.8%.

**The update.** Each player has a serve rating S and a return rating R, each with a variance. After a match, for A serving to B, with p = the expected share:

* g = points won − n p (points above expectation) and h = n p (1 − p) (their information);
* with V = var(S_A) + var(R_B), S_A moves by var(S_A) g / (1 + V h), and R_B by the opposite with var(R_B);
* the variances shrink by var² h / (1 + V h).

This is one step of a Gaussian posterior on a binomial result, as Glickman's Glicko does for wins. B serving to A likewise, both from the values the match was predicted with. Variances widen with time away (drift), up to a newcomer's.

**The time rule** is Stage 1's: a round's updates wait for the event's next round, an event's reach the player's other events after the week.

**History.** Every singles level from 2010. Only completed matches with a box score move ratings (197,673 men's and 89,115 women's); every match gets pre-match values.

**Why not subtract opponents' averages.** Those averages depend on whom the opponents played. The ratings explain every serve point at once instead.

**The adjusted rates.** Restated as against a typical opponent:

* serve points won: 1 / (1 + e^−(logit(share) + R_opponent − R̄));
* return points won likewise, with the server's rating.

The share is read as (won + ½) / (played + 1). R̄ is the average opponent's pre-match rating in the 2013–2018 analysis matches (0.08 for the men's return and serve, 0.09 and 0.10 for the women's), so an adjusted rate sits on the raw rate's scale.

**Observed: tuning** (`stage3_ratings_summary.json`, `stage3_rating_tuning.csv`).

* **The grid.** Four constants were tuned per tour by the log loss per serve point on the evaluation-level matches of 2013–2018 (2010–2012 warm up), 240 settings per tour, then frozen.
* **The chosen constants:**
  * a newcomer's serve rating starts 0.20 (men) and 0.10 (women) below their return rating;
  * newcomer variances are 0.02 (serve) and 0.005 (return);
  * the drift is 0.0002 (men) and 0.0001 (women) per week away.
* **All lie inside the grid.**
  * A first grid (every newcomer at 0) chose its corner. A second put the serve variance at its top, and the third reaches past it.
  * Only a newcomer's serve start minus return start matters: one constant added to every rating changes no prediction (a test shows it). So the return start is fixed at 0.
  * The surface is flat: 121 (men) and 124 (women) of the 240 settings are within 0.1 milli-log-loss per point of the best.

**Observed: scores.**

| Tour | Window | Matches | Ratings, log loss per serve point | Surface average | Better by (milli-log-loss per point) |
|---|---|---:|---:|---:|---:|
| ATP | 2013–2018 (tuning) | 59,559 | 0.6604 | 0.6635 | 3.08 |
| ATP | 2019–2026 | 87,532 | 0.6615 | 0.6641 | 2.65 |
| ATP | 2022–2026 | 62,397 | 0.6616 | 0.6644 | 2.72 |
| WTA | 2013–2018 (tuning) | 20,844 | 0.6833 | 0.6856 | 2.32 |
| WTA | 2019–2026 | 33,244 | 0.6832 | 0.6856 | 2.44 |
| WTA | 2022–2026 | 22,946 | 0.6832 | 0.6856 | 2.46 |

* Section 4b's ratings score for the women (2.43) differs slightly from this table's 2.44. The two score slightly different sets of points against slightly different averages:
  * 4b scores standard-format evaluation matches against the evaluation levels' surface averages;
  * this table scores every rating match at the evaluation levels (other formats included) against the ratings' own μ, taken from every level.
* Among established players (2,000+ serve points rated) in the 2022–2026 evaluation matches, ratings spread with a standard deviation of 0.17 (serve) and 0.14 (return) on the log-odds scale for the men, 0.15 and 0.12 for the women. Serve and return correlate at 0.43 and 0.47.
* **A sanity check: the highest ratings in 2026** (latest pre-match value, players with 2,000+ serve and return points rated):
  * men's serve: Jannik Sinner +0.84, Reilly Opelka +0.70, Alexander Zverev +0.67, Taylor Fritz +0.66, Ben Shelton +0.65;
  * men's return: Carlos Alcaraz +0.68, Jannik Sinner +0.56, Alex De Minaur +0.51, Dalibor Svrcina +0.50, Francisco Cerundolo +0.49;
  * women's serve: Elena Rybakina +0.66, Aryna Sabalenka +0.62, Karolina Muchova +0.56, Naomi Osaka +0.54, Iga Swiatek +0.53;
  * women's return: Iga Swiatek +0.51, Coco Gauff +0.49, Jessica Pegula +0.43, Elina Svitolina +0.43, Marta Kostyuk +0.43.
  * **Inferred:** these are the expected names.

**Observed: raw → adjusted**, all surfaces:

| Statistic | Tour | Reliability of a season | Matches for half signal | Shrinkage K, matches | Season to season | Hard to clay | Hard to grass | Clay to grass |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Serve points won | ATP | 0.81 → 0.91 | 8.3 → 3.3 | 6.3 → 2.7 | 0.62 → 0.74 | 0.50 → 0.69 | 0.55 → 0.67 | 0.42 → 0.57 |
| Serve points won | WTA | 0.78 → 0.88 | 9.4 → 4.2 | 8.2 → 3.9 | 0.61 → 0.70 | 0.52 → 0.64 | 0.47 → 0.58 | 0.40 → 0.51 |
| Return points won | ATP | 0.76 → 0.88 | 14 → 4.9 | 14 → 4.3 | 0.54 → 0.72 | 0.37 → 0.62 | 0.42 → 0.59 | 0.27 → 0.46 |
| Return points won | WTA | 0.66 → 0.81 | 18 → 6.9 | 17 → 6.0 | 0.42 → 0.64 | 0.33 → 0.54 | 0.35 → 0.52 | 0.24 → 0.40 |

On one surface the gain is larger. Men's return points won on clay go from 0.51 to 0.74 and on grass from 0.19 to 0.44; women's serve points won on grass go from 0.26 to 0.44.

**Inferred.**

* **The opponent mix is a large part of the raw serve and return rates' noise.** Adjusting removes it: match-to-match chance falls from 1.9 to 1.6 times binomial (men's serve).
* **Adjusting reveals more real spread between players.** The true standard deviation of serve points won rises from 0.03 to 0.04. A strong player's raw rate is held down by meeting strong opponents in later rounds and at higher levels.
* **The ratings are the most repeatable measure of serve and return skill this stage found, and they are computed before each match.**

## 6. Verdict per statistic

**Inferred**, from section 2's table (all surfaces), with the season-to-season carry-over and the forecasts as corroboration. A rate that repeats is a trait (a skill) or a style; whether it decides matches is Stage 2's question (`stage2_match_impact.csv`), and the summary combines the two.

* **Repeats strongly** (half signal within a few matches; carry-over near its ceiling or a little below):
  * the serve style: aces, first serves in, double faults;
  * first-serve points won;
  * serve and return points won, above all opponent-adjusted.
* **Repeats** (a season is mostly signal):
  * service games held, return games won (breaks), break points faced per service game;
  * second-serve points won and total points won.
  * Their reliability on one surface is lower, and on grass mostly weak.
* **Repeats, borderline**: games won (men 0.50, women 0.55; both 95% ranges cross 0.5).
  * **Inferred:** results repeat partly because a player's level and opponents repeat. Forecast across levels they mislead, and they are surface-specific.
* **Repeats weakly**: sets won (borderline for the women), break points saved, break points converted (borderline for the women).
  * A season is a third signal or less.
  * Break points behave like pure chance within a player.
  * Stage 2 found break-point over-performance beyond the serve rate barely persistent; break points converted adds little that the return rate does not.
* **Mostly noise**: tiebreaks won (0.06 on both tours; season to season 0.07 and 0.01; the next match's tiebreaks are 99% point luck).

## Problems found in earlier work (reported, not fixed)

1. **Stage 0: the box score with an unreadable count** (Prague 2026, `atp|2026-600|R32|atp:200266|atp:209322`, Stage 2's problem 1). Its hold, break and break-points-faced rates have a denominator but no count. Stage 3 counts a rate only where both are written. Before that rule, this one row broke the men's hold and break-points-faced reliability.
2. **The Stage 0 audit's C3** (a deciding match tiebreak read as a set, 11,127 women's ITF matches, most of them 2021–2024). It feeds phantom games into the history of the women's games won. It is one of the two candidate causes of the women's career forecast of games won scoring worse than the average (section 4b); not separated, not corrected.
3. **Stage 1's split women's identities** (64 established women under a second id from 25 May 2026). Each starts the ratings and every history afresh as a newcomer. Their 2026 forecasts and ratings are affected; not corrected.

Nothing new was found in the sources.

## Decisions for the owner

1. **Retirements.** Left out of every measurement, forecast and rating update here (17,530 men's and 12,685 women's matches), as in Stage 2 (its decision 1). For ratings a retirement's box score covers part of a match. Agree, or count their points?
2. **History for results-based rates.** The Brief takes history from every level. For games and sets won, history from other levels makes the forecast worse than the tour average for the women, and evaluation-level history fixes it (section 4b). For box-score rates it makes no difference. Choose for Stage 4:
   * evaluation-level history for results-based rates;
   * or results-based rates left off in favour of the opponent-adjusted ones.
   
   **Suggestion:** the second.
3. **The shrinkage constants for Stage 4.** `stage3_shrinkage.csv`, years 2010–2018 (the adjusted rates 2013–2018), with the measured chance variation, not the binomial one. They move little with later years, and forecasts barely depend on them. Approve?
4. **The verdict rule.** A typical season at least half signal "repeats", from 0.2 "repeats weakly", below "mostly noise", with "borderline" where the 95% range crosses a line. Accept as the study's reading for the summary, or change the lines?
5. **The serve and return ratings' constants.** Tuned on 2013–2018 and frozen, as Stage 1's Elo constants were. These ratings are built from points, not results, so the owner's entry on Elo does not cover them. Freeze them as they are?
6. **For the Stage 4 candidate list** (the owner approves it before anything is computed). Which of these should be on it?
   * **Suggestion:** the serve and return ratings' pre-match values (`stage3_ratings.parquet`). The expected serve-point shares can be fed to Stage 2's iid model (`stage2_iid.py`) to give a match probability.
   * **Suggestion:** the serve style (aces, first serves in, double faults), decayed with a short half-life: strongly repeating. Its match impact is small in Stage 2.
   * **Leave off** (suggestion): tiebreak record (noise), break-point records (mostly chance; Stage 2 found little beyond luck), and raw results-based rates (level-dependent).

## Suggestions (not applied)

* **Ratings for more rates.** The same kind of rating could be built for other server-against-returner rates (aces, first-serve and second-serve points won, break points), to adjust them for the opponent as serve points are here.
* **Surface in the ratings.** The ratings carry one serve and one return strength per player, with the surface in μ only. The cross-surface correlations of the adjusted rates (0.57–0.69 for the men's serve) leave room for a player-by-surface term.

## Limitations

* **Players are not independent units.** Correlations and their 95% ranges treat player-windows as independent; a player's seasons are not, so the ranges are somewhat too narrow.
* **Who has a large sample is selected on winning.** For results this inflates k at large n. The verdict therefore reads each rate at a typical season among players who play one, and the shrinkage constants come from every player-window.
* **The WTA's box-score holes before 2019** (whole levels missing in some years, the Brief's note) enter the reliability (2013–2026) and shrinkage (2010–2018) measurements, as history. **Inferred:** they thin the samples but do not bias a split-half correlation. The forecasts of the women's box-score rates are scored from 2019 only.
* **The ratings' model.** One serve and one return rating per player on all surfaces, additive on the log-odds scale. Levels are not modelled: they enter only through who plays whom.
  * Below the Challengers, box scores exist only from 2025, so lower-level players' ratings are tied to the pool through few matches.
  * The adjusted rates inherit the model.
* **The carry-over ceiling uses the shrinkage constants.** Where they are not right for the paired players it is off: for results (K among regulars is larger), and on grass (three-season windows). Ratios above 1 there mean "near 1".
* **The forecast scores treat a match's points as independent draws.** The "share captured" takes the tour average as the chance part's rate. Both are approximations, and they apply equally to every form.
* **The half-life grid stops at 208 weeks**, the choice for every skill rate; longer would be the career form.
