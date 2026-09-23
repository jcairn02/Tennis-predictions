# Target data structure for the cleaning and merge phase (proposal)

**Status: proposal, not a decision.** This is the structure the public data dump was organised to feed. It records the entities, keys, ordering rules and source mappings that the next phase (cleaning and merging into one database) should implement, and the defects that phase has to handle. Nothing here is built yet; the dump keeps every source verbatim so the choices below can still change.

Scope from the owner (22 Sep 2026): 2010 onward matters, with heavy emphasis on 2022–2026; as much in-match statistic as each source offers; lower tiers accepted with partial statistics.

## 1. Entities

| Entity | One row per | Fed by (dump branch / source) |
|---|---|---|
| `players` | canonical player | `players/` from Sackmann (ATP and WTA numeric ids, biography), Tennis My Life `ATP_Database` (ATP website codes, birthplace, backhand, coaches), Live Tennis API players (own ids plus a partial `sackmann_id` crosswalk), Open Tennis Data players |
| `player_ids` | (canonical player, source, source id or name form) | every source above plus name-only sources: Match Charting Project, tennis-data.co.uk (`Surname I.` form), Polymarket titles/outcomes |
| `tournaments` | tournament edition (tour, year, event) | Sackmann and TML `tourney_id`/`tourney_name`/`tourney_level`/`surface`, tennis-data.co.uk `ATP`/`WTA` number, `Tournament`, `Series`/`Tier`, `Court`, Open Tennis Data tournaments table, Live Tennis API `tournament_key`/`tier_key`, Polymarket `league` strings |
| `matches` | physical singles match | `matches/` from Sackmann (main, qualifying/Challenger, Futures, WTA qual/ITF), TML (ATP main, Challenger, ATP qualifying, WTA main, ongoing), tennis-data.co.uk results columns (inside `odds/`), Open Tennis Data completed (exact dates), Live Tennis API index (schedule, no result) |
| `matches_doubles` | physical doubles match | Sackmann ATP doubles 2010–2020 only; Slam point-by-point doubles/mixed files; Polymarket doubles markets (no public result source for current doubles) |
| `match_player_stats` | (match, player) | Sackmann/TML serve totals; Match Charting Project `stats/*` aggregates; Slam point-by-point per-point flags aggregated later |
| `points` | (match, sequence number) | MCP `points/` (shot codes), Slam `points` (per point with speed, rally, depth), Live Tennis API `points_sample` (timestamped score states, one month) |
| `rankings` | (ranking date, tour, player) | Sackmann rankings 2010s/2020s/current (to 8 Jun 2026); TML ATP rankings 2026-08-31 |
| `closing_odds` | (match, bookmaker) | tennis-data.co.uk odds columns, long format |
| `markets` | Polymarket contract | `odds/polymarket/market_index` (all contract types, tokens, lines) |
| `market_prices` | (token, timestamp) | `odds/polymarket/price_history/<bucket>/` (moneyline first-outcome token, minute prices) |
| `match_market_links` | (match, Polymarket event) | to be built in the merge; unmatched rows kept on both sides |

Player historical averages "prior to the date in question" are **not** an entity here. They are derived later from `matches` + `match_player_stats` with an as-of date, which is why the match table must carry a usable date and a date-precision flag.

## 2. The match row and the A/B ordering rule

Every match-level source stores rows as **winner / loser**. That layout leaks the label and cannot be the modelling layout. The dump keeps the source layout; the merge produces a symmetric layout:

```
match_key, tournament_edition_id, tour, tier, round, surface, indoor, best_of,
date, date_precision (day | tournament_week | scheduled_utc), start_time_utc (if known),
status (completed | retired | walkover | defaulted | abandoned | unknown), score_raw, sets_a, sets_b, games per set,
minutes,
player_a_id, player_b_id, rank_a, rank_b, points_a, points_b, seed_a, seed_b, entry_a, entry_b, age_a, age_b, hand_a, hand_b, ht_a, ht_b,
a_won (label), ab_rule (which ordering rule fired), a_is_higher_ranked, a_served_first (null unless point data exists),
stats_tier (0 none | 1 serve/return totals | 2 charted | 3 slam per-point), stats_source,
<per-player in-match stats, suffixed _a / _b>,
source_rows (JSON list of (source, source file, source row)) 
```

Recommended ordering rule, applied in this order and recorded in `ab_rule`:

1. **Higher-ranked player is A** (lower ranking number at the tournament date). Rank is present in Sackmann, TML and tennis-data.co.uk rows for most main-tour and Challenger matches, so this is the "common property" that exists in the widest set of sources.
2. If either rank is missing or the ranks are equal: **first server is A** when point-level data exists (MCP `Player1` always served first; Slam files carry `PointServer`; Live Tennis API states carry `server`).
3. Otherwise: **deterministic pseudo-random** from a hash of `match_key`, so the order is reproducible and carries no information.

Whatever rule is used, the label will be imbalanced (A wins more often under rule 1). Train with A/B swap augmentation or a symmetric model so the ordering itself is not a feature. Doubles rows use the same idea per team, with the team's players sorted by canonical id.

## 3. Keys and joins

* `match_key`: hash of (tour, tournament edition id, round, sorted canonical player ids). Source keys are kept as `source_rows`; Sackmann and TML `(tourney_id, match_num)` keys are known to repeat (TML ATP 2025 has 480 repeated keys from blank match numbers), so they are provenance, not identity.
* `tournament_edition_id`: built from a curated tournament crosswalk. The dump shows three id systems for the same events: Sackmann `2026-M020`-style ids, TML `2026-9900`/`2026-800` ids, tennis-data.co.uk running numbers plus names. Polymarket only has league strings such as `W50 Yecla` or `Hangzhou Open`.
* Player crosswalk: Sackmann WTA ids appear to be reused by TML WTA files (numeric, same magnitude); TML ATP uses ATP website codes (`S0AG`); Live Tennis API maps 25% of used players to Sackmann ids. Everything else is name matching with accents, initials and transliterations to resolve, preserving unmatched names.
* Dates: Sackmann and TML `tourney_date` is the tournament week (Monday); tennis-data.co.uk `Date` is the match day from 2003; Open Tennis Data `date` is a day-precision match date derived from tennis-data.co.uk and Wikimedia; Live Tennis API is scheduled UTC; Polymarket `gameStartTime`/`sport_date` is scheduled UTC. The merge must carry `date_precision` and prefer day precision when two sources agree on the match.
* Market joins: Polymarket titles give two names and a league; the audit's conservative name-plus-date join matched 2,460 events to Open Tennis Data rows. The merge should reuse that method against the wider match table and keep an explicit unmatched list on both sides.

## 4. In-match statistics by tier (what the dump actually holds)

| Tier | Match results | Serve/return totals | Charted shot data | Per-point sequences | Timestamped score states | Closing odds | Polymarket prices |
|---|---|---|---|---|---|---|---|
| Grand Slam main draw | Sackmann, TML, tennis-data, OTD | Sackmann/TML (near complete) | MCP (selected matches) | Slam point-by-point 2011–2024 (most matches) | Live Tennis API June 2026 sample | tennis-data | yes |
| Masters/WTA 1000, 500, 250, Finals | same | same | MCP (selected) | none | June 2026 sample | tennis-data | yes |
| Tour qualifying | Sackmann (qual files), TML ATP qualifying | partial | rare | none | June 2026 sample | none | yes |
| Challenger / WTA 125 | Sackmann, TML Challenger (ATP only) | partial to good (ATP Challenger) | rare | none | June 2026 sample | none | yes (inferred tier) |
| ITF / Futures | Sackmann Futures (ATP) and qual/ITF (WTA) to Jun 2026 only | sparse before 2025 | none | none | June 2026 sample | none | yes (largest market population) |
| Doubles | Sackmann to 2020; Slam doubles points 2018–2024 | team totals only | none | Slam doubles points | none | none | yes |

Lower tiers therefore enter the match table with `stats_tier` 0 or 1 and no odds other than Polymarket; that is expected and should be modelled explicitly rather than filtered away.

## 5. Cleaning-phase checklist (found while staging; not fixed here)

1. Tournament-type labels are inconsistent across years and sources: tennis-data.co.uk ATP uses `International`/`International Gold`/`Masters` before 2009 and `ATP250`/`ATP500`/`Masters 1000` after; WTA uses `Tier I–IV` (2007–2008), `Premier`/`International` (2009–2020) and `WTA1000`/`WTA500`/`WTA250` (2021+). The WTA 2021 workbook contains an Excel fill-down defect: 26 rows labelled `WTA251` … `WTA276` that are `WTA250` matches. Sackmann `tourney_level` codes differ by tour (`P`, `PM`, `I`, `50+H`, numeric ITF levels). A single tier taxonomy with a per-source mapping table is required.
2. Dates: tournament-week dates in Sackmann/TML must not be treated as match dates; Open Tennis Data or tennis-data.co.uk supply day precision for main-tour matches only.
3. Scores: `RET`, `W/O`, `DEF`, `ABD`, `Walkover`, `Played and unfinished`, `Awarded` and blank scores appear; tennis-data.co.uk uses a `Comment` column. Retirement/walkover status must be normalised before any label or settlement logic.
4. Identity defects already measured: TML ATP 2025 duplicate `(tourney_id, match_num)` keys; TML WTA 2026 one malformed row and 64 missing winner ids; MCP metadata files with short rows (kept with `_width_ok = short`); Sackmann lowercase `clay` and missing surfaces; Live Tennis API index without winners.
5. Serve statistics missingness varies by tier and year (for example ATP Futures 2024 has no serve stats at all; 2025 has them). `stats_tier` must be computed per row, not per source.
6. Odds validity: tennis-data.co.uk cells equal to 0 or 1.00 are not quotes; Pinnacle columns stop in January 2026; bookmaker columns change by year. Polymarket prices are the first outcome token only; the complement token is not fetched.
7. Polymarket tier buckets are inferred from league names by the tier-terrain study's classifier; `challenger_125_inferred` in particular is a residual bucket and should be re-derived from the tournament crosswalk once it exists.
8. Overlaps to reconcile rather than double count: Sackmann vs TML (same matches, different ids and corrections), tennis-data.co.uk vs Open Tennis Data (the latter cites the former), Sackmann inherited local copies vs the archive, TML season files vs ongoing files.

## 6. Rights reminder for the merged database

Sackmann and Match Charting Project data are CC BY-NC-SA 4.0; the Live Tennis API sample is CC BY-NC 4.0; Tennis My Life's rights notices conflict (MIT on the site, noncommercial in the repository); tennis-data.co.uk states no explicit licence; Polymarket API data is under Polymarket's terms. A merged database inherits the strictest applicable terms of its inputs. This is a constraint on later use, recorded here so the merge keeps per-row source attribution.
