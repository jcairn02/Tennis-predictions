"""Running the surface-offset TTT on the real history: the frozen overall constants, the history with its leak-proof
days, and one pass.

History: the rating-systems study's (every singles match of Stage 0 from 2010, every level, per tour, in the table's
order; walkovers and "other" never move ratings, retirements do), with each match's earliest possible start (es) and
latest possible finish (lf) from data/studies/match_timing/timing.parquet, exactly as match_timing/ttt_timed.py runs the
decided TTT. Overall constants: the decided TTT's (sigma0, gamma, the smoothing span in days), read from
ttt_timed_summary.json, never retuned here.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from src.eda.rating_systems import common as RC
from src.eda.surface_rating_race import common as C
from src.eda.surface_rating_race import ttt_offset as TO

TTT_SUMMARY = C.ROOT / "data" / "studies" / "match_timing" / "ttt_timed_summary.json"


def frozen_constants() -> dict:
    """Per tour: sigma0, gamma, window_days (and the blend weight w of the decided TTT, for reference)."""
    s = json.loads(TTT_SUMMARY.read_text())
    return {t: {"sigma0": float(s["constants"][t]["sigma0"]), "gamma": float(s["constants"][t]["gamma"]),
                "window_days": float(s["window_days"][t]), "w_blend": float(s["constants"][t]["w"])}
            for t in C.TOURS}


def load_history(tour: str, last_year: int | None = None) -> tuple[pd.DataFrame, dict]:
    m = RC.load_table(last_year)
    t = m[m["tour"].eq(tour)].reset_index(drop=True)
    h = RC.history(t)
    tm = pd.read_parquet(C.TIMING, columns=["match_id", "es", "lf"]).set_index("match_id")
    es, lf = t["match_id"].map(tm["es"]), t["match_id"].map(tm["lf"])
    if es.isna().any() or lf.isna().any() or (lf < es).any():
        raise ValueError("every match needs a window that does not end before it starts")
    h["es"], h["lf"] = es.astype(int).tolist(), lf.astype(int).tolist()
    return t, h


def run_pass(h: dict, cfg: dict, offsets: bool = True) -> pd.DataFrame:
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    out = TO.ttt_offset_pass_timed(h["es"], h["lf"], h["event"], h["rnd"], h["a"], h["b"], h["surf"], h["a_won"],
                                   h["upd"], h["n_players"], sigma0=cfg["sigma0"], gamma=cfg["gamma"],
                                   sigma_o=cfg.get("sigma_o", 1.0), gamma_o=cfg.get("gamma_o", 0.0),
                                   window_days=cfg["window_days"], offsets=offsets)
    return TO.frame_of(out)
