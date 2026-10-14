"""Verify Stage 4's five model inputs computed for new matches only (docs/studies/prediction_pipeline/).

The inputs: elo_games (the games-weighted Elo blend: a sequential pass over all matches, seconds), points_52w
(mu_points over 52 weeks: per-player as-of sums, the layer's translated and weighted spw/rpw counts), sets_14d (per-player
activity sums), age and age_sq (the row's own age). Everything but the Elo pass is per player: a player's sums read only
that player's rows. So the inputs of the new matches are rebuilt by the decided builder's own functions
(stage4_features.state and build) on a subset of the table: every match of the new matches' players (both rows of
each), with the weighted Elo blocks of the whole-table pass. Against the tree's stage4_features.parquet (float32).

Writes data/studies/prediction_pipeline/stage4_state/verify.json. Reads only.
Run: ./python.sh src/eda/prediction_pipeline/verify_stage4_state.py [--d0 2026-09-16]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pp_common as PC  # noqa: E402

OUT = PC.OUT / "stage4_state"
COLS = ["elo_games|single", "mu_points|52 weeks", "sets_14d|single", "age|single", "age|single|2"]
WANT = {"elo_games", "mu_points", "sets_14d", "age"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d0", default=None)
    ap.add_argument("--tree", default=str(PC.TREE))
    a = ap.parse_args()
    PC.use_tree(Path(a.tree))
    PC.set_layer(Path(a.tree))
    from src.eda.predictability_diagnostic import stage4_features as F

    rec = {"tree": a.tree}
    t0 = time.time()
    rows, typical = F.load_rows()
    xd = F.stat_xd(rows)
    pbp = F.pbp_history(rows)
    ctx, _ = F.constants(rows, xd, typical, pbp)
    rec["seconds_load_and_constants"] = round(time.time() - t0, 1)
    t1 = time.time()
    elo_w = F.elo_variants(rows, ctx["elo_scale"])
    rec["seconds_weighted_elo_passes"] = round(time.time() - t1, 1)
    cand = pd.read_csv(F.CANDIDATES)
    pool = F.pool_mask(rows)
    stored = pd.read_parquet(F.FEATURES, columns=["match_id"] + COLS)
    a_rows = rows.iloc[0::2]
    if not np.array_equal(stored["match_id"].to_numpy(), a_rows["match_id"].to_numpy()[pool]):
        raise RuntimeError("the stored Stage 4 features are not in the pool's order")
    day_m = a_rows["day"].to_numpy()
    last = int(day_m[pool].max())
    d0 = int(np.datetime64(a.d0, "D").astype("int64")) if a.d0 else last - 21
    rec["d0"] = str(np.datetime64(d0, "D"))
    new_pool = pool & (day_m > d0)                                   # per match
    rec["new_pool_matches"] = int(new_pool.sum())

    # the subset: every match of the new matches' players (both rows), in the table's order
    t2 = time.time()
    pc = rows["pcode"].to_numpy()
    players = np.unique(np.r_[pc[0::2][new_pool], pc[1::2][new_pool]])
    m_keep = np.isin(pc[0::2], players) | np.isin(pc[1::2], players)
    r_keep = np.repeat(m_keep, 2)
    rows_s = rows[r_keep].reset_index(drop=True)
    xd_s = F.stat_xd(rows_s)
    ctx_s = dict(ctx)
    ctx_s["adjusted_x"] = F.adjusted_x(rows_s, xd_s, ctx)
    elo_s = {}
    for k, v in elo_w.items():
        elo_s[k] = v[m_keep] if isinstance(v, np.ndarray) and len(v) == len(m_keep) else v
    S = F.state(rows_s, ctx_s, xd_s, pbp, elo_s)
    pool_s = F.pool_mask(rows_s)
    feats = F.build(rows_s, ctx_s, S, pool_s, cand, only=WANT)
    rec["seconds_subset"] = round(time.time() - t2, 1)
    rec["subset"] = {"players": int(len(players)), "matches": int(m_keep.sum()), "of_matches": int(len(m_keep))}
    # the new pool matches inside the subset's pool
    ids_s = rows_s.iloc[0::2]["match_id"].to_numpy()[pool_s]
    want_ids = a_rows["match_id"].to_numpy()[new_pool]
    pos = pd.Index(ids_s).get_indexer(want_ids)
    if (pos < 0).any():
        raise RuntimeError("a new match is missing from the subset's pool")
    st = stored.set_index("match_id").loc[want_ids]
    rec["vs_stored_float32"] = {c: PC.compare(np.asarray(feats[c], dtype="float64")[pos].astype("float32"),
                                              st[c].to_numpy()) for c in COLS}
    rec["seconds_total"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    PC.write_json(OUT / "verify.json", rec)
    PC.log(f"{rec['new_pool_matches']} new matches; subset {rec['subset']}; "
           f"{sum(v['bitwise_equal'] == v['rows'] for v in rec['vs_stored_float32'].values())} of {len(COLS)} columns "
           f"bitwise (float32); seconds: {rec['seconds_subset']} subset, {rec['seconds_weighted_elo_passes']} Elo passes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
