"""Shared definitions of the study "train the current best model on recent seasons only?" (training_window).

The owner's question (8 Oct 2026): the current best model trains season Y on every season of 2013 .. Y - 1. Because the
close is an input, the model learns from those seasons how far to move away from it. If the value of moving away
changes over time, the learned amount goes stale: trained on softer-close years it would move too far once the close
sharpens; trained the other way round it would move too little. Should it use only more recent seasons?

The arms. Every arm is the model's 58 inputs with the decided settings (8 estimators, softmax temperature 0.9,
pretraining limits ignored), seeds 0-3, and season Y in 2019-2024 fitted on matches of seasons before Y only. Only the
training rows differ:

    exp       the current model: every season 2013 .. Y - 1. Its stored fits are reused read-only (the rating race's
              seeds 0-2, feature interactions' seed 3). last7's and rand7's fits of 2019-2020 have exactly its rows and
              must reproduce them
    lastN     the last N seasons, max(2013, Y - N) .. Y - 1, for N = 7, 5, 3
    randN     size controls: a random subsample of 2013 .. Y - 1 with as many matches as lastN has that season, drawn
              anew for each seed. lastN against randN is recency at a fixed size; randN against exp is size alone
    decay4    recency-weighted (TabPFN takes no sample weights): each match of 2013 .. Y - 1 kept with probability
              0.5 ** (age / 4), age = Y - 1 - its season, drawn anew for each seed

Each arm becomes its own two-stage forecast (the decided rule, src/eda/serve_speed_tabpfn/adaptive/adjust.py, mode L,
weekly feed): logit q = s_tour,Y eta + b_Y spd_L, (s_atp, s_wta, b) fitted on the arm's own out-of-sample forecasts of
2019 .. Y - 1 (seeds 0-3 mean, debut seasons out), b shrunk with tau = 0.05. Seasons 2020-2024 are scored.

Seasons <= 2024 only: 2025-2026 is the proposed clean holdout (docs/studies/clean_holdout_rebuild/). The frame is read
with a season filter and asserted, and no forecast of 2025 or 2026 is opened.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402  (the model frame's inputs, kinds and flip)
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402  (paths, settings, logistic, log loss)

OUT = ROOT / "data" / "studies" / "training_window"
LOCAL = OUT / "local"
P = SC.DEFAULT                          # the serve-speed harness's paths: the model frame, its inputs, the base fits
SPEED = SC.OUT / "latency" / "variants.parquet"          # spd_B_M1 = spd_L_B: the weekly feed's 28-day column
STAGE2_PUBLISHED = SC.OUT / "adaptive" / "coefficients.json"
LAST_SEASON = 2024
SEASONS = tuple(range(2019, 2025))      # fitted; 2019 only calibrates
TEST = tuple(range(2020, 2025))         # scored
ERAS = {"2020-2021": (2020, 2021), "2022-2023": (2022, 2023), "2024": (2024,), "2020-2024": TEST}
TRAIN_FROM = SC.TRAIN_FROM              # 2013
CALIB_FROM = SC.CALIB_FROM              # 2019
SEEDS = (0, 1, 2, 3)
CONFIG = dict(SC.CONFIG)
TAU = SC.TAU_NUDGE
ARMS = ("exp", "last7", "last5", "last3", "rand7", "rand5", "rand3", "decay4")
NEW_ARMS = ARMS[1:]
DRAW_SEED = 20261008                    # the subsample draws: default_rng([DRAW_SEED, season, seed, N, kind])
KIND_CODE = {"rand": 1, "decay": 2}
REPRO_TOL = SC.REPRO_TOL                # 1e-6
lg, ll, fit_logistic, symmetrize = SC.lg, SC.ll, SC.fit_logistic, SC.symmetrize
log, write_json, read_json, sha256_file = SC.log, SC.write_json, SC.read_json, SC.sha256_file


def inputs() -> list[str]:
    return SA.arm_inputs("model", P)


def load_frame(labels: bool = True) -> pd.DataFrame:
    """The model frame's seasons <= 2024 in stored order, with the serve-speed harness's columns (labels only if
    asked). Asserted: no season after 2024 and no match after 2024 is read."""
    t = pq.read_table(P.model_frame, columns=SA.frame_columns(P, labels), filters=[("season", "<=", LAST_SEASON)])
    f = t.to_pandas()
    if f["season"].max() > LAST_SEASON or f["tournament_date"].max() > pd.Timestamp(f"{LAST_SEASON}-12-31"):
        raise RuntimeError("a season or a match after 2024 was read")
    f["match_id"] = f["match_id"].astype(str)
    if f["match_id"].duplicated().any():
        raise RuntimeError("model frame match ids are not unique")
    f["debut"] = f["debut_season"].astype(bool)
    return f.reset_index(drop=True)


def parse(arm: str) -> tuple[str, int | None]:
    if arm == "exp":
        return "exp", None
    for kind in ("last", "rand", "decay"):
        if arm.startswith(kind) and arm[len(kind):].isdigit():
            return kind, int(arm[len(kind):])
    raise KeyError(f"unknown arm {arm}")


def train_mask(seasons, arm: str, season: int, seed: int) -> np.ndarray:
    """Which rows (in frame order) train arm's fit of `season` with `seed`; seasons is the frame's season column."""
    seasons = np.asarray(seasons)
    pool = (seasons >= TRAIN_FROM) & (seasons <= season - 1)
    kind, n = parse(arm)
    if kind == "exp":
        return pool
    if kind == "last":
        return pool & (seasons >= season - n)
    rng = np.random.default_rng([DRAW_SEED, season, seed, n, KIND_CODE[kind]])
    if kind == "rand":
        k = int(train_mask(seasons, f"last{n}", season, seed).sum())
        keep = np.zeros(len(seasons), bool)
        keep[rng.choice(np.flatnonzero(pool), size=k, replace=False)] = True
        return keep
    age = (season - 1) - seasons
    return pool & (rng.random(len(seasons)) < 0.5 ** (age / n))


def job_data(frame: pd.DataFrame, arm: str, season: int, seed: int):
    """(X_train, y_train, X_query, season-Y match ids): the arm's training rows, and the season's matches as stored
    followed by the same matches with A and B swapped (the td block, as every local fit queries it)."""
    cols = inputs()
    tr = train_mask(frame["season"].to_numpy(), arm, season, seed)
    te = (frame["season"] == season).to_numpy()
    X = SA.matrix(frame, cols)
    X_test = X[te].reset_index(drop=True)
    X_query = pd.concat([X_test, SA.flip(X_test, P)], ignore_index=True)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(), X_query,
            frame.loc[te, "match_id"].to_numpy())


def stored_path(season: int, seed: int) -> Path:
    """The current model's stored fit: the rating race's seeds 0-2, feature interactions' seed 3."""
    return (P.race_local if seed <= 2 else P.fi_local) / f"model__{season}__seed{seed}.npz"


def fit_path(arm: str, season: int, seed: int) -> Path:
    return stored_path(season, seed) if arm == "exp" else LOCAL / f"{arm}__{season}__seed{seed}.npz"


def read_fit(path: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """(stored td probabilities [as stored then swapped], their match ids, meta)."""
    if not path.exists():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as z:
        meta = json.loads(str(z["meta"]))
        return z["p_td"].astype(float), z["ids_td"].astype(str), meta


def symmetrised(path: Path, ids_expected: np.ndarray) -> tuple[np.ndarray, dict]:
    p, ids, meta = read_fit(path)
    k = len(ids)
    if len(p) != 2 * k or not np.array_equal(ids, np.asarray(ids_expected, str)):
        raise RuntimeError(f"{path.name}: td block is not the season's frame matches, stored then swapped")
    return symmetrize(p[:k], p[k:]), meta


def speed_column(ids) -> np.ndarray:
    """spd_L as the weekly feed has it (spd_B_M1), 0 for every woman; never missing for a 2019-2024 frame match."""
    v = pd.read_parquet(SPEED, columns=["match_id", "spd_B_M1"])
    v["match_id"] = v["match_id"].astype(str)
    if v["match_id"].duplicated().any():
        raise RuntimeError("variants.parquet: duplicate match ids")
    z = v.set_index("match_id")["spd_B_M1"].reindex(pd.Index(ids, dtype=str)).to_numpy(float)
    if not np.isfinite(z).all():
        raise RuntimeError("spd_B_M1 missing for some frame matches")
    return z


def stage2_fit(eta: np.ndarray, atp: np.ndarray, z: np.ndarray, y: np.ndarray) -> dict:
    """score.nudge_parameters' fit: logit q = s_atp eta [men] + s_wta eta [women] + b z, maximum likelihood without an
    intercept, then b shrunk with a N(0, tau^2) prior; the slopes are not refitted."""
    beta, se = fit_logistic(np.column_stack([np.where(atp, eta, 0.0), np.where(~atp, eta, 0.0), z]), y)
    b, s = float(beta[2]), float(se[2])
    return {"s_atp": float(beta[0]), "s_wta": float(beta[1]), "b_mle": b, "se_b": s,
            "b_shrunk": b * TAU ** 2 / (TAU ** 2 + s ** 2), "rows": int(len(y))}


def stage2_apply(eta, atp, z, par: dict) -> np.ndarray:
    from scipy.special import expit
    eta = np.asarray(eta, float)
    s = np.where(atp, par["s_atp"], par["s_wta"])
    if eta.ndim == 2:
        s, zz = s[:, None], np.where(atp, z, 0.0)[:, None]
    else:
        zz = np.where(atp, z, 0.0)
    return expit(s * eta + par["b_shrunk"] * zz)
