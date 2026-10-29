"""P9 point details: the scoring harness (brief: docs/studies/p9_point_details/briefs/03_harness.md).

It scores one candidate column on the population built by harness_population.py (men, 2025-01-01 .. 2026-10-18):
an A - B difference on Stage 0's side A, one value per match id, NaN where it does not exist.

Bases (the base's log-odds L that A wins):
    price      the market's margin-free close (price_logit): every population
    model      the live model, both stages (model_logit_full): tour level only
    model_s1   the live model's stage 1 alone (model_logit_s1): a diagnostic, never the headline
Populations: all (tour level and Challengers), tour, tour_main, tour_qual, challenger, ch_main, ch_qual; each optionally
finished matches only (retirements out).

What is computed, per population and base:
    orientation  Stage 0's side A against the winner (a_won's mean); the scoring is symmetric: swapping A and B
                 negates the feature, the base's log-odds and the result's coding, and changes no score (no intercept,
                 no centring of the feature)
    z            logistic regressions of the result, without an intercept: "offset" logit = L + b x; "free"
                 logit = s_c L + b x with one slope per cell c (level group x draw: tour main, tour qualifying,
                 Challenger main, Challenger qualifying), so that no feature borrows a cell's favourite-longshot shape;
                 "curve" adds a curvature term k_c L^3 per cell (the unpriced-leads test's slope and curvature per tour).
                 x is scaled by its root mean square on the scored rows (0 stays "no difference"). Standard errors
                 clustered by calendar week (tournament date, Monday weeks; sandwich with G / (G - 1)); z = b / se; the
                 one-sided p in the declared direction (normal; the t on weeks - 1 beside it)
    gain         cross-fitted: for every 4-week block, the base-only model and the base-plus-feature model fitted on the
                 other blocks predict it ("offset": the base-only model is the base itself; "free" and "curve": the
                 per-cell slopes, and curvature, on L).
                 Gain = 1000 x (LL(base-only) - LL(with the feature)) per match: positive = the feature is better. A 95%
                 interval and P(better) from 2,000 bootstrap draws of 4-week blocks; the reading "better" / "worse" when
                 the interval clears 0, otherwise "unresolved" with P(better). The t interval over blocks (the project's
                 paired_interval) is reported beside it
    new part     tour level only: the feature minus its least-squares projection (no intercept) on the model's 48
                 non-price, non-context inputs as A - B (model_inputs.parquet), fitted on the scored rows where the
                 feature exists, missing inputs 0 (unpriced_leads/screen.py's orthogonal_part); scored the same way.
                 Below the tour the model's inputs are not built: see the memo
    missing      "subset": the rows where the feature exists; "indicator": every row, the feature 0 where missing plus
                 the term m * L (m = 1 where missing), which keeps the model antisymmetric. Coverage reported
    describe     the feature's correlation with L and its R^2 on the 48 inputs (outcome-free): how much the price and
                 the model's inputs already say about it

Run:
    ./python.sh src/eda/p9_point_details/harness.py --feature <file.parquet> --column <name> --direction 1
            [--populations all,tour,challenger] [--bases price,model,model_s1] [--finished-only] [--no-new-part]
            [--last-date YYYY-MM-DD] [--out <file.csv>]
        <file.parquet> holds match_id and the column (A - B on Stage 0's side A)
        --last-date scores only matches played on or before that day: 2026-10-18 leaves out the untouched test of the
        model's edge (H1, from 19 Oct 2026). Every run names the protected periods its window reaches
        (docs/holdouts/register.csv; soft rules: ask the owner before measuring what one protects, log every read)
    ./python.sh src/eda/p9_point_details/harness.py --bases-report       the bases' log losses; the model against the price
    ./python.sh src/eda/p9_point_details/harness.py --orientation        side A against the winner
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, log_expit
from scipy.stats import norm
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HARNESS = ROOT / "data" / "studies" / "p9_point_details" / "harness"
POP = HARNESS / "population.parquet"
INPUTS = HARNESS / "model_inputs.parquet"
BLOCK_ORIGIN = np.datetime64("2010-01-04")       # a Monday: the project harness's origin for weeks and 4-week blocks
N_BOOT = 2000
BOOT_SEED = 20261028
BASES = {"price": "price_logit", "model": "model_logit_full", "model_s1": "model_logit_s1"}
POPULATIONS = ("all", "tour", "tour_main", "tour_qual", "challenger", "ch_main", "ch_qual")
VARIANTS = ("offset", "free", "curve")
RIDGE = 1e-8


# ------------------------------------------------------------------------------------------------
# The population

def load_population(path: Path = POP) -> pd.DataFrame:
    p = pd.read_parquet(path)
    p["match_id"] = p["match_id"].astype(str)
    return p


def window(pop: pd.DataFrame, last_date: str | None) -> pd.DataFrame:
    """The matches played on or before last_date (every match when it is None)."""
    if not last_date:
        return pop
    return pop[pop["date"] <= pd.Timestamp(last_date)].reset_index(drop=True)


def population_mask(pop: pd.DataFrame, name: str, finished_only: bool = False) -> np.ndarray:
    g, d = pop["level_group"].to_numpy(), pop["draw"].to_numpy()
    masks = {"all": np.ones(len(pop), bool), "tour": g == "tour", "tour_main": (g == "tour") & (d == "main"),
             "tour_qual": (g == "tour") & (d == "qualifying"), "challenger": g == "challenger",
             "ch_main": (g == "challenger") & (d == "main"), "ch_qual": (g == "challenger") & (d == "qualifying")}
    if name not in masks:
        raise ValueError(f"unknown population {name!r}: one of {POPULATIONS}")
    m = masks[name]
    if finished_only:
        m = m & pop["finished"].to_numpy(bool)
    return m


def scored_rows(pop: pd.DataFrame, population: str, base: str, finished_only: bool = False) -> pd.DataFrame:
    """The population's rows that carry the base (price: priced; model: priced with the model's forecast)."""
    m = population_mask(pop, population, finished_only) & pop["priced"].to_numpy(bool)
    if base in ("model", "model_s1"):
        m = m & pop["has_model"].to_numpy(bool)
    return pop.loc[m].reset_index(drop=True)


def blocks(dates, width_days: int) -> np.ndarray:
    days = (np.asarray(dates, dtype="datetime64[D]") - BLOCK_ORIGIN).astype(int)
    return days // width_days


def orientation(pop: pd.DataFrame) -> dict:
    """Stage 0's side A against the winner: if A were the winner (or the favourite) by construction, a_won's mean would
    sit far from 0.5 and an A - B feature would carry the orientation."""
    out = {}
    for name in ("all", "tour", "challenger"):
        m = population_mask(pop, name)
        a = pop.loc[m, "a_won"].astype(float)
        fav = pop.loc[m & pop["priced"].to_numpy(bool), "price_logit"]
        out[name] = {"matches": int(m.sum()), "a_won_mean": float(a.mean()),
                     "a_won_se": float(a.std(ddof=1) / np.sqrt(len(a))),
                     "a_favourite_share": float((fav > 0).mean()),
                     "a_id_lower_share": float((pop.loc[m, "player_a_id"] < pop.loc[m, "player_b_id"]).mean())}
    return out


# ------------------------------------------------------------------------------------------------
# Logistic regression without an intercept, with an offset; clustered covariance

def fit_logit(X: np.ndarray, y: np.ndarray, offset: np.ndarray | None = None, beta0: np.ndarray | None = None,
              max_iter: int = 60, tol: float = 1e-10) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(coefficients, fitted probabilities, Hessian). Newton steps, a step longer than 4 cut back, a tiny ridge
    (the project's fit_logistic / fit_offset)."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n, k = X.shape
    off = np.zeros(n) if offset is None else np.asarray(offset, float)
    b = np.zeros(k) if beta0 is None else np.array(beta0, float)
    lam = np.eye(k) * RIDGE
    for _ in range(max_iter):
        p = expit(off + X @ b)
        g = X.T @ (y - p) - RIDGE * b
        H = (X.T * (p * (1 - p))) @ X + lam
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        b = b + step
        if big < tol:
            break
    p = expit(off + X @ b)
    H = (X.T * (p * (1 - p))) @ X + lam
    return b, p, H


def cluster_cov(X: np.ndarray, y: np.ndarray, p: np.ndarray, H: np.ndarray, clusters: np.ndarray) -> np.ndarray:
    s = X * (np.asarray(y, float) - p)[:, None]
    labels, ix = np.unique(clusters, return_inverse=True)
    G = len(labels)
    S = np.zeros((G, X.shape[1]))
    np.add.at(S, ix, s)
    Hi = np.linalg.inv(H)
    return G / (G - 1) * Hi @ (S.T @ S) @ Hi


def log_loss(eta: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Per-match log loss of the log-odds eta that A wins (exact, no clipping needed)."""
    y = np.asarray(y, float)
    return -(y * log_expit(eta) + (1 - y) * log_expit(-eta))


def design(L: np.ndarray, x: np.ndarray | None, variant: str, miss: np.ndarray | None = None,
           cells: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(X, offset) for a variant, the feature last:
        offset  logit = L + b x                                    (X = [x], offset L)
        free    logit = sum_c s_c L 1[c] + b x                      one slope per cell
        curve   logit = sum_c (s_c L + k_c L^3 / sd_c) 1[c] + b x   a slope and a curvature term per cell
    cells: the level group x draw of each row (None: one cell), so that no feature borrows a cell's own
    favourite-longshot shape. Every column is odd in L, so the model stays antisymmetric. x None: the base-only model.
    miss (indicator handling): the extra column miss * L."""
    L = np.asarray(L, float)
    cols = []
    if variant in ("free", "curve"):
        cl = np.zeros(len(L), dtype=int) if cells is None else np.unique(np.asarray(cells), return_inverse=True)[1]
        for c in np.unique(cl):
            m = cl == c
            cols.append(np.where(m, L, 0.0))
            if variant == "curve":
                L3 = np.where(m, L ** 3, 0.0)
                sd = float(np.std(L3[m])) or 1.0
                cols.append(L3 / sd)
    elif variant != "offset":
        raise ValueError(f"unknown variant {variant!r}: one of {VARIANTS}")
    if miss is not None:
        cols.append(np.where(miss, L, 0.0))
    if x is not None:
        cols.append(np.asarray(x, float))
    off = L if variant == "offset" else np.zeros(len(L))
    X = np.column_stack(cols) if cols else np.zeros((len(L), 0))
    return X, off


# ------------------------------------------------------------------------------------------------
# The two readings

def z_test(y: np.ndarray, L: np.ndarray, x: np.ndarray, week: np.ndarray, variant: str, direction: int = 1,
           miss: np.ndarray | None = None, cells: np.ndarray | None = None) -> dict:
    """b (per unit of x as given), its clustered se, z, the one-sided p in `direction`, the two-sided p."""
    X, off = design(L, x, variant, miss, cells)
    b, p, H = fit_logit(X, y, off)
    V = cluster_cov(X, y, p, H, week)
    j = X.shape[1] - 1
    se = float(np.sqrt(max(V[j, j], 0.0)))
    z = float(b[j] / se) if se > 0 else np.nan
    G = len(np.unique(week))
    d = 1 if direction >= 0 else -1
    out = {"b": float(b[j]), "se": se, "z": z, "p_one_sided": float(norm.sf(d * z)),
           "p_one_sided_t": float(student_t.sf(d * z, G - 1)), "p_two_sided": float(2 * norm.sf(abs(z))),
           "weeks": int(G)}
    if variant == "free":
        out["slope"] = float(b[0])                    # the first cell's slope
    return out


def crossfit(y: np.ndarray, L: np.ndarray, x: np.ndarray | None, block: np.ndarray, variant: str,
             miss: np.ndarray | None = None, cells: np.ndarray | None = None) -> np.ndarray:
    """Out-of-block log-odds: for each 4-week block, the model fitted on every other block predicts it. With x None,
    the base-only model (offset: the base itself, nothing fitted)."""
    X, off = design(L, x, variant, miss, cells)
    if X.shape[1] == 0:
        return off.copy()
    eta = np.empty(len(y))
    for blk in np.unique(block):
        te = block == blk
        tr = ~te
        b, _, _ = fit_logit(X[tr], y[tr], off[tr])     # started from 0: no warm start that has seen this block
        eta[te] = off[te] + X[te] @ b
    return eta


def boot_gain(d: np.ndarray, block: np.ndarray, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """The mean of d (mLL per match) with a bootstrap over 4-week blocks (each draw: as many blocks as there are,
    with replacement; the draw's gain is its matches' mean), and the t interval over blocks beside it."""
    labels, ix = np.unique(block, return_inverse=True)
    G = len(labels)
    S = np.bincount(ix, weights=d, minlength=G)
    n = np.bincount(ix, minlength=G).astype(float)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(G, np.full(G, 1.0 / G), size=n_boot).astype(float)
    g = (W @ S) / (W @ n)
    est = float(d.mean())
    lo, hi = (float(v) for v in np.quantile(g, [0.025, 0.975]))
    infl = S - est * n
    se_t = float(np.sqrt(G / (G - 1) * np.dot(infl, infl)) / len(d)) if G > 1 else np.nan
    tq = float(student_t.ppf(0.975, G - 1)) if G > 1 else np.nan
    p_t = (float(student_t.cdf(est / se_t, G - 1)) if se_t > 0 else
           (1.0 if est > 0 else 0.0 if est < 0 else np.nan))
    return {"gain": est, "lo": lo, "hi": hi, "p_better": float((g > 0).mean()), "reading": reading(lo, hi),
            "se_boot": float(np.std(g, ddof=1)), "blocks": int(G), "lo_t": est - tq * se_t, "hi_t": est + tq * se_t,
            "se_t": se_t, "p_better_t": p_t}


def reading(lo: float, hi: float) -> str:
    return "better" if lo > 0 else "worse" if hi < 0 else "unresolved"


def gain_test(y: np.ndarray, L: np.ndarray, x: np.ndarray, block: np.ndarray, variant: str,
              miss: np.ndarray | None = None, base_eta: np.ndarray | None = None, n_boot: int = N_BOOT,
              cells: np.ndarray | None = None) -> dict:
    """Cross-fitted mLL gain of adding x to the base (positive = the feature better). base_eta: the base-only arm's
    out-of-block log-odds if already computed (it does not depend on x)."""
    eb = crossfit(y, L, None, block, variant, miss, cells) if base_eta is None else base_eta
    ef = crossfit(y, L, x, block, variant, miss, cells)
    d = 1000.0 * (log_loss(eb, y) - log_loss(ef, y))
    return boot_gain(d, block, n_boot)


# ------------------------------------------------------------------------------------------------
# The new part and the description (outcome-free)

def load_inputs(path: Path = INPUTS) -> pd.DataFrame:
    t = pd.read_parquet(path)
    t["match_id"] = t["match_id"].astype(str)
    return t.set_index("match_id")


def new_part(x: np.ndarray, Z: np.ndarray) -> tuple[np.ndarray, float]:
    """x minus its least-squares projection on Z (no intercept), fitted on the rows where x exists; Z's missing
    values 0. Returns (the residual, NaN where x is; R^2 of the projection, uncentred: the share of x's square the
    inputs reproduce)."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    Z = np.where(np.isfinite(Z), Z, 0.0)
    res = np.full(len(x), np.nan)
    if ok.sum() <= Z.shape[1]:
        return res, np.nan
    b, *_ = np.linalg.lstsq(Z[ok], x[ok], rcond=None)
    res[ok] = x[ok] - Z[ok] @ b
    r2 = 1.0 - float(np.sum(res[ok] ** 2) / np.sum(x[ok] ** 2)) if np.sum(x[ok] ** 2) > 0 else np.nan
    return res, r2


def describe(x: np.ndarray, L: np.ndarray) -> dict:
    """The feature's correlation with the base's log-odds, uncentred (0 = no difference for both, as the swap needs:
    a centred correlation would change when A and B are exchanged on some rows)."""
    ok = np.isfinite(x) & np.isfinite(L)
    den = float(np.sqrt(np.sum(x[ok] ** 2) * np.sum(L[ok] ** 2)))
    return {"corr_with_base": float(np.sum(x[ok] * L[ok]) / den) if den > 0 else np.nan}


# ------------------------------------------------------------------------------------------------
# One feature, every reading

def rms(x: np.ndarray) -> float:
    ok = np.isfinite(x)
    return float(np.sqrt(np.mean(x[ok] ** 2))) if ok.any() else np.nan


def cells_of(rows: pd.DataFrame) -> np.ndarray:
    """Each row's cell for the per-cell slopes: level group x draw (tour main, tour qualifying, Challenger main,
    Challenger qualifying)."""
    if "level_group" not in rows.columns or "draw" not in rows.columns:
        return np.zeros(len(rows), dtype=object)
    return (rows["level_group"].astype(str) + "|" + rows["draw"].astype(str)).to_numpy()


def score_one(rows: pd.DataFrame, x: np.ndarray, base: str, direction: int = 1, variants=VARIANTS,
              missing=("subset", "indicator"), base_cache: dict | None = None, n_boot: int = N_BOOT) -> list[dict]:
    """Every reading of one feature (aligned to rows) against one base. base_cache: {(variant, missing, rows' key):
    base-only out-of-block log-odds}, reused across features scored on the same rows (placebo runs)."""
    y = rows["a_won"].to_numpy(float)
    L = rows[BASES[base]].to_numpy(float)
    week = blocks(rows["tournament_date"].to_numpy(), 7)
    block = blocks(rows["tournament_date"].to_numpy(), 28)
    cell = cells_of(rows)
    present = np.isfinite(x)
    out = []
    scale = rms(x)
    if not present.any() or not np.isfinite(scale) or scale == 0:
        return [{"base": base, "matches": int(len(rows)), "coverage": float(present.mean()), "note": "no variation"}]
    xs = x / scale
    for how in missing:
        if how == "subset":
            m = present
            yy, LL, xx, ww, bb, cc, miss = y[m], L[m], xs[m], week[m], block[m], cell[m], None
        else:
            if present.all():
                continue
            yy, LL, xx, ww, bb, cc, miss = y, L, np.where(present, xs, 0.0), week, block, cell, ~present
        mask_key = hashlib.blake2b(present.tobytes(), digest_size=8).hexdigest()
        for v in variants:
            zt = z_test(yy, LL, xx, ww, v, direction, miss, cc)
            key = (v, how, mask_key)
            eb = None
            if base_cache is not None:
                if key not in base_cache:
                    base_cache[key] = crossfit(yy, LL, None, bb, v, miss, cc)
                eb = base_cache[key]
            gt = gain_test(yy, LL, xx, bb, v, miss, eb, n_boot, cc)
            out.append({"base": base, "variant": v, "missing": how, "matches": int(len(yy)),
                        "coverage": float(present.mean()), "rms": scale, "b_per_rms": zt["b"],
                        "b_per_unit": zt["b"] / scale, "se_per_rms": zt["se"], "z": zt["z"],
                        "p_one_sided": zt["p_one_sided"], "p_one_sided_t": zt["p_one_sided_t"],
                        "p_two_sided": zt["p_two_sided"], "weeks": zt["weeks"], "slope": zt.get("slope", np.nan),
                        "gain_mll": gt["gain"], "lo": gt["lo"], "hi": gt["hi"], "p_better": gt["p_better"],
                        "reading": gt["reading"], "se_boot": gt["se_boot"], "blocks": gt["blocks"], "lo_t": gt["lo_t"],
                        "hi_t": gt["hi_t"], "p_better_t": gt["p_better_t"],
                        **describe(x[present] if how == "subset" else x, L if how != "subset" else L[present])})
    return out


def score(pop: pd.DataFrame, feature: pd.Series, direction: int = 1, populations=("all", "tour", "challenger"),
          bases=("price", "model", "model_s1"), finished_only: bool = False, with_new_part: bool = True,
          inputs: pd.DataFrame | None = None, n_boot: int = N_BOOT, caches: dict | None = None) -> pd.DataFrame:
    """The long table of readings for one feature (a Series indexed by match id: A - B on Stage 0's side A).
    caches: a dict kept across calls (placebo runs) so the base-only arms are fitted once per set of rows."""
    feature = feature.copy()
    feature.index = feature.index.astype(str)
    if feature.index.duplicated().any():
        raise ValueError("the feature has two values for a match")
    rows_out = []
    for population in populations:
        for base in bases:
            if base != "price" and population in ("all", "challenger", "ch_main", "ch_qual"):
                continue                                     # the model's forecasts exist at tour level only
            rows = scored_rows(pop, population, base, finished_only)
            if len(rows) == 0:
                continue
            x = feature.reindex(rows["match_id"]).to_numpy(float)
            parts = [("raw", x, np.nan)]
            if with_new_part and population in ("tour", "tour_main", "tour_qual"):
                inputs = load_inputs() if inputs is None else inputs
                Z = inputs.reindex(rows["match_id"]).to_numpy(float)
                if np.isnan(Z).all(axis=1).any():
                    raise RuntimeError("a tour-level row lacks the model's inputs")
                r, r2 = new_part(x, Z)
                parts.append(("new part", r, r2))
            cache = None if caches is None else caches.setdefault((population, base, finished_only), {})
            for part, xp, r2 in parts:
                for r in score_one(rows, xp, base, direction, base_cache=cache, n_boot=n_boot):
                    rows_out.append({"population": population, "finished_only": finished_only, "part": part,
                                     "r2_on_inputs": r2, **r})
    return pd.DataFrame(rows_out)


# ------------------------------------------------------------------------------------------------
# The bases' log losses and the model against the price

def bases_report(pop: pd.DataFrame, n_boot: int = N_BOOT) -> dict:
    """Per population: each base's log loss (raw, and recalibrated with a cross-fitted slope per cell), and the model
    against the price on the same matches (positive = the model has the lower log loss)."""
    out = {"unit": "log loss in nats per match; gains in mLL per match, + = the second-named (arm) better; slopes "
                   "per cell (level group x draw), cross-fitted over 4-week blocks"}
    for population in POPULATIONS:
        for fin in (False, True):
            key = f"{population}{' (finished only)' if fin else ''}"
            rows = scored_rows(pop, population, "price", fin)
            if len(rows) == 0:
                continue
            y = rows["a_won"].to_numpy(float)
            blk = blocks(rows["tournament_date"].to_numpy(), 28)
            L = rows["price_logit"].to_numpy(float)
            cell = cells_of(rows)
            r = {"matches": int(len(rows)), "ll_price_raw": float(log_loss(L, y).mean()),
                 "ll_price_slope_crossfit": float(log_loss(crossfit(y, L, None, blk, "free", cells=cell), y).mean()),
                 "price_slope_by_cell": {c: float(fit_logit(L[cell == c][:, None], y[cell == c])[0][0])
                                         for c in np.unique(cell)}}
            hm = rows["has_model"].to_numpy(bool)
            if hm.any():
                rm = rows.loc[hm]
                ym, bm = y[hm], blk[hm]
                Lp = L[hm]
                Lm, Ls = rm["model_logit_full"].to_numpy(float), rm["model_logit_s1"].to_numpy(float)
                ep = crossfit(ym, Lp, None, bm, "free", cells=cell[hm])
                r.update({"model_matches": int(hm.sum()), "ll_price_raw_on_model_rows": float(log_loss(Lp, ym).mean()),
                          "ll_model_full": float(log_loss(Lm, ym).mean()),
                          "ll_model_s1": float(log_loss(Ls, ym).mean())})
                for name, a, b in (("model (both stages) vs raw price", Lp, Lm),
                                   ("model (both stages) vs price with a cross-fitted slope", ep, Lm),
                                   ("model stage 1 vs raw price", Lp, Ls),
                                   ("model both stages vs stage 1", Ls, Lm)):
                    d = 1000.0 * (log_loss(a, ym) - log_loss(b, ym))
                    r[name] = boot_gain(d, bm, n_boot)
            out[key] = r
    return out


def edge_anatomy_check(pop: pd.DataFrame, inst_frame: Path, n_boot: int = N_BOOT) -> dict:
    """The comparison edge anatomy reported (§ 3: men, Jan 2025 - 28 Jul 2026, the model (both stages) against its
    own odds input recalibrated walk-forward, +2.83 [+1.27, +4.39] for the instance of 10 Oct): recomputed for the
    live instance on its own input (price_logit_instance), the slope fitted walk-forward on 2019..Y-1 (both tours,
    compare.close_forecast)."""
    from src.eda.current_best_model import compare as CMP
    f = pd.read_parquet(inst_frame, columns=["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt",
                                             "a_won"], filters=[("season", ">=", 2019)])
    f["match_id"] = f["match_id"].astype(str)
    info = f.set_index("match_id")
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = info["a_won"].astype(float)
    rows = scored_rows(pop, "tour_main", "model")
    out = {}
    for name, last in (("Jan 2025 - 28 Jul 2026 (edge anatomy's window)", "2026-07-28"),
                       ("the whole window, to 18 Oct 2026", "2026-10-18")):
        r = rows[rows["tournament_date"] <= last]
        ids = pd.Index(r["match_id"])
        q, _ = CMP.close_forecast(info, "p_mkt", (2025, 2026), ids)
        y = r["a_won"].to_numpy(float)
        Lc = np.log(q / (1 - q))
        d = 1000.0 * (log_loss(Lc, y) - log_loss(r["model_logit_full"].to_numpy(float), y))
        res = boot_gain(d, blocks(r["tournament_date"].to_numpy(), 28), n_boot)
        res["matches"] = int(len(r))
        out[name] = res
    return out


# ------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feature", type=Path, help="a parquet file with match_id and the candidate column")
    ap.add_argument("--column", help="the candidate column (A - B on Stage 0's side A)")
    ap.add_argument("--direction", type=int, default=1, choices=(1, -1), help="the declared direction (+1: A higher wins)")
    ap.add_argument("--populations", default="all,tour,challenger")
    ap.add_argument("--bases", default="price,model,model_s1")
    ap.add_argument("--finished-only", action="store_true")
    ap.add_argument("--no-new-part", action="store_true")
    ap.add_argument("--out", type=Path, help="write the readings here (csv)")
    ap.add_argument("--last-date", help="score only matches played on or before this day (YYYY-MM-DD)")
    ap.add_argument("--bases-report", action="store_true")
    ap.add_argument("--orientation", action="store_true")
    a = ap.parse_args(argv)
    if a.last_date and a.bases_report:
        ap.error("--last-date does not apply to --bases-report, which rewrites bases.json for the whole window")
    pop = window(load_population(), a.last_date)
    from src.eda.holdouts import ledger as HL
    starts: dict[str, list[str]] = {}
    for r in HL.warn(pop["date"].min(), pop["date"].max(), tours="atp", levels="all", tool="harness.py"):
        starts.setdefault(r["first_day"], []).append(r["id"])
    if starts:
        print("note: " + "; ".join(f"--last-date {pd.Timestamp(d) - pd.Timedelta(days=1):%Y-%m-%d} leaves out "
                                   f"{', '.join(v)}" for d, v in sorted(starts.items(), reverse=True)), file=sys.stderr)
    pd.set_option("display.width", 250)
    if a.orientation:
        print(json.dumps(orientation(pop), indent=1))
        return 0
    if a.bases_report:
        from src.eda.p9_point_details import harness_population as HP
        rep = bases_report(pop)
        rep["edge_anatomy_check"] = edge_anatomy_check(pop, HP.instance_folder() / "model_frame.parquet")
        rep["orientation"] = orientation(pop)
        HP.write_json(HARNESS / "bases.json", rep)
        print(json.dumps(rep, indent=1, default=float))
        return 0
    if a.feature is None or a.column is None:
        ap.error("--feature and --column are required (or --bases-report / --orientation)")
    f = pd.read_parquet(a.feature, columns=["match_id", a.column])
    feat = pd.Series(f[a.column].to_numpy(float), index=f["match_id"].astype(str))
    res = score(pop, feat, a.direction, tuple(a.populations.split(",")), tuple(a.bases.split(",")), a.finished_only,
                not a.no_new_part)
    cols = ["population", "base", "part", "variant", "missing", "matches", "coverage", "b_per_rms", "se_per_rms", "z",
            "p_one_sided", "gain_mll", "lo", "hi", "p_better", "reading", "r2_on_inputs", "corr_with_base"]
    print(res[[c for c in cols if c in res.columns]].round(4).to_string(index=False))
    if a.out:
        res.to_csv(a.out, index=False)
        print(f"written {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
