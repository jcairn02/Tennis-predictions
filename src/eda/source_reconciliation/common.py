"""Shared pieces of the source-reconciliation study (docs/studies/source_reconciliation/).

The study asks, field by field, which of the sources on disk is the most accurate for the raw data the current best
model reads, and whether a combination of them, or a correction of corrupt rows, beats the source the model uses.

Every part reads the frozen copies under SNAP (snapshot.py writes them, with their SHA-256), never the live tables, so
that a coordinated Stage 0 rebuild by another session cannot change the study's inputs mid-way. Outputs go to OUT and
its part folders only. Nothing here writes to Stage 0, Stage 1, the dump or any decided table.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
DUMP = DATA / "dump"
RAW = DATA / "raw"
STUDIES = DATA / "studies"
OUT = STUDIES / "source_reconciliation"
SNAP = OUT / "_snapshot"
STAGE0_LIVE = STUDIES / "predictability_diagnostic"
LINKS_LIVE = STUDIES / "match_timing" / "links"
HANDOFF = RAW / "public_dump" / "atp_pipeline_handoff"

# The nine counts of the box-score contract (data_continuity/common.py), and the derived serve points won.
COUNTS = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
FIELDS = COUNTS + ["sv_won"]

# Matches from this day on are the proposed sealed holdout (feature-provenance study): no outcome of theirs is read.
SEAL = pd.Timestamp("2026-07-29")
SPLICE = pd.Timestamp("2026-05-25")   # Sackmann's last main-tour week (stage0_build.SACKMANN_END)


def sha256(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            b = handle.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False, default=_jsonable) + "\n", encoding="utf-8")


def _jsonable(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if np.isnan(value) else round(float(value), 6)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, np.bool_):
        return bool(value)
    return str(value)


def stage0(columns_m: list[str] | None = None, columns_p: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The frozen Stage 0 (matches, player rows)."""
    m = pd.read_parquet(SNAP / "stage0_matches.parquet", columns=columns_m)
    p = pd.read_parquet(SNAP / "stage0_match_players.parquet", columns=columns_p)
    return m, p


def links(name: str, columns: list[str] | None = None) -> pd.DataFrame:
    """A frozen match-timing link file: one source's records placed on Stage 0's match ids."""
    return pd.read_parquet(SNAP / "links" / f"{name}.parquet", columns=columns)


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.strip().replace("", pd.NA), errors="coerce").astype("float64")


def agreement(left: pd.DataFrame, right: pd.DataFrame, by: list[str] | None = None,
              fields: list[str] = FIELDS) -> pd.DataFrame:
    """Field-by-field agreement of two aligned frames (same index, one player per row): rows where both values exist,
    how many are equal, within one, the mean and mean absolute difference (right minus left). As
    data_continuity/common.agreement, so the two studies' tables read the same way."""
    from src.eda.data_continuity import common as K

    return K.agreement(left, right, by=by, fields=fields)


def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval of a share k/n."""
    if n <= 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)
