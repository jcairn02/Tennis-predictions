"""Audit scratch: Stage 1's date-and-round leak probe (probe_by_round) pointed at the two NEW Elo modes of
src/eda/surface_elo_pieces/pieces.py ('anchored', 'offset'), which pieces.py itself never probes (it probes only the
surface-switch quantities and relies on Stage 1's probe of the 'stage1' mode).

Also re-runs the frozen passes and checks that they reproduce pieces.parquet exactly (D and XA columns).
Run: ./python.sh data/studies/surface_elo_pieces/audit_scratch/probe_elo_modes.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.surface_elo_pieces import pieces as P  # noqa: E402

OUT = Path(__file__).resolve().parent
t0 = time.time()
m = pd.read_parquet(C.STAGE0, columns=P.STAGE0_COLS)
meta = json.loads((C.OUT / "pieces_meta.json").read_text())
pieces = pd.read_parquet(C.PIECES, columns=["match_id", "D_a", "D_b", "XA_a", "XA_b"]).set_index("match_id")
res = {}
for tour in C.TOURS:
    sel = m["tour"].eq(tour).to_numpy()
    t = m[sel].reset_index(drop=True)
    h = B.history_arrays(t)
    upd = t["status"].isin(B.UPDATES["ret"]).tolist()
    k = {kk: float(meta["stage1_constants"][tour][kk]) for kk in ("k0", "offset", "shape")}
    kd = meta["offset_constants"][tour]
    for mode, extra in (("offset", kd), ("anchored", {})):
        def ratings(hh, mode=mode, extra=extra):
            return P.elo_pass_ext(hh["week"], hh["event"], hh["rnd"], hh["a"], hh["b"], hh["a_won"], hh["surf"], upd,
                                  hh["n_players"], k["k0"], k["offset"], k["shape"], mode=mode, **extra)
        full = ratings(h)
        ref = pieces.loc[t["match_id"], ["D_a", "D_b"] if mode == "offset" else ["XA_a", "XA_b"]].to_numpy()
        repro = float(np.nanmax(np.abs(full[:, 8:10] - ref)))
        same_nan = bool((np.isnan(full[:, 8:10]) == np.isnan(ref)).all())
        # Stage 1's probe: flips results at random in everything not earlier than the cut under the Brief's rule and
        # checks the pre-match values of every match of earlier weeks and the cut event's rounds up to the cut's round
        pr = B.probe_by_round(h, ratings, n_cuts=8, seed=777, from_quantile=0.80)
        res[f"{tour}_{mode}"] = {"reproduces_pieces_max_abs_diff": repro, "same_missing": same_nan, "probe": pr}
        print(tour, mode, res[f"{tour}_{mode}"], f"{time.time() - t0:.0f}s", flush=True)
(OUT / "probe_elo_modes.json").write_text(json.dumps(res, indent=1))
