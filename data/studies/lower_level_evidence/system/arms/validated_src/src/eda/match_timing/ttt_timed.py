"""TrueSkill Through Time on the leak-proof timeline, against Elo and against the original TTT (the match-timing study).

The rating-systems study's TTT (ratings.ttt_pass, the owner's leading rating candidate of 3 Oct 2026) adds each
tournament date's matches as one batch once the date changes, and its smoothing passes every result to every player: a
Grand Slam's second week, or any event still running under an earlier start date, reaches matches played before it.
Its hold variant (stageA_ttt_hold.py) withholds only events with a round of 128.

This script reruns TTT at the study's frozen constants (Stage A's choice; not retuned) with ratings.ttt_pass_timed on
data/studies/match_timing/timing.parquet: each result joins the model the day after its latest possible finish, each
match reads it as of its earliest possible start. The smoothing span is the original's: the median number of days the
original ``window`` of tournament-date batches covered on each tour. Then every forecast is scored as the study scores
them (summary_results.py): on the study's evaluation matches, log loss against Stage 1's surface Elo, positive = better
than Elo, with 95% intervals clustered in four-week blocks.

Writes data/studies/match_timing/ttt_timed.parquet (match_id, p_ttt_timed, p_ttt_timed_overall), ttt_timed_results.csv
and ttt_timed_summary.json.
Run: ./python.sh src/eda/match_timing/ttt_timed.py     (2 worker processes; the men's pass is the long one)
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

from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402
from src.eda.rating_systems import ratings as R  # noqa: E402
from src.eda.rating_systems.stageA_ttt_hold import ttt_constants  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

WINDOWS = {"2013-2018 (tuning)": (2013, 2018), "2019-2026": (2019, 2026), "2022-2026": (2022, 2026)}


def window_days(week: list, window: int) -> float:
    """The days the original's trailing ``window`` tournament-date batches spanned: the median, over every date, of the
    gap to the date ``window`` batches earlier."""
    d = np.unique(np.asarray(week, dtype=np.int64))
    return float(np.median(d[window:] - d[:-window])) if len(d) > window else float(7 * window)


def job(spec: dict) -> dict:
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    t0 = time.time()
    m = RC.load_table()
    t = m[m["tour"].eq(spec["tour"])].reset_index(drop=True)
    h = RC.history(t)
    tm = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf"]).set_index("match_id")
    es = t["match_id"].map(tm["es"])
    lf = t["match_id"].map(tm["lf"])
    if es.isna().any() or lf.isna().any() or (lf < es).any():
        raise ValueError("every match needs a window that does not end before it starts")
    h["es"], h["lf"] = es.astype(int).tolist(), lf.astype(int).tolist()
    cfg = dict(spec["cfg"], window_days=window_days(h["week"], int(spec["cfg"]["window"])))
    res = R.run(h, "ttt_timed", cfg)
    return {"tour": spec["tour"], "match_id": t["match_id"].to_numpy(), "p": R.blend("ttt_timed", res, spec["w"]),
            "p_overall": R.blend("ttt_timed", res, 0.0), "window_days": cfg["window_days"],
            "seconds": round(time.time() - t0, 1)}


def score(p: pd.DataFrame) -> pd.DataFrame:
    f = pd.read_parquet(RC.OUT / "stageB_features.parquet",
                        columns=["match_id", "tour", "year", "evaluation", "a_won", "p_elo", "p_ttt", "p_ttt_hold"])
    f = f.merge(p, on="match_id", how="left", validate="one_to_one")
    m = RC.C.load_matches(["match_id", "tournament_date"]).set_index("match_id")
    f["tournament_date"] = m.reindex(f["match_id"])["tournament_date"].to_numpy()
    y = f["a_won"].to_numpy(dtype=bool)
    rows = []
    for tour in RC.C.TOURS:
        for label, (a, b) in WINDOWS.items():
            sel = ((f["tour"] == tour) & f["evaluation"].astype(bool) & f["year"].between(a, b)).to_numpy()
            g = f[sel]
            yy = y[sel]
            ll = {k: T.ll(np.nan_to_num(g[f"p_{k}"].to_numpy(dtype="float64"), nan=0.5), yy)
                  for k in ("elo", "ttt", "ttt_hold", "ttt_timed")}
            for base, model in (("elo", "ttt"), ("elo", "ttt_hold"), ("elo", "ttt_timed"), ("ttt", "ttt_timed")):
                c = T.compare(ll[base], ll[model], g["tournament_date"].to_numpy())
                rows.append({"tour": tour, "window": label, "base": base, "model": model, "matches": c["n"],
                             "gain": c["gain"], "lo": c["lo"], "hi": c["hi"],
                             "log_loss_model": float(ll[model].mean())})
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.time()
    specs = ttt_constants()
    with ProcessPoolExecutor(max_workers=2) as ex:
        res = list(ex.map(job, specs))
    p = pd.concat([pd.DataFrame({"match_id": r["match_id"], "p_ttt_timed": r["p"], "p_ttt_timed_overall": r["p_overall"]})
                   for r in res], ignore_index=True)
    p.to_parquet(MT.OUT / "ttt_timed.parquet", index=False, compression="zstd")
    S = score(p)
    S.to_csv(MT.OUT / "ttt_timed_results.csv", index=False)
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "constants": {s["tour"]: {**s["cfg"], "w": s["w"]} for s in specs},
               "window_days": {r["tour"]: r["window_days"] for r in res},
               "seconds": {r["tour"]: r["seconds"] for r in res}, "timing_sha256": MT.sha256(MT.TIMING),
               "key": "milli-log-loss; positive = the model (second named) has the lower log loss than the base; a "
                      "95% interval spanning 0 is a tie", "results": S.to_dict("records")}
    MT.jdump(summary, MT.OUT / "ttt_timed_summary.json")
    with pd.option_context("display.width", 200):
        print(S.round(3).to_string(index=False))
    MT.log(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
