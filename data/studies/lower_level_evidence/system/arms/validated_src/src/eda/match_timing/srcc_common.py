"""Shared pieces of the sources-C linker (link_sources_c.py): Stage 0's side, names, set scores, rounds, the identity
linker, local days and the common output schema.

The identity rule (the task's, as the earlier studies applied it):
    * Candidates: a Stage 0 match of the same tour whose two players both share a name word with the source row's two
      players (in either order), with the source's day within -10 .. +21 days of the tournament date. Name words are
      normalised as src/eda/merge_feasibility/scan.py normalises names (accents, case, punctuation).
    * Each side's name agreement is graded: 3 the same full name (words in any order); 2 one name's words contained in
      the other's (dropped middle names, "Ramos" / "Ramos-Vinolas"), or a shared surname word with the same first
      initial; 1 a shared surname word only. A shared given name alone is no evidence.
    * Confirmation: identical set scores (stage0_build.tokens_of, winner first, trailing unplayed 0-0 sets dropped; a
      match tiebreak '[10-8]' matches a set the same side won, written 1-0, 10-8 or 7-6) and/or the same round on a day
      inside the match's plausible days (plausible()). A candidate needs names graded 2 or better on both sides (or
      3 + 1) and one of the two; weaker names need identical set scores and a round that does not disagree. A
      candidate in another tournament than the Stage 0 tournament id the source names (WTA edition number, the ATP
      code in TDI's pages) is never taken.
    * Choice (stage1_odds.pick, extended): names, then scores, then round, then a source tournament id that agrees,
      then the distance of the day from the match's plausible playing window. Equal best candidates leave the source
      row ambiguous (its candidates are recorded); a Stage 0 match takes at most one source row, the best ranked.
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
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.predictability_diagnostic import stage4_country as SC  # noqa: E402
from src.eda.match_timing import srcc_tz as TZ  # noqa: E402

OUT = ROOT / "data" / "studies" / "match_timing"
LINKS = OUT / "links"
DUMP = ROOT / "data" / "dump"
RAW = ROOT / "data" / "raw"
LINK_COLUMNS = ["match_id", "source", "source_key", "date_local", "start_utc", "date_basis", "link_method",
                "score_agrees", "round_agrees"]
SCHEMA = pa.schema([("match_id", pa.string()), ("source", pa.string()), ("source_key", pa.string()),
                    ("date_local", pa.date32()), ("start_utc", pa.timestamp("ms", tz="UTC")),
                    ("date_basis", pa.string()), ("link_method", pa.string()), ("score_agrees", pa.bool_()),
                    ("round_agrees", pa.bool_())])
WINDOW = (-10, 21)                     # source day minus tournament date, in days (the task's window)
EARLY_ROUNDS = ("R128", "R64", "R32", "R16")
PARTICLES = {"de", "da", "van", "von", "der", "del", "la", "le", "di", "dos", "du", "das", "do", "den", "ter", "ten",
             "el", "al", "bin", "y", "e", "st"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
EPOCH = pd.Timestamp("1970-01-01")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Names

TRANSLIT = str.maketrans({"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O",
                          "æ": "ae", "Æ": "Ae", "œ": "oe", "Œ": "Oe", "ß": "ss", "ı": "i",
                          "ð": "d", "þ": "th", "ħ": "h"})


def fold(word: str) -> str:
    """German umlauts written out ('Wuerth', 'Goerges') read as their plain vowel ('Wurth', 'Gorges'), on both sides."""
    return word.replace("ue", "u").replace("oe", "o").replace("ae", "a")


@lru_cache(maxsize=None)
def name_info(name) -> tuple[str, tuple, frozenset, str]:
    """(full key: sorted words; words in order; surname words; first initial) of a player name.

    Words are scan.norm's, without Jr/Sr/II; one-letter words are initials. The surname words are every word after
    the first, or every word when the name starts with an initial ("J. Pla Malfeito")."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return "", (), frozenset(), ""
    raw = [fold(t) for t in S.norm(str(name).translate(TRANSLIT)).split() if t not in SUFFIXES]
    if not raw:
        return "", (), frozenset(), ""
    words = tuple(t for t in raw if len(t) >= 2)
    initial = raw[0][0]
    if len(raw[0]) == 1:
        surname = frozenset(words)
    else:
        surname = frozenset(words[1:]) if len(words) > 1 else frozenset(words)
    return " ".join(sorted(words)), words, surname - PARTICLES, initial


def match_words(name) -> list[str]:
    """The words a name is looked up by: three letters or more and not a particle (both words of 'Li Na')."""
    _, words, _, _ = name_info(name)
    keys = [w for w in words if len(w) >= 3 and w not in PARTICLES]
    return sorted(set(keys or [w for w in words if w not in PARTICLES] or list(words)))


@lru_cache(maxsize=None)
def name_grade(a, b) -> int:
    """3 same full name; 2 one name's words inside the other's, or a shared surname word with the same initial;
    1 a shared surname word only; 0 otherwise (a shared given name is not evidence)."""
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


# ------------------------------------------------------------------------------------------------
# Set scores and rounds

@lru_cache(maxsize=None)
def s0_sets(score: str) -> tuple:
    """Stage 0's set scores, winner first; a match tiebreak in place of a set ('[10-8]') is (1, 0, 'mt') or
    (0, 1, 'mt') by who won it."""
    if not isinstance(score, str):
        return ()
    return tuple((a, b) if not br else ((1, 0, "mt") if a > b else (0, 1, "mt"))
                 for a, b, _, br in B.tokens_of(score)[0])


def trim_sets(sets) -> tuple:
    out = list(sets or ())
    while out and tuple(out[-1])[:2] == (0, 0):
        out.pop()
    return tuple(tuple(int(x) for x in s[:2]) + tuple(s[2:]) for s in out)


def _set_equal(src: tuple, ref: tuple) -> bool:
    """One set: equal games; against a match tiebreak, the same side won it, written as 1-0 (the WTA's lists), as
    the tiebreak's points (10-8) or as a 7-6-like set."""
    if len(ref) == 3:
        a, b = src[:2]
        return a != b and (a > b) == (ref[0] > ref[1]) and ((max(a, b) == 1 and min(a, b) == 0) or max(a, b) >= 7)
    return tuple(src[:2]) == tuple(ref[:2])


def sets_equal(x, y) -> bool:
    """Identical set scores: ``x`` the source's, ``y`` Stage 0's (both winner first); trailing unplayed 0-0 sets
    dropped."""
    x, y = trim_sets(x), trim_sets(y)
    return len(x) > 0 and len(x) == len(y) and all(_set_equal(a, b) for a, b in zip(x, y))


def int_or_none(v):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        s = str(v).strip()
        if s == "" or s.lower() in ("nan", "none", "null"):
            return None
        m = re.match(r"^-?\d+", s)
        return int(m.group(0)) if m else None
    except (TypeError, ValueError):
        return None


def sets_from_pairs(pairs) -> tuple:
    """(a, b) games per set from a list of (a, b) values that may be blank; stops at the first blank set."""
    out = []
    for a, b in pairs:
        a, b = int_or_none(a), int_or_none(b)
        if a is None or b is None:
            break
        out.append((a, b))
    return tuple(out)


SOFA_ROUNDS = {"round of 128": "R128", "round of 64": "R64", "round of 32": "R32", "round of 16": "R16",
               "quarterfinals": "QF", "quarterfinal": "QF", "quarter-finals": "QF", "quarter final": "QF",
               "semifinals": "SF", "semifinal": "SF", "semi-finals": "SF", "final": "F", "r128": "R128", "r64": "R64",
               "r32": "R32", "r16": "R16", "1/8-finals (r16)": "R16", "1/16-finals (r32)": "R32", "1/8": "R16",
               "1/16": "R32", "1/32": "R64", "1/64": "R128", "1st round": "N1", "2nd round": "N2", "3rd round": "N3",
               "4th round": "N4", "first round": "N1", "second round": "N2", "third round": "N3", "fourth round": "N4",
               "round 1": "N1", "round 2": "N2", "round 3": "N3", "round 4": "N4", "round robin": "RR",
               "bronze medal match": "BR", "third place": "BR",
               # draws with byes: Stage 0 (Sackmann) names the first round by the next power of two
               "round of 96": "R128", "round of 56": "R64", "round of 48": "R64", "round of 28": "R32",
               "round of 24": "R32"}


def round_code(label) -> str | None:
    """A source round label in Stage 0's vocabulary: R128..R16, QF, SF, F, RR, BR, Q1..Q4; 'N<k>' for the k-th round
    of a main draw counted from its first; 'QLAST' for a qualifying final whose number is not given; 'Q?' for
    qualifying without a number; None when unreadable."""
    if label is None or (isinstance(label, float) and np.isnan(label)):
        return None
    s = " ".join(str(label).strip().lower().replace("_", " ").split())
    if not s:
        return None
    if "qualif" in s or s.startswith("q") and re.fullmatch(r"q\d", s):
        if "final" in s and not re.search(r"\d", s):
            return "QLAST"
        m = re.search(r"(\d)", s)
        if m:
            return f"Q{m.group(1)}"
        if re.search(r"\b(1st|first)\b", s):
            return "Q1"
        if re.search(r"\b(2nd|second)\b", s):
            return "Q2"
        if re.search(r"\b(3rd|third)\b", s):
            return "Q3"
        return "Q?"
    return SOFA_ROUNDS.get(s, s.upper() if re.fullmatch(r"r\d+|qf|sf|f|rr|br", s) else None)


def round_grade(src: str | None, s0_round: str, s0_no, s0_qual: bool, s0_qmax) -> int:
    """2 the rounds agree, 1 nothing to compare, 0 they disagree."""
    if src is None or not isinstance(src, str) or not src:
        return 1
    if src == "Q?":
        return 1 if s0_qual else 0
    if src == "QLAST":
        if not s0_qual:
            return 0
        return 1 if s0_qmax is None or (isinstance(s0_qmax, float) and np.isnan(s0_qmax)) else \
            (2 if s0_round == f"Q{int(s0_qmax)}" else 0)
    if src.startswith("N"):
        k = int(src[1:])
        if s0_round in EARLY_ROUNDS:
            return 2 if (s0_no is not None and not (isinstance(s0_no, float) and np.isnan(s0_no)) and int(s0_no) == k) else 0
        return 0
    return 2 if src == s0_round else 0


# ------------------------------------------------------------------------------------------------
# Stage 0's side

def plausible(level: str, qual: bool) -> tuple[int, int]:
    """Days from the tournament date on which a match of this kind is normally played (used to rank candidates,
    and, widened, to flag days; from tennis-data's main-draw days and the qualifying schedules)."""
    if qual:
        return (-10, -1) if level == "GS" else (-4, 2)
    return {"GS": (-1, 15), "T1000": (-2, 13), "FIN": (-2, 8), "TEAM": (-4, 16)}.get(level, (-3, 8))


def flag_window(level: str, qual: bool) -> tuple[int, int]:
    """The summary's flags: a day more than one day before the tournament start (for qualifying, the start of
    qualifying: 9 days before the main draw at a Slam, 3 elsewhere), or after a plausible end."""
    if qual:
        return (-1 - (9 if level == "GS" else 3), 1)
    return (-1, {"GS": 15, "T1000": 13, "TEAM": 13, "FIN": 8}.get(level, 9))


_STAGE0: pd.DataFrame | None = None


def stage0() -> pd.DataFrame:
    """Every Stage 0 match with the two names, winner-first set scores, early-round numbers, the qualifying rounds'
    depth and the event's country (hand-made table; ITF ids carry a country code)."""
    global _STAGE0
    if _STAGE0 is not None:
        return _STAGE0
    cols = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
            "tournament_name", "tournament_date", "status", "score", "player_a_id", "player_b_id", "a_won"]
    m = pd.read_parquet(C.MATCHES, columns=cols)
    for c in ("match_id", "tour", "level", "round", "tournament_id", "tournament_name", "status", "score",
              "player_a_id", "player_b_id"):
        m[c] = m[c].astype(object)
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "side", "player_name"])
    for side in ("A", "B"):
        n = mp[mp["side"] == side].drop_duplicates("match_id").set_index("match_id")["player_name"]
        m[f"name_{side.lower()}"] = m["match_id"].map(n).astype(object)
    m["tdate"] = pd.to_datetime(m["tournament_date"]).astype("datetime64[ns]")
    m["sets_w"] = m["score"].map(s0_sets)
    ev = ["tour", "tournament_date", "tournament_id"]
    early = m["round"].isin(EARLY_ROUNDS)
    first = m[early].groupby(ev)["round_order"].transform("min")
    m["round_no"] = np.nan
    m.loc[first.index, "round_no"] = (m.loc[first.index, "round_order"] - first + 1).astype("float64")
    qn = m["round"].str.extract(r"^Q(\d)$")[0].astype("float64")
    m["qmax"] = qn.groupby([m[c] for c in ev]).transform("max")
    m["country"] = event_countries(m)
    _STAGE0 = m.reset_index(drop=True)
    return _STAGE0


def event_countries(m: pd.DataFrame) -> pd.Series:
    """The event's IOC country: the hand-made Stage 4 table (evaluation events), else the code in an ITF id."""
    t = SC.load_table()
    ev = m[["tour", "year", "tournament_id", "tournament_name"]].drop_duplicates().reset_index(drop=True)
    ev["country"] = SC.event_country(ev, t)
    itf = ev["tournament_id"].astype(str).str.extract(r"^\d{4}-[MW]-[A-Z0-9]+-([A-Z]{3})-")[0]
    ev["country"] = ev["country"].astype(object).where(ev["country"].notna(), itf)
    key = ev.set_index(["tour", "year", "tournament_id", "tournament_name"])["country"]
    idx = pd.MultiIndex.from_frame(m[["tour", "year", "tournament_id", "tournament_name"]])
    return pd.Series(key.reindex(idx).to_numpy(), index=m.index, dtype=object)


def s0_city(name) -> str:
    """The city in a Stage 0 event name: 'M25 Nottingham' -> 'nottingham', 'Heilbronn CH' -> 'heilbronn',
    'Moscow $25K' -> 'moscow', 'Makarska 125' -> 'makarska'."""
    s = TZ.norm_place(name)
    s = re.sub(r"\b([mw]\d{2,3}|\d+k|ch|challenger|wta|atp|itf|open|cup|international|championships?)\b", " ", s)
    s = re.sub(r"\b\d+\b", " ", s)
    return " ".join(s.split())


# ------------------------------------------------------------------------------------------------
# The identity linker

def _weeks(days: np.ndarray) -> np.ndarray:
    return np.floor_divide(days, 7)


LINK_COLS = ["sid", "idx", "match_id", "gap", "sc", "rd", "q1", "q2", "tidok", "dist", "p1_side", "pass"]
OTHER = {"A": "B", "B": "A"}


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and v == "")


def _score(c: pd.DataFrame, si: pd.DataFrame, s0: pd.DataFrame) -> pd.DataFrame:
    """Grade candidates (sid, idx, p1_side, gap): names per side, identical set scores, round, tournament id,
    distance from the plausible days."""
    c = c.reset_index(drop=True).copy()
    sm = s0.loc[c["idx"]]
    na, nb = sm["name_a"].to_numpy(), sm["name_b"].to_numpy()
    p1n, p2n = si.loc[c["sid"], "p1"].to_numpy(), si.loc[c["sid"], "p2"].to_numpy()
    a1 = c["p1_side"].to_numpy() == "A"
    c["q1"] = [name_grade(x, (y if f else z)) for x, y, z, f in zip(p1n, na, nb, a1)]
    c["q2"] = [name_grade(x, (z if f else y)) for x, y, z, f in zip(p2n, na, nb, a1)]
    a_won = sm["a_won"].to_numpy(dtype=bool)
    p1_won = np.where(a1, a_won, ~a_won)
    ss = si.loc[c["sid"], "sets"].to_numpy()
    c["sc"] = [bool(s) and sets_equal(s if w else tuple((b, a) for a, b in s), t)
               for s, w, t in zip(ss, p1_won, sm["sets_w"].to_numpy())]
    rnd = si.loc[c["sid"], "rnd"].to_numpy()
    qual = si.loc[c["sid"], "qual"].to_numpy()
    s0q = sm["qualifying"].to_numpy(dtype=bool)
    rd = np.array([round_grade(r, sr, sn, sq, qm) for r, sr, sn, sq, qm in
                   zip(rnd, sm["round"].to_numpy(), sm["round_no"].to_numpy(), s0q, sm["qmax"].to_numpy())],
                  dtype="int64")
    qmis = np.array([not _blank(q) and bool(q) != b for q, b in zip(qual, s0q)], dtype=bool)
    if len(rd):
        rd[qmis] = 0
    c["rd"] = rd
    tid = si.loc[c["sid"], "tid"].to_numpy()
    c["tidok"] = [0 if _blank(t) else (1 if t == u else -1) for t, u in zip(tid, sm["tournament_id"].to_numpy())]
    pw = [plausible(lv, q) for lv, q in zip(sm["level"].to_numpy(), s0q)]
    c["dist"] = [max(p[0] - x, x - p[1], 0) for p, x in zip(pw, c["gap"].to_numpy())]
    c["qs"] = c["q1"] + c["q2"]
    c["negdist"] = -c["dist"]
    return c


def _pick(c: pd.DataFrame, key: list[str]) -> tuple[pd.DataFrame, dict, list]:
    """One Stage 0 match per source row and one source row per match: the best by ``key``; equal best candidates
    leave the source row ambiguous; a match claimed by two rows goes to the better ranked. Returns (kept, ambiguous
    {sid: [idx]}, lost sids)."""
    if c.empty:
        return c, {}, []
    c = c.sort_values(["sid"] + key + ["idx"], ascending=[True] + [False] * len(key) + [True])
    top = c.drop_duplicates("sid")
    tied = c.merge(top[["sid"] + key], on=["sid"] + key)
    n = tied.groupby("sid")["idx"].nunique()
    amb = {s: sorted(g["idx"].unique().tolist()) for s, g in tied[tied["sid"].isin(n.index[n > 1])].groupby("sid")}
    top = top[~top["sid"].isin(list(amb))]
    top = top.sort_values(["idx"] + key + ["sid"], ascending=[True] + [False] * len(key) + [True])
    kept = top.drop_duplicates("idx")
    lost = top.loc[~top.index.isin(kept.index), "sid"].tolist()
    return kept, amb, lost


def crosswalk(links: pd.DataFrame, si: pd.DataFrame, s0: pd.DataFrame) -> dict:
    """Source player id -> Stage 0 player id, learned from linked matches: the Stage 0 id a source id is linked to in
    at least 80% of its links, when no other source id claims the same Stage 0 id."""
    if links.empty or "id1" not in si.columns:
        return {}
    sm = s0.loc[links["idx"]]
    a1 = links["p1_side"].to_numpy() == "A"
    s1 = np.where(a1, sm["player_a_id"].to_numpy(), sm["player_b_id"].to_numpy())
    s2 = np.where(a1, sm["player_b_id"].to_numpy(), sm["player_a_id"].to_numpy())
    pairs = pd.DataFrame({"src": np.concatenate([si.loc[links["sid"], "id1"].to_numpy(),
                                                 si.loc[links["sid"], "id2"].to_numpy()]),
                          "s0": np.concatenate([s1, s2])})
    pairs = pairs[pairs["src"].map(lambda v: not _blank(v))]
    if pairs.empty:
        return {}
    pairs["src"] = pairs["src"].astype(str)
    cnt = pairs.groupby(["src", "s0"]).size().rename("n").reset_index()
    tot = cnt.groupby("src")["n"].transform("sum")
    best = cnt[cnt["n"] >= 0.8 * tot].sort_values("n", ascending=False).drop_duplicates("src")
    claimed = best.groupby("s0")["src"].nunique()
    best = best[best["s0"].isin(claimed.index[claimed == 1])]
    return dict(zip(best["src"], best["s0"]))


def link(src: pd.DataFrame, s0: pd.DataFrame, window: tuple[int, int] = WINDOW) -> dict:
    """Link source rows to Stage 0 matches by identity, in three passes.

    ``src`` columns: sid (unique), tour, day (datetime64: the match's local or UTC day), p1, p2 (names), sets (tuple
    of (p1 games, p2 games)), rnd (round_code or None), qual (True/False/None), tid (a Stage 0 tournament id the source
    names, or None); optional id1, id2 (the source's own player ids). ``s0`` is a slice of stage0().

    1. pair: both players' names (module docstring).
    2. anchor: one player's name graded 2 or better, identical set scores, the same round, a tournament id that does
       not disagree, within two days of the plausible days: the other player is the same person under another name
       (married names: the WTA's 'Viktoria Kuzmova' is Stage 0's 'Viktoria Hruncakova'). Unique both ways.
    3. player_ids: source player ids mapped to Stage 0 ids through passes 1-2 (crosswalk()); both mapped ids are the
       Stage 0 pair, confirmed by set scores or round.
    Returns {"links": kept links (LINK_COLS), "reason": per source row, "ambiguous": {sid: [match ids]},
    "crosswalk": {source id: Stage 0 id}}."""
    src = src.reset_index(drop=True).copy()
    for col in ("id1", "id2"):
        if col not in src.columns:
            src[col] = None
    reason = pd.Series("no Stage 0 match with both players in the window", index=src["sid"], dtype=object)
    out = {"links": pd.DataFrame(columns=LINK_COLS), "reason": reason, "ambiguous": {}, "crosswalk": {}}
    if src.empty or s0.empty:
        return out
    src["d"] = ((src["day"] - EPOCH).dt.days).astype("float64")
    s0 = s0.copy()
    s0["idx"] = s0.index
    s0["d0"] = (s0["tdate"] - EPOCH).dt.days.astype("int64")
    si = src.set_index("sid")
    # Stage 0 name words, by tour and tournament week
    rows = []
    for side, col in (("A", "name_a"), ("B", "name_b")):
        words = s0[col].map(match_words)
        t = pd.DataFrame({"idx": s0["idx"].to_numpy(), "tour": s0["tour"].to_numpy(),
                          "wk": _weeks(s0["d0"].to_numpy()), "side": side, "w": words.to_numpy()}).explode("w")
        rows.append(t[t["w"].notna()])
    s0w = pd.concat(rows, ignore_index=True)
    ok = src["d"].notna()
    lo = _weeks(src.loc[ok, "d"].to_numpy() - window[1])
    hi = _weeks(src.loc[ok, "d"].to_numpy() - window[0])
    base = pd.DataFrame({"sid": src.loc[ok, "sid"].to_numpy(), "tour": src.loc[ok, "tour"].to_numpy(),
                         "wk": [list(range(int(a), int(b) + 1)) for a, b in zip(lo, hi)]}).explode("wk")
    base["wk"] = base["wk"].astype("int64")
    side_c = {}
    for pos in ("p1", "p2"):
        w = src.loc[ok, ["sid"]].assign(w=src.loc[ok, pos].map(match_words)).explode("w")
        w = w[w["w"].notna()]
        x = base.merge(w, on="sid").merge(s0w, on=["tour", "wk", "w"])[["sid", "idx", "side"]].drop_duplicates()
        x["gap"] = si.loc[x["sid"], "d"].to_numpy() - s0.loc[x["idx"], "d0"].to_numpy()
        side_c[pos] = x[(x["gap"] >= window[0]) & (x["gap"] <= window[1])]
    key = ["qs", "sc", "rd", "tidok", "negdist"]
    kept_all, amb_all = [], {}

    # 1. pair
    c = side_c["p1"].rename(columns={"side": "p1_side"}).merge(
        side_c["p2"].rename(columns={"side": "p2_side"})[["sid", "idx", "p2_side"]], on=["sid", "idx"])
    c = c[c["p1_side"] != c["p2_side"]].drop_duplicates(["sid", "idx", "p1_side"])
    if not c.empty:
        c = _score(c, si, s0)
        reason.loc[c["sid"].unique()] = "names in the window agree on a given name or other word only"
        named = c[np.minimum(c["q1"], c["q2"]) >= 1]
        reason.loc[named["sid"].unique()] = "names and window agree, but neither set scores nor round"
        # confirmed: identical set scores, or the same round on a day inside the match's plausible days; never a
        # candidate in another tournament than the one the source names
        conf = c["sc"] | ((c["rd"] == 2) & (c["dist"] == 0))
        strong = (np.minimum(c["q1"], c["q2"]) >= 1) & (c["qs"] >= 4) & conf & (c["tidok"] >= 0)
        weak = (np.minimum(c["q1"], c["q2"]) >= 1) & (c["qs"] >= 2) & c["sc"] & (c["rd"] >= 1) & (c["tidok"] >= 0)
        kept, amb, lost = _pick(c[strong | weak], key)
        kept_all.append(kept.assign(**{"pass": "pair"}))
        amb_all.update(amb)
        reason.loc[list(amb)] = "ambiguous: equally good Stage 0 matches"
        reason.loc[lost] = "its Stage 0 match was taken by a better-ranked source row"
        reason.loc[kept["sid"].tolist()] = "linked"

    # 2. anchor: one player, identical scores, same round
    taken = set(pd.concat(kept_all)["idx"]) if kept_all else set()
    done = set(reason.index[reason.eq("linked")]) | set(amb_all)
    a = pd.concat([side_c["p1"].rename(columns={"side": "p1_side"}),
                   side_c["p2"].assign(p1_side=side_c["p2"]["side"].map(OTHER)).drop(columns="side")],
                  ignore_index=True)
    a = a[~a["sid"].isin(done) & ~a["idx"].isin(taken)].drop_duplicates(["sid", "idx", "p1_side"])
    if not a.empty:
        a = _score(a, si, s0)
        good = (np.maximum(a["q1"], a["q2"]) >= 2) & a["sc"] & (a["rd"] == 2) & (a["tidok"] >= 0) & (a["dist"] <= 2)
        a = a[good]
        if not a.empty:
            per_sid = a.groupby("sid")["idx"].transform("nunique").eq(1)
            per_idx = a.groupby("idx")["sid"].transform("nunique").eq(1)
            kept = a[per_sid & per_idx].drop_duplicates("sid")
            kept_all.append(kept.assign(**{"pass": "anchor"}))
            reason.loc[kept["sid"].tolist()] = "linked"

    # 3. player ids learned from passes 1-2
    links = pd.concat(kept_all, ignore_index=True) if kept_all else pd.DataFrame(columns=LINK_COLS)
    xw = crosswalk(links, si, s0) if len(links) else {}
    out["crosswalk"] = xw
    rest = src[~src["sid"].isin(set(reason.index[reason.eq("linked")])) & ok]
    if xw and not rest.empty:
        r = rest.assign(x1=rest["id1"].astype(str).map(xw), x2=rest["id2"].astype(str).map(xw)).dropna(subset=["x1", "x2"])
        if not r.empty:
            s0k = s0[["idx", "tour", "player_a_id", "player_b_id", "d0"]]
            r = r.assign(k=[f"{min(x, y)}|{max(x, y)}" for x, y in zip(r["x1"], r["x2"])])
            s0k = s0k.assign(k=[f"{min(x, y)}|{max(x, y)}" for x, y in zip(s0k["player_a_id"], s0k["player_b_id"])])
            j = r[["sid", "tour", "k", "x1", "d"]].merge(s0k, on=["tour", "k"])
            j["gap"] = j["d"] - j["d0"]
            j = j[(j["gap"] >= window[0]) & (j["gap"] <= window[1])]
            taken = set(links["idx"]) if len(links) else set()
            j = j[~j["idx"].isin(taken)]
            if not j.empty:
                j["p1_side"] = np.where(j["x1"] == j["player_a_id"], "A", "B")
                j = _score(j[["sid", "idx", "p1_side", "gap"]], si, s0)
                j = j[(j["sc"] | ((j["rd"] == 2) & (j["dist"] == 0))) & (j["tidok"] >= 0)]
                kept, amb, lost = _pick(j, ["sc", "rd", "tidok", "negdist"])
                kept_all.append(kept.assign(**{"pass": "player_ids"}))
                for s in kept["sid"]:
                    amb_all.pop(s, None)
                reason.loc[kept["sid"].tolist()] = "linked"
    links = pd.concat(kept_all, ignore_index=True) if kept_all else pd.DataFrame(columns=LINK_COLS)
    if links.empty:
        return out
    links["match_id"] = s0.loc[links["idx"], "match_id"].to_numpy()
    out["links"] = links[LINK_COLS].reset_index(drop=True)
    out["ambiguous"] = {s: s0.loc[v, "match_id"].tolist() for s, v in amb_all.items() if reason.get(s) != "linked"}
    return out


# ------------------------------------------------------------------------------------------------
# Days and output

def local_day(utc: pd.Series, zones: pd.Series) -> pd.Series:
    """The local calendar day of each UTC instant in its zone (IANA name); missing where either is missing."""
    out = pd.Series(pd.NaT, index=utc.index, dtype="datetime64[ns]")
    u = pd.to_datetime(utc, utc=True)
    for z, idx in zones.groupby(zones).groups.items():
        if not isinstance(z, str) or not z:
            continue
        loc = u.loc[idx].dt.tz_convert(TZ.zoneinfo(z)).dt.tz_localize(None).dt.normalize()
        out.loc[idx] = loc.astype("datetime64[ns]").to_numpy()
    return out


def utc_day(utc: pd.Series) -> pd.Series:
    return pd.to_datetime(utc, utc=True).dt.tz_convert(None).dt.normalize().astype("datetime64[ns]")


def write_links(frame: pd.DataFrame, source: str, flag: bool = True) -> Path:
    """Write links/<source>.parquet in the common schema (columns exactly LINK_COLUMNS). With ``flag``, a day outside
    the match's flag window (flag_window(): more than a day before the tournament start, or after a plausible end)
    adds ';outside_plausible_days' to link_method; the day itself is kept."""
    LINKS.mkdir(parents=True, exist_ok=True)
    f = frame.reindex(columns=LINK_COLUMNS).copy()
    f["source"] = source
    assert f["match_id"].notna().all() and not f["match_id"].duplicated().any(), f"{source}: match ids not unique"
    assert f["date_basis"].isin(["local", "utc_date"]).all(), f"{source}: bad date_basis"
    dl = pd.to_datetime(f["date_local"], errors="coerce")
    su = pd.to_datetime(f["start_utc"], errors="coerce", utc=True)
    if flag and len(f):
        s = stage0().set_index("match_id")
        lv, q = f["match_id"].map(s["level"]), f["match_id"].map(s["qualifying"])
        off = (dl - f["match_id"].map(s["tdate"])).dt.days
        bad = []
        for o, a, b in zip(off, lv, q):
            if pd.isna(o) or not isinstance(a, str):
                bad.append(False)
                continue
            lo, hi = flag_window(a, bool(b))
            bad.append(bool(o < lo or o > hi))
        bad = np.array(bad, dtype=bool)
        f.loc[bad, "link_method"] = f.loc[bad, "link_method"].astype(str) + ";outside_plausible_days"
    table = pa.table({
        "match_id": pa.array(f["match_id"].astype(str).tolist(), pa.string()),
        "source": pa.array(f["source"].astype(str).tolist(), pa.string()),
        "source_key": pa.array(f["source_key"].astype(str).tolist(), pa.string()),
        "date_local": pa.array([None if pd.isna(x) else x.date() for x in dl], pa.date32()),
        "start_utc": pa.array([None if pd.isna(x) else x.to_pydatetime() for x in su], pa.timestamp("ms", tz="UTC")),
        "date_basis": pa.array(f["date_basis"].astype(str).tolist(), pa.string()),
        "link_method": pa.array(f["link_method"].astype(str).tolist(), pa.string()),
        "score_agrees": pa.array([None if pd.isna(x) else bool(x) for x in f["score_agrees"]], pa.bool_()),
        "round_agrees": pa.array([None if pd.isna(x) else bool(x) for x in f["round_agrees"]], pa.bool_()),
    }, schema=SCHEMA)
    path = LINKS / f"{source}.parquet"
    pq.write_table(table, path)
    return path


def write_diagnostics(frame: pd.DataFrame, source: str) -> Path:
    """links/<source>.csv: every source row in scope that is not linked, with why, and the ambiguous candidates."""
    LINKS.mkdir(parents=True, exist_ok=True)
    path = LINKS / f"{source}.csv"
    frame.to_csv(path, index=False, encoding="utf-8")
    return path


def rd_bool(rd) -> object:
    return {2: True, 0: False}.get(int(rd), None) if rd is not None and not pd.isna(rd) else None


def outcome_counts(reason: pd.Series) -> dict:
    return {str(k): int(v) for k, v in reason.value_counts().items()}


def jdump(value, path: Path) -> None:
    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (pd.Timestamp, np.datetime64)):
            return str(o)
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, (set, frozenset, tuple)):
            return list(o)
        return str(o)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=default), encoding="utf-8")
