"""Cache the solver's inputs for the surface-IOS study: every player-match of the full history (872,704 matches), as the
leak-proof rebuild builds them (match_timing/rebuild.load_full_rows: the repair's data corrections, the history rule),
with each statistic's centred value on the log-odds scale (stageB_common.stat_arrays: the match's value minus the
tour's average on the match's surface) and the leak-proof timeline (timing.parquet: earliest start, latest finish,
best-estimate day).

Writes data/studies/surface_ios/cache/{atp,wta}.npz (per tour, the rows in the table's order, A then B of each match:
player code, days, event, round, surface code, year, evaluation flags, es/lf/obs and per statistic ok/x/d/y/mu) and
cache/pool.parquet (one row per Stage 4 pool match: match id, tour, surface, and each side's position in its tour's
arrays), plus cache/manifest.json.

Run: ./python.sh src/eda/surface_ios/build_cache.py   (about 2-3 minutes)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import rebuild as RB  # noqa: E402
from src.eda.predictability_diagnostic import common as PC  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402
from src.eda.lower_level_evidence import level_layer_ios as _LLEIOS  # noqa: E402   # level layer, joint solves (LLE_LAYER)


def main() -> int:
    C.CACHE.mkdir(parents=True, exist_ok=True)
    rows, n_matches, _ = RB.load_full_rows()
    means = B.surface_means()
    sa = B.stat_arrays(rows, means, C.STATS)
    timing = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf", "obs"]).set_index("match_id")
    mid = rows["match_id"].to_numpy()
    es = rows["match_id"].map(timing["es"]).to_numpy(dtype="float64")
    lf = rows["match_id"].map(timing["lf"]).to_numpy(dtype="float64")
    obs = rows["match_id"].map(timing["obs"]).to_numpy(dtype="float64")
    if not (np.isfinite(es).all() and np.isfinite(lf).all() and np.isfinite(obs).all()):
        raise ValueError("every match needs es, lf and obs in timing.parquet")
    if np.any(lf < es):
        raise ValueError("an inverted window in timing.parquet")
    surf = rows["surf"].to_numpy().astype("int64")
    pos = np.full(len(rows), -1, dtype=np.int64)
    manifest = {"history_matches": int(n_matches), "player_matches": int(len(rows)), "tours": {},
                "timing_sha256": C.sha256(MT.TIMING), "stats": list(C.STATS)}
    for t in PC.TOURS:
        idx = np.flatnonzero(rows["tour"].to_numpy() == t)
        if len(idx) % 2 or not (mid[idx[0::2]] == mid[idx[1::2]]).all():
            raise ValueError("a tour's rows must come in A, B pairs")
        pos[idx] = np.arange(len(idx))
        pid = pd.factorize(rows["pcode"].to_numpy()[idx])[0].astype(np.int64)
        arrays = {"row": idx.astype(np.int64), "pid": pid, "n_players": np.int64(pid.max() + 1),
                  "day": rows["day"].to_numpy()[idx].astype(np.int64), "ev": rows["ev"].to_numpy()[idx].astype(np.int64),
                  "round_order": rows["round_order"].to_numpy()[idx].astype(np.int64), "surf": surf[idx],
                  "year": rows["year"].to_numpy()[idx].astype(np.int64),
                  "evaluation": rows["evaluation"].to_numpy()[idx].astype(bool),
                  "eval_level": rows["eval_level"].to_numpy()[idx].astype(bool),
                  "level_main": rows["level"].isin(["GS", "FIN", "T1000", "T500", "T250"]).to_numpy()[idx],
                  "es": es[idx], "lf": lf[idx], "obs": obs[idx]}
        for s in C.STATS:
            a = sa[s]
            arrays[f"{s}__ok"] = a["ok"][idx]
            arrays[f"{s}__x"] = a["x"][idx]
            arrays[f"{s}__d"] = a["d"][idx]
            arrays[f"{s}__y"] = a["c"][idx]
            arrays[f"{s}__mu"] = a["mu_scale"][idx]
        arrays = _LLEIOS.annotate_cache(arrays, rows, idx)  # level layer, joint solves (LLE_LAYER)
        np.savez_compressed(C.CACHE / f"{t}.npz", **arrays)
        manifest["tours"][t] = {"rows": int(len(idx)), "players": int(pid.max() + 1),
                                "surface_rows": {C.SURF_NAMES.get(k, "unknown"): int((surf[idx] == k).sum())
                                                 for k in range(0, C.N_SURF + 1)},
                                "box_rows": {s: int(sa[s]["ok"][idx].sum()) for s in C.STATS}}
        C.log(f"{t}: {len(idx):,} rows, {pid.max() + 1:,} players")
    A, Bi = B.pool_rows(rows)
    pool = pd.DataFrame({"match_id": mid[A], "tour": rows["tour"].to_numpy()[A], "surf": surf[A],
                         "year": rows["year"].to_numpy()[A], "pos_a": pos[A], "pos_b": pos[Bi]})
    if (pool[["pos_a", "pos_b"]] < 0).any().any() or not (pool["pos_b"] == pool["pos_a"] + 1).all():
        raise ValueError("pool rows do not map onto the tour arrays")
    pool.to_parquet(C.CACHE / "pool.parquet", index=False)
    manifest["pool_matches"] = int(len(pool))
    C.jdump(manifest, C.CACHE / "manifest.json")
    C.log(f"wrote the cache: {len(pool):,} pool matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
