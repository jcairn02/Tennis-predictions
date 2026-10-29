"""The daily live serve-speed pipeline (serve-speed TabPFN study, src/eda/serve_speed_tabpfn/live/).

Decisions: docs/decisions/2026-10-07-speed-nudge.md (amended 8 Oct 2026: the 28-day memory; daily speeds wanted) and
docs/decisions/2026-10-08-scraping-approved.md (clarified: the daily collector decrypts the current season's ATP files;
the 2015-2021 backfill stays encrypted). Not wired into src/ingest/scheduled.py: the lead does that after the owner's
OK. Reads no match result.

Steps, each morning:
    1 ManTennisData: on Mondays (or --mantd force), its weekly refresh (src.ingest.public_dump.mantennisdata --commit
      latest; plain CSV, no decryption: the fallback feed); then its rows the frozen panel and earlier staging lack are
      staged (live/staging/mantd_<date>.parquet)
    2 the ATP daily collector (live/atp_daily.py): OFF until the lead enables it in live/collector.json. When on: the
      current season's keystats of the rounds Tennis My Life lists as played since the last run (--days-back, default 1:
      yesterday), each code once and every event's main draw before any qualifying code (atp_daily.daily_plan), at
      most --max-requests requests, then decrypt-and-stage (live/staging/atp_daily_<date>.parquet; a second run on the
      same day adds to it). --plan-only prints the plan and sends nothing
    3 link every staged match to the project's match and player ids (live/linked.parquet)
    4 the live panel: the frozen panel plus the new rows (live/speed_panel_live.parquet)
    5 each ATP player's 28-day speed form as of the date (live/speed_form_<date>.parquet)
One line per run in live/runs.jsonl.

Usage:
    ./python.sh src/ingest/speed_daily.py                         # today
    ./python.sh src/ingest/speed_daily.py --date 2026-10-08 --no-network
    ./python.sh src/ingest/speed_daily.py --plan-only             # the collector's plan, no request
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.eda.serve_speed_tabpfn.live import atp_daily as AD  # noqa: E402
from src.eda.serve_speed_tabpfn.live import common as LC  # noqa: E402
from src.eda.serve_speed_tabpfn.live import form as FM  # noqa: E402
from src.eda.serve_speed_tabpfn.live import link as LK  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402
from src.eda.serve_speed_tabpfn.live import staging as ST  # noqa: E402

MANTD_RAW = ROOT / "data" / "raw" / "public_dump" / "mantennisdata" / "atp"


def mantd_refresh() -> dict:
    r = subprocess.run([sys.executable, "-m", "src.ingest.public_dump.mantennisdata", "--commit", "latest"],
                       cwd=str(ROOT), capture_output=True, text=True)
    return {"returncode": r.returncode, "tail": (r.stdout or "")[-400:] + (r.stderr or "")[-400:]}


def stage_mantd(day: int, staging: Path) -> int:
    """ManTennisData rows with both first-serve averages that neither the frozen panel nor earlier staging holds."""
    year = int(LC.date_of(day)[:4])
    years = [year - 1, year] if LC.date_of(day)[5:7] == "01" else [year]
    frames = []
    for y in years:
        f = MANTD_RAW / f"matches_{y}.csv"
        if f.exists():
            frames.append(pd.read_csv(f, dtype=str, keep_default_na=False))
    if not frames:
        return 0
    m = pd.concat(frames, ignore_index=True)
    v1 = pd.to_numeric(m["win_average_first_serves_kmh"], errors="coerce")
    v2 = pd.to_numeric(m["los_average_first_serves_kmh"], errors="coerce")
    m = m[(v1 > LC.LO) & (v2 > LC.LO)]
    fr = pd.read_parquet(LC.FROZEN_PANEL, columns=["source", "source_key"])
    known = set(fr.loc[fr["source"].eq("mantennisdata"), "source_key"])
    old = ST.read_all(staging)
    if "mantd_id" in old.columns:
        known |= set(old["mantd_id"].dropna())
    m = m[~m["id"].isin(known)]
    if m.empty:
        return 0
    df = ST.to_frame(ST.mantd_rows(m, collected_on=LC.date_of(day),
                                   retrieved_at=pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                                   source_file=str(MANTD_RAW)))
    ST.add(df, f"mantd_{LC.date_of(day)}", ["mantd_id"], staging)
    return int(len(df))


def collector(day: int, staging: Path, days_back: int, max_requests: int, plan_only: bool) -> dict:
    plan = AD.plan_days(day - days_back, day - 1)
    info = {"enabled": AD.enabled(), "plan_requests": len(plan),
            "plan_events": sorted({f"{y}-{e}" for y, e, _, _ in plan}), "max_requests": max_requests}
    if plan_only:
        info["plan"] = plan[:max_requests]
        return info
    if not AD.enabled():
        info["status"] = "disabled (live/collector.json); no request sent"
        return info
    res = AD.fetch_daily(LC.date_of(day), plan, max_requests=max_requests)
    rounds = {(e, m): r for _, e, m, r in plan}
    df = AD.decrypt_and_stage([Path(f) for f in res["files"]], collected_on=LC.date_of(day), rounds=rounds)
    if len(df):                      # added to the day's earlier rows, never replacing them (staging.add)
        ST.add(df, f"atp_daily_{LC.date_of(day)}", ["year", "event_id", "match_code"], staging)
    info.update({"status": "ran", "files": len(res["files"]), "staged": int(len(df))})
    return info


def run(day: int, out: Path, mantd: str = "auto", network: bool = True, days_back: int = 1,
        max_requests: int = AD.MAX_REQUESTS_FIRST_RUN, plan_only: bool = False) -> dict:
    t0 = time.time()
    staging = out / "staging"
    rec = {"run_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "date": LC.date_of(day)}
    monday = pd.Timestamp(LC.date_of(day)).dayofweek == 0
    if (mantd == "force" or (mantd == "auto" and monday)) and network:
        rec["mantd_refresh"] = mantd_refresh()
    else:
        rec["mantd_refresh"] = "skipped" + ("" if network else " (no network)")
    if plan_only:                                    # no side effect: nothing staged, nothing fetched
        rec["collector"] = collector(day, staging, days_back, max_requests, True)
        return rec
    rec["mantd_staged"] = stage_mantd(day, staging)
    rec["collector"] = (collector(day, staging, days_back, max_requests, False) if network
                        else {"enabled": AD.enabled(), "status": "skipped (no network)"})
    st = ST.read_all(staging)
    linked = LK.link(st) if len(st) else pd.DataFrame()
    out.mkdir(parents=True, exist_ok=True)
    if len(linked):
        linked.to_parquet(out / LC.LINKED.name, index=False)
    rec["linked"] = linked["link_method"].value_counts().to_dict() if len(linked) else {}
    live, summ = LP.build(linked, out=out)
    rec["live_panel"] = summ
    path = FM.write(day, live, out=out)
    f = pd.read_parquet(path)
    rec["form"] = {"file": path.name, "players": int(len(f)), "with_reading_28d": int((f["k28"] > 0).sum()),
                   "latest_reading": f["last_reading"].dropna().max()}
    rec["seconds"] = round(time.time() - t0, 1)
    with (out / LC.RUNS.name).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="the run's day (the form is as of this day)")
    ap.add_argument("--out", type=Path, default=LC.OUT)
    ap.add_argument("--mantd", choices=["auto", "force", "skip"], default="auto")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--days-back", type=int, default=1, help="collector: rounds played on the last N days")
    ap.add_argument("--max-requests", type=int, default=AD.MAX_REQUESTS_FIRST_RUN)
    ap.add_argument("--plan-only", action="store_true", help="print the collector's plan; send nothing")
    a = ap.parse_args(argv)
    rec = run(LC.day_of(a.date), a.out, mantd=a.mantd, network=not a.no_network, days_back=a.days_back,
              max_requests=a.max_requests, plan_only=a.plan_only)
    print(json.dumps(rec, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
