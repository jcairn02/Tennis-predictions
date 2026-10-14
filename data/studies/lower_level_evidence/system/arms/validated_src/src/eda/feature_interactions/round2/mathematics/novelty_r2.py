"""Round 2, mathematics: result-free novelty (OLS R^2 on the 58 inputs, 2013-2021 training rows, per tour) and residual
SD of the columns proposed in rebuttal_mathematics.md: z_spw (the long-memory surface serve-point IOS composed through
the iid model with the scheduled best-of; the I-008 fix and K1), the later-round price slope (L1) and the surface-level
leverage slope (L2). No result is read. Run: ./python.sh src/eda/feature_interactions/round2/mathematics/novelty_r2.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
_s = importlib.util.spec_from_file_location("mc", ROOT / "src/eda/feature_interactions/round0/mathematics/markov_composition.py")
M = importlib.util.module_from_spec(_s)
_s.loader.exec_module(M)
OUT = ROOT / "data/studies/feature_interactions/round2/mathematics"


def ols_r2(X: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    X1 = np.column_stack([np.ones(len(y)), X])
    b = np.linalg.lstsq(X1, y, rcond=None)[0]
    e = y - X1 @ b
    return float(1 - e.var() / y.var()), float(e.std())


def main() -> int:
    fr = pd.read_parquet(M.MODEL_FRAME)
    fr = fr[fr.season <= 2021].reset_index(drop=True)
    ins = [c for c in fr.columns if c.startswith("in_")]
    sf = pd.read_parquet(M.SURFACE_FEATURES, columns=["match_id"] + [f"srf_{k}_eff_spw_{s}" for k in "OD" for s in "ab"])
    f = fr.merge(sf, on="match_id", how="left")
    mu = M.mu_rows(f, "spw", M.surface_means())
    xa = mu + f.srf_O_eff_spw_a - f.srf_D_eff_spw_b
    xb = mu + f.srf_O_eff_spw_b - f.srf_D_eff_spw_a
    bo = f.in_best_of.to_numpy()
    z_spw = np.full(len(f), np.nan)
    for b in (3, 5):
        s = (bo == b) & np.isfinite(xa + xb)
        z_spw[s] = M.L(expit(xa[s]), expit(xb[s]), b)
    # L2: surface-level leverage modulation kappa_surface = beta_L(mu_surface) / beta_L(tour mean) - 1, times the price
    mu_tour = {"atp": 0.4888, "wta": 0.2414}
    kap = np.full(len(f), np.nan)
    for t in ("atp", "wta"):
        for b in (3, 5):
            s = (f.tour == t).to_numpy() & (bo == b)
            if s.any():
                kap[s] = M.lev_logit(mu[s], b) / float(M.lev_logit(mu_tour[t], b)) - 1
    z = f.in_odds_logit.to_numpy()
    rnd = f.in_round.to_numpy(float)
    out = {}
    for t in ("atp", "wta"):
        m = (f.tour == t).to_numpy() & np.isfinite(z_spw) & np.isfinite(z)
        X = np.nan_to_num(f.loc[m, ins].to_numpy(float), nan=0.0)
        X = X[:, X.std(axis=0) > 0]
        depth = (rnd[m] - np.nanmean(rnd[m])) / np.nanstd(rnd[m])
        cols = {"z_spw": z_spw[m], "L1_round_depth_x_z": depth * z[m], "L2_kappa_surface_x_z": kap[m] * z[m]}
        r = {}
        for nm, y in cols.items():
            r2, sd = ols_r2(X, y)
            r[nm] = {"r2_on_58": r2, "resid_sd": sd, "sd": float(np.std(y))}
        r["corr_z_spw_ratings_iid"] = float(np.corrcoef(z_spw[m], f.loc[m, "in_ratings_iid"])[0, 1])
        r["rms_kappa_surface"] = float(np.sqrt(np.nanmean(kap[m] ** 2)))
        out[t] = r
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "novelty_r2.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
