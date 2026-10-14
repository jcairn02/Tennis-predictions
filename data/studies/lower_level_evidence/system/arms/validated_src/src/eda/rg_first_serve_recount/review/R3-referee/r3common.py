"""R3-referee: shared helpers (names, the player-row table, RG's statistics parsed from every raw API file)."""
from __future__ import annotations

import gzip
import json
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R3-referee"
STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"
RAW = ROOT / "data" / "raw" / "point_sources"
DUMP = ROOT / "data" / "dump" / "points"
SPLIT = ["first_in", "first_won", "second_won"]
COUNTS = ["svpt", "first_in", "first_won", "second_won", "ace", "df"]
RAWC = {"svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon", "second_won": "2ndWon", "ace": "ace", "df": "df",
        "bp_faced": "bpFaced", "bp_saved": "bpSaved", "sv_gms": "SvGms"}
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


def fold(name) -> list[str]:
    s = unicodedata.normalize("NFKD", str(name or "")).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s).split()


def name_ok(a, b) -> int:
    """2: the same words in any order (or the same letters); 1: a shared word of 3+ letters, or a 6+ letter word of
    one inside the other's letters (Sobolieva / Soboleva fail both and score 0); 0: nothing shared."""
    ta, tb = fold(a), fold(b)
    if not ta or not tb:
        return 0
    if sorted(ta) == sorted(tb) or "".join(sorted(ta)) == "".join(sorted(tb)) or "".join(ta) == "".join(tb):
        return 2
    if {t for t in ta if len(t) >= 3} & {t for t in tb if len(t) >= 3}:
        return 1
    ja, jb = "".join(ta), "".join(tb)
    if any(len(t) >= 6 and t in jb for t in ta) or any(len(t) >= 6 and t in ja for t in tb):
        return 1
    return 0


def frac(v):
    m = FRAC.match(str(v)) if v is not None else None
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("object").where(s.notna(), "").astype(str).str.strip().replace("", np.nan),
                         errors="coerce")


@lru_cache(maxsize=None)
def raw_subset() -> pd.DataFrame:
    r = pd.read_parquet(OUT / "raw_subset.parquet")
    r["_row"] = r["_row"].astype("int64")
    return r


def side_rows(raw: pd.DataFrame) -> pd.DataFrame:
    """One row per raw match row and side (w, l) with the side's counts as numbers."""
    out = []
    for s, who in (("w", "winner"), ("l", "loser")):
        d = pd.DataFrame({"source_file": raw["_source_file"].to_numpy(), "source_row": raw["_row"].to_numpy(),
                          "side": s, "tour": raw["tour"].to_numpy(), "tourney_name": raw["tourney_name"].to_numpy(),
                          "season": pd.to_numeric(raw["season"]).to_numpy(), "round": raw["round"].to_numpy(),
                          "qualifying": raw["qualifying"].to_numpy(), "player": raw[f"{who}_name"].to_numpy(),
                          "opponent": raw[f"{'loser' if s == 'w' else 'winner'}_name"].to_numpy(),
                          "score": raw["score"].to_numpy()})
        for k, c in RAWC.items():
            d[f"raw_{k}"] = num(raw[f"{s}_{c}"]).to_numpy()
        out.append(d)
    return pd.concat(out, ignore_index=True)


@lru_cache(maxsize=None)
def lead_rows() -> pd.DataFrame:
    """The lead's per-player classification (proposed_rows.csv for the scope, control_2019_2021.csv for the control
    editions), keyed by source_file, source_row and raw_side; the official values verified separately."""
    a = pd.read_csv(STUDY / "proposed_rows.csv", low_memory=False)
    b = pd.read_csv(STUDY / "control_2019_2021.csv", low_memory=False)
    d = pd.concat([a, b], ignore_index=True)
    d = d.rename(columns={"raw_side": "side"})
    d["source_row"] = d["source_row"].astype("int64")
    return d


@lru_cache(maxsize=None)
def rg_api_all() -> pd.DataFrame:
    """RG's own statistics for every match file held (2019-2025), parsed here from the raw API documents: one row per
    (year, code, team) with name, rg id, winner flag and the counts; 'consistent' = the record's own checks."""
    rows = []
    for f in sorted((RAW / "rolandgarros" / "matches").glob("*/*.json.gz")):
        year, code = int(f.parent.name), f.name.split(".")[0]
        try:
            doc = json.load(gzip.open(f))
        except Exception:
            continue
        m = doc.get("match") or {}
        st = (doc.get("matchStatisticsSection") or {}).get("matchStatistics") or {}
        rec = {}
        for t, o in (("A", "B"), ("B", "A")):
            team = m.get(f"team{t}") or {}
            p = team["players"][0] if team.get("players") else {}
            v = lambda k, side=t: (st.get(k) or {}).get(f"team{side}Value")
            fi, sv = frac(v("firstServeRateIn"))
            fw, fwd = frac(v("winRateOnFirstServe"))
            sw, swd = frac(v("winRateOnSecondServe"))
            obw, obo = frac(v("breakPoint", o))
            rw, rd = frac(v("returnPoints"))
            tw = v("totalPointsWon")
            rec[t] = {"year": year, "code": code, "team": t, "rg_id": p.get("id"),
                      "name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(),
                      "winner": bool(team.get("winner")), "svpt": sv, "first_in": fi, "first_won": fw,
                      "second_won": sw, "first_won_den": fwd, "second_won_den": swd,
                      "ace": pd.to_numeric(v("aces"), errors="coerce"), "df": pd.to_numeric(v("doubleFaults"), errors="coerce"),
                      "bp_faced": obo, "bp_saved": None if obo is None else obo - obw, "ret_won": rw, "ret_den": rd,
                      "total_won": pd.to_numeric(tw, errors="coerce")}
        for t, o in (("A", "B"), ("B", "A")):
            x, y = rec[t], rec[o]
            ok = x["svpt"] is not None and y["svpt"] is not None
            x["consistent"] = bool(ok and x["first_won_den"] == x["first_in"] and x["second_won_den"] == x["svpt"] - x["first_in"]
                                   and x["ret_den"] == y["svpt"]
                                   and x["total_won"] == x["first_won"] + x["second_won"] + x["ret_won"])
            rows.append(x)
    d = pd.DataFrame(rows)
    d["consistent_both"] = d.groupby(["year", "code"])["consistent"].transform("all")
    return d
