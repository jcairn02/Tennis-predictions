"""The notebook's first cell after the imports: where everything stands, in one table.

Reads only (no step runs): the scheduled downloads' runs of the last day and alerts of the last days, how fresh each
source is (serve speeds by their newest reading, and the source watch's flags, through src/ingest/health.py), the live
model the notebook's selection names and what it holds, the tours the bet day handles (config.BET_TOURS), the latest
prediction runs, Pinnacle's latest pull, and the free disk. Every line degrades to "unknown" rather than failing, so the cell always shows something.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

from . import config as CFG


def _age(path: Path) -> str:
    if not path.exists():
        return "missing"
    t = dt.datetime.fromtimestamp(path.stat().st_mtime)
    hours = (dt.datetime.now() - t).total_seconds() / 3600
    return f"{t:%Y-%m-%d %H:%M} ({hours:.0f} h ago)" if hours < 72 else f"{t:%Y-%m-%d %H:%M} ({hours / 24:.0f} days ago)"


def _safe(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - a status line never breaks the cell
        return f"unknown ({type(exc).__name__}: {exc})"


ALERT_DAYS = 3        # STATUS repeats the scheduled task's alerts of the last three days


def downloads(now: dt.datetime | None = None) -> dict:
    """The scheduled task's runs of the last 24 hours, each job's latest run, and every alert of the last ALERT_DAYS
    days with its time. Until 22 Oct 2026 only the latest run was shown, so a morning alert vanished from STATUS as
    soon as an afternoon job ran (production-integrity plan, step 1)."""
    from .data import held_tml_files, scheduled_runs
    runs = scheduled_runs(last=80)
    if not runs:
        return {"last_run": "none recorded"}
    now = now or dt.datetime.now().astimezone()

    def when(r):
        return dt.datetime.fromisoformat(r["started_at"]).astimezone()

    def short(v):
        return (v.get("exit") if "exit" in v else ("skipped" if v.get("skipped") else "ran")) if isinstance(v, dict) else v

    runs = sorted(runs, key=when)                    # the file is in the order runs finished, not started
    jobs = {}
    for r in runs:                                   # oldest first: each job's latest run wins
        for j, v in (r.get("jobs") or {}).items():
            jobs[j] = {"at": when(r).strftime("%Y-%m-%d %H:%M"), "result": short(v)}
    said: dict[str, dict] = {}                       # one line per alert text: its latest time and how often it came
    for r in runs:
        if now - when(r) <= dt.timedelta(days=ALERT_DAYS):
            for a in r.get("alerts") or []:
                said[a] = {"at": when(r).strftime("%m-%d %H:%M"), "alert": a, "times": said.get(a, {}).get("times", 0) + 1}
    return {"last_run": when(runs[-1]).strftime("%Y-%m-%d %H:%M"),
            "runs_24h": [{"at": when(r).strftime("%m-%d %H:%M"),
                          "jobs": {j: short(v) for j, v in (r.get("jobs") or {}).items()}}
                         for r in runs if now - when(r) <= dt.timedelta(hours=24)],
            "jobs": jobs, "alerts": sorted(said.values(), key=lambda x: x["at"]), "held_tml": held_tml_files(),
            "tml": tml_lines()}


def tml_lines() -> list[str]:
    """Tennis My Life's held files (lagging after a day), the events carried from earlier copies and the corrections
    accepted by the download itself (src/ingest/health.py, 28 Oct 2026)."""
    from src.ingest import health as H
    try:
        return H.tml_status()["lines"]
    except Exception as exc:  # noqa: BLE001 - a status line never breaks the cell
        return [f"Tennis My Life status unknown ({type(exc).__name__}: {exc})"]


def source_watch() -> str:
    """The canary's flags: open ones, acknowledged ones (until their date) and lapsed acknowledgments."""
    from src.ingest import health as H
    flags = H.canary_flags()
    if not flags:
        return "no flags"
    g = H.canary_split(flags, H.canary_known())
    parts = []
    if g["open"]:
        parts.append(f"OPEN: {', '.join(g['open'])}")
    if g["lapsed"]:
        parts.append(f"ACKNOWLEDGMENT RUN OUT: {', '.join(g['lapsed'])}")
    if g["acknowledged"]:
        parts.append(f"{len(g['acknowledged'])} known and acknowledged")
    return "; ".join(parts)


def stage0_latest() -> str:
    import pandas as pd
    p = CFG.STAGE0 / "stage0_matches.parquet"
    m = pd.read_parquet(p, columns=["tour", "tournament_date", "level"])
    main = m[m["level"].astype(str).isin(["GS", "T1000", "T500", "T250", "FIN"])]
    last = pd.to_datetime(main["tournament_date"]).groupby(main["tour"]).max()
    starts = ", ".join(f"{t.upper()} {d:%Y-%m-%d}" for t, d in last.items())
    return f"latest main-tour event start: {starts}; file {_age(p)}"


def sources() -> dict:
    out = {"repo Stage 0 (shared tables)": _safe(stage0_latest),
           "Tennis My Life, ongoing files": _safe(lambda: _age(max((CFG.TML_RAW).glob("*ongoing*"),
                                                                    key=lambda p: p.stat().st_mtime))),
           "timeline (match_timing/timing.parquet)": _safe(lambda: _age(CFG.TIMING))}

    def speed():                  # the newest reading, never the form file's date (rewritten daily; 22 Oct 2026)
        from src.ingest import health as H
        return H.speed_status()["line"]
    out["ATP serve speeds"] = _safe(speed)
    out["source watch (canary)"] = _safe(source_watch)

    def oddstrader():
        months = sorted(p.stem for p in (CFG.ROOT / "data/raw/oddstrader/events/23").glob("*.json"))
        return f"months held {months[0]}..{months[-1]}; latest listing {_age(CFG.ROOT / 'data/raw/oddstrader/events/23' / (months[-1] + '.json'))}" if months else "none"
    out["OddsTrader (BetOnline/Pinnacle lines)"] = _safe(oddstrader)

    def tennis_data():
        files = sorted((CFG.ODDS_DUMP / "tennis_data_couk").rglob("*.parquet"), key=lambda p: p.stat().st_mtime)
        return _age(files[-1]) if files else "none"
    out["tennis-data.co.uk odds (staged)"] = _safe(tennis_data)

    def pinnacle():
        pulls = sorted(CFG.PINNACLE_RAW.glob("20*/*_matchups.json.gz"))
        return f"latest pull {pulls[-1].name[:15]}" if pulls else "no pull yet (live.record_pinnacle())"
    out["Pinnacle live lines"] = _safe(pinnacle)
    return out


def live_model() -> str:
    """The live model as the notebook's selection names it, the one place that does (22 Oct 2026), or a loud line."""
    from .train import _selection, selected_instance_name
    name = selected_instance_name()
    if not name:
        return ("NONE SELECTED: the daily pipeline refuses to predict until use_instance() names one "
                f"({CFG.rel(CFG.SELECTED_INSTANCE)})")
    sel = _selection()
    return f"{name} on {sel['tree']} (the notebook's selection, set {sel.get('selected_at') or 'at an unrecorded time'})"


def model() -> dict:
    from .train import instance_status, stage2_status
    st = instance_status()
    st["stage2"] = stage2_status()
    return st


def _made_at(run: Path) -> str:
    """When a run was made: its run.json's created_at, else the folder's time (a folder's own time moves when anything
    inside it is touched, e.g. a cleanup, so it put old runs first: 22 Oct 2026)."""
    try:
        return str(json.loads((run / "run.json").read_text(encoding="utf-8"))["created_at"])
    except (OSError, ValueError, KeyError):
        return dt.datetime.fromtimestamp(run.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def prediction_runs(last: int = 5) -> list[dict]:
    runs = sorted((p for p in CFG.DAILY_RUNS.iterdir() if p.is_dir()), key=_made_at)[-last:] \
        if CFG.DAILY_RUNS.exists() else []
    out = []
    for r in runs:
        rd = r / "run_day.json"
        info = {"run": r.name, "when": f"made {_made_at(r)}"}
        if rd.exists():
            j = json.loads(rd.read_text(encoding="utf-8"))
            info["finished"] = bool(j.get("finished") or j.get("total_seconds") or j.get("seconds"))
        info["predictions"] = (r / "predictions.csv").exists()
        out.append(info)
    return out


def disk() -> str:
    u = shutil.disk_usage(CFG.ROOT)
    return f"{u.free / 1e9:.0f} GB free of {u.total / 1e9:.0f} GB"


def status(show: bool = True) -> dict:
    """Everything at a glance. Returns the same content as a dict."""
    from .data import paused_jobs
    from .runner import running, scrubbed_now
    out = {"downloads": _safe(downloads), "paused": _safe(paused_jobs), "sources": _safe(sources),
           "live_model": _safe(live_model), "bet_tours": _safe(CFG.bet_tours_line),
           "model": _safe(model), "prediction_runs": _safe(prediction_runs), "running": _safe(running),
           "env_not_inherited": _safe(scrubbed_now), "disk": _safe(disk)}
    if show:
        _print(out)
    return out


def _print(out: dict) -> None:
    d = out["downloads"]
    print("== Downloads (scheduled daily 07:30; the lower-level feed's task at 12:00) ==")
    if isinstance(d, dict):
        for r in d.get("runs_24h", []):
            print(f"  run {r['at']}: " + ", ".join(f"{j} {v}" for j, v in r["jobs"].items()))
        if not d.get("runs_24h"):
            print(f"  NO RUN IN THE LAST 24 HOURS (last run {d.get('last_run')})")
        older = {j: v for j, v in (d.get("jobs") or {}).items()
                 if not any(j in r["jobs"] for r in d.get("runs_24h", []))}
        if older:
            print("  older: " + ", ".join(f"{j} {v['result']} at {v['at']}" for j, v in sorted(older.items())))
        for a in d.get("alerts", []):
            again = f", {a['times']} runs in {ALERT_DAYS} days" if a.get("times", 1) > 1 else ""
            print(f"  ALERT ({a['at']}{again}): {a['alert']}")
        for line in d.get("tml") or []:
            print(f"  {line}")
        if d.get("held_tml"):
            print(f"  held Tennis My Life files (to accept one after review: --accept-held NAME@SHA12): "
                  f"{', '.join(d['held_tml'])}")
    else:
        print(" ", d)
    print("== Sources ==")
    for k, v in (out["sources"].items() if isinstance(out["sources"], dict) else []):
        print(f"  {k:42s} {v}")
    m = out["model"]
    print("== Model ==")
    print(f"  LIVE MODEL: {out.get('live_model')}")
    print(f"  BET DAY (A1-A8): {out.get('bet_tours')}")
    if isinstance(m, dict):
        print(f"  instance {m.get('instance')} (active: {m.get('active')}), {m.get('inputs')} inputs, "
              f"odds input applied: {m.get('odds_input')}")
        print(f"  local fits (season: seeds) {m.get('local_fits')}")
        print(f"  Thinking fits {m.get('thinking_fits') or 'none'}   stage-2 seasons {list((m.get('stage2') or {}).keys())}")
        print(f"  checkpoints {m.get('checkpoints')}   TabPFN caches {m.get('tabpfn_caches')}")
    else:
        print(" ", m)
    try:                                               # the owner's timer (20 Oct 2026)
        from .train import model_age
        print(f"  MODEL AGE: {model_age()['line']}")
    except Exception as e:
        print(f"  MODEL AGE: unknown ({type(e).__name__})")
    if out.get("paused"):
        print(f"  PAUSED after a block: {out['paused']}")
    print("== Latest prediction runs ==")
    for r in (out["prediction_runs"] if isinstance(out["prediction_runs"], list) else []):
        print(f"  {r['run']:60s} {r['when']}  predictions: {r['predictions']}")
    if out.get("running"):
        print("== Steps still running (started from a notebook) ==")
        for r in out["running"]:
            print(f"  {r['step']} (pid {r['pid']}, since {r['started']}): log {r['log']}")
    if out.get("env_not_inherited"):
        print(f"== Note: set in this kernel but NOT passed to steps: {out['env_not_inherited']} ==")
    print("== Disk ==\n ", out["disk"])
