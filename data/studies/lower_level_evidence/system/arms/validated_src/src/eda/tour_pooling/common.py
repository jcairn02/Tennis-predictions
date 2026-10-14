"""Shared definitions of the tour-pooling study (docs/studies/tour_pooling/design.md).

The owner's questions (9 Oct 2026). The current best model trains one TabPFN on both tours. Would one model per tour do
better, season by season from 2022? Is there a men/women input, and does it help? Can a tour's model lean on its own
matches and borrow the other tour's only where they help?

Everything starts from the current instance, read only: data/studies/current_best_model/pinnacle_first_2026-10-09/
(its frame, its 58 inputs and, as the base, its fits). The arms change only the training rows, the query rows and,
for two arms, the inputs:

    arm        models          training rows for season Y (all from 2013 .. Y - 1)          inputs
    split      one per tour    its own tour's matches                                       58 (tour is constant)
    notour     both tours      every match                                                  57: tour dropped
    borrow25   one per tour    its own tour's + a random 25% of the other tour's            58
    borrow50   one per tour    its own tour's + a random 50% of the other tour's            58
    borrowsim  one per tour    its own tour's + 50% of the other tour's in expectation,     58
                               drawn with P(keep) rising with how much a match looks like
                               the own tour's (sim_inclusion)
    aligned    both tours      every match                                                  58; the 39 box-score
                                                                                            statistics divided by their
                                                                                            own tour's SD (align)
    sizectl    one per tour    a random draw from both tours' matches, as many as its own   58
                               tour's (the size control: split's size, pooled's mix)
    pooled     both tours      every match: the current instance's job, rebuilt by this     58
                               runner (a reproduction check; 2022, seed 0)

A per-tour model predicts season Y's matches of its tour; a both-tour model predicts every season-Y match. Draws are
new per season and seed, and reproducible: default_rng([DRAW_SEED, Y, seed, ARM_CODE[arm], TOUR_CODE[tour]]). The
borrowing draws are coupled (amended before borrow25's and borrowsim's fits, red team S2): borrow25's rows are a random
half of borrow50's, and borrowsim keeps an other-tour row when u < pi, with u uniform below 0.5 on borrow50's rows and
above it elsewhere. So the dose is nested, and borrowsim differs from borrow50 only where pi differs from 0.5.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.model_rebuild import fits as MF  # noqa: E402  (paths(): the serve-speed harness pointed at a built frame)
from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "pinnacle_first_2026-10-09"
OUT = ROOT / "data" / "studies" / "tour_pooling"
FITS = OUT / "fits"
# The similarity cache, third version (see sim_features): borrow_sim/ (all inputs; degenerate) and
# borrow_sim_situation/ (the layoff days' precision artifact) are the superseded versions, kept as the record.
SIM = OUT / "borrow_sim_v3"
SIM_VERSION = 3
P = MF.paths(INSTANCE)

TRAIN_FROM = SC.TRAIN_FROM                  # 2013
SEASONS = tuple(range(2019, 2027))          # 2019-2021 feed the walk-forward calibration only
SEEDS = (0, 1, 2, 3)                        # the comparison's seeds (current_best_model/compare.py)
TOURS = ("atp", "wta")
SEALED_FROM = pd.Timestamp("2026-07-29")    # the proposed sealed holdout: no training row, no result read
DRAW_SEED = 20261009
ARMS = {"split": "per_tour", "notour": "both", "borrow25": "per_tour", "borrow50": "per_tour",
        "borrowsim": "per_tour", "aligned": "both", "sizectl": "per_tour", "pooled": "both"}
ARM_CODE = {"split": 1, "notour": 2, "borrow25": 3, "borrow50": 4, "borrowsim": 5, "aligned": 6, "sizectl": 7,
            "pooled": 8}
TOUR_CODE = {"both": 0, "atp": 1, "wta": 2}
BORROW_SHARE = {"borrow25": 0.25, "borrow50": 0.50, "borrowsim": 0.50}
# The box-score statistics whose units differ by tour (an ace-rate gap is worth more where aces are rarer). Ratings,
# the price, age, workload, the surface-season pairs and the context keep their common scales.
ALIGN_PREFIXES = ("form_", "formdef_", "iosO_", "iosD_", "prod_")
ALIGN_EXTRA = ("adjperf_tpw_2w", "ios_points_short")

log, write_json, read_json, sha256_file = SC.log, SC.write_json, SC.read_json, SC.sha256_file


# ------------------------------------------------------------------------------------------------
# Inputs and the frame

def base_inputs() -> list[str]:
    return SA.arm_inputs("model", P)


def inputs(arm: str) -> list[str]:
    cols = base_inputs()
    return [c for c in cols if c != "tour"] if arm == "notour" else cols


def model_tours(arm: str) -> tuple[str, ...]:
    return TOURS if ARMS[arm] == "per_tour" else ("both",)


def aligned_inputs() -> list[str]:
    return [c for c in base_inputs() if c.startswith(ALIGN_PREFIXES) or c in ALIGN_EXTRA]


def load_frame(labels: bool = False) -> pd.DataFrame:
    """The instance's frame in its stored order (labels only when asked: the fit runner's training labels)."""
    f = SA.load_frame([], P, labels=labels)
    return f.reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# Training and query rows

def pool_mask(frame: pd.DataFrame, season: int) -> np.ndarray:
    s = frame["season"].to_numpy()
    return (s >= TRAIN_FROM) & (s <= season - 1)


def rng(arm: str, tour: str, season: int, seed: int) -> np.random.Generator:
    return np.random.default_rng([DRAW_SEED, season, seed, ARM_CODE[arm], TOUR_CODE[tour]])


def train_mask(frame: pd.DataFrame, arm: str, tour: str, season: int, seed: int) -> np.ndarray:
    """Which rows (frame order) train the arm's model of `tour` ("both" for a both-tour model) for season Y."""
    pool = pool_mask(frame, season)
    if tour == "both":
        if ARMS[arm] != "both":
            raise ValueError(f"{arm} has one model per tour")
        return pool
    if ARMS[arm] != "per_tour":
        raise ValueError(f"{arm} has one model for both tours")
    t = frame["tour"].to_numpy()
    own, other = pool & (t == tour), pool & (t != tour)
    if arm == "split":
        return own
    keep = np.zeros(len(frame), bool)
    if arm == "sizectl":
        keep[rng(arm, tour, season, seed).choice(np.flatnonzero(pool), size=int(own.sum()), replace=False)] = True
        return keep
    idx = np.flatnonzero(other)
    half = rng("borrow50", tour, season, seed).choice(idx, size=int(round(0.5 * len(idx))), replace=False)
    if arm == "borrow50":
        keep[half] = True
    elif arm == "borrow25":
        keep[rng(arm, tour, season, seed).choice(half, size=int(round(0.25 * len(idx))), replace=False)] = True
    elif arm == "borrowsim":
        pi = sim_inclusion(frame, tour, season)
        ids = frame["match_id"].astype(str).to_numpy()
        p = pd.Series(pi["pi"].to_numpy(), index=pi["match_id"].astype(str)).reindex(ids[idx]).to_numpy()
        if not np.isfinite(p).all():
            raise RuntimeError(f"borrowsim {tour} {season}: the inclusion cache lacks other-tour training rows")
        v = rng(arm, tour, season, seed).random(len(idx))
        u = np.where(np.isin(idx, half), 0.5 * v, 0.5 + 0.5 * v)       # uniform; below 0.5 exactly on borrow50's rows
        keep[idx[u < p]] = True
    else:
        raise ValueError(arm)
    return own | keep


def query_mask(frame: pd.DataFrame, tour: str, season: int) -> np.ndarray:
    m = (frame["season"] == season).to_numpy()
    return m if tour == "both" else m & (frame["tour"].to_numpy() == tour)


# ------------------------------------------------------------------------------------------------
# The aligned arm: each tour's box-score statistics in units of that tour's own spread

def align_scales(frame: pd.DataFrame, season: int) -> dict[tuple[str, str], float]:
    """{(tour, input): SD of the input over that tour's training rows of season Y (2013 .. Y - 1)}."""
    pool, t = pool_mask(frame, season), frame["tour"].to_numpy()
    out = {}
    for tour in TOURS:
        m = pool & (t == tour)
        for c in aligned_inputs():
            sd = float(np.nanstd(frame.loc[m, f"in_{c}"].to_numpy(float)))
            out[(tour, c)] = sd if np.isfinite(sd) and sd > 0 else 1.0
    return out


def align(X: pd.DataFrame, frame: pd.DataFrame, season: int) -> pd.DataFrame:
    """X (frame order) with each aligned input divided by its own tour's training SD. Diffs only, so the swap commutes."""
    sc = align_scales(frame, season)
    t = frame["tour"].to_numpy()
    out = X.copy()
    for c in aligned_inputs():
        v = out[c].to_numpy(float).copy()
        for tour in TOURS:
            m = t == tour
            v[m] = v[m] / sc[(tour, c)]
        out[c] = v
    return out


# ------------------------------------------------------------------------------------------------
# The borrowsim arm: borrow the other tour's matches that look like the own tour's

# The match's situation in units both tours share: the market's view (the favourite's strength), the rating gaps, the
# age and workload gaps, the surface-season pairs and the context. Left out: the 39 box-score statistics and the
# 52-week ranking points, whose units differ by tour; the missing-input pattern (a coverage artifact); `indoor`, which
# the frame records for men only (missing for every women's match, so it names the tour); tour itself.
# Amended 9 Oct 2026 before any fit or score of the arm, twice:
#   v1 (borrow_sim/) used every input; the tours separated perfectly (out-of-fold AUC 1.000 for 2019), so every
#      other-tour match got the same inclusion weight, i.e. a plain random half. `indoor` alone separates them;
#   v2 (borrow_sim_situation/) read the surface layoff's days as stored: fractional on a quarter of women's 2013-18
#      matches (the match clock's estimated days for undated matches), so it selected on dating precision (analyst);
#   v3 (borrow_sim_v3/) rounds those days to whole days.
# What the draw then borrows (declared before its fits, red team S1 and analyst): no other-tour Grand Slam match
# (best of five is men-only, and best of three at a Slam women-only), and a tilt toward closer prices.
SIM_DIFFS = ("odds_logit", "elo_games", "elo_overall", "ratings_iid", "elo_surf_offset", "age", "sets_14d")
SIM_PAIRS = ("surf_season", "surf_layoff")
SIM_CONTEXT = ("surface", "level", "best_of", "round")


def sim_features(frame: pd.DataFrame) -> pd.DataFrame:
    """What a match's situation looks like, unchanged when A and B swap: |A - B| of SIM_DIFFS, each SIM_PAIRS pair as
    (min, max), and SIM_CONTEXT. The layoff (log of 1 + days) is taken at whole days. No result."""
    cols = {f"abs_{c}": np.abs(frame[f"in_{c}"].to_numpy(float)) for c in SIM_DIFFS}
    for c in SIM_PAIRS:
        a, b = frame[f"in_{c}_a"].to_numpy(float), frame[f"in_{c}_b"].to_numpy(float)
        if c == "surf_layoff":
            a, b = np.log1p(np.round(np.expm1(a))), np.log1p(np.round(np.expm1(b)))
        cols[f"min_{c}"], cols[f"max_{c}"] = np.fmin(a, b), np.fmax(a, b)
    cols.update({c: frame[f"in_{c}"].to_numpy(float) for c in SIM_CONTEXT})
    return pd.DataFrame(cols, index=frame.index)


def sim_path(tour: str, season: int) -> Path:
    return SIM / f"{tour}__{season}.parquet"


def sim_inclusion(frame: pd.DataFrame, tour: str, season: int) -> pd.DataFrame:
    """For the other tour's training rows of `tour`'s season-Y model: P(own tour | x) out of fold, the density ratio
    r = p / (1 - p) * n_other / n_own, and the inclusion probability pi = min(1, kappa r), kappa set so that the
    expected draw is BORROW_SHARE["borrowsim"] of those rows. Fitted on the training pool (2013 .. Y - 1) only, inputs
    only; cached in SIM (deterministic: fixed folds and booster seed). A cached file is used only if its record (written
    first) names this version, today's features and the instance's frame."""
    path, rec = sim_path(tour, season), sim_path(tour, season).with_suffix(".json")
    if path.exists():
        if not rec.exists():
            raise RuntimeError(f"{path}: no record beside the cache (an interrupted build?)")
        meta = read_json(rec)
        if (meta.get("version") != SIM_VERSION or meta.get("features") != list(sim_features(frame.head(2)).columns)
                or meta.get("model_frame_sha256") != frame_sha()):
            raise RuntimeError(f"{path}: a stale cache (other version, features or frame)")
        return pd.read_parquet(path)
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    pool = pool_mask(frame, season)
    sub = frame.loc[pool]
    Xf = sim_features(sub)
    is_own = (sub["tour"].to_numpy() == tour).astype(int)
    oof = np.full(len(sub), np.nan)
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(Xf, is_own):
        clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, max_leaf_nodes=31,
                                             l2_regularization=1.0, random_state=0)
        clf.fit(Xf.iloc[tr], is_own[tr])
        oof[te] = clf.predict_proba(Xf.iloc[te])[:, 1]
    other = is_own == 0
    n_own, n_other = int(is_own.sum()), int(other.sum())
    p = np.clip(oof[other], 1e-6, 1 - 1e-6)
    r = p / (1 - p) * n_other / n_own
    target = BORROW_SHARE["borrowsim"] * n_other
    lo, hi = 0.0, 1.0
    while np.minimum(1.0, hi * r).sum() < target:
        hi *= 2
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if np.minimum(1.0, mid * r).sum() < target else (lo, mid)
    pi = np.minimum(1.0, hi * r)
    out = pd.DataFrame({"match_id": sub["match_id"].astype(str).to_numpy()[other], "season": sub["season"].to_numpy()[other],
                        "p_own": p, "ratio": r, "pi": pi})
    SIM.mkdir(parents=True, exist_ok=True)
    meta = {"version": SIM_VERSION, "tour": tour, "season": season, "train_seasons": [TRAIN_FROM, season - 1],
            "n_own": n_own, "n_other": n_other, "auc_out_of_fold": float(roc_auc_score(is_own, oof)),
            "kappa": float(hi), "expected_borrowed": float(pi.sum()), "share_pi_one": float((pi >= 1).mean()),
            "share_at_floor": float((oof[other] <= 1e-6).mean()),
            "effective_n": float(pi.sum() ** 2 / (pi ** 2).sum()), "features": list(Xf.columns),
            "model_frame_sha256": frame_sha(),
            "classifier": "HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, max_leaf_nodes=31, "
                          "l2_regularization=1.0, random_state=0), 5-fold StratifiedKFold(shuffle, random_state=0)"}
    tag = f".{os.getpid()}.tmp"                  # two builders never share a temporary file (red team N11)
    tmp_rec, tmp = rec.with_name(rec.name + tag), path.with_name(path.name + tag)
    tmp_rec.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    tmp_rec.replace(rec)                         # the record first: a cache without one is refused
    out.to_parquet(tmp, index=False)
    tmp.replace(path)
    return out


_FRAME_SHA: dict = {}


def frame_sha() -> str:
    """SHA-256 of the instance's frame (cached per process)."""
    if "sha" not in _FRAME_SHA:
        _FRAME_SHA["sha"] = sha256_file(P.model_frame)
    return _FRAME_SHA["sha"]


# ------------------------------------------------------------------------------------------------
# Jobs and their files

def job_data(frame: pd.DataFrame, arm: str, tour: str, season: int, seed: int):
    """(X_train, y_train, X_query, query match ids, training mask): the query is season Y's matches of the model's
    tour(s) as stored, then the same matches with A and B swapped (the td block every local fit writes)."""
    if "a_won" not in frame.columns:
        raise RuntimeError("job_data needs the training labels: load_frame(labels=True)")
    cols = inputs(arm)
    X = SA.matrix(frame, cols)
    if arm == "aligned":
        X = align(X, frame, season)
    tr = train_mask(frame, arm, tour, season, seed)
    te = query_mask(frame, tour, season)
    if (frame.loc[tr, "season"] >= season).any():
        raise RuntimeError("a training row is from the predicted season or later")
    if (pd.to_datetime(frame.loc[tr, "tournament_date"]) >= SEALED_FROM).any():
        raise RuntimeError("a training row is from the sealed holdout")
    X_test = X[te].reset_index(drop=True)
    X_query = pd.concat([X_test, SA.flip(X_test, P)], ignore_index=True)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(), X_query,
            frame.loc[te, "match_id"].astype(str).to_numpy(), tr)


def fit_path(arm: str, tour: str, season: int, seed: int) -> Path:
    return FITS / f"{arm}__{tour}__{season}__seed{seed}.npz"
