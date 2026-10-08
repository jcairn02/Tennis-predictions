"""Shared definitions for the line-sharpening study (docs/studies/line_sharpening/README.md).

Tier groups follow the owner's request of 6 Oct 2026 ("lower ranked tournaments vs higher vs highest"), with the
event types of src/eda/polymarket_sharp_money/build_positions.py:
    highest   Grand Slam main draws, Masters 1000 and WTA 1000, the Finals
    higher    ATP and WTA 500 and 250 main draws
    lower     Challenger, WTA 125, ITF, and qualifying (Grand Slam and tour)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PM_DIR = ROOT / "data" / "dump" / "odds" / "polymarket"
OUT = ROOT / "data" / "studies" / "line_sharpening"

TIER = {
    "slam_atp": "highest", "slam_wta": "highest", "t1000_atp": "highest", "t1000_wta": "highest", "finals": "highest",
    "t500_atp": "higher", "t500_wta": "higher", "t250_atp": "higher", "t250_wta": "higher",
    "challenger": "lower", "wta125": "lower", "itf_m": "lower", "itf_w": "lower", "itf_u": "lower",
    "slam_qual": "lower", "tour_qual": "lower",
}
TIERS = ("highest", "higher", "lower")
# Finer levels for the detail tables.
LEVEL = {
    "slam_atp": "Grand Slam", "slam_wta": "Grand Slam", "t1000_atp": "1000 and Finals", "t1000_wta": "1000 and Finals",
    "finals": "1000 and Finals", "t500_atp": "500", "t500_wta": "500", "t250_atp": "250", "t250_wta": "250",
    "slam_qual": "Qualifying", "tour_qual": "Qualifying", "challenger": "Challenger and WTA 125",
    "wta125": "Challenger and WTA 125", "itf_m": "ITF", "itf_w": "ITF", "itf_u": "ITF",
}
LEVELS = ("Grand Slam", "1000 and Finals", "500", "250", "Qualifying", "Challenger and WTA 125", "ITF")

# In-play detector (validated against 2,370 known first points, see the README): the first price-history point
# from which the summed absolute price change reaches DET_THR within DET_W minutes and DET_STHR within DET_SUS
# minutes, searched from DET_LO before to DET_HI after the listed start.
DET_W, DET_THR, DET_SUS, DET_STHR = 5, 0.04, 30, 0.15
DET_LO, DET_HI = -6 * 3600, 30 * 3600
CLOSE_BUFFER = 300        # seconds before a validated detected start
FALLBACK_BUFFER = 1800    # seconds before the listed start
MAX_PRICE_AGE = 3600      # a looked-up price must be at most this old
# A detected start is accepted only if the match is decided (price outside DECIDED for good) a plausible time
# after it; otherwise the next candidate is tried. Thin lower-tier books produce sustained pre-match swings
# hours before play (a 3-7 h early detection is followed by a decision within 4 h in 1-11% of markets, against
# 90-100% near the listed start).
DECIDED = (0.03, 0.97)
MIN_PLAY_H, MAX_PLAY_H, MAX_PLAY_H_SLAM = 0.4, 4.5, 6.5


def decided_at(t: np.ndarray, p: np.ndarray, band: tuple[float, float] = DECIDED) -> float:
    """Time from which the price never re-enters the open band (the match decided), NaN if it never leaves it."""
    inside = (p > band[0]) & (p < band[1])
    if not len(p) or inside[-1]:
        return np.nan
    last_inside = np.flatnonzero(inside)
    k = last_inside[-1] + 1 if len(last_inside) else 0
    return float(t[k])


def validated_start(t: np.ndarray, p: np.ndarray, start: float, max_play_h: float = MAX_PLAY_H,
                    tries: int = 6) -> tuple[float, float, int]:
    """(validated start of play, decision time, candidates tried). Candidates come from detect_start in time
    order; the first followed by a decision MIN_PLAY_H..max_play_h hours later is accepted."""
    dec = decided_at(t, p)
    lo = DET_LO
    for k in range(tries):
        d = detect_start(t, p, start, lo=lo)
        if not np.isfinite(d):
            return np.nan, dec, k
        if np.isfinite(dec) and MIN_PLAY_H * 3600 <= dec - d <= max_play_h * 3600:
            return d, dec, k + 1
        lo = d - start + 1800
    return np.nan, dec, tries


def detect_start(t: np.ndarray, p: np.ndarray, start: float, w: int = DET_W, thr: float = DET_THR,
                 sustain: int = DET_SUS, sthr: float = DET_STHR, lo: float = DET_LO, hi: float = DET_HI) -> float:
    """First time in [start + lo, start + hi] where the price moves at least `thr` in total within `w` minutes
    and `sthr` within `sustain` minutes (the onset of in-play trading). t: seconds, sorted; p: prices in [0, 1].
    The time returned is that of the first price change of the run. NaN if there is none."""
    if len(t) < 3:
        return np.nan
    dp = np.abs(np.diff(p))
    tt = t[1:]
    cs = np.r_[0.0, np.cumsum(dp)]
    a = np.flatnonzero((tt >= start + lo) & (tt <= start + hi) & (dp > 0))
    if len(a) == 0:
        return np.nan
    e1 = np.searchsorted(tt, tt[a] + 60 * w, side="left")
    e2 = np.searchsorted(tt, tt[a] + 60 * sustain, side="left")
    ok = np.flatnonzero((cs[e1] - cs[a] >= thr - 1e-12) & (cs[e2] - cs[a] >= sthr - 1e-12))
    return float(tt[a[ok[0]]]) if len(ok) else np.nan


def lookup(keys: np.ndarray, times: np.ndarray, values: np.ndarray, q_keys: np.ndarray, q_times: np.ndarray,
           max_age: float | None = MAX_PRICE_AGE) -> tuple[np.ndarray, np.ndarray]:
    """Last value at or before each query time, per integer key. `keys`/`times` must be sorted by (key, time).
    Returns (value, time of that value); NaN where there is none or it is older than max_age."""
    span = np.int64(1) << 36
    path = keys.astype(np.int64) * span + times.astype(np.int64)
    q = q_keys.astype(np.int64) * span + np.floor(q_times).astype(np.int64)
    idx = np.searchsorted(path, q, side="right") - 1
    safe = np.maximum(idx, 0)
    ok = (idx >= 0) & (keys[safe] == q_keys)
    if max_age is not None:
        ok &= (q_times - times[safe]) <= max_age
    return np.where(ok, values[safe], np.nan), np.where(ok, times[safe], np.nan)


def log_loss(p: np.ndarray, y: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Per-market log loss (nats) of probability p for outcome y in {0, 1}."""
    p = np.clip(p, eps, 1 - eps)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def epoch(ts: pd.Series) -> pd.Series:
    """Epoch seconds from a tz-aware datetime Series (unit-agnostic under pandas 3)."""
    return (ts - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
