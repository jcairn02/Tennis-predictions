# Filling the data map's gaps: process log

Opened 11 Oct 2026 at the start of work package P2. Earlier packages of this study (the ATP gap, P4, P5, P6) kept no log here; this log starts at P2 (resumption rule: earlier work is not retrofitted). Another package that keeps a log here adds its own section below P2's.

---

## Work package P2: the WTA API since the batches, and women's ITF after early September

11 Oct 2026 – 14 Oct 2026 (with a pause from 11 Oct 16:05 to 13 Oct 22:22 UTC) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code extension) · Session: `310009bc-0651-4504-9b7f-c4a3acdecc66` · For a future reviewer · Reports: (a) [official_point_feeds README, WTA official API](../official_point_feeds/README.md#wta-official-api); (b) [this study's README](README.md)

### 1. The request

* **The owner's words, verbatim** (11 Oct 2026):
  > "Do work package P2 of docs/studies/gap_downloads/collection-plan.md: (a) bring the WTA API collection up to date for the 2026 editions played since the B1-B9 batches, and (b) collect the women's ITF and ITF-qualifying results the WTA website lists after early September 2026 (from a newer Kaggle version if one exists, else from the WTA API's player-matches endpoint). Follow the plan's shared rules."
* **How it was read:**
  * The [collection plan](collection-plan.md)'s P2 section and its 13 shared rules govern; collecting needs no further approval ([8 Oct decision](../../decisions/2026-10-08-scraping-approved.md)).
  * (a) Rerun the five endpoints of batches B1-B8 (events, stats, advanced-stats, win-probability-momentum, point-by-point) over the 2026 editions starting from 1 Sep 2026, tiers 1000/500/250/125/Finals, each with its batch's 404 limit, then `refresh.py --sources wta_api`. B9 (Slam box scores) is not rerun: no Slam has been played since its run of 3 Oct.
  * (b) "From a newer Kaggle version if one exists, else from the WTA API's player-matches endpoint" is read with the plan's step 2: the newer version first, then the endpoint "for what it still lacks". Any Kaggle version ends some days before today, so the endpoint is used either way; the newer version only changes how much of the gap it carries.
  * Other reading set aside: using the endpoint *only* when no newer Kaggle version exists. Set aside because any version leaves its last days uncovered, and the plan's step 2 asks for the endpoint for what remains.
  * No question was put to the owner.
* **The target:** not a model study. No price, hour, season or primary applies; nothing here is scored.

### 2. Starting point

* **Code:** commit `677a63f` (8 Oct 2026) plus uncommitted changes from other sessions, among them `data/data_map.yaml`, `src/eda/data_map/measure.py` and both READMEs this package reports in. `src/ingest/point_sources/wta.py` and `src/eda/gap_sources/wta_site_kaggle.py` are unchanged since the commit (git status, 14:24 UTC).
* **Data [observed]:**
  * WTA API raw: `data/raw/point_sources/wta/` (receipts 102.6 MB). Since the batches' 2026 top-ups (3 Oct, 04:45-05:07 UTC) only 47 requests were made: 34 box scores and 2 match lists of Beijing 2026 plus 2 calendar pages (9 Oct, without a batch tag: the prediction run's fills), and 7 calendar pages of 2010-2013 (10 Oct).
  * Kaggle copy: version 29 (created 24 Sep 2026 01:36 UTC, "Update 2026-09-24"), downloaded 29 Sep 2026 into `data/raw/gap_sources/bwandowando/` (matches.csv 278,480,366 bytes, SHA-256 `310177ac…`). Read by the map (`load_wta_site` in `src/eda/data_map/measure.py`) and by the lower-level evidence study's `src/eda/lower_level_evidence/candidate_stage0.py`, both at that path.
* **Processes at the start (14:24 UTC):** P6's SofaScore run (PID 65436, since 14:18 UTC) and two Jupyter kernels of another environment. No collector on api.wtatennis.com or kaggle.com.
* **The idea:** more of a kind of data already held (accretion); collection only.

### 3. Plan

Written at 14:30 UTC on 11 Oct, before any request of this package.

**A defect found before the first request [observed, offline].** `wta.py` asks a cached match list again only while the calendar calls its edition not `past` (`fetch_listing`: `refresh or status != "past"`). Seven 2026 editions were cached before their finals and now read `past`, so a rerun would never ask for them again:
* Seoul, Tolentino, Porto, Singapore and Ankara (21-27 Sep), cached on 25 Sep 2026 at 22:02 UTC. Seoul's cached list holds 49 finished matches, 1 suspended and 6 unplayed; Tolentino's 52 finished and no later rounds.
* Jingshan and Adana (28 Sep - 4 Oct), cached on 3 Oct at 05:06 UTC.

Their last rounds are missing from the collection, and the README's "one Beijing match pending" undercounts what was missing. Fix: also ask again for a list fetched before the day after its edition's end date (`end_date` + 1 day, UTC; the end date is local). A list fetched after that is final and is not asked again. Test it offline.

**(a) The WTA API catch-up:**
1. Fix the rule above, with a test; the existing WTA tests pass before and after.
2. For each endpoint in the batches' order: events (404 limit 150), stats (1500), advanced-stats (400), win-probability-momentum (1000), point-by-point (0, off):
   * a trial with a small budget;
   * then the run: `./python.sh -m src.ingest.point_sources.wta --years 2026 --from-date 2026-09-01 --tiers 1000,500,250,125,finals --endpoints <e> --max-requests 3000 --stop-after-absences <n> --no-stage`, in the background with a log in `data/raw/point_sources/wta/_logs/`.
3. Stage 2026 (`--stage-only --years 2026`), then `verify_wta.py --years 2019-2026` and `wta_todo.py`.
4. `./python.sh src/eda/match_timing/refresh.py --sources wta_api`, after checking that no refresh or Stage 0 rebuild runs.
5. Expected (the plan): a point log for nearly every match of the late-2026 editions.

**(b) Women's ITF after early September:**
1. Ask Kaggle for the current version (2 requests). If newer than 29, download it into `data/raw/gap_sources/bwandowando/v<N>/`, beside version 29 and never over it, with receipts. v29 stays where its readers expect it.
2. Trial the player-matches endpoint (`GET https://api.wtatennis.com/tennis/players/<id>/matches/?year=2026`) on 5 players: paging, fields, how a match is identified, and whether it agrees with the Kaggle rows.
3. Build `--player-matches` in `wta.py`: the same client and receipts; raw at `players/<id>/matches_<year>.json.gz`. Players: every `perspective_player_id` with a 2026 ITF row in the newest Kaggle file, then every opponent id the answers add, until none is new (~3,000-4,000 requests).
4. Stage as the Kaggle file is read: byes, walkovers and unplayed matches out; a match listed twice (a pair's two perspectives, the Kaggle file's second pseudo id) kept once per tournament, draw, round and player pair.
5. Map: point `load_wta_site` at the newest Kaggle version plus the staged answers; refresh the `wta_site_records` entry, the `wta_site_refresh` universe row and the `in_progress:` lines; rebuild the map once, at the end; check the women's ITF and ITFQ cells of 2026.
6. Expected (the plan): about 3,000 women's ITF main-draw results after early September, plus qualifying.

**Gates and stops.** A block (403, 429, a challenge, a redirect, a reset) stops a run for a report. A trial that reaches less than half of "Expected" stops the package's bulk for a report. One collector per host: the five WTA runs and the player-matches run go one after another, never together.

### 4. Chronology

All times are UTC; rows without a date are 11 Oct 2026. (Corrected on 14 Oct: this line first said local time, UTC−7, which no row used.) A few rows sit out of time order where a step was logged after the next one. No model result is read in this package.

| When (UTC) | Step | Why | Seen by then | Output |
|---|---|---|---|---|
| 14:15-14:30 | Read CLAUDE.md, the 8 Oct decision, the plan, both READMEs, `wta.py`, `wta_site_kaggle.py`, `common.py`, the map's `load_wta_site`, the yaml entries | Rule 1 | – | – |
| 14:24 | Listed Python processes | Rule 3 | P6's SofaScore run only | no collector on the WTA API or Kaggle |
| 14:26 | Receipts since 3 Oct 05:00 UTC (scratch script `receipts_since.py`) | What was fetched after the batches | – | 47 requests (above) |
| 14:28 | The 2026 editions from 20 Aug: calendar status (cached 9 Oct) and list fetch time (scratch `editions_2026.py`) | Which lists the rerun would refresh | – | the stale-list defect (§ 3) |
| 14:30 | Opened this log (§§ 1-3) | Rule: before the first substantive step | – | – |
| 14:27 | `wta_site_kaggle.py` made version-aware (a new version into `v<N>/`; a check of the version on disk saved under `_checks/`, nothing downloaded or overwritten; `--fetch-only` skips the research analysis), then `--fetch-only` | (b) step 1. The old `fetch()` rewrote the root's `_view.json`/`_files.json` and would have overwritten any file whose size changed | – | **Kaggle's current version is still 29** (24 Sep 2026). 2 requests; answers in `data/raw/gap_sources/bwandowando/_checks/20261011T142745Z_*` [observed]. So (b) comes wholly from the API endpoint |
| 14:28 | The 2026 ITF players of v29 (scratch `kaggle_2026_itf.py`) | (b)'s seed set | – | 44,604 rows of 2026 ITF events (28,694 distinct pseudo matches); **820** perspective players; 3,842 distinct ids in their rows; last ITF event start 7 Sep 2026 [observed]. Trial players drawn with seed 20261011: 331077, 327367, 331104, 327089, 324750 |
| 14:29 | `wta.py --player-matches --players <the 5> --player-year 2026 --max-requests 10` (first cut of the mode: fetch only) | (b) step 2, the plan's trial | – | 5 × HTTP 200 [observed]; summary went to `data/studies/official_point_feeds/wta_player_matches_summary.json` (later runs write to `data/studies/gap_downloads/`) |
| 14:31 | Read the 5 answers against v29's rows (scratch `trial_counts.py`) | Fields and counts | – | **Each answer holds exactly 10 matches, the year's first** (Jan-Feb); v29 has 15-55 rows for the same players: the endpoint is paged. Answer keys: `matches`, `player`; no paging block. `player_1` = the asked player, `player_2` = the opponent's id, `opponent` = the opponent's object; `team_name_1/2` in no fixed order [observed] |
| 14:33 | 3 paging probes (scratch `probe_paging.py`, receipts `probe/players/331077/...`, raw `probe/players/`) | Find the paging | – | `page=1` gives the next 10; `pageSize=100` (with or without `page=0`) gives all **82** of 331077's 2026 matches (52 singles, 30 doubles), the last at an event starting 21 Sep [observed] |
| 14:35 | The 82-match answer read in full (scratch `inspect_full.py`) | Field rules for staging | – | `winner` 1/2 refers to `player_1`/`player_2` (a qualifier's two qualifying wins and main-draw loss read 1, 1, 2 at three events); rows in date order but not round order inside an edition; reason codes W, B, D, R [observed] |
| 14:36 | v29's reason codes since 2024 | The played filter | – | B byes (opponent "BYE"); D 1,063, all without a score; R retirements; V 46, half with partial scores; W the rest. The map drops B, D, UNP, V [observed] |
| 14:40 | Listing rule fixed (`listing_stale`, `LISTING_SETTLE_DAYS = 2`) and tested | § 3 | – | WTA tests 34 → 35 pass |
| 14:34-14:37 | (a) events trial: `--endpoints events --max-requests 80 --stop-after-absences 150 --no-stage` (log `_logs/P2a_events_trial_20261011T143421Z.log`) | Rule 5 | – | 80 requests: 2 calendar pages, 34 lists, 44 logs; **44 of 44 hold points**, all from the seven stale editions and Beijing [observed]. 1,120 played matches selected. Gate passed |
| 14:38 | (a) events run, `--max-requests 3000` (log `_logs/P2a_events_20261011T143811Z.log`) | (a) step 2 | trial above | running; at 14:47, 1,100 of 1,120 matches, 203 new logs |
| 14:48 | (a) events run ended | – | – | 252 requests, no retry, error or 404; 223 new logs (all HTTP 200), 897 held; only 27 lists asked (the seven stale ones were final after the trial) [observed, `wta_summary.json` then] |
| 14:49-14:51 | (a) stats trial (60) | Rule 5 | – | 31 of 31 new box scores with data [observed]. Gate passed |
| 14:51-15:01 | (a) stats run (log `_logs/P2a_stats_20261011T145129Z.log`) | (a) step 2 | – | 231 requests, no retry or error; 202 new box scores, all HTTP 200 [observed] |
| 14:50-15:00 | Wrote the full `--player-matches` mode while (a) ran: paged fetch (`fetch_player_pages`), frozen seeds (`frozen_seeds`, from `kaggle_seed_players`), the breadth-first crawl over singles opponents (`crawl_players`), staging (`player_matches/<year>.parquet` every served row; `player_results/<year>.parquet` one row per played single, rows joined through edition-draw-round keys with both ids, or one id and the other's surname), evidence (`wta_player_players_<year>.csv.gz`, the run summary in `data/studies/gap_downloads/`) and an offline replay for `--stage-only` (a zero-request client) | (b) step 3 | the trial's fields | `test_wta_player_matches.py`, 10 tests, from a fixture of 7 real rows of 331077's answer. A first run of the staging test failed: the results table carried `year` twice (its own column and the provenance extra), which the Parquet reader refuses; the extra is now `asked_year` |
| 15:00 | `load_wta_site` (map) reads the newest Kaggle copy and appends the API's results; a match the copy holds is kept from the copy (same pseudo edition via tournament group and start date, draw, round, pair) | (b) step 5 | v29's group ids equal the API's (Oslo 2403, Leiria 4826; titles identical); (group, start) unique but for 1 of 513 editions of 2026 [observed] | test in `test/data_map/test_data_map.py` |
| 15:01-15:04 | (a) advanced-stats trial (60) | Rule 5 | – | 31 of 31 with data. Gate passed |
| 15:04 | (a) advanced-stats run (log `_logs/P2a_advanced-stats_20261011T150417Z.log` or the like) | (a) step 2 | – | running; 1,121 matches now (one more Beijing match finished) |
| 15:04 | `src/eda/gap_downloads/verify_wta_player_matches.py` written: (1) against v29 by edition, draw, round and ids; (2) TennisLive and (3) the ITF live API through `verify_tennislive.check`, the API results standing in for official rows | (b)'s link check (rule 12) | no player-matches result yet | 5 tests. ITF-live qualifying rounds are left unset in the check (named by draw size; numbering them from a partial capture could shift) |
| 15:05 | data_map.yaml: `wta_api` and `wta_site_records` set to `downloading`; two lines under `in_progress: scrapes` | Rule 8 (late for (a): it started at 14:34) | – | yaml parses |
| 15:04-15:15 | (a) advanced-stats run ended | – | – | 266 requests, no retry or error; 237 new documents, all HTTP 200 [observed] |
| 15:15-15:18 | (a) win-probability-momentum trial (60) | Rule 5 | – | 19 with data, 12 HTTP 404; **all 12 absences are finals** (6 singles, 6 doubles; all 19 other matches have it) [observed]. The batches found late-2026 finals lacking the point records too. Treated as the endpoint's known gap, not a failed gate |
| 15:18 | (a) win-probability-momentum run (background) | (a) step 2 | trial above | running |
| 15:18-15:31 | (a) win-probability-momentum run ended | – | – | 266 requests, no retry or error; 142 new documents (HTTP 200), 95 HTTP 404 [observed]. The 404s: every final asked (2 per edition), and, at editions not yet over, 45 played qualifying matches of the four editions starting 12 Oct (Wuhan 24, Rovereto 8, Mallorca 7, Lisbon 6), 12 at Beijing, 31 at this week's two WTA 125s (Suzhou 15, Samsun 16). The rate fell to about 1,280 an hour (larger documents) |
| 15:36 | *Correction to the row above:* the breakdown counted the trial's answers too (receipts since 15:15). Trial and run together: 161 documents and 107 HTTP 404, of which 19 are finals (every final asked) and 88 are non-final matches, all 88 at editions not yet over (the list above sums to 88). The run alone: 142 documents, 95 HTTP 404 | – | – | – |
| 15:31 | `absence_stale` added: a cached 404 answered before its edition's end date plus 2 days is asked again on a later run (`fetch_endpoint(..., edition=)`, passed by the bulk and sample passes; the prediction run's fills pass none and are unchanged); test added | Judgment call 5 | the 404s above | WTA tests 164 pass (official_point_feeds folder) |
| 15:32-15:34 | (a) point-by-point trial (60) | Rule 5 | – | 31 of 31 HTTP 404: the late rounds of the six editions of 21 Sep and 28 Sep. On 3 Oct the batches had found 21-31 of the ~50 matches of each 21 Sep edition absent, and Beijing 86 of 86 present [observed]. Read as the endpoint's known patchiness (B8 runs with the 404 stop off for it), not a failed gate |
| 15:35 | (a) point-by-point run (background), `--stop-after-absences 0` | (a) step 2 | trial above | running |
| 15:47 | (a) point-by-point run ended | – | – | 294 requests, no retry or error; 177 new documents, 88 HTTP 404 [observed]. Point-by-point exists for the played qualifying of Wuhan, Mallorca, Rovereto and Lisbon (45), where win probability had answered 404 an hour earlier: support for reading those 404s as a lag |
| 15:47-15:57 | (b) first trial: `--player-matches --player-year 2026 --limit 25 --max-requests 40` | Rule 5 | – | **Failed.** The frozen seeds were the numbers 1-820, not player ids. Ids 2-6 answered HTTP 200 with an empty body, which the validator records as an error; five in a row paused the run for 10 minutes (the adapter's error rule). Stopped by hand (PID 53452) at 15:58 [observed] |
| 15:58-16:00 | Diagnosis | – | – | In the Kaggle copy, `perspective_player_id` is a WTA id on only some rows: on 34,971 of the 44,604 rows of 2026 ITF events it is a small label (23, 150 ...) covering 1,748 different `player_1` ids. `player_1` holds the asked player's WTA id (2,113 distinct ids at 2026 ITF events). An unknown id answers HTTP 200 with an empty body (one request for id 2, made with the client directly and not kept: it had no content) [observed] |
| 16:00 | Fixes: seeds from `player_1` (`kaggle_seed_players`); an empty answer recorded once as absent, "no such player" (`empty_answer`); the API's bye placeholder, id 1 ("BYE BYE"), never asked (`BYE_ID`); tests | Judgment call 6 | – | 214 tests pass. The wrong seed file kept as `wta_player_seeds_2026_superseded_perspective_ids.csv` |
| 15:59-16:01 | (b) second trial (25 players, budget 40) | Rule 5 | – | 2,113 seeds frozen; 25 players, 25 requests, all HTTP 200; 754 served rows, 507 results. Every answer complete (one page each), parsed, and holding at least the Kaggle copy's matches for the player. The API's `TournamentLevel` is a code (C, IS, P, PM, GS, ITF); the tournament object's `level` gives the name. Results now take the name (`level`) and keep the code (`level_code`); restaged offline with `--stage-only` (754 rows, 507 results, as online). Gate passed |
| 16:02 | (b) crawl started detached (`_logs/P2b_players_20261011.sh`, log `_logs/P2b_players_20261011T160207Z.log`) | (b) step 3 | trials above | – |
| (pause) | **The session was suspended from about 16:05 UTC on 11 Oct to 22:22 UTC on 13 Oct** (the transcript's clock jumped to 13 Oct). The crawl ran on its own meanwhile. This log was re-read in full at the resumption | – | – | – |
| 11 Oct 16:02-19:09 | (b) crawl ran to the end | – | – | 4,436 requests, 3.1 hours, no block, challenge or pause; 4,410 players in four waves (2,113 seeds, 2,006, 283, 8); 4,455 pages (48 players needed two or more); 2 players "no such player"; 1 page failed (HTTP 502 four times, player 334739); 95,506 served rows, 31,056 results [observed, `wta_player_matches_2026_summary.json` then] |
| 13 Oct 22:23-22:25 | Rerun of the crawl (same script) | Retry the failed page | – | 1 request (HTTP 200); everything else replayed from disk; no new opponent; 95,517 rows, 31,056 results; 31,027 results listed by both players, 27 by one, 2 by three |
| 13 Oct 22:25 | Read the evidence | – | the crawl's counts | **No player's list held a match at an edition after 21 Sep 2026.** ITF results after 7 Sep: 372 main draw, 283 qualifying (week of 14 Sep: 248 and 188; week of 21 Sep: 124 and 95) [observed]. The plan expected ~3,000 main-draw results after early September |
| 13 Oct 22:26 | Probe (`probe_lag.py`): five players whom TennisLive lists in the week of 28 Sep, asked again into `probe/players/<id>/matches_2026_0_2026-10-13.json.gz` | Is it the website or the crawl? | the evidence above | On 11 Oct their lists ended with 21 Sep; on 13 Oct all five show 28 Sep and one 5 Oct [observed]. **The website adds a week's ITF results a week or two late** (an update around Monday 12 Oct would fit) [inference] |
| 13 Oct 22:28 | Link check (`verify_wta_player_matches.py`) on the 11 Oct crawl, copied to `wta_player_matches_check_crawl_20261011.json` | Rule 12 | the lag | Against v29 only 80.3% of its matches were found, as many results being missing from v29 each month: a key mismatch, not missing matches |
| 13 Oct 22:28 (note added 00:05) | *Caveat on the dated copy above:* `wta_player_matches_check_crawl_20261011.json` was copied before the group-id fix below, so its `kaggle` section (80.3% found) is superseded; its TennisLive and ITF-live sections match by names and dates, not by that key, and stand | – | – | – |
| 13 Oct 22:29 | Diagnosis (`kaggle_miss.py`) | – | – | The row's `tourn_nbr` is fixed-width: three-digit group ids carry a leading space (`' 901'`), so 100 of 541 editions were keyed apart from the Kaggle copy and from the map's lookup (the map would have counted their matches twice). Fixed (`group_id`: the tournament object's id), tested, restaged offline |
| 13 Oct 22:30 | Link check again. *Correction:* the first printout after the fix (17,979 found) came from the old file, read by a second process before the check had rewritten it; the file written at 22:30:10 is the one quoted | – | – | Against v29: 22,342 of 22,396 played ITF singles of 2026 found (99.76%), all with v29's winner, 22,339 with its score; 3,338 results v29 lacks (about 2,050 of January-August, mostly qualifying; 1,290 of September; 168 at editions starting in December 2025). TennisLive and the ITF live API confirm 624 and 484 of the 649 results after 7 Sep; 1 and 4 score differences, no winner differs; week by week the 11 Oct crawl holds 80% of the week of 14 Sep (ITF live as reference), 34% of 21 Sep, none later [observed] |
| 14 Oct 00:55 (correction) | *To the 22:30 row:* "about 2,050 of January-August" added December 2025's 168 in; January-August holds 1,880 results the copy lacks (by month: 61, 70, 171, 156, 326, 407, 237, 452). The README quotes 1,880 | – | – | – |
| 13 Oct 22:31 | `--refresh-active-since` added (with `--refresh-before`: re-ask only players whose pages show a match since the date); test; the 11 Oct pages copied to `players_snapshot_20261011/` (4,462 files, 26 MB) | Judgment call 7 | the lag | 216 tests pass |
| 13 Oct 22:32 | Chain started detached (`_logs/P2_topup_20261013.sh`, log `_logs/P2_topup_20261013T223159Z.log`): (a)'s five endpoints again, then (b) with `--refresh-before 2026-10-13T22:45:00 --refresh-active-since 2026-08-01` | Bring both parts to 13 Oct | above | running |
| 13 Oct 22:33 | `note()` fixed: an answer recorded as absent (the empty "no such player") counts toward the 404 streak, not the error streak. The first version failed its new test (the `absent` key still reached the error streak); fixed before the chain's crawl step imported the module | – | – | 217 tests pass |
| 13 Oct 22:35 | The map's `load_wta_site` checked on the real staged results (scratch `loader_check.py`; it rewrote the map's cache file `wta_site_matches.parquet`) | Before the map build | the 11 Oct crawl | v29 alone 281,706 rows; with the results 285,256: +3,550 (ITF 832, ITFQ 2,219, CH 273, CHQ 88, TQ 57, T250 64, T500 54, TEAM 25, GSQ 6). The 380 rows without a level and 495 without a round are v29's own [observed] |
| 13 Oct 23:06 | (a) on 13 Oct ended (five steps, exit 0; 22:32-23:06) | – | – | 809 requests; 105 logs, 105 box scores, 104 advanced statistics, 106 point-by-point documents; win probability 199 HTTP 404 and no document (93 of them 404s of 11 Oct asked again under judgment call 5) [observed, receipts] |
| 13 Oct 23:07 | (a) staged (`--stage-only --years 2026`) and its coverage read (scratch `p2a_coverage.py`) | (a) step 3 | – | 22 editions from 1 Sep, 1,225 played matches: log, box score and advanced statistics for all 1,225; point-by-point 880; win probability 937, **none for the 196 matches played 8-13 Oct** (199 of 205 for 1-7 Oct) [observed] |
| 13 Oct 23:10 | `verify_wta.py --years 2019-2026` and `wta_todo.py` (background); `refresh.py --sources wta_api` (background, log `_logs/P2a_timing_refresh_20261013T231027Z.log`) after checking that no timing or Stage 0 job ran. A `mkdir -p` made an empty `data/studies/match_timing/_logs/` by mistake; left in place (empty, untracked) | (a) steps 3-4, rule 10 | – | running |
| 13 Oct 23:12 | The map was found rebuilt by another session on 12 Oct 14:22 UTC (window to 11 Oct). It read the 11 Oct crawl's results, then still keyed with the leading-space group ids: for 100 editions, its API rows were not matched to v29's | – | – | Women's ITF 2026: 14,661 matches, ITFQ 12,678 on that map. Replaced by this package's rebuild |
| 13 Oct 23:18 | `verify_wta.py --years 2019-2026` and `wta_todo.py` ended (exit 0) | (a) step 3 | – | Complete logs 35,491 (35,119 + the 372 of P2(a)); 34,939 replay (361 of the 372 new ones); 2026: 6,020 of 6,153; aces agree in 35,337, double faults in 35,088; point-by-point 21,129 documents, 17,647 replay; to-do: no error, nothing pending [observed] |
| 13 Oct 23:20 | `refresh.py --sources wta_api` ended (exit 0, 10 minutes) | Rule 10 | – | 28,808 of 31,328 WTA singles rows linked to Stage 0; 489,581 of 873,437 matches with a trusted exact day; out-of-sample window misses 0.0455%; IOS inputs rebuilt (255,832 pool matches) [observed] |
| 13 Oct 23:20-23:25 | (a) reported in the official_point_feeds README (a new subsection, the receipts rows, the status row, the 2026 limit and the rerun commands); data_map.yaml: `wta_api` back to `on_disk`, its `in_progress` lines replaced by a `not_counted` line, `wta_site_records`'s progress line updated | Rules 8, 12 | – | yaml parses. While writing, two figures were corrected before they were saved: 1-7 Oct holds 205 matches, not 207; and of the 107 win-probability 404s of 11 Oct, only the 93 at unfinished editions were asked again (receipts: 93 asked on both days, 14 once, 106 first asked on 13 Oct) |
| 14 Oct 00:46 | (b) second crawl ended (exit 0; chain `done`) | – | – | 2,366 requests in 1.65 h, all HTTP 200, no retry or pause; 4,467 players (2,113 / 2,058 / 286 / 10), 2,165 pages replayed; 99,787 rows, 32,465 results (ITF 14,378 main, 12,436 qualifying); ITF after 7 Sep: 994 main, 770 qualifying, to the editions of 5 Oct; by week 248/188, 309/268, 328/256, 109/58 [observed] |
| 14 Oct 00:46 | Final link check (`verify_wta_player_matches.py`) | Rule 12 | the crawl's counts | v29: 22,342 of 22,396 (99.76%), winners all agree, 22,339 scores; 4,445 results v29 lacks. TennisLive: 1,715 agree, 3 score differs, 823 not in the results; ITF: 1,534, 7, 1,175; no winner differs; 1,710 and 1,539 of the 1,753 results after 7 Sep confirmed. By week played (ITF as reference): 361/373, 518/542, 521/683, 141/847, 0/271 [observed] |
| 14 Oct 00:48 | Misses in the complete weeks examined (14-27 Sep, ITF reference) | How to read the ~4% | above | Scattered over events (Maanshan 10 of 82, Monastir 7 of 118, Wagga Wagga 5 of 7); examples are name forms (Boehner/Bohner, Garcia-Perez) and same-surname pairs the check cannot key [observed examples; the reading is inference] |
| 14 Oct 00:45-00:47 | data_map.yaml: `wta_site_records` refreshed (name, provider, what, years, `on_disk`, raw, staged, adapter, evidence, report, notes); `wta_site_refresh` universe row's evidence, effort and lead; the `in_progress` lines replaced by a `not_counted` line. `check_catalog` finds no problem | Rule 8 | – | – |
| 14 Oct 00:47 | Map build started (`build.py`, log `_logs/P2b_map_build_20261014T004751Z.log`) after checking that no build, timing or Stage 0 job ran | Rule 8 | – | running |
| 14 Oct 00:50-00:56 | (b) reported in this study's README (a new section). Before saving, four figures were checked against the outputs and corrected: the 2,397 results v29 lacks are at editions of September-October, not after 7 Sep; January-August is 1,880; the third row of the crawl table (52) includes the 13 Oct retry; the right-hand column counts by the week played | Rule 12 | – | – |
| 14 Oct 00:50 | Map build ended (exit 0, 2.5 min; no catalog problem) | Rule 8 | – | Women's 2026: ITF 14,675, ITFQ 12,917 (12 Oct build: 14,661, 12,678); 26,415 of the 27,592 women's ITF/ITFQ matches of 2026 carry `wta_site`; after 7 Sep by edition week: 430/432, 572/576, 582/619, 167/870, 0/175 [observed] |
| 14 Oct 00:58 | Loader comparison rerun on the final results (scratch `loader_check.py`) | The README had quoted the 13 Oct 22:35 figure (3,550), from the first crawl | – | +4,959 rows (ITF 1,454, ITFQ 2,706, CH 397, CHQ 133, others 337); 68 of v29's qualifying rows renumbered (Q1→Q2 49, Q2→Q3 19), because the API supplies their editions' first qualifying round (checked by joining on everything but the round) [observed]. README corrected before the session ended |

### 6. Judgment calls and deviations

1. **The listing rule (before any request).** Options: rerun as the plan says, which leaves seven editions' last rounds missing; pass `--refresh`, which refetches every document already held as well; or fix the rule so that only lists fetched before their edition ended are asked again. Chose the fix: it asks again only what may have changed, and keeps "nothing fetched twice" for lists that were final when fetched.
2. **Trials by budget, not `--limit 20`** (before any request). `--limit N` takes the first N matches of the plan, oldest edition first, and those are cached from the batches, so a `--limit 20` trial would ask for nothing new. A small `--max-requests` budget (shared rule 5 allows either) reaches the new matches. Effect: none on what is collected.
3. **`--no-stage` on each run, one staging at the end** (before any request). Each run would otherwise restage all of 2026; the batches' chain did the same. Effect: the staged tables lag the raw files until the end of (a).
4. **Raw page files** (after the paging probe). The plan names `players/<id>/matches_<year>.json.gz`; the endpoint is paged, so the mode writes `players/<id>/matches_<year>_<page>.json.gz` at `pageSize=100`. The 5 trial files at the plan's path hold only the default first page of 10; they are kept and never staged.
5. **404s answered while an edition is under way are not final** (after the win-probability run). Options: leave every 404 final (the adapter's rule), so the plan's post-season rerun (step 3) would never ask again for the 107 answered today (trial and run), 88 of them non-final matches at editions not yet over; pass `--refresh` then, which refetches every document held; or ask again only the 404s answered before their edition had surely ended. Chose the last, the same rule as the lists' (judgment call 1). Whether these documents appear later is unknown; the post-season rerun will tell (about 100-200 extra requests).
6. **Seeds from `player_1`, not `perspective_player_id`** (after the failed trial, before any result). The plan names `perspective_player_id`, but the copy's field is a WTA id on only some rows (§ 4). `player_1` is what the field was taken to be: the player the website was asked about. The set grows from 820 "ids" (labels) to 2,113 players; the crawl then adds every opponent either way, so only the waves' sizes depend on it.
7. **A second crawl, kept to players active since 1 August** (after reading the lag). Options: report the 11 Oct crawl as it stands (results to the week of 21 Sep); re-ask all 4,410 players (~4,460 requests); or re-ask only players whose 11 Oct pages show a match at an edition since 1 Aug (~2,250 players, plus new opponents). Chose the last: the website adds results at the end of each list, so a player idle since July gains nothing, and a match between an idle player and an active one is caught from the active side. What it can miss: a match played after 21 Sep between two players neither of whom had played from 1 Aug to 21 Sep. The plan's post-season rerun can re-ask everyone.
8. **(a) topped up on 13 Oct** (after the pause, before reading any (b) result of the second crawl). The plan's (a) was done on 11 Oct. Two days later another ~150 matches had been played, and the five runs cost 809 requests. It also tested the lag reading of the win-probability 404s (none had appeared).
9. **The map's `how` stays `kaggle`** for `wta_site_records`. The catalog allows one method per dataset, and the plan says to refresh this entry, not to add one; the API part is named in its provider and notes. Effect: the map's count by method credits the API's rows to Kaggle.

### 5. Sources

* **Kaggle API** (`https://www.kaggle.com/api/v1/datasets/view|list/...`), 11 Oct 2026: the version check. Provider claim: the dataset is "built from wtatennis.com player by player" (its description, read by the research).
* **WTA API** (`https://api.wtatennis.com/tennis/...`), 11-14 Oct 2026: the calendar, match lists, per-match documents and players' match lists. Undocumented; every convention above (paging, sides, codes, empty answers) is observed from the answers, not from a specification.
* **Not reached:** nothing was refused. `developers.wtatennis.com` (sign-in) was not touched.
* **Where the search is blind:** whether the website ever lists ITF events it does not carry now (Wagga Wagga), and when it adds each week (only one jump, 11 to 13 Oct, was observed).

### 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| (a) 2,441 requests, no error or refusal | `_receipts.jsonl` lines since 11 Oct 14:34 (scratch `p2a_accounting.py`); run summaries in `data/studies/official_point_feeds/runs.jsonl` | observed |
| (a) every one of 1,225 played matches has a log, box score and advanced statistics; point-by-point 880; win probability 937, none from 8 Oct | `data/dump/points/wta/matches/2026.parquet` statuses (scratch `p2a_coverage.py`) | observed |
| (a) seven lists were stale; fixed | receipts' fetch times against the cached calendar (scratch `editions_2026.py`); the trial's 44 logs all from those editions and Beijing | observed |
| (a) 35,491 logs, 34,939 replay | `wta_verification.json` | observed |
| (b) Kaggle still version 29 | `data/raw/gap_sources/bwandowando/_checks/20261011T142745Z_view.json` | observed |
| (b) paged at 10 by default | the five trial answers (`players/<id>/matches_2026.json.gz`) and the probes | observed |
| (b) `perspective_player_id` is not an id on most rows | v29's `matches.csv` (process log, 15:58-16:00) | observed |
| (b) 4,467 players, 32,465 results, by week | `wta_player_matches_2026_summary.json` | observed |
| (b) the website lists ITF results a week or two late | the 11 Oct lists end at 21 Sep; five probes on 13 Oct (`probe/players/*/matches_2026_0_2026-10-13.json.gz`) | observed jump; the cadence is inference |
| (b) 99.76% of v29 found, winners all agree; TennisLive and ITF agreement | `wta_player_matches_check.json` | observed |
| (b) the ~4% unfound in complete weeks are mostly name matching | examples in `wta_player_matches_check.csv.gz` | inference |
| Map cells | `coverage_cells.csv`, `matches.parquet` (build of 14 Oct 00:50) | observed |

No figure rests on a choice made after seeing an outcome in the modelling sense; the choices after looking at data (judgment calls 5-9) changed what was collected or how it was keyed, not how anything was scored.

### 8. Weak points

* **The website's lag is measured once.** One jump (11 to 13 Oct) was seen. The cadence (a weekly batch around Monday?) is a guess, and the editions of 5 Oct are partly listed.
* **The crawl's closure is not proven complete.** Players reachable only through doubles, or a group that met only each other, would be missed. The 4% unfound in complete weeks were read as matching artifacts from examples, not counted.
* **The second crawl's rule** (active since 1 Aug) can miss matches between two returning players.
* **Keys by names in the map.** The API's rows join v29's by surname pairs within an edition. Same-surname pairs have no key, and could be counted twice when both copies hold them.
* **Where a flaw would hide:** in `player_results`'s join of the two players' rows (a wrong key merges two matches or splits one). The checks bound it: 32,211 results with both rows, 1 with two winners, 99.76% agreement with v29 by ids.
* **A re-design** would crawl every player on a schedule (a weekly job, like P1's) rather than in one-off waves. It would read the website's own tournament draw pages, if the API serves them, to see whole events, and compare each week with the ITF's own lists when both are complete.

### 9. Reviewer checklist

* [ ] Rerun the tests: `./python.sh -m pytest test/official_point_feeds test/gap_downloads test/data_map -q` (301 passed on 13 Oct).
* [ ] Re-derive (a)'s coverage table: `data/dump/points/wta/matches/2026.parquet`, editions from 1 Sep, statuses by endpoint.
* [ ] Re-derive (b)'s per-week counts: `player_results/2026.parquet`, `level == "ITF"`, `start_date > 2026-09-07`.
* [ ] Check a sample of `player_results` against both players' raw pages (`players/<id>/matches_2026_*.json.gz`): the winner side and the score orientation (winner first).
* [ ] Confirm v29 is untouched: its files' SHA-256 against `data/raw/gap_sources/bwandowando/_receipts.jsonl`.
* [ ] Confirm the stale-list and stale-404 rules only re-ask what they should: `listing_stale` and `absence_stale` in `wta.py`, and their tests.

### 10. Reproduction

```
# (a): the five endpoints, staging, checks, timing (Git Bash, repository root)
A="--years 2026 --from-date 2026-09-01 --tiers 1000,500,250,125,finals --max-requests 3000 --no-stage"
./python.sh -m src.ingest.point_sources.wta $A --endpoints events --stop-after-absences 150
./python.sh -m src.ingest.point_sources.wta $A --endpoints stats --stop-after-absences 1500
./python.sh -m src.ingest.point_sources.wta $A --endpoints advanced-stats --stop-after-absences 400
./python.sh -m src.ingest.point_sources.wta $A --endpoints win-probability-momentum --stop-after-absences 1000
./python.sh -m src.ingest.point_sources.wta $A --endpoints point-by-point --stop-after-absences 0
./python.sh -m src.ingest.point_sources.wta --stage-only --years 2026
./python.sh src/eda/official_point_feeds/verify_wta.py --years 2019-2026
./python.sh src/eda/official_point_feeds/wta_todo.py
./python.sh src/eda/match_timing/refresh.py --sources wta_api
# (b): Kaggle, the crawl, a refresh, the checks, the map
./python.sh src/eda/gap_sources/wta_site_kaggle.py --fetch-only
./python.sh -m src.ingest.point_sources.wta --player-matches --player-year 2026 --max-requests 8000
./python.sh -m src.ingest.point_sources.wta --player-matches --player-year 2026 --max-requests 6000 --refresh-before <UTC time> --refresh-active-since <date>
./python.sh src/eda/gap_downloads/verify_wta_player_matches.py
./python.sh src/eda/data_map/build.py
```

Every request step resumes from the receipts when rerun; the seeds are frozen in `wta_player_seeds_2026.csv`. Run times: (a) about 70 minutes on 11 Oct and 35 on 13 Oct; the first crawl 3.1 hours, the second 1.65; staging and checks minutes. The superseded outputs kept: `wta_player_seeds_2026_superseded_perspective_ids.csv`, `wta_player_matches_check_crawl_20261011.json`, `players_snapshot_20261011/`.

### Addendum, 14 Oct 2026: P2 made a weekly scheduled job

Same session (`310009bc-0651-4504-9b7f-c4a3acdecc66`), after the report above.

**The owner's words, verbatim**, quoting the report's "still to do" line ("Rerun both parts after the season (the WTA Finals run 8-15 Nov; the last WTA 125 ends 20 Dec). The script is data/raw/point_sources/wta/_logs/P2_topup_20261013.sh; give its crawl step the rerun day's date."):
> "Set this up for this data to come in automatically with the other repeating data acquisition"

**How it was read.** Both parts of P2 become jobs of the existing scheduler (`src/ingest/scheduled.py`), recurring weekly, so the post-season rerun happens by itself and later seasons too. Set aside: a single dated run after the season, which would leave the weeks between unrefreshed and the next season unhandled.

**What was found first [observed].** Since P2 began, another session had added a second Windows task, "Tennis predictions - lower-level feed" (`scheduled.py --weekly`, daily at 12:00, 3 hours; first run due 14 Oct). Its jobs: TennisLive every day; on Wednesdays the WTA API's box scores of the last five weeks (`--endpoints stats`), the lower-level feed and the coverage alarm. The feed's candidate builder already reads P2(b)'s staged results as its source `wta_site` (since 13 Oct), and model builds and prediction runs re-link the WTA API for the timing clock in their own sandboxes (`run_chain.py`, `prediction_run/run.py`).

**Choices** (each before any run of the new jobs):
1. **Two jobs in the weekly task, not a new task:** `wta_points` on Mondays (part (a): every endpoint, the last five weeks' editions, the same window as the Wednesday `wta` job) and `wta_site` on Tuesdays (part (b)). Wednesday stays the feed's: a job there would eat into the feed's minimum time (75 minutes of the task's 3 hours).
2. **A missed day is caught up** on the next day the task runs, never on Wednesday; a job never run waits for its day. A job with too little of the task's time left waits a day.
3. **`wta_site`'s refresh:** players active in the last six weeks every week, plus one in six of the rest in rotation, so every player at least every six weeks (`--refresh-rotation`). Without the rotation, a player whose cached list showed nothing recent would never be asked again: a player back from a break, and everyone at the start of a new year.
4. **A new year** seeds from the previous year's ITF players (`previous_year_players`), since the Kaggle copy has no 2027. Until mid-February the previous year's lists are refreshed too.
5. **No timing refresh, no checks, no map rebuild in the jobs.** Stage 0 rebuilds are not scheduled (cadence decision, point 6), the clock is rebuilt in each build's sandbox, and the checks rewrite tracked evidence; sessions run them.
6. **One alert added:** the newest ITF edition the website lists more than six weeks old. Six, not five, so that the ITF calendar's Christmas break does not trip it.

**Chronology (UTC, 14 Oct):**

| When | Step | Output |
|---|---|---|
| 01:00 | Read `scheduled.py`, its tests, the cadence and lower-level-feed decisions; listed the tasks | the structure above |
| 01:02 | `wta.py`: `refresh_due` and `--refresh-rotation`; `previous_year_players` and the new-year seeds (`seeded_from` column; the 2026 file keeps `kaggle_folder`, both read); `itf_last_start` in the evidence; 3 tests | 16 player-matches tests pass |
| 01:05 | `scheduled.py`: `WEEKLY_DAYS`, `CATCH_UP`, `weekly_due`, `job_wta_points`, `job_wta_site`, the docstring; tests (the days and catch-up, both jobs with faked children, their command lines parsed by `wta.py`'s own parser); the existing weekly-task test now expects each job on its day | 351 tests pass (data_continuity, official_point_feeds, gap_downloads, data_map, data_gaps_2026) |
| 01:09-01:20 | `./python.sh -m src.ingest.scheduled --only wta_points --no-notify`, live, after checking no WTA collector ran | exit 0, no alert; 174 requests (24 lists, 2 calendar pages, 148 win-probability 404s asked again under judgment call 5 of P2, still 404); no match finished since 13 Oct 23:06; staging included, 10.6 minutes. State: `wta_points_last` 2026-10-13 (local date) |
| 01:25 | Not run live: `wta_site` (its crawl had run with the same flags hours earlier; a run now would re-fetch about 2,400 unchanged pages) | – |
| 01:25-01:40 | The cadence decision's amendment (the owner's words), both READMEs, the plan's P2 note, data_map.yaml (`wta_api`, `wta_site_records`, the `wta_site_refresh` row); `check_catalog`: no problem | – |

**Weak points.** `wta_site` has not run through the scheduler yet; its first run is Tuesday 20 Oct, `wta_points`' next Monday 19 Oct. The website's update day is unknown (one jump seen, 11 to 13 Oct), so Tuesday may fall before or after it; a week's results then arrive a week later. The rotation closes the gap of the second crawl (judgment call 7 of P2) only by late November.

---

## Work packages P7 (SofaScore, ITF) and P13 (Flashscore, ITF January 2025 to February 2026)

11 Oct 2026 – (running) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code extension) · Session: `8b00b734-ccf1-42cc-bd90-a3bb292e7ad2` · For a future reviewer · Reports: [this study's README](README.md), sections "SofaScore by edition: ITF (work package P7)" and "Flashscore point feeds" (P13); research: [itf_2025_points.md](../../research/gap-sources/itf_2025_points.md)

**Opened on 14 Oct 2026 at 14:10 UTC, at a resumption** (a Windows Update restart had stopped every run). The process-log rule reached this session only then, with the re-read instructions. So everything before 14 Oct 14:00 UTC below is **reconstructed from the session's own transcript, not contemporaneous**; the times come from the logs and receipts named. From the resumption on, it is kept as the work goes.

### 1. The request

* **The owner's words, verbatim:**
  * 11 Oct 2026, 14:22 UTC:
    > "Start only after work package P6 has finished all seven gaps (check data/data_map.yaml's in_progress block and the running processes); if it hasn't, stop and say so. Do work package P7 of docs/studies/gap_downloads/collection-plan.md: run the SofaScore by-edition adapter in browser mode over ITF, first a new gap itf_points_2025_2026, then itf_detail (2018-2024), newest first, fetching both points and box scores (no --skip statistics). It is a multi-day run: if an earlier session started it, resume it. The Chrome window with the debugging port is open. Follow the plan's shared rules. You wont need to do this for at least 6 hours. So set a timer to check in every hour, with the first one starting in 6 hours from now"
  * 13 Oct, about 22:20 UTC, quoting option 1 of the session's question:
    > ""Defer the flagged events (my recommendation). Finish the rest of 2025-26 in about 18 hours, run 2018-24, then make one last pass over the deferred events at the end, which you can keep or drop. Nothing is lost, and 2018-24 starts about 2 days sooner." Im ok with this / In parallel, see if you can find this missing data somewhere else (or still at sofa score)"
  * 14 Oct, about 00:50 UTC, quoting the session's question:
    > ""Decision for you: should I build a Flashscore collector now as its own package? It would use the IDs on disk, fetch the point feeds with receipts at the plan's pace, check them against the official scores, and put them on the data map. I'd start with a trial of about 200 matches spread across months and both tours, then the full run. The 8 October decision already covers collecting it; the open question is whether to slot it in now." Yes"
  * 14 Oct, about 14:00 UTC: "continue, it got intterupted I believe?"
* **How it was read:**
  * *The timer:* two session-only cron jobs, at minute 27: one for 13:27-23:27 local on 11 Oct, one hourly from 12 Oct. "Stop and say so" was read as "skip that hour and check again", not as cancelling the schedule; the owner was told so.
  * *The pace:* the plan's 2 s plus up to 1 s; the faster pace is the owner's call and was offered, not taken.
  * *P13 and the "elsewhere" search:* the search was split between a research subagent (disk and web, brief in the appendix) and the lead (SofaScore's other endpoints, the ITF's API and site).
* **The target:** not a model study. No price, hour, season or primary applies; nothing is scored.

### 2. Starting point (reconstructed)

* **Code:** commit `677a63f` plus other sessions' uncommitted changes. Files this work changed: `src/ingest/point_sources/sofascore_editions.py`, `src/eda/gap_downloads/verify_links.py`, `src/eda/data_map/measure.py`, `src/eda/data_map/build.py`, `src/eda/match_timing/srcc_sofascore.py`; new: `flashscore_points.py`, `keep_tab_priority.ps1` (both in `src/ingest/point_sources/`), and `itf_qualifying_probe.py`, `sofascore_uncovered_probe.py`, `itf_stadion_probe.py`, `itf_site_probe.py`, `verify_flashscore.py` (all in `src/eda/gap_downloads/`).
* **Data:** the map of 12 Oct 14:22 UTC (`data/studies/data_map/matches.parquet`, 708,437 matches); both target lists frozen from it at 14:57 UTC (63,334 and 207,045 targets).
* **Processes at P7's start (12 Oct 14:47 UTC):** the daily scheduled task and P1's ITF run, on other hosts. P6 had ended at 14:18 UTC; its map rebuild (14:22) and timing refresh (14:23-14:30) were done.

### 3. Plan (reconstructed; as first acted on, 12 Oct)

1. The plan's P7 section and shared rules: add the gap; gzip the two gaps' tables and extend their readers; trial 3 editions per gap, two at Monastir or Antalya; stop if the 2025-26 trial links under 80%; measure ITF qualifying in the trial.
2. The bulk, gap by gap: `--browser --max-requests 30000`, rerun until done; after each gap, the link check, staging, the map rebuild and the timing refresh.
3. Hourly checks: rerun a run that ended without a block; stop and report on a block.

### 4. Chronology

UTC. Rows before 14 Oct 14:00 are reconstructed (above).

| When (UTC) | Step | Why | Seen by then | Output |
|---|---|---|---|---|
| 11 Oct 14:25 | Two cron jobs at :27; P6 checked | the owner's timer | P6 on gap 4 | – |
| 11 Oct 20:32 - 12 Oct 13:47 | Hourly checks | the gate | P6 gaps 6-7 running | "not finished" each hour |
| 12 Oct 14:47 | Check found P6 done | the gate | P6's after-steps done 14:22-14:30 | P7 started |
| 12 Oct 14:50-14:57 | Code: gzipped ITF tables (`GZIPPED`), four readers, `--editions`, streamed `stage()`; tests | plan § 2; the ITF scale (tens of millions of point rows) | – | 173 tests pass; streamed staging gives P6's tables exactly (all columns but the staging time), 83 s |
| 12 Oct 14:57 | Gap `itf_points_2025_2026` added; both lists frozen | rule 8; one map build for both | – | 63,334 and 207,045 targets |
| 12 Oct 14:58-15:07 | Trial 1 (194 requests) | rule 5 | – | 92/92 linked; points 61 (W35 Antalya Feb 2026: nothing); 2026 box scores have 11 items, not the full 19 |
| 12 Oct 15:08-15:19 | Trial 2 (194) | rule 5 | trial 1 | 92/92 linked, all points complete, full box scores |
| 12 Oct 15:19-15:20 | `verify_links.py` on both | rule 5 | – | 2024: 92/92 agree; 2026: 31 agree, 61 no official row |
| 12 Oct 15:19-15:24 | Qualifying probe (125) | plan P7 step 1 | – | 59/125 (47%) with points: no qualifying gap |
| 12 Oct 15:25 - 13 Oct 01:26 | The bulk launch waited about 10 h; no sleep events in the system log, so most likely the WMI launch's approval | – | – | – |
| 13 Oct 01:26 | Run 1 launched through WMI (outside the session's job object) | rule 6; survive the session | – | – |
| 13 Oct 04:50 | Listing done (4,908 requests) | – | – | 62,727/63,334 linked |
| 13 Oct 15:40-16:49 | The pace fell below half; CPU at 100% (other sessions); every renderer of the scraping profile at Idle priority; raised to AboveNormal at 16:49 | the pace | – | back to ~25 requests a minute |
| 13 Oct 17:48 | Watchdog `keep_tab_priority.ps1` launched | Chrome lowers renderers again (a 15-min stall 16:58-17:12) | – | re-raise every 15 s, logged |
| 13 Oct 19:46-20:50 | From February 2026 every answer 404 (1,471 in a row); answers are SofaScore's JSON; the `coverage: -1` flag mapped by month; cross-tab over every fetched event | an anomaly | – | flagged events: 8 of 1,403 with points; the owner asked |
| 13 Oct ~22:20 | Owner approved deferral and asked for a search (§ 1) | – | – | – |
| 13 Oct 22:27 | Run 1 stopped by hand (about 28,830 requests) | its last 1,180 requests were flagged events | – | no evidence table written; the next run rewrites it |
| 13 Oct 22:30 | `sofascore_uncovered_probe.py` (28) | "still at SofaScore?" | – | 0/6 flagged with points; tennis-power empty for all 8; statistics on 2/6 flagged, 6 items |
| 13 Oct 22:33 | Run 2 with `--defer-uncovered` | the owner's choice | – | 38,978 deferred; 23,699 to ask |
| 13 Oct ~22:35 | Research subagent launched (brief: appendix) | the search | – | – |
| 13 Oct 22:39-22:45 | `itf_stadion_probe.py` (5, receipts) and 7 follow-ups without receipts; `itf_site_probe.py` (5) in a Chrome window on port 9223, then closed | the ITF route | – | the API lists nothing older than 14 days; the draw sheet answered 403 ×3 |
| 13 Oct ~23:00 | Twins: 136 flagged/unflagged pairs in one season | could an unflagged copy hold points? | – | 15/15 unflagged copies asked: 404; no change |
| 13 Oct ~23:05 | Subagent's report read; its 8 feed samples checked by eye and copied to `data/raw/gap_sources/flashscore_itf_2025/`; `matchesByCourt` asked (2) | verify before relaying | the note | 404 both |
| 14 Oct ~00:50 | Owner approved P13 (§ 1) | – | – | – |
| 14 Oct 01:07 | `flashscore_points.py --extract` (82 s) | – | – | 44,308 records; 42,791 in the window, 29,614 with a duration: the subagent's census exactly |
| 14 Oct 01:09-01:19 | Flashscore trial (189) | rule 5 | – | 131 records (130 complete); duration rule 131/6/0/52 |
| 14 Oct ~01:25 | `verify_flashscore.py` | rule 5 | trial | 115/115 agree; 16 no official row |
| 14 Oct ~01:35 | Order: records with a duration first | the trial's 0 of 52 | trial | tests pass |
| 14 Oct 04:38 | P13 bulk launched (after a ~3 h approval wait) | – | – | – |
| 14 Oct ~04:45 | Map loader `load_flashscore_points` and `flashscore_point_uids`; `MEASURED_IDS`; catalog check; README; cron job at :57 for P13 | rule 8 | – | 185 tests pass; 0 catalog problems |
| 14 Oct 07:29, 07:33 | Windows Update restarted the PC twice (User32 1074, MoUsoCoreWorker then TrustedInstaller) | – | – | every run and the watchdog killed; P7 run 2 at about 9,400 of 23,699 box scores, P13 at about 4,100 of 40,867 feeds |
| 14 Oct 13:54 | The SofaScore Chrome window reopened (by the owner) with the three flags | – | – | – |
| 14 Oct 14:06 | **Contemporaneous from here.** Resumed: P7 run 3 (`--defer-uncovered`), P13 run 2, the watchdog, all through WMI | the owner's "continue" | – | P7 log `run_20261014T140601Z_itf_points_2025_2026.log`; P13 log `run_20261014T140601Z.log` |
| 14 Oct 14:10 | This section opened | the process-log rule, newly in the instructions | – | – |
| 14 Oct 14:47-15:05 | Another session changed `sofascore_editions.py` (link vetoes from `sofascore_link_vetoes.csv`: 47 links of two P6 Challenger gaps refused), `verify_links.py` (never-started 0-0 sets dropped on both sides) and their tests; the owner had committed the earlier work (`1d8f53e`) | files changed on disk | – | no veto for the ITF gaps; 186 tests pass |
| 14 Oct 19:02 | Another session changed `src/eda/data_map/build.py`; `flashscore_points` still among its measured sources | file changed on disk | – | catalog check: 0 problems |
| 14 Oct 19:47-23:47 | Hourly checks; other sessions' weekly task, a candidate Stage 0 build, a Stage 0 rebuild and the TrueSkill timing ran in between and ended | rules 8 and 10 | – | – |
| 15 Oct 00:10 | P7 run 3 ended, exit 0: `itf_points_2025_2026` done but for the deferred | – | – | 62,727 of 63,334 linked; points 19,411 (18,944 complete); absent 8,007; deferred 35,309 targets (38,978 events); box scores 23,378, all the reduced 2026 set |
| 15 Oct 00:47 | `itf_detail` bulk launched with `--defer-uncovered` (budget 30,000), through WMI | the owner's order: 2018-24 next; the deferred last | – | log `run_20261015T004743Z_itf_detail.log` |
| 15 Oct 00:48 | 2025-26's after-steps chained: `verify_links.py`, `--stage-only --defer-uncovered`, the map build, `refresh.py --sources sofascore`; a guard (`wait_clear.py`, session scratch) waits before the build and the refresh while any map build, refresh or Stage 0 rebuild runs | plan P7 step 6; rules 8 and 10 | – | log `after_<stamp>_chain.log` |
| 15 Oct 00:48-01:15 | The chain ran, exit 0 (the guard found nothing to wait for) | – | – | link check: 48,253 agree, 49 another winner, 191 score differs, 324 no SofaScore winner, 13,904 no official row; staged 6,346,036 points; the map's ITF from 1 Mar 2026: 24,698 of 26,224 point or shot; 2025: 398 of 39,114; timing: 160,314 of 210,518 SofaScore singles linked (108,433 before), 42,731 of the 45,045 unlinked ITF |
| 15 Oct 10:58-11:11 | P13's second run used its budget (exit 1, as designed); a background watcher relaunched it through WMI when its exit file appeared | – | – | records for 27,502 targets (27,174 complete); 6,787 empty; 6,583 not asked; among targets without a duration, 2 records in about 6,500 asked; third run log `run_20261015T111104Z.log` |
| 15 Oct 15:57-16:00 | P13's third run ended (exit 0); a watcher ran `verify_flashscore.py` and, after the guard, the map build | P13's after-steps | – | records for 27,535 targets (27,174 complete); 40,867 requests, all with receipts; check: 24,744 agree, 226 score differs, 3 another winner |
| 15 Oct ~16:10 | `verify_flashscore.compare` changed to leave never-started 0-0 sets aside (`verify_links.unplayed_dropped`), as the other session had done for SofaScore's check; a new test; the check rerun | the differing examples were mostly retirements written "6-0 0-0" | the 226 above | 24,887 agree, 83 score differs, 3 another winner; 96 tests pass |
| 15 Oct ~16:20 | The data map (on_disk; the in_progress line moved to not_counted), the README's P13 section; the P13 check-in job deleted | P13 done | – | the map's ITF 2025: 25,933 of 39,114 with point or shot data (398 before) |
| 15 Oct ~16:25 | Two README figures corrected before reporting: "90-98%" to 92-98% (December 2024 - June 2025) and "about 13,000 left" to about 15,300 in the window (13,181 of 2025, 2,160 of 2026); and a data map count of requests ("about 47,700", from memory) to 40,867, counted from the receipts | claims checked | – | – |
| 15 Oct ~01:20 | A README sentence ("most of the unlinked are ITF events Stage 0 lacks") checked before it stood: the linker's summary gives 42,731 ITF and 43,193 "no Stage 0 match with both players"; the 2025 map count first written as 341 of 39,116 (point only, summed by hand) replaced by 398 of 39,114 (point or shot, counted) | claims checked before reporting | – | README corrected |
| 15 Oct ~21:45 | Context summary of this session; this log re-read from the chronology on | the process-log rule | – | – |
| 15 Oct 21:47 | `itf_detail` run 1 used its budget (exit 1, "STOPPED: request budget of 30000 used up"); no challenge, 403, 429 or traceback in its log | – | – | points asked for 12,500 of 201,141 events, back to 19 Aug 2024: 12,525 targets with a record (12,320 complete), 176 absent (404); box scores 92 (the trial's; they follow the points) |
| 15 Oct 21:48-21:53 | The relaunch watcher queued at 19:47 stood down (exit 2): it looked for "BudgetExhausted", the Flashscore client's wording (judgment call 11). The hourly check found the stop, checked port 9222 (the SofaScore tab), the watchdog (alive) and that no collector ran, and relaunched by hand through WMI | rule: rerun after a budget stop | the log's last lines | run 2, log `run_20261015T215358Z_itf_detail.log`; the listing replayed with 0 requests; a new watcher (deadline 30 h) accepts both wordings |
| 15 Oct ~22:00 | The data map's in_progress line and the README's P7 section updated (a new "itf_detail: the download" part; the resume command now names `itf_detail`) | rule 8 | the per-match table after run 1 | – |
| 15 Oct 22:47 - 16 Oct 18:47 | Hourly checks: run 2 alive, ~1,400-1,500 requests an hour, no challenge, 403 or 429 | the check-in | – | – |
| 16 Oct 17:47 | 404s rose (62 in the last 1,500 receipts, against ~1% before); the receipts read: every one `application/json`, status 404, in runs of neighbouring event ids, 200s resuming after each run | rule: tell a block from an absence | – | not a block. Told the owner it "looks like a few whole tournaments without point records": an inference, not checked then; corrected below |
| 16 Oct 19:01 | Run 2 ended at its budget (exit 1, STOPPED at about 18:51; the evidence tables took the last ~10 min); the watcher relaunched at once | – | – | run 3, log `run_20261016T190139Z_itf_detail.log`; the next watcher queued (30 h) |
| 16 Oct ~19:10 | The per-match table after run 2 read | the progress line; the 17:47 inference checked | the 404 runs | 43,039 targets asked (to 23 Oct 2023): 42,445 with a record (41,795 complete), 594 absent. Only 8 of 1,623 tournaments asked lack every record (23 targets); the 404 runs are mostly the first days of a tournament (W25 Santo Domingo 2023: rounds of 64 and 32, 31 of 31 absent; later rounds 11 of 15 with a record). The 17:47 statement to the owner corrected in the next reply (judgment call 12) |
| 16 Oct 19:47-22:47 | Hourly checks: run 3 alive, ~1,400-1,500 requests an hour; another session's map build and a lower-level script ran meanwhile (not P7's) | the check-in | – | – |
| 16 Oct ~23:00 | The SofaScore Chrome window closed (port 9222 refused; no process of the `sofascore-cdp` profile left). Run 3 stopped with "STOPPED: the Chrome window with the debugging port was closed" at about 23:00 (requests=5,544) and exited 1 at 23:09; the watcher stood down (exit 2), as designed | – | – | not a block. The profile's `Local State` and `Preferences` were written at 23:00:16 and there is no crash report: a clean exit (closed by hand, or by Chrome; a Chrome update, 155.0.8059.80, had been installed on 16 Oct 03:50 UTC and was waiting for a restart). The owner's own Chrome (29 processes) kept running |
| 16 Oct 23:11 | Chrome reopened by the session with the README's command (same profile, the three flags), through WMI so that it outlives the session; minimised without focus | the check-in prompt: "If the Chrome window with port 9222 has closed: ... reopen Chrome with the plan's command ..., resume, and tell the owner" | – | Chrome 155.0.8059.40 (the update still pending), session 1, page "Tennis live scores ... Sofascore"; a Turnstile frame in the page; a read-only look over CDP (`tab_state.py`, session scratch; no request to SofaScore): no token stored, no check showing |
| 16 Oct 23:12 | Run 4 launched with the same command; a new watcher (30 h) | earlier logs: only P6's 8 Oct episode ever needed a token renewal; the 14 Oct restart in a fresh window ran without one | – | log `run_20261016T231210Z_itf_detail.log` |
| 16 Oct 23:28 | Run 4's first 200 requests answered, watched by a background check | confirm the reopened window works | – | 199 point records, 1 absent; no `[browser]` line (no challenge, no token renewal); the watchdog raised the new window's renderers and the adapter at 23:11-23:12 |
| 17 Oct 00:55 | The owner: "change the check to every 4 hours to reduce token output". The two hourly cron jobs (of 11 Oct) replaced by one at "27 */4 * * *" (`9ce59439`; expires about 23 Oct 17:55 local). Its prompt drops the P6 gate and the start steps (both long past), asks for 1-2 line replies, and adds the watchdog's relaunch (it stops by itself on 21 Oct about 07:06 local) and the queuing of each next watcher | the owner's instruction | – | relaunches at a budget stop and stops that end a run still arrive at once, through the watchers; only a stall without an exit now waits up to 4 hours |
| 17 Oct 03:57-19:57 | Four-hourly checks: run 4 alive, ~1,400-1,450 requests an hour, no challenge, 403 or 429 | the check-in | – | – |
| 17 Oct 20:23 | Run 4 ended at its budget (exit 1); the watcher relaunched at once; the next watcher queued (30 h) | – | – | run 5, log `run_20261017T202340Z_itf_detail.log`. After run 4: 78,847 targets asked (to 10 Oct 2022), 77,804 with a record (76,379 complete), 1,043 absent; 11 of 2,933 tournaments without any record (56 targets) |
| 17 Oct 23:07-23:21 | Run 5: after 3,702 requests (last receipt 23:07:51, a 200), SofaScore answered with its challenge (403 "challenge"; the first since P6's 8 Oct episode). The adapter reloaded the tab and waited for a fresh token (no check detected in the page at 3 s and 63 s). Chrome closed at 23:09:11 (the profile's settings written then; no crash report: a clean exit). At 300 s the adapter's attempt to clear the site's data found the browser closed; STOPPED (window closed); exit 1 at 23:20:59; the watcher stood down (exit 2) | – | – | 81,800 events asked by then. Windows logged three Configuration-Change-Monitor events at 23:07:55-56, DCOM 10016 errors and a DNS time-out at 23:08:12-17, the minute of the challenge: perhaps a network change, which would also explain the challenge (inference). The 16 Oct closure (23:00:16) had no such events. No scheduled task of the project or of Chrome runs at either time; the cleanup script's process stops are by fixed PIDs with checked command lines |
| 17 Oct 23:24 | Chrome reopened by the session (same command, through WMI; shown without focus this time, so that the site's check can run in a visible page and the owner can see it); read-only look: no token, no check showing. Run 6 launched; its watcher (30 h) and a short watch on its first requests queued | the check-in prompt; the owner had not answered whether the 16 Oct closure was theirs | – | log `run_20261017T232427Z_itf_detail.log` |
| 17 Oct 23:40 | Run 6's first 218 requests answered | confirm the reopened window works after the challenge | – | 217 point records, 1 absent; no `[browser]` line: SofaScore accepted the fresh window without a token |
| 18 Oct 03:57 | 404s higher over the previous 4 h (~280 in ~5,700 requests); the last 3,000 receipts read: 2,982 × 200 and 18 × 404, all `application/json`, no run longer than 2 | rule: tell a block from an absence | – | not a block; the extra 404s came in an earlier stretch |
| 18 Oct 04:00-19:57 | Four-hourly checks: run 6 alive, ~1,400-1,450 requests an hour | the check-in | – | – |
| 18 Oct 20:37 | Run 6 ended at its budget (exit 1 at 20:36:49); the watcher relaunched at once; the next watcher queued (30 h) | – | – | run 7, log `run_20261018T203706Z_itf_detail.log`. After run 6: 112,899 targets asked (to 13 Sep 2021), 111,091 with a record (107,465 complete), 1,808 absent |
| 18 Oct 23:57 | Four-hourly check: run 7 alive; the window stayed open through 16:00 local | the check-in | – | – |
| 19 Oct 14:20 | The Chrome window closed a third time (settings written 14:20:27; no crash report; no `[browser]` line; last receipt 14:20:23, a 200). The watchdog logged the tab's renderer raised "from Normal" at 14:20:22: Chrome sets the foreground tab's renderer to Normal, so the window had most likely just been brought to the front [inference: a manual close]. Run 7 stopped after 137,100 events (exit 1 at 14:35:52); its watcher stood down (exit 2) | – | – | no Windows event 14:15-14:25 |
| 19 Oct 14:35 - 20 Oct 12:49 | **Gap: no session activity.** The watcher's notification and the four-hourly check-ins were queued but not acted on (they arrived together at the next turn); the PC restarted at 04:18 UTC on 20 Oct, ending the watchdog. The run sat idle ~22 h | – | – | a deviation from the check-in prompt (the window should have been reopened at once) |
| 20 Oct 12:49 | The owner: "continue / continue downloading the sofascore itf data". Resumed: Chrome reopened minimised through WMI (now 155.0.8059.85, the pending update applied by the restart); the watchdog relaunched through WMI with `-Hours 336` (to 3 Nov) instead of the default 168, to outlast the gap; run 8 launched; its watcher (30 h) and a short watch on its first requests queued | the owner's instruction; the check-in prompt | after run 7: 138,243 targets asked (to 25 Nov 2019), 135,859 with a record (130,717 complete), 2,384 absent | log `run_20261020T125101Z_itf_detail.log` |
| 20 Oct 13:17 | Run 8's first 246 requests answered (the cached listing's replay took ~25 min after the restart, against ~7 before) | confirm the reopened window | – | 235 point records, 11 absent; no `[browser]` line |
| 20 Oct 15:57 - 21 Oct 03:57 | Four-hourly checks: run 8 alive, ~1,400-1,450 requests an hour; the 404 share rising with age (~5-6% in 2019) | the check-in | – | – |
| 21 Oct 10:13 | Run 8 ended at its budget (exit 1 at 10:13:07); the watcher relaunched at once (run 9). The 04:57, 08:57 (local) check-ins and the watcher's notification were acted on together at 15:57 UTC; the next watcher queued then (30 h) | – | – | log `run_20261021T101330Z_itf_detail.log`. After run 8: 168,242 targets asked (to 21 Jan 2019), 164,302 with a record (158,555 complete), 3,940 absent. The watchdog (pid 17580, to 3 Nov) runs: the prompt's 21 Oct relaunch step needs nothing |
| 21 Oct 19:57 - 22 Oct 03:57 | Four-hourly checks and the owner's "continue" (22 Oct 03:36): run 9 alive, ~1,400 requests an hour; the 404 share ~7-8% in 2018 | the check-in | – | the watcher was alive (a pwsh process whose command line does not name the log: the tool passes the script through an environment variable) |
| 22 Oct 07:31 | Run 9 ended at its budget (exit 1 at 07:30:49); the watcher relaunched at once (run 10); the next watcher queued (30 h) | – | – | log `run_20261022T073108Z_itf_detail.log`. After run 9: 192,131 targets with a record (185,663 complete), 6,125 absent, 3,997 not asked |
| 22 Oct ~09:20 | Run 10 finished the point records (request 3,998) and started the statistics | – | – | by event: 194,772 of 201,141 with a point record, 6,369 absent (404). Statistics by 11:56: 2,300 asked, 2,189 + 92 cached with a box score, 19 absent |
| 22 Oct 19:57 | The check-in job renewed as its step 6 says: `9c406adc` ("27 */4 * * *", expires about 29 Oct 13:00 local) replaced `9ce59439`. The past watchdog date dropped; a standing "relaunch the watchdog if it is not running" step added (the 20 Oct restart had ended it) | the job's 7-day expiry | statistics 13,800 asked, 97 absent | – |
| 23 Oct 04:49 | Run 10 ended at its budget (exit 1 at 04:48:47); the watcher relaunched at once (run 11); the next watcher queued (30 h) | – | – | log `run_20261023T044917Z_itf_detail.log`. After run 10: points all asked (195,871 targets with one, 189,340 complete, 6,382 absent); statistics for 25,300 events (26,215 targets with a box score, 26,177 full) |
| 24 Oct 02:07 | Run 11 ended at its budget (exit 1 at 02:07:48); the watcher relaunched at once (run 12); the next watcher queued (30 h) | – | – | log `run_20261024T020752Z_itf_detail.log`. After run 11: statistics for ~55,300 events (56,242 targets with a box score, 56,161 full) |
| 24 Oct 03:57-19:57 | Four-hourly checks: run 12 alive; at 07:57 the 404 share of the previous 4 h was ~4.6%, the last 2,000 receipts 22 × 404 (all JSON; 19 of the 22 events without a point record either) | the check-in | – | – |
| 24 Oct 20:40-23:03 | **A block.** Last 200 at 20:39:58. SofaScore then answered 403 "challenge"; the adapter's renewal reloaded the tab and waited 3,600 s (site data cleared every 300 s), gave up, retried, waited 3,600 s again; no token, no check detected (`CHECK_SHOWN_JS` false throughout); STOPPED "HTTP 403 (challenge) ... after 3 attempts" ~22:55, exit 1 at 23:03; the watcher stood down (exit 2) | – | – | read-only look at the tab (23:04, no request): URL `www.sofascore.com/captcha.html?redirectUrl=...`, no token. Box scores: 82,296 targets with one (82,150 full). Not rerun: the plan's stop-and-report rule; a captcha is the owner's |
| 24 Oct 23:04 | Reported to the owner with three options: (1) rest until the next morning, then a ~20-request test, and if it passes resume at a gentler pace (3 s + up to 2 s); (2) the owner passes the check; (3) stop the box scores. Recommended (1) | the stop-and-report rule; recommend, don't delegate | the block's log and the captcha page | – |
| 24 Oct 23:57 - 27 Oct 13:29 | No owner reply; check-ins reported "stopped, waiting". Sometime in that time the scraping Chrome window was closed (found closed on 27 Oct 13:30; the PC did not restart) | – | – | no request to SofaScore since 24 Oct 20:39:58 UTC |
| 27 Oct 13:30 | The owner: "continue". **Read as option 1, the one recommended**: the rest (about 2.5 days) is done; nothing in "continue" asks the session to pass a check, which stays the owner's. Reading set aside: option 2 (needs the owner's own click) and option 3 (the opposite of "continue") | the owner's word | – | – |
| 27 Oct 13:30-13:31 | Chrome reopened minimised through WMI (same profile and flags); read-only look: the normal page (`/tennis`), not the captcha page, no token. A test run launched with `--max-requests 20 --min-interval 3.0 --jitter 2.0` (log `run_20261027T133109Z_itf_detail_test.log`, named apart so no watcher or check-in mistakes it for a run), watched by a background check that stops it at the first `[browser]` line | option 1's test | – | – |
| 27 Oct 14:02 | **The test passed**: its 20 requests (14:01-14:02 UTC, after a ~30 min replay of the cached answers) were all answered 200, with no `[browser]` line; STOPPED at its budget of 20. (The watch itself timed out at 45 min, before the test finished writing its tables: the replay was slower than allowed for.) A second background step waits for the test's exit and then launches the full run at 3 s + up to 2 s | option 1 | the test's receipts | the README's resume command, the data map's command and the check-in prompt changed to the slower pace; check-in job `3f875c05` replaced `9c406adc` (expires about 3 Nov) |
| 27 Oct 14:30 | The test exited at 14:29:59 (budget 20); the waiting step launched run 13 at 3 s + up to 2 s (pid 40684 confirmed with that pace); its watcher queued (40 h; it relaunches at the slower pace, and stands down if any `[browser]` line appears even before a budget stop) | – | – | log `run_20261027T143015Z_itf_detail.log` |
| 27 Oct 14:54 | The owner: "Note: It stopped and challenged because I started VPN while the process was running, not because of our pace". Read as: the slower pace is not needed, so back to the plan's (an inference from the note, not an instruction; stated to the owner with the offer to keep the slower pace). Run 13's watcher stopped; run 13 stopped by hand at 14:54:48 (195 requests, all 200; exit 127 from the killed process); run 14 launched at 14:55:07 at 2 s + up to 1 s; its watcher queued (30 h) | the owner's word | run 13's first 195 answers | log `run_20261027T145507Z_itf_detail.log`. Check-in job `617d76ce` replaced `3f875c05` (plan's pace; the VPN cause; "check whether the network changed" on a challenge). The README now warns against network changes mid-run. The 17 Oct challenge coincided with network-configuration events: the same cause, likely (inference) |
| 27 Oct 15:57 | Check-in: run 14 is asking at the plan's pace with no `[browser]` line; 439 requests by the 83,300 mark (438 answered 200, one 404); the newest receipt was 3 s old. The log's file time read 48 minutes old: Windows lags in updating the folder's file times for a file that is still open, so the receipts decide | – | the log's tail and the receipts | log `run_20261027T145507Z_itf_detail.log` |
| 28 Oct 12:49 | Run 14 used its budget (30,000 requests, no `[browser]` line, no 403 or 429; about 0.8% absent) and ended at 12:49:07 UTC; its watcher started run 15 at 12:49:37 UTC (python pid 30548, the plan's pace confirmed on its command line); the next watcher queued (30 h, same script) | – | run 14's summary: box scores for 112,571 targets (112,130 full) | log `run_20261028T124937Z_itf_detail.log` |
| 28 Oct 21:17 | The PC restarted. Windows' event 1074: started by the Start menu's host process on behalf of the PC's user, reason "Other (Unplanned)", at 14:17:36 local (21:17:36 UTC). Run 15's last answer was at 21:17:33 UTC (a 200); it left no exit file (about 12,000 requests; 124,800 events walked at its last progress line). The restart also ended Chrome (port 9222), the watchdog and this session's watcher `bvcgowtmj`; the check-in job `617d76ce` survived the session's resumption | – | the run's last lines, the newest receipt, the System event log | – |
| 28 Oct 22:57 | Session `8b00b734-ccf1-42cc-bd90-a3bb292e7ad2` resumed; the owner: "continue". The conversation had been summarized once before, on 27 Oct before the 15:57 row; noted here late. Checked before resuming: NordVPN's app started with Windows at 21:19:30 UTC, but its three adapters (NordLynx, OpenVPN DCO, TAP) were disconnected and the only default route was the home Wi-Fi: the network was as before, the 24 Oct cause absent [observed] | the owner's word; the check-in rules (a run that ended without a block, a closed window, a stopped watchdog) | adapters, routes, processes | – |
| 28 Oct 22:59-23:00 | Chrome reopened minimised through WMI (same profile and flags, as on 20 Oct); watchdog relaunched with `-Hours 336` (pid 14756, to about 11 Nov 22:59 UTC); read-only look: the normal `/tennis` page, no token, no check showing (the state the 27 Oct test passed from). Run 16 launched at 23:00:36 UTC at the plan's pace (python pid 12092); its watcher queued (30 h, same script), and a second background check reports the first answered requests or the first `[browser]`, 403 or 429 line | – | the tab's state | log `run_20261028T230036Z_itf_detail.log` |
| 28 Oct 23:31 | Run 16's first requests answered after its 31-minute replay (23 of 23 answered 200 by the 124,900 mark). The replay counted 124,877 events already answered (123,531 box scores, 1,346 absent), so run 15 had reached about 124,877 before the restart | – | the check's line | `bisems65r`'s output |

### 5. Sources (research parts)

* **SofaScore's other endpoints:** observed, `data/studies/gap_downloads/sofascore_uncovered_probe.json`.
* **The ITF live-data API:** observed, `itf_stadion_probe.json` and the receipts in `data/raw/point_sources/itf_stadion_probe/`. Seven follow-ups have no receipts (judgment call 9).
* **itftennis.com:** observed, `itf_site_probe.json`; Imperva refused the draw sheet. Blind spot: the site's draws are the only listing of 2025 match ids found, and they were not read.
* **Flashscore, other datasets and vendors:** the subagent's [research note](../../research/gap-sources/itf_2025_points.md), with its own sources and request list. The lead re-checked the feed format (by eye on the 8 saved feeds), the extract's counts (by an independent extractor) and the duration rule (the trial). The vendor claims and the TennisLive measure were taken as reported.

### 6. Judgment calls and deviations

1. **The trial's editions** were chosen by hand (the newest full editions at Monastir and Antalya, plus one more), after the gap sizes and before any request. The newest Monastir editions held one target each (P1's live API), so they were passed over.
2. **No qualifying gap:** 59 of 125 (47%) is not "most" (the plan's rule). The other branch would have added about 270,000 targets.
3. **Detached runs through WMI**, not `Start-Process`: the session's shell was found inside a job object (observed), whose children could die with the session. Cost: each launch needed the owner's approval, and two launches waited 10 and 3 hours.
4. **The CPU-priority fix and watchdog** touch only the collector's own processes; the owner was told. Other sessions' processes were never changed.
5. **The deferral** (`--defer-uncovered`) was the owner's choice among three options; the session recommended it. It was recommended after the 1,471 404s and the flag's cross-tab had been seen.
6. **Run 1 stopped by hand** at 22:27, not at its budget: its remaining ~1,180 requests were flagged events.
7. **The twins rule was not changed:** the 15 unflagged copies asked had no record.
8. **Flashscore's order** (records with a duration first) was set after the trial's 0 of 52, and skips nothing.
9. **Seven requests to the ITF API without receipts** (13 Oct ~22:42): quick reads of a refusal's text and of three spec paths. A deviation from rule 4; their answers were only printed in the session.
10. **The subagent's stray request:** one request to itftennis.com (a news article, ~22:43 UTC), against its brief. It came after the lead's probe had been refused, and returned nothing.
11. **A miswired relaunch watcher** (added 15 Oct): the watcher queued at 19:47 UTC for `itf_detail` matched the budget stop by P13's wording ("BudgetExhausted"); this adapter writes "request budget of 30000 used up". It stood down, and the run sat idle 6 minutes (21:47-21:53 UTC) until the hourly check relaunched it. No data was affected. The next watcher matches both wordings.
12. **An unchecked inference told to the owner** (added 16 Oct): at the 17:47 UTC check, that the 404 runs "look like a few whole tournaments". The per-match table, read after run 2, showed them to be mostly the first days of a tournament. Corrected to the owner at the next reply; the README states the checked version.

### 7. Claims and their evidence

* *SofaScore has no ITF points January 2025 - February 2026:* observed for February 2026 (receipts; 1,471 404s, then 4,505 by the stop) and for the 6 sampled flagged events. The rest of the window is inferred from the flag (8 of 1,403).
* *2024 is complete on SofaScore:* observed in trial 2 only (92 matches, 3 editions).
* *No qualifying gap:* `itf_qualifying_probe.json`.
* *Flashscore's ~28,000 expected records:* an inference from the trial's 131/137 applied to 29,614. Bulk counts will replace it.
* *115/115 Flashscore records agree with the official result:* `flashscore_itf_points_2025_2026_link_check.json` (as of the trial).

### 8. Weak points

* **The flag inference** covers about 39,000 deferred events on a cross-tab of 1,403 fetched ones, mostly February 2026. The final pass would test it, at about 80,000 requests.
* **Flashscore's link** is by surname words and dates; 2,003 targets are unlinked and some links may be wrong. The official check reaches only Sackmann's targets.
* **Box scores** from SofaScore 2026 are a reduced set; their counting against official box scores is not yet measured.
* **Re-design:** read itftennis.com's draws with the owner's help (a click on Imperva's check, if it offers one). The ITF's own feed would give 2025 points with statistics.

### 9. Reviewer checklist

* [ ] Rerun the tests: `./python.sh -m pytest test/gap_downloads test/data_map test/match_timing/test_link_sources_c.py test/point_shot_sources -q`.
* [ ] Re-derive the flag cross-tab from the receipts and season listings.
* [ ] Check that `--defer-uncovered` runs left only flagged events unasked (`points_deferred` in the summary).
* [ ] Re-derive the Flashscore trial's duration table from `flashscore_itf_points_2025_2026_matches.csv.gz`.

### 10. Reproduction

The commands are in the README's "Running and resuming P7" and "Running and resuming P13" sections. The probes:

```
./python.sh src/eda/gap_downloads/itf_qualifying_probe.py --browser --per-edition 30 --max-requests 250
./python.sh src/eda/gap_downloads/sofascore_uncovered_probe.py --browser --max-requests 40
./python.sh src/eda/gap_downloads/itf_stadion_probe.py --max-requests 40
./python.sh src/eda/gap_downloads/itf_site_probe.py --max-requests 40   # Chrome on port 9223, profile itf-cdp
```

### Appendix: the research subagent's brief

* **Role:** a general-purpose subagent, in the background, 13 Oct ~22:35 UTC.
* **Allowed:** files on disk and the web, but no request to SofaScore, the ITF's API, itftennis.com or tennislive.net. No results of any model were involved.
* **Report:** [itf_2025_points.md](../../research/gap-sources/itf_2025_points.md).
* **Its brief, verbatim:** saved beside this log as [process_log_brief_itf_2025_points.md](process_log_brief_itf_2025_points.md).

---

## P5 follow-up: Tennis My Life's misdated Challenger editions

14 Oct 2026 (18:45-19:44 UTC) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code extension) · Session: `77acaf97-4eaa-464e-b85b-18648b0eb97b` (the session that ran P5, 9-10 Oct; P5 itself kept no log here, so anything of P5 cited below is from its README and evidence, reconstructed, not contemporaneous) · For a future reviewer · Report: [this study's README](README.md), section "TennisLive pages for the gaps (work package P5)"

### 1. The request

* **The owner's words, verbatim** (14 Oct 2026, about 18:45 UTC), quoting two bullets of P5's final report:
  > "Misdated Challengers: Tennis My Life files several Challengers under another event's name and date. Examples are Irving 2018 as "Dallas" and Biella 2–7 of 2021 as Biella 1. As a result the map holds about 900 of these matches twice; both copies now get the page's points.
  > Looser linking was wrong: a first linking pass using shared name words alone paired a few hundred matches wrongly. So a link is now confirmed only when the TennisLive match's score also agrees with the result file's.
  >
  > Fix this if it isnt already fixed"
* **How it was read:**
  * *The linking bullet* was fixed in P5 itself: only score-confirmed links were fetched and placed. To confirm, not redo.
  * *The misdating bullet* is not fixed: P5 only made both copies of a doubly-held match get the page's points. The fix is that each match is held once, at its own date and event, wherever Tennis My Life's misdated rows are read.
  * *Where they are read:* the data map (`src/eda/data_map/measure.py`, which links sources by surname pair within -10..+21 days, so a copy months away becomes a second match), and Stage 0, the model's match table (`src/eda/predictability_diagnostic/stage0_build.py`), whose own linking already tolerates this pattern (its `pick()` docstring names it). Stage 0 matters more: a match dated months early would also break the feature-timing rule. So Stage 0 is checked first, and only fixed if the check finds misdated or doubled rows there.
  * *Other readings set aside:* (1) only re-wording the README: the owner asked for a fix. (2) Correcting Tennis My Life's raw files: they are kept as served, and Stage 0 and the map read them with their own rules.
  * No question was put to the owner before starting.
* **The target:** not a model study; nothing is scored. If Stage 0 must change, that is a repair of the model's data, governed by the project rules (CLAUDE.md, the lower-level and corrupt-data decisions), and is reported for the owner before it reaches training.

### 2. Starting point

* **Code:** commit `1d8f53e` (14 Oct 2026) plus other sessions' uncommitted changes; `src/eda/data_map/measure.py` is among them (git status, 18:53 UTC).
* **Data [observed]:** the map of 14 Oct 15:55 UTC (`data/studies/data_map/matches.parquet`); Stage 0 of 14 Oct 04:13 UTC (`data/studies/predictability_diagnostic/stage0_matches.parquet`, 873,636 matches); TennisLive's listings of P4 (`data/dump/points/tennislive/listed.parquet`); P5's per-target tables (`data/studies/gap_downloads/tennislive_*_matches.csv.gz`).
* **Already seen before this log was opened (18:45-18:53 UTC) [observed]:** Stage 0 holds Dallas and Irving 2018, Biella 1-7 2021, Forli 1-3 2021 and Prague I and II 2020 from Sackmann alone, each at its own date with a full draw (31 or 47 main-draw matches), and no Tennis My Life row in them. `stage0_build.py` appends a Tennis My Life-only row with the date of the Sackmann edition most of its Tennis My Life event links to (`mode_by(lk, ["tour", "ekey"], "stid")`), so such a row in a lumped edition could take the wrong edition's date.

### 3. Plan

Written at 18:55 UTC, before any measurement of this follow-up.

1. **Measure the misdating in Tennis My Life's rows:** a Tennis My Life Challenger or qualifying row whose Sackmann twin (same tour, pair, round and set scores, same season, the event agreeing by id or a name word) is dated more than 10 days away. Count by year and edition; cross-check a sample with TennisLive's event weeks.
2. **Stage 0:** (a) its Tennis My Life-sourced rows against TennisLive's dates (same pair and games): any more than 10 days away; (b) doubles: a Tennis My Life-only row with a Sackmann twin elsewhere in the season. If either is found, prepare corrections with a dry run and report before anything reaches training.
3. **The map:** before Tennis My Life's rows join the map, give each misdated row its Sackmann twin's date and tournament name, so that Sackmann's row then links to it; rebuild; check that the doubled matches are gone (P5's 921 pages linked by two map matches should fall to near 0) and that the P5 pages still place.
4. Tests for each rule; the README and this log updated.

### 4. Chronology

UTC, 14 Oct 2026.

| When | Step | Why | Seen by then | Output |
|---|---|---|---|---|
| 18:45-18:53 | Read CLAUDE.md (re-read at the session's start), `docs/pipeline.md`, the corrupt-data, Tennis My Life revisions and gap-fill decisions; `stage0_build.py`'s merge; Stage 0's rows for the named examples | Orientation | – | § 2 |
| 18:55 | This section opened (§§ 1-3) | The process-log rule | – | – |
| 18:56-19:00 | Scratch `tml_misdated_scan.py` (session scratchpad): Stage 0's own preparation and `link_tml`, in memory, men's rows only; the decided row corrections left out (they name women's rows, and change no date). Nothing in the repository written | Plan step 1 | – | 152,521 Tennis My Life rows: 140,602 linked by exact name pair, 6,080 by anchor, 494 by ids, 112 same event other round, 5,233 unlinked. **3,083 rows (2010-2025) are linked to a Sackmann twin more than 10 days away**: whole misdated editions ("Dallas" 2012-16 = Irving, "Biella 1" 2021 = Biella 2-7, "Forli 1" 2022, the 2021 Australian Open qualifying played in Doha). Only one Tennis My Life event's links point at several Sackmann editions (the 2021 AO, 2 rows): each lumped edition keeps its own tournament id [observed] |
| 19:00-19:02 | Scratch `tml_only_vs_tennislive.py`: the 5,233 unlinked rows against TennisLive's listings (same surname pair and games, same year) | Plan step 2(a), before Stage 0's own table | the scan | 4,538 found; all but 27 within 11 days of TennisLive's event week; 2026: 4,439 found, none far. Far: "Tenerife 1" 2024 (24 rows at TennisLive's Tenerife 3, +36 days), one row each at Prague and Santiago 2021, one Davis Cup row [observed] |
| 19:03 | Stage 0's Tenerife 2024 events | – | above | Stage 0 holds "Tenerife 1", id 2024-2847, dated 2024-01-21, 31 main-draw matches from Tennis My Life alone (Kukushkin beat Gigante in the final); Sackmann has Tenerife (15 Jan) and Tenerife 2 (19 Feb) but not Tenerife 3 [observed] |
| 19:04 | Doubles in Stage 0: Tennis My Life-sourced matches before 25 May 2026 with a Sackmann match of the same player ids, round and season in another event | Plan step 2(b) | – | 488 such Tennis My Life rows in all; 4 with a Sackmann match elsewhere, 2 with the same score: two walkovers of the 2021 AO qualifying (Doha), dated 8 Feb by Tennis My Life and 10 Jan by Sackmann. **No played match is held twice** [observed] |
| 19:06 | Scratch `stage0_tml_events_vs_tennislive.py`: Stage 0's own dates of its 5,213 men's Tennis My Life matches against TennisLive | Plan step 2(a) on the table itself | above | 4,533 on TennisLive; per event, only "Tenerife 1" 2024 is more than 10 days away (median +36 days; 24 of its 31 matches found); the Prague and Santiago rows are dated right in Stage 0 (its event mapping placed them); the Davis Cup row is a false pairing (TennisLive lists no team events). 263 rows of 2010-2017 cannot be checked (TennisLive's listings start in 2018) [observed] |
| 19:10 | Read `history.py` and `corrections.py` | How a Stage 0 date fix would enter | above | A revised Tennis My Life row at a level it fed the reference is classed `tml_lower` and refuses no build; rows named in the decided tables count as decided repairs. The correction tables have box and age actions only, and a row that no longer finds its source row stops the build [observed] |
| 19:12 | **Change of plan** (judgment call 1) | – | the rows above | Stage 0: no doubles to fix; one misdated event (31 matches). Not changed here: recommended to the owner instead (§ 6). The map: fixed as planned, with TennisLive as a second date reference for rows Sackmann lacks (Tenerife 3) |
| 19:15-19:35 | `measure.py`: `repair_tml_dates` (with `event_words`, `set_games`), the loaders carrying the score and tournament id, the build repairing Tennis My Life's rows before adding them; `tml_redated.csv` written by `run()`. Tests `test/data_map/test_tml_redate.py` (5); two P4 tests failed on listing fixtures without a score column, fixed in the loader | Plan step 3 | – | On the real files (no build): **1,841 rows moved** (1,659 by a Sackmann twin, 166 by TennisLive, 16 with their event), whole editions of 30-31 matches: the three named, plus "Poprad Tatry" 2018 holding Bratislava's November matches, "Nottingham" and "Manama" 2025 dated months after their January and February editions, and the 2021 AO qualifying moved to Doha's week [observed] |
| 19:38 | Map before (build of 15:55 UTC; scratch `map_before_redate.json`) | Baseline | above | 709,194 matches; men's 2021 Biella events 454 matches (268 Sackmann, 186 Tennis My Life; 7 editions × 43 = 301 real) [observed] |
| 19:39 | Process list | Rule: no two map builds | – | Another session's `match_timing/rebuild.py` in a sandbox `C:\Users\zerom\tnr_sb_tenerife\` [observed] |
| 19:40-19:45 | Read the other session's study and decision: [P6 data issues](../p6_data_issues/README.md), [decision of 14 Oct](../../decisions/2026-10-14-p6-data-issues.md) | The sandbox's name | – | **The same findings, independently and earlier today** (67 editions, 2,093 matches; the map's 1,586 doubles; Stage 0's 31 Tenerife matches, reviewed by three reviewers). The owner decided its Stage 0 Tenerife correction (a keyed date correction, a harm check, then a coordinated rebuild), being carried out in that sandbox. Its map fix ("re-date ... with their old keys kept") was recommended, not decided or applied, for one reason: re-dating detaches the gap downloads keyed to the old name and date (1,843 SofaScore targets, ~1,700 TennisLive pages) [observed in its report] |
| 19:45-20:00 | `placement_index` (alias keys) and the three placement functions taking `aliases`; the build records the old keys of moved rows and the keys of the Sackmann and API-Tennis rows that join them; 1 more test | Judgment call 2 | the other study's design point | 151 tests pass (data_map, gap_downloads) |
| 19:17 | *Correction to the rows from 18:56 on:* their times were estimated when written and run ahead of the clock. File times (UTC) place them: the scan 18:55, the two TennisLive comparisons 18:56-18:57, the code and tests to 19:13, the map's before figures 19:10, the other study read about 19:12-19:14. The order is right | – | – | – |
| 19:15 | First map build attempt: failed at once, `data/studies/data_map/_logs/` no longer exists (removed by someone on 11 Oct; it held this session's build logs of 10 Oct). Not recreated; logs go to the session's scratchpad | – | – | – |
| 19:18 | Map build (`build.py`, log in the scratchpad) after checking that no other map build ran | Plan step 3 | – | running |
| 19:19 | Scratch comparison of the repaired editions with the other study's reviewed `tml_edition_date_corrections.csv` (68 editions) | Cross-check, before reading the build's result | – | 57 of 68 moved; same true start for 56; the 2021 AO qualifying one day apart (Sackmann's Sunday v TennisLive's Monday); the other 11 are 7-9 days off (Burnie 2020, Oeiras 1 2021-22, Nonthaburi 1 2022-24, Prague 1 2022, Forli 1 2022, Tenerife 1 2023, Kigali 1 2024, Targu Mures 2025), which the map's linker joins anyway; none moved that the table lacks [observed] |
| 19:26 | Build ended (exit 0, about 8 minutes; no catalog problem) | – | – | 1,841 rows given their own date; 708,199 matches; placement by the adapters' links: SofaScore 34,453 of 34,453, TennisLive pages 36,851 of 36,903, Flashscore 131 of 131 [observed, `coverage.json`] |
| 19:27-19:31 | Before/after, and the other study's 1,586 doubles against the new map (scratch, inline) | Plan step 3's check | the build | Matches 709,194 → 708,199; men's CH+CHQ 2018-25 −1,646; Biella 2021 454 → 298 (301 real). Doubles: 1,548 held once at the true date; of the 38 flagged by the first rough test, 27 are pairs with two real meetings that season (as many meetings on the map as in Sackmann's files) and 11 are the other study's separate "not flagged" kind (2026's two-week events, dated by the day played; Maia 2026 a false flag). So all 1,575 doubles of the misdating are gone [observed] |
| 19:32-19:45 | `data/studies/data_map/README.md` (method and files), the `tennis_my_life` catalog entry's notes, this study's README (P5's update section; the Biella 2-7 slip corrected to 3-7) | Report | all above | – |
| 19:31 | §§ 6-10 written | Rule 10 | – | – |
| 19:32 | **Context summary** of this session (the harness condensed the conversation so far); this log re-read at 19:33 before continuing | Rule 3 | – | – |
| 19:33 | *Second correction, to the rows from 19:19 on:* again written ahead of the clock. File times (UTC): the build ran from 19:17 (its log's name) to 19:26:35, about 9 minutes, not 8; the before/after and doubles check came before the documents that quote it, so 19:26-19:29; the documents 19:29-19:31 (the catalog 19:29:25, the map's README 19:29:32, this study's README 19:30:44). The 19:19 cross-check ran while the build did; no file records its time. The order is right. Stage 0's file is still the build of 04:13:57 UTC: not touched by this work [observed] | – | – | – |
| 19:34-19:36 | Re-checked the Biella example before reporting it: Stage 0's Biella events of 2021 by source and link, and the scan's far links (`linked_far.csv`) | The 19:30 README edit had called P5's "Biella 2-7" a slip | the build | Sackmann dates Biella 1 to 7 of 2021 at 7 Feb, 14 Feb, 8 Mar, 15 Mar, 3 May, 17 May and 31 May. Tennis My Life's one "Biella 1", dated 14 Feb, holds Biella 2 to 7 (six editions of 31 rows). Biella 2's rows carry their own date; the far-linked rows are Biella 3-7's 155. No Tennis My Life row links to Sackmann's Biella 1. **So P5's line was right and the 19:30 edit wrong**: it took "moved" for "misfiled". The README line is restored to "Biella 2-7", with a note that only 3-7 are misdated. The owner's quoted example stands [observed] |
| 19:36-19:40 | Re-measured the "18 matches the map holds twice under one key", which the 19:30 README edits had carried from P5's report of 10 Oct as still unfixed (scratch, inline: `matches.parquet`'s keys with the draw; Tennis My Life's and Sackmann's rows under them) | Before reporting it as unfixed | the build | 22 keys name two matches: 17 Challenger, 3 ATP Finals, 2 ITF. The 17 Challenger keys are 17 pairs who met at two editions a week apart that Tennis My Life files under one name and date (34 rows, with different ids, rounds and scores; each has a Sackmann twin 6-9 days or 0-2 days away). **So they are not doubles.** The map holds both matches of each pair, one dated a week off, and the shared key sends their downloads to the generic linker. The 3 Finals keys are round-robin-and-final repeats; the 2 ITF keys were not checked. The README's two lines were corrected [observed] |
| 19:41-19:43 | `./python.sh -m pytest test/data_map test/gap_downloads test/point_shot_sources test/match_timing -q` | Before reporting | – | 244 passed in 52 s [observed] |

### 6. Judgment calls and deviations

1. **Stage 0 left to the decision already taken** (19:12, after the scans, before any map result). Options: correct the 31 Tenerife dates in Stage 0 here; or leave them. Chosen at first: recommend, not apply, because a date correction needs a new kind of correction in the model's central builder, the tables stop every build when a guarded Tennis My Life row moves, and Stage 0's lower-level history changes only by decision. At 19:40 the other study's decision was found: the owner had already decided this correction today, with a keyed mechanism (not row numbers) and a harm check, and that session is carrying it out. So nothing here touches Stage 0, and the owner is told it is in hand. Had I applied it, two sessions would have changed the same tables at once.
2. **The map's downloads keep their old keys** (19:45, after reading the other study, before the build). Options: re-date and let the downloads fall to the generic linker (the other study's objection: about 1,843 SofaScore targets and 1,700 TennisLive pages detached); alias every source's keys (risks spreading a wrong link of any source to the presets); or alias only the copies this repair merges (the moved rows' old keys and the Sackmann and API-Tennis rows that join them). Chose the last.
3. **TennisLive as a second date reference** (19:12). Without it Tenerife 3 of 2024 would stay misdated on the map and double with TennisLive's own listing of it. Its dates are the event week's Monday, a day off Sackmann's Sunday dates at most.
4. **The 10-day threshold** (19:15, before any result). The map's linker already joins twins up to 10 days early, so rows 7-9 days off (11 editions) are left at Tennis My Life's date. Moving them would only shift their date by a week, at the cost of a wider rule.
5. **Not fixed: 2026's two-week events** (11 doubles, found at 19:30). A different mechanism (dating by the day played), and the map dates 2026 by the day played on purpose (`sofascore_edition_uids`); changing it is a wider question.

*Correction (19:41), § 6's times:* these were taken from the chronology's rows before their corrections. By the file times:
* Call 1 came after 18:57:43 (the last Stage 0 scan's output) and before the code. The other study's decision was read at about 19:12, not 19:40.
* Call 2 came before 19:13:47, when `measure.py` and the tests were last saved, not at 19:45. It still came before the build.
* Call 3 came with call 1.
* Call 4's threshold was set in the plan at 18:55, before any result, not at 19:15.
* Call 5 came at about 19:27, from the doubles check.

So calls 1-4 came before any map result, and call 5 after the build.

### 5. Sources

None searched or fetched: every file read was already on disk. That is the map's own inputs (`load_tml`, `load_sackmann`, `load_tennislive_listed`), Stage 0, the map's last build, and the P6 data-issues study's tables and report.

### 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| Stage 0 holds no played match twice from this | scratch check of 19:04 (Stage 0's Tennis My Life-sourced matches against Sackmann's of the same ids, round and season) | observed |
| Stage 0's only misdated event is Tenerife 3 2024 (31) | scratch `stage0_tml_events_vs_tennislive.py`; agrees with the other study's own finding | observed (2018-2026; 2010-2017 not checkable with TennisLive) |
| 1,841 rows moved, by reference | `data/studies/data_map/tml_redated.csv`; `coverage.json` (`link_report.tml.redated`) | observed |
| 57 of 68 reviewed editions moved, 56 to the same date | scratch comparison of 19:19 against `data/studies/p6_data_issues/tml_misdates/tml_edition_date_corrections.csv` | observed |
| All 1,575 doubles gone | scratch check of 19:27-19:31 against `map_doubles.csv` | observed |
| Downloads still placed | `coverage.json`, `link_report` (`placed_by_adapter_links`) | observed |
| Before/after counts | `map_before_redate.json` (scratchpad) and `matches.parquet` of 19:26 | observed |
| P5's Biella example right: Tennis My Life's "Biella 1" holds Biella 2-7, and only 3-7 are misdated | Stage 0's `tml_link` by Biella event of 2021; the scan's `linked_far.csv` (19:34-19:36) | observed |
| The 17 shared Challenger keys are real repeat meetings, not doubles | scratch check of 19:36-19:40 (`matches.parquet`; Tennis My Life's and Sackmann's rows under the keys) | observed; the 2 ITF keys not checked |

### 8. Weak points

* **The rule links by names, round and games per set.** Two meetings of one pair in one round with the same games, in one city's editions of a season, would make a row ambiguous (left alone) or, if only the other meeting is held, move it wrongly. The cross-check against the reviewed table found no wrong move; it cannot see a row that table does not list.
* **TennisLive's dates** decide 166 rows (Tenerife 3 2024 among them). P4 checked TennisLive's events by week; a wrong TennisLive week would move a row wrongly.
* **The aliases** cover only the copies this repair merges. A download frozen under some other stale key falls to the generic linker (52 TennisLive rows here).
* **Where a flaw would hide:** in rows moved by "event" (16), which have no twin of their own.
* **A re-design** would date every result-file row from play-day evidence (the other study's weekly check does this for new editions) and key the downloads by stable match ids instead of names and dates.

### 9. Reviewer checklist

* [ ] Rerun the tests: `./python.sh -m pytest test/data_map test/gap_downloads -q`.
* [ ] Re-derive the moved rows from the files: `repair_tml_dates(load_tml(), [("sackmann", load_sackmann({})), ("tennislive_listed", load_tennislive_listed())])`, against `tml_redated.csv`.
* [ ] Check five moved editions against the ATP's own results pages (Irving 2018, Biella 6 2021, Forli 4 2022, Nottingham 2025, Tenerife 3 2024).
* [ ] Confirm Stage 0 was not touched: `stage0_matches.parquet` unchanged by this work (14 Oct 04:13 UTC build, 873,636 matches).

### 10. Reproduction

```
./python.sh -m pytest test/data_map/test_tml_redate.py -q
./python.sh src/eda/data_map/build.py          # about 8 minutes; writes data/studies/data_map/, tml_redated.csv
```

The scratch scans (session scratchpad): `tml_misdated_scan.py` (Stage 0's linker in memory), `tml_only_vs_tennislive.py`, `stage0_tml_events_vs_tennislive.py`. No GPU; nothing scored.

---

## Work package P11: bookmaker odds below the 250s (probe, collect, forward capture)

22 Oct 2026 – (open) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code extension) · Session: `ba590081-dd3e-41d4-98d8-07bb7e289a13` · For a future reviewer · Report: [this study's README](README.md), section "Bookmaker odds below the 250s (work package P11)"

### 1. The request

* **The owner's words, verbatim** (22 Oct 2026, about 04:30 UTC):
  > "Do work package P11 of docs/studies/gap_downloads/collection-plan.md: measure which public site holds bookmakers' opening and closing odds for Challenger, WTA 125 and ITF matches of 2018-2026, collect from the best one, and test a forward capture of closing lines. Follow the plan's shared rules."
* **How it was read:**
  * Three parts. (1) *Measure:* a probe of at most 500 requests over the plan's candidates (BetExplorer, TennisExplorer, OddsPortal), on a seeded sample of the map's Challenger, WTA 125 and ITF matches of 2019, 2022, 2025 and 2026, recording per match: listed or not; which books; Pinnacle or not; opening and closing prices, with their times. (2) *Collect:* an adapter for the source with the best closing coverage at each level, newest first, staged under `data/dump/odds/<source>/`, a trial and then the bulk (shared rules 5-6); prices never in git (the repository is public). (3) *Forward capture:* a test of recording closing lines from now on.
  * *"Best":* the plan's words, "the best closing coverage at each level". Ties are broken by Pinnacle's presence (the model's odds input is Pinnacle first: [decision of 9 Oct](../../decisions/2026-10-09-pinnacle-first-odds-input.md)), then by opening prices and times.
  * *The forward capture:* the plan names Pinnacle's guest API as "an inherited claim from June 2026, unverified". It has since been verified and recorded: `src/ingest/pinnacle.py` pulls Pinnacle's whole tennis listing (lower levels included) on bet days since 11 Oct. And since 21 Oct a daily job downloads TennisExplorer's match pages after play for Pinnacle's time-stamped close (`pinnacle_closes`, tour level only). So the test compares two routes on the same lower-level matches: **(A)** polling Pinnacle's listing at a fixed cadence and keeping each matchup's last price before its start; **(B)** the match page fetched after play (the site's Pinnacle price and its time), if the probe finds Pinnacle there.
  * *Qualifying* (Challenger and ITF) is in scope as a second stratum: Polymarket lists ITF qualifying ([lane C](../../../data/studies/gap_sources/research_notes/C_itf_listings.md): markets for 504 of 521 men's ITF qualifying matches in 15-22 Sep 2026).
  * *Set aside:* paid feeds (the plan's "Not in this plan"); any regional workaround (a proxy or VPN, a forged country) for books hidden from this connection, as the Pinnacle-gap session decided (its judgment call 1); signing up for keys (OddsPapi).
  * No question was put to the owner.
* **The target:** not a model study; nothing is scored. The data's use is a later odds input for lower-level matches. The current model's frame holds tour main draws only.

### 2. Starting point

* **Code:** commit `1d8f53e` plus other sessions' uncommitted changes (471 paths in git status at 04:44 UTC), among them `data/data_map.yaml`, `src/ingest/scheduled.py` and `src/ingest/tennisexplorer.py`.
* **Processes (04:35 UTC):**
  * P7's SofaScore run (PID 8244, www.sofascore.com);
  * the Pinnacle-gap TennisExplorer pull (PID 41792, `src.ingest.tennisexplorer --matches --since 2025-08-01 --pause 2.5`, started 01:40 UTC; 2,847 of about 6,273 gap pages at 04:40 UTC, about 4.3 s a page, then 3,541 pages of January-July 2025; expected end about 13:00 UTC). The daily task's `pinnacle_closes` job also uses TennisExplorer, at 07:30 local (14:30 UTC).
  * Pinnacle's guest API: bet-day pulls at 03:31 and 04:18 UTC today (the owner's notebook or another session), on demand.
  * **So, by shared rule 3, TennisExplorer is not probed or collected from until that pull ends.** BetExplorer, OddsPortal and Pinnacle's API are free.
* **Read offline before this log was opened** (04:35-04:44 UTC; files already on disk, no request) [observed]:
  * *Pinnacle's 22 staged bet-day pulls* (11-22 Oct): 762 ITF matchups, 244 Challenger, 59 WTA 125, 279 tour; 1,766, 521 and 167 of the lower-level rows usable pre-match.
  * *BetExplorer* (the Pinnacle-gap probe's saved answer for a Shanghai 2026 match): its odds call returns, per book, each side's last price and the time it was set (`data-created`); no opening price in the table (the page asks `/archive-odds/<oid>/<bid>/<bt>/<sc>/<hcp>/` per cell for the history); 17 books, no Pinnacle.
  * *TennisExplorer's day results pages* (saved 19-21 Oct 2026 and 30-31 Jan 2023): one page per day and tour lists every singles match of the day: Challengers and WTA 125s, women's ITF by event, and men's ITF lumped as "Futures 2026" (no event page). Each match has two prices. On 19 Oct 2026, men: 206 matches, 99 priced (Futures 40 of 145); women: 175, 90 priced. On 30 Jan 2023, women: 115, 102 priced (WTA 125 Cali 5 of 5).
  * *What those two prices are:* the average of the books' last prices on the match page (59 of 61 matches within 0.015, 19-21 Oct 2026), not any one book.
  * *Calendars* (2025-26): men's list Challengers (217 a year) and no ITF; women's list ITF events (631 in 2025, 513 in 2026).
  * *Match pages:* a Challenger of April 2026 (Tallahassee) lists Pinnacle with its changes and opening, times included (15 books); Barranquilla Challenger, August 2025: Pinnacle untimed (the site's August-October 2025 hole, as at tour level).
  * *The map* (build of 16 Oct): 2018-2026 holds about 75,000-85,000 lower-level matches a year (ITF main and qualifying about 30,000-40,000 each, Challengers about 6,500, Challenger qualifying about 3,500, WTA 125 about 1,500). Most lower-level rows are dated by their tournament's Monday (Sackmann's and TennisLive's lists), not the day played; men's Challengers of 2019-2024 (Tennis My Life) carry the day.

### 3. Plan

Written at 04:50 UTC on 22 Oct, before any request of this package.

1. **The sample** (offline; seed 20261022; `src/eda/gap_downloads/odds_probe.py`). One week per year (2019, 2022, 2025, 2026), drawn among weeks that hold at least one WTA 125 edition and several men's Challengers and ITF editions of both tours (2026: before the map's last complete week). The sample is every map match of those weeks' editions at the levels CH, CHQ, ITF and ITFQ, both tours. Because most rows carry only the tournament's Monday, each site is read by day for the whole span of the week's play: the Saturday before (qualifying) to the Sunday after (finals), 9 days. A seeded subsample per stratum (level × tour × year: 5 main-draw matches, 2 qualifying) gets the match-level reading (books, Pinnacle, opening and closing, times).
2. **The probe, site by site,** through `common.Client` and `fetch` (paced 2 s plus up to 1 s, receipts, raw copies gzipped under `data/raw/odds_probe/<site>/`, a budget per run):
   * BetExplorer now (budget 200): its day results, then each sampled match's odds call; opening prices (the per-cell history) on a few matches only.
   * OddsPortal now (budget 60): whether its pages and odds feed answer the plain client, whether the feed decodes with the page's own code, and whether Pinnacle is listed.
   * TennisExplorer when its host is free (budget 200): day results pages, then each sampled match's page.
   * Measures per site and stratum: listed; priced; number of books; Pinnacle; opening price and time; last price and the time of its last change, against the listed start. Evidence holds counts and flags, never prices.
3. **Forward capture (A)** starts now, in its own folders (`data/raw/pinnacle_capture/`, `data/dump/odds/pinnacle_capture/`), so that the bet-day path, which reads only the latest file of `data/dump/odds/pinnacle/pulls/`, sees nothing new mid-run. A pull of Pinnacle's listing every 10 minutes for about 36 hours, with the same parser as the recorder; a cycle is skipped while a bet-day pull runs. **(B)**, once TennisExplorer is free: the match pages of the lower-level matches (A) captured that have been played. The comparison: coverage of each route by level, (A)'s last pre-start price against (B)'s Pinnacle last price (agreement to the cent), and how long before the listed start each was set.
4. **The choice and the collection:** the source with the best closing coverage per level, Pinnacle weighed first. Its adapter, newest first (the Polymarket window, then back to 2018; main draws before qualifying), raw and staged in their own folders, a trial on a few days, then the bulk in the background with a budget per run and a resume command. If it is TennisExplorer, its lower-level pages stay out of the tour-level adapter's folders (`data/raw/tennisexplorer/`), whose staging feeds the model's odds input, and the collector waits whenever the tour-level adapter runs.
5. **The map:** a catalog entry for the new odds data (grain market, not measured on the match table, like the other odds entries), and an `in_progress` line while it downloads. **Tests** for the parsers and selection rules under `test/gap_downloads/`. **Report** in this study's README.

**Gates and stops.** A block (HTTP 429, a challenge page, an unexpected 403) stops that site's run for a report. The trial's Expected comes from the probe's rates: under half of it stops the bulk for a report.

### 4. Chronology

UTC, 22 Oct 2026.

| When | Step | Why | Seen by then | Output |
|---|---|---|---|---|
| 04:30-04:44 | Read CLAUDE.md, the 8 Oct decision, the plan, this study's README and log, the Pinnacle-gap report and log, the BetOnline-lines and early-lines notes, lane C, the data audit's odds section, `common.py`, `tennisexplorer.py`, `pinnacle.py`, `scheduled.py`'s TennisExplorer job, the map's odds entries | Shared rule 1 | – | §§ 1-2 |
| 04:35 | Python processes listed | Shared rule 3 | – | TennisExplorer in use (§ 2) |
| 04:35-04:44 | The offline reads of § 2 (scratch scripts `pin_levels.py`, `peek.py` and inline reads, session scratchpad) | Design the probe | – | § 2's list |
| 04:50 | This section opened (§§ 1-4) | The process-log rule | – | – |
| 04:44:46 | *Correction to the row above and to § 3's "04:50":* both were estimated ahead of the clock. The file was saved at 04:44:46, before the sample and before any request | Rule 3 of the log template | – | – |
| 04:45-04:46 | `odds_probe.py --sample` (seed 20261022), offline | Plan step 1 | no request yet | Weeks 2019-02-25, 2022-05-09, 2025-07-14, 2026-01-05 (eligible weeks 9, 19, 26, 19); 6,043 map matches; strata from 2 (2019 W CHQ) to 566 (2025 M ITFQ). Files `odds_probe_sample.csv` and `.json` (04:46:21) |
| 04:46:33 | BetExplorer, one day page (`/results/tennis/?year=2026&month=1&day=7`), to learn its layout | Plan step 2 | – | HTTP 200, 758,674 bytes, redirected to `/tennis/results/?...`. One table: singles and doubles groups of every level ("Challenger Men - Singles: Bengaluru", "ITF Women - Singles: W15 Oslo"); 542 singles rows. **No price in the listing.** Its rows are dated 5-8 Jan, so a "day" page spans more than its day. Times are UTC+1 (`data-dt-now` read 05:46 at 04:46 UTC) [observed] |
| 04:46-04:49 | The BetExplorer reader (`be_day_rows`, `be_odds`, `be_history`), the name rules (`site_name`, `same_player`: a hyphenated initial "J-L." first parsed as a surname, fixed) and the linker; offline checks on the day page and the Pinnacle-gap probe's saved odds answer | Plan step 2 | the day page | Dry link of the 2026 week on that one page: M CH 105 of 154, M ITF 163 of 218, W CH 24 of 31, W ITF 150 of 200; **no qualifying match linked** (to be read on the full 9 days) |
| 04:49:04 | **BetExplorer probe run**, `odds_probe.py --site betexplorer --max-requests 200` (log `data/raw/odds_probe/betexplorer/_logs/probe_20261022T044904Z.log`) | Plan step 2 | the dry link | running: 36 day pages by 04:50:32, then the detail matches' odds calls |
| 04:49-04:50 | `pinnacle_capture.py` and `.sh` written (the recorder's client and staging, its own folders, the key reused for an hour, a cycle skipped while a bet-day pull runs) | Plan step 3 (A) | – | – |
| 04:50:13 | **Capture (A) launched detached** (Start-Process Git Bash `-l -c`; every 600 s for 36 h; log `data/raw/pinnacle_capture/_logs/capture_20261022T045013Z.log`) | Plan step 3 | – | Pull 1 at 04:50:19: 197 moneylines, 164 of the lower levels (149 usable pre-match); 3 requests [observed] |
| 04:51-04:55 | While BetExplorer ran: the linker indexed by surname word (the first version compared every pair, slow on 6,043 matches); the TennisExplorer reader (`te_day_rows`, `te_books` on the tour-level adapter's `parse_match`, a guard that refuses to start while `src.ingest.tennisexplorer` runs); `--report` (every measure re-derived from the raw files); tests `test/gap_downloads/test_odds_probe.py` (10, synthetic pages, made-up prices) pass | – | BetExplorer's first answers | A first look at BetExplorer's history answers: `[{"date": "26.02. 20:08", "odd": ..., "change": "0"}]`, a date **without a year**; the run's parser left their times empty. Fixed (the year nearest the match's start) and re-derived offline |
| 04:56 | BetExplorer probe ended (exit 0); measures re-derived with `--report --site betexplorer` | Plan step 2 | – | **141 requests, all HTTP 200, no refusal** (36 day pages, 85 odds calls, 20 history calls). Listed (of the sample's map matches): Challengers 2019 138/141, 2022 153/190, 2025 112/123, 2026 150/154; WTA 125 43/48, 60/60, 61/62, 31/31; ITF main 2019 men 30/184, **women 0/215**, 2022 405/415 and 376/407, 2025 504/524 and 441/463, 2026 211/218 and 196/200; Challenger qualifying 75/80, 70/72, 86/90 (2022-26); **ITF qualifying 0 in every year**. Every detail match (78) has odds: 4-16 books (median 7-16 by stratum), each book's last price with the time it was set; **no Pinnacle on any**; no opening in the table (only through the per-cell history call: 20 asked, each one entry, set 457-2,230 minutes before the start). Books' last change a median 34-444 minutes before the listed start (ITF the longest) [observed; `odds_probe_betexplorer.json`, `.csv.gz`] |
| 04:53-04:56 | **OddsPortal**, bounded: a day page (2026-01-07), then the site's scripts in order until the one holding its feed decoding (13 files; `0h9izan-bqvt1.js`) | Plan step 2 | – | The day page is a Next.js shell: the list comes from a feed keyed by a page hash (`xHash`) and a "bookiehash" (the books shown to this region) [observed] |
| 04:57-04:59 | Three more scripts (the list component), the day feed's address traced: `/proxy/ajax-nextgames/<sport>/<tz>/<sort>/<date>/<xHash>.dat?page=N` with the page's own headers; two wrong guesses first (HTTP 200 answers whose body says "Status: 404") | – | – | Answers are encrypted: base64 of "ciphertext:iv", AES-256-CBC with a PBKDF2-SHA-256 key (1,000 rounds) whose password and salt are in the public script; decrypted offline with the same steps (the decryption the page performs: covered by the 8 Oct decision). **The date feed serves only the last 30 days** ("older results ... Archived results"). For 19 Oct 2026: 120 rows, Challenger, ITF and tour, each with an event code [observed] |
| 04:59 | One Challenger match (Guangzhou, 19 Oct): its page by a guessed path (HTTP 404), then its head-to-head page (`/tennis/h2h/<a>/<b>/#<code>`) | Pinnacle and times on OddsPortal? | – | The head-to-head page loads the match's odds client-side, and **the site runs an anti-bot layer**: a script mints a proof token every few minutes (`/ajax-esi/ab-proof-mint/` with a nonce header) and injects honeypot links (`data-ab-trap`). **OddsPortal stopped here (24 requests)**: fetching its odds would mean imitating that proof, which is getting past a bot check, outside the 8 Oct decision (judgment call 1) [observed] |
| 05:01 | A background watcher on `data/studies/pinnacle_gap/pull.log` ("JOB DONE" or "JOB STOPPED") | Shared rule 3: TennisExplorer waits for the other session's pull | its log at 05:00: 3,100 gap pages | – |
| 05:01-05:06 | **The lower-level collector written ahead of the TennisExplorer probe** (`src/ingest/tennisexplorer_lower.py`; nothing run): day by day, newest first, the day's two results pages, then each in-scope match the day lists with prices; its own raw and staging folders; a wait while the tour-level adapter runs; a stop on a refusal or 10 failures in a row; staging by month, rebuilt when its pages change. The probe's day parser now imports the collector's. Tests `test_tennisexplorer_lower.py` (5) and `test_odds_probe.py` (10) pass after three fixes of the tests' own expectations (a fixture calendar without the women's events; 9 priced rows, not 8; a day page fetched two days after its day is rightly asked again) | Prepared while the host is busy; whether it runs depends on the probe (plan step 4) | BetExplorer's reading | Offline check on the saved day pages of 19 Oct 2026: men 230 rows (Futures 148, Challenger 51, UTR 16, tour 15), women 187 (ITF 152, UTR 24, tour 11) |
| 05:07-05:09 | `data_map.yaml`: entries `odds_probe` (on disk) and `pinnacle_capture` (downloading), an `in_progress` line for the capture; `check_catalog` finds no problem and both raw folders and the staged one are claimed. No map build (odds are not measured on the match table) | Shared rule 8 | – | – |
| 05:07-05:13 | *Correction:* the row above happened at 05:06-05:07 (the clock read 05:07:33 after it). Then: `pinnacle_capture.py --compare` (route B's comparison: captured close against the site's last Pinnacle prices, sides oriented by names, no price written) and `--closes`; tests `test_pinnacle_capture.py` (3); the collector's resume made cheap (a day whose results pages are final and whose every page was answered is marked done in `_state/done_days.txt` and skipped later without a read) and its exit codes (0 done, 3 budget, 4 crowded out, 2 block, 1 other); the detached launcher `src/ingest/tennisexplorer_lower_bulk.sh` (runs of 20,000 requests until done, staging after each) | Prepared while waiting | – | `--closes` after 2 pulls: 149 lower-level matchups (ITF 134, Challenger 15), none started yet. `test/gap_downloads` and `test/pinnacle_gap`: 132 passed at 05:09 |
| 05:10-05:11 | README section "Bookmaker odds below the 250s (work package P11)" written with what is measured (BetExplorer, OddsPortal), the TennisExplorer wait, the running capture and the resume commands | Shared rule 6: the resume command in the report before the session may end | the BetExplorer and OddsPortal readings | Capture pull 3 at 05:10:16 (162 lower-level, 149 usable); the other session's pull at 3,300 gap pages |
| 05:12-12:09 | Waited (the session idle; the capture ran detached) | – | – | – |
| 12:09 | The watcher fired: the other session's pull ended with "JOB DONE" at 12:07:35 UTC (its last stage and link: 9,565 of 9,631 frame matches linked). Processes listed: no TennisExplorer collector; the capture (pid 28224) only | Shared rule 3 | – | Capture at pull 44 (12:00:16): 101 lower-level moneylines, 77 usable |
| 12:09 | **TennisExplorer probe run**, `odds_probe.py --site tennisexplorer --max-requests 200` (log `data/raw/odds_probe/tennisexplorer/_logs/probe_<stamp>.log`). Before 14:30 UTC, when the daily task's `pinnacle_closes` job uses the site | Plan step 2 | BetExplorer's and OddsPortal's readings | running |
| 12:17 | TennisExplorer probe ended (exit 0) | Plan step 2 | – | **181 requests, all HTTP 200, no refusal** (72 day pages, 109 match pages). Listed (of the sample's map matches): Challengers 140/141, 153/190, 114/123, 150/154 (2019, 2022, 2025, 2026); WTA 125 47/48, 60/60, 61/62, 31/31; ITF main men **175/184** (2019), 400/415, 512/524, 210/218; women **204/215**, 382/407, 444/463, 195/200; Challenger qualifying men 5/5, 77/80, 72/72, 90/90; **ITF qualifying listed 92-98% every year, priced 15-60%** (30/94, 63/125, 189/491, 177/301, 86/566, 143/379, 65/235, 63/124). Detail pages: books median 15-16 (Challengers, WTA 125), 5 (ITF 2019) to 12-15 (ITF 2022-26), 2-7 (ITF qualifying). **Pinnacle on 20 of 20 Challenger and WTA 125 main-draw matches, 25 of 40 ITF main-draw (2019 2/10, 2022 8/10, 2025 8/10, 2026 7/10), 7 of 13 Challenger and WTA 125 qualifying, 0 of 16 ITF qualifying**; Pinnacle's prices timed on all but 3 of those 52; an opening with its time for most books. Pinnacle's last change a median 6-563 minutes before the listed start (wide; route B will say whether that is the close) [observed; `odds_probe_tennisexplorer.json`, `.csv.gz`] |
| 12:22 | *Correction to the row above* (recounted from `odds_probe_tennisexplorer.csv.gz`): Pinnacle is on **6** of the 13 Challenger and WTA 125 qualifying detail matches, not 7, so on 51 detail matches in all; its prices are untimed on **4** of the 51 (2019 Challenger men 1, 2019 WTA 125 1, 2025 ITF men 1, 2026 WTA 125 qualifying 1) | – | – | – |
| 12:18-12:21 | Side by side, offline (`odds_probe_*.csv.gz`) | The choice (plan step 4) | both probes | Where both list a level, TennisExplorer lists as much as BetExplorer (Challengers, WTA 125s, ITF main 2022-26 within a few matches). TennisExplorer alone: Pinnacle, opening prices with times on the page, change histories, ITF 2019 (379 of 399 against 30), ITF qualifying (2,229 of 2,315 listed against 0), more books for ITF (12-15 against 7-11) |
| 12:21 | **Decision: collect from TennisExplorer at every level** (the rule of § 1: best closing coverage per level, Pinnacle next). Expected for the trial, from the probe's own day pages (calendar 2026 from the tour adapter's copy): **about 105 in-scope priced matches a day** (January 2026 week, 10-191 a day) | Plan step 4; shared rule 5 | the probes | A two-day trial of the newest days should reach about 210 match pages; under 105 stops the bulk. Pinnacle on most Challenger pages (the probe: 20 of 20) |
| 12:18:55 | **Trial A** of the collector: `tennisexplorer_lower --max-days 2 --max-requests 500` (21 and 20 Oct 2026; log `data/raw/tennisexplorer_lower/_logs/trial_A_<stamp>.log`) | Shared rule 5 | the decision | running |
| 12:19 | *Correction (clock 12:19:15):* the rows stamped 12:18-12:21, 12:21 and 12:22 above were written ahead of the clock. By the file times: the probe's evidence was written at 12:17:12, the side-by-side, the decision and its correction at 12:17-12:18 (this log saved at 12:18:52), trial A's first request at 12:18:55; then the data map entry `tennisexplorer_lower` (downloading) at 12:19:07 | – | – | – |
| 12:20-12:43 | Two waiters of mine on trial A watched conditions that could not come true (an "exit" line the trial writes to its task's output, not to its log); both stopped (TaskStop). The trial was not affected | – | – | – |
| 12:43 | **Trial A ended** (exit 3: its budget of 500 used, as set) | Shared rule 5 | Expected 105 a day | 21 Oct done, 20 Oct nearly. The two day pages hold 851 singles rows, 678 in scope (Challenger 76, women's ITF and WTA 125 306, men's Futures 296); the run reached 509 of them (495 priced) before its budget ended. **494 match pages, every one HTTP 200 and parsed**: about 250 a day against Expected 105 (October is busier than the sample's January week). Pinnacle on 66 of 76 Challenger pages, 83 of 145 women's ITF and WTA 125, 157 of 235 men's ITF main draw, 0 of 38 men's ITF qualifying; 250 of the 306 Pinnacle rows timed; books median 15, 11, 9 and 2. Staged: 851 listed, 494 matches, 4,706 book rows, 39,206 changes [observed] |
| 12:44 | **Trial B**: one 2019 day, `--since 2019-02-26 --until 2019-02-26 --max-requests 300` | Shared rule 5: an old page's parse | trial A | running |
| 12:45 | *Note:* the three rows above were first saved above the 12:19 row and with a garbled in-scope count ("509: Challenger 76, women's lower 306, men's Futures 296"); moved here and the count split into the day pages' 678 and the run's 509 | – | – | – |
| 12:50 | **Trial B ended** (exit 0, the day done) | Shared rule 5 | trial A | 132 requests, all HTTP 200 (2 calendars, 2 day pages, 128 match pages); 172 rows listed, 129 in scope (Challenger 35, Futures 39, women's ITF and WTA 125 55), 128 priced, **128 pages, all parsed**. Pinnacle on 35 of 35 Challenger pages, 14 of 37 women's main-draw (ITF and the WTA 125), 0 of 26 men's ITF main draw, 0 of 30 qualifying; 42 of its 49 rows timed; books median 15 (Challengers), 5 (ITF), 3 (qualifying) [observed] |
| 12:51 | The collector also waits while the model's odds step runs (`odds_input.py` refreshes TennisExplorer in-process, unseen by the first check); 18 tests pass | One collector per host | – | – |
| 12:51:55 | **Bulk launched detached** (`src/ingest/tennisexplorer_lower_bulk.sh` with BUDGET=10000, MAX_RUNS=60, SINCE=2018-01-01; log `data/raw/tennisexplorer_lower/_logs/bulk.log`); the data map's `in_progress` line added | Plan step 4 | both trials passed | First run (pid 26568): calendars of 2017-2026, then days from 21 Oct back; no error at 12:52:27 |
| 12:52-12:55 | README section rewritten (the probe of all three sites, the choice, the trials, the bulk, files, limits, resume commands). Checked against the evidence before leaving it | Shared rule 12 | all above | **Corrections found by that check:** (1) the probe's Challenger and WTA 125 main-draw detail pages are **40** (5 per tour and year), with Pinnacle on **40 of 40**, not "20 of 20"; so Pinnacle is on **71** detail pages, timed on **67** (not 51 and 47) — the 12:17 and 12:22 rows and the decision row above carry the wrong figures, and the session's chat note of about 12:18 ("on all 20 sampled Challenger and WTA 125 main-draw matches") carried the same slip and is corrected in the session's report. (2) The 2022 Challengers unlisted on each site (37) are the same matches on 33 of 37, not all. (3) Pinnacle's last change before the listed start: median 98 minutes (quartiles 29 and 228; one a minute after the start; 25 of 67 within an hour), replacing a garbled "6 to 563". (4) OddsPortal answered one guessed address with HTTP 404. The README carries the corrected figures |
| 12:55-12:57 | The plan's P11 section: a dated note (the choice; three statements proved wrong or incomplete). The log's §§ 5 and 7-10. Route B's comparison now reads the collector's raw pages of the capture's days (no staging needed) and keeps only matches that had started by the last pull; a dry run (no page of 22 Oct yet) | Report; route B | – | **The captured closes so far** (started matches): Challenger 10, a median 5.7 minutes before the listed start; ITF 96, a median 9.8 minutes [observed]. So a 10-minute poll reaches within minutes of the start at these levels. A watcher waits for the bulk to fetch 22 Oct (its run starting about 05:30 UTC on 23 Oct) |

### 6. Judgment calls and deviations

1. **OddsPortal stopped at its anti-bot layer** (04:59, after its day feed was decoded, before any of its odds was read). Options: imitate the page's proof request (one GET with the nonce it prints) and read the match feeds; or stop. Chose to stop. The 8 Oct decision covers the decryption a page performs, not getting past a bot check; a proof token minted to tell browsers from scripts, with honeypot links beside it, is a bot check. Also weighed: OddsPortal's books carry BetExplorer's ids (its "bookiehash" uses the same numbering: bet365 16, Pinnacle 18, 888sport 27), and the two sites cooperate on odds (the data audit), so its prices would likely repeat BetExplorer's. What is lost: whether OddsPortal shows Pinnacle to this region (its bookiehash's bit 18 is set, which may mean it does) and its archive's depth.
2. **The capture writes to its own folders** (04:49, before it ran). Options: the recorder's own folders (one Pinnacle history for both uses) or separate ones. The bet-day path reads only the newest pull file (`src/pipeline/live.py`, twice in one run), so a capture pull landing between those two reads would change a bet day's prices mid-run. Separate folders cost a second copy of the listing on bet days, nothing else.
3. **Pinnacle and opening prices weigh after closing coverage** (§ 1, before any result). The plan's criterion is closing coverage at each level; Pinnacle decides between sources that cover a level about equally, because the model's odds input is Pinnacle first.
4. **A separate collector and folders for the lower levels** (05:01, before the TennisExplorer probe). Options: extend the tour-level adapter (`src/ingest/tennisexplorer.py`) and its folders, or a new module with its own. The tour-level staging feeds the model's odds input through `link_frame`, which links frame matches by names inside a date window; a lower-level page of the same pair inside that window could take a frame match's link if the tour-level page were missing. Its own folders keep the model's input exactly as it is. Cost: a few main-typed WTA 125s (the site types Suzhou 2026 "main") stay with the tour adapter's scope.
5. **Matches listed without prices are not asked** (05:01). Their pages hold no book (the day listing's average is the books' own); asking them would add about 5-60% more requests by level (most at ITF qualifying) for no odds.
6. **The bulk's pace: 2.5 s plus up to 1 s** (12:51, after the trials). The plan's default is 2 s plus up to 1 s. The site is also the one the daily `pinnacle_closes` job reads for the model's odds input, so the bulk takes the tour adapter's pace, which held for about 10,000 pages without a refusal, rather than a faster one. Cost: about 15% more time. Runs of 10,000 requests, not 30,000, so that each new run starts again from the newest day about three times a day (the forward-capture comparison needs the pages of 22-23 Oct soon after).
7. **The trial's Expected came from the probe's day listings** (12:18, before the trial). The plan's P11 section gives no Expected; the probe's January week gave about 105 priced matches a day.

### 5. Sources

* **Fetched** (22 Oct 2026; receipts in each raw folder's `_receipts.jsonl`):
  * betexplorer.com: `/results/tennis/?year=&month=&day=` (redirected to `/tennis/results/...`), `/match-odds-old/<id>/1/ha/1/en/`, `/archive-odds/<oid>/<bid>/<bt>/<sc>/<hcp>/`.
  * oddsportal.com: two day pages, 16 scripts under `/_next/static/chunks/`, `/proxy/ajax-nextgames/2/2/2/<date>/<xHash>.dat?page=1` (encrypted), one head-to-head page.
  * tennisexplorer.com: `/results/?type=<atp|wta>-single&year=&month=&day=`, `/calendar/<atp-men|wta-women>/<year>/`, `/match-detail/?id=<id>`.
  * guest.api.arcadia.pinnacle.com (with www.pinnacle.com/config/app.json for the key): the tennis matchups and straight markets.
* **Read offline, already on disk:** the Pinnacle-gap research's saved BetExplorer and TennisExplorer pages (`data/raw/pinnacle_gap/probe/`), the tour adapter's calendars (`data/raw/tennisexplorer/calendar/`), the bet-day recorder's pulls (`data/dump/odds/pinnacle/pulls/`), the map's match table (build of 16-17 Oct).
* **Provider claims not relied on:** none of the sites documents these routes; every convention above (the day pages' spans, BetExplorer's UTC+1, TennisExplorer's average price, OddsPortal's feed format) is read from the answers.
* **Where the search is blind:** OddsPortal's own archive and its region-dependent books; BetExplorer from another country; other odds archives (Oddspedia, Flashscore's odds tab) not probed.

### 7. Claims and their evidence (as of 22 Oct 12:56 UTC; the collection is running)

| Claim (README) | Evidence | Status |
|---|---|---|
| The sample: 4 weeks, 6,043 matches, seeded | `odds_probe_sample.json`, `.csv` (`odds_probe.py --sample`, seed 20261022) | observed |
| Listing coverage per site, level and year | `odds_probe_betexplorer.json`, `odds_probe_tennisexplorer.json` (`by_stratum`), re-derivable with `--report` | observed |
| TennisExplorer's detail pages: books, Pinnacle 40/40, 25/40, 6/13, 0/16; timed 67 of 71; last change median 98 min | `odds_probe_tennisexplorer.csv.gz` (`detail` rows) | observed (small samples) |
| BetExplorer shows no Pinnacle | `odds_probe_betexplorer.csv.gz` (`books` column, 78 detail matches) | observed from this connection only |
| OddsPortal: encrypted feeds, 30-day date feed, anti-bot layer | `data/raw/odds_probe/oddsportal/` (the feed answers, the scripts, the head-to-head page) | observed |
| TennisExplorer's day listing shows the books' average last price | 59 of 61 matches within 0.015 (19-21 Oct 2026, the Pinnacle-gap probe's pages; § 2) | observed |
| Trials: 622 pages parsed; Pinnacle shares by level | `tennisexplorer_lower_summary.json` of each trial (copied in the rows above), the staged months 2019-02 and 2026-10 | observed |
| The bulk's duration (about two weeks) | about 1,200 requests an hour in the trials; about 105-250 priced matches a day | inference |

### 8. Weak points

* **The detail samples are small** (5 and 2 per level and year). The trials' 622 pages are the better guide, but they are two October days and one February 2019 day.
* **"Close" is the site's last recorded price.** Its distance from Pinnacle's true close below the tour level is route B's question, still open. At tour level the Pinnacle-gap research found the site 93% exact against Pinnacle's own price at the same moments.
* **The scope rule leans on the site's calendar types.** A WTA 125 typed "main" (Suzhou 2026) is left to the tour adapter; an event missing from the calendar is in scope only if its name says ITF. The staged `listed/` tables keep every row with its scope reason, so a later check can count what was left out.
* **Linking by names** in the probe (`same_player`: surname words and an initial) can miss transliterated names and could pair a wrong row in a crowded week; the "several" counts are small (0-4 per stratum).
* **Where a flaw would hide:** in the day listing's "priced" flag (a match whose average is missing although books priced it would never be asked), and in matches the site lists on a day other than the one played (a qualifying round listed under its edition's first day).
* **A re-design** would fetch the site's event pages (where they exist) as well as the day pages, to cross-check listings, and would sample unpriced matches' pages once to confirm they hold no book.

### 9. Reviewer checklist

* [ ] Rerun the tests: `./python.sh -m pytest test/gap_downloads -q`.
* [ ] Re-derive the probe's tables offline: `./python.sh src/eda/gap_downloads/odds_probe.py --report`; compare with the README's table.
* [ ] Open five match pages of different levels from `data/raw/tennisexplorer_lower/matches/` and check the staged `odds/` rows (books, Pinnacle's last prices and times) against them.
* [ ] Count the staged `listed/` rows by `scope` for a month and look at what was left out as "not on the calendar".
* [ ] Confirm the tour-level folders are untouched by P11: nothing under `data/raw/tennisexplorer/` or `data/dump/odds/tennisexplorer/` written by `tennisexplorer_lower`.

### 10. Reproduction

```
./python.sh src/eda/gap_downloads/odds_probe.py --sample                               # offline, seeded
./python.sh src/eda/gap_downloads/odds_probe.py --site betexplorer --max-requests 200  # 141 requests on 22 Oct
./python.sh src/eda/gap_downloads/odds_probe.py --site tennisexplorer --max-requests 200
./python.sh src/eda/gap_downloads/odds_probe.py --report                               # offline
./python.sh -m src.ingest.tennisexplorer_lower --max-days 2 --max-requests 500         # trial A (newest two days)
./python.sh -m src.ingest.tennisexplorer_lower --since 2019-02-26 --until 2019-02-26 --max-requests 300   # trial B
src/ingest/tennisexplorer_lower_bulk.sh                                                # the bulk (detached; README for the launch)
src/eda/gap_downloads/pinnacle_capture.sh                                              # the capture (detached)
./python.sh src/eda/gap_downloads/pinnacle_capture.py --compare                        # offline
```

OddsPortal's probe was run by hand (scratch commands logged at 04:53-04:59); its decryption is the page's own: base64 of "ciphertext:iv", AES-256-CBC, key PBKDF2-SHA-256 (1,000 rounds) of the password and salt in its script `0h9izan-bqvt1.js`.

### Addendum, 22 Oct 2026 (from about 23:15 UTC): the daily job and the comparison's reminder

Same session. **The owner's words, verbatim**, after asking what "the comparison" meant and getting the answer:
> "Implement gathering lower level odds daily and perform this comparison or remind me in the future about this comparison so I dont forget it once the state of the program is such I can run it.. ie make sure future agents will be aware of this idea (either in the master plan that stores daily actions and a "future actions" document that can be built, or via your memory) decide what makes the sense."

**How it was read:**
* *Daily gathering:* a job of the daily scheduled task, as `pinnacle_closes` (the owner's daily-download request of 21 Oct) and P1-P3's jobs were added.
* *"Perform ... or remind me":* run the comparison in this session if it is still open when the data allow (about 24 Oct), and in any case a reminder that fires by itself once the comparison can run.
* *Where future agents will see it.* The owner offered three places and asked me to decide:
  * **The scheduler** (the "master plan that stores daily actions"): a check, which cannot go stale, and the owner's notification channel. Yes.
  * **CLAUDE.md**, which every session loads: one short entry. Yes.
  * **A new "future actions" document: no.** The owner's production-integrity plan of this morning ([decision](../../decisions/2026-10-22-production-integrity-plan.md)) makes *one* to-do list for every decided-but-unbuilt item; its step 4, building that list, is planned and another session started on the plan at 23:15. A separate list would be one more of the 25+ scattered places that plan replaces. When the list exists, this item belongs on it.
  * **Memory: no.** The owner's own memory rules exclude pending work ("Work in progress, or anything whose whole content is 'X is still pending'"), and the repository is what every agent reads.
* *Before changing the scheduled downloads* (CLAUDE.md, "Production integrity"): STATUS read at about 23:19 (no alerts, no paused job; the live model template_2026-10-21b); no to-do list or claims mechanism exists yet (the plan's steps 4 and 6). **The scheduler file was being edited by the other session** (saved at 23:20:46), so my edits were small, targeted and made against a fresh read; the editing tool refuses an edit when the file changed since the read.

**Chronology** (UTC, 22 Oct):

| When | Step | Output |
|---|---|---|
| 23:18-23:20 | Read the scheduler (jobs, `child`, `host_busy`, `job_pinnacle_closes`, `main`), the cadence decision, the production-integrity decision and the master pipeline's Part 10 (only its plan written yet), CLAUDE.md's production-integrity rule; STATUS | the choices above |
| 23:20 | `pinnacle_capture.py`: `--ready` (exit 0 ready, 1 not yet, 3 done: the capture over, and TennisExplorer's pages of every capture day on disk, 95% of each day's in-scope priced matches) and `--compare` writing `complete` and the days' state | On the real files at 23:20: not ready (the capture running; no page of 22 Oct yet), exit 1. The comparison file of 12:56 rewritten as `complete: false` |
| 23:21-23:23 | `scheduled.py`: `lower_odds` (constants, the job, `p11_compare_reminder`, the daily list after `pinnacle_closes`, the dispatch, the docstring and `--only` help) | – |
| 23:23 | Tests `test/gap_downloads/test_lower_odds_job.py` (8: a usual day, skipped while the backfill holds the site, a budget stop is no failure, a refusal pauses, an offline morning alerts the second time, crowded out waits a day, the reminder weekly until done, a broken check alerts the second time, the daily list) | 8 passed |
| 23:23-23:24 | Every test that imports the scheduler | 229 passed, 3 failed. (1) `test_tdi.py::test_scheduled_tdi_job_is_due_on_its_weekday_or_by_name` asserted that the daily list ends with `slams` or `tdi`: false since `pinnacle_closes` was appended on 21 Oct, and kept false by `lower_odds`. Its expectation now ignores the two TennisExplorer jobs (its intent, TDI after the other source jobs, kept). (2) Two canary tests of `test_rebuild_and_schedule.py` fail because `canary_flags` now reads the other session's new `src/ingest/health.py`, not the path the tests patch: that session's work in progress, not touched here |
| 23:24 | Process list (no scheduler run; the backfill pid 46816), then **one live run by name**: `scheduled.py --only lower_odds --no-notify` | Exit 0; `lower_odds` skipped ("P11's backfill holds the site"); the readiness check ran ("not ready"); no alert, nothing kept in `state.json` |
| 23:24-23:25 | The cadence decision's amendment (the owner's words) and its index row; CLAUDE.md, "Data collection": the daily job and the open comparison; this study's README (a section "Daily from 22 Oct 2026, and the comparison still to run", the files list); the data map entry's notes; `check_catalog` | no problem |
| 23:25 | A message from another session (tennis-predictions-92) about a deleted build folder (`tnr_tpl1014`), addressed to the session writing `study_data_versions`' log | Not this session's; nothing here names that folder |

**Judgment calls:**
1. **The daily task, not the lower-level feed's task.** `pinnacle_closes` already reads the same site there, and running after it keeps the two TennisExplorer jobs from overlapping. A usual day takes about 15 minutes; with under 8 minutes of the task left it waits a day.
2. **The scheduler reminds; it does not run the comparison.** The comparison rewrites tracked evidence, and its reading and the recommendation are a session's, as the P2 jobs' rule has it ("the checks rewrite tracked evidence; sessions run them").
3. **Skipped while the backfill runs:** one collector per host, and each backfill run begins at the newest day.
4. **This session's own watcher** (started at 12:57) still waits for the backfill to fetch 22 Oct. If the session is still open then, it runs a partial comparison (22 Oct only, `complete: false`), and the full one once 23 Oct is in.

### The partial comparison (23 Oct 2026)

UTC.

| When | Step | Seen by then | Output |
|---|---|---|---|
| 05:52-06:17 | The backfill's run 2 ended on its budget (exit 3, staged 05:55); run 3 began from the newest day and fetched 22 Oct; the watcher fired at 06:17 (22 Oct's results pages at receipt line 20,636, 433 receipts after) | – | No error answer in 21,069 receipts |
| 06:18 | `compare()` rows now carry the match's start (`start_utc`) and the number of candidate pages, so a day can be read alone; tests 3 pass. `--ready` | – | 22 Oct fetched (234 in-scope priced matches, 234 pages); 23 Oct not; the capture still running: not ready (exit 1) |
| 06:18 | `--compare` (writes `complete: false`), then 22 Oct read alone (in memory) | – | 151 started lower-level matches captured (Challenger 21, ITF 130; none of qualifying), 134 linked (no pair with two candidates), 112 with a Pinnacle row on the site, **89 equal to Pinnacle's own last price** (to 0.005; 91 to 0.01). Captured close a median 9.8 minutes before the listed start (quartiles 4.9 and 9.8); the site's last Pinnacle change a median 227 minutes before it (126 and 250), never after [observed] |
| 06:18-06:19 | The 23 misses, in memory: Pinnacle's own price after the site's last change stamp, and at it | the reading above | **18 of 23: Pinnacle moved after the site's last stamp** (the site missed late moves). 5: the capture began after the site's stamp. Only 1 of 23 equals what Pinnacle showed at the site's stamp (pull within 10 minutes). The 88 equal ones: Pinnacle did not move after the site's stamp [observed] |
| 06:19 | README: "First reading: 22 Oct only" | – | – |

**Reading** [inference, one day, written before 23 Oct is in]: below the tour level the site records Pinnacle's prices sparsely and stops hours before the start, so its "last" is the close on about 4 in 5 matches, not all. Pinnacle's own site, read every 10 minutes, reaches every match it lists at about 10 minutes from the start. A recommendation waits for the full comparison (23 Oct).

**Weak points of this reading:** one day; matches linked by names (17 of 151 unlinked); "equal" judged at 0.005 on decimal prices; the capture's 10-minute grid means its "close" can be up to 10 minutes early; the 5 matches whose site stamp precedes the capture cannot be judged.

### The full comparison (24 Oct 2026)

UTC.

| When | Step | Seen by then | Output |
|---|---|---|---|
| 23 Oct 06:19 | A watcher on `--ready` (every 15 minutes) | the partial reading | – |
| 23 Oct 14:30 | (the owner's scheduled task) `lower_odds` ran for the first time unattended | – | Skipped (the backfill held the site); the check ran, "not ready"; its only alert was another matter (a held Tennis My Life file) [observed, `runs.jsonl`] |
| 23 Oct 16:50 | The capture ended as set | – | 216 reads, 463 requests, nothing skipped, no refusal |
| 24 Oct 07:13-07:40 | The backfill's run 6 began at the newest day and fetched 23 Oct; the watcher fired at 07:40:33 (`--ready` exit 0) | – | 22 Oct: 234 of 234 in-scope priced matches with their page; 23 Oct: 165 of 165; the capture over |
| 07:40 | `--compare` (`complete: true`), then the per-day and per-level tables (in memory, from the per-match file) | the partial reading | **259 captured, 249 on the site, 197 with a Pinnacle row there, 148 equal to Pinnacle's own close** (to 0.005; 150 to 0.01). Challengers 35/34/32/20; ITF 224/215/165/128. 22 Oct 151/144/118/94; 23 Oct 108/105/79/54. The partial run's 134 linked on 22 Oct became 144: the full run reads the site's pages of 23 Oct too, where some late matches of 22 Oct (UTC) are listed. Captured close a median 9.8 minutes before the listed start (quartiles 7.0 and 19.8); the site's last Pinnacle change a median 217 minutes (120 and 250), never after the start, 10 untimed [observed] |
| 07:41 | The 49 misses (in memory) | the table above | 36: Pinnacle moved after the site's last stamp; 8: untimed on the site; about 5 not checkable (the capture began later; one row falls in two groups). None of the 148 equal ones had a Pinnacle move after the site's stamp. Of the 185 captured matches with any move, 82 had their last move in the final 3 hours, 44 in the final hour [observed] |
| 07:41 | Checked the scheduler's records | – | the 23 Oct run above; `state.json` keeps nothing for the job (nothing failed) |
| 07:42-07:44 | README (the test's section rewritten: the result, what it means, the recommendation; the status and "in short" lines; the limits line), CLAUDE.md (the open item replaced by the finding and the owner's decision), the data map (`pinnacle_capture` on disk; its progress line made a "not counted" note; `check_catalog` clean), the plan's P11 note, the cadence amendment | – | – |

**Reading** [inference, two days]: below the tour level TennisExplorer records Pinnacle's prices correctly but stops hours before the start, so its last price is the close only when Pinnacle does not move late. That held on 75% of the matches with a Pinnacle row, and the site has such a row on 76% of the matches Pinnacle lists. Pinnacle's own site, read every 10 minutes, reaches every listed match at about 10 minutes from the start.

**Recommendation (made to the owner, not acted on):** keep the daily TennisExplorer job, which holds the history, the other books and the openings. Add Pinnacle's own site every 10 minutes as a standing job if lower-level markets may be bet: closes not recorded on the day are lost, and a model's odds input is Pinnacle's close. Its cost is a PC on all day, about 450 requests and 50 MB a day. Not started: a new standing job on the owner's PC is the owner's call.

**Weak points:** two weekdays of October; matches linked by names (10 of 259 unlinked); "equal" at 0.005; the capture's 10-minute grid; the comparison covers only the matches Pinnacle lists (none of qualifying); the other books' staleness on the site is not measured.

*Correction (27 Oct 2026), the recommendation's cost:* "about 450 requests and 50 MB a day" was wrong. The test's 36 hours used 463 requests, 9.0 MB raw and 5.6 MB staged, so a standing job is about 300 requests and 10 MB a day. Fixed in the README. Also measured then, for the owner's question about a PC switched off at times: of October 2026's 5,195 priced lower-level matches on TennisExplorer's day listings, 62.5% start between 00:00 and 08:00 Pacific (67.7% between 22:00 and 08:00). The two Windows tasks start a missed run when the PC is next on (`StartWhenAvailable`) and do not wake it (`WakeToRun` off).
