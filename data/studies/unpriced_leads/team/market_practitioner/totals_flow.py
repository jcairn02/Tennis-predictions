"""Outcome-free check for the totals lead (MP-01): does BetOnline's total-games market carry a view of the match's
competitiveness that the moneyline lacks at the open, and does the moneyline move toward it by the close?

No outcome is read (no a_won, won, score or status). Seasons <= 2024 only (2019-2024, where totals exist), so no
2025-26 market-response reading of this new statistic is made.

excess_open  = tg_open_line  - E[tg_open_line  | |L_open|,  L_open^2,  tour, best_of, surface, indoor, level]
excess_close = tg_close_line - E[tg_close_line | |L_close|, L_close^2, tour, best_of, surface, indoor, level]
fav_move     = |L_close| - |L_open| for the opening favourite (+ = the favourite firmed)
Regressions (OLS, clusters = tournament weeks):
  fav_move ~ excess_open + |L_open| + controls          (does the moneyline drift when the total says 'closer'?)
  tg_move  ~ fav_move + controls                        (does the total follow the moneyline?)
Run: ./python.sh data/studies/unpriced_leads/team/market_practitioner/totals_flow.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
T = ROOT / "data/studies/current_best_model/template_2026-10-10"


def lg(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def ols_cluster(X, y, g):
    m = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y, g = X[m], y[m], g[m]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    xtx_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for k in np.unique(g):
        s = (X[g == k] * r[g == k, None]).sum(axis=0)
        meat += np.outer(s, s)
    v = xtx_inv @ meat @ xtx_inv
    return b, np.sqrt(np.diag(v)), int(m.sum())


mf = pd.read_parquet(T / "model_frame.parquet",
                     columns=["match_id", "tour", "season", "tournament_date", "in_level", "in_surface", "in_indoor",
                              "in_best_of"])
mf = mf[mf["season"].between(2019, 2024)].copy()
bt = pd.read_parquet(ROOT / "data/studies/bet_timing/frame.parquet",
                     columns=["match_id", "p_bol_open", "p_bol_close", "ok_bol_open", "ok_bol_close"])
os_ = pd.read_parquet(T / "odds_sources.parquet", columns=["match_id", "eid"])
tg = pd.read_parquet(ROOT / "data/dump/odds/oddstrader/betonline_matches.parquet",
                     columns=["eid", "tg_open_line", "tg_close_line", "tg_open_uncertain", "tg_close_uncertain"])
for d in (mf, bt, os_):
    d["match_id"] = d["match_id"].astype(str)
f = mf.merge(bt, on="match_id").merge(os_, on="match_id", how="left").merge(tg, on="eid", how="left")
keep = (f["ok_bol_open"].astype(bool) & f["ok_bol_close"].astype(bool) & np.isfinite(f["tg_open_line"])
        & np.isfinite(f["tg_close_line"]) & ~f["tg_open_uncertain"].fillna(True).astype(bool)
        & ~f["tg_close_uncertain"].fillna(True).astype(bool))
f = f[keep.to_numpy()].copy()
f["Lo"], f["Lc"] = lg(f["p_bol_open"]), lg(f["p_bol_close"])
f["week"] = pd.to_datetime(f["tournament_date"]).dt.to_period("W").astype(str)


def design(df, L):
    cols = [np.ones(len(df)), np.abs(L), L ** 2, (df["tour"] == "wta").astype(float)]
    for v in sorted(df["in_surface"].dropna().unique())[1:]:
        cols.append((df["in_surface"] == v).astype(float))
    for v in sorted(df["in_level"].dropna().unique())[1:]:
        cols.append((df["in_level"] == v).astype(float))
    cols.append(df["in_indoor"].astype(float))
    return np.column_stack(cols)


res = {"note": "outcome-free; BetOnline lines 2019-2024; no result read", "n": int(len(f))}
parts = []
for bo, g in f.groupby("in_best_of"):
    g = g.copy()
    for side, line, L in (("open", "tg_open_line", "Lo"), ("close", "tg_close_line", "Lc")):
        X = design(g, g[L].to_numpy())
        y = g[line].to_numpy(float)
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        g[f"excess_{side}"] = y - X @ b
        res[f"bo{int(bo)}_{side}_r2"] = round(float(1 - (y - X @ b).var() / y.var()), 3)
        res[f"bo{int(bo)}_{side}_resid_sd_games"] = round(float((y - X @ b).std()), 2)
    parts.append(g)
f = pd.concat(parts)
f["fav_sign"] = np.sign(f["Lo"])
f["fav_move"] = np.abs(f["Lc"]) - np.abs(f["Lo"])  # + = the opening favourite firmed (in |log-odds|)
# when the opening favourite flips, |L| still measures lopsidedness; fine for a lopsidedness move
f["tg_move"] = f["tg_close_line"] - f["tg_open_line"]
for bo in (3, 5):
    g = f[f["in_best_of"] == bo]
    z = (g["excess_open"] / g["excess_open"].std()).to_numpy()
    X = np.column_stack([z, np.abs(g["Lo"]), g["Lo"] ** 2, (g["tour"] == "wta").astype(float),
                         np.ones(len(g))])
    b, se, n = ols_cluster(X, g["fav_move"].to_numpy(float), g["week"].to_numpy())
    res[f"bo{bo}_fav_move_on_excess_open_per_sd"] = {"coef": round(float(b[0]), 5), "se": round(float(se[0]), 5),
                                                     "z": round(float(b[0] / se[0]), 2), "n": n,
                                                     "reading": "negative = when the total says closer than the "
                                                                "moneyline, the favourite drifts by the close"}
    zm = (g["fav_move"] / g["fav_move"].std()).to_numpy()
    X2 = np.column_stack([zm, np.abs(g["Lo"]), (g["tour"] == "wta").astype(float), np.ones(len(g))])
    b2, se2, n2 = ols_cluster(X2, g["tg_move"].to_numpy(float), g["week"].to_numpy())
    res[f"bo{bo}_tg_move_on_fav_move_per_sd"] = {"coef_games": round(float(b2[0]), 4), "se": round(float(se2[0]), 4),
                                                 "z": round(float(b2[0] / se2[0]), 2), "n": n2,
                                                 "reading": "negative = the total falls when the favourite firms"}
    res[f"bo{bo}_share_tg_move_ge_1"] = round(float((np.abs(g["tg_move"]) >= 1).mean()), 3)
    res[f"bo{bo}_corr_excess_open_close"] = round(float(np.corrcoef(g["excess_open"], g["excess_close"])[0, 1]), 3)
(OUT / "totals_flow.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
