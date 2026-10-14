"""Shared definitions of the study "which bookmakers' prices to train on and feed live: recording quality and drift"
(src/eda/odds_sources/).

The owner's questions of 9 Oct 2026, after the bet-timing study (docs/studies/bet_timing/):
    * OddsTrader lists other books besides BetOnline: "Do we have a history here? how much drift do we expect from which
      sports books used for this?"
    * "Id like to keep it as a weighted average of the sharpest books with vig extracted ideally and then do the same
      live. I plan to betting on betonline, polymarket and pinnacle mostly. If that means training simply
      pinnacle/betonline after some year than maybe thats it."
    * "An idea to check too is if pinnacle/betonline data has potential recording flaws. If we use them as history and
      some matches show -600/+400 while the oddsportal has it -110/-110 it shows that there may be some data issues and
      we may want to use the more stable books rather than the outlier."

    table.py    --link: tennis-data's 2018-2026 rows linked to OddsTrader's events (the eid list for the every-book pull)
                --build: one row per model-frame match, 2013-2026, with every source's price for side A
    quality.py  recording flaws: the two recordings of Pinnacle, each source against the others, who was right
    drift.py    by season: margin, accuracy on the same matches, calibration, distance between sources
    pools.py    margin-free averages of several books: equal, weighted (walk-forward), guarded against outliers
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking.common import fit_logistic  # noqa: E402,F401  (light: numpy and scipy only)

OUT = ROOT / "data" / "studies" / "odds_sources"
DOCS = ROOT / "docs" / "studies" / "odds_sources"
REF = ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen"
MODEL_FRAME = REF / "instance" / "model_frame.parquet"          # the current best model's frame (label, season, input)
STAGE1 = REF / "tables" / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet"
OT = ROOT / "data" / "dump" / "odds" / "oddstrader"
OT_EVENTS = OT / "events.parquet"
OT_BOOKS = OT / "books_lines.parquet"                            # src/ingest/oddstrader.py --books-eids
POLYMARKET = ROOT / "data" / "studies" / "sharp_benchmark" / "matches.parquet"

LINK = OUT / "oddstrader_link.parquet"        # tennis-data row -> OddsTrader event (gitignored)
EIDS = OUT / "oddstrader_eids.csv"            # the events asked for in the every-book pull (ids only)
SOURCES = OUT / "sources.parquet"             # one row per match, every source's price (gitignored: OddsTrader's prices)

FRAME_SEASONS = tuple(range(2013, 2027))
OT_SEASONS = tuple(range(2018, 2027))
OVERROUND_OK = (1.0, 1.2)                     # a coherent two-way quote (the sharp benchmark's rule)
EPS = 1e-6
BLOCK_ORIGIN = np.datetime64("2010-01-04")    # four-week blocks for clustered intervals, as the bet-timing study

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def lg(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def ex(z) -> np.ndarray:
    return expit(np.asarray(z, dtype=float))


def devig(d_a, d_b) -> np.ndarray:
    """P(A) with the margin removed proportionally (the model's own input is this of the books' average)."""
    ia, ib = 1.0 / np.asarray(d_a, dtype=float), 1.0 / np.asarray(d_b, dtype=float)
    return ia / (ia + ib)


def coherent(d_a, d_b) -> np.ndarray:
    """Both prices above 1 and the pair's overround inside OVERROUND_OK."""
    d_a, d_b = np.asarray(d_a, dtype=float), np.asarray(d_b, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        s = 1.0 / d_a + 1.0 / d_b
        return (d_a > 1.0) & (d_b > 1.0) & (s >= OVERROUND_OK[0]) & (s <= OVERROUND_OK[1])


def median_logit(P: np.ndarray, min_count: int) -> np.ndarray:
    """expit of the median log-odds across the columns of P (chances; NaN = not priced), NaN below min_count."""
    Z = lg(P)
    n = np.isfinite(Z).sum(axis=1)
    out = np.full(len(Z), np.nan)
    ok = n >= min_count
    out[ok] = ex(np.nanmedian(Z[ok], axis=1))
    return out


def mean_logit(P: np.ndarray, min_count: int = 1, weights=None) -> np.ndarray:
    """expit of the (weighted) mean log-odds of the priced columns of P, NaN below min_count."""
    Z = lg(P)
    have = np.isfinite(Z)
    W = np.where(have, 1.0 if weights is None else np.asarray(weights, float), 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = (np.where(have, Z, 0.0) * W).sum(axis=1) / W.sum(axis=1)
    return np.where(have.sum(axis=1) >= min_count, ex(m), np.nan)


def log_loss(p, y) -> np.ndarray:
    """Per-match log loss (nats) of P(A) = p for the result y (1 when A won)."""
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    y = np.asarray(y, dtype=float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def blocks(dates, width_days: int = 28) -> np.ndarray:
    days = (np.asarray(dates, dtype="datetime64[D]") - BLOCK_ORIGIN).astype(int)
    return days // width_days


def mean_ci(v, clusters, scale: float = 1000.0) -> dict:
    """Mean with a cluster-sandwich SE (G / (G - 1)) and t on G - 1 degrees of freedom, times scale (the bet-timing
    study's mean_ci). With the default scale a log-loss difference reads in milli-log-loss."""
    v = np.asarray(v, float)
    if len(v) == 0:
        return {"est": None, "lo": None, "hi": None, "n": 0, "blocks": 0}
    labels, ix = np.unique(clusters, return_inverse=True)
    G, n = len(labels), len(v)
    m = float(v.mean())
    infl = np.bincount(ix, weights=v - m)
    se = float(np.sqrt(G / (G - 1) * infl @ infl) / n) if G > 1 else np.nan
    r = student_t.ppf(0.975, G - 1) * se if G > 1 else np.nan
    return {"est": scale * m, "lo": scale * (m - r), "hi": scale * (m + r), "n": int(n), "blocks": int(G)}


def slope_ci(z, y, clusters) -> dict:
    """Calibration slope: logistic regression of the result on a price's log-odds without intercept (side A is random,
    so the intercept is about 0), with a cluster-sandwich interval. Above 1: the price is too timid (favourites win
    more often than it says); below 1: too bold."""
    Z = np.asarray(z, float)[:, None]
    y = np.asarray(y, float)
    beta, _ = fit_logistic(Z, y)
    p = ex(Z @ beta)
    h = float((Z[:, 0] ** 2 * p * (1 - p)).sum())
    labels, ix = np.unique(clusters, return_inverse=True)
    g = len(labels)
    s = np.bincount(ix, weights=Z[:, 0] * (y - p))
    se = float(np.sqrt(g / (g - 1) * (s @ s)) / h)
    tq = student_t.ppf(0.975, g - 1)
    return {"est": float(beta[0]), "lo": float(beta[0] - tq * se), "hi": float(beta[0] + tq * se), "n": int(len(y))}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=_default), encoding="utf-8")


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)
