"""Check the surface solver against the existing leak-proof IOS before using it.

    1. kappa_s = inf (the pooled path) reproduces ios_time.run_timed's O and D on the same inputs;
    2. kappa_s = 1e9 (the surface code path, deviations all but forbidden) reproduces them too;
    3. the pool's A - B differences reproduce the stored leak-proof inputs (match_timing/ios_features.parquet), so the
       cache, the constants and the solver together give the model's current IOS columns.

Run: ./python.sh src/eda/surface_ios/verify_solver.py [tour] [stat]     (default wta second_won, about 3 minutes)
Writes data/studies/surface_ios/verify_solver.json.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402
from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import ios_time as IT  # noqa: E402


def main() -> int:
    tour = sys.argv[1] if len(sys.argv) > 1 else "wta"
    stat = sys.argv[2] if len(sys.argv) > 2 else "second_won"
    chosen, typ = C.ios_constants()
    c = chosen[(tour, stat)]
    td = C.load_tour(tour)
    ty = typ[(stat, tour)]
    td_old = {"pid": td["pid"], "n_players": td["n_players"], "day": td["day"], "ev": td["ev"],
              "round_order": td["round_order"],
              "stats": {stat: {"ok": td["stats"][stat]["ok"], "y": td["stats"][stat]["y"],
                               "d": td["stats"][stat]["d"], "typ": ty}}}
    t0 = time.time()
    ref = IT.run_timed(td_old, stat, c["h"], c["kappa"], c["tau"], td["es"], td["lf"], td["obs"])
    t_ref = time.time() - t0
    t0 = time.time()
    pooled = IS.run(td, stat, c["h"], c["kappa"], np.inf, c["tau"], ty)
    t_pool = time.time() - t0
    t0 = time.time()
    huge = IS.run(td, stat, c["h"], c["kappa"], 1e9, c["tau"], ty)
    t_huge = time.time() - t0

    def gap(a, b):
        m = np.isfinite(a) & np.isfinite(b)
        return {"max_abs": float(np.max(np.abs(a[m] - b[m]))), "rows": int(m.sum()),
                "nan_mismatch": int((np.isfinite(a) != np.isfinite(b)).sum())}
    out = {"tour": tour, "stat": stat, "constants": c,
           "seconds": {"ios_time": round(t_ref, 1), "pooled": round(t_pool, 1), "kappa_s_1e9": round(t_huge, 1)},
           "pooled_vs_ios_time": {"O": gap(pooled["O_eff"], ref["O"]), "D": gap(pooled["D_eff"], ref["D"])},
           "kappa1e9_vs_ios_time": {"O": gap(huge["O_eff"], ref["O"]), "D": gap(huge["D_eff"], ref["D"])},
           "solver": {"ios_time": ref["solver"], "pooled": pooled["solver"], "kappa_s_1e9": huge["solver"]}}
    if stat in C.PROFILE_IOS:
        pool = pd.read_parquet(C.CACHE / "pool.parquet")
        pool = pool[pool["tour"] == tour]
        stored = pd.read_parquet(MT.OUT / "ios_features.parquet",
                                 columns=["match_id", f"ios_O_{stat}|single", f"ios_D_{stat}|single", f"prod_{stat}|single"])
        stored = pool[["match_id", "pos_a", "pos_b"]].merge(stored, on="match_id", how="left", validate="one_to_one")
        a, b = stored["pos_a"].to_numpy(), stored["pos_b"].to_numpy()
        o, d = pooled["O_eff"], pooled["D_eff"]
        out["pool_vs_stored"] = {
            "matches": int(len(stored)),
            "O": gap(o[a] - o[b], stored[f"ios_O_{stat}|single"].to_numpy(dtype=float)),
            "D": gap(d[a] - d[b], stored[f"ios_D_{stat}|single"].to_numpy(dtype=float)),
            "prod": gap(o[a] * (-d[b]) - o[b] * (-d[a]), stored[f"prod_{stat}|single"].to_numpy(dtype=float))}
    C.jdump(out, C.OUT / f"verify_solver_{tour}_{stat}.json")
    print(pd.json_normalize(out, sep=".").T.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
