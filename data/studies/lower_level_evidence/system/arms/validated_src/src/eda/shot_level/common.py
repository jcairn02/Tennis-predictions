"""Shared helpers for the study "shot-level statistics" (src/eda/shot_level/).

The study asks whether statistics built from shot-level data (rally length, how points end, serve speed and
placement, net play, return depth, stroke mix, ball tracking) carry information that the closing odds and Elo do
not, and whether what is on disk is enough to tell. Every source is linked to the predictability diagnostic's
Stage 0 match table (data/studies/predictability_diagnostic/stage0_matches.parquet), so that features built later
use that study's players, chronological order and time rule, and are scored on the same pool with the same
harness (src/eda/ufc_ideas/common.py).

Linking reuses the data map's linker (src/eda/data_map/measure.py, ``Universe.link``): the same tour, the same pair
of surname keys, and a date within 10 days before to 21 days after the Stage 0 tournament date (40 days before for
Grand Slam qualifying), with fallbacks for married or shortened names and for a surname change within one round.
Here the universe is Stage 0 itself, every level from 2010, rather than the data map's own list from 2018.

The earlier studies' code and tables are read-only: imported, never edited.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.data_map import measure as M  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

OUT = ROOT / "data" / "studies" / "shot_level"
DOCS = ROOT / "docs" / "studies" / "shot_level"
DUMP = ROOT / "data" / "dump"
RAW = ROOT / "data" / "raw"
HANDOFF = RAW / "public_dump" / "atp_pipeline_handoff"
T0 = time.time()

# The kinds of shot-level information a source can carry, finest last. A source match "carries" a family when at
# least half of its points have the field (FAMILY_SHARE); match totals count for the families they total.
FAMILIES = {
    "rally": "Rally length: how many shots each point lasted",
    "ending": "How points end: winner, forced error or unforced error, and who hit it",
    "speed": "Serve speed",
    "placement": "Serve placement: wide, body or T",
    "net": "Net play: approaches and points won at the net",
    "return": "Return depth or returns put in play",
    "stroke": "Stroke mix: forehand, backhand, slice, volley, drop shot",
    "tracking": "Ball tracking of every stroke: positions, speeds, spin",
}
FAMILY_SHARE = 0.5

# What each source is; grain "shot" means every stroke is recorded, "point+" means points annotated with how they
# ended, rally length or serve detail, "totals" means match totals of shot-derived counts.
SOURCES = {
    "mcp": {"name": "Match Charting Project", "grain": "shot", "tours": "both", "data_map_id": "match_charting_project"},
    "infosys": {"name": "ATP Infosys Stats Centre (Hugging Face handoff)", "grain": "point+", "tours": "men",
                "data_map_id": "infosys"},
    "court_vision": {"name": "Hawk-Eye Court Vision, ATP (Hugging Face handoff)", "grain": "shot", "tours": "men",
                     "data_map_id": "court_vision"},
    "slam_pbp": {"name": "Sackmann's Grand Slam point-by-point (IBM and Infosys feeds)", "grain": "point+",
                 "tours": "both", "data_map_id": "slam_pbp_archive"},
    "slamtracker": {"name": "Wimbledon and US Open scoring feeds (IBM SlamTracker)", "grain": "point+", "tours": "both",
                    "data_map_id": "wimbledon_feeds, usopen_feeds"},
    "slam_tracking": {"name": "Hawk-Eye Court Vision at the Australian Open and Roland Garros (GitHub copy)",
                      "grain": "shot", "tours": "both", "data_map_id": "slam_ball_tracking"},
    "ausopen": {"name": "Australian Open match centre 2026", "grain": "point+", "tours": "both",
                "data_map_id": "ausopen_match_centre"},
    "tdi": {"name": "TDI Tennis Results (ATP)", "grain": "point+", "tours": "men", "data_map_id": "tdi"},
    "sirgenkii": {"name": "SirGenkii infotennis (ATP Stats Centre, Jan-Apr 2025)", "grain": "point+", "tours": "men",
                  "data_map_id": "sirgenkii_infotennis"},
    "wta_advanced": {"name": "WTA official API, advanced statistics", "grain": "totals", "tours": "women",
                     "data_map_id": "wta_api"},
}

TOUR_OF = {"atp": "M", "wta": "W"}
STAGE0_TOUR = {"M": "atp", "W": "wta"}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The Stage 0 universe and linking

def prepare(rows: pd.DataFrame) -> pd.DataFrame:
    """Rows (tour M/W, d, name1, name2[, round, level, draw]) made ready for ``M.Universe.link``: surname keys, the
    pair key, the canonical round and a row id. Like the data map's ``Universe._prepare`` but with no year cut, so
    sources from 2010 link too. Rows without two distinct surnames or a date are dropped."""
    rows = rows.copy()
    rows["d"] = pd.to_datetime(rows["d"], errors="coerce").astype("datetime64[ns]")
    rows["name1"] = rows["name1"].fillna("").astype(str)
    rows["name2"] = rows["name2"].fillna("").astype(str)
    rows["k1"], rows["k2"] = rows["name1"].map(M.surname_key), rows["name2"].map(M.surname_key)
    rows["pair"] = M.pair_key(rows["k1"], rows["k2"])
    rows["rnd"] = rows["round"].map(M.canon_round) if "round" in rows else None
    for col in ("level", "draw"):
        if col not in rows:
            rows[col] = None
    keep = rows["pair"].notna() & rows["d"].notna()
    rows = rows[keep].copy()
    rows["rid"] = np.arange(len(rows))
    return rows


def stage0_universe() -> pd.DataFrame:
    """Stage 0's matches as a linking universe: one row per match with uid (the row number), match_id, tour (M/W),
    d (tournament date), the A and B players' ids and names, level (the data map's codes), draw, round."""
    m = C.load_matches(["match_id", "tour", "year", "map_level", "qualifying", "round", "tournament_name",
                        "tournament_date", "player_a_id", "player_b_id"])
    names = C.load_match_players(["match_id", "player_id", "player_name"], with_order=False)
    names = names.drop_duplicates(["match_id", "player_id"]).set_index(["match_id", "player_id"])["player_name"]
    u = pd.DataFrame({
        "uid": np.arange(len(m)), "match_id": m["match_id"], "tour": m["tour"].map(TOUR_OF), "year": m["year"],
        "d": m["tournament_date"], "level": m["map_level"], "draw": np.where(m["qualifying"], "qual", "main"),
        "round": m["round"], "tname": m["tournament_name"], "id_a": m["player_a_id"], "id_b": m["player_b_id"],
        "name1": names.reindex(pd.MultiIndex.from_arrays([m["match_id"], m["player_a_id"]])).to_numpy(),
        "name2": names.reindex(pd.MultiIndex.from_arrays([m["match_id"], m["player_b_id"]])).to_numpy(),
        "creator": "stage0"})
    u = prepare(u)
    return u.drop(columns=["rid"]).reset_index(drop=True)


class Stage0Linker:
    """``M.Universe.link`` with Stage 0 as the universe."""

    def __init__(self, universe: pd.DataFrame | None = None):
        self.universe = stage0_universe() if universe is None else universe
        self._u = M.Universe(pd.Timestamp("2026-12-31"))
        self._u.matches = self.universe

    def link(self, rows: pd.DataFrame) -> pd.DataFrame:
        """Each source row (tour, d, name1, name2[, round, level, draw]) with the Stage 0 match it is (match_id,
        or missing), and which source player is Stage 0's side A: a1 = True when name1 is A, False when name2 is,
        missing when the names do not tell (orientation by surname key, then by the data map's loose test)."""
        prep = prepare(rows.assign(_src_index=rows.index))
        uid = self._u.link(prep)
        prep["uid"] = uid
        u = self.universe.set_index("uid")
        hit = prep["uid"].notna()
        ui = prep.loc[hit, "uid"].astype("int64")
        prep["match_id"] = None
        prep.loc[hit, "match_id"] = u.loc[ui, "match_id"].to_numpy()
        ka, kb = pd.Series(None, index=prep.index, dtype=object), pd.Series(None, index=prep.index, dtype=object)
        na, nb = ka.copy(), kb.copy()
        ka[hit], kb[hit] = u.loc[ui, "k1"].to_numpy(), u.loc[ui, "k2"].to_numpy()
        na[hit], nb[hit] = u.loc[ui, "name1"].to_numpy(), u.loc[ui, "name2"].to_numpy()
        prep["a1"] = [orient(k1, k2, n1, n2, a, b, xa, xb) if h else None
                      for k1, k2, n1, n2, a, b, xa, xb, h in zip(prep["k1"], prep["k2"], prep["name1"], prep["name2"],
                                                                  ka, kb, na, nb, hit)]
        out = rows.copy()
        back = prep.set_index("_src_index")
        out["match_id"] = back["match_id"].reindex(out.index)
        out["a1"] = back["a1"].reindex(out.index)
        return out


def orient(k1: str, k2: str, n1: str, n2: str, ka: str, kb: str, na: str, nb: str):
    """True when source player 1 is Stage 0's A, False when they are B, None when the names do not tell."""
    if k1 == ka and k2 == kb and k1 != k2:
        return True
    if k1 == kb and k2 == ka and k1 != k2:
        return False
    s1a, s1b = (k1 == ka) or M.same_player(n1, na), (k1 == kb) or M.same_player(n1, nb)
    s2a, s2b = (k2 == ka) or M.same_player(n2, na), (k2 == kb) or M.same_player(n2, nb)
    if (s1a or s2b) and not (s1b or s2a):
        return True
    if (s1b or s2a) and not (s1a or s2b):
        return False
    return None


# ------------------------------------------------------------------------------------------------
# The pool and the market

def pool() -> pd.DataFrame:
    """The ufc_ideas harness's pool (every evaluation-level match of 2010-2026 in the earlier study's Stage 4 table),
    with the closing-odds probability p_mkt where the main-tour match has odds."""
    from src.eda.ufc_ideas import common as U
    return U.load_pool()


def mde_milli(n: np.ndarray | float, z_crit: float = 1.96, z_power: float = 0.8416, inflation: float = 1.0):
    """The smallest gain in log loss (milli-log-loss) that a test on n matches detects with the stated power.

    A standardised feature x with true coefficient beta, added to a calibrated base forecast p, improves the
    expected log loss per match by G = beta^2 v / 2 nats, v = E[p (1 - p)], and the per-match improvement has
    standard deviation |beta| sqrt(v) to first order; so the test's z is |beta| sqrt(v n) / 2 and the gain it
    detects is G = 2 (z_crit + z_power)^2 / n nats, whatever v is. ``inflation`` multiplies the standard error
    (estimation noise in a walk-forward fit, clustering by week): the detectable gain scales with its square."""
    n = np.asarray(n, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(n > 0, 1000.0 * 2.0 * ((z_crit + z_power) * inflation) ** 2 / n, np.nan)
