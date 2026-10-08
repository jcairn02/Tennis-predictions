# Audit B: Stage 4

**Status: an audit of Stage 4, run 2 Oct 2026. A review, not a decision.** Nothing in the study was changed: no Stage 4 code, table, evidence file or write-up. The audit's scripts are `src/eda/predictability_diagnostic/audit4_*.py`, and their evidence is in `data/studies/predictability_diagnostic/audit4/`. Every number below comes from those files, or from Stage 4's own outputs where they are named. The test count is pytest's own.

Labels, as in the study: **observed** is measured, **inferred** is a reading of measurements or of outside knowledge, **suggestion** is a proposal for the owner. Each finding is classed as a **confirmed problem**, a **possible problem** or **fine**.

## Findings

| # | Finding | Class | Check | Size |
|---|---|---|---|---|
| C1 | In 4 evaluation matches, the format "match tiebreak" is read from the match's own score: women's 2021 quarter-finals at the Gippsland Trophy and the Yarra Valley Classic that went to a match tiebreak, while their straight-set round-mates count as standard sets. The iid model then plays them under a different format. Stage 4's probe does not redraw the format, and its rebuild "from the record" keeps this flag. So stage4.md's "the one dependency on the match's own outcome" (best of five) is not the only one. | Confirmed | 3 | 4 matches; the rows that use the format move by 0.001 milli-log-loss or less |
| C2 | Three men's rankings come from the list published the Monday after their event: three first-round losers at the 2026 Barletta Challenger (Tennis My Life rows). | Confirmed | 3 | 3 player rows; their points equal the list in force, only the rank moved (1–2 places) |
| C3 | The Stage 0 audit's P5 (rows moved into another edition of their event) is confirmed by the rankings. Three Rome Challenger 2022 rows carry the ranks of lists published 210 and 224 days after their recorded date; one Santiago 2 Challenger 2021 row, those of a list 210 days before. A match recorded too early puts its result into other players' histories before it was played. One recorded too late reads, for its own features, results played after it. | Confirmed (inherited from Stage 0) | 3 | 4 player rows |
| C4 | Stage 4's lag table shows one correlation per feature, computed over both tours and all seasons from 2010, printed against each tour. | Confirmed | 2 | Cosmetic: for example 0.457 for both tours' sets over 14 days |
| P1 | Stage 4 reads the load features' small gains over the market as vanishing one match later. That comes from its lag moving the 7- or 14-day window back to the previous match. Kept on the match's own dates, with only the latest match removed, the men's 7-day load gains over the market grow. | Possible (reading) | 2 | Men's sets over 7 days 0.30 → 0.38 better than the market (Stage 4's lag: → 0.03) |
| P2 | The second training minimum, added after Stage 4's first run, decides the scored seasons of two women's findings, one of them fifth given Elo. Disclosed as Stage 4's decision 2. | Possible (disclosed) | 7 | Women's minutes over 14 days and over 7 days: seasons 2013–2016 left out |
| P3 | The plan's hash shows that candidates.md has not changed since the features were built. Nothing records which text the owner approved. | Possible | 7 | The study's folders are untracked in git; the scorer checks the plan's hash, not the candidate table's |
| F | Everything else | Fine | 1–8 | See below |

The fine results, in one line each:

* **No leak in the strongest features (check 1).** 3,528 of 3,528 recomputed values agree, and the audit's own engine reproduces 23 feature columns on all 255,123 matches of Stage 4's table.
* **One more match of lag collapses nothing (check 2).** The games-weighted Elo loses most of its gain, which check 1 shows is recency, not a leak.
* **A and B are oriented and scored correctly (check 4).** Every one of the 956 scores is reproduced exactly, each baseline on its row's own matches.
* **The null band and the family-wide line are computed as the plan says (check 5).**
* **No claim rests on a group under 300 matches (check 6),** apart from the Tour Finals, which Stage 4 already labels directional.
* **The hashes match (check 7).**
* **Pinnacle (check 8).** With Pinnacle's close, no row gains 1 milli-log-loss. Four small gains stay above Pinnacle's own family-wide line.

The study's 218 tests pass unchanged (run without writing any cache).

## Terms used below

* **Gain:** how much a row's model beats its baseline, in milli-log-loss (thousandths of log loss; positive is better). Given Elo, the baseline is surface Elo alone, refitted on the same matches; given the market, the closing odds alone. This is the study's "improvement". Elo is a rating that rises when a player wins and falls when they lose.
* **The closing odds** are the bookmakers' average price (tennis-data.co.uk's AvgW/AvgL), turned into probabilities that sum to one. The provider says its odds "generally represent the most recent before play starts" (a provider claim, as Stage 1 records). **Pinnacle's close** is one bookmaker's price from the same files (PSW/PSL), turned into probabilities the same way by Stage 1. Pinnacle's prices end in January 2026.
* **Stage 4's table:** `stage4_features.parquet`, 255,123 matches (182,440 men's, 72,683 women's) at the evaluation levels, 2010–2026. 155,130 men's and 60,321 women's of them are evaluation matches, the ones scored.
* **Row:** a candidate in one form, for one tour.
* **Null band and family-wide line:** as in stage4.md. Twenty copies of each feature are shuffled within each season. The band is the range of their gains. The line is the largest standardised gain any copy of any row reaches, per tour and score.
* **One match later:** a feature rebuilt as if the player's most recent earlier match had not happened. A feature that leaked the match's own result would lose almost all of its gain; a real one loses some.
* **Tennis terms.** *Qualifying* is the small tournament before the main draw, usually played in the days before the main draw's Monday. A *round robin* is a group stage. Its matches count as simultaneous under the study's rule, so none may see another. A *match tiebreak* is a single tiebreak to 10 points played instead of a deciding set. A *Challenger* is the men's second tier. *Tennis My Life* is the study's second match source after Sackmann's files.

## How the audit was run

* **Independence.** The audit's code does not import Stage 4's (`stage4_features.py`, `stage4_rundown.py`). It reads Stage 0's tables, the constants the plan names (Stage 3's averages and shrinkage constants, Stage 4's for the new statistics, Stage 1's Elo constants) and Stage 4's outputs.
  * Two constants were recomputed: the games-weighted Elo's scale (0.650022 men, 0.673419 women) and Stage 3's surface log-odds. Both equal the stored values (`recompute.json`, `constants`).
  * The time rule is applied in ways different from Stage 4's group sums (`common.asof_sums`). Check 1 filters each player's matches one by one. Check 2's engine finds the same matches by binary search in the table's global order, in which every match of an earlier date, and every match of the same date with an earlier round, comes first.
  * The rating passes (Stage 1's Elo with weighted updates; Stage 3's serve and return ratings) are rewritten week by week, event by event, round by round.
  * The iid model (the chance of winning a match from the two players' serve-point rates) is an exact recursion over the score. Stage 2's vectorised version is used only for the full-table rebuild, after it was checked equal to the audit's recursion: largest difference 2.2e-15 over 300 pairs of rates and 16 formats (`lag.json`, `iid_check`).
  * The scorer (walk-forward logistic regression without an intercept, 20 shuffled copies with the plan's keys) is the audit's own.
* **Scripts and evidence** (in `audit4/`):

| Check | Script | Evidence |
|---|---|---|
| Shared helpers | `audit4_common.py` | |
| 1 Leaks, and the A/B part of 4 | `audit4_recompute.py` | `recompute.json`, `recompute_matches.csv` |
| 2 Lag | `audit4_lag.py` | `lag.json`, `lag.csv`, `lag_features.parquet` |
| 3 The match itself, later rounds, rankings | `audit4_inputs.py` | `inputs.json`, `rank_check.csv` |
| 4, 5, 8 Scores reproduced, the line, Pinnacle | `audit4_scoring.py` | `scoring.json`, `scoring_rows.csv` |
| 5 The copies' links, what sets the line | `audit4_band.py` | `band.json` |
| 6, 7 Small groups, the plan's hash | `audit4_claims.py` | `claims.json` |

* **Re-running.** From the repository root, `./python.sh src/eda/predictability_diagnostic/audit4_<name>.py`. Each script stands alone, in any order.
  * Times: recompute about 1½ minutes, lag 2½, scoring 13 (12 worker processes), inputs half a minute, claims and band seconds.
  * The audit's random draws use seed 20261002. The shuffled copies use the plan's keys (Stage 4's seed 20261001), so that they can be compared.

## 1. Leaks: the strongest features recomputed from earlier matches only

**Verdict: fine.** No recomputed value differs from Stage 4's.

**The rows.** The ten strongest per tour given Elo (`stage4_ranking.csv`). The first five are the check; the rest extend it. That is 13 features, 14 inputs with age squared.

* Men's five strongest: ratings through the iid model, games-weighted Elo, sets over the last 14 days, the points matchup over 52 weeks, the serve point from its parts over 52 weeks.
* Women's five strongest: ratings through the iid model, games-weighted Elo, sets over 14 days, the serve rating, minutes over 14 days.

**The matches** (seed 20261002): 100 random evaluation matches per tour, and, per tour, matches where the time rule is most delicate:

* 6 round-robin matches;
* 4 Tour Finals knockout matches played after a round robin;
* 8 matches of a player with two events in one week;
* 4 Grand Slam quarter-finals or later;
* 4 qualifiers' first main-draw matches, whose history includes the same event's qualifying rounds.

252 matches in all.

**How each value was rebuilt.**

* **Histories:** for each player, their rows were filtered one by one: an earlier tournament date, or the same tournament and date with a smaller round. Every sum was taken over that list in plain Python.
* **Ratings:** the games-weighted Elo and Stage 3's ratings were replayed from scratch for each match. Each replay saw only the tour's matches that the match may see: from 60,658 to 464,327 of them, median 247,692. The match's own result was blanked. The replay was never given anything later.
* **A and B:** every feature was built as side A's value minus side B's, from `player_a_id` and `player_b_id`.

**Observed** (`recompute.json`, `recompute_matches.csv`):

| Feature | Matches | Missing in both | Largest difference |
|---|---:|---:|---:|
| Ratings through the iid model | 252 | 0 | 2.1e-7 |
| Games-weighted Elo | 252 | 0 | 1.1e-7 |
| Sets over 14 days | 252 | 0 | 8.3e-8 |
| Points matchup, 52 weeks | 252 | 9 | 6.5e-8 |
| Serve point from its parts, 52 weeks | 252 | 9 | 8.4e-8 |
| Serve rating | 252 | 0 | 3.8e-8 |
| Minutes over 14 days | 252 | 75 | 2.1e-7 |
| One of the first matches on the surface | 252 | 0 | 0 |
| Age; age squared | 252 | 1 | 3.8e-7; 6.7e-6 |
| Points matchup, decayed | 252 | 6 | 7.5e-8 |
| Serve point from its parts, decayed | 252 | 6 | 9.8e-8 |
| Total points won, 52 weeks | 252 | 9 | 5.8e-9 |
| Games matchup, 52 weeks | 252 | 25 | 1.0e-7 |

* All 3,528 values agree, by every kind of match: the round robins, the knockout after them, two events in a week, late Grand Slam rounds, qualifiers' first main-draw match.
* Where Stage 4 has a feature missing, so does the audit.
* The differences are the rounding of Stage 4's stored values, which are kept to about 7 significant digits (float32).
* None of the 252 matches had its format read from its own score (check 3).

**At full scale.**

* The audit's rating passes, run once over every match, equal Stage 3's stored ratings on all 466,115 men's and 406,589 women's matches. The largest difference is 4.3e-8.
* They equal Stage 4's games-weighted Elo on all 255,123 matches of its table, to 2.4e-7.
* The audit's history engine (check 2) reproduces 23 of Stage 4's feature columns on all 255,123 matches. The same matches have each feature, and the largest difference is 9.5e-7 (`lag.json`, `engine_vs_stage4`). The columns: the 13 above plus the decayed games matchup and total points, sets and minutes over 7 days, days since the last match, matches played, the ranking and ranking points, and the level played over 52 weeks.

**Inferred.** Every feature checked uses only earlier events and earlier rounds of the same event, and is oriented A minus B. The only exception is the format, which reads the match's own score (check 3).

## 2. One more match of lag

**Verdict: no gain collapses (fine).** Two problems in how Stage 4 reported its own lag check: C4 and P1.

**How it was built.** Every feature was rebuilt for all matches by the audit's engine, as if the player's most recent visible match had not happened.

* For a statistic, that is the latest match carrying it.
* For load, rest and activity, it is the latest match played.
* For a rating, it is the value before the latest match that moved it.
* Windows keep this match's dates, so "sets over 14 days" becomes the 14 days' sets less the latest match.
* For age and the ranking, it is the value at the latest match played, as Stage 4 did.

Each row was scored given Elo and given the market on the matches where both versions exist, with its own 20 shuffled copies.

The rule was fixed before the scores were seen:

* a gain **collapses** if one match later it no longer clears its own null band;
* it is **largely lost** if it keeps under half.

**Observed** (`lag.csv`; gains given Elo, milli-log-loss better than Elo alone):

| Men | As built | One match later | Kept | Lagged band's top | Stage 4's lag |
|---|---:|---:|---:|---:|---:|
| Ratings through the iid model | 3.61 | 2.56 | 71% | 0.005 | 2.56 |
| Games-weighted Elo | 1.82 | 0.33 | 18% | 0.008 | 0.33 |
| Sets over 14 days | 1.63 | 1.27 | 78% | 0.003 | 0.97 |
| Points matchup, 52 weeks | 1.61 | 1.33 | 83% | −0.001 | 1.33 |
| Serve point from its parts, 52 weeks | 1.58 | 1.29 | 82% | −0.001 | 1.29 |
| Minutes over 14 days | 1.51 | 1.32 | 87% | −0.004 | 1.41 → 1.04 |
| First matches on the surface | 1.45 | 1.36 | 94% | 0.003 | 1.35 |
| Age | 1.54 | 1.48 | 96% | 0.014 | 1.48 |
| Points matchup, decayed | 1.43 | 1.17 | 82% | 0.009 | 1.17 |
| Serve point from its parts, decayed | 1.41 | 1.14 | 81% | 0.008 | 1.14 |

| Women | As built | One match later | Kept | Lagged band's top | Stage 4's lag |
|---|---:|---:|---:|---:|---:|
| Ratings through the iid model | 4.58 | 3.37 | 74% | 0.037 | 3.37 |
| Games-weighted Elo | 2.38 | 0.57 | 24% | 0.017 | 0.57 |
| Sets over 14 days | 1.87 | 1.37 | 73% | −0.004 | 1.86 → 0.76 |
| Serve rating | 1.87 | 1.45 | 77% | 0.026 | 1.45 |
| Minutes over 14 days | 1.59 | 1.53 | 96% | 0.029 | 1.33 → 1.22 |
| Points matchup, 52 weeks | 1.48 | 1.12 | 76% | 0.043 | 1.12 |
| Serve point from its parts, 52 weeks | 1.39 | 1.04 | 75% | 0.049 | 1.04 |
| Total points won, 52 weeks | 1.30 | 0.99 | 76% | 0.054 | 0.99 |
| Games matchup, 52 weeks | 1.32 | 0.98 | 75% | 0.042 | 0.98 |
| First matches on the surface | 1.30 | 1.41 | 109% | 0.027 | 1.42 |

Notes on the table:

* Where Stage 4 scored on other matches, its pair is shown "as built → one match later".
* Some "as built" values differ slightly from the ranking because they are on the matches where both versions exist. For example, the men's points matchup is 1.61 here on 144,777 matches, and 1.55 in the ranking on 149,120.

**Observed.**

* **No gain collapses.** The lowest lagged gain is the men's games-weighted Elo, 0.33 (95% range 0.17 to 0.49), against a band whose top is 0.008. Every lagged gain is at least 0.32 above its band's top.
* **Largely lost:** the games-weighted Elo only, keeping 18% (men) and 24% (women).
* **Every other row keeps 71% to 109%.**
* **Where the two lags are defined alike, the audit's values match Stage 4's to 0.01.** That covers the ratings, the statistics and matchups, the games-weighted Elo, age and the first matches on a surface.

**Inferred.**

* No check points to a leak.
* The games-weighted Elo's loss is recency. Check 1 shows it is built from earlier matches only. What it adds to Elo sits mostly in the latest result, its margin and the update it brings.

**C4 (confirmed, cosmetic).** In `stage4_rundown.compare`, the matches used for the correlation (line 453) are not limited to the tour, while the count of differing values (line 466) is. So the correlation column is pooled over both tours and every season 2010–2026. That column appears in `stage4_leak_checks.csv` and in the report's "One match later" table. Every feature therefore shows the same correlation for both tours: 0.987 for the ratings through the iid model, 0.457 for sets over 14 days, 0.267 for minutes over 14 days. stage4.md's "correlating at 0.02–0.46 with the original" quotes these pooled values.

**P1 (possible: a reading, not a leak).** Stage 4's lag moved the whole load window back to the previous match: "the load before the previous match", a different quantity, as stage4.md says. On that basis stage4.md reads the load features' gains over the market as vanishing (In short; section 7). Keeping the window on the match's own dates and removing only the latest match:

| Row, given the market | As built | One match later (audit) | 95% range | Lagged band's top | Stage 4's lag |
|---|---:|---:|---|---:|---:|
| Men's sets over 7 days | 0.30 | 0.38 | 0.16 to 0.60 | 0.12 | 0.03 |
| Men's minutes over 7 days | 0.18 | 0.33 | 0.13 to 0.53 | 0.05 | 0.04 |
| Men's sets over 14 days | 0.23 | 0.21 | 0.02 to 0.39 | 0.04 | 0.14 |
| Women's sets over 14 days | 0.29 | 0.22 | −0.15 to 0.59 | 0.01 | 0.09 |

* Given Elo, the four 14-day load rows keep 73% to 96% of their gains (tables above), where Stage 4's lag kept 41% to 92%.
* **Inferred.** The load features' small edge over the market is not carried by the latest match. If anything it lies in the earlier part of the window. Neither lag suggests a leak, but "vanish" is not a property of the features; it comes from how the lag was defined.
* The other rows Stage 4 rebuilt as a precaution come out close to its numbers, because their lag is defined alike or nearly so. Given the market, as built → one match later (Stage 4's lag in brackets): the women's ranking 0.32 → 0.31 (0.31), ranking points 0.21 → 0.16 (0.16), matches played 0.16 → 0.16 (0.16), level of the last 52 weeks 0.20 → 0.19 (0.20), days since the last match 0.19 → 0.03 (0.03). The gap between ranking and Elo was not rebuilt.

## 3. The match itself, later rounds, and rankings dated after the match

**Verdict: three confirmed problems, all small (C1, C2, C3); the rest fine.**

**What each feature reads from the match it predicts** (from reading `stage4_features.py`; observed counts from `inputs.json`):

| Read from the match itself | Used by | Depends on how the match went? |
|---|---|---|
| Best of five, read from the score (a player won three sets), or the source's record, or the Next Gen Finals | the four matchups through the iid model in five forms, the ratings through it, match length | Yes, where score and record disagree: 111 men's matches, all at Wimbledon's last qualifying round. Stage 4 found this and sized it: 0.015 milli-log-loss or less (its decision 3) |
| Match tiebreak, Stage 0's per-match `format` | the same rows | **Yes, in 4 matches (C1)** |
| An event's format (short sets; an event where most deciding sets are match tiebreaks) | the same rows | Read from the event's scores, but it is the format the event announced: fine |
| Surface, level, round, tournament and year (the deciding-set rule) | many | No |
| Age, height, hand, the player's country, the event's country | player features | No |
| Entry code | entry types | No. Whether a type is "recorded" in a level and season is decided from the whole season's records, which sets coverage, not values: fine |
| Ranking and ranking points | the ranking rows, the gap | See "Rankings" below |
| Stage 1's Elo, Stage 3's pre-match ratings | baselines, rating rows | No; built from earlier matches (check 1) |
| The closing odds | the market baseline | No: prices before play |

**C1 (confirmed).**

* Stage 0 flags a match "match tiebreak" when its own score has a bracketed deciding tiebreak, even in an event that plays standard sets (`stage0_build.py`, the `format` rule).
* 29 evaluation matches carry the flag. 25 are in events that play match tiebreaks: the Grampians Trophy 2021, flagged as a whole. 4 are not (`inputs.json`, `format`):

| Event | Round | Score |
|---|---|---|
| Yarra Valley Classic 2021 | QF | 4-6 6-3 [10-4] |
| Yarra Valley Classic 2021 | QF | 6-2 4-6 [10-6] |
| Yarra Valley Classic 2021 | QF | 7-5 2-6 [10-4] |
| Gippsland Trophy 2021 | QF | 6-3 5-7 [10-6] |

* The same rounds' straight-set matches count as standard sets. The iid model plays the deciding set of the four as a 10-point tiebreak, a format that favours the stronger player less. The flag is set because the match reached a deciding set, that is, because of how it went.
* Stage 4's probe redraws results, scores, box scores, minutes and statuses, but not `format`. Its rebuild "from the record" replaces best of five but keeps this flag. Neither can see it.
* **Size, observed.** The audit rebuilt the women's rows that use the format with the four read as standard, as their round-mates are, and rescored them. The as-flagged values were first reproduced to 1.2e-7. Gains given Elo move by between −0.0001 and +0.0010 milli-log-loss (the ratings through the iid model: 4.5787 → 4.5797). Given the market they move by 0.0003 or less.

**Later rounds of the same event.** Nothing found.

* Check 1's late Grand Slam rounds, round robins and Finals knockouts agree with an implementation that cannot see them.
* The engine of check 2 agrees on every match.
* Big-point play reads only Grand Slams of earlier dates. The same Slam's earlier rounds are left out, which is stricter than the rule.

**Rankings** (`inputs.json`, `rank_check.csv`). Every evaluation player row with a rank, 424,280 of them, was compared with Sackmann's weekly ranking lists on disk (to 8 June 2026). A rank counts as matching a list when both the rank and the points agree.

| How the rank matches the lists | Men | Women |
|---|---:|---:|
| The list in force on the tournament date (the latest dated on or before it) | 292,002 | 116,359 |
| The list before that one | 374 | 13 |
| Only a later list | 5,318 | 1,355 |
| None of the nearby lists (the one before to eight weeks after) | 97 | 112 |
| Dated after the last list on disk (Tennis My Life rows of 2026) | 6,961 | 1,689 |

* **Later lists, observed.** 6,670 of the 6,673 "later" rows match the list one day after the tournament date. These are events the sources date on a Sunday, which take the next Monday's list. That list is the one in force when the main draw starts, and it holds none of the event's results.
* **C2 (confirmed).** The other 3 match the list a week later. They are three first-round losers at the 2026 Barletta Challenger (Tennis My Life rows, dated 30 March), carrying the ranks of 6 April, the Monday after the event. Their points are those of the list in force (213, 187, 177). Only the rank moved, by 1 or 2 places, because other players' points changed that week.
* **C3 (confirmed, inherited from Stage 0).** Of the rows matching no nearby list:
  * 3 Rome Challenger 2022 rows match lists 210 and 224 days after their recorded date. They were played about seven months later than recorded, so their results enter the two players' histories early.
  * 1 Santiago 2 Challenger 2021 row matches a list 210 days before its date. It was played earlier than recorded, so its own features read later results.
  * These are the four rows of the Stage 0 audit's P5, "moved 204–230 days into another edition of their event"; that audit traced the three Rome rows to Tennis My Life's 2023 Challenger file. The rankings now show which way each moved. The Stage 0 audit classed P5 as possible.
* **Other unmatched rows.** 3 men's rows match only much older lists (497 and 1,792 days before): stale or misattributed, not dated after the match. The rest, including all 112 women's (Tennis My Life, 2026), match no list on disk.
* **Qualifying, observed.**
  * 66,553 of 66,782 qualifying evaluation matches carry the main draw's date, although qualifying is played before it (a Grand Slam's in the week before).
  * Their ranks follow that Monday's list. Where it differs from the week before, 108,542 of 108,807 qualifying player rows follow the main draw's list.
  * So a qualifying rank is from a list dated after the match. Does that list hold the match's result? If it did, winners would gain more points than losers from the week before to that list. They do not:

| Mean points gained from the list before to the list in force | Won | Lost |
|---|---:|---:|
| Men, Grand Slam qualifying | −1.85 | −1.79 |
| Women, Grand Slam qualifying | −2.37 | −1.75 |
| Men, tour qualifying | −1.36 | −1.50 |
| Women, tour qualifying | −0.07 | −1.15 |
| Men, Challenger qualifying | 0.55 | 0.05 |

  * In main draws, where the list is dated before the match, winners did gain more: men's 1000s 10.69 against 4.56, women's Grand Slams 8.80 against 4.70. **Inferred:** that is form carried in from the week before, which a pre-match list may hold.
  * **Inferred:** the qualifying ranks hold no result of the match itself. A rank number can still move with other players' results of the qualifying week. Fine.

**Constants fitted on evaluation years (fine, with one inaccuracy in the plan).** These constants were all set on years up to 2018, which are also scored years:

* the shrinkage constants for match wins and deciding sets (2010–2018);
* the opponent adjustment's slopes (2013–2018);
* the games-weighted Elo's scale (2010–2018);
* Elo's and the ratings' constants.

The plan discloses this ("2013–2018 are in-sample for the frozen constants") and Stage 4 gives 2019–2026 beside every score. One sentence of the plan, "No result of a match being scored enters it", about the slopes, is not accurate for the five results-based statistics: matches, sets, games, tiebreaks and deciding sets won. Their slopes are fitted on those very results. **Inferred:** each slope is one number fitted on tens of thousands of matches, so one match's own result moves its own feature negligibly.

## 4. A and B, and whether baselines and features were scored on the same matches

**Verdict: fine.**

**A and B** (`scoring.json`, `orientation`; `recompute.json`).

* Every feature recomputed in checks 1 and 2 was built from the explicit identities of side A and side B, and agrees with Stage 4's.
* Stage 4's `a_won` equals Stage 0's for every match.
* Its Elo probability equals Stage 1's `p_elo_surf_ret` exactly (largest difference 0).
* Its market probability equals the odds file's `p_avg_a` exactly, with none missing where the file has one.
* Side A won 50.02% of the men's and 49.94% of the women's evaluation matches.
* Against who won, the baselines score as they should, and badly if A and B were exchanged:

| Log loss | Men | If A and B were exchanged | Women | If exchanged |
|---|---:|---:|---:|---:|
| Surface Elo (all evaluation matches) | 0.6046 | 1.0482 | 0.6003 | 1.0176 |
| Closing odds (matches with odds) | 0.5791 | 1.0569 | 0.5920 | 1.0047 |

* For the 18 features whose direction is fixed by how they are built, the alone fit for 2026 gives all 36 coefficients (two tours) positive: rankings, ratings, Elo variants, and the career forms of serve, return and points won and of the matchups.

**The same matches within a row.**

* The audit's scorer fits and scores the baseline and the model on the same matches by construction.
* It reproduces every score Stage 4 reports: 318 alone, 319 given Elo, 319 given the market, 956 in all.
* Largest differences: 4.1e-14 milli-log-loss in the gains, 3.5e-14 in the bands, 1.4e-10 in the standardised scores. The matches scored are identical in number for every row.

**Across rows, where stage4.md compares them.**

* **Which form did best.** The five forms of a statistic exist on different matches. Rescored on the matches where all five exist (given Elo, without copies), the 52-week form is best for 15 of 25 men's statistics and 17 of 26 women's; Stage 4 found 16 and 18 on each form's own matches. The surface form is best for 8 and 6 (Stage 4: 8 and 5), the opponent-adjusted for 1 and 1 (Stage 4: 1 and 2). The reading "recent form beats opponent adjustment" stands (`scoring.json`, `forms_on_common_matches`).
* **"For scale."** stage4.md sets the leaders' gains over all evaluation matches (3.61 men, 4.58 women) beside the market's lead over Elo on the matches with odds of 2022–2026 (22.5 and 18.8). Below, both on the same matches: each row's 2022–2026 evaluation matches with odds. Both models are walked forward as built.

| Row, 2022–2026 matches with odds | Matches | The market's lead over refitted Elo | The row's gain given Elo |
|---|---:|---:|---:|
| Men: ratings through the iid model | 12,352 | 21.8 | 5.93 |
| Men: points matchup, 52 weeks | 12,336 | 21.8 | 3.19 |
| Men: sets over 14 days | 12,352 | 21.8 | 1.28 |
| Men: games-weighted Elo | 12,352 | 21.8 | 0.64 |
| Women: ratings through the iid model | 11,467 | 19.3 | 4.94 |
| Women: points matchup, 52 weeks | 11,370 | 17.7 | 1.72 |
| Women: sets over 14 days | 11,432 | 19.5 | 1.71 |
| Women: games-weighted Elo | 11,467 | 19.3 | 2.10 |

* **Inferred.** On the matches where the market is, the leading row closes about a quarter of Elo's deficit to it (5.9 of 21.8; 4.9 of 19.3). That is more than the all-match figure beside the gap suggests. It still adds nothing on top of the market (section 8).

## 5. The shuffled null band

**Verdict: fine. It is computed as the plan says, with two notes.**

**Observed.**

* **The copies.** The plan says to shuffle each feature within each season and tour, among the matches where it exists, with 20 keys per match shared by every row. Written afresh from that description, the audit's copies reproduce every band Stage 4 reports. That covers the copies' minimum, maximum, mean and spread for all three scores of every row, to 4e-14 (`scoring.json`, `reproduction`).
* **The family-wide line.** It was rebuilt as the plan defines it: each copy's gain put on a common scale against the other 19 copies of its row, its largest value over all rows, the largest of the 20. Rebuilt from Stage 4's own copies (`stage4_null_copies.csv`) and again from the audit's, it equals the stored line to 2e-12. Every row's place against it agrees:

| Line (standard deviations) | Men | Rows above | Women | Rows above |
|---|---:|---:|---:|---:|
| Alone | 6.36 | 152 | 7.50 | 140 |
| Given Elo | 9.88 | 73 | 8.11 | 58 |
| Given the market | 7.79 | 3 | 6.97 | 8 |

**Note 1: the copies keep the rows' links only for rows that exist on the same matches** (`band.json`, `links`). The plan expects every copy to "shuffle every feature the same way". But a copy's shuffle is drawn over the matches where its row exists, so two rows share it only when they exist on identical matches. Over the five forms of each statistic (102 pairs each):

| Pairs of forms | Correlation of their copies' gains (median) | Correlation of the features themselves (median) |
|---|---:|---:|
| On the same matches (career with decayed, with adjusted) | 0.905 | 0.934 |
| On different matches (career with 52 weeks, with surface) | −0.015 | 0.822 |

**Inferred.** For rows on different matches, the copies behave as independent where the real features are related. More independent copies reach higher maxima, so the line sits higher than the plan intends, and fewer rows clear it. The guard is conservative, not lax.

**Note 2: each line is set by a single copy of an ordinary row** (`band.json`, `line_drivers`). The men's line given Elo, 9.88, is one copy of games won (adjusted); the next copy's maximum is 8.07, and the median of the 20 maxima is 2.94.

* The readings of a few rows hinge on that one copy. They lie between the second-largest copy maximum and the line, so they miss the line only because of its single largest copy: 2 men's and 9 women's rows given Elo, 2 and 1 given the market.
* The line also moves when the matches change. Given the market, on the matches that also have Pinnacle's close (86% of them), it is 4.77 for the men against 7.79.
* **Inferred.** This is what the plan's rule gives with 20 copies, and the rule was fixed in advance. Its 1-in-21 guarantee for the whole family holds, but the line's exact height is lumpy.

## 6. Claims that rest on groups under about 300 matches

**Verdict: fine.**

**Observed** (`claims.json`).

* **Which groups are small.** Under 300 matches, by score:
  * alone and given Elo: 170 groups each, 166 of them the Tour Finals and 4 Challenger / 125 qualifying;
  * given the market: 313, of which 312 are the Tour Finals and 1 a single season.
* **No era is small.** No era group of any row is under 300.
* **Every small group is flagged.** All are flagged "directional" in `stage4_results.csv`, and the report draws them as hollow dots.
* **The plan's three eras.** No finding needs an era under 300 to reach its three positive eras.
* **The claims stage4.md makes about groups:**
  * the ratings through the iid model, the points matchup, the serve point from its parts and age by era;
  * the ratings at the Grand Slams;
  * the ranking season by season;
  * the 2022–2026 and 2019–2026 values in the market table and the limitations.

  All rest on groups of 1,930 matches or more. The exception is the Tour Finals: at most 315 for the men (8 rows under 300) and 285 for the women (all 158 rows). Stage 4 labels these directional and draws no conclusion from them.

## 7. The plan's fingerprint, and nothing outside the plan reported as a result

**Verdict: the hashes match (fine). Two possible problems: P2, P3.**

**Observed** (`claims.json`, `hashes`).

* **The hashes.** The SHA-256 of `candidates.md` is `504c729a…7290b0a` and that of `stage4_candidates.csv` is `14cbbd04…31a45d6d`. Recomputed today, they equal the values recorded in `stage4_features_summary.json` and `stage4_results.json` and quoted in stage4.md.
* **The order of events, UTC.** The plan was last modified on 1 Oct at 23:47 and the table at 22:56. The features were written at 02:15 on 2 Oct (summary 02:19), the rundown at 02:31.
* **The scorer's guard.** `stage4_rundown.py` refuses to run if the plan's hash has changed, but it does not check the table's.

**P3 (possible).**

* The study's folders are untracked in git: a read-only `git status` lists them as new. Nothing else records the approved text.
* The hash proves that the plan did not change after 02:19 UTC on 2 Oct. It does not prove that this is the text the owner approved on 1 Oct.
* The plan's status line still reads "awaits the owner's approval". Editing it would have changed the hash, so the line was left as it was.

**Results outside the plan.** Each is disclosed in stage4.md:

* **The second training minimum**: 300 training matches on which the feature is not zero ("What Stage 4 set", after the first run).
* **Per-season results**: a finer grouping of the plan's walk-forward (the same list).
* **The reading "not scored"** (the same list).
* **The surface intercept in the opponent adjustment's slopes** ("What Stage 4 set", before scoring).
* **Two extra leak checks**: the format rebuilt from the record, and one match later (section 7). These are checks, not results.
* **The readings of section 6**: "2022–2026 is the fairer reading". Labelled inferred, and put to the owner as decision 1.

Two modelling choices appear only in the code. Inside the iid model, the Next Gen Finals' short sets are played as standard sets (121 men's matches). A match tiebreak is played as a 10-point tiebreak (29 women's matches). Both are small and reasonable, but stage4.md does not list them.

**P2 (possible, disclosed).** The second minimum was added after the first run "showed unpenalised fits separating": a rare input that always went with one result made its coefficient run off. The audit lists what it alone leaves out, that is seasons with 300 or more training matches but fewer than 300 non-zero ones:

| Row | Reading | Seasons left out (given Elo) | Matches |
|---|---|---|---:|
| Women's minutes over 14 days | finding, fifth given Elo | 2013–2016 | 3,635 |
| Women's minutes over 7 days | finding | 2013–2016 | 5,754 |
| Women's lucky loser | no sign | 2014–2017 | 9,538 |
| Women's protected ranking | not scored | 2015, 2021–2025 | 12,610 |
| Men's protected ranking | possible | 2016, 2017 | 22,108 |
| Men's lucky loser | no sign | 2014 | 7,158 |

The plan's literal rule would have scored those seasons with fits on a handful of non-zero values. **Inferred:** the guard is sensible, but a rule set after seeing results decides the scored seasons of a top-five women's row. Stage 4 discloses it and asks for decision 2.

## 8. Pinnacle's close in place of the market average

**Verdict: the gains over the closing odds are as small with Pinnacle's close as with the average. None reaches 1 milli-log-loss. Four stay above Pinnacle's own family-wide line.**

**How.** Every row with a market score was scored three ways, each with its 20 copies and its own family-wide line (`scoring_rows.csv`):

1. the average close, as built: Stage 4's score, reproduced exactly;
2. the average close on the matches that also have Pinnacle's;
3. Pinnacle's close on those matches.

For a row that exists on every match, Pinnacle's close covers 27,159 men's and 27,896 women's scored matches, against 31,683 and 32,178 for the average, because its prices end in January 2026.

**Observed.**

| Rows above their band (and above the line) | Men | Women |
|---|---:|---:|
| Average close, as built | 49 (3) | 15 (8) |
| Average close, on Pinnacle's matches | 46 (2) | 18 (3) |
| Pinnacle's close | 34 (2) | 17 (2) |
| The line, for the three rows above in turn | 7.79; 4.77; 4.83 | 6.97; 5.62; 5.62 |

The largest gain over Pinnacle's close is 0.25 (men) and 0.30 (women).

The rows above the line given the average, under each:

| Row | Average, as built | Average, Pinnacle's matches | Pinnacle | Pinnacle's 95% range | Above Pinnacle's band | Above Pinnacle's line |
|---|---:|---:|---:|---|---|---|
| Men's sets over 7 days | 0.30 | 0.27 | 0.25 | −0.01 to 0.51 | yes | yes |
| Men's sets over 14 days | 0.23 | 0.19 | 0.19 | −0.11 to 0.49 | yes | yes |
| Men's minutes over 7 days | 0.18 | 0.18 | 0.16 | −0.03 to 0.36 | yes | no |
| Women's ranking | 0.32 | 0.32 | 0.30 | 0.02 to 0.57 | yes | yes |
| Women's gap between ranking and Elo | 0.27 | 0.24 | 0.23 | −0.09 to 0.56 | yes | yes |
| Women's sets over 14 days | 0.29 | 0.18 | 0.16 | −0.19 to 0.51 | yes | no |
| Women's level of the last 52 weeks | 0.21 | 0.17 | 0.13 | −0.07 to 0.33 | yes | no |
| Women's ranking points | 0.20 | 0.17 | 0.15 | −0.08 to 0.39 | yes | no |
| Women's first matches on the surface | 0.20 | 0.12 | 0.12 | −0.16 to 0.39 | yes | no |
| Women's days since the last match | 0.19 | 0.12 | 0.09 | −0.21 to 0.39 | yes | no |
| Women's matches played | 0.16 | 0.20 | 0.19 | −0.13 to 0.50 | yes | no |

**Inferred.**

* The same few public facts that edge past the average edge past Pinnacle, by about as much: the recent load and the women's ranking-type features.
* Where a gain drops a lot, most of the drop comes from losing the matches without Pinnacle's prices, not from the bookmaker. The women's sets over 14 days fall from 0.29 to 0.18 on Pinnacle's matches with the average, and only to 0.16 with Pinnacle; the first matches on the surface and days since the last match behave alike. On the same matches, Pinnacle's close takes 0.00 to 0.04 more off than the average does, for every row in the table.
* Only the women's ranking keeps a 95% range above zero against Pinnacle. Those ranges treat matches as independent and are somewhat too narrow.
* As stage4.md says, a gain in log loss of this size is not a betting edge, and this audit does not measure one.

## Suggestions for the owner (not applied)

1. **C1.** Read the match tiebreak per event and round, not per match, as the event's format is read. With the format taken from the record (Stage 4's decision 3), no feature would read its own match's score.
2. **C2, C3.**
   * For Tennis My Life rows, take the rank and points from the list in force on the tournament's date where the lists cover it (to 8 June 2026).
   * Settle the four P5 rows' dates in Stage 0.
3. **C4.** Compute the lag table's correlation per tour (the tour filter of line 466 applied at line 453 of `stage4_rundown.py`).
4. **P1.** If the load features go forward (decision 9), describe their lag check as "the latest match removed, the same window", or report both lags. "Vanish" describes Stage 4's lag, not the features.
5. **P2.** When deciding on the minimum training rule (decision 2), note that it decides the scored seasons of the women's minutes over 14 and 7 days, both findings.
6. **P3.** When approving a plan, record its SHA-256 in the README's decision entry. Have the scorer check the candidate table's hash as well as the plan's.
7. **The line.** Where findings are counted, consider naming the rows that miss the line only because of its single largest copy (2 men's and 9 women's given Elo).

## Limits of this audit

* **The full-table rebuild uses Stage 2's iid model.** It was checked equal to the audit's recursion on 300 random pairs of rates in 16 formats. The 252 sampled matches use the audit's recursion itself.
* **Constants are taken as stored**, as the plan names them. Two were recomputed and agree.
* **Rankings were checked against Sackmann's lists, which end on 8 June 2026.** 8,650 Tennis My Life rows of 2026 lie beyond them. 112 women's Tennis My Life rows match no list on disk, so their dates could not be checked.
* **The qualifying points test is indirect**: it rules out the match's own result in the list, on average, not row by row.
* **The lag check uses one definition of "one match later".** A leak would collapse under any definition, but how much a real feature loses depends on the definition (P1).
* **Pinnacle's scores cover fewer matches**: 14% fewer men's and 13% fewer women's than the average's.
* **Ranges treat matches as independent**, as Stage 4's do, so they are somewhat too narrow.
