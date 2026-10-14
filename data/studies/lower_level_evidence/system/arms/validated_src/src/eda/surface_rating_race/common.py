"""Shared definitions for the study "the surface-offset rating race" (src/eda/surface_rating_race/).

The owner's request of 6 Oct 2026, after the surface-Elo-pieces study (docs/studies/surface_elo_pieces/README.md):
give TrueSkill Through Time (TTT; the leading base-rating candidate, docs/decisions/2026-10-03-leading-rating-candidate.md)
the same surface-offset structure that made the offset Elo better than the 30% blend, and race the two head to head
with the local, non-thinking TabPFN-3.5, calibrated. The owner's note: bets are placed before the close, so information
that the market has not priced at the time of the bet but has by the close is useful; the race is read at the price
24 hours before the start as well as at the close.

Design discipline (as the Elo-pieces study): the new rating's constants are tuned on 2013-2018 only, the calibration
slopes come from 2019-2021, and the test is 2022-2026, one season per sample. The base model's inherited inputs were
chosen by earlier studies after their 2022-2026 results were seen; that caveat is the baseline's, unchanged here.

Every number in the write-up is read from data/studies/surface_rating_race/ (written by this study's scripts).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402  (scoring, intervals, symmetry, fingerprint)

OUT = ROOT / "data" / "studies" / "surface_rating_race"
DOCS = ROOT / "docs" / "studies" / "surface_rating_race"
PIECES_OUT = ROOT / "data" / "studies" / "surface_elo_pieces"
PIECES_FRAME = PIECES_OUT / "frame.parquet"            # the Elo-pieces study's frame: base 54 inputs + the Elo pieces
EARLY = PIECES_OUT / "early_price_frame.parquet"       # Polymarket prices 24 h and 30 min before the listed start
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
TTT_TIMED = ROOT / "data" / "studies" / "match_timing" / "ttt_timed.parquet"   # TTT as decided, leak-proof
TTT_OFFSET = OUT / "ttt_offset.parquet"                # this study's surface-offset TTT, one row per Stage 0 match

TOURS = ("atp", "wta")
TUNE_YEARS = (2013, 2018)
CALIB_YEARS = (2019, 2021)
TEST_YEARS = tuple(range(2022, 2027))
SEASONS = tuple(range(2019, 2027))                     # walk-forward folds: calibration 2019-2021, test 2022-2026
TRAIN_FROM = 2013
SEEDS = (0, 1, 2)

T0 = time.time()
ll, compare, blocks = T.ll, T.compare, T.blocks
write_json, sha256_file = T.write_json, T.sha256_file


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def mean_ll(p, y) -> float:
    return float(np.mean(ll(p, y)))
