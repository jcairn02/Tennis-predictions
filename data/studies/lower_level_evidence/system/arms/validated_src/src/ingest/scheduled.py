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
    slams    every day   A reminder only. Once a Grand Slam with an official feed (the Australian Open, Wimbledon, the US
                         Open) has finished and its year is missing from data/raw/point_sources/, a Claude session must
                         collect it. Each year needs the adapter's settings for that year, and the decision of 24 Sep
                         2026 asks for someone present to stop on a block.
    tdi      Mondays     TDI's forward capture (point_sources/tdi.py --recent 10 --max-requests 1000), proposed 8 Oct 2026
                         by work package P3 of docs/studies/gap_downloads/collection-plan.md and not yet in the cadence
                         decision: the listings of the last ten days, then the page of every new match, about 500
                         requests (21 minutes) and the table rebuild. It runs last and is stopped after 45 minutes, or
                         sooner so that the task ends inside its 2 hours (with under 15 minutes left it waits a week).
                         The listing keeps about 92 days, so a missed or cut-short week is caught up the next Monday. A
                         block pauses the job and alerts at once, then each Monday while paused; a run asked for by name
                         (--only tdi) tries anyway and lifts the pause when it gets through. Another TDI run holding the
                         lock is a skip, not a failure; a failure or a crowded-out Monday alerts the second time in a row.
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
     ./python.sh -m src.ingest.scheduled [--only tml,speeds,itf,canary,slams,tdi] [--force-canary] [--no-notify] [--dry-run]
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
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# (name, raw folder, (month, day) by which the event has surely finished)
SLAMS = [("Australian Open", "ausopen", (2, 1)), ("Wimbledon", "wimbledon", (7, 15)), ("US Open", "usopen", (9, 15))]
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
    (Wimbledon, the US Open), or, for the Australian Open, whose raw files carry no year, match-centre rows of that
    year in its staged matches table."""
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
            alerts.append(f"{name} {today.year} has finished and its official feed is not collected. Ask Claude to "
                          f"collect it (src/ingest/point_sources/{folder}.py needs {today.year}'s settings).")
            reminded[key] = today.isoformat()
    return {"missing": missing}, alerts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma list of jobs: tml, speeds, itf, canary, slams, tdi (default: all that are due)")
    ap.add_argument("--force-canary", action="store_true", help="run the canary even if it is not Monday")
    ap.add_argument("--no-notify", action="store_true", help="log only; no Windows notification")
    ap.add_argument("--dry-run", action="store_true", help="print the jobs that are due and stop")
    a = ap.parse_args()
    today = dt.date.today()
    only = set(a.only.split(",")) if a.only else {"tml", "speeds", "itf", "canary", "slams", "tdi"}
    due = [j for j in ("tml", "speeds", "itf", "canary", "slams", "tdi")
           if j in only and (j != "canary" or today.weekday() == 0 or a.force_canary or a.only)
           and (j != "tdi" or today.weekday() == TDI_WEEKDAY or a.only)]
    if a.dry_run:
        print(json.dumps({"today": today.isoformat(), "due": due, "python": str(PY)}))
        return 0
    state = load_state()
    alerts: list[str] = []
    entry: dict = {"started_at": now(), "jobs": {}}
    t0 = time.time()
    try:
        for job in due:
            if job == "tml":
                out, more = job_tml(state)
            elif job == "speeds":
                out, more = job_speeds(state)
            elif job == "itf":
                out, more = job_itf(state, asked=bool(a.only), left=TASK_LIMIT - (time.time() - t0))
            elif job == "canary":
                out, more = job_canary(state)
            elif job == "tdi":
                out, more = job_tdi(state, asked=bool(a.only), left=TASK_LIMIT - (time.time() - t0))
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
