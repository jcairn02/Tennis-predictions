"""Shared definitions of the study "betting before the close, with the price of the moment as the model's odds input"
(src/eda/bet_timing/).

The owner's question of 8 Oct 2026. The current best model (docs/decisions/2026-10-07-speed-nudge.md) takes the closing
line as an input. Betting earlier should pay better because the line is softer, but the model's best input is then less
accurate, and no early prices exist for most of the seasons the model trains on (2013 onward). How big a deal is it to
bet before the close while feeding the model the price of the moment in place of the close?

The identity the study measures. For a bet time t and the close c, on the same matches, with L the mean log loss:

    E(t) = L(price_t) - L(q_t)       the model's edge over the price it bets into (q_t: the model fed price_t)
    S(t) = L(price_t) - L(price_c)   how much softer the line at t is than the close
    A(t) = L(q_t) - L(q_c)           how much accuracy the model loses by being fed price_t instead of the close
    E(t) = E(c) + S(t) - A(t)

Betting at t instead of the close changes the edge by S(t) - A(t): what the line gives away minus what the model
inherits. A(t) / S(t) is the share of the early line's error the model inherits: 1 means the model only copies the
price (nothing gained by betting early), 0 that it already knew everything the market learned by the close.

    frame.py   the sample: model-frame matches 2020-2026 with BetOnline's opening and last line (OddsTrader) and
               Polymarket's price at fixed horizons before the listed start (2025-2026), the moment each price was
               available, and whether every model input existed by then. Reads no result except A's orientation
    fits.py    the 58-input local TabPFN-3.5, season Y trained on 2013 .. Y - 1, queried with its odds input replaced
               by each price (GPU, waits until no other local TabPFN process runs)
    score.py   the decomposition, the market's move toward the model, the plug-in's sizing, and the money
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "bet_timing"
DOCS = ROOT / "docs" / "studies" / "bet_timing"
LOCAL = OUT / "local"
FRAME = OUT / "frame.parquet"                 # prices stay in gitignored parquet (OddsTrader's lines are not republished)
CONSENSUS_FRAME = OUT / "consensus_frame.parquet"     # consensus.py: the sharp-consensus prices (gitignored)
LOCAL_CONSENSUS = OUT / "local_consensus"             # fits.py --set consensus
CONSENSUS_BLOCKS = ("ps_close", "cons_close", "cons_h24", "bfe_close", "cons_late")

# The snapshot the model frame was built on (the coordinated Stage 0 rebuild of 7 Oct 2026 changed some June 2026 ids)
SNAP = ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
STAGE0 = SNAP / "predictability_diagnostic" / "stage0_matches.parquet"
STAGE1 = SNAP / "predictability_diagnostic" / "stage1_odds.parquet"
TIMING = SNAP / "match_timing" / "timing.parquet"
MODEL = ROOT / "data" / "studies" / "surface_rating_race" / "model"
MODEL_FRAME = MODEL / "model_frame.parquet"
MODEL_INPUTS = MODEL / "model_inputs.json"
SHARP = ROOT / "data" / "studies" / "sharp_benchmark" / "matches.parquet"
SHARP_MARKETS = ROOT / "data" / "studies" / "polymarket_sharp_money" / "markets.parquet"
ADAPTIVE = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "adaptive"
SPEED_COLUMNS = ADAPTIVE / "columns.parquet"
COEFFICIENTS = ADAPTIVE / "coefficients.json"

SEASONS = tuple(range(2020, 2027))            # scored seasons; the decided calibration needs 2019 .. Y - 1
FRAME_SEASONS = tuple(range(2018, 2027))      # the sample: 2018-2019 add training rows for the opening-line arms
STAGE2_SEASONS = (2024, 2025, 2026)           # seasons with the speed adjustment's coefficients (both stages)
SEEDS = (0, 1, 2, 3)                          # the decided calibration's seeds
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}
TRAIN_FROM = 2013

# The price blocks. Each early block is scored against its own venue's close.
BOL = ("bol_open", "bol_close")
PM_HORIZONS = {"pm_h48": 2880, "pm_h24": 1440, "pm_h12": 720, "pm_h6": 360, "pm_h3": 180, "pm_h1": 60,
               "pm_m30": 30}                  # minutes before the listed start (the sharp benchmark's pw_pm_m<minutes>)
PRICE_BLOCKS = BOL + tuple(PM_HORIZONS)
BLOCKS = ("td",) + PRICE_BLOCKS               # td: the frame as stored (the market-average close), the reproduction check
CLOSE_OF = {"bol_open": "bol_close", **{b: "pm_m30" for b in PM_HORIZONS if b != "pm_m30"}}

EPS = 1e-6                                    # the clip before a logit, as every TabPFN harness of the project
LOCAL_DAY_END = 4 / 3                         # a local day ends at most 1.33 days after its UTC midnight (UTC-8)
BLOCK_ORIGIN = np.datetime64("2010-01-04")    # a Monday: four-week blocks as the corrected harness

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def lg(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def ex(z) -> np.ndarray:
    return expit(np.asarray(z, dtype=float))


def devig(d_a, d_b) -> np.ndarray:
    """P(A) with the margin removed proportionally (the project's convention; Stage 1's p_mkt is this of the average)."""
    ia, ib = 1.0 / np.asarray(d_a, dtype=float), 1.0 / np.asarray(d_b, dtype=float)
    return ia / (ia + ib)


def blocks(dates, width_days: int = 28) -> np.ndarray:
    days = (np.asarray(dates, dtype="datetime64[D]") - BLOCK_ORIGIN).astype(int)
    return days // width_days


def stake(d) -> np.ndarray:
    """The owner's staking rule of 8 Oct 2026 (src/eda/tabpfn_thinking58/common.stake): to win 1 unit on a favourite
    (d <= 2), d / (2 (d - 1)) units on an underdog (wins d / 2)."""
    d = np.asarray(d, dtype=float)
    if np.any(~np.isfinite(d) | (d <= 1.0)):
        raise ValueError("decimal odds must be finite and above 1")
    return np.where(d <= 2.0, 1.0 / (d - 1.0), d / (2.0 * (d - 1.0)))


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=_default), encoding="utf-8")


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)
