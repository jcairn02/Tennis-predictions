"""Shared paths, constants and helpers for the study "point sequence" (src/eda/point_sequence/).

The study builds one validated point-sequence table: who served and who won every point, in order, with the set and
game structure, from every point source on disk, linked to the predictability diagnostic's Stage 0 match table so that
momentum, streak and pressure statistics can later be computed for as many main-tour matches as possible. It computes
no feature and fits no model.

Sources
    The eight sources the shot-level study already converted to its common point table (src/eda/shot_level/points.py)
    are reused as they are, from data/studies/shot_level/stage1_points_<source>.parquet with their Stage 0 links in
    stage0_source_matches.parquet. New sources get an adapter here (adapters.py): the Kaggle marcosjn2 SofaScore scrape,
    the project's own SofaScore scrapes, the WTA API's umpire event logs and its point-by-point feed, and Sackmann's old
    point strings.

The earlier studies' code and tables are read-only: imported, never edited.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "point_sequence"
SHOT = ROOT / "data" / "studies" / "shot_level"
DUMP = ROOT / "data" / "dump"
RAW = ROOT / "data" / "raw"
BASE_FRAME = ROOT / "data" / "studies" / "surface_ios" / "base_frame.parquet"
T0 = time.time()

# The shot-level study's eight converted sources (reused as they are) and this study's new ones.
EXISTING = ["slamtracker", "slam_pbp", "ausopen", "slam_tracking", "infosys", "sirgenkii", "tdi", "mcp"]
NEW = ["ausopen_mc", "wta", "wta_pbp", "sofascore", "marcosjn2", "sackmann_pbp"]

# Reused tables found unfit for point sequences: replayed and reported, never chosen. The shot-level study's AO table
# keeps rows of type 'point' only, so every game lacks its last point (the feed writes it as type 'game', 'set' or
# 'match'); ausopen_mc is this study's corrected conversion of the same feed.
DEFECTIVE = {"ausopen": "every game's last point is missing (rows of type game/set/match left out); replaced by "
                        "ausopen_mc"}

# Preference when several sources hold one Stage 0 match, after quality (complete, agreeing with the official
# result and with the other sources): the official and annotated feeds first, then SofaScore, marcosjn2 (SofaScore
# as scraped by a third party), Sackmann's strings. Within the first group the official feeds with clock times come
# first, and the WTA's umpire log (millisecond times, serve number) before the volunteer charts. The WTA's
# point-by-point feed is placed after marcosjn2, on measurement (build_summary.json, "wta_feeds"): in the 7,102 WTA
# matches held by the umpire log, the point-by-point feed and marcosjn2, when the last two disagree (1,444 matches)
# the umpire log sides with marcosjn2 in 1,106 and with the point-by-point feed in 198; where both WTA feeds replay to
# the official score, the point-by-point feed has fewer points in 2.5% of matches (typically two: a dropped deuce).
PRIORITY = ["slamtracker", "slam_pbp", "ausopen_mc", "slam_tracking", "infosys", "sirgenkii", "tdi", "wta", "mcp",
            "sofascore", "marcosjn2", "wta_pbp", "sackmann_pbp", "ausopen"]
RANK = {s: i for i, s in enumerate(PRIORITY)}

# Which sources' raw files carry a clock time per point (the reused tables of the shot-level study do not keep it).
RAW_TIMES = {"slamtracker": "raw feed has a clock time per point (not kept in the shot-level table)",
             "tdi": "raw feed has a UTC time per point (not kept in the shot-level table)",
             "ausopen": "raw match centre has a time per point (not kept in the shot-level table)",
             "ausopen_mc": "kept: t_utc, the match centre's time of each point (whole seconds)",
             "wta": "kept: t_utc, the umpire log's millisecond UTC time of each point",
             "wta_pbp": "kept: t_utc, the point-by-point feed's UTC time (whole seconds)"}

# The common point schema (src/eda/shot_level/points.py) plus this study's extra columns.
from src.eda.shot_level import points as SP  # noqa: E402

COLUMNS = list(SP.COLUMNS)
EXTRA = ["t_utc", "is_tb", "game_no"]
END = SP.END


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def num(s) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


SLAM_ORDER = [("AO", r"australian|aus open|melbourne"), ("RG", r"roland|french open|paris, france"),
              ("W", r"wimbledon"), ("USO", r"us open|u\.s\. open|new york, usa")]


def slam_of(name) -> str | None:
    """The Grand Slam a tournament name refers to, or None. The Australian Open is tested first, since 'Aus Open'
    contains 'us open'."""
    n = str(name or "").lower()
    if not n:
        return None
    for code, pat in SLAM_ORDER:
        if re.search(pat, n):
            return code
    return None


def file_sig(path: Path) -> dict:
    """Size and modification time of an input file (hashing hundreds of megabytes on every run is not worth it; the
    small files are hashed)."""
    p = Path(path)
    if not p.exists():
        return {"path": rel(p), "exists": False}
    st = p.stat()
    out = {"path": rel(p), "bytes": int(st.st_size),
           "modified_utc": pd.Timestamp(st.st_mtime, unit="s", tz="UTC").isoformat(timespec="seconds")}
    if st.st_size <= 50_000_000:
        out["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, default=_json_default, ensure_ascii=False) + "\n", encoding="utf-8")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.isoformat()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def int8(a) -> np.ndarray:
    return np.asarray(a).astype("int8")
