"""The common point table: every point-level source in one schema, so that every statistic is computed by one code path.

One row per point played (first-serve faults and lets are not rows; walkover and pre-match rows are dropped):

    source, key     the source and its match key (as in stage0_source_matches.parquet, which links it to Stage 0)
    seq             the point's order in the match (0-based, gapless)
    set_no          the set (1-based)
    game_key        the game's order in the match (0-based); a game is a run of points with one (set, game) label
    server, winner  1 or 2: the source's player 1 (name1 in stage0_source_matches) or player 2
    serve_no        1 (first serve in, or an ace or fault-free point on the first serve) or 2 (the point was played on
                    the second serve, double faults included); 0 unknown
    rally           shots in the point, the serve counted as shot 1 and an erring shot counted (an ace 1, a double fault
                    0, a return error 2, a return winner 2): the convention of the volunteer charts and of Infosys's
                    groups; -1 unknown. The IBM feeds (Sackmann's Slam files, SlamTracker), Hawk-Eye's copy at the Slams
                    and TDI count only shots that landed in, so points that end in an error get 1 added (checked point
                    by point on matches two sources hold: shot_level Stage 1). Infosys and SirGenkii group long points as
                    "9+ odd" (stored 9) and "10+ even" (stored 10)
    end             how the point ended: 1 ace, 2 double fault, 3 winner, 4 forced error, 5 unforced error, 0 unknown. A
                    serve that wins without being an ace (the returner touched it but could not return it; a 'service
                    winner') is a forced error by the returner on shot 2 in every source, as the IBM feeds and Hawk-Eye
                    classify it (code 6 is kept for compatibility and no longer produced)
    ender           1 or 2: the player who hit the point's last shot (the winner's hitter, the erring player, the server
                    on aces and double faults); 0 unknown
    speed           the speed of the serve that started the point, km/h; NaN unknown
    place           where that serve landed: 1 T (centre line), 2 body, 3 wide; 0 unknown
    net1, net2      whether player 1 / player 2 came to the net in the point: 1 or 0; -1 unknown
    ret_deep        whether the return landed deep (the back of the court): 1 or 0; -1 unknown or no return in play
    wing            the wing of the point's last shot: 1 forehand, 2 backhand; 0 unknown

Each adapter documents how its source's fields map onto this schema. The semantics were read from the data (shot_level
Stage 1 write-up, section "Sources"), e.g. an ace's rally count is 1 and a double fault's 0 in the IBM feeds.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import common as S  # noqa: E402

END = {"unknown": 0, "ace": 1, "df": 2, "winner": 3, "forced": 4, "unforced": 5, "svc": 6}
COLUMNS = ["source", "key", "seq", "set_no", "game_key", "server", "winner", "serve_no", "rally", "end", "ender", "speed",
           "place", "net1", "net2", "ret_deep", "wing"]
INT8 = ["server", "winner", "serve_no", "end", "ender", "place", "net1", "net2", "ret_deep", "wing"]


def num(s) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def finish(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Order, keep the schema, fill unknowns, add seq and game_key (a new game whenever the (set, game) label changes
    between consecutive points), drop matches whose points lack a server or winner."""
    df = df.copy()
    df["source"] = source
    for c, fill in (("serve_no", 0), ("rally", -1), ("end", 0), ("ender", 0), ("place", 0), ("net1", -1), ("net2", -1),
                    ("ret_deep", -1), ("wing", 0)):
        if c not in df:
            df[c] = fill
        df[c] = num(df[c]).fillna(fill)
    if "speed" not in df:
        df["speed"] = np.nan
    df["speed"] = num(df["speed"])
    df.loc[(df["speed"] <= 40) | (df["speed"] > 270), "speed"] = np.nan
    df = df[df["server"].isin([1, 2]) & df["winner"].isin([1, 2])].copy()
    df = df.sort_values(["key", "_order"], kind="mergesort").reset_index(drop=True)
    df["seq"] = df.groupby("key").cumcount().astype("int32")
    lab = df["set_no"].astype(str) + "|" + df["game_label"].astype(str)
    new = (lab != lab.shift()) | (df["key"] != df["key"].shift())
    df["game_key"] = (new.astype("int32").groupby(df["key"]).cumsum() - 1).astype("int16")
    df["set_no"] = num(df["set_no"]).fillna(0).astype("int8")
    for c in INT8:
        df[c] = df[c].astype("int8")
    df["rally"] = df["rally"].astype("int16")
    df["speed"] = df["speed"].astype("float32")
    return df[COLUMNS]


# ------------------------------------------------------------------------------------------------
# Grand Slam point-by-point (Sackmann's copies of the IBM and Infosys feeds, 2011-2024)

def slam_pbp() -> pd.DataFrame:
    """PointServer / PointWinner 1 or 2; RallyCount (or Rally, older files) counts the serve as 1, a double fault 0;
    P1Ace, P1DoubleFault, P1Winner (the player hit a winner), P1UnfErr (the player erred), P1ForcedError (the player
    made a forced error, filled in some years only); P1NetPoint (came in); ServeNumber 1/2 (from 2014) or the
    first-serve-in flags; Speed_KMH 0 when unknown; ServeWidth C (centre = T), B, BC, BW (body), W (wide); ReturnDepth D
    (deep) / ND; WinnerShotType F / B (winners only). Rows with PointNumber 0X / 0Y are pre-match rows."""
    parts = []
    base = S.DUMP / "points" / "sackmann_archive" / "slam_pointbypoint"
    for ppath in sorted(base.glob("*-points.parquet")):
        cols = [c for c in pq.read_schema(ppath).names if not c.startswith("_")]
        p = pd.read_parquet(ppath, columns=cols)
        p = p[~p["PointNumber"].astype(str).str.contains("X|Y", regex=True)]
        g = lambda c: num(p[c]).fillna(0) if c in p else pd.Series(0, index=p.index)
        d = pd.DataFrame({"key": p["match_id"].astype(str), "_order": num(p["PointNumber"]),
                          "set_no": num(p["SetNo"]), "game_label": num(p["GameNo"]),
                          "server": num(p["PointServer"]), "winner": num(p["PointWinner"])})
        rc, rr = g("RallyCount"), g("Rally")
        shots_in = rc.where(rc.gt(0), rr)                 # shots that landed in; aces 1 (0 in some AO/RG files), DF 0
        ace = g("P1Ace").gt(0) | g("P2Ace").gt(0)
        dfl = g("P1DoubleFault").gt(0) | g("P2DoubleFault").gt(0)
        w1, w2 = g("P1Winner").gt(0), g("P2Winner").gt(0)
        u1, u2 = g("P1UnfErr").gt(0), g("P2UnfErr").gt(0)
        f1, f2 = g("P1ForcedError").gt(0), g("P2ForcedError").gt(0)
        # a match whose winners and unforced errors are flagged classifies every point: the rest are forced errors by
        # the player who lost the point (checked against Hawk-Eye's and SlamTracker's classification)
        classified = (w1 | w2 | u1 | u2).groupby(d["key"]).transform("any")
        loser = 3 - d["winner"]
        end = np.select([ace, dfl, w1 | w2, u1 | u2, f1 | f2, classified],
                        [END["ace"], END["df"], END["winner"], END["unforced"], END["forced"], END["forced"]], 0)
        ender = np.select([ace | dfl, w1, w2, u1, u2, f1, f2, classified],
                          [d["server"], 1, 2, 1, 2, 1, 2, loser], 0)
        is_err = np.isin(end, [END["forced"], END["unforced"]])
        # in a match without ending flags a rally count cannot be converted (error or not is unknown)
        d["rally"] = np.select([dfl, ace, shots_in.gt(0) & (end > 0)], [0, 1, shots_in + is_err.astype(int)], -1)
        d["end"], d["ender"] = end, ender
        sn = g("ServeNumber")
        first_in = g("P1FirstSrvIn").gt(0) | g("P2FirstSrvIn").gt(0)
        second_in = g("P1SecondSrvIn").gt(0) | g("P2SecondSrvIn").gt(0)
        d["serve_no"] = np.where(sn.isin([1, 2]), sn, np.where(first_in, 1, np.where(second_in | dfl, 2, 0)))
        d["speed"] = g("Speed_KMH").where(g("Speed_KMH") > 0)
        width = p["ServeWidth"].astype(str).str.strip().str.upper() if "ServeWidth" in p else pd.Series("", index=p.index)
        d["place"] = np.select([width.eq("C"), width.isin(["B", "BC", "BW"]), width.eq("W")], [1, 2, 3], 0)
        if "P1NetPoint" in p:
            n1, n2 = g("P1NetPoint").gt(0), g("P2NetPoint").gt(0)
            # a file that never flags a net point does not record them
            recorded = (n1 | n2).groupby(d["key"]).transform("any")
            d["net1"] = np.where(recorded, n1.astype(int), -1)
            d["net2"] = np.where(recorded, n2.astype(int), -1)
        rd = p["ReturnDepth"].astype(str).str.strip().str.upper() if "ReturnDepth" in p else pd.Series("", index=p.index)
        d["ret_deep"] = np.select([rd.eq("D"), rd.eq("ND")], [1, 0], -1)
        wst = p["WinnerShotType"].astype(str).str.strip().str.upper() if "WinnerShotType" in p else pd.Series("", index=p.index)
        d["wing"] = np.where(d["end"].eq(END["winner"]), np.select([wst.eq("F"), wst.eq("B")], [1, 2], 0), 0)
        parts.append(d)
    return finish(pd.concat(parts, ignore_index=True), "slam_pbp")


# ------------------------------------------------------------------------------------------------
# Wimbledon and US Open SlamTracker feeds

SENT_END = [("double fault", END["df"]), ("an ace", END["ace"]), ("unforced error", END["unforced"]),
            ("forced error", END["forced"]), ("winner", END["winner"])]


def sentence_parts(sent: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(end, subject wins (1) or loses (0) or unknown (-1), wing) from the feeds' sentence, e.g. 'A. Gray loses the point
    with a forehand forced error', 'E. Lys wins the point with an ace'."""
    s = sent.fillna("").astype(str).str.lower()
    end = np.zeros(len(s), dtype=np.int8)
    for pat, code in reversed(SENT_END):
        end = np.where(s.str.contains(pat, regex=False), code, end)
    end = np.where(s.str.contains("forced error", regex=False) & ~s.str.contains("unforced", regex=False), END["forced"],
                   end)
    end = np.where(s.str.contains("unforced error", regex=False), END["unforced"], end)
    wins = np.select([s.str.contains(" wins the point", regex=False), s.str.contains(" loses the point", regex=False)],
                     [1, 0], -1)
    wing = np.select([s.str.contains("forehand", regex=False), s.str.contains("backhand", regex=False)], [1, 2], 0)
    return end, wins, wing


def slamtracker() -> pd.DataFrame:
    """PointServer / PointWinner 1 or 2 (0 on non-point rows); RallyCount as in Sackmann's files; Ace, Winner,
    UnforcedError hold the player (1/2) who hit them (Winner includes aces); forced errors only in the sentence; NetPoint
    1, 2 or 3 (both); ServeNumber 1/2; Speed_KMH; ServeWidth and ReturnDepth as in Sackmann's files."""
    parts = []
    for site in ("wimbledon", "usopen"):
        m = pd.read_parquet(S.DUMP / "points" / site / "matches.parquet", columns=["year", "event", "match_id"])
        m = m[m["event"].isin(["MS", "LS", "WS", "QS", "RS", "MQ", "WQ"])]
        p = pd.read_parquet(S.DUMP / "points" / site / "points.parquet",
                            columns=["year", "event", "match_id", "SetNo", "GameNo", "PointNumber", "PointServer",
                                     "PointWinner", "ServeNumber", "RallyCount", "Speed_KMH", "Ace", "DoubleFault",
                                     "Winner", "UnforcedError", "NetPoint", "WinnerShotType", "ServeWidth", "ReturnDepth",
                                     "Sentence"])
        p = p.merge(m, on=["year", "event", "match_id"], how="inner")
        p = p[num(p["PointWinner"]).isin([1, 2]) & num(p["PointServer"]).isin([1, 2])]
        key = site + "_" + p["year"].astype(str) + "_" + p["event"] + "_" + p["match_id"].astype(str)
        d = pd.DataFrame({"key": key, "_order": num(p["PointNumber"]), "set_no": num(p["SetNo"]),
                          "game_label": num(p["GameNo"]), "server": num(p["PointServer"]),
                          "winner": num(p["PointWinner"])})
        rc = num(p["RallyCount"]).fillna(-1)
        end_s, wins_s, wing_s = sentence_parts(p["Sentence"])
        ace_by, df_by = num(p["Ace"]).fillna(0), num(p["DoubleFault"]).fillna(0)
        win_by, ue_by = num(p["Winner"]).fillna(0), num(p["UnforcedError"]).fillna(0)
        end = np.select([ace_by.gt(0), df_by.gt(0), ue_by.gt(0), win_by.gt(0)],
                        [END["ace"], END["df"], END["unforced"], END["winner"]], 0)
        end = np.where(end == 0, end_s, end)
        loser = 3 - d["winner"]
        ender = np.select([ace_by.gt(0), df_by.gt(0), ue_by.gt(0), win_by.gt(0)], [ace_by, df_by, ue_by, win_by], 0)
        ender = np.where((ender == 0) & np.isin(end, [END["forced"], END["unforced"]]), loser, ender)
        ender = np.where((ender == 0) & (end == END["winner"]), d["winner"], ender)
        classified = pd.Series(end > 0, index=d.index).groupby(d["key"]).transform("mean") > 0.5
        rest = (end == 0) & classified.to_numpy()
        end = np.where(rest, END["forced"], end)
        ender = np.where(rest, loser, ender)
        d["end"], d["ender"] = end, ender
        is_err = np.isin(end, [END["forced"], END["unforced"]])
        # RallyCount counts shots that landed in (an ace 1, a double fault 0): an erring shot is added
        d["rally"] = np.select([end == END["df"], end == END["ace"], (rc > 0) & (end > 0)], [0, 1, rc + is_err.astype(int)], -1)
        d["serve_no"] = num(p["ServeNumber"]).where(num(p["ServeNumber"]).isin([1, 2]), 0)
        d["speed"] = num(p["Speed_KMH"]).where(num(p["Speed_KMH"]) > 0)
        width = p["ServeWidth"].astype(str).str.strip().str.upper()
        d["place"] = np.select([width.eq("C"), width.isin(["B", "BC", "BW"]), width.eq("W")], [1, 2, 3], 0)
        net = num(p["NetPoint"]).fillna(0)
        d["net1"] = np.select([net.eq(1) | net.eq(3), net.eq(2) | net.eq(0)], [1, 0], -1)
        d["net2"] = np.select([net.eq(2) | net.eq(3), net.eq(1) | net.eq(0)], [1, 0], -1)
        rd = p["ReturnDepth"].astype(str).str.strip().str.upper()
        d["ret_deep"] = np.select([rd.eq("D"), rd.eq("ND")], [1, 0], -1)
        wst = p["WinnerShotType"].astype(str).str.strip().str.upper()
        d["wing"] = np.where(wing_s > 0, wing_s, np.where(end == END["winner"], np.select([wst.eq("F"), wst.eq("B")],
                                                                                           [1, 2], 0), 0))
        parts.append(d)
    return finish(pd.concat(parts, ignore_index=True), "slamtracker")


# ------------------------------------------------------------------------------------------------
# Hawk-Eye Court Vision at the Australian Open and Roland Garros (hawkilol copy, per-point CSV)

def slam_tracking() -> pd.DataFrame:
    """One row per serve attempt: 'Faulty Serve' rows (first-serve faults) are dropped; the point row's serve_num is 1 or
    2. rally_length counts shots that landed in (an ace 1, a double fault 0, a return error 1), so points ending in an
    error get 1 added. point_end_type Ace / DoubleFault / Winner / Forced Error / Unforced Error; the last shot's hitter
    follows from the rally length's parity (odd: the server). serve_dir T / Body / Wide; last_hand ForeHand / BackHand."""
    base = S.DUMP / "points" / "slam_ball_tracking"
    m = pd.read_parquet(base / "matches.parquet", columns=["match_id", "slam", "year", "player1_id", "player2_id"])
    p = pd.concat([pd.read_parquet(x, columns=["match_id", "slam", "year", "set_num", "game_num", "point_num",
                                                "serve_num", "server_id", "point_winner_id", "rally_length",
                                                "point_end_type", "serve_speed_kph", "serve_dir", "last_hand"])
                   for x in sorted((base / "points").glob("*.parquet"))], ignore_index=True)
    p = p[~p["point_end_type"].astype(str).eq("Faulty Serve")]
    p = p.merge(m, on=["slam", "year", "match_id"], how="inner")
    # Roland Garros codes carry no year (SM001 recurs every year): the key is the Slam, the year and the code
    p["match_id"] = p["slam"].astype(str) + "_" + p["year"].astype(str) + "_" + p["match_id"].astype(str)
    srv = np.select([p["server_id"].eq(p["player1_id"]), p["server_id"].eq(p["player2_id"])], [1, 2], 0)
    win = np.select([p["point_winner_id"].eq(p["player1_id"]), p["point_winner_id"].eq(p["player2_id"])], [1, 2], 0)
    d = pd.DataFrame({"key": p["match_id"].astype(str),
                      "_order": num(p["set_num"]) * 1e6 + num(p["game_num"]) * 1e3 + num(p["point_num"]),
                      "set_no": num(p["set_num"]), "game_label": num(p["game_num"]), "server": srv, "winner": win})
    pet = p["point_end_type"].astype(str)
    end = np.select([pet.eq("Ace"), pet.eq("DoubleFault"), pet.eq("Winner"), pet.eq("Forced Error"),
                     pet.eq("Unforced Error")], [END["ace"], END["df"], END["winner"], END["forced"], END["unforced"]], 0)
    rl = num(p["rally_length"]).fillna(-1)
    is_err = np.isin(end, [END["forced"], END["unforced"]])
    rally = np.where(end == END["df"], 0, np.where(rl > 0, rl + is_err.astype(int), -1))
    # an error on shot 1 (the serve was in but the return failed) is a forced or unforced return error: shot 2;
    # a 'Winner' on shot 1 is a serve the returner touched but could not return: a forced error on shot 2
    svc = (end == END["winner"]) & (rally == 1)
    end = np.where(svc, END["forced"], end)
    rally = np.where(svc, 2, rally)
    is_err = np.isin(end, [END["forced"], END["unforced"]])
    d["rally"], d["end"] = rally, end
    loser = 3 - d["winner"]
    d["ender"] = np.select([np.isin(end, [END["ace"], END["df"]]), end == END["winner"], is_err],
                           [d["server"], d["winner"], loser], 0)
    d["serve_no"] = num(p["serve_num"]).where(num(p["serve_num"]).isin([1, 2]), 0)
    d["speed"] = num(p["serve_speed_kph"].astype(str).str.extract(r"([\d.]+)")[0])
    sd = p["serve_dir"].astype(str)
    d["place"] = np.select([sd.eq("T"), sd.eq("Body"), sd.eq("Wide")], [1, 2, 3], 0)
    lh = p["last_hand"].astype(str)
    d["wing"] = np.where(np.isin(end, [END["winner"], END["forced"], END["unforced"]]),
                         np.select([lh.eq("ForeHand"), lh.eq("BackHand")], [1, 2], 0), 0)
    return finish(d, "slam_tracking")


# ------------------------------------------------------------------------------------------------
# Match Charting Project (volunteer charts; one shot string per serve)

MCP_SHOTS = set("fbrsvzopuylmhijktq")
MCP_FOREHAND = set("frvouylhj")       # forehand side: groundstroke, slice, volley, overhead, drop, lob, half-volley, swinging volley
MCP_BACKHAND = set("bszpymik")
MCP_NET = set("vzopijhk")
MCP_FAULTS = set("nwdxge!V")


def mcp_parse(first, second) -> tuple:
    """(rally, end, ender_is_server (1) / returner (2) / 0, serve_no, place, ret_deep, wing, server_net, returner_net)
    of one charted point. Rally counts the serve and the final shot; the last shot's hitter alternates from the server.
    Outcome marks: '*' winner (an ace when right after the serve), '#' forced error (after the serve: an unreturnable
    serve), '@' unforced error; a second-serve fault is a double fault."""
    s1 = first.strip() if isinstance(first, str) else ""
    s2 = second.strip() if isinstance(second, str) else ""
    serve_no = 2 if s2 else 1
    s = (s2 if s2 else s1).lstrip("c")
    if not s or s[0] not in "4560":
        return (-1, 0, 0, 0, 0, -1, 0, -1, -1)
    place = {"4": 3, "5": 2, "6": 1}.get(s[0], 0)
    body = s[1:]
    shots = [i for i, ch in enumerate(body) if ch in MCP_SHOTS]
    if not shots:
        if s2 and body[:1] in MCP_FAULTS:
            return (0, END["df"], 1, 2, 0, -1, 0, 0, 0)
        if "*" in body:
            return (1, END["ace"], 1, serve_no, place, -1, 0, 0, 0)
        if "#" in body:
            return (2, END["forced"], 2, serve_no, place, -1, 0, 0, 0)
        return (-1, 0, 0, serve_no, place, -1, 0, -1, -1)
    rally = 1 + len(shots)
    last = body[shots[-1]]
    tail = body[shots[-1] + 1:]
    end = END["winner"] if "*" in tail else END["forced"] if "#" in tail else END["unforced"] if "@" in tail else 0
    hitter = 1 if (rally % 2 == 1) else 2          # shot k is the server's when k is odd
    ret_deep = -1
    j = shots[0] + 1
    digits = ""
    while j < len(body) and body[j].isdigit():
        digits += body[j]
        j += 1
    if any(c in "789" for c in digits):
        ret_deep = 1 if "9" in digits else 0
    if rally == 2 and end in (END["forced"], END["unforced"]):
        ret_deep = -1                               # the return was not in play
    wing = 1 if last in MCP_FOREHAND else 2 if last in MCP_BACKHAND else 0
    srv_net = 1 if body[:1] == "+" else 0
    ret_net = 0
    for k, i in enumerate(shots):
        ch = body[i]
        nxt = body[i + 1:i + 2]
        at_net = ch in MCP_NET or nxt == "+"
        if at_net:
            if (k + 2) % 2 == 1:                     # shots list starts at shot 2 (the return): k=0 is the returner's
                srv_net = 1
            else:
                ret_net = 1
    return (rally, end, hitter if end else 0, serve_no, place, ret_deep, wing if end in (END["winner"], END["forced"],
                                                                                         END["unforced"]) else 0,
            srv_net, ret_net)


def mcp() -> pd.DataFrame:
    """Columns Pt (order), Set1/Set2 and Gm1/Gm2 (sets and games before the point, player 1 first), Svr 1/2, PtWinner
    1/2, '1st' and '2nd' (the shot strings). A game is a run of points with the same games-before."""
    base = S.DUMP / "points" / "match_charting_project"
    pts = pd.concat([pd.read_parquet(p, columns=["match_id", "Pt", "Set1", "Set2", "Gm1", "Gm2", "Svr", "1st", "2nd",
                                                 "PtWinner"])
                     for p in sorted((base / "points").glob("charting-*-points-*.parquet"))], ignore_index=True)
    parsed = np.array([mcp_parse(a, b) for a, b in zip(pts["1st"].to_numpy(), pts["2nd"].to_numpy())], dtype=object)
    srv = num(pts["Svr"])
    d = pd.DataFrame({"key": pts["match_id"].astype(str), "_order": num(pts["Pt"]),
                      "set_no": num(pts["Set1"]).fillna(0) + num(pts["Set2"]).fillna(0) + 1,
                      "game_label": num(pts["Gm1"]).fillna(0) * 100 + num(pts["Gm2"]).fillna(0),
                      "server": srv, "winner": num(pts["PtWinner"])})
    d["rally"] = parsed[:, 0].astype(int)
    d["end"] = parsed[:, 1].astype(int)
    rel = parsed[:, 2].astype(int)                  # 1 the server hit the last shot, 2 the returner
    d["ender"] = np.where(rel == 1, srv, np.where(rel == 2, 3 - srv, 0))
    d["serve_no"] = parsed[:, 3].astype(int)
    d["place"] = parsed[:, 4].astype(int)
    d["ret_deep"] = parsed[:, 5].astype(int)
    d["wing"] = parsed[:, 6].astype(int)
    sn, rn = parsed[:, 7].astype(int), parsed[:, 8].astype(int)
    d["net1"] = np.where(sn < 0, -1, np.where(srv == 1, sn, rn))
    d["net2"] = np.where(sn < 0, -1, np.where(srv == 2, sn, rn))
    return finish(d, "mcp")


# ------------------------------------------------------------------------------------------------
# ATP Infosys match centre (tour-level points with how they ended) and SirGenkii (the same feed, Jan-Apr 2025)

INFOSYS_SHOT = {"Serve": 1, "Return": 2, "3rd shot": 3, "4th shot": 4, "5th shot": 5, "6th shot": 6, "7th shot": 7,
                "8th shot": 8, "9+ odd shots": 9, "10+ even shots": 10, "9+_odd": 9, "10+_even": 10}
INFOSYS_END = {"ACE": END["ace"], "DOUBLE FAULT": END["df"], "WINNER": END["winner"], "FORCED ERROR": END["forced"],
               "UNFORCED ERROR": END["unforced"]}


def infosys_points(rec: dict) -> list[tuple]:
    """Points of one Infosys record: (set, game, point, serve, shot, team that hit the last shot, won-by-that-shot,
    end code, speed, net1, net2). The record groups points by the shot that ended them ('Serve', 'Return', '3rd shot'
    ... '10+ even shots') and by the team that hit it (t1win / t1err / t2win / t2err); shot k is the server's when k is
    odd, so the server is that team when k is odd, the other otherwise. Points in an unnamed group (Challengers) have no
    shot and are skipped."""
    out = []
    ra = rec.get("rally_analysis") if isinstance(rec.get("rally_analysis"), dict) else {}
    cats = [c for c in (ra.get("rallyData") or []) if isinstance(c, dict)]
    total = sum(len(c.get(s) or []) for c in cats for s in ("t1win", "t1err", "t2win", "t2err"))
    named = sum(len(c.get(s) or []) for c in cats if INFOSYS_SHOT.get(c.get("name"))
                for s in ("t1win", "t1err", "t2win", "t2err"))
    if total == 0 or named < 0.5 * total:
        return out
    for cat in cats:
        shot = INFOSYS_SHOT.get(cat.get("name"))
        if not shot:
            continue
        for side in ("t1win", "t1err", "t2win", "t2err"):
            team = 1 if side.startswith("t1") else 2
            won = side.endswith("win")
            for p in cat.get(side) or []:
                if not isinstance(p, dict):
                    continue
                pid = str(p.get("pointId") or "")
                parts = pid.split("_")
                if len(parts) < 3 or not all(x.isdigit() for x in parts[:3]):
                    continue
                pet = str(p.get("pointEndType") or "")
                end = INFOSYS_END.get(pet, 0)
                sp = p.get("serveSpeed")
                try:
                    sp = float(sp)
                except (TypeError, ValueError):
                    sp = np.nan
                serve = p.get("serve")
                out.append((int(parts[0]), int(parts[1]), int(parts[2]), serve if serve in (1, 2) else 0, shot, team,
                            won, end, sp, int(bool(p.get("t1NetPoint"))), int(bool(p.get("t2NetPoint")))))
    return out


def _infosys_file(path: str) -> pd.DataFrame:
    opener = gzip.open if path.endswith(".gz") else open
    rows = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            code = str(rec.get("match_id") or "")
            if not re.match(r"^[MQ]S", code):
                continue
            key = f"{rec.get('year')}_{rec.get('tournament_id')}_{code}"
            for t in infosys_points(rec):
                rows.append((key,) + t)
    cols = ["key", "set_no", "game_label", "point", "serve_no", "shot", "team", "won", "end", "speed", "net1", "net2"]
    return pd.DataFrame(rows, columns=cols)


def shot_points_to_schema(d: pd.DataFrame) -> pd.DataFrame:
    """The Infosys / SirGenkii point layout to the schema: the server from the ending shot's parity, the point winner
    from who hit the last shot and whether it won."""
    shot, team, won = d["shot"].to_numpy(), d["team"].to_numpy(), d["won"].to_numpy().astype(bool)
    server = np.where(shot % 2 == 1, team, 3 - team)
    winner = np.where(won, team, 3 - team)
    end = d["end"].to_numpy().copy()
    # a serve won without an ace (shot 1, unclassified): a forced error by the returner on shot 2
    svc = (shot == 1) & won & (end == 0)
    end = np.where(svc, END["forced"], end)
    team = np.where(svc, 3 - team, team)
    shot = np.where(svc, 2, shot)
    rally = np.where(end == END["df"], 0, shot)
    out = pd.DataFrame({"key": d["key"], "_order": d["set_no"] * 1e6 + d["game_label"] * 1e3 + d["point"],
                        "set_no": d["set_no"], "game_label": d["game_label"], "server": server, "winner": winner,
                        "serve_no": d["serve_no"], "rally": rally, "end": end,
                        "ender": np.where(end > 0, team, 0), "speed": d["speed"],
                        "net1": d["net1"], "net2": d["net2"]})
    # a match whose points never flag a net point does not record them
    for c in ("net1", "net2"):
        rec = (out["net1"].gt(0) | out["net2"].gt(0)).groupby(out["key"]).transform("any")
        out[c] = np.where(rec, out[c], -1)
    # matches whose endings are not classified (every point 0 or svc) keep end unknown; drop duplicate point ids
    out = out.drop_duplicates(["key", "_order"])
    return out


def infosys(workers: int = 5) -> pd.DataFrame:
    from concurrent.futures import ProcessPoolExecutor
    paths = sorted(str(p) for d in ("infosys_deep", "infosys_full") for p in (S.HANDOFF / d).glob("*_data.jsonl*"))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(_infosys_file, paths))
    d = pd.concat(parts, ignore_index=True)
    # the two folders overlap: keep, per match, the folder copy with the most points
    sizes = d.groupby(["key"]).size()
    d = d.drop_duplicates(["key", "set_no", "game_label", "point"])
    S.log(f"  infosys points: {len(d)} (matches {d['key'].nunique()}, raw {int(sizes.sum())})")
    return finish(shot_points_to_schema(d), "infosys")


def sirgenkii() -> pd.DataFrame:
    """atp_rally_analysis: one row per point with the last shot's hitter (player_id) and outcome (W: the shot won, L: it
    lost), shot_number as Infosys's groups, point_end_type, serve 1/2, serve_speed (0 unknown), p1/p2 net flags."""
    base = S.DUMP / "points" / "sirgenkii_infotennis"
    res = pd.read_parquet(base / "atp_results.parquet", columns=["tournament_id", "year", "match_id", "player1_id",
                                                                 "player2_id"])
    ra = pd.read_parquet(base / "atp_rally_analysis.parquet",
                         columns=["tournament_id", "year", "match_id", "point_id", "shot_number", "outcome", "player_id",
                                  "point_end_type", "serve", "serve_speed", "p1_net_point", "p2_net_point"])
    for t in (res, ra):
        for c in ("tournament_id", "year", "match_id"):
            t[c] = t[c].astype(str)
    ra = ra.drop_duplicates(["tournament_id", "year", "match_id", "point_id"]).merge(
        res, on=["tournament_id", "year", "match_id"], how="inner")
    parts = ra["point_id"].astype(str).str.split("_", expand=True)
    shot = ra["shot_number"].astype(str).map(lambda v: INFOSYS_SHOT.get(v, int(v) if str(v).isdigit() else 0))
    pid = ra["player_id"].astype(str).str.upper()      # the results table writes ids in lower case, the points in upper
    team = np.select([pid.eq(ra["player1_id"].astype(str).str.upper()), pid.eq(ra["player2_id"].astype(str).str.upper())],
                     [1, 2], 0)
    d = pd.DataFrame({"key": ra["year"] + "_" + ra["tournament_id"] + "_" + ra["match_id"],
                      "set_no": num(parts[0]), "game_label": num(parts[1]), "point": num(parts[2]),
                      "serve_no": num(ra["serve"]).where(num(ra["serve"]).isin([1, 2]), 0), "shot": shot,
                      "team": team, "won": ra["outcome"].astype(str).eq("W"),
                      "end": ra["point_end_type"].astype(str).map(INFOSYS_END).fillna(0).astype(int),
                      "speed": num(ra["serve_speed"]).where(num(ra["serve_speed"]) > 0),
                      "net1": ra["p1_net_point"].astype(str).isin(["1", "True", "true"]).astype(int),
                      "net2": ra["p2_net_point"].astype(str).isin(["1", "True", "true"]).astype(int)})
    d = d[(d["team"] > 0) & (d["shot"] > 0)]
    return finish(shot_points_to_schema(d), "sirgenkii")


# ------------------------------------------------------------------------------------------------
# TDI Tennis Results (ATP and Challenger)

def tdi() -> pd.DataFrame:
    """team_serving and winner teamA/teamB (player 1 is team A); serve FIRST / SECOND / ACE / DOUBLE FAULT; total_shots
    counts shots that landed in (an ace 1, a double fault 0, a return error 1), so error endings get 1 added; outcome
    winner / forced / unforced (by the point winner / loser); situation names who was at the net; winning_shot_type the
    last shot (forehand / backhand / return / serve / volley)."""
    p = pd.read_parquet(S.DUMP / "points" / "tdi" / "points.parquet",
                        columns=["match_id", "set", "game", "point", "point_sequence", "winner", "team_serving", "serve",
                                 "total_shots", "outcome", "winning_shot_type", "situation"])
    m = pd.read_parquet(S.DUMP / "points" / "tdi" / "matches.parquet", columns=["match_id", "draw_type"])
    p = p[p["match_id"].isin(m.loc[m["draw_type"].eq("singles"), "match_id"])]
    srv = p["team_serving"].map({"teamA": 1, "teamB": 2})
    win = p["winner"].map({"teamA": 1, "teamB": 2})
    d = pd.DataFrame({"key": p["match_id"].astype(str),
                      "_order": num(p["set"]) * 1e6 + num(p["game"]) * 1e3 + num(p["point"]),
                      "set_no": num(p["set"]), "game_label": num(p["game"]), "server": srv, "winner": win})
    serve = p["serve"].astype(str)
    out = p["outcome"].astype(str)
    end = np.select([serve.eq("ACE"), serve.eq("DOUBLE FAULT"), out.eq("winner"), out.eq("forced"), out.eq("unforced")],
                    [END["ace"], END["df"], END["winner"], END["forced"], END["unforced"]], 0)
    ts = num(p["total_shots"]).fillna(-1)
    is_err = np.isin(end, [END["forced"], END["unforced"]])
    d["end"] = end
    d["rally"] = np.where(end == END["df"], 0, np.where((ts > 0) & (end > 0), ts + is_err.astype(int), -1))
    d["ender"] = np.select([np.isin(end, [END["ace"], END["df"]]), end == END["winner"], is_err],
                           [d["server"], d["winner"], 3 - d["winner"]], 0)
    d["serve_no"] = np.select([serve.eq("FIRST"), serve.isin(["SECOND", "DOUBLE FAULT"])], [1, 2], 0)
    sit = p["situation"].astype(str)
    known = sit.isin(["baseline", "returning", "serving", "player1_at_net", "player2_at_net", "both_at_net"])
    d["net1"] = np.where(known, sit.isin(["player1_at_net", "both_at_net"]).astype(int), -1)
    d["net2"] = np.where(known, sit.isin(["player2_at_net", "both_at_net"]).astype(int), -1)
    wst = p["winning_shot_type"].astype(str)
    d["wing"] = np.where(np.isin(end, [END["winner"], END["forced"], END["unforced"]]),
                         np.select([wst.eq("forehand"), wst.eq("backhand")], [1, 2], 0), 0)
    return finish(d, "tdi")


# ------------------------------------------------------------------------------------------------
# Australian Open match centre (2026, and Wayback captures)

def ausopen() -> pd.DataFrame:
    """winner 1/2 per point; point_server_team 1/2; outcome ace / double_fault / winner / forced_error / unforced_error
    / service_winner with subject_role winner / loser and subject_team; stroke_side forehand / backhand. No rally
    length or serve speed."""
    p = pd.read_parquet(S.DUMP / "points" / "ausopen" / "points.parquet",
                        columns=["record_key", "seq", "set", "game", "point", "type", "winner", "outcome",
                                 "subject_team", "stroke_side", "point_server_team"])
    m = pd.read_parquet(S.DUMP / "points" / "ausopen" / "matches.parquet", columns=["record_key", "event"])
    p = p[p["type"].eq("point") & p["record_key"].isin(m.loc[m["event"].isin(["MS", "WS", "MQ", "WQ"]), "record_key"])]
    d = pd.DataFrame({"key": p["record_key"].astype(str), "_order": num(p["seq"]), "set_no": num(p["set"]),
                      "game_label": num(p["game"]), "server": num(p["point_server_team"]), "winner": num(p["winner"])})
    oc = p["outcome"].astype(str)
    svc = oc.eq("service_winner").to_numpy()
    end = np.select([oc.eq("ace"), oc.eq("double_fault"), oc.eq("winner"), oc.eq("forced_error"),
                     oc.eq("unforced_error"), oc.eq("service_winner")],
                    [END["ace"], END["df"], END["winner"], END["forced"], END["unforced"], END["forced"]], 0)
    d["end"] = end
    subj = num(p["subject_team"]).fillna(0).to_numpy()
    d["ender"] = np.where(svc, 3 - num(p["point_server_team"]).fillna(0).to_numpy(), np.where(end > 0, subj, 0))
    d["rally"] = np.select([end == END["df"], end == END["ace"], svc], [0, 1, 2], -1)
    ss = p["stroke_side"].astype(str)
    d["wing"] = np.where(np.isin(end, [END["winner"], END["forced"], END["unforced"]]),
                         np.select([ss.eq("forehand"), ss.eq("backhand")], [1, 2], 0), 0)
    return finish(d, "ausopen")


ADAPTERS = {"slam_pbp": slam_pbp, "slamtracker": slamtracker, "slam_tracking": slam_tracking, "mcp": mcp,
            "infosys": infosys, "sirgenkii": sirgenkii, "tdi": tdi, "ausopen": ausopen}
