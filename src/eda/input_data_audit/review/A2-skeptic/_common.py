"""Shared loaders for reviewer A2-skeptic (read-only review of candidate fixes F1-F6, 8 Oct 2026).

Reads the live Stage 0 tables (7 Oct build), Sackmann's staged raw rows, the Match Charting Project and the WTA API.
Writes nothing outside data/studies/input_data_audit/fixes/A2-skeptic/.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "A2-skeptic"
OUT.mkdir(parents=True, exist_ok=True)
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
SACK = ROOT / "data" / "dump" / "matches" / "sackmann_archive"
MCP = ROOT / "data" / "raw" / "public_dump" / "match_charting_project"
WTA = ROOT / "data" / "dump" / "points" / "wta"
INFOSYS = ROOT / "data" / "dump" / "points" / "infosys_slams"
AUDIT = ROOT / "data" / "studies" / "input_data_audit"

BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
RAW = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon", "second_won": "2ndWon",
       "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}


def name_key(name) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return " ".join(sorted(re.findall(r"[a-z]+", s)))


def stage0() -> pd.DataFrame:
    """Player rows of the live Stage 0 with the match columns and the opponent's counts (o_<count>)."""
    p = pd.read_parquet(S0 / "stage0_match_players.parquet")
    m = pd.read_parquet(S0 / "stage0_matches.parquet")
    d = p.merge(m, on="match_id", how="left", validate="many_to_one", suffixes=("", "_m"))
    opp = d[["match_id", "side", "player_name", "player_id", "entry"] + BOX].copy()
    opp["side"] = opp["side"].map({"A": "B", "B": "A"})
    opp = opp.rename(columns={c: f"o_{c}" for c in BOX + ["player_name", "player_id", "entry"]})
    return d.merge(opp, on=["match_id", "side"], how="left", validate="one_to_one")


def sackmann(tour: str, pattern: str = "*") -> pd.DataFrame:
    fs = sorted((SACK / tour).glob(f"{tour}_matches_{pattern}.parquet"))
    out = []
    for f in fs:
        if "doubles" in f.name:
            continue
        r = pd.read_parquet(f)
        r["staged_file"] = f.name
        out.append(r)
    r = pd.concat(out, ignore_index=True)
    for side in ("w", "l"):
        for b, src in RAW.items():
            r[f"{side}_{src}"] = pd.to_numeric(r[f"{side}_{src}"], errors="coerce")
    return r


def wta_stats(year: int) -> pd.DataFrame:
    return _dedup(WTA / "stats" / f"{year}.parquet")


def _dedup(path: Path) -> pd.DataFrame:
    t = pq.ParquetFile(path).read()
    keep, seen = [], set()
    for i, n in enumerate(t.column_names):
        if n in seen:
            continue
        seen.add(n)
        keep.append(i)
    return t.select(keep).to_pandas()


WTA_WINNER = {"2": "a", "4": "a", "6": "a", "3": "b", "5": "b", "7": "b"}   # completed, retired, walkover


def wta_api(years=range(2019, 2027)) -> pd.DataFrame:
    """One row per WTA API singles match: players A/B (name keys), winner side, score, and each side's nine counts
    mapped as in src/eda/data_continuity/sources.py (break points are recorded on the returner's side)."""
    ms, ss = [], []
    for y in years:
        p = WTA / "matches" / f"{y}.parquet"
        if p.exists():
            ms.append(_dedup(p))
        p = WTA / "stats" / f"{y}.parquet"
        if p.exists():
            ss.append(_dedup(p))
    m = pd.concat(ms, ignore_index=True)
    s = pd.concat(ss, ignore_index=True)
    m = m[m["DrawMatchType"].astype(str).eq("S")].copy()
    m["key"] = m["tournament_id"].astype(str) + "/" + m["year"].astype(str) + "/" + m["match_id"].astype(str)
    s["key"] = s["tournament_id"].astype(str) + "/" + s["year"].astype(str) + "/" + s["match_id"].astype(str)
    s = s[s["setnum"].astype(str).eq("0")].drop_duplicates("key")
    m = m.drop_duplicates("key")
    m["winner_side"] = m["Winner"].astype(str).map(WTA_WINNER)
    m["name_a"] = m["PlayerNameFirstA"].fillna("") + " " + m["PlayerNameLastA"].fillna("")
    m["name_b"] = m["PlayerNameFirstB"].fillna("") + " " + m["PlayerNameLastB"].fillna("")
    m["ka"], m["kb"] = m["name_a"].map(name_key), m["name_b"].map(name_key)
    num = lambda c: pd.to_numeric(s[c], errors="coerce")   # noqa: E731
    box = pd.DataFrame({"key": s["key"]})
    for side, other in (("a", "b"), ("b", "a")):
        box[f"{side}_ace"] = num(f"aces{side}")
        box[f"{side}_df"] = num(f"dblflt{side}")
        box[f"{side}_svpt"] = num(f"totservplayed{side}")
        box[f"{side}_first_in"] = num(f"ptsplayed1stserv{side}")
        box[f"{side}_first_won"] = num(f"ptswon1stserv{side}")
        box[f"{side}_second_won"] = num(f"ptstotwonserv{side}") - num(f"ptswon1stserv{side}")
        box[f"{side}_sv_gms"] = num(f"servgamesplayed{side}")
        box[f"{side}_bp_faced"] = num(f"breakptsplayed{other}")
        box[f"{side}_bp_saved"] = num(f"breakptsplayed{other}") - num(f"breakptsconv{other}")
    ga = sum(pd.to_numeric(m[f"ScoreSet{i}A"], errors="coerce").fillna(0) for i in range(1, 6))
    gb = sum(pd.to_numeric(m[f"ScoreSet{i}B"], errors="coerce").fillna(0) for i in range(1, 6))
    m["games_a"], m["games_b"] = ga, gb
    tbs = [pd.to_numeric(m[f"ScoreTbSet{i}"], errors="coerce") for i in range(1, 5) if f"ScoreTbSet{i}" in m]
    m["any_tb"] = pd.concat(tbs, axis=1).notna().any(axis=1) if tbs else False
    for i in range(1, 6):   # a 7-6 set is a tiebreak even without points
        a = pd.to_numeric(m[f"ScoreSet{i}A"], errors="coerce")
        b = pd.to_numeric(m[f"ScoreSet{i}B"], errors="coerce")
        m["any_tb"] |= ((a == 7) & (b == 6)) | ((a == 6) & (b == 7))
    keep = ["key", "tournament_id", "year", "match_id", "DrawLevelType", "RoundID", "MatchState", "ResultString",
            "ScoreString", "Winner", "winner_side", "name_a", "name_b", "ka", "kb", "EntryTypeA", "EntryTypeB",
            "PlayerIDA", "PlayerIDB", "stats_status", "games_a", "games_b", "any_tb"]
    return m[keep].merge(box, on="key", how="left")


def mcp(g: str) -> pd.DataFrame:
    """MCP whole-match overview per player, with the match's date, players and tournament."""
    mm = pd.read_csv(MCP / f"charting-{g}-matches.csv", dtype=str, on_bad_lines="skip")
    ov = pd.read_csv(MCP / f"charting-{g}-stats-Overview.csv", dtype=str, on_bad_lines="skip")
    ov = ov[ov["set"].eq("Total")].copy()
    for c in ["serve_pts", "aces", "dfs", "first_in", "first_won", "second_in", "second_won", "bk_pts", "bp_saved",
              "return_pts", "return_pts_won"]:
        ov[c] = pd.to_numeric(ov[c], errors="coerce")
    mm["date"] = pd.to_datetime(mm["Date"], format="%Y%m%d", errors="coerce")
    m = mm.merge(ov, on="match_id")
    m["pk"] = m["player"].map(name_key)
    other = np.where(m["player"].eq(m["Player 1"]), m["Player 2"], m["Player 1"])
    m["ok"] = pd.Series(other, index=m.index).map(name_key)
    return m
