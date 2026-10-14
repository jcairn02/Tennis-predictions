"""Linking every source of the Roland-Garros first-serve recount to Stage 0's matches.

A source match is placed on the Stage 0 match of the same event, year, tour, draw and round whose two players both
carry its two names (either order). Names are compared as word sets after folding accents and punctuation:
    3  the same words (any order: "DJOKOVIC Novak" = "Novak Djokovic"), or the same letters once spaces are dropped
    2  a shared surname word and the same first initial (a word of five letters or more that differs only by a
       transliteration, similarity 0.8 or more, counts as shared: "Anastasiia Sobolieva" / "Anastasiya Soboleva")
    1  a shared word of two letters or more (particles excluded), or one name's long word inside the other's letters
A match is placed when its weaker side scores at least 1 and no other Stage 0 match of that round scores as well.
RG's statistics, its MatchBeats and the Court Vision copy share RG's own match codes (SM001, ...), so they are joined
on the code; within a code, players are paired by name, never by position.
"""
from __future__ import annotations

from difflib import SequenceMatcher

import numpy as np
import pandas as pd

from src.eda.rg_first_serve_recount import sources as S

PARTICLES = {"de", "da", "di", "van", "von", "der", "del", "la", "le", "el", "dos", "du", "den", "ter", "al", "y"}
OG_ROUND = {"First Round": "R64", "Second Round": "R32", "Third Round": "R16", "Quarterfinal": "QF",
            "Quarter-final": "QF", "Quarterfinals": "QF", "Semifinal": "SF", "Semi-final": "SF", "Semifinals": "SF",
            "Gold Medal Match": "F", "Bronze Medal Match": "BR", "Final": "F"}


def name_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ta, tb = a.split(), b.split()
    if sorted(ta) == sorted(tb) or "".join(sorted(ta)) == "".join(sorted(tb)) or "".join(ta) == "".join(tb):
        return 3.0
    sa = {t for t in ta if len(t) >= 2 and t not in PARTICLES}
    sb = {t for t in tb if len(t) >= 2 and t not in PARTICLES}
    # a transliteration ("Sobolieva" / "Soboleva", "Anastasiia" / "Anastasiya") counts as a shared word
    fuzzy = any(len(x) >= 5 and len(y) >= 5 and SequenceMatcher(None, x, y).ratio() >= 0.8 for x in sa for y in sb)
    if sa & sb or fuzzy:
        return 2.0 if ta[0][0] == tb[0][0] or ta[-1][0] == tb[0][0] or ta[0][0] == tb[-1][0] else 1.0
    ja, jb = "".join(ta), "".join(tb)
    if any(len(t) >= 4 and t in jb for t in sa) or any(len(t) >= 4 and t in ja for t in sb):
        return 1.0
    return 0.0


def stage0_matches(s0: pd.DataFrame) -> pd.DataFrame:
    """One row per Stage 0 match: its keys and the two player rows' names and ids."""
    a = s0[s0["side"].eq("A")].set_index("match_id")
    b = s0[s0["side"].eq("B")].set_index("match_id")
    m = a[["event", "year", "tour", "draw", "round"]].copy()
    m["key_a"], m["key_b"] = a["name_key"], b["name_key"].reindex(a.index)
    m["pid_a"], m["pid_b"] = a["player_id"], b["player_id"].reindex(a.index)
    return m.reset_index()


def place(src: pd.DataFrame, s0m: pd.DataFrame, keys: list[str], k1: str, k2: str) -> pd.DataFrame:
    """For each source match (one row with names k1, k2 and the columns ``keys`` in Stage 0's terms), the Stage 0
    match and which source name is Stage 0's side A. Returns src with match_id, a_is ('1' or '2'), score, how."""
    groups = {k: g for k, g in s0m.groupby(keys)}
    out = []
    for r in src.itertuples(index=False):
        rec = r._asdict()
        cand = groups.get(tuple(rec[k] for k in keys))
        best, tie = None, False
        if cand is not None:
            for c in cand.itertuples(index=False):
                for a_is, (x, y) in (("1", (rec[k1], rec[k2])), ("2", (rec[k2], rec[k1]))):
                    sa, sb = name_score(x, c.key_a), name_score(y, c.key_b)
                    sc = (min(sa, sb), sa + sb)
                    if sc[0] < 1:
                        continue
                    if best is None or sc > best[0]:
                        best, tie = (sc, c.match_id, a_is), False
                    elif sc == best[0] and c.match_id != best[1]:
                        tie = True
        if best is None or tie:
            out.append({**rec, "match_id": None, "a_is": None, "link_score": None,
                        "link": "tie" if tie else "none"})
        else:
            out.append({**rec, "match_id": best[1], "a_is": best[2], "link_score": best[0][0], "link": "names"})
    return pd.DataFrame(out)


def pair_slots(left: pd.DataFrame, right: pd.DataFrame, on: list[str], lkey: str, rkey: str,
               lslot: str, rslot: str) -> pd.DataFrame:
    """Within each code, pair the two players of ``left`` with those of ``right`` by name (both orders tried).
    Returns on + [lslot, rslot, pair_score]."""
    out = []
    rg = {k: g for k, g in right.groupby(on)}
    for k, g in left.groupby(on):
        h = rg.get(k if isinstance(k, tuple) else (k,))
        if h is None or len(g) != 2 or len(h) != 2:
            continue
        g, h = g.sort_values(lslot), h.sort_values(rslot)
        straight = min(name_score(g[lkey].iloc[0], h[rkey].iloc[0]), name_score(g[lkey].iloc[1], h[rkey].iloc[1]))
        crossed = min(name_score(g[lkey].iloc[0], h[rkey].iloc[1]), name_score(g[lkey].iloc[1], h[rkey].iloc[0]))
        if max(straight, crossed) < 1 or straight == crossed:
            continue
        order = [0, 1] if straight > crossed else [1, 0]
        for i in range(2):
            out.append({**dict(zip(on, k if isinstance(k, tuple) else (k,))), lslot: g[lslot].iloc[i],
                        rslot: h[rslot].iloc[order[i]], "pair_score": max(straight, crossed)})
    return pd.DataFrame(out)


def rg_codes(s0: pd.DataFrame) -> pd.DataFrame:
    """RG match code -> Stage 0 match, from RG's own statistics (full names): one row per (year, code, team) with the
    Stage 0 player row it is (match_id, player_id)."""
    api = S.api()
    s0m = stage0_matches(s0[s0["event"].eq("RG")])
    m = api.pivot_table(index=["year", "match_id", "tour", "draw", "round"], columns="team",
                        values="name_key", aggfunc="first").reset_index()
    m = m.rename(columns={"match_id": "code", "A": "name1", "B": "name2"})
    m["event"] = "RG"
    placed = place(m, s0m, ["event", "year", "tour", "draw", "round"], "name1", "name2")
    rows = []
    s0m_i = s0m.set_index("match_id")
    for r in placed.itertuples():
        if pd.isna(r.match_id):
            rows += [{"year": r.year, "code": r.code, "team": t, "match_id": None, "player_id": None, "link": r.link}
                     for t in ("A", "B")]
            continue
        sa, sb = s0m_i.loc[r.match_id, "pid_a"], s0m_i.loc[r.match_id, "pid_b"]
        team_of_a = "A" if r.a_is == "1" else "B"
        rows.append({"year": r.year, "code": r.code, "team": team_of_a, "match_id": r.match_id, "player_id": sa,
                     "link": r.link, "link_score": r.link_score})
        rows.append({"year": r.year, "code": r.code, "team": "B" if team_of_a == "A" else "A", "match_id": r.match_id,
                     "player_id": sb, "link": r.link, "link_score": r.link_score})
    return pd.DataFrame(rows)


def og_units(s0: pd.DataFrame) -> pd.DataFrame:
    """Olympic unit -> Stage 0 match: one row per (unit, athlete_code) with the Stage 0 player row."""
    ol = S.olympics()
    s0m = stage0_matches(s0[s0["event"].eq("OG")])
    desc = ol.groupby("unit")[["description", "tour"]].first()
    desc["round"] = desc["description"].map(lambda d: next((v for k, v in OG_ROUND.items() if str(d).endswith(k)), None))
    names = ol.pivot_table(index="unit", columns="side", values="name_key", aggfunc="first")
    codes = ol.pivot_table(index="unit", columns="side", values="athlete_code", aggfunc="first")
    m = desc.join(names).reset_index().rename(columns={"home": "name1", "away": "name2"})
    m["event"], m["year"], m["draw"] = "OG", 2024, "main"
    placed = place(m, s0m, ["event", "year", "tour", "draw", "round"], "name1", "name2")
    s0m_i = s0m.set_index("match_id")
    rows = []
    for r in placed.itertuples():
        if pd.isna(r.match_id):
            continue
        a_code = codes.loc[r.unit, "home" if r.a_is == "1" else "away"]
        b_code = codes.loc[r.unit, "away" if r.a_is == "1" else "home"]
        rows.append({"unit": r.unit, "athlete_code": a_code, "match_id": r.match_id,
                     "player_id": s0m_i.loc[r.match_id, "pid_a"], "link_score": r.link_score})
        rows.append({"unit": r.unit, "athlete_code": b_code, "match_id": r.match_id,
                     "player_id": s0m_i.loc[r.match_id, "pid_b"], "link_score": r.link_score})
    return pd.DataFrame(rows), placed


MCP_ROUND = {"Q1": "Q1", "Q2": "Q2", "Q3": "Q3", "R128": "R128", "R64": "R64", "R32": "R32", "R16": "R16",
             "QF": "QF", "SF": "SF", "F": "F", "BR": "BR"}


def mcp_rows(s0: pd.DataFrame) -> pd.DataFrame:
    """MCP charts of Roland Garros 2019-2026 and the Paris Olympics -> Stage 0 player rows."""
    o = S.mcp()
    t = o["tournament"].astype(str)
    o = o[(t.str.contains("Roland Garros", case=False) & o["year"].between(2019, 2026))
          | (t.str.contains("Olympic", case=False) & o["year"].eq(2024))].copy()
    o["event"] = np.where(o["tournament"].astype(str).str.contains("Olympic", case=False), "OG", "RG")
    o["round"] = o["round"].astype(str).map(MCP_ROUND)
    o["draw"] = np.where(o["round"].astype(str).str.fullmatch(r"Q\d"), "qual", "main")   # QF is the main draw
    m = o.groupby("match_id").agg(event=("event", "first"), year=("year", "first"), tour=("tour", "first"),
                                  draw=("draw", "first"), round=("round", "first"),
                                  name1=("p1", "first"), name2=("p2", "first")).reset_index()
    m["name1"], m["name2"] = m["name1"].map(S.nkey), m["name2"].map(S.nkey)
    m = m.rename(columns={"match_id": "mcp_id"})
    s0m = stage0_matches(s0)
    placed = place(m, s0m, ["event", "year", "tour", "draw", "round"], "name1", "name2")
    placed = placed[placed["match_id"].notna()]
    rows = []
    s0m_i = s0m.set_index("match_id")
    for r in placed.itertuples():
        g = o[o["match_id"].eq(r.mcp_id)]
        for who, pid in ((r.name1 if r.a_is == "1" else r.name2, s0m_i.loc[r.match_id, "pid_a"]),
                         (r.name2 if r.a_is == "1" else r.name1, s0m_i.loc[r.match_id, "pid_b"])):
            h = g[g["name_key"].eq(who)]
            if len(h) != 1:
                continue
            h = h.iloc[0]
            rows.append({"match_id": r.match_id, "player_id": pid, "mcp_id": r.mcp_id,
                         **{f"mcp_{c}": h[c] for c in ("svpt", "first_in", "first_won", "second_won", "ace", "df")}})
    return pd.DataFrame(rows)
