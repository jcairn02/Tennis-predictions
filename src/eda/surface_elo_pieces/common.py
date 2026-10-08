"""Shared definitions for the study "Elo by surface: give the model the pieces" (src/eda/surface_elo_pieces/).

The owner's request of 6 Oct 2026: audit two suggestions for the best 2026 model (the closing odds plus 53 pre-match
inputs of src/eda/tabpfn_leakproof/), build a representation from evidence, have it reviewed, and test it with the
non-thinking TabPFN-3.5 ("3.5-Plus", the API's plain v3.5) in a walk-forward over 2022-2026, one season per sample.

    5. Give the model the pieces of surface Elo (overall rating, surface-only rating, each player's surface match
       count) instead of the fixed 70/30 blend (75/25 for the women).
    6. Represent surface switches better than "first matches on this surface this season" as A minus B: both players'
       counts, days since each last played on the surface, and last season's form on it.

Design discipline. Every choice of representation is made on seasons 2010-2021 only (tuning 2013-2018, checking
2019-2021), so that the 2022-2026 test seasons stay unseen for the new inputs. The inherited 53 inputs were chosen by
earlier studies after their 2022-2026 results were seen; that caveat is the baseline's, unchanged here.

Every number in the write-up is read from data/studies/surface_elo_pieces/ (written by this study's scripts).
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

from src.eda.tabpfn_thinking import common as T  # noqa: E402  (scoring, intervals, symmetry, fingerprint)

OUT = ROOT / "data" / "studies" / "surface_elo_pieces"
DOCS = ROOT / "docs" / "studies" / "surface_elo_pieces"
PD_OUT = ROOT / "data" / "studies" / "predictability_diagnostic"
STAGE0 = PD_OUT / "stage0_matches.parquet"
STAGE1 = PD_OUT / "stage1_baselines.parquet"
STAGE1_SUMMARY = PD_OUT / "stage1_baselines_summary.json"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
LEAKPROOF = ROOT / "data" / "studies" / "match_timing" / "leakproof_features.parquet"
FRAME = ROOT / "data" / "studies" / "tabpfn_thinking" / "frame.parquet"     # the best model's 32 unchanged inputs
PIECES = OUT / "pieces.parquet"                                             # one row per match (all 872,704)

TOURS = ("atp", "wta")
SURFACES = ("Hard", "Clay", "Grass", "Carpet")          # Stage 1's codes 0-3
TUNE_YEARS = (2013, 2018)                               # tuning of any new constant (Stage 1's tuning years)
CHECK_YEARS = (2019, 2021)                              # out-of-sample check inside the design years
DESIGN_YEARS = (2013, 2021)
TEST_YEARS = tuple(range(2022, 2027))                   # the walk-forward folds: one season each
TRAIN_FROM = 2013                                       # every fold trains on 2013 .. season - 1 (the best model's start)
L10 = float(np.log(10) / 400.0)                         # Elo points -> log-odds

T0 = time.time()
ll, compare, paired_interval, blocks = T.ll, T.compare, T.paired_interval, T.blocks
write_json, sha256_file = T.write_json, T.sha256_file


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def mean_ll(p, y) -> float:
    return float(np.mean(ll(p, y)))
