"""Shared pieces of the data-continuity study: the box-score contract, number parsing, and the agreement measure.

The contract is Sackmann's nine serve counts per player, the inputs of every box-score feature in the repository
(stage0_match_players and everything built on it). His data dictionary names them without defining them further:

    ace         aces
    df          double faults
    svpt        serve points
    first_in    first serves in
    first_won   first-serve points won
    second_won  second-serve points won
    sv_gms      serve games
    bp_saved    break points saved
    bp_faced    break points faced

Whether serve points include double faults, or serve games include tiebreak games, is not written down anywhere.
So a source "uses Sackmann's definitions" only to the extent that its counts equal his on the same matches, which is
what this study measures. One derived count, ``sv_won`` (first_won + second_won, serve points won), is compared too,
because two sources (TDI, the WTA API) publish it directly but not its split.

Every reader returns one row per (record, player) with the columns in ``COUNTS`` + ``DERIVED`` (NaN where the source
has no such count) and a boolean ``won``. Nothing here writes outside data/studies/data_continuity/ and
data/raw/data_continuity/.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "data_continuity"
RAW = ROOT / "data" / "raw" / "data_continuity"
DUMP = ROOT / "data" / "dump"
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic"
LINKS = ROOT / "data" / "studies" / "match_timing" / "links"

COUNTS = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
DERIVED = ["sv_won"]
FIELDS = COUNTS + DERIVED
SACKMANN_NAMES = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
                  "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}
# Sackmann's main-tour weeks end with the week of 25 May 2026; lower tiers run to 1-2 June (stage0_build.SACKMANN_END)
SPLICE = pd.Timestamp("2026-05-25")

# Row checks of the contract: the plausibility checks Stage 0 applies (stage0_build.BOX_CHECKS B0-B4, B6-B8), here
# per player and on raw counts. A failure marks the row; it is not dropped, so the agreement tables can be read both
# ways.
INVARIANTS = {
    "negative": "a negative count",
    "first_in_gt_svpt": "first serves in exceed serve points",
    "first_won_gt_first_in": "first-serve points won exceed first serves in",
    "second_won_gt_second": "second-serve points won exceed second serves",
    "bp_saved_gt_faced": "break points saved exceed break points faced",
    "df_gt_second": "double faults exceed second serves",
    "ace_gt_won": "aces exceed serve points won",
    "breaks_gt_sv_gms": "breaks conceded exceed service games",
}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False, default=_jsonable) + "\n", encoding="utf-8")


def _jsonable(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else round(float(value), 6)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return str(value)


def num(s: pd.Series) -> pd.Series:
    """Source text to float; blanks and non-numbers are NaN."""
    return pd.to_numeric(s.astype("string").str.strip().replace("", pd.NA), errors="coerce").astype("float64")


RATIO = re.compile(r"^\s*(-?\d+)\s*/\s*(-?\d+)")


def ratio(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    """SofaScore's "38/52 (73%)" as (38, 52); anything else as (NaN, NaN)."""
    parts = s.astype("string").str.extract(RATIO)
    return num(parts[0]), num(parts[1])


def read_parquet_dedup(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Read a staged Parquet file whose schema repeats a column name (the WTA per-year files carry ``year``
    twice); later repeats get a ``__2`` suffix."""
    table = pq.ParquetFile(path).read()
    seen: dict[str, int] = {}
    names = []
    for name in table.column_names:
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f"{name}__{seen[name]}")
    df = table.rename_columns(names).to_pandas()
    return df[columns] if columns else df


def finish(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the derived count and make every field a float column."""
    for c in COUNTS:
        if c not in frame:
            frame[c] = np.nan
        frame[c] = frame[c].astype("float64")
    if "sv_won" not in frame or frame["sv_won"].isna().all():
        frame["sv_won"] = frame["first_won"] + frame["second_won"]
    frame["sv_won"] = frame["sv_won"].astype("float64")
    return frame


def invariant_failures(box: pd.DataFrame) -> pd.DataFrame:
    """One boolean column per INVARIANTS key: True where this player's row breaks the check (NaN counts pass)."""
    b = box
    second = b["svpt"] - b["first_in"]
    won = b["first_won"] + b["second_won"]
    checks = {
        "negative": (b[COUNTS] < 0).any(axis=1),
        "first_in_gt_svpt": b["first_in"] > b["svpt"],
        "first_won_gt_first_in": b["first_won"] > b["first_in"],
        "second_won_gt_second": b["second_won"] > second,
        "bp_saved_gt_faced": b["bp_saved"] > b["bp_faced"],
        "df_gt_second": b["df"] > second,
        "ace_gt_won": b["ace"] > won,
        "breaks_gt_sv_gms": (b["bp_faced"] - b["bp_saved"]) > b["sv_gms"],
    }
    return pd.DataFrame({k: v.fillna(False).astype(bool) for k, v in checks.items()}, index=box.index)


def agreement(left: pd.DataFrame, right: pd.DataFrame, by: list[str] | None = None,
              fields: list[str] = FIELDS) -> pd.DataFrame:
    """Field-by-field agreement of two aligned frames (same index, one player per row).

    For each field and group: rows where both values exist, how many are equal, within one, the mean and the mean
    absolute difference (right minus left). Groups come from columns of ``left``."""
    by = by or []
    keys = left[by].copy() if by else pd.DataFrame(index=left.index)
    rows = []
    for f in fields:
        a, b = left[f], right[f]
        both = a.notna() & b.notna()
        d = (b - a).where(both)
        frame = keys.assign(_both=both, _eq=(d == 0) & both, _w1=(d.abs() <= 1) & both, _d=d, _ad=d.abs())
        g = frame.groupby(by, dropna=False) if by else frame.groupby(lambda _: "all")
        out = g.agg(n=("_both", "sum"), equal=("_eq", "sum"), within1=("_w1", "sum"), mean_diff=("_d", "mean"),
                    mean_abs_diff=("_ad", "mean")).reset_index()
        if not by:
            out = out.drop(columns=["index"])
        out.insert(len(by), "field", f)
        rows.append(out)
    res = pd.concat(rows, ignore_index=True)
    res["equal_share"] = res["equal"] / res["n"].where(res["n"] > 0)
    res["within1_share"] = res["within1"] / res["n"].where(res["n"] > 0)
    for c in ("equal", "within1", "n"):
        res[c] = res[c].astype("int64")
    return res


def norm_name(s: pd.Series) -> pd.Series:
    """Accents, case and punctuation removed, tokens sorted ("Zhang Zhizhen" == "Zhizhen Zhang"), as in
    merge_feasibility/scan.py."""
    from src.eda.merge_feasibility import scan as S  # noqa: E402

    return s.fillna("").astype(str).map(S.name_key)


def load_stage0() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 0's matches and the two player rows of each, as read-only inputs."""
    m = pd.read_parquet(STAGE0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "round", "tournament_date",
                                 "status", "score", "has_box", "box_status", "sv_gms_incl_tb", "source", "tml_link",
                                 "source_file", "source_row"])
    p = pd.read_parquet(STAGE0 / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "side", "won", "player_name"] + COUNTS)
    return m, p
