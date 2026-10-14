"""Reviewer A1-rederive: shared loaders (independent of src/eda/input_data_audit/common.py).

Read-only. Everything is recomputed from the staged raw files and the live Stage 0 tables.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
DUMP = ROOT / "data" / "dump"
SACK = DUMP / "matches" / "sackmann_archive"
TML = DUMP / "matches" / "tennis_my_life"
MCP = DUMP / "points" / "match_charting_project"
WTA = DUMP / "points" / "wta"
INFOSYS = DUMP / "points" / "infosys_slams"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
AUDIT = ROOT / "data" / "studies" / "input_data_audit"
OUT = AUDIT / "fixes" / "A1-rederive"
OUT.mkdir(parents=True, exist_ok=True)

BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
RAW = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
       "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}


def read_pq(path: Path) -> pd.DataFrame:
    """Read a parquet file with pyarrow, dropping duplicated column names (keep the first)."""
    t = pq.ParquetFile(path).read()
    names = t.column_names
    keep, seen = [], set()
    for i, n in enumerate(names):
        if n in seen:
            continue
        seen.add(n)
        keep.append(i)
    t = t.select(keep)
    return t.to_pandas()


def sack(tour: str, pattern: str) -> pd.DataFrame:
    """Sackmann staged rows for files matching ``pattern`` under sackmann_archive/<tour>/, with numeric box
    columns (w_*, l_* as floats) and the raw text kept in columns suffixed _raw."""
    frames = []
    for f in sorted((SACK / tour).glob(pattern)):
        d = pd.read_parquet(f)
        d["_file"] = f.name
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    for side in ("w", "l"):
        for b, src in RAW.items():
            col = f"{side}_{src}"
            df[f"{side}_{b}"] = pd.to_numeric(df[col].replace("", np.nan), errors="coerce")
    df["tdate"] = pd.to_datetime(df["tourney_date"], format="%Y%m%d", errors="coerce")
    return df


def has_box(df: pd.DataFrame) -> pd.Series:
    return df["w_svpt"].notna() & df["l_svpt"].notna() & (df["w_svpt"] > 0) & (df["l_svpt"] > 0)


@lru_cache(maxsize=None)
def stage0():
    m = pd.read_parquet(S0 / "stage0_matches.parquet")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet")
    return m, p


@lru_cache(maxsize=None)
def nkey(name) -> str:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    s = unicodedata.normalize("NFKD", str(name)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def last(name) -> str:
    k = nkey(name).split()
    return k[-1] if k else ""


# ------------------------------------------------------------------------------------------------
# Score -> games (winner's side as written)
SET_RE = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")


def parse_score(score: str):
    """Return list of (a, b, tb_flag) per set token from the winner's side, plus marker text."""
    sets, marks = [], []
    for tok in str(score).replace(",", " ").split():
        m = SET_RE.match(tok)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            tb = m.group(3) is not None or (max(a, b), min(a, b)) in ((7, 6),)
            sets.append((a, b, tb))
        elif re.match(r"^\[\d+-\d+\]$", tok):
            a, b = map(int, tok.strip("[]").split("-"))
            sets.append((a, b, "mtb"))
        else:
            marks.append(tok.lower())
    return sets, " ".join(marks)


def games_of(score: str):
    """(games_w, games_l, tiebreaks_w, tiebreaks_l, n_tiebreak_sets, retired)"""
    sets, mk = parse_score(score)
    gw = gl = tw = tl = ntb = 0
    for a, b, tb in sets:
        if tb == "mtb":
            continue
        gw += a
        gl += b
        if tb and max(a, b) == 7 and min(a, b) == 6:
            ntb += 1
            tw += a > b
            tl += b > a
    ret = bool(re.search(r"ret|def|w/o|abd|unf", mk))
    return gw, gl, tw, tl, ntb, ret


# ------------------------------------------------------------------------------------------------
# MCP

def mcp_overview(gender: str) -> pd.DataFrame:
    o = pd.read_parquet(MCP / "stats" / f"charting-{gender}-stats-Overview.parquet")
    o = o[o["set"].astype(str).eq("Total")].copy()
    for c in ["serve_pts", "aces", "dfs", "first_in", "first_won", "second_in", "second_won", "bk_pts", "bp_saved",
              "return_pts", "return_pts_won"]:
        o[c] = pd.to_numeric(o[c], errors="coerce")
    mm = pd.read_parquet(MCP / "metadata" / f"charting-{gender}-matches.parquet")
    mm = mm.rename(columns={"Player 1": "p1", "Player 2": "p2", "Date": "date", "Tournament": "tournament",
                            "Round": "round"})
    o = o.merge(mm[["match_id", "p1", "p2", "date", "tournament", "round"]], on="match_id", how="left")
    o["mdate"] = pd.to_datetime(o["date"].astype(str).str[:8], format="%Y%m%d", errors="coerce")
    o["pkey"] = o["player"].map(nkey)
    return o


# ------------------------------------------------------------------------------------------------
# WTA API

def wta_stats(year: int) -> pd.DataFrame:
    return read_pq(WTA / "stats" / f"{year}.parquet")


def wta_matches() -> pd.DataFrame:
    return read_pq(WTA / "matches.parquet")


def wta_api(year: int) -> pd.DataFrame:
    """One row per WTA API singles match of ``year`` with stats (setnum 0): names, winner side, score and the nine
    counts per player in Sackmann's definitions:
        ace = aces, df = double faults, svpt = total serve points played, first_in = points played on first serve,
        first_won = points won on first serve, second_won = total serve points won - first-serve points won,
        sv_gms = service games played, bp_faced = the opponent's break points played, bp_saved = bp_faced - the
        opponent's break points converted."""
    mt = read_pq(WTA / "matches" / f"{year}.parquet")
    mt = mt[mt["DrawMatchType"].astype(str).eq("S")].copy()
    st = wta_stats(year)
    st = st[st["setnum"].astype(str).eq("0")].copy()
    num = [c for c in st.columns if c.endswith("a") or c.endswith("b")]
    for c in num:
        if c in ("eventid", "matchid", "tournament_id"):
            continue
        st[c] = pd.to_numeric(st[c], errors="coerce")
    st["tournament_id"] = st["tournament_id"].astype(str)
    mt["tournament_id"] = mt["tournament_id"].astype(str)
    st["match_id"] = st["match_id"].astype(str)
    mt["match_id"] = mt["match_id"].astype(str)
    st = st.drop_duplicates(["tournament_id", "match_id"])
    d = mt.merge(st, on=["tournament_id", "match_id"], how="inner", suffixes=("", "_st"))
    out = pd.DataFrame({
        "year": year, "event": d["tournament_id"], "wmid": d["match_id"], "draw": d["DrawLevelType"].astype(str),
        "round_id": d["RoundID"].astype(str), "winner_code": d["Winner"].astype(str),
        "result": d["ResultString"].astype(str), "score": d["ScoreString"].astype(str),
        "nameA": (d["PlayerNameFirstA"].astype(str) + " " + d["PlayerNameLastA"].astype(str)),
        "nameB": (d["PlayerNameFirstB"].astype(str) + " " + d["PlayerNameLastB"].astype(str)),
        "lastA": d["PlayerNameLastA"].astype(str), "lastB": d["PlayerNameLastB"].astype(str)})
    for me, op in (("A", "b"), ("B", "a")):
        s = me.lower()
        out[f"{me}_ace"] = d[f"aces{s}"]
        out[f"{me}_df"] = d[f"dblflt{s}"]
        out[f"{me}_svpt"] = d[f"totservplayed{s}"]
        out[f"{me}_first_in"] = d[f"ptsplayed1stserv{s}"]
        out[f"{me}_first_won"] = d[f"ptswon1stserv{s}"]
        out[f"{me}_second_won"] = d[f"ptstotwonserv{s}"] - d[f"ptswon1stserv{s}"]
        out[f"{me}_sv_gms"] = d[f"servgamesplayed{s}"]
        out[f"{me}_bp_faced"] = d[f"breakptsplayed{op}"]
        out[f"{me}_bp_saved"] = d[f"breakptsplayed{op}"] - d[f"breakptsconv{op}"]
        out[f"{me}_totptswon"] = d[f"totptswon{s}"]
    out["kA"], out["kB"] = out["nameA"].map(nkey), out["nameB"].map(nkey)
    out["lkA"], out["lkB"] = out["lastA"].map(nkey), out["lastB"].map(nkey)
    return out.reset_index(drop=True)
