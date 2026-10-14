"""Serve-speed TabPFN study, R3 build: the per-player-match first-serve speed panel (C1), the as-of edition offsets
(C2) and the frame join (C4) of design/2_audit.md. Reads no match result.

C1  speed_panel.parquet: one row per rebuilt Stage 0 (match_id, side) that any held source times.
    Sources: point tables (stage1_points_<src>.parquet of slam_pbp, slam_tracking, slamtracker, infosys, sirgenkii;
    data/dump/points/infosys_slams/points.parquet), ManTennisData's and the handoff's ATP key statistics, and the AO
    match centre. Flashscore is not used. Added on 8 Oct 2026, after the study's frozen build (which they cannot
    change: speed_panel.parquet stays as run): the ATP Stats Centre's own decrypted files of 2018 to Oct 2021
    (data/dump/points/infosys_atp/), as MatchBeats point means (infosys_atp; a double fault is "P" or "DF" there) and
    key statistics (infosys_atp_ks, from serve_speed_acquisition/speeds.parquet). build_records(sources=...) builds
    any subset by the same code (docs/studies/infosys_atp_backfill/).
    Value per player-match, by tier (Slams = Stage 0 level GS, main draw or qualifying):
        Slams          point mean > key statistic > AO match centre
        other levels   key statistic > point mean > AO match centre
      point mean       first serves in (serve 1, not a double fault) timed in (40, 270] km/h; n = timed count; gate
                       n / first serves in >= 0.5; the source with the largest n wins, ties infosys_slams > infosys_atp >
                       sirgenkii > infosys > slam_tracking > slamtracker > slam_pbp
      key statistic    ManTennisData, else the handoff's copy, else the ATP files' own; y = KS - 0.5 (the statistic is
                       the ceiling of the point mean); n = first serves in from the box score
      AO match centre  y = MC + 0.5 (the published average is the floor of the point mean); n = first serves in
    A record that does not belong to its linked match is not a candidate, so the player-match takes its next valid
    record (checked in this order; the reason is kept on the record in speed_records.parquet):
        mislink_round  a ManTennisData row whose round label differs from the linked Stage 0 round (the QF rows that
                       speeds.py labelled as qualifying and that went to qualifying or R32 matches among them)
        mislink_level  a Slam-only feed linked to a non-Slam match, or an ATP-tour feed linked to a Slam match
        ks_duplicate / mc_duplicate   two records of one source for one player-match, more than 0.5 km/h apart
                       (after the round check, so a mislinked record does not void the match's own record)
        gate           a point mean with under half of its first serves in timed
    The chosen value is dropped (use = False, no fallback to another tier) when: no clock; men y < 120 or women y < 100
    (implausible); n < 10 (low_n). A player-match with records but no valid candidate keeps a row with use = False.
    No point-dependent cleaning is applied to key statistics. `draw` is never read from speeds.parquet: the draw is
    Stage 0's `qualifying`.
    edition = tournament_id | M or Q | basis (ks or pts; the AO match centre is pts); family = Slam name, tour (T250,
    T500, T1000, FIN), ch, or other (TEAM, ITF), | M or Q.
    Clock: es, lf from timing.parquet (whole days); obs floored to a whole day (half-day best estimates exist);
    rel = lf + 1, the first day the match surely exists.

C2  EditionOffsets(panel, tour).at(day): gamma (km/h) of every edition of the tour as of `day`, fitted on use rows
    with rel <= day and obs >= day - 364 (y = alpha_player + gamma_edition, weights 1 / (22 + 12.4^2 / n), each gamma
    shrunk to its family's weighted mean residual with a prior worth 25 player-matches, at most 60 iterations, stop at
    max |delta| < 1e-6, at least 50 rows else all 0; reference: the men's tour main-draw editions average 0 when they
    hold 200+ rows, else the Slam main draws). An edition without a released in-window row takes the unweighted mean of
    its family's in-window editions, else 0. Snapshots for the frame's es days are cached on disk, keyed to a
    fingerprint of the tour's use rows, so a changed panel (a probe) never reads them.

C4  frame_keys.parquet: one row per model-frame match (63,737). Sides are the frame's own pre-rebuild ids
    (feature_interactions.screen.PRE_REBUILD_STAGE0); the clock, tdate, tournament_id and round_order come from the
    rebuilt timing through id_map.csv. flipped: the rebuild swapped A and B (21); id_conflict: the rebuild's players
    differ (67) or are flipped (21), 88 in all.

Run: ./python.sh src/eda/serve_speed_tabpfn/panel.py   (about 30 s; the first run parses the handoff, about 50 s more)
Writes data/studies/serve_speed_tabpfn/: speed_panel.parquet, speed_records.parquet, frame_keys.parquet,
offsets_snapshots.parquet + offsets_snapshots.json, panel_summary.json, handoff_keystats.parquet (cache)
"""
from __future__ import annotations

import gzip
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

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn"
PANEL = OUT / "speed_panel.parquet"
FRAME_KEYS = OUT / "frame_keys.parquet"
RECORDS = OUT / "speed_records.parquet"
SUMMARY = OUT / "panel_summary.json"
SNAPSHOTS = OUT / "offsets_snapshots.parquet"
SNAPSHOTS_META = OUT / "offsets_snapshots.json"
HANDOFF_CACHE = OUT / "handoff_keystats.parquet"

S0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
ID_MAP = ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "id_map.csv"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
SHOT = ROOT / "data" / "studies" / "shot_level"
SPEEDS = ROOT / "data" / "studies" / "serve_speed_acquisition" / "speeds.parquet"
INFO_SLAMS_POINTS = ROOT / "data" / "dump" / "points" / "infosys_slams" / "points.parquet"
INFO_ATP_POINTS = ROOT / "data" / "dump" / "points" / "infosys_atp" / "points.parquet"
AO_STATS = ROOT / "data" / "dump" / "points" / "ausopen" / "set_statistics.parquet"
HANDOFF = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
MODEL_FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
N2_COUNTS = ROOT / "data" / "studies" / "serve_speed_acquisition" / "coverage_feature_by_year.csv"

# Explicit column lists: none names a match result (test T-P1)
S0_COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "surface", "indoor",
           "tournament_id", "tournament_name", "tournament_date", "player_a_id", "player_b_id"]
S0_PRE_COLS = ["match_id", "player_a_id", "player_b_id"]
TIMING_COLS = ["match_id", "es", "lf", "obs", "exact", "tournament_date", "tournament_id", "round_order"]
FRAME_COLS = ["match_id", "tour", "season"]
SPEEDS_COLS = ["source", "source_key", "player_no", "match_id", "side", "round", "year", "ks_spd1", "ks_spd2",
               "ks_max", "ks_first_in", "ks_first_total"]               # never `draw` (test T-P5)
LINK_COLS = ["source", "key", "match_id", "a1"]
POINT_COLS = ["key", "server", "serve_no", "end", "speed"]               # point-level: who served, serve number,
                                                                        # ending code (double faults), speed
INFO_SLAMS_COLS = ["slam", "year", "match_id", "server", "serve", "serveSpeed", "faultSrvSpd", "result"]
INFO_ATP_COLS = ["year", "event_id", "match_id", "server", "serve", "serveSpeed", "faultSrvSpd", "result"]
ATP_DOUBLE_FAULTS = ("P", "DF")                                       # the ATP MatchBeats files' double-fault codes
AO_STATS_COLS = ["record_key", "set", "stat", "team1_primary", "team1_secondary", "team2_primary", "team2_secondary"]
RESULT_COLUMNS = {"a_won", "won", "winner", "winner_id", "loser", "score", "sets", "games", "status_detail",
                  "minutes", "match_winner", "winner_team", "p_mkt"}

POINT_SOURCES = ["slam_pbp", "slam_tracking", "slamtracker", "infosys", "sirgenkii"]
PTS_PRIORITY = ["infosys_slams", "infosys_atp", "sirgenkii", "infosys", "slam_tracking", "slamtracker", "slam_pbp"]
KS_RANK = {"mantennisdata": 0, "handoff_ks": 1, "infosys_atp_ks": 2}
SLAM_ONLY = {"slam_pbp", "slam_tracking", "slamtracker", "infosys_slams", "ausopen_mc"}
TOUR_ONLY = {"infosys", "mantennisdata", "handoff_ks", "infosys_atp", "infosys_atp_ks"}
ALL_SOURCES = set(POINT_SOURCES) | {"infosys_slams", "infosys_atp", "mantennisdata", "handoff_ks", "infosys_atp_ks",
                                    "ausopen_mc"}
TOUR_LEVELS = ("T250", "T500", "T1000", "FIN")
LO, HI = 40.0, 270.0
KS_SHIFT, MC_SHIFT = -0.5, +0.5
MIN_N, MEN_MIN, WOMEN_MIN = 10, 120.0, 100.0
OUTLIER_KMH, OUTLIER_PREV, OUTLIER_MIN_PREV = 20.0, 10, 5
GATE = 0.5
DUP_TOL = 0.5

# C2 constants, frozen (from seasons <= 2023)
TAU2, S_SERVE, K_PRIOR, WINDOW, MIN_ROWS = 22.0, 12.4, 25.0, 364, 50
MAX_ITER, TOL, REF_MIN_ROWS = 60, 1e-6, 200
SLAM_MAIN = ("AO|M", "RG|M", "W|M", "USO|M")
TOUR_MAIN = "tour|M"

FIRST = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def plaus(x) -> np.ndarray:
    v = pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(dtype=float)
    return np.where((v > LO) & (v <= HI), v, np.nan)


def pre_rebuild_stage0() -> Path:
    from src.eda.feature_interactions import screen
    return Path(screen.PRE_REBUILD_STAGE0)


def id_map() -> dict:
    m = pd.read_csv(ID_MAP, usecols=["old_match_id", "new_match_id"])
    return dict(zip(m["old_match_id"], m["new_match_id"]))


def days(ts: pd.Series) -> np.ndarray:
    return pd.to_datetime(ts).to_numpy().astype("datetime64[D]").astype("int64")


def slam_of(level: pd.Series, name: pd.Series) -> np.ndarray:
    n = name.fillna("").str.lower()
    s = np.select([n.str.contains("austral"), n.str.contains("roland|french"), n.str.contains("wimbledon"),
                   n.str.contains("us open|u.s. open")], ["AO", "RG", "W", "USO"], "")
    return np.where(level.eq("GS").to_numpy(), s, "")


def family_of(level: pd.Series, slam: np.ndarray, qualifying: pd.Series) -> np.ndarray:
    """Slam name, 'tour' (T250, T500, T1000, FIN), 'ch' (CH) or 'other' (TEAM, ITF), then '|M' or '|Q'."""
    lv = level.reset_index(drop=True)
    base = pd.Series("other", index=lv.index, dtype=object)
    base[lv.isin(TOUR_LEVELS)] = "tour"
    base[lv.eq("CH")] = "ch"
    sl = pd.Series(slam, dtype=object)
    base[lv.eq("GS")] = np.where(sl[lv.eq("GS")].eq(""), "slam", sl[lv.eq("GS")])
    mq = np.where(qualifying.reset_index(drop=True).astype(bool), "|Q", "|M")
    return (base + mq).to_numpy(dtype=object)


# ------------------------------------------------------------------------------------------------
# C1: records per source
# ------------------------------------------------------------------------------------------------
def _point_records(name: str, links: pd.DataFrame) -> pd.DataFrame:
    """One source's point table oriented to Stage 0 sides, as shot_level.stage1_stats.oriented (the link copy with the
    most points per match), read with point-level columns only."""
    p = pd.read_parquet(SHOT / f"stage1_points_{name}.parquet", columns=POINT_COLS)
    lk = links[links["source"].eq(name) & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    sizes = p.groupby("key").size().rename("pts")
    lk = lk.join(sizes, on="key").sort_values("pts", ascending=False).drop_duplicates("match_id")
    p = p.merge(lk[["key", "match_id", "a1"]], on="key", how="inner")
    srv = p["server"].to_numpy()
    a1 = p["a1"].astype(bool).to_numpy()
    srv = np.where(srv == 0, 0, np.where(a1, srv, 3 - srv))
    p = p[np.isin(srv, [1, 2])]
    srv = srv[np.isin(srv, [1, 2])]
    from src.eda.shot_level.points import END
    sp = plaus(p["speed"])
    df = p["end"].to_numpy() == END["df"]
    sn = p["serve_no"].to_numpy()
    f1, f2 = (sn == 1) & ~df, (sn == 2) & ~df
    t1, t2 = f1 & np.isfinite(sp), f2 & np.isfinite(sp)
    g = pd.DataFrame({"match_id": p["match_id"].to_numpy(), "side": np.where(srv == 1, "A", "B"),
                      "key": p["key"].to_numpy(), "f1": f1, "n1": t1, "s1": np.where(t1, sp, 0.0),
                      "q1": np.where(t1, sp * sp, 0.0), "f2": f2, "n2": t2, "s2": np.where(t2, sp, 0.0),
                      "mx": np.where((f1 | f2) & np.isfinite(sp), sp, np.nan)})
    a = g.groupby(["match_id", "side"]).agg(source_key=("key", "first"), f1=("f1", "sum"), n1=("n1", "sum"),
                                            s1=("s1", "sum"), q1=("q1", "sum"), f2=("f2", "sum"), n2=("n2", "sum"),
                                            s2=("s2", "sum"), spd_max=("mx", "max")).reset_index()
    a["source"] = name
    return a


def _infosys_slams_records(sp_tab: pd.DataFrame) -> pd.DataFrame:
    p = pd.read_parquet(INFO_SLAMS_POINTS, columns=INFO_SLAMS_COLS)
    p = p[p["server"].astype(str).isin(["1", "2"])]
    spd, flt = plaus(p["serveSpeed"]), plaus(p["faultSrvSpd"])
    df = p["result"].astype(str).eq("DF").to_numpy()            # the point's ending code, not a match result
    sv = p["serve"].astype(str).to_numpy()
    f1, f2 = (sv == "1") & ~df, (sv == "2") & ~df
    t1, t2 = f1 & np.isfinite(spd), f2 & np.isfinite(spd)
    fl = (sv == "2") & np.isfinite(flt)
    g = pd.DataFrame({"source_key": p["slam"].astype(str) + "_" + p["year"].astype(str) + "_" + p["match_id"].astype(str),
                      "player_no": p["server"].astype(int).to_numpy(), "f1": f1, "n1": t1,
                      "s1": np.where(t1, spd, 0.0), "q1": np.where(t1, spd * spd, 0.0), "f2": f2, "n2": t2,
                      "s2": np.where(t2, spd, 0.0), "mx": np.where((f1 | f2) & np.isfinite(spd), spd, np.nan),
                      "fl": fl, "sf": np.where(fl, flt, 0.0)})
    a = g.groupby(["source_key", "player_no"]).agg(f1=("f1", "sum"), n1=("n1", "sum"), s1=("s1", "sum"),
                                                   q1=("q1", "sum"), f2=("f2", "sum"), n2=("n2", "sum"),
                                                   s2=("s2", "sum"), spd_max=("mx", "max"), nfault1=("fl", "sum"),
                                                   sf=("sf", "sum")).reset_index()
    a["fault1"] = a["sf"] / a["nfault1"].where(a["nfault1"] > 0)
    lk = sp_tab[sp_tab["source"].eq("infosys_slams")][["source_key", "player_no", "match_id", "side"]]
    a = a.merge(lk, on=["source_key", "player_no"], how="left").drop(columns=["sf", "player_no"])
    a["source"] = "infosys_slams"
    return a


def _infosys_atp_records(sp_tab: pd.DataFrame) -> pd.DataFrame:
    """The ATP's own decrypted MatchBeats points (2018 to Oct 2021), as _infosys_slams_records: these files end a double
    fault with "P" or "DF" (both are the point's ending code, not a match result). Linked through speeds.parquet."""
    p = pd.read_parquet(INFO_ATP_POINTS, columns=INFO_ATP_COLS)
    p = p[p["server"].astype(str).isin(["1", "2"])]
    spd, flt = plaus(p["serveSpeed"]), plaus(p["faultSrvSpd"])
    df = p["result"].astype(str).isin(ATP_DOUBLE_FAULTS).to_numpy()
    sv = p["serve"].astype(str).to_numpy()
    f1, f2 = (sv == "1") & ~df, (sv == "2") & ~df
    t1, t2 = f1 & np.isfinite(spd), f2 & np.isfinite(spd)
    fl = (sv == "2") & np.isfinite(flt)
    g = pd.DataFrame({"source_key": p["year"].astype(str) + "_" + p["event_id"].astype(str) + "_"
                      + p["match_id"].astype(str), "player_no": p["server"].astype(int).to_numpy(), "f1": f1, "n1": t1,
                      "s1": np.where(t1, spd, 0.0), "q1": np.where(t1, spd * spd, 0.0), "f2": f2, "n2": t2,
                      "s2": np.where(t2, spd, 0.0), "mx": np.where((f1 | f2) & np.isfinite(spd), spd, np.nan),
                      "fl": fl, "sf": np.where(fl, flt, 0.0)})
    a = g.groupby(["source_key", "player_no"]).agg(f1=("f1", "sum"), n1=("n1", "sum"), s1=("s1", "sum"),
                                                   q1=("q1", "sum"), f2=("f2", "sum"), n2=("n2", "sum"),
                                                   s2=("s2", "sum"), spd_max=("mx", "max"), nfault1=("fl", "sum"),
                                                   sf=("sf", "sum")).reset_index()
    a["fault1"] = a["sf"] / a["nfault1"].where(a["nfault1"] > 0)
    lk = sp_tab[sp_tab["source"].eq("infosys_atp")][["source_key", "player_no", "match_id", "side", "round"]]
    a = a.merge(lk, on=["source_key", "player_no"], how="left").drop(columns=["sf", "player_no"])
    a = a.rename(columns={"round": "round_src"})
    a["source"] = "infosys_atp"
    return a


def _infosys_atp_ks_records(sp_tab: pd.DataFrame) -> pd.DataFrame:
    """The ATP files' own key statistics (the same statistic as ManTennisData's and the handoff's)."""
    m = sp_tab[sp_tab["source"].eq("infosys_atp") & sp_tab["ks_spd1"].notna()]
    return pd.DataFrame({"source": "infosys_atp_ks", "source_key": m["source_key"], "match_id": m["match_id"],
                         "side": m["side"], "ks": m["ks_spd1"], "ks2": m["ks_spd2"], "spd_max": m["ks_max"],
                         "ks_first_in": m["ks_first_in"], "ks_first_total": m["ks_first_total"],
                         "round_src": m["round"]})


def _mantd_records(sp_tab: pd.DataFrame) -> pd.DataFrame:
    m = sp_tab[sp_tab["source"].eq("mantennisdata") & sp_tab["ks_spd1"].notna()]
    return pd.DataFrame({"source": "mantennisdata", "source_key": m["source_key"], "match_id": m["match_id"],
                         "side": m["side"], "ks": m["ks_spd1"], "ks2": m["ks_spd2"], "spd_max": m["ks_max"],
                         "ks_first_in": m["ks_first_in"], "ks_first_total": m["ks_first_total"],
                         "round_src": m["round"]})


def _handoff_file(path: str) -> list[tuple]:
    rows = []
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "Serve Average Speed" not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            ks = r.get("keystats") if isinstance(r.get("keystats"), dict) else {}
            s0 = ((ks.get("setStats") or {}).get("set0")) or []
            d = {e.get("name"): (e.get("player1"), e.get("player2")) for e in s0 if isinstance(e, dict)}
            if "1st Serve Average Speed" not in d:
                continue
            for no in (0, 1):
                fs = FIRST.match(str((d.get("1st Serve") or (None, None))[no] or ""))
                rows.append((str(r.get("year")), str(r.get("tournament_id")), str(r.get("match_id")).upper(), no + 1,
                             (d.get("1st Serve Average Speed") or (None, None))[no],
                             (d.get("2nd Serve Average Speed") or (None, None))[no],
                             (d.get("Max Speed") or (None, None))[no],
                             int(fs.group(1)) if fs else np.nan, int(fs.group(2)) if fs else np.nan))
    return rows


def handoff_keystats() -> pd.DataFrame:
    """The handoff's decrypted ATP key statistics (match level, "set0"), one row per record and player; cached."""
    if HANDOFF_CACHE.exists():
        return pd.read_parquet(HANDOFF_CACHE)
    import multiprocessing as mp
    files = sorted(str(p) for d in ("infosys_deep", "infosys_full") for p in (HANDOFF / d).glob("*_data.jsonl*"))
    with mp.Pool(min(6, len(files))) as pool:
        parts = pool.map(_handoff_file, files, chunksize=1)
    h = pd.DataFrame([r for p in parts for r in p], columns=["k_year", "k_tid", "k_code", "player_no", "v1", "v2",
                                                             "vmax", "first_in", "first_total"])
    for c in ("v1", "v2", "vmax"):
        h[c] = plaus(h[c])
    # the two folders overlap: one copy per match and player, preferring one with a speed
    h = h.sort_values(["k_year", "k_tid", "k_code", "player_no", "v1"], na_position="last")
    h = h.drop_duplicates(["k_year", "k_tid", "k_code", "player_no"]).reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    h.to_parquet(HANDOFF_CACHE, index=False)
    return h


def _side_of(a1: pd.Series, player_no: pd.Series) -> np.ndarray:
    t = a1.eq(True).fillna(False).to_numpy(dtype=bool)
    f = a1.eq(False).fillna(False).to_numpy(dtype=bool)
    one = (player_no.astype(int) == 1).to_numpy(dtype=bool)
    return np.select([(t & one) | (f & ~one), (t & ~one) | (f & one)], ["A", "B"], default=None)


def _handoff_records(links: pd.DataFrame) -> pd.DataFrame:
    h = handoff_keystats()
    h = h[h["v1"].notna()].copy()
    h["source_key"] = h["k_year"] + "_" + h["k_tid"] + "_" + h["k_code"]
    lk = links[links["source"].eq("infosys") & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    h = h.merge(lk.drop_duplicates("key").rename(columns={"key": "source_key"}), on="source_key", how="left")
    return pd.DataFrame({"source": "handoff_ks", "source_key": h["source_key"], "match_id": h["match_id"],
                         "side": _side_of(h["a1"], h["player_no"]), "ks": h["v1"], "ks2": h["v2"],
                         "spd_max": h["vmax"], "ks_first_in": h["first_in"], "ks_first_total": h["first_total"]})


def _ausopen_records(links: pd.DataFrame) -> pd.DataFrame:
    a = pd.read_parquet(AO_STATS, columns=AO_STATS_COLS)
    a = a[a["set"].eq("All") & a["stat"].isin(["1st Serve Average", "2nd serve average", "Fastest serve",
                                                "1st serve in"])].drop_duplicates(["record_key", "stat"])
    rows = []
    for no in (1, 2):
        w = a.pivot_table(index="record_key", columns="stat", values=f"team{no}_primary", aggfunc="first")
        sec = a[a["stat"].eq("1st serve in")].set_index("record_key")[f"team{no}_secondary"]
        fs = sec.astype(str).str.extract(FIRST)
        w = w.assign(player_no=no, first_in=pd.to_numeric(fs[0], errors="coerce").reindex(w.index),
                     first_total=pd.to_numeric(fs[1], errors="coerce").reindex(w.index))
        rows.append(w.reset_index())
    w = pd.concat(rows, ignore_index=True)
    lk = links[links["source"].eq("ausopen") & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    w = w.merge(lk.drop_duplicates("key").rename(columns={"key": "record_key"}), on="record_key", how="left")
    return pd.DataFrame({"source": "ausopen_mc", "source_key": w["record_key"], "match_id": w["match_id"],
                         "side": _side_of(w["a1"], w["player_no"]), "mc": plaus(w.get("1st Serve Average")),
                         "mc2": plaus(w.get("2nd serve average")), "spd_max": plaus(w.get("Fastest serve")),
                         "f1": w["first_in"], "n1": w["first_in"]})


def _read_speeds() -> pd.DataFrame:
    """speeds.parquet with SPEEDS_COLS only: the draw is never read (the panel takes it from Stage 0)."""
    return pd.read_parquet(SPEEDS, columns=SPEEDS_COLS)


def build_records(sources: set[str] | None = None) -> pd.DataFrame:
    """Every timed record of every source (or of `sources` only: ALL_SOURCES' names), linked to the rebuilt Stage 0,
    harmonised, with its validity. Every validity rule reads one record or one source's records, so a subset gets the
    validity it has in the full build."""
    want = ALL_SOURCES if sources is None else set(sources)
    unknown = want - ALL_SOURCES
    if unknown:
        raise ValueError(f"unknown sources {sorted(unknown)}")
    links = pd.read_parquet(SHOT / "stage0_source_matches.parquet", columns=LINK_COLS)
    sp_tab = _read_speeds()
    parts = []
    for name in POINT_SOURCES:
        if name in want:
            parts.append(_point_records(name, links))
    if "infosys_slams" in want:
        parts.append(_infosys_slams_records(sp_tab))
    if "infosys_atp" in want:
        parts.append(_infosys_atp_records(sp_tab))
    pts = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["source", "s1", "n1", "s2", "n2",
                                                                                  "q1", "f1"])
    pts["kind"], pts["basis"] = "point_mean", "pts"
    pts["y_raw"] = pts["s1"] / pts["n1"].where(pts["n1"] > 0)
    pts["y"] = pts["y_raw"]
    pts["n"] = pts["n1"]
    pts["spd2_raw"] = pts["s2"] / pts["n2"].where(pts["n2"] > 0)
    pts["spd2"] = pts["spd2_raw"]
    pts["sd_within"] = np.sqrt(np.maximum(pts["q1"] / pts["n1"].where(pts["n1"] > 0) - pts["y_raw"] ** 2, 0.0))
    pts["timed_share"] = pts["n1"] / pts["f1"].where(pts["f1"] > 0)
    pts["gate"] = pts["timed_share"] >= GATE
    kparts = []
    if "mantennisdata" in want:
        kparts.append(_mantd_records(sp_tab))
    if "handoff_ks" in want:
        kparts.append(_handoff_records(links))
    if "infosys_atp_ks" in want:
        kparts.append(_infosys_atp_ks_records(sp_tab))
    ks = pd.concat(kparts, ignore_index=True) if kparts else pd.DataFrame(columns=["ks", "ks2", "ks_first_in",
                                                                                   "ks_first_total"])
    ks["kind"], ks["basis"] = "keystat", "ks"
    ks["y_raw"], ks["y"] = ks["ks"], ks["ks"] + KS_SHIFT
    ks["n"], ks["f1"] = ks["ks_first_in"], ks["ks_first_in"]
    ks["spd2_raw"], ks["spd2"] = ks["ks2"], ks["ks2"] + KS_SHIFT
    ks["n2"] = ks["ks_first_total"] - ks["ks_first_in"]
    ks["gate"] = True
    mc = _ausopen_records(links) if "ausopen_mc" in want else pd.DataFrame(columns=["mc", "mc2", "n1"])
    mc = mc[mc["mc"].notna()]
    mc["kind"], mc["basis"] = "mc_floor", "pts"
    mc["y_raw"], mc["y"] = mc["mc"], mc["mc"] + MC_SHIFT
    mc["n"] = mc["n1"]
    mc["spd2_raw"], mc["spd2"] = mc["mc2"], mc["mc2"] + MC_SHIFT
    mc["gate"] = True
    keep = ["source", "kind", "basis", "source_key", "match_id", "side", "y_raw", "y", "n", "f1", "n1", "timed_share",
            "gate", "sd_within", "spd2_raw", "spd2", "n2", "spd_max", "fault1", "nfault1", "ks_first_in",
            "ks_first_total", "round_src"]
    rec = pd.concat([pts.reindex(columns=keep), ks.reindex(columns=keep), mc.reindex(columns=keep)], ignore_index=True)
    rec = rec[rec["y_raw"].notna()].copy()           # timed records only
    # the shot-level links point at the pre-rebuild Stage 0: move the 42 re-keyed ids
    remap = id_map()
    old = rec["source"].isin(POINT_SOURCES + ["handoff_ks", "ausopen_mc"])
    rec.loc[old, "match_id"] = rec.loc[old, "match_id"].map(lambda x: remap.get(x, x) if isinstance(x, str) else x)
    rec["linked"] = rec["match_id"].notna() & rec["side"].notna()
    m = pd.read_parquet(S0, columns=["match_id", "tour", "year", "level", "round"])
    rec = rec.merge(m.rename(columns={"round": "round_s0"}), on="match_id", how="left")
    rec["linked"] &= rec["tour"].notna()
    # validity of each record as a candidate for its linked player-match
    reason = pd.Series("", index=rec.index, dtype=object)
    reason[~rec["linked"]] = "unlinked"
    reason[(reason == "") & rec["kind"].eq("point_mean") & ~rec["gate"].astype(bool)] = "gate"
    rmis = rec["source"].isin(["mantennisdata", "infosys_atp", "infosys_atp_ks"]) & rec["round_src"].notna() \
        & (rec["round_src"] != rec["round_s0"])
    reason[(reason == "") & rmis] = "mislink_round"
    slam_only = rec["source"].isin(SLAM_ONLY) & rec["level"].ne("GS")
    tour_only = rec["source"].isin(TOUR_ONLY) & rec["level"].eq("GS")
    reason[(reason == "") & (slam_only | tour_only)] = "mislink_level"
    for src, why in (("mantennisdata", "ks_duplicate"), ("handoff_ks", "ks_duplicate"),
                     ("infosys_atp_ks", "ks_duplicate"), ("ausopen_mc", "mc_duplicate")):
        ok = rec["source"].eq(src) & (reason == "")
        g = rec[ok].groupby(["match_id", "side"])["y"]
        spread = g.transform("max") - g.transform("min")
        size = g.transform("size")
        conflict = (size > 1) & (spread > DUP_TOL)
        reason[conflict[conflict].index] = why
        # duplicates within the tolerance: keep the first copy only
        dup = rec[ok & (reason == "")].duplicated(["match_id", "side"], keep="first")
        reason[dup[dup].index] = "duplicate_copy"
    rec["invalid_reason"] = reason
    rec["valid"] = reason.eq("")
    for c in ("n", "f1", "n1", "n2", "nfault1"):
        rec[c] = pd.to_numeric(rec[c], errors="coerce")
    return rec.rename(columns={"tour": "tour_s0", "year": "year_s0", "level": "level_s0"})


# ------------------------------------------------------------------------------------------------
# C1: the panel
# ------------------------------------------------------------------------------------------------
def choose(rec: pd.DataFrame, s0: pd.DataFrame) -> pd.DataFrame:
    """One row per linked (match_id, side) with any timed record: the chosen valid candidate by tier."""
    r = rec[rec["linked"]].merge(s0[["match_id", "level"]], on="match_id", how="left")
    slam = r["level"].eq("GS").to_numpy()
    kind_rank = np.select([r["kind"].eq("point_mean"), r["kind"].eq("keystat"), r["kind"].eq("mc_floor")],
                          [np.where(slam, 0, 1), np.where(slam, 1, 0), 2], 9)
    src_rank = r["source"].map({**{s: i for i, s in enumerate(PTS_PRIORITY)}, **KS_RANK,
                                "ausopen_mc": 0}).fillna(9).to_numpy()
    r = r.assign(_valid=(~r["valid"]).astype(int), _kind=kind_rank, _n=-r["n"].fillna(0).to_numpy(), _src=src_rank)
    # point means: the largest n wins within the tier; key statistics: ManTennisData before the handoff
    r["_n"] = np.where(r["kind"].eq("point_mean"), r["_n"], 0)
    r = r.sort_values(["match_id", "side", "_valid", "_kind", "_n", "_src"])
    alt = r[r["valid"]].groupby(["match_id", "side"])["source"].agg(lambda x: "+".join(sorted(set(x))))
    best = r.drop_duplicates(["match_id", "side"]).copy()
    # alternatives: the other valid candidates' harmonised values
    vals = r[r["valid"]][["match_id", "side", "source", "kind", "y", "n"]]
    pv = vals[vals["kind"].eq("point_mean")].drop_duplicates(["match_id", "side"]).set_index(["match_id", "side"])
    kv = vals[vals["kind"].eq("keystat")].drop_duplicates(["match_id", "side"]).set_index(["match_id", "side"])
    key = pd.MultiIndex.from_frame(best[["match_id", "side"]])
    best["spd1_pts"] = pv["y"].reindex(key).to_numpy()
    best["n_pts"] = pv["n"].reindex(key).to_numpy()
    best["spd1_ks"] = kv["y"].reindex(key).to_numpy()
    best["n_ks"] = kv["n"].reindex(key).to_numpy()
    best["alt_sources"] = alt.reindex(key).fillna("").to_numpy()
    best["n_sources"] = np.where(best["alt_sources"].eq(""), 0, best["alt_sources"].str.count(r"\+") + 1)
    span = vals.groupby(["match_id", "side"])["y"].agg(lambda x: float(x.max() - x.min()) if len(x) > 1 else 0.0)
    best["max_alt_diff"] = span.reindex(key).to_numpy()
    best["drop_reason"] = np.where(best["valid"], "", best["invalid_reason"])
    return best.drop(columns=["_valid", "_kind", "_n", "_src", "level"])


def own_outlier_flag(p: pd.DataFrame) -> np.ndarray:
    """|y - median of the player's previous <= 10 use rows (own order)| > 20 km/h, with at least 5 previous rows."""
    q = p[p["use"]].sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"])
    prev = (q.groupby(["tour", "player_id"])["y"]
            .transform(lambda s: s.shift(1).rolling(OUTLIER_PREV, min_periods=OUTLIER_MIN_PREV).median()))
    flag = pd.Series(False, index=p.index)
    flag[q.index] = (q["y"] - prev).abs() > OUTLIER_KMH
    return flag.to_numpy()


def build_panel(rec: pd.DataFrame) -> pd.DataFrame:
    s0 = pd.read_parquet(S0, columns=S0_COLS)
    best = choose(rec, s0)
    p = best.merge(s0, on="match_id", how="left", validate="many_to_one")
    p["player_id"] = np.where(p["side"].eq("A"), p["player_a_id"], p["player_b_id"])
    p["opp_id"] = np.where(p["side"].eq("A"), p["player_b_id"], p["player_a_id"])
    p = p.drop(columns=["player_a_id", "player_b_id"])
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs", "exact"])
    p = p.merge(tm, on="match_id", how="left", validate="many_to_one")
    p["obs_raw"] = p["obs"]
    no_clock = p[["es", "lf", "obs"]].isna().any(axis=1)
    for c in ("es", "lf"):
        p[c] = p[c].fillna(-1).astype("int64")
    p["obs"] = np.floor(p["obs"].fillna(-1)).astype("int64")
    p["rel"] = p["lf"] + 1
    p["tdate"] = days(p["tournament_date"])
    p["slam"] = slam_of(p["level"], p["tournament_name"])
    p["family"] = family_of(p["level"], p["slam"], p["qualifying"])
    p["mq"] = np.where(p["qualifying"].astype(bool), "Q", "M")
    p["event"] = np.where(p["slam"] != "", p["slam"], p["tournament_id"].str.split("-", n=1).str[1])
    q_ = p["qualifying"].astype(bool)
    p["lgroup"] = np.select([p["level"].eq("GS") & ~q_, p["level"].eq("GS") & q_, p["level"].isin(TOUR_LEVELS) & ~q_,
                             p["level"].isin(TOUR_LEVELS) & q_, p["level"].eq("CH") & ~q_, p["level"].eq("CH") & q_,
                             p["level"].eq("TEAM"), p["level"].eq("ITF")],
                            ["slam_main", "slam_qual", "tour_main", "tour_qual", "ch_main", "ch_qual", "team", "itf"],
                            "other").astype(object)
    p["edition"] = p["tournament_id"] + "|" + p["mq"] + "|" + p["basis"]
    p["n"] = p["n"].fillna(0).round().astype("int64")
    # value-level drops of the chosen value (no fallback to another tier)
    reason = p["drop_reason"].astype(object).copy()
    reason[(reason == "") & no_clock.to_numpy()] = "no_clock"
    low = np.where(p["tour"].eq("atp"), p["y"] < MEN_MIN, p["y"] < WOMEN_MIN)
    reason[(reason == "") & low] = "implausible"
    reason[(reason == "") & (p["n"] < MIN_N)] = "low_n"
    p["drop_reason"] = reason
    p["use"] = reason.eq("")
    p["flag_own_outlier"] = own_outlier_flag(p)
    cols = ["match_id", "side", "player_id", "opp_id", "tour", "year", "level", "qualifying", "mq", "lgroup", "round",
            "round_order", "tournament_id", "tournament_name", "tournament_date", "tdate", "surface", "indoor", "slam", "event",
            "family", "edition", "es", "lf", "obs", "obs_raw", "rel", "exact", "source", "source_key", "basis", "kind", "y",
            "y_raw",
            "n", "f1", "timed_share", "sd_within", "spd1_pts", "n_pts", "spd1_ks", "n_ks", "spd2", "spd2_raw", "n2",
            "spd_max", "fault1", "nfault1", "alt_sources", "n_sources", "max_alt_diff", "use", "drop_reason",
            "flag_own_outlier"]
    p = p[cols].sort_values(["tour", "tdate", "round_order", "match_id", "side"]).reset_index(drop=True)
    assert not p.duplicated(["match_id", "side"]).any()
    assert not (set(p.columns) & RESULT_COLUMNS)
    return p


def load_panel(use_only: bool = True) -> pd.DataFrame:
    p = pd.read_parquet(PANEL)
    return p[p["use"]].reset_index(drop=True) if use_only else p


# ------------------------------------------------------------------------------------------------
# C2: as-of edition offsets
# ------------------------------------------------------------------------------------------------
def _fingerprint(q: pd.DataFrame) -> str:
    cols = ["match_id", "side", "player_id", "edition", "family", "y", "n", "lf", "obs"]
    q = q[cols].sort_values(["match_id", "side"])
    h = pd.util.hash_pandas_object(q, index=False).to_numpy()
    return hashlib.sha256(h.tobytes()).hexdigest()


class EditionOffsets:
    """gamma (km/h) of every edition of one tour as of a day, from the use rows released by then (lf + 1 <= day) within
    364 days (obs >= day - 364). See the module docstring (C2)."""

    def __init__(self, panel: pd.DataFrame, tour: str, cache: bool = True, release: str = "rel"):
        q = panel[panel["tour"].eq(tour) & panel["use"].astype(bool)].reset_index(drop=True)
        self.tour = tour
        self.editions = pd.Index(np.unique(q["edition"].to_numpy().astype(str)))
        ed_fam = q.drop_duplicates("edition").set_index("edition")["family"]
        self.ed_family = ed_fam.reindex(self.editions).to_numpy().astype(str)
        self.families = pd.Index(np.unique(self.ed_family))
        self.fam_of_ed = self.families.get_indexer(self.ed_family)
        # the release column: "rel" (lf + 1) is the build; any other column exists only for a leaky-control test
        rel = (q["lf"].to_numpy(np.int64) + 1) if release == "rel" else q[release].to_numpy(np.int64)
        self.rel = rel
        self.obs = q["obs"].to_numpy(np.int64)
        self.y = q["y"].to_numpy(float)
        n = np.maximum(q["n"].to_numpy(float), 1.0)
        self.w = 1.0 / (TAU2 + S_SERVE ** 2 / n)
        self.pid = pd.factorize(q["player_id"])[0]
        self.ed = self.editions.get_indexer(q["edition"].astype(str))
        tour_main = self.families.get_loc(TOUR_MAIN) if TOUR_MAIN in self.families else -1
        self.is_tour_main = self.fam_of_ed == tour_main
        slam_main = [self.families.get_loc(f) for f in SLAM_MAIN if f in self.families]
        self.is_slam_main = np.isin(self.fam_of_ed, slam_main)
        self._mem: dict[int, pd.Series] = {}
        self._disk = None
        self.fingerprint = _fingerprint(q) if release == "rel" else None
        if cache and release == "rel":
            self._load_disk()

    def _load_disk(self) -> None:
        if not (SNAPSHOTS.exists() and SNAPSHOTS_META.exists()):
            return
        meta = json.loads(SNAPSHOTS_META.read_text(encoding="utf-8"))
        if meta.get(self.tour, {}).get("fingerprint") != self.fingerprint:
            return
        t = pd.read_parquet(SNAPSHOTS, filters=[("tour", "==", self.tour)])
        self._disk = {int(d): g for d, g in t.groupby("day")}

    def _assemble(self, fit_eds: np.ndarray, fit_g: np.ndarray, fam_idx: np.ndarray, fam_mean: np.ndarray) -> pd.Series:
        fm = np.zeros(len(self.families))
        fm[fam_idx] = fam_mean
        has = np.zeros(len(self.families), bool)
        has[fam_idx] = True
        g = np.where(has[self.fam_of_ed], fm[self.fam_of_ed], 0.0)
        g[fit_eds] = fit_g
        return pd.Series(g, index=self.editions, name=f"gamma_{self.tour}")

    def fit(self, day: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """The snapshot at `day`: (edition indices fitted, their gamma, their released rows, family indices with an
        in-window edition, the families' unweighted mean gamma)."""
        m = (self.rel <= day) & (self.obs >= day - WINDOW)
        empty = (np.array([], int), np.array([]), np.array([], int), np.array([], int), np.array([]))
        if m.sum() < MIN_ROWS:
            return empty
        y, w = self.y[m], self.w[m]
        pu, pi = np.unique(self.pid[m], return_inverse=True)
        eu, ei = np.unique(self.ed[m], return_inverse=True)
        fu, fi = np.unique(self.fam_of_ed[eu], return_inverse=True)
        wp = np.bincount(pi, weights=w)
        we = np.bincount(ei, weights=w)
        wf = np.bincount(fi, weights=we)
        kw = K_PRIOR * float(np.mean(w))
        g = np.zeros(len(eu))
        for _ in range(MAX_ITER):
            a = np.bincount(pi, weights=w * (y - g[ei])) / wp
            r = np.bincount(ei, weights=w * (y - a[pi]))
            fam_mean_resid = np.bincount(fi, weights=r) / wf
            g_new = (r + kw * fam_mean_resid[fi]) / (we + kw)
            delta = np.max(np.abs(g_new - g))
            g = g_new
            if delta < TOL:
                break
        n_e = np.bincount(ei)
        ref = self.is_tour_main[eu]
        if n_e[ref].sum() < REF_MIN_ROWS:
            ref = self.is_slam_main[eu]
        if ref.any():
            g = g - np.average(g[ref], weights=n_e[ref])
        fam_mean = np.bincount(fi, weights=g) / np.bincount(fi)
        return eu, g, n_e, fu, fam_mean

    def at(self, day: int) -> pd.Series:
        day = int(day)
        if day in self._mem:
            return self._mem[day]
        if self._disk is not None and day in self._disk:
            t = self._disk[day]
            fit = t[t["kind"].eq("fit")]
            fam = t[t["kind"].eq("fam")]
            s = self._assemble(self.editions.get_indexer(fit["key"]), fit["gamma"].to_numpy(),
                               self.families.get_indexer(fam["key"]), fam["gamma"].to_numpy())
        else:
            eu, g, _, fu, fm = self.fit(day)
            s = self._assemble(eu, g, fu, fm)
        self._mem[day] = s
        return s

    def gamma(self, editions: np.ndarray, day: int) -> np.ndarray:
        s = self.at(day)
        idx = self.editions.get_indexer(np.asarray(editions).astype(str))
        return np.where(idx >= 0, s.to_numpy()[np.maximum(idx, 0)], 0.0)


def build_snapshots(panel: pd.DataFrame, fk: pd.DataFrame) -> dict:
    """Fit and store the snapshots at every frame es day, per tour."""
    parts, meta = [], {"constants": {"tau2": TAU2, "s": S_SERVE, "K": K_PRIOR, "window": WINDOW, "min_rows": MIN_ROWS,
                                     "max_iter": MAX_ITER, "tol": TOL, "ref_min_rows": REF_MIN_ROWS}}
    for tour in ("atp", "wta"):
        eo = EditionOffsets(panel, tour, cache=False)
        day_list = np.unique(fk.loc[fk["tour"].eq(tour), "es"].to_numpy(np.int64))
        t0 = time.time()
        for d in day_list:
            eu, g, n_e, fu, fm = eo.fit(int(d))
            if len(eu):
                parts.append(pd.DataFrame({"tour": tour, "day": int(d), "kind": "fit", "key": eo.editions[eu],
                                           "gamma": g, "n_rel": n_e}))
                parts.append(pd.DataFrame({"tour": tour, "day": int(d), "kind": "fam", "key": eo.families[fu],
                                           "gamma": fm, "n_rel": 0}))
            else:
                parts.append(pd.DataFrame({"tour": [tour], "day": [int(d)], "kind": ["empty"], "key": [""],
                                           "gamma": [0.0], "n_rel": [0]}))
        meta[tour] = {"fingerprint": eo.fingerprint, "days": int(len(day_list)), "editions": int(len(eo.editions)),
                      "seconds": round(time.time() - t0, 1)}
        log(f"  snapshots {tour}: {len(day_list)} days in {meta[tour]['seconds']} s")
    t = pd.concat(parts, ignore_index=True)
    t["day"] = t["day"].astype("int64")
    t.to_parquet(SNAPSHOTS, index=False)
    SNAPSHOTS_META.write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    return meta


# ------------------------------------------------------------------------------------------------
# C4: the frame join
# ------------------------------------------------------------------------------------------------
def build_frame_keys() -> pd.DataFrame:
    f = pd.read_parquet(MODEL_FRAME, columns=FRAME_COLS)
    pre = pd.read_parquet(pre_rebuild_stage0(), columns=S0_PRE_COLS)
    f = f.merge(pre, on="match_id", how="left", validate="one_to_one")
    remap = id_map()
    f["rebuilt_id"] = f["match_id"].map(lambda x: remap.get(x, x))
    tm = pd.read_parquet(TIMING, columns=TIMING_COLS).rename(columns={"match_id": "rebuilt_id"})
    f = f.merge(tm, on="rebuilt_id", how="left", validate="one_to_one")
    new = pd.read_parquet(S0, columns=["match_id", "level", "player_a_id", "player_b_id"]).rename(
        columns={"match_id": "rebuilt_id", "player_a_id": "a_rebuilt", "player_b_id": "b_rebuilt"})
    f = f.merge(new, on="rebuilt_id", how="left", validate="one_to_one")
    same_set = (((f["player_a_id"] == f["a_rebuilt"]) & (f["player_b_id"] == f["b_rebuilt"]))
                | ((f["player_a_id"] == f["b_rebuilt"]) & (f["player_b_id"] == f["a_rebuilt"])))
    f["flipped"] = same_set & (f["player_a_id"] != f["a_rebuilt"])
    f["id_conflict"] = ~same_set | f["flipped"]
    f["obs_raw"] = f["obs"]
    f["es"], f["lf"] = f["es"].astype("int64"), f["lf"].astype("int64")
    f["obs"] = np.floor(f["obs"]).astype("int64")
    f["tdate"] = days(f["tournament_date"])
    cols = ["match_id", "rebuilt_id", "tour", "season", "player_a_id", "player_b_id", "es", "lf", "obs", "obs_raw",
            "tdate", "tournament_id", "round_order", "level", "id_conflict", "flipped", "a_rebuilt", "b_rebuilt"]
    f = f[cols]
    assert len(f) == f["match_id"].nunique()
    return f


def load_frame_keys() -> pd.DataFrame:
    return pd.read_parquet(FRAME_KEYS)


# ------------------------------------------------------------------------------------------------
# presence (x_raw's window rule) for the validation and the summary
# ------------------------------------------------------------------------------------------------
def presence(t: pd.DataFrame, panel: pd.DataFrame, short: int = 14, long: int = 364) -> tuple[np.ndarray, np.ndarray]:
    """For target sides t (tour, player_id, tdate, tournament_id, round_order, obs): whether the player has a use row
    that is his own earlier match (an earlier tdate, or the same tournament_id and an earlier round) with
    obs_t - obs_h <= short / long. The test is max obs over own earlier rows >= obs_t - window."""
    h = panel[panel["use"]][["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]]
    keys = pd.Index(pd.unique(pd.concat([h["tour"] + "|" + h["player_id"].astype(str),
                                          t["tour"] + "|" + t["player_id"].astype(str)])))
    hk = keys.get_indexer(h["tour"] + "|" + h["player_id"].astype(str))
    tk = keys.get_indexer(t["tour"] + "|" + t["player_id"].astype(str))
    comp_h = hk.astype(np.int64) * 100_000 + h["tdate"].to_numpy(np.int64)
    o = np.argsort(comp_h, kind="stable")
    comp_s, obs_s, hk_s = comp_h[o], h["obs"].to_numpy(np.int64)[o], hk[o]
    # running max of obs within each player block
    run = pd.Series(obs_s).groupby(hk_s).cummax().to_numpy()
    comp_t = tk.astype(np.int64) * 100_000 + t["tdate"].to_numpy(np.int64)
    idx = np.searchsorted(comp_s, comp_t, side="left") - 1
    ok = (idx >= 0) & (hk_s[np.maximum(idx, 0)] == tk)
    max_a = np.where(ok, run[np.maximum(idx, 0)], -10**9)
    # same tournament, earlier round
    tt = pd.DataFrame({"k": tk, "tid": t["tournament_id"].to_numpy(), "ro": t["round_order"].to_numpy(),
                       "i": np.arange(len(t))})
    hh = pd.DataFrame({"k": hk, "tid": h["tournament_id"].to_numpy(), "ro_h": h["round_order"].to_numpy(),
                       "obs_h": h["obs"].to_numpy(np.int64)})
    j = tt.merge(hh, on=["k", "tid"])
    j = j[j["ro_h"] < j["ro"]]
    max_b = np.full(len(t), -10**9)
    if len(j):
        mb = j.groupby("i")["obs_h"].max()
        max_b[mb.index.to_numpy()] = mb.to_numpy()
    mx = np.maximum(max_a, max_b)
    ob = t["obs"].to_numpy(np.int64)
    return mx >= ob - short, mx >= ob - long


def match_presence(m: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Per match (columns match_id, tour, player_a_id, player_b_id, tdate, tournament_id, round_order, obs): both / one
    side with a 14-day row, both with a 364-day row."""
    out = m.copy()
    for side, col in (("a", "player_a_id"), ("b", "player_b_id")):
        s14, s364 = presence(m.assign(player_id=m[col]), panel)
        out[f"s14_{side}"], out[f"s364_{side}"] = s14, s364
    out["both14"] = out["s14_a"] & out["s14_b"]
    out["one14"] = out["s14_a"] | out["s14_b"]
    out["both364"] = out["s364_a"] & out["s364_b"]
    return out


def validation_n2(panel: pd.DataFrame) -> pd.DataFrame:
    """Both-sides 14-day presence on Stage 0's main-tour main draws 2015-2026 against the acquisition's N2 counts."""
    s0 = pd.read_parquet(S0, columns=["match_id", "tour", "year", "level", "qualifying", "tournament_id", "round_order",
                                      "tournament_date", "player_a_id", "player_b_id"])
    s0 = s0[s0["level"].isin(("GS",) + TOUR_LEVELS) & ~s0["qualifying"].astype(bool) & s0["year"].between(2015, 2026)]
    tm = pd.read_parquet(TIMING, columns=["match_id", "obs"])
    s0 = s0.merge(tm, on="match_id", how="left")
    s0["obs"] = np.floor(s0["obs"]).astype("int64")
    s0["tdate"] = days(s0["tournament_date"])
    mp_ = match_presence(s0, panel)
    mp_["slam"] = mp_["level"].eq("GS")
    ours = mp_.groupby(["tour", "year", "slam"]).agg(frame=("both14", "size"), both14=("both14", "sum")).reset_index()
    acq = pd.read_csv(N2_COUNTS)[["tour", "year", "slam", "frame", "N2_slams"]].rename(columns={"frame": "acq_frame"})
    v = ours.merge(acq, on=["tour", "year", "slam"], how="left")
    v["diff"] = v["both14"] - v["N2_slams"]
    v["ok"] = v["diff"].abs() <= np.maximum(5, np.ceil(0.01 * v["N2_slams"]))
    return v


# ------------------------------------------------------------------------------------------------
def summary(rec: pd.DataFrame, p: pd.DataFrame, fk: pd.DataFrame, snap_meta: dict, val: pd.DataFrame) -> dict:
    u = p[p["use"]]
    by = (u.assign(slam=u["level"].eq("GS")).groupby(["tour", "year", "slam"]).size().unstack("slam", fill_value=0)
          .rename(columns={False: "non_slam", True: "slam"}).reset_index())
    fp = match_presence(fk.rename(columns={"season": "year"}), p)
    fp["slam"] = fp["level"].eq("GS")
    cov = (fp.groupby(["tour", "year", "slam"]).agg(frame=("both14", "size"), both14=("both14", "sum"),
                                                     one14=("one14", "sum"), both364=("both364", "sum"))
           .reset_index())
    hist = u[u["level"].ne("GS")]
    return {
        "built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "reads_results": False,
        "records": {"rows": int(len(rec)), "by_source": rec["source"].value_counts().to_dict(),
                    "invalid_by_reason_source": rec[~rec["valid"]].groupby(["invalid_reason", "source"]).size()
                    .reset_index(name="n").to_dict(orient="records")},
        "panel": {"rows": int(len(p)), "use": int(p["use"].sum()),
                  "drops": p.loc[~p["use"], "drop_reason"].value_counts().to_dict(),
                  "chosen_source_by_tour": u.groupby(["tour", "source"]).size().reset_index(name="n")
                  .to_dict(orient="records"),
                  "non_slam_basis_by_year": hist.groupby(["year", "basis"]).size().unstack(fill_value=0)
                  .reset_index().to_dict(orient="records"),
                  "use_rows_by_tour_year_slam": by.to_dict(orient="records"),
                  "ao_2026_use_rows": u[(u["slam"] == "AO") & (u["year"] == 2026)].groupby("tour").size().to_dict(),
                  "flag_own_outlier": int(p["flag_own_outlier"].sum()),
                  "obs_half_days_floored": int((p["obs_raw"] != p["obs"]).sum())},
        "frame_keys": {"rows": int(len(fk)), "rebuilt_id_differs": int((fk["rebuilt_id"] != fk["match_id"]).sum()),
                       "flipped": int(fk["flipped"].sum()), "id_conflict": int(fk["id_conflict"].sum()),
                       "id_conflict_not_flipped": int((fk["id_conflict"] & ~fk["flipped"]).sum()),
                       "obs_half_days_floored": int((fk["obs_raw"] != fk["obs"]).sum())},
        "frame_coverage": cov.to_dict(orient="records"),
        "validation_n2": {"cells": int(len(val)), "cells_ok": int(val["ok"].sum()),
                          "max_abs_diff": int(val["diff"].abs().max()), "rows": val.to_dict(orient="records")},
        "snapshots": snap_meta,
    }


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log("records (point tables, Infosys Slams, ManTennisData, handoff key statistics, AO match centre)")
    rec = build_records()
    rec.to_parquet(RECORDS, index=False)
    log(f"  {len(rec):,} timed records; panel")
    p = build_panel(rec)
    p.to_parquet(PANEL, index=False)
    log(f"  {len(p):,} rows, {int(p['use'].sum()):,} use; frame keys")
    fk = build_frame_keys()
    fk.to_parquet(FRAME_KEYS, index=False)
    log(f"  {len(fk):,} frame matches; as-of snapshots at the frame's es days")
    meta = build_snapshots(p, fk)
    log("validation against the acquisition's N2 counts; summary")
    val = validation_n2(p)
    s = summary(rec, p, fk, meta, val)
    SUMMARY.write_text(json.dumps(s, indent=1, default=str) + "\n", encoding="utf-8")
    log(f"wrote {PANEL.name}, {FRAME_KEYS.name}, {SNAPSHOTS.name}, {SUMMARY.name}; N2 cells ok "
        f"{s['validation_n2']['cells_ok']}/{s['validation_n2']['cells']}")


if __name__ == "__main__":
    build()
