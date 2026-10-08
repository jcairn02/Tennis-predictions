"""Score the early-price test (plan: docs/studies/surface_elo_pieces/early_price_plan.md, fixed before this was run).

    agreement   local fits against the paid API's forecasts of the same arm, season and seed (log-odds correlation, mean
                absolute probability gap): the local runs reproduce the confirmation's model
    test 1      OLS without intercept of the move M = logit P(close) - logit P(24 h) on D = logit base_noodds -
                logit P(24 h) and Delta = logit primary_noodds - logit base_noodds (local seed means); slopes with
                cluster-robust 95% intervals over four-week blocks, t on (blocks - 1) df; calendar weeks as sensitivity
    test 2      logistic stacks without intercept, cross-fitted leaving one four-week block out: S0 = early price,
                S1 = + base_noodds, S2 = + primary_noodds; the same with the 30-minute price (R0-R2) as a reference
    test 3      deployment: base and primary trained on closing odds and queried with the 24-hour price (seed means),
                against each other and against S0; the same with the 30-minute price

Populations: "clean" (primary: event openers, previous match >= 3 days before, both prices, no identity-split debut)
and "all" (sensitivity: every match with both prices, later rounds included; the forecasts may know a previous round
that ended within 24 hours of the start). Per tour and both tours.

Milli-log-loss, positive = the second-named forecast is better; slopes signed as stated in the output.
Writes data/studies/surface_elo_pieces/early_price_results.json and early_price_results.csv.
Run: ./python.sh src/eda/surface_elo_pieces/early_price_score.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

LOCAL = C.OUT / "local"
SEASONS = (2025, 2026)
SEEDS = (0, 1, 2)
EPS = 1e-6


def lg(p):
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def load_local(arm: str, query: str) -> pd.DataFrame:
    """Seed-mean symmetrised forecasts of one arm for one query block, both seasons; also each seed."""
    parts = []
    for season in SEASONS:
        cols = {}
        for seed in SEEDS:
            with np.load(LOCAL / f"{arm}__{season}__seed{seed}.npz", allow_pickle=False) as z:
                if f"p_{query}" not in z:
                    raise KeyError(f"{arm} has no {query} query")
                p, ids = z[f"p_{query}"], z[f"ids_{query}"]
            n = len(ids)
            cols["match_id"] = ids
            cols[f"s{seed}"] = T.symmetrize(p[:n], p[n:])
        parts.append(pd.DataFrame(cols))
    d = pd.concat(parts, ignore_index=True)
    d["mean"] = d[[f"s{s}" for s in SEEDS]].mean(axis=1)
    return d


def ols_cluster(y: np.ndarray, X: np.ndarray, clusters: np.ndarray) -> dict:
    """OLS without intercept; CR1 cluster-robust covariance; t on (G - 1) df."""
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    labels, ix = np.unique(clusters, return_inverse=True)
    g = len(labels)
    S = np.zeros((g, k))
    np.add.at(S, ix, X * e[:, None])
    V = XtX_inv @ (S.T @ S) @ XtX_inv * (g / (g - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V))
    tq = student_t.ppf(0.975, g - 1)
    r2 = 1 - (e @ e) / (y @ y)
    return {"beta": beta.tolist(), "se": se.tolist(), "lo": (beta - tq * se).tolist(), "hi": (beta + tq * se).tolist(),
            "clusters": int(g), "n": int(n), "r2_uncentred": float(r2)}


def crossfit_stack(X: np.ndarray, y: np.ndarray, blocks: np.ndarray) -> np.ndarray:
    """Leave-one-block-out logistic fits without intercept."""
    p = np.full(len(y), np.nan)
    for b in np.unique(blocks):
        te = blocks == b
        beta, _ = T.fit_logistic(X[~te], y[~te].astype(float))
        p[te] = expit(X[te] @ beta)
    return p


def main() -> int:
    ep = pd.read_parquet(C.OUT / "early_price_frame.parquet")
    nb, npm = load_local("base_noodds", "td"), load_local("primary_noodds", "td")
    be, pe = load_local("base", "early"), load_local("primary", "early")
    bc, pc = load_local("base", "close"), load_local("primary", "close")
    btd, ptd = load_local("base", "td"), load_local("primary", "td")
    # agreement with the paid API's forecasts of the same arms, seasons and seeds
    agree = {}
    api_d = pd.read_parquet(C.OUT / "predictions_diagnostic.parquet")
    api_c = pd.read_parquet(C.OUT / "predictions_confirm.parquet")
    for name, loc, api, col in (("base_noodds seed 0", nb, api_d, "p_base_noodds_s0"),
                                ("primary_noodds seed 0", npm, api_d, "p_primary_noodds_s0"),
                                ("base seed 0", btd, api_c, "p_base_s0"), ("base seed 1", btd, api_c, "p_base_s1"),
                                ("primary seed 0", ptd, api_c, "p_primary_s0"), ("primary seed 2", ptd, api_c, "p_primary_s2")):
        seed = name.split("seed ")[1]
        m = loc[["match_id", f"s{seed}"]].merge(api[["match_id", col]], on="match_id", how="inner")
        a, b = m[f"s{seed}"].to_numpy(), m[col].to_numpy()
        agree[name] = {"matches": int(len(m)), "log_odds_correlation": float(np.corrcoef(lg(a), lg(b))[0, 1]),
                       "mean_abs_prob_gap": float(np.mean(np.abs(a - b))), "max_abs_prob_gap": float(np.max(np.abs(a - b)))}
    f = ep.copy()
    for tag, d in (("nb", nb), ("np", npm), ("be", be), ("pe", pe), ("bc", bc), ("pc", pc)):
        f = f.merge(d[["match_id", "mean"]].rename(columns={"mean": f"p_{tag}"}), on="match_id", how="left")
    api_s0 = api_d[["match_id", "p_base_noodds_s0", "p_primary_noodds_s0"]]
    f = f.merge(api_s0, on="match_id", how="left")
    f["M"] = lg(f["p_close_a"]) - lg(f["p_early_a"])
    f["D"] = lg(f["p_nb"]) - lg(f["p_early_a"])
    f["Delta"] = lg(f["p_np"]) - lg(f["p_nb"])
    f["Delta_api_s0"] = lg(f["p_primary_noodds_s0"]) - lg(f["p_base_noodds_s0"])
    f["D_api_s0"] = lg(f["p_base_noodds_s0"]) - lg(f["p_early_a"])
    f["block"] = T.blocks(f["tournament_date"].to_numpy(), 28)
    f["week"] = T.blocks(f["tournament_date"].to_numpy(), 7)
    y_all = f["a_won"].to_numpy(bool)
    test1, test2, test3, rows = [], [], [], []
    pops = {"clean": f["clean"].to_numpy(bool), "all": f["all_early"].to_numpy(bool)}
    tours = {"atp": (f["tour"] == "atp").to_numpy(), "wta": (f["tour"] == "wta").to_numpy(), "both": np.ones(len(f), bool)}
    for pop, pm in pops.items():
        for tour, tm in tours.items():
            k = pm & tm & np.isfinite(f["M"]) & np.isfinite(f["D"]) & np.isfinite(f["Delta"])
            g = f[k]
            for variant, dcol, xcol in (("local seed means", "D", "Delta"), ("API seed 0", "D_api_s0", "Delta_api_s0")):
                for cl in ("block", "week"):
                    r = ols_cluster(g["M"].to_numpy(), g[[dcol, xcol]].to_numpy(), g[cl].to_numpy())
                    test1.append({"population": pop, "tour": tour, "forecasts": variant, "clusters_by": cl,
                                  "matches": r["n"], "clusters": r["clusters"],
                                  "beta_D": r["beta"][0], "lo_D": r["lo"][0], "hi_D": r["hi"][0],
                                  "beta_Delta": r["beta"][1], "lo_Delta": r["lo"][1], "hi_Delta": r["hi"][1],
                                  "sd_M": float(g["M"].std()), "sd_D": float(g[dcol].std()), "sd_Delta": float(g[xcol].std()),
                                  "r2_uncentred": r["r2_uncentred"]})
            # tests 2 and 3 on the same matches
            y = y_all[k]
            blk = g["block"].to_numpy()
            le, lc = lg(g["p_early_a"]), lg(g["p_close_a"])
            lnb, lnp = lg(g["p_nb"]), lg(g["p_np"])
            stacks = {"S0": [le], "S1": [le, lnb], "S2": [le, lnp], "R0": [lc], "R1": [lc, lnb], "R2": [lc, lnp]}
            P = {s: crossfit_stack(np.column_stack(c), y, blk) for s, c in stacks.items()}
            P.update({"base@early": g["p_be"].to_numpy(), "primary@early": g["p_pe"].to_numpy(),
                      "base@close": g["p_bc"].to_numpy(), "primary@close": g["p_pc"].to_numpy(),
                      "raw early": g["p_early_a"].to_numpy(), "raw close": g["p_close_a"].to_numpy()})
            dates = g["tournament_date"].to_numpy()
            for test, pairs in (("2", [("S1", "S2"), ("S0", "S1"), ("S0", "S2"), ("R1", "R2"), ("R0", "R1"), ("R0", "R2")]),
                                ("3", [("base@early", "primary@early"), ("S0", "base@early"), ("S0", "primary@early"),
                                       ("base@close", "primary@close"), ("R0", "base@close"), ("R0", "primary@close"),
                                       ("raw early", "S0"), ("S0", "R0")])):
                for a_, b_ in pairs:
                    c = T.compare(T.ll(P[a_], y), T.ll(P[b_], y), dates)
                    (test2 if test == "2" else test3).append(
                        {"population": pop, "tour": tour, "base": a_, "model": b_, "matches": c["n"], "gain": c["gain"],
                         "lo": c["lo"], "hi": c["hi"], "blocks": c["blocks"], "week_lo": c["week_lo"],
                         "week_hi": c["week_hi"]})
            rows.append({"population": pop, "tour": tour, "matches": int(k.sum()),
                         **{f"log_loss {s}": float(T.ll(P[s], y).mean()) for s in P}})
    res = {"key": "test 1: slopes of the move M = logit P(close) - logit P(24h) on D (base no-odds forecast minus the "
                  "24h price) and Delta (primary no-odds minus base no-odds), log-odds units; a positive slope means "
                  "the price moves toward that forecast. Tests 2-3: milli-log-loss, positive = the second-named forecast "
                  "is better. 95% intervals; spanning 0 = tie.",
           "agreement_local_vs_api": agree, "test1": test1, "test2": test2, "test3": test3, "log_loss": rows}
    C.write_json(C.OUT / "early_price_results.json", res)
    pd.concat([pd.DataFrame(test1).assign(test="1"), pd.DataFrame(test2).assign(test="2"),
               pd.DataFrame(test3).assign(test="3")]).to_csv(C.OUT / "early_price_results.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 300):
        print(json.dumps(agree, indent=1))
        t1 = pd.DataFrame(test1)
        print(t1[t1["clusters_by"] == "block"].drop(columns=["clusters_by"]).round(3).to_string(index=False))
        print(pd.DataFrame(test2).round(2).to_string(index=False))
        print(pd.DataFrame(test3).round(2).to_string(index=False))
        print(pd.DataFrame(rows).round(5).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
