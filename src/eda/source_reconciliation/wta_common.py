"""Shared pieces of the WTA readers of the source-reconciliation study (box part, prefix wta_).

The readers put the WTA's own records of women's matches (the API's box score, the chair umpire's event log, the
point-by-point feed) on Stage 0's match and player ids, one row per (match, player), in the reader contract of
docs/studies/source_reconciliation/subagent_briefs.md:

    reader, family, kind, source_key, match_id, player_id, the nine counts + sv_won (float64, NaN where the source
    does not give the count), complete (bool), link_method, extra columns prefixed x_.

What this module does:
    * reads the WTA API's match lists (data/dump/points/wta/matches/<year>.parquet; the files repeat the column
      "year", so they are read through data_continuity.common.read_parquet_dedup or with named columns);
    * reads the frozen Stage 0 (source_reconciliation/_snapshot/, through common.stage0) and the frozen wta_api link
      file (match id <- "wta:<tournament_id>/<year>/<MatchID>");
    * orients the API's sides A/B on Stage 0's players by name (never by who won), and reports the share whose winner
      then disagrees;
    * writes each reader's parquet and JSON under data/studies/source_reconciliation/box/readers/.

Name grading is a copy of match_timing/srcc_common.name_grade (that module imports Stage 0 builders at import time,
so it is not imported here): 3 the same full name, words in any order; 2 one name's words inside the other's, or a
shared surname word with the same first initial; 1 a shared surname word only; 0 otherwise.
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.merge_feasibility import scan as S  # noqa: E402

WTA = C.DUMP / "points" / "wta"
RAW_WTA = C.RAW / "point_sources" / "wta"
BOX = C.OUT / "box"
READERS = BOX / "readers"
YEARS = list(range(2019, 2027))
FAMILY = "wta_official"
CONTRACT = ["reader", "family", "kind", "source_key", "match_id", "player_id"] + C.FIELDS + ["complete", "link_method"]

# Stage 0's map levels of the women's draws the WTA API lists, grouped as the brief asks (Slam, tour main draw,
# WTA 125, qualifying), with the Slam and qualifying groups kept apart by draw as well.
LEVEL_GROUP = {"GS": "slam_main", "GSQ": "slam_qual", "FIN": "tour_main", "T1000": "tour_main", "T500": "tour_main",
               "T250": "tour_main", "TQ": "tour_qual", "CH": "wta125_main", "CHQ": "wta125_qual"}
GROUP4 = {"slam_main": "Slam", "slam_qual": "Slam", "tour_main": "tour main draw", "wta125_main": "WTA 125",
          "tour_qual": "qualifying", "wta125_qual": "qualifying"}
LIST_COLS = ["tournament_id", "match_id", "tier", "draw", "walkover", "RoundID", "MatchState", "ResultString",
             "ScoreString", "Winner", "MatchTimeStamp", "PlayerIDA", "PlayerNameFirstA", "PlayerNameLastA",
             "PlayerIDB", "PlayerNameFirstB", "PlayerNameLastB"] + \
            [f"ScoreSet{k}{s}" for k in range(1, 6) for s in "AB"] + [f"ScoreTbSet{k}" for k in range(1, 5)] + \
            ["point_by_point_status", "events_status", "stats_status"]
WINNER_SIDE = {"2": "A", "4": "A", "6": "A", "3": "B", "5": "B", "7": "B"}
WINNER_HOW = {"2": "completed", "3": "completed", "4": "retired", "5": "retired", "6": "walkover", "7": "walkover"}


def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------------------------------------ the API's lists
def wta_key(tid, year, mid) -> str:
    return f"wta:{tid}/{year}/{mid}"


def listing(years=YEARS) -> pd.DataFrame:
    """Every listed match of the years (singles and doubles), with the source key the link file uses."""
    frames = []
    for y in years:
        path = WTA / "matches" / f"{y}.parquet"
        have = set(pq.read_schema(path).names)
        cols = [c for c in LIST_COLS if c in have]
        m = pq.read_table(path, columns=cols).to_pandas()
        m["year"] = y
        frames.append(m)
    m = pd.concat(frames, ignore_index=True).rename(columns={"match_id": "wta_mid"})
    m["source_key"] = "wta:" + m["tournament_id"].astype(str) + "/" + m["year"].astype(str) + "/" + m["wta_mid"]
    m["name_a"] = (m["PlayerNameFirstA"].fillna("") + " " + m["PlayerNameLastA"].fillna("")).str.strip()
    m["name_b"] = (m["PlayerNameFirstB"].fillna("") + " " + m["PlayerNameLastB"].fillna("")).str.strip()
    m["winner_side"] = m["Winner"].astype(str).map(WINNER_SIDE)
    m["how"] = m["Winner"].astype(str).map(WINNER_HOW)
    return m.drop_duplicates("source_key").reset_index(drop=True)


# ------------------------------------------------------------------------------------------------ Stage 0
def stage0_women() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The frozen Stage 0's women's matches from 2019 (the levels the API lists) and their player rows."""
    m, p = C.stage0(["match_id", "tour", "year", "level", "qualifying", "round", "tournament_id", "tournament_name",
                     "tournament_date", "status", "status_detail", "score", "has_box", "box_status", "sv_gms_incl_tb",
                     "player_a_id", "player_b_id", "a_won", "source", "map_level"],
                    ["match_id", "player_id", "opponent_id", "side", "won", "player_name"] + C.COUNTS)
    m = m[(m["tour"] == "wta") & (m["year"] >= 2019)].copy()
    m["level_group"] = m["map_level"].map(LEVEL_GROUP)
    p = p[p["match_id"].isin(set(m["match_id"]))].copy()
    return m.reset_index(drop=True), p.reset_index(drop=True)


# ------------------------------------------------------------------------------------------------ names
PARTICLES = {"de", "da", "van", "von", "der", "del", "la", "le", "di", "dos", "du", "das", "do", "den", "ter", "ten",
             "el", "al", "bin", "y", "e", "st"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
TRANSLIT = str.maketrans({"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O", "æ": "ae", "Æ": "Ae",
                          "œ": "oe", "Œ": "Oe", "ß": "ss", "ı": "i", "ð": "d", "þ": "th", "ħ": "h"})


def _fold(word: str) -> str:
    return word.replace("ue", "u").replace("oe", "o").replace("ae", "a")


@lru_cache(maxsize=None)
def name_info(name) -> tuple[str, tuple, frozenset, str]:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return "", (), frozenset(), ""
    raw = [_fold(t) for t in S.norm(str(name).translate(TRANSLIT)).split() if t not in SUFFIXES]
    if not raw:
        return "", (), frozenset(), ""
    words = tuple(t for t in raw if len(t) >= 2)
    initial = raw[0][0]
    if len(raw[0]) == 1:
        surname = frozenset(words)
    else:
        surname = frozenset(words[1:]) if len(words) > 1 else frozenset(words)
    return " ".join(sorted(words)), words, surname - PARTICLES, initial


@lru_cache(maxsize=None)
def name_grade(a, b) -> int:
    fa, wa, sa, ia = name_info(a)
    fb, wb, sb, ib = name_info(b)
    if not fa or not fb:
        return 0
    if fa == fb:
        return 3
    xa, xb = set(wa) - PARTICLES, set(wb) - PARTICLES
    if min(len(xa), len(xb)) >= 2 and (xa <= xb or xb <= xa):
        return 2
    shared = (sa & xb) | (sb & xa)
    shared = {w for w in shared if len(w) >= 3} or shared
    if not shared:
        return 0
    return 2 if ia and ia == ib else 1


# ------------------------------------------------------------------------------------------------ linking
def link(lst: pd.DataFrame, s0m: pd.DataFrame, s0p: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The API's listed matches placed on Stage 0 by the frozen wta_api link file, and oriented by names.

    Returns one row per linked match: source_key, match_id, wta_a_is_s0 ("A" when the API's player A is Stage 0's
    side A, "B" when it is side B), the name grades, the link file's method and flags, and the winner check (the API's
    listed winner mapped onto Stage 0 against a_won). Also the counts of what was dropped and why."""
    lk = C.links("wta_api", ["match_id", "source_key", "link_method", "score_agrees", "round_agrees"])
    n_links = len(lk)
    lk = lk.merge(lst, on="source_key", how="left", indicator=True)
    drops = {"link_without_listing_row": int((lk["_merge"] == "left_only").sum())}
    lk = lk[lk["_merge"] == "both"].drop(columns="_merge")
    names = s0p.pivot_table(index="match_id", columns="side", values="player_name", aggfunc="first")
    names.columns = [f"s0_name_{c.lower()}" for c in names.columns]
    lk = lk.merge(names, left_on="match_id", right_index=True, how="left")
    before = len(lk)
    lk = lk.merge(s0m[["match_id", "year", "map_level", "level_group", "status", "score", "a_won", "player_a_id",
                       "player_b_id"]].rename(columns={"year": "s0_year"}), on="match_id", how="inner")
    drops["link_to_match_outside_women_2019"] = before - len(lk)
    g_direct = [(name_grade(a, x), name_grade(b, y)) for a, b, x, y in
                zip(lk["name_a"], lk["name_b"], lk["s0_name_a"], lk["s0_name_b"])]
    g_swap = [(name_grade(a, y), name_grade(b, x)) for a, b, x, y in
              zip(lk["name_a"], lk["name_b"], lk["s0_name_a"], lk["s0_name_b"])]
    lk["wta_a_is_s0"] = [orient_by_names(d, s) for d, s in zip(g_direct, g_swap)]
    lk["x_name_grade"] = [f"{d[0]}{d[1]}" if o == "A" else f"{s[0]}{s[1]}" if o == "B" else f"{d[0]}{d[1]}|{s[0]}{s[1]}"
                          for d, s, o in zip(g_direct, g_swap, lk["wta_a_is_s0"])]
    lk["x_orient_one_name"] = [o is not None and min(d if o == "A" else s) == 0
                               for d, s, o in zip(g_direct, g_swap, lk["wta_a_is_s0"])]
    drops["names_do_not_orient"] = int(lk["wta_a_is_s0"].isna().sum())
    lk = lk[lk["wta_a_is_s0"].notna()].copy()
    # a check of the orientation by the API's player ids: an id -> Stage 0 id crosswalk learned from the links whose
    # two names both agree, then every link whose two ids are in it is checked against it
    both = lk[~lk["x_orient_one_name"]]
    pairs = pd.concat([pd.DataFrame({"wid": both["PlayerIDA"].astype(str),
                                     "sid": np.where(both["wta_a_is_s0"].eq("A"), both["player_a_id"], both["player_b_id"])}),
                       pd.DataFrame({"wid": both["PlayerIDB"].astype(str),
                                     "sid": np.where(both["wta_a_is_s0"].eq("A"), both["player_b_id"], both["player_a_id"])})])
    cw = pairs.groupby("wid")["sid"].agg(lambda x: x.mode().iloc[0] if len(x.mode()) == 1 else None).dropna()
    a_sid = np.where(lk["wta_a_is_s0"].eq("A"), lk["player_a_id"], lk["player_b_id"])
    b_sid = np.where(lk["wta_a_is_s0"].eq("A"), lk["player_b_id"], lk["player_a_id"])
    ca = lk["PlayerIDA"].astype(str).map(cw)
    cb = lk["PlayerIDB"].astype(str).map(cw)
    checked = ca.notna() & cb.notna()
    lk["x_ids_agree"] = pd.array([None if not c else bool(x == p and y == q)
                                  for c, x, y, p, q in zip(checked, ca, cb, a_sid, b_sid)], dtype="boolean")
    # the API's winner on Stage 0's sides, against a_won (a check, not used to orient)
    s0_winner = np.where(lk["a_won"].astype(bool), "A", "B")
    api_winner_s0 = np.where(lk["winner_side"].isna(), None,
                             np.where(lk["winner_side"].eq(lk["wta_a_is_s0"]), "A", "B"))
    lk["x_winner_agrees"] = pd.array([None if w is None else bool(w == s) for w, s in zip(api_winner_s0, s0_winner)],
                                     dtype="boolean")
    lk["link_method"] = "wta_api_link:" + lk["link_method"].astype(str) + ";names:" + lk["x_name_grade"]
    info = {"link_file_rows": n_links, "linked_and_oriented": int(len(lk)), "dropped": drops,
            "oriented_by_one_name_only (the other changed, e.g. a married name)": int(lk["x_orient_one_name"].sum()),
            "orientation_checked_by_ids": {"checked": int(lk["x_ids_agree"].notna().sum()),
                                           "agree": int((lk["x_ids_agree"] == True).sum()),  # noqa: E712
                                           "crosswalk_ids": int(len(cw))},
            "winner_disagrees_after_orienting": int((lk["x_winner_agrees"] == False).sum()),  # noqa: E712
            "winner_unknown_in_listing": int(lk["x_winner_agrees"].isna().sum())}
    return lk.reset_index(drop=True), info


def orient_by_names(d: tuple[int, int], s: tuple[int, int]) -> str | None:
    """'A' when the API's A is Stage 0's A (direct grades d), 'B' when swapped (grades s), None when unclear. Both
    names agreeing is the rule; one name agreeing (grade 2 or 3) with no name agreeing the other way is accepted too
    (a player who changed her name since: Kozlova/Baindl, Sanders/Hunter, Kuzmova/Hruncakova)."""
    if min(d) >= 1 and sum(d) > sum(s):
        return "A"
    if min(s) >= 1 and sum(s) > sum(d):
        return "B"
    if max(d) >= 2 and sum(s) == 0:
        return "A"
    if max(s) >= 2 and sum(d) == 0:
        return "B"
    return None


def players_of(lk: pd.DataFrame, s0p: pd.DataFrame) -> pd.DataFrame:
    """For each linked match, Stage 0's two players as the API's sides: (source_key, match_id, api_side, player_id,
    s0_side, won)."""
    sides = s0p[["match_id", "side", "player_id", "won"]]
    out = []
    for api_side in ("A", "B"):
        s0_side = np.where(lk["wta_a_is_s0"].eq("A"), api_side, "B" if api_side == "A" else "A")
        part = lk[["source_key", "match_id"]].assign(api_side=api_side, s0_side=s0_side)
        out.append(part)
    out = pd.concat(out, ignore_index=True)
    return out.merge(sides.rename(columns={"side": "s0_side"}), on=["match_id", "s0_side"], how="left")


# ------------------------------------------------------------------------------------------------ outputs
def finish_reader(frame: pd.DataFrame, reader: str, kind: str) -> pd.DataFrame:
    frame = frame.copy()
    frame.insert(0, "reader", reader)
    frame.insert(1, "family", FAMILY)
    frame.insert(2, "kind", kind)
    for c in C.FIELDS:
        frame[c] = pd.to_numeric(frame[c], errors="coerce").astype("float64")
    frame["complete"] = frame["complete"].fillna(False).astype(bool)
    extra = sorted(c for c in frame.columns if c not in CONTRACT)
    bad = [c for c in extra if not c.startswith("x_")]
    if bad:
        raise ValueError(f"columns outside the contract without the x_ prefix: {bad}")
    return frame[CONTRACT + extra].reset_index(drop=True)


def write_reader(frame: pd.DataFrame, reader: str, summary: dict) -> Path:
    READERS.mkdir(parents=True, exist_ok=True)
    path = READERS / f"{reader}.parquet"
    frame.to_parquet(path, index=False)
    summary = {"reader": reader, "file": str(path.relative_to(ROOT)).replace("\\", "/"), "rows": int(len(frame)),
               "matches": int(frame["match_id"].nunique()), **summary}
    C.write_json(READERS / f"{reader}.json", summary)
    log(f"wrote {path} ({len(frame):,} rows) and {reader}.json")
    return path


def equality_with_stage0(frame: pd.DataFrame, s0p: pd.DataFrame, by: list[str] | None = None,
                         only: pd.Series | None = None) -> pd.DataFrame:
    """The reader's sanity check: per count, rows where both values exist and the share equal to Stage 0's (Stage 0's
    sv_won = first_won + second_won)."""
    ref = s0p[["match_id", "player_id"] + C.COUNTS].copy()
    ref["sv_won"] = ref["first_won"] + ref["second_won"]
    f = frame if only is None else frame[only]
    j = f.merge(ref, on=["match_id", "player_id"], how="inner", suffixes=("", "_s0"))
    left = j[[c + "_s0" for c in C.FIELDS] + (by or [])].rename(columns={c + "_s0": c for c in C.FIELDS})
    right = j[C.FIELDS]
    return C.agreement(left, right, by=by)


def agreement_records(table: pd.DataFrame) -> list[dict]:
    keep = [c for c in table.columns if c in ("field", "n", "equal", "equal_share", "within1_share", "mean_diff")
            or c not in ("equal", "within1", "mean_abs_diff")]
    out = table[keep].copy()
    for c in ("equal_share", "within1_share", "mean_diff"):
        if c in out:
            out[c] = out[c].astype(float).round(4)
    return json.loads(out.to_json(orient="records"))
