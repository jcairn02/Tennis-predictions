"""Round 2, MECHANICS, part F: is the surface part of the pair's dominance priced like its all-surface part?
The surface IOS splits each rating into an all-surface part (srf_O, srf_D) and a surface deviation (srf_E, srf_F), with
O_eff = O + E and D_eff = D + F. The pair's dominance m = mu + (sum O_eff - sum D_eff)/2 splits the same way. Regress the
close's log-odds (and the iid benchmark) on cell slopes x Delta, Delta^3, Delta x kappa_all and Delta x kappa_dev
(2013-2021; a_won never read; the price only as a regressand against pre-match features).

Run: ./python.sh src/eda/feature_interactions/round2/mechanics/part_f.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import OUT, SF, leverage_ratio, load, logit, match_logit, pr, sig


def main():
    f, _ = load()
    extra = ["match_id"] + [f"srf_{k}_spw_{x}" for k in "ODEF" for x in "ab"]
    f = f.merge(pd.read_parquet(SF, columns=extra), on="match_id", how="left")
    mu = logit(f["mu_spw"])
    m_all = mu + (f["srf_O_spw_a"] + f["srf_O_spw_b"] - f["srf_D_spw_a"] - f["srf_D_spw_b"]) / 2
    m_tot = mu + (f["srf_O_eff_spw_a"] + f["srf_O_eff_spw_b"] - f["srf_D_eff_spw_a"] - f["srf_D_eff_spw_b"]) / 2
    cell = f["tour"] + f["surface"] + f["in_indoor"].fillna(-1).astype(str) + f["in_best_of"].astype(str)
    lam_all, lam_tot = leverage_ratio(sig(m_all)), leverage_ratio(sig(m_tot))
    ref = f.assign(l=lam_tot).groupby(cell)["l"].transform("mean").to_numpy()
    k_all, k_tot = lam_all / ref - 1, lam_tot / ref - 1
    k_dev = k_tot - k_all
    delta = ((f["srf_O_eff_spw_a"] - f["srf_D_eff_spw_b"]) - (f["srf_O_eff_spw_b"] - f["srf_D_eff_spw_a"])).to_numpy()
    z_iid = match_logit(pr(f, "spw", "a", "b"), pr(f, "spw", "b", "a"), f["in_best_of"].to_numpy())
    out = {"note": "2013-2021; a_won never read; the close only as a regressand against pre-match features"}
    for t in ("atp", "wta"):
        m = f["tour"].eq(t).to_numpy() & np.isfinite(delta) & np.isfinite(z_iid) & np.isfinite(k_dev)
        cells = sorted(cell[m].unique())
        X = np.column_stack([delta[m] * (cell[m] == c).to_numpy() for c in cells]
                            + [delta[m] ** 3, delta[m] * k_all[m], delta[m] * k_dev[m]])
        w = np.array([(cell[m] == c).sum() for c in cells], dtype=float)
        res = {"n": int(m.sum()), "rms_kappa_all": round(float(np.sqrt(np.mean(k_all[m] ** 2))), 4),
               "rms_kappa_dev": round(float(np.sqrt(np.mean(k_dev[m] ** 2))), 4),
               "corr_kappa_all_dev": round(float(np.corrcoef(k_all[m], k_dev[m])[0, 1]), 3)}
        for name, z in (("close", f["in_odds_logit"].to_numpy()), ("iid", z_iid)):
            beta = np.linalg.lstsq(X, z[m], rcond=None)[0]
            a = float(np.sum(beta[:len(cells)] * w) / w.sum())
            res[name] = {"ratio_all": round(float(beta[-2] / a), 3), "ratio_dev": round(float(beta[-1] / a), 3)}
        out[t] = res
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "part_f.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
