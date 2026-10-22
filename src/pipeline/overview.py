"""The notebook's first cell after the imports: where everything stands, in one table.

Reads only (no step runs): the scheduled downloads' last run, how fresh each source is, the model instance the daily
pipeline predicts with and what it holds, the latest prediction runs, Pinnacle's latest pull, and the free disk.
Every line degrades to "unknown" rather than failing, so the cell always shows something.
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


def downloads() -> dict:
    from .data import held_tml_files, scheduled_runs
    runs = scheduled_runs(last=1)
    if not runs:
        return {"last_run": "none recorded"}
    r = runs[-1]
    exits = {j: v.get("exit") for j, v in r.get("jobs", {}).items() if isinstance(v, dict) and "exit" in v}
    return {"last_run": dt.datetime.fromisoformat(r["started_at"]).astimezone().strftime("%Y-%m-%d %H:%M"),
            "exits": exits, "alerts": r.get("alerts", []), "held_tml": held_tml_files()}


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

    def speed():
        files = sorted(CFG.SPEED_LIVE.glob("speed_form_*.parquet"))
        return f"latest form {files[-1].stem.replace('speed_form_', '')}" if files else "none"
    out["ATP serve-speed form"] = _safe(speed)

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


def model() -> dict:
    from .train import instance_status, stage2_status
    st = instance_status()
    st["stage2"] = stage2_status()
    return st


def prediction_runs(last: int = 5) -> list[dict]:
    runs = sorted((p for p in CFG.DAILY_RUNS.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)[-last:] \
        if CFG.DAILY_RUNS.exists() else []
    out = []
    for r in runs:
        rd = r / "run_day.json"
        info = {"run": r.name, "when": _age(r)}
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
           "model": _safe(model), "prediction_runs": _safe(prediction_runs), "running": _safe(running),
           "env_not_inherited": _safe(scrubbed_now), "disk": _safe(disk)}
    if show:
        _print(out)
    return out


def _print(out: dict) -> None:
    d = out["downloads"]
    print("== Downloads (scheduled daily 07:30) ==")
    if isinstance(d, dict):
        print(f"  last run {d.get('last_run')}   exit codes {d.get('exits')}")
        for a in d.get("alerts", []):
            print(f"  ALERT: {a}")
        if d.get("held_tml"):
            print(f"  held Tennis My Life files: {', '.join(d['held_tml'])}")
    else:
        print(" ", d)
    print("== Sources ==")
    for k, v in (out["sources"].items() if isinstance(out["sources"], dict) else []):
        print(f"  {k:42s} {v}")
    m = out["model"]
    print("== Model ==")
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
