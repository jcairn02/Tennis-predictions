"""Shared loading and scoring for the market-anchoring study (men's main tour).

One row per match, in the orientation of the 2026 TabPFN frame (random A/B).
Joins: the frozen 36-input frame, raw closing odds, the repaired Elo components,
the annual out-of-sample sporting forecasts, and the one 2026 TabPFN forecast.
Nothing upstream is written; every artifact goes to data/studies/market_anchoring.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

for _key in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_key, "1")

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.feature_alpha_audit import profile_retest as P
from src.eda.feature_alpha_audit import elo_retest as E
from src.eda.predictive_frontier.features import FEATURE_COLUMNS, FEATURE_GROUPS
from src.eda.predictive_frontier.score import STRONG

OUT = ROOT / "data/studies/market_anchoring"
TABPFN = ROOT / "data/studies/predictive_frontier_tabpfn"
REPAIRS = ROOT / "data/studies/feature_alpha_audit/repairs"
FRONTIER = ROOT / "data/studies/predictive_frontier"
ODDS = ROOT / "data/studies/predictability_diagnostic/stage1_odds.parquet"
SPORTS = STRONG + FEATURE_COLUMNS
PROFILE = P.PROFILE
ELO_SCALE = np.log(10) / 400
SURFACE_WEIGHT = {"atp": 0.30, "wta": 0.25}   # frozen Stage 1 blend, checked in load_atp()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=float), encoding="utf-8")


def clip_logit(p):
    return logit(np.clip(np.asarray(p, dtype=float), 1e-10, 1 - 1e-10))


def load_atp() -> pd.DataFrame:
    """The 2013-2026 men's common cohort with every column the study needs."""
    f = pd.read_parquet(TABPFN / "frame.parquet")
    odds = pd.read_parquet(ODDS, columns=["match_id", "avg_a", "avg_b", "max_a", "max_b", "ps_a", "ps_b",
                                          "b365_a", "b365_b", "overround_avg", "overround_ps"])
    f = f.merge(odds, on="match_id", how="left", validate="one_to_one")
    elo = pd.read_parquet(REPAIRS / "repair_matches.parquet",
                          columns=["match_id", "elo_a", "elo_b", "elo_n_a", "elo_n_b", "elo_surf_a", "elo_surf_b",
                                   "elo_surf_n_a", "elo_surf_n_b"])
    f = f.merge(elo, on="match_id", how="left", validate="one_to_one")
    sa = np.where(f.elo_surf_a.isna(), f.elo_a, f.elo_surf_a)
    sb = np.where(f.elo_surf_b.isna(), f.elo_b, f.elo_surf_b)
    f["elo_overall"] = ELO_SCALE * (f.elo_a - f.elo_b)
    f["elo_surface_only"] = ELO_SCALE * (sa - sb)
    f["elo_surface_gap"] = f.elo_surface_only - f.elo_overall
    w = SURFACE_WEIGHT["atp"]
    if np.nanmax(np.abs((1 - w) * f.elo_overall + w * f.elo_surface_only - f.elo_logit)) > 1e-9:
        raise ValueError("Elo components do not reproduce the frozen surface blend")
    pred = pd.read_parquet(FRONTIER / "predictions.parquet",
                           columns=["match_id", "route", "a_won", "baseline", "combined"])
    pred = pred[pred.route.eq("elo")].drop(columns="route")
    pred = pred.rename(columns={"baseline": "p_sport9", "combined": "p_sport36", "a_won": "a_won_pred"})
    f = f.merge(pred, on="match_id", how="left", validate="one_to_one")
    both = f.a_won_pred.notna()
    if not (f.loc[both, "a_won_pred"].astype(bool) == f.loc[both, "a_won"].astype(bool)).all():
        raise ValueError("Out-of-sample forecast orientation differs from the frame")
    tab = pd.read_parquet(TABPFN / "test_predictions.parquet", columns=["match_id", "tabpfn", "a_won"])
    f = f.merge(tab.rename(columns={"a_won": "a_won_tab"}), on="match_id", how="left", validate="one_to_one")
    both = f.a_won_tab.notna()
    if not (f.loc[both, "a_won_tab"].astype(bool) == f.loc[both, "a_won"].astype(bool)).all():
        raise ValueError("TabPFN orientation differs from the frame")
    f = f.drop(columns=["a_won_pred", "a_won_tab"])
    f["a_won"] = f.a_won.astype(float)
    f["tournament_date"] = pd.to_datetime(f.tournament_date)
    days = (f.tournament_date - pd.Timestamp("2010-01-04")).dt.days
    f["block4week"] = (days // 28).astype(int)
    f["week"] = (days // 7).astype(int)
    f["event"] = f.tournament_id.astype(str) + "|" + f.tournament_date.dt.strftime("%Y-%m-%d")
    f["month"] = pd.to_datetime(f.match_date).dt.month.fillna(f.tournament_date.dt.month).astype(int)
    for book in ("avg", "ps"):
        p = f[f"p_{book}_a"]
        f[f"mkt_{book}"] = np.where(np.isfinite(p), clip_logit(p), np.nan)
    if not np.isfinite(f.loc[f.year.eq(2026), "p_avg_a"]).all():
        raise ValueError("2026 average closing prices are expected to be complete")
    return f.sort_values(["year", "tournament_date", "match_id"], kind="stable").reset_index(drop=True)


def ll(y, p) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))


def gain(frame: pd.DataFrame, model, reference, mask=None) -> dict:
    """Paired gain in milli-log-loss (positive = model better), 4-week clustered 95% interval."""
    y = frame.a_won.to_numpy(dtype=float)
    delta = ll(y, reference) - ll(y, model)
    keep = np.isfinite(delta) if mask is None else (np.asarray(mask, dtype=bool) & np.isfinite(delta))
    if keep.sum() < 30:
        return {"n": int(keep.sum()), "gain_mll": None, "lo_mll": None, "hi_mll": None}
    r = P.clustered_interval(delta[keep], frame.block4week.to_numpy()[keep])
    return {"n": int(keep.sum()), "gain_mll": r["gain_mll"], "lo_mll": r["lo_mll"], "hi_mll": r["hi_mll"],
            "model_ll": float(ll(y[keep], np.asarray(model)[keep]).mean()),
            "reference_ll": float(ll(y[keep], np.asarray(reference)[keep]).mean())}


def walk(frame: pd.DataFrame, columns: list[str], market: str | None, fixed: bool, tune: bool = True,
         train_from: int = 2013) -> np.ndarray:
    """Annual expanding logistic fits, ridge picked on the prior two seasons (the audit's walk_model).

    market is a probability column (p_avg_a or p_ps_a); fixed=True holds its logit as an offset with
    slope 1, fixed=False gives it an unpenalized slope. market=None fits the columns alone, all
    ridge-penalized. Rows with any missing input are left NaN.
    """
    cols = list(columns)
    need = cols + ([market] if market else [])
    keep = frame.year.ge(train_from).to_numpy() & np.isfinite(frame[need].to_numpy(dtype=float)).all(axis=1)
    g = frame.loc[keep].reset_index(drop=True)
    out = np.full(len(frame), np.nan)
    if market is None:
        eta = walk_model(g, cols, None, True, tune)
    else:
        eta = walk_model(g, cols, market, fixed, tune)
    out[np.flatnonzero(keep)] = expit(eta)
    return out


GRID = (0.0001, 0.001, 0.01, 0.1)   # positive only: the frontier short/long/momentum columns are collinear


def walk_model(frame: pd.DataFrame, cols: list[str], market: str | None, fixed: bool, tune: bool,
               grid=GRID) -> np.ndarray:
    """P.walk_model with a positive ridge grid: train on every earlier season, pick the ridge on the
    prior two seasons' out-of-season losses (default 0.01 below 300 validation rows)."""
    x = frame[cols].to_numpy(dtype=float)
    y = frame.a_won.to_numpy(dtype=float)
    years = frame.year.to_numpy()
    base = np.zeros(len(frame)) if market is None else clip_logit(frame[market])
    free = market is not None and not fixed
    grid = grid if tune else (0.01,)
    eta_all = np.full((len(frame), len(grid)), np.nan)
    loss_all = np.full_like(eta_all, np.nan)
    chosen_eta = np.full(len(frame), np.nan)
    for year in sorted(set(years)):
        tr, te = years < year, years == year
        if tr.sum() < 300:
            continue
        scale = P.rms_scale(x[tr])
        xt, xv = x[tr] / scale, x[te] / scale
        if free:
            zt, zv, off, add = np.column_stack([base[tr], xt]), np.column_stack([base[te], xv]), np.zeros(tr.sum()), 0
        else:
            zt, zv, off, add = xt, xv, base[tr], base[te]
        for j, ridge in enumerate(grid):
            pen = np.full(zt.shape[1], ridge)
            if free:
                pen[0] = 0.0
            b = P.fit_logistic(zt, y[tr], off, pen)
            eta_all[te, j] = zv @ b + add
            loss_all[te, j] = P.ll(y[te], eta_all[te, j])
        valid = (years < year) & (years >= year - 2) & np.isfinite(loss_all).all(axis=1)
        j = int(np.argmin(loss_all[valid].mean(axis=0))) if valid.sum() >= 300 else list(grid).index(0.01)
        chosen_eta[te] = eta_all[te, j]
    return chosen_eta


def calibrated(frame: pd.DataFrame, market: str, train_from: int = 2013) -> np.ndarray:
    """Annual expanding slope calibration of a market probability column."""
    keep = frame.year.ge(train_from).to_numpy() & np.isfinite(frame[market].to_numpy(dtype=float))
    g = frame.loc[keep].reset_index(drop=True)
    out = np.full(len(frame), np.nan)
    out[np.flatnonzero(keep)] = expit(P.market_calibration(g, market))
    return out


def cluster_logit(x: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unpenalized no-intercept logistic fit with cluster-robust (sandwich) standard errors."""
    beta = P.fit_logistic(x, y, np.zeros(len(y)), np.zeros(x.shape[1]))
    p = expit(x @ beta)
    hess = (x.T * (p * (1 - p))) @ x
    ids, inv = np.unique(np.asarray(clusters), return_inverse=True)
    score = np.zeros((len(ids), x.shape[1]))
    np.add.at(score, inv, x * (y - p)[:, None])
    g = len(ids)
    bread = np.linalg.inv(hess)
    cov = bread @ (score.T @ score) @ bread * g / (g - 1)
    return beta, np.sqrt(np.diag(cov))
