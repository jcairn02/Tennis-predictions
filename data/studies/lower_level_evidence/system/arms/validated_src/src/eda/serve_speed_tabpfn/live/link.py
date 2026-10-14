"""Linking staged ATP speed rows to the project's match and player ids, for matches Stage 0 holds and for newer ones.
Reads no match result: Tennis My Life's files are read with identity columns only (tournament, date, round, the two
players' codes and names), and the winner / loser pair is put in code order at once, so its order carries nothing.

Player ids. ATP codes (the Infosys and ManTennisData player codes, Tennis My Life's ATP ids) map to the project's ids by a
crosswalk learned from links Stage 0 already holds:
    * ManTennisData rows linked to Stage 0 matches (serve_speed_acquisition/speeds.parquet: code, match, side);
    * the Infosys handoff's matches linked by the shot-level study (stage0_source_matches 'infosys': id1, id2, a1).
    * Tennis My Life's 2024-26 rows that Stage 0 holds, linked by the shot-level linker (how Stage 0 resolved each code).
    A code takes the id it has in at least 80% of its links (stray pairs are linker slips); an unknown code becomes
    'atpcode:<CODE>', Stage 0's own id for a player newer than Sackmann's files (stage0_build C61).
Matches, tried in this order (link_method):
    stage0_exact  the id Stage 0 would give: atp|<year>-<event>|<round>|<lo id>|<hi id> exists in Stage 0
    stage0_pair   the event's Stage 0 match with the same two players (qualifying codes give no round)
    stage0_names  the shot-level linker (names, tournament date, round, draw) inside the event's Stage 0 matches
    tml           Tennis My Life (season and ongoing files): the event's match with the same two codes; the match id is
                  built as Stage 0 builds it (sides by predictability_diagnostic.common.side_is_low), so it equals
                  Stage 0's once Stage 0 is rebuilt
    unlinked      none of these
Clock. A Stage 0 match takes es / lf / obs from timing.parquet (obs floored to a day, as the panel). A Tennis My Life
match takes its own date: es = obs = that day, lf = the next day; where the event lists one date only (its start),
es = start, lf = start + 9, obs = start + 3 (clock = 'tml_event_start').
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.serve_speed_tabpfn.live import common as LC

S0 = LC.ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
TIMING = LC.ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
SPEEDS = LC.ROOT / "data" / "studies" / "serve_speed_acquisition" / "speeds.parquet"
SOURCE_LINKS = LC.ROOT / "data" / "studies" / "shot_level" / "stage0_source_matches.parquet"
ID_MAP = LC.ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "id_map.csv"
TML = LC.ROOT / "data" / "dump" / "matches" / "tennis_my_life"
TML_COLS = ["tourney_id", "tourney_date", "round", "winner_id", "winner_name", "loser_id", "loser_name",
            "tourney_level"]                      # identity only: never the score or the box score
S0_COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
           "tournament_name", "tournament_date", "player_a_id", "player_b_id"]
TML_LEVEL = {"G": "GS", "M": "T1000", "500": "T500", "250": "T250", "A": "T250", "F": "FIN", "D": "TEAM", "C": "CH",
             "CH": "CH"}


def _remap() -> dict:
    m = pd.read_csv(ID_MAP, usecols=["old_match_id", "new_match_id"])
    return dict(zip(m["old_match_id"], m["new_match_id"]))


XW_CACHE = LC.OUT / "crosswalk.parquet"
XW_YEARS = (2024, 2025, 2026)
XW_MIN_SHARE = 0.8


def _xw_links() -> pd.DataFrame:
    """(code, pid) pairs from the links Stage 0 already holds: ManTennisData rows and the Infosys handoff's matches."""
    s0 = pd.read_parquet(S0, columns=["match_id", "player_a_id", "player_b_id"]).set_index("match_id")
    sp = pd.read_parquet(SPEEDS, columns=["source", "player_source_id", "match_id", "side"])
    sp = sp[sp["source"].eq("mantennisdata") & sp["match_id"].notna() & sp["side"].notna()]
    sp = sp.join(s0, on="match_id", how="inner")
    a = pd.DataFrame({"code": sp["player_source_id"].map(LC.atp_code),
                      "pid": np.where(sp["side"].eq("A"), sp["player_a_id"], sp["player_b_id"]), "via": "mantd"})
    lk = pd.read_parquet(SOURCE_LINKS, columns=["source", "match_id", "id1", "id2", "a1"])
    lk = lk[lk["source"].eq("infosys") & lk["match_id"].notna() & lk["a1"].notna()].copy()
    remap = _remap()
    lk["match_id"] = lk["match_id"].map(lambda x: remap.get(x, x))
    lk = lk.join(s0, on="match_id", how="inner")
    a1 = lk["a1"].astype(bool).to_numpy()
    b = pd.DataFrame({"code": pd.concat([lk["id1"], lk["id2"]]).map(LC.atp_code).to_numpy(),
                      "pid": np.concatenate([np.where(a1, lk["player_a_id"], lk["player_b_id"]),
                                             np.where(a1, lk["player_b_id"], lk["player_a_id"])]), "via": "infosys"})
    return pd.concat([a, b], ignore_index=True)


def _xw_tml(years=XW_YEARS) -> pd.DataFrame:
    """(code, pid) pairs from Tennis My Life's rows that Stage 0 holds, linked by the shot-level linker (names, event
    date, round, draw): the way Stage 0 itself resolved each TML player code."""
    from src.eda.shot_level import common as S
    t = tml_table(years)
    if t.empty:
        return pd.DataFrame(columns=["code", "pid", "via"])
    u = S.stage0_universe()
    u = u[u["tour"].eq("M") & u["year"].isin(list(years))].reset_index(drop=True)
    u["uid"] = np.arange(len(u))
    rows = pd.DataFrame({"tour": "M", "d": t["event_start"], "name1": t["n_lo"], "name2": t["n_hi"],
                         "round": t["round"], "draw": np.where(t["qualifying"], "qual", "main")}, index=t.index)
    lk = S.Stage0Linker(universe=u).link(rows)
    ok = lk["match_id"].notna() & lk["a1"].notna()
    s0 = pd.read_parquet(S0, columns=["match_id", "player_a_id", "player_b_id"]).set_index("match_id")
    m = lk[ok].join(s0, on="match_id", how="inner")
    a1 = m["a1"].astype(bool).to_numpy()
    tt = t.loc[m.index]
    return pd.DataFrame({"code": np.concatenate([tt["c_lo"].to_numpy(), tt["c_hi"].to_numpy()]),
                         "pid": np.concatenate([np.where(a1, m["player_a_id"], m["player_b_id"]),
                                                np.where(a1, m["player_b_id"], m["player_a_id"])]), "via": "tml"})


def _stage0_stamp() -> str:
    st = S0.stat()
    return f"{st.st_size}-{int(st.st_mtime)}"


def crosswalk(rebuild: bool = False) -> pd.Series:
    """ATP code -> project player id: the id a code takes in at least 80% of its links (cached in
    live/crosswalk.parquet, rebuilt when Stage 0 changes)."""
    if not rebuild and XW_CACHE.exists():
        c = pd.read_parquet(XW_CACHE)
        if len(c) and c["stage0_stamp"].iloc[0] == _stage0_stamp():
            return c.set_index("code")["pid"]
    x = pd.concat([_xw_links(), _xw_tml()], ignore_index=True).dropna(subset=["code", "pid"])
    # the id a code takes in most of its links (stray pairs are linker slips); kept when it holds >= 80% of them
    top = x.groupby(["code", "pid"]).size().reset_index(name="k")
    top["share"] = top["k"] / top.groupby("code")["k"].transform("sum")
    best = top.sort_values(["code", "k", "pid"], ascending=[True, False, True]).drop_duplicates("code")
    out = best[best["share"] >= XW_MIN_SHARE][["code", "pid"]].reset_index(drop=True)
    out["stage0_stamp"] = _stage0_stamp()
    LC.OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(XW_CACHE, index=False)
    return out.set_index("code")["pid"]


def project_id(code, xw: pd.Series) -> str | None:
    c = LC.atp_code(code)
    if c is None:
        return None
    return xw.get(c, f"atpcode:{c}")


def tml_table(years) -> pd.DataFrame:
    """Tennis My Life's ATP matches of the years (main, Challenger, qualifying season files and the ongoing files):
    identity columns only, the pair in code order, the match's own date."""
    parts = []
    for y in years:
        for fam, name, qual in (("atp_main", f"{y}.parquet", False), ("atp_challenger", f"{y}_challenger.parquet", False),
                                ("atp_qualifying", f"{y}_atp_quali.parquet", True)):
            f = TML / fam / name
            if f.exists():
                parts.append(pd.read_parquet(f, columns=TML_COLS).assign(tml_qual=qual, tml_file=f.name))
    for name in ("ongoing_tourneys.parquet", "challenger_ongoing_tourneys.parquet"):
        f = TML / "ongoing" / name
        if f.exists():
            parts.append(pd.read_parquet(f, columns=TML_COLS).assign(tml_qual=False, tml_file=name))
    if not parts:
        return pd.DataFrame(columns=["tid", "round", "c_lo", "c_hi", "n_lo", "n_hi", "d", "level", "qualifying"])
    t = pd.concat(parts, ignore_index=True)
    t["tid"] = t["tourney_id"].astype(str)
    w, l = t["winner_id"].map(LC.atp_code), t["loser_id"].map(LC.atp_code)
    lo_first = w.fillna("") <= l.fillna("")
    t["c_lo"], t["c_hi"] = np.where(lo_first, w, l), np.where(lo_first, l, w)
    t["n_lo"] = np.where(lo_first, t["winner_name"], t["loser_name"])
    t["n_hi"] = np.where(lo_first, t["loser_name"], t["winner_name"])
    t["d"] = pd.to_datetime(t["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    t["qualifying"] = t["tml_qual"] | (t["round"].astype(str).str.startswith("Q") & t["round"].ne("QF"))
    t["level"] = t["tourney_level"].astype(str).map(TML_LEVEL).fillna("T250")
    t = t.drop(columns=["winner_id", "winner_name", "loser_id", "loser_name", "tourney_date", "tml_qual"])
    t = t.drop_duplicates(["tid", "round", "c_lo", "c_hi"], keep="last")
    nd = t.groupby("tid")["d"].transform("nunique")
    t["per_match_dates"] = nd > 1
    t["event_start"] = t.groupby("tid")["d"].transform("min")
    return t.reset_index(drop=True)


def link(staged: pd.DataFrame, s0: pd.DataFrame | None = None, tml: pd.DataFrame | None = None,
         xw: pd.Series | None = None, use_names: bool = True) -> pd.DataFrame:
    """One row per staged match: the staged columns plus link_method, match_id, in_stage0, side_p1 (the Stage 0 side
    of player 1), pid_p1 / pid_p2 (project ids), tournament_id, round, level, qualifying, tdate, es, lf, obs (days),
    clock."""
    from src.eda.predictability_diagnostic import common as PD
    st = staged.reset_index(drop=True).copy()
    xw = crosswalk() if xw is None else xw
    s0 = pd.read_parquet(S0, columns=S0_COLS) if s0 is None else s0
    s0 = s0[s0["tour"].eq("atp")]
    st["tid"] = st["year"].astype(str) + "-" + st["event_id"].astype(str)
    x1 = pd.Series([project_id(c, xw) for c in st["p1_atp_id"]], index=st.index, dtype=object)
    x2 = pd.Series([project_id(c, xw) for c in st["p2_atp_id"]], index=st.index, dtype=object)
    first = x1.fillna("") < x2.fillna("")
    lo, hi = x1.where(first, x2), x2.where(first, x1)
    st["match_id"], st["link_method"], st["a1"] = None, "unlinked", None
    for c in ("es", "lf", "obs", "tdate"):
        st[c] = np.nan
    st["clock"] = None
    ids = set(s0["match_id"])
    # 1 the id Stage 0 would give
    cand = "atp|" + st["tid"] + "|" + st["round"].fillna("?").astype(str) + "|" + lo.astype(str) + "|" + hi.astype(str)
    hit = cand.isin(ids) & st["round"].notna()
    st.loc[hit, "match_id"], st.loc[hit, "link_method"] = cand[hit], "stage0_exact"
    # 2 the event's Stage 0 match with the same two players
    s0e = s0[s0["tournament_id"].isin(set(st["tid"]))]
    pr = s0e.assign(p_lo=np.minimum(s0e["player_a_id"], s0e["player_b_id"]),
                    p_hi=np.maximum(s0e["player_a_id"], s0e["player_b_id"]))
    pr = pr.groupby(["tournament_id", "p_lo", "p_hi"])["match_id"].agg(lambda x: x.iloc[0] if len(x) == 1 else None)
    todo = st["match_id"].isna()
    got = pr.reindex(pd.MultiIndex.from_arrays([st.loc[todo, "tid"], lo[todo], hi[todo]])).to_numpy()
    idx = st.index[todo][pd.notna(got)]
    st.loc[idx, "match_id"], st.loc[idx, "link_method"] = got[pd.notna(got)], "stage0_pair"
    # 3 names (the shot-level linker) inside the event's Stage 0 matches
    todo = st["match_id"].isna() & st["tid"].isin(set(s0e["tournament_id"]))
    if use_names and todo.any():
        from src.eda.shot_level import common as S
        u = S.stage0_universe()
        u = u[u["match_id"].str.split("|").str[1].isin(set(st.loc[todo, "tid"]))].reset_index(drop=True)
        if len(u):
            u["uid"] = np.arange(len(u))
            dmap = s0e.groupby("tournament_id")["tournament_date"].first()
            rnd = st.loc[todo, "round"]
            rows = pd.DataFrame({"tour": "M", "d": st.loc[todo, "tid"].map(dmap), "name1": st.loc[todo, "p1_name"],
                                 "name2": st.loc[todo, "p2_name"], "round": rnd,
                                 "draw": np.where(rnd.astype(str).str.startswith("Q") & rnd.ne("QF"), "qual",
                                                  "main")}, index=st.index[todo])
            lk = S.Stage0Linker(universe=u).link(rows)
            ok = lk["match_id"].notna()
            st.loc[lk.index[ok], "match_id"] = lk.loc[ok, "match_id"]
            st.loc[lk.index[ok], "link_method"] = "stage0_names"
            st.loc[lk.index[ok], "a1"] = lk.loc[ok, "a1"]
    st["in_stage0"] = st["match_id"].notna()
    # 4 Tennis My Life, for matches newer than Stage 0
    todo = st["match_id"].isna()
    if todo.any():
        tml = tml_table(sorted(set(st.loc[todo, "year"]))) if tml is None else tml
        c1, c2 = st["p1_atp_id"].map(LC.atp_code), st["p2_atp_id"].map(LC.atp_code)
        cf = c1.fillna("") <= c2.fillna("")
        c_lo, c_hi = c1.where(cf, c2), c2.where(cf, c1)
        pos = pd.Series(tml.index, index=pd.MultiIndex.from_frame(tml[["tid", "c_lo", "c_hi"]]))
        pos = pos[~pos.index.duplicated(keep=False)]
        hitpos = pos.reindex(pd.MultiIndex.from_arrays([st.loc[todo, "tid"], c_lo[todo], c_hi[todo]])).to_numpy()
        for i, p_ in zip(st.index[todo], hitpos):
            if pd.isna(p_):
                continue
            r = tml.loc[int(p_)]
            st.loc[i, "match_id"] = f"atp|{r['tid']}|{r['round']}|{lo[i]}|{hi[i]}"
            st.loc[i, ["link_method", "round_tml", "level_tml"]] = ["tml", r["round"], r["level"]]
            st.loc[i, "qual_tml"] = bool(r["qualifying"])
            if r["per_match_dates"]:
                d = LC.day_of(r["d"])
                st.loc[i, ["es", "lf", "obs", "tdate"]] = [d, d + 1, d, LC.day_of(r["event_start"])]
                st.loc[i, "clock"] = "tml_date"
            else:
                d = LC.day_of(r["event_start"])
                st.loc[i, ["es", "lf", "obs", "tdate"]] = [d, d + 9, d + 3, d]
                st.loc[i, "clock"] = "tml_event_start"
    # sides, project ids and the Stage 0 fields
    s0i = s0.set_index("match_id")
    ins = st["in_stage0"]
    a_id, b_id = st["match_id"].map(s0i["player_a_id"]), st["match_id"].map(s0i["player_b_id"])
    side = pd.Series(None, index=st.index, dtype=object)
    side[ins & (a_id == x1)] = "A"
    side[ins & (b_id == x1)] = "B"
    named = st["link_method"].eq("stage0_names") & side.isna()
    side[named & st["a1"].eq(True)] = "A"
    side[named & st["a1"].eq(False)] = "B"
    tmlr = st["link_method"].eq("tml")
    if tmlr.any():
        low = st.loc[tmlr, "match_id"].map(PD.side_is_low).astype(bool)
        a_tml = lo[tmlr].where(low, hi[tmlr])
        side[tmlr] = np.where(a_tml == x1[tmlr], "A", "B")
    st["side_p1"] = side
    st["pid_p1"] = np.where(ins, np.where(side.eq("A"), a_id, np.where(side.eq("B"), b_id, None)), x1)
    st["pid_p2"] = np.where(ins, np.where(side.eq("A"), b_id, np.where(side.eq("B"), a_id, None)), x2)
    for c in ("level", "qualifying", "round", "round_order", "tournament_id"):
        st[c + "_s0"] = st["match_id"].where(ins).map(s0i[c])
    tdate_s0 = st["match_id"].where(ins).map(s0i["tournament_date"])
    st.loc[ins, "tdate"] = [LC.day_of(x) for x in tdate_s0[ins]]
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs"]).set_index("match_id")
    for c in ("es", "lf", "obs"):
        st.loc[ins, c] = st.loc[ins, "match_id"].map(tm[c])
    st.loc[ins, "clock"] = "timing"
    st["obs"] = np.floor(pd.to_numeric(st["obs"], errors="coerce"))
    return st
