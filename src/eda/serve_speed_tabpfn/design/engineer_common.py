"""Serve-speed TabPFN study, design round 1 (speed-data engineer): shared paths and loaders for the scratch scripts.

Reads no match result: Stage 0 is always read with an explicit column list that never names a_won, score, status
detail or any box-score column. The model frame is read without a_won and p_mkt.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design"
S0_NEW = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
REBUILD = ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z"
S0_PRE = REBUILD / "replaced" / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
ID_MAP = REBUILD / "id_map.csv"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
TIMING_PRE = REBUILD / "replaced" / "data" / "studies" / "match_timing" / "timing.parquet"
SHOT = ROOT / "data" / "studies" / "shot_level"
SPEEDS = ROOT / "data" / "studies" / "serve_speed_acquisition" / "speeds.parquet"
MODEL_FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
INFO_SLAMS = ROOT / "data" / "dump" / "points" / "infosys_slams"
AO_STATS = ROOT / "data" / "dump" / "points" / "ausopen" / "set_statistics.parquet"
HANDOFF = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
RECORDS = OUT / "engineer_records.parquet"

POINT_SOURCES = ["slam_pbp", "slam_tracking", "slamtracker", "infosys", "sirgenkii"]
TOUR_LEVELS = ("T250", "T500", "T1000", "FIN")
T0 = time.time()

# Stage 0 columns that are safe to read (no result, no score, no box score)
S0_COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "surface", "indoor",
           "tournament_id", "tournament_name", "tournament_date", "player_a_id", "player_b_id", "order"]


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def stage0(path: Path = S0_NEW, cols: list[str] | None = None) -> pd.DataFrame:
    cols = cols or S0_COLS
    assert not set(cols) & {"a_won", "score", "status_detail", "minutes"}, "never read a result column"
    return pd.read_parquet(path, columns=cols)


def id_map() -> dict:
    m = pd.read_csv(ID_MAP, usecols=["old_match_id", "new_match_id"])
    return dict(zip(m["old_match_id"], m["new_match_id"]))


def slam_of(level: pd.Series, name: pd.Series) -> pd.Series:
    n = name.fillna("").str.lower()
    out = np.select([n.str.contains("austral"), n.str.contains("roland|french"), n.str.contains("wimbledon"),
                     n.str.contains("us open|u.s. open")], ["AO", "RG", "W", "USO"], "")
    return pd.Series(np.where(level.eq("GS").to_numpy(), out, ""), index=level.index)


def level_group(level: pd.Series, qualifying: pd.Series) -> pd.Series:
    q = qualifying.astype(bool)
    return pd.Series(np.select(
        [level.eq("GS") & ~q, level.eq("GS") & q, level.isin(TOUR_LEVELS) & ~q, level.isin(TOUR_LEVELS) & q,
         level.eq("CH") & ~q, level.eq("CH") & q, level.eq("TEAM"), level.eq("ITF")],
        ["slam_main", "slam_qual", "tour_main", "tour_qual", "ch_main", "ch_qual", "team", "itf"], "other"),
        index=level.index)


def player_rows(path: Path = S0_NEW, years: tuple[int, int] = (2009, 2026)) -> pd.DataFrame:
    """Every Stage 0 player-match (two rows per match) with the own-history keys and the match clock (es, lf, obs)."""
    m = stage0(path)
    m = m[m["year"].between(*years)]
    rows = pd.concat([m.assign(side="A", player_id=m["player_a_id"], opp_id=m["player_b_id"]),
                      m.assign(side="B", player_id=m["player_b_id"], opp_id=m["player_a_id"])],
                     ignore_index=True).drop(columns=["player_a_id", "player_b_id"])
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs", "exact", "width_days"])
    rows = rows.merge(tm, on="match_id", how="left")
    rows["tdate"] = rows["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    rows["slam"] = slam_of(rows["level"], rows["tournament_name"]).to_numpy()
    rows["lgroup"] = level_group(rows["level"], rows["qualifying"]).to_numpy()
    return rows


def model_frame() -> pd.DataFrame:
    """The model frame's identifiers only (no a_won, no p_mkt, no inputs)."""
    return pd.read_parquet(MODEL_FRAME, columns=["match_id", "tour", "season", "tournament_date", "debut_season"])


def wmean(x: pd.Series, w: pd.Series) -> float:
    w = w.astype(float)
    return float((x * w).sum() / w.sum()) if w.sum() > 0 else float("nan")


def q(x, qs=(0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)) -> dict:
    x = pd.Series(x).dropna()
    return {f"p{int(k * 100)}": round(float(x.quantile(k)), 3) for k in qs} if len(x) else {}
