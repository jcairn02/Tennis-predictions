"""Round-1 mathematical audit: result-free numbers behind the verdicts (seasons <= 2021, no result column loaded).

    ./python.sh src/eda/feature_interactions/round1/math_audit/novelty.py

Writes data/studies/feature_interactions/round1/math_audit/novelty.csv (one row per candidate proxy column) and
numbers.json (price weights, MDE table, the I-007 price-only substitute, I-001 / I-006 / I-035 / I-032 checks).
Every regression here has a feature or a price on the left, never a match outcome.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.math_audit import candidates as CB  # noqa: E402
from src.eda.feature_interactions.round1.math_audit.common_audit import (OUT, design58, load_panel, nearest_inputs,  # noqa: E402
                                                                        num, r2_on, resid_sd, surface_means)


def mde_table(n: int = 50087) -> dict:
    """80%-power MDE (mLL, population-averaged) of a one-sided coefficient test at Holm's first step, alpha 5% x w / m."""
    out = {}
    for m in (1, 30, 40, 50, 80):
        for w in (0.5, 1.0, 2.0):
            a = 0.05 * w / m if m > 1 else 0.025
            zc = norm.isf(a) + norm.isf(0.2)
            out[f"m={m}|w={w}"] = round(1000 * zc ** 2 / (2 * n), 3)
    return out


def price_weights(z: np.ndarray, tour: np.ndarray) -> dict:
    out = {}
    for t in ("atp", "wta"):
        v = z[(tour == t) & np.isfinite(z)]
        p = expit(v)
        w = p * (1 - p)
        out[t] = {"E_w": float(w.mean()), "E_wz2": float((w * v * v).mean()), "E_2cosh": float(np.mean(2 * np.cosh(v))),
                  "E_w_sinh2": float(np.mean(w * np.sinh(v) ** 2)), "sd_z": float(v.std())}
    return out


def main() -> int:
    P = load_panel()
    means = surface_means()
    C, KIND, AUX = CB.build(P, means)
    C2, K2 = CB.build2(P, means, AUX)
    C.update(C2)
    KIND.update(K2)
    X = design58(P)
    z = num(P, "in_odds_logit")
    Xm = np.column_stack([X, z ** 3, z * np.abs(z)])
    tour = P["tour"].astype(str).to_numpy()
    rows = []
    for name, x in C.items():
        x = np.asarray(x, dtype=float)
        ok = np.isfinite(x)
        row = {"column": name, "kind": KIND.get(name, "diff"), "coverage": round(float(ok.mean()), 3),
               "sd": float(np.nanstd(x))}
        for t in ("atp", "wta"):
            s = tour == t
            row[f"r2_58_{t}"] = round(r2_on(X, x, s), 3) if (ok & s).sum() > 500 and np.nanstd(x[s]) > 0 else np.nan
        row["r2_58"] = round(r2_on(X, x), 3)
        row["r2_58_mset"] = round(r2_on(Xm, x), 3)
        row["resid_sd_58"] = resid_sd(X, x)
        row["nearest"] = "; ".join(f"{n} {r:+.2f}" for n, r in nearest_inputs(P, x))
        rows.append(row)
    nov = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    nov.to_csv(OUT / "novelty.csv", index=False)
    num_ = {"mde_mll": mde_table(), "price_weights": price_weights(z, tour)}
    # I-001: within-cell leverage modulation and the bound if the price ignores it (79 kappa^2 rule, damped by c^4)
    k = AUX["kappa"]
    pw = num_["price_weights"]
    num_["I-001"] = {t: {"rms_kappa_within_cell": float(np.sqrt(np.nanmean(k[tour == t] ** 2))),
                         "bound_undamped_mll": float(500 * pw[t]["E_wz2"] * np.nanmean(k[tour == t] ** 2)),
                         "bound_damped_c2_0.47_0.75": [float(500 * pw[t]["E_wz2"] * np.nanmean(k[tour == t] ** 2) * c ** 2)
                                                       for c in (0.47, 0.75)]} for t in ("atp", "wta")}
    # I-006 / I-007: the Bo5 leverage column against 1[bo5] x ratings_iid; the price's own Bo5/Bo3 slope ratio
    bo = num(P, "in_best_of")
    rat = num(P, "in_ratings_iid")
    u, v = AUX["u"], AUX["v"]
    s5 = (bo == 5) & np.isfinite(u) & np.isfinite(v) & (tour == "atp")
    s3 = (bo == 3) & np.isfinite(u) & (tour == "atp") & np.isfinite(z)
    L = (u - v)[s5]
    num_["I-006"] = {"bo5_men_matches": int(s5.sum()), "corr_L_vs_bo5_ratings_iid": float(np.corrcoef(L, rat[s5])[0, 1]),
                     "slope_L_on_ratings_iid": float(np.polyfit(rat[s5], L, 1)[0]),
                     "mean_u_over_v": float(np.median(u[s5][np.abs(v[s5]) > 0.2] / v[s5][np.abs(v[s5]) > 0.2])),
                     "corr_u_vs_in_ratings_iid_bo5": float(np.corrcoef(u[s5], rat[s5])[0, 1])}
    s5z = s5 & np.isfinite(z)
    b5 = np.polyfit(u[s5z], z[s5z], 1)[0]
    b3 = np.polyfit(u[s3], z[s3], 1)[0]
    b5v = np.polyfit(v[s5z], z[s5z], 1)[0]
    num_["I-007 price-only substitute"] = {
        "slope_price_on_u_bo5": float(b5), "slope_price_on_u_bo3": float(b3), "ratio_bo5_over_bo3": float(b5 / b3),
        "slope_price_on_bo3_equivalent_v_at_bo5": float(b5v), "implied_market_bo5_over_bo3_logodds_ratio": float(b5v / b3),
        "reading": "ratio of slopes on u: 1.0 = the market applies the iid 1.25; 0.8 = it applies Bo3 leverage; "
                   "0.88-0.90 = the day-noise damping (MAT A5)"}
    # I-035: the margin-aware gap beyond any fixed odd function of the price (the M-set)
    g = C["I-035 shin_gap"]
    Q = AUX["Q"]
    out35 = {}
    for t in ("atp", "wta"):
        s = (tour == t) & np.isfinite(g) & np.isfinite(z)
        M = np.column_stack([z[s], z[s] ** 3, z[s] * np.abs(z[s]), np.sinh(z[s])])
        res = g[s] - M @ np.linalg.lstsq(M, g[s], rcond=None)[0]
        w = expit(z[s]) * (1 - expit(z[s]))
        out35[t] = {"sd_overround": float(np.nanstd(Q[s])), "sd_gap": float(g[s].std()),
                    "r2_gap_on_mset_and_sinh": float(1 - res.var() / g[s].var()), "resid_sd": float(res.std()),
                    "bound_mll_coef1": float(500 * np.mean(w * res ** 2))}
    num_["I-035"] = out35
    rb = C["I-032 rbar"]
    num_["I-032"] = {t: {"cv_rbar": float(np.nanstd(rb[tour == t]) / np.nanmean(rb[tour == t])),
                         "p10_p50_p90": [float(np.nanquantile(rb[tour == t], q)) for q in (0.1, 0.5, 0.9)]}
                     for t in ("atp", "wta")}
    a = AUX["arb"]
    num_["I-037"] = {"share_arbitrage_positive": float(np.nanmean(a > 0)), "sd_a": float(np.nanstd(a))}
    num_["I-049"] = {"share_early": float(np.mean(AUX["early"]))}
    (OUT / "numbers.json").write_text(json.dumps(num_, indent=1))
    pd.set_option("display.width", 250)
    print(nov[["column", "kind", "coverage", "sd", "r2_58_atp", "r2_58_wta", "r2_58", "r2_58_mset", "nearest"]]
          .to_string(index=False))
    print(json.dumps({k_: num_[k_] for k_ in num_ if k_ != "mde_mll"}, indent=0)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
