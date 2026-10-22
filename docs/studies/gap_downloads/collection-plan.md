# Collection plan: the public tennis data not yet held

**Status: a plan, not a decision.** Written on 8 October 2026 from the [data map](../../../data/data_map.yaml) (its `universe:` and `gaps:` sections), the [gap-sources research](../../research/gap-sources/README.md), the research's [lane notes](../../../data/studies/gap_sources/research_notes/) and the adapters in `src/ingest/`. Collecting needs no further approval under the [8 October decision](../../decisions/2026-10-08-scraping-approved.md). The order and the pace are the owner's choice.

**How to use it.** Each work package below opens with a prompt to paste into a fresh Claude Code session in this repository. The prompt points back here. The package's section and the shared rules say where the data is, how to fetch it, and when the package is done. Packages on different sites can run side by side; packages on the same site run one after another.

## What is left

"Would add" is the data map's count of 8 Oct 2026 (its "Public, not collected yet" table). Sources overlap, so the rows do not sum. Gap sizes count the matches on the map's table of 8 Oct (`data/studies/data_map/matches.parquet`) that lack the gap's level of detail.

| Source | Would add (map) | Targets | Package |
|---|---|---|---|
| ITF live-data API (forward only) | Every ITF match of the last 14 days, with statistics and points | Lost after 14 days | **P1** |
| WTA API since the batches; WTA website records | 2,964 women's ITF results after early September | Late-2026 WTA editions | **P2** |
| TDI, Match Charting, Live Tennis API v1.0.2, Hawk-Eye 2019-21 | Catch-ups of sources already held | – | **P3** |
| TennisLive, ITF 2019-2026 | 299,493 with points (set-closing games missing), 271,620 with totals, 9,069 results | Men's ITF qualifying (no file lists it); ITF after June 2026 | **P4** (listings), **P8** (pages) |
| TennisLive, Challengers 2018-2026 and tour qualifying 2018-2021 | 41,664 and 4,034 with points | `challenger_points_2018_2021` 24,874; Challengers 2022-24 5,781; qualifying 2018-26 6,579; `wta_2018_points` 2,079 | **P5** |
| SofaScore, Challengers 2024 to June 2026, and tour level 2018-2026 | 15,914 and 849 with every point | `challenger_points_2025` 14,675; Challengers 2022-24 5,781; `challenger_points_2018_2021` 24,874; `atp_points_2018_2020` 2,685; `wta_2018_points` 2,079; tour residual 1,216; WTA 125 377 | **P6** |
| SofaScore, ITF 2018-2024 | 191,392 with every point, 201,723 with totals | ITF 2025-26 below point 55,416 (more once P4 lists June-October 2026); `itf_detail` 205,872 | **P7** |
| ATP Stats Centre files 2025-2026 | 10,833 with every point, its outcome and the serve speed | About 24,600 tour and Challenger match codes | **P9** |
| Tennis Abstract website-only charts | 2,061 women's matches with every shot | `women_shots` 17,810; also about 330 men's charts of 2025-26 | **P10** |
| Bookmaker odds below the 250s (not on the map) | Unmeasured | Challenger, WTA 125, ITF | **P11** (probe first) |
| ITF official statistics and points, 2025-26 (not on the map) | Unmeasured | ITF 2025-26 | **P12** (probe) |

## Order, sites and time

| | Package | Site (one session per site) | Requests | Time | Start |
|---|---|---|---:|---|---|
| P1 | ITF live-data API: the last 14 days, then daily | api.itf-production.sports-data.stadion.io | ~6,000, then ~450 a day | ~5 h, then ~20 min a day | **Today.** Each day waited loses a day of ITF data |
| P2 | WTA API catch-up; women's ITF results | api.wtatennis.com, kaggle.com | ~10,000 | ~8 h | Now |
| P3 | Catch-ups of held sources | results.tennisdata.com, GitHub, Zenodo | ~1,500 + ~1.3 GB | ~2 h | Now (TDI last ran on 29 Sep) |
| P4 | TennisLive: women and events; every event of 2018-26 listed | www.tennislive.net | ~19,000 | ~12 h | Now |
| P5 | TennisLive: Challengers 2018-24, qualifying, WTA 2018 | www.tennislive.net | ~38,000 | ~24 h | After P4 |
| P6 | SofaScore (Chrome): Challengers, tour level, WTA 2018 (points only for the last four gaps) | www.sofascore.com | ~72,000 | ~2.3 days (~1.1 faster) | Now |
| P7 | SofaScore (Chrome): ITF 2025-26, then 2018-24 | www.sofascore.com | ~590,000 | ~19 days (~9 faster) | After P4 and P6 |
| P8 | TennisLive: the ITF pages SofaScore left | www.tennislive.net | ~19,000 (+ qualifying, if P4's sample says so) | ~12 h (+3-6 days) | After P5 and P7 |
| P9 | ATP Stats Centre 2025-26, decrypted | itp-atp-sls.infosys-platforms.com | ~60,000-90,000 | 2-3 days | When the running 2021 backfill has ended (same host) |
| P10 | Tennis Abstract charts | www.tennisabstract.com, huggingface.co | ~2,500 | ~1 h | Now |
| P11 | Odds below the 250s: probe, then collect | betexplorer.com, tennisexplorer.com, oddsportal.com | Probe ≤ 500 | – | Optional |
| P12 | ITF official statistics 2025-26: probe | www.itftennis.com (Chrome), the Stadion API | Probe ≤ 150 | – | Optional; while P1's run is idle |
| P13 | Flashscore point feeds: ITF January 2025 to February 2026 (added 14 Oct 2026, UTC) | global.flashscore.ninja | ~40,800 | ~31 h | Now, beside P7 (another site) |

* **Pace.** The times assume the decision's practice: about 2 s between requests plus up to 1 s of jitter, which comes to ~1,300 requests an hour, or ~31,000 a day. TennisLive's adapter default (1.5 s + 1 s) is ~1,550 an hour.
* **SofaScore's faster option.** SofaScore's adapter default, 1.0 s + 0.6 s, ran 7,867 requests on 30 Sep without a challenge (~2,800 an hour). The "faster" times use it. Which pace P6 and P7 use is the owner's call; their sections name the flags.
* **Why ITF goes listings → SofaScore → TennisLive.** The map counts TennisLive's partial records (set-closing games missing) as "point", and they would hide those matches from SofaScore's complete records. So P4 lists results only, P7 fetches SofaScore's records, and P8 fetches TennisLive pages for what SofaScore lacks. This saves about 250,000 TennisLive requests.
* **Running now** (8 Oct 2026, 17:30 UTC):
  * the encrypted 2015-2021 Stats Centre backfill, `infosys_atp --years 2021` (PID 51772; P9's host);
  * the cold-storage backup upload, `backup.py upload` (PID 31092).
* **The PC.** Sleep stops every run; rerunning the same command resumes it. P6 and P7 also need the Chrome window open, and P7 runs for one to three weeks.

## Shared rules for every package

1. **Read first:** [CLAUDE.md](../../../CLAUDE.md), the [8 October decision](../../decisions/2026-10-08-scraping-approved.md), these rules and the package's section.
2. **Collect without stopping to ask.**
   * Stop and report only on a block: HTTP 429, a challenge page or an unexpected 403. The clients back off first.
   * Never log in, get past a paywall or solve a CAPTCHA.
   * A "verify you are human" box in a Chrome window the owner opened is the owner's to click. Log that it is showing, and wait.
3. **One collector per host.** Before starting, list the running Python processes (`Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Select-Object ProcessId, CommandLine`). Do not start a second collector on a host already in use.
4. **The project's clients and receipts.** Use `src/ingest/point_sources/common.py` (`Client`, `fetch`, receipts), `feeds.FeedClient` or `browser.BrowserClient`:
   * one request at a time, at the pace above, with a `--max-requests` budget on every run;
   * every answer saved as served (gzipped) under `data/raw/…/<source>/`, with `_receipts.jsonl` (URL, time, status, bytes, SHA-256);
   * nothing fetched twice; a 404 recorded once as absent;
   * every time field a source sends kept (start, scheduled or actual, finish, court).
5. **Trial, then bulk.** First run a few editions (`--limit`, a small budget). Check the parse and the counts against the section's "Expected". If the trial reaches less than half of it, stop and report instead of running the bulk.
6. **Long runs** go in the background, logging to `_logs/` beside the raw files, and resume when the same command is rerun. Before the session ends, write the exact resume command into the package's report.
7. **Staging** goes under `data/dump/<branch>/<source>/`: Parquet, every column a string, with provenance columns (source file, SHA-256, retrieval time). `--stage-only` rebuilds from raw with no HTTP.
8. **The data map.**
   * When a download starts, set its entry's `status: downloading` and add a line under `in_progress:` in [data_map.yaml](../../../data/data_map.yaml). A new dataset gets its own entry (copy a neighbour's fields).
   * When it ends, set `status: on_disk`, update the `universe:` row, then rebuild: `./python.sh src/eda/data_map/build.py`.
   * A new source needs a loader in `src/eda/data_map/measure.py` (pattern: `load_sofascore_editions`), or the map will not count it.
   * Other sessions edit these files too. Re-read just before editing, change only your own lines with targeted edits (never rewrite the file), and never run two map builds at once.
9. **Evidence stays small.** Tracked files under `data/studies/` should stay under ~20 MB. Write big per-match tables gzipped (`.csv.gz`) and make their readers accept that.
10. **Timing.** When WTA API, SofaScore or TDI data adds matches or days, run `./python.sh src/eda/match_timing/refresh.py --sources <wta_api|sofascore|tdi>` once at the end. It rewrites `data/studies/match_timing/` (the timeline and the IOS inputs), so never run it while another refresh or a Stage 0 rebuild (`src/eda/data_continuity/rebuild_stage0.py`) is running; check the processes first. The new sources (TennisLive events, the ITF API, the 2025-26 Infosys files, Tennis Abstract) are not wired into the leak-proof clock. Say so in the report; wiring them is separate work.
11. **Tests:** offline tests for every parser and selection rule go under `test/<study>/`, and `./python.sh -m pytest test/<study> -q` passes.
12. **Report** in the study README that the package names, labelled observed or inference: requests, hours, blocks, what was fetched against "Expected", the link check and the limits. Evidence (run summaries, per-match tables) goes in `data/studies/<study>/`.
13. **Unchanged rules:** `./python.sh` only; no git command that changes state; delete nothing, temporary files included. A new raw folder is the only copy until the next `backup.py` run.

---

## P1. ITF live-data API: the last 14 days now, then every day

```text
Do work package P1 of docs/studies/gap_downloads/collection-plan.md: build a collector for the ITF's live-data API, capture every ITF World Tennis Tour match it still serves (the last 14 days) with its statistics and point-by-point, and make it run daily. Follow the plan's shared rules. This is time-critical: the API refuses dates older than 14 days.
```

**Where.** `https://api.itf-production.sports-data.stadion.io/` is the API behind the ITF's "World Tennis Tour Live" pages (its SDK: `https://widgets.itf-production.sports-data.stadion.io/itf-widget-sdk.umd.js`). It takes no credentials and has no robots.txt, and it showed no challenge in 138 requests on 29 Sep ([lane C](../../../data/studies/gap_sources/research_notes/C_itf_listings.md#the-itf-live-data-api-observed)).

| Endpoint | What it gives |
|---|---|
| `custom/wttCompleteMatchList/<YYYY-MM-DD>` | Every World Tennis Tour match of that day, singles and doubles, main draw and qualifying: the event (name, ITF key `tennisId`, grade, dates, surface, country), draw, round, status, `winnerSideId`, set scores, duration and the match id. **HTTP 422 for a date more than 14 days back** |
| `custom/widgetMatchStats/<match id>` | Per side, per set and for the match: 34 statistic types (40 at higher grades), including aces, double faults, serve points, first-serve percentage, first- and second-serve points won, and break points. A 212-byte body means none |
| `custom/pointByPoint/<match id>` | Every point: server, outcome (`ACE`, `DOUBLE_FAULT`, `POINT` …) and the game score after it. A 96-byte body means none |

Only the day list is date-limited. The two per-match endpoints also answered for 2025 match ids.

**How.**
1. Build `src/ingest/point_sources/itf_live.py` on `common.Client`, starting from the research code: `src/eda/gap_sources/itf_http.py` (the client) and `itf_site.py` (`fetch-live`, `fetch-detail`, `fetch-stats`, `flatten_day`). Raw files go under `data/raw/point_sources/itf_live/`:
   * `day/<date>.json.gz`, fetched again on each run until the day is 3 days old and every match on it is final;
   * `match/<id>/stats.json.gz` and `match/<id>/points.json.gz`.
2. Each run: the day lists from 14 days ago to today, then the statistics and points of every finished singles match not yet held. Doubles: the lists only.
3. Stage `data/dump/points/itf_live/`: `events`, `matches` (every row of every list, with its list date and capture time), `statistics` and `points`.
4. **Daily job.** Add it to `src/ingest/scheduled.py` (pattern `job_tml`: two failures in a row alert; a block stops the job and alerts). *The owner can strike this step*, but without it every day not run by hand is lost after 14 days. Record the job in `scheduled.py`'s docstring, and tell the owner that the [cadence decision](../../decisions/2026-10-06-download-cadence.md) needs a line.
5. **Map:**
   * a new entry `itf_live` (grain point; levels ITF and ITFQ; `how: api_scrape`);
   * a `measure.py` loader that may add matches the map lacks (it has almost no men's ITF results after early June);
   * the universe row `itf_live_api`.

**Expected** (research, weeks 38-39):
* every event of a week (23 of 23 against Wikipedia's lists);
* about 1,500 singles matches a week;
* statistics and points on every main-draw match sampled (32 of 32), and on about two-thirds of qualifying matches (the final round always).

**Done when:**
* the first run holds every finished singles match of the 14-day window, with both documents asked for;
* a full week's events equal Wikipedia's "2026 ITF Men's / Women's World Tennis Tour (October–December)" lists;
* the tests pass;
* the daily job, if kept, has run once.

**Report:** a section "ITF live-data API" in [official_point_feeds](../official_point_feeds/README.md); evidence in `data/studies/official_point_feeds/`.

---

## P2. WTA API: the 2026 editions since the batches, and women's ITF results after early September

```text
Do work package P2 of docs/studies/gap_downloads/collection-plan.md: (a) bring the WTA API collection up to date for the 2026 editions played since the B1-B9 batches, and (b) collect the women's ITF and ITF-qualifying results the WTA website lists after early September 2026 (from a newer Kaggle version if one exists, else from the WTA API's player-matches endpoint). Follow the plan's shared rules.
```

**(a) The 2026 editions since the batches.** The batches finished on 2 Oct. `src/ingest/point_sources/wta.py` fetches an edition's match list again while the edition is not over, so rerunning the batches' endpoints over late-2026 editions adds what was played since.
1. Run once per endpoint, in the batches' order, each with its batch's absence limit (`BATCHES` in `wta.py`). The first:
   ```
   ./python.sh -m src.ingest.point_sources.wta --years 2026 --from-date 2026-09-01 --tiers 1000,500,250,125,finals --endpoints events --max-requests 3000 --stop-after-absences 150
   ```
2. Then the same command for `stats` (absence limit 1500), `advanced-stats` (400), `win-probability-momentum` (1000) and `point-by-point` (0). Trial each with `--limit 20` first.
3. The WTA Finals and the late WTA 125s are still to come: rerun all five after the season ends (late November).
4. Then run `refresh.py --sources wta_api`.

**(b) Women's ITF after early September.** The Kaggle copy on disk (version 29, 24 Sep 2026, in `data/raw/gap_sources/bwandowando/`) ends in early September.
1. Ask Kaggle for the current version of `bwandowando/womens-tennis-association-matches-1975-present` (`src/eda/gap_sources/wta_site_kaggle.py` fetched version 29). If a newer one exists, download it beside version 29, never over it.
2. For what it still lacks, use `GET https://api.wtatennis.com/tennis/players/<id>/matches/?year=2026`. One request on 29 Sep showed the same records.
   * Trial it on 5 players first, to learn its paging and fields.
   * Players: every `perspective_player_id` with a 2026 ITF row in the Kaggle file, then every opponent id the answers add, until no id is new. Expect ~3,000-4,000 requests.
3. Build this as a `--player-matches` mode of `wta.py`: the same client and receipts, raw files at `players/<id>/matches_<year>.json.gz`. Stage it the way the Kaggle file is read:
   * byes, walkovers and unplayed matches left out;
   * the second pseudo id (12% of ITF rows) de-duplicated on tournament, draw, round and player pair.
4. Map: refresh the `wta_site_records` entry (`measured_as: wta_site`).

**Expected:**
* (a) a point log for nearly every match of the late-2026 editions (the API had one for all but 18 of 33,480 matches in 2020-26);
* (b) about 3,000 women's ITF main-draw results after early September (the map's universe row), plus qualifying.

**Report:** (a) in [official_point_feeds](../official_point_feeds/README.md#wta-official-api); (b) a section in this study's [README](README.md).

**Since 14 Oct 2026 no rerun by hand is needed:** the scheduler's weekly jobs `wta_points` (Mondays, part (a)) and `wta_site` (Tuesdays, part (b)) keep both current, the WTA Finals and the season's last WTA 125s included (owner: "Set this up for this data to come in automatically with the other repeating data acquisition"; [cadence decision](../../decisions/2026-10-06-download-cadence.md)).

**Done 11-13 Oct 2026; four statements above proved wrong, to know before the post-season rerun** ([process log](process_log.md)):
* *(a) step 1:* `wta.py` asked a cached match list again only while the calendar called its edition unfinished, so lists cached before a final were never refreshed (seven 2026 editions). It now asks again a list fetched before its edition's end date plus two days, and a 404 answered before then.
* *(a) step 2:* a `--limit 20` trial asks for nothing new (the oldest selected matches are cached); trial with a small `--max-requests` instead.
* *(b) step 2:* `perspective_player_id` is the Kaggle copy's own label, a WTA id on only some rows; the players asked about are `player_1`.
* *(b) steps 2-3:* the endpoint is paged, 10 matches a page by default; the mode reads `pageSize=100` into `players/<id>/matches_<year>_<page>.json.gz`. The website also lists a week's ITF results a week or two late, so a rerun needs `--refresh-before` (and, to save requests, `--refresh-active-since`).

---

## P3. Catch-ups of sources already held

```text
Do work package P3 of docs/studies/gap_downloads/collection-plan.md: the four small catch-ups (TDI's forward capture, the Match Charting Project's latest commit, the Live Tennis API sample's corrected v1.0.2, and the Hawk-Eye copy's 2019-2021 tracking files). Follow the plan's shared rules.
```

1. **TDI.** The last forward run was on 29 Sep, and the listing keeps about 92 days.
   * Run `./python.sh -m src.ingest.point_sources.tdi --recent 14 --max-requests 1500`, then `refresh.py --sources tdi`.
   * From now on, run `--recent 10` once a week. Propose a Monday job in `scheduled.py`, as in P1.
2. **Match Charting Project.** The pinned commit is `1813a13` ("thru 18 sep 2026").
   * Run `./python.sh -m src.ingest.public_dump.match_charting --mcp-commit master` (the branch name, or the head commit's sha).
   * First check how the adapter stores a second commit: the first commit's files must stay. The Tennis My Life adapter's `superseded/` folder is the pattern.
   * Update the data map entry's commit and dates.
3. **Live Tennis API sample, v1.0.2** (Zenodo record 23018680, 28 Sep 2026).
   * It has the same rows with `scheduled_time_utc` corrected. The staged v1.0.0 is in Israel local time, 2-3 h ahead of UTC.
   * Add a `--record` option to `src/ingest/public_dump/live_tennis_api_zenodo.py`, download v1.0.2 beside v1.0.0, and re-stage from it.
4. **Hawk-Eye tracking, 2019-2021** (802 matches, 1.2 GB, not fetched yet).
   * Run `./python.sh -m src.ingest.public_dump.slam_ball_tracking --json-years 2019-2021`.
   * Check the range syntax in `--help` first.

**Report:** a short note in each owning study:
* [official_point_feeds](../official_point_feeds/README.md) for TDI;
* [public_data_dump](../public_data_dump/README.md) for Match Charting and the Live Tennis API;
* [ao_rg_points](../ao_rg_points/README.md) for Hawk-Eye.

---

## P4. TennisLive: women's players, whole events, and every event of 2018-2026 listed

```text
Do work package P4 of docs/studies/gap_downloads/collection-plan.md: extend the TennisLive adapter to women's players and to whole events, and list every ITF, Challenger / WTA 125 and tour or Slam event of 2018-2026 from TennisLive's results section, so that men's ITF qualifying and the ITF matches since June 2026 reach the map as results. Fetch match pages only as the section's samples. Follow the plan's shared rules.
```

**Where.** The site is www.tennislive.net, read through `src/ingest/point_sources/tennislive.py` (curl_cffi with Safari's fingerprint; no block in ~4,900 requests over two days). The exact calls are in the research probes:
* `src/eda/gap_sources/tennislive_probe.py` (both tours, slug search);
* `src/eda/gap_sources/tennislive_itf_after_june.py` (events);
* their notes: [lane D](../../../data/studies/gap_sources/research_notes/D_tennislive.md).

| Call | What it gives |
|---|---|
| `GET /atp/<slug>/`, `GET /wta/<slug>/` | A player page. Its `window.TENNISLIVE_RUNTIME` JSON holds the session token (`playerLiveRequestToken`), and the page sets the session cookie. Open every session with one page: a token from another session is refused (403) |
| `GET /api/player-matches?tour=<atp\|wta>&slug=<slug>&discipline=singles&year=<y>&surface=all&offset=<n>` | A season's matches, 60 a page, grouped by tournament with the tournament's URL (`/atp-men/<event>/`, `/wta-women/<event>/`). Headers: `X-TennisLive-Token`, `X-Requested-With: XMLHttpRequest` and same-origin `Sec-Fetch-*` |
| `GET /api/search?q=<name>` | A player's slug, when the hyphenated name answers 404 |
| `GET /api/tournament-section?tour=<atp\|wta>&slug=<event>&section=results` | The whole event by round (qualifying, main draw and doubles), with each match's score, winner and URL. One request lists an event |
| `GET /<atp\|wta>/match/<p1>-VS-<p2>/<event>/` | A match page: the score after each point, game by game (the set-closing game usually missing), the server, break-point markers and 8 match statistics |

The site has no calendar endpoint (its scripts name only these calls), so events are found through players.

**How.**
1. **Women.** Make the adapter tour-aware: the page path, the API's `tour=` and the raw paths. Also fix `load_tennislive` in `src/eda/data_map/measure.py`, which files every row as men's (`"tour": "M"`); take the tour from the match URL.
2. **Find the events.** Take the editions (tour, tournament, year, week) from the map's match table:
   * ITF 2018-2026, both tours (~11,400);
   * Challengers and WTA 125s, 2018-2026 (~3,500);
   * the tour-level events and Slams of 2018-2021, for their qualifying (~540).

   For each tour and year, pick players greedily: each pick's season listing should cover the most editions not yet found (a journeyman plays 25-30 events a year). Resolve slugs as the probe does: a slug already seen in a listing, then the hyphenated name, then `/api/search`. An edition counts as found when a listing group's name has its city and level and its matches fall in its week. At weekly venues (Monastir, Antalya, Sharm El Sheikh), also check the final's date: the probe once took the previous week's Monastir. Expect ~2,000-3,000 listing requests.
3. **List each edition** with one `tournament-section … section=results` request (~15,400).
4. **Two seeded samples of pages, not a bulk run:**
   * 200 main-draw pages from ITF events since 1 June 2026, to measure point coverage for P8;
   * 200 ITF qualifying pages over 2019-2026. The ITF's umpire devices record mainly the final qualifying round, so P8 fetches qualifying pages only if most of these carry points.
5. **Stage** into `data/dump/points/tennislive/`:
   * a new `events.parquet` (one row per listed edition);
   * a new `listed.parquet` (every match of every results section: round, draw, players, score, winner, URL);
   * the sampled pages join the existing `matches`, `games`, `points` and `statistics`.
6. **Map:**
   * the listings create the matches the map lacks, as the result files do: men's ITF qualifying of every year, and the ITF matches since June 2026 (men) and since early September (women);
   * add new data map entries for the listings and the pages;
   * after the rebuild, check the ITF 2026 and ITFQ cells.

**Expected:**
* every sampled event listed in full (11 of 11 after June in the research);
* men's ITF qualifying listed with results for every event (318 matches in 8 sampled events);
* points on most sampled main-draw pages (18 of 24 men's and 9 of 9 women's in the research), and statistics on all.

**Report:** a section "TennisLive by event" in this study's [README](README.md); evidence in `data/studies/gap_downloads/tennislive_*`.

---

## P5. TennisLive: Challengers 2018-2024, tour and Slam qualifying, WTA 2018

```text
Do work package P5 of docs/studies/gap_downloads/collection-plan.md: with TennisLive's event mode from P4, fetch the match pages of the map's gap matches in Challengers 2018-2024, tour and Slam qualifying 2018-2026, and WTA 2018. Follow the plan's shared rules.
```

1. **Targets** come from the map and are frozen at the first run, as `sofascore_editions.py` does (`data/studies/gap_downloads/tennislive_<gap>_matches.csv`). The gaps:
   * `challenger_points_2018_2021` (24,874);
   * `wta_2018_points` (2,079; TennisLive is the only source found for its qualifying);
   * two new gaps to add under `gaps:` in data_map.yaml (P6 adds the first too; add it only if it is not there yet):
     * `challenger_points_2022_2024`: `{tours: [M], levels: [CH, CHQ], years: [2022, 2023, 2024], below: point}` (5,781; the matches the Infosys copy holds without points);
     * `qualifying_points_2018_2026`: `{tours: [M, W], levels: [TQ, GSQ], years: [2018, … 2026], below: point}` (6,579).
2. **Link** each target to its event's listed match in P4's `listed.parquet`: names sharing a word, the same round and draw. Reuse the rules of `sofascore_editions.best_event`.
3. **Fetch** the pages newest first: ~38,000 pages (the gaps overlap in WTA 2018 qualifying), ~24 h at the adapter's 1.5 s + 1 s.
4. **Check each record.**
   * Record completeness per match with the rules of `src/eda/point_shot_sources/verify_scrape.py`: complete; only set-closing games missing; other shortfall.
   * Where an official box score exists, compare the statistics block with it. TennisLive swapped the two players in 2 of 36 sampled tour matches; flag swaps.

**Expected:**
* points on 95-99% of Challenger matches (the ten careers, in every period);
* points on all 32 sampled WTA 2018 matches;
* points on ~80% of tour qualifying (a thin sample);
* complete records rare, because set-closing games are missing.

**Report:** this study's [README](README.md).

---

## P6. SofaScore in Chrome: Challengers, tour level, WTA 2018

```text
Do work package P6 of docs/studies/gap_downloads/collection-plan.md: run the SofaScore by-edition adapter in browser mode over challenger_points_2025, wta125_points_2019_2026, tour_points_rest, challenger_points_2022_2024, atp_points_2018_2020, wta_2018_points and challenger_points_2018_2021, in that order (add the new gaps first), fetching points only (--skip statistics) for the last four. The Chrome window with the debugging port is open. Follow the plan's shared rules.
```

**Before (the owner).** SofaScore has refused the plain client since 29 Sep. Open Chrome with a blank profile and a debugging port, in PowerShell, and click the check if one shows:
```
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\sofascore-cdp" --no-first-run --no-default-browser-check https://www.sofascore.com/tennis
```
The adapter makes each request as a `fetch()` in that tab and reloads the tab when the hourly token expires. If a check wants a click, it says so in the log ([how it runs](README.md#running-it)).

**How.**
1. **New gaps** under `gaps:` in data_map.yaml:
   * `challenger_points_2022_2024` (as in P5; 5,781; add it only if P5 has not);
   * `wta125_points_2019_2026`: `{tours: [W], levels: [CH, CHQ], years: [2019, … 2026], below: point}` (377);
   * `tour_points_rest`: `{tours: [M, W], levels: [GS, FIN, T1000, T500, T250], years: [2019, … 2026], below: point}` (1,216). These are mostly WTA matches of January-March 2019, before the WTA's point log starts, plus scattered ATP matches of 2021-26.

   Qualifying is left to P5: SofaScore had none of 10 sampled WTA 2018 qualifying matches.
2. **For each gap, in the order of the prompt,** a trial, then the run. The runs resume, and nothing is asked twice across gaps:
   ```
   ./python.sh -m src.ingest.point_sources.sofascore_editions --gap challenger_points_2025 --browser --limit 3 --max-requests 60
   ./python.sh -m src.ingest.point_sources.sofascore_editions --gap challenger_points_2025 --browser --max-requests 40000 --min-interval 2.0 --jitter 1.0
   ```
   *Faster (the owner's call):* leave out `--min-interval 2.0 --jitter 1.0` to use the adapter's 1.0 s + 0.6 s.
3. **Points only for the last four gaps** (changed on 9 Oct 2026, while gap 3 ran): `challenger_points_2022_2024`, `atp_points_2018_2020`, `wta_2018_points` and `challenger_points_2018_2021` run with `--skip statistics`, for example:
   ```
   ./python.sh -m src.ingest.point_sources.sofascore_editions --gap challenger_points_2018_2021 --browser --skip statistics --max-requests 40000 --min-interval 2.0 --jitter 1.0
   ```
   * **Why.** Stage 0 already holds a box score for about 99% of these matches (Challengers 2018-21: 23,504 of 23,595; 2022-24: 5,135 of 5,190; [lower-level study](../lower_level_evidence/team/04_incoming.md)). The second request per match would mostly fetch it again, counted SofaScore's way (SofaScore counts first serves in and break points differently from the official box scores; [data continuity](../data_continuity/README.md), section 3.3). The points are the new data.
   * **Enough box scores already.** The first three gaps fetched both parts: about 16,000 SofaScore box scores of matches Stage 0 also holds, enough to calibrate SofaScore's counting.
   * **Given up:** a SofaScore box score for the few target matches with none in Stage 0 (91 Challenger matches of 2018-21, 55 of 2022-24, a few in the other two gaps). P5's TennisLive pages carry a statistics block for the Challenger ones.
   * **Saved:** about 34,000 requests, about 26-30 hours at 2 s, so P7 starts about a day sooner.
4. **After each gap:**
   * `./python.sh src/eda/gap_downloads/verify_links.py --gap <gap>` (the winner and the games of every set against the map's official result);
   * the map rebuild.
5. **At the end:** `refresh.py --sources sofascore`.

**Expected** (research; box scores from the first three gaps only):
* Challengers 2025-26: every point for 31 of 32, a box score for 32 of 32 (about 14,000 matches);
* Challengers 2022-24: 99% of the ten careers' 2024 matches;
* WTA 2018 main draws: 19 of 22 complete;
* ATP 2018-20 main draws: mostly (qualifying unmeasured);
* Challengers 2018-21: about 74% (the ten careers, 2019-21; 33% in 2012-18).

**Report:** a section per gap in this study's [README](README.md), like the ATP gap's.

---

## P7. SofaScore in Chrome: ITF 2025-2026, then ITF 2018-2024

```text
Do work package P7 of docs/studies/gap_downloads/collection-plan.md: run the SofaScore by-edition adapter in browser mode over ITF, first a new gap itf_points_2025_2026, then itf_detail (2018-2024), newest first, fetching both points and box scores (no --skip statistics). It is a multi-day run: if an earlier session started it, resume it. The Chrome window with the debugging port is open. Follow the plan's shared rules.
```

1. **Start after P4's map rebuild**, so that the ITF matches TennisLive listed since June 2026 are targets too. Then add the gap `itf_points_2025_2026`: `{tours: [M, W], levels: [ITF], years: [2025, 2026], below: point}`.
   * On 8 Oct it held 55,416 matches (men 24,234, women 31,182); the map's ITF results then ended on 2 Sep (men) and 7 Sep (women).
   * ITF qualifying: measure it in the trial (the qualifying events of the trial's editions). Add a separate qualifying gap only if most of those events carry points.
2. **Big gaps, small evidence.** `itf_detail` freezes 205,872 targets; at ~300 bytes a row, its per-match table would be ~60 MB.
   * Write the per-match and link-check tables of both ITF gaps gzipped (`.csv.gz`).
   * Extend their readers: `load_targets` in `sofascore_editions.py`, `verify_links.py`, and `sofascore_edition_uids` in `measure.py` (its glob is `sofascore_*_matches.csv`).
3. **Trial** on 3 editions of each gap, two of them at weekly venues (Monastir, Antalya). The research found one SofaScore season per ITF edition (2-3 listing pages, 40-90 singles events), within the adapter's cap of 25 pages; confirm it.
4. **Runs:**
   * `--gap itf_points_2025_2026` (~150,000 requests), then `--gap itf_detail` (~440,000);
   * each run with `--browser --max-requests 30000` (about a day at 2 s), rerun to continue;
   * the adapter goes newest edition first, so each stop leaves the recent seasons done.
5. **Keep the box scores: no `--skip statistics` here,** unlike P6's last four gaps.
   * **2018-24:** Stage 0 holds these ITF matches as results only (5 of 100,311 men's targets and 5 of 101,896 women's have a box score), so their box scores are the main new data, about 197,000 of them.
   * **2025-26:** 96% of the 49,180 Stage 0 matches it reaches already have Sackmann's box scores. Keep them anyway:
     * that overlap is the only place to measure SofaScore's ITF counting against official ITF box scores before its 2018-24 ones are trusted;
     * 13,862 of its targets are matches Stage 0 lacks (mostly after June 2026), whose box scores are new.
6. **After each gap:** `verify_links.py --gap <gap>`, staging, the map rebuild and `refresh.py --sources sofascore`.
7. **Flagged events last (changed on 13 Oct 2026, the owner's choice, while gap 1 ran).**
   * *Why:* SofaScore holds no ITF point records from January 2025 to February 2026. Its listings flag almost every ITF event of that window `coverage: -1`, and of 1,403 flagged events fetched, 8 had a point record ([the report](README.md#itf_points_2025_2026-the-download-running)).
   * *The order now:* the runs pass `--defer-uncovered`, which leaves those events unasked. The rest of `itf_points_2025_2026` runs first, then `itf_detail`, then one last run without the option for the deferred events, if the owner keeps it (about 80,000 requests).

**Expected:**
* box scores for ~98% and complete points for ~93% (84 sampled ITF matches of 2018-24, men and women alike);
* 2018 the weakest year (Hungary F1 listed 23 of its 31 singles matches);
* 2025-26 unmeasured, because the block stopped that count. If its trial links under 80% of targets, stop and report.

**Time:** at 2 s + 1 s, ~5 days for 2025-26 and ~14 for 2018-24; at the faster pace, ~2.5 and ~6.5.

**Report:** this study's [README](README.md).

---

## P8. TennisLive: the ITF pages SofaScore did not fill

```text
Do work package P8 of docs/studies/gap_downloads/collection-plan.md: after P7, fetch TennisLive's match pages for the ITF main-draw matches of 2019-2026 that are still below point on the rebuilt map, and fetch ITF qualifying pages if P4's sample says they carry points. Follow the plan's shared rules.
```

1. **Targets:** ITF main-draw singles of 2019-2026 still below point after P7's last rebuild. Expect ~7% of ~276,000, about 19,000. Link them to P4's listings as in P5.
   * TennisLive's women's ITF of 2018 is thin: Hammamet $15K 2018 has results but no match pages.
2. **Qualifying:** if at least half of P4's 200 qualifying pages carry points, fetch every ITF qualifying page of 2019-2026: ~96,000 women's plus the men's from P4's lists, which may be as many again (3-6 days). Otherwise keep the listings' results.

**Expected:** points on ~95% of pages (80 of 84 sampled ITF matches, with a median 93% of games), none complete.

**Report:** this study's [README](README.md).

---

## P9. ATP Stats Centre files 2025-2026, decrypted (tour level and Challengers)

```text
Do work package P9 of docs/studies/gap_downloads/collection-plan.md: collect the ATP Stats Centre's Infosys files of 2025-2026 for tour-level and Challenger singles (key statistics, MatchBeats, rally analysis, Court Vision), keep them as served, decrypt them at staging, and stage the points, serve speeds and outcomes. Start only when the 2015-2021 backfill (infosys_atp --years 2021) has finished, since it uses the same host. Follow the plan's shared rules.
```

**Where.** The host is `https://itp-atp-sls.infosys-platforms.com`. Send atptour.com's `Origin` and `Referer` with Chrome's TLS fingerprint, as `src/ingest/point_sources/infosys_atp.py` does.
* **Static files:**
  * `/static/prod/stats-plus/<year>/<event>/<MID>/keystats.json`;
  * `/static/prod/{match-beats,rally-analysis,court-vision}/<year>/<event>/<MID>/data.json`.
* **API routes,** for current-season files whose static copy answers AccessDenied:
  * `/prod/api/stats-plus/v1/keystats/year/<y>/eventId/<e>/matchId/<MID>`;
  * `/prod/api/match-beats/data/year/<y>/eventId/<e>/matchId/<MID>`.
* **Encryption.** Each file is an envelope `{lastModified, response, data: null}`. `response` is AES-128-CBC with a key derived from `lastModified`: `key_iv` and `decrypt` in `src/ingest/point_sources/infosys_slams.py`, pinned by tests.
* **Coverage.** In the 29 Sep probe, 16 of 20 sampled 2025-26 tour and Challenger matches had files, with all four routes at tour level ([probe](../../../data/studies/gap_sources/atp_statscentre_probe.csv)).

**How.**
1. **Plan.** Take the matches from ManTennisData (`data/raw/public_dump/mantennisdata/atp/matches_2025.csv` and `_2026.csv`; refresh it first with `--commit latest`).
   * Series `atp`, `1000` and `ch`: about 24,600 match codes with a stats link (MS001 is the final; QS codes are qualifying).
   * Reuse `infosys_atp.py`'s calibrate, discover and expand steps. Add `ch` to its series, and run with `--since 20250101 --until <today>`.
2. **A separate raw folder:** `data/raw/point_sources/infosys_atp_recent/`.
   * Never `infosys_atp/`. Its 2015-2021 files stay encrypted on the owner's instruction, and the guard in `src/eda/serve_speed_tabpfn/live/atp_daily.py` refuses any file there.
   * Give the new staging its own guard: years 2022 and later only, nothing under `infosys_atp/`.
3. **Stage** into `data/dump/points/infosys_atp_recent/`, following SirGenkii's tables (`data/dump/points/sirgenkii_infotennis/`) as the schema:
   * MatchBeats points: server, serve number, serve speed and first-serve fault speed, ending, stroke, rally counts, clock;
   * key statistics per set;
   * rally analysis;
   * Court Vision shots.
4. **Checks:**
   * the January-April 2025 matches against SirGenkii's decrypted copy, point for point (the AO 2025 check matched 3,368 of 3,368);
   * first-serve averages against ManTennisData.
5. **The daily collector** (`infosys_atp_daily/`) is off until enabled. If it is on, run outside its morning slot, and do not fetch again the 2026 key statistics it holds.
6. **Map:** a loader by ATP ids (pattern `load_sirgenkii`), a new entry `infosys_atp_recent`, and the universe row `atp_statscentre_2025`.

**Expected:** about 10,800 matches with every point (the map); about 4 requests a match where files exist; 60,000-90,000 requests in all.

**Report:** [serve_speed_acquisition](../serve_speed_acquisition/README.md).

**Started 16 Oct 2026** (the trial at 21:22 UTC, the bulk at 22:08 UTC, detached; [report, section 9](../serve_speed_acquisition/README.md#9-the-atps-own-files-of-20252026-tour-level-and-challengers-work-package-p9-from-16-oct-2026)):
* **Trial:** every point for 219 of 219 matches at five events, 3.9 requests a match, no refusal.
* **Three statements above proved incomplete:**
  * *"…and the serve speed":* speeds exist only where the event recorded them, about 4,200 of the 24,961 planned matches by ManTennisData's copy of the same key statistics (Masters about 95%, 250s and 500s 38-52%, Challengers under 8%).
  * *API routes "for current-season files":* the API also serves 2025 files whose static copy is missing (5 of the trial's matches), and builds its MatchBeats on request in a newer format (8 more point fields) where the static copy is older.
  * *Step 5:* the daily collector is on; its 82 completed 2026 key-statistics files are read from its folder, and the collector waits while the daily job or a prediction run's refresh uses the host.
* **Interrupted and resumed:** one dropped connection stopped the bulk on 17 Oct (83 events done); not a block. Resumed on 22 Oct with a retry after a reset, on ManTennisData's copy of 19 Oct (541 events, 25,277 codes); expected to end around 24 Oct.

---

## P10. Tennis Abstract website-only charts

```text
Do work package P10 of docs/studies/gap_downloads/collection-plan.md: collect the shot-by-shot charts that exist only on tennisabstract.com (women 2018-2026, men 2025-2026), from the Hugging Face copy ramizheman/TennisNLData where it has them and from the chart pages otherwise, and parse their point logs into shot rows. Follow the plan's shared rules.
```

1. **The index.** Fetch `https://www.tennisabstract.com/charting/meta.html` again (18,262 charts on 23 Sep, 18,284 on 29 Sep). Recompute the website-only list with `src/eda/granular_data_leads/mcp_website_gap.py`, against the latest Match Charting commit if P3 has run. On 23 Sep, 2,282 women's and 1,311 men's charts of 2018-2026 were website-only.
2. **Wanted:**
   * women's charts of every year, 2018-2026;
   * men's charts that the held handoff copy (`data/raw/public_dump/atp_pipeline_handoff/mcp/`, to 2024) lacks: about 330 of 2025-26.
3. **Hugging Face.** Pin `ramizheman/TennisNLData` to its head (`9a1fc64` on 29 Sep; 9,256 JSON files, one per chart, 1.38 GB).
   * Fetch only the wanted charts' files (1,467 of the women's gap charts are there).
   * Hash-check them as `src/ingest/public_dump/atp_pipeline_handoff.py` does.
4. **Pages** for the rest: `https://www.tennisabstract.com/charting/<chart id>.html` (about 594 women's and 330 men's; robots.txt allows `/charting/`). The point log is the page's `pointlog`: 142-170 rows a match, every shot in words ("1st serve wide; forehand return down the middle (very deep) …").
5. **Parse** to one row per shot (point, server, shot number, stroke, direction, depth, outcome), with Match Charting codes where the words map to them. Check the parse on charts that are both in the export and in the copy.
6. **Map:** shot grain for the `women_shots` gap and for men's 2025-26.

**Expected:** 2,061 women's gap matches at shot level (the map), and about 330 men's.

**Report:** this study's [README](README.md).

---

## P11. Bookmaker odds below the 250s (probe, then collect)

```text
Do work package P11 of docs/studies/gap_downloads/collection-plan.md: measure which public site holds bookmakers' opening and closing odds for Challenger, WTA 125 and ITF matches of 2018-2026, collect from the best one, and test a forward capture of closing lines. Follow the plan's shared rules.
```

**Why.** The current best model takes closing odds as an input, and the odds held stop at the 250s (tennis-data.co.uk, and OddsTrader's BetOnline lines). The [data audit](../../research/tennis-data-audit/market-history-and-odds.md) found no file with bookmaker prices for Challengers, WTA 125s or ITF. That tier carries about a fifth of Polymarket's tennis money.

**Candidates, all unmeasured:**
* **BetExplorer and Tennis Explorer** (Livesport sites): openings and moves per bookmaker, bet365 and Pinnacle among them ([BetOnline research](../../research/betonline-lines/README.md#3-other-routes-checked)). Tennis Explorer lists women's ITF with qualifying and odds, but no men's ITF in 2026 ([lane C](../../../data/studies/gap_sources/research_notes/C_itf_listings.md#c2-other-public-listings)).
* **OddsPortal:** an archive of closing odds by bookmaker; heavy on JavaScript.
* **Going forward:** Pinnacle's public guest API. This is an inherited claim from June 2026, unverified.

**How.**
1. **Probe** (≤ 500 requests) on a seeded sample of Challenger, WTA 125 and ITF matches from the map: 2019, 2022, 2025 and 2026, Polymarket's window included. For each match: is it listed; which bookmakers; is Pinnacle there; are opening and closing prices given, with their times.
2. **Collect** from the source with the best closing coverage at each level: an adapter, newest first, staged under `data/dump/odds/<source>/`. Prices stay out of git: the repository is public.

**Started 22 Oct 2026** (the probe 04:46-12:17 UTC, the bulk from 12:51 UTC; [report](README.md#bookmaker-odds-below-the-250s-work-package-p11)):
* **The probe** (346 requests over the three sites) chose **TennisExplorer at every level**. It lists as much as BetExplorer where both list, and alone has Pinnacle, opening prices with times, ITF of 2019 and ITF qualifying. The bulk (`src/ingest/tennisexplorer_lower.py`) goes newest first, waiting whenever the tour-level adapter uses the site.
* **Three statements above proved wrong or incomplete:**
  * *"Tennis Explorer lists ... no men's ITF in 2026":* only the event pages are missing. Its daily results list men's ITF under "Futures <year>", with prices and match pages, in 2019 as in 2026.
  * *BetExplorer "openings and moves per bookmaker, ... Pinnacle among them":* from this connection it shows no Pinnacle, and an opening costs one more request per book and side.
  * *OddsPortal "heavy on JavaScript":* also encrypted (the page's own decryption works) and, for a match's odds, behind an anti-bot layer that the probe did not pass.
* **"Pinnacle's public guest API ... unverified":** verified on 9 Oct, and recorded on bet days since 11 Oct (`src/ingest/pinnacle.py`). The forward-capture test reads it every 10 minutes for 36 hours from 22 Oct and compares each lower-level close with TennisExplorer's record after play.

---

## P12. ITF official statistics and points for 2025-2026 (probe)

```text
Do work package P12 of docs/studies/gap_downloads/collection-plan.md: find out whether itftennis.com's draws, read in a Chrome tab, give match ids that the ITF live-data API's per-match statistics and point-by-point accept for 2025-2026 matches, and size what that would add. A probe of at most 150 requests. Follow the plan's shared rules.
```

* **The question.** The Stadion per-match endpoints (P1) answer for 2025 match ids, but ids can be listed only for the last 14 days ([lane C](../../../data/studies/gap_sources/research_notes/C_itf_listings.md)). itftennis.com lists every draw, but it sits behind Imperva, which refused the plain client (403).
* **The probe.** Use a Chrome tab, as for SofaScore but with its own profile and port (`--remote-debugging-port=9223 --user-data-dir="$env:LOCALAPPDATA\itf-cdp"`), on `https://www.itftennis.com/`. For 5 events of 2025:
  1. call `/tennis/api/TournamentApi/GetEventFilters?tournamentKey=<key>`;
  2. then `GetDrawsheet?circuitCode=<MT|WT>&eventClassificationCode=<M|Q>&matchTypeCode=S&tournamentId=<id>&tourType=N&weekNumber=0`;
  3. look for a match id, and try it on `custom/widgetMatchStats/<id>` and `custom/pointByPoint/<id>`.

  Do not probe while P1's run is fetching (same API). If Imperva shows a CAPTCHA, stop.
* **If the ids work,** the ITF's own umpire-device statistics and points (aces and double faults per point) would reach 2025-26, perhaps earlier. Compare their coverage with SofaScore's on the same matches, and propose a package before P7 spends days on 2025-26.
* **Result (13 Oct 2026, asked for P7's hole).** In the Chrome tab, the calendar and event filters answered, but `GetDrawsheet` got HTTP 403 three times, and the probe stopped. The Stadion API exposes no draw, round or event listing, and its court listing answered 404 for a 2025 event ([report](README.md#itf_points_2025_2026-the-download-running)).

---

## P13. Flashscore point feeds: ITF January 2025 to February 2026

```text
Do work package P13 of docs/studies/gap_downloads/collection-plan.md: fetch Flashscore's point feeds for the ITF main-draw matches of January 2025 to February 2026 that SofaScore lacks, with the match ids of the Flashscore copy on disk, a seeded trial first. Follow the plan's shared rules.
```

* **Why (added on 14 Oct 2026, about 00:50 UTC, at the owner's word).** SofaScore holds no ITF point records for January 2025 to February 2026 (P7). Flashscore's live site serves complete records for many of those matches ([research](../../research/gap-sources/itf_2025_points.md)), and the handoff copy on disk gives their ids, so nothing needs listing.
* **How** (`src/ingest/point_sources/flashscore_points.py`):
  1. `--extract`, offline and once: the handoff copy's ITF singles records of the window.
  2. A trial of about 200 targets, seeded and spread over months and both tours: `--trial 200 --max-requests 250`.
  3. The bulk: `--max-requests 30000`, rerun until done (about 40,800 feeds; about 31 hours at 2 s plus up to 1 s).
  4. After: the link check against the official results, the map's loader and the map rebuild.
* **Expected** (the research's 8 checks): complete points for about 28,400 of the 42,876 targets, 93% to June 2025 and 45% from July. Nothing where the handoff copy has no match duration; the trial measures that rule.
* **Then P8** aims TennisLive at what Flashscore leaves.
* **Done (15 Oct 2026, 15:57 UTC).** A record for 27,535 of the 42,876 targets (27,174 complete), from 40,867 requests with no refusal. 24,887 of the 24,973 checkable records agree with the official result. The map's ITF 2025 matches with point data rose from 398 to 25,933 of 39,114 ([report](README.md#flashscore-point-feeds-itf-january-2025-to-february-2026-work-package-p13)).
* **Not in the timing clock:** like the other new sources, it is not wired into the leak-proof clock (rule 10).
* **Report:** this study's [README](README.md).

---

## Not in this plan

* **Paid feeds:** the Live Tennis API archive ($49 a month; it claims points for Challengers and men's ITF) and Sportradar. Nothing is bought.
* **Decrypting the 2015-2021 ATP files** on disk: the owner said "DO NOT DECRYPT IT".
* **Flashscore, beyond P13:** the 127 GB handoff copy on disk was read on 13 Oct 2026. It holds no points, and its match ids reach the ITF matches to April 2026. Fresh crawls for other gaps are allowed, but their point coverage is unmeasured.
* **Earlier AO and RG Infosys editions (2019-2024):** Sackmann's archive and the Hawk-Eye copy hold those Slams, and whether the hosts still serve them is unknown.
* **SofaScore again for tour-level matches the Kaggle copy (marcosjn2) holds:** it would only add ace and double-fault codes to the point winners.
* **ManTennisData 1999-2020:** it has no speeds, and its box scores are already held.
* **Already current:** Tennis My Life (the daily task), and Polymarket and the other odds (`src/ingest/refresh_odds.py`, current to 7 Oct).

## After the downloads

The map counts what is held, but the models read only Stage 0 and the leak-proof clock, and those know none of the new sources (TennisLive events, the ITF API, the 2025-26 Infosys files, Tennis Abstract). Linking them (`src/eda/match_timing/` and Stage 0), and checking each new cross-player feature with `src/eda/match_timing/probe.py`, is separate work.
