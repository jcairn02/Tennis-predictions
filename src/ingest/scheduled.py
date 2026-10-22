"""Unattended downloads, run once a day by Windows Task Scheduler (docs/decisions/2026-10-06-download-cadence.md).

Jobs:
    tml      every day   Tennis My Life (public_dump/tennis_my_life.py --start-year 2000). Each changed file is
                         downloaded; the version it replaces is kept (superseded/) and a damaged one is held (held/).
    speeds   every day   The daily live serve-speed pipeline (src/ingest/speed_daily.py --max-requests 200), added 8 Oct
                         2026 on the owner's request ("id love to get the speed data daily"; decisions 2026-10-07-speed-nudge
                         amendment and 2026-10-08-scraping-approved, Clarified). Right after tml, whose played-match lists
                         it plans from: yesterday's ATP keystats (current season only, decrypted), on Mondays also
                         ManTennisData's weekly refresh, then linking, the live panel and each ATP player's 28-day speed
                         form (data/studies/serve_speed_tabpfn/live/). Stopped after 15 minutes. A block alerts at once;
                         any other failure alerts the second time in a row.
    itf      every day   The ITF live-data API (point_sources/itf_live.py --max-requests 1500), added 8 Oct 2026 by work
                         package P1 of docs/studies/gap_downloads/collection-plan.md: the day lists of the last 14 days
                         (the API refuses older dates, so a day not captured within 14 days is lost), then statistics
                         and points of the new singles matches, about 450 requests and 20 minutes a day; a backlog
                         after missed days is caught up 1,500 requests a day. Its tables are rebuilt after each run
                         (a parse cache: seconds). The run stops after at most 80 minutes, sooner when the task's
                         2-hour limit needs it (the canary follows on Mondays); its day lists come first. With under 3
                         minutes left it does not start (a failure). A block (exit 2) pauses the job and alerts at
                         once, again every 3 days while paused; a run asked for by name (--only itf) tries anyway and
                         lifts the pause when it gets through. Exit 3 (another ITF run holds the lock) is a skip, not
                         a failure.
    canary   Mondays     data_continuity/canary.py: whether each source is still there, archived, and unchanged in terms.
    slams    every day   A reminder only. Once a Grand Slam with an official feed (the Australian Open, Roland Garros,
                         Wimbledon, the US Open) has finished and its year is missing from data/raw/point_sources/, a
                         Claude session must collect it: the Australian Open's and Roland Garros's Infosys statistics and
                         point files, and rolandgarros.com's statistics, are their box-score source (decision of 9 Oct
                         2026). Each year needs the adapter's settings for that year, and the decision of 24 Sep 2026
                         asks for someone present to stop on a block.
    tdi      Mondays     TDI's forward capture (point_sources/tdi.py --recent 10 --max-requests 1000), proposed 8 Oct 2026
                         by work package P3 of docs/studies/gap_downloads/collection-plan.md and not yet in the cadence
                         decision: the listings of the last ten days, then the page of every new match, about 500
                         requests (21 minutes) and the table rebuild. It runs last and is stopped after 45 minutes, or
                         sooner so that the task ends inside its 2 hours (with under 15 minutes left it waits a week).
                         The listing keeps about 92 days, so a missed or cut-short week is caught up the next Monday. A
                         block pauses the job and alerts at once, then each Monday while paused; a run asked for by name
                         (--only tdi) tries anyway and lifts the pause when it gets through. Another TDI run holding the
                         lock is a skip, not a failure; a failure or a crowded-out Monday alerts the second time in a row.
    pinnacle_closes  every day   Pinnacle's closing prices, with every other listed book's, from TennisExplorer's match
                         pages (src/ingest/tennisexplorer.py), added 21 Oct 2026 at the owner's request ("Include in our
                         automatic download script downloading pinnacles closing value weekly (or daily if theres a daily
                         script thats being executed)"; docs/research/pinnacle-gap/). The model's odds input trains on
                         them from 1 Nov 2025 (current_best_model/odds_input.py). This year's calendar, the pages of the
                         events under way or just finished, every finished tour-level main-draw match of the last 21 days
                         not on disk (at most 400 pages; a usual day is 20-80, about 4 seconds each), then the site's
                         tables restaged. It runs last, in the time the others leave (with under 8 minutes left it waits
                         a day; the 21 days catch it up). A refusal (an HTTP 4xx answer or a challenge page) pauses the job
                         and alerts at once, then weekly while paused; a run asked for by name (--only pinnacle_closes)
                         tries anyway and lifts the pause when it gets through. Any other failure (usually the PC offline)
                         alerts the second time in a row.
The lower-level feed's run (--weekly; the Windows task "Tennis predictions - lower-level feed", every day at 12:00, a
3-hour limit), added 13 Oct 2026 at the owner's request ("Make sure our pipeline is set up to automatically integrate
this so this doesnt happen again"; docs/studies/data_gaps_2026/, docs/decisions/2026-10-13-lower-level-feed.md). The
levels Tennis My Life does not publish (ITF, women's qualifying, WTA 125, men's Challenger qualifying) were lost from
Stage 0 for four months after Sackmann's files ended; these jobs keep them current and watch for the next loss:
    tennislive   every day: TennisLive's event listings of the last complete week and the week in progress, its days up
                 to yesterday (point_sources/tennislive_events.py --through-yesterday --pageless-days --no-pages), about
                 100-300 requests: every level's results, the doubles and the observed start and finish times, which
                 the site keeps for about a month (the unpriced-leads rhythm group's data at bet time)
    wta_points   Mondays: the WTA API's five per-match documents (the umpire's point log, box score, advanced statistics,
                 win probability, point-by-point) of the tour, WTA 125 and Finals editions of the last five weeks,
                 staged (point_sources/wta.py --endpoints events,stats,advanced-stats,win-probability-momentum,
                 point-by-point): work package P2(a) of docs/studies/gap_downloads/collection-plan.md, added 14 Oct 2026
                 at the owner's request ("Set this up for this data to come in automatically with the other repeating
                 data acquisition"). About 800-1,800 requests; lists and 404s answered before an edition ended are asked
                 again, so the season's last editions (the WTA Finals, the December WTA 125s) settle by themselves
    wta_site     Tuesdays: the WTA website's records (P2(b), the same request): each player's list of the year asked
                 again when it shows a match in the last six weeks, one in six of the rest, every new opponent
                 followed (point_sources/wta.py --player-matches --refresh-before ... --refresh-active-since ...
                 --refresh-rotation 6), about 2,400 requests, staged for Wednesday's feed (its source wta_site). The
                 previous year's lists too until mid-February; a new year starts from the previous year's players. The
                 website lists a week's ITF results a week or two late: an alert when the newest ITF edition it lists is
                 more than six weeks old, again every four weeks while it lasts
                 Both run on the next day the task runs when their own day was missed (not on Wednesdays), and wait a day
                 when too little of the task's time is left
    wta          Wednesdays: the WTA API's match lists and box scores of the editions of the last five weeks
                 (point_sources/wta.py --endpoints stats; WTA 125, qualifying, Slams), about 300 requests
    feed         Wednesdays: the lower-level feed (src/eda/data_gaps_2026/feed.py --run --auto --advance): a candidate Stage 0 from
                 every source, its checks and a rule identity screen, the lost levels' scope, a dated snapshot that
                 every build and prediction run merges (additions.py). Exit 4 (the identity screen) or 5 (a check)
                 keeps the previous snapshot and alerts at once; a failure alerts the second time in a row
    coverage     Wednesdays: a Stage 0 built from today's files, with the accepted packages and the feed merged, against the same
                 months 1 and 2 years earlier (src/eda/data_gaps_2026/coverage.py): an alarm cell alerts when new, and
                 again every 4 weeks while it lasts; cells acknowledged in coverage.KNOWN do not alert
    tml_dates    Wednesdays (since 14 Oct 2026, docs/decisions/2026-10-14-p6-data-issues.md): Tennis My Life's edition
                 dates against the days played (src/eda/tml_revisions/edition_dates.py, about a minute, no request): an
                 edition dated in another week, not on its known list, alerts when new and every 4 weeks while it lasts
The feed's run also compares its "player in two main draws of one week" flags with the last advanced snapshot's
(src/eda/data_gaps_2026/two_draws.py); a new flag alerts, never blocks (same decision).
A block of TennisLive or the WTA API pauses that job and alerts, as for TDI; a run asked for by name tries anyway. The
WTA API's three jobs check that no other WTA collector is running (one collector per host).
Each job's outcome is appended to data/raw/_scheduled/runs.jsonl. state.json holds what the next run compares against,
and each child's output goes to logs/. Something that needs a person raises one Windows notification:
    a file held two runs in a row;
    a download that failed two runs in a row (one failure is usually the PC waking up offline);
    a block of the ITF live-data API (at once, then every 3 days while the job is paused);
    a block of TDI (at once, then each Monday while the job is paused);
    a new canary flag (not when most sources gave no answer at all: then the PC was offline);
    a finished Slam whose feed is missing (repeated weekly).
Nothing else is shown.

Run: C:/Users/zerom/miniforge3/envs/tennis/pythonw.exe -m src.ingest.scheduled     (the scheduled task: no window)
     C:/Users/zerom/miniforge3/envs/tennis/pythonw.exe -m src.ingest.scheduled --weekly    (the feed task, daily)
     ./python.sh -m src.ingest.scheduled [--only tml,speeds,itf,canary,slams,tdi,pinnacle_closes,tennislive,wta_points,wta_site,wta,
                                          feed,coverage]
                                         [--force-canary] [--no-notify] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = Path(sys.executable).with_name("python.exe")     # the tennis env's console Python, started without a window
OUT = ROOT / "data" / "raw" / "_scheduled"
LOGS = OUT / "logs"
STATE = OUT / "state.json"
RUNS = OUT / "runs.jsonl"
POINTS = ROOT / "data" / "raw" / "point_sources"
CANARY_LATEST = ROOT / "data" / "studies" / "data_continuity" / "canary_latest.json"
ITF_SUMMARY = ROOT / "data" / "studies" / "official_point_feeds" / "itf_live_summary.json"
ITF_REMIND = dt.timedelta(days=3)     # the API keeps 14 days: a paused ITF job is worth a reminder well before that
ITF_BUDGET = 1500                     # requests a run; a usual day needs about 450, so missed days are caught up
ITF_TIMEOUT = 80 * 60                 # stops the ITF run before the task's 2-hour limit would kill the whole task
ITF_SPARE = 10 * 60                   # of the task's time, kept after ITF's run for the jobs after it and the record
ITF_MONDAY_AFTER = 30 * 60            # the canary's own time limit: it follows ITF on Mondays
ITF_LEAST = 3 * 60                    # enough for the day lists (15 requests), the part that cannot wait a day
SPEEDS_BUDGET = 200                   # requests a day: a busy tour day is well under 100 keystats codes
SPEEDS_TIMEOUT = 15 * 60              # 200 requests at 2-3 s each, plus the panel and the form (about a minute)
TDI_SUMMARY = ROOT / "data" / "studies" / "official_point_feeds" / "tdi_summary.json"
TDI_WEEKDAY = 0                       # Monday: the ATP week ends on Sunday
TDI_TIMEOUT = 45 * 60                 # a week is about 500 pages (21 minutes) and the table rebuild; the rest resumes
TDI_LOCKED = "another TDI run is fetching"
TASK_LIMIT = 2 * 60 * 60              # Task Scheduler stops the whole task, its record and state unsaved, after 2 hours
TDI_SPARE = 10 * 60                   # of the task's time, kept after TDI's run for the record and the notification
TDI_LEAST = 15 * 60                   # with less than this left for it, TDI waits for the next Monday
PINNACLE_TIMEOUT = 40 * 60            # a usual day: ~15 event pages, 20-80 match pages (~4 s each) and the restage
PINNACLE_BUDGET = 400                 # match pages a run: a missed week (~350 pages) is caught up in one run
PINNACLE_DAYS = 21                    # the matches of the last three weeks; older ones the odds step fetches itself
PINNACLE_LEAST = 8 * 60               # with less than this of the task left, the job waits a day
PINNACLE_SPARE = 5 * 60               # of the task's time, kept after its run for the record and the notification
PINNACLE_REMIND = dt.timedelta(days=7)
PINNACLE_REFUSED = re.compile(r"STOPPED: .*(HTTP 4\d\d|challenge)")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
WEEKLY_JOBS = ("tennislive", "wta_points", "wta_site", "wta", "feed", "coverage", "tml_dates")   # the feed task's
FEED_WEEKDAY = 2                      # Wednesday: wta, feed and coverage (tennislive runs every day)
WTA_POINTS_WEEKDAY = 0                # Monday: the WTA week ends on Sunday (work package P2(a), added 14 Oct 2026)
WTA_SITE_WEEKDAY = 1                  # Tuesday: the website's records, read by Wednesday's feed (P2(b), 14 Oct 2026)
WEEKLY_DAYS = {"tennislive": None, "wta_points": WTA_POINTS_WEEKDAY, "wta_site": WTA_SITE_WEEKDAY,
               "wta": FEED_WEEKDAY, "feed": FEED_WEEKDAY, "coverage": FEED_WEEKDAY,
               "tml_dates": FEED_WEEKDAY}   # None: every day
CATCH_UP = ("wta_points", "wta_site")  # run on the next day the task runs when their own day was missed (PC off),
#                                       never on the feed's day, which is kept for the feed
WTA_POINTS_TIMEOUT = 100 * 60         # five weeks of editions, every endpoint: ~800-1,800 requests and the staging
WTA_POINTS_BUDGET = 2500
WTA_POINTS_ENDPOINTS = "events,stats,advanced-stats,win-probability-momentum,point-by-point"
WTA_POINTS_LEAST = 20 * 60            # with less than this left, the job waits for the next day (a catch-up)
WTA_SITE_TIMEOUT = 110 * 60           # the players active in the last six weeks and one in six of the rest: ~2,400
WTA_SITE_BUDGET = 3000                # requests in season (a new year's first crawl, ~4,000, takes two runs)
WTA_SITE_ACTIVE = 42                  # days: a player whose list shows a match this recent is asked again every week
WTA_SITE_ROTATION = 6                 # the rest one in six a week, so every player at least every six weeks
WTA_SITE_LEAST = 30 * 60
WTA_SITE_LAG = 42                     # days: the newest ITF edition the website lists older than this alerts (1-2
#                                       weeks behind in Oct 2026; six weeks clears the ITF calendar's Christmas break)
WTA_SITE_REMIND = dt.timedelta(days=28)
WTA_SUMMARY = ROOT / "data" / "studies" / "official_point_feeds" / "wta_summary.json"
WTA_SITE_SUMMARY = ROOT / "data" / "studies" / "gap_downloads" / "wta_player_matches_{year}_summary.json"
STAGE_TIMEOUT = 15 * 60               # a year's staging after a run its timeout stopped (a few minutes)
WEEKLY_LIMIT = 3 * 60 * 60            # the feed task's own limit (Task Scheduler stops it after 3 hours)
TENNISLIVE_TIMEOUT = 40 * 60          # two weeks' date pages and results sections (~300 requests) and the restage
WTA_TIMEOUT = 40 * 60                 # five weeks of editions' lists and box scores (~300 requests) and the staging
FEED_TIMEOUT = 110 * 60               # the candidate build (~30 min), checks, derive, snapshot, check
COVERAGE_TIMEOUT = 15 * 60            # a Stage 0 from today's files (~2 min) and the check with the merge
FEED_LEAST = 75 * 60                  # with less than this left for it, the feed waits a week (and alerts the 2nd time)
COVERAGE_REMIND = dt.timedelta(days=28)
COVERAGE_SUMMARY = ROOT / "data" / "studies" / "data_gaps_2026" / "coverage" / "weekly" / "summary.json"
COVERAGE_STAGE0 = ROOT / "data" / "studies" / "data_gaps_2026" / "coverage" / "stage0_scratch"
TML_DATES_TIMEOUT = 10 * 60          # the edition-date check (about a minute; no request)
TML_DATES_SUMMARY = ROOT / "data" / "studies" / "tml_revisions" / "edition_dates" / "weekly" / "summary.json"
TML_DATES_REMIND = dt.timedelta(days=28)
FEED_RUNS = ROOT / "data" / "studies" / "data_gaps_2026" / "feed" / "runs.jsonl"
# (name, raw folder, (month, day) by which the event has surely finished). The Australian Open's and Roland Garros's box
# scores come from their own Infosys statistics and point files, and Roland Garros's also from rolandgarros.com's
# statistics (docs/decisions/2026-10-09-ao-rg-box-scores-from-feeds.md); each needs collecting after the event
SLAMS = [("Australian Open", "ausopen", (2, 1)), ("Australian Open (Infosys statistics and point files)",
                                                  "infosys_slams/AO", (2, 1)),
         ("Roland Garros (rolandgarros.com statistics)", "rolandgarros", (6, 15)),
         ("Roland Garros (Infosys statistics and point files)", "infosys_slams/RG", (6, 15)),
         ("Wimbledon", "wimbledon", (7, 15)), ("US Open", "usopen", (9, 15))]
ADAPTER = {"infosys_slams/AO": "infosys_slams", "infosys_slams/RG": "infosys_slams"}   # folder -> adapter module
REMIND_EVERY = dt.timedelta(days=7)
HELD = re.compile(r"\[tennis_my_life\] held (\S+?):")
DONE = re.compile(r"\[tennis_my_life\] done: .*?(\d+) download errors")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def save_state(state: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    part = STATE.with_name(STATE.name + ".part")
    part.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    part.replace(STATE)


def record(entry: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with RUNS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def child(name: str, args: list[str], timeout: int) -> dict:
    """Run the tennis env's Python on args, without a window, its output appended to logs/<day>_<name>.log."""
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"{dt.date.today():%Y-%m-%d}_{name}.log"
    t0 = time.time()
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"=== {now()} {' '.join(args)}\n")
        fh.flush()
        try:
            code = subprocess.run([str(PY), *args], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT,
                                  creationflags=NO_WINDOW, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    return {"exit": code, "seconds": round(time.time() - t0, 1), "log": log.relative_to(ROOT).as_posix()}


def ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def notify(title: str, text: str) -> None:
    """One Windows toast through Windows PowerShell (best effort: a failure here is ignored)."""
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] "
        "> $null; $t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
        "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); $x = $t.GetElementsByTagName('text'); "
        f"$x.Item(0).AppendChild($t.CreateTextNode({ps_quote(title)})) > $null; "
        f"$x.Item(1).AppendChild($t.CreateTextNode({ps_quote(text)})) > $null; "
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
        "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe')"
        ".Show([Windows.UI.Notifications.ToastNotification]::new($t))")
    try:
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                       creationflags=NO_WINDOW, capture_output=True, timeout=60)
    except Exception:  # noqa: BLE001 - a missing notification must never stop the downloads
        pass


def job_tml(state: dict) -> tuple[dict, list[str]]:
    out = child("tml", ["-m", "src.ingest.public_dump.tennis_my_life", "--start-year", "2000"], timeout=3600)
    text = (ROOT / out["log"]).read_text(encoding="utf-8", errors="replace").split("=== ")[-1]   # this run's part
    held = sorted(set(HELD.findall(text)))
    done = DONE.search(text)
    out["held"], out["errors"] = held, int(done.group(1)) if done else None
    alerts = []
    again = sorted(set(held) & set(state.get("tml_held", [])))
    if again:
        alerts.append(f"Tennis My Life: {', '.join(again)} held two runs in a row. Ask Claude to review the held "
                      "copy (see data/raw/_scheduled/runs.jsonl).")
    failed = done is None or bool(out["errors"])
    if failed and state.get("tml_failed"):     # twice in a row: one failure is usually the PC waking up offline
        alerts.append(f"Tennis My Life download failed two runs in a row ({out['errors'] or 'no summary'}; exit "
                      f"{out['exit']}). Log: {out['log']}")
    state["tml_held"], state["tml_failed"] = held, failed
    return out, alerts


def job_speeds(state: dict) -> tuple[dict, list[str]]:
    """The daily live serve-speed pipeline. A block (the collector's Blocked in this run's log) alerts at once; any other
    non-zero exit or a timeout alerts the second time in a row (one failure is usually the PC waking up offline)."""
    out = child("speeds", ["src/ingest/speed_daily.py", "--max-requests", str(SPEEDS_BUDGET)], timeout=SPEEDS_TIMEOUT)
    text = (ROOT / out["log"]).read_text(encoding="utf-8", errors="replace").split("=== ")[-1]   # this run's part
    failed = out["exit"] != 0
    blocked = failed and "Blocked" in text
    out["blocked"] = blocked
    alerts = []
    if blocked:
        alerts.append(f"The daily ATP serve-speed collector was blocked by the ATP's server. It stops by itself; ask "
                      f"Claude to look before it runs again. Log: {out['log']}")
    elif failed and state.get("speeds_failed"):
        alerts.append(f"The daily serve-speed pipeline failed two runs in a row (exit {out['exit']}). Log: {out['log']}")
    state["speeds_failed"] = failed
    return out, alerts


def job_itf(state: dict, asked: bool, left: float = TASK_LIMIT) -> tuple[dict, list[str]]:
    """The ITF live-data API, given ``left`` seconds of the task's time. Exit 2 (a block) pauses the job until a run
    asked for by name gets through; exit 3 (another ITF run holds the lock) is a skip; any other non-zero exit, or too
    little time left to read the day lists, is a failure, alerted the second time."""
    paused = state.get("itf_blocked")
    alerts = []
    if paused and not asked:
        last = paused.get("reminded") or paused["at"]
        if dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last) >= ITF_REMIND:
            alerts.append(f"ITF live data is still paused after a block on {paused['at'][:10]}. Ask Claude to look "
                          f"({paused['log']}); the API keeps only 14 days of match lists.")
            paused["reminded"] = now()
        return {"skipped": f"paused since the block of {paused['at']}"}, alerts
    started = now()
    # the task as a whole may run 2 hours (Task Scheduler's limit): 1,500 requests take about an hour, and the run
    # stops in time for the jobs after it (on Mondays the canary, up to 30 minutes) and the record. The day lists come
    # first in a run; its tables are rebuilt at the end (only new answers are parsed: seconds)
    monday = dt.date.today().weekday() == 0
    timeout = int(min(ITF_TIMEOUT, left - ITF_SPARE - (ITF_MONDAY_AFTER if monday else 0)))
    if timeout < ITF_LEAST:
        if state.get("itf_failed"):
            alerts.append("ITF live data: the day's other jobs left too little time two runs in a row. Log: "
                          "data/raw/_scheduled/runs.jsonl")
        state["itf_failed"] = True
        return {"skipped": f"{int(left)} s of the task's time left"}, alerts
    out = child("itf", ["-m", "src.ingest.point_sources.itf_live", "--max-requests", str(ITF_BUDGET)], timeout=timeout)
    out["timeout"] = timeout
    try:
        summary = json.loads(ITF_SUMMARY.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        summary = {}
    if summary.get("started_at", "") >= started:     # this run's summary, not an earlier one
        out["requests"] = (summary.get("client") or {}).get("requests")
        out["outcomes"] = summary.get("fetch_outcomes")
        out["stopped"] = summary.get("stopped")
    if out["exit"] == 2:
        state["itf_blocked"] = {"at": now(), "log": out["log"]}
        alerts.append("ITF live data: the API refused the collector (a block), so the daily ITF job is paused. Ask "
                      f"Claude to look ({out['log']}); the API keeps only 14 days of match lists.")
    elif out["exit"] == 0 and paused:
        state.pop("itf_blocked", None)
    if out["exit"] == 3:                               # another ITF run was fetching: nothing asked, not a failure
        return out, alerts
    failed = out["exit"] not in (0, 2)
    if failed and state.get("itf_failed"):
        alerts.append(f"ITF live data download failed two runs in a row (exit {out['exit']}). Log: {out['log']}")
    state["itf_failed"] = failed
    return out, alerts


def job_tdi(state: dict, asked: bool, left: float = TASK_LIMIT) -> tuple[dict, list[str]]:
    """TDI's forward capture, given ``left`` seconds of the task's time. A block (the run's summary says Blocked) pauses
    the job, since the decision of 25 Sep 2026 says stop and report and never escalate; it is reminded of each week it
    stays paused, and a run asked for by name tries anyway and lifts the pause when it gets through. Another TDI run
    holding the lock is a skip. A failure, or a Monday whose other jobs left too little time, alerts the second time in
    a row. The listing keeps about 92 days, so a missed week is caught up by the next."""
    paused = state.get("tdi_blocked")
    if paused and not asked:
        return {"skipped": f"paused since the block of {paused['at']}"}, [
            f"TDI is still paused after a block on {paused['at'][:10]}. Ask Claude to look ({paused['log']}); the "
            "listing keeps about 92 days."]
    timeout = min(TDI_TIMEOUT, left - TDI_SPARE)
    if timeout < TDI_LEAST:
        alerts = ["TDI's weekly run did not complete two Mondays in a row (this time the day's other jobs left too "
                  "little of the task's 2 hours). Ask Claude to look at data/raw/_scheduled/runs.jsonl."] \
            if state.get("tdi_failed") else []
        state["tdi_failed"] = True
        return {"skipped": f"only {left / 60:.0f} minutes of the task were left"}, alerts
    started = now()
    out = child("tdi", ["-m", "src.ingest.point_sources.tdi", "--recent", "10", "--max-requests", "1000"],
                timeout=int(timeout))
    try:
        summary = json.loads(TDI_SUMMARY.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        summary = {}
    fresh = summary.get("started_at", "") >= started  # this run's summary, not an earlier one
    if fresh:
        out["requests"] = (summary.get("client") or {}).get("requests")
        out["pages"] = summary.get("pages")
        out["stopped"] = summary.get("stopped")
    text = (ROOT / out["log"]).read_text(encoding="utf-8", errors="replace").split("=== ")[-1]   # this run's part
    if TDI_LOCKED in text:                             # another TDI run was fetching: nothing asked, not a failure
        return {**out, "skipped": "another TDI run held the lock"}, []
    alerts = []
    if fresh and str(summary.get("stopped") or "").startswith("Blocked"):
        state["tdi_blocked"] = {"at": now(), "log": out["log"]}
        alerts.append("TDI refused the weekly collector (a block), so the TDI job is paused. Ask Claude to look "
                      f"({out['log']}); the listing keeps about 92 days.")
        return out, alerts
    if out["exit"] == 0:
        state.pop("tdi_blocked", None)
    failed = out["exit"] != 0
    if failed and state.get("tdi_failed"):
        alerts.append(f"TDI download failed two runs in a row (exit {out['exit']}). Log: {out['log']}")
    state["tdi_failed"] = failed
    return out, alerts


def job_pinnacle_closes(state: dict, asked: bool, left: float = TASK_LIMIT) -> tuple[dict, list[str]]:
    """Pinnacle's closing prices from TennisExplorer, given ``left`` seconds of the task's time (see the module's notes).
    A refusal pauses the job until a run asked for by name gets through, reminded weekly; any other failure alerts the
    second time in a row; too little time left is a skip, alerted the second time in a row."""
    paused = state.get("pinnacle_closes_blocked")
    if paused and not asked:
        alerts = []
        last = paused.get("reminded") or paused["at"]
        if dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last) >= PINNACLE_REMIND:
            alerts.append(f"The daily Pinnacle-closes download (TennisExplorer) is still paused after a refusal on "
                          f"{paused['at'][:10]}. Ask Claude to look ({paused['log']}): the model's odds input reads "
                          "these prices from 1 Nov 2025.")
            paused["reminded"] = now()
        return {"skipped": f"paused since the refusal of {paused['at']}"}, alerts
    timeout = min(PINNACLE_TIMEOUT, left - PINNACLE_SPARE)
    if timeout < PINNACLE_LEAST:
        alerts = ["The daily Pinnacle-closes download was crowded out two runs in a row (the day's other jobs left too "
                  "little of the task's 2 hours). Ask Claude to look at data/raw/_scheduled/runs.jsonl."] \
            if state.get("pinnacle_closes_failed") else []
        state["pinnacle_closes_failed"] = True
        return {"skipped": f"only {left / 60:.0f} minutes of the task were left"}, alerts
    today = dt.date.today()
    years = [str(today.year - 1), str(today.year)] if today.month == 1 else [str(today.year)]
    since = today - dt.timedelta(days=PINNACLE_DAYS)
    out = child("pinnacle_closes", ["-m", "src.ingest.tennisexplorer", "--calendar", *years, "--events", "--matches",
                                    "--since", since.isoformat(), "--max", str(PINNACLE_BUDGET), "--stage"],
                timeout=int(timeout))
    text = (ROOT / out["log"]).read_text(encoding="utf-8", errors="replace").split("=== ")[-1]   # this run's part
    fetched = re.search(r"matches: (\d+) pages fetched", text)
    out["match_pages"] = int(fetched.group(1)) if fetched else None
    alerts = []
    if out["exit"] == 2 and PINNACLE_REFUSED.search(text):
        state["pinnacle_closes_blocked"] = {"at": now(), "log": out["log"]}
        alerts.append("TennisExplorer refused the daily Pinnacle-closes download (a block), so the job is paused. Ask "
                      f"Claude to look ({out['log']}): the model's odds input reads these prices from 1 Nov 2025.")
        return out, alerts
    if out["exit"] == 0:
        state.pop("pinnacle_closes_blocked", None)
    failed = out["exit"] != 0
    if failed and state.get("pinnacle_closes_failed"):
        alerts.append(f"The daily Pinnacle-closes download (TennisExplorer) failed two runs in a row (exit {out['exit']}). "
                      f"Log: {out['log']}")
    state["pinnacle_closes_failed"] = failed
    return out, alerts


def iso_week(monday: dt.date) -> str:
    y, w, _ = monday.isocalendar()
    return f"{y}-W{w:02d}"


def host_busy(module: str) -> int | None:
    """The process id of another Python process running this collector module (one collector per host: the collection
    plan's shared rule 3), or None. TDI and the ITF job hold their own locks; TennisLive's and the WTA API's do not."""
    try:
        import psutil
    except ImportError:
        return None
    me = psutil.Process().pid
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["pid"] != me and "python" in (p.info["name"] or "").lower() \
                    and module in " ".join(p.info["cmdline"] or []):
                return p.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def blocked_job(state: dict, name: str, asked: bool, what: str, out: dict, text: str) -> tuple[bool, list[str]]:
    """A collector's block (its log says Blocked): pause the job and alert at once; a paused job alerts once a week and
    is skipped unless asked for by name. Returns (paused now, alerts)."""
    if "Blocked" in text:
        state[f"{name}_blocked"] = {"at": now(), "log": out["log"]}
        return True, [f"{what} refused the weekly collector (a block), so the {name} job is paused. Ask Claude to look "
                      f"({out['log']})."]
    if out["exit"] == 0:
        state.pop(f"{name}_blocked", None)
    return False, []


def job_tennislive(state: dict, asked: bool, left: float) -> tuple[dict, list[str]]:
    """TennisLive's event listings of the last two complete weeks: every level's results, qualifying and doubles
    included (the lower-level feed's results; the rhythm group's doubles). The staged listing always holds every week
    on disk (tennislive_events.run, since 13 Oct 2026)."""
    paused = state.get("tennislive_blocked")
    if paused and not asked:
        return {"skipped": f"paused since the block of {paused['at']}"}, [
            f"TennisLive is still paused after a block on {paused['at'][:10]}. Ask Claude to look ({paused['log']})."]
    busy = host_busy("point_sources.tennislive")
    if busy:
        return {"skipped": f"another TennisLive collector is running (PID {busy})"}, []
    today = dt.date.today()
    last = today - dt.timedelta(days=today.weekday() + 7)          # the Monday of the last complete week
    weeks = f"{iso_week(last)}:{iso_week(last + dt.timedelta(days=7))}"
    out = child("tennislive", ["-m", "src.ingest.point_sources.tennislive_events", "--weeks", weeks, "--through-yesterday",
                               "--pageless-days", "--max-requests", "800", "--skip-samples", "--no-pages"],
                timeout=int(min(TENNISLIVE_TIMEOUT, max(60, left - 10 * 60))))
    out["weeks"] = weeks
    text = (ROOT / out["log"]).read_text(encoding="utf-8", errors="replace").split("=== ")[-1]
    paused_now, alerts = blocked_job(state, "tennislive", asked, "TennisLive", out, text)
    failed = out["exit"] != 0 and not paused_now
    if failed and state.get("tennislive_failed"):
        alerts.append(f"TennisLive's weekly listing failed two weeks in a row (exit {out['exit']}). Log: {out['log']}")
    state["tennislive_failed"] = failed
    return out, alerts


def job_wta(state: dict, asked: bool, left: float) -> tuple[dict, list[str]]:
    """The WTA API's match lists and box scores of the editions of the last five weeks (WTA 125, qualifying, Slams and
    the tour), staged at the end: the lower-level feed's women's box scores."""
    paused = state.get("wta_blocked")
    if paused and not asked:
        return {"skipped": f"paused since the block of {paused['at']}"}, [
            f"The WTA API is still paused after a block on {paused['at'][:10]}. Ask Claude to look ({paused['log']})."]
    busy = host_busy("point_sources.wta")
    if busy:
        alerts = ["The WTA API's weekly top-up was skipped two weeks in a row: another WTA collector was running."] \
            if state.get("wta_skipped") else []
        state["wta_skipped"] = True
        return {"skipped": f"another WTA API collector is running (PID {busy})"}, alerts
    state["wta_skipped"] = False
    since = dt.date.today() - dt.timedelta(days=35)
    years = sorted({since.year, dt.date.today().year})
    out = child("wta", ["-m", "src.ingest.point_sources.wta", "--years", ",".join(map(str, years)),
                        "--from-date", since.isoformat(), "--tiers", "1000,500,250,125,slam,finals",
                        "--endpoints", "stats", "--max-requests", "600", "--stop-after-absences", "400"],
                timeout=int(min(WTA_TIMEOUT, max(60, left - 10 * 60))))
    text = (ROOT / out["log"]).read_text(encoding="utf-8", errors="replace").split("=== ")[-1]
    paused_now, alerts = blocked_job(state, "wta", asked, "The WTA API", out, text)
    failed = out["exit"] != 0 and not paused_now
    if failed and state.get("wta_failed"):
        alerts.append(f"The WTA API's weekly top-up failed two weeks in a row (exit {out['exit']}). Log: {out['log']}")
    state["wta_failed"] = failed
    return out, alerts


def this_run(path: Path, started: str) -> dict:
    """The run summary at ``path`` if this run wrote it (its started_at at or after ``started``), else {}."""
    try:
        summary = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}
    return summary if summary.get("started_at", "") >= started else {}


def run_text(out: dict) -> str:
    """The latest run's part of a child's log."""
    return (ROOT / out["log"]).read_text(encoding="utf-8", errors="replace").split("=== ")[-1]


def stopped_on_budget(summary: dict) -> bool:
    return str(summary.get("stopped") or "").startswith("BudgetExhausted")


def weekly_paused(state: dict, name: str, asked: bool, what: str) -> tuple[dict, list[str]] | None:
    """The skip of a paused weekly job (a block): skipped unless asked for by name, and reminded each time."""
    paused = state.get(f"{name}_blocked")
    if paused and not asked:
        return {"skipped": f"paused since the block of {paused['at']}"}, [
            f"{what} is still paused after a block on {paused['at'][:10]}. Ask Claude to look ({paused['log']})."]
    return None


def job_wta_points(state: dict, asked: bool, left: float) -> tuple[dict, list[str]]:
    """The WTA API's five per-match documents (the umpire's point log, the box score, advanced statistics, win
    probability and point-by-point) of the editions of the last five weeks, staged at the end: work package P2(a) of
    docs/studies/gap_downloads/collection-plan.md, kept current every Monday (owner, 14 Oct 2026). Match lists and 404s
    answered before their edition ended are asked again (wta.listing_stale, absence_stale), so each edition settles
    within a week of its end, the WTA Finals and the last WTA 125s of the season included. A run its timeout stops is
    staged by a short second child, so that Wednesday's feed reads what came. A block pauses the job; a run that stops
    on its request budget is not a failure (the rest comes the next week)."""
    skip = weekly_paused(state, "wta_points", asked, "The WTA API's weekly point records")
    if skip:
        return skip
    busy = host_busy("point_sources.wta")
    if busy:
        return {"skipped": f"another WTA API collector is running (PID {busy})"}, []   # caught up the next day
    timeout = int(min(WTA_POINTS_TIMEOUT, left - 10 * 60))
    if timeout < WTA_POINTS_LEAST:
        return {"skipped": f"only {left / 60:.0f} minutes of the task were left"}, []   # caught up the next day
    today = dt.date.today()
    since = today - dt.timedelta(days=35)
    years = ",".join(map(str, sorted({since.year, today.year})))
    started = now()
    out = child("wta_points", ["-m", "src.ingest.point_sources.wta", "--years", years, "--from-date", since.isoformat(),
                               "--tiers", "1000,500,250,125,finals", "--endpoints", WTA_POINTS_ENDPOINTS,
                               "--max-requests", str(WTA_POINTS_BUDGET), "--stop-after-absences", "400"],
                timeout=timeout)
    text = run_text(out)
    summary = this_run(WTA_SUMMARY, started)
    out.update(years=years, requests=(summary.get("client") or {}).get("requests"),
               outcomes=summary.get("fetch_outcomes"), stopped=summary.get("stopped"))
    if out["exit"] == "timeout":
        out["staged"] = child("wta_points", ["-m", "src.ingest.point_sources.wta", "--stage-only", "--years", years],
                              timeout=STAGE_TIMEOUT)["exit"]
    paused_now, alerts = blocked_job(state, "wta_points", asked, "The WTA API", out, text)
    failed = out["exit"] != 0 and not paused_now and not stopped_on_budget(summary)
    if failed and state.get("wta_points_failed"):
        alerts.append(f"The WTA API's weekly point records failed two weeks in a row (exit {out['exit']}). "
                      f"Log: {out['log']}")
    state["wta_points_failed"] = failed
    state["wta_points_last"] = today.isoformat()
    return out, alerts


def job_wta_site(state: dict, asked: bool, left: float) -> tuple[dict, list[str]]:
    """The WTA website's records (work package P2(b)): every Tuesday the players' lists of the year are asked again
    for the players whose list shows a match in the last six weeks, and for one in six of the rest (wta.py
    --player-matches --refresh-before <this run> --refresh-active-since <six weeks back> --refresh-rotation 6), and
    any new opponent is followed. Staged at the end for Wednesday's feed, which reads them as its source wta_site
    (src/eda/lower_level_evidence/candidate_stage0.py). Until mid-February the previous year's lists are refreshed
    too, for its last weeks' results; a new year starts from the previous year's players (wta.frozen_seeds). The
    website lists a week's ITF results a week or two late: when the newest ITF edition it lists is more than six
    weeks old, an alert, again every four weeks while it lasts."""
    skip = weekly_paused(state, "wta_site", asked, "The WTA website's weekly records")
    if skip:
        return skip
    busy = host_busy("point_sources.wta")
    if busy:
        return {"skipped": f"another WTA API collector is running (PID {busy})"}, []   # caught up the next day
    timeout = int(min(WTA_SITE_TIMEOUT, left - 10 * 60))
    if timeout < WTA_SITE_LEAST:
        return {"skipped": f"only {left / 60:.0f} minutes of the task were left"}, []   # caught up the next day
    today = dt.date.today()
    active = today - dt.timedelta(days=WTA_SITE_ACTIVE)
    before = now()                 # pages fetched before this run are asked again, for the players the rule picks
    t0, runs, failures, newest, blocked, log = time.time(), {}, [], None, False, None
    for year in sorted({active.year, today.year}):          # the previous year until mid-February, then this one
        remaining = int(timeout - (time.time() - t0))
        if remaining < 5 * 60:
            runs[year] = {"skipped": "no time left"}
            break
        started = now()
        run = child("wta_site", ["-m", "src.ingest.point_sources.wta", "--player-matches", "--player-year", str(year),
                                 "--max-requests", str(WTA_SITE_BUDGET), "--refresh-before", before,
                                 "--refresh-active-since", active.isoformat(),
                                 "--refresh-rotation", str(WTA_SITE_ROTATION)], timeout=remaining)
        log, text = run["log"], run_text(run)
        summary = this_run(str(WTA_SITE_SUMMARY).format(year=year), started)
        evidence = summary.get("evidence") or {}
        run.update(requests=(summary.get("client") or {}).get("requests"), stopped=summary.get("stopped"),
                   players=summary.get("players_asked"), results=evidence.get("results"),
                   itf_last_start=evidence.get("itf_last_start"))
        if run["exit"] == "timeout":             # the run stages at its end: stage what it fetched for the feed
            run["staged"] = child("wta_site", ["-m", "src.ingest.point_sources.wta", "--player-matches",
                                               "--player-year", str(year), "--stage-only"], timeout=STAGE_TIMEOUT)["exit"]
        runs[year] = run
        newest = max(filter(None, [newest, evidence.get("itf_last_start")]), default=None)
        if "Blocked" in text:
            blocked = True
            break
        if run["exit"] != 0 and not stopped_on_budget(summary):
            failures.append(run["exit"])
    result = {"years": runs, "log": log, "exit": failures[0] if failures else 0}
    paused_now, alerts = blocked_job(state, "wta_site", asked, "The WTA API (player lists)", result,
                                     "Blocked" if blocked else "")
    failed = bool(failures) and not paused_now
    if failed and state.get("wta_site_failed"):
        alerts.append(f"The WTA website's weekly records failed two weeks in a row (exit {failures[0]}). "
                      f"Log: {result['log']}")
    state["wta_site_failed"] = failed
    state["wta_site_last"] = today.isoformat()
    if newest:
        lag = (today - dt.date.fromisoformat(newest)).days
        result.update(itf_last_start=newest, lag_days=lag)
        last = state.get("wta_site_lag_alerted")
        if lag > WTA_SITE_LAG:
            if not last or today - dt.date.fromisoformat(last) >= WTA_SITE_REMIND:
                alerts.append(f"The WTA website's records: the newest ITF edition it lists began on {newest}, {lag} "
                              f"days ago (one or two weeks is usual). Ask Claude to look "
                              f"(data/studies/gap_downloads/wta_player_matches_{today.year}_summary.json).")
                state["wta_site_lag_alerted"] = today.isoformat()
        else:
            state.pop("wta_site_lag_alerted", None)
    return result, alerts


def weekly_due(today: dt.date, only: set[str] | None, state: dict) -> list[str]:
    """The weekly task's jobs due ``today``: tennislive every day, each other job on its weekday (WEEKLY_DAYS). A job of
    CATCH_UP whose own day was missed (its last run at least 8 days back; the PC off) runs on the next day the task
    runs, except the feed's day, which is kept for the feed. A job never run waits for its day."""
    if only:
        return [j for j in WEEKLY_JOBS if j in only]
    due = []
    for job in WEEKLY_JOBS:
        day = WEEKLY_DAYS[job]
        if day is None or today.weekday() == day:
            due.append(job)
        elif job in CATCH_UP and today.weekday() != FEED_WEEKDAY and state.get(f"{job}_last"):
            if (today - dt.date.fromisoformat(state[f"{job}_last"])).days >= 8:
                due.append(job)
    return due


def job_feed(state: dict, left: float) -> tuple[dict, list[str]]:
    """The lower-level feed's weekly snapshot (src/eda/data_gaps_2026/feed.py --run --auto --advance). Exit 4 (the
    identity screen) and 5 (a check) keep the previous snapshot and alert at once; another failure, or too little time
    left, alerts the second time in a row."""
    if left < FEED_LEAST:
        alerts = ["The lower-level feed did not run two weeks in a row (too little of the weekly task's time was left). "
                  "Ask Claude to look at data/raw/_scheduled/runs.jsonl."] if state.get("feed_failed") else []
        state["feed_failed"] = True
        return {"skipped": f"only {left / 60:.0f} minutes of the task were left"}, alerts
    out = child("feed", ["src/eda/data_gaps_2026/feed.py", "--run", "--auto", "--advance"],
                timeout=int(min(FEED_TIMEOUT, left - 10 * 60)))
    try:
        last = json.loads(FEED_RUNS.read_text(encoding="utf-8").splitlines()[-1])
        out["feed"] = {k: last.get(k) for k in ("label", "exit", "why", "snapshot", "minutes")}
    except (FileNotFoundError, ValueError, IndexError):
        pass
    alerts = []
    if out["exit"] in (4, 5):
        alerts.append(f"The lower-level feed stopped at a check ({(out.get('feed') or {}).get('why', out['exit'])}); "
                      "the previous snapshot stays in use. Ask Claude to look at data/studies/data_gaps_2026/feed/.")
    failed = out["exit"] not in (0, 4, 5)
    if failed and state.get("feed_failed"):
        alerts.append(f"The lower-level feed failed two weeks in a row (exit {out['exit']}). Log: {out['log']}")
    state["feed_failed"] = failed
    # a "player in two main draws of one week" flag the last advanced snapshot did not hold (owner, 14 Oct 2026,
    # docs/decisions/2026-10-14-p6-data-issues.md, point 4): an alert, never a block
    try:
        two = json.loads(FEED_RUNS.read_text(encoding="utf-8").splitlines()[-1]).get("two_draws") or {}
    except (FileNotFoundError, ValueError, IndexError):
        two = {}
    out["two_draws"] = two
    if two.get("new"):
        alerts.append(f"The lower-level feed's new snapshot has {two['new']} new \"player in two main draws of one week\" "
                      f"flag(s) (e.g. {'; '.join(two.get('new_examples', [])[:2])}): a source may file matches under the "
                      f"wrong event. Ask Claude to look ({two.get('file', 'data/studies/data_gaps_2026/feed/two_draws/')}).")
    elif two.get("error"):
        alerts.append(f"The lower-level feed's two-draws comparison failed ({two['error'][:120]}). Ask Claude to look.")
    return out, alerts


def job_tml_dates(state: dict, left: float) -> tuple[dict, list[str]]:
    """Tennis My Life's edition dates against the days played (src/eda/tml_revisions/edition_dates.py; owner, 14 Oct
    2026, docs/decisions/2026-10-14-p6-data-issues.md, point 3): an edition dated in another week than it was played,
    and not on the known list, alerts at once and every 4 weeks while it stays; it corrects nothing (a flagged edition
    goes to the three-reviewer route)."""
    out = child("tml_dates", ["src/eda/tml_revisions/edition_dates.py", "--label", "weekly"],
                timeout=int(min(TML_DATES_TIMEOUT, max(60, left - 5 * 60))))
    failed = out["exit"] not in (0, 3)                        # 3: the check ran and found a new misdated edition
    alerts = []
    if failed and state.get("tml_dates_failed"):
        alerts.append(f"The Tennis My Life date check failed two weeks in a row (exit {out['exit']}). Log: {out['log']}")
    state["tml_dates_failed"] = failed
    if failed:
        return out, alerts
    try:
        summary = json.loads(TML_DATES_SUMMARY.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return out, alerts + ["The Tennis My Life date check wrote no summary. Ask Claude to look."]
    flagged = set(summary.get("new", []))
    seen = state.setdefault("tml_dates_alerted", {})
    today = dt.date.today()
    new = sorted(e for e in flagged if e not in seen)
    due = sorted(e for e in flagged if e in seen and today - dt.date.fromisoformat(seen[e]) >= TML_DATES_REMIND)
    for e in new + due:
        seen[e] = today.isoformat()
    for e in list(seen):
        if e not in flagged:
            del seen[e]                                       # acknowledged (on the known list) or gone
    out.update(misdated=summary.get("misdated"), new=new, reminded=due)
    if new or due:
        names = ", ".join(" ".join(e.split("|")[2:4])[:30] for e in (new + due)[:3])
        alerts.append(f"Tennis My Life dates {len(new + due)} edition(s) in another week than they were played ({names}"
                      f"{' ...' if len(new + due) > 3 else ''}). Stage 0 would take the wrong date. Ask Claude to look "
                      "(data/studies/tml_revisions/edition_dates/weekly/summary.json).")
    return out, alerts


def job_coverage(state: dict, left: float) -> tuple[dict, list[str]]:
    """The coverage alarm on a Stage 0 built from today's files, with the accepted packages and the feed merged: a new
    alarm cell alerts at once, a lasting one every 4 weeks."""
    t = int(min(COVERAGE_TIMEOUT, max(60, left - 5 * 60)))
    out = child("coverage", ["src/eda/predictability_diagnostic/stage0_build.py", "--out-dir", str(COVERAGE_STAGE0)],
                timeout=t)
    if out["exit"] == 0:
        out["check"] = child("coverage", ["src/eda/data_gaps_2026/coverage.py", "--stage0", str(COVERAGE_STAGE0),
                                          "--with-accepted", "--label", "weekly"], timeout=t)
    code = out["check"]["exit"] if "check" in out else out["exit"]
    failed = code not in (0, 3)                            # 3: the check ran and the alarm is up
    alerts = []
    if failed and state.get("coverage_failed"):
        alerts.append(f"The coverage check failed two weeks in a row (exit {code}). Log: {out['log']}")
    state["coverage_failed"] = failed
    if failed:
        return out, alerts
    try:
        summary = json.loads(COVERAGE_SUMMARY.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return out, alerts + ["The coverage check wrote no summary. Ask Claude to look."]
    cells = set(summary.get("alarm_cell_keys", []))
    seen = state.setdefault("coverage_alarm", {})
    today = dt.date.today()
    new = sorted(c for c in cells if c not in seen)
    due = sorted(c for c in cells if c in seen and today - dt.date.fromisoformat(seen[c]) >= COVERAGE_REMIND)
    for c in new + due:
        seen[c] = today.isoformat()
    for c in list(seen):
        if c not in cells:
            del seen[c]                                   # cleared: a new loss alerts again
    out.update(alarm=len(cells), new=new, reminded=due)
    if new or due:
        alerts.append(f"Data coverage: {len(new)} new and {len(due)} lasting gaps against the year before "
                      f"({', '.join((new + due)[:3])}{' ...' if len(new + due) > 3 else ''}). Ask Claude to look "
                      "(data/studies/data_gaps_2026/coverage/weekly/summary.json).")
    return out, alerts


def canary_flags() -> set[str]:
    """item:FLAG pairs of the latest canary run. Only the flag's first word counts, so a flag whose text carries a
    date or a day count does not look new every week."""
    try:
        flags = json.loads(CANARY_LATEST.read_text(encoding="utf-8")).get("flags", {})
    except (FileNotFoundError, ValueError):
        return set()
    if isinstance(flags, dict):
        return {f"{item}:{str(f).split()[0]}" for item, fl in flags.items()
                for f in (fl if isinstance(fl, list) else [fl]) if str(f).strip()}
    return {str(f).split()[0] for f in flags if str(f).strip()}


def canary_offline() -> bool:
    """Whether most items of the latest canary run got no HTTP answer at all: the PC was offline, not the sources."""
    try:
        items = json.loads(CANARY_LATEST.read_text(encoding="utf-8")).get("items", [])
    except (FileNotFoundError, ValueError):
        return False
    return bool(items) and sum(i.get("status") is None for i in items) * 2 > len(items)


def job_canary(state: dict) -> tuple[dict, list[str]]:
    out = child("canary", ["src/eda/data_continuity/canary.py"], timeout=1800)
    if canary_offline():
        out["offline"] = True          # no alert, and the flags to compare against stay as they were
        return out, []
    flags = canary_flags()
    new = sorted(flags - set(state.get("canary_flags", [])))
    out["new_flags"] = new
    alerts = []
    if new:
        alerts.append(f"Source watch: new flag{'s' if len(new) > 1 else ''} {', '.join(new[:4])}"
                      f"{' and more' if len(new) > 4 else ''}. Ask Claude to look (canary_latest.json).")
    if out["exit"] != 0:
        alerts.append(f"Source watch failed (exit {out['exit']}). Log: {out['log']}")
    state["canary_flags"] = sorted(flags)
    return out, alerts


def slam_held(folder: str, year: int) -> bool:
    """Whether a year of a Slam's feed is held: a year folder of gzipped documents under data/raw/point_sources/
    (Wimbledon, the US Open, the Infosys files of the Australian Open and Roland Garros; rolandgarros.com's statistics
    under matches/), or, for the Australian Open's own feed, whose raw files carry no year, match-centre rows of that
    year in its staged matches table."""
    if folder == "rolandgarros":
        base = POINTS / folder / "matches" / str(year)
        return base.is_dir() and any(base.rglob("*.gz"))
    if folder == "ausopen":
        import pandas as pd

        staged = ROOT / "data" / "dump" / "points" / "ausopen" / "matches.parquet"
        if not staged.exists():
            return False
        d = pd.read_parquet(staged, columns=["year", "route"])
        return bool((d["year"].astype(str).eq(str(year)) & d["route"].eq("api")).any())
    base = POINTS / folder / str(year)
    return base.is_dir() and any(base.rglob("*.gz"))


def job_slams(state: dict, today: dt.date) -> tuple[dict, list[str]]:
    reminded = state.setdefault("slam_reminded", {})
    missing, alerts = [], []
    for name, folder, (month, day) in SLAMS:
        if today < dt.date(today.year, month, day) or slam_held(folder, today.year):
            continue
        key = f"{folder}/{today.year}"
        missing.append(key)
        last = reminded.get(key)
        if last is None or today - dt.date.fromisoformat(last) >= REMIND_EVERY:
            adapter = ADAPTER.get(folder, folder)
            alerts.append(f"{name} {today.year} has finished and its official feed is not collected. Ask Claude to "
                          f"collect it (src/ingest/point_sources/{adapter}.py needs {today.year}'s settings).")
            reminded[key] = today.isoformat()
    return {"missing": missing}, alerts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma list of jobs: tml, speeds, itf, canary, slams, tdi, pinnacle_closes, "
                                   "tennislive, wta_points, wta_site, wta, feed, coverage, tml_dates (default: the daily "
                                   "jobs that are due)")
    ap.add_argument("--weekly", action="store_true", help="the weekly task's jobs: tennislive, wta_points, wta_site, "
                                                          "wta, feed, coverage, tml_dates")
    ap.add_argument("--force-canary", action="store_true", help="run the canary even if it is not Monday")
    ap.add_argument("--no-notify", action="store_true", help="log only; no Windows notification")
    ap.add_argument("--dry-run", action="store_true", help="print the jobs that are due and stop")
    a = ap.parse_args()
    today = dt.date.today()
    daily = ("tml", "speeds", "itf", "canary", "slams", "tdi", "pinnacle_closes")
    if a.weekly:
        due = weekly_due(today, set(a.only.split(",")) if a.only else None, load_state())
        limit = WEEKLY_LIMIT
    else:
        only = set(a.only.split(",")) if a.only else set(daily)
        due = [j for j in daily + WEEKLY_JOBS
               if j in only and (j != "canary" or today.weekday() == 0 or a.force_canary or a.only)
               and (j != "tdi" or today.weekday() == TDI_WEEKDAY or a.only)]
        limit = TASK_LIMIT if not set(due) & set(WEEKLY_JOBS) else WEEKLY_LIMIT
    if a.dry_run:
        print(json.dumps({"today": today.isoformat(), "due": due, "python": str(PY)}))
        return 0
    state = load_state()
    alerts: list[str] = []
    entry: dict = {"started_at": now(), "jobs": {}, "weekly": a.weekly}
    t0 = time.time()
    asked = bool(a.only)
    try:
        for job in due:
            left = limit - (time.time() - t0)
            if job == "tml":
                out, more = job_tml(state)
            elif job == "speeds":
                out, more = job_speeds(state)
            elif job == "itf":
                out, more = job_itf(state, asked=asked, left=left)
            elif job == "canary":
                out, more = job_canary(state)
            elif job == "tdi":
                out, more = job_tdi(state, asked=asked, left=left)
            elif job == "pinnacle_closes":
                out, more = job_pinnacle_closes(state, asked=asked, left=left)
            elif job == "tennislive":
                out, more = job_tennislive(state, asked, left)
            elif job == "wta_points":
                out, more = job_wta_points(state, asked, left)
            elif job == "wta_site":
                out, more = job_wta_site(state, asked, left)
            elif job == "wta":
                out, more = job_wta(state, asked, left)
            elif job == "feed":
                out, more = job_feed(state, left)
            elif job == "coverage":
                out, more = job_coverage(state, left)
            elif job == "tml_dates":
                out, more = job_tml_dates(state, left)
            else:
                out, more = job_slams(state, today)
            entry["jobs"][job] = out
            alerts += more
    except Exception:  # noqa: BLE001 - recorded, notified, and the run exits non-zero
        entry["error"] = traceback.format_exc(limit=5)
        alerts.append("The scheduled tennis downloads stopped with an error. Ask Claude to look at "
                      "data/raw/_scheduled/runs.jsonl.")
    entry["finished_at"] = now()
    entry["alerts"] = alerts
    record(entry)
    save_state(state)
    if alerts and not a.no_notify:
        notify("Tennis predictions: data needs a look", alerts[0] + (f" (+{len(alerts) - 1} more)" if len(alerts) > 1
                                                                     else ""))
    return 1 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
