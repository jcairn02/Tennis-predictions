# TennisLive's box scores fill 417 lower-level gaps, and the freeze is narrowed to data that changes coverage

14 October 2026 · For the owner · Status: **done and in use** (decision of 14 Oct 2026, [record](../../decisions/2026-10-14-lower-level-gap-fills.md)) · [Process log](process_log.md)

## What you asked

> "I was pretty sure I lifted the data freeze? yet it keeps coming up? Filling in those ~420 box scores seems strictly better than not?"

then "record the decision, update the projecct rules to match and build the tenis live package", and, about the 183 men's Slam-qualifying matches left out of the first package, "Yes add and fix those".

## What was done

1. **The decision is recorded.** It is what you asked on 11 October ("Why aren't we just using the newest data?"), which had been written down only for Tennis My Life's own corrections.
   * **Enters by itself:** lower-level data that fills holes, from a source whose box scores match ours. It goes into bet-day runs at once and into training at the next rebuild. That rebuild's harm check covers it.
   * **Still tested first:** only data that would change coverage. Examples: ITF box scores for seasons that have none, or a level the history never held.
   * The two tests and their thresholds are in the record. The thresholds are mine; you can change them.
2. **The project rules match it.** The instructions every session reads (CLAUDE.md), the decision index, and notes in the 8 Oct and 13 Oct decisions now say this, so sessions stop calling these fills frozen.
3. **Two TennisLive packages are in use, 417 box scores in all.** 414 of them fill a gap in today's tables; the other 3 matches already have Roland Garros's own box score from the repair you adopted on 10 Oct.
   * The first package (233) went in at 09:59.
   * The second, men's 2018 Slam qualifying (184), went in at 12:32.
4. **Both tests are fixed** (your "fix those"), so the misfire that held back the men's matches can't repeat.

## The two tests, as fixed

* **Do TennisLive's numbers match ours?** Where both have a box score, TennisLive's must equal ours on at least 98% of matches, for each tour and level.
  * **Fixed:** it is now read against today's tables, with every repair you adopted. The first check read only the frozen 8 Oct copy. That copy still has the Roland Garros 2022–26 error, second serves recorded as first serves, which is why men's Slam qualifying read 95.3% there.
  * Against today's tables it reads 99.6%, and every tour and level passes.
* **Does it fill a hole, rather than add a new kind of data?** Before the fill, a season must already have box scores for at least half its matches.
  * **Fixed:** a season now also passes when the fill brings it closer to that level's other seasons.
  * Men's 2018 Slam qualifying had box scores for 49% of its matches, against about 100% in every season from 2019. It goes to 90%.
  * A level that is empty in most seasons still fails, so it is still tested first. ITF before 2025 is the example.

## What the packages fill

| | Matches |
|---|---:|
| Men's Grand Slam qualifying (Roland Garros 2018 88, Wimbledon 2018 95; 1 RG 2022 already scored) | 184 |
| Women's Grand Slam qualifying (Roland Garros and Wimbledon 2018: 139) | 142 |
| Men's Challengers | 61 |
| Men's Challenger qualifying | 20 |
| Women's tour qualifying | 5 |
| WTA 125 and its qualifying | 3 |
| Men's tour qualifying (2015) | 2 |

All are from 2015–2024, most from 2018. None are from 2025 or 2026.

**How we know TennisLive's numbers can be trusted.** Against today's tables, where both have a box score, they are equal on every count:
* 99.87% of 17,013 men's Challenger matches;
* 99.99% of 6,746 Challenger qualifying matches;
* 99.6% of 845 men's Slam qualifying matches;
* 99.7% to 100% at every women's level.

TennisLive gives no count of service games. Our history already accepts box scores without that count.

**What I checked on the 417 themselves:**
* **The right match.** 60 drawn at random, 30 from each package, compared by hand: all 60 had the same players, event, round and score.
* **The right player.** All 417: each player's numbers sit on that player's side.
* **The right winner.** Agreed on 416. The other is the 2018 Chengdu Challenger final, a retirement (Ze Zhang beat Henri Laaksonen 2-6 5-2, retired). TennisLive names the wrong winner there; our result stands, and the numbers are placed by player name.

**How much it changes.** Very little, as expected.
* 2,100 of the 67,226 main-tour training matches (3.1%) have a player whose previous year gains a box score, and 292 within the last four weeks:
  * mostly women's 2018–19 from the first package (1,229 alone);
  * mostly men's 2018–19 from the second (913 alone).
* Today's bets are barely touched, since no filled match is from 2025 or 2026.
* No retrain for this alone. The next rebuild takes them in, and its harm check covers them.

**One cost on bet days.** The daily run checks whether the history behind its saved checkpoint has changed, and it has. So it recomputes those parts, about four extra minutes a run. That stops once a run saves a checkpoint on the new tables, which it does by itself when a new checkpoint week starts.

## Still not in

* **Up to 73 matches that our builder could not confidently match to our records.** It left them out by its own rules. Some may already have a box score from our other results file.
* **ITF matches.** TennisLive misses points in about 15% of ITF matches, so the weekly feed already excludes them.

## Files

* The packages: `data/studies/current_best_model/accepted_additions/tennislive_box_fill/` and `…/tennislive_box_fill_men_gsq/` (both listed in `accepted.json`).
* The evidence: `data/studies/tennislive_box_fill/`:
  * `conditions.json`, `c1_agreement.csv` and `c2_coverage.csv`: the first reading of the whole candidate, under the tests as first written;
  * `parent_fixed/`: the whole candidate under the fixed tests;
  * `package/` and `men_gsq/`: each package's own numbers, hand check, side check and merge on today's tables.
* The code: `src/eda/tennislive_box_fill/conditions.py`. Tests in `test/tennislive_box_fill/`.
