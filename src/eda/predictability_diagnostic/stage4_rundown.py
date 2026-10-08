"""Stage 4 of the predictability diagnostic, part 2: corrected exploratory rundown.
The candidate definitions are historical research, not an approved implementation plan.

    walk-forward    for each season Y of the row's scored seasons (2013-2026; the women's box-score rows from 2019):
                    fitted on the evaluation-level matches (completed or retired) of 2010 to Y - 1 on which the row
                    exists, scored on season Y's evaluation matches on which it exists. A season is not scored when its
                    training set holds fewer than 300 matches, or fewer than 300 on which the feature is not zero (the
                    plan names no minimum; the Brief's 300 is used, and the matches left out are counted). The second
                    condition was added after the first run showed unpenalised fits separating on a handful of non-zero
                    values (the women's minutes before 2016, rare entry types).
    the model       logistic regression without an intercept (side A is random), on at most three inputs
    three scores    alone (the feature against a coin), given surface Elo (Stage 1's p_elo_surf_ret, refitted on the same
                    matches) and given the closing odds (Stage 1's normalised average, main-tour matches with odds);
                    each the baseline's log loss minus the candidate model's, per match, in milli-log-loss (positive =
                    better), with paired four-week cluster intervals and calendar-week sensitivities; raw probability
                    comparisons are explicit alongside the slope-recalibrated baseline
    shuffle band    20 copies of the feature shuffled within each season (and tour) among the matches where it exists,
                    every match carrying 20 random keys shared by every candidate; a two-input feature moves as a pair;
                    the copies go through the same fits and scores. Match length (an interaction) shuffles its
                    best-of-five flag and multiplies it by each match's own baseline log-odds
    the line        per tour and score, on a common scale (a row's improvement minus its copies' mean, over their
                    standard deviation): each copy's largest value over every row, each copy measured against the other
                    19; the line is the largest of the 20. Descriptive heuristic, NOT a conditional null or
                    family-wise error control; a positive clustered lower bound is also required for clears_line
    direction       the given-Elo model refitted inside each era and each level group: the feature's coefficient (per
                    standard deviation of the feature) with its 95% range, beside the walk-forward improvement there
    reading         an exploratory finding clears the corrected line given Elo and its given-Elo improvement is
                    positive in at least three eras; possible clears its own band but not the line; no sign stays inside
                    its band; worse falls below it. A row whose feature never varies carries no information, and a row
                    with no season that passes the minimum is not scored

Leak checks (the prompt; candidates.md section 1, rule 1): the probe cut by date, event and round
(stage4_features.py), and for the ten strongest rows per tour given Elo and every row with a clear gain over the closing
odds, the feature recomputed one match later (stage4_features.build_all(lag=True)) and scored again on the matches
where both exist: a real feature changes a little, a leak collapses.

Writes, in data/studies/predictability_diagnostic/:
    stage4_results.csv       one row per candidate x form x tour x group (all scored seasons, 2019-2026, 2022-2026, each
                             era, each level group, each season): for each of the three scores the coverage, the
                             improvement and its range, and the null band (the copies' minimum, maximum, mean and spread);
                             given Elo, the feature's coefficient refitted inside the group; per season, the walk-forward
                             fit's own coefficients
    stage4_ranking.csv       one row per candidate x form x tour: the ranking's columns
    stage4_null_copies.csv   every copy's improvement over all scored seasons (the family-wide line's inputs)
    stage4_leak_checks.csv   the lag check, and the format rebuilt from the source's record (with the matches whose
                             values differ, by season and by event and round)
    stage4_results.json      everything stage4.md and the report quote, with the plan's hash

Run after stage4_features.py: ./python.sh src/eda/predictability_diagnostic/stage4_rundown.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

PLAN = C.DOCS / "candidates.md"
CANDIDATES = C.OUT / "stage4_candidates.csv"
FEATURES = C.OUT / "stage4_features.parquet"
FEATURES_SUMMARY = C.OUT / "stage4_features_summary.json"
RESULTS_CSV = C.OUT / "stage4_results.csv"
RANKING_CSV = C.OUT / "stage4_ranking.csv"
COPIES_CSV = C.OUT / "stage4_null_copies.csv"
LEAK_CSV = C.OUT / "stage4_leak_checks.csv"
RESULTS_JSON = C.OUT / "stage4_results.json"

COPIES = 20
SEED = 20261001
MIN_TRAIN = 300                    # a season is scored when its training set holds this many matches, and this many on
                                   # which the feature is not zero (the Brief's 300; a rare feature fitted on a handful of
                                   # non-zero values separates and its unpenalised coefficient runs off)
RIDGE = 1e-6                       # a numerical guard on the Newton steps (unpenalised in substance)
EPS = 1e-12
LN2 = float(np.log(2))
SCORES = ("alone", "elo", "market")
ERAS = list(C.ERAS)
LEVEL_GROUPS = {"GS": "Grand Slams", "FIN": "Tour Finals", "T1000": "1000s", "T500": "500s", "T250": "250s",
                "GSQ": "Grand Slam qualifying", "TQ": "Tour qualifying", "CH": "Challenger / WTA 125",
                "CHQ": "Challenger / 125 qualifying"}
WINDOWS = {"2019-2026": (2019, 2026), "2022-2026": (2022, 2026)}
EVALUATION_PROTOCOL = {
    "version": "2026-10-02-corrected",
    "scaling": "feature SD fitted separately on each season's training rows; no centering",
    "baseline": "slope-recalibrated on prior seasons; raw_baseline_* reports the published probability comparator",
    "interval": "paired cluster sandwich t interval; primary four-week blocks, sensitivity calendar weeks",
    "cluster_dates": "tournament start dates, not actual match times; this does not repair chronology",
    "shuffle": "descriptive heuristic only; not a conditional null or family-wise error control",
    "clears_line": "compatibility label: positive four-week lower bound AND above descriptive shuffled line; exploratory",
    "all_years": "exploratory; includes 2010-2018 feature-constant tuning overlap",
    "2019-2026": "post-constant-tuning exploratory; feature selection reused these outcomes, not untouched holdout",
    "2022-2026": "recent exploratory sensitivity; not untouched holdout",
    "interval_selection": "pointwise; no correction for selecting features, models or historical windows",
}
SUMMARY_METRICS = ("imp", "lo", "hi", "week_lo", "week_hi", "week_clusters", "block4week_clusters",
                   "iid_lo", "iid_hi", "ci_method", "raw_baseline_imp", "raw_baseline_lo", "raw_baseline_hi",
                   "raw_baseline_week_lo", "raw_baseline_week_hi", "band_min", "band_max", "band_mean", "band_sd", "z")
LEAK_TOP = 10
LARGE_MARKET_GAIN = 1.0            # milli-log-loss: the plan's "clear" line given the market
WORKERS = max(1, min(14, (os.cpu_count() or 2) - 2))
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Logistic regression without an intercept: Newton steps for a batch of copies at once

SEPARATED = 10.0                   # a fitted coefficient (per standard deviation of its input) beyond this: no finite MLE


def newton(Z: np.ndarray, y: np.ndarray, beta: np.ndarray, max_iter: int = 60, tol: float = 1e-10,
           info: dict | None = None) -> np.ndarray:
    """The maximum-likelihood coefficients of a logistic regression without an intercept, for C design matrices that
    share the outcome: Z (C, n, k), y (n,), a starting beta (C, k). Plain Newton steps (a step longer than 4 is cut
    back) with a tiny ridge so that a constant input cannot make the Hessian singular. Where the training data
    separate (a rare input that only ever goes with one result), no finite maximum exists and the coefficient runs off;
    ``info`` receives, per copy, whether the last step converged."""
    beta = beta.copy()
    k = Z.shape[2]
    eye = np.eye(k) * RIDGE
    Zt = np.transpose(Z, (0, 2, 1))
    step = np.zeros_like(beta)
    for _ in range(max_iter):
        eta = (Z @ beta[:, :, None])[:, :, 0]
        p = expit(eta)
        g = (Zt @ (y[None, :] - p)[:, :, None])[:, :, 0] - RIDGE * beta
        H = (Zt * (p * (1 - p))[:, None, :]) @ Z + eye
        step = np.linalg.solve(H, g[:, :, None])[:, :, 0]
        big = np.abs(step).max(axis=1, keepdims=True)
        step = np.where(big > 4, step * 4 / np.maximum(big, 1e-300), step)
        beta += step
        if np.abs(step).max() < tol:
            break
    if info is not None:
        info["converged"] = np.abs(step).max(axis=1) < 1e-6
    return beta


def fit_se(Z: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """One logistic fit (no intercept) with the standard errors from the inverse of the information matrix."""
    b = newton(Z[None], y, np.zeros((1, Z.shape[1])))[0]
    p = expit(Z @ b)
    H = (Z.T * (p * (1 - p))) @ Z
    cov = np.linalg.pinv(H)
    return b, np.sqrt(np.maximum(np.diag(cov), 0))


def ll(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.where(y, -np.log(p), -np.log(1 - p))


# ------------------------------------------------------------------------------------------------
# The rows of the plan

def plan_rows(cand: pd.DataFrame, cols: set) -> list[dict]:
    """One task per candidate x form x tour: the feature's columns, its scores, whether the women's row is scored
    from 2019."""
    tasks = []
    for c in cand.itertuples(index=False):
        for form in c.forms.split(";"):
            base = f"{c.id}|{form}"
            inputs = [base] + ([f"{base}|2"] if f"{base}|2" in cols else [])
            assert base in cols, base
            for tour in c.tours.split(";"):
                tasks.append({"tour": tour, "id": c.id, "form": form, "name": c.name, "group": c.group,
                              "cols": inputs, "scores": c.scores.split(";"),
                              "from": C.WTA_BOX_FROM if (tour == "wta" and c.wta_box_from_2019 == "yes") else C.EVAL_YEARS[0],
                              "interaction": c.id == "best_of_five"})
    return tasks


# ------------------------------------------------------------------------------------------------
# Workers: one row at a time

_D: dict = {}


def init_worker() -> None:
    f = pd.read_parquet(FEATURES)
    f["tournament_date"] = cluster_dates(f)
    f["era"] = f["era"].astype(object).fillna("").astype(str)       # the warm-up seasons 2010-2012 have no era
    _D["f"] = f
    rng = np.random.default_rng(SEED)
    _D["keys"] = rng.random((len(f), COPIES))          # every match's 20 keys, the same for every candidate
    for t in C.TOURS:
        _D[t] = np.flatnonzero(f["tour"].to_numpy() == t)


def shuffled(X: np.ndarray, year: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """COPIES copies of X (n, q), each permuted within every season by that copy's keys: the j-th match of a season
    (in the table's order) gives its value to the j-th match of the same season in the key's order."""
    n = len(X)
    out = np.empty((COPIES, n, X.shape[1]))
    for c in range(COPIES):
        perm = np.lexsort((keys[:, c], year))
        out[c, perm] = X
    return out


def walk(Z: np.ndarray, y: np.ndarray, year: np.ndarray, seasons: list[int], base: np.ndarray | None) -> dict:
    """Walk-forward by season over matches sorted by season. Z (C, n, k): the model's inputs for each copy (copy 0 the
    real feature); base (n,): the baseline's one input, or None for a coin. Returns per-match log losses of every copy
    and of the baseline (missing where not scored) and the seasons scored."""
    Cc, n, k = Z.shape
    llm = np.full((Cc, n), np.nan)
    llb = np.full(n, np.nan)
    llraw = np.full(n, np.nan)
    beta = np.zeros((Cc, k))
    bb = np.zeros((1, 1))
    scored, skipped, coefs = [], {}, {}
    sep_real = sep_copies = 0
    # matches on which the real feature is not zero (the copies, shuffled within seasons, have the same count)
    nonzero = np.cumsum(np.r_[0, (Z[0][:, (0 if base is None else 1):] != 0).any(axis=1)])
    for Y in seasons:
        lo, hi = np.searchsorted(year, Y, "left"), np.searchsorted(year, Y, "right")
        if hi == lo:
            continue
        if lo < MIN_TRAIN or nonzero[lo] < MIN_TRAIN:
            skipped[int(Y)] = {"matches": int(hi - lo), "training": int(lo), "training_nonzero": int(nonzero[lo])}
            continue
        info = {}
        # Keep warm-start coefficients in original units across changing training scales.
        # No held-out feature values enter scaling or the numerical ridge penalty.
        scales = Z[:, :lo].std(axis=1)
        scales = np.where(scales > 1e-12, scales, 1.0)
        if base is not None:
            scales[:, 0] = 1.0  # retain interpretable baseline calibration slopes
        start = beta * scales
        scaled_beta = newton(Z[:, :lo] / scales[:, None, :], y[:lo],
                             np.where(np.abs(start) > SEPARATED, 0.0, start), info=info)
        beta = scaled_beta / scales
        feat = scaled_beta if base is None else scaled_beta[:, 1:]
        off = (np.abs(feat).max(axis=1) > SEPARATED) | ~info["converged"]
        sep_real += int(off[0])
        sep_copies += int(off[1:].sum())
        p = expit((Z[:, lo:hi] @ beta[:, :, None])[:, :, 0])
        llm[:, lo:hi] = ll(p, y[lo:hi][None, :])
        if base is None:
            llb[lo:hi] = LN2
            llraw[lo:hi] = LN2
        else:
            bb = newton(base[None, :lo, None], y[:lo], bb)
            llb[lo:hi] = ll(expit(base[lo:hi] * bb[0, 0]), y[lo:hi])
            llraw[lo:hi] = ll(expit(base[lo:hi]), y[lo:hi])
        # the real model's fitted coefficients for this season (the feature per standard deviation; the baseline's
        # input, in the model and alone)
        coefs[int(Y)] = {"feature": [float(v) for v in feat[0]],
                         "feature_training_sd": [float(v) for v in (scales[0] if base is None else scales[0, 1:])],
                         "base_in_model": None if base is None else float(beta[0, 0]),
                         "base_alone": None if base is None else float(bb[0, 0])}
        scored.append(int(Y))
    return {"llm": llm, "llb": llb, "llraw": llraw, "scored": scored, "skipped": skipped, "coefs": coefs,
            "separated_real": sep_real, "separated_copies": sep_copies}


def cluster_dates(frame: pd.DataFrame) -> np.ndarray:
    """Resolve cluster dates in row order; never silently substitute independent-match errors."""
    if "tournament_date" in frame:
        dates = pd.to_datetime(frame["tournament_date"])
    else:
        source = C.load_matches(["match_id", "tournament_date"])
        dates = pd.to_datetime(frame["match_id"].map(source.set_index("match_id")["tournament_date"]))
    if dates.isna().any():
        raise ValueError("Every scored row needs a tournament_date for dependence-aware uncertainty")
    return dates.to_numpy(dtype="datetime64[ns]")


def paired_interval(values: np.ndarray, clusters: np.ndarray) -> dict:
    """Paired mean loss gain with a cluster-sandwich SE and G-1 t reference."""
    values = np.asarray(values, dtype=float)
    labels, ix = np.unique(clusters, return_inverse=True)
    n, count = len(values), len(labels)
    mean = float(values.mean()) if n else np.nan
    influence = np.bincount(ix, weights=values - mean)
    se = np.sqrt(count / (count - 1) * np.dot(influence, influence)) / n if count > 1 else np.nan
    radius = student_t.ppf(0.975, count - 1) * se if count > 1 else np.nan
    return {"clusters": count, "lo": float(1000 * (mean - radius)), "hi": float(1000 * (mean + radius))}


def summarize(d: np.ndarray, mask: np.ndarray, dates: np.ndarray | None = None,
              raw_d: np.ndarray | None = None) -> dict:
    """The improvement (milli-log-loss, positive = better) of the real feature (row 0 of d) and of each copy on the
    matches in ``mask``, with the real one's 95% range."""
    n = int(mask.sum())
    if n == 0:
        return {"n": 0, "imp": np.nan, "lo": np.nan, "hi": np.nan, "ci_method": "no_scored_matches"}
    real = d[0, mask]
    m = 1000 * real.mean()
    se = 1000 * real.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    result = {"n": n, "imp": float(m), "iid_lo": float(m - 1.96 * se), "iid_hi": float(m + 1.96 * se)}
    result.update(lo=np.nan, hi=np.nan, ci_method="unavailable_without_cluster_dates")
    if dates is not None:
        dates = np.asarray(dates, dtype="datetime64[D]")
        if np.isnat(dates[mask]).any():
            raise ValueError("Missing tournament date in scored interval")
        # Monday origin: calendar weeks and contiguous four-week blocks, including across years.
        days = (dates[mask] - np.datetime64("2010-01-04")).astype(int)
        for name, width in (("week", 7), ("block4week", 28)):
            ci = paired_interval(real, days // width)
            result.update({f"{name}_{k}": v for k, v in ci.items()})
        result.update(lo=result["block4week_lo"], hi=result["block4week_hi"], ci_method="paired_four_week_cluster_t")
    cp = 1000 * d[1:, mask].mean(axis=1)
    sd = float(cp.std(ddof=1)) if len(cp) > 1 else np.nan
    result.update(band_min=float(cp.min()) if len(cp) else np.nan, band_max=float(cp.max()) if len(cp) else np.nan,
                  band_mean=float(cp.mean()) if len(cp) else np.nan, band_sd=sd,
                  z=float((m - cp.mean()) / sd) if sd > 0 else np.nan,
                  above_band=bool(len(cp) and m > 0 and m > cp.max()), below_band=bool(len(cp) and m < cp.min()),
                  directional=bool(n < C.DIRECTIONAL_ONLY_BELOW), copies=[float(v) for v in cp])
    if raw_d is not None:
        raw = summarize(np.asarray(raw_d)[None, :], mask, dates)
        result.update({f"raw_baseline_{k}": raw[k] for k in ("imp", "lo", "hi", "week_lo", "week_hi") if k in raw})
    return result


def clears_heuristic_line(g: dict, line: dict | None) -> bool:
    """Compatibility flag, NOT family-wise significance: require positive clustered evidence too."""
    return bool(g and line and g.get("imp", 0) > 0 and g.get("lo", np.nan) > 0
                and g.get("ci_method") == "paired_four_week_cluster_t"
                and np.isfinite(g.get("z", np.nan)) and g["z"] > line["line"])


def score_row(task: dict) -> dict:
    f = _D["f"]
    idx_t = _D[task["tour"]]
    year_all = f["year"].to_numpy()[idx_t]
    X = np.column_stack([f[c].to_numpy(dtype="float64")[idx_t] for c in task["cols"]])
    exists = np.isfinite(X).all(axis=1)
    idx = idx_t[exists]
    Xe = X[exists]
    year = year_all[exists]
    assert (np.diff(year) >= 0).all()
    y = f["a_won"].to_numpy()[idx]
    ev = f["evaluation"].to_numpy()[idx]
    era = f["era"].astype(object).to_numpy()[idx]
    group = f["group"].to_numpy()[idx]
    dates = cluster_dates(f)[idx]
    l_elo = logit(np.clip(f["p_elo"].to_numpy(dtype="float64")[idx], 1e-9, 1 - 1e-9))
    p_mkt = f["p_mkt"].to_numpy(dtype="float64")[idx]
    has_mkt = np.isfinite(p_mkt)
    l_mkt = logit(np.clip(np.nan_to_num(p_mkt, nan=0.5), 1e-9, 1 - 1e-9))
    first = task["from"]
    seasons = list(range(first, C.EVAL_YEARS[-1] + 1))
    out = {k: task[k] for k in ("tour", "id", "form", "name", "group", "from", "cols")}
    sd = Xe.std(axis=0)
    out["constant"] = bool((sd == 0).any())
    # what could be scored, for coverage: the tour's evaluation matches in the row's scored seasons (with odds for the
    # market score), and on how many the row exists
    ev_t = f["evaluation"].to_numpy()[idx_t] & (year_all >= first)
    mk_t = ev_t & np.isfinite(f["p_mkt"].to_numpy(dtype="float64")[idx_t])
    out["eligible"] = {"alone": int(ev_t.sum()), "elo": int(ev_t.sum()), "market": int(mk_t.sum())}
    out["exists"] = {"alone": int((ev_t & exists).sum()), "elo": int((ev_t & exists).sum()), "market": int((mk_t & exists).sum())}
    # what each group could hold, for its coverage: the tour's evaluation matches of the scored seasons in the group
    era_t, grp_t = f["era"].to_numpy()[idx_t], f["group"].to_numpy()[idx_t]
    gm_t = {"all": np.ones(len(idx_t), dtype=bool)}
    for w, (a, b) in WINDOWS.items():
        gm_t[w] = (year_all >= a) & (year_all <= b)
    for e in ERAS:
        gm_t[e] = era_t == e
    for g in LEVEL_GROUPS:
        gm_t[g] = grp_t == g
    for Y in range(first, C.EVAL_YEARS[-1] + 1):
        gm_t[f"season {Y}"] = year_all == Y
    out["eligible_by_group"] = {g: {"alone": int((ev_t & m).sum()), "elo": int((ev_t & m).sum()), "market": int((mk_t & m).sum())}
                                for g, m in gm_t.items()}
    out["scores"] = {}
    if out["constant"]:
        return out
    Xs = Xe  # walk() fits feature scales on each training fold only
    keys = _D["keys"][idx]
    copies = shuffled(Xs, year, keys)                                  # (COPIES, n, q)
    allX = np.concatenate([Xs[None], copies], axis=0)                  # copy 0: the real feature
    groups_t = {"all": np.ones(len(idx), dtype=bool)}
    for w, (a, b) in WINDOWS.items():
        groups_t[w] = (year >= a) & (year <= b)
    for e in ERAS:
        groups_t[e] = era == e
    for g in LEVEL_GROUPS:
        groups_t[g] = group == g
    for Y in seasons:
        groups_t[f"season {Y}"] = year == Y
    for score in task["scores"]:
        sub = has_mkt if score == "market" else np.ones(len(idx), dtype=bool)
        if sub.sum() < MIN_TRAIN:
            continue
        ys, yr = y[sub], year[sub]
        if task["interaction"]:
            base = l_elo[sub] if score == "elo" else l_mkt[sub]
            Z = np.concatenate([np.broadcast_to(base[None, :, None], (COPIES + 1, len(base), 1)),
                                (allX[:, sub, :] * base[None, :, None])], axis=2)
        elif score == "alone":
            Z = allX[:, sub, :]
        else:
            base = l_elo[sub] if score == "elo" else l_mkt[sub]
            Z = np.concatenate([np.broadcast_to(base[None, :, None], (COPIES + 1, len(base), 1)), allX[:, sub, :]], axis=2)
        Z = np.ascontiguousarray(Z)
        w = walk(Z, ys, yr, seasons, None if score == "alone" else (l_elo[sub] if score == "elo" else l_mkt[sub]))
        d = w["llb"][None, :] - w["llm"]                                # (C, n): positive = better
        scored = np.isfinite(d[0]) & ev[sub]
        res = {"seasons_scored": w["scored"], "skipped_seasons": w["skipped"],
               "not_scored_for_training": int(sum(v["matches"] for v in w["skipped"].values())), "groups": {},
               "separated_real": w["separated_real"], "separated_copies": w["separated_copies"], "coefs": w["coefs"]}
        for gname, gm in groups_t.items():
            res["groups"][gname] = summarize(d, scored & gm[sub], dates[sub],
                                                w["llraw"] - w["llm"][0])
        # direction: the given-Elo model refitted inside each era and level group (and over all scored seasons)
        if score == "elo":
            dirs = {}
            for gname, gm in groups_t.items():
                if gname in WINDOWS or gname.startswith("season "):     # the plan's direction: all, eras, levels
                    continue
                m = scored & gm[sub]
                if m.sum() < 30 or (Z[0][m][:, 1:].std(axis=0) == 0).any():   # too few, or the feature does not vary there
                    continue
                direction_z = Z[0][m].copy()
                direction_z[:, 1:] /= direction_z[:, 1:].std(axis=0)
                b, se = fit_se(direction_z, ys[m])
                dirs[gname] = {"n": int(m.sum()), "coef": [float(v) for v in b[1:]], "lo": [float(v) for v in (b - 1.96 * se)[1:]],
                               "hi": [float(v) for v in (b + 1.96 * se)[1:]], "elo_coef": float(b[0])}
            res["direction"] = dirs
        out["scores"][score] = res
    return out


# ------------------------------------------------------------------------------------------------
# The historical candidate expectations (candidates.md section 3)

SCALE_WORDS = ("none", "weak", "moderate", "strong", "small", "clear", "worse")
MATCHUP_NAMES = {"Points": "mu_points", "Games": "mu_games", "Break points": "mu_bp",
                 "The serve point from its parts": "mu_components"}                        # section 3.2
FEATURE_ALIASES = {"Ratings through the iid model": "rating_matchup",
                   "Big-point play on return": "bigpoint_return"}                          # section 3.3


def plan_expectations(cand: pd.DataFrame) -> dict:
    """Per candidate id: the plan's expected Alone / Given Elo / Given market / Sign cells, as written."""
    text = PLAN.read_text(encoding="utf-8")
    # only section 3 ("The candidates") holds the expectation tables
    text = text.split("\n## 3. The candidates", 1)[1].split("\n## 4.", 1)[0]
    stat_ids = cand.loc[cand["group"].eq("statistic"), "id"].tolist()
    by_name = {n: i for n, i in zip(cand["name"], cand["id"])}
    out = {}
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 8 and cells[0].isdigit():                    # 3.1: # | statistic | why | alone | elo | market | sign | form
            out[stat_ids[int(cells[0]) - 1]] = {"alone": cells[3], "elo": cells[4], "market": cells[5], "sign": cells[6], "form": cells[7]}
        elif len(cells) == 8 and cells[0] in MATCHUP_NAMES:           # 3.2: matchup | statistics | why | alone | elo | market | sign | form
            out[MATCHUP_NAMES[cells[0]]] = {"alone": cells[3], "elo": cells[4], "market": cells[5], "sign": cells[6], "form": cells[7]}
        elif len(cells) == 8 and (cells[0] in by_name or cells[0] in FEATURE_ALIASES):   # 3.3: feature | before | data | why | alone | elo | market | sign
            cid = by_name.get(cells[0], FEATURE_ALIASES.get(cells[0]))
            out[cid] = {"alone": cells[4], "elo": cells[5], "market": cells[6], "sign": cells[7], "form": ""}
    missing = set(cand["id"]) - set(out)
    assert not missing, missing
    return out


def expected_for(exp: dict, cid: str, score: str, tour: str, form: str, all_exp: dict) -> str | None:
    """One expectation cell read for a tour and form: "X (men), Y (women)", "X (adjusted: Y)", "as the ranking"."""
    cell = exp[cid][score]
    if cell in ("–", "-", ""):
        return None
    if cell.startswith("as the ranking"):
        return expected_for(all_exp, "rank", score, tour, form, all_exp)
    m = re.match(r"^(\w+) \(men\), (\w+) \(women\)$", cell)
    if m:
        return m.group(1) if tour == "atp" else m.group(2)
    m = re.match(r"^(\w+) \(adjusted: (\w+)\)$", cell)
    if m:
        return m.group(2) if form == "adjusted" else m.group(1)
    word = cell.split()[0]
    return word if word in SCALE_WORDS else cell


def observed_category(score: str, g: dict) -> str | None:
    """The plan's scale (candidates.md, section 3) applied to a score over all scored seasons."""
    if not g or g.get("n", 0) == 0:
        return None
    if g["below_band"] or g.get("imp", 0) < 0:
        return "worse"
    if (not g["above_band"] or g.get("imp", 0) <= 0 or not g.get("lo", np.nan) > 0
            or g.get("ci_method") != "paired_four_week_cluster_t"):
        return "none"
    v = g["imp"]
    if score == "alone":
        return "strong" if v >= 40 else ("moderate" if v >= 10 else "weak")
    return "clear" if v >= 1 else "small"


# ------------------------------------------------------------------------------------------------
# The family-wide line

def family_line(rows: list[dict], tour: str, score: str) -> dict:
    """Each copy's largest standardised value over every row (measured against the other 19 copies of its row); the
    line is the largest of the 20. Rows whose copies do not vary are left out."""
    mats = []
    for r in rows:
        g = r["scores"].get(score, {}).get("groups", {}).get("all") if r["tour"] == tour else None
        if not g or g.get("n", 0) == 0 or not np.isfinite(g.get("band_sd", np.nan)) or g["band_sd"] <= 0:
            continue
        mats.append(g["copies"])
    if not mats:
        return {"rows": 0, "line": np.nan, "copy_maxima": [], "copy_maxima_median": np.nan,
                "interpretation": "descriptive shuffled-feature heuristic; not a conditional test"}
    M = np.array(mats)                                              # rows x copies
    zs = np.empty_like(M)
    for c in range(M.shape[1]):
        others = np.delete(M, c, axis=1)
        zs[:, c] = (M[:, c] - others.mean(axis=1)) / others.std(axis=1, ddof=1)
    maxima = zs.max(axis=0)
    return {"rows": int(M.shape[0]), "line": float(maxima.max()), "copy_maxima": [float(v) for v in maxima],
            "copy_maxima_median": float(np.median(maxima)),
            "interpretation": "descriptive shuffled-feature heuristic; not a conditional test"}


# ------------------------------------------------------------------------------------------------
# Leak check: the strongest rows one match later

FORMAT_IDS = ("mu_points", "mu_games", "mu_components", "rating_matchup", "best_of_five")


def compare(f: pd.DataFrame, p: dict, Xo: np.ndarray, Xn: np.ndarray, check: str,
            labels: np.ndarray | None = None) -> dict:
    """Score a row's feature as built (Xo) and as rebuilt (Xn), real feature only, on the matches where both exist.
    The matches whose values differ are counted by season and, given ``labels`` (event and round), by label."""
    both = np.isfinite(Xo).all(axis=1) & np.isfinite(Xn).all(axis=1)
    rec = {"check": check, **{k: p[k] for k in ("tour", "id", "form")}}
    for kind, X in (("original", Xo), ("rebuilt", Xn)):
        g = f.assign(**{f"_x{j}": np.where(both, X[:, j], np.nan) for j in range(X.shape[1])})
        res = score_plain(g, p, [f"_x{j}" for j in range(X.shape[1])])
        for score, v in res.items():
            rec[f"{kind}_{score}"] = v["imp"]
            rec[f"{kind}_{score}_lo"] = v["lo"]
            rec[f"{kind}_{score}_hi"] = v["hi"]
            rec[f"n_{score}"] = v["n"]
    a, b = Xo[both, 0], Xn[both, 0]
    rec["feature_corr"] = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else np.nan
    # the stored features are float32: compare at that precision
    tour_rows = f["tour"].eq(p["tour"]).to_numpy()
    diff = (Xo.astype("float32") != Xn.astype("float32")).any(axis=1) & both & tour_rows
    rec["values_differ"] = int(diff.sum())
    if diff.any():
        seasons = pd.Series(f["year"].to_numpy()[diff]).value_counts().sort_index()
        rec["differ_by_season"] = "; ".join(f"{int(k)}: {int(v)}" for k, v in seasons.items())
        if labels is not None:
            events = pd.Series(labels[diff]).value_counts()
            rec["differ_by_event"] = "; ".join(f"{k}: {int(v)}" for k, v in events.head(5).items())
    tour_ev = f["tour"].eq(p["tour"]).to_numpy() & f["evaluation"].to_numpy()
    rec["exists_original"] = int(np.isfinite(Xo).all(axis=1)[tour_ev].sum())
    rec["exists_both"] = int(both[tour_ev].sum())
    return rec


def leak_checks(cand: pd.DataFrame, picks: list[dict], tasks: list[dict]) -> list[dict]:
    """Two rebuilds of features, each scored against the features as built:
        one match later   the picked rows (stage4_features.build_all(lag=True)): a real feature changes a little, a leak
                          collapses
        format recorded   every row that uses the match's format (the matchups through the iid model, the ratings
                          through it, match length): the plan reads best of five from the match's own score, which the
                          probe flags; rebuilt from the source's record alone (stage4_features.best_of_five("recorded"))"""
    from src.eda.predictability_diagnostic import stage4_features as F
    ids = sorted({p["id"] for p in picks if p["id"] != "best_of_five"})
    R, typical = F.load_rows()
    xd = F.stat_xd(R)
    pbp = F.pbp_history(R)
    ctx, _ = F.constants(R, xd, typical, pbp)
    pool = F.pool_mask(R)
    f = pd.read_parquet(FEATURES)
    assert len(f) == int(pool.sum())
    A = np.flatnonzero(pool) * 2                                    # A's row of each pool match, as the features
    assert (R["match_id"].to_numpy()[A] == f["match_id"].to_numpy()).all()
    rounds = {v: k for k, v in C.ROUND_ORDER.items()}
    labels = (R["tournament_name"].astype(str).to_numpy()[A] + " "
              + R["round_order"].map(rounds).astype(str).to_numpy()[A])
    log(f"leak check: rebuilding {len(ids)} candidates one match later: {', '.join(ids)}")
    lagged = F.build_all(R, ctx, cand, pbp, pool, lag=True, only=set(ids))
    log("leak check: rebuilding the format-dependent candidates with the recorded format")
    recorded = F.build_all(R, {**ctx, "format_from": "recorded"}, cand, pbp, pool, only=set(FORMAT_IDS))
    out = []
    for p in picks:
        if p["id"] == "best_of_five":
            out.append({"check": "one match later", **{k: p[k] for k in ("tour", "id", "form")}, "why": p["why"],
                        "note": "the match's own format, not a history: no lag (see the format check)"})
            continue
        Xo = np.column_stack([f[c].to_numpy(dtype="float64") for c in p["cols"]])
        Xn = np.column_stack([np.asarray(lagged[c], dtype="float64") for c in p["cols"]])
        rec = {**compare(f, p, Xo, Xn, "one match later"), "why": p["why"]}
        out.append(rec)
        log(f"  lag {p['tour']} {p['id']} {p['form']}: given Elo {rec.get('original_elo', np.nan):.2f} -> {rec.get('rebuilt_elo', np.nan):.2f}")
    for p in tasks:
        if p["id"] not in FORMAT_IDS:
            continue
        Xo = np.column_stack([f[c].to_numpy(dtype="float64") for c in p["cols"]])
        Xn = np.column_stack([np.asarray(recorded[c], dtype="float64") for c in p["cols"]])
        rec = {**compare(f, p, Xo, Xn, "format recorded", labels), "why": "uses the match's format, read from its score"}
        out.append(rec)
        log(f"  format {p['tour']} {p['id']} {p['form']}: given Elo {rec.get('original_elo', np.nan):.3f} -> "
            f"{rec.get('rebuilt_elo', np.nan):.3f} ({rec['values_differ']} matches differ)")
    return out


def score_plain(f: pd.DataFrame, task: dict, cols: list[str]) -> dict:
    """The real feature's three scores over all its scored seasons (no copies), as score_row computes them."""
    t = f["tour"].to_numpy() == task["tour"]
    X = np.column_stack([f[c].to_numpy(dtype="float64") for c in cols])
    ex = t & np.isfinite(X).all(axis=1)
    idx = np.flatnonzero(ex)
    Xe = X[idx]
    Xs = Xe
    dates = cluster_dates(f)[idx]
    year, y, ev = f["year"].to_numpy()[idx], f["a_won"].to_numpy()[idx], f["evaluation"].to_numpy()[idx]
    l_elo = logit(np.clip(f["p_elo"].to_numpy(dtype="float64")[idx], 1e-9, 1 - 1e-9))
    p_mkt = f["p_mkt"].to_numpy(dtype="float64")[idx]
    has = np.isfinite(p_mkt)
    l_mkt = logit(np.clip(np.nan_to_num(p_mkt, nan=0.5), 1e-9, 1 - 1e-9))
    seasons = list(range(task["from"], C.EVAL_YEARS[-1] + 1))
    out = {}
    for score in task["scores"]:
        sub = has if score == "market" else np.ones(len(idx), dtype=bool)
        if score == "alone":
            Z, base = Xs[sub][None], None
        elif task.get("interaction"):
            base = (l_elo if score == "elo" else l_mkt)[sub]
            Z = np.concatenate([base[:, None], (Xe[sub] * base[:, None])], axis=1)[None]
        else:
            base = (l_elo if score == "elo" else l_mkt)[sub]
            Z = np.concatenate([base[:, None], Xs[sub]], axis=1)[None]
        w = walk(np.ascontiguousarray(Z), y[sub], year[sub], seasons, base)
        d = (w["llb"][None, :] - w["llm"])
        m = np.isfinite(d[0]) & ev[sub]
        out[score] = summarize(d, m, dates[sub], w["llraw"] - w["llm"][0])
    return out


# ------------------------------------------------------------------------------------------------

def main() -> int:
    cand = pd.read_csv(CANDIDATES)
    fsum = json.loads(FEATURES_SUMMARY.read_text(encoding="utf-8"))
    plan_hash = __import__("hashlib").sha256(PLAN.read_bytes()).hexdigest()
    assert plan_hash == fsum["plan"]["sha256"], "candidates.md changed since the features were built"
    cols = set(pd.read_parquet(FEATURES).columns)
    tasks = plan_rows(cand, cols)
    log(f"{len(tasks)} rows to score with {WORKERS} workers")
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"              # one thread per worker: the workers share the cores
    results = []
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_worker) as ex:
        for i, r in enumerate(ex.map(score_row, tasks, chunksize=1)):
            results.append(r)
            if (i + 1) % 25 == 0:
                log(f"  scored {i + 1} of {len(tasks)}")
    log("all rows scored")
    exp = plan_expectations(cand)

    # the family-wide line, per tour and score
    lines = {f"{t}|{s}": family_line(results, t, s) for t in C.TOURS for s in SCORES
             if any(r["tour"] == t and s in r["scores"] for r in results)}
    # per row: reading, categories, eras sharing the sign
    ranking, long, copies = [], [], []
    for r in results:
        base = {k: r[k] for k in ("tour", "id", "form", "name", "group")}
        rec = {**base, "inputs": len(r["cols"]), "scored_from": r["from"], "constant": r["constant"]}
        for s in SCORES:
            sc = r["scores"].get(s)
            g = sc["groups"]["all"] if sc else {}
            rec[f"{s}_eligible"] = r["eligible"][s]
            rec[f"{s}_exists"] = r["exists"][s]
            rec[f"{s}_scored"] = g.get("n", 0)
            rec[f"{s}_coverage"] = g.get("n", 0) / r["eligible"][s] if r["eligible"][s] else np.nan
            for k in SUMMARY_METRICS:
                rec[f"{s}_{k}"] = g.get(k, np.nan)
            rec[f"{s}_above_band"] = g.get("above_band")
            rec[f"{s}_below_band"] = g.get("below_band")
            ln = lines.get(f"{r['tour']}|{s}")
            rec[f"{s}_clears_line"] = clears_heuristic_line(g, ln)
            rec[f"{s}_observed"] = observed_category(s, g) if not r["constant"] else "none (constant)"
            rec[f"{s}_expected"] = expected_for(exp, r["id"], s, r["tour"], r["form"], exp)
            for w in WINDOWS:
                gw = sc["groups"].get(w, {}) if sc else {}
                rec[f"{s}_{w}"] = gw.get("imp", np.nan)
                rec[f"{s}_{w}_n"] = gw.get("n", 0)
            if sc:
                rec[f"{s}_not_scored_for_training"] = sc["not_scored_for_training"]
                rec[f"{s}_skipped_seasons"] = "; ".join(
                    f"{y} ({v['matches']} matches; training {v['training']}, non-zero {v['training_nonzero']})"
                    for y, v in sc["skipped_seasons"].items())
                rec[f"{s}_separated_real"] = sc["separated_real"]
                rec[f"{s}_separated_copies"] = sc["separated_copies"]
                for gname, gg in sc["groups"].items():
                    if gg.get("n", 0) == 0:
                        continue
                    kind = ("all" if gname == "all" else "window" if gname in WINDOWS else "era" if gname in ERAS
                            else "season" if gname.startswith("season ") else "level")
                    elig = r["eligible_by_group"][gname][s]
                    row = {**base, "score": s, "group_kind": kind, "group_name": gname, "eligible": elig,
                           "coverage": gg["n"] / elig if elig else np.nan,
                           **{k: gg.get(k) for k in ("n", *SUMMARY_METRICS, "above_band", "below_band", "directional")}}
                    if kind == "season":
                        cf = sc["coefs"].get(int(gname.split()[1]))
                        if cf:
                            row.update({"walk_coef": cf["feature"][0], "walk_base_in_model": cf["base_in_model"],
                                        "walk_base_alone": cf["base_alone"]})
                    dr = sc.get("direction", {}).get(gname)
                    if dr:
                        row.update({"coef": dr["coef"][0], "coef_lo": dr["lo"][0], "coef_hi": dr["hi"][0],
                                    "coef2": dr["coef"][1] if len(dr["coef"]) > 1 else np.nan,
                                    "coef2_lo": dr["lo"][1] if len(dr["lo"]) > 1 else np.nan,
                                    "coef2_hi": dr["hi"][1] if len(dr["hi"]) > 1 else np.nan})
                    long.append(row)
                gall = sc["groups"]["all"]
                if gall.get("n", 0):
                    copies.append({**base, "score": s, **{f"copy_{c + 1}": v for c, v in enumerate(gall["copies"])}})
        e = r["scores"].get("elo")
        eras_pos = [x for x in ERAS if e and e["groups"].get(x, {}).get("n", 0) and e["groups"][x]["imp"] > 0]
        eras_have = [x for x in ERAS if e and e["groups"].get(x, {}).get("n", 0)]
        rec["eras_scored"] = len(eras_have)
        rec["eras_positive"] = len(eras_pos)
        d_all = (e or {}).get("direction", {}).get("all")
        rec["sign_coef"] = d_all["coef"][0] if d_all else np.nan
        rec["sign_lo"] = d_all["lo"][0] if d_all else np.nan
        rec["sign_hi"] = d_all["hi"][0] if d_all else np.nan
        rec["sign_observed"] = (None if not d_all else ("+" if d_all["lo"][0] > 0 else ("−" if d_all["hi"][0] < 0 else "unclear")))
        rec["sign_expected"] = exp[r["id"]]["sign"]
        rec["form_expected_best"] = exp[r["id"]]["form"]
        if r["constant"]:
            rec["reading"] = "no information (constant)"
        elif not e or e["groups"]["all"].get("n", 0) == 0:
            rec["reading"] = "not scored"
        elif rec["elo_clears_line"] and rec["eras_positive"] >= 3:
            rec["reading"] = "finding"
        elif rec["elo_above_band"]:
            rec["reading"] = "possible"
        elif rec["elo_below_band"]:
            rec["reading"] = "worse"
        else:
            rec["reading"] = "no sign"
        ranking.append(rec)
    rank = pd.DataFrame(ranking)
    rank["rank_given_elo"] = rank.groupby("tour")["elo_imp"].rank(ascending=False, method="first")
    rank = rank.sort_values(["tour", "rank_given_elo"]).reset_index(drop=True)
    rank.to_csv(RANKING_CSV, index=False)
    # one row per candidate x form x tour x group: coverage, the three scores and their null bands side by side, and
    # the given-Elo direction inside the group
    L = pd.DataFrame(long)
    keys = ["tour", "id", "form", "name", "group", "group_kind", "group_name"]
    vals = ["eligible", "n", "coverage", *SUMMARY_METRICS,
            "above_band", "below_band", "directional", "walk_coef", "walk_base_in_model", "walk_base_alone"]
    wide = L.set_index(keys + ["score"])[vals].unstack("score")
    wide.columns = [f"{s}_{v}" for v, s in wide.columns]
    wide = wide[[f"{s}_{v}" for s in SCORES for v in vals if f"{s}_{v}" in wide.columns]].reset_index()
    dcols = [c for c in ("coef", "coef_lo", "coef_hi", "coef2", "coef2_lo", "coef2_hi") if c in L]
    coefs = L[L["score"].eq("elo")][keys + dcols].rename(columns={c: f"elo_{c}" for c in dcols})
    wide = wide.merge(coefs, on=keys, how="left")
    kind_order = {"all": 0, "window": 1, "era": 2, "level": 3, "season": 4}
    wide = wide.sort_values(["tour", "id", "form"], kind="mergesort")
    wide = wide.assign(_k=wide["group_kind"].map(kind_order)).sort_values(["tour", "id", "form", "_k"], kind="mergesort").drop(columns="_k")
    wide.to_csv(RESULTS_CSV, index=False)
    pd.DataFrame(copies).to_csv(COPIES_CSV, index=False)
    log(f"wrote {RANKING_CSV.name}, {RESULTS_CSV.name}, {COPIES_CSV.name}")

    # leak checks: the ten strongest rows per tour given Elo, and any clear gain over the closing odds
    picks = []
    for t in C.TOURS:
        top = rank[rank["tour"].eq(t) & ~rank["constant"]].nsmallest(LEAK_TOP, "rank_given_elo")
        picks += [{**next(x for x in tasks if x["tour"] == t and x["id"] == rr.id and x["form"] == rr.form),
                   "why": "ten strongest given Elo"} for rr in top.itertuples()]
    # every clear gain over the closing odds (1 milli-log-loss or more, its range above zero) is a suspected leak; the rows
    # that clear the family-wide line given the odds are checked too, as a precaution
    big = rank[(rank["market_imp"] >= LARGE_MARKET_GAIN) & (rank["market_lo"] > 0)]
    line_mkt = rank[rank["market_clears_line"].astype(bool)]
    for frame, why in ((big, "clear gain over the closing odds"), (line_mkt, "clears the family-wide line given the closing odds")):
        for rr in frame.itertuples():
            if not any(p["tour"] == rr.tour and p["id"] == rr.id and p["form"] == rr.form for p in picks):
                picks.append({**next(x for x in tasks if x["tour"] == rr.tour and x["id"] == rr.id and x["form"] == rr.form),
                              "why": why})
    leak = leak_checks(cand, picks, tasks)
    pd.DataFrame(leak).to_csv(LEAK_CSV, index=False)
    log(f"wrote {LEAK_CSV.name}")

    res = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
           "evaluation_protocol": EVALUATION_PROTOCOL,
           "plan": fsum["plan"], "settings": {"copies": COPIES, "seed": SEED, "min_train": MIN_TRAIN, "ridge": RIDGE,
                                               "eras": ERAS, "level_groups": LEVEL_GROUPS, "windows": WINDOWS,
                                               "directional_below": C.DIRECTIONAL_ONLY_BELOW, "leak_top": LEAK_TOP,
                                               "large_market_gain": LARGE_MARKET_GAIN, "workers": WORKERS},
           "lines": lines, "ranking": json.loads(rank.to_json(orient="records")),
           # by era, level group and window, given Elo and given the market (the CSV keeps every group and score)
           "by_group": json.loads(pd.DataFrame(long).query("group_kind != 'all' and score != 'alone'")
                                  [["tour", "id", "form", "score", "group_kind", "group_name", "n", "imp", "lo", "hi",
                                    "band_min", "band_max", "directional"]
                                   + [c for c in ("coef", "coef_lo", "coef_hi", "walk_coef", "walk_base_in_model",
                                                  "walk_base_alone") if c in pd.DataFrame(long)]]
                                  .round(4).to_json(orient="records")),
           "leak_checks": json.loads(pd.DataFrame(leak).to_json(orient="records")),
           "probe": fsum["probe"], "coverage_vs_plan": fsum["coverage_vs_plan"], "pool": fsum["pool"],
           "pool_evaluation": fsum["pool_evaluation"], "pbp_linked_player_matches": fsum["pbp_linked_player_matches"],
           "constants": json.loads(pd.read_csv(C.OUT / "stage4_constants.csv").query("surface == 'all'")
                                   .to_json(orient="records")),
           "event_country": json.loads((C.OUT / "stage4_event_country_summary.json").read_text(encoding="utf-8")),
           "comparisons": {"rows": {t: int((rank["tour"] == t).sum()) for t in C.TOURS},
                                                   "scores": int(sum(len(r["scores"]) for r in results)),
                                                   "constant_rows": int(rank["constant"].sum())},
           "seconds": round(time.time() - T0, 1)}
    RESULTS_JSON.write_text(json.dumps(res, default=float), encoding="utf-8")
    log(f"wrote {RESULTS_JSON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
