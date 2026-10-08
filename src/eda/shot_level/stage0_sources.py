"""Stage 0, part 1: every source of shot-level data on disk, read match by match, and linked to Stage 0.

For each source this script reads every singles match and counts, per match, how many points carry each family of
shot-level fields (common.FAMILIES): rally length, how the point ended, serve speed, serve placement, net play, return
depth, stroke type, ball tracking. Sources that hold match totals instead of points (the WTA's advanced statistics,
the Infosys key statistics) count the families their totals cover. Each match is then linked to the predictability
diagnostic's Stage 0 table (common.Stage0Linker) so that later stages can use that study's players, order and pool.

Nothing here reads who won a match: the counts are of fields, not of results.

Run:  ./python.sh src/eda/shot_level/stage0_sources.py [--only mcp,infosys,...] [--workers 5]
Writes data/studies/shot_level/:
    stage0_source_matches.parquet   one row per source match: keys, names, date, the family counts, the Stage 0 link
    stage0_sources.csv              per source, tour and year: matches read, linked, carrying each family
    stage0_sources.json             the same, plus each source's reading notes and the link report
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.data_map import measure as M  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402

FAM = list(S.FAMILIES)
CNT = [f"cnt_{f}" for f in FAM]
# A match carries a family when at least this share of its points has the field (net play: any net point; match
# totals: the total is recorded).
THRESHOLD = {"rally": 0.5, "ending": 0.4, "speed": 0.4, "placement": 0.4, "net": None, "return": 0.4, "stroke": 0.4,
             "tracking": 0.5}
NOTES: dict[str, list[str]] = {}


def note(src: str, text: str) -> None:
    NOTES.setdefault(src, []).append(text)


def frame(src: str, rows: list[dict]) -> pd.DataFrame:
    f = pd.DataFrame(rows)
    f.insert(0, "source", src)
    for c in CNT + ["n_points"]:
        if c not in f:
            f[c] = 0
        f[c] = pd.to_numeric(f[c], errors="coerce").fillna(0).astype("int64")
    for c in ("round", "draw", "level", "id1", "id2", "totals"):
        if c not in f:
            f[c] = None
    return f


def nonblank(s: pd.Series) -> pd.Series:
    """True where a field holds a value: not missing, not empty, not 'NA', not zero."""
    t = s.astype(object).where(s.notna(), "").astype(str).str.strip()
    return ~t.isin(["", "0", "0.0", "NA", "nan", "None", "null", "-", "None None"])


def per_match(points: pd.DataFrame, key: str | list, flags: dict[str, pd.Series]) -> pd.DataFrame:
    """Sum boolean point flags per match: n_points and one cnt_<family> per flag."""
    g = pd.DataFrame({f"cnt_{k}": v.astype("int64").to_numpy() for k, v in flags.items()}, index=points.index)
    keys = [key] if isinstance(key, str) else list(key)
    for k in keys:
        g[k] = points[k].to_numpy()
    out = g.groupby(keys, sort=False).sum()
    out["n_points"] = points.groupby(keys, sort=False).size()
    return out.reset_index()


# ------------------------------------------------------------------------------------------------
# Match Charting Project (shot by shot; volunteers' charts)

MCP_SHOTS = set("fbrsvzopuylmhijktq")
MCP_NET_SHOTS = set("vzopijhk")
MCP_SERVE_FAULTS = set("nwdxge!V")


def mcp_point(first, second) -> tuple:
    """(rally length, serve direction known, return depth known, ending known, net, last shot's stroke known) of one
    charted point, from the first- and second-serve strings. The point is played from the second string when the first
    is a fault. Rally length counts the serve as one shot."""
    s1 = first if isinstance(first, str) else ""
    s2 = second if isinstance(second, str) else ""
    s = s2 if s2.strip() else s1
    s = s.strip().lstrip("c")
    if not s or s[0] not in "4560":
        return (0, False, False, False, False, False)
    body = s[1:]
    shots = [i for i, ch in enumerate(body) if ch in MCP_SHOTS]
    rally = 1 + len(shots)
    serve_dir = s[0] in "456"
    ret_depth = False
    if shots:
        j = shots[0] + 1
        while j < len(body) and body[j].isdigit():
            if body[j] in "789":
                ret_depth = True
            j += 1
    fault_end = bool(s2.strip()) and len(body) > 0 and body[0] in MCP_SERVE_FAULTS and not shots
    ending = ("*" in body) or ("#" in body) or ("@" in body) or fault_end
    net = ("+" in body) or any(body[i] in MCP_NET_SHOTS for i in shots)
    stroke = bool(shots)
    return (rally, serve_dir, ret_depth, ending, net, stroke)


def mcp() -> pd.DataFrame:
    base = S.DUMP / "points" / "match_charting_project"
    parts = []
    for g, tour in (("m", "M"), ("w", "W")):
        meta = pd.read_parquet(base / "metadata" / f"charting-{g}-matches.parquet")
        pts = pd.concat([pd.read_parquet(p, columns=["match_id", "1st", "2nd"])
                         for p in sorted((base / "points").glob(f"charting-{g}-points-*.parquet"))], ignore_index=True)
        parsed = [mcp_point(a, b) for a, b in zip(pts["1st"].to_numpy(), pts["2nd"].to_numpy())]
        arr = np.array(parsed, dtype=object)
        flags = {"rally": pd.Series(arr[:, 0].astype(int) > 0), "placement": pd.Series(arr[:, 1].astype(bool)),
                 "return": pd.Series(arr[:, 2].astype(bool)), "ending": pd.Series(arr[:, 3].astype(bool)),
                 "net": pd.Series(arr[:, 4].astype(bool)), "stroke": pd.Series(arr[:, 5].astype(bool))}
        pm = per_match(pts, "match_id", {k: v.set_axis(pts.index) for k, v in flags.items()})
        meta = meta.merge(pm, on="match_id", how="left")
        rows = pd.DataFrame({
            "key": meta["match_id"], "tour": tour, "d": M.to_date(meta["Date"], "%Y%m%d"),
            "name1": meta["Player 1"], "name2": meta["Player 2"], "round": meta["Round"],
            "draw": np.where(M.is_qual_round(meta["Round"]), "qual", "main"), "tname": meta["Tournament"],
            "n_points": meta["n_points"], **{c: meta[c] for c in CNT if c in meta}})
        rows["year"] = rows["d"].dt.year
        parts.append(rows)
        note("mcp", f"{tour}: {len(meta)} charts listed, {int(meta['n_points'].notna().sum())} with points staged "
                    f"(the staged points start in 2010)")
    out = frame("mcp", pd.concat(parts, ignore_index=True).to_dict("records"))
    note("mcp", "Rally length, serve direction (wide/body/T), return depth, how the point ended, net approaches and the "
                "stroke of every shot are parsed from each point's shot string; the point is played from the second-"
                "serve string when the first is a fault")
    return out


# ------------------------------------------------------------------------------------------------
# ATP Infosys Stats Centre (points with how they ended, rally length by shot number, serve speed)

INFOSYS_SHOT_NO = {"Serve": 1, "Return": 2, "3rd shot": 3, "4th shot": 4, "5th shot": 5, "6th shot": 6,
                   "7th shot": 7, "8th shot": 8, "9+ odd shots": 9, "10+ even shots": 10}
INFOSYS_ENDINGS = {"WINNER", "FORCED ERROR", "UNFORCED ERROR", "ACE", "DOUBLE FAULT"}


def _infosys_file(path: str) -> list[dict]:
    """One summary per record of an Infosys year file: ids, names, date, and the per-point field counts."""
    opener = gzip.open if path.endswith(".gz") else open
    out = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            ra = rec.get("rally_analysis") if isinstance(rec.get("rally_analysis"), dict) else {}
            n = rally = ending = speed = placement = net = stroke = 0
            buckets = np.zeros(11, dtype="int64")
            for cat in ra.get("rallyData") or []:
                if not isinstance(cat, dict):
                    continue
                shot_no = INFOSYS_SHOT_NO.get(cat.get("name"), 0)
                for side in ("t1err", "t1win", "t2err", "t2win"):
                    for p in cat.get(side) or []:
                        if not isinstance(p, dict):
                            continue
                        n += 1
                        buckets[shot_no] += 1
                        rally += shot_no > 0
                        ending += (p.get("pointEndType") or "") in INFOSYS_ENDINGS
                        sp = p.get("serveSpeed")
                        speed += sp not in (None, 0, "", "0", "NA")
                        placement += p.get("serveDir") not in (None, "", "NA")
                        net += bool(p.get("t1NetPoint")) or bool(p.get("t2NetPoint"))
                        stroke += (p.get("hand") or "NA") not in ("NA", "") or (p.get("shotType") not in (None, "", "NA"))
            ks = rec.get("keystats") if isinstance(rec.get("keystats"), dict) else {}
            names = set()
            set_stats = ks.get("setStats") if isinstance(ks.get("setStats"), dict) else {}
            for sk, rows in set_stats.items():
                for r in rows or []:
                    if not isinstance(r, dict):
                        continue
                    v1, v2 = str(r.get("player1") or "").strip(), str(r.get("player2") or "").strip()
                    if v1 not in ("", "0", "0%", "NA") or v2 not in ("", "0", "0%", "NA"):
                        names.add(r.get("name"))
            sum_ = rec.get("stroke_summary") if isinstance(rec.get("stroke_summary"), dict) else {}
            ss = sum_.get("rallyShots") if isinstance(sum_.get("rallyShots"), dict) else {}
            stroke_tot = 0
            for tot in ss.get("totalPointsCount") or []:
                if not isinstance(tot, dict):
                    continue
                for wing in ("forehand", "backhand"):
                    w = tot.get(wing) if isinstance(tot.get(wing), dict) else {}
                    for k in ("player1Wins", "player1Frcs", "player1Unfs", "player2Wins", "player2Frcs", "player2Unfs"):
                        try:
                            stroke_tot += int(w.get(k) or 0)
                        except (TypeError, ValueError):
                            pass
            ms = rec.get("match_status") if isinstance(rec.get("match_status"), dict) else {}
            mc = ms.get("matchCenter") if isinstance(ms.get("matchCenter"), dict) else {}
            out.append({
                "year": str(rec.get("year")), "tournament_id": str(rec.get("tournament_id")),
                "match_code": str(rec.get("match_id")), "match_date": rec.get("match_date"),
                "name1": rec.get("player1_name"), "name2": rec.get("player2_name"),
                "id1": rec.get("player1_id"), "id2": rec.get("player2_id"),
                "n_points": n, "cnt_rally": rally, "cnt_ending": ending, "cnt_speed": speed,
                "cnt_placement": placement, "cnt_net": net, "cnt_stroke": stroke,
                "rally_buckets": buckets.tolist(),
                "ks_winners": "Winners" in names, "ks_unforced": "Unforced Errors" in names,
                "ks_net": "Net Points Won" in names, "ks_speed": "1st Serve Average Speed" in names,
                "stroke_totals": stroke_tot, "cv_flag": bool(mc.get("courtVision")),
                "status": ms.get("matchStatus"), "file": Path(path).parent.name})
    return out


def infosys(workers: int = 5) -> pd.DataFrame:
    paths = sorted(str(p) for d in ("infosys_deep", "infosys_full") for p in (S.HANDOFF / d).glob("*_data.jsonl*"))
    recs = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for part in ex.map(_infosys_file, paths):
            recs.extend(part)
    f = pd.DataFrame(recs)
    S.log(f"  infosys: {len(f)} records in {len(paths)} files")
    # infosys_deep and infosys_full overlap; keep, per match, the record with the most points (as the data map does),
    # with the key statistics' flags from either
    f["key"] = f["year"] + "_" + f["tournament_id"] + "_" + f["match_code"]
    flags = f.groupby("key")[["ks_winners", "ks_unforced", "ks_net", "ks_speed", "cv_flag"]].max()
    f = f.sort_values(["key", "n_points", "stroke_totals"], ascending=[True, False, False]).drop_duplicates("key")
    f = f.drop(columns=["ks_winners", "ks_unforced", "ks_net", "ks_speed", "cv_flag"]).merge(flags, on="key")
    singles = f["match_code"].str.match(r"^[MQ]S")
    note("infosys", f"{len(f)} distinct matches ({int(singles.sum())} singles: codes MS and QS); doubles left out")
    f = f[singles].copy()
    qual = f["match_code"].str.startswith("Q")
    f["totals"] = np.where(f["ks_winners"] & f["ks_unforced"], "winners_unforced", None)
    rows = pd.DataFrame({
        "key": f["key"], "tour": "M", "d": M.to_date(f["match_date"], "%Y-%m-%d"),
        "year": pd.to_numeric(f["year"], errors="coerce"), "name1": f["name1"], "name2": f["name2"],
        "id1": f["id1"], "id2": f["id2"], "draw": np.where(qual, "qual", "main"), "n_points": f["n_points"],
        **{c: f[c] for c in ["cnt_rally", "cnt_ending", "cnt_speed", "cnt_placement", "cnt_net", "cnt_stroke"]},
        "totals": f["totals"], "ks_net": f["ks_net"], "ks_speed": f["ks_speed"], "stroke_totals": f["stroke_totals"],
        "cv_flag": f["cv_flag"], "rally_buckets": f["rally_buckets"], "status": f["status"],
        "tournament_id": f["tournament_id"], "match_code": f["match_code"]})
    note("infosys", "Rally length is the shot that ended the point (serve, return, 3rd ... 8th, then '9+ odd' and "
                    "'10+ even'); serve speed, serve direction, net flags and stroke per point; per-set key statistics "
                    "(winners, unforced errors, net points won, serve speeds) are counted as match totals")
    return frame("infosys", rows.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# Hawk-Eye Court Vision, ATP (every stroke tracked), placed through the Infosys record of the same match

def _cv_file(path: str) -> dict:
    try:
        rec = json.load(gzip.open(path, "rt", encoding="utf-8"))
    except (OSError, EOFError, json.JSONDecodeError):
        return {"path": path, "n_points": 0, "tracked": 0, "readable": False}
    n = tracked = 0
    for cv in rec.get("courtVisionData") or []:
        pts = cv.get("a50") or {}
        for p in pts.values():
            n += 1
            traj = p.get("a12") or []
            tracked += len(traj) > 0
    return {"path": path, "n_points": n, "tracked": tracked, "readable": True}


def court_vision(info: pd.DataFrame, workers: int = 5) -> pd.DataFrame:
    paths = sorted(str(p) for p in (S.HANDOFF / "court_vision").rglob("*.json.gz"))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        recs = list(ex.map(_cv_file, paths, chunksize=50))
    f = pd.DataFrame(recs)
    f["year"] = f["path"].map(lambda p: Path(p).parent.name)
    f["stem"] = f["path"].map(lambda p: Path(p).name[:-8])
    f["key"] = f["year"] + "_" + f["stem"]
    names = info.set_index("key")[["d", "name1", "name2", "id1", "id2", "draw"]]
    f = f.join(names, on="key")
    note("court_vision", f"{len(f)} files; {int(f['name1'].notna().sum())} placed through an Infosys record of the same "
                         f"year, tournament and match code; {int((~f['readable']).sum())} unreadable")
    rows = pd.DataFrame({"key": f["key"], "tour": "M", "d": f["d"], "year": pd.to_numeric(f["year"]),
                         "name1": f["name1"], "name2": f["name2"], "id1": f["id1"], "id2": f["id2"],
                         "draw": f["draw"], "n_points": f["n_points"], "cnt_tracking": f["tracked"]})
    note("court_vision", "Counted as ball tracking only here; its per-stroke fields (speeds, spin, positions) use "
                         "obfuscated keys that a later stage would decode against the readable Slam copy")
    return frame("court_vision", rows.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# Grand Slam point-by-point (Sackmann's copies of the IBM and Infosys feeds, 2011-2024)

SLAM_OF = {"ausopen": "AO", "frenchopen": "RG", "wimbledon": "W", "usopen": "USO"}


def slam_starts(universe: pd.DataFrame) -> dict:
    """(year, slam) -> the Stage 0 tournament date of that Grand Slam's main draw."""
    gs = universe[universe["level"].eq("GS")]
    out = {}
    for slam, pattern in M.SLAM_PATTERNS.items():
        hit = gs[gs["tname"].fillna("").str.lower().str.contains(pattern)]
        for year, d in hit.groupby("year")["d"].min().items():
            out[(int(year), slam)] = d
    return out


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0)


def slam_pbp(starts: dict) -> pd.DataFrame:
    parts = []
    base = S.DUMP / "points" / "sackmann_archive" / "slam_pointbypoint"
    for mpath in sorted(base.glob("*-matches.parquet")):
        year = int(mpath.name[:4])
        slam = SLAM_OF.get(mpath.name.split("-")[1])
        ppath = mpath.with_name(mpath.name.replace("-matches", "-points"))
        m = pd.read_parquet(mpath)
        num = m["match_num"].fillna("").astype(str)
        singles = num.str[:1].isin(["1", "2"]) | num.str[:2].isin(["MS", "WS"])
        m = m[singles].copy()
        if not ppath.exists() or m.empty:
            continue
        cols = [c for c in pq.read_schema(ppath).names if not c.startswith("_")]
        p = pd.read_parquet(ppath, columns=cols)
        p = p[p["match_id"].isin(m["match_id"])]
        if p.empty:
            continue
        def has(c):
            return nonblank(p[c]) if c in p else pd.Series(False, index=p.index)
        def flag(c):
            return _num(p[c]).gt(0) if c in p else pd.Series(False, index=p.index)
        rally = (_num(p["Rally"]).gt(0) if "Rally" in p else False) | (_num(p["RallyCount"]).gt(0) if "RallyCount" in p else False)
        rally = rally if isinstance(rally, pd.Series) else pd.Series(False, index=p.index)
        ending = (flag("P1Ace") | flag("P2Ace") | flag("P1DoubleFault") | flag("P2DoubleFault") | flag("P1Winner")
                  | flag("P2Winner") | flag("P1UnfErr") | flag("P2UnfErr") | flag("P1ForcedError") | flag("P2ForcedError"))
        flags = {"rally": rally, "ending": ending, "speed": _num(p.get("Speed_KMH", pd.Series(0, index=p.index))).gt(0),
                 "placement": has("ServeWidth") | has("Serve_Direction"), "net": flag("P1NetPoint") | flag("P2NetPoint"),
                 "return": has("ReturnDepth"), "stroke": has("WinnerShotType") | flag("Winner_FH") | flag("Winner_BH")}
        pm = per_match(p, "match_id", flags)
        mm = m.merge(pm, on="match_id", how="inner")
        num = mm["match_num"].fillna("").astype(str)
        digit = np.where(num.str[:1].str.isdigit(), num.str[1:2], num.str[2:3])
        parts.append(pd.DataFrame({
            "key": mm["match_id"], "tour": np.where(num.str[:1].isin(["1", "M"]), "M", "W"),
            "d": starts.get((year, slam)), "year": year, "name1": mm["player1"], "name2": mm["player2"],
            "round": [M.slam_round(x, False) for x in digit], "draw": "main", "level": "GS",
            "n_points": mm["n_points"], **{c: mm[c] for c in CNT if c in mm}}))
    out = pd.concat(parts, ignore_index=True)
    note("slam_pbp", "Ending counts points flagged ace, double fault, winner, unforced or forced error; net play counts "
                     "points with a net-point flag; which columns are filled varies by Slam and year")
    return frame("slam_pbp", out.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# Wimbledon and US Open SlamTracker feeds (2019, 2021-2026; 2022-2026)

def slamtracker() -> pd.DataFrame:
    parts = []
    for site, slam in (("wimbledon", "W"), ("usopen", "USO")):
        m = pd.read_parquet(S.DUMP / "points" / site / "matches.parquet")
        m = m[m["event"].isin(["MS", "LS", "WS", "QS", "RS", "MQ", "WQ"])]
        m = m[~m["entry.status"].fillna("").astype(str).str.lower().str.contains("walkover")]
        p = pd.read_parquet(S.DUMP / "points" / site / "points.parquet",
                            columns=["year", "event", "match_id", "RallyCount", "Speed_KMH", "ServeWidth", "ReturnDepth",
                                     "Winner", "UnforcedError", "Ace", "DoubleFault", "NetPoint", "WinnerShotType",
                                     "PointWinner"])
        p = p[_num(p["PointWinner"]).gt(0)]
        flags = {"rally": _num(p["RallyCount"]).gt(0),
                 "ending": _num(p["Winner"]).gt(0) | _num(p["UnforcedError"]).gt(0) | _num(p["Ace"]).gt(0)
                           | _num(p["DoubleFault"]).gt(0),
                 "speed": _num(p["Speed_KMH"]).gt(0), "placement": nonblank(p["ServeWidth"]),
                 "net": _num(p["NetPoint"]).gt(0), "return": nonblank(p["ReturnDepth"]),
                 "stroke": nonblank(p["WinnerShotType"])}
        pm = per_match(p, ["year", "event", "match_id"], flags)
        mm = m.merge(pm, on=["year", "event", "match_id"], how="inner")
        qual = mm["event"].isin(["QS", "RS", "MQ", "WQ"])
        parts.append(pd.DataFrame({
            "key": site + "_" + mm["year"].astype(str) + "_" + mm["event"] + "_" + mm["match_id"].astype(str),
            "tour": np.where(mm["event"].isin(["MS", "QS", "MQ"]), "M", "W"),
            "d": pd.to_datetime(pd.to_numeric(mm["entry.epoch"], errors="coerce"), unit="ms", errors="coerce"),
            "year": pd.to_numeric(mm["year"], errors="coerce"),
            "name1": mm["entry.team1.firstNameA"].fillna("") + " " + mm["entry.team1.lastNameA"].fillna(""),
            "name2": mm["entry.team2.firstNameA"].fillna("") + " " + mm["entry.team2.lastNameA"].fillna(""),
            "round": [M.slam_round(c, q) for c, q in zip(mm["entry.roundCode"], qual)],
            "draw": np.where(qual, "qual", "main"), "level": np.where(qual, "GSQ", "GS"),
            "n_points": mm["n_points"], **{c: mm[c] for c in CNT if c in mm}}))
    out = pd.concat(parts, ignore_index=True)
    note("slamtracker", "Ending counts points flagged winner, unforced error, ace or double fault (forced errors are not "
                        "flagged in these feeds, so about two thirds of points carry an ending)")
    return frame("slamtracker", out.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# Hawk-Eye Court Vision at the Australian Open and Roland Garros (hawkilol copy)

def slam_tracking(starts: dict) -> pd.DataFrame:
    base = S.DUMP / "points" / "slam_ball_tracking"
    m = pd.read_parquet(base / "matches.parquet")
    # Roland Garros codes carry no year (SM001 recurs every year): the key is the Slam, the year and the code
    tkey = lambda f: f["slam"].astype(str) + "_" + f["year"].astype(str) + "_" + f["match_id"].astype(str)
    m["match_id"] = tkey(m)
    p = pd.concat([pd.read_parquet(x, columns=["match_id", "slam", "year", "rally_length", "point_end_type",
                                                "serve_speed_kph", "serve_dir", "serve_return_bounce_x",
                                                "last_stroke_type", "point_winner_id"])
                   for x in sorted((base / "points").glob("*.parquet"))], ignore_index=True)
    p["match_id"] = tkey(p)
    speed = pd.to_numeric(p["serve_speed_kph"].astype(str).str.extract(r"([\d.]+)")[0], errors="coerce")
    flags = {"rally": _num(p["rally_length"]).gt(0), "ending": nonblank(p["point_end_type"]),
             "speed": speed.fillna(0).gt(0), "placement": nonblank(p["serve_dir"]),
             "return": nonblank(p["serve_return_bounce_x"]), "stroke": nonblank(p["last_stroke_type"])}
    pm = per_match(p, "match_id", flags)
    jp = pd.concat([pd.read_parquet(x, columns=["match_id", "slam", "year", "ballHitCordinate"])
                    for x in sorted((base / "json_points").glob("*.parquet"))], ignore_index=True)
    jp["match_id"] = tkey(jp)
    tr = jp.assign(t=nonblank(jp["ballHitCordinate"])).groupby("match_id")["t"].agg(["sum", "size"])
    mm = m.merge(pm, on="match_id", how="left")
    mm["cnt_tracking"] = mm["match_id"].map(tr["sum"]).fillna(0)
    mm["n_points"] = mm["n_points"].fillna(mm["match_id"].map(tr["size"])).fillna(0)
    year = pd.to_numeric(mm["year"], errors="coerce")
    first = pd.to_datetime(pd.Series([starts.get((int(y), s)) for y, s in zip(year, mm["slam"])], index=mm.index))
    code = mm["match_id"].fillna("").str.split("_").str[-1]          # the code after the Slam and year
    out = pd.DataFrame({
        "key": mm["match_id"], "tour": mm["tour"], "d": first + pd.Timedelta(days=3), "year": year,
        "name1": mm["player1"], "name2": mm["player2"], "id1": mm["player1_id"], "id2": mm["player2_id"],
        "round": [M.court_vision_round(s, c) for s, c in zip(mm["slam"], code)], "draw": "main", "level": "GS",
        "n_points": mm["n_points"], **{c: mm[c] for c in CNT if c in mm}})
    note("slam_tracking", "Dated three days after the Slam's first day, as the data map does (the copy has no match "
                          "dates); every stroke's trajectory only for 2022-2024")
    return frame("slam_tracking", out.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# Australian Open match centre 2026 (and Wayback captures)

def ausopen() -> pd.DataFrame:
    m = pd.read_parquet(S.DUMP / "points" / "ausopen" / "matches.parquet")
    m = m[m["event"].isin(["MS", "WS", "MQ", "WQ"])]
    p = pd.read_parquet(S.DUMP / "points" / "ausopen" / "points.parquet",
                        columns=["record_key", "type", "outcome", "stroke_side"])
    p = p[p["type"].eq("point")]
    flags = {"ending": p["outcome"].isin(["forced_error", "unforced_error", "winner", "ace", "double_fault",
                                          "service_winner"]),
             "stroke": nonblank(p["stroke_side"])}
    pm = per_match(p, "record_key", flags)
    mm = m.merge(pm, on="record_key", how="inner")
    qual = mm["event"].isin(["MQ", "WQ"])
    out = pd.DataFrame({
        "key": mm["record_key"], "tour": np.where(mm["event"].isin(["MS", "MQ"]), "M", "W"),
        "d": M.to_date(mm["date"]), "year": pd.to_numeric(mm["year"], errors="coerce"),
        "name1": mm["team1_names"], "name2": mm["team2_names"],
        "round": [M.slam_round(c, q) for c, q in zip(mm["round_name"], qual)],
        "draw": np.where(qual, "qual", "main"), "level": np.where(qual, "GSQ", "GS"),
        "n_points": mm["n_points"], **{c: mm[c] for c in CNT if c in mm}})
    return frame("ausopen", out.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# TDI Tennis Results (ATP and Challenger, from mid-2025)

def tdi() -> pd.DataFrame:
    m = pd.read_parquet(S.DUMP / "points" / "tdi" / "matches.parquet",
                        columns=["match_id", "draw_type", "draw", "level", "completed_on", "team_a_names",
                                 "team_b_names", "team_a_atp_ids", "team_b_atp_ids", "points"])
    m = m[m["draw_type"].eq("singles")]
    p = pd.read_parquet(S.DUMP / "points" / "tdi" / "points.parquet",
                        columns=["match_id", "outcome", "total_shots", "winning_shot_type", "situation", "serve"])
    flags = {"rally": _num(p["total_shots"]).gt(0),
             "ending": p["outcome"].isin(["winner", "forced", "unforced"]) | p["serve"].isin(["ACE", "DOUBLE FAULT"]),
             "net": p["situation"].fillna("").astype(str).str.contains("net"),
             "stroke": nonblank(p["winning_shot_type"])}
    pm = per_match(p, "match_id", flags)
    mm = m.merge(pm, on="match_id", how="inner")
    qual = mm["draw"].fillna("").eq("qualifying")
    level = np.where(mm["level"].eq("challenger"), np.where(qual, "CHQ", "CH"), None)
    out = pd.DataFrame({
        "key": mm["match_id"], "tour": "M", "d": M.to_date(mm["completed_on"].astype(str).str[:10], "%Y-%m-%d"),
        "name1": mm["team_a_names"], "name2": mm["team_b_names"], "id1": mm["team_a_atp_ids"],
        "id2": mm["team_b_atp_ids"], "draw": np.where(qual, "qual", "main"), "level": level,
        "n_points": mm["n_points"], **{c: mm[c] for c in CNT if c in mm}})
    out["year"] = out["d"].dt.year
    return frame("tdi", out.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# SirGenkii infotennis (ATP Stats Centre, 27 Dec 2024 - 7 Apr 2025)

def sirgenkii() -> pd.DataFrame:
    base = S.DUMP / "points" / "sirgenkii_infotennis"
    res = pd.read_parquet(base / "atp_results.parquet")
    cal = pd.read_parquet(base / "atp_calendars.parquet", columns=["tournament_id", "year", "date_start"])
    ra = pd.read_parquet(base / "atp_rally_analysis.parquet",
                         columns=["tournament_id", "year", "match_id", "point_id", "shot_number", "point_end_type",
                                  "serve_speed", "serve_dir", "shot_type", "p1_net_point", "p2_net_point"])
    for t in (res, cal, ra):
        for c in ("tournament_id", "year", "match_id"):
            if c in t:
                t[c] = t[c].astype(str)
    ra = ra.drop_duplicates(["tournament_id", "year", "match_id", "point_id"])
    flags = {"rally": _num(ra["shot_number"]).gt(0),
             "ending": ra["point_end_type"].fillna("").astype(str).str.upper().isin(INFOSYS_ENDINGS),
             "speed": _num(ra["serve_speed"]).gt(0), "placement": nonblank(ra["serve_dir"]),
             "net": ra["p1_net_point"].astype(str).str.lower().isin(["true", "1"])
                    | ra["p2_net_point"].astype(str).str.lower().isin(["true", "1"]),
             "stroke": nonblank(ra["shot_type"])}
    pm = per_match(ra, ["tournament_id", "year", "match_id"], flags)
    res = res[res["match_id"].fillna("").astype(str).str.upper().str.match(r"^[MQ]S")]
    mm = res.merge(pm, on=["tournament_id", "year", "match_id"], how="inner")
    mm = mm.merge(cal.drop_duplicates(["tournament_id", "year"]), on=["tournament_id", "year"], how="left")
    qual = mm["match_id"].astype(str).str.upper().str.startswith("Q")
    # the calendar gives each event's dates as '2025.02.03 - 2025.02.09'; several first days are weeks early (Miami
    # '2025.03.01 - 2025.03.30', Doha '2025.02.01 - 2025.02.22') while the last days are right, so a match is dated by
    # its event's last day, inside the linker's window of 21 days after the Stage 0 tournament date
    start = M.to_date(mm["date_start"].fillna("").astype(str).str[-10:], "%Y.%m.%d")
    out = pd.DataFrame({
        "key": mm["year"].astype(str) + "_" + mm["tournament_id"].astype(str) + "_" + mm["match_id"].astype(str),
        "tour": "M", "d": start, "name1": mm["player1_name"], "name2": mm["player2_name"],
        "id1": mm["player1_id"], "id2": mm["player2_id"], "draw": np.where(qual, "qual", "main"),
        "n_points": mm["n_points"], **{c: mm[c] for c in CNT if c in mm}})
    out["year"] = out["d"].dt.year
    return frame("sirgenkii", out.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# WTA official API, advanced statistics (match totals: winners, unforced and forced errors by wing, net approaches)

WTA_TOTALS = {
    "ending": ["shotStats.winnersTotal", "shotStats.unforcedErrorsTotal", "shotStats.forcedErrorsTotal"],
    "net": ["netPlayStats.netApproaches", "netPlayStats.netApproachesSuccessful"],
    "stroke": ["shotStats.winnersForehand", "shotStats.winnersBackhand", "shotStats.unforcedErrorsForehand",
               "shotStats.unforcedErrorsBackhand"],
}


def _wta_adv(path: str) -> dict:
    try:
        doc = json.load(gzip.open(path, "rt", encoding="utf-8"))
    except (OSError, EOFError, json.JSONDecodeError):
        return {"path": path, "readable": False}
    if isinstance(doc, list):
        doc = doc[0] if doc else {}
    out = {"path": path, "readable": True}
    for fam, keys in WTA_TOTALS.items():
        ok = True
        tot = 0
        for team in ("teamA", "teamB"):
            mt = ((doc or {}).get(team) or {}).get("matchTotal") or {}
            for k in keys:
                a, b = k.split(".")
                v = (mt.get(a) or {}).get(b)
                if v is None:
                    ok = False
                else:
                    try:
                        tot += float(v)
                    except (TypeError, ValueError):
                        ok = False
        out[f"has_{fam}"] = ok and tot > 0
    return out


def wta_advanced(workers: int = 5) -> pd.DataFrame:
    lists = []
    for p in sorted((S.DUMP / "points" / "wta" / "matches").glob("*.parquet")):
        t = pq.ParquetFile(p).read(columns=["tournament_id", "match_id", "tier", "draw", "MatchTimeStamp", "RoundID",
                                            "PlayerNameFirstA", "PlayerNameLastA", "PlayerNameFirstB", "PlayerNameLastB",
                                            "PlayerIDA", "PlayerIDB", "DrawMatchType", "MatchState"]).to_pandas()
        t["list_year"] = p.stem
        lists.append(t)
    lists = pd.concat(lists, ignore_index=True)
    lists = lists[lists["DrawMatchType"].eq("S") | lists["match_id"].astype(str).str.match(r"^[LQ]S")]
    root = S.RAW / "point_sources" / "wta" / "matches"
    lists["path"] = [str(root / f"{t}_{y}" / str(m) / "advanced-stats.json.gz")
                     for t, y, m in zip(lists["tournament_id"], lists["list_year"], lists["match_id"])]
    exists = lists["path"].map(lambda x: Path(x).exists())
    note("wta_advanced", f"{len(lists)} singles matches listed 2019-2026; {int(exists.sum())} with an advanced-"
                         f"statistics file on disk (raw files read directly; the staged table holds a sample only; "
                         f"the download chain that writes other files beside them was left running)")
    todo = lists[exists]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        recs = list(ex.map(_wta_adv, todo["path"].tolist(), chunksize=200))
    r = pd.DataFrame(recs).set_index("path")
    todo = todo.join(r, on="path")
    qual = todo["draw"].fillna("").astype(str).str.lower().str.startswith("q") | todo["match_id"].astype(str).str.startswith("Q")
    out = pd.DataFrame({
        "key": todo["tournament_id"].astype(str) + "_" + todo["list_year"].astype(str) + "_" + todo["match_id"].astype(str),
        "tour": "W", "d": M.to_date(todo["MatchTimeStamp"]),
        "name1": todo["PlayerNameFirstA"].fillna("") + " " + todo["PlayerNameLastA"].fillna(""),
        "name2": todo["PlayerNameFirstB"].fillna("") + " " + todo["PlayerNameLastB"].fillna(""),
        "id1": todo["PlayerIDA"], "id2": todo["PlayerIDB"], "draw": np.where(qual, "qual", "main"),
        "round": todo["RoundID"], "n_points": 0, "totals": "advanced",
        **{f"cnt_{fam}": todo[f"has_{fam}"].fillna(False).astype(int) for fam in WTA_TOTALS}})
    out["year"] = out["d"].dt.year
    return frame("wta_advanced", out.to_dict("records"))


# ------------------------------------------------------------------------------------------------
# Families carried, linking, summaries

def carried(f: pd.DataFrame) -> pd.DataFrame:
    """has_<family>: the match carries the family (THRESHOLD, or the match totals)."""
    f = f.copy()
    n = f["n_points"].where(f["n_points"] > 0)
    for fam in FAM:
        c = f[f"cnt_{fam}"]
        if THRESHOLD[fam] is None:
            has = c > 0
        else:
            has = (c / n) >= THRESHOLD[fam]
        f[f"has_{fam}"] = has.fillna(False).astype(bool)
    totals = f["totals"].notna()
    # match totals: the WTA's advanced statistics carry a family when the total is recorded (cnt = 1)
    adv = f["source"].eq("wta_advanced")
    for fam in ("ending", "net", "stroke"):
        f.loc[adv, f"has_{fam}"] = f.loc[adv, f"cnt_{fam}"] > 0
    # Infosys key statistics: winners and unforced errors, net points won, serve speeds per set
    inf = f["source"].eq("infosys")
    f.loc[inf & totals, "has_ending"] = True
    if "ks_net" in f:
        f.loc[inf & f["ks_net"].fillna(False).astype(bool), "has_net"] = True
    if "ks_speed" in f:
        f.loc[inf & f["ks_speed"].fillna(False).astype(bool), "has_speed"] = True
    if "stroke_totals" in f:
        f.loc[inf & (pd.to_numeric(f["stroke_totals"], errors="coerce").fillna(0) > 0), "has_stroke"] = True
    return f


def summarise(f: pd.DataFrame) -> pd.DataFrame:
    g = f.assign(linked=f["match_id"].notna(), oriented=f["a1"].notna())
    agg = {"matches": ("key", "size"), "linked": ("linked", "sum"), "oriented": ("oriented", "sum"),
           "points": ("n_points", "sum")}
    for fam in FAM:
        agg[f"has_{fam}"] = (f"has_{fam}", "sum")
        agg[f"linked_{fam}"] = (f"lk_{fam}", "sum")
    for fam in FAM:
        g[f"lk_{fam}"] = g[f"has_{fam}"] & g["linked"]
    return g.groupby(["source", "tour", "year"], dropna=False).agg(**agg).reset_index()


LOADERS = ["mcp", "infosys", "court_vision", "slam_pbp", "slamtracker", "slam_tracking", "ausopen", "tdi", "sirgenkii",
           "wta_advanced"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated loaders (default: all)")
    ap.add_argument("--workers", type=int, default=5)
    args = ap.parse_args()
    only = [x for x in args.only.split(",") if x] or LOADERS
    S.OUT.mkdir(parents=True, exist_ok=True)
    S.log("Stage 0 universe")
    linker = S.Stage0Linker()
    starts = slam_starts(linker.universe)
    S.log(f"  {len(linker.universe)} Stage 0 matches ready to link")
    frames = {}
    info = None
    for name in only:
        S.log(f"reading {name}")
        if name == "mcp":
            f = mcp()
        elif name == "infosys":
            f = info = infosys(args.workers)
        elif name == "court_vision":
            if info is None:
                info = infosys(args.workers)
            f = court_vision(info, args.workers)
        elif name == "slam_pbp":
            f = slam_pbp(starts)
        elif name == "slamtracker":
            f = slamtracker()
        elif name == "slam_tracking":
            f = slam_tracking(starts)
        elif name == "ausopen":
            f = ausopen()
        elif name == "tdi":
            f = tdi()
        elif name == "sirgenkii":
            f = sirgenkii()
        elif name == "wta_advanced":
            f = wta_advanced(args.workers)
        else:
            raise SystemExit(f"unknown loader {name}")
        S.log(f"  {len(f)} matches; linking")
        f = linker.link(f)
        S.log(f"  linked {int(f['match_id'].notna().sum())} of {len(f)}; oriented {int(f['a1'].notna().sum())}")
        frames[name] = carried(f)
    allf = pd.concat(frames.values(), ignore_index=True)
    keep = ["source", "key", "tour", "year", "d", "name1", "name2", "id1", "id2", "round", "draw", "level", "totals",
            "n_points"] + CNT + [f"has_{x}" for x in FAM] + ["match_id", "a1"]
    extra = [c for c in ("rally_buckets", "tournament_id", "match_code", "status", "cv_flag") if c in allf]
    out = allf[keep + extra].copy()
    out["a1"] = out["a1"].astype("boolean")
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    for c in ("key", "name1", "name2", "id1", "id2", "round", "draw", "level", "totals", "match_id", "tournament_id",
              "match_code", "status"):
        if c in out:
            out[c] = out[c].astype(object).where(out[c].notna(), None).map(lambda v: None if v is None else str(v))
    if "rally_buckets" in out:
        out["rally_buckets"] = out["rally_buckets"].map(lambda v: json.dumps(v) if isinstance(v, list) else None)
    path = S.OUT / "stage0_source_matches.parquet"
    if args.only and path.exists():
        old = pd.read_parquet(path)
        out = pd.concat([old[~old["source"].isin(only)], out], ignore_index=True)
    out.to_parquet(path, index=False)
    summ = summarise(out)
    summ.to_csv(S.OUT / "stage0_sources.csv", index=False)
    notes_path = S.OUT / "stage0_sources.json"
    old_notes = json.loads(notes_path.read_text(encoding="utf-8")).get("notes", {}) if (args.only and notes_path.exists()) else {}
    old_notes.update(NOTES)
    totals = summ.groupby("source")[["matches", "linked", "oriented", "points"] + [f"has_{x}" for x in FAM]].sum()
    notes_path.write_text(json.dumps({"notes": old_notes, "thresholds": THRESHOLD,
                                      "by_source": totals.reset_index().to_dict("records")}, indent=1, default=int),
                          encoding="utf-8")
    S.log(f"wrote {path} ({len(out)} rows), stage0_sources.csv, stage0_sources.json")
    print(totals.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
