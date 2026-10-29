# Scheduled downloads: Tennis My Life every day, each Slam's official feed after the event

**Delegated by the owner on 6 October 2026, with conditions.**
* Asked "How often should TML be downloaded?", the owner answered: "What's the trade off? As much as possible as long as we are using the data actively, and it doesnt require too much distraction or manual entry or MASSIVE amounts of space".
* Asked "Should we download each Slam's official feed while it's played?", the owner answered: "Yes if that will get us real up to date info as we are betting".

Decided by Claude the same day under those conditions. Recorded on 6 October 2026.

## The trade-off, measured

* **What Tennis My Life (TML) publishes.** Its manifest of 6 Oct shows:
  * the 2026 season files change about once a week (last on 28 Sep, 29 Sep and 5 Oct);
  * its three in-progress files change several times a day (11:00, 13:05 and 14:00 UTC that day).

  Stage 0 reads both.
* **What a download costs.**
  * The adapter fetches only what changed. A kept version is the file it replaces: 0.2–1.3 MB for a season file, 4–24 KB for an in-progress file. The first run on 6 Oct kept 3.0 MB.
  * Daily: every season-file version, plus each day's state of the in-progress files. About 0.2–0.3 GB a year.
  * Hourly: adds only versions of the in-progress files within the day. A match stays in those files until its week ends and TML folds it into the season file, so a daily run already keeps every result. Nothing reads the extra versions.
* **Attention.** None, unless something needs a person. Then one Windows notification for any of:
  * a file held two runs in a row;
  * a download that failed two runs in a row (one failure is usually the PC waking up offline);
  * a new flag from the source watch (not when the PC was offline);
  * a finished Slam whose feed is missing.
* **"Using the data actively."** No bets or predictions are made yet: `data/betting_history/` and `predictions/` hold only their READMEs. New results reach the model's inputs when Stage 0 is rebuilt.

## Decision

1. **Download Tennis My Life every day.**
   * At 07:30 local time. A missed run happens when the PC is next on.
   * Windows Task Scheduler's task "Tennis predictions - daily data downloads" runs `src/ingest/scheduled.py` with the `tennis` environment's windowless Python. There is no window and no manual step.
   * Each run keeps what it replaces and holds a damaged file, under the [TML file-versions decision](2026-10-06-tml-file-versions.md).
2. **Not hourly, for now.** Once bets are placed, each prediction run downloads TML first. That gives the same freshness without polling.
3. **The source watch** (`canary.py`) runs every Monday from the same task. It notifies only on a flag it has not shown before.
4. **Each Slam's official feed is collected after the event:** the Australian Open, Wimbledon and the US Open.
   * Roland Garros has no official feed held.
   * **Updated 9 Oct 2026:** Roland Garros's records are held and collected too. The Infosys statistics and point files of both Slams, and rolandgarros.com's statistics, are now their box-score source, and the scheduler reminds for each ([decision](2026-10-09-ao-rg-box-scores-from-feeds.md)).
   * The task does not scrape the feeds unattended. Each adapter needs that year's settings: the Australian Open's event ids, and Wimbledon's and the US Open's hosts. The [official-feeds decision](2026-09-24-official-point-feeds.md) also asks for someone present to stop on a block.
   * Once an event has finished and its year is missing from `data/raw/point_sources/`, the task notifies once a week until a Claude session collects it.
   * About 15–20 MB per event.
5. **Collecting during the event waits for the betting pipeline.** Measured against the owner's condition:
   * **For.** The feed has each match's box score minutes after it ends, and correct. TML's men's Slam first serves have been wrong since about August 2025 ([Slam box-score decision](2026-10-06-slam-box-scores.md)). TML's in-progress file is the only other same-day source.
   * **Against.** No bet is placed, and nothing turns an in-progress result into a prediction yet. Collected during the event, the feed would not reach a bet.
   * So it is built with the betting pipeline, before the first Slam the project bets on. The adapters need a live mode that re-reads the draws on each run and fetches only finished matches. Today they are built for finished events and never ask for a document twice.
6. **Stage 0 rebuilds are not scheduled.** They rewrite tables that other studies read.
   * They run on request, coordinated with those studies, through `src/eda/data_continuity/rebuild_stage0.py`.
   * The first such rebuild was on 6 October; see the [Slam box-score decision](2026-10-06-slam-box-scores.md).

## Where it is implemented

* **`src/ingest/scheduled.py`:** the jobs, the alert rules and the notification.
  * Its log: `data/raw/_scheduled/runs.jsonl`, one line per run.
  * What the next run compares against: `state.json`.
  * Each job's output: `logs/`.
* **The task.**
  * Registered on 6 Oct 2026; it runs as the owner's account, only while logged on.
  * Test run on 6 Oct: exit 0, Tennis My Life downloaded, nothing held, no alert.
* **Tests:** `test/data_continuity/test_rebuild_and_schedule.py`.
  * A hold, or a failed download, alerts only the second time in a row.
  * An offline source watch stays silent.
  * A Slam reminder repeats weekly.
  * Canary flags are compared by their first word.


## Amendment, 8 October 2026: the daily serve-speed job

**The owner:** "id love to get the speed data daily :)" (recorded in the [speed-nudge amendment](2026-10-07-speed-nudge.md)). Decryption is allowed for the current season's ATP files ([scraping approval](2026-10-08-scraping-approved.md), "Clarified").

* **The job `speeds`** runs every day right after `tml`, because it plans from Tennis My Life's list of played matches. It runs `src/ingest/speed_daily.py --max-requests 200` and stops after 15 minutes.
* **Each run:**
  1. **On Mondays,** ManTennisData's weekly refresh, the no-decryption fallback.
  2. **Yesterday's ATP keystats,** current season only, through the `/prod/api/` routes. About 2 seconds plus jitter between requests, a receipt for every answer, and a stop on any block.
  3. **Decryption and staging.**
  4. **Linking** to the project's ids.
  5. **The live panel.**
  6. **Each ATP player's 28-day speed form,** in `data/studies/serve_speed_tabpfn/live/`.
* **Alerts.** A block alerts at once. Any other failure alerts the second time in a row.
* **The first live test** (8 Oct 2026, Shanghai's round of 128): 60 requests, 30 matches served, 30 empty draw slots (404), no block. The decrypted first-serve averages were 171–210 km/h, and 29 of the 30 matches linked.

## Amendment, 14 October 2026: the WTA API's point records and the WTA website's records, weekly

**The owner**, on the report of work package P2 (which listed "Rerun both parts after the season" as still to do): "Set this up for this data to come in automatically with the other repeating data acquisition".

* **Two jobs join the weekly task** ("Tennis predictions - lower-level feed", `src/ingest/scheduled.py --weekly`, daily at 12:00, 3 hours), so the post-season rerun needs no session:
  * **`wta_points`, Mondays:** the WTA API's five per-match documents of the tour, WTA 125 and Finals editions of the last five weeks, staged: the umpire's point log, box score, advanced statistics, win probability and point-by-point. About 800-1,800 requests, at most 100 minutes. Match lists and 404s answered before their edition ended are asked again, so the WTA Finals and the December WTA 125s settle by themselves.
  * **`wta_site`, Tuesdays:** the WTA website's records, staged for Wednesday's lower-level feed. Each player's list of the year is asked again when it shows a match in the last six weeks; one in six of the rest is asked each week; new opponents are followed. About 2,400 requests, at most 110 minutes. Until mid-February the previous year's lists are refreshed too, and a new year starts from the previous year's players.
* **Both** check that no other WTA collector is running, pause on a block and alert, and alert on a failure the second time in a row. They run on the next day the task runs when their day was missed, but never on Wednesday, the feed's day. A run cut short by its time limit stages what it fetched.
* **One new alert:** the newest ITF edition the website lists more than six weeks old (it lists a week's ITF results one or two weeks late), repeated every four weeks while it lasts.
* **Tested** on 14 Oct 2026:
  * `wta_points` ran live through the scheduler: exit 0, 174 requests, 11 minutes, staging included, no alert.
  * `wta_site`'s crawl had run in full hours earlier with the same flags; its job logic is tested offline (`test/data_continuity/test_rebuild_and_schedule.py`).
* **Reported in** [official_point_feeds](../studies/official_point_feeds/README.md#the-catch-up-of-11-and-13-october-2026-work-package-p2a) and [gap_downloads](../studies/gap_downloads/README.md#wta-website-records-after-early-september-work-package-p2b).

## Amendment, 21 October 2026: Pinnacle's closing prices, daily

**The owner:** "Include in our automatic download script downloading pinnacles closing value weekly (or daily if theres a daily script thats being executed)". The daily task is that script, so the job runs daily. The model's odds input trains on these prices from 1 Nov 2025 from the next retrain on ([Pinnacle-first amendment](2026-10-09-pinnacle-first-odds-input.md)).

* **The job `pinnacle_closes`** runs every day, last in the daily task, in the time the other jobs leave. It runs `src/ingest/tennisexplorer.py --calendar <year> --events --matches --since <today − 21 days> --max 400 --stage`.
* **Each run:**
  1. **This year's calendar** (last year's too in January).
  2. **The pages of the tour-level events under way or just finished** (team events, Challengers and exhibitions skipped).
  3. **Every finished main-draw match of the last 21 days not on disk:** Pinnacle's and every other listed book's last price, each change with its time, and the opening. Usually 20–80 pages, about 4 seconds apart, a receipt for each.
  4. **The site's tables restaged.**
* **Alerts.**
  * A refusal (an HTTP 4xx answer or a challenge page) pauses the job and alerts at once, then weekly while paused. A run asked for by name (`--only pinnacle_closes`) tries anyway and lifts the pause.
  * Any other failure (usually the PC offline) alerts the second time in a row.
  * With under 8 minutes of the task left it waits a day; the 21-day window catches it up.
* **Tested offline** (`test/pinnacle_gap/test_daily_job.py`). The adapter's first full pull (Jan 2025 – Oct 2026, about 10,000 pages) ran on 21–22 Oct 2026 with no block ([research](../research/pinnacle-gap/README.md)).

## Amendment, 22 October 2026: bookmakers' odds below the tour level, daily

**The owner** (after work package P11 chose TennisExplorer for Challenger, WTA 125 and ITF odds): "Implement gathering lower level odds daily and perform this comparison or remind me in the future about this comparison so I dont forget it once the state of the program is such I can run it". The comparison is P11's forward-capture test: Pinnacle's own last price before each lower-level match, recorded every 10 minutes for 36 hours from 22 Oct, against TennisExplorer's record of the same match after play ([report](../studies/gap_downloads/README.md#bookmaker-odds-below-the-250s-work-package-p11)).

* **The job `lower_odds`** runs every day, in the daily task, right after `pinnacle_closes` and in the time the other jobs leave. It runs `src/ingest/tennisexplorer_lower.py --since <today − 21 days> --max-requests 1500`.
  * Each day of the window not yet done: its two results pages, then the page of every Challenger, WTA 125 and ITF match (main draw and qualifying) they list with prices, then the changed months restaged.
  * Usually 100–300 pages, about 3 seconds apart, a receipt for each. Not a model input.
* **While P11's backfill runs** (it goes back to January 2018, about three weeks from 22 Oct), the job is skipped: the backfill asks the newest days itself.
* **Alerts** as for `pinnacle_closes`:
  * a refusal pauses the job and alerts at once, then weekly while paused; a run asked for by name (`--only lower_odds`) tries anyway and lifts the pause;
  * any other failure alerts the second time in a row;
  * with under 8 minutes of the task left it waits a day.
* **The reminder:** each day the job checks, offline, whether the comparison can be run on full data (`src/eda/gap_downloads/pinnacle_capture.py --ready`: the capture over, and TennisExplorer's pages of its days fetched). When it can, a notification says so, weekly, until a complete comparison is on disk. The job does not run the comparison itself: that rewrites tracked evidence, and its reading is a session's.
* **Tested offline** (`test/gap_downloads/test_lower_odds_job.py`). Run once by name on 22 Oct 2026 at 23:24 UTC: skipped, as the backfill held the site; the check said "not ready"; no alert.
* **The comparison ran on 24 Oct 2026** (complete), so the reminder is spent: the next check marks it done and stops. The scheduled task of 23 Oct had run the job as expected (skipped; "not ready"). Result in the [report](../studies/gap_downloads/README.md#forward-capture-of-closing-lines-the-test-done-24-oct-2026).

## Amendment, 27 October 2026: a reminder for the ATP Stats Centre files' 2026 top-up

**The owner** (after work package P9's report, [serve-speed acquisition, section 9](../studies/serve_speed_acquisition/README.md)): "Top up 2026 once after the season ends: yes. One run in early December adds every match since 18 October, at under an hour per week of play. [...] give me clear reminders come early december to do this until its done (in this tennis-predictions project pipeline only)".

* **The job `p9_topup`** runs every day in the daily task, before `slams`. It is a reminder only: no request, a few seconds (`src/ingest/scheduled.py`, `job_p9_topup`).
* **The due date** is the season's last finish in ManTennisData's calendar plus 8 days, so that its Sunday copy, read by the speeds job on Mondays, holds the last week: **Monday 28 Dec 2026** on the calendar of 26 Oct (the 2026 Challenger season ends on 20 Dec, later than "early December" assumed).
* **From 1 Dec 2026** (the owner's "early december") a notice gives that date, weekly. **From the due date** a reminder comes every day until the top-up is done: a full run of P9's plan that started on or after the due date (`data/studies/serve_speed_acquisition/infosys_atp_recent_full_runs.jsonl`, written by the collector) and was staged after it. Then the job marks it done and stops for good.
* **Where it shows:** a Windows notification (the task's first alert, with a count of the others) and the notebook's STATUS, which repeats the task's alerts of the last three days.
* **An agent's choice:** the due rule, the weekly notices before it and the daily reminders after it. The owner asked for "clear reminders ... until its done".
* **Tested offline** (`test/serve_speed_acquisition/test_p9_topup_reminder.py`): nothing before 1 Dec, weekly notices, daily reminders once a day, a run before the season's end not counted, and the end once a full run after the due date is staged. On the real calendar on 27 Oct: due Monday 28 Dec, nothing to say until 1 Dec.

## How to pause or remove it

```powershell
Disable-ScheduledTask -TaskName 'Tennis predictions - daily data downloads'                 # pause
Unregister-ScheduledTask -TaskName 'Tennis predictions - daily data downloads' -Confirm:$false   # remove
```

## Not decided (the owner's)

* **The monthly copy off this PC** ([data continuity study](../studies/data_continuity/README.md), section 4.2).
* **Hourly downloads once bets are placed**, if a prediction run's own download is not enough.
