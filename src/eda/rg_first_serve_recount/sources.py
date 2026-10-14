"""Loaders for the Roland-Garros first-serve recount: every per-player box of Roland Garros 2019-2026 and the Paris
Olympics 2024, one table per source, in Stage 0's counts.

Counts per player and match (Sackmann's definitions; serve points include double faults):
    ace, df, svpt, first_in, first_won, second_won, sv_gms, bp_saved, bp_faced

Sources (each read verbatim from its raw or staged files; nothing here writes outside the study folder):
    stage0   Stage 0 (data/studies/predictability_diagnostic/), with the Sackmann row each match came from
    api      RG's own statistics, rolandgarros.com's plain match API (src/ingest/point_sources/rolandgarros.py):
             "first serve" in/served, "win on 1st serve" won/in, "win on 2nd serve" won/(served - in), aces,
             double faults; break points from the opponent's "break points won" (won/opportunities)
    mb       RG's own point-by-point (Infosys MatchBeats), recounted point by point: each point has its server and
             "serve" 1 (played on the first serve) or 2 (after a first-serve fault); 2019-2024 from the raw files
             (decrypted here with the adapter's own routine), 2025 from the match-centre files, 2026 from the API
    ks       RG's Infosys key statistics (2025-2026), as the 8 Oct reviewers read them
    cv       the Hawk-Eye Court Vision copy (hawkilol), one row per serve, recounted: a faulted first serve is its
             own row ("Faulty Serve"), so points are the other rows and first serves in are those with serve 1
    ol       the Paris 2024 Olympic results files (src/ingest/point_sources/olympics.py): 1ST_SERVE in/served with
             points won, 2ND_SERVE points won, ACES, DBL_FAULT, BREAK_PTS (as receiver)
    mcp      the Match Charting Project's hand-charted totals (Overview, set "Total")
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
DUMP = ROOT / "data" / "dump" / "points"
RAW = ROOT / "data" / "raw" / "point_sources"
BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
SPLIT = ["first_in", "first_won", "second_won"]
RAW_COUNTS = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
              "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


# --------------------------------------------------------------------------------------------------- names
@lru_cache(maxsize=None)
def nkey(name) -> str:
    """Lower-case ASCII words: accents folded, punctuation (hyphens, apostrophes, dots) to spaces."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    s = unicodedata.normalize("NFKD", str(name)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def frac(value) -> tuple[float, float]:
    m = FRAC.match(str(value)) if value is not None else None
    return (float(m.group(1)), float(m.group(2))) if m else (np.nan, np.nan)


def num(value) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return np.nan


# --------------------------------------------------------------------------------------------------- Stage 0
@lru_cache(maxsize=None)
def stage0() -> pd.DataFrame:
    """One row per Stage 0 player row of Roland Garros 2019-2026 and the Paris Olympics 2024, with the match's
    keys (year, tour M/W, draw main/qual, round, event RG/OG) and the Sackmann row it came from."""
    m = pd.read_parquet(S0 / "stage0_matches.parquet")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet")
    rg = m["tournament_name"].eq("Roland Garros") & m["year"].between(2019, 2026)
    og = m["tournament_name"].eq("Paris Olympics") & m["year"].eq(2024)
    m = m[rg | og].copy()
    m["event"] = np.where(m["tournament_name"].eq("Paris Olympics"), "OG", "RG")
    keep = ["match_id", "event", "year", "tour", "qualifying", "round", "score", "status", "has_box", "source",
            "source_file", "source_row", "tournament_id", "sv_gms_incl_tb"]
    out = p.merge(m[keep], on="match_id", suffixes=("", "_m"))
    out["tour"] = out["tour"].map({"atp": "M", "wta": "W"})
    out["draw"] = np.where(out["qualifying"], "qual", "main")
    out["name_key"] = out["player_name"].map(nkey)
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------------------------------- RG's API
@lru_cache(maxsize=None)
def api() -> pd.DataFrame:
    """One row per RG match code and team (A/B) with RG's own counts; the opponent's break points give bp_faced and
    bp_saved. Columns ending _den are the denominators the site printed, for the consistency checks."""
    mt = pd.read_parquet(DUMP / "rolandgarros" / "matches.parquet")
    st = pd.read_parquet(DUMP / "rolandgarros" / "statistics.parquet")
    st = st[st["set_key"].eq("match")]
    mt = mt[mt["answer"].eq("ok")]
    rows = []
    stats = {k: g.set_index("stat") for k, g in st.groupby(["year", "match_id"])}
    for r in mt.itertuples():
        g = stats.get((r.year, r.match_id))
        names = {"A": json.loads(r.a_names), "B": json.loads(r.b_names)}
        ids = {"A": json.loads(r.a_ids), "B": json.loads(r.b_ids)}
        rec = {"year": int(r.year), "match_id": r.match_id, "tour": r.tour, "draw": r.draw, "round": r.round_from_code,
               "court": r.court_name, "status": r.status, "has_statistics": r.has_statistics == "TRUE"}
        for t, o in (("A", "B"), ("B", "A")):
            col = "team_a" if t == "A" else "team_b"
            ocol = "team_b" if t == "A" else "team_a"
            def v(stat, c=col):
                return g.loc[stat, c] if g is not None and stat in g.index else None
            fi, sv = frac(v("firstServeRateIn"))
            fw, fwd = frac(v("winRateOnFirstServe"))
            sw, swd = frac(v("winRateOnSecondServe"))
            obw, obo = frac(v("breakPoint", ocol))
            rw, rd = frac(v("returnPoints"))
            rows.append({**rec, "team": t, "name": names[t][0] if names[t] else None,
                         "rg_id": ids[t][0] if ids[t] else None, "opp_name": names[o][0] if names[o] else None,
                         "winner": (r.a_winner if t == "A" else r.b_winner) == "TRUE",
                         "end_cause": r.a_end_cause if t == "A" else r.b_end_cause,
                         "ace": num(v("aces")), "df": num(v("doubleFaults")), "svpt": sv, "first_in": fi,
                         "first_won": fw, "second_won": sw, "bp_faced": obo, "bp_saved": obo - obw,
                         "first_won_den": fwd, "second_won_den": swd, "ret_won": rw, "ret_den": rd,
                         "total_won": num(v("totalPointsWon"))})
    out = pd.DataFrame(rows)
    out["name_key"] = out["name"].map(nkey)
    out["opp_key"] = out["opp_name"].map(nkey)
    return out


# --------------------------------------------------------------------------------------------------- Infosys
def _mb_counts(mb: dict) -> list[dict]:
    """Per player (tm1, tm2) recount of one MatchBeats document.

    Service games, sv_gms_regular, follow Sackmann's convention: a game counts for its server when it is complete and
    not a tiebreak, so neither the tiebreak games nor the unfinished game of a retirement count (in 2022-2025 this
    equals Sackmann's rows in about 98% of RG rows, and in every retirement; the round-2 reviewers of 9 Oct 2026).
    A game is a tiebreak by MatchBeats' isTieBreak flag, or where both players serve in it without the flag; a game's
    server is the one who served most of its points. served_first marks who served the match's first point, and
    alternation_ok says that this is proven: the first point is set 1's first game, and every game the file holds, in
    order, is served by the player the alternation of serve names (a tiebreak takes its turn by its first point)."""
    pts = [(si, g.get("game", gi), p) for si, s in enumerate(mb.get("setData") or [], 1)
           for gi, g in enumerate(s.get("gameData") or [], 1) for p in g.get("pointData") or []]
    pdat = mb.get("playerData") or {}
    games: dict[tuple, dict] = {}
    for si, s in enumerate(mb.get("setData") or [], 1):
        for gi, g in enumerate(s.get("gameData") or [], 1):
            srv = Counter(str(p.get("server")) for p in g.get("pointData") or [])
            if not srv:
                continue
            info = games.setdefault((si, g.get("game", gi)), {"servers": Counter(), "tb": False, "done": True,
                                                              "flagged": "isTieBreak" in g,
                                                              "first_server": str(g["pointData"][0].get("server"))})
            info["servers"].update(srv)
            info["tb"] |= bool(g.get("isTieBreak"))
            info["done"] &= g.get("isGameComplete") is not False
    for info in games.values():
        info["tb"] |= not info["flagged"] and len(info["servers"]) > 1
        info["server"] = info["servers"].most_common(1)[0][0]
    first = str(pts[0][2].get("server")) if pts else None
    alternation_ok = bool(pts) and pts[0][0] == 1 and str(pts[0][1]) == "1" and first in ("1", "2")
    expected = first
    for info in games.values():
        turn = info["first_server"] if info["tb"] else info["server"]
        alternation_ok &= turn == expected
        expected = "2" if expected == "1" else "1"
    # stricter: each set's game numbers run 1, 2, 3, ... with no repeat or gap, and every game has one server (a
    # tiebreak apart). A garbled file can pass alternation_ok, which keys games by number (AO 2024 Griekspoor d.
    # Safiullin repeats a game: the round-2 reviewers confirmed its swap on Court Vision and a hand chart instead)
    numbers = [[str(g.get("game", gi)) for gi, g in enumerate(s.get("gameData") or [], 1) if g.get("pointData")]
               for s in mb.get("setData") or []]
    alternation_strict = alternation_ok and all(n == [str(i) for i in range(1, len(n) + 1)] for n in numbers) \
        and all(info["tb"] or len(info["servers"]) == 1 for info in games.values())
    out = []
    for k in ("1", "2"):
        mine = [(si, gi, p) for si, gi, p in pts if str(p.get("server")) == k]
        serve = [str(p.get("serve")) for _, _, p in mine]
        won = [str(p.get("scorer")) == k for _, _, p in mine]
        out.append({"slot": int(k), "name": pdat.get(f"tm{k}Ply1Name"), "first": pdat.get(f"tm{k}Ply1FirstName"),
                    "last": pdat.get(f"tm{k}Ply1LastName"), "infosys_id": pdat.get(f"tm{k}Ply1Id"),
                    "svpt": len(mine), "first_in": serve.count("1"),
                    "first_won": sum(w for s, w in zip(serve, won) if s == "1"),
                    "second_won": sum(w for s, w in zip(serve, won) if s == "2"),
                    "serve_other": sum(s not in ("1", "2") for s in serve),
                    "ace": sum(p.get("result") == "A" for _, _, p in mine),
                    "df": sum(p.get("result") == "DF" for _, _, p in mine),
                    "sv_gms": len({(si, gi) for si, gi, _ in mine}),
                    "sv_gms_regular": sum(1 for v in games.values() if v["done"] and not v["tb"] and v["server"] == k),
                    "tb_games": sum(1 for v in games.values() if v["tb"]),
                    "unfinished_games": sum(1 for v in games.values() if not v["done"]),
                    "served_first": first == k, "alternation_ok": alternation_ok,
                    "alternation_strict": alternation_strict,
                    "points_total": len(pts)})
    return out


@lru_cache(maxsize=None)
def mb(slam: str = "RG") -> pd.DataFrame:
    """RG's (or the AO's) MatchBeats recounted per player, from every raw file held (decrypted here)."""
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import infosys_slams as I
    rows = []
    base = RAW / "infosys_slams" / slam
    for path in sorted(base.glob("*/*/*.json.gz")):
        year, route, mid = path.parts[-3], path.parts[-2], path.name.split(".")[0]
        if route not in ("match-beats", "match-beats-api", "match-centre"):
            continue
        blocks = I.blocks_of(route, P.read_json(path))
        if "mbData" not in blocks:
            continue
        try:
            doc = I.decrypt(blocks["mbData"])
        except Exception as err:       # recorded, never silently dropped
            rows.append({"year": int(year), "match_id": mid, "route": route, "decrypt_error": str(err)})
            continue
        if not isinstance(doc, dict) or not doc.get("setData"):
            rows.append({"year": int(year), "match_id": mid, "route": route, "empty": True})
            continue
        for c in _mb_counts(doc):
            rows.append({"year": int(year), "match_id": mid, "route": route, "court": doc.get("courtName"),
                         "complete": doc.get("isMatchComplete"), "status": doc.get("matchStatus"),
                         "winner_slot": doc.get("matchWinner"), **c})
    out = pd.DataFrame(rows)
    # one route per match: the static MatchBeats file, else the match-centre file, else the API
    order = {"match-beats": 0, "match-centre": 1, "match-beats-api": 2}
    out["_o"] = out["route"].map(order)
    first = out.groupby(["year", "match_id"])["_o"].transform("min")
    out = out[out["_o"].eq(first)].drop(columns="_o").reset_index(drop=True)
    out["name_key"] = (out["first"].fillna("") + " " + out["last"].fillna("")).map(nkey)
    return out


@lru_cache(maxsize=None)
def keystats() -> pd.DataFrame:
    """RG's Infosys key statistics (2025-2026, staged), per player (player1/player2 = MatchBeats slots 1/2)."""
    ks = pd.read_parquet(DUMP / "infosys_slams" / "keystats.parquet")
    ks = ks[ks["slam"].eq("RG") & ks["set_key"].eq("set0")]
    rows = []
    for (yr, mid), g in ks.groupby(["year", "match_id"]):
        st = {r["name"]: (r["player1"], r["player2"]) for r in g.to_dict("records")}
        if "First Serve" not in st:
            continue
        for j, k in ((0, 1), (1, 2)):
            fi, sv = frac(st["First Serve"][j])
            bw, bo = frac(st.get("Break Points Won", (None, None))[1 - j])
            rows.append({"year": int(yr), "match_id": mid, "slot": k, "ace": num(st.get("Aces", (None, None))[j]),
                         "df": num(st.get("Double Faults", (None, None))[j]), "svpt": sv, "first_in": fi,
                         "first_won": frac(st.get("Win On 1st Serve", (None, None))[j])[0],
                         "second_won": frac(st.get("Win On 2nd Serve", (None, None))[j])[0],
                         "bp_faced": bo, "bp_saved": bo - bw})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------------- Court Vision
@lru_cache(maxsize=None)
def court_vision(slam: str = "RG") -> pd.DataFrame:
    """The Hawk-Eye Court Vision copy recounted per player (one row per serve; 'Faulty Serve' rows are faulted first
    serves, so a point is any other row). Names are the catalogue's 'X.SURNAME'."""
    cat = pd.read_parquet(DUMP / "slam_ball_tracking" / "matches.parquet")
    rows = []
    for f in sorted((DUMP / "slam_ball_tracking" / "points").glob(f"{slam}_*.parquet")):
        pt = pd.read_parquet(f)
        year = int(f.stem.split("_")[1])
        pt = pt.drop_duplicates(["match_id", "point_ID"])
        pts = pt[~pt["point_end_type"].isin(["Faulty Serve"])]
        by_code = {str(k).split("_")[-1]: g for k, g in pts.groupby("match_id")}
        c = cat[(cat["slam"].eq(slam)) & (cat["year"].astype(str).eq(str(year)))]
        for r in c.itertuples():
            mid = str(r.match_id)
            q = by_code.get(mid.split("_")[-1])
            if q is None or q.empty:
                continue
            for k, (pid, nm) in enumerate(((r.player1_id, r.player1), (r.player2_id, r.player2)), 1):
                s = q[q["server_id"].astype(str).eq(str(pid))]
                n = s["serve_num"].astype(str)
                w = s["point_winner_id"].astype(str).eq(str(pid))
                rows.append({"year": year, "match_id": mid.split("_")[-1], "slot": k, "name": nm,
                             "tour": "M" if "Men" in str(r.match_type) else "W", "svpt": len(s),
                             "first_in": int(n.eq("1").sum()), "first_won": int((n.eq("1") & w).sum()),
                             "second_won": int((n.eq("2") & w).sum()),
                             "ace": int(s["point_end_type"].eq("Ace").sum()),
                             "df": int(s["point_end_type"].eq("DoubleFault").sum()),
                             "na_rows": int(s["point_end_type"].isin(["NA"]).sum() + s["point_ID"].eq("NA").sum()),
                             "points_in_match": len(q)})
    out = pd.DataFrame(rows)
    out["last_key"] = out["name"].map(lambda x: nkey(str(x).split(".", 1)[-1]).replace(" ", ""))
    return out


# --------------------------------------------------------------------------------------------------- Olympics
@lru_cache(maxsize=None)
def olympics() -> pd.DataFrame:
    """The Paris 2024 official statistics per player (pos TOT), in Stage 0's counts."""
    st = pd.read_parquet(DUMP / "olympics" / "stats.parquet")
    un = pd.read_parquet(DUMP / "olympics" / "units.parquet")
    st = st[st["pos"].eq("TOT")]
    rows = []
    for (unit, code), g in st.groupby(["unit", "athlete_code"]):
        g = g.set_index("code")
        def ext(code_, key):
            if code_ not in g.index:
                return np.nan
            for e in json.loads(g.loc[code_, "extended"] or "[]"):
                if e.get("code") == key:
                    return num(e.get("value"))
            return np.nan
        def val(code_, field="value"):
            return num(g.loc[code_, field]) if code_ in g.index else np.nan
        rows.append({"unit": unit, "athlete_code": code, "name": g["athlete_name"].iloc[0], "side": g["side"].iloc[0],
                     "svpt": val("1ST_SERVE", "attempt"), "first_in": val("1ST_SERVE"),
                     "first_won": ext("1ST_SERVE", "POINTS_WON"), "second_won": ext("2ND_SERVE", "POINTS_WON"),
                     "second_in": val("2ND_SERVE"), "second_served": val("2ND_SERVE", "attempt"),
                     "ace": val("ACES"), "df": val("DBL_FAULT"), "bp_won": val("BREAK_PTS"),
                     "bp_opps": val("BREAK_PTS", "attempt"), "spw": val("PTS_WON_SERVE"),
                     "spw_den": val("PTS_WON_SERVE", "attempt")})
    out = pd.DataFrame(rows)
    opp = out[["unit", "athlete_code", "bp_won", "bp_opps"]].rename(
        columns={"athlete_code": "opp_code", "bp_won": "opp_bp_won", "bp_opps": "opp_bp_opps"})
    out = out.merge(opp, on="unit")
    out = out[out["athlete_code"].ne(out["opp_code"])]
    out["bp_faced"] = out["opp_bp_opps"]
    out["bp_saved"] = out["opp_bp_opps"] - out["opp_bp_won"]
    out = out.merge(un[["unit", "status", "description", "court", "home_name", "away_name", "capture", "lang"]],
                    on="unit", how="left")
    out["tour"] = np.where(out["unit"].str.startswith("TENM"), "M", "W")
    out["name_key"] = out["name"].map(nkey)
    return out.reset_index(drop=True)


@lru_cache(maxsize=None)
def olympics_pbp() -> pd.DataFrame:
    """The Paris 2024 play-by-play recounted per server: each point's result is PS1/PS2 (server won, on the first or
    second serve), PR1/PR2 (receiver won), A1/A2 (an ace on that serve) or DF. Tie-break rows (action T...) count
    like any point; their server is the SERVER field."""
    return count_olympic_points(pd.read_parquet(DUMP / "olympics" / "pbp.parquet"))


def count_olympic_points(p: pd.DataFrame) -> pd.DataFrame:
    """Per (unit, server): serve points, first serves in, points won on each serve, aces, double faults."""
    p = p[p["result"].notna()]
    r = p["result"].astype(str)
    p = p.assign(first=r.isin(["PS1", "PR1", "A1"]), first_won=r.isin(["PS1", "A1"]), second_won=r.isin(["PS2", "A2"]),
                 ace=r.isin(["A1", "A2"]), dbl=r.eq("DF"), known=r.isin(["PS1", "PR1", "A1", "PS2", "PR2", "A2", "DF"]))
    g = p.groupby(["unit", "server"])
    out = pd.DataFrame({"svpt": g.size(), "first_in": g["first"].sum(), "first_won": g["first_won"].sum(),
                        "second_won": g["second_won"].sum(), "ace": g["ace"].sum(), "df": g["dbl"].sum(),
                        "unknown_results": (~p["known"]).groupby([p["unit"], p["server"]]).sum()}).reset_index()
    return out.rename(columns={"server": "athlete_code"})


# --------------------------------------------------------------------------------------------------- MCP
@lru_cache(maxsize=None)
def mcp() -> pd.DataFrame:
    """The Match Charting Project's per-player totals with the match's date, tournament, round and players."""
    base = DUMP / "match_charting_project"
    frames = []
    for g in ("m", "w"):
        o = pd.read_parquet(base / "stats" / f"charting-{g}-stats-Overview.parquet")
        o = o[o["set"].astype(str).eq("Total")].copy()
        for c in ["serve_pts", "aces", "dfs", "first_in", "first_won", "second_in", "second_won", "bk_pts", "bp_saved"]:
            o[c] = pd.to_numeric(o[c], errors="coerce")
        mm = pd.read_parquet(base / "metadata" / f"charting-{g}-matches.parquet")
        mm = mm.rename(columns={"Player 1": "p1", "Player 2": "p2", "Date": "date", "Tournament": "tournament",
                                "Round": "round"})
        o = o.merge(mm[["match_id", "p1", "p2", "date", "tournament", "round"]], on="match_id", how="left")
        o["tour"] = "M" if g == "m" else "W"
        frames.append(o)
    o = pd.concat(frames, ignore_index=True)
    o["year"] = pd.to_numeric(o["date"].astype(str).str[:4], errors="coerce")
    o["name_key"] = o["player"].map(nkey)
    o["opp"] = np.where(o["player"].eq(o["p1"]), o["p2"], o["p1"])
    o["opp_key"] = o["opp"].map(nkey)
    return o.rename(columns={"serve_pts": "svpt", "aces": "ace", "dfs": "df", "bk_pts": "bp_faced"})


# --------------------------------------------------------------------------------------------------- raw rows
@lru_cache(maxsize=None)
def raw_rows() -> pd.DataFrame:
    """Every raw match row as stage0_build normalises it (before the decided corrections), keyed source_file/row."""
    from src.eda.predictability_diagnostic import stage0_build as B
    raw = B.normalise(B.load_raw())
    raw = raw.rename(columns={"_source_file": "source_file"})
    raw["source_row"] = pd.to_numeric(raw["_row"]).astype("Int64")
    return raw
