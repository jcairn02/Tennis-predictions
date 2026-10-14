"""Shared definitions of the edge-anatomy study (docs/studies/edge_anatomy/, 12 Oct 2026).

The owner's question: which parts of the current best model's information the recent (2025-26) closing line prices and
which it does not, and where the recent edge comes from. The instance studied is the current one,
data/studies/current_best_model/template_2026-10-10/ (read-only). This study's fits and outputs live in
data/studies/edge_anatomy/.

The input families were fixed before any result was read (process_log.md, section 3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10"
OUT = ROOT / "data" / "studies" / "edge_anatomy"
FITS = OUT / "fits"
SPEED = ROOT / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
SEALED_FROM = pd.Timestamp("2026-07-29")        # the proposed sealed holdout: no result from this day on is read
FIT_SEASONS = tuple(range(2019, 2027))          # 2019 feeds the walk-forward calibration of 2020
SEEDS = (0, 1, 2, 3)
RECENT = (2025, 2026)                           # the recent window (2026 up to 28 Jul)
EARLIER = (2020, 2021, 2022, 2023, 2024)

FAMILIES: dict[str, list[str]] = {
    "price": ["odds_logit"],
    "context": ["tour", "surface", "level", "indoor", "best_of", "round"],
    "ratings": ["ratings_iid", "elo_games", "elo_overall", "elo_surf_offset", "points_52w"],
    "schedule": ["sets_14d", "age", "age_sq", "surf_season_a", "surf_season_b", "surf_layoff_a", "surf_layoff_b"],
    "form": ["adjperf_tpw_2w"] + [f"form_{s}" for s in ("ace", "df", "first_in", "first_won", "second_won", "hold",
                                                         "bp_saved", "bp_faced_pg", "brk", "bp_conv", "rpw_first",
                                                         "rpw_second")]
            + [f"formdef_{s}" for s in ("ace", "df", "first_in", "bp_faced_pg")],
    "ios": [f"ios{side}_{s}" for s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
            for side in ("O", "D")] + [f"prod_{s}" for s in ("ace", "df", "first_in", "first_won", "second_won",
                                                              "hold", "bp_saved")],
}
LADDER = ("price", "context", "ratings", "schedule", "form", "ios")   # the order families are added in


def input_names() -> list[str]:
    meta = json.loads((INSTANCE / "model_inputs.json").read_text(encoding="utf-8"))
    return [d["name"] for d in meta["inputs"]]


def input_kinds() -> dict[str, str]:
    meta = json.loads((INSTANCE / "model_inputs.json").read_text(encoding="utf-8"))
    return {d["name"]: d["kind"] for d in meta["inputs"]}


def check_families(names: list[str]) -> None:
    flat = [c for fam in FAMILIES.values() for c in fam]
    if sorted(flat) != sorted(names) or len(flat) != len(set(flat)):
        missing = sorted(set(names) - set(flat))
        extra = sorted(set(flat) - set(names))
        raise RuntimeError(f"the families do not partition the 57 inputs: missing {missing}, extra {extra}")


def arms() -> dict[str, list[str]]:
    """Arm -> its inputs, in the instance's column order. L1..L5: the ladder (families added in LADDER order); full:
    every input (the instance's own fits are this arm, seeds 0-15); drop_<family>: the full model without one family."""
    names = input_names()
    check_families(names)
    out = {}
    keep: set[str] = set()
    for i, fam in enumerate(LADDER[:-1], start=1):
        keep |= set(FAMILIES[fam])
        out[f"L{i}"] = [c for c in names if c in keep]
    for fam in ("context", "ratings", "schedule", "form", "ios"):
        out[f"drop_{fam}"] = [c for c in names if c not in FAMILIES[fam]]
    out["full"] = list(names)
    return out


def fit_path(arm: str, season: int, seed: int) -> Path:
    return FITS / f"{arm}__{season}__seed{seed}.npz"


def log(msg: str) -> None:
    import time
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=float), encoding="utf-8")


def sym(p: np.ndarray, k: int) -> np.ndarray:
    """P(A wins): the mean of the stored and the flipped orientation's forecasts."""
    return 0.5 * (p[:k] + 1.0 - p[k:])
