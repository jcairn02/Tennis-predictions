"""Harness verifier: shared helpers for planted-effect simulations on the real frame with SYNTHETIC outcomes.

The real current-best log-odds eta (screen.load()'s z_model) and real candidate-like columns; outcomes are drawn as
y ~ Bernoulli(sigmoid(a_tour * eta + beta * x [+ v_A - v_B])), a = 0.89 men, 0.91 women, optional career-long player
effects v ~ N(0, tau^2). Real results are never used here (the frame's a_won is overwritten before any fit).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit

from src.eda.feature_interactions import screen as S

A_TOUR = {"atp": 0.89, "wta": 0.91}


def nuisance_fixed(f: pd.DataFrame, rows: np.ndarray, base: str, per_season: bool, prep) -> np.ndarray:
    """screen.nuisance with the verifier's proposed fix (bug B1): with one slope per tour, both tour columns are always
    present, so a design built on rows without one tour (the men's 2018 season has no matches) keeps the fit's width."""
    eta = f[f"z_{base}"].to_numpy(float)[rows]
    tour = f["tour"].to_numpy()[rows]
    season = f["season"].to_numpy()[rows]
    cols = []
    keys = sorted(set(zip(tour, season))) if per_season else [(t, None) for t in S.C.TOURS]
    for t, s in keys:
        m = (tour == t) if s is None else ((tour == t) & (season == s))
        if m.any() or s is None:
            cols.append(np.where(m, eta, 0.0))
    for t in S.C.TOURS:
        cols.append(np.where(tour == t, eta ** 3 / prep.cube_sd[t], 0.0))
    return np.column_stack(cols)


def patch_nuisance() -> None:
    S.nuisance = nuisance_fixed


def base_logit(F: pd.DataFrame) -> np.ndarray:
    a = np.where(F["tour"].to_numpy() == "atp", A_TOUR["atp"], A_TOUR["wta"])
    return a * F["z_model"].to_numpy(float)


def std_disc(F: pd.DataFrame, x: np.ndarray) -> np.ndarray:
    """x / its SD on the discovery rows, NaN -> 0 (the planted truth; no clipping)."""
    x = np.asarray(x, float)
    disc = (F["window"] == "discovery").to_numpy()
    return np.nan_to_num(x / np.nanstd(x[disc]), nan=0.0)


def player_effects(F: pd.DataFrame, tau: float, rng) -> np.ndarray:
    if tau <= 0:
        return np.zeros(len(F))
    ids = pd.unique(np.r_[F["player_a_id"].astype(str).to_numpy(), F["player_b_id"].astype(str).to_numpy()])
    v = dict(zip(ids, rng.normal(0, tau, len(ids))))
    return np.array([v[p] for p in F["player_a_id"].astype(str)]) - np.array([v[p] for p in F["player_b_id"].astype(str)])


def null_design(F: pd.DataFrame, rows: np.ndarray, controls: np.ndarray | None, prep) -> np.ndarray:
    N = S.nuisance(F, rows, "model", True, prep)
    return N if controls is None else np.column_stack([N, controls[rows]])


def gain_nats(F: pd.DataFrame, lin: np.ndarray, Cs: np.ndarray | None, prep) -> dict:
    """Population-averaged gain of the true model sigmoid(lin) over the best model without the planted term (the
    screen's null design per window, fitted to the true probabilities): mean KL, per window and pooled."""
    p1 = expit(lin)
    out, tot = {}, 0.0
    for w in ("discovery", "replication"):
        rows = (F["window"] == w).to_numpy()
        Z = null_design(F, rows, Cs, prep)
        _, p0, _ = S.fit(Z, p1[rows])
        q1, q0 = p1[rows], np.clip(p0, 1e-12, 1 - 1e-12)
        kl = q1 * np.log(q1 / q0) + (1 - q1) * np.log((1 - q1) / (1 - q0))
        out[w] = float(kl.mean())
        tot += float(kl.sum())
    out["pooled"] = tot / len(F)
    return out


def calibrate(F: pd.DataFrame, x0: np.ndarray, delta_mll: float, Cs=None, prep=None, extra=None) -> tuple[float, dict]:
    """beta such that the pooled gain of beta * x0 (x0 already standardised) is delta_mll milli-nats."""
    base = base_logit(F) + (0 if extra is None else extra)
    if prep is None:
        _, _, prep = S.prepare(F, S.Hypothesis("cal", x0), "model")
    beta = 0.05
    for _ in range(4):
        g = gain_nats(F, base + beta * x0, Cs, prep)
        beta *= np.sqrt(delta_mll / 1000 / g["pooled"])
    return float(beta), gain_nats(F, base + beta * x0, Cs, prep)


def draw(F: pd.DataFrame, lin: np.ndarray, rng) -> np.ndarray:
    return rng.random(len(F)) < expit(lin)
