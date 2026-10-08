"""Shared definitions for the study "a logistic meta-model over a market-free TabPFN and the closing price"
(src/eda/meta_stack/).

The owner's request of 6 Oct 2026. The current best model, the local TabPFN-3.5 (non-thinking) in expanding windows,
takes the closing line as one of its 54 inputs, and one calibration slope per tour, refitted each season on all earlier
out-of-sample seasons from 2019, is applied to its log-odds (docs/studies/surface_ios/README.md, "Added after the
study"). The idea to test: keep the closing line out of the model, and combine (1) the model without the closing line,
(2) the closing line and (3) the difference between the two in a logistic meta-model. How much data goes to the model
and how much to the meta-learner is to be decided with mathematical justification. Then compare with the current best.

Forecasts (every one symmetrised over the two orientations; a model's forecast is the mean of four seeds):
    base     the current best's TabPFN: 54 inputs, the closing odds' log-odds first (the surface-IOS arm "base")
    noodds   the same TabPFN, the same 53 other inputs, no odds column (the surface-IOS arm "base_noodds")
Both: the open TabPFN-3.5 checkpoint (tabpfn-v3.5-20260909) on this machine's GPU, 8 estimators, softmax temperature
0.9, seeds 0-3, trained on every main-tour match with closing odds from 2013 up to a season, the matches of later
seasons queried. 2019-2026 come from the surface-IOS study's fits (read only, fingerprints checked); this study adds the
seasons 2014-2018 and the hold-out design's fits (run_local.py).

Every number in the write-up is read from data/studies/meta_stack/ (written by this study's scripts).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "meta_stack"
DOCS = ROOT / "docs" / "studies" / "meta_stack"
LOCAL = OUT / "local"                                   # this study's local fits (run_local.py)
SIOS = ROOT / "data" / "studies" / "surface_ios"        # the current best's fits and frames (read only)
SIOS_ARM = {"base": "base", "noodds": "base_noodds"}    # this study's name -> the surface-IOS arm
ARM_FRAMES = {a: SIOS / "arms" / f"{s}.parquet" for a, s in SIOS_ARM.items()}

TOURS = ("atp", "wta")
SEEDS = (0, 1, 2, 3)
FIRST_TRAIN = 2013                  # every window trains from 2013 (the surface-IOS design)
PRE = (2014, 2015, 2016, 2017, 2018)                    # out-of-sample seasons this study adds (the men's 2018: no odds)
VAL = (2019, 2020, 2021)            # the design is chosen here, before any 2022-2026 stack is scored
TEST = (2022, 2023, 2024, 2025, 2026)
CURRENT_BEST_FROM = 2019            # the current best's slope: all out-of-sample seasons from 2019 to the season before
EPS = 1e-9

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def zlogit(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))
