"""Source reconciliation, Part G (serve speed): one reader per on-disk source of a player's first-serve average speed in
a match. Reads no match result (no winner, score or label column is carried; ManTennisData's winner / loser layout is
read only to place each player's numbers in his slot and is dropped at once).

Every reader returns the same long frame, one row per source record and player slot:

    src      the reader (below)
    kind     "points" (a point copy: the mean is computed here from the points) or "stat" (a published aggregate)
    sys      the measuring and publishing chain, for independence: infosys_atp (the ATP's Infosys files), infosys_slam
             (the AO and RG Infosys files), ibm (the Wimbledon and US Open feeds), hawkeye_slam (the AO and RG Court
             Vision copy), sackmann (Sackmann's copies of the IBM and Infosys Slam feeds)
    key      the source's match key (the format its link table uses); pno the source's player slot (1 or 2)
    pname    the source's player name (for the orientation check); year the source's season
    points columns (kind "points"; NaN for "stat"):
      npts   points the player served; f1 points played on his first serve (serve 1, not a double fault);
      n1     those of them with a plausible speed (40 < v <= 270 km/h); s1 / sd1 their mean / SD (the point mean);
      f2, n2, s2  the same for second-serve points in (serve 2, not a double fault);
      nf, sf timed first-serve faults and their mean (where the source records a fault's speed);
      pmax   his fastest timed serve (points in, and faults where recorded);
      rep    the share of his timed serves whose speed equals the previous timed serve's in the match (any server): the
             input-data audit's stale-repeat sign (RG 2023-24 Hawk-Eye copy)
    stat columns (kind "stat"; NaN for "points"):
      v1, v2, vmax  the published first-serve average, second-serve average and fastest serve (km/h);
      vfin, vftot   the published first serves in and first serves attempted, where given

Readers (one per source family; the module docstring of each says what it maps):
    points   mb_slams, mb_atp (Infosys MatchBeats), ra_atp, ra_handoff, ra_sirgenkii (Infosys rally analysis),
             ibm_pts (SlamTracker points), sackmann_pts (Sackmann's Slam point-by-point), hawkeye_pts (the AO/RG copy)
    stats    ks_mantd (ManTennisData), ks_handoff, ks_atp, ks_sirgenkii, ks_rg (Infosys key statistics), ibm_stat (the
             IBM feeds' match statistics), ao_mc (the AO match centre)
Linking (link_records): each record is placed on the frozen snapshot's (match_id, side) through an existing link table
(the match-timing links of the snapshot, shot_level's stage0_source_matches, serve_speed_acquisition's speeds.parquet),
and its orientation is checked by the players' names against the snapshot's player rows (name_ok).
"""
from __future__ import annotations

import gzip
import json
import re
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.eda.source_reconciliation import common as C

DUMP_PTS = C.DUMP / "points"
SHOT_LINKS = C.STUDIES / "shot_level" / "stage0_source_matches.parquet"
SPEEDS = C.STUDIES / "serve_speed_acquisition" / "speeds.parquet"
ID_MAP = C.STUDIES / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "id_map.csv"
MTD_DIR = C.DUMP / "matches" / "mantennisdata"
LO, HI = 40.0, 270.0
POINT_COLS = ["npts", "f1", "n1", "s1", "sd1", "f2", "n2", "s2", "nf", "sf", "pmax", "rep"]
# v1_set1 / fin_set1: the first set's published average and first serves in; v1_rest / fin_rest: the later sets',
# first-serves-in weighted (Infosys key statistics only: they are published per set)
STAT_COLS = ["v1", "v2", "vmax", "vfin", "vftot", "v1_set1", "fin_set1", "v1_rest", "fin_rest"]
BASE_COLS = ["src", "kind", "sys", "key", "pno", "pname", "year"]
RECORD_COLS = BASE_COLS + POINT_COLS + STAT_COLS
INFOSYS_SHOT = {"Serve": 1, "Return": 2, "3rd shot": 3, "4th shot": 4, "5th shot": 5, "6th shot": 6, "7th shot": 7,
                "8th shot": 8, "9+ odd shots": 9, "10+ even shots": 10, "9+_odd": 9, "10+_even": 10}
KMH = re.compile(r"(\d+(?:\.\d+)?)")
FRACTION = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


def plaus(x) -> np.ndarray:
    v = pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(dtype=float)
    return np.where((v > LO) & (v <= HI), v, np.nan)


def kmh(s: pd.Series) -> np.ndarray:
    """The first number of a speed string ('195 KPH', '["190 KMH", "118 MPH"]', '205.54 KPH'), plausible only."""
    return plaus(s.astype("string").str.extract(KMH, expand=False))


def frac(s: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """'35/44 (80%)' -> (35, 44)."""
    m = s.astype("string").str.extract(FRACTION)
    return (pd.to_numeric(m[0], errors="coerce").to_numpy(float), pd.to_numeric(m[1], errors="coerce").to_numpy(float))


# ------------------------------------------------------------------------------------------------ point aggregation
def aggregate_points(p: pd.DataFrame) -> pd.DataFrame:
    """Per (key, pno) aggregates of a point table with columns key, pno (the server's slot), serve (1 or 2; 0 unknown),
    dfault (bool: the point was a double fault), speed (the speed of the serve that started the point; NaN unknown),
    fspeed (that point's first-serve fault speed, NaN unknown or none) and order (the points' order in the match)."""
    p = p.sort_values(["key", "order"], kind="mergesort").reset_index(drop=True)
    sp = plaus(p["speed"])
    fs = plaus(p["fspeed"]) if "fspeed" in p else np.full(len(p), np.nan)
    serve = pd.to_numeric(p["serve"], errors="coerce").fillna(0).to_numpy()
    dfl = p["dfault"].astype(bool).to_numpy()
    in1, in2 = (serve == 1) & ~dfl, (serve == 2) & ~dfl
    t1, t2 = in1 & np.isfinite(sp), in2 & np.isfinite(sp)
    tf = np.isfinite(fs)
    # stale repeats: a timed serve whose speed equals the previous timed serve of the match (faults included, in order)
    seq = pd.DataFrame({"key": p["key"].to_numpy(), "v": np.where(np.isfinite(sp), sp, np.nan)})
    prev = seq.groupby("key")["v"].shift(1)
    # the previous TIMED serve: forward-fill within the match
    prev = prev.groupby(seq["key"]).ffill()
    rep = np.isfinite(sp) & (sp == prev.to_numpy())
    g = pd.DataFrame({"key": p["key"].to_numpy(), "pno": p["pno"].to_numpy(),
                      "one": 1, "f1": in1, "n1": t1, "s1": np.where(t1, sp, 0.0), "q1": np.where(t1, sp * sp, 0.0),
                      "f2": in2, "n2": t2, "s2": np.where(t2, sp, 0.0), "nf": tf, "sf": np.where(tf, fs, 0.0),
                      "mx": np.fmax(np.where(np.isfinite(sp), sp, np.nan), fs), "timed": np.isfinite(sp), "rep": rep})
    a = g.groupby(["key", "pno"]).agg(npts=("one", "sum"), f1=("f1", "sum"), n1=("n1", "sum"), s1=("s1", "sum"),
                                      q1=("q1", "sum"), f2=("f2", "sum"), n2=("n2", "sum"), s2=("s2", "sum"),
                                      nf=("nf", "sum"), sf=("sf", "sum"), pmax=("mx", "max"), timed=("timed", "sum"),
                                      rep=("rep", "sum")).reset_index()
    n1 = a["n1"].where(a["n1"] > 0)
    a["sd1"] = np.sqrt(np.maximum(a["q1"] / n1 - (a["s1"] / n1) ** 2, 0.0))
    a["s1"] = a["s1"] / n1
    a["s2"] = a["s2"] / a["n2"].where(a["n2"] > 0)
    a["sf"] = a["sf"] / a["nf"].where(a["nf"] > 0)
    a["rep"] = a["rep"] / a["timed"].where(a["timed"] > 0)
    return a.drop(columns=["q1", "timed"])


def _frame(a: pd.DataFrame, src: str, kind: str, sys: str) -> pd.DataFrame:
    a = a.copy()
    a["src"], a["kind"], a["sys"] = src, kind, sys
    for c in RECORD_COLS:
        if c not in a:
            a[c] = np.nan
    a["key"] = a["key"].astype(str)
    a["pno"] = pd.to_numeric(a["pno"], errors="coerce").astype("Int64")
    a["year"] = pd.to_numeric(a["year"], errors="coerce").astype("Int64")
    return a[RECORD_COLS]


# ------------------------------------------------------------------------------------------------ Infosys MatchBeats
def mb_slams() -> pd.DataFrame:
    """AO 2025, RG 2025, RG 2026 MatchBeats (data/dump/points/infosys_slams/points.parquet): server 1/2 = the match's
    p1/p2 (matches.parquet), serve 1/2, result DF = double fault, serveSpeed (whole km/h), faultSrvSpd = the point's
    first-serve fault speed (0 none)."""
    base = DUMP_PTS / "infosys_slams"
    p = pd.read_parquet(base / "points.parquet", columns=["slam", "year", "match_id", "seq", "server", "serve",
                                                          "serveSpeed", "faultSrvSpd", "result"])
    p = p[p["server"].astype(str).isin(["1", "2"])]
    d = pd.DataFrame({"key": p["slam"].astype(str) + "_" + p["year"].astype(str) + "_" + p["match_id"].astype(str),
                      "pno": p["server"].astype(int), "serve": pd.to_numeric(p["serve"], errors="coerce"),
                      "dfault": p["result"].astype(str).eq("DF"), "speed": p["serveSpeed"],
                      "fspeed": np.where(p["serve"].astype(str).eq("2"), p["faultSrvSpd"], np.nan),
                      "order": pd.to_numeric(p["seq"], errors="coerce")})
    a = aggregate_points(d)
    m = pd.read_parquet(base / "matches.parquet", columns=["slam", "year", "match_id", "p1_name", "p2_name"])
    m["key"] = m["slam"].astype(str) + "_" + m["year"].astype(str) + "_" + m["match_id"].astype(str)
    a = _names(a, m, "p1_name", "p2_name")
    a["year"] = a["key"].str.split("_").str[1]
    return _frame(a, "mb_slams", "points", "infosys_slam")


def mb_atp() -> pd.DataFrame:
    """The ATP host's MatchBeats, 2018 Finals and Washington, San Diego, Indian Wells 2021 timed
    (data/dump/points/infosys_atp/points.parquet): as mb_slams; a double fault is "DF" or "P"; no fault speeds."""
    base = DUMP_PTS / "infosys_atp"
    p = pd.read_parquet(base / "points.parquet", columns=["year", "event_id", "match_id", "seq", "server", "serve",
                                                          "serveSpeed", "faultSrvSpd", "result"])
    p = p[p["server"].astype(str).isin(["1", "2"])]
    d = pd.DataFrame({"key": p["year"].astype(str) + "_" + p["event_id"].astype(str) + "_" + p["match_id"].astype(str),
                      "pno": p["server"].astype(int), "serve": pd.to_numeric(p["serve"], errors="coerce"),
                      "dfault": p["result"].astype(str).isin(["DF", "P"]), "speed": p["serveSpeed"],
                      "fspeed": np.where(p["serve"].astype(str).eq("2"), p["faultSrvSpd"], np.nan),
                      "order": pd.to_numeric(p["seq"], errors="coerce")})
    a = aggregate_points(d)
    m = pd.read_parquet(base / "matches.parquet", columns=["year", "event_id", "match_id", "p1_name", "p2_name"])
    m["key"] = m["year"].astype(str) + "_" + m["event_id"].astype(str) + "_" + m["match_id"].astype(str)
    a = _names(a, m, "p1_name", "p2_name")
    a["year"] = a["key"].str.split("_").str[0]
    return _frame(a, "mb_atp", "points", "infosys_atp")


def _names(a: pd.DataFrame, m: pd.DataFrame, c1: str, c2: str) -> pd.DataFrame:
    m = m.drop_duplicates("key").set_index("key")
    n1, n2 = m[c1].reindex(a["key"]).to_numpy(), m[c2].reindex(a["key"]).to_numpy()
    a["pname"] = np.where(a["pno"].astype(int).to_numpy() == 1, n1, n2)
    return a


# ------------------------------------------------------------------------------------------------ Infosys rally analysis
def rally_servers(r: pd.DataFrame) -> np.ndarray:
    """The server (1 or 2; 0 unknown) of each rally-analysis entry, by set-level parity.

    An entry's ending shot was hit by its list's team (t1* = team 1); shot k is the server's when k is odd, so a
    classified entry implies its game's server, hence the set's first server (games alternate; in a tie-break the
    first point is the game's server's, then the serve changes every two points). Each set's first server is the
    majority of its classified entries' implications, double faults left out (some files list a double fault under
    the point's winner); every entry of the set, unclassified ones included, takes the server that parity gives it.
    Checked against the ATP host's MatchBeats servers point by point (spd_checks.py): the per-point rule the panel's
    reader used agrees on 97.7% of classified points (87% at the 2018 ATP Finals), this rule on 99.8% of all points."""
    parts = r["pointId"].astype(str).str.split("_", expand=True)
    s = pd.to_numeric(parts[0], errors="coerce").to_numpy()
    g = pd.to_numeric(parts[1], errors="coerce").to_numpy()
    k = pd.to_numeric(parts[2], errors="coerce").to_numpy()
    shot = r["category"].map(INFOSYS_SHOT).fillna(0).astype(int).to_numpy()
    lst = r["list"].astype(str)
    team = np.where(lst.str.startswith("t1"), 1, np.where(lst.str.startswith("t2"), 2, 0))
    inf = np.where((shot > 0) & (team > 0), np.where(shot % 2 == 1, team, 3 - team), 0)
    dfl = r["pointEndType"].astype(str).str.upper().eq("DOUBLE FAULT").to_numpy()
    tb = r["tieBreak"].astype(str).str.lower().isin(["true", "1"]).to_numpy()
    ok = np.isfinite(s) & np.isfinite(g) & np.isfinite(k)
    kk = np.nan_to_num(k).astype(int)
    gg = np.nan_to_num(g).astype(int)
    tb_turn = ((kk // 2) % 2) == 0                          # a tie-break point served by the tie-break's first server
    game_srv = np.where(tb, np.where(tb_turn, inf, 3 - inf), inf)
    first = np.where(gg % 2 == 1, game_srv, 3 - game_srv)   # the set's first server implied
    vote = ok & (inf > 0) & ~dfl
    v = pd.DataFrame({"key": r["key"].to_numpy()[vote], "s": s[vote], "p1": (first[vote] == 1).astype(float)})
    share = v.groupby(["key", "s"])["p1"].mean()
    sh = share.reindex(pd.MultiIndex.from_arrays([r["key"].to_numpy(), s])).to_numpy()
    s1 = np.where(sh > 0.5, 1, np.where(sh < 0.5, 2, 0))
    gs = np.where(gg % 2 == 1, s1, 3 - s1)
    srv = np.where(tb, np.where(tb_turn, gs, 3 - gs), gs)
    return np.where(ok & (s1 > 0), srv, 0)


def rally_points(r: pd.DataFrame) -> pd.DataFrame:
    """Infosys rally-analysis entries (key, category, list, pointId, serve, serveSpeed, pointEndType, tieBreak) to the
    point layout of aggregate_points; the server by rally_servers. pointId = set_game_point_serve."""
    r = r.drop_duplicates(["key", "pointId"]).reset_index(drop=True)
    srv = rally_servers(r)
    parts = r["pointId"].astype(str).str.split("_", expand=True)
    order = (pd.to_numeric(parts[0], errors="coerce") * 1e6 + pd.to_numeric(parts[1], errors="coerce") * 1e3
             + pd.to_numeric(parts[2], errors="coerce")).to_numpy()
    d = pd.DataFrame({"key": r["key"].to_numpy(), "pno": srv,
                      "serve": pd.to_numeric(r["serve"], errors="coerce").to_numpy(),
                      "dfault": r["pointEndType"].astype(str).str.upper().eq("DOUBLE FAULT").to_numpy(),
                      "speed": pd.to_numeric(r["serveSpeed"], errors="coerce").to_numpy(), "fspeed": np.nan,
                      "order": order})
    return d[d["pno"].isin([1, 2])]


def ra_atp() -> pd.DataFrame:
    """The ATP host's rally analysis (data/dump/points/infosys_atp/rally.parquet): speeds cut to whole km/h."""
    base = DUMP_PTS / "infosys_atp"
    r = pd.read_parquet(base / "rally.parquet", columns=["year", "event_id", "match_id", "category", "list", "pointId",
                                                         "serve", "serveSpeed", "pointEndType", "tieBreak"])
    r["key"] = r["year"].astype(str) + "_" + r["event_id"].astype(str) + "_" + r["match_id"].astype(str)
    a = aggregate_points(rally_points(r))
    m = pd.read_parquet(base / "matches.parquet", columns=["year", "event_id", "match_id", "p1_name", "p2_name"])
    m["key"] = m["year"].astype(str) + "_" + m["event_id"].astype(str) + "_" + m["match_id"].astype(str)
    a = _names(a, m, "p1_name", "p2_name")
    a["year"] = a["key"].str.split("_").str[0]
    return _frame(a, "ra_atp", "points", "infosys_atp")


def _handoff_file(path: str) -> tuple[list, list, list]:
    """One handoff year file: (record meta, rally entries, set0 key-statistics rows) of its singles records. Meta =
    (key, folder, player1_name, player2_name, rally entries), so that the caller keeps one copy per match."""
    opener = gzip.open if path.endswith(".gz") else open
    meta, rally, ks = [], [], []
    folder = Path(path).parent.name
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            code = str(rec.get("match_id") or "").upper()
            if not re.match(r"^[MQ]S", code):
                continue
            key = f"{rec.get('year')}_{rec.get('tournament_id')}_{code}"
            ra = rec.get("rally_analysis") if isinstance(rec.get("rally_analysis"), dict) else {}
            ents = []
            for cat in ra.get("rallyData") or []:
                if not isinstance(cat, dict):
                    continue
                for lst in ("t1win", "t1err", "t2win", "t2err"):
                    for pt in cat.get(lst) or []:
                        if isinstance(pt, dict):
                            ents.append((key, folder, cat.get("name"), lst, str(pt.get("pointId") or ""),
                                         pt.get("serve"), pt.get("serveSpeed"), pt.get("pointEndType"),
                                         pt.get("tieBreak")))
            rally.extend(ents)
            meta.append((key, folder, rec.get("player1_name"), rec.get("player2_name"), len(ents)))
            kst = rec.get("keystats") if isinstance(rec.get("keystats"), dict) else {}
            sets = kst.get("setStats") if isinstance(kst.get("setStats"), dict) else {}
            per = {}
            for sk, rows in sets.items():
                if isinstance(rows, list):
                    per[sk] = {e.get("name"): (e.get("player1"), e.get("player2")) for e in rows if isinstance(e, dict)}
            d = per.get("set0", {})
            if "1st Serve Average Speed" in d:
                for no in (0, 1):
                    by_set = {sk: ((v.get("1st Serve Average Speed") or (None, None))[no],
                                   (v.get("1st Serve") or (None, None))[no])
                              for sk, v in per.items() if sk != "set0"}
                    ks.append((key, folder, no + 1, d.get("1st Serve Average Speed", (None, None))[no],
                               d.get("2nd Serve Average Speed", (None, None))[no], d.get("Max Speed", (None, None))[no],
                               (d.get("1st Serve") or (None, None))[no], json.dumps(by_set)))
    return meta, rally, ks


_HANDOFF_CACHE: dict = {}


def handoff_tables(workers: int = 5) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The handoff's rally entries, set0 key statistics and players' names (data/raw/public_dump/atp_pipeline_handoff/
    infosys_deep and infosys_full). The two folders overlap: the rally entries of one copy per match, the copy with the
    most entries (ties: infosys_full); the key statistics of that copy, else of the other folder's."""
    if "t" in _HANDOFF_CACHE:
        return _HANDOFF_CACHE["t"]
    paths = sorted(str(p) for d in ("infosys_deep", "infosys_full") for p in (C.HANDOFF / d).glob("*_data.jsonl*"))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(_handoff_file, paths))
    meta = pd.DataFrame([x for p in parts for x in p[0]], columns=["key", "folder", "name1", "name2", "size"])
    rally = pd.DataFrame([x for p in parts for x in p[1]],
                         columns=["key", "folder", "category", "list", "pointId", "serve", "serveSpeed", "pointEndType",
                                  "tieBreak"])
    ks = pd.DataFrame([x for p in parts for x in p[2]], columns=["key", "folder", "pno", "v1", "v2", "vmax", "first",
                                                                 "by_set"])
    meta["full"] = meta["folder"].eq("infosys_full")
    best = meta.sort_values(["key", "size", "full"], ascending=[True, False, False]).drop_duplicates("key")
    keep = set(zip(best["key"], best["folder"]))
    rally = rally[[k in keep for k in zip(rally["key"], rally["folder"])]]
    ks = ks.assign(chosen=[k in keep for k in zip(ks["key"], ks["folder"])])
    ks = ks.sort_values(["key", "pno", "chosen"], ascending=[True, True, False]).drop_duplicates(["key", "pno"])
    nm = pd.concat([best[["key", "name1"]].rename(columns={"name1": "pname"}).assign(pno=1),
                    best[["key", "name2"]].rename(columns={"name2": "pname"}).assign(pno=2)], ignore_index=True)
    _HANDOFF_CACHE["t"] = (rally.reset_index(drop=True), ks.reset_index(drop=True), nm)
    return _HANDOFF_CACHE["t"]


def ra_handoff() -> pd.DataFrame:
    """The Hugging Face handoff's rally analysis, 2018-2024 (the panel's "infosys" point means): as ra_atp."""
    rally, _, nm = handoff_tables()
    a = aggregate_points(rally_points(rally))
    a = a.merge(nm, on=["key", "pno"], how="left")
    a["year"] = a["key"].str.split("_").str[0]
    return _frame(a, "ra_handoff", "points", "infosys_atp")


def ks_handoff() -> pd.DataFrame:
    """The handoff's set0 key statistics: 1st / 2nd Serve Average Speed, Max Speed, 1st Serve 'in/total (pct)'."""
    _, ks, nm = handoff_tables()
    fin, ftot = frac(ks["first"])
    split = np.array([set_split(json.loads(b) if isinstance(b, str) else {}) for b in ks["by_set"]], dtype=float)
    a = pd.DataFrame({"key": ks["key"].to_numpy(), "pno": ks["pno"].to_numpy(), "v1": plaus(ks["v1"]),
                      "v2": plaus(ks["v2"]), "vmax": plaus(ks["vmax"]), "vfin": fin, "vftot": ftot,
                      "v1_set1": split[:, 0], "fin_set1": split[:, 1], "v1_rest": split[:, 2], "fin_rest": split[:, 3]})
    a = a[np.isfinite(a["v1"])].merge(nm, on=["key", "pno"], how="left")
    a["year"] = a["key"].str.split("_").str[0]
    return _frame(a, "ks_handoff", "stat", "infosys_atp")


def ra_sirgenkii() -> pd.DataFrame:
    """SirGenkii's rally analysis, 27 Dec 2024 - 7 Apr 2025 (atp_rally_analysis): one row per point; player_id hit the
    ending shot (shot_number as Infosys's groups); the server is that player when the shot number is odd, else the
    opponent; serve 1/2; serve_speed 0 = unknown; point_end_type DOUBLE FAULT."""
    base = DUMP_PTS / "sirgenkii_infotennis"
    res = pd.read_parquet(base / "atp_results.parquet", columns=["tournament_id", "year", "match_id", "player1_id",
                                                                 "player2_id", "player1_name", "player2_name"])
    ra = pd.read_parquet(base / "atp_rally_analysis.parquet",
                         columns=["tournament_id", "year", "match_id", "point_id", "shot_number", "outcome",
                                  "player_id", "point_end_type", "serve", "serve_speed", "tie_break"])
    for t in (res, ra):
        for c in ("tournament_id", "year", "match_id"):
            t[c] = t[c].astype(str)
    res["key"] = res["year"] + "_" + res["tournament_id"] + "_" + res["match_id"]
    ra["key"] = ra["year"] + "_" + ra["tournament_id"] + "_" + ra["match_id"]
    ra = ra.drop_duplicates(["key", "point_id"]).merge(res[["key", "player1_id", "player2_id"]], on="key", how="inner")
    hit = ra["player_id"].astype(str).str.upper()
    team = np.select([hit.eq(ra["player1_id"].astype(str).str.upper()), hit.eq(ra["player2_id"].astype(str).str.upper())],
                     [1, 2], 0)
    # the rally-analysis layout of rally_points: category from the shot number, list from the hitter and W / L
    names = {"1": "Serve", "2": "Return", "3": "3rd shot", "4": "4th shot", "5": "5th shot", "6": "6th shot",
             "7": "7th shot", "8": "8th shot", "9+_odd": "9+_odd", "10+_even": "10+_even"}
    r = pd.DataFrame({"key": ra["key"].to_numpy(),
                      "category": ra["shot_number"].astype(str).map(names).fillna("UNCLASSIFIED").to_numpy(),
                      "list": np.where(team > 0, np.char.add(np.char.add("t", team.astype(str)),
                                                             np.where(ra["outcome"].astype(str).eq("W"), "win", "err")),
                                       ""),
                      "pointId": ra["point_id"].astype(str).to_numpy(), "serve": ra["serve"].to_numpy(),
                      "serveSpeed": ra["serve_speed"].to_numpy(), "pointEndType": ra["point_end_type"].to_numpy(),
                      "tieBreak": np.where(ra["tie_break"].astype(str).eq("1"), "true", "false")})
    a = aggregate_points(rally_points(r))
    a = _names(a, res.rename(columns={"player1_name": "n1", "player2_name": "n2"}), "n1", "n2")
    a["year"] = a["key"].str.split("_").str[0]
    return _frame(a, "ra_sirgenkii", "points", "infosys_atp")


# ------------------------------------------------------------------------------------------------ the Slams' point feeds
def ibm_pts() -> pd.DataFrame:
    """Wimbledon (2019, 2021-26) and US Open (2022-26) SlamTracker points (data/dump/points/<site>/points.parquet): one
    row per point; PointServer 1/2; ServeNumber 1 = first serve in, 2 = second serve in, 0 on double faults (DoubleFault
    names the player) and on non-point rows; Speed_KMH 0 = unknown. Singles events as shot_level's reader (MS, LS, WS,
    QS, RS, MQ, WQ)."""
    parts = []
    for site in ("wimbledon", "usopen"):
        m = pd.read_parquet(DUMP_PTS / site / "matches.parquet",
                            columns=["year", "event", "match_id", "entry.team1.displayNameA", "entry.team2.displayNameA"])
        m = m[m["event"].isin(["MS", "LS", "WS", "QS", "RS", "MQ", "WQ"])]
        p = pd.read_parquet(DUMP_PTS / site / "points.parquet",
                            columns=["year", "event", "match_id", "row", "PointNumber", "PointServer", "PointWinner",
                                     "ServeNumber", "DoubleFault", "Speed_KMH"])
        p = p.merge(m[["year", "event", "match_id"]], on=["year", "event", "match_id"], how="inner")
        srv = pd.to_numeric(p["PointServer"], errors="coerce")
        win = pd.to_numeric(p["PointWinner"], errors="coerce")
        p = p[srv.isin([1, 2]) & win.isin([1, 2])]
        key = site + "_" + p["year"].astype(str) + "_" + p["event"].astype(str) + "_" + p["match_id"].astype(str)
        sn = pd.to_numeric(p["ServeNumber"], errors="coerce").fillna(0)
        dfl = pd.to_numeric(p["DoubleFault"], errors="coerce").fillna(0) > 0
        d = pd.DataFrame({"key": key, "pno": pd.to_numeric(p["PointServer"]).astype(int),
                          "serve": np.where(dfl, 2, sn), "dfault": dfl,
                          "speed": pd.to_numeric(p["Speed_KMH"], errors="coerce"), "fspeed": np.nan,
                          "order": pd.to_numeric(p["row"], errors="coerce")})
        a = aggregate_points(d)
        m["key"] = site + "_" + m["year"].astype(str) + "_" + m["event"].astype(str) + "_" + m["match_id"].astype(str)
        a = _names(a, m, "entry.team1.displayNameA", "entry.team2.displayNameA")
        a["year"] = a["key"].str.split("_").str[1]
        parts.append(a)
    return _frame(pd.concat(parts, ignore_index=True), "ibm_pts", "points", "ibm")


def ibm_stat() -> pd.DataFrame:
    """The same feeds' match statistics (statistics.parquet, section serve_stats, period match, team_1 / team_2):
    f_srv_a_spd (first-serve average), s_srv_a_spd (second), t_f_spd (fastest serve), f_srv_p (first-serve points =
    first serves in); base_stats t_f_srv (first serves attempted)."""
    parts = []
    for site in ("wimbledon", "usopen"):
        m = pd.read_parquet(DUMP_PTS / site / "matches.parquet",
                            columns=["year", "event", "match_id", "entry.team1.displayNameA", "entry.team2.displayNameA"])
        m = m[m["event"].isin(["MS", "LS", "WS", "QS", "RS", "MQ", "WQ"])]
        st = pq.read_table(DUMP_PTS / site / "statistics.parquet",
                           columns=["year", "event", "match_id", "section", "period", "team", "key", "value"]).to_pandas()
        st = st[st["period"].eq("match") & st["key"].isin(["f_srv_a_spd", "s_srv_a_spd", "t_f_spd", "f_srv_p",
                                                           "t_f_srv"])]
        st = st.merge(m[["year", "event", "match_id"]], on=["year", "event", "match_id"], how="inner")
        st = st.drop_duplicates(["year", "event", "match_id", "team", "key"])
        w = st.pivot_table(index=["year", "event", "match_id", "team"], columns="key", values="value",
                           aggfunc="first").reset_index()
        for c in ("f_srv_a_spd", "s_srv_a_spd", "t_f_spd", "f_srv_p", "t_f_srv"):
            if c not in w:
                w[c] = np.nan
        a = pd.DataFrame({"key": site + "_" + w["year"].astype(str) + "_" + w["event"].astype(str) + "_"
                          + w["match_id"].astype(str),
                          "pno": w["team"].astype(str).str.extract(r"(\d)$", expand=False).astype(int),
                          "v1": kmh(w["f_srv_a_spd"]), "v2": kmh(w["s_srv_a_spd"]), "vmax": kmh(w["t_f_spd"]),
                          "vfin": pd.to_numeric(w["f_srv_p"], errors="coerce"),
                          "vftot": pd.to_numeric(w["t_f_srv"], errors="coerce")})
        m["key"] = site + "_" + m["year"].astype(str) + "_" + m["event"].astype(str) + "_" + m["match_id"].astype(str)
        a = _names(a[np.isfinite(a["v1"]).to_numpy()], m, "entry.team1.displayNameA", "entry.team2.displayNameA")
        a["year"] = a["key"].str.split("_").str[1]
        parts.append(a)
    return _frame(pd.concat(parts, ignore_index=True), "ibm_stat", "stat", "ibm")


def sackmann_pts() -> pd.DataFrame:
    """Sackmann's Slam point-by-point, 2011-2024 (data/dump/points/sackmann_archive/slam_pointbypoint/*-points.parquet):
    one row per point; PointServer 1/2; ServeNumber 1/2 (from 2014), else the P1/P2 FirstSrvIn and SecondSrvIn flags;
    P1/P2DoubleFault; Speed_KMH 0 = unknown; rows with PointNumber 0X / 0Y are pre-match rows."""
    base = DUMP_PTS / "sackmann_archive" / "slam_pointbypoint"
    parts = []
    for ppath in sorted(base.glob("*-points.parquet")):
        names = pq.read_schema(ppath).names
        want = [c for c in ["match_id", "PointNumber", "PointServer", "PointWinner", "ServeNumber", "P1FirstSrvIn",
                            "P2FirstSrvIn", "P1SecondSrvIn", "P2SecondSrvIn", "P1DoubleFault", "P2DoubleFault",
                            "Speed_KMH", "_row"] if c in names]
        p = pd.read_parquet(ppath, columns=want)
        p = p[~p["PointNumber"].astype(str).str.contains("X|Y", regex=True)]
        g = lambda c: pd.to_numeric(p[c], errors="coerce").fillna(0) if c in p else pd.Series(0, index=p.index)  # noqa
        srv, win = g("PointServer"), g("PointWinner")
        keep = srv.isin([1, 2]) & win.isin([1, 2])
        dfl = (g("P1DoubleFault") > 0) | (g("P2DoubleFault") > 0)
        sn = g("ServeNumber")
        fin = (g("P1FirstSrvIn") > 0) | (g("P2FirstSrvIn") > 0)
        sin = (g("P1SecondSrvIn") > 0) | (g("P2SecondSrvIn") > 0)
        serve = np.where(sn.isin([1, 2]), sn, np.where(fin, 1, np.where(sin | dfl, 2, 0)))
        d = pd.DataFrame({"key": p["match_id"].astype(str), "pno": srv.astype(int), "serve": serve, "dfault": dfl,
                          "speed": g("Speed_KMH").where(g("Speed_KMH") > 0), "fspeed": np.nan,
                          "order": pd.to_numeric(p["_row"], errors="coerce")})[keep.to_numpy()]
        a = aggregate_points(d)
        mpath = Path(str(ppath).replace("-points.parquet", "-matches.parquet"))
        if mpath.exists():
            m = pd.read_parquet(mpath, columns=["match_id", "player1", "player2"]).rename(columns={"match_id": "key"})
            a = _names(a, m, "player1", "player2")
        else:
            a["pname"] = None
        a["year"] = a["key"].str.split("-").str[0]
        parts.append(a)
    return _frame(pd.concat(parts, ignore_index=True), "sackmann_pts", "points", "sackmann")


def hawkeye_pts() -> pd.DataFrame:
    """The AO 2020-24 / RG 2019-24 Court Vision copy's per-serve CSV (data/dump/points/slam_ball_tracking/points/*.parquet):
    one row per serve attempt; a 'Faulty Serve' row on serve 1 is a first-serve fault (its speed is the fault's); the
    point's row has serve_num 1 (first serve in) or 2 (second serve, DoubleFault included); server_id names the server
    (matches.parquet player1_id / player2_id); serve_speed_kph '195 KPH'."""
    base = DUMP_PTS / "slam_ball_tracking"
    m = pd.read_parquet(base / "matches.parquet", columns=["match_id", "slam", "year", "player1_id", "player2_id",
                                                           "player1", "player2"])
    p = pd.concat([pd.read_parquet(x, columns=["match_id", "slam", "year", "_row", "serve_num", "server_id",
                                                "point_end_type", "serve_speed_kph"])
                   for x in sorted((base / "points").glob("*.parquet"))], ignore_index=True)
    p = p.merge(m, on=["slam", "year", "match_id"], how="inner")
    key = p["slam"].astype(str) + "_" + p["year"].astype(str) + "_" + p["match_id"].astype(str)
    pno = np.select([p["server_id"].astype(str).eq(p["player1_id"].astype(str)),
                     p["server_id"].astype(str).eq(p["player2_id"].astype(str))], [1, 2], 0)
    pet = p["point_end_type"].astype(str)
    fault = pet.eq("Faulty Serve")
    sn = pd.to_numeric(p["serve_num"], errors="coerce").fillna(0)
    spd = kmh(p["serve_speed_kph"])
    # a fault row is not a point: its speed goes to the next row (the same point's second serve) as fspeed
    d = pd.DataFrame({"key": key, "pno": pno, "serve": sn, "dfault": pet.eq("DoubleFault"), "speed": spd,
                      "fault": fault.to_numpy(), "order": pd.to_numeric(p["_row"], errors="coerce")})
    d = d[d["pno"] > 0].sort_values(["key", "order"], kind="mergesort").reset_index(drop=True)
    prev_fault = d.groupby("key")["fault"].shift(1).fillna(False).astype(bool)
    prev_speed = d.groupby("key")["speed"].shift(1)
    d["fspeed"] = np.where(prev_fault & (d["serve"] == 2) & ~d["fault"], prev_speed, np.nan)
    pts = d[~d["fault"]].drop(columns="fault")
    a = aggregate_points(pts)
    # stale repeats over every serve attempt (faults included), as the audit counted them
    allv = d.assign(v=d["speed"])
    prv = allv.groupby("key")["v"].shift(1).groupby(allv["key"]).ffill()
    allv["rep"] = np.isfinite(allv["v"]) & (allv["v"] == prv)
    rr = allv[np.isfinite(allv["v"])].groupby(["key", "pno"])["rep"].mean().rename("rep_all")
    a = a.join(rr, on=["key", "pno"])
    a["rep"] = a["rep_all"]
    a = a.drop(columns="rep_all")
    m["key"] = m["slam"].astype(str) + "_" + m["year"].astype(str) + "_" + m["match_id"].astype(str)
    a = _names(a, m, "player1", "player2")
    a["year"] = a["key"].str.split("_").str[1]
    return _frame(a, "hawkeye_pts", "points", "hawkeye_slam")


# ------------------------------------------------------------------------------------------------ published aggregates
def ks_mantd() -> pd.DataFrame:
    """ManTennisData's per-match ATP Stats Centre statistics (data/dump/matches/mantennisdata/atp_matches_2021..2026):
    the row id is year-tournament-code1-code2-round and slot 1 is code1's columns (win_*), slot 2 code2's (los_*); the
    winner / loser naming is used only to place each player's numbers and is not kept."""
    rows = []
    for y in range(2021, 2027):
        path = MTD_DIR / f"atp_matches_{y}.parquet"
        if not path.exists():
            continue
        cols = ["id", "stadie_id", "winner_name", "loser_name"] + [f"{s}_{c}" for s in ("win", "los") for c in (
            "average_first_serves_kmh", "average_second_serve_kmh", "fastest_first_serves_kmh",
            "fastest_second_serve_kmh", "first_serves_in", "first_serves_total")]
        t = pd.read_parquet(path, columns=cols)
        for no, s, nm in ((1, "win", "winner_name"), (2, "los", "loser_name")):
            v1 = pd.to_numeric(t[f"{s}_average_first_serves_kmh"], errors="coerce")
            a = pd.DataFrame({"key": t["id"].astype(str), "pno": no, "pname": t[nm], "year": y,
                              "v1": plaus(v1), "v2": plaus(t[f"{s}_average_second_serve_kmh"]),
                              "vmax": np.fmax(plaus(t[f"{s}_fastest_first_serves_kmh"]),
                                              plaus(t[f"{s}_fastest_second_serve_kmh"])),
                              "vfin": pd.to_numeric(t[f"{s}_first_serves_in"], errors="coerce"),
                              "vftot": pd.to_numeric(t[f"{s}_first_serves_total"], errors="coerce")})
            rows.append(a[v1.gt(0).to_numpy()])
    return _frame(pd.concat(rows, ignore_index=True), "ks_mantd", "stat", "infosys_atp")


def set_split(by_set: dict) -> tuple[float, float, float, float]:
    """(first set's average, its first serves in, the later sets' first-serves-in weighted average, their first serves
    in) from {set_key: (average, 'in/total (pct)')} of one player; NaN where absent or implausible."""
    def one(v):
        a = plaus([v[0]])[0] if v and v[0] not in (None, "") else np.nan
        m = FRACTION.match(str(v[1] or "")) if v else None
        return a, (float(m.group(1)) if m else np.nan)
    a1, f1 = one(by_set.get("set1"))
    num = den = 0.0
    for sk, v in by_set.items():
        if sk in ("set0", "set1") or not re.match(r"^set\d+$", sk):
            continue
        a, f = one(v)
        if np.isfinite(a) and np.isfinite(f) and f > 0:
            num += a * f
            den += f
    return a1, f1, (num / den if den > 0 else np.nan), (den if den > 0 else np.nan)


def _infosys_ks(path: Path, keycols: list[str], first_name: str, src: str, sys: str) -> pd.DataFrame:
    k = pd.read_parquet(path, columns=keycols + ["set_key", "name", "player1", "player2"])
    k = k[k["name"].isin(["1st Serve Average Speed", "2nd Serve Average Speed", "Max Speed", first_name])]
    k["key"] = k[keycols].astype(str).agg("_".join, axis=1)
    k = k.drop_duplicates(["key", "set_key", "name"])
    s0 = k[k["set_key"].astype(str).eq("set0")]
    out = []
    for no in (1, 2):
        w = s0.pivot_table(index="key", columns="name", values=f"player{no}", aggfunc="first")
        fin, ftot = frac(w[first_name]) if first_name in w else (np.nan, np.nan)
        ps = k[~k["set_key"].astype(str).eq("set0") & k["name"].isin(["1st Serve Average Speed", first_name])]
        by = {}
        for (key, sk, nm), v in zip(ps[["key", "set_key", "name"]].itertuples(index=False, name=None),
                                    ps[f"player{no}"].to_numpy()):
            d = by.setdefault(key, {}).setdefault(sk, [None, None])
            d[0 if nm == "1st Serve Average Speed" else 1] = v
        split = np.array([set_split(by.get(key, {})) for key in w.index], dtype=float).reshape(-1, 4)
        a = pd.DataFrame({"key": w.index, "pno": no,
                          "v1": plaus(w.get("1st Serve Average Speed")), "v2": plaus(w.get("2nd Serve Average Speed")),
                          "vmax": plaus(w.get("Max Speed")), "vfin": fin, "vftot": ftot,
                          "v1_set1": split[:, 0], "fin_set1": split[:, 1], "v1_rest": split[:, 2],
                          "fin_rest": split[:, 3]})
        out.append(a[np.isfinite(a["v1"]).to_numpy()])
    return pd.concat(out, ignore_index=True)


def ks_atp() -> pd.DataFrame:
    """The ATP host's key statistics, set0 (data/dump/points/infosys_atp/keystats.parquet)."""
    a = _infosys_ks(DUMP_PTS / "infosys_atp" / "keystats.parquet", ["year", "event_id", "match_id"], "1st Serve",
                    "ks_atp", "infosys_atp")
    m = pd.read_parquet(DUMP_PTS / "infosys_atp" / "matches.parquet", columns=["year", "event_id", "match_id", "p1_name",
                                                                             "p2_name"])
    m["key"] = m["year"].astype(str) + "_" + m["event_id"].astype(str) + "_" + m["match_id"].astype(str)
    a = _names(a, m, "p1_name", "p2_name")
    a["year"] = a["key"].str.split("_").str[0]
    return _frame(a, "ks_atp", "stat", "infosys_atp")


def ks_rg() -> pd.DataFrame:
    """Roland-Garros's own Infosys key statistics, RG 2025-26, set0 (data/dump/points/infosys_slams/keystats.parquet;
    'First Serve' = in/total). The AO host has none."""
    a = _infosys_ks(DUMP_PTS / "infosys_slams" / "keystats.parquet", ["slam", "year", "match_id"], "First Serve",
                    "ks_rg", "infosys_slam")
    m = pd.read_parquet(DUMP_PTS / "infosys_slams" / "matches.parquet", columns=["slam", "year", "match_id", "p1_name",
                                                                               "p2_name"])
    m["key"] = m["slam"].astype(str) + "_" + m["year"].astype(str) + "_" + m["match_id"].astype(str)
    a = _names(a, m, "p1_name", "p2_name")
    a["year"] = a["key"].str.split("_").str[1]
    return _frame(a, "ks_rg", "stat", "infosys_slam")


def ks_sirgenkii() -> pd.DataFrame:
    """SirGenkii's key statistics, match level (atp_key_stats, set_n 0; -999 = missing): serve1_avg_speed,
    serve2_avg_speed, max_speed, per player_id (slot by atp_results player1_id / player2_id)."""
    base = DUMP_PTS / "sirgenkii_infotennis"
    res = pd.read_parquet(base / "atp_results.parquet", columns=["tournament_id", "year", "match_id", "player1_id",
                                                                 "player2_id", "player1_name", "player2_name"])
    k = pd.read_parquet(base / "atp_key_stats.parquet", columns=["tournament_id", "year", "match_id", "set_n",
                                                                 "player_id", "serve1_avg_speed", "serve2_avg_speed",
                                                                 "max_speed"])
    for t in (res, k):
        for c in ("tournament_id", "year", "match_id"):
            t[c] = t[c].astype(str)
    k = k[k["set_n"].astype(str).eq("0")]
    res["key"] = res["year"] + "_" + res["tournament_id"] + "_" + res["match_id"]
    k["key"] = k["year"] + "_" + k["tournament_id"] + "_" + k["match_id"]
    k = k.merge(res[["key", "player1_id", "player2_id", "player1_name", "player2_name"]], on="key", how="inner")
    pid = k["player_id"].astype(str).str.upper()
    pno = np.select([pid.eq(k["player1_id"].astype(str).str.upper()), pid.eq(k["player2_id"].astype(str).str.upper())],
                    [1, 2], 0)
    a = pd.DataFrame({"key": k["key"], "pno": pno, "pname": np.where(pno == 1, k["player1_name"], k["player2_name"]),
                      "v1": plaus(k["serve1_avg_speed"]), "v2": plaus(k["serve2_avg_speed"]),
                      "vmax": plaus(k["max_speed"])})
    a = a[(a["pno"] > 0) & np.isfinite(a["v1"])].drop_duplicates(["key", "pno"])
    a["year"] = a["key"].str.split("_").str[0]
    return _frame(a, "ks_sirgenkii", "stat", "infosys_atp")


def ao_mc() -> pd.DataFrame:
    """The AO match centre's statistics (data/dump/points/ausopen/set_statistics.parquet, set 'All'): '1st Serve
    Average', '2nd serve average', 'Fastest serve', '1st serve in' (secondary 'in/total'); team1 / team2 = slots."""
    a = pd.read_parquet(DUMP_PTS / "ausopen" / "set_statistics.parquet",
                        columns=["record_key", "year", "set", "stat", "team1_primary", "team1_secondary",
                                 "team2_primary", "team2_secondary"])
    m = pd.read_parquet(DUMP_PTS / "ausopen" / "matches.parquet", columns=["record_key", "event", "team1_names",
                                                                         "team2_names"])
    singles = set(m.loc[m["event"].isin(["MS", "WS", "MQ", "WQ"]), "record_key"])
    a = a[a["set"].astype(str).eq("All") & a["stat"].isin(["1st Serve Average", "2nd serve average", "Fastest serve",
                                                            "1st serve in"]) & a["record_key"].isin(singles)]
    a = a.drop_duplicates(["record_key", "stat"])
    m = m.drop_duplicates("record_key").set_index("record_key")
    out = []
    for no in (1, 2):
        w = a.pivot_table(index="record_key", columns="stat", values=f"team{no}_primary", aggfunc="first")
        sec = a[a["stat"].eq("1st serve in")].drop_duplicates("record_key").set_index("record_key")[f"team{no}_secondary"]
        fin, ftot = frac(sec.reindex(w.index))
        yr = a.drop_duplicates("record_key").set_index("record_key")["year"].reindex(w.index)
        nm = m[f"team{no}_names"].reindex(w.index).astype("string")
        out.append(pd.DataFrame({"key": w.index, "pno": no, "pname": nm.to_numpy(), "year": yr.to_numpy(),
                                 "v1": plaus(w.get("1st Serve Average")), "v2": plaus(w.get("2nd serve average")),
                                 "vmax": plaus(w.get("Fastest serve")), "vfin": fin, "vftot": ftot}))
    a = pd.concat(out, ignore_index=True)
    a = a[np.isfinite(a["v1"]).to_numpy()]
    return _frame(a, "ao_mc", "stat", "infosys_slam")


READERS = {"mb_slams": mb_slams, "mb_atp": mb_atp, "ra_atp": ra_atp, "ra_handoff": ra_handoff,
           "ra_sirgenkii": ra_sirgenkii, "ibm_pts": ibm_pts, "sackmann_pts": sackmann_pts, "hawkeye_pts": hawkeye_pts,
           "ks_mantd": ks_mantd, "ks_handoff": ks_handoff, "ks_atp": ks_atp, "ks_sirgenkii": ks_sirgenkii,
           "ks_rg": ks_rg, "ibm_stat": ibm_stat, "ao_mc": ao_mc}


# ------------------------------------------------------------------------------------------------ names and links
def name_tokens(s) -> frozenset:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return frozenset()
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return frozenset(x for x in re.split(r"[^a-z]+", t) if len(x) >= 3)


def names_match(a, b) -> bool:
    """Two names share a token of three letters or more (surnames; initials and accents ignored)."""
    ta, tb = name_tokens(a), name_tokens(b)
    return bool(ta & tb)


def id_remap() -> dict:
    m = pd.read_csv(ID_MAP, usecols=["old_match_id", "new_match_id"])
    return dict(zip(m["old_match_id"], m["new_match_id"]))


def link_tables() -> dict:
    """The link tables, each as (key -> match_id[, a1]) or (key, pno -> match_id, side), on the snapshot's ids."""
    remap = id_remap()
    sm = pd.read_parquet(SHOT_LINKS, columns=["source", "key", "match_id", "a1"])
    sm = sm[sm["match_id"].notna()].copy()
    sm["match_id"] = sm["match_id"].map(lambda x: remap.get(x, x))
    sp = pd.read_parquet(SPEEDS, columns=["source", "source_key", "player_no", "match_id", "side", "round"])
    sp = sp[sp["match_id"].notna() & sp["side"].isin(["A", "B"])]
    mt = C.links("infosys", columns=["match_id", "source_key"])
    return {"shot": sm, "speeds": sp, "timing_infosys": mt}


# which link each reader uses: ("shot", shot_level source name) / ("speeds", speeds.parquet source) / ("timing", name)
LINK_OF = {"mb_slams": ("speeds", "infosys_slams"), "ks_rg": ("speeds", "infosys_slams"),
           "mb_atp": ("speeds", "infosys_atp"), "ra_atp": ("speeds", "infosys_atp"), "ks_atp": ("speeds", "infosys_atp"),
           "ks_mantd": ("speeds", "mantennisdata"),
           "ra_handoff": ("timing", "infosys"), "ks_handoff": ("timing", "infosys"),
           "ra_sirgenkii": ("shot", "sirgenkii"), "ks_sirgenkii": ("shot", "sirgenkii"),
           "ibm_pts": ("shot", "slamtracker"), "ibm_stat": ("shot", "slamtracker"),
           "sackmann_pts": ("shot", "slam_pbp"), "hawkeye_pts": ("shot", "slam_tracking"),
           "ao_mc": ("shot", "ausopen")}


def link_records(rec: pd.DataFrame, tables: dict, s0_names: pd.DataFrame) -> pd.DataFrame:
    """match_id and side for every record.
    side_link   the link's own orientation (speeds.parquet's side; shot_level's a1); none for the match-timing links
    side_names  the names' verdict for the source match (both slots): slot 1's name matches exactly one of the
                snapshot's two players and slot 2's the other (or one slot is clear and the other has no name); NaN when
                the names cannot tell (no name, a shared surname, or both slots on one player)
    side        side_names where it exists, else side_link; records with neither are dropped
    name_ok     1 when side_link agrees with side_names, 0 when the names reversed the link (link_flip), NaN when either
                is missing"""
    out = []
    for src, g in rec.groupby("src", sort=False):
        how, name = LINK_OF[src]
        g = g.copy()
        if how == "speeds":
            sp = tables["speeds"]
            sp = sp[sp["source"].eq(name)][["source_key", "player_no", "match_id", "side", "round"]].rename(
                columns={"source_key": "key", "player_no": "pno", "round": "round_src"})
            sp = sp.drop_duplicates(["key", "pno"])
            sp["pno"] = sp["pno"].astype("Int64")
            g = g.merge(sp, on=["key", "pno"], how="left")
        elif how == "shot":
            sm = tables["shot"]
            sm = sm[sm["source"].eq(name)][["key", "match_id", "a1"]].drop_duplicates("key")
            g = g.merge(sm, on="key", how="left")
            a1 = g["a1"].astype("boolean")
            one = g["pno"].astype(int).eq(1)
            g["side"] = np.where(a1.isna(), None, np.where(a1.fillna(False) == one, "A", "B"))
            g = g.drop(columns="a1")
            g["round_src"] = None
        else:
            mt = tables["timing_infosys"].drop_duplicates("source_key").rename(columns={"source_key": "key"})
            g = g.merge(mt, on="key", how="left")
            g["side"] = None
            g["round_src"] = None
        g["link"] = f"{how}:{name}"
        out.append(g)
    r = pd.concat(out, ignore_index=True)
    r = r[r["match_id"].notna()].copy()
    r = r.rename(columns={"side": "side_link"})
    # names against the snapshot's players
    nm = s0_names.drop_duplicates(["match_id", "side"]).set_index(["match_id", "side"])["player_name"]
    na = nm.reindex(pd.MultiIndex.from_arrays([r["match_id"], np.full(len(r), "A")])).to_numpy()
    nb = nm.reindex(pd.MultiIndex.from_arrays([r["match_id"], np.full(len(r), "B")])).to_numpy()
    r["in_s0"] = pd.notna(na) | pd.notna(nb)
    mA = np.array([names_match(x, y) for x, y in zip(r["pname"], na)])
    mB = np.array([names_match(x, y) for x, y in zip(r["pname"], nb)])
    own = pd.Series(np.where(mA & ~mB, "A", np.where(mB & ~mA, "B", "")), index=r.index)
    both = pd.Series(mA & mB, index=r.index)
    # the match-level verdict, by the slot-1 orientation it implies (1 = slot 1 is side A)
    imp = np.where(own.eq("A"), np.where(r["pno"].astype(int).eq(1), 1, 0),
                   np.where(own.eq("B"), np.where(r["pno"].astype(int).eq(1), 0, 1), -1))
    r["_imp"] = np.where(imp >= 0, imp, np.nan)
    r["_both"] = both.to_numpy().astype(int)
    grp = r.groupby(["src", "key", "match_id"])
    lo = grp["_imp"].transform("min").to_numpy()
    hi = grp["_imp"].transform("max").to_numpy()
    anyboth = grp["_both"].transform("max").to_numpy() > 0
    ok = np.isfinite(lo) & (lo == hi) & ~anyboth                      # consistent and no slot on both players
    verdict = np.where(ok, np.nan_to_num(lo, nan=-1).astype(int), -1)
    one = r["pno"].astype(int).eq(1).to_numpy()
    r["side_names"] = np.where(verdict < 0, None, np.where((verdict == 1) == one, "A", "B"))
    r["side"] = np.where(pd.notna(r["side_names"]), r["side_names"], r["side_link"])
    r["link_flip"] = pd.notna(r["side_names"]) & pd.notna(r["side_link"]) & (r["side_names"] != r["side_link"])
    r["name_ok"] = np.where(pd.isna(r["side_names"]) | pd.isna(r["side_link"]), np.nan,
                            (r["side_names"] == r["side_link"]).astype(float))
    r = r[r["side"].isin(["A", "B"]) & r["in_s0"]].drop(columns=["_imp", "_both"]).copy()
    # one record per (src, match_id, side): a second copy of the same source on one player-match is ambiguous
    r["dup_link"] = r.duplicated(["src", "match_id", "side"], keep=False)
    return r.reset_index(drop=True)
