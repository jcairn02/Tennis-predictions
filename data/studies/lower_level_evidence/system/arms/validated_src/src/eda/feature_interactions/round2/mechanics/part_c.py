"""Round 2, MECHANICS, part C: does the current best's own forecast eta (the screen's offset) already apply the pair's
dominance leverage? The regression of checks.py part B, with eta's log-odds as the regressand, on 2014-2021 rows,
beside the close and the iid benchmark on the same rows. eta is a forecast, not a result; a_won is never read.

Run: ./python.sh src/eda/feature_interactions/round2/mechanics/part_c.py
"""
from __future__ import annotations

import json

import numpy as np

from common import OUT, ROOT, leverage_ratio, load, logit, match_logit, pr, sig  # noqa: F401  (ROOT sets sys.path)
from src.eda.feature_interactions.screen import oos_model_forecast  # noqa: E402


def main():
    f, _ = load()
    s = oos_model_forecast()
    f = f[f["season"].ge(2014)].copy()
    p = f["match_id"].astype(str).map(s).to_numpy(dtype=float)
    f["eta"] = logit(np.clip(p, 1e-6, 1 - 1e-6))
    m_dom = logit(f["mu_spw"]) + (f["srf_O_eff_spw_a"] + f["srf_O_eff_spw_b"]
                                  - f["srf_D_eff_spw_a"] - f["srf_D_eff_spw_b"]) / 2
    lam = leverage_ratio(sig(m_dom))
    cell = f["tour"] + f["surface"] + f["in_indoor"].fillna(-1).astype(str) + f["in_best_of"].astype(str)
    kappa = lam / f.assign(l=lam).groupby(cell)["l"].transform("mean").to_numpy() - 1
    delta = ((f["srf_O_eff_spw_a"] - f["srf_D_eff_spw_b"]) - (f["srf_O_eff_spw_b"] - f["srf_D_eff_spw_a"])).to_numpy()
    z_iid = match_logit(pr(f, "spw", "a", "b"), pr(f, "spw", "b", "a"), f["in_best_of"].to_numpy())
    targets = {"eta (current best)": f["eta"].to_numpy(), "close": f["in_odds_logit"].to_numpy(), "iid": z_iid}
    out = {"note": "2014-2021 rows; eta and the close as regressands against pre-match features; a_won never read"}
    for t in ("atp", "wta"):
        m = f["tour"].eq(t).to_numpy() & np.isfinite(delta) & np.isfinite(z_iid) & np.isfinite(f["eta"].to_numpy())
        cells = sorted(cell[m].unique())
        X = np.column_stack([delta[m] * (cell[m] == c).to_numpy() for c in cells] + [delta[m] ** 3, delta[m] * kappa[m]])
        w = np.array([(cell[m] == c).sum() for c in cells], dtype=float)
        res = {"n": int(m.sum())}
        for name, z in targets.items():
            beta = np.linalg.lstsq(X, z[m], rcond=None)[0]
            a = float(np.sum(beta[:len(cells)] * w) / w.sum())
            res[name] = {"a_mean": round(a, 4), "b": round(float(beta[-1]), 4), "ratio": round(float(beta[-1] / a), 3)}
        # the model's adjustment over the close: does it scale with kappa beyond the close?
        adj = f["eta"].to_numpy() - f["in_odds_logit"].to_numpy()
        Xa = np.column_stack([f["in_odds_logit"].to_numpy()[m], f["in_odds_logit"].to_numpy()[m] * kappa[m]])
        beta = np.linalg.lstsq(Xa, adj[m], rcond=None)[0]
        res["adjustment_on_[z, z*kappa]"] = [round(float(x), 4) for x in beta]
        out[t] = res
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "part_c.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
