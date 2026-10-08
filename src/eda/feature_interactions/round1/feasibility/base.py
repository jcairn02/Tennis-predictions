"""Shared helpers of the round-1 feasibility audit (gate G2): result-free only (critique M5).

Loads the player panel and each player's own history up to 2024 (no 2025-2026 value is loaded; their model-frame rows
are only counted), and provides: the full swap (every _a/_b exchanged, the 58 inputs' differences negated, the pairs
exchanged, the A-side probabilities flipped), coverage by tour and window, the candidate's R-squared on the 58 inputs,
and the iid point-model helpers.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.panel import panel  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402  (iid point -> match model; read-only)

OUT = C.OUT / "round1"
DISC, REP = (2014, 2021), (2022, 2024)
CONTEXT_IN = ["in_tour", "in_surface", "in_level", "in_indoor", "in_best_of", "in_round"]
PAIR_IN = ["in_surf_season_a", "in_surf_season_b", "in_surf_layoff_a", "in_surf_layoff_b"]
EXTRA_DIFF = ("d_bigpoint", "d_home_s4", "eta")
EPS = 1e-6


def lg(p):
    return logit(np.clip(np.asarray(p, float), EPS, 1 - EPS))


@lru_cache(maxsize=1)
def get_panel() -> pd.DataFrame:
    P = panel(max_season=2024)
    return P[P["season"] >= DISC[0]].reset_index(drop=True)


@lru_cache(maxsize=1)
def get_history() -> pd.DataFrame:
    """history.long_table() cut at 31 Dec 2024 before anything is derived (2025-2026 rows are dropped unread)."""
    from src.eda.feature_interactions.history import long_table
    L = long_table()
    L = L[pd.to_datetime(L["tournament_date"]) < pd.Timestamp("2025-01-01")].reset_index(drop=True)
    return L


def at_model(L: pd.DataFrame, values: np.ndarray, P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """A per-row history value read at the model matches for side A and side B (pre-match by construction of `values`)."""
    s = pd.Series(np.asarray(values, float), index=L.index)
    out = []
    for side in ("A", "B"):
        idx = L.index[L["side"] == side]
        m = pd.Series(s.loc[idx].to_numpy(), index=L.loc[idx, "match_id"].to_numpy())
        m = m[~m.index.duplicated()]
        out.append(m.reindex(P["match_id"].to_numpy()).to_numpy(dtype=float))
    return out[0], out[1]


def swap_full(P: pd.DataFrame) -> pd.DataFrame:
    """A and B exchanged, everywhere: _a/_b columns, the model's differences (negated), pairs, A-side probabilities."""
    from src.eda.surface_rating_race import arms as RA
    out = P.copy()
    for c in P.columns:
        if c.endswith("_a") and c[:-2] + "_b" in P.columns:
            out[c], out[c[:-2] + "_b"] = P[c[:-2] + "_b"].to_numpy(), P[c].to_numpy()
    for c in P.columns:
        if c.startswith("in_") and (c[3:] in RA.ANTISYMMETRIC or c[3:] in {n[3:] for n in RA.ANTISYMMETRIC if n.startswith("sf_")}):
            out[c] = -P[c]
    for c in ("p_mkt", "p_ps_a"):
        out[c] = 1.0 - P[c].astype(float)
    for c in EXTRA_DIFF:                      # A - B quantities of the augmented panel, and A's forecast log-odds
        if c in P.columns:
            out[c] = -P[c].astype(float)
    out["a_won"] = ~P["a_won"].astype(bool)
    out["player_a_id"], out["player_b_id"] = P["player_b_id"].to_numpy(), P["player_a_id"].to_numpy()
    return out


def swap_ok(builder, P: pd.DataFrame, kind: str) -> bool:
    x = np.asarray(builder(P), float)
    y = np.asarray(builder(swap_full(P)), float)
    ok = np.isfinite(x) & np.isfinite(y)
    same_missing = bool((np.isfinite(x) == np.isfinite(y)).all())
    if kind == "diff":
        return same_missing and bool(np.allclose(x[ok], -y[ok], atol=1e-8, rtol=1e-6))
    return same_missing and bool(np.allclose(x[ok], y[ok], atol=1e-8, rtol=1e-6))


def coverage(P: pd.DataFrame, x: np.ndarray) -> dict:
    ok = np.isfinite(np.asarray(x, float))
    res = {}
    for tag, (lo, hi) in (("disc", DISC), ("rep", REP)):
        for t in ("atp", "wta"):
            m = (P["tour"].to_numpy() == t) & P["season"].between(lo, hi).to_numpy()
            res[f"cov_{tag}_{t}"] = round(float(ok[m].mean()), 4) if m.any() else np.nan
    return res


def input_matrix(P: pd.DataFrame, aug: str | None = None) -> np.ndarray:
    """The 58 inputs as a design matrix: numeric inputs (missing -> 0 plus a missing indicator), context one-hot.
    aug = 'diff': adds each difference times the tour, surface and best-of dummies (existing context modulations);
    aug = 'context': adds |difference| and difference squared (symmetric functions of the inputs)."""
    cols, parts = [c for c in P.columns if c.startswith("in_")], []
    num = [c for c in cols if c not in CONTEXT_IN]
    X = P[num].to_numpy(float)
    miss = ~np.isfinite(X)
    parts.append(np.where(miss, 0.0, X))
    parts.append(miss[:, miss.any(axis=0)].astype(float))
    ctx = []
    for c in CONTEXT_IN:
        v = P[c].fillna(-1).to_numpy()
        for u in np.unique(v)[1:]:
            ctx.append((v == u).astype(float))
    ctx = np.column_stack(ctx)
    parts.append(ctx)
    diffs = np.where(miss, 0.0, X)[:, [i for i, c in enumerate(num) if c not in PAIR_IN]]
    if aug == "diff":
        dummies = np.column_stack([P["in_tour"].to_numpy(float), (P["in_best_of"].to_numpy(float) == 5).astype(float)]
                                  + [(P["in_surface"].to_numpy() == s).astype(float) for s in (1.0, 2.0)])
        parts += [diffs * d[:, None] for d in dummies.T]
    elif aug == "context":
        parts += [np.abs(diffs), diffs ** 2]
    return np.column_stack(parts)


def r2_on_inputs(P: pd.DataFrame, x: np.ndarray, kind: str, window=DISC) -> dict:
    """R-squared of the candidate on the 58 inputs (ordinary least squares with intercept), 2014-2021 rows where the
    candidate exists; and on the symmetry-aware augmented basis. Result-free."""
    x = np.asarray(x, float)
    m = np.isfinite(x) & P["season"].between(*window).to_numpy()
    if m.sum() < 200 or np.nanstd(x[m]) == 0:
        return {"novelty_r2": np.nan, "novelty_r2_aug": np.nan, "r2_rows": int(m.sum())}
    out = {"r2_rows": int(m.sum())}
    for key, aug in (("novelty_r2", None), ("novelty_r2_aug", "diff" if kind == "diff" else "context")):
        X = input_matrix(P.loc[m], aug)
        X = np.column_stack([np.ones(len(X)), X])
        y = x[m]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ beta
        out[key] = round(float(1 - res.var() / y.var()), 4)
    return out


@lru_cache(maxsize=1)
def surface_means() -> dict:
    from src.eda.ufc_ideas import stageB_common as B
    return B.surface_means()


def mean_logit(P: pd.DataFrame, stat: str) -> np.ndarray:
    """logit of the tour x surface average of a statistic (Stage B's means; 'all' where the surface is unknown)."""
    means = surface_means()[stat]
    keys = list(zip(P["tour"], P["surface"]))
    return lg([means.get(k, means.get((k[0], "all"))) for k in keys])


def iid_match(pa, pb, bo) -> np.ndarray:
    """P(A wins the match) under the iid model, A serving at pa and B at pb, best of 3 or 5, standard tiebreak sets."""
    pa, pb = np.clip(np.asarray(pa, float), 0.02, 0.98), np.clip(np.asarray(pb, float), 0.02, 0.98)
    bo = np.where(np.asarray(bo, float) == 5, 5, 3)
    out = np.full(len(pa), np.nan)
    ok = np.isfinite(pa) & np.isfinite(pb)
    out[ok] = M.match_win_by(pa[ok], pb[ok], bo[ok], np.full(int(ok.sum()), "TB7@6"))
    return out
