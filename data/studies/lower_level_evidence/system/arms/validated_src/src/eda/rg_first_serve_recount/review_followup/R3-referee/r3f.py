"""R3-referee (follow-up review of 9 Oct 2026): shared paths and helpers.

Writes nothing. The scripts of this folder write only into
data/studies/rg_first_serve_recount/followup/review/R3-referee/.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R3-referee"
FOLLOW = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
RAW = ROOT / "data" / "raw" / "point_sources"
DUMP = ROOT / "data" / "dump" / "points"

# Sackmann's column names of the nine counts, in the override table's order (common.BOX_SOURCE_NAMES)
NINE = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
        "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}
EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_saved", "bp_faced"]
OV_COLS = [f"{s}_{c}" for s in ("w", "l") for c in NINE.values()]
SCOPE_COLS = ["feed_key", "stage0_match_id"] + OV_COLS
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


def fold(name) -> list[str]:
    s = unicodedata.normalize("NFKD", str(name or "")).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s).split()


def name_ok(a, b) -> int:
    """2: the same words in any order (or the same letters); 1: a shared word of 3+ letters, or a 6+ letter word of
    one inside the other's letters; 0: nothing shared."""
    ta, tb = fold(a), fold(b)
    if not ta or not tb:
        return 0
    if sorted(ta) == sorted(tb) or "".join(sorted(ta)) == "".join(sorted(tb)) or "".join(ta) == "".join(tb):
        return 2
    if {t for t in ta if len(t) >= 3} & {t for t in tb if len(t) >= 3}:
        return 1
    ja, jb = "".join(ta), "".join(tb)
    if any(len(t) >= 6 and t in jb for t in ta) or any(len(t) >= 6 and t in ja for t in tb):
        return 1
    return 0


def frac(v):
    m = FRAC.match(str(v)) if v is not None else None
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def numbers(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """The columns as floats, blank text as NaN (the way Stage 0 reads them)."""
    return frame[cols].apply(lambda s: pd.to_numeric(s.astype("object").where(s.notna(), "").astype(str).str.strip()
                                                     .replace({"": np.nan, "nan": np.nan, "None": np.nan}),
                                                     errors="coerce"))


def rowkey(files: pd.Series, rows: pd.Series) -> pd.Series:
    return files.astype(str).str.strip() + "#" + pd.to_numeric(rows, errors="coerce").astype("Int64").astype(str)
