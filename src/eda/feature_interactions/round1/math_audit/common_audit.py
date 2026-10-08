"""Shared helpers for the round-1 mathematical audit (docs/studies/feature_interactions/round1/math_audit.md).

RESULT-FREE by construction: the player panel is loaded for seasons <= 2021 only, and its result column (`a_won`) is
dropped at load time, before any other code sees the frame. Nothing here relates a column to a match outcome. Prices
(`in_odds_logit`, the bookmakers' quotes) are used only as regressors or modulators, which the look ledger records.

The panel (src/eda/feature_interactions/panel.py) is cached once, without the result column, in
data/studies/feature_interactions/round1/math_audit/panel_le2021_noresult.parquet.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "feature_interactions" / "round1" / "math_audit"
CACHE = OUT / "panel_le2021_noresult.parquet"
INPUTS = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_inputs.json"
CONSTANTS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_constants.csv"
MAX_SEASON = 2021
RESULT_COLS = ("a_won", "won", "y")
SURF = {0: "Hard", 1: "Clay", 2: "Grass", 3: "Carpet"}
CONTEXT = ("tour", "surface", "level", "indoor", "best_of", "round")


def load_panel() -> pd.DataFrame:
    """The player panel, seasons <= 2021, with every result column removed."""
    if CACHE.exists():
        P = pd.read_parquet(CACHE)
    else:
        from src.eda.feature_interactions.panel import panel
        P = panel(max_season=MAX_SEASON)
        P = P.drop(columns=[c for c in RESULT_COLS if c in P.columns])
        OUT.mkdir(parents=True, exist_ok=True)
        obj = [c for c in P.columns if P[c].dtype == object]
        for c in obj:
            P[c] = P[c].astype(str)
        P.to_parquet(CACHE, index=False)
    assert not any(c in P.columns for c in RESULT_COLS), "a result column reached the audit"
    assert int(P["season"].max()) <= MAX_SEASON
    return P


def input_names() -> list[str]:
    return [d["name"] for d in json.loads(INPUTS.read_text())["inputs"]]


def design58(P: pd.DataFrame) -> np.ndarray:
    """The 58 model inputs as a linear design: numeric inputs as they are (missing -> 0 plus an indicator), context
    inputs one-hot (surface, level, round) or as 0/1 (tour, indoor, best of)."""
    cols = []
    for n in input_names():
        c = f"in_{n}"
        v = pd.to_numeric(P[c], errors="coerce").to_numpy(dtype=float)
        if n in ("surface", "level", "round"):
            for lv in np.unique(v[np.isfinite(v)])[1:]:
                cols.append((v == lv).astype(float))
            continue
        miss = ~np.isfinite(v)
        cols.append(np.where(miss, 0.0, v))
        if miss.any():
            cols.append(miss.astype(float))
    X = np.column_stack([np.ones(len(P))] + cols)
    return X


def r2_on(X: np.ndarray, x: np.ndarray, mask: np.ndarray | None = None) -> float:
    ok = np.isfinite(x) if mask is None else (np.isfinite(x) & mask)
    beta, *_ = np.linalg.lstsq(X[ok], x[ok], rcond=None)
    res = x[ok] - X[ok] @ beta
    return float(1 - res.var() / x[ok].var())


def resid_sd(X: np.ndarray, x: np.ndarray, mask: np.ndarray | None = None) -> float:
    ok = np.isfinite(x) if mask is None else (np.isfinite(x) & mask)
    beta, *_ = np.linalg.lstsq(X[ok], x[ok], rcond=None)
    return float((x[ok] - X[ok] @ beta).std())


def nearest_inputs(P: pd.DataFrame, x: np.ndarray, k: int = 3) -> list[tuple[str, float]]:
    out = []
    ok0 = np.isfinite(x)
    for n in input_names():
        if n in CONTEXT:
            continue
        v = pd.to_numeric(P[f"in_{n}"], errors="coerce").to_numpy(dtype=float)
        ok = ok0 & np.isfinite(v)
        if ok.sum() < 1000 or np.std(v[ok]) == 0:
            continue
        out.append((n, float(np.corrcoef(x[ok], v[ok])[0, 1])))
    out.sort(key=lambda t: -abs(t[1]))
    return [(n, round(r, 3)) for n, r in out[:k]]


def surface_means() -> dict:
    k = pd.read_csv(CONSTANTS)
    k = k[k["kind"].eq("surface average")]
    return {(r.stat, r.tour, r.surface): float(r.value) for r in k.itertuples(index=False)}


def lg(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    return np.log(p) - np.log1p(-p)


def mu_rows(P: pd.DataFrame, stat: str, means: dict) -> np.ndarray:
    """Logit of the tour x surface mean of a statistic (Stage 3's constants, 2010-2018); carpet falls back to 'all'."""
    tour = P["tour"].astype(str).to_numpy()
    surf = pd.to_numeric(P["in_surface"], errors="coerce").map(SURF).fillna("all").to_numpy()
    vals = [means.get((stat, t, s), means.get((stat, t, "all"), np.nan)) for t, s in zip(tour, surf)]
    return lg(np.array(vals, dtype=float))


def pair(P: pd.DataFrame, name: str) -> tuple[np.ndarray, np.ndarray]:
    return (pd.to_numeric(P[f"{name}_a"], errors="coerce").to_numpy(dtype=float),
            pd.to_numeric(P[f"{name}_b"], errors="coerce").to_numpy(dtype=float))


def num(P: pd.DataFrame, c: str) -> np.ndarray:
    return pd.to_numeric(P[c], errors="coerce").to_numpy(dtype=float)
