"""Readers of each held source's match totals, mapped onto the box-score contract (common.COUNTS).

Each reader returns one row per (record, player): ``source``, ``source_key`` (the key the match-timing link files use),
``side`` (the source's own label), ``won`` and the contract fields. Mappings, as read from the staged tables:

SofaScore (period ALL of the three collections)
    ace aces · df doubleFaults · first_in / svpt firstServeAccuracy "in/attempts" · first_won firstServePointsAccuracy ·
    second_won secondServePointsAccuracy · sv_gms Service/serviceGamesTotal · bp_saved / bp_faced breakPointsSaved
    "saved/faced" · sv_won servicePointsScored
WTA API (stats, setnum 0 = the whole match)
    ace aces · df dblflt · svpt totservplayed · first_in ptsplayed1stserv · first_won ptswon1stserv ·
    sv_won ptstotwonserv (second_won = sv_won - first_won) · sv_gms servgamesplayed ·
    bp_faced = the opponent's breakptsplayed, bp_saved = that minus the opponent's breakptsconv (both are recorded on
    the returner's side; checked against Sackmann in referees.py)
TDI (statistics, period "match")
    ace Aces · df Double Faults · sv_gms Service Games Played · bp_faced / bp_saved Break Points Faced / Saved ·
    sv_won Total Service Points Won · svpt = sv_won + the opponent's Total Return Points Won. No first-serve split.
Wimbledon and US Open (IBM SlamTracker statistics, base_stats and serve_stats, period "match")
    ace t_ace · df df · svpt t_f_srv (first-serve attempts) · first_in t_f_srv_in · first_won t_f_srv_w ·
    second_won t_s_srv_w · sv_gms serve_stats t_gms · bp_faced = the opponent's t_bp, bp_saved = that minus the
    opponent's t_bp_w (break points are recorded on the returner's side)
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.eda.data_continuity import common as K

SOFASCORE_COLLECTIONS = ("sofascore", "sofascore_editions", "sofascore_tournaments")


def _two_sides(frame: pd.DataFrame, left: str, right: str, mapping: dict, source: str) -> pd.DataFrame:
    """Wide (one row per record, columns per side) to long (one row per record and side)."""
    rows = []
    for side, other in ((left, right), (right, left)):
        cols = {"source_key": frame["source_key"], "side": side,
                "won": frame["winner"].eq(side).where(frame["winner"].notna())}
        for field, fn in mapping.items():
            cols[field] = fn(frame, side, other)
        rows.append(pd.DataFrame(cols))
    out = pd.concat(rows, ignore_index=True)
    out.insert(0, "source", source)
    return K.finish(out)


# ---------------------------------------------------------------------------------------------- SofaScore
SOFA_KEYS = {("Service", "aces"): "ace", ("Service", "doubleFaults"): "df",
             ("Service", "firstServeAccuracy"): "first_serve", ("Service", "firstServePointsAccuracy"): "first_pts",
             ("Service", "secondServePointsAccuracy"): "second_pts", ("Service", "serviceGamesTotal"): "sv_gms",
             ("Service", "breakPointsSaved"): "bp", ("Points", "servicePointsScored"): "sv_won"}


def sofascore() -> pd.DataFrame:
    """SofaScore box scores of every singles event held in the three collections (one copy per event)."""
    frames, seen = [], set()
    for c in SOFASCORE_COLLECTIONS:
        st = pd.read_parquet(K.DUMP / "points" / c / "statistics.parquet",
                             columns=["event_id", "period", "group", "key", "home", "away"],
                             filters=[("period", "==", "ALL")])
        ev = pd.read_parquet(K.DUMP / "points" / c / "events.parquet",
                             columns=["event_id", "winner_code", "doubles", "status_type"])
        ev = ev[~ev["doubles"].astype(str).str.lower().isin(["true", "1"]) & ~ev["event_id"].isin(seen)]
        seen |= set(ev["event_id"])
        st = st[st["event_id"].isin(set(ev["event_id"]))]
        st = st[[(g, k) in SOFA_KEYS for g, k in zip(st["group"], st["key"])]]
        st = st.assign(field=[SOFA_KEYS[(g, k)] for g, k in zip(st["group"], st["key"])])
        wide = st.pivot_table(index="event_id", columns="field", values=["home", "away"], aggfunc="first")
        wide.columns = [f"{side}_{field}" for side, field in wide.columns]
        wide = wide.reset_index().merge(ev[["event_id", "winner_code", "status_type"]], on="event_id", how="left")
        wide["collection"] = c
        frames.append(wide)
    w = pd.concat(frames, ignore_index=True)
    w["source_key"] = "sofascore:" + w["event_id"].astype(str)
    w["winner"] = w["winner_code"].astype(str).map({"1": "home", "2": "away"})
    for side in ("home", "away"):
        for f in ("ace", "df", "sv_gms", "sv_won"):
            w[f"{side}_{f}"] = K.num(w.get(f"{side}_{f}", pd.Series(index=w.index, dtype="object")))
        for f, (n, d) in {"first_serve": ("first_in", "svpt"), "first_pts": ("first_won", "first_in_den"),
                          "second_pts": ("second_won", "second_den"), "bp": ("bp_saved", "bp_faced")}.items():
            w[f"{side}_{n}"], w[f"{side}_{d}"] = K.ratio(w.get(f"{side}_{f}", pd.Series(index=w.index, dtype="object")))

    def col(name):
        return lambda f, side, other: f[f"{side}_{name}"]

    out = _two_sides(w, "home", "away", {c: col(c) for c in K.COUNTS + ["sv_won"]}, "sofascore")
    meta = w[["source_key", "collection", "status_type"]]
    out = out.merge(meta, on="source_key", how="left")
    # SofaScore's own consistency: first-serve and second-serve denominators against its serve points
    dens = pd.concat([w[["source_key", f"{s}_first_in_den", f"{s}_second_den", f"{s}_first_in", f"{s}_svpt"]]
                      .set_axis(["source_key", "first_in_den", "second_den", "first_in", "svpt"], axis=1)
                      .assign(side=s) for s in ("home", "away")])
    out = out.merge(dens[["source_key", "side", "first_in_den", "second_den"]], on=["source_key", "side"], how="left")
    return out


# ---------------------------------------------------------------------------------------------- WTA API
WTA_WINNER = {"2": "a", "4": "a", "6": "a", "3": "b", "5": "b", "7": "b"}   # completed, retired, walkover


def wta_key(frame: pd.DataFrame) -> pd.Series:
    return "wta:" + frame["tournament_id"].astype(str) + "/" + frame["year"].astype(str) + "/" + frame["match_id"].astype(str)


def wta_api(years=range(2019, 2027)) -> pd.DataFrame:
    """WTA API box scores (B3): the setnum 0 row of each match. The winner is the match list's ``Winner`` code
    (2, 4, 6 player A; 3, 5, 7 player B: completed, retired, walkover). Set counts disagree with it at retirements,
    where the retiring player can lead in sets."""
    parts, lists = [], []
    for y in years:
        path = K.DUMP / "points" / "wta" / "stats" / f"{y}.parquet"
        if path.exists():
            parts.append(K.read_parquet_dedup(path))
        path = K.DUMP / "points" / "wta" / "matches" / f"{y}.parquet"
        if path.exists():
            lists.append(K.read_parquet_dedup(path, ["tournament_id", "year", "match_id", "Winner"]))
    s = pd.concat(parts, ignore_index=True)
    s["source_key"] = wta_key(s)
    m = pd.concat(lists, ignore_index=True)
    m["source_key"] = wta_key(m)
    winner = m.drop_duplicates("source_key").set_index("source_key")["Winner"].astype(str).map(WTA_WINNER)
    total = s[s["setnum"].astype(str) == "0"].drop_duplicates("source_key").copy()
    total["winner"] = total["source_key"].map(winner)

    def n(name):
        return lambda f, side, other: K.num(f[f"{name}{side}"])

    def second(f, side, other):
        return K.num(f[f"ptstotwonserv{side}"]) - K.num(f[f"ptswon1stserv{side}"])

    def bp_faced(f, side, other):
        return K.num(f[f"breakptsplayed{other}"])

    def bp_saved(f, side, other):
        return K.num(f[f"breakptsplayed{other}"]) - K.num(f[f"breakptsconv{other}"])

    mapping = {"ace": n("aces"), "df": n("dblflt"), "svpt": n("totservplayed"), "first_in": n("ptsplayed1stserv"),
               "first_won": n("ptswon1stserv"), "second_won": second, "sv_won": n("ptstotwonserv"),
               "sv_gms": n("servgamesplayed"), "bp_faced": bp_faced, "bp_saved": bp_saved}
    out = _two_sides(total, "a", "b", mapping, "wta_api")
    # the other reading of the break-point columns (recorded on the server's side), for the orientation check
    alt = []
    for side in ("a", "b"):
        alt.append(pd.DataFrame({"source_key": total["source_key"], "side": side,
                                 "bp_faced_alt": K.num(total[f"breakptsplayed{side}"]),
                                 "bp_saved_alt": K.num(total[f"breakptsplayed{side}"]) - K.num(total[f"breakptsconv{side}"])}))
    return out.merge(pd.concat(alt), on=["source_key", "side"], how="left")


# ---------------------------------------------------------------------------------------------- TDI
TDI_LABELS = {"Aces": "ace", "Double Faults": "df", "Service Games Played": "sv_gms", "Break Points Faced": "bp_faced",
              "Break Points Saved": "bp_saved", "Total Service Points Won": "sv_won",
              "Total Return Points Won": "rt_won"}
SET_SCORE = re.compile(r"(\d+):(\d+)")


def _sets_won(a: str, b: str) -> tuple[int, int]:
    """Sets won from TDI's "1:6 2:7/7" strings (set number, games, optional tiebreak points)."""
    ga = {k: int(g) for k, g in SET_SCORE.findall(str(a or ""))}
    gb = {k: int(g) for k, g in SET_SCORE.findall(str(b or ""))}
    wa = sum(1 for k in ga if k in gb and ga[k] > gb[k] and ga[k] >= 6)
    wb = sum(1 for k in gb if k in ga and gb[k] > ga[k] and gb[k] >= 6)
    return wa, wb


def tdi() -> pd.DataFrame:
    st = pd.read_parquet(K.DUMP / "points" / "tdi" / "statistics.parquet",
                         columns=["match_id", "period", "label", "team_a", "team_b"], filters=[("period", "==", "match")])
    st = st[st["label"].isin(TDI_LABELS)]
    st = st.assign(field=st["label"].map(TDI_LABELS))
    wide = st.pivot_table(index="match_id", columns="field", values=["team_a", "team_b"], aggfunc="first")
    wide.columns = [f"{side}_{field}" for side, field in wide.columns]
    m = pd.read_parquet(K.DUMP / "points" / "tdi" / "matches.parquet",
                        columns=["match_id", "draw_type", "team_a_scores", "team_b_scores"])
    m = m[m["draw_type"].eq("singles")]
    w = wide.reset_index().merge(m, on="match_id", how="inner")
    sets = [_sets_won(a, b) for a, b in zip(w["team_a_scores"], w["team_b_scores"])]
    w["winner"] = ["team_a" if x > y else "team_b" if y > x else None for x, y in sets]
    w["source_key"] = "tdi:" + w["match_id"].astype(str)

    def n(name):
        return lambda f, side, other: K.num(f[f"{side}_{name}"])

    def svpt(f, side, other):
        return K.num(f[f"{side}_sv_won"]) + K.num(f[f"{other}_rt_won"])

    mapping = {"ace": n("ace"), "df": n("df"), "sv_gms": n("sv_gms"), "bp_faced": n("bp_faced"),
               "bp_saved": n("bp_saved"), "sv_won": n("sv_won"), "svpt": svpt}
    return _two_sides(w, "team_a", "team_b", mapping, "tdi")    # sv_won as published; it has no split to sum


# ---------------------------------------------------------------------------------------------- Slam feeds
SLAM_BASE = {"t_ace": "ace", "df": "df", "t_f_srv": "svpt", "t_f_srv_in": "first_in", "t_f_srv_w": "first_won",
             "t_s_srv_w": "second_won", "t_bp": "bp_chances", "t_bp_w": "bp_won"}


def slam_feeds(sites=("wimbledon", "usopen")) -> pd.DataFrame:
    frames = []
    for site in sites:
        st = pd.read_parquet(K.DUMP / "points" / site / "statistics.parquet",
                             columns=["year", "event", "match_id", "section", "period", "team", "key", "value"],
                             filters=[("period", "==", "match"), ("section", "in", ["base_stats", "serve_stats"])])
        st = st[((st["section"] == "base_stats") & st["key"].isin(SLAM_BASE))
                | ((st["section"] == "serve_stats") & (st["key"] == "t_gms"))]
        st = st.assign(field=np.where(st["key"].eq("t_gms"), "sv_gms", st["key"].map(SLAM_BASE)))
        st["source_key"] = site + ":" + st["year"].astype(str) + "/" + st["event"].astype(str) + "/" + st["match_id"].astype(str)
        wide = st.pivot_table(index="source_key", columns=["team", "field"], values="value", aggfunc="first")
        wide.columns = [f"{team}_{field}" for team, field in wide.columns]
        m = pd.read_parquet(K.DUMP / "points" / site / "matches.parquet", columns=["year", "event", "match_id", "entry.winner"])
        m["source_key"] = site + ":" + m["year"].astype(str) + "/" + m["event"].astype(str) + "/" + m["match_id"].astype(str)
        w = wide.reset_index().merge(m[["source_key", "entry.winner"]], on="source_key", how="left")
        w["winner"] = w["entry.winner"].astype(str).map({"1": "team_1", "2": "team_2"})

        def n(name):
            return lambda f, side, other: K.num(f.get(f"{side}_{name}", pd.Series(index=f.index, dtype="object")))

        def bp_faced(f, side, other):
            return K.num(f.get(f"{other}_bp_chances", pd.Series(index=f.index, dtype="object")))

        def bp_saved(f, side, other):
            return bp_faced(f, side, other) - K.num(f.get(f"{other}_bp_won", pd.Series(index=f.index, dtype="object")))

        mapping = {c: n(c) for c in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms")}
        mapping.update(bp_faced=bp_faced, bp_saved=bp_saved)
        out = _two_sides(w, "team_1", "team_2", mapping, site)
        frames.append(out)
    return pd.concat(frames, ignore_index=True)


READERS = {"sofascore": sofascore, "wta_api": wta_api, "tdi": tdi, "slam_feeds": slam_feeds}
