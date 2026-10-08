"""Refresh the odds branch to today in one command: tennis-data.co.uk, Polymarket (new events, results of
events captured while open, prices, trades), Betfair historical files when an account token is set, and the
sharp-benchmark study.

Steps, in order. Each is resumable and fetches only what is missing or was captured before its market closed;
a failed step is reported and the rest still run, so running the command again picks up where it stopped.
    tennis_data   tennis-data.co.uk workbooks of last season and this one, downloaded again (a changed
                  workbook's old bytes are kept under data/raw/public_dump/tennis_data_couk/superseded/)
    catalog       Polymarket tennis events listed since the last run
    settle        Polymarket events whose match-winner markets were still open when captured, fetched again
                  for their results, close times and listed starts
    prices        minute price history of markets whose match day has passed, and again for any whose stored
                  history ended before the market closed
    trades        every fill of markets whose match day has passed, and again for any fetched before they closed
    betfair       Betfair historical tick files held by the account in BETFAIR_SSOID; skipped, with the steps
                  to get access, when it is not set (src/ingest/betfair_history.py)
    study         src/eda/sharp_benchmark/build.py and evaluate.py
    map           data/data_map.html, only with --map

Usage:
    ./python.sh -m src.ingest.refresh_odds
    ./python.sh -m src.ingest.refresh_odds --skip tennis_data,betfair --map
    ./python.sh -m src.ingest.refresh_odds --only settle,prices,trades
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEPS = ("tennis_data", "catalog", "settle", "prices", "trades", "betfair", "study", "map")
DEFAULT_OFF = {"map"}
BETFAIR_HELP = ("BETFAIR_SSOID is not set, so Betfair's tick data was not fetched. To get it: log in at "
                "https://historicdata.betfair.com, add Tennis with the BASIC plan (free) for 1 Jan 2025 to today and "
                "check out, then set BETFAIR_SSOID to the session token and run this again (see "
                "src/ingest/betfair_history.py).")


def commands(step: str, now: dt.datetime) -> list[list[str]]:
    """The command lines a step runs, with this interpreter."""
    py = sys.executable
    year = now.year
    return {
        "tennis_data": [[py, "-m", "src.ingest.public_dump.tennis_data_couk", "--start-year", str(year - 1),
                         "--end-year", str(year), "--refresh"]],
        "catalog": [[py, "-m", "src.ingest.public_dump.polymarket_catalog"]],
        "settle": [[py, "-m", "src.ingest.public_dump.polymarket_catalog", "--revisit"]],
        "prices": [[py, "-m", "src.ingest.public_dump.polymarket_prices", "--buckets", "all", "--workers", "10",
                    "--rps", "8"]],
        "trades": [[py, "-m", "src.ingest.public_dump.polymarket_trades", "--buckets", "all", "--cutoff",
                    now.isoformat(timespec="seconds"), "--workers", "6", "--rps", "12"]],
        "betfair": [[py, "-m", "src.ingest.betfair_history", "--plan", os.environ.get("BETFAIR_PLAN", "basic"),
                     "--from", "2025-01-01", "--to", now.date().isoformat()]],
        "study": [[py, "src/eda/sharp_benchmark/build.py"], [py, "src/eda/sharp_benchmark/evaluate.py"]],
        "map": [[py, "src/eda/data_map/build.py"]],
    }[step]


def tennis_data_fetched(since: str, years: range) -> bool:
    """The tennis-data adapter exits 1 if any receipt it ever wrote ended in an error, including out-of-scope
    seasons of earlier runs (ATP 2002, 2004 and 2006 since 22 Sep 2026). The step counts as done when every
    season asked for was fetched in this run without one."""
    sys.path.insert(0, str(ROOT))
    from src.ingest.public_dump import common as C
    receipts = C.Receipts("tennis_data_couk")
    wanted = [receipts.get(f"{tour}/{year}") or {} for tour in ("atp", "wta") for year in years]
    return all(not r.get("error") and (r.get("retrieved_at") or "") >= since for r in wanted)


def plan(only: str = "", skip: str = "", with_map: bool = False) -> list[str]:
    chosen = [s.strip() for s in only.split(",") if s.strip()] or [s for s in STEPS if s not in DEFAULT_OFF or with_map]
    if with_map and "map" not in chosen:
        chosen.append("map")
    unknown = set(chosen) | {s.strip() for s in skip.split(",") if s.strip()}
    if unknown - set(STEPS):
        raise SystemExit(f"unknown step(s) {sorted(unknown - set(STEPS))}; choose from {', '.join(STEPS)}")
    dropped = {s.strip() for s in skip.split(",") if s.strip()}
    return [s for s in STEPS if s in chosen and s not in dropped]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help=f"comma list of steps to run ({', '.join(STEPS)})")
    ap.add_argument("--skip", default="", help="comma list of steps to leave out")
    ap.add_argument("--map", action="store_true", help="also rebuild data/data_map.html")
    args = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    results = []
    for step in plan(args.only, args.skip, args.map):
        if step == "betfair" and not os.environ.get("BETFAIR_SSOID"):
            print(f"\n=== betfair: skipped. {BETFAIR_HELP}", flush=True)
            results.append((step, "skipped (no BETFAIR_SSOID)", 0.0))
            continue
        started = time.time()
        since = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        status = "ok"
        for command in commands(step, now):
            print(f"\n=== {step}: {' '.join(command[1:])}", flush=True)
            if subprocess.run(command, cwd=ROOT).returncode != 0:
                if step == "tennis_data" and tennis_data_fetched(since, range(now.year - 1, now.year + 1)):
                    status = "ok (old errors in receipts)"
                    continue
                status = "FAILED"
                break
        results.append((step, status, time.time() - started))
    print("\n=== refresh summary (" + now.isoformat() + ")")
    for step, status, seconds in results:
        print(f"  {step:<12} {status:<26} {seconds / 60:5.1f} min")
    return 1 if any(status == "FAILED" for _, status, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
