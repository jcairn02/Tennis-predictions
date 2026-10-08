"""Stage A of "rating systems against Elo", a sensitivity: TrueSkill Through Time with two-week events held back.

The time rule reads a tournament's start date as its week, so the second week of a Grand Slam counts as known once the
start date's week is over. A filtering rating (Elo, Glicko, TrueSkill) cannot pass those later rounds to another
player: a rating moves only with the player's own matches. TrueSkill Through Time re-scores opponents when it smooths,
so it can: a week-two Challenger player's estimate can move because a former opponent went deep at the Slam later that
week. The feature-alpha audit's repairs (2 Oct 2026) removed the same kind of overlap from the features.

This script reruns TTT at Stage A's frozen constants (not retuned) with ratings.ttt_pass's hold: the matches of an
event with a round of 128 (the Grand Slams and the 96-draw 1000s; common.history's "fortnight") join the smoothed model
only at the first date at least 14 days after the event's start date. That also withholds the event's first week, so
the variant is conservative. If TTT's gain over Elo survives it, the overlap is not its source.

Writes data/studies/rating_systems/stageA_ttt_hold.parquet (match_id, p_ttt_hold with Stage A's surface weight,
p_ttt_hold_overall) and stageA_ttt_hold_summary.json (the constants used, how many matches the hold touched, timings).
Run after stageA_ratings.py: ./python.sh src/eda/rating_systems/stageA_ttt_hold.py   (2 worker processes)
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402
from src.eda.rating_systems import ratings as R  # noqa: E402

OUT = RC.OUT
A_SUMMARY = OUT / "stageA_summary.json"
PARQUET = OUT / "stageA_ttt_hold.parquet"
SUMMARY = OUT / "stageA_ttt_hold_summary.json"
T0 = time.time()


def job(spec: dict) -> dict:
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    t0 = time.time()
    m = RC.load_table()
    t = m[m["tour"].eq(spec["tour"])].reset_index(drop=True)
    h = RC.history(t)
    res = R.run(h, "ttt_hold", spec["cfg"])
    fort = np.asarray(h["fortnight"], dtype=bool)
    return {"tour": spec["tour"], "match_id": t["match_id"].to_numpy(), "p": R.blend("ttt_hold", res, spec["w"]),
            "p_overall": R.blend("ttt_hold", res, 0.0), "held_matches": int((fort & np.asarray(h["upd"])).sum()),
            "held_events": int(t.loc[fort, ["tournament_date", "tournament_id"]].drop_duplicates().shape[0]),
            "seconds": round(time.time() - t0, 1)}


def ttt_constants() -> list[dict]:
    """TTT's frozen constants, read as Stage A chooses them: the lowest 2013-2018 log loss in stageA_tuning.csv, then
    the surface weight with the lowest log loss in stageA_surface_weights.csv (both written before Stage A's full
    passes, so this can run beside them)."""
    t = pd.read_csv(OUT / "stageA_tuning.csv")
    w = pd.read_csv(OUT / "stageA_surface_weights.csv")
    specs = []
    for tour in C.TOURS:
        g = t[t["system"].eq("ttt") & t["tour"].eq(tour)]
        best = g.loc[g["log_loss_2013_2018"].idxmin()]
        gw = w[w["system"].eq("ttt") & w["tour"].eq(tour)]
        specs.append({"tour": tour, "cfg": {"sigma0": float(best["sigma0"]), "gamma": float(best["gamma"]),
                                            "window": float(best["window"])},
                      "w": float(gw.loc[gw["log_loss_2013_2018"].idxmin(), "w"])})
    return specs


def main() -> int:
    specs = ttt_constants()
    if A_SUMMARY.exists():                      # when Stage A has finished, its record must agree
        A = json.loads(A_SUMMARY.read_text(encoding="utf-8"))
        for s in specs:
            ch = A["chosen"].get(f"ttt|{s['tour']}")
            if ch:
                assert all(abs(float(ch[k]) - v) < 1e-9 for k, v in s["cfg"].items()) and abs(ch["w"] - s["w"]) < 1e-9, (ch, s)
    with ProcessPoolExecutor(max_workers=2) as ex:
        res = list(ex.map(job, specs))
    out = pd.concat([pd.DataFrame({"match_id": r["match_id"], "p_ttt_hold": r["p"], "p_ttt_hold_overall": r["p_overall"]})
                     for r in res], ignore_index=True)
    RC.write_parquet(out, PARQUET)
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "constants": {s["tour"]: {**s["cfg"], "w": s["w"]} for s in specs},
               "hold": "events with a round of 128 join the smoothed model at the first date >= start date + 14 days",
               "held": {r["tour"]: {"rating_moving_matches": r["held_matches"], "events": r["held_events"],
                                    "seconds": r["seconds"]} for r in res},
               "shared_code": RC.dependency_hashes(), "seconds": round(time.time() - T0, 1)}
    SUMMARY.write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    print(f"wrote {PARQUET.name} ({len(out):,} rows) and {SUMMARY.name} in {summary['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
