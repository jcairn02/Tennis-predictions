# Stage 4: the rundown

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: built 1 Oct 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md); the report section is "The rundown" in [report.html](report.html).

**The plan.** Stage 4 computes [candidates.md](candidates.md), approved as written on 1 Oct 2026 (README, Owner decisions), with its hand-made table `stage4_candidates.csv`. Their SHA-256 hashes are recorded in `stage4_features_summary.json` and `stage4_results.json`, and the scoring script refuses to run if the plan has changed since the features were built:

* `candidates.md`: `504c729a356cdb5f1ee06c01081ce3ee4f065714f5aac4028f7be7b8d7290b0a`
* `stage4_candidates.csv`: `14cbbd0467fc7c435f40d5e7c752c61de956491115d3412213fd7f2831a45d6d`

Nothing was added to the list. Where Stage 4 had to set something the plan left open, it is listed under [What Stage 4 set](#what-stage-4-set-that-the-plan-left-open), with what was added after a first run.

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/predictability_diagnostic/`: from `stage4_results.json` or `stage4_ranking.csv` unless another file is named (`stage4_features_summary.json`, `stage4_constants.csv`, `stage4_leak_checks.csv`, `stage4_event_country_summary.json`, `stage4_results.csv`).

## In short

* **Observed. What was scored.** 163 men's rows and 162 women's: a row is a candidate in one form, for one tour.
  * Each is scored walk-forward, season by season, three ways: alone against a coin, added to surface Elo ("given Elo"), and added to the closing odds ("given the market").
  * Each score has 20 shuffled copies of the feature beside it: 956 scores and 19,120 copies (`stage4_null_copies.csv`). Match length has no score alone: it acts through the baseline's odds.
  * 158 men's and 161 women's rows were scored. The other six carry nothing. For the men, break points won above expectation shows no spread between players' seasons, so every man gets the average in all five forms. The women's protected ranking never has 300 non-zero training matches.
* **Observed. Given Elo, many rows add something real, and a few add a lot.**
  * 73 men's and 58 women's rows clear the family-wide line, the multiple-comparison guard (9.9 and 8.1 standard deviations of their shuffled copies).
  * Findings, which also gain in at least three eras: 63 men's rows and 47 women's. Of these, 15 and 13 gain 1 milli-log-loss or more, the plan's "clear"; the rest are "small".
  * The largest gains in milli-log-loss, better than Elo alone over all scored seasons:

    | Row | Men | 95% range | Women | 95% range |
    |---|---:|---|---:|---|
    | Serve and return ratings through the iid model | 3.61 | 3.04–4.18 | 4.58 | 3.64–5.52 |
    | Games-weighted Elo | 1.82 | 1.55–2.08 | 2.38 | 1.96–2.79 |
    | Sets over the last 14 days | 1.63 | 1.41–1.84 | 1.87 | 1.49–2.25 |
    | The points matchup, last 52 weeks | 1.55 | 1.26–1.85 | 1.59 | 1.05–2.12 |

  * For scale: on the matches with odds, Elo trails the market by 22.5 (men) and 18.8 (women) in 2022–2026 (Stage 1).
* **Observed. Given the closing odds, almost nothing.**
  * No row gains 1 milli-log-loss, the plan's "clear" line.
  * The largest gains are 0.32 (the women's ranking, 95% range 0.01 to 0.62) and 0.30 (the men's sets over the last 7 days, 0.05 to 0.54).
  * 3 men's and 8 women's rows clear the family-wide line given the market, all "small" on the plan's scale.
  * Of the four leaders above, the ratings through the iid model and the games-weighted Elo add nothing on the market (−0.06 to −0.01). The points matchup adds 0.09 (men) and 0.03 (women), and sets over the last 14 days 0.23 and 0.29.
* **Observed. Recent form beats opponent adjustment.**
  * For 16 of the 25 men's statistics and matchups, and 18 of the 26 women's, the last-52-weeks form adds the most to Elo.
  * The opponent-adjusted form does best for one men's and two women's statistics, though the plan expected it to do best for most.
  * **Inferred:** Elo already adjusts for the opponent by construction; what it misses is recent form. The serve and return ratings carry both, and lead.
* **Observed. The ranking scores worse than Elo alone over all seasons, and better in 2022–2026.**
  * The men's ranking scores 1.67 worse given Elo over all seasons. Season by season it is 2.60 worse in 2013 and 0.51 better in 2026.
  * **Inferred:** the walk-forward fits start on 2010–2012, when Elo is still warming up from 1,500 for every player, so the ranking is over-weighted in the early fits. This touches every feature that stands in for strength ([section 6](#6-why-the-ranking-looks-worse-than-it-is)).
* **Observed. Leak checks** ([section 7](#7-leak-checks)).
  * The probe cut by date, event and round left the features of all 107,752 protected matches unchanged, once the match's format is taken from the source's record. A deliberately leaky control moved at 30.
  * With the format read from the match's own score, as the plan reads it, only the 17 format-dependent columns moved. Rebuilt from the record, their improvements change by at most 0.015 milli-log-loss.
  * Built one match later, none of the ten strongest rows per tour collapses: each stays well above its null band.
  * The small gains over the market survive the lag where the feature is stable public information (the women's ranking: 0.32 to 0.31). They vanish where the lagged feature measures a different, older window (the men's sets over 7 days: 0.30 to 0.03).
* **For the owner.** Nine decisions, [at the end](#decisions-for-the-owner).

## What was built

| File | What it holds |
|---|---|
| `stage4_event_country.csv` (hand-made, tracked) | Each evaluation event's country as an IOC code, from the city in its name: 837 rows for 630 men's and 204 women's event names, one row per name, with a season span or a tournament id where an event moved or a name is shared |
| `stage4_event_country_check.csv`, `stage4_event_country_summary.json` | The table against tennis-data.co.uk's location, the country codes in the WTA's 2013–2015 tournament ids and the WTA calendar; every disagreement listed |
| `stage4_features.parquet` (197.0 MB) | One row per evaluation-level match of 2010–2026 (completed or retired; 182,440 men's, 72,683 women's): the result, surface Elo's and the market's probabilities, the level group, and each candidate × form's inputs, missing where the feature does not exist |
| `stage4_constants.csv` | The constants set in Stage 4 (the shrinkage constants of the new statistics, the opponent adjustment's slopes, the surface averages, the weighted Elos' scale), with bootstrap ranges |
| `stage4_features_summary.json` | The plan's hashes, the coverage reproduced against the plan's counts, the probe |
| `stage4_results.csv` | The rundown: one row per candidate × form × tour × group (all scored seasons, 2019–2026, 2022–2026, each era, each level group, each season), with coverage, the three scores, each score's null band, and the given-Elo coefficient refitted inside the group; per season, the walk-forward fit's own coefficients |
| `stage4_ranking.csv` | One row per candidate × form × tour: the ranking's columns, the plan's expectations beside what was seen, the reading |
| `stage4_null_copies.csv` | Every shuffled copy's improvement over all scored seasons (the family-wide line's inputs) |
| `stage4_leak_checks.csv` | The two rebuilds: one match later, and the format from the record (with the matches whose values differ, by season and by event and round) |
| `stage4_results.json` | Everything quoted here and in the report |

Code in `src/eda/predictability_diagnostic/`:

* `stage4_country.py`: applies and checks the country table (15 seconds).
* `stage4_features.py`: every feature in one chronological pass, the constants, the coverage check and the probe (about 9 minutes).
* `stage4_rundown.py`: the walk-forward scores, null bands, the family-wide line, direction by era and level, and the leak checks (about 13 minutes, 14 worker processes).
* `report_stage4.py`: the report section.

Tests: `test/predictability_diagnostic/test_stage4.py` (19 tests). `stage4_features.parquet` is over 50 MB and is listed in [data/LARGE_FILES.md](../../../data/LARGE_FILES.md).

## Terms used here

* **Row.** A candidate in one form, for one tour. The forms are career to date, the last 52 weeks, decayed (half-life 52 weeks), this surface only and opponent-adjusted (candidates.md, section 2). A single feature has one form.
* **Log loss, milli-log-loss.** As in Stage 1: minus the log of the probability given to the winner, averaged; a coin scores 0.693, and one milli-log-loss is 0.001. Improvements are positive when better.
* **The three scores.** Each is the baseline's log loss minus the row's model's, per match, on the matches where the row exists.
  * *Alone*: the feature against a coin.
  * *Given Elo*: Stage 1's surface Elo (retirements counted) plus the feature, against surface Elo alone, refitted on the same matches.
  * *Given the market*: the same with the closing odds, on main-tour matches that have them.
  * Each model is a logistic regression without an intercept.
* **Walk-forward.** For each season from 2013 (the women's box-score rows from 2019): fitted on the evaluation-level matches of 2010 to the season before, scored on that season.
* **Null band.** The range of the improvements of 20 copies of the feature, shuffled within each season. Every match carries 20 random keys shared by every row, so a copy shuffles every feature the same way. A copy knows nothing about who won, so its score is what chance gives a feature of that kind.
* **Family-wide line.** Per tour and score, each row's improvement is put on one scale: minus its copies' mean, over their standard deviation.
  * Each copy's largest value over all rows is the best that useless features, as correlated as these, reach. The line is the largest of the 20.
  * A row above it is about a 1-in-21 event for the whole family of about 160 rows, not for one row.
* **Reading** (the plan's rule, fixed in advance):
  * **finding**: clears the line given Elo, and its improvement given Elo is positive in at least three eras;
  * **possible**: above its own band but not the line;
  * **no sign**: inside its band;
  * **worse**: below its band.
* **The plan's scale.** Alone: none (inside the band), weak (under 10), moderate (10–40), strong (40 or more). Given Elo or the market: none, small (under 1), clear (1 or more), worse (below the band).
* **Eras.** 2013–16, 2017–19, 2020–21, 2022–26.
* **Directional.** A group of fewer than 300 matches: its result shows a direction only.

## What Stage 4 set that the plan left open

**Before anything was scored:**

* **The constants the plan left to Stage 4** (`stage4_constants.csv`), estimated by Stage 3's method on player-seasons of 2010–2018 (grass in three-season windows).
  * **Shrinkage constants**, all surfaces:
    * match wins: 29 matches (men) and 28 (women);
    * deciding sets: 101 and 97;
    * return points against the first serve: 886 and 947 points;
    * against the second serve: 623 and 623.
  * **Break points won above expectation.** For the men, no spread between players' seasons on any surface: the constant is infinite, so every man gets the average. For the women: 10,583 break points, about 629 matches.
  * **Big-point play on return**, from the Grand Slam point-by-point seasons 2011–2018: 494 matches (men) and 160 (women). Each bootstrap range reaches "no signal".
  * **The weighted Elos' scale**: the mean winner's share of the games is 0.650 (men) and 0.673 (women), of the points 0.626 and 0.658.
* **The opponent adjustment's slopes (β)**, 2013–2018. The slope of each match's log-odds rate on the opponent's rating, with an intercept per surface (the plan names the slope; the surface intercept is Stage 4's). For example:
  * service games held 0.87 (men) and 1.17 (women); breaks 1.50 and 1.61; matches won 0.67 and 0.82; total points won 0.16 and 0.22.
  * **Observed:** fitted the same way, serve points won give 0.36 (men) and 0.47 (women), where Stage 3's model, which the plan uses for them, implies 1.
  * **Inferred:** a simple slope is attenuated, because players meet opponents of similar strength. If the same holds for the other statistics, their adjusted forms take out only part of the opponent's effect. This is decision 4.
* **The tournament's country** (the plan's section 4.6). The table gives a country to every one of the 834 evaluation event names except Kingston (2026, two Challengers, 62 men's matches). Several cities share that name, and it is left blank rather than read from the players' nationalities, which would bias the home-country feature.
  * The table agrees with tennis-data.co.uk on 63,887 of 63,941 linked matches.
  * It agrees with the country codes in the WTA's 2013–2015 tournament ids on 187 of 187 events, and with the WTA calendar on 644 of 647. The calendar writes Hong Kong as China in 2023–2024.
  * The 54 tennis-data disagreements are the ATP's 2020 Adelaide and Auckland events, 27 matches each, whose names tennis-data's workbook exchanges ([problems](#problems-found-in-earlier-work-reported-not-fixed)).
  * 209 evaluation player rows carry a country code other than the IOC's (`stage4_event_country_summary.json`, `player_rows_aliased`): 53 an ISO code, 153 Lebanon's LIB (the IOC's LBN), and 3 New Caledonia's or Guadeloupe's own code (NCL 2, GUD 1). They are read as the IOC code, the last three as France, as the event table codes those territories (`stage4_country.PLAYER_ALIASES`).
* **The walk-forward's minimum.** A season is scored only when its training set holds 300 matches or more (the Brief's 300); the plan named no minimum.

**After the first full run (disclosed):**

* **A second minimum: 300 training matches on which the feature is not zero.** The first run showed unpenalised fits separating: a rare input that only ever went with one result, whose coefficient then runs off.
  * The women's minutes over the last 7 days were fitted in 2016 on 2 non-zero values among 4,255 training matches, because women's minutes are almost absent before 2016. The season's predictions were ruined.
  * Rare entry types were affected too, in both the real fits and the shuffled copies.
  * With the second minimum, no fit separates (`*_separated_*` in the ranking: 0).
  * The seasons it leaves out are listed per row (`*_skipped_seasons`, beside those the first minimum leaves out). It touches the women's minutes over 7 and 14 days (2013–2016), the lucky losers and the protected ranking of both tours, and the men's wildcards given the market (2014). The women's protected ranking it leaves unscored.
  * The unpenalised fit is the plan's; the guard is decision 2.
* **Per-season results** were added to the output, with each season's walk-forward coefficients, to show the pattern in section 6. They are a finer grouping of the plan's walk-forward, not a new score.
* **Rows that never pass the minimum** are read "not scored", a reading the plan's rule does not name (one row: the women's protected ranking).

## 1. The features, and the checks on them

**Observed.**

* **The plan reproduced.** For 324 of 325 rows, the evaluation matches on which a feature exists equal the plan's own coverage counts (`stage4_candidates_coverage.csv`) exactly. The exception is the men's home country: 57 fewer matches, the Kingston events (62 matches, of which 5 already lacked a player's country).
* **One chronological pass.**
  * Every history goes through `common.asof_sums`, or Stage 3's `lookback_sums` and `sums_before`, over every player-match on file, never a per-row look-back.
  * The previous match comes from a vectorised search under the same rule.
  * Stage 3's constants, ratings and adjusted serve and return rates, and Stage 1's Elo, are used as they are.
  * The weighted Elos are Stage 1's pass with each update weighted. A test shows that with weights of 1 they equal Stage 1's pass, and with weights of 2 they equal a pass with k0 doubled.
* **Tests** (19, on hand-made histories against a row-by-row reading of the rule):
  * the previous match;
  * all five forms of a history (career, 52 weeks, decayed, surface with an infinite constant, adjusted);
  * the meetings (a round robin blind to itself, walkovers not counted);
  * the iid model's formats;
  * the weighted Elo under the date-and-round probe;
  * the Newton fits against scikit-learn's;
  * walk-forward never seeing the season it scores;
  * the copies staying inside their season;
  * the family-wide line;
  * the leak check's count of the matches that differ, by season and event;
  * the plan's expectations read for every candidate;
  * the country table's precedence and coverage.
* **The probe** ([section 7](#7-leak-checks)).

## 2. The rundown

**How to read the numbers.**

* An improvement of 1 milli-log-loss given Elo means the feature makes Elo's forecasts better by 0.001 log loss per match on average.
* For scale: the leaders gain 3.61 (men) and 4.58 (women) given Elo on all evaluation matches. On the matches with odds of 2022–2026, the market beats Elo by 22.5 and 18.8 (Stage 1).
* Each row is scored on 12,368 to 155,130 matches (`elo_scored`; the fewest are the head-to-head rows, which exist only where the two have met). So the shuffled copies' scores vary little: a band given Elo is a median 0.03 milli-log-loss wide for the men and 0.09 for the women.
* So small real effects clear their band and the line: the smallest improvements above the line are 0.05 (men) and 0.13 (women). A finding means "beyond chance", not "large"; the plan's scale (small under 1, clear from 1) carries the size.

**Observed. The readings, given Elo:**

| Reading | Men | Women |
|---|---:|---:|
| Finding | 63 | 47 |
| Possible | 27 | 50 |
| No sign | 18 | 45 |
| Worse | 50 | 19 |
| No information (constant) | 5 | 0 |
| Not scored | 0 | 1 |

**Observed. The ten strongest given Elo** (milli-log-loss better than Elo alone; all scored seasons, then 2022–2026):

| Men | All | 2022–26 | Women | All | 2022–26 |
|---|---:|---:|---|---:|---:|
| Ratings through the iid model | 3.61 | 4.11 | Ratings through the iid model | 4.58 | 4.06 |
| Games-weighted Elo | 1.82 | 1.32 | Games-weighted Elo | 2.38 | 2.22 |
| Sets over the last 14 days | 1.63 | 1.74 | Sets over the last 14 days | 1.87 | 2.11 |
| Points matchup, 52 weeks | 1.55 | 2.26 | Serve rating | 1.87 | 1.59 |
| Serve point from its parts, 52 weeks | 1.53 | 2.23 | Minutes over the last 14 days | 1.59 | 1.84 |
| Minutes over the last 14 days | 1.51 | 1.50 | Points matchup, 52 weeks | 1.59 | 1.20 |
| One of the first matches on the surface | 1.45 | 1.55 | Serve point from its parts, 52 weeks | 1.49 | 1.11 |
| Age | 1.42 | 2.88 | Total points won, 52 weeks | 1.39 | 1.04 |
| Points matchup, decayed | 1.39 | 2.05 | Games matchup, 52 weeks | 1.34 | 1.07 |
| Serve point from its parts, decayed | 1.38 | 2.03 | One of the first matches on the surface | 1.30 | 1.71 |

Every one of them is a finding: it clears the line given Elo and gains in three eras or more. The full ranking, sortable, is in the report.

**Observed. The signs, given Elo** (the refitted coefficient over all seasons, per standard deviation of the feature):

* **More recent load wins more often than Elo says.** The sets and minutes over the last 14 days take +0.14 and +0.13 (men), +0.15 and +0.13 (women).
* **The first matches on a surface lose more often:** −0.13 on both tours.
* **Age** (men): −0.13 for the linear term; older players lose more often than Elo says.
* **Days since the last match:** −0.10 (men), −0.12 (women).
* **Inferred:** "load" counts matches won recently: a player still in a draw has played more. It is not fatigue, which the plan's "?" left open.

**Observed. Two negative controls are not quite null.**

* The tiebreak record over 52 weeks is a finding on both tours (+0.14 men, +0.23 women), with a negative coefficient (−0.045 and −0.053): players who won more tiebreaks recently win *less* often than Elo says.
* Big-point play on return (men, possible, +0.09) also takes a negative sign (−0.043), where the plan expected +.
* **Inferred:** Elo counts lucky wins, decided in tiebreaks or on big points, as skill. A record of that luck corrects Elo downward. This reads as luck, not a trait.

**Observed. Against the plan's expectations,** given Elo (`stage4_ranking.csv`, `elo_expected` and `elo_observed`):

| Expected | Men: seen clear | small | none | worse | Women: clear | small | none | worse |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Clear (12 men's rows) | 5 | 7 | 0 | 0 | – | – | – | – |
| Small | 8 | 46 | 0 | 25 | 11 | 56 | 13 | 9 |
| None | 2 | 22 | 18 | 25 | 2 | 28 | 32 | 10 |

The women's rows have no "clear" expectation; one women's row expected "small" was never scored.

* **The surprises upward:**
  * the load features (sets and minutes over 14 days, both tours: expected none, seen clear);
  * expected small, seen clear: the games-weighted Elo, the serve rating and the first matches on a surface (both tours); age, and total points won and the games matchup over 52 weeks and decayed (men); the ratings through the iid model, the points, components and games matchups and total points won over 52 weeks, and the points and components matchups and total points won decayed (women).
* **Downward:**
  * the ranking-type features (section 6), expected small, seen worse;
  * for the men, the serve statistics (serve points, first- and second-serve points, holds, break points faced) in their career, surface and adjusted forms, games won in four forms and wildcards: expected small, seen worse, by 0.02 to 0.36. For the women: games won (career and adjusted), home country and return against the second serve (career), by 0.03 to 0.33;
  * the men's matchups in their career, surface and adjusted forms, and match length: expected clear, seen small.
* **Given the market:**
  * no row was expected to do better than small, and none did;
  * 47 men's and 14 women's rows expected "none" were seen "small" (above their band, under 1).

**Observed. Which form did best given Elo** (the report has every statistic):

| Best form | Men (of 25 statistics and matchups) | Women (of 26) |
|---|---:|---:|
| Last 52 weeks | 16 | 18 |
| This surface | 8 | 5 |
| Opponent-adjusted | 1 (matches won, negative) | 2 (first serves in, head to head) |
| Decayed | 0 | 1 |

* The opponent-adjusted form beats the career form for 21 of 25 men's statistics and 16 of 26 women's. But the 52-week, decayed and surface forms each beat the adjusted form for 20 to 23 statistics on each tour.
* **Inferred:** Elo already weighs each result by the opponent's rating. What a history adds beyond it is recency, which an established player's Elo (a small K) follows slowly. The serve and return ratings carry both, through the iid model, and lead.

**Observed. Alone, against a coin.**

* The Elo variants come first: games-weighted Elo is 89.8 (men) and 92.0 (women) better than a coin, points-weighted 89.0 and 91.5.
* Then the ratings through the iid model (76.9 and 82.0), and the ranking (59.8 and 59.1).
* 152 men's and 140 women's rows clear the family-wide line alone: almost anything that measures strength predicts the winner.

## 3. Given the market

**Observed.**

* **No row gains 1 milli-log-loss on the closing odds.** 49 men's and 15 women's rows are above their band; 3 and 8 clear the family-wide line given the market:

| Row | Tour | Given the market | 95% range | 2022–2026 |
|---|---|---:|---|---:|
| Ranking | women | 0.32 | 0.01 to 0.62 | 0.36 |
| Sets over the last 7 days | men | 0.30 | 0.05 to 0.54 | 0.28 |
| Sets over the last 14 days | women | 0.29 | −0.06 to 0.64 | 0.41 |
| Gap between ranking and Elo | women | 0.27 | −0.01 to 0.55 | 0.15 |
| Sets over the last 14 days | men | 0.23 | −0.01 to 0.48 | −0.04 |
| Level played over the last 52 weeks | women | 0.21 | −0.07 to 0.48 | 0.12 |
| Ranking points | women | 0.20 | −0.04 to 0.44 | 0.17 |
| One of the first matches on the surface | women | 0.20 | −0.01 to 0.41 | 0.43 |
| Days since the last match | women | 0.19 | −0.16 to 0.54 | 0.27 |
| Minutes over the last 7 days | men | 0.18 | −0.05 to 0.41 | 0.18 |
| Matches played, career | women | 0.16 | −0.07 to 0.40 | 0.01 |

* The leaders given Elo add nothing on the market: −0.06 and −0.01 for the ratings through the iid model, −0.03 and −0.03 for the games-weighted Elo.
* **Inferred:** the market already holds what Elo misses from these histories. What survives against it is a few tenths of a milli-log-loss from public information: the women's ranking, recent load and scheduling. A log-loss gain is not a betting edge; this stage does not measure one.
* Two men's rows are below their band given the market: the head-to-head record over 52 weeks and on the surface.

## 4. Direction by era and level

**Observed** (`stage4_results.csv`; the coefficients are refitted inside each group, given Elo).

* **The leaders gain in almost every era.** Seven of the men's ten strongest rows, and all ten women's, gain given Elo in every era scored (the women's box-score rows have three eras, from 2019).
  * The ratings through the iid model gain 3.05, 2.50, 5.70 and 4.11 (men, 2013–16 to 2022–26) and 4.35, 6.77 and 4.06 (women, 2019 to 2022–26).
  * The three exceptions are the men's, each below Elo in 2013–16 only: the points matchup over 52 weeks −0.12 (then 0.98, 4.36 and 2.26), the serve point from its parts over 52 weeks −0.05, and age −1.10 (then 0.46, 4.19 and 2.88).
* **By level, the ratings through the iid model gain most at the Grand Slams:** 14.40 given Elo for the men (6,951 matches) and 8.41 for the women (3,921). **Inferred:** for the men, part of this is the format: Elo does not know that these matches are best of five (Stage 1), and the iid model does. The women's Slams are best of three, so the format is not the whole of it.
* **The games-weighted Elo** gains at every level on both tours. Its coefficient is positive in every era: 2.0–2.6 (men), 1.6–2.4 (women).
* **The Tour Finals** are directional only for the women (285 matches at most). The men's hold 315 matches for a row with full coverage, fewer (directional) for rows with less.
* The report charts every leading row by era and level.

## 5. Coverage

**Observed** (`stage4_ranking.csv`, `elo_coverage`; the share of the tour's evaluation matches of the row's scored seasons on which it was scored).

* Box-score histories and the matchups built from them: 96–98%.
* The ratings, the weighted Elos and Elo's change, the ranking, age, activity and load from the score: 98–100%.
* Head to head: 18% (men, 52 weeks) to 47% (women, career).
* The entry types: 42–90%, scored only where their code is recorded.
* Minutes: the men's over 14 days 75%, the women's 52%.
* Big-point play on return: 32% (men) and 60% (women).
* Height: 87% and 65%.
* The women's protected ranking: 0%, never scored.

## 6. Why the ranking looks worse than it is

**Observed.** Given Elo, over all seasons, these score worse than Elo alone:

* the ranking: 1.67 (men) and 1.76 (women) worse;
* ranking points: 1.68 and 0.98 worse;
* the gap between ranking and Elo: 2.26 and 1.84 worse;
* the level played over 52 weeks: 2.48 and 2.09 worse.

Refitted on all scored seasons at once, the ranking and ranking points take positive coefficients (+0.106 and +0.123 per standard deviation for the men, +0.080 and +0.141 for the women). The gap, which is Elo's rating minus the one the ranking implies, takes a negative one (−0.084 and −0.062), which also weights the ranking. The level played's is near zero (−0.012 and −0.009).

The ranking's walk-forward improvement given Elo, by season:

| | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Men | −2.60 | −3.95 | −2.46 | −2.56 | −5.58 | −3.35 | −2.56 | −2.27 | −1.41 | −0.26 | +0.63 | +0.30 | +0.07 | +0.51 |
| Women | +0.93 | −2.05 | −4.70 | −2.91 | −7.49 | −2.28 | −3.16 | −3.04 | −3.03 | −2.87 | +0.42 | +1.00 | +0.18 | +3.15 |

In 2022–2026: +0.24 (men), +0.28 (women). Ranking points +0.31 and +0.89. The gap +0.15 and +0.29.

The walk-forward fits' own weights for the ranking (`stage4_results.csv`, season rows, `elo_walk_coef`, `elo_walk_base_in_model`, `elo_walk_base_alone`):

| Fit for | Ranking (per standard deviation), men | Elo's log-odds beside it | Elo's log-odds alone | Ranking, women | Elo beside it | Elo alone |
|---|---:|---:|---:|---:|---:|---:|
| 2013 (trained on 2010–2012) | 0.61 | 0.40 | 0.73 | 0.63 | 0.37 | 0.65 |
| 2019 (2010–2018) | 0.33 | 0.68 | 0.91 | 0.35 | 0.63 | 0.86 |
| 2026 (2010–2025) | 0.24 | 0.72 | 0.89 | 0.24 | 0.76 | 0.93 |

For the men, the level played over 52 weeks follows the same course, from 0.39 in the 2013 fit to 0.07 in the 2026 fit; matches played (career) from 0.24 to −0.02.

**Inferred.**

* The walk-forward fits begin on 2010–2012, the seasons in which Elo is still warming up from 1,500 for every player.
* There a ranking corrects an immature rating, so the first fits weight it heavily and Elo lightly. In the women's 2013 season that still helps (+0.93).
* Every later fit still carries those seasons, so the ranking's weight comes down only slowly while Elo matures, and on both tours the ranking costs more than it adds in every season from 2014 to 2022.
* The plan fixes this window. The full-period ranking therefore understates every feature that stands in for strength, and the reading marks them worse.
* For them, 2022–2026 is the fairer reading: there the ranking, ranking points and the gap add 0.15 to 0.89 given Elo. The level played over 52 weeks is still worse there: −1.36 (men), −1.11 (women).

## 7. Leak checks

What was checked, in order.

**1. The probe cut by date, event and round** (`stage4_features_summary.json`, `probe`).

* **Setup.** On the matches of 2025–2026, both tours, with history inside the slice, 4 cut matches were chosen in 2026. At each, the following were redrawn:
  * what was played in every match the time rule does not let the cut see (its own round and later rounds of its event, the week's other events, later weeks): results, box scores, scores, minutes, statuses and point-by-point values;
  * the pre-match values of every match after the protected set: rankings, ages, ratings, Elo.
* Every feature (165 columns) was rebuilt, with the weighted Elos rerun on the redrawn results. Checked: the features of the 107,752 protected match-cuts (earlier weeks, and the cut event's rounds up to and including the cut's).
* **Format from the source's record:** 0 changed (largest difference 1.1e-14, rounding). 28,716 later ones changed. A deliberately leaky control, career wins counted with the match itself, changed at 30.
* **Format read from the match's own score, as the plan reads it:** 27 protected matches changed, all in the 17 columns that use the format: the three matchups through the iid model in five forms, the ratings through it, match length.
* **Inferred:** the plan reads best of five from the score, as Stage 2 did. That uses the match's own outcome, though it tells the format and not the winner.

**2. The format, rebuilt from the record** (`stage4_leak_checks.csv`, "format recorded").

* Rebuilt from the source's recorded best-of and the Next Gen Finals' short sets only, the format-dependent rows change on at most 111 men's matches and 1 women's (a qualifying match at Cincinnati in 2012).
* The 111 are all Wimbledon's last qualifying round, which the source records as best of three though its scores show five sets: 16 per season in 2015–2019 and 2022, 15 in 2024 (`differ_by_event`, `differ_by_season`).
* Their improvements change by at most 0.015 milli-log-loss: match length given Elo 0.298 to 0.313; every other row by 0.003 or less. Given the market, no improvement changes by more than 1e-8.

**3. One match later** (`stage4_leak_checks.csv`, "one match later").

* **Setup.** Rebuilt with each player's history read as it stood at their previous match of that history (the same code evaluated at the earlier row), and scored on the matches where both versions exist. Rebuilt:
  * the ten strongest rows per tour given Elo;
  * as a precaution, every row that clears the family-wide line given the market.
* **No row gained 1 milli-log-loss on the market**, the "large gain" that would make it a suspected leak by the rule set before scoring, so no row was checked on that ground.
* **The ten strongest, given Elo, as built and one match later:**
  * ratings through the iid model 3.61 to 2.56 (men), 4.58 to 3.37 (women);
  * points matchup (52 weeks) 1.61 to 1.33 and 1.48 to 1.12;
  * age 1.54 to 1.48;
  * first matches on a surface 1.45 to 1.35 and 1.30 to 1.42;
  * games-weighted Elo 1.82 to 0.33 and 2.38 to 0.57.
  * These are on the matches where both versions exist, so some differ slightly from the ranking.
  * Every lagged value stays well above its row's band: the lowest is 0.33 (the men's games-weighted Elo), and the highest band edge among these rows is 0.10.
* **Inferred.** None collapses.
  * The ratings and matchups lose part of their gain: the last match's serve points carry information that Elo, which has the last result, does not.
  * The games-weighted Elo falls furthest, from 1.82 to 0.33 and from 2.38 to 0.57: what it adds to Elo is the margin of the most recent results, so delaying it by one match removes most of that.
  * For the load features (sets and minutes over 7 or 14 days, days since the last match) the lagged version is a different quantity: the load before the previous match, correlating at 0.02–0.46 with the original. So this check cannot separate a leak from recency for them; the probe can, and found none.
* **Given the market, the precautionary rows:**
  * the women's ranking 0.32 to 0.31, ranking points 0.21 to 0.16, the gap 0.27 to 0.20, level played 0.20 to 0.20, matches played 0.16 to 0.16: stable public information, as expected;
  * the load features fall towards zero: the men's sets over 7 days 0.30 to 0.03, minutes over 7 days 0.17 to 0.04, the women's days since the last match 0.19 to 0.03;
  * three more rows above the line given the market were already among the ten strongest: sets over the last 14 days, 0.23 to 0.14 (men) and 0.29 to 0.09 (women), and the women's first matches on a surface, 0.20 to 0.16.

**4. A leak would beat the market.** A feature that knew the match's result would beat the closing odds, which do not. **Observed:** no row gains 1 milli-log-loss given the market. The largest gain of any row is 0.32 (the women's ranking); among the ten strongest rows given Elo, 0.23 (men) and 0.29 (women), both sets over the last 14 days.

**Inferred.** No check points to a leak. The one dependency on the match's own outcome is the plan's own reading of the format, and it changes the scores by at most 0.015 milli-log-loss.

## Problems found in earlier work (reported, not fixed)

1. **tennis-data.co.uk's ATP 2020 workbook exchanges Adelaide and Auckland.** Rublev's Adelaide final is filed as the ASB Classic (Auckland) and Humbert's Auckland final as the Adelaide International. Stage 0 has them right. The odds are unaffected: Stage 1 links by players and scores. Found by the country check (54 matches).
2. **Wimbledon's last qualifying round recorded as best of three** (Stage 2's problem 2). It is so in 2015–2018 too, not only in the 2019, 2022 and 2024 seasons Stage 2 counted inside its box-score population: 16 matches per season in 2015–2019 and 2022, 15 in 2024 (`stage4_leak_checks.csv`, `differ_by_season`). Stage 2's "in the other years the record agrees with the scores" holds only inside that population.
3. **The plan's reading of best of five from the score** (candidates.md, section 3.3, as Stage 2 did) depends on the match's own outcome. The probe flags it ([section 7](#7-leak-checks)); the effect on the scores is at most 0.015.
4. **The plan's section 4.6 says no file on disk gives every event's country.** That stands, but Sackmann's WTA tournament ids of 2013–2015 carry a country code for every event (187), a partial source the plan did not list. It is used here as a check.
5. **Stage 0's players' countries** carry codes other than the IOC's in 209 evaluation player rows: 53 ISO codes, 153 Lebanon's LIB (against LBN), and New Caledonia's NCL (2) and Guadeloupe's GUD (1). Read as IOC here, the last three as France.
6. **Earlier stages' open problems** feed every history here, unchanged: the women's split identities of 2026 (Stage 1), match tiebreaks read as sets (the audit's C3), repeated Tennis My Life rows (C1), break counts that do not add up (P2).

## Worth testing in a later round (listed, not computed)

* **The walk-forward without the warm-up seasons.** Training from 2013 (scoring from 2014), or Elo warmed up before 2010, to read the strength-proxy features without the artifact of section 6.
* **The opponent adjustment with a partial slope.** A rate's slope on the opponent's rating holding the player's own rating fixed, which would undo the attenuation (decision 4).
* **Break points above expectation on career windows.** Stage 2 found the men's record persisting beyond luck between career halves; season windows find no spread.
* **A few inputs together.** For example, the ratings through the iid model, the games-weighted Elo and recent load in one model: still within "logistic regression on a few inputs", but not in the plan.
* **The load and schedule features on dated matches.** tennis-data.co.uk dates main-tour matches by day (the plan's decision 8). With the women's ranking-type features, they are the only rows above the family-wide line given the market.
* **Luck as a correction to Elo.** The tiebreak record and big-point play predict *against* Elo: small, and above the line for the tiebreak record over 52 weeks on both tours.
* **The format from the record**, with a hand rule for Wimbledon's last qualifying round, in place of the score.

## Decisions for the owner

1. **The training window** ([section 6](#6-why-the-ranking-looks-worse-than-it-is)). The plan trains the walk-forward from 2010, while Elo is warming up, which distorts every strength proxy. Keep it as the study's reading (with 2022–2026 quoted beside it), or rescore from 2013 in a later round?
2. **The minimum training rule** ([What Stage 4 set](#what-stage-4-set-that-the-plan-left-open)). 300 training matches, and 300 on which the feature is not zero. The second part was added after the first run showed separation. Approve, or treat sparse features another way, for example a weak penalty?
3. **The format** ([section 7](#7-leak-checks)). Keep reading best of five from the score, as the plan does (a dependency on the match's own outcome, worth at most 0.015), or switch to the source's record with a hand rule for Wimbledon's last qualifying round?
4. **The opponent adjustment's slope.** Fitted to serve points, the plan's simple slope gives 0.36 (men) and 0.47 (women), where Stage 3's model implies 1. Keep it, or use a partial slope in a later round?
5. **Break points above expectation, men.** No spread between seasons, so every man gets the average and the statistic carries nothing. Accept, or estimate the constant on longer windows?
6. **The women's protected ranking.** Too rare in the recorded seasons ever to have 300 non-zero training matches. Drop it, or keep it for more data?
7. **The country table.** Kingston (2026, 62 matches) is unresolved. Supply its country, or leave it blank? Monte Carlo is coded Monaco, though the club is in Roquebrune-Cap-Martin, France.
8. **The reading for the summary.** With 12,368 to 155,130 matches per row, improvements from 0.05 (men) and 0.13 (women) milli-log-loss clear the family-wide line: 63 and 47 findings, of which 15 and 13 gain 1 or more. Should the summary read findings together with the plan's size scale (small under 1, clear from 1), as this write-up does?
9. **What the summary carries forward**, for example:
   * the ratings through the iid model and the 52-week matchups (the largest gains on Elo);
   * the load features and the women's ranking-type features (the only rows above the line given the market, all under 1);
   * the negative controls (luck corrects Elo).

   Earlier stages' open decisions remain open and were not changed here; Stage 4 used their tables as built.

## Limitations

* **Ranges treat matches as independent**, as in Stages 1–3, so they are somewhat too narrow. The shuffled copies are the more robust guard.
* **In-sample constants.** Elo's (Stage 1), the ratings' (Stage 3), the shrinkage constants and the slopes were set on years up to 2018. The 2019–2026 values are in `stage4_ranking.csv` and the report. There the four leaders gain 4.28, 1.34, 1.91 and 2.52 (men: the ratings through the iid model, the games-weighted Elo, sets over 14 days, the points matchup over 52 weeks) and 4.58, 2.02, 2.21 and 1.59 (women).
* **The copies for the market score** are shuffled among all the season's matches where the feature exists, Challengers included, as the plan specifies, then scored on the matches with odds.
* **Days between events, not matches.** The fatigue windows count between tournament start dates (the plan's decision 8, as planned).
* **The lag check** cannot separate a leak from recency for features about the most recent matches; the probe does that.
* **Unpenalised fits.** Where a feature is sparse in early seasons, the second minimum leaves those seasons out rather than shrink the coefficient.
* **The country table is hand-made,** from the event names. A French player at Monte Carlo, or at Nouméa, Le Gosier or Réunion (coded France), counts as home, as the codes say.
