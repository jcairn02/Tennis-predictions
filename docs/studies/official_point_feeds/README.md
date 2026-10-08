# Official point feeds

**Status: study, not a decision.** On 24 September 2026 the owner decided to collect the five public feeds in rows 2–6 of the [granular data leads](../../research/granular-data-leads/README.md) regardless of the sites' no-scraping terms, for non-commercial research, within the limits in the [decision record](../../decisions/2026-09-24-official-point-feeds.md). The feeds are collected one source per session, and each session reports here. On 25 September the owner extended the decision to TDI's Tennis Results site, row 9 ([decision record](../../decisions/2026-09-25-tdi-tennis-results.md)).

| Source | Row | Status |
|---|---|---|
| Australian Open 2026 match centre | 4 | Collected 24 Sep 2026 ([below](#australian-open-2026-match-centre)) |
| Wimbledon scoring feeds, 2019 and 2021–2026 | 2 | Collected 24–25 Sep 2026: all 4,228 matches of the six events, 2,445 of them new to the dump ([below](#wimbledon-scoring-feeds-ibm-slamtracker)) |
| US Open scoring feeds, 2022–2026 | 3 | Collected 24–25 Sep 2026: all 3,020 matches of the six events, 2,445 with points, 1,313 of them new to the dump ([below](#us-open-scoring-feeds-ibm-slamtracker)) |
| IBM extras at the US Open and Wimbledon | 5 | Wimbledon: collected with its feeds, likelihood-to-win 2025–26 and TennisViz 2024–25 for the singles main draws ([below](#wimbledons-ibm-extras)). US Open: collected with its feeds, likelihood-to-win and pre-match likelihood 2025–26, limb tracking and key moments 2026, distance run 2022–26 ([below](#the-us-opens-ibm-extras)) |
| WTA official API | 6 | Coverage measured 24 Sep 2026. Batch B1 (the umpire's point log, every draw, 2020–2026) done 25 Sep: 33,301 of 33,304 matches' logs. B2 (2019) done 26 Sep: the log holds points from 1 April 2019. B3–B9 (every other endpoint) approved 29 Sep and run one after the other from 17:20 UTC that day to 05:13 UTC on 3 Oct, every batch done: B3 (box scores, 2019–2026) done 30 Sep, 36,825 of 36,832 matches with one; B4 (advanced statistics, 2025–26) done 1 Oct, 11,902 of 12,068; B5 (win probability, 2026) done 1 Oct, 5,097 of 5,727; B6 (momentum, 2025) done 1 Oct after a PC restart, 5,896 of 6,341; B7 (advanced statistics, 2021–24) done 2 Oct after another, 19,518 of 19,581; B8 (point-by-point, 2022–26) done 3 Oct, 20,841 of 26,507; B9 (Slam box scores, 2024–26) done 3 Oct, all 3,020 listed. No error is left; one 2026 match finished after the last top-up and waits for the next 2026 refresh ([below](#wta-official-api)) |
| TDI Tennis Results (ATP Tour and Challenger) | 9 | Collected 25 Sep 2026: all 5,202 matches its listing held (23 Jun – 25 Sep 2026) and the 634 older matches whose ids the Wayback Machine kept, 795,162 points. Forward capture weekly: the last run, 29 Sep, added the 260 matches completed since, for 6,096 matches and 831,206 points ([below](#tdi-tennis-results-resultstennisdatacom)) |

## Layout and rules shared by every source

| Item | Where |
|---|---|
| Adapters | `src/ingest/point_sources/<source>.py`; the shared client in `feeds.py`, the cached fetch and staging in `common.py` |
| Verbatim responses, with a receipt per fetch | `data/raw/point_sources/<source>/` (gitignored) |
| Staged tables (string Parquet) | `data/dump/points/<source>/` (gitignored) |
| Run summaries (`<source>_summary.json`; one line per run in `runs.jsonl`) and checks | [data/studies/official_point_feeds/](../../../data/studies/official_point_feeds/) |
| Checking code | `src/eda/official_point_feeds/` |
| Tests | `test/official_point_feeds/` (offline, on fixtures cut from real payloads) |

**How the feeds are read** (`feeds.FeedClient`, on the `curl_cffi` client of the SofaScore and TennisLive adapters):
* **Pace.** One request at a time, 2 s apart plus up to 1 s of random jitter, within a `--max-requests` budget.
* **Cache.** Every answer is cached with a receipt (URL, time, status, bytes, SHA-256), so nothing is fetched twice. A "not found" answer is kept as a terminal *absent* record.
* **Stops.** The run stops at once, without a retry, on:
  * any HTTP 403, unless it is a source's own way of saying "not found";
  * an HTTP 429;
  * a bot challenge;
  * a redirect, which is never followed;
  * a connection reset.
* **Retries.** Server errors and timeouts are retried three times with a growing pause, then recorded as errors. Five fetches in a row without a document also stop the run.

No login, token, CAPTCHA or decryption is used, and no redirect or 403 is worked around.

**Shared code changes.** Two changes to `common.py`, both inert unless a caller uses them:
* `write_summary` takes a `root`, so a study other than point_shot_sources can keep its run summaries.
* `fetch` takes an `absent` function, so a site's non-404 "not found" answer is cached like a 404.

The point_shot_sources tests (27) pass before and after.

Two more, made for the WTA's day-long runs, change nothing for a run that is not interrupted:
* `common.fetch` writes each document to a `.part` file and then renames it into place, so an interrupted write never leaves a truncated file where a good one was (a refreshed match list, say).
* `public_dump.common.Receipts` skips a receipt line cut short by an interrupted write, or being written while another process reads, instead of failing to load; that fetch simply has no receipt and is done again. The next receipt starts on a fresh line. It also counts such lines, in `unreadable_lines`.

The whole test suite passes after both.

## Australian Open 2026 match centre

**All 604 matches of the six 2026 events are accounted for:**
* 600 have a point-by-point record, 96,414 points in all;
* the other 4 are walkovers, where no point was played;
* none is absent, and no request was refused.

**Every point carries:**
* a clock time;
* who won it;
* the server;
* how it ended (an ace, a double fault, a service winner, a winner, a forced error or an unforced error), with the stroke side for winners and errors.

**Only 21 points lack the detail.** The per-set statistics add serve speeds, and winners and errors by shot family.

**The records check out with six exceptions:**
* **Commentary:** every sentence maps to a known form.
* **Aces and double faults:** they match the key statistics in 1,570 of 1,571 sets.
* **Score replay:** replaying the point winners reproduces the final score of 597 of 600 matches, retirements included.
* **The exceptions:** all six disagreements trace to faults in the feed itself, listed [below](#six-matches-with-record-faults).

**Clock times:**
* **Consistent:** every point has one, and the first comes a median 0.9 minutes after the listed start.
* **But entry times, not play times:** 0.4% of points are stamped later than the point after them, some by hours.

**Wayback captures:** 40 main-event matches of 2022–2025, found in the Wayback Machine, are added as well.

**None of this was in the dump.** It holds the Australian Open only to 2021. The API will probably stop serving 2026 when the 2027 draws are published in January 2027, and no other source or seller holds these records ([access routes](../../research/granular-data-leads/access-routes.md)).

| Item | Where |
|---|---|
| Adapter | `src/ingest/point_sources/ausopen.py` |
| Raw documents | `data/raw/point_sources/ausopen/`: `draws/`, `match-centre/<MID>.json`, `wayback/`, `_receipts.jsonl` |
| Staged tables | `data/dump/points/ausopen/`: `matches.parquet` (703 rows), `points.parquet` (108,667), `set_statistics.parquet` (188,632) |
| Run summary | [ausopen_summary.json](../../../data/studies/official_point_feeds/ausopen_summary.json); every run in [runs.jsonl](../../../data/studies/official_point_feeds/runs.jsonl) |
| Checks | `src/eda/official_point_feeds/verify_ausopen.py`: [ausopen_verification.json](../../../data/studies/official_point_feeds/ausopen_verification.json) (totals), [ausopen_accounting.csv](../../../data/studies/official_point_feeds/ausopen_accounting.csv) (every match and capture), [ausopen_commentary_map.csv](../../../data/studies/official_point_feeds/ausopen_commentary_map.csv), [ausopen_checks.csv](../../../data/studies/official_point_feeds/ausopen_checks.csv) (per match), [ausopen_mismatches.csv](../../../data/studies/official_point_feeds/ausopen_mismatches.csv) |
| Tests | `test/official_point_feeds/test_ausopen.py` (21 tests; fixtures cut from MD106, MQ122, MS406 and the women's doubles draw) |

### What was fetched

Tennis Australia's scores API (`prod-scores-api.ausopen.com`, an AWS API Gateway) serves only the current edition. Two endpoints were read, with no login or key:
* `/event/<nid>/draws` for the six 2026 events (the event ids are in the [Slam notes](../../../data/studies/granular_data_leads/research_notes/B_grand_slams.md), lead 5);
* `/match-centre/<MID>` for every match the draws list.

The gateway answers an unknown path with HTTP 403 `{"message": "Missing Authentication Token"}`. The adapter records that answer as an absent document, and any other 403 stops the run. None came: all 610 requests to the API were answered with HTTP 200.

| Event | In the draw | With points | Without (walkover) | Retired | Points | Points per match |
|---|---:|---:|---:|---:|---:|---:|
| Men's singles (MS) | 127 | 126 | 1 (MS406) | 6 | 28,026 | 222 |
| Women's singles (WS) | 127 | 126 | 1 (WS315) | 2 | 17,426 | 138 |
| Men's qualifying (MQ) | 112 | 112 | – | 3 | 16,237 | 145 |
| Women's qualifying (WQ) | 112 | 112 | – | 4 | 16,577 | 148 |
| Men's doubles (MD) | 63 | 63 | – | 1 | 9,231 | 147 |
| Women's doubles (WD) | 63 | 61 | 2 (WD205, WD301) | 1 | 8,917 | 146 |
| **All** | **604** | **600** | **4** | **17** | **96,414** | |

Play ran from 12 January (qualifying) to 1 February 2026. The draws give every player's ATP or WTA id (all 1,460 player slots), so the matches can be joined to the rest of the dump.

### What a record holds

**The commentary, newest first, one entry per point:**
* **Id:** `<MID>-<set>-<game>-<point>`. Point `000` of each game is a *serve line*, such as "F. Martin is serving game 13", which has no timestamp.
* **Type:** `point`, or `game`, `set` or `match` for the point that ends one.
* **`winner`:** 1 for the first team listed, 2 for the second.
* **`timestamp` and `duration`:** Unix seconds, and elapsed match time in h:mm.
* **`score`:** the point score after the point, server first ("15 - 40", "AD - 40", tiebreak "1 - 3"), and "Game" on a game-ending point.
* **`games_score`:** the set's games after the point, server first (99.7% of entries), except on the match-ending entry, where the first team comes first (579 of 584). The readings are counted in the verification file.
* **The sentence** names the side that hit the last shot and what it was. Examples: "C. Alcaraz wins the point with a Forehand Winner", "Mannarino/Martin lose the point with a Backhand Forced Error". The detail is one of Ace, Double Fault or Service Winner, or rarely just "wins the point". Singles use the player's short name, doubles the two surnames.

**The statistics, for each set and for the match ("All"), for each side:**
* *Key:* aces, double faults, first serves in, points won behind the first and second serve, break points, net points, receiving points, winners, return winners, unforced errors, return unforced errors, total points, fastest serve, and first- and second-serve average speeds.
* *Serve:* aces, and service and return points played and won, for first serves, second serves and in total.
* *Rally:* forehand and backhand winners and unforced errors, by shot family: groundstroke, volley, approach, passing shot, lob, overhead, drop shot.

### How it was staged

All three tables are strings, with the dump's provenance columns and each row's source file, SHA-256 and retrieval time.
* **`matches.parquet`:** one row per match of the draws, plus one per Wayback capture.
  * *Descriptive fields:* event, round, date, court, status, teams with players' names, ids, ATP/WTA ids and seeds, and set scores with tiebreak points.
  * *Standing:* `record` (points, empty or absent) and `record_reason`.
* **`points.parquet`:** one row per point, with the verbatim fields and the parsed sentence.
  * `outcome`: ace, double_fault, service_winner, winner, forced_error, unforced_error or unspecified.
  * `stroke_side`: forehand or backhand.
  * `subject_team`: the side that hit the shot described. That is the point's winner for "wins" and its loser for "loses".
  * The server:
    * `game_server_team` and `game_server_player_id` come from the serve line;
    * `point_server_team` is the same outside tiebreaks, and inside them follows the rotation (the first server once, then two points each).
* **`set_statistics.parquet`:** one row per statistic, block and set. Each side has a primary value, a secondary value ("18/26", "136 mph") and a unit.

### Checks

`verify_ausopen.py` reads the staged tables and the raw documents. Figures here are for 2026 unless marked.

| Check | Result |
|---|---|
| Accounting | 604 of 604 matches: 600 with points, 4 walkovers without. No match is absent, failed or unfetched |
| Commentary map | All 125,724 sentences (2026 and the Wayback captures, serve lines included) fit 21 forms. **None is unmapped**, and no verb contradicts its outcome |
| Names | Every sentence's subject names the side its verb and winner imply (108,667 of 108,667, Wayback included). This needs case-insensitive matching and a hyphenated surname cut at its hyphen: the commentary calls one player "V. Tomova" although her record says "V. Tomova-Traycheva" |
| Aces and double faults against the key statistics | 1,570 of 1,571 sets and 599 of 600 match totals agree. The exception is MS159, set 1: two extra "double faults" (below) |
| Aces and double faults against the server | 9,734 of 9,735 fall on a point served by the side that hit them. The exception is MD121 (below) |
| Score replay | The point winners alone, replayed under the Slam's rules, reproduce the listed final score of **597 of 600 matches**, including all 17 retirements. Every game ends where the commentary types an end in 597. The exceptions are MS159, MQ203 and MD109 (below) |
| Point score text | 96,351 of 96,414 scores match the replayed state, written server first. The 53 that differ are in the matches below; 10 could not be checked because their game has no serve line |
| Servers | Named for 15,099 of 15,101 games. WS403 and MQ206 have no serve line for game 1. Service alternates correctly except in WQ159 and MD121 |
| Clock times | See below |

The replay rules: advantage games, sets to six with a tiebreak to 7 at 6-6, and a tiebreak to 10 at 6-6 in the deciding set. Men's singles (format A) are best of five, the other events (B, C) best of three.

#### Six matches with record faults

Each was read in the raw document. The verification now labels these faults itself (the `extra_game_end_entries`, `serve_line_inside_game` and `serve_line_contradicted` rows of the mismatch file).

| Match | What the commentary holds | Effect |
|---|---|---|
| MS159 | Two extra entries after Baez's hold in set 1, game 8, both "S. Baez loses the point with a Double Fault", typed as the game's end; one is stamped earlier than the point before it | The replay gains a game; set 1 double faults exceed the statistics by 2 |
| MQ203 | A second entry typed as the end of set 2, game 2 | The replay gains a game (4-6 against 3-6) |
| WD105 | Three entries typed "match" on the last point, one won by the losing side, all with the same timestamp | The final score is reproduced; 2 entries follow the match's end |
| MD109 | The match point is an entry typed "serve" inside game 9 of set 2 ("M. Pavic is serving game 10", games 6-3) | The points stop at 5-3, 40-15 |
| WQ159, MD121 | The serve line of game 1 names the receiver; the scores and, in MD121, an ace show that the other side served | Game 1's server is wrong in the staged table; the replayed score is unaffected |

The first three look like superseded entries left in the feed. Staging keeps them all verbatim; a consumer should drop a duplicate game-ending entry, or take the score from the draw.

#### Clock times

* **Coverage:** every point has one.
* **Pace:** points run a median 36 s apart, and the first comes a median 0.9 minutes after the listed start time.
* **Out of order:** 388 points (0.40%) in 218 matches are stamped later than the point after them.
  * The median step back is 38 s.
  * 52 steps exceed 10 minutes, 32 exceed an hour, and the longest is 25.6 hours.
  * In MD121, game 1's points carry times about 2.7 hours after game 2's.

The stamp is therefore when a point was entered or last corrected, not when it was played. For an exact join to market prices, the few points out of order need to be dropped or bounded by their neighbours.

### Gaps

* **Matches:**
  * the 4 walkovers have no points;
  * the 17 retirements end where play stopped (in WS114 the last game has a serve line but no point);
  * the six faulty matches above.
* **Per point, the feed has none of:**
  * first or second serve;
  * rally length;
  * serve speed or placement;
  * the stroke family (volley, drop shot and so on), which exists only as per-set totals;
  * in doubles, which partner hit the last shot.
* **Missing detail:** 21 points in 5 matches say only "wins the point", 12 of them in MD121.
* **Scope:**
  * only the six events were collected; mixed doubles, junior, wheelchair and legends events were not, and their event ids were not looked up;
  * earlier editions exist only as the Wayback captures below.

### Receipts

All on 24 September 2026, 18:43–19:26 UTC. [ausopen_verification.json](../../../data/studies/official_point_feeds/ausopen_verification.json) (`receipts`) has the breakdown.

| Kind | Documents | Answers | Bytes |
|---|---:|---|---:|
| Draws | 6 | 6 × 200 | 2.3 MB |
| Match centres | 604 | 604 × 200 | 51.6 MB |
| Wayback capture list | 1 | 200 | 14 kB |
| Wayback captures | 99 | 87 × 200, 9 × 404, 3 redirects recorded and not followed | 6.8 MB |

**Requests.** 711 requests brought 710 documents:
* **The pilot:** 11 requests (the six draws and five matches).
* **The main run:** 599 requests in 25 minutes, 2 s apart plus jitter, with no retry.
* **Two Wayback runs:** 52 and 49 requests, 4 s apart plus jitter.
* **The one repeat:** the capture whose redirect stopped the first Wayback run was asked again in the second.

No request was refused, rate-limited, challenged or reset, and nothing was retried.

### Wayback captures of 2022–2025 (and 2020–21, 2026)

The Wayback Machine's capture list for `prod-scores-api.ausopen.com/match-centre/` (read 24 Sep 2026) holds 99 distinct captures from 2020 to 2026, more than the ≈65 of 2022–25 the Slam notes counted. All 99 were requested.
* **73 hold points** (12,253 points): 54 finished, 15 mid-match, 3 retired and 1 suspended.
  * By year, in distinct matches: 2020: 1, 2021: 6, 2022: 11, 2023: 13, 2024: 15, 2025: 8, 2026: 18.
  * **2022–2025 main events: 40 distinct matches, 29 captured finished**, mostly men's singles.
  * Side events: six Legends' Doubles matches of 2022, a 2025 wheelchair match, and 2026 junior and legends matches.
* **10 hold none:** 7 scheduled, 1 warming up, 1 walkover, 1 without a status.
* **16 are absent:**
  * 4 captured the API's own "match id not found";
  * 9 answered 404;
  * 3 answered with a redirect to another capture of the same URL.
* **The redirects.**
  * *What happened:* the first redirect stopped the run, as the rules require. The redirect was to another capture of the same URL on web.archive.org, which is the archive's "closest capture" behaviour. It was not to robots.txt or another site.
  * *The change:* the adapter now records such a redirect as an absence naming the target, without following it; any other redirect still stops the run. The second run then finished the list.
  * *The targets:* for MS403 of 2021 the target is itself a listed capture, fetched on its own turn.
* **Checks.**
  * Aces and double faults agree with the statistics in 210 of 210 sets.
  * The replay reproduces the listed score of all 73 captures.
  * That required the legends' and junior doubles format (`D`): no-ad games and a match tiebreak to 10 for the third set. The codes are undocumented and this reading is inferred from the records.
  * Two captures type a game's end as "set".
* **2026 captures against today's documents.** The 14 captures of 2026 main-event matches, taken between 20 January and 2 June 2026, still match what the API serves: 13 are identical and 1, taken mid-match, is contained in today's document. Those records have not been edited since they were captured.

### Rerunning

```
./python.sh -m src.ingest.point_sources.ausopen                  # draws and every match; cached documents are not asked for again
./python.sh -m src.ingest.point_sources.ausopen --wayback        # also the Wayback captures
./python.sh -m src.ingest.point_sources.ausopen --stage-only     # rebuild the Parquet tables from the raw files, no HTTP
./python.sh src/eda/official_point_feeds/verify_ausopen.py       # the checks
./python.sh -m pytest test/official_point_feeds/test_ausopen.py -q
```

`--matches`, `--limit` and `--max-requests` bound a run. The raw documents under `data/raw/point_sources/ausopen/` are the only copy once the API moves on to 2027. They are gitignored (60 MB), so a backup outside the working tree is worth considering.

## Older editions in the Wayback Machine (all feeds)

On 24 September the owner asked for a search of the Wayback Machine for more of these feeds' point data from older matches and years. `src/eda/official_point_feeds/wayback_survey.py` asked the Wayback's capture index (the CDX API) for every archived copy of each feed's point-data URLs. Only the index was downloaded: 11 requests, 15 MB, cached under `data/raw/point_sources/wayback_cdx/`. Results are in [wayback_survey.json](../../../data/studies/official_point_feeds/wayback_survey.json) (counts by URL family and year) and [wayback_point_data.csv](../../../data/studies/official_point_feeds/wayback_point_data.csv) (every capture of a point-data URL, marked fetched or not).

**There is little more to have.** These are the point-data captures of editions the live feeds no longer serve:

| Feed | Editions | Captures | Held now |
|---|---|---|---|
| Australian Open match centre | 2020–2025 | 79 | All, fetched earlier the same day ([above](#wayback-captures-of-20222025-and-202021-2026)) |
| Australian Open IBM-era SlamTracker histories | 2017 | 3 | Fetched, raw only |
| Australian Open 2019 "manhattan" API | 2019 | 3 | Fetched, raw only |
| US Open SlamTracker histories | 2016–2019, 2021 | 25 (21 matches) | Not fetched: outside the decision's US Open range (2022–2026), left for the owner ([US Open](#gaps-and-limits-1)) |
| Wimbledon SlamTracker histories | before 2019 | none | – |
| WTA point-by-point | before 2022 | none | – |

A capture's edition is the year in its URL. Where the URL has none, it is the capture's year, or the year before when the capture predates that year's event.

**Australian Open:**
* **The match pages hold no data.**
  * The archive has 5,342 captures of `ausopen.com/match/...` pages, covering 2,369 distinct matches of 2019–2025.
  * The captured page of the 2023 final loads its data from the API when viewed (`dataUrl: .../match-centre/MS701`) and holds none itself.
  * So the archive has only the API answers it happened to record, and all 99 are held.
* **The 2019 "manhattan" API was the richest AO feed.** Each point carries:
  * serve number (first or second);
  * rally length, serve speed and a timestamp;
  * the game score and how the point ended.

  It cannot be read now:
  * the 2023 match page shows the feature switched off (`manhattan_active: false`);
  * its host now resolves to 192.0.2.1, an address reserved for documentation, and three probe requests found no server.

  The archive holds three of its documents: the 2019 men's final and two junior girls' matches.
* **The IBM-era histories** are three 2017 main-draw singles matches (1315, 1401, 2401), which the dump already holds through Sackmann's archive.
* **Where the fetched items are.** The six items above and the sampled page are under `data/raw/point_sources/ausopen/wayback_extra/` and `wayback_pages/`. They are in other formats and are not staged.
* **The archived draws, fetched on the owner's go-ahead the same evening.** They list every match of an event, and its score once played, but hold no points.
  * *The fetch:* the index lists 101 distinct copies of event draws. The seven copies of the four 2026 main events (held live) were left out, and the other 94 requested: 72 were saved, 16 answered 404, and 6 redirected to another copy (recorded, not followed).
  * *Staged:* `archived_draws.parquet`, 2,387 matches. Each event is taken from its most complete copy, and each match is linked to its Wayback captures with points.
  * *What survives by year:*
    * all six main events are archived complete only for 2025;
    * 2021, 2023 and 2024 have only the men's singles;
    * 2022 has the men's singles and doubles and the women's singles;
    * 2020 has both singles;
    * the 2019 copies predate play.

  Every edition's six main events hold 604 matches (127, 127, 112, 112, 63 and 63, as the complete 2025 copies confirm), so each year's share is measured against 604:

  | Edition | Main-event matches with archived points | Of them captured finished |
  |---|---:|---:|
  | 2019 | 0 | 0 |
  | 2020 | 1 (0.2%) | 1 |
  | 2021 | 6 (1.0%) | 4 |
  | 2022 | 5 (0.8%) | 5 |
  | 2023 | 13 (2.1%) | 9 |
  | 2024 | 15 (2.5%) | 9 |
  | 2025 | 7 (1.2%) | 6 |
  | **2019–2025** | **47 of 4,228 (1.1%)** | **34** |

  The per-event figures, with each draw copy's completeness, are in [ausopen_wayback_coverage.csv](../../../data/studies/official_point_feeds/ausopen_wayback_coverage.csv); the totals are under `archived_editions` in the verification file. The 47 captured matches are singles above all (29 men's, 14 women's) and spread over every round, 11 of them first-round matches.
  * *A side benefit:* the complete copies give every match and score of events the dump may lack at match level. These are 2025 qualifying and doubles, the 2022 and 2025 mixed doubles, the 2023 junior boys' doubles and the 2021 wheelchair events. The 2019 and 2022 qualifying copies stop before their last matches.
  * *Requests:* 95 (the index and the 94 copies), 22:31–22:39 UTC, none refused.
  * *A staging fault:* the first staging stopped on the empty places of later rounds in draws copied before they were played. The run's line in `runs.jsonl` was lost with it; the receipts hold the fetch. The adapter now reads such places and records a staging failure in its summary instead of losing the run.

**US Open.**
* *What exists:* 25 captures of point histories for 21 matches of 2016–2019 and 2021, mostly late rounds.
* *What they add:* by the held archive's coverage, 20 of the 21 fall in editions and events the dump already holds at point level. They would add clock times and the stroke sentence where the old files carry them.
* *Not fetched here,* because the US Open is another session's source. The URLs are in `wayback_point_data.csv`.

**Wimbledon.** No archived point history from before 2019. The archive host already serves 2019 and 2021–2025.

**WTA.** No archived point-by-point documents.

**Requests for the search.** 11 to the index, 7 for archived documents (the 2023 page and the six items above), and 3 to the dead manhattan host. None was refused.

## Wimbledon scoring feeds (IBM SlamTracker)

**All 4,228 matches of the six events (MS, LS, QS, RS, MD, LD) of 2019 and 2021–2026 are accounted for:**
* 4,203 have a point history, 709,664 points in all;
* the other 25 are walkovers, where no point was played;
* no request was refused, rate-limited, challenged or reset, and nothing was retried.

**2,445 of the matches with points are new to the dump** (390,319 points), exactly the research estimate:
* qualifying of every year: 1,119;
* the 2024 doubles: 124;
* every event of 2025: 601;
* every event of 2026: 601.

**The other 1,758 were in the dump already, from Sackmann's archive. 1,757 of them match his copy point for point** (the number of points and the winner of every point). His copy of the exception, the 2022 ladies' doubles final, stops at point 58 of 92. For these matches the feed adds what his copy lacks.

**Every point carries:**
* its winner, server, serve number and score;
* a clock time at its start and its end (`EpochTimeStart`, `EpochTimeEnd`, Unix seconds);
* a sentence naming the stroke and the outcome: an ace, a double fault, a service winner, or a forehand or backhand (volley, smash) winner, forced error or unforced error. **It is the only per-point record of forced errors:** 237,883 points end in one.

Serve speed, rally count, serve and return placement, kick height and distance run are filled on the main draws, and on qualifying from 2025 (table [below](#what-a-record-holds-1)).

**Three things to know before using it:**
* **Doubles sentences mostly name no shot** ("S. Hsieh/J. Ostapenko wins the point"). A stroke and outcome are given for 43% of men's and 32% of women's doubles points, against 99.9% in singles.
* **`EpochTimeEnd` is the more reliable clock, with exceptions.**
  * `EpochTimeStart` sometimes records when a point was keyed in late.
  * In 28 matches both times jump by a spurious day partway through.
  * In two 2026 matches `EpochTimeEnd` is not a Unix time for part of the match.

  All are listed [below](#clock-times-1).
* **9 histories stop before the match ended.** Six of them are 2021 main-draw singles, and Sackmann's copies stop at the same point.

**IBM extras:**
* *Likelihood-to-win after every point:* 508 files, for the singles main draws of 2025 and 2026. Four of the 2025 files were written after the event.
* *TennisViz metrics per set:* 508 files, for the singles main draws of 2024 and 2025.
* *Elsewhere:* a probe found neither in doubles or qualifying.

| Item | Where |
|---|---|
| Adapter | `src/ingest/point_sources/slamtracker.py`, host-agnostic and shared with the US Open; Wimbledon's settings are in `wimbledon.py` |
| Raw documents | `data/raw/point_sources/wimbledon/<year>/`: `draws/`, `days/` (2026), `history/`, `stats/`, `livel2w/`, `tz/`, all gzipped; `_receipts.jsonl`. 93 MB on disk (1.29 GB of JSON) |
| Staged tables | `data/dump/points/wimbledon/`: `matches` (4,228 rows), `points` (718,385 rows: every history row, marker rows included), `statistics` (3,783,754 rows, long form), `livel2w` (96,083 rows), `tz` (53,324 rows, path and value). 50 MB |
| Run summary | [wimbledon_summary.json](../../../data/studies/official_point_feeds/wimbledon_summary.json) (the last run, a restage, with receipts counted by feed, year and outcome); every run in [runs.jsonl](../../../data/studies/official_point_feeds/runs.jsonl) |
| Checks | `src/eda/official_point_feeds/slamtracker_checks.py --site wimbledon`: [wimbledon_checks.json](../../../data/studies/official_point_feeds/wimbledon_checks.json) (totals and lists), [coverage](../../../data/studies/official_point_feeds/wimbledon_coverage.csv), [Sackmann](../../../data/studies/official_point_feeds/wimbledon_sackmann.csv), [sentences](../../../data/studies/official_point_feeds/wimbledon_sentences.csv), [epoch problems](../../../data/studies/official_point_feeds/wimbledon_epoch_problems.csv), [result problems](../../../data/studies/official_point_feeds/wimbledon_result_problems.csv), [field fill](../../../data/studies/official_point_feeds/wimbledon_field_fill.csv) |
| Tests | `test/official_point_feeds/test_slamtracker.py` (22 tests; fixtures `wimbledon_*` cut from 2025 MS 1101 and 1107, 2019 MD 3101, 2019 MS 1101 and the 2026 day lists) |

### What was fetched

| Years | Host | Notes |
|---|---|---|
| 2019, 2021–2025 | `https://2025.wimbledon.com` (the archive host) | Its robots.txt is `Disallow: /` for every agent. It was read on the owner's instruction, at the decision's pace. `www` answers 403 for these years and was not asked |
| 2026 | `https://www.wimbledon.com` | The MS and LS draw files redirect automated clients to robots.txt (seen by the research pass). They are listed as blocked in the settings and were never requested. Those two events were listed from the completed-match days instead: `completed_matches/eventDays.json`, then `days/day_<tournDay>.json` for the 18 days of play (qualifying days 1–4, the Championships' days 8–21) |

**Paths.** The draws are `/en_GB/scores/feeds/<year>/draws/<EV>.json`. For every match listed:
* `slamtracker/history/<id>C.json`, the point history;
* `matches/complete/<id>.json`, the match statistics.

The extras are under `/clouddata/`: `livel2w/<year>/<id>C.json` and `tz/<year>/<id>.json`.

**Not-found answers.** A missing `/clouddata/` file answers HTTP 302 to `/notfound` (absolute URL). The client does not follow it and records it as absent. A missing feed file answers 404.

**Order.** The matches not in Sackmann's archive came first, newest year first, in case the archive host disappeared mid-run. The held main draws came last, and 2026 followed the archive host.

| Year | Draw matches | With points | Walkovers | New to the dump | Points | Likelihood-to-win | TennisViz |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 604 | 602 | 2 | 224 (qualifying) | 104,862 | – | – |
| 2021 | 604 | 598 | 6 | 224 (qualifying) | 99,810 | – | – |
| 2022 | 604 | 600 | 4 | 223 (qualifying) | 103,771 | – | – |
| 2023 | 604 | 601 | 3 | 224 (qualifying) | 99,211 | – | – |
| 2024 | 604 | 600 | 4 | 348 (qualifying, doubles) | 99,723 | – | 254 |
| 2025 | 604 | 601 | 3 | 601 (all) | 99,972 | 254 (+1 replay, QS 11101) | 254 |
| 2026 | 604 | 601 | 3 | 601 (all) | 102,315 | 254 | – |
| **All** | **4,228** | **4,203** | **25** | **2,445** | **709,664** | **509** | **508** |

Each event's draw holds 127 (MS, LS), 112 (QS, RS) or 63 (MD, LD) matches in every year. 2026 MS and LS reach 127 each from the day files. Per event and year, with every feed's outcomes, see [wimbledon_coverage.csv](../../../data/studies/official_point_feeds/wimbledon_coverage.csv).

### What a record holds

**The point history.**
* *Structure:* a list of flat records, all values strings. Two marker rows come first (`PointNumber` 0X "Players arrive on court." and 0Y "Players warming up.", epochs 0), then one row per point. Further markers carry a letter after the number of the point before them:
  * "Match suspended." (`<n>D`, 37 rows);
  * "Players arrive on court." or "Players warming up." after a break (`<n>X`, `<n>Y`, 238 rows, most in the 2026 doubles).

  A point is a row whose `PointNumber` is all digits, and every check here counts only those.
* *Fields:* 52 in 2019–2022, mostly 52 in 2023 (some 54), 57 from 2024; 2024 added `CourtIndicator`, `TeamOrientStart`, `TeamOrientEnd`, `P1SetsWon` and `P2SetsWon`. The main ones:
  * `PointNumber`, `SetNo`, `GameNo`, `PointServer`, `PointWinner`;
  * `ServeNumber` (0 on a double fault), `ServeIndicator`;
  * `P1Score`/`P2Score` and `P1GamesWon`/`P2GamesWon` after the point;
  * `EpochTimeStart`/`EpochTimeEnd`, and `ElapsedTime` (derived from the start time);
  * `Sentence`;
  * flags that hold the player number (`Ace`, `Winner`, `DoubleFault`, `UnforcedError`, `BreakPoint`…);
  * `Speed_KMH`/`MPH`, `RallyCount`, `ServeWidth`, `ServeDepth`, `ReturnDepth`;
  * `KickHeight` ("1.3,4.3", metres and feet [inference]), `P1/P2DistanceRun` (metres and feet);
  * `Court` (D/A), `ChallengeWon`, momentum, `Stage`.
* *The side-level flags are unreliable:* `SetWinner` and `MatchWinner` are often unset on the deciding point before 2024 (2021 MS 1113), and a few points carry a stray one (2025 MS 1201). Take results from the point winners (below).

**The sentence.** "<player or team> <situation> with a(n) <shot>":
* *The situation* is one of "wins" or "loses" the point, game, break, set or match; "saves" or "wins" the break point; or "fails to convert the break point".
* *The shot* is "<stroke> winner", "<stroke> forced error" or "<stroke> unforced error", or one of "ace", "double fault", "service winner".
* *Strokes:* forehand, backhand, forehand or backhand volley, forehand or backhand smash.
* *The player named* is the one who hit the last shot, and the verb says whether that side won the point.
* *2026 exception:* 275 sentences say "X wins the point with a forehand forced error" (or unforced error): the verb still names the point's winner, so the error must be the opponent's [inference].

| Stroke | Winner | Forced error | Unforced error |
|---|---:|---:|---:|
| Forehand | 68,734 | 117,471 | 89,450 |
| Backhand | 37,323 | 112,314 | 66,750 |
| Forehand volley | 15,487 | 3,439 | 2,937 |
| Backhand volley | 10,664 | 4,219 | 2,507 |
| Forehand smash | 7,285 | 334 | 866 |
| Backhand smash | 155 | 106 | 21 |

Serve outcomes: 44,582 aces, 29,944 double faults, 9,173 service winners.

**The 85,903 sentences that name no shot:**
* *Patterns:* "<actor> wins the point" (69,473), "wins the game" (8,486), "wins the break" (4,724), "saves the break point" (1,106), "wins the set" (793), "wins the break point" (749), "wins the match" (519), and 51 others.
* *Where:* almost all are in doubles, where 57% of men's and 68% of women's doubles points name no shot. Singles have 221, 134 of them in 2026.

**The match statistics** (`matches/complete`):
* *Sections:* `base_stats`, `serve_stats` (by first and second serve, including average and fastest speeds), `return_stats`, `rally_stats` (winners, forced and unforced errors by stroke family and wing), `dss` (serve speeds by serve, court side and direction), `serves` and `distance_run`. Each is given for the match and each set, for each team; 2019 adds `keys`.
* *Its own `statsLevel`* ("K" for full data in 2025, "N" for a walkover) is not the draw's.

**The extras:**
* *Likelihood-to-win:* one row per point with `point_number`, `live_l2w_p1/p2`, `p1_l2w`/`p2_l2w`, momentum, the score, `serve_indicator`, the players' tour ids and `created_epoch`/`created_time`.
* *TennisViz:* `players`, and `insights.{in_attack, serve_quality, return_quality, forehand_quality, backhand_quality}` per set and in total for each player (plus "neutral" for in-attack), with each player's and the championship's averages, and `ai_selected`.

**Per-point width, share of points with a value** (full table in [wimbledon_field_fill.csv](../../../data/studies/official_point_feeds/wimbledon_field_fill.csv)):

| Events and years | Serve speed | Rally count | Kick height | Serve placement | Return depth | Distance run |
|---|---|---|---|---|---|---|
| Main-draw singles 2019–2024 | 47–56% | 95–97% (2019, 2021); 48–61% (2022–24) | 51–91% | 77–99% | 60–90% | 79–100% |
| Main-draw singles 2025–26 | 95–96% | 93–96% | 95–98% | 99%+ | 83–90% | 99%+ |
| Qualifying 2019–2024 | none | 95–97% (2019, 2021, 2023); none (2022, 2024) | none | none | none | none |
| Qualifying 2025–26 | 91–95% | 84–92% | 81–92% | 88–99% | 69–88% | 88–99% |
| Doubles 2019–2024 | 16–37% | 95–96% | 0–2% | none | 0–2% | none |
| Doubles 2025–26 | 89–95% | 95–96% | none | none | none | none |

Both clock times and the sentence are on every point of every year. Challenges won drop to 0 from 2025, when electronic line calling replaced the line judges.

### How it was staged

All tables are strings with the dump's provenance columns.
* **`matches.parquet`:** one row per match listed. It holds the draw entry, flattened (`entry.*`: round, court, status, teams with names, tour ids and seeds, set scores, `entry.score_text` such as "7-6(8) 3-1"), where the match was listed (`draw`, `days` or both), whether Sackmann's archive holds it, each feed's outcome and bytes, and the history's rows and points.
* **`points.parquet`:** every history row verbatim, under the union of the keys of all years, with `year`, `event`, `match_id` and the row's position.
* **`statistics.parquet`:** the statistics file in long form: `section`, `period` (match, set_N), `team`, `key`, `value`. The match object's other fields are rows of section `meta`.
* **`livel2w.parquet`:** one row per likelihood-to-win object.
* **`tz.parquet`:** one row per leaf, as `path` and `value`.

A saved document that does not parse is kept on disk, never asked for again and left out of the tables. It is listed under `unreadable` in the run summary, and its feed's outcome in `matches.parquet` is "unreadable". At Wimbledon there are none.

### Checks

`slamtracker_checks.py` reads the staged tables and Sackmann's copy. Marker rows are left out everywhere.

| Check | Result |
|---|---|
| Accounting | 4,228 of 4,228. The 4,203 "H" matches all have a history with points. The 25 others are walkovers (`statsLevel` "S", status "Walkover"): 20 histories are stubs holding only the marker rows and 5 answer 404; two 2019 walkovers (LD 4301, 4305) answer their statistics file with HTTP 200 and an empty body, recorded as errors |
| Against the 24 Sep research table | Every event's "H" count equals the table's, wherever the table has one. The table could not read the 2026 MS and LS draws; here they are 127 of 127 each |
| Sackmann's archive | 1,757 of 1,758 identical in point count and in the winner of every point. The exception is 2022 LD 4601, whose copy in Sackmann's archive stops at point 58 of 92. The 138 mixed-doubles matches he holds were not collected |
| Sentences | All 709,664 read. 623,761 name a stroke and outcome, and 85,903 name none. **Every sentence agrees with `PointWinner`** (the named side and the verb give the winner), once names are compared without spaces, dots or apostrophes ("C.O'Connell", "C Gauff"). In 308 the verb contradicts the outcome, 275 of them in 2026 (above) |
| Result replay | **4,192 of 4,203 histories reproduce the listed sets won and winner.** A set goes to the winner of its last point; the last set counts when its games show it finished or its sentence ends the match. 9 histories end early (below). In 2 matches the listing's set count contradicts its own score (2021 MD 3110 and 3202, both decided by a 12-12 tiebreak), and the points agree with the score |
| Repeated rows | 19 matches repeat a point row (same times, score and sentence), 13 of them in 2024 |
| Clock times | See below |
| Likelihood-to-win | Every one of the 96,083 rows joins a point on `point_number`; 167 points have no row. Player one is team 1 in all 509 files. The lag behind the point is below |

**The 9 histories that end early** (the listed score shows the match went on):

| Match | Where the history stops |
|---|---|
| 2021 MS 1113 | in set 2 of 3 (129 points) |
| 2021 MS 1122 | at 4-3 in set 5 (319 points) |
| 2021 MS 1147 | in set 2 of 4 (147 points) |
| 2021 MS 1150 | at 5-1 in set 4 (218 points) |
| 2021 LS 2128 | at 3-2 in set 2 (111 points) |
| 2021 LS 2137 | at deuce in the first game (10 points) |
| 2024 QS 11153 | at 3-5 in set 2 (135 points) |
| 2026 QS 11130 | in set 3 (219 points) |
| 2026 LD 4208 | in set 2 (108 points) |

Sackmann's archive holds the six 2021 matches stopped at the same point.

#### Clock times

* **Coverage:** every one of the 709,664 points has both fields filled.
  * *Not Unix times:* 166 values in two 2026 matches. From point 202 of 2026 MS 1127, `EpochTimeEnd` holds numbers such as 93,053 (148 points), and `ElapsedTime` goes negative while `EpochTimeStart` stays right. MS 1207 has 8 more such end times, and the two matches have 10 such start times between them.
  * *Plausible throughout:* 4,201 of 4,203 matches.
* **Order:** 4,127 of 4,203 matches run in order.
  * *Ends before starts:* in 67 matches, 243 points end before they start. 153 of those are in two 2026 matches (MS 1207, 92; MS 1221, 61), where `EpochTimeStart` jumps ahead mid-match while `EpochTimeEnd` keeps its rhythm. The US Open session saw the same in its 2026 files.
  * *Steps back:* in 9 more (2023 MS 1127, 1140, 1141, 1144 and 1145, LS 2107; 2024 MS 1138 and 1139; 2026 MS 1127), a time steps back from one point to the next. Across all matches starts step back 17 times and ends 17.
* **Late entry.** In 2025 QS 11154, from point 17 `EpochTimeStart` (and `ElapsedTime` with it) jumps 516 s ahead and then advances 1 s a point until point 37, while `EpochTimeEnd` keeps a 20–90 s rhythm. The start time there is when the point was keyed in.
* **A spurious day.** In 28 matches both times jump by a day (86,400 s plus an ordinary point interval) between two consecutive points, often mid-set and well before any real break. `ElapsedTime` jumps with them (2025 MS 1113: point 113, 1:30:01 to 25:30:26).
  * *Where:* 2023 MS 9, LS 6; 2024 MS 1; 2025 MS 4; 2026 MS 8.
  * *Spurious where it can be checked:* 12 of them have a live likelihood-to-win file (2025 and 2026). In 11, the rows written after the jump are stamped a median ~86,300 s before the points they follow, so the points' day is wrong. 2025 MS 1205 mixes the jump with a real overnight suspension.
  * *Against the draw's time* (`entry.epoch`, the match's end):
    * in 18 of the 28, the last point ends a day after it;
    * in 7, all of 2023 (MS 1102, 1144, 1161; LS 2134, 2154, 2159, 2160), the last point agrees with it. Either play resumed at the same clock time the next day, or the draw's time carries the shift too. No other clock exists for 2023;
    * 4 more matches have no jump inside the history but end a day after it (2023 MS 1150, 1155, 1202; 2024 MS 1147).
  * *The fix is left to the cleaning phase:* subtract a day from the jump on, point by point. `first_day_jump_at_point` in the epoch file gives where it starts.
* **Other long gaps.** 343 gaps over an hour are real: rain delays, and overnight suspensions such as 2025 MS 1113's later 67,507 s.
* **Against the listing's time.** The last point ends within 10 minutes of it in 4,094 matches. The listing is later by more in 75, which look updated after the match.
* **Late last points.** In 10 matches the last point is later than the listing by 13–17 minutes (six), 4.6 hours (the 2025 final), 7.2 hours (2026 MS 1207), or about 23 hours (2023 MD 3401, 2024 MS 1138).

* **A listing's whole-hour offset** is counted as the listing's error, not the points', when the history's end times are consistent: none steps back or is implausible, no day jump, and an ordinary gap before the last point. Start-time faults do not count against it. The US Open's 2026 listings run 5 hours early. No Wimbledon match qualifies: 2024 MS 1138's 23 h 5 min stays a late last point, because one of its end times steps back.

For an exact join to market prices, use `EpochTimeEnd` and drop or correct the listed matches.

### Wimbledon's IBM extras

* **Likelihood-to-win:**
  * *Coverage:* 254 files per year, one for every singles main-draw match of 2025 and 2026.
  * *Live or replay:* a file is live when its rows were written while the match was played. 504 files are live. Four 2025 files are replays, written after the event: MS 1109, 1111, 1161, 1164. The same holds for the one qualifying file found (2025 QS 11101), written on 24 June, the day after its match.
* **Lag behind the point's `EpochTimeEnd`, live files** (13 matches with the clock faults above left out):

  | Year | Median | 10th percentile | 90th | 99th | Rows over 10 minutes |
  |---|---:|---:|---:|---:|---:|
  | 2025 | 12 s | 5 s | 51 s | 281 s | 364 of 44,402 |
  | 2026 | 89 s | 45 s | 361 s | 1,363 s | 1,926 of 46,738 |

  33 files have rows written hours or days late, often the last point before an overnight suspension; the extreme is 13 days (2026 LS 2311). Join on `point_number`, not on time.
* **TennisViz:** one file for every singles main-draw match of 2024 and 2025 (508).
* **The probe outside singles main draws** (28 requests):
  * likelihood-to-win is absent for 2025 QS 11102, RS 12101–12102, MD 3101–3102 and LD 4101–4102, and for all eight files probed in 2026 (the same events);
  * TennisViz is absent for 2024 and 2025 MD, LD and RS (12 files);
  * 2025 QS 11101 is the one exception, the replay above.

### Gaps and limits

* **Not collected:**
  * mixed doubles, the junior, wheelchair and invitation events;
  * 2018 and 2020 (not served; the 2020 event was cancelled);
  * the 2026 MS and LS draw files (blocked). Their 127 matches each come from the day files, whose entries have the draw's fields.
* **Per point, the feed has none of:**
  * ball or player coordinates;
  * in doubles, which partner hit the last shot;
  * a stroke for most doubles points.
* **Flags are unreliable:** use `PointWinner` and the scores, not `SetWinner`, `MatchWinner` or `GameWinner`.
* **Two-host dependence.** The archive host could be retired at any time. The raw documents under `data/raw/point_sources/wimbledon/` would then be the only copy of 2019 and 2021–2025 qualifying, the 2024 doubles and all of 2025. They are gitignored (93 MB), so a backup outside the working tree is worth considering.
* **Terms.** AELTC's terms allow personal, non-commercial extracts; the archive host's robots.txt disallows every robot. This was collected under the owner's decision, within its limits.

### Receipts

All between 24 September 18:45 and 25 September 01:31 UTC. **9,562 requests:**
* 9,525 answered 200 with a document;
* 20 answered 302 to `/notfound` (absent);
* 13 answered 404 (absent: 5 walkover histories and the 8 probed 2026 likelihood-to-win files);
* 4 answered 200 without JSON: the two 2019 walkover statistics files, asked a second time to record what came back (an empty body).

No 403, 429, challenge or reset; nothing was retried.

| Run | Host | Requests | Time |
|---|---|---:|---|
| Pilots: the payload shapes (archive host), then the 2026 day list (www, while the main run was on the archive host) | both | 8 + 2 | 18:45–18:46, 18:57 |
| 2019 and 2021–2025 | archive host | 8,039 | 18:51–00:27, 2.5 s a request |
| 2026 | www | 1,483 | 00:28–01:30 |
| Probe of the extras, and the two walkover files again | both | 30 | 01:30–01:31 |

### Rerunning

```
./python.sh -m src.ingest.point_sources.wimbledon --years 2019,2021,2022,2023,2024,2025   # archive host; cached answers are not asked again
./python.sh -m src.ingest.point_sources.wimbledon --years 2026                           # www: draws, day lists, every match
./python.sh -m src.ingest.point_sources.wimbledon --stage-only                           # rebuild every table from the raw files, no HTTP
./python.sh src/eda/official_point_feeds/slamtracker_checks.py --site wimbledon           # the checks
./python.sh -m pytest test/official_point_feeds/test_slamtracker.py -q
```

`--events`, `--feeds`, `--matches <year>:<id>`, `--limit` and `--max-requests` bound a run; `--order calendar` drops the new-first order. Staging always covers every year (`--stage-years` narrows it, which also shrinks the tables).

## US Open scoring feeds (IBM SlamTracker)

**All 3,020 matches of the six events (MS, WS, MQ, WQ, MD, WD) of 2022–2026 are accounted for:**
* 2,445 have a point history with points, 405,804 points in all;
* 518 are qualifying matches the draw marks "S" (not full data) and 14 are walkovers. Their histories hold only the two marker rows, except 5 walkovers', which answer 404;
* 43 are marked "H" (full data) in the draw, but their history holds no point: qualifying on outer courts ([below](#h-matches-without-points));
* no request was refused, rate-limited, challenged or reset, and nothing was retried.

**1,313 of the matches with points are new to the dump** (212,752 points):
* qualifying of 2022–2024: 242;
* every event of 2025: 471;
* every event of 2026: 600.

The research estimate was 1,356. The 43 "H" histories without points make the difference.

**The other 1,132 were in the dump already, from Sackmann's archive. 1,131 of them match his copy point for point** (the number of points and the winner of every point). The exception is 2022 WS 2139: his copy stops at point 69 of 168, and the feed has the whole match. For these matches the feed adds what his copy lacks.

**Every point carries, as at Wimbledon:**
* its winner, server, serve number and score;
* a clock time at its start and its end;
* a sentence naming the stroke and the outcome. It is the only per-point record of forced errors: 140,405 points end in one. Unlike Wimbledon's, doubles sentences name the shot too (99.7–99.8%).

Serve speed is filled on 86–95% of points in every event and year, qualifying and doubles included. Placement, return depth, kick height and distance run are filled on the main-draw singles, and on qualifying in 2023 and 2025–26 (table [below](#what-a-record-holds-2)).

**Four things to know before using it:**
* **`EpochTimeEnd` is the reliable clock. In 2026 neither `EpochTimeStart` nor the draw's own time is.**
  * *`EpochTimeStart`:* it goes wrong partway through 152 of 2026's 600 matches, so 14,652 points end before they start. `EpochTimeEnd` never steps back in 2026.
  * *The draw's time:* its `epoch`, the match's end in 2022–2025, is exactly 5 hours early in 473 of 2026's matches. Polymarket's markets side with the point clock ([below](#clock-times-2)).
* **Eight 2025 qualifying histories are mostly hollow.** They number every point but give a winner for at most four; the other rows carry no winner, score, time or sentence. 689 point rows in 14 matches are hollow.
* **32 histories stop before the match ended.** The 17 that Sackmann holds stop at the same point in his copy.
* **The 2025 likelihood-to-win files for the singles main draws are replays.** 251 of 252 were written on 23–25 July 2026, not during the 2025 event.

**IBM extras** ([below](#the-us-opens-ibm-extras)):
* *Likelihood-to-win after every point:* 575 files. That is every singles main-draw match of 2025 and 2026, plus 69 matches of 2025 qualifying.
* *Pre-match likelihood to win:* 684 files, for the same main draws and 177 matches of 2025 qualifying. One more file (2025 WS 2701) was served as malformed JSON.
* *Serve biomechanics from limb tracking:* 245 files, 2026 singles main draw.
* *Key moments:* 254 files, 2026 singles main draw.
* *Distance run, per set:* 1,652 files. The main-draw singles of every year, and qualifying where its courts had tracking.
* *None* for doubles, or for 2026 qualifying.

| Item | Where |
|---|---|
| Adapter | `src/ingest/point_sources/usopen.py`: the US Open's settings for the shared engine `slamtracker.py` (Wimbledon's section above) |
| Raw documents | `data/raw/point_sources/usopen/<year>/`: `draws/`, `history/`, `stats/`, `distance/`, `livel2w/`, `limbtracking/`, `keymoments/`, `prematch_l2w/`, all gzipped; `_receipts.jsonl`. 73 MB on disk (819 MB of JSON) |
| Staged tables | `data/dump/points/usopen/`: `matches` (3,020 rows), `points` (412,037 rows: every history row, marker rows included), `statistics` (2,551,556 rows, long form), `livel2w` (102,100 rows), `keymoments` (6,367 rows); `distance` (11,468), `limbtracking` (22,491) and `prematch_l2w` (4,104) as path and value. 36 MB |
| Run summary | [usopen_summary.json](../../../data/studies/official_point_feeds/usopen_summary.json) (the last run, a restage, with receipts by feed, year and outcome and the unreadable file); every run in [runs.jsonl](../../../data/studies/official_point_feeds/runs.jsonl) |
| Checks | `src/eda/official_point_feeds/slamtracker_checks.py --site usopen`: [usopen_checks.json](../../../data/studies/official_point_feeds/usopen_checks.json) (totals and lists), [coverage](../../../data/studies/official_point_feeds/usopen_coverage.csv), [Sackmann](../../../data/studies/official_point_feeds/usopen_sackmann.csv), [sentences](../../../data/studies/official_point_feeds/usopen_sentences.csv), [epoch problems](../../../data/studies/official_point_feeds/usopen_epoch_problems.csv), [result problems](../../../data/studies/official_point_feeds/usopen_result_problems.csv), [field fill](../../../data/studies/official_point_feeds/usopen_field_fill.csv). US Open only, `src/eda/official_point_feeds/usopen_notes.py`: [usopen_notes.json](../../../data/studies/official_point_feeds/usopen_notes.json) (hollow rows, the statistics file's own level, the listing's clock) and [usopen_clock_vs_polymarket.csv](../../../data/studies/official_point_feeds/usopen_clock_vs_polymarket.csv) |
| Tests | `test/official_point_feeds/test_usopen.py` (10 tests; fixtures `usopen_*` cut from 2022 MS 1101, 2025 MS 1101, MQ 11101 and 11108, MD 3101, 2026 MS 1101 and MQ 11101) |

### What was fetched

| Years | Host | Notes |
|---|---|---|
| 2022–2026 | `https://www.usopen.org` | A plain client gets its connection reset (research pass). The shared client, `curl_cffi` with the Chrome profile, was never reset. robots.txt does not disallow the feed paths; the USTA's terms forbid scraping, and this was collected under the owner's decision. 2019–2021 are not served (404, here and on `2024.usopen.org`, research pass). `2024.usopen.org` mirrors 2024 and was not asked |

**Paths.** The draws are `/en_US/scores/feeds/<year>/draws/<EV>.json`. For every match listed:
* `slamtracker/history/<id>C.json`, the point history;
* `matches/complete/<id>.json`, the match statistics;
* `slamtracker/distance/<id>.dist.json`, the distance run (the US Open only).

The extras are under `/clouddata/`: `livel2w/<year>/<id>C.json`, `likelihood-to-win/<year>/<id>.json`, `limbtracking/<year>/match/<id>.json` and `keymoments/key_moment/<year>/<id>.json`.

**Not-found answers.** A missing `/clouddata/` file answers HTTP 302 to `https://www.usopen.org/notfound`. A missing feed file answers 404 with an HTML page. Both are recorded as absent and never asked again.

**What was asked of which match.**
* *History and statistics:* every match.
* *Distance, likelihood-to-win, limb tracking and key moments:* every match the draw marks "H".
* *Pre-match likelihood:* every match.
* *Years:* each extra only in the years it was seen in (below).

**Where the extras were probed.** Each extra was asked for in all six events. The engine gives up on a feed for one year and event after five absences in a row. After the main run, two follow-ups:
* where the feed had turned up before the engine gave up (distance in 2022 and 2024 qualifying and 2024 WS; likelihood-to-win and pre-match in 2025 qualifying), the rest of the group was asked, with that limit off;
* where it had not, the group's last three matches were asked (the qualifying finals, the doubles semi-finals and final). None held one.

**Order.** The matches not in Sackmann's archive came first, newest year first; the held main draws came last.

| Year | Draw matches | "H" | With points | "H" without points | Walkovers | New to the dump | Points | Distance | Likelihood-to-win | Pre-match | Limb tracking | Key moments |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 604 | 459 | 459 | – | 3 | 82 (qualifying) | 78,131 | 262 | – | – | – | – |
| 2023 | 604 | 457 | 452 | 5 | 3 | 75 (qualifying) | 74,882 | 331 | – | – | – | – |
| 2024 | 604 | 463 | 463 | – | 2 | 85 (qualifying) | 75,978 | 219 | – | – | – | – |
| 2025 | 604 | 509 | 471 | 38 | 2 | 471 (all) | 77,812 | 364 | 321 | 430 | – | – |
| 2026 | 604 | 600 | 600 | – | 4 | 600 (all) | 99,001 | 476 | 254 | 254 | 245 | 254 |
| **All** | **3,020** | **2,488** | **2,445** | **43** | **14** | **1,313** | **405,804** | **1,652** | **575** | **684** | **245** | **254** |

Each event's draw holds 127 (MS, WS), 112 (MQ, WQ) or 63 (MD, WD) matches every year. The draw counts and "H" counts equal the 24 Sep research table's in all 30 cells. Per event and year, with every feed's outcomes, see [usopen_coverage.csv](../../../data/studies/official_point_feeds/usopen_coverage.csv).

### What a record holds

**As at Wimbledon** ([above](#what-a-record-holds-1)), with these differences:
* **History fields:** 52 in 2022–2023 and 57 from 2024, as at Wimbledon.
  * 2026 adds `PointID`, e.g. "010101" (set, game and point [inference]).
  * 2026 drops `ChallengeWon`, which is 0 on every point of 2022–2025: electronic line calling covered every court.
* **The statistics file** has the same sections. Its own `statsLevel`:
  * full data: "H", or "K" on 165–184 matches a year in 2022–2025;
  * "S" for qualifying without full data;
  * "N" for walkovers.

  37 matches the draw marks "H" say "S" in their statistics file, 26 of them among the "H" matches without points.
* **The distance file:** metres and feet run by each team, cumulative at the end of each set, e.g. `{"teams": {"team1": {"1": ["707.1 m", "2319.8 ft"], "2": […]}, "team2": {…}}}`.
* **Pre-match likelihood:** `p1_id` and `p2_id` (tour ids), `predicted_winner`, `likelihood_to_win`, `opponent_likelihood_to_win`.
* **Limb tracking.** Per player:
  * `insight`, a sentence;
  * `match_summary`: average serve quality, efficiency and effectiveness scores, total serves;
  * `standout_metrics` for the player's top phases only: toss (apex height, drift, toss-to-contact time), loading (knee angle, pelvis rise, hip–shoulder separation), cocking, acceleration (chain order, peak racket speed) and contact;
  * effectiveness: serves in, aces, average ball speed, distance of the bounce from the target;
  * per set, the average serve quality and the best serve, with its point number.
* **Key moments:** one row per moment: `point_number`, `set_number`, `moment_type`, `insight_importance`, `factual_insight`, `insight`, `created_epoch` and the players' names and ids.

**The sentence** follows Wimbledon's grammar:

| Stroke | Winner | Forced error | Unforced error |
|---|---:|---:|---:|
| Forehand | 42,246 | 67,935 | 61,621 |
| Backhand | 20,439 | 61,570 | 42,383 |
| Forehand volley | 16,735 | 4,884 | 3,878 |
| Backhand volley | 10,084 | 5,509 | 2,848 |
| Forehand smash | 10,674 | 426 | 1,291 |
| Backhand smash | 195 | 81 | 36 |

Serve outcomes: 24,277 aces, 20,983 double faults, 5,994 service winners.

**Sentences without a stroke and outcome:**
* *No shot named:* 1,026, e.g. "<actor> wins the point" (788), "wins the game" (61), "loses the point" (39). Most are in qualifying: 98.9% of men's and 97.9% of women's qualifying points name a shot, against 99.7–99.9% elsewhere.
* *Empty:* 689, the hollow rows.

**Per-point width, share of points with a value** (full table in [usopen_field_fill.csv](../../../data/studies/official_point_feeds/usopen_field_fill.csv); 2025 qualifying shares include the hollow rows):

| Events and years | Serve speed | Rally count | Kick height | Serve placement | Return depth | Distance run |
|---|---|---|---|---|---|---|
| Main-draw singles 2022 | 91% | 52–55% | 51–55% | 93–94% | 84–86% | 94% |
| Main-draw singles 2023–26 | 92–95% | 89–95% | 89–98% | 92–99% | 82–91% | 92–100% |
| Qualifying 2022 | 91–92% | none | none | 11–17% | 10–16% | 11–17% |
| Qualifying 2023 | 93% | 65–68% | 60% | 75–78% | 61–67% | 76–79% |
| Qualifying 2024 | 92% | 22–25% | none | none | none | none |
| Qualifying 2025–26 | 86–93% | 80–83% | 80–85% | 83–96% | 75–80% | 83–96% |
| Doubles 2022–24 | 91–92% | 94–95% | none | none | none | none |
| Doubles 2025 | 92% | none | none | none | none | none |
| Doubles 2026 | 94–95% | 87–89% | none | none | none | none |

Both clock times and the sentence are on every point except the hollow rows.

### How it was staged

As at Wimbledon ([above](#how-it-was-staged-1)). `livel2w` and `keymoments` keep one row per object. `distance`, `limbtracking` and `prematch_l2w` are flattened to path and value.

The main run's staging stopped on the malformed pre-match file. The engine now keeps such a file, never asks for it again and lists it as unreadable (same section). The restage then wrote every table and the summary.

### Checks

`slamtracker_checks.py --site usopen` for the checks shared with Wimbledon. `usopen_notes.py` for the hollow rows, the statistics file's own level and the listing's clock. Marker rows are left out everywhere.

| Check | Result |
|---|---|
| Accounting | 3,020 of 3,020. 2,445 histories hold points. The 518 "S" qualifying matches and 9 walkovers answer a history holding only the marker rows; 5 walkovers answer 404 (2022 WD 4201, 2024 WD 4212, 2025 MS 1208, 2026 MD 3204, WD 4208). 43 "H" matches have no point (below) |
| Against the 24 Sep research table | Every event's match count and "H" count equals the table's |
| Sackmann's archive | 1,131 of 1,132 identical in point count and in the winner of every point. The exception is 2022 WS 2139, whose copy in Sackmann's archive stops at point 69 of 168. The 92 mixed-doubles matches he holds were not collected |
| Sentences | All 405,804 read. 404,089 name a stroke and outcome, 1,026 name none and 689 are empty (the hollow rows). **Every sentence that names a side agrees with `PointWinner`**, once names are compared without spaces, dots and apostrophes (the feed writes "C. O''Connell"). In 74 the verb contradicts the outcome, e.g. "P. Stearns wins the point with a forehand unforced error" |
| Result replay | **2,413 of 2,445 histories reproduce the listed sets won and winner.** 32 end early (below) |
| Hollow rows | 689 point rows in 14 matches have no winner: eight 2025 qualifying histories are mostly hollow (12214, 11207, 12314, 12312, 12304, 12229, 11301, 11223), and six other matches have 1–14 such rows |
| Repeated rows | 730 rows in 24 matches repeat the point before. 711 of them are in 11 of the damaged 2025 qualifying records, most of them hollow rows, and 19 are in 13 other matches |
| Clock times | See below |
| Likelihood-to-win | 100,912 of the 102,100 rows join a point on `point_number`. The other 1,188 belong to matches whose history has no points. The scores follow the history's player order: the games agree on at least 99% of the points of every file but two (2025 MQ 11148, 76%, the match with a day jump; WQ 12125, 97%). The player ids do not in 16 files: 12 of the 2025 replays name a player who did not play the match, and 4 files of 2026 name team 2 as player one. So join on `point_number` and read p1 as the draw's team 1, not by id. The lag behind the point is [below](#the-us-opens-ibm-extras) |

#### "H" matches without points

43 matches: 2023 MQ (5), 2025 MQ (20) and 2025 WQ (18).
* *Where:* on outer courts (5, 8, 9, 10, 13–17).
* *Their statistics file* says "S" for 26 and "H" for 17.
* *IBM's other feeds* do hold data for many of them: a distance file for 33, likelihood-to-win for 16 and the pre-match likelihood for 35.

The point history is missing, not the match's tracking.

#### The 32 histories that end early

The listed score shows each of these matches went on.
* **2022:**
  * MS 1103, 1114, 1116, 1149, 1150, 1151;
  * WS 2121, 2123, 2140, 2147, 2150, 2152, 2154, 2155, 2160;
  * MD 3122;
  * MQ 11310.
* **2023:** MS 1129; WQ 12313, 12315.
* **2025 qualifying:**
  * MQ 11163, 11207, 11223, 11301, 11316;
  * WQ 12138, 12156, 12214, 12229, 12304, 12312, 12314.

  Most of these are hollow records.

Sackmann's archive holds the 17 main-draw matches stopped at the same point.

#### Clock times

* **Coverage.** Both times are on every point except:
  * the 632 hollow rows of 7 matches;
  * 57 rows in 9 matches whose times are implausible (outside 2000–2100, e.g. 86,400).
* **`EpochTimeStart` goes wrong in 2026:**
  * *Scale:* 14,652 points in 152 matches end before they start.
  * *Pattern:* from some point in the match the start jumps to an exact hour, then about a day ahead (MQ 11101 from point 32, WS 2101 from point 77, WD 4101 from point 87), while `EpochTimeEnd` keeps its rhythm.
  * *Other years:* 20–25 matches a year have a few points ending before they start (23–29 points a year; 267 in 2024).
* **Steps back.** `EpochTimeEnd` steps back 6 times in 3 matches (2022 MS 1111 and MD 3122, 2025 MQ 11148).
* **A spurious day,** as at Wimbledon.
  * *Where it jumps:* in 2022 WS 2104 from point 40, and 2025 WQ 12213 from point 55.
  * *End a day after their listing:* 2022 MS 1111 and WS 2104, 2025 MQ 11148.
* **The listing's time, and which clock is right.**
  * *2022–2025:* the draw's `epoch` is the match's end. The last point is within 10 minutes of it in 1,763 of 1,845 matches; in most of the rest the listing is later, updated after the match.
  * *2026:* it is exactly 5 hours early in 473 matches (checks: 5 h ± 6 min) and within 10 minutes in 121.
  * *The evidence:* Polymarket's markets for the US Open are an independent clock ([usopen_clock_vs_polymarket.csv](../../../data/studies/official_point_feeds/usopen_clock_vs_polymarket.csv)). Of 477 singles and qualifying matches of 2026, 461 were matched to a market by the players' names.

    | Measure, in minutes (quartiles) | 414 matches with the 5-hour offset | 43 matches without it |
    |---|---|---|
    | Market close, after the last point | 31–37 | 31–33 |
    | Market close, after the listing's time | 331–337 | 31–33 |
    | First point, after the market's scheduled start | −1 to 5 | 2 to 8 |

    Both groups agree with the point clock, and only the listing is off. The live likelihood-to-win rows agree too (below).
* **Other long gaps.** 103 gaps over an hour: rain delays and suspensions.

For an exact join to market prices, use `EpochTimeEnd`. Leave out the hollow rows and the two day jumps, and don't use the 2026 listing times.

### The US Open's IBM extras

**Likelihood-to-win.**

| Year | Singles main draws | Qualifying | Doubles |
|---|---|---|---|
| 2025 | 252 files: 251 replays written 23–25 July 2026, and one live | 69 of 131 "H" matches: MQ 33, WQ 36. 53 live; 16 cannot be dated, as their history has no points | none |
| 2026 | 254 files: 251 live, and 3 regenerated during the event (31 Aug, 4 Sep) | none | none |

* **Lag behind the point's `EpochTimeEnd`, live files** (3 files of matches with the clock faults above left out): median 53 s, 10th percentile 18 s, 90th 139 s, 99th 513 s. 331 rows are over 10 minutes late. Join on `point_number`, not on time.
* **The replays** are generated after the event. Their values need not be what IBM showed live, and the 12 with a wrong player id are among them (above).

**Pre-match likelihood to win.**
* *Coverage:* 2025 MS 127 and WS 126, plus WS 2701 as malformed JSON (`"p2_id": "wta320760""`, a doubled quote), kept and flagged unreadable; 2026 MS and WS 127 each.
* *Qualifying:* 177 of 224 matches in 2025 (MQ 88, WQ 89), including "S" matches; none in 2026.

**Limb tracking and key moments:**
* *Limb tracking:* 2026 singles main draw only, 245 of 254 files (MS 120, WS 125).
* *Key moments:* the same draws, 254 of 254 files (6,367 moments).
* *Limits:* limb tracking gives only each player's top phases, and no per-serve rows.

**Distance run.**

| Draw | Files |
|---|---|
| Main-draw singles | 252, 253, 219, 252 and 254 in 2022–2026. 2024 has gaps: MS 121 of 127, WS 98 of 126 |
| Qualifying ("H" matches) | 10 of 82 in 2022, 78 of 80 in 2023, none of 85 in 2024, 112 of 131 in 2025, 222 of 223 in 2026, following the courts that had tracking |
| Doubles | none |

**Where the extras are not:**
* *Doubles:* none of the extras, in any year. The engine found five absences in a row at the start of each group, and the semi-finals and final were absent too.
* *2026 qualifying:* none of likelihood-to-win, pre-match, limb tracking or key moments; its distance files are all there.
* *Other years:* limb tracking and key moments are absent before 2026 (the research pass), and likelihood-to-win before 2025.

### Gaps and limits

* **Not collected:**
  * mixed doubles (Sackmann holds 92 matches of 2022–2024), and junior, wheelchair and champions events;
  * 2019–2021, which are not served;
  * 25 archived histories of 2016–2019 and 2021 found by the Wayback survey ([above](#older-editions-in-the-wayback-machine-all-feeds)). They are outside the decision's 2022–2026 range and were left for the owner;
  * SlamTracker 3D (`3d.usopen.org`), which needs a Firebase sign-in.
* **Per point, the feed has none of:**
  * ball or player coordinates;
  * in doubles, which partner hit the last shot.
* **Holes in the record:**
  * the 43 "H" histories without points;
  * the eight mostly hollow 2025 qualifying histories;
  * the 32 that end early.
* **Unreliable fields:**
  * `EpochTimeStart` in 2026;
  * the draw's `epoch` in 2026;
  * player ids in 16 likelihood-to-win files;
  * `SetWinner`, `MatchWinner` and `GameWinner`, as at Wimbledon.
* **Backups.** The raw documents under `data/raw/point_sources/usopen/` are gitignored (73 MB). They would be the only copy if the site drops older years, so a backup outside the working tree is worth considering.

### Receipts

All between 24 September 19:01 and 25 September 02:06 UTC. **10,082 requests brought 10,082 answers, each for a different document:**
* 9,473 answered 200 with a document (one of them malformed JSON);
* 301 answered 302 to `/notfound` (absent);
* 308 answered 404 (absent).

No 403, 429, challenge or reset; nothing was retried.

| Run | Requests | Time (UTC) |
|---|---:|---|
| Pilot: every draw, then 16 matches across years, events and levels | 114 | 19:01–19:06 |
| Every match, new-first | 9,560 | 19:07–01:46 |
| Follow-ups: the rest of the groups where an extra was sporadic (318), then the late-round sample (90) | 408 | 01:49–02:06 |

All at 2.5 s a request. The main run's line in `runs.jsonl` was lost when its staging stopped; its receipts, and its own count of 9,560 requests, hold the fetch.

### Rerunning

```
./python.sh -m src.ingest.point_sources.usopen --max-requests 11000        # every year; cached answers are not asked again
./python.sh -m src.ingest.point_sources.usopen --stage-only                # rebuild every table from the raw files, no HTTP
./python.sh src/eda/official_point_feeds/slamtracker_checks.py --site usopen   # the shared checks
./python.sh src/eda/official_point_feeds/usopen_notes.py                   # hollow rows, statistics levels, the listing's clock
./python.sh -m pytest test/official_point_feeds/test_usopen.py -q
```

A rerun gives up on the same groups again after five absences in a row. To finish a group where a feed is sporadic, the follow-up passed `--years`, `--events` and `--feeds` for it with `--streak 0` (and `--no-stage`).

## WTA official API

**The listing method is verified and coverage is measured on a seeded sample. The owner's plan is to collect every endpoint in batches; the [collection plan and to-do list](#collection-plan-and-to-do-list) scope every endpoint and track what remains.**
* **B1**, the umpire's point log for every draw of 2020–2026, ran from 21:13 UTC on 24 September to 20:38 UTC on 25 September: 33,599 requests, no refusal or pause, and the logs of 33,301 of the 33,304 played matches. A rerun at 22:02 fetched the two logs that had timed out (HTTP 504) and four 2026 matches played since. The one match left answers 404.
* **B2**, 2019's point log, approved on 25 September ("when B1 is done, you have permission to start B2"), ran from 22:04 UTC on 25 September to 00:28 on 26 September: 3,454 requests, no error, pause or refusal, and a log for every one of the 3,394 played matches 2019's match lists hold. The log holds points only from 1 April 2019, and until the end of May only bare records ([below](#what-a-document-holds)). 15 of 2019's 64 editions have no match list at all.
* **B3–B9**, every other endpoint, were approved together on 29 September ("finish B2, then continue with B3 etc...") and ran one after the other in one detached chain, relaunched twice after the PC restarted, from 17:20 UTC that day to 05:13 UTC on 3 October ([the chain](#running-a-batch-and-keeping-it-safe)). Every batch is done.
  * *B3*, the box score of every played match of 2019–2026, ran from 17:20 UTC on 29 September to 18:54 on 30 September: 36,741 requests, three retried, no error, pause or refusal. 36,825 of the 36,832 matches have a box score with data and 7 an empty one (`[]`); none answered 404. 130 of those matches were 2026 ones played after B1, picked up when B3 refreshed the unfinished editions' match lists.
  * *B4*, the advanced statistics of 2025–26, ran from 18:58 UTC on 30 September to 03:26 on 1 October: 12,069 requests, no pause or refusal. One answer failed (HTTP 504 four times: Rome 2026 qualifying RS016) and is retried by the chain's 2026 top-up. 11,902 of the 12,068 matches have advanced statistics, none of them empty, and 165 answer 404: 5 in 2025, and 160 in 2026. 136 of the 2026 ones fall in the week of 13 April 2026: Stuttgart, Rouen and Oeiras have them for only 38 of their 174 matches.
  * *B5*, 2026's win probability and momentum, ran from 03:29 to 09:10 UTC on 1 October: 5,751 requests, no pause or refusal, slower than the others (about 1,015 an hour) because the documents are larger (31 kB in the middle). Three answers failed (HTTP 504 four times) and are retried by the 2026 top-up. 5,097 of the 5,727 matches have a document with points, 10 an empty one, and 617 answer 404. Every draw has them, qualifying and doubles included. April 2026 is the gap again: 376 of the 404s, against 4 to 75 in every other month.
  * *B6* (momentum, 2025) started at 09:17 UTC on 1 October. The PC restarted at 13:12 UTC (shutting down from about 13:08), which ended B6 and the chain at 3,850 of 2025's 6,341 matches. Nothing was lost: the receipts read whole, and no partial file was left. The chain was relaunched from B6 at 13:21 UTC ([below](#running-a-batch-and-keeping-it-safe)), skipping the 3,850 answers already held without a request, and B6 ended at 15:42: 6,323 requests over its two parts, no error, pause or refusal. 5,896 of the 6,341 matches have momentum, none empty, and 445 answer 404. 197 of those are the three editions that began on 29–30 December 2024: Brisbane and Canberra have none, Auckland only its 15 doubles matches. From Hobart and Adelaide (6 January 2025) on, every edition has it, with gaps that are widest in September (47 of 960 matches), October (71 of 930) and December (50 of 121).
  * *B7*, the advanced statistics of 2021–24, ran from 15:50 UTC on 1 October to 07:46 on 2 October in two parts around the PC's second restart (20:52 UTC): about 19,570 requests, no refusal or challenge. During the second part the PC lost its internet connection for about 40 minutes (00:47–01:27 UTC; the API's name would not resolve). The run paused three times for 10 minutes, as designed, and the requests that had failed were asked again and answered. 19,518 of the 19,581 matches have advanced statistics, none empty, and 63 answer 404 (48 of them in 2021); no error is left.
  * *B8*, point-by-point from 14 March 2022 to 2026, ran from 07:55 UTC on 2 October to 02:21 on 3 October in two parts: 2022–24 with a 404 limit of 400, then 2025–26 with none. 26,384 requests, no pause or refusal. 20,841 of the 26,507 matches have it and 5,663 answer 404. Three answers failed (HTTP 504 four times, in 2022–23) and are to be asked again.
    * *By year:* 3,571 of 3,770 (2022: the 198 404s are Miami and Marbella, before it began), 5,176 of 5,181, 5,425 of 5,433, 3,345 of 6,341 (2025) and 3,324 of 5,782 (2026).
    * *2025–26 by month:* complete from January to May 2025; patchy in June to September 2025 (1,729 404s); **none from October 2025 to March 2026** (all 3,112 matches); back for 403 of April 2026's 655 matches and almost every match from May to August; patchy again in September 2026 (257 of 852 missing).
  * *B9*, the Slams' box scores of 2024–26, ran from 02:33 to 04:40 UTC on 3 October: 3,028 requests (nine match lists, the rest box scores), no error, pause or refusal. **All 3,020 listed matches have a box score with data**: every draw of every Slam of 2025 and 2026 (302 matches each), but of 2024 only Roland Garros and the US Open. The 2024 Australian Open's and Wimbledon's match lists are empty, like every Slam's of 2020–23.
  * *Top-ups*, 04:45–05:07 UTC on 3 October: B1, B3, B4, B5 and B8 asked again for 2026's unfinished editions, which brought 191 logs, 61 box scores, 57 advanced statistics, 57 win-probability documents and 2 point-by-point documents for matches played since each batch passed 2026 (525 requests). They also answered the four 2026 requests that had failed with HTTP 504. The chain then restaged every year, reran the checks and the to-do list, and ended at 05:13.
  * *Afterwards*, at about 05:20 UTC, the three point-by-point requests of 2022–23 that had failed with HTTP 504 were asked again (`--batch B8 --years 2022-2023`, 3 requests) and answered. **No error is left in any batch.** What remains is one Beijing 2026 match (1020/2026/LS046) finished after the last top-up, pending for four endpoints, with every 2026 match still to be played: a 2026 refresh after the season picks them up ([Rerunning](#rerunning-3)).

* **The umpire's event log is the record to collect.** Its endpoint, `…/matches/<id>/events`, is not one of the four the request named; it came from third-party research and was probed with them.
  * *Coverage:* in the sample, the points of every sampled match of every year, 2019 to 2026, in every draw: 235 of 235 non-Slam documents, and both 2019 finals asked. In the batches, 33,289 of the 33,308 played matches of 2020–2026 (18 logs empty, one absent) and 2,306 of 2019's 3,394.
  * *Content:* every point with its server, whether it was played on the first or second serve, aces, double faults, lets, corrections and a millisecond UTC time.
  * *Check:* replayed, the complete logs of 2019–2026 reproduce the listed score of 34,392 of 34,928 matches (98.5%); in the sample, 237 of 238.
* **Point-by-point covers less and is less reliable:**
  * *absent* in 2020, in 2021 and until at least 9 March 2022;
  * *present* in every sampled match from April 2022 to 2024;
  * *patchy from mid-2025:* none from October 2025 to February 2026, and in 2026 the finals are missing.
  * It reproduces the listed score of 106 of 121 matches, and its `pointWinner` field is wrong on 434 of 16,256 points.
* **2019 is partly served** (batch B2). Point-by-point is not, and the event log comes in three kinds:
  * *empty* for the 1,088 matches from Brisbane and Auckland (31 December 2018) to Guadalajara (11 March), but for one Acapulco qualifying match;
  * *bare* for the 662 matches from Monterrey and Charleston (1 April; their qualifying of 30–31 March is empty) to Strasbourg (May): point, ace and fault records with set, game and clock time, but no score, server, winner or serve number;
  * *complete* for the 1,644 matches from Bol (4 June) on, 1,636 of which replay to the listed score.
  * The box score is served for the whole year (B3): all 3,394 matches have one with data, those with an empty or bare log included.
  * 15 of the 64 editions (Miami, Rome and Toronto among them) have no match list, so none of their matches can be asked. The one 2018 log asked (Charleston final) was empty.
* **The extras are recent:**
  * *win probability* starts in 2025, and only the 2026 documents carry real values;
  * *advanced statistics* are zeros in 2021, winner and unforced-error totals in 2022–24, and full detail (by wing, forced errors, rallies, net approaches, fault reasons) in 2025–26;
  * *the box score* is present everywhere.
* **Slams and the United Cup hold no WTA point data.** The API lists Slam matches only from 2024, and their event logs are empty. The United Cup's match list is empty in every year.

| Item | Where |
|---|---|
| Adapter | `src/ingest/point_sources/wta.py` |
| Raw documents | `data/raw/point_sources/wta/`: `calendar/`, `tournaments/<id>_<year>/matches.json`, `matches/<id>_<year>/<MatchID>/<endpoint>.json.gz`, `_receipts.jsonl` (98 MB) |
| Staged tables | `data/dump/points/wta/`: `editions.parquet`, and one file per table and year, `<table>/<year>.parquet`, for `matches`, `points` (point-by-point), `events`, `stats`, `advanced` (long) and `momentum` (long). Staging streams the documents, so a year of thousands of logs fits in memory. The single-file tables of the first staging (`events.parquet` and the like) are superseded |
| To-do list | `src/eda/official_point_feeds/wta_todo.py`: [wta_todo.csv](../../../data/studies/official_point_feeds/wta_todo.csv) (one row per batch and per population the API does not serve), [wta_todo_detail.csv](../../../data/studies/official_point_feeds/wta_todo_detail.csv) (per batch, year, endpoint and draw), `data/dump/points/wta/todo.parquet` (every match and endpoint with its status; gitignored) |
| Run logs | `data/raw/point_sources/wta/_logs/` (gitignored): one line per 25 matches with the time, the year's progress, the request rate and the outcomes |
| Run summaries | [wta_calendar_summary.json](../../../data/studies/official_point_feeds/wta_calendar_summary.json), [wta_sample_summary.json](../../../data/studies/official_point_feeds/wta_sample_summary.json), [wta_stage_summary.json](../../../data/studies/official_point_feeds/wta_stage_summary.json); every run in [runs.jsonl](../../../data/studies/official_point_feeds/runs.jsonl) |
| Coverage and scope sizes | `src/eda/official_point_feeds/wta_coverage.py`: [wta_coverage.csv](../../../data/studies/official_point_feeds/wta_coverage.csv) (every year, tier, draw and endpoint), [wta_coverage.json](../../../data/studies/official_point_feeds/wta_coverage.json) |
| Checks | `src/eda/official_point_feeds/verify_wta.py`: [wta_verification.json](../../../data/studies/official_point_feeds/wta_verification.json) (totals), [wta_checks.csv](../../../data/studies/official_point_feeds/wta_checks.csv) (per match), [wta_mismatches.csv](../../../data/studies/official_point_feeds/wta_mismatches.csv) |
| Tests | `test/official_point_feeds/test_wta.py` (31 tests; fixtures `wta_*` cut from real documents) and `test_wta_todo.py` (3) |

### How the API is read

Plain GETs from `python-requests` with a User-Agent that names the project's non-commercial research. No login, key or browser fingerprint was needed; `developers.wtatennis.com` (sign-in) was not touched. The client is `feeds.FeedClient` with the shared rules above, with one difference. A 404 is this API's ordinary "no such document", so it does not count towards the five-failure stop. Instead, a long run of 404s stops a run, as a sign the API changed: 150 in a row by default, and for each batch a limit above the longest run its measured coverage allows (`absences` in `BATCHES`; `--stop-after-absences` overrides it, and 0 turns the stop off). `--max-requests` is compulsory.

| Step | Request | What was observed |
|---|---|---|
| Calendar | `/tennis/tournaments/?page=<n>&pageSize=100&excludeLevels=ITF&from=<Y>-01-01&to=<Y>-12-31` | Every edition whose dates overlap the year, keyed by `tournamentGroup.id` and `year`; an edition can start the December before. `pageInfo.numPages` reads 0 even with entries, so pages are counted from `numEntries` (2025 and 2026 need two). `excludeLevels` is always sent, because third-party code reports that without it the dates are ignored. 68 to 124 editions a year |
| Match list | `/tennis/tournaments/<id>/<year>/matches` | **Verified on Washington 2024 (54 matches).** Every match of the edition: `MatchID` LS… main singles, RS… qualifying singles, LD… main doubles; state, players with WTA ids, set scores, result, start stamp. Sent with and without the `account: wta` header third-party code uses, the answer was the same 54 rows field for field, so it is not sent |
| Per match | `/tennis/tournaments/<id>/<year>/matches/<MatchID>/<endpoint>` | `point-by-point`, `events`, `win-probability-momentum`, `advanced-stats`, `stats`; an absent document is HTTP 404 with an empty body |

**Calendar quirks:**
* 2019–2020 editions carry the tier names used before 2021; the adapter maps Premier Mandatory and Premier 5 to 1000, Premier to 500, International to 250 and 125K to 125.
* 2020 still lists the events cancelled for COVID, some without a draw size and some with one; their match lists are empty.
* The United Cup is listed as a WTA 500 without a draw.
* Qualifying doubles appear in no match list.

### The sample

* **Draw.** A seeded draw (seed 20260924). For each year 2020–2026 it took two editions of each of the 1000, 500, 250 and 125 tiers, one Finals, one Slam and one United Cup. A drawn edition whose match list held no played match was replaced by the next in the seeded order, with at most three spares per cell.
* **Matches, per edition:**
  * *two main-singles matches, all five endpoints:* the final and one other;
  * *one qualifying-singles and one main-doubles match:* point-by-point and the event log only;
  * *Slams and the United Cup:* only their point endpoints and the final's box score.
* **Result.** 64 editions, 241 matches, 848 documents. 28 candidates were replaced: 8 events cancelled in 2020, every Slam of 2020–2023 (listed without matches) and the United Cup in every year.
* **Checks outside the sample:** the 2019 finals of Washington and Birmingham; the depth check (the Charleston 2018 final's log; the 2016 list, which uses an older result format); and the first probes, including one request for RS001 at Washington 2024, which does not exist (its qualifying ids run RS004–RS015), so that 404 says nothing about coverage and is not counted.

### Coverage by year

Present over asked, pooled over the non-Slam tiers (per tier in [wta_coverage.csv](../../../data/studies/official_point_feeds/wta_coverage.csv); within a period no tier differs from the others). The 2019 row is batch B2's count over every played match, logs with points over matches; the rest are empty (until March):

| Year | Main singles: log | point-by-point | Qualifying: log | point-by-point | Doubles: log | point-by-point | Box score | Advanced stats | Win probability |
|---|---|---|---|---|---|---|---|---|---|
| 2019 (B2, every match) | 1,210/1,740: 863 complete, 347 bare | 0/2 (finals) | 567/881: 401 complete, 166 bare | – | 529/773: 380 complete, 149 bare | – | 3,394/3,394 (B3) | – | – |
| 2020 | 16/16 | 0/16 | 8/8 | 0/8 | 8/8 | 0/8 | 16/16 | 0/16 | 0/16 |
| 2021 | 18/18 | 0/18 | 7/7 | 0/7 | 9/9 | 0/9 | 18/18 | 18/18, all zeros | 0/18 |
| 2022 | 17/17 | 13/17 | 7/7 | 5/7 | 9/9 | 7/9 | 17/17 | 17/17, winner and unforced-error totals | 0/17 |
| 2023 | 18/18 | 18/18 | 7/7 | 7/7 | 9/9 | 9/9 | 18/18 | 18/18, totals | 0/18 |
| 2024 | 18/18 | 18/18 | 8/8 | 8/8 | 9/9 | 9/9 | 18/18 | 18/18, totals | 0/18 |
| 2025 | 18/18 | 7/18 | 8/8 | 4/8 | 9/9 | 4/9 | 18/18 | 18/18, full detail (B4, every draw: 6,336/6,341) | 17/18, momentum only |
| 2026 | 16/16 | 4/16 | 8/8 | 4/8 | 8/8 | 2/8 | 16/16 | 16/16, full detail (B4, every draw: 5,566/5,727) | 12/16, win probability |
| Slams 2024–26 | 0/6 (empty logs) | 0/6 | – | – | – | – | 3/3 | – | – |

**When point-by-point is served**, read from the sampled editions' dates:
* *absent:* Doha (from 20 Feb) and Indian Wells (from 9 Mar) in 2022;
* *present:* every sampled match from Charleston 2022 (4 Apr) to the 2024 WTA Finals, and at Bogotá, Rome and Cincinnati 2025, apart from the Strasbourg 2025 final and one Cincinnati qualifying match;
* *absent again:* the main draw of the Rome WTA 125 (July 2025), and everything at Tokyo, Chennai, the WTA Finals and Buenos Aires (October–November 2025) and Auckland, Hobart, Adelaide and Dubai (January–February 2026);
* *back from June 2026* (Bad Homburg, Cincinnati, Montreux, Ljubljana), except at each of those editions' finals.

Batch B8 then asked every match, and the dates hold, with the gap wider than sampled: complete until May 2025, patchy from June to September 2025, none at all from October 2025 to March 2026, and back for most matches from April 2026 ([above](#wta-official-api)).

### What a document holds

* **Point-by-point:**
  * *Fields:* `pointNumber`, `setNumber`, `gameNumber`, `server`, `pointWinner`, the game score after the point in A/B order (0, 15, 30, 40, A, G; tiebreak points as numbers), the set's score and a UTC time to the second.
  * *Traps:*
    * `sets` is the set's final score from its first point on.
    * `server` is blank on tiebreak points and on every doubles point (4,400 of 16,256 points).
    * `pointWinner` repeats the previous point's winner on some points, typically when an advantage is lost (1045/2024/LS001 points 89 and 160: the umpire's log reads "advantage in", then "deuce"). The winner has to be read from the change of score.
* **The umpire's event log:**
  * *Records:* Point, Ace and Fault; Let, Challenge and Overrule; Suspension (rain and others); violations; medical and toilet breaks; swaps of server and receiver; and state changes (on court, warm-up, in progress, changeovers, corrections).
  * *Per point:* the server's and receiver's WTA ids, the score after the point with the server's count first ("advantage in" is the server's), whether it was played on the first serve, set and game, and a millisecond UTC time.
  * *Faults:* a first-serve fault is a Fault with `firstServe` true; a double fault is a Fault without it. The sample's points were played on the second serve 33% of the time.
  * *Other fields:* each record also names the umpire and the court.
  * *Conventions that vary by year and match, all handled by the checks:*
    * Tiebreak scores are written with the tiebreak's first server first (2020), each point's server first, or the next point's server first (894/2025/LD006). Of the 59 sampled matches with a tiebreak: 10, 40 and 9.
    * Some logs (2022, 2026) write "0-0" on every tiebreak point and end the tiebreak with "game", or with nothing: play simply goes on to the next set (1160/2026/LS016).
    * A game-ending record carries its own game's number in 2020 and the next game's in 2024.
    * A second-serve point has `firstServe` false from 2022 and no `firstServe` before.
    * The whole-match `GameScore` and `MatchScore` fields are empty in 2020.
    * 73 corrections in the sample's 49 matches: most precede a let with the score unchanged; a few replace the point before them. The batches show more: a run of corrections can undo several points, even back into an earlier game, which the umpire then re-enters (2014/2026/RS024 undoes the eighth game of set 1 and the start of set 2; the `InProgress` record after each correction shows the score it restored). The checks drop the point before a correction only when the next record redoes it. Reading every correction as undoing the last record was tried on every log: it lost more matches (274) than it won (56).
    * In doubles, `server` names the team's first-listed player, and a no-ad deciding point is written only "game", so its winner is not recorded. After a `SwapServer` record (the wrong partner was down as serving), the log names the other partner within the same game (1050/2026/LD006), so games are cut where the serving *team* changes.
    * 2019's logs are empty until March and **bare** from 1 April to May: Point, Ace and Fault records with set, game and clock time, and no `Attributes`, so no score, server, winner or serve number. The 662 bare logs cannot be replayed; the checks count them apart and compare their ace records with the box score.
    * Non-point records are stamped to the second and can sit a few seconds out of order among the points.
    * In two Brisbane 2020 logs (first seen in batch B1), `Name` is shifted by one record against the rest of it ("Let" on a record typed "Point" with the score "game"). `Attributes.type` fits the scores everywhere, so the checks read it.
* **Box score (`stats`):** per set and for the match: aces, double faults, first serves in and won, service points won, break points, service games, total points won.
* **Advanced statistics:** per side, per set and for the match: winners and errors by wing, forced errors, service and return winners, fault reasons (net, out, foot fault), rally-length buckets, net approaches, break points and violations. How full they are depends on the year (table above).
* **Win probability and momentum:**
  * *Shape:* one entry per point, with each side's `momentum` and `winProbability`.
  * *2025:* the probability is 0 on every point but the last; the momentum starts with a ±9999 placeholder.
  * *2026:* most documents carry a probability on every point, but three finals hold a one-point stub.
* **Match list:**
  * *Scores:* set scores in A/B order; `ScoreTbSet` is the tiebreak loser's points, and a doubles match tiebreak is a third set of 1-0 with the loser's points.
  * *`Winner`:* 2/3 means A/B won, 4/5 by retirement, 6/7 by walkover. `ResultString` is written from the winner's side (in A/B order at the Slams).
  * *Self-contradictions:* the set fields disagree with the result string in 2 of 397 listings checked so far, both at Brisbane 2020. In 800/2020/LS010 the fields read 6-4 6-4 against "7-6(6),2-1", which the umpire's log replays to. The checks flag such listings (`listing_consistent`).
  * *`BinPacketBase64`:* an undocumented umpire-device packet (point letters and time tags), cut off after about 1 kB. It is kept verbatim and not used.

### Checks

`verify_wta.py` reads the raw documents and the match lists. Figures as of 3 Oct 2026, over everything the batches fetched (rerun after the last of them):

| Check | Result |
|---|---|
| Event log against the listed score | **34,578 of the 35,119 complete logs of 2019–2026 reproduced (98.5%)**, retirements included: 23,904 by replaying every game independently under WTA rules, and 10,674 after giving the games whose winner the log does not record (no-ad deciding points in doubles; tiebreaks written "0-0") the winners that reproduce the listing, which are therefore not an independent check of those games. By year: 1,636 of 1,644 (2019), 1,761 of 1,779, 4,189 of 4,273, 4,620 of 4,688, 5,132 of 5,181, 5,332 of 5,432, 6,249 of 6,341, 5,659 of 5,781 (2026). The 541 failures, by first difference: 263 with a game without a recorded winner that no assignment resolves, 87 with a set score that differs, 83 logs that stop before the match ends, 79 with points after the replay ends the match (48 of them in logs with a correction, whose undone points may be left in; above), and 29 with a tiebreak where the rules have none or the reverse. In the sample: 237 of 238 (718/2023/LS026's log stops after 96 of 158 points) |
| Bare logs (April–May 2019) | 662, not replayable: no winner is recorded. Their records' times are in order in all 662, and **their ace records match the box score's aces in all 662** |
| Point-by-point against the listed score | Every document (B8): **17,402 of the 20,846 reproduced (83.5%)**, against 98.5% for the event log. Point numbering is whole in all 20,846, times are in order in 20,437 and set and game numbers agree with the replay in 19,405. The `pointWinner` field is wrong on 85,763 points in 16,294 matches, so winners are read from the change of score. In the sample: 106 of 121. The failures there were documents missing points (1017/2025/LS001 holds 61 of 142; 800/2023/LD026 holds 2) or with a score string the rules cannot follow |
| Timestamps | The log's point records are in order in 34,965 of the 35,119 complete logs (in the sample, 237 of 238: one step back in 2025/2020/LS029). Point-by-point never steps back; two documents lack times on their first points |
| The two records against each other | The same number of points in 16,341 of the 20,842 matches with both. Where the counts agree, **the winners agree point for point in 16,286 of 16,341 (99.7%)**. In the sample: 101 of 121 and 101 of 101; where the counts differed, point-by-point was the one short in 16 |
| Log against the box score | Every match (B3): **aces agree in 34,967 of the 35,119 complete logs (99.6%), double faults in 34,720 (98.9%)**. The differences are small, mostly one either way (the log one double fault short in 192 matches, one over in 82), and spread over every year; 230 of the double-fault differences are in logs that still replay to the listed score. In the sample: 121 of 122 and 119 of 122 |
| Match lists | 130 of the 36,900 matches checked have set scores that contradict their own result string |

Two readings were added on 29 September after B2: games are cut where the serving team changes, not the serving player, and an unwritten tiebreak that play goes on from counts as finished with its winner open. They raised the reproduced logs from 33,917 to 34,392 (410 of the 475 in 2026) and lost none.

The rules replayed: advantage games in singles; no-ad games and a 10-point match tiebreak for the deciding set in doubles; 7-point tiebreaks at 6-6. The first test on 1045/2024/LS001 also showed that its 162 Point, 7 Ace and 12 double-fault records make the 181 points of point-by-point, and the box score's 7 aces and 12 double faults.

### Collection plan and to-do list

**Every endpoint, in batches the owner approves** (owner, 24 Sep 2026: "the goal is to eventually get every endpoint, but we will do it in batches and stages"): B1 and B2 one at a time, B3–B9 together on 29 Sep 2026 ("finish B2, then continue with B3 etc... At each step mentioning when you are done"). The plan is `BATCHES` in `wta.py`. `--batch <id>` runs a batch year by year, oldest first, and refuses any batch not marked approved. [wta_todo.csv](../../../data/studies/official_point_feeds/wta_todo.csv) gives each batch's live progress and what remains.

Sizes at the first approval (24 Sep 2026), before B1 had read the 2020–2026 match lists, and what the to-do list counted still to ask on 29 Sep:

| Batch | Endpoint | Scope | Status | Requests (24 Sep) | Hours (24 Sep) | To ask (29 Sep) | 404s in a row that stop it | Why this order |
|---|---|---|---|---:|---:|---:|---:|---|
| B1 | events | 2020–2026 | **approved 24 Sep; done 25 Sep** (33,599 + 42 requests) | 33,000 | 23 | 0 | 150 | the point sequence of every played match (option B) |
| B2 | events | 2019 | **approved 25 Sep; done 26 Sep** (3,454 requests) | 4,600 | 3.3 | 0 | 150 | the rest of the point log |
| B3 | stats | 2019–2026 | **approved 29 Sep; done 30 Sep** (36,741 requests) | 37,700 | 27 | 36,580 | 1,500 | the official box score, a check on the log |
| B4 | advanced-stats | 2025–2026 | **approved 29 Sep; done 1 Oct** (12,069 requests) | 11,200 | 8 | 11,899 | 400 | the years with full detail |
| B5 | win-probability-momentum | 2026 | **approved 29 Sep; done 1 Oct** (5,751 requests) | 5,100 | 3.7 | 5,576 | 1,000 | the year with real probabilities |
| B6 | win-probability-momentum | 2025 | **approved 29 Sep; done 1 Oct** (6,323 requests, in two parts around a PC restart) | 6,000 | 4.3 | 6,323 | 1,000 | momentum only |
| B7 | advanced-stats | 2021–2024 | **approved 29 Sep; done 2 Oct** (about 19,570 requests, in two parts around a PC restart) | 20,200 | 14 | 19,509 | 400 | zeros in 2021, totals in 2022–24 |
| B8 | point-by-point | April 2022–2026 | **approved 29 Sep; done 3 Oct** (26,384 requests) | 25,500 | 18 | 26,154 | off (400 for 2022–24) | a second point record, with gaps |
| B9 | stats | Slams 2024–2026 | **approved 29 Sep; done 3 Oct** (3,028 requests) | 3,600 | 2.6 | 3,630 | 600 | Slam box scores |
| | | | **all** | **147,000** | **105** | **109,671** | | |

Scope shared by B1–B8: tiers 1000, 500, 250, 125 and Finals, every draw. B1 and B2 took 2.51 s per request, so B3–B9's 109,671 requests take about 76 hours. B9's figure included 2,718 matches estimated for nine Slam match lists not then held; they held 2,114. In all, the batches made 147,491 requests over nine days, against the 147,000 estimated at the first approval.

**Why each batch has its own 404 limit** (`absences` in `BATCHES`). The limit sits above the longest run of 404s the batch's measured coverage allows. Matches are asked edition by edition: doubles, then main singles, then qualifying.
* *B1, B2: 150.* The log was present in every sampled match.
* *B3: 1,500.* 2019's log is empty before April, about 1,050 matches in a row, and the box score might have been too. The first three 2019 box scores asked hold data.
* *B4, B7: 400.* Qualifying and doubles were not sampled. If both lack advanced statistics, one edition's qualifying and the next edition's doubles make about 70 in a row.
* *B5, B6: 1,000.* Two of four sampled WTA 125 main-singles matches lack win probability, so whole editions may. No sampled 2025 edition before Bogotá (31 March) had been asked, so B6 might have met a long run at the start of 2025; it met 117 at most, at the editions of late December 2024.
* *B8: off.* Point-by-point is missing for months at a time (none from October 2025 to February 2026 in the sample), so thousands of 404s in a row are expected. Its 2022–24 part, where every sampled match had it, runs first with a limit of 400.
* *B9: 600.* A Slam's qualifying (112 matches) and the next Slam's doubles (63) may both lack it.

A block (403, 429, a challenge, a redirect or a reset) still stops every run at once, and five errors in a row still pause it.

**How the estimates are built.**
* *Match lists not yet held:* their matches are estimated from the lists of the same tier and year, scaled by the share of those lists with a played match.
* *Coverage not sampled:* B3–B7 ask every played match of every draw. For qualifying and doubles the sample did not ask these endpoints, so those estimates are upper bounds.
* *Figures move as batches run:* B1 reads every 2020–2026 match list, which turns the estimates into counts, and later batches then need no lists except 2019's and the Slams'.
* *Editions not played yet:* the 2026 editions still to come are counted once their matches are played. Rerunning a batch picks them up.

**Not served**, and not in any batch (`NOT_SERVED` in `wta.py`, listed in wta_todo.csv):
* point-by-point before mid-March 2022, and from October 2025 to March 2026 (found by B8);
* win probability before 2025;
* advanced statistics before 2021;
* Slam point data (empty logs, no point-by-point; Slam matches of 2020–23, the 2024 Australian Open and Wimbledon 2024 are not listed at all);
* the United Cup (empty match lists);
* qualifying doubles (none listed);
* the point log before April 2019 (empty; bare records until May), found by B2;
* 15 of 2019's 64 editions, whose match lists answer 404, found by B2;
* years before 2019.

The evidence for each is in [the coverage table](#coverage-by-year) and, for 2019, [above](#wta-official-api).

**What a document's status means** in the to-do list:
* **fetched:** saved, with data.
* **empty:** saved, without a point or a row.
* **absent:** HTTP 404, final.
* **error:** failed; the next run asks again.
* **pending:** never asked, or its file is gone.

The builder makes no request and can run while a batch is fetching.

### Running a batch, and keeping it safe

**Started** detached, so that it survives closing the editor (PowerShell):

```
Start-Process "C:\Program Files\Git\bin\bash.exe" -WindowStyle Minimized -ArgumentList '-lc "cd /c/Users/zerom/Documents/Tennis-predictions && ./python.sh -m src.ingest.point_sources.wta --batch B1 --max-requests 40000 --no-stage >> data/raw/point_sources/wta/_logs/B1_<UTC stamp>.log 2>&1"'
```

B1 started this way at 21:13:32 UTC on 24 September 2026. Its log is `_logs/B1_20260924T211332Z.log`, and its budget was 40,000 requests against the 34,000 estimated; it used 33,599.

**Queueing the next batch.** `--after-pid <pid>` makes a run wait for a running batch's process to exit. It then does not start if that run ended on a block or a streak of errors or absences (it reads the last `wta_summary.json`). B2 was queued this way on 25 September, in one detached chain whose steps each run only if the one before ended cleanly (log `_logs/queue_B1rerun_B2_20260925T220223Z.log`):

```
--batch B1 --after-pid 39064 --max-requests 2000 --no-stage   # retries B1's errors, picks up 2026 matches played since
--batch B2 --max-requests 6000 --no-stage
--stage-only --years 2019-2026
verify_wta.py --years 2019-2026
wta_todo.py
```

**The B3–B9 chain.** Approved together, B3–B9 run in the plan's order from one script, `_logs/chain_B3_B9_20260929.sh` (gitignored, with the logs). It was started detached at 17:19:58 UTC on 29 September 2026, the same way as B1 (`Start-Process … bash data/raw/point_sources/wta/_logs/chain_B3_B9_20260929.sh >> …`), and logs to `_logs/chain_B3_B9_20260929T171958Z.log`.
* *Before it:* a 3-request smoke test of B3 (Brisbane 2019's first three doubles box scores, all with data).
* *Steps:* each batch, then staging of every year and the to-do list, with the checks as well after B3 (box scores) and after B8 (point-by-point). B8 runs in two steps: 2022–24 with a 404 limit of 400, then 2025–26 with none. Last come top-ups of B1, B3, B4, B5 and B8 for 2026, to pick up matches played while the chain ran, then a final staging, checks and to-do list.
* *Budgets:* the to-do list's remaining requests plus about 15%.
* *Stops:* a step starts only if the one before ended cleanly. A block, a streak of errors or 404s, a spent budget or a crash stops the chain for a report.
* *Log lines:* the chain writes `[chain] <UTC time> start <step>` and `end <step>: exit <code>` around each step, and `stopped after <step>` or `done` at the end.

```
B3 stats 2019-2026 (--max-requests 42500), then stage, checks, to-do
B4 advanced-stats 2025-2026 (14000), B5 win probability 2026 (7000), B6 momentum 2025 (7300),
B7 advanced-stats 2021-2024 (22500), each then stage and to-do
B8 point-by-point 2022-2024 (16500, --stop-after-absences 400) and 2025-2026 (14500), then stage, checks, to-do
B9 Slam box scores 2024-2026 (4200), then stage and to-do
top-ups for 2026: B1, B3, B4, B5, B8 (3000 each), then stage, checks, to-do
```

**Relaunched after the PC restarted.** A detached chain survives closing the editor but not a restart of Windows, and Windows restarted twice on 1 October 2026:
* *13:12 UTC, during B6.* An unclean reboot: Windows logged the previous shutdown as unexpected (event 6008). The chain's last lines show Git Bash failing to start processes from about 13:08 (`fork: retry: Resource temporarily unavailable`, child exit code `0xC000026B`). They also show `end B6: exit 0`, but B6 had not finished: its last progress line reads 3,850 of 6,341, and it wrote no run summary. The rest of the chain was relaunched at 13:21 UTC from `_logs/chain_B6_B9_20261001.sh` (log `_logs/chain_B6_B9_20261001T132133Z.log`).
* *20:52 UTC, during B7.* A restart from the Start menu (event 1074), with B7 at 7,240 of 2021–24's matches. No error in the log, the receipts whole (`unreadable_lines` 0) and no partial file. Relaunched at 22:29 UTC from `_logs/chain_rest.sh B7` (log `_logs/chain_rest_20261001T222942Z.log`). It skipped the 7,271 answers already held without a request.

`chain_rest.sh "<step>"` runs the chain's steps from the named one on, with the same steps, budgets and rules, so any later interruption is resumed with one command (for example `chain_rest.sh "B8 2025-2026"`). Check first that the receipts load whole.

**Nothing is lost by an interruption:**
* *Documents:* each is written whole and then renamed into place.
* *Receipts:* each is appended after its document is saved, and a receipt line cut short is skipped on reading.
* *Cost:* an interruption at any moment costs at most the request in flight.
* *Stopping:* closing the minimised window, a reboot, a crash or `Stop-Process -Id <python pid>` all stop the run safely.
* *Resuming:* rerun the same command (a fresh log name is fine). Cached documents and 404s are not asked again, and errors are.
* *Outages:* five errors in a row (a network outage, say) pause the run for 10 minutes before it resumes, up to 12 times.
* *Blocks:* a block (403, 429, a challenge, a redirect or a connection reset) stops the run at once for a report, as the decision requires.

**Watching it:**
* the log, one line per 25 matches;
* `./python.sh src/eda/official_point_feeds/wta_todo.py`, which rewrites the to-do list and prints each batch's progress in about 10 seconds. It opens only documents too small to be sure they hold data; box scores it judges by size (an empty one is `[]`).

**After a batch:**
```
./python.sh -m src.ingest.point_sources.wta --stage-only --years 2019-2026    # the Parquet tables, one file per table and year
./python.sh src/eda/official_point_feeds/verify_wta.py --years 2019-2026    # replays, timestamps, box-score checks
./python.sh src/eda/official_point_feeds/wta_todo.py                        # what remains
```

**Approving the next batch:** set its `status` to `"approved"` and its `approved_on` date in `BATCHES`. The command to run it is in its row of wta_todo.csv.

**Backups.** The raw documents under `data/raw/point_sources/wta/` are the only copy, and they are gitignored (890 MB at the end of B9, documents gzipped; the staged tables are another 448 MB). A copy outside the working tree after each batch guards against losing the disk, which no retry covers.

### Receipts

All on 24 September 2026, 18:44–19:36 UTC: **972 requests, 738 answered 200 and 234 answered 404. No error, retry, refusal or challenge.**

| Run | Requests |
|---|---:|
| First probes: a calendar page, the match list with and without the `account` header, and seven documents of Washington 2024 | 10 |
| Calendars 2019–2026 | 9 |
| The sample (2 calendar pages refreshed, 92 match lists, 848 documents), 40 minutes | 942 |
| 2019 check (two match lists and four documents) | 6 |
| Depth check (2018 and 2016 calendars and match lists, one 2018 log) | 5 |

After these, a 3-request smoke test of batch B1 (three 2020 match lists) at 21:13 UTC, then batch B1 itself: its receipts carry `"batch": "B1"`, and wta_todo.csv counts them. The batches since, each with no refusal, challenge or pause:

| Run | When (UTC) | Requests | Answers |
|---|---|---:|---|
| B1 | 24 Sep 21:13 – 25 Sep 20:38 | 33,599 | 33,065 logs 200, one 404, two 504 errors; the rest match lists and calendar pages |
| B1 rerun | 25 Sep 22:02–22:04 | 42 | the two 504s and four new 2026 logs, 200 |
| B2 | 25 Sep 22:04 – 26 Sep 00:28 | 3,454 | 3,392 logs 200; 47 match lists 200 and 15 answering 404 |
| B3 smoke test | 29 Sep 17:19 | 3 | three box scores 200 |
| B3 | 29 Sep 17:20 – 30 Sep 18:54 | 36,741 | 36,707 box scores 200 (7 of them `[]`), 29 refreshed 2026 match lists 200; three requests retried after a server error, all answered |
| B4 | 30 Sep 18:58 – 1 Oct 03:26 | 12,069 | 11,868 advanced statistics 200, 165 answering 404, one HTTP 504 after four attempts; 29 refreshed 2026 match lists 200 |
| B5 | 1 Oct 03:29–09:10 | 5,751 | 5,095 win-probability documents 200, 613 answering 404, three HTTP 504 after four attempts; 29 refreshed 2026 match lists 200 |
| B6, first part | 1 Oct 09:17 – about 13:08 | 3,854 | 3,592 momentum documents 200, 262 answering 404; cut short by the PC's restart, so it wrote no run summary |
| B6, second part | 1 Oct 13:21–15:42 | 2,469 | 2,287 momentum documents 200, 182 answering 404; the 3,872 answered in the first part were skipped |
| B7, first part | 1 Oct 15:50–20:52 | 7,240 | 7,188 advanced statistics 200, 52 answering 404; cut short by the PC's restart, so it wrote no run summary |
| B7, second part (relaunched with `chain_rest.sh B7`) | 1 Oct 22:29 – 2 Oct 07:46 | 12,329 | the rest of 2022–24's advanced statistics (11 more 404s), and 30 failed during a 40-minute loss of the PC's connection, asked again and answered; three 10-minute pauses, 60 requests retried |
| B8, 2022–24 | 2 Oct 07:55–17:56 | 14,297 | 14,076 point-by-point documents 200, 209 answering 404, three HTTP 504 after four attempts |
| B8, 2025–26 | 2 Oct 17:56 – 3 Oct 02:21 | 12,087 | 6,644 point-by-point documents 200, 5,412 answering 404 (October 2025 to March 2026 throughout); 29 refreshed 2026 match lists 200 |
| B9 | 3 Oct 02:33–04:40 | 3,028 | 3,017 Slam box scores 200, nine match lists 200 (two of them empty: the 2024 Australian Open and Wimbledon) |
| 2026 top-ups | 3 Oct 04:45–05:07 | 525 | 191 logs, 61 box scores, 57 advanced statistics, 57 win-probability documents and 2 point-by-point documents 200 (four of them answering requests that had failed), 2 answering 404; 29 refreshed 2026 match lists 200 at each of the five |
| B8 retry, 2022–23 | 3 Oct about 05:20 | 3 | the three point-by-point documents that had failed with HTTP 504, now 200 |

### Gaps and limits

* **Thin cells.** Each year-and-tier cell holds one to four sampled matches. The coverage pattern is clear by year, but a single edition could differ.
* **Dates bracketed, not pinned:**
  * point-by-point's start lies between 9 March and 4 April 2022;
  * its 2025–26 gaps are drawn from one or two editions per period;
  * the event log's start is now pinned by B2: points from 1 April 2019, complete records from 4 June 2019.
* **Conventions inferred from the records.** No documentation was used: the log's orientations, the double-fault record and the correction rule were each confirmed against the listed scores and the box score, not against a specification.
* **Corrections that undo several points are not read.** The checks drop a point before a correction only when the next record redoes it. Longer undo runs (most common in 2026) leave the undone points in, and such a log may fail to replay. The `InProgress` record after each correction, whose score shows what was restored, would be the way to read them.
* **Not independent everywhere.** The games whose winners the log does not record (no-ad deciding points, unwritten tiebreaks) were resolved against the listing: in 10,631 of the 34,928 complete logs.
* **Bare 2019 logs.** The 662 logs of April–May 2019 hold no winners, so they give only the number of points, faults and aces per game and their times.
* **2026 is still being played.** The batches hold 2026's matches up to 3 October 2026 (one Beijing match pending); a refresh after the season adds the rest.
* **Not collected:** Slam matches (no WTA point data), the United Cup, qualifying doubles (none listed), the 15 unlisted 2019 editions, and years before 2019.
* **Terms.** wtatennis.com forbids automated access and harvesting; this was collected under the decision, whose limits it kept.

### Rerunning

```
./python.sh -m src.ingest.point_sources.wta --calendar-only --years 2019-2026 --max-requests 20
./python.sh -m src.ingest.point_sources.wta --sample --years 2020-2026 --max-requests 1500   # the seeded sample; cached answers are reused
./python.sh -m src.ingest.point_sources.wta --stage-only --years 2019-2026                  # rebuild the Parquet tables, no HTTP
./python.sh src/eda/official_point_feeds/wta_coverage.py                                   # coverage and scope sizes
./python.sh src/eda/official_point_feeds/verify_wta.py                                     # replays and checks
./python.sh src/eda/official_point_feeds/wta_todo.py                                       # the to-do list
./python.sh -m src.ingest.point_sources.wta --batch B1 --max-requests 40000                # a batch (approved ones only)
bash data/raw/point_sources/wta/_logs/chain_B3_B9_20260929.sh                               # the B3-B9 chain; rerun, it resumes
bash data/raw/point_sources/wta/_logs/chain_rest.sh "top-up B1 2026"                        # 2026 refresh: new matches, every endpoint, then checks
./python.sh -m pytest test/official_point_feeds/test_wta.py test/official_point_feeds/test_wta_todo.py -q
```

`--batch` sets the slice from the plan; `--years` can narrow it to some of its years. Without `--batch`, `--tiers`, `--draws`, `--endpoints` and `--from-date` select a slice by hand. Point-by-point asked of editions starting before mid-March 2022 would only return 404s.

## TDI Tennis Results (results.tennisdata.com)

**Every match the site listed on 25 September 2026 is collected, with the 634 older matches whose ids the Wayback Machine kept:**
* **The window:** 5,202 ATP Tour and Challenger matches completed 23 June – 25 September 2026, singles and doubles, main draw and qualifying. They include the 45 matches of 24 June, which had left the listing by the time of the sweep and survive through the research session's saved listing.
* **The Wayback ids:** 634 matches of May 2025 – April 2026.
* **All 5,836 pages were saved and parsed:** 795,162 points, every page with points, every page with its ATP code. Nothing was refused, rate-limited, challenged or reset, and nothing was retried.

**None of this was in the dump**, and no public route reaches TDI's history before the window ([access routes](../../research/granular-data-leads/access-routes-tdi-and-open-data.md)).

**Every point carries:**
* its UTC time;
* its winner, and the players serving and receiving (in doubles, which partner);
* the score after it;
* the serve events in order: fault, let, ace.

**Singles points carry more:** how the point ended (a winner, a forced or an unforced error), the rally length, the last shot (serve, return, forehand, backhand, volley), net or out, and who was at the net. This detail is present:
* at tour level on every point, in every month collected;
* at Challengers from February 2026 on.
* It began tournament by tournament. In May 2025, Bordeaux, Turin and Zagreb had it while Bogotá, Tunis and Oeiras did not. By November 2025 every Challenger had it except Lima.

**Doubles points never carry it,** at either level, in any month.

**Every page links each player's TDI id to an ATP player id,** and gives the match and set statistics, with TennisViz ratings for singles.

**Things to know before using it:**
* **The window is shorter than the research notes said, and runs by the day a match ended** ([below](#what-was-fetched-3)).
* **About 1 match in 16 has a game whose points stop before anyone won it** (366 matches, 394 games), and 72 points in 62 matches carry a winner that contradicts the page's own score. The rest replay exactly to the result ([checks](#checks-4)).
* **Where a match exists in SofaScore too, they agree in 99.9% of games** ([checks](#checks-4)).
* **The level (tour or Challenger) comes from each tournament's 2025 edition,** and 9 new events are "unknown": 8 on 25 Sep, and Levante Open from the 29 Sep forward capture ([how it was staged](#how-it-was-staged-3)).

| Item | Where |
|---|---|
| Adapter | `src/ingest/point_sources/tdi.py`: listing sweeps, match pages, forward capture, staging |
| Raw pages | `data/raw/point_sources/tdi/`, all gzipped: `listings/` (`home/`, `date/`, `tournament/`, and the research session's imports), `matches/<first two characters>/<uuid>.html.gz`; `_receipts.jsonl`, `_sweeps.jsonl` (each sweep's plan and end), `_run.lock`. 269 MB on disk (3.40 GB of HTML), after the 29 Sep forward capture |
| Staged tables | `data/dump/points/tdi/`: `matches` (6,096 rows), `points` (831,206), `statistics` (509,025, long form), `players` (1,504); from the listings `match_ids` (the id index, 5,462), `listing_cards` (11,984 sightings), `listing_pages` (203), `filter_tournaments` (94), `filter_players` (2,725). 24 MB, after the 29 Sep forward capture |
| Run summary | [tdi_summary.json](../../../data/studies/official_point_feeds/tdi_summary.json) (the last run, with the listing reports); every run in [runs.jsonl](../../../data/studies/official_point_feeds/runs.jsonl) |
| Listing reports | [tdi_listing_days.csv](../../../data/studies/official_point_feeds/tdi_listing_days.csv) (every date listing read), [tdi_listing_tournaments.csv](../../../data/studies/official_point_feeds/tdi_listing_tournaments.csv) (every tournament listing) |
| Checks | `src/eda/official_point_feeds/verify_tdi.py`: [tdi_verification.json](../../../data/studies/official_point_feeds/tdi_verification.json) (totals), [tdi_accounting.csv](../../../data/studies/official_point_feeds/tdi_accounting.csv) (every id: listed, fetched, parsed), [tdi_checks.csv](../../../data/studies/official_point_feeds/tdi_checks.csv) (every match), [tdi_field_fill.csv](../../../data/studies/official_point_feeds/tdi_field_fill.csv), [tdi_cross_source.csv](../../../data/studies/official_point_feeds/tdi_cross_source.csv) |
| Tests | `test/official_point_feeds/test_tdi.py` (33 tests; fixtures `tdi_*`: two listings and four match pages cut from the pages the research session saved on 24 Sep) |

### What was fetched

**The site** is Next.js on Vercel behind Cloudflare. Pages are rendered on the server with their data in the React Server Components payload (the `self.__next_f.push` strings), so no JavaScript runs; `/api/trpc` was never called. The client is the shared `feeds.FeedClient` (`curl_cffi` with the Chrome profile), 2 s apart plus up to 1 s of jitter.

**The listings.**
* `/en?date=YYYY-MM-DD` lists one day's completed matches, `/en?tournamentId=<uuid>` one tournament's, `/en` the last few days'. A date outside the window is answered with the default list.
* **The window keeps about 92 days by the day a match ended, and a listing groups matches by their start.**
  * On 24 Sep, 24 Jun listed 45 matches. At 14:22 UTC on 25 Sep it had gone entirely, and was answered with the default list.
  * 23 Jun still listed one match, a Copa Internacional de Tenis round of 32 stamped 23 Jun 19:14 UTC. Its page says it was completed on 25 Jun 14:36.
* **24 June was rescued.** The research session had saved that day's listing on 24 Sep. It is kept with a receipt marked `imported`, with that session's other five saved listings.
* **The sweep.** It read the default list, then every day from 22 Jun to 25 Sep oldest first (the window's edge was sliding), then every tournament in the filter. It was planned in `_sweeps.jsonl` when it started, and a sweep interrupted is resumed with its plan.

**What the listings showed** (sweep 20260925T1422Z, 14:22–14:31 UTC):
* 95 days in the window, 23 Jun – 25 Sep. A day listed a median 55 matches and at most 93. There is no sign of a cap.
* **Date and tournament listings agree completely.** 85 tournaments listed matches, and the Laver Cup, in the filter, had none yet. Every match of the date listings is in its tournament's listing and every match of a tournament listing is on its day. No match differs between listings in time, round, tournament or players.
* **Matches without a listing day.** Some ids have no date listing to their day, but none that the sweep's own listings should have held:
  * the 45 of 24 Jun (only the saved copy lists them);
  * the 16 found by the catch-up pass at 19:21 UTC, finished after the sweep's 14:26 read of 25 Sep.

**The match pages.**
* `/en/results/<uuid>` answers HTTP 200 inside the window, and HTTP 404 outside it with every point still in the page.
* **The rule for a 404:** the adapter keeps one when it carries the match's own point ids, and records one without them as absent. `common.fetch`, which drops every 404, is not used for match pages, and is unchanged.
* **The order:** the index's matches oldest first, then the Wayback ids ([tdi_wayback_match_ids.csv](../../../data/studies/granular_data_leads/tdi_wayback_match_ids.csv)). They were fetched in 12 batches of up to 500 requests, each a run of its own.

| Pages | Matches | HTTP 200 | HTTP 404 with points | Absent |
|---|---:|---:|---:|---:|
| The window (23 Jun – 25 Sep 2026) | 5,202 | 5,157 | 45 (24 Jun) | 0 |
| The Wayback ids (May 2025 – Apr 2026) | 634 | 0 | 634 | 0 |

**The window's matches by level and draw:**

| Level | Singles, main draw | Singles, qualifying | Doubles, main draw | Doubles, qualifying | All |
|---|---:|---:|---:|---:|---:|
| Tour (13 tournaments) | 458 | 165 | 194 | 3 | 820 |
| Challenger (64) | 1,912 | 1,068 | 909 | – | 3,889 |
| Unknown (8 new events) | 239 | 144 | 110 | – | 493 |
| **All** | **2,609** | **1,377** | **1,213** | **3** | **5,202** |

**By month completed:** June (23–30) 302, July 1,889, August 1,622, September (to the 25th) 1,389.

**The Wayback ids by level and draw:** Challenger singles 255 main and 137 qualifying, Challenger doubles 102, tour singles 81 main and 9 qualifying, tour doubles 50.

**By month:** May 2025 145, October 2 and November 133, February 2026 83, March 131 and April 140.

### What a record holds

**The title and description.**
* *The title,* e.g. "A vs B | 2026#7395#MS016 | Tennis Results", gives the ATP year, tournament id and match code (MS, QS, MD, QD).
* *The meta description* adds the event, the place and the score, from the winner's side: "Match 2026#7395#MS016 - Men's Singles at Buenos Aires 2 \r\n 6/1 4/6 6/2", and for a retirement "6/0 1/0 RET".

**The header.**
* *The match:* "Completed on <date> at <tournament> in <place>".
* *Each player,* in an element keyed by the TDI player uuid: the ATP headshot URL, whose last part is the ATP player id (`…/player-headshot/C0DF`), then the full name, country, short name and seed or entry note.
* *The scoreboard:* games per set, with tiebreak points.

**The points** (`ExpandedPointDetails`, id `<match uuid>-<set>-<game>-<point>`):
* **Clock:** `time` on 99.8% of points, and `completedDateUtc` only on recent pages (every page of September 2026, almost none before August).
* **Who:** `winner`, `teamServing`, and `playerServing` and `playerReceiving` as player uuids.
* **Score:** both teams' point score after the point (advantage is "Av"), and their games in every set.
* **`rally`:** the serve events in order: SERVE, FAULT, LET, ACE, POINT_COMPLETE. A first-serve fault reads SERVE/FAULT/SERVE/….
* **`pointBreakdown`:**
  * `outcome`: winner, forced, unforced;
  * `serve`: FIRST, SECOND, ACE, DOUBLE FAULT;
  * `totalShots`: the rally length;
  * `winningShotType`: the last shot: serve, return, forehand, backhand, volley;
  * `errorType`: out or net, on error points only (about 70% of points);
  * `situation`: baseline, serving, returning, player1_at_net, player2_at_net, both_at_net.
* **Flags:** ace; break point and break point saved; deuce; game point and set point, naming the team that has it; game and set won; the streak.

**The statistics** (the Summary tab). For the match and every set, 25 rows of "value A | label | value B" under six headings:
* Points;
* Service;
* Returns;
* Winners and Errors;
* Quality: the TennisViz Performance Rating, and Serve, Return, Backhand and Forehand Shot Quality, all 0–10;
* Attack & Defense: Shots In Attack, Conversion Score, Steal Score.

The TennisViz rows read "–" where a match has no ratings:
* doubles never have them;
* singles have them wherever the outcomes are present: tour singles in 2026 on 675 of 679 matches, Challenger singles in 2026 on 2,781 of 3,167.

**Field fill.** The share of points carrying the outcome, rally length, last shot and net position:

| Points | Share with the detail |
|---|---|
| Tour singles, every month (main and qualifying) | 99–100% |
| Challenger singles, May 2025 | 42% main draw, 56% qualifying |
| Challenger singles, November 2025 | 81% main draw, 99% qualifying |
| Challenger singles, February 2026 on | 98–100% |
| Doubles, tour and Challenger, every month | 0 |

Serve number, faults, lets, aces and double faults are on every point of every match. [tdi_field_fill.csv](../../../data/studies/official_point_feeds/tdi_field_fill.csv) has every field by level, draw and month.

### How it was staged

All tables are strings with the dump's provenance columns.
* **`matches`:** one row per match id of the index and the Wayback list, with:
  * the answer: 200, or 404 with points;
  * the title's ATP code and the description;
  * the header: tournament, place, completion time, and both teams' TDI ids, ATP ids, names, countries, seeds and set scores;
  * the listing's day, round and tournament;
  * counts: points, points with an outcome or a completion time, and statistics periods.
* **`points`:** one row per point:
  * identity, clock, winner, server and receiver;
  * the scores after the point, and the flags;
  * `pointBreakdown` flattened;
  * the rally kept as "SERVE/FAULT/SERVE/POINT_COMPLETE", with its fault and let counts.

  A key not seen in the samples would go to `extra`; none did. 25 pages write a repeated streak as a reference to an earlier one ("$62:props:children:props:details:2:streak"), and those are resolved.
* **`statistics`:** one row per statistic, period ("match", "1", "2"…) and heading, both values verbatim.
* **`players`:** one row per TDI player uuid on the pages, with the ATP id, names and country.

**The level.** Tour or Challenger is the level of the title's ATP tournament id in Jeff Sackmann's archive (`data/dump/matches/sackmann_archive/atp`): A, M, F, G, D or O is tour, and C is Challenger.
* *The edition used:* the archive's 2026 files end in May, so for a window match the level is its tournament's 2025 edition's (`level_source` names the year). Two events labelled Challenger from 2025 have tour-250-shaped draws in 2026 (28 players, 16-player qualifying): Estoril (id 7290, "Millennium Estoril Open") and Cancún (3009, "Cancun Country Open"). Their 2026 level is uncertain.
* *Ids the archive lacks:* a tournament whose name says Challenger is labelled so (11 tournaments). The rest is "unknown": 8 events new in 2026, 493 matches, all with Challenger-shaped draws (32 players, 24-player qualifying [inference]). They are Liège (3101), Istanbul "ENKA Open" (3111), Kingston 1 and 2 (3121, 3129), Indianapolis (3131), Sion (3133), Samsun (3167) and "Tennis Warehouse Open" (3175). The shape alone cannot settle their level, because Washington, a tour event, has it too.

### Checks

`verify_tdi.py` reads the staged tables. For the comparison it reads SofaScore's and TennisLive's through the point_shot_sources study's links: that study's `ref_id` carries the ATP code ("CH12:atp:2026/741/ms008:G0EU"), the same as a TDI title's, so the join is exact.

**The replay.** Each game is replayed from its point winners, game by game as TDI numbers them, under the ATP's rules:
* advantage games in singles, no-ad games in doubles;
* tiebreaks to 7;
* in doubles, a match tiebreak to 10 in place of a third set.

The games won in each set are compared with the header's scoreboard, and the score with the description's.

| Check | Result |
|---|---|
| Accounting | 5,836 of 5,836 ids listed or kept by the Wayback, fetched and parsed. Every page holds points |
| Replay | **5,351 matches (91.7%) reproduce the header's score exactly**, and 99 more (1.7%) are retirements that reproduce the score where play stopped. **366 (6.3%) have a game whose points stop before anyone won it**: 394 games, one in most matches, often a tiebreak or a match's last game. 20 (0.3%) replay to another score; 11 of them contain a point whose winner contradicts the page's own score |
| Winners against the score | 72 points in 62 matches carry a `winner` other than the side the score shows won them: the point score's change, or on a game's last point the side whose games went up |
| Score against the description | 5,447 of 5,469 checkable matches (those without a stopped game). The other 22 are the 20 that replay to another score and 2 that reproduce the header but not the description |
| Aces and double faults against the page's own statistics | Aces agree in 5,792 matches of 5,836; of the 44 others, 36 have points missing. Double faults agree in 5,753; of the 83 others, 40 have points missing and 37 replay exactly, so there the page's count and its points' differ |
| Duplicates | None: no point id twice, no set-game-point twice, every id's numbers equal the fields' |
| ATP code | On all 5,836 pages |
| Clock | In 15 matches the times step back, 869 times in all, 707 of them in 5 matches (Lexington 2026 MS004 has 195). 96 points end before they start. 1,687 points (0.2%) have no time |

**Against SofaScore and TennisLive** (125 singles matches of the ten reference careers: 114 in the window and 11 among the Wayback ids):

| | SofaScore | TennisLive |
|---|---|---|
| Games compared | all 125 matches; TDI has 5 games SofaScore lacks | 124 matches; TDI has 207 games TennisLive lacks (tiebreaks and last games) |
| Game winners | 99.93% agree | 89.6% |
| Game servers | 99.22% | 11.6%, and 88.4% with TennisLive's server marker read as the other player |
| Points per game, and the score after each point | 99.7% | 90.4% and 81.9%: TennisLive's lists skip some points |
| Every game the same | 93 of 125 matches | 1 of 124 |
| Aces, double faults against their statistics | 123 and 121 of 125 | 115 and 111 of 124 |

SofaScore's point lists are the more complete. The disagreements with TennisLive are its gaps, not TDI's.

### Gaps and limits

* **History.** Nothing lists matches before the window. The 634 Wayback ids are a few percent of the roughly 20,000 matches of January 2025 – June 2026. Pages of old matches still serve their points, so any id found later can be fetched.
* **Per point, the site has none of:**
  * serve speed or placement;
  * ball or player coordinates;
  * in doubles, the outcome, shot, error and net position;
  * a completion time before August 2026.
* **Record faults** (above):
  * games whose points stop early;
  * winners that contradict the score;
  * a few matches with disordered times.
* **Matches the site lacks.** Walkovers appear not to be listed [inference: no page lacks points, and a few rounds are one match short, such as the Canada Masters' round of 64, 31 of 32]. The Canada Masters listed 16 first-round qualifying matches and no second-round ones, where Cincinnati listed all 36. The site lacks the rest, since the date and tournament listings agree.
* **Level:** as above, the 2025 edition's level, 9 unknown events (Levante Open since 29 Sep) and 2 uncertain.
* **Terms.** TDI's terms forbid scraping and use for statistical models or betting. This was collected under the owner's decision of 25 September, within its limits.

### Receipts

All on 25 September 2026, 14:22–19:22 UTC. **6,024 requests brought 6,024 documents.** No 403, 429, challenge, redirect or reset, and no retry.

| Run | Requests | Time |
|---|---:|---|
| Pilot: the default list and 22–24 Jun | 4 | 14:22 |
| The listing sweep | 179 | 14:23–14:31 |
| Pilot: 20 window pages across levels and months, and 4 Wayback ids | 24 | 15:16–15:17 |
| 12 page batches: the window, then the Wayback ids | 5,796 | 15:18–19:21, 2.5 s a request |
| Catch-up (`--recent 3`): the default list, 22–25 Sep, and 16 new pages | 21 | 19:20–19:22 |

The research session's six saved listings of 24 Sep were added without a request (receipts marked `imported`).

### Forward capture

```
./python.sh -m src.ingest.point_sources.tdi --recent 10 --max-requests 1000
```

**What it does:** a sweep of the default list and the last ten days (the week, and the days still filling up; no tournament listings), then the page of every indexed match not yet saved.

**Cost and cadence:** about 500 requests (25 minutes) a week. The listing keeps about 92 days by completion day, so a missed week is caught up by the next run. A gap of more than about 90 days between runs loses the matches that fell out.

**Runs** (each also a line in [runs.jsonl](../../../data/studies/official_point_feeds/runs.jsonl)):
* **29 Sep 2026, 17:23–17:41 UTC.** The default list and 22–29 Sep (19–21 Sep were settled, so not asked again), then 260 new pages: 269 requests, each answered, with no retry or block.
  * The 260 matches were completed between 25 Sep 20:11 and 29 Sep 17:01 UTC: 64 tour, 151 Challenger and 45 at events of unknown level. They hold 36,044 points.
  * They were checked with `verify_tdi.py`'s own functions, on these 260 only; its evidence files still cover the first 5,836. 240 replay exactly, 3 are retirements that match, and 17 have a game whose points stop early; 1 point's winner contradicts the score. Aces and double faults agree with the page's statistics in 514 of 520 counts. How each singles point ended is on 99–100% of points at both levels.
  * Levante Open (35 matches) is a ninth event of unknown level.

### Rerunning

```
./python.sh -m src.ingest.point_sources.tdi --max-requests 200                        # a full listing sweep, or resume one
./python.sh -m src.ingest.point_sources.tdi --pages --wayback-ids --max-requests 500 --no-stage   # a batch of pages
./python.sh -m src.ingest.point_sources.tdi --recent 10 --max-requests 1000           # forward capture
./python.sh -m src.ingest.point_sources.tdi --stage-only                              # rebuild every table, no HTTP
./python.sh src/eda/official_point_feeds/verify_tdi.py                                # the checks
./python.sh -m pytest test/official_point_feeds/test_tdi.py -q
```

**Interruptions:**
* Every fetch has a receipt, and a page is written whole before it replaces anything. Nothing saved is asked for again, so an interrupted command is continued by running it again.
* One run fetches at a time: the next waits for the OS lock on `_run.lock`, which is released if the process dies.
* A run exits 1 only when it was stopped: a block, five fetches in a row without a document, or failed staging.

**Backup.** The raw pages are the only copy of the matches that have left the window. They are gitignored (257 MB), so a backup outside the working tree is worth considering.
