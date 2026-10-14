"""Shared definitions of the study "lower-level evidence: informing the main-tour model without treating Challenger
and ITF matches as equivalent" (lower_level_evidence).

The owner's question (9 Oct 2026): the current best model trains on main-tour matches (250 and above) only, but its
inputs are built from every level's history. A large volume of Challenger and ITF data is about to arrive. It should
INFORM the main-tour model (as the UFC pipeline lets a fighter's record outside the UFC skew his prior) without being
treated as EQUIVALENT to main-tour evidence. Diagnose how lower-level data enters the model today, and propose how it
should.

Paths default to the frozen reference of 8 Oct 2026 (read-only, hashed copies), so every number can be recomputed on
the same tables while other sessions rebuild the live ones. Every script takes --stage0-dir so that it reruns unchanged
on a candidate Stage 0 carrying the incoming lower-level data (the renewable part of the study).

Levels. Stage 0's `map_level` already separates qualifying. The study's buckets:
    MAIN   main draws of the Grand Slams, Tour Finals, 1000s, 500s and 250s: the model's training rows ("250+")
    TQ     qualifying of the 1000s, 500s and 250s
    GSQ    Grand Slam qualifying
    CH     Challenger and WTA 125 main draws
    CHQ    Challenger and WTA 125 qualifying
    ITF    ITF World Tennis Tour main draws
    ITFQ   ITF qualifying
    TEAM   team events (Davis Cup, Billie Jean King Cup, United Cup, ...)

The holdout. 2025-2026 is the proposed clean holdout (docs/studies/clean_holdout_rebuild/): every match of events from
30 Dec 2024. Nothing in this study reads an outcome of a holdout match (who won, a score, a box-score performance, a
forecast's accuracy). Counting holdout matches, their levels and their data coverage reads no outcome and is allowed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REF = ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen"
STAGE0_DIR = REF / "tables" / "data" / "studies" / "predictability_diagnostic"   # stage0_matches / _match_players
FRAME = REF / "instance" / "model_frame.parquet"                                  # 67,226 main-tour matches, in_* inputs
INPUTS = REF / "instance" / "model_inputs.json"
FITS = REF / "instance" / "fits"                                                  # seeds 0-3, seasons 2019-2026
TIMING = REF / "tables_later" / "data" / "studies" / "match_timing" / "timing.parquet"
OUT = ROOT / "data" / "studies" / "lower_level_evidence"
DOCS = ROOT / "docs" / "studies" / "lower_level_evidence"

HOLDOUT_START = pd.Timestamp("2024-12-30")      # events from this date belong to the proposed 2025-2026 holdout

MAIN_LEVELS = ("GS", "FIN", "T1000", "T500", "T250")
BUCKETS = ("MAIN", "TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ", "TEAM")
LOWER = ("TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ")   # below the main tour's main draws (TEAM is kept apart)


def bucket(map_level: pd.Series) -> pd.Series:
    """Stage 0's map_level -> the study's bucket. Fails on a value it does not know (a new source's new level)."""
    b = map_level.astype("string")
    b = b.where(~b.isin(MAIN_LEVELS), "MAIN")
    unknown = set(b.dropna().unique()) - set(BUCKETS)
    if unknown:
        raise ValueError(f"unknown map_level values {sorted(unknown)}: extend common.bucket before reading them")
    if b.isna().any():
        raise ValueError(f"{int(b.isna().sum())} rows without a map_level")
    return b


def load_matches(stage0_dir: Path = STAGE0_DIR, columns: list[str] | None = None) -> pd.DataFrame:
    """Stage 0's matches (one row per match), with the study's `bucket` added when map_level is read."""
    cols = None if columns is None else sorted(set(columns) | {"match_id"})
    m = pd.read_parquet(Path(stage0_dir) / "stage0_matches.parquet", columns=cols)
    if "map_level" in m.columns:
        m["bucket"] = bucket(m["map_level"])
    return m


def load_players(stage0_dir: Path = STAGE0_DIR, columns: list[str] | None = None,
                 match_ids=None) -> pd.DataFrame:
    """Stage 0's player rows (two per match): identities, ranks and the box-score numerators and denominators.

    With match_ids, only those matches' rows are read (a filtered read): the other matches' box scores never reach
    memory. Pass the pre-holdout match ids whenever box-score values are read."""
    cols = None if columns is None else sorted(set(columns) | {"match_id", "player_id"})
    path = Path(stage0_dir) / "stage0_match_players.parquet"
    if match_ids is None:
        return pd.read_parquet(path, columns=cols)
    ids = pd.Index(match_ids).astype(str).unique().tolist()
    return pd.read_parquet(path, columns=cols, filters=[("match_id", "in", ids)])


def load_frame(path: Path = FRAME, columns: list[str] | None = None) -> pd.DataFrame:
    """The current best model's frame: main-tour matches with closing odds, 2013-2026; the inputs are `in_*`."""
    return pd.read_parquet(path, columns=columns)


def in_holdout(dates: pd.Series) -> pd.Series:
    """True for matches of events from 30 Dec 2024 (the proposed 2025-2026 holdout), by tournament date."""
    return pd.to_datetime(dates) >= HOLDOUT_START


def assert_no_holdout_outcomes(dates: pd.Series, what: str) -> None:
    """Call before reading outcomes: refuses if any row belongs to the holdout."""
    n = int(in_holdout(dates).sum())
    if n:
        raise AssertionError(f"{what}: {n} rows from the 2025-2026 holdout would have their outcome read")
