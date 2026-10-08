"""Unattended downloads, run once a day by Windows Task Scheduler (docs/decisions/2026-10-06-download-cadence.md).

Jobs:
    tml      every day   Tennis My Life (public_dump/tennis_my_life.py --start-year 2000). Each changed file is
                         downloaded; the version it replaces is kept (superseded/) and a damaged one is held (held/).
    canary   Mondays     data_continuity/canary.py: whether each source is still there, archived, and unchanged in terms.
    slams    every day   A reminder only. Once a Grand Slam with an official feed (the Australian Open, Wimbledon, the US
                         Open) has finished and its year is missing from data/raw/point_sources/, a Claude session must
                         collect it. Each year needs the adapter's settings for that year, and the decision of 24 Sep
                         2026 asks for someone present to stop on a block.
Each job's outcome is appended to data/raw/_scheduled/runs.jsonl. state.json holds what the next run compares against,
and each child's output goes to logs/. Something that needs a person raises one Windows notification:
    a file held two runs in a row;
    a download that failed two runs in a row (one failure is usually the PC waking up offline);
    a new canary flag (not when most sources gave no answer at all: then the PC was offline);
    a finished Slam whose feed is missing (repeated weekly).
Nothing else is shown.

Run: C:/Users/zerom/miniforge3/envs/tennis/pythonw.exe -m src.ingest.scheduled     (the scheduled task: no window)
     ./python.sh -m src.ingest.scheduled [--only tml,canary,slams] [--force-canary] [--no-notify] [--dry-run]
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
    ap.add_argument("--only", help="comma list of jobs: tml, canary, slams (default: all that are due)")
    ap.add_argument("--force-canary", action="store_true", help="run the canary even if it is not Monday")
    ap.add_argument("--no-notify", action="store_true", help="log only; no Windows notification")
    ap.add_argument("--dry-run", action="store_true", help="print the jobs that are due and stop")
    a = ap.parse_args()
    today = dt.date.today()
    only = set(a.only.split(",")) if a.only else {"tml", "canary", "slams"}
    due = [j for j in ("tml", "canary", "slams")
           if j in only and (j != "canary" or today.weekday() == 0 or a.force_canary or a.only)]
    if a.dry_run:
        print(json.dumps({"today": today.isoformat(), "due": due, "python": str(PY)}))
        return 0
    state = load_state()
    alerts: list[str] = []
    entry: dict = {"started_at": now(), "jobs": {}}
    try:
        for job in due:
            if job == "tml":
                out, more = job_tml(state)
            elif job == "canary":
                out, more = job_canary(state)
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
