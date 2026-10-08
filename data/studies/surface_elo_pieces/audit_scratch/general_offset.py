"""Audit scratch: is the 'surface offset' Elo's gain about SURFACE at all?

The bias table shows the offset D averaging +50 to +77 Elo points for experienced players on EVERY surface (hard and
clay alike), i.e. most of D is a general correction of Stage 1's overall rating, not a surface deviation. Control:
the same pieces.py pass with every known surface mapped to ONE code, so the 'offset' becomes a general offset G moved by
every match (same update rule, its own K re-tuned on the same 2013-2018 evaluation matches and grid). If R + G scores
like R + D, the offset's gain is not evidence for Elo by surface.

Also: D decomposed into the player's general level (mean of their offsets across surfaces) and the surface-specific
remainder; and the evidence-weighted shrinkage of that remainder.

Run: ./python.sh data/studies/surface_elo_pieces/audit_scratch/general_offset.py   (about 10 minutes)
"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.surface_elo_pieces import pieces as P  # noqa: E402

OUT = Path(__file__).resolve().parent
L10 = np.log(10) / 400
ORIGIN = np.datetime64("2010-01-04")
t0 = time.time()


def ll(p, y):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return np.where(np.asarray(y, bool), -np.log(p), -np.log(1 - p))


def gain_ci(lb, lm, dates):
    d = lb - lm
    blk = ((np.asarray(dates, dtype="datetime64[D]") - ORIGIN).astype(int)) // 28
    u, inv = np.unique(blk, return_inverse=True)
    G, n = len(u), len(d)
    s = np.bincount(inv, weights=d - d.mean())
    se = np.sqrt(G / (G - 1) * (s @ s)) / n
    r = student_t.ppf(0.975, G - 1) * se
    return {"n": int(n), "gain": round(1000 * d.mean(), 3), "lo": round(1000 * (d.mean() - r), 3), "hi": round(1000 * (d.mean() + r), 3)}


def slope(x, y):
    lr = LogisticRegression(C=np.inf, fit_intercept=False, max_iter=1000, tol=1e-10)
    lr.fit(np.asarray(x, float).reshape(len(x), -1), np.asarray(y, int))
    return lr.coef_[0]


m = pd.read_parquet(C.STAGE0, columns=P.STAGE0_COLS)
meta = json.loads((C.OUT / "pieces_meta.json").read_text())
pc = pd.read_parquet(C.PIECES).set_index("match_id")
fr = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/frame.parquet", columns=["match_id", "split"]).set_index("match_id")
res = {}
for tour in C.TOURS:
    sel = m["tour"].eq(tour).to_numpy()
    t = m[sel].reset_index(drop=True)
    h = B.history_arrays(t)
    upd = t["status"].isin(B.UPDATES["ret"]).tolist()
    k = {kk: float(meta["stage1_constants"][tour][kk]) for kk in ("k0", "offset", "shape")}
    h1 = {**h, "surf": [0 if s >= 0 else -1 for s in h["surf"]]}          # one 'surface' for every known-surface match
    # tune the general offset on the same rows and grid as pieces.tune_offset
    kd, grid = P.tune_offset(t, h1, upd, k)
    og = P.run(h1, upd, k, "offset", kd)
    y = t["a_won"].to_numpy(bool)
    ev = (t["evaluation"] & t["status"].isin(["completed", "retired"]) & t["surface"].notna()).to_numpy()
    mid = t["match_id"].to_numpy()
    R_a, R_b = og[:, 0], og[:, 1]
    D = pc.loc[mid, ["D_a", "D_b"]].fillna(0).to_numpy()
    w = 0.30 if tour == "atp" else 0.25
    S = pc.loc[mid, ["S_a", "S_b"]].to_numpy()
    S = np.where(np.isnan(S), np.column_stack([R_a, R_b]), S)
    fc = {"stage1_blend": L10 * ((R_a + w * (S[:, 0] - R_a)) - (R_b + w * (S[:, 1] - R_b))),
          "surface_offset": L10 * ((R_a + D[:, 0]) - (R_b + D[:, 1])),
          "general_offset": L10 * ((R_a + og[:, 8]) - (R_b + og[:, 9]))}
    # both: general offset then a surface offset on top is not built here; report the two on the same rows
    yr = t["year"].to_numpy()
    tune = ev & (yr >= 2013) & (yr <= 2018)
    chk = ev & (yr >= 2019) & (yr <= 2021)
    main = fr["split"].reindex(mid).isin(["train", "test"]).to_numpy()
    cal = {kk: slope(v[tune], y[tune])[0] for kk, v in fc.items()}
    base = ll(expit(cal["stage1_blend"] * fc["stage1_blend"]), y)
    out = {"general_offset_constants": kd, "best_tuning_ll_general": min(g["log_loss_2013_2018"] for g in grid if g["kd0"] > 0)}
    for sub, sm in (("all evaluation", chk), ("main tour", chk & main)):
        for kk in ("surface_offset", "general_offset"):
            lv = ll(expit(cal[kk] * fc[kk]), y)
            out[f"{sub}|{kk}_vs_stage1_blend"] = gain_ci(base[sm], lv[sm], t.loc[sm, "tournament_date"].to_numpy())
        ls = ll(expit(cal["surface_offset"] * fc["surface_offset"]), y)
        lg = ll(expit(cal["general_offset"] * fc["general_offset"]), y)
        out[f"{sub}|surface_offset_vs_general_offset"] = gain_ci(lg[sm], ls[sm], t.loc[sm, "tournament_date"].to_numpy())
    # decomposition of D on main-tour design rows: player's mean offset across the surfaces they have (as of each row)
    out["corr_D_vs_general_G_main_design_rows"] = float(np.corrcoef(
        np.r_[D[main & (yr >= 2013) & (yr <= 2021), 0], D[main & (yr >= 2013) & (yr <= 2021), 1]],
        np.r_[og[main & (yr >= 2013) & (yr <= 2021), 8], og[main & (yr >= 2013) & (yr <= 2021), 9]])[0, 1])
    res[tour] = out
    print(tour, json.dumps(out, indent=1), f"{time.time() - t0:.0f}s", flush=True)
(OUT / "general_offset.json").write_text(json.dumps(res, indent=1))
