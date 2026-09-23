# Merge feasibility and a proposed database structure

**The staged sources can be joined into one singles database, but only identity-first: players and tournament editions must be resolved before matches are matched, because name-only matching would have double-counted 9,331 matches in the Sackmann and Tennis My Life overlap.** At 873,362 singles matches and 30,942 players since 2010, the UFC project's layout does not scale. That project keeps one wide two-rows-per-fight history table holding in-match statistics and pre-match averages, for 7,687 fights. This study measures how the sources join. It then proposes separate identity, fact, market, feature and modelling layers, with pre-match features computed in one chronological pass.

**Status: study and proposal, not a decision.** Nothing is built into a pipeline. The provisional canonical table used here is a measuring device, not the merged database.

| Item | Where |
|---|---|
| Scan: source overlap, identity, link rates, dates, statistics, prices | `src/eda/merge_feasibility/scan.py` → [summary.json](../../../data/studies/merge_feasibility/summary.json) |
| Running-state feature demo | `src/eda/merge_feasibility/running_state_demo.py` → [running_state_demo.json](../../../data/studies/merge_feasibility/running_state_demo.json) |
| Input | Staged public dump of 22 September 2026 (`data/dump/`, see the [dump report](../public_data_dump/README.md)); singles; source files for 2010 onward |
| Earlier proposal this revises | [Public dump structure plan](../public_data_dump/structure-plan.md) |

## Question and method

**Question.** How do the staged sources join (overlap, identifiers, link rates, dates, statistics), at what scale, and what structure should the cleaned database take?

**Method.** Staged string Parquet is read with names normalised: accents, case and punctuation are removed and name tokens are sorted, so "Zhang Zhizhen" equals "Zhizhen Zhang". There are two linking stages.

* **Tennis My Life (TML) to Sackmann.**
  * First pass: same tour, round and name pair, with tournament weeks within 10 days.
  * Second pass, the *one-player anchor*: same tour, normalised tournament id (`2024-0339` = `2024-339`), round, and one identical player. In singles a player plays one match per round.
* **All other sources to a provisional canonical table.** The table is Sackmann's rows plus the TML rows that neither pass found. Other sources link by exact name pair inside a date window measured from the tournament week. Qualifying may precede the week by up to 10 days and other rounds by up to 3. The nearest tournament week wins, and ties count as ambiguous.
  * tennis-data.co.uk ("Sinner J.") uses surname plus first initial, matched against every surname span of the full name.
  * Abbreviated Grand Slam point-file names ("N. Djokovic") use the same rule.

There is no fuzzy matching, so every rate is a lower bound. Settled Polymarket outcomes are compared with the linked results as a check on link quality.

The demo builds the two-rows-per-match facts table from the canonical table and times pre-match features. It also times a UFC-style per-row look-back on a sample and extrapolates.

## Findings

### Scale

| | UFC project (men's v3 history file) | Tennis, singles, 2010 onward |
|---|---:|---:|
| Matches or fights | 7,687 | 873,362 (114×) |
| Players or fighters | 2,322 | 30,942 (ATP 14,807, WTA 16,135; 14,069 active since 2022) |
| Two-rows-per-match rows | 15,374 × 168 columns, 28 MB CSV | 1,746,582 |

* **By tier.** Qualifying is included in each tier.

  | Tier | Matches | Share |
  |---|---:|---:|
  | ITF | 608,137 | 69.6% |
  | Challenger / WTA 125 | 124,746 | 14.3% |
  | Tour level | 101,603 | 11.6% |
  | Grand Slams | 30,703 | 3.5% |
  | Team events | 8,173 | 0.9% |

* **Players are very unequal.** The median player has 6 matches and the 90th percentile 173; 45% of players have fewer than 5. The 6,587 players with 50 or more matches produce 88.4% of player-match rows.
* **Score markers.** 3.3% of matches are marked retired and 0.5% walkover.

### Two overlapping sources, one match table

| Tennis My Life rows compared with Sackmann | Exact name pair | One-player anchor | Ambiguous | Not in Sackmann |
|---|---:|---:|---:|---:|
| ATP, tournament weeks before 25 May 2026 | 137,237 | 9,090 | 32 | 1,187 |
| WTA, tournament weeks before 25 May 2026 | 43,326 | 216 | 0 | 121 |
| ATP, from 25 May 2026 | 425 | 25 | 0 | 3,840 |
| WTA, from 25 May 2026 | 0 | 0 | 0 | 912 |

* **The 9,331 anchor links are the same matches under another spelling.**
  * In 9,226 of them the other player shares a name token, for example "Fred Gil" and "Frederico Gil", "Albert Ramos Vinolas" and "Albert Ramos", or "Aliaksandr Bury" and "Alexander Bury".
  * 105 name a different opponent. That is a source disagreement to review, not a separate match.
  * 1,140 players appear under a second spelling.
* **Shared matches mostly agree.** Of 180,988 exact-pair shared matches, 114 disagree on the winner. Serve statistics are in both sources for 169,447, only TML for 2,262, and only Sackmann for 537.
* **Each source repeats matches internally.**
  * Sackmann repeats 1,479 matches, mostly WTA 125 events and their qualifying duplicated inside the `qual_itf` files.
  * TML repeats 89.
* **Result.** The canonical table is Sackmann's 867,302 matches plus 6,060 from TML:
  * 4,752 from tournament weeks starting 25 May 2026 or later, which Sackmann lacks;
  * 1,308 older gaps.
* **Residue.** 886 player rows share player, week and round under two different tournament ids.
  * Example: Memphis 2014 appears as `2014-402` and `2014-424`, with "Victor Estrella" and "Victor Estrella Burgos".
  * A third pass on resolved player ids catches these.
  * 8,718 rows are round-robin matches that need a match number or day to order them.

### Identity

| Source | Player identifier | Measured |
|---|---|---|
| Sackmann | Numeric ATP and WTA ids | Carries the ids for over 99% of canonical rows |
| TML, ATP files | ATP website codes such as `S0AG` | 4,373 of 4,562 codes learned from shared matches. 196 codes map to two Sackmann ids and 319 Sackmann ids have two codes. Name plus birth date matches 8,365 of 12,903 database codes. |
| TML, WTA files | Sackmann WTA ids | 262 of the 339 ids in TML-only rows confirmed by name. The rest are players newer than the Sackmann player file. |
| Live Tennis API | Own ids, partial `sackmann_id` | 5,947 of 23,683 players in its match index have a Sackmann id |
| Open Tennis Data | Sackmann ids | 1,211 of 1,216 players |
| tennis-data.co.uk, Polymarket, Match Charting Project, Grand Slam point files | Names only, in four formats | See the link rates below |

518 active player ids share a normalised name with another active id. For example, three WTA ids normalise to "Brooke Black". These are either namesakes or duplicate records; in both cases a name-only join needs context (tour, date, opponent).

### Link rates onto the canonical table

| Source | Rows | Linked | Notes |
|---|---:|---:|---|
| tennis-data.co.uk results and closing odds, 2010 onward | 79,728 | 95.0% | 19 more link only with winner and loser swapped. The match day falls a median 2 days after the tournament-week date (5th–95th percentile: 0–6). |
| Open Tennis Data completed results | 26,619 | 99.8% | Day-precision dates |
| Match Charting Project charts, 2010 onward | 9,429 | 98.6% | |
| Grand Slam point-by-point | 10,481 | 95.2% | Australian and French Open files abbreviate names from about 2019; 97% of those link once that format is handled |
| Live Tennis API match index | 173,571 | 58.9% | ATP 84.8%, WTA 79.4%, Challenger 80.0%, ITF 57–58%; doubles and other keys 0% |
| Polymarket singles moneylines | 33,673 | 40.2% | Varies by bucket and period (next table) |

| Polymarket bucket | Linked, before 2 June 2026 | Linked, from 2 June 2026 |
|---|---:|---:|
| Grand Slam main draw | 94.8% | 94.1% |
| Masters / WTA 1000 | 93.1% | 93.7% |
| 500s | 89.6% | 88.9% |
| 250s | 89.1% | 83.2% |
| Challenger / WTA 125 (inferred bucket) | 85.4% | 57.1% |
| ITF | 92.1% of 1,768 | 3.5% of 16,162 |
| Main-tour qualifying | 86.6% | 36.3% |
| Grand Slam qualifying | 69.5% | 45.2% |
| Grand Slam juniors | 0.5% | 0% |

* **Links are reliable.** Settled winners agree with the linked match data 13,418 times and disagree 21 times.
* **Walkovers settle at half.** 53 of the 73 linked markets settled at 0.5/0.5 are walkovers in the match data; one is a retirement.
* **The gap is missing results, not unknown players.** Of the 18,773 markets from 2 June left unlinked, both players already appear in the match data for 15,168. For ITF that is 12,660 of 15,593.
* **Minute prices are available close to the start.**
  * 33,153 singles moneylines have minute prices, 53.5 million rows in all.
  * By bucket, 95.7–100% have an observation within the hour before the scheduled start.
  * Median price history before the start runs from 11.7 hours (ITF) to 54 hours (Grand Slam main draws).

### Dates and statistics

* **Exact match days depend on tier.** Coverage below counts a day from any of tennis-data.co.uk, Open Tennis Data, the Live Tennis API or the Match Charting Project, for tournament weeks from January 2023 to July 2026.

  | Draw | Exact day available |
  |---|---:|
  | Grand Slam and tour-level main draws | 97–99% |
  | Challenger / WTA 125 main draws | 82–84% |
  | ITF main draws | 34% |
  | WTA ITF qualifying | 0% |

  Elsewhere only the tournament week is known, so order within an event has to come from the round.
* **Sources date the same match differently.** The 2026 Miami final carries:
  * 18 March in Sackmann (tournament start);
  * 29 March in TML, tennis-data.co.uk, Open Tennis Data and the Match Charting Project;
  * 20:45 UTC on 29 March as Polymarket's scheduled start;
  * 02:45 UTC on 30 March in the Live Tennis API.
* **Serve statistics are near-complete except at ITF level.**
  * About 99% of Grand Slam, tour-level and Challenger main-draw matches have them in most years.
  * Exceptions: WTA tour level was 90% in 2010 and 75% in 2015, and qualifying had gaps in 2015.
  * ITF: 0–0.6% through 2024, then 97–99.6% in 2025–2026.
  * Team events are patchy.

### Running state versus per-row look-back

| Step, on 1,746,724 player-match rows | Seconds |
|---|---:|
| Load both sources and link them | 5.9 |
| Build the two-row facts table (17 columns) | 2.5 |
| Career-to-date features, vectorised | 0.3 |
| Time-decayed win rate, one pass | 3.1 |
| Elo over 873,362 matches, one pass | 0.9 |

* **Sizes.**
  * The facts table is 17.1 MB as Parquet (181 MB in memory).
  * Eight pre-match feature columns take 30.3 MB (88 MB in memory).
  * By extrapolation (28 MB × 114), the UFC history layout scaled to tennis row counts would be about 3.2 GB of CSV.
* **Look-back cost.** A UFC-style per-row look-back masks the whole table for this player before this date. It measured 13.8 ms per row, which is about 6.7 hours per feature column at this size.
* **Checks.**
  * No first appearance has any history.
  * The pre-match Elo favourite won 68.3% of matches. This is a sanity check only; the Elo parameters are arbitrary.

## Proposed structure

### Layers

| Layer | Holds | Built from |
|---|---|---|
| Raw | Byte-exact downloads and receipts (exists) | Append-only |
| Staged | One string Parquet per source file (exists) | Raw |
| Identity | `players`, `player_ids`, `tournaments`, `editions`, `edition_ids` | Staged, with reviewed conflicts persisted |
| Facts | `matches`, `match_players`, `match_sources`, `rankings`; detail tables `points`, `charting_stats`, `score_states` | Staged plus identity, deterministically |
| Markets | `bookmaker_odds`, `markets`, `market_prices`, `market_links` | Staged plus facts |
| Features | `player_form`, versioned by feature set | Facts, in one chronological pass |
| Modelling | `train_matches`, `train_markets` | Queries over the layers above, not stored truth |

### Tables

| Table | One row per | Key | Main columns |
|---|---|---|---|
| `players` | Person | `player_id` (own) | Tour, name, birth date, hand, height, country |
| `player_ids` | Player, source and source id or name form | (`source`, `source_key`) | Method, evidence count, first and last seen, status (confirmed / conflict / review) |
| `tournaments`, `editions` | Event; event-year | `edition_id` | Tour, start (week Monday), end, tier, prize level, surface, indoor, draw size, best of |
| `edition_ids` | Edition and source id or name | (`source`, `source_key`) | Sackmann and TML ids, tennis-data.co.uk names, Live Tennis API keys, Polymarket leagues |
| `matches` | Physical singles match | `match_id`; natural key (edition, draw, round, player) | Winner and loser ids, status, score, best of, minutes, `match_date`, `date_precision`, `scheduled_start_utc`, `round_order`, `stats_level`, `result_source` |
| `match_players` | Match and player (two rows per match) | (`match_id`, `player_id`) | Opponent id, won, seed, entry, rank and points, age, in-match serve and return counts, `stats_source` |
| `match_sources` | Source row behind a match | (`source`, `source_file`, `source_row`) | Link method, recorded disagreements |
| `rankings` | Player and ranking date | | Rank, points |
| `points`, `charting_stats`, `score_states` | Point, chart category, captured score state | `match_id` plus sequence | Kept at their own grain |
| `bookmaker_odds` | Match and bookmaker | | Closing odds for winner and loser |
| `markets` | Polymarket contract | `market_id` | Event, contract type, line, outcomes to token ids, scheduled start, settlement, volume |
| `market_prices` | Token and minute | | Price. Stays partitioned by bucket and month. |
| `market_links` | Market | `market_id` | `match_id`, token-to-player mapping, method |
| `player_form` | Match, player and feature set | | Pre-match values only |
| `train_matches` | Match | View | Context, A and B form, differences, label |
| `train_markets` | Market and decision time | View | Price as of the decision time, both players' form as of their latest completed match, settlement |

### Merge order and rules

1. **Identity first.**
   * Seed players from the Sackmann ATP and WTA player files.
   * Learn other sources' ids from matches both sources contain: exact pair, then one-player anchor, repeated until no new ids appear.
   * Use name plus birth date as a second route.
   * Keep every spelling, and resolve namesakes by context, never silently.
2. **Editions.** Normalise Sackmann and TML ids, then attach the other sources' tournament names and keys.
3. **Matches.**
   * Sackmann is the base up to its end (25 May for main tours, 2 June 2026 for lower tiers).
   * TML is appended where neither linking pass finds a match, followed by a resolved-id pass (same player, week and round).
   * Field precedence: the result comes from the base source, with disagreements recorded. Statistics come from whichever source has them. The date comes from the most precise source, with `date_precision` recorded.
4. **Attach details:** odds, exact dates, charts and points.
5. **Attach markets.** Where no public result exists, a settled moneyline may create the match with `result_source = market`. Settlements at 0.5 are treated as walkovers.
6. **Compute `player_form` in one chronological pass.** Order by tournament week, then round order, then match number or scheduled time.
7. **Assemble the modelling tables as queries.**

### Time rules

* A pre-match feature for match M uses only matches ordered before M. Within an event, earlier rounds come first.
* At prediction time T, only matches completed before T count.
* An upcoming match is a `matches` row without a result, so training and prediction use the same feature function.

### Modelling tables

* **`train_matches`.** A and B are assigned by a deterministic hash of `match_id`, which is reproducible, keeps the label balanced and carries no information. Swap augmentation is an alternative.
* **`train_markets`.** A is the player of the priced token (Polymarket's first outcome), because the stored price history is for that token.
* **Features.** Differences for symmetric quantities, plus raw context: tier, surface, round, best of, date precision and statistics level.

### Engine

Keep Parquet as storage and query it with DuckDB, which provides SQL over Parquet folders, window functions and as-of joins. This is a new dependency for the owner to approve. pandas copes with the match-level tables at this size (the full scan runs in about 25 seconds); the 62 million Polymarket price rows are where a query engine matters.

## Relation to the public dump structure plan

The [structure plan](../public_data_dump/structure-plan.md) remains the base. This study keeps its entity list, the move from winner/loser to a symmetric modelling layout, `date_precision`, the statistics tier, per-row provenance, and a match key built from resolved player ids.

It changes the following:

* Linking is identity-first, with the one-player anchor and resolved-id passes. The measured need is the 9,331 matches that name-only matching duplicates.
* Player and edition ids are minted by the project, with source ids kept as aliases.
* `match_players` is a two-row facts table with no averages, replacing `match_player_stats`.
* There is an explicit feature layer computed as a running state.
* A/B assignment uses a hash for match history and the priced token for markets. The plan's higher-ranked-first rule remains an option.
* Polymarket settlements become a result source for the lower-tier gap after early June 2026.
* DuckDB is proposed as the engine.

## Open decisions for the owner

1. Whether to add `duckdb` to `environment.yml`.
2. Whether to use project-minted ids or Sackmann ids as the canonical player id.
3. How to assign A and B in the modelling tables.
4. Whether settlement-derived results may create match rows, and how they are flagged in modelling.
5. The first build's scope. The suggestion is singles, all tiers, from 2010, since features need the full history even when modelling covers less; doubles later.

## Limitations

* **Lower bounds.** Linking uses exact normalised names, so the rates are lower bounds.
* **Unexplained residue.** The 1,308 older TML-only matches, the 886 rows under two tournament ids and 497 same-tournament, same-round rows remain to be examined in cleaning.
* **Provisional canonical table.** It removes duplicates by an exact key only.
* **Polymarket parsing.** Moneyline names come from the question text, and doubles are excluded by the `/` and `&` separators.
* **Illustrative demo.** The features are examples, the Elo parameters are arbitrary, and the look-back cost is extrapolated from 300 timed rows on this machine.
* **Exact-day window.** Exact-day coverage was measured only for tournament weeks from January 2023 to July 2026.
* **Rights.** Terms are as recorded in the [dump report](../public_data_dump/README.md#limitations). A merged database inherits the strictest terms of its inputs, so per-row source attribution is kept.
