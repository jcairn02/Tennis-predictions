"""Step 6: stage 2's speed column (spd_L_B, spd_L_D) for the study's men's qualifying matches.

The instance's stage-2 column (stage2_speed_columns.parquet) holds its frame's matches only. The same builder
(in_season_retrain/speed_extend.build: the decided augmented speed history plus the live panel, the release rules and
the 28-day memory) runs here on keys made the way speed_extend.instance_keys makes them (Stage 0's players, event and
round, the match clock's es / lf / obs, the tournament date), from the build tree's Stage 0 and clock.

The check: the same call on the keys of 2,000 of the instance's men's main-draw matches (2019-2025, a fixed draw) must
give the instance's own column values (to 1e-9). A men's qualifying match the builder cannot fill gets 0 at scoring time
(the "zero" rule of the harm checks); women's rows are 0. Reads no result.

Writes data/studies/qualifying_targets/speed.parquet (match_id, spd_L_B, spd_L_D) and speed.json.
Run: ./python.sh src/eda/qualifying_targets/speed.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.in_season_retrain import speed_extend as SX  # noqa: E402
from src.eda.qualifying_targets import common as C  # noqa: E402

CHECK_N = 2000


def keys_for(f: pd.DataFrame) -> pd.DataFrame:
    """speed_extend.instance_keys' columns for the matches of f (match_id, tour, season, tournament_date, a_won)."""
    from src.eda.serve_speed_tabpfn import panel as P
    k = f.copy()
    k["match_id"] = k["match_id"].astype(str)
    s0 = pd.read_parquet(C.TREE_STAGE0, columns=["match_id", "player_a_id", "player_b_id", "tournament_id",
                                                 "round_order", "level", "a_won"])
    s0["match_id"] = s0["match_id"].astype(str)
    k = k.merge(s0, on="match_id", how="left", suffixes=("", "_s0"), validate="one_to_one")
    if k["player_a_id"].isna().any():
        raise SystemExit("matches missing from the tree's Stage 0")
    if not (k["a_won"].astype(int) == k["a_won_s0"].astype(int)).all():
        raise SystemExit("side A differs from Stage 0's")
    tm = pd.read_parquet(C.TREE_TIMING, columns=["match_id", "es", "lf", "obs"])
    tm["match_id"] = tm["match_id"].astype(str)
    k = k.merge(tm, on="match_id", how="left", validate="one_to_one")
    if k[["es", "lf", "obs"]].isna().any().any():
        raise SystemExit("matches without a clock row")
    k["rebuilt_id"] = k["match_id"]
    k["obs_raw"] = k["obs"].astype(float)
    k["obs"] = np.floor(k["obs_raw"]).astype("int64")
    k["es"], k["lf"] = k["es"].astype("int64"), k["lf"].astype("int64")
    k["tdate"] = P.days(k["tournament_date"])
    k["round_order"] = k["round_order"].astype("int64")
    k["id_conflict"], k["flipped"] = False, False
    k["a_rebuilt"], k["b_rebuilt"] = k["player_a_id"], k["player_b_id"]
    return k[["match_id", "rebuilt_id", "tour", "season", "player_a_id", "player_b_id", "es", "lf", "obs", "obs_raw",
              "tdate", "tournament_id", "round_order", "level", "id_conflict", "flipped", "a_rebuilt",
              "b_rebuilt"]].reset_index(drop=True)


def main() -> int:
    t0 = time.time()
    q = pd.read_parquet(C.FRAME, columns=["match_id", "tour", "season", "tournament_date", "a_won"])
    q = q[q["tour"] == "atp"].reset_index(drop=True)
    inst = pd.read_parquet(C.INSTANCE / "model_frame.parquet",
                           columns=["match_id", "tour", "season", "tournament_date", "a_won"])
    inst = inst[(inst["tour"] == "atp") & inst["season"].between(2019, 2025)]
    chk = inst.sample(CHECK_N, random_state=20261022).reset_index(drop=True)
    keys = keys_for(pd.concat([q, chk], ignore_index=True))
    got, info = SX.build(keys)
    got["match_id"] = got["match_id"].astype(str)
    col = pd.read_parquet(C.INSTANCE / "stage2_speed_columns.parquet")
    col["match_id"] = col["match_id"].astype(str)
    g = got.set_index("match_id").loc[chk["match_id"].astype(str)]
    c = col.set_index("match_id").loc[chk["match_id"].astype(str)]
    check = {}
    for s in ("B", "D"):
        d = np.abs(g[f"spd_L_{s}"].to_numpy(float) - c[f"spd_L_{s}"].to_numpy(float))
        check[s] = {"compared": int(len(d)), "equal_1e-9": int((d <= 1e-9).sum()), "max_abs_diff": float(np.nanmax(d)),
                    "nan_either": int(np.isnan(d).sum())}
    passed = all(v["equal_1e-9"] == v["compared"] for v in check.values())
    out = got[got["match_id"].isin(set(q["match_id"]))].reset_index(drop=True)
    out.to_parquet(C.OUT / "speed.parquet", index=False)
    rec = {"men_qualifying": int(len(q)), "filled_B": int(np.isfinite(out["spd_L_B"]).sum()),
           "nonzero_B": int((np.nan_to_num(out["spd_L_B"].to_numpy(float)) != 0).sum()),
           "check_on_main_draw": check, "check_passed": passed, "builder": info,
           "seconds": round(time.time() - t0, 1)}
    C.write_json(C.OUT / "speed.json", rec)
    C.log(f"speed: {rec}")
    return 0 if passed else 5


if __name__ == "__main__":
    sys.exit(main())
