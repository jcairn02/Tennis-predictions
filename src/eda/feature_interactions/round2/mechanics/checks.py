"""Round 2, MECHANICS: result-free checks behind the rebuttals (seasons <= 2021; a_won never read).

A. Remainders (feasibility's remedy for I-008 and I-012): each column regressed by OLS on the 58 inputs, fitted on
   2013-2018 per tour, applied to 2019-2021; the remainder's SD in match log-odds (G2's line: about 0.03).
B. I-001's premise: at matched IOS strength, does the close's log-odds scale with the pair's dominance leverage?
   z = in_odds_logit on cell slopes x Delta, Delta^3, and Delta x kappa (no intercept, per tour). b/a is the share of
   the leverage the close applies; the same regression of the iid's own log-odds is the benchmark (about 1).
   The price is a regressand against pre-match features only, the class of the auditor's I-006 check.

Run: ./python.sh src/eda/feature_interactions/round2/mechanics/checks.py
"""
from __future__ import annotations

import json

import numpy as np

from common import OUT, comp, leverage_ratio, load, logit, match_logit, pr, shield, sig


def design(d, names):
    X = d[names].to_numpy(dtype=float)
    keep = ~np.isnan(X).all(axis=0)
    X = X[:, keep]
    col_mean = np.nanmean(X[d["season"].le(2018).to_numpy()], axis=0)
    idx = np.where(np.isnan(X))
    X[idx] = np.take(col_mean, idx[1])
    return np.column_stack([np.ones(len(X)), X])


def remainder(y, X, fit):
    ok = np.isfinite(y)
    beta = np.linalg.lstsq(X[ok & fit], y[ok & fit], rcond=None)[0]
    return y - X @ beta, ok


def part_a(f, names):
    out = {}
    bo = f["in_best_of"].to_numpy()
    cols = {
        "I-008 z_C1": match_logit(comp(f, "a", "b"), comp(f, "b", "a"), bo),
        "I-012 x' (shield, composed)": match_logit(shield(f, "a", "b"), shield(f, "b", "a"), bo)
        - match_logit(pr(f, "spw", "a", "b"), pr(f, "spw", "b", "a"), bo),
    }
    for t in ("atp", "wta"):
        m = f["tour"].eq(t).to_numpy()
        g = f[m]
        X = design(g, names)
        fit = g["season"].le(2018).to_numpy()
        for k, y in cols.items():
            r, ok = remainder(y[m], X, fit)
            oos = ok & ~fit
            out[f"{t} {k}"] = {"sd_column": round(float(np.nanstd(y[m][ok])), 4),
                               "r2_fit_2013_2018": round(float(1 - np.var(r[ok & fit]) / np.var(y[m][ok & fit])), 4),
                               "remainder_sd_2013_2018": round(float(np.std(r[ok & fit])), 4),
                               "remainder_sd_2019_2021": round(float(np.std(r[oos])), 4), "n_2019_2021": int(oos.sum())}
    return out


def part_b(f):
    out = {}
    m_dom = logit(f["mu_spw"]) + (f["srf_O_eff_spw_a"] + f["srf_O_eff_spw_b"]
                                  - f["srf_D_eff_spw_a"] - f["srf_D_eff_spw_b"]) / 2
    lam = leverage_ratio(sig(m_dom))
    cell = f["tour"] + f["surface"] + f["in_indoor"].fillna(-1).astype(str) + f["in_best_of"].astype(str)
    kappa = lam / f.assign(l=lam).groupby(cell)["l"].transform("mean").to_numpy() - 1
    delta = ((f["srf_O_eff_spw_a"] - f["srf_D_eff_spw_b"]) - (f["srf_O_eff_spw_b"] - f["srf_D_eff_spw_a"])).to_numpy()
    z_iid = match_logit(pr(f, "spw", "a", "b"), pr(f, "spw", "b", "a"), f["in_best_of"].to_numpy())
    targets = {"close (in_odds_logit)": f["in_odds_logit"].to_numpy(), "iid benchmark": z_iid}
    for t in ("atp", "wta"):
        m = f["tour"].eq(t).to_numpy() & np.isfinite(delta) & np.isfinite(z_iid) & f["in_odds_logit"].notna().to_numpy()
        cells = sorted(cell[m].unique())
        cols = [delta[m] * (cell[m] == c).to_numpy() for c in cells] + [delta[m] ** 3, delta[m] * kappa[m]]
        X = np.column_stack(cols)
        res = {"n": int(m.sum()), "rms_kappa": round(float(np.sqrt(np.mean(kappa[m] ** 2))), 4)}
        for name, z in targets.items():
            beta = np.linalg.lstsq(X, z[m], rcond=None)[0]
            w = np.array([((cell[m] == c).sum()) for c in cells], dtype=float)
            a_mean = float(np.sum(beta[:len(cells)] * w) / w.sum())
            res[name] = {"a_mean": round(a_mean, 4), "b": round(float(beta[-1]), 4),
                         "ratio_b_over_a": round(float(beta[-1] / a_mean), 3)}
        terc = np.quantile(kappa[m], [1 / 3, 2 / 3])
        grp = np.digitize(kappa[m], terc)
        res["var_delta_by_kappa_tercile"] = [round(float(np.var(delta[m][grp == j])), 4) for j in range(3)]
        out[t] = res
    return out


def main():
    f, names = load()
    res = {"note": "seasons <= 2021; a_won never read; the price only as a regressand against pre-match features",
           "matches": int(len(f)), "A_remainders": part_a(f, names), "B_i001_premise": part_b(f)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "checks.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
