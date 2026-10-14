"""Shared definitions of the study "how the tournament levels blend, and should the model be segmented by level?"
(event_levels).

The owner's question (8 Oct 2026): the current best model's training rows are main-tour matches (Grand Slams, Tour
Finals, 1000s, 500s, 250s). Is each level useful? Should each level learn mostly from its own level, with the others
pooled at a lower weight? Lower-level events (Challenger, ITF, qualifying) bring more rows and different statistics:
could they hurt the model, or do they deserve a separate model if they are to be bet? And how do the levels blend
into each other by ranking, and how does that affect the data?

Parts:
    blend.py   descriptive, no model: who plays at which level (the ranking ladder, the mix of levels by rank band,
               moves between levels), what each main-tour match's feature history is made of, the same players'
               statistics at two levels, and Elo's calibration at each level and for players arriving from lower levels
    frame.py   the model's 58 inputs for every Challenger and qualifying match too, on the model frame's own snapshot
               (the 30 Sep 2026 Stage 0 and leak-proof table, kept by the 7 Oct rebuild), checked value for value
               against the model frame on its rows
    fits.py    the local TabPFN-3.5 fits of experiment A (the current model segmented by level) and B (Challenger rows)
    score.py   scoring of A and B, and the current model's own record by level and by the players' history

Experiment A. The current model (58 inputs, decided settings) with only its training rows changed, for each target
level L in TARGETS. Season Y in 2019-2024 is fitted on seasons 2013 .. Y - 1, seeds 0-3, and queries every season-Y
match (stored, then A and B swapped):

    own_L     level L's matches only
    w25_L     L's matches, plus each other match kept with probability 0.25 (TabPFN takes no sample weights, so a
              lower weight is a lower inclusion probability; a new draw per seed)
    w50_L     the same with probability 0.5
    size_L    size control for own_L: a random draw of the whole pool with as many matches as own_L has
    drop_L    every level except L (is L's data useful to the other levels; how do the others transfer to L?)

Experiment B. The extended frame's main-tour (MT, the model frame's rows) and Challenger (CH: men's Challengers and
WTA 125, main draws) matches. Season Y in 2021-2024, seeds 0-1, each fit queries every season-Y MT and CH match:

    nmt       no odds (57 inputs); MT rows only: the current model without its price (stored fits seeds 0-2 exist and
              must be reproduced on the MT rows)
    nch       no odds; CH rows only: a separate Challenger model
    nmtch     no odds; MT and CH rows pooled
    omtch     the 58 inputs; MT rows and CH rows pooled, CH rows with the price missing (no closing price exists for
              them): do lower-level rows hurt the current model on the main tour?

Seasons <= 2024 only for anything that reads a result: 2025-2026 is the proposed clean holdout
(docs/studies/clean_holdout_rebuild/). Frames are built and asserted to stop at 2024.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.training_window import common as TW  # noqa: E402  (frame <= 2024, stored fits, stage 2, speed column)

OUT = ROOT / "data" / "studies" / "event_levels"
LOCAL = OUT / "local"
DOCS = ROOT / "docs" / "studies" / "event_levels"
STUDIES = ROOT / "data" / "studies"

# The model frame's snapshot: the 30 Sep 2026 Stage 0 and the leak-proof table the model was built on, kept by the
# 7 Oct rebuild (data_continuity/rebuilds/2026-10-07T0005Z/replaced/); the other sources are unchanged since.
SNAP = STUDIES / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
SOURCES = {
    "stage0_matches": (SNAP / "predictability_diagnostic" / "stage0_matches.parquet",
                       "271d2561f31d0c8cc407e5fb9b73d572115173e329e272c337f8daddda4662af"),
    "stage0_players": (SNAP / "predictability_diagnostic" / "stage0_match_players.parquet",
                       "f84ec8410140740e929fef2b57b44f28f8ddef2b6b6983c43345d213ee9a6e28"),
    # the leak-proof refit's recorded hash (tabpfn_leakproof/manifest.json), read at check time
    "leakproof": (SNAP / "match_timing" / "leakproof_features.parquet", "manifest"),
    "stage4": (STUDIES / "predictability_diagnostic" / "stage4_features.parquet", None),
    "stageD": (STUDIES / "ufc_ideas" / "stageD_features.parquet", None),
    "stageD_profile": (STUDIES / "ufc_ideas" / "stageD_profile_features.parquet", None),
    "pieces": (STUDIES / "surface_elo_pieces" / "pieces.parquet",
               "40661ce97ee43f6fda8ff69f033c4799bb3e4fd4236efe6a44d95f6cd5e985e2"),
    "surface_features": (STUDIES / "surface_ios" / "surface_features.parquet", None),
}
MODEL_FRAME = TW.P.model_frame
FRAME = OUT / "frame.parquet"                    # the extended frame (frame.py)
COVERAGE_CELLS = STUDIES / "data_map" / "coverage_cells.csv"

LAST_SEASON = 2024
TRAIN_FROM = 2013
TOURS = ("atp", "wta")
# Stage 0's map_level codes, in ladder order
LEVELS = ("GS", "FIN", "T1000", "T500", "T250", "TEAM", "TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ")
MAIN = ("GS", "FIN", "T1000", "T500", "T250")
# the model's level codes (tabpfn_thinking: GS 0 .. T250 4), extended for the rows the model never had
LEVEL_CODES = {"GS": 0, "FIN": 1, "T1000": 2, "T500": 3, "T250": 4, "CH": 5, "TQ": 6, "GSQ": 7, "CHQ": 8}
CODE_LEVEL = {v: k for k, v in LEVEL_CODES.items()}
# tiers for history composition: main tour, tour qualifying, Challenger (main and qualifying), ITF, team events
TIER_OF = {"GS": "MT", "FIN": "MT", "T1000": "MT", "T500": "MT", "T250": "MT", "TQ": "Q", "GSQ": "Q", "CH": "CH",
           "CHQ": "CH", "ITF": "ITF", "ITFQ": "ITF", "TEAM": "TEAM"}
TIERS = ("MT", "Q", "CH", "ITF", "TEAM")
RANK_BANDS = [(1, 10), (11, 20), (21, 50), (51, 100), (101, 150), (151, 200), (201, 300), (301, 500), (501, 1000),
              (1001, 10 ** 6)]

# ---- experiment A
TARGETS = ("GS", "T1000", "T500", "T250")
KINDS_A = ("own", "w25", "w50", "size", "drop")
ARMS_A = tuple(f"{k}_{lv}" for lv in TARGETS for k in KINDS_A)
SEASONS_A = TW.SEASONS                         # 2019-2024; 2019 only calibrates
TEST_A = TW.TEST                               # 2020-2024 scored
SEEDS_A = TW.SEEDS                             # 0-3
DRAW_SEED = 20261009
KIND_CODE = {"w25": 1, "w50": 2, "size": 3}
KEEP_P = {"w25": 0.25, "w50": 0.5}

# ---- experiment B
ARMS_B = ("nmt", "nch", "nmtch", "omtch")
SEASONS_B = (2021, 2022, 2023, 2024)           # 2021 only calibrates
TEST_B = (2022, 2023, 2024)
SEEDS_B = (0, 1)
POP_B = {"nmt": ("MT",), "nch": ("CH",), "nmtch": ("MT", "CH"), "omtch": ("MT", "CH")}

# ---- experiment C (added after part 4's first read, see reading_rules.md): the history composition as an input
ARMS_C = ("hist1",)                            # the 58 inputs + low_share_diff (A's share of last year's matches
                                               # below the main tour minus B's; blend.history)
SEASONS_C = TW.SEASONS
SEEDS_C = TW.SEEDS
NEW_INPUT_C = "low_share_diff"

CONFIG = TW.CONFIG
log, write_json, read_json, sha256_file = TW.log, TW.write_json, TW.read_json, TW.sha256_file
lg, ll, fit_logistic, symmetrize = TW.lg, TW.ll, TW.fit_logistic, TW.symmetrize


def check_sources() -> dict:
    """SHA-256 of every source; the pinned ones must equal the snapshot the model frame was built on."""
    import json
    lp_full = json.loads((STUDIES / "tabpfn_leakproof" / "manifest.json").read_text(encoding="utf-8"))
    lp_full = lp_full["sources"]["leakproof_features"]["sha256"]
    out = {}
    for name, (path, want) in SOURCES.items():
        got = sha256_file(path)
        if want == "manifest":
            want = lp_full
        if want is not None and got != want:
            raise RuntimeError(f"{name}: {path} is not the model frame's snapshot ({got[:12]} != {want[:12]})")
        out[name] = {"path": str(path.relative_to(ROOT)), "sha256": got}
    return out


def band_of(rank: np.ndarray) -> np.ndarray:
    """Rank band labels ('1-10' ... '1001+'), 'unranked' where the rank is missing."""
    r = np.asarray(rank, dtype="float64")
    out = np.full(len(r), "unranked", dtype=object)
    for lo, hi in RANK_BANDS:
        out[(r >= lo) & (r <= hi)] = f"{lo}-{hi}" if hi < 10 ** 6 else f"{lo}+"
    return out


BAND_ORDER = [f"{lo}-{hi}" if hi < 10 ** 6 else f"{lo}+" for lo, hi in RANK_BANDS] + ["unranked"]


# ------------------------------------------------------------------------------------------------
# Experiment A: training rows

def parse_a(arm: str) -> tuple[str, str]:
    kind, level = arm.split("_", 1)
    if kind not in KINDS_A or level not in TARGETS:
        raise KeyError(f"unknown experiment-A arm {arm}")
    return kind, level


def train_mask_a(seasons, levels, arm: str, season: int, seed: int) -> np.ndarray:
    """Which rows (frame order) train arm's fit of `season` with `seed`. seasons, levels: the frame's season and level
    code columns. 'exp' is the current model (every row of 2013 .. season - 1)."""
    seasons, levels = np.asarray(seasons), np.asarray(levels)
    pool = (seasons >= TRAIN_FROM) & (seasons <= season - 1)
    if arm == "exp":
        return pool
    kind, level = parse_a(arm)
    code = LEVEL_CODES[level]
    own = pool & (levels == code)
    if kind == "own":
        return own
    if kind == "drop":
        return pool & (levels != code)
    rng = np.random.default_rng([DRAW_SEED, season, seed, KIND_CODE[kind], code])
    if kind == "size":
        keep = np.zeros(len(seasons), bool)
        keep[rng.choice(np.flatnonzero(pool), size=int(own.sum()), replace=False)] = True
        return keep
    return own | (pool & (rng.random(len(seasons)) < KEEP_P[kind]))


def fit_path_a(arm: str, season: int, seed: int) -> Path:
    return TW.stored_path(season, seed) if arm == "exp" else LOCAL / "A" / f"{arm}__{season}__seed{seed}.npz"


# ------------------------------------------------------------------------------------------------
# Experiment B: training rows

def train_mask_b(seasons, pops, arm: str, season: int) -> np.ndarray:
    """B's training rows: the arm's populations ('MT', 'CH'), seasons 2013 .. season - 1."""
    seasons, pops = np.asarray(seasons), np.asarray(pops)
    if arm not in POP_B:
        raise KeyError(f"unknown experiment-B arm {arm}")
    return (seasons >= TRAIN_FROM) & (seasons <= season - 1) & np.isin(pops, POP_B[arm])


def query_mask_b(seasons, pops, season: int) -> np.ndarray:
    seasons, pops = np.asarray(seasons), np.asarray(pops)
    return (seasons == season) & np.isin(pops, ("MT", "CH"))


def has_odds_b(arm: str) -> bool:
    return arm.startswith("o")


def fit_path_b(arm: str, season: int, seed: int) -> Path:
    return LOCAL / "B" / f"{arm}__{season}__seed{seed}.npz"


def fit_path_c(arm: str, season: int, seed: int) -> Path:
    return LOCAL / "C" / f"{arm}__{season}__seed{seed}.npz"


def stored_noodds_path(season: int, seed: int) -> Path:
    """The current model without its price: the rating race's model_noodds fits (seeds 0-2, MT rows only)."""
    return TW.P.race_local / f"model_noodds__{season}__seed{seed}.npz"


def read_fit(path: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    return TW.read_fit(path)


def frame_seasons_ok(f: pd.DataFrame) -> None:
    if int(f["season"].max()) > LAST_SEASON or pd.Timestamp(f["tournament_date"].max()) > pd.Timestamp(
            f"{LAST_SEASON}-12-31"):
        raise RuntimeError("a season or a match after 2024 was read")
