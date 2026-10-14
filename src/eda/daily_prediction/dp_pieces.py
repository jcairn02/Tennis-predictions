"""The Elo pieces' six model inputs (surface_elo_pieces: pieces.py, arms.new_inputs) for chosen matches.

elo_overall and elo_surf_offset come from the offset pass (dp_elo, R and D of the match); surf_season and surf_layoff
from the per-player surface-switch quantities (pieces.surface_switch: this season's earlier played matches on the
surface, days since the last one on the timeline's best-estimate days). Those are as-of sums and a previous-row lookup
per player; computed here on the whole table with the decided functions (a few seconds), so they are the full build's
values by construction.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _mods():
    from src.eda.predictability_diagnostic import stage1_baselines as B
    from src.eda.surface_elo_pieces import arms as A
    from src.eda.surface_elo_pieces import common as C
    from src.eda.surface_elo_pieces import pieces as PI
    return B, A, C, PI


def stage0() -> tuple[pd.DataFrame, np.ndarray]:
    """Stage 0's matches (pieces.STAGE0_COLS) in Stage 0's order and each match's best-estimate day (pieces.main)."""
    _, _, C, PI = _mods()
    m = pd.read_parquet(C.STAGE0, columns=PI.STAGE0_COLS)
    if not (np.diff(m["order"].to_numpy()) > 0).all():
        raise RuntimeError("Stage 0 must be in its chronological order")
    tm = pd.read_parquet(C.TIMING, columns=["match_id", "obs"]).set_index("match_id").reindex(m["match_id"])
    obs = tm["obs"].to_numpy(dtype="float64")
    if not np.isfinite(obs).all():
        raise RuntimeError("every match needs its best-estimate day in the timeline")
    return m, obs


def switch(m: pd.DataFrame, obs: np.ndarray, p_overall: np.ndarray) -> pd.DataFrame:
    """season_n, days_since, prev_n, prev_res for A and B of every match (pieces.main's columns)."""
    _, _, _, PI = _mods()
    rows = PI.player_rows(m, obs, p_overall)
    sw = PI.surface_switch(rows)
    out = pd.DataFrame({"match_id": m["match_id"].astype(str).to_numpy()})
    for c in sw.columns:
        v = sw[c].to_numpy()
        out[f"{c}_a"], out[f"{c}_b"] = v[0::2], v[1::2]
    return out


def inputs(offset: pd.DataFrame, sw: pd.DataFrame, target_ids) -> dict:
    """The six inputs of the target matches: offset holds R/N/S/NS/D for A and B by match id (the offset pass), sw the
    surface-switch columns by match id."""
    _, A, _, _ = _mods()
    ids = pd.Index(np.asarray(target_ids).astype(str))
    q = offset.set_index("match_id").reindex(ids).join(sw.set_index("match_id").reindex(ids))
    if q[["R_a", "R_b"]].isna().any().any():
        raise RuntimeError("a target match has no offset-pass ratings")
    new = A.new_inputs(q.reset_index(drop=True))
    names = ["elo_overall", "elo_surf_offset", "surf_season_a", "surf_season_b", "surf_layoff_a", "surf_layoff_b"]
    return {n: new[n].to_numpy(dtype="float64") for n in names}
