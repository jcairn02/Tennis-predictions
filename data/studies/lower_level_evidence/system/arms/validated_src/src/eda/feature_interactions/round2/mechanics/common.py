"""Round 2, brainstormer MECHANICS: shared loading for the result-free rebuttal checks.

Seasons <= 2021 only, read with a parquet filter so that no later season is ever loaded; `a_won` is never selected.
The price enters only as `in_odds_logit` (one of the 58 inputs), as a regressand against pre-match features.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage2_iid as I  # noqa: E402  (read-only import)

MF = ROOT / "data/studies/surface_rating_race/model/model_frame.parquet"
SF = ROOT / "data/studies/surface_ios/surface_features.parquet"
CONST = ROOT / "data/studies/predictability_diagnostic/stage4_constants.csv"
LEV = ROOT / "data/studies/feature_interactions/round0/mechanics/iid_mechanics.json"
OUT = ROOT / "data/studies/feature_interactions/round2/mechanics"
S = ["spw", "ace", "first_in", "first_won", "second_won"]
SURF = {0.0: "Hard", 1.0: "Clay", 2.0: "Grass"}
LAST = 2021


def sig(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))


def logit(p):
    p = np.asarray(p, dtype=float)
    return np.log(p / (1 - p))


def load():
    names = ["in_" + d["name"] for d in json.loads((MF.parent / "model_inputs.json").read_text())["inputs"]]
    assert len(names) == 58 and "in_a_won" not in names
    f = pd.read_parquet(MF, columns=["match_id", "tour", "season"] + names, filters=[("season", "<=", LAST)])
    f = f[f["in_surface"].isin(list(SURF))].copy()
    f["surface"] = f["in_surface"].map(SURF)
    sc = ["match_id"] + [f"srf_{k}_eff_{s}_{x}" for s in S for k in "OD" for x in "ab"]
    f = f.merge(pd.read_parquet(SF, columns=sc), on="match_id", how="left")
    c = pd.read_csv(CONST)
    c = c[c["kind"].eq("surface average")]
    mu = c.pivot_table(index=["tour", "surface"], columns="stat", values="value")[S].reset_index()
    f = f.merge(mu.rename(columns={s: f"mu_{s}" for s in S}), on=["tour", "surface"], how="left")
    return f.reset_index(drop=True), names


def pr(d, s, srv, ret):
    """IOS's own predictor: expected rate of statistic s when srv serves to ret."""
    return sig(logit(d[f"mu_{s}"]) + d[f"srf_O_eff_{s}_{srv}"] - d[f"srf_D_eff_{s}_{ret}"])


def comp(d, srv, ret):
    """I-008: the serve point from its parts, fi*fw + (1 - fi)*sw."""
    fi, fw, sw = pr(d, "first_in", srv, ret), pr(d, "first_won", srv, ret), pr(d, "second_won", srv, ret)
    return fi * fw + (1 - fi) * sw


def shield(d, srv, ret):
    """I-012 (MEC-04) exactly: p = a + (1 - a) r, the returner acting on the rally part r with elasticity k, k fixed by
    the tour x surface averages so that the average elasticity is 1. No free function."""
    abar, pbar = d["mu_ace"].to_numpy(), d["mu_spw"].to_numpy()
    rbar = (pbar - abar) / (1 - abar)
    k = pbar * (1 - pbar) / ((1 - abar) * rbar * (1 - rbar))
    a0 = sig(logit(abar) + d[f"srf_O_eff_ace_{srv}"].to_numpy())
    a = pr(d, "ace", srv, ret)
    p0 = sig(logit(pbar) + d[f"srf_O_eff_spw_{srv}"].to_numpy())
    r0 = np.clip((p0 - a0) / (1 - a0), 1e-4, 1 - 1e-4)
    r = sig(logit(r0) - k * d[f"srf_D_eff_spw_{ret}"].to_numpy())
    return a + (1 - a) * r


def match_logit(pa, pb, bo):
    """logit P_iid(A wins) with a 7-point tiebreak in every set (deciding-set rules ignored: < 0.02 logit)."""
    pa, pb, bo = np.asarray(pa, float), np.asarray(pb, float), np.asarray(bo)
    out = np.full(len(pa), np.nan)
    for b in (3, 5):
        m = (bo == b) & np.isfinite(pa) & np.isfinite(pb)
        if m.any():
            out[m] = logit(I.match_win(pa[m], pb[m], b, "TB7@6"))
    return out


def leverage_ratio(pbar):
    lev = json.loads(LEV.read_text())["leverage"]
    return np.interp(pbar, np.array(lev["pbar"]), np.array(lev["formats"]["bo3"]["leverage_relative_to_pbar_0.62"]))
