"""Shared definitions of the study "tour-level qualifying as prediction targets" (qualifying_targets).

The owner's request (22 Oct 2026, on the recommendation of 16 Oct): download Pinnacle's qualifying lines; check how
accurate the closing prices are on qualifying and whether BetOnline's match Pinnacle's there; build the model's inputs
for qualifying and test, on seasons it has not seen, whether it beats the closing price at the bookmaker's own odds
and whether the main-draw predictions stay as good. Design: docs/studies/qualifying_targets/preregistration.md.

Everything rests on the active instance of 22 Oct 2026, template_2026-10-21b, and its build tree (the tables and the
code that built it). Nothing here writes into the instance, the tree or the shared tables, except the OddsTrader dump,
which the every-book pull extends with the qualifying events' lines.
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
OUT = ROOT / "data" / "studies" / "qualifying_targets"
DOCS = ROOT / "docs" / "studies" / "qualifying_targets"
LOCAL = OUT / "local"                       # fits (gitignored: *.npz)

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-21b"
TREE = Path("C:/Users/zerom/tnr_tpl1021")    # the instance's build tree (selected_instance.json, 21 Oct 2026)
TREE_STUDIES = TREE / "data" / "studies"
TREE_STAGE0 = TREE_STUDIES / "predictability_diagnostic" / "stage0_matches.parquet"
TREE_PLAYERS = TREE_STUDIES / "predictability_diagnostic" / "stage0_match_players.parquet"
TREE_TIMING = TREE_STUDIES / "match_timing" / "timing.parquet"

OT = ROOT / "data" / "dump" / "odds" / "oddstrader"
OT_EVENTS, OT_BOOKS, OT_LINES = OT / "events.parquet", OT / "books_lines.parquet", OT / "lines.parquet"
PINNACLE, BETONLINE = 20, 8                 # OddsTrader's book ids (paid)

LINK = OUT / "oddstrader_link.parquet"
EIDS = OUT / "oddstrader_eids.csv"
PRICES = OUT / "prices.parquet"
FRAME = OUT / "frame.parquet"

QUAL_LEVELS = ("GS", "T1000", "T500", "T250")      # Stage 0's level of the event whose qualifying it is
QUAL_GROUPS = ("TQ", "GSQ")                         # Stage 4's groups for those matches
LEVEL_CODES = {"TQ": 6.0, "GSQ": 7.0}               # new codes (event_levels' codes); the model's are GS 0 .. T250 4
FIRST_SEASON, LAST_SEASON = 2018, 2026
FIT_SEASONS = tuple(range(2019, 2027))              # 2019 calibrates only
TEST_SEASONS = tuple(range(2020, 2027))
SEEDS = (0, 1, 2, 3)
ARMS = ("M0", "M1", "M2")
LATE_MIN = 30.0                                     # a line stamped later than this after the listed start is out
OVERROUND_OK = (1.0, 1.2)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.isoformat()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"{type(o)} is not JSON serialisable")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=_default), encoding="utf-8")


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def day_number(ts) -> np.ndarray:
    """Days since 1970-01-01 (the match clock's unit) of timestamps or dates."""
    return (pd.to_datetime(ts).to_numpy("datetime64[D]").astype("int64")).astype(float)


def qualifying_matches(stage0: Path = TREE_STAGE0) -> pd.DataFrame:
    """The study's qualifying population in a Stage 0: tour-level qualifying (Slams, 1000s, 500s, 250s), ATP and WTA,
    completed or retired, not flagged non-standard format, seasons FIRST_SEASON .. LAST_SEASON. No result is read."""
    cols = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "status", "nonstandard_format",
            "tournament_id", "tournament_name", "tournament_date", "player_a_id", "player_b_id", "best_of", "surface"]
    m = pd.read_parquet(stage0, columns=cols)
    keep = (m["qualifying"].astype(bool) & m["level"].isin(QUAL_LEVELS) & m["tour"].isin(["atp", "wta"])
            & m["status"].isin(["completed", "retired"]) & ~m["nonstandard_format"].fillna(False).astype(bool)
            & m["year"].between(FIRST_SEASON, LAST_SEASON))
    m = m[keep].copy()
    m["match_id"] = m["match_id"].astype(str)
    m["kind"] = np.where(m["level"].eq("GS"), "GSQ", "TQ")
    return m.reset_index(drop=True)
