"""Red team (round 2) of the edge-anatomy study, 12 Oct 2026: shared helpers written independently of
src/eda/edge_anatomy/ (no import of the lead's modules). Log loss lower-is-better; gains in mLL, + = the second-named
forecast better; intervals: cluster-robust mean over four-week blocks, t on G - 1.

Outcomes: only analysis.parquet (stops on 28 Jul 2026) or model_frame.parquet filtered on tournament_date < 2026-07-29
BEFORE the result column is read (load_frame below asserts it).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import norm, t as student_t

ROOT = Path(__file__).resolve().parents[5]
STUDY = ROOT / "data" / "studies" / "edge_anatomy"
OUT = STUDY / "team" / "red_team"
INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10"
SPEED = ROOT / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
SEALED = pd.Timestamp("2026-07-29")
EPS = 1e-6
ORIGIN = np.datetime64("2010-01-04")


def lg(p):
    return logit(np.clip(np.asarray(p, float), EPS, 1 - EPS))


def ll(p, y):
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    y = np.asarray(y, float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def blocks(dates, width=28, shift=0):
    d = (np.asarray(dates, dtype="datetime64[D]") - ORIGIN).astype(int) + shift
    return d // width


def cmean(v, cl, scale=1000.0, extra_var=0.0):
    """Mean of v (times scale) with a cluster-robust SE over cl, t on G - 1; extra_var added to the variance."""
    v = np.asarray(v, float)
    lab, ix = np.unique(cl, return_inverse=True)
    G, n = len(lab), len(v)
    m = v.mean()
    inf = np.bincount(ix, weights=v - m)
    se = np.sqrt(G / (G - 1) * inf @ inf) / n * scale
    se = float(np.sqrt(se ** 2 + extra_var))
    r = student_t.ppf(0.975, G - 1) * se
    est = scale * m
    return {"est": est, "lo": est - r, "hi": est + r, "se": se, "G": G, "n": n,
            "P": float(student_t.cdf(est / se, G - 1)) if se > 0 else np.nan}


def gain(q_base, q_arm, y, cl, extra_var=0.0):
    return cmean(ll(q_base, y) - ll(q_arm, y), cl, extra_var=extra_var)


def word(d):
    if d["lo"] > 0:
        return "better"
    if d["hi"] < 0:
        return "worse"
    return f"unresolved (P {d['P']:.2f})"


def fmt(d, k=2):
    return f"{d['est']:+.{k}f} [{d['lo']:+.{k}f}, {d['hi']:+.{k}f}] {word(d)}"


def logistic(X, y, offset=None, ridge=1e-8, w=None, iters=200):
    """Logistic regression, no intercept, optional offset, per-coefficient ridge (vector or scalar), optional row
    weights. Newton with step capping. Returns (b, inverse Hessian)."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n, k = X.shape
    off = np.zeros(n) if offset is None else np.asarray(offset, float)
    lam = np.full(k, ridge) if np.isscalar(ridge) else np.asarray(ridge, float)
    ww = np.ones(n) if w is None else np.asarray(w, float)
    b = np.zeros(k)
    for _ in range(iters):
        p = expit(off + X @ b)
        g = X.T @ (ww * (y - p)) - lam * b
        H = (X.T * (ww * p * (1 - p))) @ X + np.diag(lam)
        st = np.linalg.solve(H, g)
        mx = np.abs(st).max()
        if mx > 4:
            st *= 4 / mx
        b += st
        if mx < 1e-11:
            break
    p = expit(off + X @ b)
    H = (X.T * (ww * p * (1 - p))) @ X + np.diag(lam)
    return b, np.linalg.inv(H)


def sandwich(X, y, offset, b, Hinv, cl):
    p = expit(offset + X @ b)
    s = X * (np.asarray(y, float) - p)[:, None]
    lab, ix = np.unique(cl, return_inverse=True)
    S = np.zeros((len(lab), X.shape[1]))
    np.add.at(S, ix, s)
    G = len(lab)
    return G / (G - 1) * Hinv @ (S.T @ S) @ Hinv, G


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(q, 1)
    return out


def load_analysis() -> pd.DataFrame:
    a = pd.read_parquet(STUDY / "analysis.parquet")
    assert a["tournament_date"].max() < SEALED, "analysis.parquet holds a sealed match"
    return a


def load_frame(cols: list[str]) -> pd.DataFrame:
    """model_frame.parquet rows with tournament_date < 29 Jul 2026 only (filter applied in the read)."""
    f = pd.read_parquet(INSTANCE / "model_frame.parquet", columns=["match_id", "tournament_date"] + cols,
                        filters=[("tournament_date", "<", SEALED)])
    assert f["tournament_date"].max() < SEALED
    f["match_id"] = f["match_id"].astype(str)
    return f


def input_names() -> list[str]:
    import json
    meta = json.loads((INSTANCE / "model_inputs.json").read_text(encoding="utf-8"))
    return [d["name"] for d in meta["inputs"]]


FAM = {
    "ratings": ["ratings_iid", "elo_games", "elo_overall", "elo_surf_offset", "points_52w"],
    "schedule": ["sets_14d", "age", "age_sq", "surf_season", "surf_layoff"],          # pairs as A - B
    "form": ["adjperf_tpw_2w"] + [f"form_{s}" for s in ("ace", "df", "first_in", "first_won", "second_won", "hold",
                                                         "bp_saved", "bp_faced_pg", "brk", "bp_conv", "rpw_first",
                                                         "rpw_second")]
            + [f"formdef_{s}" for s in ("ace", "df", "first_in", "bp_faced_pg")],
    "ios": [f"ios{k}_{s}" for s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
            for k in ("O", "D")] + [f"prod_{s}" for s in ("ace", "df", "first_in", "first_won", "second_won", "hold",
                                                           "bp_saved")],
}
PAIRS = ("surf_season", "surf_layoff")


def add_pairs(df: pd.DataFrame) -> pd.DataFrame:
    for p in PAIRS:
        df[f"in_{p}"] = df[f"in_{p}_a"] - df[f"in_{p}_b"]
    return df


def rms_scaled(x, rms=None):
    x = np.where(np.isfinite(x), x, 0.0)
    r = float(np.sqrt(np.mean(x ** 2))) if rms is None else rms
    return (x / r if r > 0 else x), r
