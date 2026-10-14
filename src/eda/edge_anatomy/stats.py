"""Shared scoring helpers of the edge-anatomy study: paired log-loss gains with four-week-block intervals, verdict
words, the realisation coefficient and offset logistic fits."""
from __future__ import annotations

import numpy as np
from scipy.special import expit, logit
from scipy.stats import t as student_t

EPS = 1e-6


def lg(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, float), EPS, 1 - EPS))


def ll(p, y) -> np.ndarray:
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.where(np.asarray(y, bool), -np.log(p), -np.log(1 - p))


def mean_ci(v, clusters, scale: float = 1000.0, extra_var: float = 0.0) -> dict:
    """Mean with a cluster-sandwich interval over the clusters (t on G - 1), times scale. extra_var (in scaled units
    squared) is added to the variance (a seed term). p_better = the t CDF of est / se."""
    v = np.asarray(v, float)
    labels, ix = np.unique(clusters, return_inverse=True)
    G, n, m = len(labels), len(v), float(v.mean()) if len(v) else np.nan
    if G < 2:
        return {"est": scale * m, "lo": np.nan, "hi": np.nan, "se": np.nan, "p_better": np.nan, "n": int(n),
                "blocks": int(G)}
    infl = np.bincount(ix, weights=v - m)
    se = float(np.sqrt(G / (G - 1) * infl @ infl) / n) * scale
    se = float(np.sqrt(se ** 2 + extra_var))
    r = student_t.ppf(0.975, G - 1) * se
    est = scale * m
    return {"est": est, "lo": est - r, "hi": est + r, "se": se,
            "p_better": float(student_t.cdf(est / se, G - 1)) if se > 0 else np.nan, "n": int(n), "blocks": int(G)}


def gain(q_base, q_arm, y, clusters, extra_var: float = 0.0) -> dict:
    """1000 x mean(LL(base) - LL(arm)): + = the arm better."""
    return mean_ci(ll(q_base, y) - ll(q_arm, y), clusters, extra_var=extra_var)


def seed_term(qk_base: np.ndarray | None, qk_arm: np.ndarray | None, y) -> float:
    """The seed variance of a paired gain (scaled units squared): the variance over seeds k of the per-seed gain
    1000 x mean(LL(base_k) - LL(arm_k)), over the number of seeds (seeds matched by index); a side without seeds
    (a price) contributes its other side's seed variance alone."""
    y = np.asarray(y)
    if qk_base is None and qk_arm is None:
        return 0.0
    if qk_base is None:
        g = -1000 * ll(qk_arm, y[:, None]).mean(axis=0)
    elif qk_arm is None:
        g = 1000 * ll(qk_base, y[:, None]).mean(axis=0)
    else:
        g = 1000 * (ll(qk_base, y[:, None]).mean(axis=0) - ll(qk_arm, y[:, None]).mean(axis=0))
    return float(np.var(g, ddof=1) / len(g)) if len(g) > 1 else 0.0


def verdict(d: dict, label_better: str = "better", label_worse: str = "worse") -> str:
    if not np.isfinite(d.get("lo", np.nan)):
        return "—"
    if d["lo"] > 0:
        return label_better
    if d["hi"] < 0:
        return label_worse
    return f"unresolved (P {d['p_better']:.2f})"


def fmt(d: dict, digits: int = 2) -> str:
    if not np.isfinite(d.get("est", np.nan)):
        return "—"
    if not np.isfinite(d.get("lo", np.nan)):
        return f"{d['est']:+.{digits}f}"
    return f"{d['est']:+.{digits}f} [{d['lo']:+.{digits}f}, {d['hi']:+.{digits}f}]"


def fit_offset(X: np.ndarray, y: np.ndarray, offset: np.ndarray, ridge: np.ndarray | float = 1e-8,
               max_iter: int = 100, tol: float = 1e-10) -> tuple[np.ndarray, np.ndarray]:
    """Logistic regression without an intercept, with a fixed offset: logit p = offset + X b, b ridge-penalised
    (ridge * b'b / 2). Newton steps. Returns (b, the Hessian at the optimum)."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    k = X.shape[1]
    lam = np.full(k, ridge) if np.isscalar(ridge) else np.asarray(ridge, float)
    b = np.zeros(k)
    for _ in range(max_iter):
        p = expit(offset + X @ b)
        g = X.T @ (y - p) - lam * b
        H = (X.T * (p * (1 - p))) @ X + np.diag(lam)
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        b += step
        if np.abs(step).max() < tol:
            break
    p = expit(offset + X @ b)
    return b, (X.T * (p * (1 - p))) @ X + np.diag(lam)


def cluster_cov(X: np.ndarray, y: np.ndarray, offset: np.ndarray, b: np.ndarray, H: np.ndarray,
                clusters: np.ndarray) -> np.ndarray:
    """Cluster-robust (sandwich) covariance of an offset logistic fit's coefficients."""
    p = expit(offset + X @ b)
    s = X * (np.asarray(y, float) - p)[:, None]
    labels, ix = np.unique(clusters, return_inverse=True)
    S = np.zeros((len(labels), X.shape[1]))
    np.add.at(S, ix, s)
    G = len(labels)
    if G < 2:
        return np.full((X.shape[1], X.shape[1]), np.nan)
    Hi = np.linalg.inv(H)
    return G / (G - 1) * Hi @ (S.T @ S) @ Hi


def realisation(q_base, q_model, y, clusters) -> dict:
    """r in logit p = logit q_base + r (logit q_model - logit q_base): 1 = the model's disagreement right-sized,
    below 1 = too far, above 1 = not far enough. Cluster-robust SE."""
    off = lg(q_base)
    d = (lg(q_model) - off)[:, None]
    b, H = fit_offset(d, y, off)
    V = cluster_cov(d, y, off, b, H, clusters)
    return {"r": float(b[0]), "se": float(np.sqrt(V[0, 0])), "spread": float(np.std(d))}
