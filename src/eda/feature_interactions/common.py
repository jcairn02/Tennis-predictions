"""Shared definitions for the study "feature interactions" (src/eda/feature_interactions/).

The owner's request of 6 Oct 2026: find interactions between features of the best local, non-thinking TabPFN-3.5
model's feature universe (including features it does not use yet), narrow them like a cone with a team of Opus agents
(docs/studies/feature_interactions/team.md), explore them with EDA and test the best in the model. The brief every
agent reads: docs/studies/feature_interactions/brief.md.

Windows (fixed before any outcome was computed):

    DISCOVERY     2014-2021  EDA screens, cross-fitted by season (the current best model's out-of-sample forecasts
                             exist from 2014: walk-forward fits trained on 2013 to the season before)
    REPLICATION   2022-2024  coefficients frozen on discovery, applied forward
    TEST          2025-2026  closed: no EDA, tuning or choice reads it; opened once for the pre-registered test

The model is the 58-input model after the owner's two decisions of 6 Oct 2026
(data/studies/surface_rating_race/model/model_frame.parquet, built by src/eda/surface_rating_race/model_frame.py).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402  (log loss, block intervals, symmetry, fingerprint)

OUT = ROOT / "data" / "studies" / "feature_interactions"
DOCS = ROOT / "docs" / "studies" / "feature_interactions"
LOCAL = OUT / "local"                       # this study's local TabPFN fits
FEATURES = OUT / "features"                 # new inputs: <family>.parquet (match_id + columns) and registry.json

MODEL_DIR = ROOT / "data" / "studies" / "surface_rating_race" / "model"
MODEL_FRAME = MODEL_DIR / "model_frame.parquet"
MODEL_INPUTS = MODEL_DIR / "model_inputs.json"
RACE_LOCAL = ROOT / "data" / "studies" / "surface_rating_race" / "local"   # the race's fits of arm "model" (read only)
EARLY = ROOT / "data" / "studies" / "surface_elo_pieces" / "early_price_frame.parquet"

TOURS = ("atp", "wta")
TRAIN_FROM = 2013
DISCOVERY = tuple(range(2014, 2022))
REPLICATION = tuple(range(2022, 2025))
TEST = (2025, 2026)
CALIB_FROM = 2019                           # walk-forward calibration slopes use out-of-sample seasons from 2019
SEEDS = (0, 1, 2)
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}
EPS = 1e-6

T0 = time.time()
ll, compare, blocks, write_json, sha256_file = T.ll, T.compare, T.blocks, T.write_json, T.sha256_file


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def lg(p) -> np.ndarray:
    from scipy.special import logit
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))
