"""Robustness checks of the early-price test 1, run after its pre-registered result (so: post hoc, labelled so).

    marginal   OLS of the move M on Delta alone (no intercept). Delta = logit primary_noodds - logit base_noodds never
               sees a price, so its slope cannot pick up the reversal of noise in the 24-hour price, which the
               pre-registered control D (base_noodds minus the 24-hour price) contains by construction. If Delta and D
               were correlated, part of that mechanical effect could leak into Delta's partial slope; this rules it out
    corr       the correlation of Delta with D
    weeks      the pre-registered regression with calendar-week clusters (the plan's sensitivity)
    horizons   where the move happens: 24 h -> 6 h and 6 h -> 30 minutes, each on Delta and D at the start of the leg
    magnitude  what a one-standard-deviation Delta moves the price by, in log-odds and in points of probability
    price-free OLS of M on b = logit base_noodds and Delta: both controls free of any price, so neither slope can pick up
               the reversal of the early price's noise; Delta's slope is its value beyond the old model's own view
    money      the deployment forecasts (trained on closing odds, fed the 24-hour or the 30-minute price) against the raw
               price they were fed, in milli-log-loss (positive = the model is better than the price)

Writes data/studies/surface_elo_pieces/early_price_checks.csv. Run: ./python.sh src/eda/surface_elo_pieces/early_price_checks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.surface_elo_pieces import early_price_score as S  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402


def main() -> int:
    ep = pd.read_parquet(C.OUT / "early_price_frame.parquet")
    nb, npm = S.load_local("base_noodds", "td"), S.load_local("primary_noodds", "td")
    f = ep.merge(nb[["match_id", "mean"]].rename(columns={"mean": "p_nb"}), on="match_id", how="left") \
          .merge(npm[["match_id", "mean"]].rename(columns={"mean": "p_np"}), on="match_id", how="left")
    lg = S.lg
    f["Delta"] = lg(f["p_np"]) - lg(f["p_nb"])
    f["block"] = T.blocks(f["tournament_date"].to_numpy(), 28)
    f["week"] = T.blocks(f["tournament_date"].to_numpy(), 7)
    legs = {"24h -> 30m": ("p_early_a", "p_close_a"), "24h -> 6h": ("p_early_a", "p_6h_a"), "6h -> 30m": ("p_6h_a", "p_close_a")}
    rows = []
    for pop, pm in (("clean", f["clean"]), ("all", f["all_early"])):
        for tour in ("atp", "wta", "both"):
            tm = pm & ((f["tour"] == tour) if tour != "both" else True)
            for leg, (a, b) in legs.items():
                M = lg(f[b]) - lg(f[a])
                D = lg(f["p_nb"]) - lg(f[a])
                k = (tm & np.isfinite(M) & np.isfinite(D) & np.isfinite(f["Delta"])).to_numpy()
                g = f[k]
                m_, d_, x_ = M[k], D[k], g["Delta"].to_numpy()
                for cl in ("block", "week"):
                    both = S.ols_cluster(m_, np.column_stack([d_, x_]), g[cl].to_numpy())
                    marg = S.ols_cluster(m_, x_[:, None], g[cl].to_numpy())
                    rows.append({"population": pop, "tour": tour, "leg": leg, "clusters_by": cl, "matches": int(k.sum()),
                                 "clusters": both["clusters"], "corr_Delta_D": float(np.corrcoef(x_, d_)[0, 1]),
                                 "beta_Delta_partial": both["beta"][1], "lo_partial": both["lo"][1],
                                 "hi_partial": both["hi"][1], "beta_Delta_marginal": marg["beta"][0],
                                 "lo_marginal": marg["lo"][0], "hi_marginal": marg["hi"][0],
                                 "beta_D": both["beta"][0], "lo_D": both["lo"][0], "hi_D": both["hi"][0],
                                 "sd_Delta": float(np.std(x_)), "sd_M": float(np.std(m_)),
                                 "move_per_sd_Delta_logodds": float(marg["beta"][0] * np.std(x_)),
                                 "move_per_sd_Delta_points_at_50pct": float(25 * marg["beta"][0] * np.std(x_))})
    out = pd.DataFrame(rows)
    out.to_csv(C.OUT / "early_price_checks.csv", index=False)
    # price-free controls, and the deployment forecasts against the raw prices
    be, pe = S.load_local("base", "early"), S.load_local("primary", "early")
    bc, pc = S.load_local("base", "close"), S.load_local("primary", "close")
    for tag, d in (("be", be), ("pe", pe), ("bc", bc), ("pc", pc)):
        f = f.merge(d[["match_id", "mean"]].rename(columns={"mean": f"p_{tag}"}), on="match_id", how="left")
    f["M"] = lg(f["p_close_a"]) - lg(f["p_early_a"])
    f["b"] = lg(f["p_nb"])
    pf, money = [], []
    for pop, pm in (("clean", f["clean"]), ("all", f["all_early"])):
        for tour in ("atp", "wta", "both"):
            k = (pm & ((f["tour"] == tour) if tour != "both" else True) & np.isfinite(f["M"])).to_numpy()
            g = f[k]
            for cl in ("block", "week"):
                r = S.ols_cluster(g["M"].to_numpy(), g[["b", "Delta"]].to_numpy(), g[cl].to_numpy())
                pf.append({"population": pop, "tour": tour, "clusters_by": cl, "matches": r["n"], "clusters": r["clusters"],
                           "corr_Delta_b": float(np.corrcoef(g["Delta"], g["b"])[0, 1]),
                           "beta_b": r["beta"][0], "lo_b": r["lo"][0], "hi_b": r["hi"][0],
                           "beta_Delta": r["beta"][1], "lo_Delta": r["lo"][1], "hi_Delta": r["hi"][1]})
            y = g["a_won"].to_numpy()
            for base, model in (("p_early_a", "p_be"), ("p_early_a", "p_pe"), ("p_close_a", "p_bc"),
                                ("p_close_a", "p_pc"), ("p_early_a", "p_close_a")):
                c = T.compare(T.ll(g[base].to_numpy(), y), T.ll(g[model].to_numpy(), y), g["tournament_date"].to_numpy())
                money.append({"population": pop, "tour": tour, "base": base, "model": model, "matches": c["n"],
                              "gain": c["gain"], "lo": c["lo"], "hi": c["hi"], "week_lo": c["week_lo"],
                              "week_hi": c["week_hi"]})
    pf, money = pd.DataFrame(pf), pd.DataFrame(money)
    pf.to_csv(C.OUT / "early_price_checks_pricefree.csv", index=False)
    money.to_csv(C.OUT / "early_price_checks_money.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(out.round(3).to_string(index=False))
        print(pf.round(3).to_string(index=False))
        print(money.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
