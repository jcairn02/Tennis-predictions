"""Refresh the leak-proof timeline and the solved-together inputs after new data arrives (docs/decisions/2026-10-05-
match-timing.md).

Where new matches and their days come from:
    results     Tennis My Life only (src/ingest/public_dump/tennis_my_life.py, then
                src/eda/predictability_diagnostic/stage0_build.py): it dates matches by their event's week
    days        the sources that keep updating, each scraped by its own adapter, which keeps every time field its source
                sends (start, whether a start is only scheduled, finish, venue):
                    tennis-data.co.uk   src/ingest/refresh_odds.py, then predictability_diagnostic/stage1_odds.py
                    WTA API             src/ingest/point_sources/wta.py
                    SofaScore           src/ingest/point_sources/sofascore.py (and _editions, _tournaments)
                    Slam feeds          src/ingest/point_sources/ausopen.py, wimbledon.py, usopen.py
                    TDI                 src/ingest/point_sources/tdi.py
Run those first. This script then re-links the updating sources to Stage 0 (link_sources_c.py), rebuilds the timeline
(timing.py: exact days, calibration, windows) and checks it (timing_check.py), then rebuilds the solved-together (IOS)
inputs on it (rebuild.py --part ios, then --part merge). The frozen sources (the Flashscore export, api-tennis, the
Live Tennis API copy, open tennis data, Infosys, Match Charting, TML days, the point-by-point copy) keep their link
files. A match's id can change at a Stage 0 rebuild when a player's id is corrected (42 did on 6 Oct 2026):
src/eda/data_continuity/rebuild_stage0.py rewrites such ids in the frozen link files and runs this refresh.

Run: ./python.sh src/eda/match_timing/refresh.py [--sources tennis_data,wta_api,sofascore,slam_feeds,tdi] [--skip-ios]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UPDATING = "tennis_data,wta_api,sofascore,slam_feeds,tdi"
HERE = "src/eda/match_timing"


def step(args: list[str]) -> None:
    t0 = time.time()
    print(f"--> {' '.join(args)}", flush=True)
    done = subprocess.run([sys.executable, *args], cwd=ROOT)
    if done.returncode != 0:
        raise SystemExit(f"stopped: {' '.join(args)} exited {done.returncode}")
    print(f"    done in {time.time() - t0:.0f}s", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default=UPDATING, help="sources to re-link (link_sources_c.py names)")
    ap.add_argument("--skip-ios", action="store_true", help="stop after the timeline and its check")
    a = ap.parse_args()
    step([f"{HERE}/link_sources_c.py", "--sources", a.sources])
    step([f"{HERE}/timing.py"])
    step([f"{HERE}/timing_check.py"])
    if not a.skip_ios:
        step([f"{HERE}/rebuild.py", "--part", "ios"])
        step([f"{HERE}/rebuild.py", "--part", "merge"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
