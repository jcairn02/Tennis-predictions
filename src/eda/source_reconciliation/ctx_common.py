"""Shared pieces of parts C, D and E of the source-reconciliation study (results and scores, context fields, birth dates).

Everything reads the study's frozen Stage 0 (common.SNAP) and the raw or staged source files read-only; outputs go to
data/studies/source_reconciliation/context/ only. Per-match rows are written as parquet (git-ignored); only aggregates,
ids and short examples go to CSV / JSON / MD (the repository is public).

Conventions used by every ctx_ module:
    * a source row is oriented to Stage 0 by names (srcc_common.name_grade, the timeline linker's grading), by player
      ids where the source has a crosswalk, and only where names tie by the set scores (counted);
    * set scores are kept as lists of (games_1, games_2, tiebreak_points_1, tiebreak_points_2), None where unknown;
      Stage 0 gives only the tiebreak loser's points (Sackmann's "7-6(5)");
    * a status is one of completed, retired, walkover, defaulted, abandoned, awarded, unknown;
    * an independence family groups dependent copies (the brief: count dependent copies once): Open Tennis Data is
      built from tennis-data and Sackmann; Tennis My Life's rows before its 2026 splice continue Sackmann's; the
      WTA API and the WTA website are the WTA's own records; Infosys and TDI the ATP's.
"""
from __future__ import annotations

import json
import re
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402

OUT = C.OUT / "context"
WORK = OUT / "work"            # per-row parquet tables (git-ignored by *.parquet)
T0 = time.time()

# Independence families of the result / context sources. "stage0_own" marks a source that IS Stage 0's source for
# the row (Sackmann's file, or TML for Stage 0's TML rows); "derived" a copy built from Stage 0's own sources.
FAMILY = {
    "tennis_data": "tennis_data",
    "open_tennis_data": "derived_otd",        # built from tennis-data.co.uk and Sackmann (its 'source' column)
    "api_tennis": "api_tennis",
    "flashscore": "flashscore",
    "sofascore": "sofascore",
    "slam_feeds": "slam_official",
    "wta_api": "wta_official",
    "wta_site": "wta_official",
    "infosys": "atp_official",
    "tdi": "atp_official",
    "live_tennis_api": "live_tennis_api",
    "tennislive": "tennislive",
    "itf_live": "itf_official",
    "tml": "sackmann_tml",                    # the brief: TML's pre-2026 rows continue Sackmann's (dependent)
    "pbp_copy": "sackmann_tml",               # Sackmann's own point-by-point copy
    "match_charting": "mcp",
}
OFFICIAL = {"slam_official", "wta_official", "atp_official", "itf_official"}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def write_json(path: Path, value) -> None:
    C.write_json(path, value)


def blank(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and v.strip() == "") or \
        v is pd.NA or (isinstance(v, pd.Timestamp) and pd.isna(v))


def int_or_none(v):
    try:
        if blank(v):
            return None
        s = str(v).strip()
        if s.lower() in ("nan", "none", "null", "-"):
            return None
        m = re.match(r"^-?\d+", s)
        return int(m.group(0)) if m else None
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------------------------------------
# Stage 0 (the frozen snapshot)

S0_COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "match_num", "surface", "indoor",
           "best_of", "draw_size", "tournament_id", "tournament_name", "tournament_date", "status", "status_detail",
           "score", "score_flag", "format", "player_a_id", "player_b_id", "a_won", "source", "tml_link", "source_file",
           "source_row", "map_level"]
_S0: dict = {}


def stage0_matches() -> pd.DataFrame:
    """The snapshot's matches with both names and seeds (A, B), the tournament date as datetime64[ns]."""
    if "m" in _S0:
        return _S0["m"]
    m, p = C.stage0(S0_COLS, ["match_id", "side", "player_id", "player_name", "seed", "entry", "age", "rank"])
    for side in ("A", "B"):
        q = p[p["side"] == side].drop_duplicates("match_id").set_index("match_id")
        s = side.lower()
        m[f"name_{s}"] = m["match_id"].map(q["player_name"]).astype(object)
        m[f"seed_{s}"] = m["match_id"].map(q["seed"])
        m[f"entry_{s}"] = m["match_id"].map(q["entry"]).astype(object)
    m["tdate"] = pd.to_datetime(m["tournament_date"]).astype("datetime64[ns]")
    for c in ("match_id", "tour", "level", "round", "tournament_id", "tournament_name", "status", "status_detail",
              "score", "player_a_id", "player_b_id", "source", "surface"):
        m[c] = m[c].astype(object)
    _S0["m"] = m
    return m


def model_frame_ids() -> pd.Index:
    """The current best model's frame (the template instance of 14 Oct 2026, built on the tables the snapshot holds):
    main-tour main-draw matches at tennis-data's levels from 2013."""
    f = pd.read_parquet(C.STUDIES / "current_best_model" / "template_2026-10-14" / "model_frame.parquet",
                        columns=["match_id"])
    return pd.Index(f["match_id"].astype(str))


# ------------------------------------------------------------------------------------------------
# Set scores

@lru_cache(maxsize=None)
def s0_sets_w(score) -> tuple:
    """Stage 0's score as winner-first sets: ((w, l, tb_loser or None, bracket), ...) and the marker text."""
    from src.eda.predictability_diagnostic import stage0_build as B
    if not isinstance(score, str) or not score.strip():
        return (), ""
    sets, marker = B.tokens_of(score)
    return tuple((a, b, (t if t >= 0 else None), br) for a, b, t, br in sets), marker


def s0_sets_a(score, a_won, reversed_: bool = False, slam: bool = False) -> tuple:
    """Stage 0's sets as (A games, B games, A tb points, B tb points, bracket); tiebreak points known for the loser
    only, the winner's derived (max(7, loser + 2)) only where the set is a 7-6 tiebreak.

    reversed_: Stage 0's score_flag 'read_reversed' (the score text is written loser first: Stage 0 keeps the text
    and flags it). slam: a Grand Slam match, whose long final set is a real advantage set; elsewhere a last set of
    10 or more games is a match tiebreak written without its brackets (no set ends 10-6), marked as one."""
    sets, _ = s0_sets_w(score)
    if reversed_:
        sets = tuple((l, w, t, br) for w, l, t, br in sets)
    sets = tuple(s for s in sets)
    if sets and not slam:
        w, l, t, br = sets[-1]
        if not br and max(w, l) >= 10:
            sets = sets[:-1] + ((w, l, t, True),)
    out = []
    for w, l, t, br in sets:
        tw = tl = None
        if t is not None and not br and {w, l} == {7, 6}:
            tl, tw = t, max(7, t + 2)
        if a_won:
            out.append((w, l, tw if w > l else tl, tl if w > l else tw, br))
        else:
            out.append((l, w, tl if w > l else tw, tw if w > l else tl, br))
    return tuple(out)


def trim(sets) -> list:
    out = list(sets or ())
    while out and out[-1][0] == 0 and out[-1][1] == 0:
        out.pop()
    return out


def set_equal(src, ref) -> bool:
    """One set's games: equal; against a Stage 0 match tiebreak ([10-8]), the same side won it, written as 1-0, as
    its points or as a 7-6-like set (srcc_common._set_equal's rule)."""
    if ref[4]:
        a, b = src[0], src[1]
        return a != b and (a > b) == (ref[0] > ref[1]) and ((max(a, b) == 1 and min(a, b) == 0) or max(a, b) >= 7)
    return src[0] == ref[0] and src[1] == ref[1]


def tb_loser_points(s) -> int | None:
    """The tiebreak loser's points of a 7-6 set (g1, g2, t1, t2, ...), None if not given."""
    g1, g2, t1, t2 = s[0], s[1], s[2], s[3]
    if {g1, g2} != {7, 6}:
        return None
    return t2 if g1 > g2 else t1


def compare_sets(src: list, ref: tuple) -> tuple[str, int]:
    """Class of a source's sets (oriented to Stage 0's A) against Stage 0's, and the number of sets compared.

    identical         every set equal (games); tiebreak points equal where both give them
    tb_points_differ  games equal, a tiebreak's loser points differ
    src_shorter       the source's sets are the start of Stage 0's (one source stops early)
    src_longer        Stage 0's sets are the start of the source's
    mirrored          the same games with A and B exchanged in every set (the winner read the other way)
    games_differ      same number of sets, at least one set's games differ
    count_differs     different number of sets, neither the start of the other
    no_src_sets / no_s0_sets / no_sets
    """
    a, b = trim(src), trim(ref)
    if not a and not b:
        return "no_sets", 0
    if not a:
        return "no_src_sets", 0
    if not b:
        return "no_s0_sets", 0
    n = min(len(a), len(b))
    eq = [set_equal(x, y) for x, y in zip(a, b)]
    if len(a) == len(b) and all(eq):
        for x, y in zip(a, b):
            if y[4]:
                continue
            tx, ty = tb_loser_points(x), tb_loser_points(y)
            if tx is not None and ty is not None and tx != ty:
                return "tb_points_differ", n
        return "identical", n
    if all(eq[:n]):
        return ("src_shorter" if len(a) < len(b) else "src_longer"), n
    mir = [set_equal((x[1], x[0], x[3], x[2]), y) for x, y in zip(a, b)]
    if len(a) == len(b) and all(mir):
        return "mirrored", n
    return ("games_differ" if len(a) == len(b) else "count_differs"), n


def set_relation(x, y) -> str:
    """One source set x (g1, g2, t1, t2) against Stage 0's y (g1, g2, t1, t2, bracket), both A first:
    eq        the same games (tiebreak points equal or not both given)
    tb        the same games, the tiebreak loser's points differ
    mt        Stage 0's match tiebreak ([10-8]) and a source set won by the same side, written as 1-0, as a 7-6 set
              or as other points (a definitional difference, or the points differ)
    capped    Stage 0's advantage set (8 games or more: 8-6, 10-8, 70-68) that the source writes as 7-6 with the same
              set winner (the source stores at most 7 games in a set: definitional)
    diff      otherwise"""
    if y[4]:
        a, b = x[0], x[1]
        if a == b or (a > b) != (y[0] > y[1]):
            return "diff"
        if (a, b) == (y[0], y[1]):
            return "eq"
        if (max(a, b) == 1 and min(a, b) == 0) or {a, b} == {7, 6} or max(a, b) >= 7:
            return "mt"
        return "diff"
    if x[0] == y[0] and x[1] == y[1]:
        tx, ty = tb_loser_points(x), tb_loser_points(y)
        return "tb" if (tx is not None and ty is not None and tx != ty) else "eq"
    if max(y[0], y[1]) >= 8 and {x[0], x[1]} == {7, 6} and (x[0] > x[1]) == (y[0] > y[1]):
        return "capped"
    # the source's match tiebreak (its points, or 1-0) where Stage 0 writes it as a 7-6 or 1-0 set
    src_mt = max(x[0], x[1]) >= 10 or (max(x[0], x[1]) == 1 and min(x[0], x[1]) == 0)
    s0_mt_like = {y[0], y[1]} == {7, 6} or (max(y[0], y[1]) == 1 and min(y[0], y[1]) == 0)
    if src_mt and s0_mt_like and x[0] != x[1] and (x[0] > x[1]) == (y[0] > y[1]):
        return "mt"
    return "diff"


SAME = {"eq", "tb", "mt", "capped"}


def compare_sets2(src: list, ref: tuple) -> tuple[str, int]:
    """compare_sets with the definitional classes kept apart:
    identical, tb_points_differ, mt_written_otherwise (a match tiebreak written as 1-0, 7-6 or other points),
    long_set_capped (an advantage set written as 7-6), src_shorter, src_longer (one is the start of the other, sets
    related as above), mirrored, games_differ, count_differs, no_src_sets, no_s0_sets, no_sets."""
    a, b = trim(src), trim(ref)
    if not a and not b:
        return "no_sets", 0
    if not a:
        return "no_src_sets", 0
    if not b:
        return "no_s0_sets", 0
    n = min(len(a), len(b))
    rel = [set_relation(x, y) for x, y in zip(a, b)]
    if all(r in SAME for r in rel):
        if len(a) != len(b):
            return ("src_shorter" if len(a) < len(b) else "src_longer"), n
        if all(r == "eq" for r in rel):
            return "identical", n
        if "capped" in rel:
            return "long_set_capped", n
        if "mt" in rel:
            return "mt_written_otherwise", n
        return "tb_points_differ", n
    mir = [set_relation((x[1], x[0], x[3], x[2]), y) for x, y in zip(a, b)]
    if len(a) == len(b) and all(r in SAME for r in mir):
        return "mirrored", n
    return ("games_differ" if len(a) == len(b) else "count_differs"), n


def sets_text(sets) -> str:
    """'6-4 7-6(5)' from (g1, g2, t1, t2[, bracket]) sets, first player's games first; the tiebreak loser's points."""
    out = []
    for s in sets or ():
        g1, g2 = s[0], s[1]
        br = len(s) > 4 and s[4]
        if br:
            out.append(f"[{g1}-{g2}]")
            continue
        t = tb_loser_points(s) if len(s) >= 4 else None
        out.append(f"{g1}-{g2}" + (f"({t})" if t is not None else ""))
    return " ".join(out)


# ------------------------------------------------------------------------------------------------
# Status

S0_STATUS = {"completed": "completed", "retired": "retired", "retired_unmarked": "retired",
             "walkover_after_play": "retired", "walkover": "walkover", "bye": "walkover", "defaulted": "defaulted",
             "abandoned": "abandoned", "unknown": "unknown"}


def s0_status(detail) -> str:
    return S0_STATUS.get(str(detail), "unknown")


def norm_status(text) -> str | None:
    """A source's status text as completed / retired / walkover / defaulted / abandoned / awarded / unknown."""
    if blank(text):
        return None
    s = str(text).strip().lower()
    if s in ("completed", "complete", "cmp", "finished", "ended", "c", "d", "f", "played", "w", "aet", "final",
             "post"):
        return "completed"
    if "ret" in s or s in ("e", "rtd", "rrtired"):
        return "retired"
    if "walk" in s or s in ("w/o", "wo", "walkoer"):
        return "walkover"
    if "default" in s or "disqual" in s or s in ("def", "dq"):
        return "defaulted"
    if "award" in s:
        return "awarded"
    if "abandon" in s or "abd" in s or "interrupt" in s or "suspend" in s or "cancel" in s or "postpon" in s:
        return "abandoned"
    return "unknown"


# ------------------------------------------------------------------------------------------------
# Orientation

def _grade(a, b) -> int:
    from src.eda.match_timing import srcc_common as K
    return K.name_grade(a, b)


def orient_one(p1, p2, name_a, name_b, id1=None, id2=None, pid_a=None, pid_b=None) -> tuple[str | None, str]:
    """Which Stage 0 side the source's first player is: ('A' | 'B' | None, how). Stage 0 ids first where the source
    gives them, then names (the sum of both players' grades; a tie is unresolved here)."""
    if not blank(id1) and not blank(pid_a):
        if id1 == pid_a or (not blank(id2) and id2 == pid_b):
            return "A", "ids"
        if id1 == pid_b or (not blank(id2) and id2 == pid_a):
            return "B", "ids"
    same = _grade(p1, name_a) + _grade(p2, name_b)
    swap = _grade(p1, name_b) + _grade(p2, name_a)
    if same > swap:
        return "A", "names"
    if swap > same:
        return "B", "names"
    return None, "names_tie"


def orient_frame(f: pd.DataFrame) -> pd.DataFrame:
    """Adds p1_side ('A' / 'B' / None) and orient_how to a frame with p1, p2, name_a, name_b (and optionally s0 ids
    in id1 / id2, Stage 0's player_a_id / player_b_id). A names tie is resolved by the set scores where exactly one
    orientation makes them identical ('sets_tiebreak')."""
    id1 = f["s0_id1"] if "s0_id1" in f else pd.Series(None, index=f.index)
    id2 = f["s0_id2"] if "s0_id2" in f else pd.Series(None, index=f.index)
    res = [orient_one(a, b, x, y, i, j, pa, pb) for a, b, x, y, i, j, pa, pb in
           zip(f["p1"], f["p2"], f["name_a"], f["name_b"], id1, id2, f["player_a_id"], f["player_b_id"])]
    f = f.copy()
    f["p1_side"] = [r[0] for r in res]
    f["orient_how"] = [r[1] for r in res]
    tie = f["p1_side"].isna()
    if tie.any() and "sets" in f:
        for i in f.index[tie]:
            src = f.at[i, "sets"]
            ref = s0_sets_a(f.at[i, "score"], bool(f.at[i, "a_won"]))
            if not src or not ref:
                continue
            ok_a = compare_sets(list(src), ref)[0] in ("identical", "tb_points_differ")
            flip = [(s[1], s[0], s[3], s[2]) for s in src]
            ok_b = compare_sets(flip, ref)[0] in ("identical", "tb_points_differ")
            if ok_a != ok_b:
                f.at[i, "p1_side"] = "A" if ok_a else "B"
                f.at[i, "orient_how"] = "sets_tiebreak"
    return f


def to_a(f: pd.DataFrame) -> pd.DataFrame:
    """Source values oriented to Stage 0's A: a_won_src, sets_a (list of (gA, gB, tA, tB)), seed_a_src, seed_b_src
    (where present: seed1/seed2), entry_a_src / entry_b_src."""
    f = f.copy()
    a1 = f["p1_side"].eq("A")
    b1 = f["p1_side"].eq("B")
    w = f["p1_won"].astype("float64")
    f["a_won_src"] = np.where(a1, w, np.where(b1, 1 - w, np.nan))
    sets = []
    for s, x, y in zip(f["sets"], a1, b1):
        if x:
            sets.append(list(s) if s else [])
        elif y:
            sets.append([(t[1], t[0], t[3], t[2]) for t in s] if s else [])
        else:
            sets.append(None)
    f["sets_a"] = sets
    for c in ("seed", "entry"):
        if f"{c}1" in f:
            f[f"{c}_a_src"] = np.where(a1, f[f"{c}1"], np.where(b1, f[f"{c}2"], None))
            f[f"{c}_b_src"] = np.where(a1, f[f"{c}2"], np.where(b1, f[f"{c}1"], None))
    return f


def sets_tuple(pairs) -> list:
    """(g1, g2[, t1, t2]) per set, padded to four values."""
    out = []
    for p in pairs or ():
        p = tuple(p) + (None,) * (4 - len(p))
        out.append((int(p[0]), int(p[1]), p[2], p[3]))
    return out


def seed_num(v) -> float:
    """A seed as a number: '5' -> 5; 'Q', 'WC', 'LL', '', '-' and the like -> NaN (entry types are not seeds)."""
    if blank(v):
        return np.nan
    m = re.match(r"^\s*\[?(\d+)\]?\s*$", str(v))
    return float(m.group(1)) if m else np.nan
