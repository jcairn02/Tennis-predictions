"""Shared definitions for the study "pair strength" (src/eda/pair_strength/).

The owner's request of 7 Oct 2026: investigate the feature-interactions study's lead I-084 (pair prominence x the
forecast: joint z -2.99, against its declared direction) and whether it belongs in the best local, non-thinking
TabPFN-3.5 model (the 58-input model of data/studies/surface_rating_race/model/).

Windows, as in docs/studies/feature_interactions/:

    DEVELOPMENT   2014-2024 (discovery 2014-2021, replication 2022-2024): every exploration and choice
    TEST          2025-2026: closed; opened once, by final_test.py, after docs/studies/pair_strength/preregistration.md
                  is hashed

The base log-odds eta is the current best's walk-forward out-of-sample forecast (seeds 0-2, symmetrised, raw), read
through the feature-interactions screen (`screen.load`), which asserts that no season after 2024 is loaded.

Pair strength. A symmetric modulator s (unchanged when A and B swap) multiplies the antisymmetric log-odds eta, so
s * eta is antisymmetric and can enter a model without an intercept. A negative coefficient on s * eta means the
forecast should be FLATTER (closer to 50%) where s is high.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as FC  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = ROOT / "data" / "studies" / "pair_strength"
DOCS = ROOT / "docs" / "studies" / "pair_strength"
LOCAL = OUT / "local"                         # this study's local TabPFN fits

TOURS = FC.TOURS
DISCOVERY, REPLICATION, TEST = FC.DISCOVERY, FC.REPLICATION, FC.TEST
CALIB_FROM = FC.CALIB_FROM
EPS = FC.EPS

PANEL_COLS = ["elo_R_a", "elo_R_b", "elo_N_a", "elo_N_b", "rank_a", "rank_b", "rank_points_a", "rank_points_b",
              "ttt_mu_a", "ttt_mu_b", "age_a", "age_b", "overround_avg", "p_ps_a", "avg_a", "avg_b", "ps_a", "ps_b",
              "max_a", "max_b", "level", "draw_size", "round", "best_of", "surface", "indoor", "tournament_id",
              "tournament_name", "player_a_id", "player_b_id"]

T0 = time.time()
ll, compare, blocks, write_json, sha256_file, lg = T.ll, T.compare, T.blocks, T.write_json, T.sha256_file, FC.lg


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------ the development frame

def dev_frame() -> pd.DataFrame:
    """The screen's frame (2014-2024, debut seasons out, eta_model and the price) with the panel's per-player columns
    and the pair-strength modulators. Asserts that no test season is present."""
    from src.eda.feature_interactions.panel import panel
    F = S.load(with_model=True)
    assert F["season"].max() <= REPLICATION[-1], "a test season reached the development frame"
    P = panel(max_season=REPLICATION[-1])
    keep = [c for c in PANEL_COLS if c in P.columns and c not in F.columns]
    F = F.merge(P[["match_id"] + keep], on="match_id", how="left", validate="one_to_one")
    return add_modulators(F)


def disc_mask(F: pd.DataFrame) -> np.ndarray:
    return F["season"].astype(int).between(DISCOVERY[0], DISCOVERY[-1]).to_numpy()


def zsym(v: np.ndarray, F: pd.DataFrame, ref: np.ndarray | None = None) -> np.ndarray:
    """A symmetric modulator centred per tour and divided by its per-tour SD, both on the reference rows (default:
    discovery 2014-2021)."""
    v = np.asarray(v, float).copy()
    ref = disc_mask(F) if ref is None else ref
    t = F["tour"].astype(str).to_numpy()
    out = np.full(len(v), np.nan)
    for tour in TOURS:
        m = t == tour
        ok = m & ref & np.isfinite(v)
        if ok.any():
            out[m] = (v[m] - v[ok].mean()) / v[ok].std()
    return out


def add_modulators(F: pd.DataFrame) -> pd.DataFrame:
    """Symmetric pair-level columns (raw `pr_*`, standardised `s_*`), all unchanged under an A/B swap."""
    F = F.copy()
    ra, rb = F["elo_R_a"].to_numpy(float), F["elo_R_b"].to_numpy(float)
    z = F["z_market"].to_numpy(float)
    fav_a = (z > 0) | ((z == 0) & (ra >= rb))          # an even price: the higher-rated player (swap-symmetric)
    rk_a = pd.to_numeric(F["rank_a"], errors="coerce").to_numpy(float)
    rk_b = pd.to_numeric(F["rank_b"], errors="coerce").to_numpy(float)
    lra, lrb = np.log(np.where(np.isfinite(rk_a), rk_a, 1500.0)), np.log(np.where(np.isfinite(rk_b), rk_b, 1500.0))
    raw = {
        "elo_sum": ra + rb,                                    # I-084's prominence (sum of overall Elo)
        "elo_max": np.maximum(ra, rb),
        "elo_min": np.minimum(ra, rb),
        "elo_fav": np.where(fav_a, ra, rb),                    # the price favourite's overall Elo
        "elo_dog": np.where(fav_a, rb, ra),
        "elo_absdiff": np.abs(ra - rb),
        "lrank_max": np.maximum(lra, lrb),                     # I-036's obscurity (worse player's log rank)
        "lrank_min": np.minimum(lra, lrb),
        "lrank_sum": lra + lrb,
        "ttt_sum": F["ttt_mu_a"].to_numpy(float) + F["ttt_mu_b"].to_numpy(float),
        "overround": pd.to_numeric(F["overround_avg"], errors="coerce").to_numpy(float),
        "age_sum": pd.to_numeric(F["age_a"], errors="coerce").to_numpy(float)
        + pd.to_numeric(F["age_b"], errors="coerce").to_numpy(float),
        "n_min": np.minimum(F["elo_N_a"].to_numpy(float), F["elo_N_b"].to_numpy(float)),
    }
    for k, v in raw.items():
        F[f"pr_{k}"] = v
        F[f"s_{k}"] = zsym(v, F)
    F["s_log_n_min"] = zsym(np.log1p(raw["n_min"]), F)
    return F


# ------------------------------------------------------------------------------------------------ the slope regression

def nuisance(F: pd.DataFrame, rows: np.ndarray, eta: np.ndarray, per_season: bool = True, mset: bool = True,
             cubic: bool = True) -> tuple[np.ndarray, list[str]]:
    """The screen's eta terms: a slope per tour x season (or per tour), the cubic per tour (scaled by its SD on the
    rows), and the M-set's eta|eta| per tour."""
    e = eta[rows]
    tour = F["tour"].to_numpy()[rows]
    season = F["season"].to_numpy()[rows]
    cols, names = [], []
    keys = sorted(set(zip(tour, season))) if per_season else [(t, None) for t in TOURS if (tour == t).any()]
    for t, s in keys:
        m = (tour == t) if s is None else ((tour == t) & (season == s))
        cols.append(np.where(m, e, 0.0))
        names.append(f"slope {t} {s if s is not None else ''}".strip())
    for t in TOURS:
        if not (tour == t).any():
            continue
        if cubic:
            sd = float(np.std(e[tour == t] ** 3)) or 1.0
            cols.append(np.where(tour == t, e ** 3 / sd, 0.0))
            names.append(f"cubic {t}")
        if mset:
            cols.append(np.where(tour == t, e * np.abs(e), 0.0))
            names.append(f"eta|eta| {t}")
    return np.column_stack(cols), names


def slope_fit(F: pd.DataFrame, rows: np.ndarray, eta: np.ndarray, mods: dict[str, np.ndarray],
              controls: dict[str, np.ndarray] | None = None, per_season: bool = True, mset: bool = True,
              cubic: bool = True, tests: dict[str, np.ndarray] | None = None, y: np.ndarray | None = None) -> dict:
    """logit P(A wins) = nuisance(eta) + sum_j g_j control_j + sum_k b_k (s_k * eta) + sum_l c_l test_l, no intercept,
    maximum likelihood. Each modulator s_k is symmetric (missing -> 0, i.e. its centre); controls and tests are
    antisymmetric columns (missing -> 0; controls scaled by their SD, tests used as given). Returns, for every modulator
    and test term, the coefficient, its clustered SE (the largest of four-week block, shared player and their union, as
    the screen) and z; plus the log-likelihood and the nuisance coefficients."""
    rows = np.asarray(rows, bool)
    N, nn = nuisance(F, rows, eta, per_season, mset, cubic)
    e = eta[rows]
    names = list(mods) + list(tests or {})
    cols = [np.nan_to_num(np.asarray(mods[k], float)[rows], nan=0.0) * e for k in mods]
    cols += [np.nan_to_num(np.asarray(v, float)[rows], nan=0.0) for v in (tests or {}).values()]
    parts = [N]
    if controls:
        Cm = np.column_stack([np.nan_to_num(np.asarray(v, float)[rows], nan=0.0) for v in controls.values()])
        sd = Cm.std(axis=0)
        parts.append(Cm / np.where(sd > 0, sd, 1.0))
    parts.append(np.column_stack(cols))
    Z = np.column_stack(parts)
    yy = (F["a_won"].to_numpy(float) if y is None else np.asarray(y, float))[rows]
    beta, p, H = S.fit(Z, yy)
    k = len(names)
    J = np.arange(Z.shape[1] - k, Z.shape[1])
    A = np.linalg.solve(H, np.eye(Z.shape[1])[:, J])
    U = (yy - p)[:, None] * (Z @ A)
    covs = S.clustered_cov(U, F["block"].to_numpy()[rows], F["player_a_id"].to_numpy(str)[rows],
                           F["player_b_id"].to_numpy(str)[rows])
    pc = np.clip(p, 1e-12, 1 - 1e-12)
    out = {"n": int(rows.sum()), "loglik": float(np.sum(yy * np.log(pc) + (1 - yy) * np.log(1 - pc))), "terms": {}}
    for j, name in enumerate(names):
        var = max(covs["block"][j, j], covs["player"][j, j], covs["union"][j, j])
        se = float(np.sqrt(var))
        out["terms"][name] = {"b": float(beta[J[j]]), "se": se, "z": float(beta[J[j]] / se),
                              "se_model": float(np.sqrt(A[J[j], j]))}
    out["base_slopes"] = {nm: float(beta[i]) for i, nm in enumerate(nn)}
    return out


def joint_z(z1: float, z2: float, n1: int, n2: int) -> float:
    return float((np.sqrt(n1) * z1 + np.sqrt(n2) * z2) / np.sqrt(n1 + n2))


def windows(F: pd.DataFrame) -> dict[str, np.ndarray]:
    s = F["season"].astype(int).to_numpy()
    return {"2014-2021": np.isin(s, DISCOVERY), "2022-2024": np.isin(s, REPLICATION)}


def by_window(F: pd.DataFrame, eta: np.ndarray, mods: dict, controls: dict | None = None, rows: np.ndarray | None = None,
              **kw) -> dict:
    """slope_fit on 2014-2021 and 2022-2024 separately, with the joint z per modulator (the screen's combination)."""
    rows = np.ones(len(F), bool) if rows is None else rows
    res = {w: slope_fit(F, m & rows, eta, mods, controls, **kw) for w, m in windows(F).items()}
    a, b = res["2014-2021"], res["2022-2024"]
    res["joint_z"] = {k: joint_z(a["terms"][k]["z"], b["terms"][k]["z"], a["n"], b["n"]) for k in a["terms"]}
    return res
