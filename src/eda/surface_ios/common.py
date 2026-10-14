"""Shared paths and constants for the surface-IOS study (src/eda/surface_ios/).

The owner's request of 6 Oct 2026: the best 2026 model's long-memory IOS profile (each player's opponent-adjusted serve
and return strength, statistic by statistic) pools surfaces. Build it per surface, with IOS's long memory, opponent
adjustment and shrinkage towards the player's all-surface value, decide how to give it to the model from evidence, and
test it with TabPFN-3.5 (the non-thinking "Plus" model) in five expanding windows, one test season each, 2022-2026,
against the same model without it.

The IOS model here is the leak-proof one of src/eda/match_timing/ios_time.py (a result enters the solve the day after its
latest possible finish; a match reads the solve of its earliest possible start), with player-by-surface deviations:

    y_k = O_server + E_server,surface - D_returner - F_returner,surface + noise

E and F carry their own ridge penalty (kappa_surface) on top of the tuned all-surface penalty (kappa), so a player's
surface value is shrunk towards their all-surface value; kappa_surface = inf is the existing pooled IOS exactly.

Days are integers since 1970-01-01, as in the match-timing study.
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

OUT = ROOT / "data" / "studies" / "surface_ios"
DOCS = ROOT / "docs" / "studies" / "surface_ios"
CACHE = OUT / "cache"                       # per-tour arrays for the solver (build_cache.py)

STATS = ("spw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
PROFILE_IOS = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")   # the model's 7
N_SURF = 4                                  # 1 Hard, 2 Clay, 3 Grass, 4 Carpet (stage4_features.SURF); 0 unknown
SURF_NAMES = {1: "Hard", 2: "Clay", 3: "Grass", 4: "Carpet"}
TUNE_FROM, TUNE_TO = "2013-01-01", "2018-12-31"   # Stage B's tuning window: constants frozen before any test season

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def day_of(date: str) -> int:
    return int(np.datetime64(date, "D").astype("int64"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, float) and not np.isfinite(o):
            return None if np.isnan(o) else ("inf" if o > 0 else "-inf")
        return o
    path.write_text(json.dumps(clean(value), indent=1, default=default), encoding="utf-8")


def load_tour(tour: str) -> dict:
    """The cached solver arrays of one tour (build_cache.py), as plain numpy arrays."""
    with np.load(CACHE / f"{tour}.npz", allow_pickle=False) as z:
        d = {k: z[k] for k in z.files}
    d["stats"] = {s: {"ok": d.pop(f"{s}__ok"), "x": d.pop(f"{s}__x"), "d": d.pop(f"{s}__d"), "y": d.pop(f"{s}__y"),
                      "mu": d.pop(f"{s}__mu")} for s in STATS}
    d["n_players"] = int(d["n_players"])
    d["tour"] = tour
    return d


def ios_constants() -> tuple[dict, dict]:
    """Stage B's tuned (h, kappa, tau) per (tour, statistic) and the typical units, as the leak-proof rebuild uses
    them: the IOS constants registry's version in effect (src/eda/ios_constants/registry.py)."""
    from src.eda.ios_constants import registry as IC
    return IC.ios_constants()
