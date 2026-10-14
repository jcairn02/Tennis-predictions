"""Removing the margin from two-way prices, and scoring them by log loss, for the sharp-benchmark study.

Decimal odds o give implied probabilities q = 1/o. A bookmaker's pair sums to S = q_w + q_l > 1; the excess is
its margin (the overround, or "juice"). Three standard ways to take it out, each giving the winner's chance:
    proportional   p_w = q_w / S                  the project's convention (normalise the pair to sum to one)
    power          p_w = q_w ** k, with k such that q_w ** k + q_l ** k = 1
    shin           p_w = (1 + q_w - q_l) / 2      Shin's insider-trading model. With two outcomes its solution
                                                  does not depend on the insider share z and reduces to this
                                                  closed form, which is also "take half the margin off each side"
                                                  (checked against a numerical solve in the tests)
Betfair's back prices have a small overround of their own (best back on each side; commission is charged on
winnings, not built into the price), so the same three apply. A Polymarket price needs none of them: its two
outcomes are one book, so the second outcome's chance is one minus the first's.

Log loss is -log of the chance given to the player who won, in nats, averaged over matches. Lower is better;
differences are reported in thousandths (milli-log-loss), as in the project's other studies.
"""
from __future__ import annotations

import numpy as np

METHODS = ("proportional", "power", "shin")
P_FLOOR = 1e-6  # keeps -log finite for a price of exactly 0 or 1; no quote in the study reaches it


def implied(odds_w, odds_l) -> tuple[np.ndarray, np.ndarray]:
    return 1.0 / np.asarray(odds_w, dtype=float), 1.0 / np.asarray(odds_l, dtype=float)


def proportional(q_w, q_l) -> np.ndarray:
    q_w, q_l = np.asarray(q_w, dtype=float), np.asarray(q_l, dtype=float)
    return q_w / (q_w + q_l)


def power(q_w, q_l, iterations: int = 80) -> np.ndarray:
    """Solve q_w**k + q_l**k = 1 by bisection on log k (the sum falls as k rises when both q are below 1)."""
    q_w, q_l = np.asarray(q_w, dtype=float), np.asarray(q_l, dtype=float)
    lo, hi = np.full(q_w.shape, np.log(0.05)), np.full(q_w.shape, np.log(20.0))
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        k = np.exp(mid)
        too_big = q_w ** k + q_l ** k > 1.0
        lo, hi = np.where(too_big, mid, lo), np.where(too_big, hi, mid)
    return q_w ** np.exp((lo + hi) / 2.0)


def shin(q_w, q_l) -> np.ndarray:
    q_w, q_l = np.asarray(q_w, dtype=float), np.asarray(q_l, dtype=float)
    return (1.0 + q_w - q_l) / 2.0


def devig(odds_w, odds_l, method: str = "proportional") -> np.ndarray:
    """The winner's chance from a pair of decimal odds (winner's, loser's) with the margin removed."""
    q_w, q_l = implied(odds_w, odds_l)
    return {"proportional": proportional, "power": power, "shin": shin}[method](q_w, q_l)


def log_loss(p_winner) -> np.ndarray:
    """Per-match log loss from the chance given to the actual winner."""
    return -np.log(np.clip(np.asarray(p_winner, dtype=float), P_FLOOR, 1.0))


def brier(p_winner) -> np.ndarray:
    """Per-match Brier score of the two-way forecast, on the winner's side: (1 - p_w)^2."""
    return (1.0 - np.asarray(p_winner, dtype=float)) ** 2


# --------------------------------------------------------------------------------------
# intervals: Poisson bootstrap over matches, shared weights for paired comparisons
# --------------------------------------------------------------------------------------
def weights(n: int, draws: int, rng: np.random.Generator) -> np.ndarray:
    return rng.poisson(1.0, size=(draws, n)).astype(np.float32)


def boot_means(w: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Bootstrap means of x under weight rows w (draws x n)."""
    return (w @ np.asarray(x, dtype=np.float64)) / w.sum(axis=1)


def interval(estimate: float, boot: np.ndarray, scale: float = 1.0) -> dict:
    lo, hi = np.nanpercentile(boot, [2.5, 97.5])
    return {"est": float(estimate * scale), "lo": float(lo * scale), "hi": float(hi * scale)}
