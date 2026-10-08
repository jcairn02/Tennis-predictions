"""Scoring of the TabPFN arms (plan.md: M8's deployment and harm checks, M9's final test, H-S2), on forecasts written by
local_fits.py. Nothing here runs on 2025-2026 except `final_test`, once, after the final pre-registration is hashed.

    forecasts(arm, seeds, seasons)       seed-mean symmetrised P(A wins) by match id (this study's fits, or the rating
                                         race's for arm "model", seeds 0-2, from 2019)
    encompassing(F, eta_b, dev)          logit P = sum_{tour, season} a eta_B + sum_tour c eta_B^3 + b dev, no intercept;
                                         b with the union-clustered variance (four-week blocks and shared players) and
                                         t on G - 1 degrees of freedom; dev = eta_arm - eta_B from DISJOINT seeds
                                         (the critique's 1.7: shared seeds reward the averaging of fit noise)
    calibrated(F, col)                   one slope per tour on the log-odds, refitted each season on all earlier
                                         out-of-sample seasons from 2019 (the decided calibration)
    paired_gain(F, pa, pb)               mLL, positive = pb better; four-week-block interval
    capture(F, dev, term)                slope of the arm's deviation on the screen's term b_hat x (M8: >= 0.5 deploys
                                         the candidate as a TabPFN column, otherwise as a nudge)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions import screen as S
from src.eda.tabpfn_thinking import common as T


def forecasts(arm: str, seeds, seasons, block: str = "td") -> pd.Series:
    parts = []
    for season in seasons:
        per = []
        for seed in seeds:
            name = f"{arm}__{season}__seed{seed}.npz"
            path = C.LOCAL / name
            if not path.exists() and arm == "model" and (C.RACE_LOCAL / name).exists():
                path = C.RACE_LOCAL / name
            if not path.exists():
                raise FileNotFoundError(path)
            with np.load(path, allow_pickle=False) as z:
                p, ids = z[f"p_{block}"], z[f"ids_{block}"]
                k = len(ids)
                per.append(pd.Series(T.symmetrize(p[:k], p[k:]), index=ids.astype(str)))
        parts.append(pd.concat(per, axis=1).mean(axis=1))
    return pd.concat(parts)


def frame(seasons, with_players: bool = True) -> pd.DataFrame:
    """The model frame's matches of the given seasons, debut seasons out, with players and four-week blocks."""
    f = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "tour", "season", "tournament_date", "a_won",
                                                "debut_season", "in_odds_logit"])
    f = f[f["season"].isin(list(seasons)) & ~f["debut_season"].astype(bool)].reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    if with_players:
        s0 = pd.read_parquet(S.PRE_REBUILD_STAGE0, columns=["match_id", "player_a_id", "player_b_id"])
        s0["match_id"] = s0["match_id"].astype(str)
        f = f.merge(s0, on="match_id", how="left", validate="one_to_one")
    f["block"] = T.blocks(f["tournament_date"].to_numpy(), 28)
    return f


def encompassing(f: pd.DataFrame, eta_b: np.ndarray, dev: np.ndarray) -> dict:
    eta_b, dev = np.asarray(eta_b, float), np.asarray(dev, float)
    tour, season = f["tour"].to_numpy(), f["season"].to_numpy()
    cols = []
    for t_, s_ in sorted(set(zip(tour, season))):
        cols.append(np.where((tour == t_) & (season == s_), eta_b, 0.0))
    for t_ in C.TOURS:
        if not (tour == t_).any():           # a subset holding one tour (the final test's verifier, bug 1)
            continue
        e3 = np.where(tour == t_, eta_b ** 3, 0.0)
        sd = np.std(e3[tour == t_]) or 1.0
        cols.append(e3 / sd)
    sd_dev = float(np.std(dev)) or 1.0
    Z = np.column_stack(cols + [dev / sd_dev])
    y = f["a_won"].to_numpy(float)
    beta, p, H = S.fit(Z, y)
    j = Z.shape[1] - 1
    a_j = np.linalg.solve(H, np.eye(Z.shape[1])[j])
    u = (y - p) * (Z @ a_j)
    v = S.clustered_variances(u, f["block"].to_numpy(), f["player_a_id"].to_numpy(str), f["player_b_id"].to_numpy(str))
    var = max(v.values())
    G = len(np.unique(f["block"]))
    b = float(beta[j]) / sd_dev                       # per unit of the deviation's log-odds
    se = float(np.sqrt(var)) / sd_dev
    tval = b / se
    return {"b": b, "se": se, "t": tval, "df": G - 1, "p_one_sided": float(student_t.sf(tval, G - 1)),
            "p_two_sided": float(2 * student_t.sf(abs(tval), G - 1)),
            "lo": b - student_t.ppf(0.975, G - 1) * se, "hi": b + student_t.ppf(0.975, G - 1) * se,
            "n": int(len(f)), "blocks": G, "sd_dev": sd_dev}


def calibrated(f: pd.DataFrame, p: np.ndarray, oos: pd.DataFrame | None = None) -> np.ndarray:
    """One slope per tour on logit p, for each season fitted on all earlier out-of-sample seasons from 2019 (oos: a frame
    with match_id, tour, season, a_won and p covering those seasons; default: f itself)."""
    oos = f.assign(p=p) if oos is None else oos
    out = np.full(len(f), np.nan)
    z_all = C.lg(oos["p"].to_numpy(float))
    y_all = oos["a_won"].to_numpy(float)
    for season in sorted(f["season"].unique()):
        for tour in C.TOURS:
            fit_rows = ((oos["season"] >= C.CALIB_FROM) & (oos["season"] < season) & (oos["tour"] == tour)).to_numpy()
            rows = ((f["season"] == season) & (f["tour"] == tour)).to_numpy()
            if fit_rows.sum() < 1000 or not rows.any():
                continue
            beta, _ = T.fit_logistic(z_all[fit_rows][:, None], y_all[fit_rows])
            out[rows] = expit(beta[0] * C.lg(np.asarray(p, float)[rows]))
    return out


def paired_gain(f: pd.DataFrame, pa: np.ndarray, pb: np.ndarray, rows: np.ndarray | None = None) -> dict:
    """pb against pa in mLL (positive = pb has the lower log loss, better), four-week-block interval."""
    rows = np.ones(len(f), bool) if rows is None else rows
    ok = rows & np.isfinite(pa) & np.isfinite(pb)
    y = f["a_won"].to_numpy(bool)[ok]
    return T.compare(T.ll(np.asarray(pa)[ok], y), T.ll(np.asarray(pb)[ok], y), f.loc[ok, "tournament_date"].to_numpy())


def capture(dev: np.ndarray, term: np.ndarray) -> float:
    """OLS slope without intercept of the arm's deviation from base on the screen's term b_hat x (both log-odds)."""
    dev, term = np.asarray(dev, float), np.asarray(term, float)
    ok = np.isfinite(dev) & np.isfinite(term)
    return float(np.dot(dev[ok], term[ok]) / np.dot(term[ok], term[ok]))
