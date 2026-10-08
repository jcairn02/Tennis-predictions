"""Round 2, MECHANICS, part G: statistic-level link tests (no winners; 2013-2021 model-frame matches).
For every serving side: r = logit((spw + 1/2)/(svpt + 1)) - (mu + O_srv - D_ret), the match's serve-point residual
against the surface IOS. Weighted regressions of r per tour:
  link:   r ~ 1 + O + D + O*D          (O*D = 0 under logit-additivity; about -0.24 if serve and return add on the
                                         probability scale, from -sigma''(mu) / (p(1-p)) at p = 0.62)
  shield: r ~ 1 + O + D + Oace + Oace*D (I-012's precheck: + if aces shield the server from return skill)
SEs are weighted-OLS SEs times sqrt(1.9), the measured over-dispersion of serve-point rates (Stage 3).

Run: ./python.sh src/eda/feature_interactions/round2/mechanics/part_g.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import OUT, ROOT, load, logit

OLD = ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/predictability_diagnostic"


def wls(y, X, w):
    Xw = X * np.sqrt(w)[:, None]
    yw = y * np.sqrt(w)
    beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    res = yw - Xw @ beta
    s2 = res @ res / (len(y) - X.shape[1])
    se = np.sqrt(np.diag(np.linalg.inv(Xw.T @ Xw)) * s2)
    return beta, se * np.sqrt(1.9)


def main():
    f, _ = load()
    p = pd.read_parquet(OLD / "stage0_match_players.parquet", columns=["match_id", "side", "svpt", "first_won", "second_won"])
    p = p[p["match_id"].isin(f["match_id"])].copy()
    p["spw"] = p["first_won"] + p["second_won"]
    rows = []
    for srv, ret, side in (("a", "b", "A"), ("b", "a", "B")):
        q = p[p["side"].eq(side)].set_index("match_id")[["spw", "svpt"]]
        d = f.join(q, on="match_id").dropna(subset=["spw", "svpt"])
        d = d[d["svpt"] >= 20]
        rows.append(pd.DataFrame({
            "tour": d["tour"].to_numpy(), "n": d["svpt"].to_numpy(),
            "r": logit((d["spw"] + 0.5) / (d["svpt"] + 1)) - (logit(d["mu_spw"]) + d[f"srf_O_eff_spw_{srv}"] - d[f"srf_D_eff_spw_{ret}"]),
            "O": d[f"srf_O_eff_spw_{srv}"].to_numpy(), "D": d[f"srf_D_eff_spw_{ret}"].to_numpy(),
            "Oa": d[f"srf_O_eff_ace_{srv}"].to_numpy(), "mu": d["mu_spw"].to_numpy()}))
    r = pd.concat(rows, ignore_index=True).dropna()
    out = {"note": "serve-point statistics only; no match result read"}
    for t, g in r.groupby("tour"):
        w = g["n"] * g["mu"] * (1 - g["mu"])
        O, D, Oa = g["O"] - g["O"].mean(), g["D"] - g["D"].mean(), g["Oa"] - g["Oa"].mean()
        one = np.ones(len(g))
        b1, s1 = wls(g["r"].to_numpy(), np.column_stack([one, O, D, O * D]), w.to_numpy())
        b2, s2 = wls(g["r"].to_numpy(), np.column_stack([one, O, D, Oa, Oa * D]), w.to_numpy())
        out[t] = {"serving_rows": int(len(g)),
                  "link O*D": {"coef": round(float(b1[3]), 4), "se": round(float(s1[3]), 4)},
                  "shield Oace*D": {"coef": round(float(b2[4]), 4), "se": round(float(s2[4]), 4)},
                  "slopes O, D (link fit)": [round(float(b1[1]), 3), round(float(b1[2]), 3)],
                  "sd O, D, Oace": [round(float(O.std()), 3), round(float(D.std()), 3), round(float(Oa.std()), 3)]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "part_g.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
