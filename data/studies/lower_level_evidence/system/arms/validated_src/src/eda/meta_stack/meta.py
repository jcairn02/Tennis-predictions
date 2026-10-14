"""The meta-models and their walk-forward fits (pure functions; tests in test/meta_stack/).

Every meta-model is a logistic regression per tour WITHOUT an intercept, on log-odds that A wins. Side A is random, so
every input is antisymmetric (it changes sign when A and B are swapped) and the meta-model's forecast for B is exactly
one minus its forecast for A; an intercept would only add noise (its true value is zero).

The owner's model has three inputs: the no-odds model z_M, the closing line z_C and their difference. On the log-odds
scale the difference is z_M - z_C, an exact linear combination of the other two, so

    b_C z_C + b_M z_M + b_D (z_M - z_C) = (b_C - b_D) z_C + (b_M + b_D) z_M

and the three-input model makes the same forecasts as the two-input one (S2). Its coefficients are not identified (any
b_D fits equally well), only their combinations are. "S3lit" keeps the literal three inputs to show this numerically.
The difference adds something only if it enters non-linearly: on the probability scale (S3p), or with a weight that
changes with the size of the disagreement (S3q: d|d|, d = z_M - z_C). The log of the probability ratio, log(p_M / p_C),
is not antisymmetric; its antisymmetric part is (z_M - z_C) / 2, collinear again.
"""
from __future__ import annotations

from typing import Callable, Iterable

import numpy as np
from scipy.special import expit

from src.eda.meta_stack import common as C
from src.eda.tabpfn_thinking import common as T

Z = dict[str, np.ndarray]           # log-odds that A wins: "mkt" (closing line), "noodds", "base" (with odds)

SPECS: dict[str, Callable[[Z], list[np.ndarray]]] = {
    "mkt": lambda z: [z["mkt"]],                                             # the closing line, one slope
    "best": lambda z: [z["base"]],                                           # the current best: one slope on base
    "S2": lambda z: [z["mkt"], z["noodds"]],                                 # the owner's model (difference drops out)
    "S3lit": lambda z: [z["mkt"], z["noodds"], z["noodds"] - z["mkt"]],      # literally three inputs: rank two
    "S3p": lambda z: [z["mkt"], z["noodds"], expit(z["noodds"]) - expit(z["mkt"])],
    "S3q": lambda z: [z["mkt"], z["noodds"], (z["noodds"] - z["mkt"]) * np.abs(z["noodds"] - z["mkt"])],
    "E1": lambda z: [z["base"], z["noodds"]],                                # does noodds add to the current best?
    "E2": lambda z: [z["mkt"], z["base"]],                                   # the current best with its own market weight
}
LABELS = {
    "mkt": "closing line, one slope per tour",
    "best": "current best: TabPFN with the odds, one slope per tour",
    "S2": "meta-model: closing line + TabPFN without the odds (+ their log-odds difference, which drops out)",
    "S3lit": "the same with the log-odds difference kept as a third column (rank 2: same forecasts as S2)",
    "S3p": "S2 + the probability difference p_M - p_C",
    "S3q": "S2 + the signed square of the log-odds difference, d|d|",
    "E1": "current best + TabPFN without the odds",
    "E2": "closing line + current best (separate weights)",
}


def design(spec: str, z: Z) -> np.ndarray:
    return np.column_stack(SPECS[spec](z))


def fit(spec: str, z: Z, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Maximum likelihood, no intercept (T.fit_logistic: Newton steps, a 1e-8 ridge against a singular Hessian)."""
    return T.fit_logistic(design(spec, z), y)


def predict(spec: str, z: Z, beta: np.ndarray) -> np.ndarray:
    return expit(design(spec, z) @ beta)


def take(z: Z, mask: np.ndarray) -> Z:
    return {k: v[mask] for k, v in z.items()}


# ------------------------------------------------------------------------------------------------
# Which out-of-sample seasons train the meta-learner for a target season

def window(kind: str, target: int, first: int = 2014) -> list[int]:
    """Calendar seasons whose out-of-sample forecasts train the meta-learner for ``target``.

    from<YYYY>    every season from YYYY to the season before (expanding; the current best uses from2019)
    last<W>       the W seasons before the target (rolling)
    """
    if kind.startswith("from"):
        return list(range(int(kind[4:]), target))
    if kind.startswith("last"):
        w = int(kind[4:])
        return list(range(max(target - w, first), target))
    raise ValueError(kind)


def walk_forward(spec: str, z: Z, y: np.ndarray, year: np.ndarray, tour: np.ndarray, targets: Iterable[int],
                 seasons: Callable[[int], list[int]]) -> tuple[np.ndarray, dict]:
    """Forecasts for the target seasons, each from a meta-learner fitted per tour on ``seasons(target)`` only (all
    earlier than the target). Returns the forecasts (NaN outside the targets or where a tour's window is empty) and the
    coefficients per (target, tour)."""
    p = np.full(len(y), np.nan)
    coefs = {}
    for t in targets:
        use = seasons(t)
        if any(s >= t for s in use):
            raise ValueError(f"window for {t} reaches the target: {use}")
        for tr in C.TOURS:
            train = (tour == tr) & np.isin(year, use)
            test = (tour == tr) & (year == t)
            if not test.any() or not train.any():
                continue
            b, se = fit(spec, take(z, train), y[train])
            p[test] = predict(spec, take(z, test), b)
            coefs[(t, tr)] = {"beta": b.tolist(), "se": se.tolist(), "n": int(train.sum()), "seasons": use}
    return p, coefs


# ------------------------------------------------------------------------------------------------
# The quantities the design argument needs

def sandwich(spec: str, z: Z, y: np.ndarray, beta: np.ndarray, clusters: np.ndarray | None = None) -> dict:
    """Per-match Fisher information J (mean Hessian of the log loss), score covariance K (iid, or summed within
    clusters), and tr(J^-1 K): the expected excess log loss of the fitted meta-learner on new matches is
    tr(J^-1 K) / (2 n) nats per match (Takeuchi's correction; = k / (2 n) when the model is right and matches are
    independent)."""
    X = design(spec, z)
    p = expit(X @ beta)
    n = len(y)
    J = (X.T * (p * (1 - p))) @ X / n
    s = X * (y - p)[:, None]
    if clusters is None:
        K = s.T @ s / n
    else:
        _, ix = np.unique(clusters, return_inverse=True)
        S = np.zeros((ix.max() + 1, X.shape[1]))
        np.add.at(S, ix, s)
        K = S.T @ S / n
    Ji = np.linalg.pinv(J)
    return {"J": J, "K": K, "tr": float(np.trace(Ji @ K)), "n": n, "cov": Ji @ K @ Ji / n}
