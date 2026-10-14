"""Design-phase scratch (agent 2, the Bayesian state modeller): a per-player-match first-serve speed panel from every
source on disk, for the variance decomposition, the state model and the result-free gates.

This is NOT the study's panel (the speed-data engineer owns that). It reads no match result: no `a_won`, `won`,
`sets_won`, `games_won`, score or winner column is ever loaded.

Sources (one row per player-match and source):
    pm   held point means, data/studies/shot_level/stage1_match_stats.parquet: spd1_n / spd1_d, and the within-match
         variance of single first serves in from spd1_sq_n (sources infosys, sirgenkii, slam_pbp, slam_tracking,
         slamtracker)
    ks   ManTennisData's key statistic (ATP Stats Centre "1st serve average"), integer km/h, with ks_first_in
    isl  the decrypted AO / RG Infosys point means of 2025-26 (spd1_mean, spd1_n)

Values outside 40-270 km/h are missing; men's values below 120 km/h are also treated as missing here (flagged).
Clock days are match_timing's `obs` (best-estimate day), `es`, `lf` (days since 1970-01-01).
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

from src.eda.predictability_diagnostic import common as PD  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design"
SHOT = ROOT / "data" / "studies" / "shot_level" / "stage1_match_stats.parquet"
SPEEDS = ROOT / "data" / "studies" / "serve_speed_acquisition" / "speeds.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
LO, HI, MEN_LO = 40.0, 270.0, 120.0
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def family_of(level: pd.Series, name: pd.Series) -> np.ndarray:
    """The point-sequence study's event families: AO, RG, W, USO at the Slams, 'tour' elsewhere."""
    n = name.fillna("").str.lower()
    out = np.where(n.str.contains("australian|aus open"), "AO",
                   np.where(n.str.contains("roland|french open"), "RG",
                            np.where(n.str.contains("wimbledon"), "W",
                                     np.where(n.str.contains("us open|u.s. open"), "USO", "tour"))))
    return np.where(level.eq("GS").to_numpy(), out, "tour")


def match_keys(match_ids: pd.Series | None = None) -> pd.DataFrame:
    """Stage 0 (rebuilt) keys of matches, with the clock days. No result column is read."""
    m = pd.read_parquet(PD.MATCHES, columns=["match_id", "tour", "year", "level", "qualifying", "round",
                                             "round_order", "surface", "indoor", "tournament_id", "tournament_name",
                                             "tournament_date", "player_a_id", "player_b_id", "order"])
    if match_ids is not None:
        m = m[m["match_id"].isin(set(match_ids))]
    t = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs"])
    m = m.merge(t, on="match_id", how="left")
    m["tdate"] = m["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    m["family"] = family_of(m["level"], m["tournament_name"])
    return m


def speed_obs() -> pd.DataFrame:
    """One row per (match_id, side) with any timed first serve, every source's value side by side."""
    st = pd.read_parquet(SHOT, columns=["match_id", "side", "spd1_n", "spd1_d", "spd1_sq_n", "spd1_src", "spd2_n",
                                        "spd2_d"])
    st = st[st["spd1_d"] > 0].copy()
    st["pm_mean"] = st["spd1_n"] / st["spd1_d"]
    st["pm_n"] = st["spd1_d"]
    st["pm_var"] = ((st["spd1_sq_n"] - st["spd1_n"] ** 2 / st["spd1_d"]) / (st["spd1_d"] - 1)).where(st["spd1_d"] > 1)
    st["pm_src"] = st["spd1_src"]
    st["pm2_mean"] = (st["spd2_n"] / st["spd2_d"]).where(st["spd2_d"] > 0)
    st = st[["match_id", "side", "pm_mean", "pm_n", "pm_var", "pm_src", "pm2_mean"]]

    sp = pd.read_parquet(SPEEDS, columns=["source", "match_id", "side", "event", "ks_spd1", "ks_first_in",
                                          "spd1_mean", "spd1_n"])
    sp = sp[sp["match_id"].notna()]
    ks = sp[sp["source"].eq("mantennisdata") & sp["ks_spd1"].notna()].copy()
    ks = ks.rename(columns={"ks_spd1": "ks_mean", "ks_first_in": "ks_n", "event": "ks_event"})
    ks = ks[["match_id", "side", "ks_mean", "ks_n", "ks_event"]].drop_duplicates(["match_id", "side"])
    isl = sp[sp["source"].eq("infosys_slams") & sp["spd1_mean"].notna()].copy()
    isl = isl.rename(columns={"spd1_mean": "isl_mean", "spd1_n": "isl_n"})
    isl = isl[["match_id", "side", "isl_mean", "isl_n"]].drop_duplicates(["match_id", "side"])

    o = st.merge(ks, on=["match_id", "side"], how="outer").merge(isl, on=["match_id", "side"], how="outer")
    return o


def panel(policy: str = "ks_first") -> pd.DataFrame:
    """The timed panel with keys, the clock and one chosen observation per player-match.

    policy  'ks_first': ATP tour-level / Challenger rows use ManTennisData's key statistic where present (one basis,
                         October 2021-2026), else the held point mean; Slams use point means (held, then the AO/RG files)
            'pm_first': the held point mean wherever present, else the key statistic, else the AO/RG files
    """
    o = speed_obs()
    k = match_keys(o["match_id"])
    o = o.merge(k, on="match_id", how="inner")
    o["player_id"] = np.where(o["side"].eq("A"), o["player_a_id"], o["player_b_id"])
    o = o.drop(columns=["player_a_id", "player_b_id"])
    for c in ("pm_mean", "ks_mean", "isl_mean"):
        v = o[c]
        bad = (v < LO) | (v > HI) | ((o["tour"] == "atp") & (v < MEN_LO))
        o.loc[bad, c] = np.nan
    has_pm, has_ks, has_isl = o["pm_mean"].notna(), o["ks_mean"].notna(), o["isl_mean"].notna()
    slam = o["level"].eq("GS")
    if policy == "ks_first":
        use_ks = has_ks & ~slam
        use_pm = ~use_ks & has_pm
    else:
        use_pm = has_pm
        use_ks = ~use_pm & has_ks
    use_isl = ~use_ks & ~use_pm & has_isl
    o["basis"] = np.select([use_pm, use_ks, use_isl], ["pm", "ks", "isl"], "none")
    o["y"] = np.select([use_pm, use_ks, use_isl], [o["pm_mean"], o["ks_mean"], o["isl_mean"]], np.nan)
    o["n"] = np.select([use_pm, use_ks, use_isl], [o["pm_n"], o["ks_n"], o["isl_n"]], np.nan)
    o = o[o["basis"].ne("none") & o["n"].gt(0)].copy()
    # the measuring system: event family at the Slams; at tour level, the basis (point mean of the Infosys points or
    # the Stats Centre key statistic) and Challengers apart
    sysname = np.where(o["family"].ne("tour"), o["family"],
                       np.where(o["basis"].eq("ks"), np.where(o["level"].eq("CH"), "ks_ch", "ks_tour"),
                                np.where(o["level"].eq("CH"), "pm_ch", "pm_tour")))
    o["system"] = sysname
    o = o.sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"], kind="mergesort")
    return o.reset_index(drop=True)


def box_rows(years: tuple[int, int]) -> pd.DataFrame:
    """Box-score serve counts per player-match (statistic targets for the mechanism gate; no result column)."""
    mp = pd.read_parquet(PD.MATCH_PLAYERS, columns=["match_id", "side", "player_id", "opponent_id", "has_box",
                                                    "ace_n", "ace_d", "first_in_n", "first_in_d", "first_won_n",
                                                    "first_won_d", "second_won_n", "second_won_d", "spw_n", "spw_d",
                                                    "df_n", "df_d", "height", "age"])
    k = pd.read_parquet(PD.MATCHES, columns=["match_id", "tour", "year", "level", "qualifying", "round_order",
                                             "surface", "tournament_id", "tournament_date"],
                        filters=[("year", ">=", years[0]), ("year", "<=", years[1])])
    mp = mp.merge(k, on="match_id", how="inner")
    mp["tdate"] = mp["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    return mp
