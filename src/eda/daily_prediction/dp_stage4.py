"""Stage 4's six model inputs for chosen matches (PLAN.md section 3.3: "none needed: recomputed for the day's players").

ratings_iid (rating_matchup), elo_games, points_52w (mu_points over 52 weeks), sets_14d, age and age_sq. Apart from the
games-weighted Elo (a pass over every match: dp_elo, its blocks handed in) and Stage 3's ratings (each match's own row,
in stage3_ratings.parquet), each is a per-player as-of sum: a player's value reads only that player's rows. So the
decided builder's own functions (stage4_features.state and build) run on a subset of the table, every match of the
chosen matches' players (both rows of each), with the whole table's constants: the plan's prototype check
(prediction_pipeline/verify_stage4_state.py: bitwise on five of these inputs, float32), here with rating_matchup too.
pandas' grouped sums are compensated (Kahan), so a resumed running total would not be exact; per-player recomputation
is (the plan's process log, 19:20).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WANT = {"elo_games", "mu_points", "sets_14d", "age", "rating_matchup"}
COLUMNS = {"ratings_iid": "rating_matchup|single", "elo_games": "elo_games|single", "points_52w": "mu_points|52 weeks",
           "sets_14d": "sets_14d|single", "age": "age|single", "age_sq": "age|single|2"}


def _F():
    from src.eda.predictability_diagnostic import stage4_features as F
    return F


def load():
    """Stage 4's rows (also Stage B's), their statistics, the point-by-point history and the constants, as
    stage4_features.main computes them."""
    F = _F()
    rows, typical = F.load_rows()
    xd = F.stat_xd(rows)
    pbp = F.pbp_history(rows)
    ctx, consts = F.constants(rows, xd, typical, pbp)
    return rows, typical, xd, pbp, ctx, consts


def inputs_for(rows: pd.DataFrame, ctx: dict, pbp: pd.DataFrame, target_ids, elo_w: dict) -> tuple[dict, dict]:
    """The six inputs (float64 as computed; the builder stores float32) of the target matches, in target order.
    elo_w: elo_variants' dict (blocks over every match of rows, side A order). Returns (inputs, record)."""
    import time
    F = _F()
    t0 = time.time()
    target_ids = np.asarray(target_ids).astype(str)
    pc = rows["pcode"].to_numpy()
    mids = rows["match_id"].to_numpy()[0::2].astype(str)
    tsel = np.isin(mids, target_ids)
    players = np.unique(np.r_[pc[0::2][tsel], pc[1::2][tsel]])
    m_keep = np.isin(pc[0::2], players) | np.isin(pc[1::2], players)
    rows_s = rows[np.repeat(m_keep, 2)].reset_index(drop=True)
    xd_s = F.stat_xd(rows_s)
    ctx_s = dict(ctx)
    ctx_s["adjusted_x"] = F.adjusted_x(rows_s, xd_s, ctx)
    elo_s = {k: (v[m_keep] if isinstance(v, np.ndarray) and len(v) == len(m_keep) else v) for k, v in elo_w.items()}
    S = F.state(rows_s, ctx_s, xd_s, pbp, elo_s)
    pool_s = F.pool_mask(rows_s)
    feats = F.build(rows_s, ctx_s, S, pool_s, pd.read_csv(F.CANDIDATES), only=WANT)
    ids_s = rows_s.iloc[0::2]["match_id"].to_numpy()[pool_s].astype(str)
    pos = pd.Index(ids_s).get_indexer(target_ids)
    if (pos < 0).any():
        raise RuntimeError(f"{int((pos < 0).sum())} target matches are not in Stage 4's pool")
    out = {name: np.asarray(feats[col], dtype="float64")[pos] for name, col in COLUMNS.items()}
    return out, {"players": int(len(players)), "subset_matches": int(m_keep.sum()), "seconds": round(time.time() - t0, 1)}


def elo_blocks(rows: pd.DataFrame, per_tour: dict, consts: dict) -> dict:
    """elo_variants' dict over every match of rows from per-tour weighted-pass outputs: per_tour[(kind, tour)] =
    (side-A positions of the tour's matches, block rows for them); rows not given stay NaN."""
    n = len(rows) // 2
    out = {}
    for kind in ("games", "points"):
        block = np.full((n, 8), np.nan)
        for tour in ("atp", "wta"):
            got = per_tour.get((kind, tour))
            if got is not None:
                idx, vals = got
                block[idx] = vals
            out[(kind, tour, "w")] = consts["stage1"][tour]["w"]
        out[kind] = block
    return out
