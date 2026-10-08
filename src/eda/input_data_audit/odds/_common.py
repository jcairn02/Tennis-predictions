"""Shared paths and loaders for the closing-odds audit (read-only on the repo)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\zerom\Documents\Tennis-predictions")
AUD = Path(__file__).resolve().parent
OUTD = ROOT / "data" / "studies" / "input_data_audit" / "odds"
OUTD.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

TD = ROOT / "data" / "dump" / "odds" / "tennis_data_couk"
RAW = ROOT / "data" / "raw" / "public_dump" / "tennis_data_couk"
SUP = RAW / "superseded"
OLD = ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/predictability_diagnostic"
NEW = ROOT / "data/studies/predictability_diagnostic"
MF = ROOT / "data/studies/surface_rating_race/model/model_frame.parquet"

KNOWN_BOOKS = ["B365", "B&W", "CB", "EX", "LB", "GB", "IW", "PS", "SB", "SJ", "UB", "Max", "Avg", "BbMx", "BbAv"]


def book_cols(cols) -> list[str]:
    """Bookmaker prefixes that have both <p>W and <p>L in the columns."""
    out = []
    cs = set(cols)
    for c in cols:
        if c.endswith("W") and c[:-1] + "L" in cs:
            p = c[:-1]
            if p in ("", "Wsets", "W"):
                continue
            if p in KNOWN_BOOKS or p not in ("Best of",):
                if p not in out and p not in ("WRank", "WPts"):
                    out.append(p)
    return [p for p in out if p in KNOWN_BOOKS]


def load_staged(years=range(2010, 2027)) -> pd.DataFrame:
    """Every staged tennis-data row (current staging = the 5 Oct 2026 download), all columns as text."""
    frames = []
    for f in sorted(TD.glob("*/*/*.parquet")):
        y = int(f.stem)
        if y not in years:
            continue
        df = pd.read_parquet(f)
        df["_tour"] = f.parts[-3]
        df["_season"] = y
        df["_file"] = f.relative_to(ROOT).as_posix()
        df["_td_row"] = np.arange(len(df))
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def read_book(path: Path) -> pd.DataFrame:
    from src.ingest.public_dump import common as IC
    sheet, header, rows, meta = IC.read_workbook(path)
    w = len(header)
    rows = [r + [None] * (w - len(r)) if len(r) < w else r[:w] for r in rows]
    return pd.DataFrame(rows, columns=header)


def num(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    return v.where(v > 1.0)


def logit(p):
    p = np.asarray(p, dtype="float64")
    return np.log(p / (1 - p))
