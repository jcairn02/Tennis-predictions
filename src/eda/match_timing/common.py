"""Shared paths and helpers for the match-timing study (src/eda/match_timing/).

The study replaces the tournament-week clock with a leak-proof timeline. Every match of the analysis table gets an
earliest possible start day (ES) and a latest possible finish day (LF): its real day where any source supplies one,
otherwise a window from its tournament, round and level. A result may inform another match's features only if it
surely finished before that match could start (LF of the result < ES of the match).

Days are integers: days since 1970-01-01, the convention of stage4_features.prepare (tournament_date as datetime64[D]).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "match_timing"
LINKS = OUT / "links"
DOCS = ROOT / "docs" / "studies" / "match_timing"
TIMING = OUT / "timing.parquet"                   # one row per match: es_day, lf_day, exact day and its provenance
FEATURES = OUT / "leakproof_features.parquet"     # one row per pool match: the 53 sporting inputs, rebuilt
REPAIRED = ROOT / "data" / "studies" / "feature_alpha_audit" / "repairs"

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def to_day(values) -> np.ndarray:
    """Dates (any pandas-readable form) to integer days since 1970-01-01; missing stays missing (as float NaN)."""
    d = pd.to_datetime(pd.Series(values), errors="coerce")
    out = d.to_numpy().astype("datetime64[D]").astype("float64")
    out[d.isna().to_numpy()] = np.nan
    return out


def from_day(days) -> pd.Series:
    return pd.to_datetime(pd.Series(days, dtype="float64"), unit="D", errors="coerce")


def jdump(value, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (pd.Timestamp, np.datetime64)):
            return str(o)
        if isinstance(o, Path):
            return str(o)
        raise TypeError(type(o))
    path.write_text(json.dumps(value, indent=1, default=default), encoding="utf-8")
