# Stage 4 plan: the candidate list

**Status: written 1 Oct 2026; awaits the owner's approval.** The owner edits and approves this list before Stage 4 computes anything. Nothing here was compared with who won: the only numbers computed for this plan are coverage counts (on how many matches each feature would exist) and the number of comparisons the plan makes. A study plan, not a decision. The Brief and the stage table are in the [README](README.md).

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Coverage and counts come from `data/studies/predictability_diagnostic/stage4_candidates_summary.json` and `stage4_candidates_coverage.csv`, written by `src/eda/predictability_diagnostic/stage4_candidates.py`. The list itself is the hand-made table `stage4_candidates.csv`. Numbers from earlier stages are quoted from their write-ups, which name their files.

## In short

* **59 candidates.** 22 per-match statistics and 4 "serve against return" matchups, each in five forms, and 33 features that have one form. That makes 163 rows (a candidate in one form) for the men and 162 for the women; match length applies to the men only.
* **Nothing from the starting list was removed.**
  * Entry type became four candidates, because each type is recorded in different seasons.
  * "Left-handed against right-handed" gets a second reading.
  * The tiebreak record is the Stage 0 tiebreak rate.
  * Added from Stages 1–3: return points won against the first serve and against the second serve, break points won above expectation, the serve point built from its parts, match length, the level played over the last 52 weeks, and big-point play on return from the Grand Slam point-by-point files.
* **The five forms:** career to date, shrunk with Stage 3's constants; the last 52 weeks; exponentially decayed with a **52-week half-life** (the owner's decision, 1 Oct 2026); this surface only; opponent-adjusted with Stage 3's ratings.
  * Features enter as A − B differences.
  * The matchups set A's serve against B's return and pass both through Stage 2's iid model to a match probability.
* **Coverage (observed):** the share of evaluation matches on which a feature exists for both players. The men's figures cover 2013–2026; the women's box-score figures cover 2019–2026.
  * Box-score histories: 97.3–97.6% (men) and 98.0–98.1% (women).
  * Head to head: 38.6% and 46.5%.
  * Height: 87.4% and 65.0%; for the women only 37.2% in 2022–2026.
  * Minutes of the previous match: 81.1% and 62.0%. The women's matches have almost no minutes before 2016.
  * Big-point play on return: 32.1% and 60.3% of all evaluation matches, 86.0% and 82.3% of main-tour matches.
  * Protected rankings are coded for the men from 2015 outside the Grand Slams, and for the women in a few seasons only.
  * No file on disk gives every tournament's country. The plan names a hand-made table: 630 men's and 204 women's event names to map.
* **The scoring plan is fixed below:**
  * walk-forward by year from 2013;
  * three scores per row and tour;
  * a null band from 20 shuffled copies;
  * direction by era and level;
  * a ranking by the improvement given Elo.
* **974 comparisons.** If every candidate were useless, about 46 would still beat all 20 of their own shuffled copies by chance. A family-wide line built from the same copies, and a rule on eras, keep those from being read as findings.
* **For the owner:** nine open decisions, [at the end](#9-decisions-for-the-owner). The half-life was decided on 1 Oct 2026.

## Terms used here

**Tennis.**

* **Serve and return points.** Every point has a server and a returner. A player's serve points won are the points they win on their own serve; their return points won are the points they win on the opponent's serve.
* **Hold, break, break point.** A game won by the server is a hold; a game won by the returner is a break. A break point is a point that would give the returner the game; the server saves it by winning it.
* **First and second serve, ace, double fault.** A server has two attempts. A missed first serve is followed by a safer second; missing both is a double fault, and the point is lost. An ace is a serve the returner does not touch.
* **Tiebreak, deciding set.** At six games all, a race to 7 points (won by two) settles the set. The deciding set is the last possible set, played at one set all (best of three) or at two sets all (best of five).
* **Best of three or five.** The first to two sets, or to three. Among the evaluation matches, only the men's Grand Slam main draws, the men's last qualifying round at Wimbledon, and the Next Gen ATP Finals (five short sets) are best of five.
* **Main draw, qualifying, entry types.** The main draw is an event's main bracket. Qualifying is the small tournament before it; its winners (**qualifiers**) join the main draw. A **lucky loser** lost in qualifying but took the place of a player who withdrew. A **wild card** is a place given by the organisers, often to local or young players or to returning stars. A **protected ranking** (the WTA calls it a special ranking) lets a player back from a long injury enter on the ranking they had when they stopped.
* **Levels.** The Grand Slams; the Tour Finals; the 1000s, 500s and 250s (named for the ranking points the winner earns); below them the Challenger events (men) and WTA 125s (women); ITF events at the bottom, used here as history only. **Main tour** here means the Grand Slam to 250 main draws, the only matches with closing odds.
* **Retirement, walkover.** A player stops during a match, or does not start it; the opponent advances.

**This study.**

* **Candidate, row, form.** A candidate is a pre-match statistic or feature. A row is a candidate in one form. A form is a way of summarising a player's history (section 2).
* **Evaluation matches** (the Brief, built in Stage 0). Completed or retired singles at the Grand Slams, Finals, 1000s, 500s, 250s and Challenger / WTA 125 events and their qualifying, 2013–2026: 155,130 men's and 60,321 women's. 31,683 and 32,178 of them have closing odds.
* **History.** A player's earlier matches under the Brief's time rule: earlier events, and earlier rounds of the same event. Never the match itself, another match of the same round (a round-robin group), or another event of the same week.
* **Units** are what a rate's denominator counts: serve points, break points, tiebreaks. **Shrinkage:** a player's shrunk rate is (x + K × average) / (d + K), with x their count and d their units. K is Stage 3's constant: with d = K units, the player's own rate counts half.
* **Log-odds** of a share p: log(p / (1 − p)).
* **The iid model** (Stage 2). The exact chance of winning a match when every point is an independent draw at the two players' serve rates. It knows the format: best of three or five, and each Grand Slam's deciding-set rule.
* **Log loss, milli-log-loss** (Stage 1). A coin scores 0.693; one milli-log-loss is 0.001. Differences are stated as better or worse.
* **The three scores.** Alone, against a coin; the improvement when added to surface-blended Elo; the improvement when added to the closing odds.
* **Null band, family-wide line** (sections 5 and 6). What 20 shuffled copies of a feature score; the best score any shuffled copy reaches across all rows.

## 1. Rules every candidate follows

1. **Time.** Features use the history only. They are computed in one chronological pass through `common.asof_sums` and Stage 3's `lookback_sums` and `sums_before`, as Stages 1 and 3 computed theirs. Before scoring, each family of features passes two checks: hand-made-history tests, and a probe that cuts the history by date, event and round (as `stage1_baselines.probe_by_round` does). The order-based probe alone is not enough (the Stage 0 audit's P3).
2. **History.** Every singles level from 2010, ITF and team events included, as the Brief sets.
   * Box-score and score statistics use completed matches in the standard format. This is Stage 3's rule; retirements are left out, which is Stage 3's open decision 1.
   * Match wins, meetings and the activity features also count retirements, as Elo does (closed by the owner on 30 Sep 2026).
   * Walkovers enter only the candidate "last match ended early".
3. **Results-based history** (sets, games, tiebreaks, wins, deciding sets, head to head) comes from every level, as the Brief sets.
   * Stage 3 found that history from other levels misleads for results (its open decision 2).
   * The opponent-adjusted form discounts results against weak opponents, so it is the form expected to fix that.
   * If the owner chooses evaluation-level history for these statistics instead, they switch to it.
4. **Sides.** Side A is set by a hash of the match id (Stage 0), so A carries no information. Every feature enters as an A − B difference, or, for a matchup, as A's prospects against B's; no model has an intercept.
5. **Scales.**
   * Shares on the log-odds scale; break points faced per game on the log scale.
   * Counts of matches, days, minutes and sets as log(1 + x).
   * Ratings, Elo, age and height as they are; indicators as 0 or 1.
6. **Missing.** A feature exists for a player when its form has the inputs it needs. For a statistic, that is at least one earlier match carrying it inside the form's window. Nothing is imputed. A match is scored for a row only where the feature exists for both players (section 5). Two exceptions keep Stage 1's rules: an unranked player takes the rank below the tour's lowest and 0 points; Elo and the ratings exist for every match.
7. **WTA box scores.** History from every year; scored from 2019 (the Brief).
8. **Retirements as results.** Counted, the player who advanced having won (the Brief).

## 2. The five forms

For every per-match statistic (section 3.1) and every matchup (section 3.2):

| Form | What it measures | How |
|---|---|---|
| Career to date | Everything the player has done before | Stage 3's forecast form. Each earlier match is counted against its own surface's tour average; the sum is shrunk toward the tour's average on this match's surface with Stage 3's constant K (`stage3_shrinkage.csv`, all surfaces, 2010–2018) |
| Last 52 weeks | The last year | The same over matches of events starting up to 364 days before this one, plus this event's earlier rounds; the same K |
| Decayed | Recent seasons count more; older ones fade instead of dropping out | The same with each earlier match weighted ½ for every 52 weeks of age; the same K |
| Surface | This surface only | Earlier matches on this match's surface only, shrunk toward that surface's average with Stage 3's constant for the surface (the all-surface constant for carpet). Where Stage 3 found no spread between players on a surface (K infinite), every player gets the average |
| Opponent-adjusted | As if every earlier opponent had been typical | The career form, after each earlier match's rate is restated against a typical opponent with that opponent's pre-match Stage 3 rating (below) |

**The half-life: 52 weeks** (the owner's decision, 1 Oct 2026; the plan had proposed 13 weeks).
* Stage 3 found two groups of best half-lives: 13–26 weeks for the serve style and for games and sets won, and 104–208 weeks for serve and return skill and break points. 52 weeks is the geometric middle of the two.
* For a player who plays steadily, half of the decayed weight lies on the last 52 weeks, where the 52-week window puts half on the last 26. The decayed form is then a smoothed, longer-memory version of the window: older matches fade instead of dropping out.
* Stage 3's next-match forecasts for 2019–2026 (`stage3_forecast.csv`, milli-log-loss per unit better than the tour average), a 52-week half-life against the career form:
  * serve points won: 1.16 against 1.13 (men), 1.10 against 1.10 (women);
  * first serves in, where recency helps: 2.72 against 2.29 (men), 4.40 against 3.80 (women);
  * break points saved, where a long memory helps: 0.77 against 0.83 (men), 0.76 against 0.87 (women).

**Constants Stage 3 did not measure.** Match wins, deciding sets, return points against the first and against the second serve, break points above expectation, and big-point play get their constants in Stage 4, before anything is scored. They are estimated by Stage 3's method (`stage3_traits.eb_constants`) on player-seasons of 2010–2018; big-point play uses the Grand Slam point-by-point seasons 2011–2018. The head-to-head share uses the match-win constant.

**The opponent adjustment.** A rate earned against a strong opponent is raised, one earned against a weak opponent lowered. On the log-odds scale: adjusted = log-odds of (x + ½) / (d + 1), plus β × (the opponent's rating − a typical opponent's); it is then turned back into a share of the same d units. Break points faced per game, a count, shifts on the log scale instead.
* The opponent's rating is the one the statistic faces:
  * the return rating, for serve-side statistics: serve points won, aces, double faults, first serves in, first- and second-serve points won, holds, break points saved and faced;
  * the serve rating, for return-side statistics: return points won, breaks, break points converted, return points against the first and second serve;
  * serve plus return, for whole-match statistics: total points, games, sets, tiebreaks, matches, deciding sets, break points above expectation.
* β = 1 for serve and return points won. These are Stage 3's own adjusted rates (`stage3_traits.load_rows`), shrunk with Stage 3's adjusted constants (2013–2018).
* For the other statistics, β is the slope of each match's log-odds rate on the opponent's rating, fitted per tour on the evaluation-level match statistics of 2013–2018. No result of a match being scored enters it. The raw statistic's K is kept: Stage 3 found that halving or doubling K moves a forecast by a median 0.03 milli-log-loss per unit.
* The head-to-head record is adjusted differently, since its opponent is always the same player: meetings won above what the two players' Stage 3 ratings expected through the iid model.

**2013–2018 are in-sample for the frozen constants.** Elo's constants (Stage 1), the ratings' constants (Stage 3), K and β were all set on years up to 2018. Every score is therefore also given for 2019–2026, as Stage 1 did.

The 33 features of section 3.3 (rankings, ratings, age, rest, entry type and the rest) have no forms. Each has one definition, given in its entry.

### A's serve against B's return

**Inferred (from the arithmetic, not from data).** On the log-odds scale, "A's serve against B's return, minus B's serve against A's return" is just the serve difference plus the return difference. A model that holds both differences already has it. So a matchup goes through a model of the match that is not a sum, where one exists. For break points, where none does, it is the sum: one feature where the two differences are two.

| Matchup | A's expected rate when serving to B | How it becomes a match probability |
|---|---|---|
| Points | log-odds μ + (log-odds of A's serve points won − log-odds μ) − (log-odds of B's return points won − log-odds (1 − μ)), with μ the tour's serve-point average on the surface; B's likewise | Stage 2's iid model (`stage2_iid.match_win`) with the match's format and deciding-set rule (`stage2_iid.deciding_set_rule`). The feature is the log-odds of its probability |
| Games | The same with holds and breaks | Each expected hold rate turned into the serve-point rate that gives it (`stage2_iid.game` inverted), then the iid model |
| Break points | The same with break points saved and converted | None: the log-odds sum |
| The serve point from its parts | A's first serves in × A's first-serve points won against B's returns of first serves, plus the rest × A's second-serve points won against B's returns of second serves; each pair combined as above | The iid model |

Each matchup exists in every form: both of its statistics are taken in the same form.

## 3. The candidates

Every expectation uses one scale, set before anything is scored, so that surprises show:

* **Alone**, in milli-log-loss better than a coin on the matches where the feature exists: **none** (inside its null band), **weak** (above it, under 10), **moderate** (10 to 40), **strong** (40 or more). For scale (Stage 1, matches with odds, 2022–2026): the ranking alone is 50.1 better than a coin for the men and 53.1 for the women; surface Elo 81.7 and 83.8.
* **Given Elo** and **given the market**: **none** (inside its band), **small** (above it, under 1 milli-log-loss), **clear** (1 or more), **worse** (below its band). For scale: in 2022–2026 surface Elo trails the closing odds by 22.5 milli-log-loss for the men and 18.8 for the women (Stage 1's room). Stage 2 put the most any pre-match forecast could gain on the market at about 160 milli-log-loss, a ceiling no forecast reaches.
* **Sign**: the direction of the feature given Elo. **+**: the player with more of it wins more often than Elo says. **−**: less often. **?**: no prior.

### 3.1 Per-match statistics, five forms each

**Data:** Stage 0's per-player counts (`stage0_match_players.parquet`): the box scores (Sackmann's, as Stage 0 kept them) and the scores. **Coverage:** section 4.1.

| # | Statistic | Per match | Side | Units | K, units (men; women) | A season's reliability, Stage 3 (men; women) |
|---|---|---|---|---|---|---|
| 1 | Serve points won | points won on own serve / points served | serve | serve points | 466; 582 | 0.81; 0.78 (adjusted 0.91; 0.88) |
| 2 | Return points won | points won on the opponent's serve / the opponent's serve points | return | return points | 1,052; 1,170 | 0.76; 0.66 (adjusted 0.88; 0.81) |
| 3 | Total points won | all points won / all points played | whole match | points | 1,959; 2,117 | 0.55; 0.58 |
| 4 | Service games held | holds / service games | serve | service games | 72; 90 | 0.77; 0.76 |
| 5 | Return games won (breaks) | breaks / the opponent's service games | return | return games | 245; 245 | 0.73; 0.63 |
| 6 | Aces | aces / serve points | serve | serve points | 137; 156 | 0.96; 0.95 |
| 7 | Double faults | double faults / serve points | serve | serve points | 256; 170 | 0.90; 0.92 |
| 8 | First serves in | first serves in / serve points | serve | serve points | 225; 131 | 0.93; 0.95 |
| 9 | First-serve points won | won / first serves in | serve | first serves in | 221; 254 | 0.87; 0.86 |
| 10 | Second-serve points won | won / second-serve points | serve | second-serve points | 460; 439 | 0.59; 0.62 |
| 11 | Break points saved | saved / faced | serve | break points faced | 246; 370 | 0.37; 0.39 |
| 12 | Break points converted | converted / chances on the opponent's serve | return | break-point chances | 1,016; 791 | 0.34; 0.29 |
| 13 | Break points faced per service game | faced / service games (a count per game) | serve | service games | 119; 156 | 0.71; 0.64 |
| 14 | Tiebreaks won (the tiebreak record) | won / played, from the score | whole match | tiebreaks | 429; 569 | 0.06; 0.06 |
| 15 | Sets won | won / completed, from the score | whole match | sets | 60; 57 | 0.45; 0.47 |
| 16 | Games won | won / played, from the score | whole match | games | 341; 361 | 0.50; 0.55 |
| 17 | Matches won (the recent win rate) | won / played (completed or retired) | whole match | matches | set in Stage 4 | – |
| 18 | Deciding sets won (the deciding-set record) | matches won / matches that reached a deciding set (read from the score) | whole match | deciding sets | set in Stage 4 | – |
| 19 | Head-to-head record | earlier meetings won by A / earlier meetings | the pair | meetings | the match-win K | – |
| 20 | Return points won against the first serve | the opponent's first serves in that the player won / the opponent's first serves in | return | return points against first serves | set in Stage 4 | – |
| 21 | Return points won against the second serve | the opponent's second-serve points the player won / the opponent's second-serve points | return | return points against second serves | set in Stage 4 | – |
| 22 | Break points won above expectation | saves and conversions above what the match's own serve and return rates predict (Stage 2's measure) / break points played | whole match | break points | set in Stage 4 | – |

| # | Statistic | Why it might help | Alone | Given Elo | Given market | Sign | Form expected to do best |
|---|---|---|---|---|---|---|---|
| 1 | Serve points won | The core of serve skill. Elo knows who won, not how | moderate | small | none | + | adjusted |
| 2 | Return points won | Return skill, the other half of every point | moderate | small | none | + | adjusted |
| 3 | Total points won | The owner's thesis at its simplest: strength measured in points, not results. Stage 2: a man who wins 51.7% of the points in a best-of-three match wins about 90% of the time | moderate (adjusted: strong) | small | none | + | adjusted |
| 4 | Service games held | Serve strength where it decides games | moderate | small | none | + | adjusted |
| 5 | Return games won | Return strength where it decides games | moderate | small | none | + | adjusted |
| 6 | Aces | Serve style, the most repeatable statistic, but a small part of the points edge: 7% (men) and 5% (women) of its variation across matches (Stage 2) | weak | none | none | + | decayed, surface |
| 7 | Double faults | Style and nerves | weak | none | none | − | decayed |
| 8 | First serves in | How much risk the first serve takes; 3% and 2% of the points edge's variation (Stage 2) | none | none | none | ? | decayed |
| 9 | First-serve points won | Serve quality once in. Points that start with a first serve in play account for 55% and 60% of the points edge's variation (Stage 2) | moderate | small | none | + | adjusted |
| 10 | Second-serve points won | Rally skill behind the weaker serve; 37% and 32% of the edge's variation | moderate | small | none | + | adjusted |
| 11 | Break points saved | "Clutch" on serve. Stages 2 and 3: mostly chance | weak | none | none | + | career |
| 12 | Break points converted | Clutch on return | weak | none | none | + | career |
| 13 | Break points faced per service game | How often the serve comes under pressure | moderate | small | none | − | adjusted |
| 14 | Tiebreaks won | The list's tiebreak record. Stage 3: noise; no player's history reaches K (section 4.2). A negative control | weak | none | none | ? | career |
| 15 | Sets won | Results, with a little margin | moderate | none | none | + | adjusted |
| 16 | Games won | The margin Elo ignores (the idea behind the margin-aware Elo) | moderate | small | none | + | adjusted |
| 17 | Matches won | The list's recent win rate | moderate | none | none | + | decayed |
| 18 | Deciding sets won | The "clutch" reading of results | weak | none | none | ? | career |
| 19 | Head-to-head record | Some pairings suit one player beyond strength | moderate | none | none | + | adjusted (above the ratings' expectation) |
| 20 | Return points against the first serve | The return half of the largest part of the points edge (Stage 2) | moderate | small | none | + | adjusted |
| 21 | Return points against the second serve | The return half of the second largest | moderate | small | none | + | adjusted |
| 22 | Break points above expectation | The only box-score big-point measure that persists beyond luck, weakly and for the men only. Stage 2: 0.11 between halves of 50+ matches, against 0.00 in the pure-luck replays | none | none | none | + | career |

### 3.2 Serve against return, five forms each

**Data:** the statistics each matchup combines (section 2). **Coverage:** section 4.1.

| Matchup | Statistics | Why it might help | Alone | Given Elo | Given market | Sign | Form expected to do best |
|---|---|---|---|---|---|---|---|
| Points | serve and return points won | A points-level forecast that knows the format. Stage 1: Elo is over-confident at best of three and under-confident at best of five; the iid model accounts for match length by construction | strong | clear (men), small (women) | none | + | adjusted |
| Games | holds and breaks | The same at the level of games | strong | small | none | + | adjusted |
| Break points | break points saved and converted | Clutch both ways | weak | none | none | + | career |
| The serve point from its parts | first serves in, first- and second-serve points won, return points against first and second serves | Stage 2's exact split of the points edge, each part set against the opponent's matching return | strong | clear (men), small (women) | none | + | adjusted |

### 3.3 Features with one form

**Coverage:** section 4.3. The "Data" column names the Stage 0 column (`stage0_match_players` or `stage0_matches`) or the earlier stage's table.

**Rankings and ratings.**

| Feature | Before the match | Data | Why it might help | Alone | Given Elo | Given market | Sign |
|---|---|---|---|---|---|---|---|
| Ranking | log(B's rank) − log(A's rank), as of the tournament's start; an unranked player takes the rank below the tour's lowest (Stage 1) | `rank` (Sackmann) | The market's most visible number. Stage 1: 50.1 (men) and 53.1 (women) better than a coin, on the 2022–2026 matches with odds | strong | small | none | + |
| Ranking points | log(1 + A's points) − log(1 + B's points) | `rank_points` | Stage 1: 58.3 and 53.7 better than a coin | strong | small | none | + |
| Gap between ranking and Elo | Each player's surface-blended Elo rating (the baseline's) minus the rating their ranking implies, from a line of that rating on log(rank) fitted on earlier seasons; A − B | `stage1_baselines`, `rank` | A ranking lags a rating: players back from injury, fast risers. Given Elo, adding the gap is the same model as adding the ranking, so its improvement given Elo will equal the ranking's; it is listed for the other two scores | weak | as the ranking | small | + |
| Games-weighted Elo | Stage 1's surface Elo (retirements counted, its frozen constants) with each update multiplied by the match winner's share of the games, rescaled to average one over 2010–2018; the log-odds of its probability that A wins | scores; `stage1_baselines.elo_pass` | The weighted Elo (WElo) of Angelini, Candila and De Angelis, *European Journal of Operational Research* 297(1), 2022, doi:10.1016/j.ejor.2021.04.011. Its abstract reports that it beat the common tennis forecasting methods on over 60,000 matches ([abstract](https://cris.unibo.it/handle/11585/821483); the update rule in the [welo package documentation](https://search.r-project.org/CRAN/refmans/welo/html/welofit.html); both accessed 1 Oct 2026) | strong | small | none | + |
| Points-weighted Elo | The same, weighted by the winner's share of the points (of the games where there is no box score) | box scores, scores | The margin measured in points | strong | small | none | + |
| Serve rating | A's pre-match serve rating minus B's | `stage3_ratings.parquet` | Stage 3: the most repeatable measure of serve skill | moderate | small | none | + |
| Return rating | A's pre-match return rating minus B's | `stage3_ratings.parquet` | The same for the return | moderate | small | none | + |
| Ratings through the iid model | The log-odds of the iid model's match probability from the two expected serve rates (`p_serve_a`, `p_serve_b`), with the match's format and deciding-set rule | `stage3_ratings.parquet`, `stage2_iid.py` | Stage 3's suggestion. It knows match length | strong | clear (men), small (women) | none | + |
| Elo's change over 6 months | A's overall Elo now minus at A's first match on or after 182 days before this event; A − B | `stage1_baselines` | A rising or falling player whom Elo has not caught up with | weak | none | none | ? |
| Elo's change over 12 months | The same over 364 days | `stage1_baselines` | The same over a year | weak | none | none | ? |

**The player.**

| Feature | Before the match | Data | Why it might help | Alone | Given Elo | Given market | Sign |
|---|---|---|---|---|---|---|---|
| Age and age squared | (age − 25) and (age − 25)², each A − B: two inputs. Ages outside 14–50 count as missing | `age` (at the tournament's start) | Young players improve faster than a rating follows; older players decline | weak | small | none | − (with a peak) |
| Height | Centimetres, A − B | `height` | Taller players serve bigger | weak | none | none | + (men), ? (women) |
| Left-handed against right-handed | 1 if left-handed else 0, A − B: not zero only when a left-hander meets a right-hander | `hand` (R, L; U is unknown) | Left-handers' serve and spin are unusual for right-handers | weak | none | none | + |
| Record against the opponent's hand | A's career total points won against players with B's hand, minus against everyone (both shrunk); B's likewise; A − B | box scores, `hand` | Some players struggle against left-handers. This is the second reading of "left-handed against right-handed" | none | none | none | + |

**Activity, rest and fatigue.**

| Feature | Before the match | Data | Why it might help | Alone | Given Elo | Given market | Sign |
|---|---|---|---|---|---|---|---|
| Matches played (career) | log(1 + earlier matches, completed or retired, every level), A − B | Stage 0 | Experience. Elo starts every player at 1,500, which Stage 1 inferred is above a debutant's level | moderate | small | none | + |
| Matches played (last 52 weeks) | log(1 + matches of the last 364 days) | Stage 0 | Activity; winners also play more matches | moderate | small | none | + |
| Days since the last match | log(1 + days between the start of the last match's event and the start of this one), 0 for an earlier round of the same event; A − B | `tournament_date` | Rust after a break. Elo ignores time away (Stage 1) | weak | small | none | − |
| Last match ended early | Two inputs, each A − B: the player retired or gave a walkover in their last scheduled match; their last opponent did | `status` | An injury of their own, or a free pass | weak | small | none | − (own), + (opponent's) |
| Minutes in the previous match | Minutes of the last match played, A − B | `minutes` | Fatigue | weak | none | none | − |
| Sets in the previous match | Sets of the last match played, A − B | scores | Fatigue, known where minutes are not | weak | none | none | − |
| Minutes over the last 7 days | Minutes of this event's earlier rounds and of events that started up to 7 days before it; missing if any of those matches lacks minutes | `minutes` | Load. More rounds also means more matches won | weak | none | none | ? |
| Minutes over the last 14 days | The same up to 14 days | `minutes` | Load | weak | none | none | ? |
| Sets over the last 7 days | The same in sets | scores | Load | weak | none | none | ? |
| Sets over the last 14 days | The same up to 14 days | scores | Load | weak | none | none | ? |
| One of the first matches on this surface this season | 1 if the player has fewer than 3 earlier matches (completed or retired) on this surface this season, else 0; A − B | `surface`, `year` | Adapting to a new surface | weak | small | none | − |

**Inferred: what "days" means here.** Tournament start dates are not match dates (CLAUDE.md). The table holds each event's start date and the round, not the day a match was played. So days are counted between event start dates, and the 7- and 14-day windows are this event's earlier rounds plus events that started up to 7 or 14 days before it. **Observed:** of the evaluation players' previous matches, 49.5% were an earlier round of the same event, 23.1% were at an event that started exactly 7 days earlier, and 2.9% were more than 8 weeks back. tennis-data.co.uk dates its matches by day, but only on the main tour.

**Place and entry.**

| Feature | Before the match | Data | Why it might help | Alone | Given Elo | Given market | Sign |
|---|---|---|---|---|---|---|---|
| Playing in the home country | 1 if the player's country is the tournament's, else 0; A − B | `country` (the nation the player represents); the tournament's country from a hand-made table (section 4.6) | Crowd, travel, conditions | weak | small | none | + |
| Entry type: qualifier | 1 if the player came through qualifying; main draws only | `entry` | Qualifiers arrive with matches won on site, and tired | weak | small | none | + |
| Entry type: lucky loser | 1 if the player lost in qualifying and took a withdrawn player's place; main draws only | `entry` | They lost in qualifying | weak | none | none | − |
| Entry type: wild card | 1 if given a wild card | `entry` | Often a rising junior or a returning player | weak | small | none | ? |
| Entry type: protected ranking | 1 if entered on a protected ranking (the WTA's code SR included) | `entry` | Back from injury: rusty, while Elo keeps the old rating | weak | small | none | − |

**Format and level.**

| Feature | Before the match | Data | Why it might help | Alone | Given Elo | Given market | Sign |
|---|---|---|---|---|---|---|---|
| Match length (best of five) | The baseline's log-odds × 1 if the match is best of five, else 0. An interaction; it has no "alone" score, and applies to the men only. Best of five is read from the score, as Stage 2 did, and includes the Next Gen Finals' five short sets | scores, `format` | Stage 1, best of five: surface Elo's favourites won 2.9 points more often than it said (best of three: 1.9 points less often), and the market's favourites 2.0 points more often than their price | – | clear | small | + |
| Level played over the last 52 weeks | The share of the player's matches of the last 364 days played in Grand Slam to 250 main draws; A − B | `level` | Elo pools every level, so wins at lower levels flatter a rating. Stage 3: results from lower levels mislead | moderate | small | none | + |

**Point by point.**

| Feature | Before the match | Data | Why it might help | Alone | Given Elo | Given market | Sign |
|---|---|---|---|---|---|---|---|
| Big-point play on return | Stage 2's measure in each of the player's matches at earlier Grand Slams in the point-by-point files: importance-weighted return points won minus plain return points won. The mean, shrunk with a constant estimated as above; A − B | `stage2_pbp_players.parquet`, from Sackmann's files: the Australian Open and Roland Garros 2011–2021, Wimbledon 2011–2024 (no 2020), the US Open 2011–2024. Each player is linked to a Stage 0 id within the same draw | Stage 2: the one big-point skill that persists beyond luck (0.21 and 0.19 between halves of 10+ matches, against 0.01 and −0.01 in the pure-luck replays) | weak | small | none | + |

### 3.4 What happened to the starting list

| Starting list | Candidates |
|---|---|
| Every Stage 0 rate | Statistics 1–16 |
| Ranking and ranking points; the gap between ranking and Elo | Ranking, ranking points, the gap |
| Elo variants, including a margin-aware Elo on games or points | Games-weighted and points-weighted Elo. Overall Elo, Elo with retirements skipped and surface-only Elo are not added: Stage 1 scored them, and the owner closed Elo's details on 30 Sep 2026 |
| The Stage 3 serve and return ratings | Serve rating, return rating, ratings through the iid model |
| Age, age squared | One candidate with two inputs |
| The rating's change over 6 and 12 months | Two candidates, on overall Elo |
| Height | Height |
| Handedness; left-handed against right-handed | One feature covers both, since the difference is non-zero only when a left-hander meets a right-hander. The record against the opponent's hand is the second reading |
| Matches played | Career and last 52 weeks |
| Days since the last match | As listed |
| Whether the last match ended in retirement | Extended to walkovers, and to the opponent's retirement |
| Minutes and sets: the previous match, the last 7 and 14 days | Six candidates |
| First matches on this surface this season | As listed (fewer than 3 earlier matches on it) |
| Playing in the home country | As listed; the source is a hand-made table (section 4.6) |
| Entry type | Four candidates |
| Head to head; recent win rate; tiebreak and deciding-set records | Statistics 19, 17, 14 and 18 |
| Added | Statistics 20–22; the four matchups (from "A's serve against B's return"), one of them, the serve point from its parts, new; match length; level of the last 52 weeks; big-point play on return |
| Removed | None |

## 4. Coverage by tour, level and year

**How it is counted (observed, `stage4_candidates.py`).** For every candidate and form, the evaluation matches on which the feature exists for both players, under the rules of section 1, per tour × level group × season. The full table is `stage4_candidates_coverage.csv` (30,504 rows).
* Shares pool the scored seasons: 2013–2026, or 2019–2026 for the women's box-score candidates.
* "Main tour" is the Grand Slam to 250 main draws.
* "Lowest level" and "lowest year" are the level group and the season with the smallest share.
* The script reads no result column (who won) and compares nothing with results. Its one use of a score, whether a past match reached a deciding set, does not ask who won.

### 4.1 Statistics and matchups

Share of evaluation matches (%) on which both players have history in the form's window. The decayed and opponent-adjusted forms exist wherever the career form does.

| Statistic | Men: career | 52 weeks | surface | lowest level (career) | lowest year (career) | Women: from | career | 52 weeks | surface | lowest level (career) | lowest year (career) |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---|
| Serve points won | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Return points won | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Total points won | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Service games held | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.0 | 96.2 | 95.9 | Challenger / 125 qualifying 89.6 | 2021 97.0 |
| Return games won (breaks) | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.0 | 96.2 | 95.9 | Challenger / 125 qualifying 89.6 | 2021 97.0 |
| Aces | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Double faults | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| First serves in | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| First-serve points won | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Second-serve points won | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Break points saved | 97.6 | 96.1 | 95.8 | Challenger / 125 qualifying 91.7 | 2016 93.7 | 2019 | 98.0 | 96.3 | 96.1 | Challenger / 125 qualifying 89.8 | 2021 97.2 |
| Break points converted | 97.4 | 95.8 | 95.6 | Challenger / 125 qualifying 90.9 | 2016 93.3 | 2019 | 98.0 | 96.2 | 96.1 | Challenger / 125 qualifying 89.3 | 2021 97.2 |
| Break points faced per service game | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.0 | 96.2 | 95.9 | Challenger / 125 qualifying 89.6 | 2021 97.0 |
| Tiebreaks won | 98.2 | 96.7 | 96.4 | Challenger / 125 qualifying 93.4 | 2016 95.3 | 2013 | 99.3 | 97.4 | 96.7 | Challenger / 125 qualifying 97.2 | 2026 97.4 |
| Sets won | 99.5 | 99.0 | 98.7 | Challenger / 125 qualifying 98.5 | 2016 97.9 | 2013 | 99.8 | 99.4 | 99.1 | Challenger / 125 qualifying 99.6 | 2026 98.4 |
| Games won | 99.5 | 99.0 | 98.7 | Challenger / 125 qualifying 98.5 | 2016 97.9 | 2013 | 99.8 | 99.4 | 99.1 | Challenger / 125 qualifying 99.6 | 2026 98.4 |
| Matches won | 99.5 | 99.0 | 98.8 | Challenger / 125 qualifying 98.5 | 2016 97.9 | 2013 | 99.8 | 99.4 | 99.1 | Challenger / 125 qualifying 99.6 | 2026 98.5 |
| Deciding sets won | 98.4 | 97.1 | 96.7 | Challenger / 125 qualifying 94.1 | 2016 95.4 | 2013 | 99.4 | 98.3 | 97.5 | Challenger / 125 qualifying 97.8 | 2026 97.7 |
| Head-to-head record | 38.6 | 18.0 | 28.2 | Challenger / 125 qualifying 21.4 | 2024 36.6 | 2013 | 46.5 | 20.5 | 30.2 | Challenger / 125 qualifying 25.8 | 2013 41.7 |
| Return points against the first serve | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Return points against the second serve | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Break points above expectation | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Matchup: points | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |
| Matchup: games | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.0 | 96.2 | 95.9 | Challenger / 125 qualifying 89.6 | 2021 97.0 |
| Matchup: break points | 97.3 | 95.7 | 95.5 | Challenger / 125 qualifying 90.8 | 2016 93.3 | 2019 | 98.0 | 96.2 | 96.0 | Challenger / 125 qualifying 89.2 | 2021 97.2 |
| Matchup: the serve point from its parts | 97.6 | 96.1 | 95.9 | Challenger / 125 qualifying 91.8 | 2016 93.8 | 2019 | 98.1 | 96.3 | 96.2 | Challenger / 125 qualifying 89.9 | 2021 97.3 |

**Observed.**
* The box-score histories are thinnest in Challenger / 125 qualifying, and for the men in 2016. **Inferred:** 2016 is the first full season of men's Challenger qualifying in the table (Stage 0 found it absent before 2015 and thin in 2015), so it brings many players with no earlier box score.
* Head to head: the players had met before in 60.1% of the men's and 57.1% of the women's main-tour matches, and in 21.4% and 25.8% of Challenger / 125 qualifying matches (section 4.4).

### 4.2 How much history stands behind a shrunk statistic

Share of evaluation matches (%) in which both players' career history carries at least Stage 3's K units, so that each player's own rate counts at least half against the average.

| Statistic | K, units (men; women) | Men 2013–26 | main tour | Challenger / 125 qualifying | Women | main tour | Challenger / 125 qualifying |
|---|---|---:|---:|---:|---:|---:|---:|
| Serve points won | 466; 582 | 90.1 | 99.5 | 68.7 | 90.4 (2019–26) | 97.4 | 64.3 |
| Return points won | 1,052; 1,170 | 83.5 | 99.1 | 52.4 | 84.7 (2019–26) | 95.3 | 50.8 |
| Total points won | 1,959; 2,117 | 84.3 | 99.1 | 54.2 | 85.8 (2019–26) | 95.7 | 53.5 |
| Service games held | 72; 90 | 90.1 | 99.5 | 68.5 | 89.5 (2019–26) | 97.1 | 62.3 |
| Return games won (breaks) | 245; 245 | 78.9 | 98.6 | 43.3 | 79.4 (2019–26) | 93.2 | 40.0 |
| Aces | 137; 156 | 95.1 | 99.9 | 83.3 | 95.7 (2019–26) | 99.0 | 79.4 |
| Double faults | 256; 170 | 93.1 | 99.7 | 76.9 | 95.5 (2019–26) | 98.9 | 78.4 |
| First serves in | 225; 131 | 93.5 | 99.8 | 78.4 | 96.2 (2019–26) | 99.1 | 80.8 |
| First-serve points won | 221; 254 | 91.4 | 99.6 | 72.1 | 92.2 (2019–26) | 97.9 | 68.5 |
| Second-serve points won | 460; 439 | 82.6 | 99.0 | 50.5 | 84.6 (2019–26) | 95.2 | 50.1 |
| Break points saved | 246; 370 | 72.3 | 97.7 | 32.6 | 69.0 (2019–26) | 86.8 | 22.4 |
| Break points converted | 1,016; 791 | 35.4 | 80.2 | 4.5 | 46.4 (2019–26) | 68.5 | 4.8 |
| Break points faced per service game | 119; 156 | 86.5 | 99.3 | 59.4 | 85.1 (2019–26) | 95.5 | 52.8 |
| Tiebreaks won | 429; 569 | 0.0 | 0.0 | 0.0 | 0.0 (2013–26) | 0.0 | 0.0 |
| Sets won | 60; 57 | 94.5 | 99.8 | 81.8 | 98.0 (2013–26) | 99.4 | 92.2 |
| Games won | 341; 361 | 96.1 | 99.8 | 86.1 | 98.5 (2013–26) | 99.5 | 94.6 |

**Observed.** On the main tour nearly every player's history is deep enough for the serve and return statistics. Break points converted pass K in 35.4% of the men's matches. The tiebreak record passes it in none: Stage 3's constant is 429 tiebreaks for the men, about 1,150 matches. **Inferred:** the shrunk tiebreak record stays close to the average for everyone, which makes it a negative control.

### 4.3 Features with one form

Share of evaluation matches (%) on which the feature exists for both players. For the qualifier and lucky-loser candidates, the share is of main-draw matches (Grand Slams, 1000s, 500s, 250s, Challenger / 125). The Tour Finals have no entry types and are left out of "lowest level" for all four.

| Feature | Men: all | main tour | 2022–26 | lowest level | lowest year | Women: from | all | main tour | 2022–26 | lowest level | lowest year |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---|
| Ranking | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2013 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 |
| Ranking points | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2013 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 |
| Gap between ranking and Elo | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2013 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 |
| Games-weighted Elo | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2013 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 |
| Points-weighted Elo | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2019 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2019 100.0 |
| Serve rating | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2019 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2019 100.0 |
| Return rating | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2019 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2019 100.0 |
| Ratings through the iid model | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2019 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2019 100.0 |
| Elo's change over 6 months | 98.8 | 100.0 | 98.9 | Challenger / 125 qualifying 96.1 | 2016 96.8 | 2013 | 99.5 | 99.7 | 99.4 | Challenger / 125 qualifying 98.7 | 2026 97.4 |
| Elo's change over 12 months | 98.1 | 99.9 | 98.0 | Challenger / 125 qualifying 93.6 | 2016 95.7 | 2013 | 99.2 | 99.6 | 99.2 | Challenger / 125 qualifying 97.8 | 2026 97.3 |
| Age and age squared | 99.7 | 100.0 | 99.3 | Challenger / 125 qualifying 98.9 | 2026 98.0 | 2013 | 99.6 | 99.6 | 99.0 | Challenger / 125 qualifying 97.5 | 2026 96.3 |
| Height | 87.4 | 99.5 | 91.0 | Challenger / 125 qualifying 67.1 | 2016 74.3 | 2013 | 65.0 | 79.6 | 37.2 | Challenger / 125 qualifying 15.9 | 2025 24.9 |
| Left-handed against right-handed | 94.2 | 99.7 | 94.4 | Challenger / 125 qualifying 82.4 | 2016 88.4 | 2013 | 92.7 | 98.1 | 87.0 | Challenger / 125 qualifying 56.1 | 2026 79.3 |
| Record against the opponent's hand | 91.7 | 99.6 | 92.6 | Challenger / 125 qualifying 75.1 | 2016 83.8 | 2019 | 88.0 | 96.6 | 85.7 | Challenger / 125 qualifying 44.3 | 2026 78.5 |
| Matches played (career) | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2013 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 |
| Matches played (last 52 weeks) | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2013 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 |
| Days since the last match | 99.5 | 100.0 | 99.7 | Challenger / 125 qualifying 98.5 | 2016 97.9 | 2013 | 99.8 | 99.9 | 99.7 | Challenger / 125 qualifying 99.6 | 2026 98.5 |
| Last match ended early | 99.5 | 100.0 | 99.7 | Challenger / 125 qualifying 98.5 | 2016 98.0 | 2013 | 99.8 | 99.9 | 99.7 | Challenger / 125 qualifying 99.6 | 2026 98.5 |
| Minutes in the previous match | 81.1 | 91.5 | 86.6 | Challenger / 125 qualifying 64.3 | 2015 37.6 | 2013 | 62.0 | 69.7 | 81.0 | Slam qualifying 37.3 | 2014 0.0 |
| Sets in the previous match | 99.5 | 100.0 | 99.7 | Challenger / 125 qualifying 98.5 | 2016 97.9 | 2013 | 99.8 | 99.8 | 99.7 | Challenger / 125 qualifying 99.5 | 2026 98.5 |
| Minutes over the last 7 days | 85.6 | 91.5 | 88.7 | Challenger / 125 qualifying 81.2 | 2015 49.5 | 2013 | 71.8 | 72.9 | 87.0 | Challenger / 125 qualifying 67.2 | 2015 16.8 |
| Minutes over the last 14 days | 75.4 | 86.7 | 79.9 | Challenger / 125 qualifying 64.8 | 2015 39.7 | 2013 | 58.4 | 64.9 | 74.1 | Slam qualifying 44.4 | 2015 5.4 |
| Sets over the last 7 days | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2013 | 100.0 | 99.9 | 99.9 | 250s 99.9 | 2023 99.6 |
| Sets over the last 14 days | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | 2013 | 99.9 | 99.9 | 99.8 | 1000s 99.8 | 2023 99.4 |
| First matches on this surface this season | 100.0 | 100.0 | 100.0 | Challenger / 125 99.9 | 2024 99.8 | 2013 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 |
| Playing in the home country (players' countries only) | 99.9 | 100.0 | 99.9 | Challenger / 125 99.9 | 2026 99.1 | 2013 | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 |
| Entry type: qualifier (main draws) | 97.4 | 98.9 | 93.7 | Grand Slams 94.6 | 2026 69.5 | 2013 | 95.5 | 94.6 | 96.3 | Grand Slams 74.5 | 2016 80.9 |
| Entry type: lucky loser (main draws) | 97.4 | 98.9 | 93.7 | Grand Slams 94.6 | 2026 69.5 | 2013 | 94.3 | 93.0 | 96.3 | Grand Slams 67.2 | 2016 80.9 |
| Entry type: wild card | 95.8 | 95.1 | 95.1 | Slam qualifying 68.5 | 2026 76.5 | 2013 | 91.1 | 93.7 | 94.6 | Slam qualifying 60.0 | 2014 64.3 |
| Entry type: protected ranking | 79.0 | 67.2 | 88.6 | Grand Slams 0.0 | 2013 0.0 | 2013 | 22.5 | 26.1 | 37.1 | Grand Slams 14.6 | 2013 0.0 |
| Match length (best of five) | 100.0 | 100.0 | 100.0 | Grand Slams 100.0 | 2013 100.0 | – | – | – | – | – | – |
| Level played over the last 52 weeks | 99.0 | 99.9 | 99.2 | Challenger / 125 qualifying 96.5 | 2016 97.1 | 2013 | 99.4 | 99.7 | 99.3 | Challenger / 125 qualifying 97.9 | 2026 98.2 |
| Big-point play on return | 32.1 | 86.0 | 26.4 | Challenger / 125 qualifying 2.0 | 2026 19.5 | 2013 | 60.3 | 82.3 | 55.8 | Challenger / 125 qualifying 6.3 | 2026 45.9 |

**Observed.**
* **Rankings and ratings exist for every match by rule** (section 1, rule 6). How much stands behind them:
  * both players ranked: 96.6% of men's and 98.2% of women's matches; lowest in Challenger / 125 qualifying (88.1% and 90.8%);
  * both players rated on at least one earlier box score: 97.6% and 98.1% (women 2019–2026);
  * both established, with 2,000+ rated serve points (Stage 3's mark): 76.0% and 77.7%; on the main tour 98.3% and 92.3%; in Challenger / 125 qualifying 37.9% and 35.2%.
* **The market score** exists on 91.0% of men's and 98.0% of women's main-tour matches, and nowhere else. Stage 1 found no men's 2018 file and no odds below the main tour.
* **Home country:** the players' countries exist for nearly every match; the tournament's country is still to be built (section 4.6).

### 4.4 Where coverage varies by level

Share of evaluation matches (%) on which the feature exists for both players, 2013–2026.

| Feature | Tour | Grand Slams | Finals | 1000s | 500s | 250s | Slam qualifying | tour qualifying | Challenger / 125 | Challenger / 125 qualifying |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Height | men | 99.8 | 98.1 | 99.7 | 99.6 | 99.4 | 95.5 | 87.3 | 88.7 | 67.1 |
| Height | women | 82.1 | 96.8 | 82.6 | 82.5 | 74.3 | 51.8 | 57.1 | 32.2 | 15.9 |
| Left-handed against right-handed | men | 99.8 | 98.1 | 99.7 | 99.7 | 99.7 | 98.6 | 94.5 | 95.5 | 82.4 |
| Left-handed against right-handed | women | 99.2 | 100.0 | 99.3 | 98.7 | 96.3 | 91.4 | 88.7 | 83.2 | 56.1 |
| Minutes in the previous match | men | 88.7 | 93.7 | 94.7 | 91.4 | 91.1 | 78.8 | 76.2 | 83.5 | 64.3 |
| Minutes in the previous match | women | 68.2 | 74.4 | 74.9 | 73.0 | 65.5 | 37.2 | 47.9 | 72.8 | 55.2 |
| Minutes over the last 7 days | men | 89.0 | 96.8 | 94.3 | 91.8 | 90.8 | 86.4 | 89.0 | 83.9 | 81.2 |
| Minutes over the last 7 days | women | 70.0 | 91.9 | 77.3 | 77.8 | 68.9 | 77.5 | 67.9 | 70.9 | 67.2 |
| Entry type: protected ranking | men | 0.0 | 0.0 | 85.8 | 86.4 | 83.9 | 0.0 | 78.4 | 84.2 | 97.8 |
| Entry type: protected ranking | women | 14.6 | 0.0 | 19.7 | 23.2 | 38.8 | 17.8 | 19.3 | 16.5 | 17.3 |
| Big-point play on return | men | 86.7 | 83.2 | 91.2 | 89.5 | 81.5 | 30.2 | 35.6 | 17.4 | 2.0 |
| Big-point play on return | women | 86.0 | 100.0 | 91.1 | 87.8 | 71.3 | 29.0 | 37.7 | 35.4 | 6.3 |
| Head to head (career) | men | 57.6 | 72.1 | 66.8 | 64.7 | 55.5 | 33.7 | 34.2 | 35.9 | 21.4 |
| Head to head (career) | women | 55.4 | 89.5 | 65.6 | 64.3 | 48.4 | 29.1 | 33.4 | 39.8 | 25.8 |
| Head to head (52 weeks) | men | 27.1 | 58.7 | 35.5 | 33.5 | 25.1 | 14.1 | 14.4 | 16.6 | 9.7 |
| Head to head (52 weeks) | women | 24.3 | 63.9 | 33.0 | 31.2 | 19.4 | 11.8 | 13.5 | 16.5 | 10.3 |

### 4.5 Where coverage varies by year

Share of evaluation matches (%) on which the feature exists for both players.

| Feature | Tour | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Minutes in the previous match | men | 81 | 82 | 38 | 75 | 78 | 83 | 88 | 89 | 83 | 81 | 81 | 80 | 95 | 97 |
| Minutes in the previous match | women | 0 | 0 | 0 | 71 | 72 | 76 | 79 | 80 | 77 | 74 | 76 | 73 | 91 | 92 |
| Minutes over the last 7 days | men | 90 | 92 | 49 | 84 | 83 | 90 | 90 | 94 | 82 | 85 | 81 | 83 | 97 | 97 |
| Minutes over the last 7 days | women | 19 | 18 | 17 | 80 | 80 | 85 | 85 | 92 | 89 | 84 | 82 | 80 | 94 | 96 |
| Minutes over the last 14 days | men | 78 | 81 | 40 | 71 | 68 | 78 | 82 | 88 | 72 | 73 | 69 | 71 | 94 | 95 |
| Minutes over the last 14 days | women | 6 | 6 | 5 | 66 | 64 | 71 | 68 | 81 | 76 | 65 | 64 | 64 | 88 | 92 |
| Height | men | 83 | 84 | 85 | 74 | 81 | 83 | 91 | 96 | 96 | 95 | 96 | 93 | 85 | 85 |
| Height | women | 90 | 91 | 88 | 86 | 85 | 85 | 79 | 75 | 68 | 54 | 46 | 34 | 25 | 27 |
| Left-handed against right-handed | men | 95 | 94 | 95 | 88 | 92 | 93 | 96 | 98 | 99 | 98 | 99 | 96 | 90 | 89 |
| Left-handed against right-handed | women | 96 | 98 | 98 | 97 | 97 | 95 | 96 | 96 | 95 | 93 | 91 | 89 | 82 | 79 |
| Entry type: wild card | men | 100 | 99 | 100 | 92 | 91 | 95 | 97 | 97 | 100 | 96 | 100 | 100 | 100 | 77 |
| Entry type: wild card | women | 99 | 64 | 100 | 79 | 80 | 91 | 94 | 93 | 99 | 79 | 99 | 99 | 99 | 96 |
| Entry type: protected ranking | men | 0 | 0 | 89 | 92 | 91 | 91 | 89 | 86 | 90 | 92 | 92 | 93 | 93 | 69 |
| Entry type: protected ranking | women | 0 | 24 | 23 | 0 | 0 | 0 | 0 | 0 | 64 | 79 | 60 | 28 | 17 | 0 |
| Big-point play on return | men | 35 | 38 | 41 | 31 | 34 | 32 | 36 | 43 | 41 | 31 | 29 | 28 | 24 | 20 |
| Big-point play on return | women | 57 | 64 | 66 | 63 | 61 | 61 | 64 | 69 | 68 | 62 | 63 | 59 | 49 | 46 |
| Head to head (career) | men | 39 | 41 | 42 | 38 | 39 | 38 | 41 | 40 | 41 | 37 | 37 | 37 | 38 | 37 |
| Head to head (career) | women | 42 | 45 | 48 | 48 | 48 | 49 | 47 | 47 | 46 | 45 | 46 | 46 | 46 | 48 |

**Observed.**
* **Match minutes have holes in the sources** (`source_checks` in the summary):
  * the women's evaluation matches of 2013–2015 have almost none (40% of the 2013 Finals matches and 0.2% of the 2015 Grand Slam matches);
  * the men's of 2015 hold minutes for between none (Challenger qualifying) and 63.0% (1000s) of a level's matches, Challengers 37.2%, against 99.6% or more at every level in 2014.
* **Women's heights thin out from 2019.** Inferred: players who appear from then on mostly have no height recorded.
* **Big-point play falls in the last seasons.** The point-by-point files stop with the 2021 Australian Open and Roland Garros and the 2024 Wimbledon and US Open, so newer players have no such history.
* **The qualifier candidate** (section 4.3) is lowest in the men's 2026 main draws (69.5%) and the women's of 2016 (80.9%).

### 4.6 The tournament's country (the home-country candidate)

**Observed: no file on disk gives every event's country.**
* Sackmann's and Tennis My Life's match files carry each player's country (`winner_ioc`), not the event's.
* Open Tennis Data's tournament table gives a country for 61 of its 763 events (2020–2026).
* tennis-data.co.uk gives the city (`Location`), for the main tour only.
* The WTA's own calendar (`data/dump/points/wta/editions.parquet`) gives a country for all 828 of its editions: 2016 and 2018–2026, WTA 125 to Grand Slams, written in mixed forms (names and codes).

**The source, proposed: a hand-made table**, `data/studies/predictability_diagnostic/stage4_event_country.csv`, built at the start of Stage 4 and tracked by git.
* It gives each event's country as an IOC code (the code the players' countries use), from the city in the event's name in Sackmann's or Tennis My Life's files ("Brisbane", "Busan CH", "Forli 1").
* The evaluation matches of 2013–2026 hold 630 distinct men's and 204 distinct women's event names (digits removed).
* It is checked against tennis-data.co.uk's `Location`, through Stage 1's link (91.0% of men's and 98.1% of women's main-tour evaluation matches), and against the WTA calendar's country.
* Disagreements are listed, not resolved silently.
* **Players' countries** (Stage 0's `country`, the nation each player represents) exist for both players in 99.9% of men's and 100.0% of women's evaluation matches.

### 4.7 How often the single features are not zero

Share of evaluation matches (%) in which at least one of the two players has the property; entry types where they are recorded.

| Share of evaluation matches | Men | main tour | Women | main tour |
|---|---:|---:|---:|---:|
| Either player's last match ended early (retirement or walkover) | 8.0 | 7.7 | 7.4 | 7.9 |
| … of which a walkover | 1.1 | 1.5 | 1.2 | 1.6 |
| Either player has under 3 earlier matches on this surface this season | 24.5 | 22.9 | 28.5 | 24.2 |
| One left-hander against one right-hander | 22.3 | 23.9 | 15.5 | 15.5 |
| The two have met before | 38.6 | 60.1 | 46.5 | 57.1 |
| Best of five (read from the score) | 4.7 | 20.3 | 0.0 | 0.0 |
| A qualifier in the match (main draws where recorded) | 22.1 | 21.0 | 22.2 | 23.2 |
| A lucky loser (main draws where recorded) | 3.4 | 4.2 | 4.1 | 4.3 |
| A wild card (where recorded) | 16.3 | 12.2 | 15.1 | 12.6 |
| A protected ranking (where recorded) | 1.9 | 2.5 | 1.7 | 1.1 |

**Observed.**
* A protected ranking is in about one match in fifty. Inferred: in many level groups its results will be directional only.
* The big-point candidate links 19,705 of the point-by-point files' 19,896 player rows to Stage 0 ids (993 players). The other 191 are 32 blank names, and players whose name changed (Daria Gavrilova, now Saville; Klara Zakopalova, now Koukalova; Kateryna Kozlova, now Baindl), whose short name fits two players of the draw, or whose name is written in another short form.

## 5. The scoring plan (fixed now)

1. **Walk-forward by year from 2013.** For each tour, row and season Y from 2013 (2019 for the women's box-score rows) to 2026:
   * fit on the evaluation-level matches (completed or retired) of 2010 to Y − 1 on which the row exists;
   * score season Y's evaluation matches on which it exists.
   * 2010–2012 serve as the first training years, as in Stage 1's rank fits. Histories are short then, so the 2013 fits are the thinnest.
2. **The model.** Logistic regression without an intercept (side A is random), unpenalised, on at most three inputs. The Brief allows nothing beyond logistic regression on a few inputs.
3. **Three scores, each paired on the same matches.**
   * **Alone, against a coin.** Inputs: the feature (one or two inputs). Against 0.693.
   * **Given Elo.** Inputs: the log-odds of Stage 1's surface Elo (retirements counted, `p_elo_surf_ret`) and the feature. Against the model with Elo alone, refitted on the same matches. Refitting Elo means no feature gains credit for merely recalibrating it; Stage 1 found Elo over-confident at best of three.
   * **Given the market.** The same with the log-odds of the closing odds (`p_market`, the normalised average), on the main-tour matches with odds only.
   * The improvement is the baseline's log loss minus the candidate model's, per match, in milli-log-loss (positive = better), with a 95% range from the per-match differences.
4. **The null band.** For each row, tour and score, 20 copies of the feature, shuffled within each season (and tour) among the matches where it exists, go through exactly the same fits and scores.
   * Every match gets 20 random keys, the same for every candidate. A copy therefore shuffles every feature the same way, and the copies keep the candidates' links to each other, which the family-wide line needs (section 6).
   * A two-input feature moves as a pair.
   * The band is the copies' range; their mean and standard deviation are kept.
5. **Direction by era and by level.** For each row and tour, the given-Elo model is refitted inside each era (2013–16, 2017–19, 2020–21, 2022–26) and inside each of the nine level groups. Reported: the feature's coefficient with its 95% range, and the walk-forward improvement inside the group. Groups under 300 matches are directional only (the Brief).
6. **The ranking.** Per tour, rows ordered by their improvement given Elo over all scored seasons. Beside each:
   * its coverage;
   * its alone and market improvements;
   * its 95% range;
   * whether it clears its own band and the family-wide line;
   * how many eras share its sign;
   * its 2019–2026 and 2022–2026 values.
7. **Missing features.** A row is scored only on matches where it exists, and its baselines are fitted and scored on the same matches. Coverage is reported beside every score; improvements are per scored match.
8. **Leakage.** Before any scoring, the tests and the probe of section 1, rule 1.
9. **Out of scope** (the Brief): betting simulations, models beyond logistic regression on a few inputs, AUC.

## 6. How many comparisons, and what the null band and the ranking do about them

**Observed (counted from `stage4_candidates.csv`).**
* Men: 163 rows × 3 scores, less one because match length has no "alone" score: 488. Women: 162 rows × 3: 486. **974 comparisons** in all.
* Each comparison has 20 shuffled copies: 19,480 more fits of the same kind.
* Direction by era and level adds 4,225 looks (325 rows × 13 groups). They are read as description, not as tests.

**What chance alone would produce.** A row whose feature carries no information beats all 20 of its own copies with probability 1/21. Among 974 such comparisons, about 46 would clear their own band. The band alone cannot separate findings from chance at this scale.

**The family-wide line.** For each tour and score, each of the 20 copies gives the best improvement any row's shuffled copy reaches; the line is the largest of these 20 maxima.
* All features are shuffled with the same keys, so each maximum is a draw of "the best that this many useless features, as correlated with each other as these are, would look".
* A row above the line is about a 1-in-21 event for the whole family, not for one row.
* Rows differ in precision, so the line is drawn on a common scale: a row's improvement minus its copies' mean, in units of its copies' standard deviation. Each copy is measured against the other 19.
* Many rows are near-copies of one another: five forms of one statistic, the mirrors of serve and return. The effective number of independent tests is well below 974. The shared keys let the line account for that, rather than assume independence as a Bonferroni correction would.

**Reading rule (suggestion, fixed now).**
* A row counts as a **finding** only if it clears the family-wide line given Elo, **and** its improvement has the same sign in at least three of the four eras.
* A row that clears its own band but not the line is **possible**.
* A row inside its band shows **no sign** of adding anything.
* The top of each ranking is the best of about 160 rows, so its improvement is expected to be inflated. The summary quotes the 2019–2026 value beside the full-period one.

**Limitation.** 95% ranges from per-match differences treat matches as independent, as in Stages 1–3, so they are somewhat too narrow. The shuffled copies are the more robust guard.

## 7. Considered and left off

* **Big-point play on serve.** Stage 2 found no persistence beyond luck (its decision 6 suggested leaving it off).
* **Tiebreak over-performance against the iid expectation.** Stage 2: luck. The raw tiebreak record stays, as the list asks, as a negative control.
* **Momentum within a match** (Stage 2's decision 7). Not a pre-match feature.
* **Overall Elo, Elo with retirements skipped, surface-only Elo.** These are Elo's details, closed by the owner on 30 Sep 2026; Stage 1 scored them.
* **Seeding.** Set from the ranking at entry.
* **Indoor or outdoor.** Known only from Tennis My Life, which Stage 0 found gives it for 15.2% of Challenger and 0.3% of WTA 250 matches.
* **Match days and times.** Not in the table (section 3.3).
* **Ratings by surface, and ratings for more rates** (Stage 3's suggestions). Each needs a new rating pass. The surface and opponent-adjusted forms cover part of each.
* **Point-by-point data beyond Sackmann's Grand Slam files** (the official feeds, SofaScore and the others on disk). They are not linked to the study's tables; linking them is a project of its own.

## 8. Data problems that touch candidates

From earlier stages, reported and not fixed:
* **Match tiebreaks read as sets** (the Stage 0 audit's C3). In 11,127 women's ITF matches, most of them 2021–2024, phantom games enter the history of games won, and the match tiebreaks are missing from the tiebreak record. Stage 3 found the women's career games won misleading and named this as one of two causes. Touches games, sets and tiebreaks through history.
* **Split identities** (the audit's C2; Stage 1's 64 women from 25 May 2026). A split player's history starts again, so every history feature of those matches is affected.
* **Repeated Tennis My Life rows** (the audit's C1, 101 rows). Counted twice in histories, head to head included; the later copy of the 2025 Billie Jean King Cup sees its own result. Team events are history only.
* **Break counts that do not add up** (the audit's P2): 0.37% of men's and 1.67% of women's evaluation box scores. Touches holds, breaks and the break-point rates.
* **Wimbledon's last qualifying round recorded as best of three** (Stage 2's problem 2). Match length is read from the score, as Stage 2 did.
* **The closing odds** (Stage 1): no men's 2018 file; captured on 3 Aug 2026; Pinnacle's odds end in January 2026.

Found while counting coverage (observed, `source_checks` and the coverage table; not fixed):
* **Minutes.** Almost no women's minutes in 2013–2015; few men's minutes in 2015 (section 4.5).
* **Heights.** Both players' heights are known in only 37.2% of the women's 2022–2026 matches (section 4.5).
* **Ages.** 32 evaluation player rows carry an age outside 14–50, up to 3,387; the plan reads them as missing.
* **Entry codes.** In 30 tour × level × season cells, under half of the evaluation matches are in events whose draws carry any entry code:
  * the Tour Finals in most seasons (no qualifiers or wild cards there);
  * the men's Grand Slam qualifying of 2016–2018;
  * the women's Grand Slam qualifying of 2014 and 2016–2019;
  * the women's tour and 125 qualifying of 2014;
  * the women's 2022 Grand Slams, about half of their matches.
* **Protected rankings** are never coded at the men's Grand Slams or before 2015, and for the women only in some seasons. Each entry type is therefore scored only in the tour × level × season cells where its code appears at least once (section 4.3).

## 9. Decisions for the owner

1. **The list.** Approve, or edit: strike, add, or change a definition. In particular the additions: return points against the first and second serve, break points above expectation, the serve point from its parts, match length, the level of the last 52 weeks, and big-point play on return.
2. **The half-life.** Decided by the owner on 1 Oct 2026: 52 weeks.
3. **History for results-based statistics** (Stage 3's open decision 2). Every level, with the opponent-adjusted form as the fix (as planned), or evaluation levels only.
4. **Retirements in box-score histories** (Stage 3's open decision 1). Left out (as planned), or counted.
5. **"Left-handed against right-handed."** Keep the second reading, the record against the opponent's hand, or strike it.
6. **The reading rule and the expectation scale** (sections 3 and 6). Accept, or move the lines.
7. **The tournament's country.** Build the hand-made table at the start of Stage 4 (as planned), or name another source.
8. **The fatigue windows.** Counted in days between event start dates (as planned), or fatigue features restricted to main-tour matches dated by tennis-data.co.uk.
9. **Entry types where they are not recorded.** Each type is scored only where its code appears (as planned). The women's protected ranking then rests on 22.5% of matches: keep it, or drop it.
10. **Earlier open decisions that change coverage:** Stage 0's (the box-score windows, Tennis My Life's box scores, the last weeks of 2026) and Stage 1's women's split identities. Stage 4 uses the tables as built unless decided otherwise.

## Files

| What | Where |
|---|---|
| The candidate table (hand-made: one row per candidate, with its forms, scores, tours and coverage key) | `data/studies/predictability_diagnostic/stage4_candidates.csv` |
| Coverage and comparison counts | `src/eda/predictability_diagnostic/stage4_candidates.py` (under a minute), writing `stage4_candidates_coverage.csv` and `stage4_candidates_summary.json` |
| Tests | `test/predictability_diagnostic/test_stage4_candidates.py` (5 tests; 199 in the study, all passing) |
