"""Readers of the result and context fields of every source the match-timing link files place on Stage 0's matches.

Each reader takes the source_keys of a link file and returns one row per key (indexed by source_key) with:
    p1, p2            the two players as the source writes them (p1 = its first / home / team-1 / winner player)
    s0_id1, s0_id2    Stage 0 player ids where the source gives them in Stage 0's own form (Open Tennis Data, the Live
                      Tennis API's Sackmann crosswalk), else None
    p1_won            1.0 the first player won, 0.0 the second, NaN not given
    sets              list of (games_1, games_2, tiebreak_points_1, tiebreak_points_2), the first player first; None
                      for tiebreak points not given
    status            ctx_common.norm_status() of the source's own status field
    seed1, seed2      the source's seeds as numbers (NaN unseeded or not given); entry1, entry2 its entry codes
    surface_raw, indoor_raw, level_raw, round_raw, best_of_raw, draw_raw, tournament_raw, day_raw
                      the context fields as the source writes them (NaN where it has none)
Read-only. The key formats are the link builders' (src/eda/match_timing/srcc_*.py, srcb_sources.py,
link_flashscore.py).
"""
from __future__ import annotations

import gzip
import json
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.eda.source_reconciliation import common as C
from src.eda.source_reconciliation import ctx_common as X

ROOT = C.ROOT
DUMP = C.DUMP
HANDOFF = C.HANDOFF
COLS = ["p1", "p2", "s0_id1", "s0_id2", "p1_won", "sets", "status", "seed1", "seed2", "entry1", "entry2",
        "surface_raw", "indoor_raw", "level_raw", "round_raw", "best_of_raw", "draw_raw", "tournament_raw", "day_raw"]


def _finish(df: pd.DataFrame, keys) -> pd.DataFrame:
    for c in COLS:
        if c not in df:
            df[c] = None if c not in ("p1_won", "seed1", "seed2") else np.nan
    df = df[~df.index.duplicated(keep="first")]
    want = pd.Index(pd.Series(list(keys)).astype(str).unique())
    return df.reindex(want)[COLS]


# ------------------------------------------------------------------------------------------------ tennis-data.co.uk

def tennis_data(keys) -> pd.DataFrame:
    """'<partition>#<row>': the row's position in its staged partition (Stage 1's td_row). Winner first."""
    k = pd.Series(list(keys), dtype=str).drop_duplicates()
    parts = k.str.rsplit("#", n=1)
    frame = pd.DataFrame({"key": k.to_numpy(), "file": parts.str[0].to_numpy(), "row": parts.str[1].astype(int).to_numpy()})
    out = []
    for f, g in frame.groupby("file"):
        have = set(pq.read_schema(ROOT / f).names)
        cols = [c for c in ["Location", "Tournament", "Date", "Series", "Tier", "Court", "Surface", "Round", "Best of",
                            "Winner", "Loser", "Comment", "Wsets", "Lsets", "WRank", "LRank"]
                + [f"{s}{i}" for i in range(1, 6) for s in "WL"] if c in have]
        raw = pd.read_parquet(ROOT / f, columns=cols)
        sub = raw.iloc[g["row"].to_numpy()].copy()
        sub.index = g["key"].to_numpy()
        sub["_file"] = f
        out.append(sub)
    t = pd.concat(out)
    sets = []
    for _, r in t.iterrows():
        s = []
        for i in range(1, 6):
            w, l = X.int_or_none(r.get(f"W{i}")), X.int_or_none(r.get(f"L{i}"))
            if w is None or l is None:
                break
            s.append((w, l, None, None))
        sets.append(s)
    level = t["Series"] if "Series" in t else pd.Series(None, index=t.index)
    if "Tier" in t:
        level = level.where(level.notna(), t["Tier"])
    df = pd.DataFrame({
        "p1": t["Winner"], "p2": t["Loser"], "p1_won": 1.0, "sets": sets, "status": t["Comment"].map(X.norm_status),
        "surface_raw": t["Surface"], "indoor_raw": t["Court"], "level_raw": level, "round_raw": t["Round"],
        "best_of_raw": t["Best of"], "tournament_raw": t["Tournament"], "day_raw": t["Date"].astype(str),
        "location": t["Location"], "td_file": t["_file"]}, index=t.index)
    return _finish(df, keys).join(df[["location", "td_file"]])


# ------------------------------------------------------------------------------------------------ api-tennis.com

def _api_sets(js) -> list:
    """scores_json: [{'score_first': '6.4', 'score_second': '7.7', 'score_set': '1'}, ...]: games, then the
    tiebreak's points after the dot."""
    try:
        v = json.loads(js) if isinstance(js, str) and js.startswith("[") else []
    except ValueError:
        return []
    out = []
    for d in sorted(v, key=lambda d: int(d.get("score_set", 0) or 0)):
        a, b = str(d.get("score_first", "")), str(d.get("score_second", ""))
        ma, mb = re.match(r"^(\d+)(?:\.(\d+))?$", a), re.match(r"^(\d+)(?:\.(\d+))?$", b)
        if not ma or not mb:
            break
        ta = int(ma.group(2)) if ma.group(2) else None
        tb = int(mb.group(2)) if mb.group(2) else None
        out.append((int(ma.group(1)), int(mb.group(1)), ta, tb))
    return out


def api_tennis(keys) -> pd.DataFrame:
    frames = []
    for p in sorted((HANDOFF / "api_tennis").glob("fixtures_*.csv*")):
        frames.append(pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False))
    f = pd.concat(frames, ignore_index=True).drop_duplicates("event_key").set_index("event_key")
    f = f.reindex(pd.Index(pd.Series(list(keys)).astype(str).unique()))
    win = f["event_winner"].map({"First Player": 1.0, "Second Player": 0.0})
    df = pd.DataFrame({
        "p1": f["event_first_player"], "p2": f["event_second_player"], "p1_won": win,
        "sets": f["scores_json"].map(_api_sets), "status": f["event_status"].map(X.norm_status),
        "round_raw": f["tournament_round"], "level_raw": f["event_type_type"], "tournament_raw": f["tournament_name"],
        "day_raw": f["event_date"], "qual_raw": f["event_qualification"]}, index=f.index)
    return _finish(df, keys).join(df[["qual_raw"]])


# ------------------------------------------------------------------------------------------------ Open Tennis Data

def _first(js):
    from src.eda.merge_feasibility import scan as S
    v = S.parse_list(js)
    return str(v[0]) if v else None


def open_tennis_data(keys) -> pd.DataFrame:
    """completed.parquet: player ids are Sackmann's (Stage 0's form); the score is winner first."""
    o = pd.read_parquet(DUMP / "matches" / "open_tennis_data" / "completed.parquet")
    o = o.drop_duplicates("match_id").set_index("match_id")
    o = o.reindex(pd.Index(pd.Series(list(keys)).astype(str).unique()))
    id1, id2, wid = o["player1_id"].map(_first), o["player2_id"].map(_first), o["winner_id"].map(_first)
    p1_won = np.where(wid.isna(), np.nan, np.where(wid == id1, 1.0, np.where(wid == id2, 0.0, np.nan)))
    from src.eda.match_timing import srcb_common as SB
    sets = []
    for sc, w in zip(o["score"], p1_won):
        s = [(a, b, None, None) for a, b in SB.sets_of_score(sc)] if isinstance(sc, str) else []
        sets.append(s if w != 0.0 else [(b, a, None, None) for a, b, _, _ in s])
    df = pd.DataFrame({
        "p1": o["player1_name"].map(_first), "p2": o["player2_name"].map(_first), "s0_id1": id1, "s0_id2": id2,
        "p1_won": p1_won, "sets": sets, "status": o["status"].map(X.norm_status),
        "seed1": o["player1_seed"].map(X.seed_num), "seed2": o["player2_seed"].map(X.seed_num),
        "round_raw": o["round"], "best_of_raw": o["best_of"], "draw_raw": o["draw"], "tournament_raw": o["tournament_name"],
        "day_raw": o["date"], "provenance": o["source"]}, index=o.index)
    return _finish(df, keys).join(df[["provenance"]])


# ------------------------------------------------------------------------------------------------ Flashscore

def flashscore(keys) -> pd.DataFrame:
    """The parsed records (links/flashscore_records.parquet): home first; set scores without tiebreak points."""
    r = pd.read_parquet(C.SNAP / "links" / "flashscore_records.parquet",
                        columns=["fs_match_id", "home_name", "away_name", "winner", "set_scores", "status", "surface",
                                 "category", "category_guess", "round", "round_raw", "tournament_name", "start_utc",
                                 "gender", "is_doubles"])
    r = r.drop_duplicates("fs_match_id").set_index("fs_match_id")
    r = r.reindex(pd.Index(pd.Series(list(keys)).astype(str).unique()))
    sets = []
    for s in r["set_scores"]:
        out = []
        for tok in str(s or "").split():
            m = re.match(r"^(\d+)-(\d+)$", tok)
            if not m:
                break
            out.append((int(m.group(1)), int(m.group(2)), None, None))
        sets.append(out)
    df = pd.DataFrame({
        "p1": r["home_name"], "p2": r["away_name"], "p1_won": r["winner"].map({"home": 1.0, "away": 0.0}),
        "sets": sets, "status": r["status"].map(X.norm_status), "surface_raw": r["surface"],
        "level_raw": r["category"].where(r["category"].notna(), r["category_guess"]),
        "round_raw": r["round"].where(r["round"].notna(), r["round_raw"]), "tournament_raw": r["tournament_name"],
        "day_raw": r["start_utc"].astype(str)}, index=r.index)
    return _finish(df, keys)


# ------------------------------------------------------------------------------------------------ the Slams' own feeds

def _ao_side(score) -> list:
    """'7 4 6 7(7)' -> [(7, None), (4, None), (6, None), (7, 7)]: one team's games and its own tiebreak points."""
    out = []
    for tok in str(score or "").split():
        m = re.match(r"^(\d+)(?:\((\d+)\))?$", tok)
        if not m:
            break
        out.append((int(m.group(1)), int(m.group(2)) if m.group(2) else None))
    return out


def _st_sets(text) -> list:
    """SlamTracker's score_text, team 1 first: '6-7(6) 3-6 6-4': the bracket holds the tiebreak loser's points."""
    out = []
    for tok in str(text or "").split():
        m = re.match(r"^(\d+)-(\d+)(?:\((\d+)\))?$", tok)
        if not m:
            break
        a, b = int(m.group(1)), int(m.group(2))
        t = int(m.group(3)) if m.group(3) else None
        ta = tb = None
        if t is not None and {a, b} == {7, 6}:
            if a < b:
                ta, tb = t, max(7, t + 2)
            else:
                ta, tb = max(7, t + 2), t
        out.append((a, b, ta, tb))
    return out


def slam_feeds(keys) -> pd.DataFrame:
    keys = pd.Series(list(keys), dtype=str).drop_duplicates()
    rows = []
    # Australian Open: match centre (api), its Wayback captures, and the archived draws
    ao_keys = keys[keys.str.startswith("ausopen:")]
    if len(ao_keys):
        m = pq.read_table(DUMP / "points" / "ausopen" / "matches.parquet").to_pandas()
        a = pq.read_table(DUMP / "points" / "ausopen" / "archived_draws.parquet").to_pandas()
        for t in (m, a):
            t["year"] = t["year"].astype(int)
        done = m["match_status"].isin(["CMP", "RET", "W/O"])
        m = m.assign(_done=done.astype(int)).sort_values(
            ["year", "match_id", "_done"] + (["capture_timestamp"] if "capture_timestamp" in m else []))
        api = m[m["route"].eq("api")].drop_duplicates(["year", "match_id"], keep="last")
        way = m[~m["route"].eq("api")].drop_duplicates(["year", "match_id"], keep="last")
        arch = a.drop_duplicates(["year", "match_id"], keep="last")
        for key in ao_keys:
            body = key.split(":", 1)[1]
            kind = "api"
            if body.endswith("@wayback"):
                kind, body = "wayback", body[: -len("@wayback")]
            elif body.endswith("@archived_draw"):
                kind, body = "archived", body[: -len("@archived_draw")]
            y, mid = body.split("/", 1)
            src = {"api": api, "wayback": way, "archived": arch}[kind]
            hit = src[(src["year"] == int(y)) & (src["match_id"] == mid)]
            if hit.empty:
                continue
            r = hit.iloc[-1]
            if r.get("match_status") not in ("CMP", "RET", "W/O"):
                continue                       # a capture taken before the match ended: no result
            s1, s2 = _ao_side(r.get("team1_score")), _ao_side(r.get("team2_score"))
            sets = [(x[0], y_[0], x[1] if {x[0], y_[0]} == {7, 6} else None,
                     y_[1] if {x[0], y_[0]} == {7, 6} else None) for x, y_ in zip(s1, s2)]
            # one side's own tiebreak points only: the other's from the 7-point rule where needed
            sets = [(g1, g2, t1 if t1 is not None else (None if t2 is None else (max(7, t2 + 2) if g1 > g2 else None)),
                     t2 if t2 is not None else (None if t1 is None else (max(7, t1 + 2) if g2 > g1 else None)))
                    for g1, g2, t1, t2 in sets]
            wt = str(r.get("winner_team", "")).strip()
            rows.append({"key": key, "p1": r.get("team1_names"), "p2": r.get("team2_names"),
                         "p1_won": {"1": 1.0, "2": 0.0}.get(wt[:1], np.nan), "sets": sets,
                         "status": {"CMP": "completed", "RET": "retired", "W/O": "walkover"}.get(r.get("match_status")),
                         "seed1": X.seed_num(r.get("team1_seed")), "seed2": X.seed_num(r.get("team2_seed")),
                         "entry1": r.get("team1_entry_status"), "entry2": r.get("team2_entry_status"),
                         "round_raw": r.get("round_name"), "tournament_raw": "Australian Open " + str(r.get("event")),
                         "day_raw": str(r.get("date"))})
    for site in ("wimbledon", "usopen"):
        sk = keys[keys.str.startswith(site + ":")]
        if not len(sk):
            continue
        cols = ["year", "event", "match_id", "entry.roundCode", "entry.statusCode", "entry.score_text", "entry.winner",
                "entry.team1.firstNameA", "entry.team1.lastNameA", "entry.team2.firstNameA", "entry.team2.lastNameA",
                "entry.team1.seed", "entry.team2.seed", "entry.team1.entryStatus", "entry.team2.entryStatus",
                "entry.eventDay"]
        m = pq.read_table(DUMP / "points" / site / "matches.parquet", columns=cols).to_pandas()
        m["key"] = site + ":" + m["year"].astype(int).astype(str) + "/" + m["event"] + "/" + m["match_id"].astype(str)
        m = m.drop_duplicates("key", keep="last").set_index("key").reindex(sk)
        for key, r in m.iterrows():
            if pd.isna(r["year"]):
                continue
            rows.append({"key": key,
                         "p1": f"{r['entry.team1.firstNameA'] or ''} {r['entry.team1.lastNameA'] or ''}".strip(),
                         "p2": f"{r['entry.team2.firstNameA'] or ''} {r['entry.team2.lastNameA'] or ''}".strip(),
                         "p1_won": {"1": 1.0, "2": 0.0}.get(str(r["entry.winner"]).strip()[:1], np.nan),
                         "sets": _st_sets(r["entry.score_text"]),
                         "status": {"D": "completed", "E": "retired", "F": "walkover"}.get(r["entry.statusCode"]),
                         "seed1": X.seed_num(r["entry.team1.seed"]), "seed2": X.seed_num(r["entry.team2.seed"]),
                         "entry1": r["entry.team1.entryStatus"], "entry2": r["entry.team2.entryStatus"],
                         "round_raw": r["entry.roundCode"], "tournament_raw": f"{site} {r['event']}",
                         "day_raw": str(r["entry.eventDay"])})
    df = pd.DataFrame(rows).set_index("key") if rows else pd.DataFrame(columns=["key"]).set_index("key")
    return _finish(df, keys)


# ------------------------------------------------------------------------------------------------ the WTA API

WTA = DUMP / "points" / "wta"


def wta_api(keys) -> pd.DataFrame:
    """'wta:<tournament_id>/<year>/<match_id>'. Winner 2 / 4: A won (4 by retirement); 3 / 5: B won; 6 / 7
    walkover; ScoreTbSet<k> holds the tiebreak loser's points."""
    keys = pd.Series(list(keys), dtype=str).drop_duplicates()
    sc = [f"ScoreSet{k}{s}" for k in range(1, 6) for s in "AB"] + [f"ScoreTbSet{k}" for k in range(1, 5)]
    cols = ["tournament_id", "match_id", "tier", "draw", "walkover", "RoundID", "MatchState", "Winner", "ScoreString",
            "PlayerIDA", "PlayerNameFirstA", "PlayerNameLastA", "PlayerIDB", "PlayerNameFirstB", "PlayerNameLastB",
            "SeedA", "SeedB", "EntryTypeA", "EntryTypeB", "MatchTimeStamp"] + sc
    frames = []
    for y in range(2019, 2027):
        path = WTA / "matches" / f"{y}.parquet"
        have = set(pq.read_schema(path).names)
        t = pq.read_table(path, columns=[c for c in cols if c in have]).to_pandas()
        frames.append(t.assign(year=y))
    m = pd.concat(frames, ignore_index=True)
    m["key"] = "wta:" + m["tournament_id"].astype(str) + "/" + m["year"].astype(str) + "/" + m["match_id"].astype(str)
    m = m.drop_duplicates("key", keep="last").set_index("key").reindex(keys)
    sets = []
    for _, r in m.iterrows():
        s = []
        for k in range(1, 6):
            a, b = X.int_or_none(r.get(f"ScoreSet{k}A")), X.int_or_none(r.get(f"ScoreSet{k}B"))
            if a is None or b is None:
                break
            t = X.int_or_none(r.get(f"ScoreTbSet{k}")) if k <= 4 else None
            ta = tb = None
            if t is not None and {a, b} == {7, 6}:
                ta, tb = (t, max(7, t + 2)) if a < b else (max(7, t + 2), t)
            s.append((a, b, ta, tb))
        sets.append(s)
    win = m["Winner"].astype(str)
    p1_won = np.where(win.isin(["2", "4", "6"]), 1.0, np.where(win.isin(["3", "5", "7"]), 0.0, np.nan))
    walk = win.isin(["6", "7"]) | m["walkover"].astype(str).str.upper().eq("TRUE")
    status = np.where(walk, "walkover", np.where(win.isin(["4", "5"]), "retired",
                                                  np.where(win.isin(["2", "3"]), "completed", None)))
    df = pd.DataFrame({
        "p1": (m["PlayerNameFirstA"].fillna("") + " " + m["PlayerNameLastA"].fillna("")).str.strip(),
        "p2": (m["PlayerNameFirstB"].fillna("") + " " + m["PlayerNameLastB"].fillna("")).str.strip(),
        "p1_won": p1_won, "sets": sets, "status": status,
        "seed1": m["SeedA"].map(X.seed_num), "seed2": m["SeedB"].map(X.seed_num),
        "entry1": m["EntryTypeA"], "entry2": m["EntryTypeB"], "level_raw": m["tier"], "round_raw": m["RoundID"],
        "draw_raw": m["draw"], "tournament_raw": m["tournament_id"].astype(str), "day_raw": m["MatchTimeStamp"],
        "wta_id1": m["PlayerIDA"].astype(str), "wta_id2": m["PlayerIDB"].astype(str),
        "score_string": m["ScoreString"]}, index=m.index)
    return _finish(df, keys).join(df[["wta_id1", "wta_id2", "score_string"]])


# ------------------------------------------------------------------------------------------------ TDI

def _tdi_side(text) -> dict:
    """'1:4 2:7/7 3:6' -> {1: (4, None), 2: (7, 7), 3: (6, None)}."""
    out = {}
    for tok in str(text or "").split():
        m = re.match(r"^(\d+):(\d+)(?:/(\d+))?$", tok)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), int(m.group(3)) if m.group(3) else None)
    return out


def tdi(keys) -> pd.DataFrame:
    """'tdi:<match id>'. Team A first; the winner is the side whose sets lead description_score (winner first, 'RET'
    marking a retirement)."""
    t = pq.read_table(DUMP / "points" / "tdi" / "matches.parquet").to_pandas()
    t["key"] = "tdi:" + t["match_id"].astype(str)
    t = t.drop_duplicates("key", keep="last").set_index("key").reindex(pd.Index(pd.Series(list(keys)).astype(str).unique()))
    sets, won, status = [], [], []
    for _, r in t.iterrows():
        a, b = _tdi_side(r.get("team_a_scores")), _tdi_side(r.get("team_b_scores"))
        s = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                break
            ta, tb = a[k][1], b[k][1]
            s.append((a[k][0], b[k][0], ta, tb))
        sets.append(s)
        desc = str(r.get("description_score") or "")
        ws = [(int(x), int(y)) for x, y in re.findall(r"(\d+)/(\d+)", desc)]
        w = np.nan
        if ws and s:
            fa = [(x[0], x[1]) for x in s][: len(ws)]
            fb = [(x[1], x[0]) for x in s][: len(ws)]
            if fa == ws and fb != ws:
                w = 1.0
            elif fb == ws and fa != ws:
                w = 0.0
        won.append(w)
        d = desc.lower()
        status.append("retired" if "ret" in d else "walkover" if ("w/o" in d or "walkover" in d) else
                      "defaulted" if "def" in d else ("completed" if ws else None))
    df = pd.DataFrame({
        "p1": t["team_a_names"], "p2": t["team_b_names"], "p1_won": won, "sets": sets, "status": status,
        "seed1": t["team_a_entry"].map(X.seed_num), "seed2": t["team_b_entry"].map(X.seed_num),
        "entry1": t["team_a_entry"], "entry2": t["team_b_entry"], "level_raw": t["level"], "round_raw": t["round"],
        "draw_raw": t["draw"], "tournament_raw": t["tournament"], "day_raw": t["first_point_time"]}, index=t.index)
    return _finish(df, keys)


# ------------------------------------------------------------------------------------------------ SofaScore

SOFA = ("sofascore", "sofascore_editions", "sofascore_tournaments")


def sofascore(keys) -> pd.DataFrame:
    """'sofascore:<event_id>' in the three collections (the first collection's row where an event is in several, as
    srcc_sofascore.load keeps it). Home first; winner_code 1 home, 2 away; home_tb<k> each side's tiebreak points."""
    cols = (["event_id", "start_timestamp", "tournament_name", "unique_tournament_name", "category_name", "round_name",
             "status_description", "winner_code", "home_name", "away_name", "home_seed", "away_seed", "ground_type"]
            + [f"{s}_set{k}" for k in range(1, 6) for s in ("home", "away")]
            + [f"{s}_tb{k}" for k in range(1, 6) for s in ("home", "away")])
    frames = []
    for c in SOFA:
        path = DUMP / "points" / c / "events.parquet"
        have = set(pq.read_schema(path).names)
        frames.append(pq.read_table(path, columns=[x for x in cols if x in have]).to_pandas())
    e = pd.concat(frames, ignore_index=True).drop_duplicates("event_id")
    e["key"] = "sofascore:" + e["event_id"].astype(str)
    e = e.set_index("key").reindex(pd.Index(pd.Series(list(keys)).astype(str).unique()))
    sets = []
    for _, r in e.iterrows():
        s = []
        for k in range(1, 6):
            a, b = X.int_or_none(r.get(f"home_set{k}")), X.int_or_none(r.get(f"away_set{k}"))
            if a is None or b is None:
                break
            s.append((a, b, X.int_or_none(r.get(f"home_tb{k}")), X.int_or_none(r.get(f"away_tb{k}"))))
        sets.append(s)
    wc = e["winner_code"].astype(str).str.replace(".0", "", regex=False)
    df = pd.DataFrame({
        "p1": e["home_name"], "p2": e["away_name"], "p1_won": wc.map({"1": 1.0, "2": 0.0}), "sets": sets,
        "status": e["status_description"].map(X.norm_status), "seed1": e["home_seed"].map(X.seed_num),
        "seed2": e["away_seed"].map(X.seed_num), "entry1": e["home_seed"], "entry2": e["away_seed"],
        "surface_raw": e["ground_type"], "indoor_raw": e["ground_type"], "level_raw": e["category_name"],
        "round_raw": e["round_name"], "tournament_raw": e["tournament_name"],
        "day_raw": pd.to_datetime(pd.to_numeric(e["start_timestamp"], errors="coerce"), unit="s", utc=True).astype(str)},
        index=e.index)
    return _finish(df, keys)


# ------------------------------------------------------------------------------------------------ the Live Tennis API

def live_tennis_api(keys) -> pd.DataFrame:
    """The Zenodo match index: no score or winner, only a status; players by id, with the Sackmann crosswalk."""
    lm = pd.read_parquet(DUMP / "matches" / "live_tennis_api_zenodo" / "matches.parquet")
    lp = pd.read_parquet(DUMP / "players" / "live_tennis_api_zenodo" / "players.parquet",
                         columns=["player_id", "name", "tour", "sackmann_id"])
    lm = lm.drop_duplicates("match_id").set_index(lm.drop_duplicates("match_id")["match_id"].astype(str))
    lm = lm.reindex(pd.Index(pd.Series(list(keys)).astype(str).unique()))
    names = dict(zip(lp["player_id"], lp["name"]))
    tour = dict(zip(lp["player_id"], lp["tour"]))
    sack = dict(zip(lp["player_id"], lp["sackmann_id"]))

    def sid(pid):
        s, t = sack.get(pid), tour.get(pid)
        if blank_s(s) or t not in ("atp", "wta"):
            return None
        return f"{t}:{s}"
    df = pd.DataFrame({
        "p1": lm["player1_id"].map(names), "p2": lm["player2_id"].map(names),
        "s0_id1": lm["player1_id"].map(sid), "s0_id2": lm["player2_id"].map(sid),
        "p1_won": np.nan, "sets": [[] for _ in range(len(lm))], "status": lm["event_status"].map(X.norm_status),
        "surface_raw": lm["surface"], "indoor_raw": lm["indoor"], "level_raw": lm["tier_key"], "round_raw": lm["round"],
        "best_of_raw": lm["best_of"], "tournament_raw": lm["tournament"], "day_raw": lm["scheduled_time_utc"],
        "qual_raw": lm["is_qualifying"]}, index=lm.index)
    return _finish(df, keys).join(df[["qual_raw"]])


def blank_s(v) -> bool:
    return X.blank(v)


# ------------------------------------------------------------------------------------------------ Infosys (handoff)

def _infosys_file(path: str) -> list[dict]:
    """One dict per singles record of one handoff file (a worker process): ids, names, seeds, winner and status."""
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    rows = []
    with opener(p, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            code = str(r.get("match_id") or "")
            if not re.match(r"^[MQ]S\d+$", code):
                continue
            ms = r.get("match_status") or {}
            pdx = ms.get("playerData") or {}
            rows.append({"folder": p.parent.name, "year": r.get("year"), "tournament_id": r.get("tournament_id"),
                         "code": code, "match_date": r.get("match_date"),
                         "first1": pdx.get("tm1Ply1FirstName"), "last1": pdx.get("tm1Ply1LastName"),
                         "first2": pdx.get("tm2Ply1FirstName"), "last2": pdx.get("tm2Ply1LastName"),
                         "name1": r.get("player1_name"), "name2": r.get("player2_name"),
                         "id1": r.get("player1_id"), "id2": r.get("player2_id"),
                         "seed1": r.get("player1_seed"), "seed2": r.get("player2_seed"),
                         "pseed1": pdx.get("tm1Seed"), "pseed2": pdx.get("tm2Seed"),
                         "winner": ms.get("matchWinner"), "status": ms.get("matchStatus")})
    return rows


INFOSYS_CACHE = X.WORK / "infosys_records.parquet"


def infosys_records(workers: int = 3) -> pd.DataFrame:
    """Every singles record of the handoff's Infosys files (cached in work/; a run needs a __main__ guard on Windows,
    the reader starts worker processes)."""
    if INFOSYS_CACHE.exists():
        return pd.read_parquet(INFOSYS_CACHE)
    paths = sorted(str(p) for d in ("infosys_deep", "infosys_full") for p in (HANDOFF / d).glob("*_data.jsonl*"))
    paths.sort(key=lambda s: -Path(s).stat().st_size)
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for part in ex.map(_infosys_file, paths):
            rows.extend(part)
    r = pd.DataFrame(rows).astype(str).replace({"None": None, "nan": None})
    X.WORK.mkdir(parents=True, exist_ok=True)
    r.to_parquet(INFOSYS_CACHE, index=False)
    return r


def infosys(keys, workers: int = 3) -> pd.DataFrame:
    """'<year>_<tournament_id>_<code>' in the handoff's infosys_deep and infosys_full (one record per match, deep first,
    as srcb_sources.load_infosys keeps it). matchWinner 1 / 2; matchStatus as given (C, R, W ...)."""
    r = infosys_records(workers).copy()
    r["year"] = pd.to_numeric(r["year"], errors="coerce")
    r = r[r["year"].between(2010, 2026)]
    r["key"] = r["year"].astype(int).astype(str) + "_" + r["tournament_id"].astype(str) + "_" + r["code"]
    r = r.sort_values(["key", "folder"]).drop_duplicates("key", keep="first").set_index("key")
    r = r.reindex(pd.Index(pd.Series(list(keys)).astype(str).unique()))
    p1 = (r["first1"].fillna("") + " " + r["last1"].fillna("")).str.strip()
    p2 = (r["first2"].fillna("") + " " + r["last2"].fillna("")).str.strip()
    w = pd.to_numeric(r["winner"], errors="coerce")
    df = pd.DataFrame({
        "p1": p1.where(p1 != "", r["name1"]), "p2": p2.where(p2 != "", r["name2"]),
        "p1_won": np.where(w == 1, 1.0, np.where(w == 2, 0.0, np.nan)), "sets": [[] for _ in range(len(r))],
        "status": r["status"].map(lambda s: None if X.blank(s) else
                                  {"C": "completed", "F": "completed", "R": "retired", "W": "walkover",
                                   "D": "defaulted"}.get(str(s).strip().upper(), "unknown")),
        "seed1": r["seed1"].map(X.seed_num), "seed2": r["seed2"].map(X.seed_num), "entry1": r["seed1"],
        "entry2": r["seed2"], "round_raw": r["code"], "tournament_raw": r["tournament_id"].astype(str),
        "day_raw": r["match_date"], "status_text": r["status"], "atp_id1": r["id1"], "atp_id2": r["id2"]}, index=r.index)
    return _finish(df, keys).join(df[["status_text", "atp_id1", "atp_id2"]])


READERS = {"tennis_data": tennis_data, "api_tennis": api_tennis, "open_tennis_data": open_tennis_data,
           "flashscore": flashscore, "slam_feeds": slam_feeds, "wta_api": wta_api, "tdi": tdi, "sofascore": sofascore,
           "live_tennis_api": live_tennis_api, "infosys": infosys}
