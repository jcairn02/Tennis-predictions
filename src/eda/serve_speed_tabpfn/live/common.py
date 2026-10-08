"""The daily live speed pipeline (serve-speed TabPFN study): shared paths and helpers.

Decisions: docs/decisions/2026-10-07-speed-nudge.md (amended 8 Oct 2026: always the 28-day memory; "id love to get the
speed data daily") and docs/decisions/2026-10-08-scraping-approved.md (collection and decryption approved; clarified the
same day: the daily collector decrypts the CURRENT season's ATP Stats Centre files; the 2015-2021 backfill of session
tennis-predictions-74 stays encrypted). Reads no match result.

Layout:
    data/studies/serve_speed_tabpfn/live/staging/      staged per-match speeds, one file per source and collection day
    data/studies/serve_speed_tabpfn/live/linked.parquet the staged matches linked to project match and player ids
    data/studies/serve_speed_tabpfn/live/speed_panel_live.parquet   the frozen panel plus the new rows
    data/studies/serve_speed_tabpfn/live/speed_form_<date>.parquet  each ATP player's 28-day form as of that morning
    data/studies/serve_speed_tabpfn/live/collector.json  the ATP daily collector's switch (off until the lead enables it)
    data/studies/serve_speed_tabpfn/live/runs.jsonl      one line per runner run
The study's frozen files (speed_panel.parquet, frame_keys.parquet, offsets_snapshots.*) are never written here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STUDY = ROOT / "data" / "studies" / "serve_speed_tabpfn"
OUT = STUDY / "live"
STAGING = OUT / "staging"
LINKED = OUT / "linked.parquet"
PANEL_LIVE = OUT / "speed_panel_live.parquet"
COLLECTOR_CFG = OUT / "collector.json"
RUNS = OUT / "runs.jsonl"
FROZEN_PANEL = STUDY / "speed_panel.parquet"
LO, HI = 40.0, 270.0
EPOCH = pd.Timestamp("1970-01-01")


def day_of(x) -> int:
    """Days since 1970-01-01 of a date, timestamp or ISO string."""
    return int((pd.Timestamp(x).normalize() - EPOCH).days)


def date_of(day: int) -> str:
    return (EPOCH + pd.Timedelta(days=int(day))).strftime("%Y-%m-%d")


def form_path(day: int, out: Path = OUT) -> Path:
    return out / f"speed_form_{date_of(day)}.parquet"


def plaus(x) -> float:
    """A speed in km/h, or NaN outside (40, 270] (the project's rule)."""
    try:
        v = float(str(x).strip())
    except (TypeError, ValueError):
        return float("nan")
    return v if LO < v <= HI else float("nan")


def atp_code(x) -> str | None:
    """An ATP player code in one spelling: upper case, without the Infosys 'ATP' prefix ('ATPD643' -> 'D643')."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip().upper()
    if len(s) > 4 and s.startswith("ATP"):
        s = s[3:]
    return s or None


def read_json(path: Path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
