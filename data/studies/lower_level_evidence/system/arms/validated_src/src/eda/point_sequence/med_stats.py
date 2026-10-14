"""Regression helpers for the E1 medical-event gate (med_*.py): numpy only (statsmodels is not in the env).

    poisson_fit   modified Poisson (log link on a 0/1 or count endpoint), IRLS, cluster-robust sandwich variance
    wls_fit       weighted least squares, cluster-robust sandwich variance
    logit_fit     logistic regression (propensity scores), IRLS
    mh_rr         Mantel-Haenszel risk ratio with the Greenland-Robins variance
    holm          Holm step-down adjusted p-values
    design        a numeric design matrix from numeric and categorical columns, with fixed reference levels

Nuisance coefficients carry a tiny ridge (``ridge``, default 1e-6 times the number of rows) so that a sparse covariate
cell without events cannot make the Newton steps diverge; the exposure and the intercept are never penalised.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats


def _cluster_meat(scores: np.ndarray, cluster: np.ndarray) -> tuple[np.ndarray, int]:
    """Sum of outer products of the per-cluster score sums."""
    codes, inv = np.unique(cluster, return_inverse=True)
    g = np.zeros((len(codes), scores.shape[1]))
    np.add.at(g, inv, scores)
    return g.T @ g, len(codes)


def _penalty(k: int, free: list[int], lam: float) -> np.ndarray:
    p = np.full(k, lam)
    p[free] = 0.0
    return np.diag(p)


def poisson_fit(y, X, cluster, w=None, free=(0, 1), ridge=1e-6, max_iter=100, tol=1e-10) -> dict:
    """Poisson regression, log link. Returns coef, cluster-robust cov, convergence flag.

    ``free`` lists the columns left unpenalised (by convention 0 = intercept, 1 = exposure).
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    w = np.ones(n) if w is None else np.asarray(w, dtype=float)
    P = _penalty(k, list(free), ridge * n)
    beta = np.zeros(k)
    beta[0] = math.log(max(np.average(y, weights=w), 1e-12))
    converged = False
    for _ in range(max_iter):
        eta = np.clip(X @ beta, -50, 50)
        mu = np.exp(eta)
        grad = X.T @ (w * (y - mu)) - P @ beta
        H = (X * (w * mu)[:, None]).T @ X + P
        step = np.linalg.solve(H, grad)
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            converged = True
            break
    mu = np.exp(np.clip(X @ beta, -50, 50))
    H = (X * (w * mu)[:, None]).T @ X + P
    Hi = np.linalg.inv(H)
    scores = X * (w * (y - mu))[:, None]
    meat, G = _cluster_meat(scores, np.asarray(cluster))
    cov = Hi @ meat @ Hi * (G / (G - 1))
    return {"coef": beta, "cov": cov, "converged": converged, "n": n, "clusters": G, "events": float((w * y).sum())}


def wls_fit(y, X, w, cluster) -> dict:
    """Weighted least squares with a player-clustered sandwich variance (Stata's small-sample factor)."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    w = np.asarray(w, dtype=float)
    n, k = X.shape
    XtW = (X * w[:, None]).T
    A = XtW @ X
    Ai = np.linalg.pinv(A)
    beta = Ai @ (XtW @ y)
    e = y - X @ beta
    scores = X * (w * e)[:, None]
    meat, G = _cluster_meat(scores, np.asarray(cluster))
    c = (G / (G - 1)) * ((n - 1) / max(n - k, 1))
    cov = Ai @ meat @ Ai * c
    return {"coef": beta, "cov": cov, "converged": True, "n": n, "clusters": G}


def logit_fit(y, X, ridge=1e-6, max_iter=100, tol=1e-10) -> np.ndarray:
    """Logistic regression coefficients (column 0 = intercept, unpenalised; tiny ridge on the rest)."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    P = _penalty(k, [0], ridge * n)
    beta = np.zeros(k)
    pbar = min(max(y.mean(), 1e-6), 1 - 1e-6)
    beta[0] = math.log(pbar / (1 - pbar))
    for _ in range(max_iter):
        p = 1 / (1 + np.exp(-np.clip(X @ beta, -50, 50)))
        grad = X.T @ (y - p) - P @ beta
        H = (X * (p * (1 - p))[:, None]).T @ X + P
        step = np.linalg.solve(H, grad)
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    return beta


def logit_predict(beta, X) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(np.asarray(X, dtype=float) @ beta, -50, 50)))


def coef_summary(fit: dict, j: int = 1, log_scale: bool = False) -> dict:
    """Estimate, 95% Wald interval and two-sided p for coefficient j (exponentiated when log_scale)."""
    b = float(fit["coef"][j])
    se = float(math.sqrt(max(fit["cov"][j, j], 0.0)))
    z = b / se if se > 0 else float("nan")
    p = float(2 * stats.norm.sf(abs(z))) if se > 0 else float("nan")
    lo, hi = b - 1.959963984540054 * se, b + 1.959963984540054 * se
    if log_scale:
        return {"est": math.exp(b), "lo": math.exp(lo), "hi": math.exp(hi), "beta": b, "se": se, "p": p}
    return {"est": b, "lo": lo, "hi": hi, "beta": b, "se": se, "p": p}


def mh_rr(y, x, strata) -> dict:
    """Mantel-Haenszel risk ratio of 0/1 endpoint y for 0/1 exposure x across strata (Greenland-Robins variance)."""
    d = pd.DataFrame({"y": np.asarray(y, float), "x": np.asarray(x, int), "s": np.asarray(strata)})
    num = den = vnum = 0.0
    for _, g in d.groupby("s"):
        n1 = (g["x"] == 1).sum()
        n0 = (g["x"] == 0).sum()
        if n1 == 0 or n0 == 0:
            continue
        a = g.loc[g["x"] == 1, "y"].sum()
        b = g.loc[g["x"] == 0, "y"].sum()
        N = n1 + n0
        num += a * n0 / N
        den += b * n1 / N
        vnum += (n1 * n0 * (a + b) - a * b * N) / N ** 2
    if num <= 0 or den <= 0:
        return {"est": float("nan"), "lo": float("nan"), "hi": float("nan"), "p": float("nan")}
    lrr = math.log(num / den)
    se = math.sqrt(vnum / (num * den))
    z = lrr / se
    return {"est": math.exp(lrr), "lo": math.exp(lrr - 1.96 * se), "hi": math.exp(lrr + 1.96 * se),
            "p": float(2 * stats.norm.sf(abs(z))), "se": se}


def holm(p: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order."""
    p = np.asarray(p, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def design(df: pd.DataFrame, numeric: list[str], categorical: dict[str, list], first: list[str] | None = None,
           drop_empty: bool = True) -> tuple[np.ndarray, list[str]]:
    """Intercept, the ``first`` columns (in order: the exposure goes here), numeric columns, then one dummy per
    non-reference level of each categorical (``categorical`` maps a column to its levels; the first level is the
    reference). Empty dummy columns are dropped when ``drop_empty``."""
    cols = [np.ones(len(df))]
    names = ["const"]
    for c in (first or []) + numeric:
        cols.append(pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float))
        names.append(c)
    for c, levels in categorical.items():
        v = df[c].astype(object).to_numpy()
        for lev in levels[1:]:
            col = (v == lev).astype(float)
            if drop_empty and col.sum() == 0:
                continue
            cols.append(col)
            names.append(f"{c}={lev}")
    X = np.column_stack(cols)
    if np.isnan(X).any():
        bad = [names[j] for j in range(X.shape[1]) if np.isnan(X[:, j]).any()]
        raise ValueError(f"missing values in design columns: {bad}")
    return X, names
