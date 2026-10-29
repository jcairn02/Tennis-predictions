# The P9 point details: no new statistic to test, for men or women

28 October 2026 · For the owner · How it was done, step by step: [process_log.md](process_log.md) · The team's memos:
[builder](team/builder.md), [ideas](team/ideas.md), [scoring tool](team/harness.md) · Their briefs: [briefs/](briefs/)

**Status: a study, not a decision.** Nothing in the live model, the bet-day notebook or the shared tables changed. No
statistic was scored against match results. I added a dated note to the P9 report, which overstated what the new
fields hold, and later added what the rally counts really cover
([serve-speed acquisition, § 9.7](../serve_speed_acquisition/README.md)).

## Your request

> "24,997 of the 25,003 matches that have every point now carry the eight extra details per point, such as point
> duration and net approaches. Due to the P9 ATP infosys files
>
> IF AND ONLY IF, these were statistics not explored before properly for predictiveness (either from insufficient data,
> it not being relevant to the prodution model but now is, or we simply didnt have these stats before).
> Do a deep dive with a team of agents to see if any of these extra details could be promising as a new predictive
> statistics for either men or women (or both).
> The most important quality is orthogonality to the market information. Having it help the model predict better also
> helps."

**How I read it:**
* **Your condition first, detail by detail.** Does the field hold information we did not already have? Was the
  statistic behind it explored properly before? I checked each of your three clauses.
* **The team only for what passes.** Its measure: first, the gain beyond the closing price (your "orthogonality to the
  market"); second, the gain beyond the live model, both stages.
* **P9 is the ATP's files, so men only.**

## In short

* **None of the eight details meets your condition, so the deep dive did not go ahead.** For women there is nothing
  new: P9 holds no women's matches.
  * The fields are filled on nearly every match, as the P9 report said, but what they hold is mostly not new.
  * Five of the eight fields are copies of things we already had, or empty: who served first, the serve class, the two
    net flags and the last hitter. The extra momentum score is a running tally of the score.
  * Point duration is a real duration at only 17 of 535 events.
  * The two shot counts are a less reliable recount of rally lengths the files already had.
* **Rally length (men) was the one statistic your "insufficient data" clause could cover.** The shot-level study (2 Oct)
  found that its noisier rally statistics were held back by thin data. It also named a gap in men's tour-level data,
  April 2025 to June 2026, which P9 fills.
* **It failed on depth, before any match result was read.**
  * The bar, set first: P9 had to raise a player's year of rally data at least 1.5 times.
  * It raises it 1.07 times (1.45 under a second reading of the rule).
  * The reason: P9's "rally length known" flag is junk outside the matches the ATP tracked with cameras. Real rally
    lengths exist in 4,330 of its 25,004 matches: nearly every 1000s match, about half the 250s and 500s, and fewer
    than 1 Challenger match in 20.
* **So nothing enters the feature pool.** This does not show that rally statistics are worthless. They were not tested,
  because a test now could not answer.
* **What the work leaves behind:**
  * a calibrated scoring tool for any new men's statistic of 2025–26, against the closing price and against the live
    model (§ 4);
  * eight rally ideas, ranked, with the three to test first when the data allows (§ 3);
  * four side findings (§ 5);
  * **a lapse of mine for you to rule on.** The scoring tool measured the live model on matches kept sealed for an
    untouched test (§ 6). My recommendation is there.

Units: "thousandths" means thousandths of a log-loss point per match, the project's measure of forecast accuracy
(mLL). Higher gains mean more accurate. For scale, the model's whole edge over the men's closing price from January
2025 to 28 Jul 2026 was about 2.8 thousandths ([edge anatomy](../edge_anatomy/README.md), measured on the version of
10 Oct).

## 1. The eight details, one by one

The eight fields are who served first, the last hitter, the serve class, two shot counts and two net flags (one per
player), and point duration. The files also carry a momentum score per game.

| Detail | What it holds (measured on every P9 point) | New? |
|---|---|---|
| Who served first | The server of the match's first point, on 24,998 of 24,998 matches | No: already in the points |
| Last hitter | Empty on every point (3,589,532) | No data |
| Serve class | Ace, in play or double fault; agrees with the point's ending on 99.99% | No: aces and double faults are model inputs |
| Shot counts | A recount of the older rally counts: equal on 95.6% of points. On error points it adds the erring shot only about half the time, so it agrees with the ATP's own rally categories on 71% of errors, against 99% for the older count | No: less reliable than what was there. The statistic behind it, rally length, is § 2 |
| Point duration | A duration at 17 of 535 events (768 matches). Elsewhere a rally point gets the same value as an ace (median ratio 0.99), and the values bear no relation to the match's clock | Unusable outside 17 events |
| Net flags | Set at 24 of 535 events (1,133 matches), the same 24 whose net flags we have held since 24 Oct | No: a duplicate |
| Momentum per game | A running tally: +1 for a hold, +2 for a break, reset each set, with half-steps near level scores | No: a function of the score. Momentum and streaks were already tested at full depth and closed ([point sequence](../point_sequence/README.md), 6 Oct) |

## 2. Rally length: the one candidate, and why it stopped

* **Why it was a candidate.**
  * The shot-level study ([report](../shot_level/README.md)) found that rally length, net play and the other style
    rates add nothing beyond the close.
  * But its noisiest statistics carry only 15–34% of a player's true value into a pre-match number: quick points won,
    long rallies won, net points won. Edges of 1–2 thousandths could hide in them.
  * It also named the April 2025 – June 2026 gap. That is your "insufficient data" clause.
* **The bar, set at 08:55, before any result:** stop unless P9 raises the typical player-match's count of points with a
  known rally length, over the previous 52 weeks, at least 1.5 times on the priced matches.
* **The reading** (men's tour-level and Challenger main draws, 1 Jan 2025 – 18 Oct 2026):

  | Matches | Typical year of rally data, without P9 → with | Each player's ratio, median | Ratio of the medians |
  |---|---|---:|---:|
  | **All, priced (the rule's population; 35,660 player-matches)** | 758 → 1,100 points | **1.07** | **1.45** |
  | Tour-level main draws | 3,416 → 5,329 | 1.39 | 1.56 |
  | Challenger main draws | 343 → 485 | 1.00 | 1.41 |

  The last two rows count every match, priced or not (99.6% are priced).
* **Why so little.**
  * The flag, above.
  * P9 starts in January 2025, so matches early in 2025 gain nothing.
  * Tour players already had deep histories without P9, about 3,400 rally points a year. They come from the Slams' own
    feeds, the volunteer charts and other copies of the ATP's files.
  * Where P9 does add, it adds a lot: tour-level matches in the first half of 2026 have 2.1–2.2 times the data. That is
    the gap the shot-level study named.
* **The noisy statistics barely get more reliable.**
  * The measure: how well a player's rate in one half of his matches predicts it in the other half. 1 means a stable
    trait, 0 pure noise.
  * Points won at each rally length, 2026: 0.10–0.38 with P9, 0.08–0.39 without. Net points won: 0.105 with P9, 0.110
    without.
* **How close the call was.**
  * Under one reading of the rule (the ratio of the medians, 1.45) the call was close.
  * I made it after seeing the depth numbers, which a reviewer should weigh.
  * The reliability readings and the depth tour players already had point the same way.
* **What would reopen it:** real rally lengths at the Challengers (camera tracking at more events), or a 2027 season of
  1000s data for a tour-level test.

## 3. Eight rally ideas, for when the data allows

The ideas agent read the earlier studies' closures and a literature scan (14 sources, listed in its memo). It proposed
eight men's statistics. The percentages are its own rough guesses that each holds an edge beyond the closing price, not
measurements.

1. **Serve first-strike change (about 12%).** A player's recent share of serve points won within 4 shots, against his
   own norm, adjusted for opponents and venue. It is the rally version of the serve-speed change, the one point-level
   "how is he playing right now" statistic that has held up beyond the model.
2. **Return-neutralisation change (about 10%).** His recent share of returns put in play, against his own norm.
3. **Long-rally luck (about 8%).** Long rallies won beyond what the two players' long-run strengths imply. Prices
   follow results, and the market has under-corrected for luck in results (break points saved beyond what serving
   implies) in every era tested.
4. **Long-rally load within an event (about 6%).** Long rallies played in the last 4 days, beyond what minutes played
   imply.
5. **Venue rally pace (about 5%).** Where rallies run longer than the players' norms imply, favourites beat the close.
   It may re-find the fast-courts pattern already in the live model.
6. **Rally-mix style clash (about 3%).** How much this opponent and venue shift the rally lengths toward each player's
   strengths.
7. **Rally balance at depth (about 3%).** Strength in long rallies minus strength in short points, for players with
   deep histories.
8. **Net-approach change (about 1%).** Not computable: players have a median of 3 flagged matches.

* **The three to test first:** 1, 2 and 3, as one combined score.
* **None can be tested usefully now.**
  * Ideas 1–3 could be computed on roughly 1,500–2,000 tour-level matches of 2025–26 (the agent's estimate, not
    counted).
  * On that many matches, a real effect as large as the serve-speed change would be measured at about 1.8 times its own
    noise. So it would be missed about half the time, and rally effects are likely smaller.

## 4. The scoring tool, ready for the next question

* **The matches:** 25,807 men's matches, 1 Jan 2025 – 18 Oct 2026, tour level (main draws and qualifying) and
  Challengers. 25,542 of them have a price, with the margin removed:
  * tour main draws: the Pinnacle-first closing price (the rule of 21 Oct);
  * tour qualifying: OddsTrader's last lines (Pinnacle to Sep 2025, then BetOnline);
  * Challengers: TennisExplorer's last pre-match price, Pinnacle's where shown with a time, else the other books'
    median. It is linked to our match table for 99.4% of matches. It is a late price, not a close.
* **The live model's forecasts**, both stages, on all 7,266 priced tour-level matches. They come from stored fits that
  never saw the season they forecast: no new fit, no GPU.
* **Checked against noise.** 2,000 random columns per group behaved as noise should: the spread of the test statistic
  was 1.00–1.05, against 1 expected.
* **The smallest effect it detects 80% of the time,** for a statistic present on every match:

  | Matches | Count | Smallest detectable gain (thousandths) |
  |---|---:|---:|
  | All | 25,542 | 0.15 |
  | Challengers | 18,276 | 0.22 |
  | Tour level | 7,266 | 0.53 |
  | Tour main draws | 4,937 | 0.76 |
  | Tour qualifying | 2,329 | 1.65 |

  The stricter reading, a gain whose 95% range clears 0, needs about four times as much.
* **How to run it:**

  ```
  ./python.sh src/eda/p9_point_details/harness.py --feature <file.parquet> --column <name> --direction 1 \
      --populations all,tour,tour_main,tour_qual,challenger,ch_main,ch_qual --bases price,model \
      --last-date 2026-10-18 --out <readings.csv>
  ```

  The file holds Stage 0's match id and the statistic as player A minus player B. `--last-date 2026-10-18` leaves out
  the untouched test of the model's edge (§ 6). *Updated 29 Oct:* the tool names every protected period its window
  reaches, from the project's [register](../../holdouts/README.md), and says which `--last-date` leaves each out.

## 5. Side findings

1. **Below the main tour, favourites win more often than the prices say.**
   * The price's calibration slope (1 = right-sized; above 1 = favourites under-priced): 1.08 at Challenger main draws,
     1.19 at Challenger qualifying, 1.16 at tour qualifying, against 0.99 on the tour main draw.
   * The qualifying study found the same on tour qualifying (1.11–1.13).
   * The Challenger prices are late pre-match prices, not closes. No profit was tested.
2. **The shared match table has no men's Challenger qualifying after June 2026.** This is by design: the weekly
   lower-level feed is merged only into each build's own copy. A study that reads the shared table for lower-level 2026
   matches has to merge the feed first.
3. **Rally lengths are counted two ways.** Roland Garros 2026's ATP-format files count the erring shot; P9 and the
   Australian Open and Roland Garros 2025 files do not. The builder reads each event's rule from the data. Anyone
   reading rally lengths from those files needs the same step.
4. **The close under-rates newer players.**
   * One of the tool's dummy columns was the order of the players' ids, roughly when each joined the tour. It predicted
     results beyond the price: 3.3 times its noise pooled, 2.2 at tour level.
   * Beyond the live model it read only 1.2. The model's age and rating inputs absorb most of it.
   * It echoes a lead already in the feature pool (U-330: the close under-rates players arriving from lower levels).
   * It was read over the whole window, sealed months included.

## 6. A lapse of mine: the sealed matches

* **What happened.**
  * The [edge-anatomy study](../edge_anatomy/README.md) (12 Oct) kept every match from 29 Jul 2026 "sealed for a
    future untouched test" of the model's edge.
  * My brief for the scoring tool set its window to 18 Oct without checking that.
  * So the tool measured the live model against the closing price on matches up to 18 Oct, sealed weeks included.
* **What it exposed.** The tool's memo gives two pooled figures, to July and to 18 Oct. From them the sealed weeks'
  figure could be roughly worked out.
  * I made a rough estimate in my head on first reading them, then stopped. It is not written anywhere, and I have not
    used it.
  * I recommend that nobody works it out.
* **What it did not touch:** any candidate statistic, and the five-pattern score.
* **Those weeks were not untouched before.** Your check of the five patterns on 13 Oct read matches to 23 Sep, with the
  model as its base. That check led to the adjustment now in the live model.
* **My recommendation: count the untouched test of the model's edge from 19 Oct 2026,** the day after the tool's
  window.
  * The live model's five-pattern adjustment was adopted on a check that read the matches to 23 Sep. So for the model
    as it runs today, those weeks were already seen by a decision.
  * The weeks to 18 Oct now have a published figure from which their edge can be estimated.
  * A clean start date avoids arguing later about what was seen.
  * **The cost:** about 600 men's main-draw matches, and the women's of the same weeks. An untouched test needs several
    thousand matches, so it would finish about two to three months later.
* **The other option:** keep 29 Jul, since no decision has been made from this figure. That keeps more matches but
  rests on nobody working it out.
* **Either way, record the ruling in the decisions folder.** No central record of the seal exists today, which is how
  my brief missed it. The tool now warns whenever a window reaches 29 Jul 2026.
* ***Ruled on 29 Oct 2026:*** *you chose 19 Oct 2026, as a soft rule you may override
  ([decision](../../decisions/2026-10-29-holdout-soft-rule.md)). The protected periods are now in one
  [register](../../holdouts/README.md). Every read of recent results goes into a ledger, and the tool's warning reads
  the register.*

## 7. What I recommend

1. **Nothing from the eight details enters the feature pool.** By the adoption framework these would be new features.
   None was built, so there is nothing to admit.
2. **Keep the rally ideas on file** (§ 3, with full definitions in the ideas memo). Revisit them when real rally
   lengths reach most tour-level and Challenger matches, or after a 2027 season of the 1000s. No action now.
3. **A Challenger test of rally statistics is possible today, but I don't recommend it.** It falls outside your
   request.
   * Outside the sealed weeks, about 7,900 main-draw matches have both players with at least 300 rally points of
     history: 3,655 Challenger and about 4,200 tour-level. A test there would see effects of about 0.5 thousandths.
   * But it would rest on data we already had, not on P9's details.
   * We do not bet Challengers, so there is no price to act on.
   * Worth doing only if Challenger betting becomes a target.
4. **Rule on the sealed weeks** (§ 6). I recommend counting from 19 Oct 2026 and recording it.
5. **Outside the eight details,** P9's per-point serve speeds could test two leads the serve-and-return study left
   unresolved: the speed fade within a match, and fault speed. That study rated them low priority. Nothing here changes
   that.

## 8. Files and reproduction

| What | Code (`src/eda/p9_point_details/`) | Outputs |
|---|---|---|
| The gate's numbers (§ 1) | `field_profile.py`, ~20 s | `data/studies/p9_point_details/field_profile.json`, `field_profile_events.csv` |
| Rally data, depth, reliability, timing probe (§ 2) | `build_*.py`, in the order of the [builder's memo](team/builder.md#what-was-built), ~10 min | `data/studies/p9_point_details/build/` |
| The ideas (§ 3) | `ideas_coverage.py` (prints only) | [team/ideas.md](team/ideas.md), [team/ideas.csv](team/ideas.csv) |
| The scoring tool (§ 4) | `harness_population.py`, `harness.py`, `harness_calibrate.py`, ~20 min | `data/studies/p9_point_details/harness/` |
| Tests | `test/p9_point_details/`: 21 pass | |

Run everything from the repository root with `./python.sh`. The P9 tables, the shared match table, the match clock and
TennisExplorer's tables all move with later downloads. Their hashes and dates at the time are recorded in the
outputs (`population_facts.json` and the builder's reports). A later rebuild gives slightly different numbers.

**29 Oct 2026:** the nine `.parquet` tables in `build/` and `harness/` (26.1 MB, ignored by git) were deleted at your
word ([cleanup inventory, process log § 10](../cleanup_inventory/process_log.md)). The JSON and CSV outputs stay, and so
does every number in this report. The commands above rebuild the tables, with slightly different numbers.
