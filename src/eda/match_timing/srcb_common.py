"""Shared machinery for linking match-timing sources (sources B) to the Stage 0 match table.

Identity first. A source row is a candidate for a Stage 0 match of the same tour when both players
agree (Stage 0 player ids where the source has a crosswalk, else normalised names) and the source's
date lies between 10 days before and 21 days after the Stage 0 tournament date. Candidates are then
ranked as src/eda/predictability_diagnostic/stage1_odds.pick() ranks them: identical set scores first
(either side's reading; a score cut short in one source neither confirms nor contradicts), then an
agreeing round, then the nearest date, with one extra rule: a date inside the match's expected span
beats one outside it (qualifying: 10 days before the tournament date to 2 after; first rounds and round
robins: the day before to a level-dependent end; the round of 16 onwards: the day after the start to
that end - see expected()). A candidate without identical scores must also lie inside that span
(otherwise it is more likely the same pair at a neighbouring event), unless the pass matched the event
itself (Infosys) or the source is dated by event (Tennis My Life). Equal best candidates leave the row
ambiguous, and each Stage 0 match takes at most one source row (pick() keeps the better-ranked row).

Name keys reuse src/eda/merge_feasibility/scan.py: name_key() (accents, case and punctuation removed,
words sorted, so 'Zhang Zhizhen' equals 'Zhizhen Zhang'; apostrophes dropped first, so "O'Connell"
equals "Oconnell") for full names, and td_variants() ('surname span + first initial', every span) for
abbreviated names such as 'O. Otte' or 'Otte O.'. Full names that differ between sources (married
names, dropped middle names) are caught by a one-player anchor pass (the other two names must share a
word; identical set scores, or for sources without scores an agreeing round), and by player ids
learned from the links already made.
"""
from __future__ import annotations

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

from src.eda.match_timing import srcb_tz as TZ  # noqa: E402
from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.predictability_diagnostic import stage1_odds as O  # noqa: E402
from src.eda.predictability_diagnostic import stage4_country as K  # noqa: E402

OUT = ROOT / "data" / "studies" / "match_timing" / "links"
RAW = ROOT / "data" / "raw" / "public_dump"
DUMP = C.DUMP
WINDOW = (-10, 21)                   # source date minus Stage 0 tournament date, in days
END_DAYS = {"GS": 15, "T1000": 14, "TEAM": 14, "FIN": 10}   # plausible last day after the start; others 9
END_DEFAULT = 9
OUTSIDE_PENALTY = 100                # added to |gap| when a date is outside the event's expected span
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Names

_APOSTROPHE = re.compile(r"['’`´]")


def _clean(name) -> str:
    """Apostrophes dropped before scan.py's normalisation, so "O'Connell" and "Oconnell" agree."""
    return _APOSTROPHE.sub("", name) if isinstance(name, str) else ""


@lru_cache(maxsize=None)
def full_key(name) -> str:
    """'F:' + scan.py's name_key (sorted normalised words); '' for a blank or one-word name."""
    k = S.name_key(_clean(name)) if isinstance(name, str) else ""
    return "F:" + k if len(k.split()) >= 2 else ""


@lru_cache(maxsize=None)
def abbr_variants(name) -> tuple:
    """Every 'surname span + first initial' form of a full name (scan.py's td_variants), as 'A:' keys."""
    name = _clean(name)
    if not name or len(S.norm(name).split()) < 2:
        return ()
    return tuple("A:" + v for v in S.td_variants(name))


@lru_cache(maxsize=None)
def abbr_from_full(name) -> tuple:
    """A source's full name as a few abbreviated keys (first initial + the last one, two or all later words)."""
    if not isinstance(name, str):
        return ()
    t = S.norm(_clean(name)).split()
    if len(t) < 2:
        return ()
    ini = t[0][0]
    keys = {t[-1] + " " + ini, " ".join(t[1:]) + " " + ini}
    if len(t) >= 3:
        keys.add(" ".join(t[-2:]) + " " + ini)
    if len(t) == 2:
        keys.add(t[0] + " " + t[1][0])      # surname first ('Sun Qian' is Qian Sun)
    return tuple(sorted("A:" + k for k in keys))


_INITIAL = re.compile(r"^[A-Za-z]\.?$")


@lru_cache(maxsize=None)
def abbr_short(name) -> str:
    """An abbreviated name as an 'A:' key: 'O. Otte' / 'J. M. Del Potro' / 'P. KOTOV' (initials first) or
    'Otte O.' (tennis-data style, scan.py's td_key) -> 'A:otte o'. '' if the name is not abbreviated."""
    if not isinstance(name, str):
        return ""
    name = _clean(name)
    toks = name.replace(".", ". ").split()
    if len(toks) < 2:
        return ""
    if _INITIAL.match(toks[0]):
        i = 0
        while i < len(toks) and _INITIAL.match(toks[i]):
            i += 1
        rest = S.norm(" ".join(toks[i:]))
        return "A:" + rest + " " + toks[0][0].lower() if rest else ""
    if _INITIAL.match(toks[-1]):
        k = S.td_key(name.replace(".", ". ").strip())
        return "A:" + k if len(k.split()) >= 2 else ""
    return ""


def share_word(a, b) -> bool:
    """Two names share a normalised word of three letters or more."""
    wa = {w for w in S.norm(_clean(a)).split() if len(w) >= 3} if isinstance(a, str) else set()
    wb = {w for w in S.norm(_clean(b)).split() if len(w) >= 3} if isinstance(b, str) else set()
    return bool(wa & wb)


# ------------------------------------------------------------------------------------------------
# Rounds and scores

ROUND_WORDS = {
    "final": "F", "the final": "F", "semi-finals": "SF", "semifinals": "SF", "semi-final": "SF", "semifinal": "SF",
    "quarter-finals": "QF", "quarterfinals": "QF", "quarter-final": "QF", "quarterfinal": "QF",
    "1/8-finals": "R16", "1/16-finals": "R32", "1/32-finals": "R64", "1/64-finals": "R128",
    "round of 16": "R16", "round of 32": "R32", "round of 64": "R64", "round of 128": "R128",
    "3rd place": "BR", "match for 3rd place": "BR", "third place": "BR",
    "qualification round 1": "Q1", "qualification round 2": "Q2", "qualification round 3": "Q3",
    "qualifying round 1": "Q1", "qualifying round 2": "Q2", "qualifying round 3": "Q3",
    "qualification final": "QREL0", "qualifications": "Q", "qualification": "Q", "qualifying": "Q",
    "qualifying competition": "Q",
}
CODES = {"R128", "R64", "R32", "R16", "QF", "SF", "F", "BR", "RR", "Q1", "Q2", "Q3", "Q4"}
REL_OF_MAIN = {"F": 0, "SF": 1, "QF": 2, "R16": 3}   # a qualifying draw labelled with main-draw names


def round_spec(label, qualifying) -> str:
    """A source's round as alternatives of Stage 0 codes joined by '|': 'R32', 'Q1', 'Q' (some qualifying
    round), 'QREL0' (the event's last qualifying round, QREL1 the one before ...). ``qualifying`` is the
    source's flag: True, False or None (unknown, so 'Final' may be the main final or the last qualifying round)."""
    s = str(label or "").strip()
    if not s:
        return "Q" if qualifying is True else ""
    s = s.rsplit(" - ", 1)[-1].strip() if " - " in s else s
    code = s.upper() if s.upper() in CODES else ROUND_WORDS.get(s.lower(), "")
    if not code:
        return "Q" if qualifying is True else ""
    if code.startswith("Q"):
        return code    # an explicit qualifying label wins over the flag
    if qualifying is True:
        return f"QREL{REL_OF_MAIN[code]}" if code in REL_OF_MAIN else "Q"
    if qualifying is None and code in REL_OF_MAIN:
        return f"{code}|QREL{REL_OF_MAIN[code]}"
    return code


def round_agree(spec: str, s0_round: str, s0_qual: bool, s0_qrel) -> int:
    """2 the round agrees, 0 it does not, 1 unknown (stage1_odds.round_agrees' scale). An alternative
    'RR?' says the source's label cannot be read against a round robin (Infosys match numbers)."""
    if not spec:
        return 1
    if s0_round == "RR" and "RR?" in spec:
        return 1
    for alt in spec.split("|"):
        if alt == "Q":
            if s0_qual:
                return 1 if spec == "Q" else 2
        elif alt.startswith("QREL"):
            if s0_qual and s0_qrel == int(alt[4:]):
                return 2
        elif alt == s0_round:
            return 2
    return 0


def sets_of_score(score) -> tuple:
    """Stage 0's set scores as (games, games) pairs, written as the source wrote them; match tiebreaks out."""
    if not isinstance(score, str) or not score:
        return ()
    return tuple((a, b) for a, b, br in B.set_scores(score) if not br)


def _strip_empty(sets) -> tuple:
    """Trailing 0-0 sets out (api-tennis pads 2024 scores to five sets with 0-0)."""
    s = tuple(sets or ())
    while s and s[-1] == (0, 0):
        s = s[:-1]
    return s


def sets_agree(src_sets, s0_sets) -> int:
    """2 identical set scores (either side's reading); 1 one side has none, or one is the start of the
    other (a score cut short in one source); 0 different."""
    a, b = _strip_empty(src_sets), _strip_empty(s0_sets)
    if not a or not b:
        return 1
    flip = tuple((y, x) for x, y in a)
    if a == b or flip == b:
        return 2
    n = min(len(a), len(b))
    if a[:n] == b[:n] or flip[:n] == b[:n]:
        return 1
    return 0


# ------------------------------------------------------------------------------------------------
# Stage 0

S0_COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
           "tournament_name", "tournament_date", "status", "score", "player_a_id", "player_b_id", "a_won",
           "source", "tml_link", "source_file", "source_row"]


def load_stage0() -> pd.DataFrame:
    """Stage 0 matches with both names, set scores, the event's zone, country and expected span."""
    m = pd.read_parquet(C.MATCHES, columns=S0_COLS)
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "side", "player_name"])
    names = mp.pivot(index="match_id", columns="side", values="player_name")
    m["a_name"] = m["match_id"].map(names["A"])
    m["b_name"] = m["match_id"].map(names["B"])
    m["sets"] = m["score"].map(sets_of_score)
    m["tdate"] = m["tournament_date"].astype("datetime64[ns]")
    # qualifying rounds counted back from each event's last one (QREL0 = the qualifying final)
    q = m["qualifying"].to_numpy()
    qn = pd.to_numeric(m["round"].str.extract(r"^Q(\d)$")[0], errors="coerce")
    ev = m["tour"] + "|" + m["tournament_id"] + "|" + m["tdate"].dt.strftime("%Y%m%d")
    qmax = qn.groupby(ev).transform("max")
    m["qrel"] = np.where(q, qmax - qn, np.nan)
    # the event's country (stage 4 table) and zone
    events = m[["tour", "year", "tournament_id", "tournament_name"]].drop_duplicates().reset_index(drop=True)
    events["country"] = K.event_country(events).astype("object")
    events["event_key"] = events["tournament_name"].map(K.event_key)
    events["tz"] = [TZ.zone_for(c, k) for c, k in zip(events["country"], events["event_key"])]
    m = m.merge(events, on=["tour", "year", "tournament_id", "tournament_name"], how="left")
    m["end_days"] = m["level"].map(END_DAYS).fillna(END_DEFAULT).astype("int64")
    return m


def player_names(s0: pd.DataFrame) -> pd.Series:
    """Each Stage 0 player id's most common name."""
    both = pd.concat([s0[["player_a_id", "a_name"]].set_axis(["pid", "name"], axis=1),
                      s0[["player_b_id", "b_name"]].set_axis(["pid", "name"], axis=1)])
    both = both.dropna()
    cnt = both.groupby(["pid", "name"]).size().rename("n").reset_index().sort_values(["pid", "n"], ascending=[True, False])
    return cnt.drop_duplicates("pid").set_index("pid")["name"]


def s0_long(s0: pd.DataFrame, idx, forms=("F", "A", "I")) -> pd.DataFrame:
    """(li, tour, side, form, key): every key of each side of the Stage 0 matches ``idx``."""
    sub = s0.loc[idx]
    parts = []
    for side, ncol, icol in ((0, "a_name", "player_a_id"), (1, "b_name", "player_b_id")):
        base = pd.DataFrame({"li": sub.index, "tour": sub["tour"].to_numpy(), "side": side})
        if "F" in forms:
            parts.append(base.assign(form="F", key=sub[ncol].map(full_key).to_numpy()))
        if "A" in forms:
            parts.append(base.assign(form="A", key=sub[ncol].map(abbr_variants).to_numpy()).explode("key"))
        if "I" in forms:
            parts.append(base.assign(form="I", key=sub[icol].fillna("").to_numpy()))
    out = pd.concat(parts, ignore_index=True)
    out = out[out["key"].notna() & (out["key"] != "")]
    return out.drop_duplicates(["li", "side", "form", "key"]).reset_index(drop=True)


def pairs_from_long(long: pd.DataFrame, idx: str, side: str) -> pd.DataFrame:
    """(idx, tour, form, pair): every unordered pair of one key per side, within one form."""
    a = long[long[side] == 0][[idx, "tour", "form", "key"]]
    b = long[long[side] == 1][[idx, "form", "key"]]
    j = a.merge(b, on=[idx, "form"], suffixes=("1", "2"))
    j = j[j["key1"] != j["key2"]]
    pair = np.where(j["key1"] < j["key2"], j["key1"] + "|" + j["key2"], j["key2"] + "|" + j["key1"])
    return pd.DataFrame({idx: j[idx].to_numpy(), "tour": j["tour"].to_numpy(), "form": j["form"].to_numpy(),
                         "pair": pair}).drop_duplicates()


# ------------------------------------------------------------------------------------------------
# The linker

LATE_ROUNDS = ("R16", "QF", "SF", "F", "BR")   # never played before the event's first day
QUAL_LAST_DAY = 2                               # qualifying ends by the second day after the start date


def expected(gap, qualifying, late, end_days) -> np.ndarray:
    """A date inside the event's expected span: qualifying from 10 days before the tournament date to 2
    after; first main-draw rounds and round robins from the day before to the level's end; the round of
    16 onwards from the day after the start to the end."""
    lo = np.where(qualifying, WINDOW[0], np.where(late, 1, -1))
    hi = np.where(qualifying, QUAL_LAST_DAY, end_days)
    return (gap >= lo) & (gap <= hi)


class Linker:
    """Links one source's rows (index ri = 0..n-1) to Stage 0 matches (index li) in passes.

    The source frame needs: tour, date (naive day used for the window), sets (tuple or ()), rspec
    (round_spec), and the key columns its passes use. ``scope`` limits the Stage 0 matches considered."""

    def __init__(self, name: str, src: pd.DataFrame, s0: pd.DataFrame, scope: pd.Index):
        assert isinstance(src.index, pd.RangeIndex) and isinstance(s0.index, pd.RangeIndex)
        self.name, self.src, self.s0, self.scope = name, src, s0, scope
        self.links: list[pd.DataFrame] = []
        self.taken_r: set = set()
        self.taken_l: set = set()
        self.ambiguous: dict = {}         # ri -> (method, [li, ...]) tied best candidates
        self.lost: dict = {}              # ri -> method (its best match went to a better-ranked row)
        self.unverified: dict = {}        # ri -> method (candidates failed both score and round)
        self.counts: dict = {}
        # positional arrays (both frames have a RangeIndex)
        self._sdate = src["date"].to_numpy(dtype="datetime64[ns]")
        self._ssets = src["sets"].to_numpy(dtype=object)
        self._spec = src["rspec"].to_numpy(dtype=object)
        self._tdate = s0["tdate"].to_numpy(dtype="datetime64[ns]")
        self._tsets = s0["sets"].to_numpy(dtype=object)
        self._round = s0["round"].to_numpy(dtype=object)
        self._qual = s0["qualifying"].to_numpy(dtype=bool)
        self._qrel = s0["qrel"].to_numpy(dtype="float64")
        self._end = s0["end_days"].to_numpy(dtype="int64")
        self._late = s0["round"].isin(LATE_ROUNDS).to_numpy(dtype=bool)

    # -- candidates ------------------------------------------------------------------------------
    def open_rows(self, rows=None) -> pd.Index:
        idx = self.src.index if rows is None else rows
        return idx[~idx.isin(list(self.taken_r)) & ~idx.isin(list(self.ambiguous))]

    def free_matches(self) -> pd.Index:
        return self.scope[~self.scope.isin(list(self.taken_l))]

    def gaps(self, c: pd.DataFrame) -> pd.DataFrame:
        ri, li = c["ri"].to_numpy(dtype="int64"), c["li"].to_numpy(dtype="int64")
        g = (self._sdate[ri] - self._tdate[li]) / np.timedelta64(1, "D")
        c = c.assign(gap=g)
        return c[c["gap"].notna()].assign(gap=lambda f: f["gap"].round().astype("int64"))

    def score(self, c: pd.DataFrame) -> pd.DataFrame:
        """sc (set scores), rd (round), in_exp (inside the expected span) and pick()'s dist."""
        if c.empty:
            return c.assign(sc=pd.Series(dtype="int64"), rd=pd.Series(dtype="int64"), dist=pd.Series(dtype="int64"),
                            in_exp=pd.Series(dtype=bool))
        ri, li = c["ri"].to_numpy(dtype="int64"), c["li"].to_numpy(dtype="int64")
        sc = np.fromiter((sets_agree(a, b) for a, b in zip(self._ssets[ri], self._tsets[li])), dtype="int64",
                         count=len(c))
        rd = np.fromiter((round_agree(p, r, q, (None if np.isnan(x) else int(x))) for p, r, q, x in
                          zip(self._spec[ri], self._round[li], self._qual[li], self._qrel[li])),
                         dtype="int64", count=len(c))
        gap = c["gap"].to_numpy()
        in_exp = expected(gap, self._qual[li], self._late[li], self._end[li])
        dist = np.abs(gap) + np.where(in_exp, 0, OUTSIDE_PENALTY)
        return c.assign(sc=sc, rd=rd, in_exp=in_exp, dist=dist)

    @staticmethod
    def accept(c: pd.DataFrame, need_span: bool = True) -> pd.Series:
        """Identical scores (any date in the window); or, inside the match's expected span, no scores to
        compare and a round that does not disagree, or different scores but an agreeing round. Scores
        and round both disagreeing: a different match. Without identical scores a date outside the span
        is more likely the same pair at a neighbouring event than this match. ``need_span`` False: a
        pass that matches the event itself (Infosys) or a source dated by event (TML) skips the span."""
        span = c["in_exp"].astype(bool) if need_span else pd.Series(True, index=c.index)
        return (c["sc"] == 2) | (span & (c["sc"] == 1) & (c["rd"] >= 1)) | (span & (c["sc"] == 0) & (c["rd"] == 2))

    # -- passes ----------------------------------------------------------------------------------
    def _keep(self, method: str, c: pd.DataFrame, window: bool = True, need_span: bool = True) -> int:
        """Score candidates (ri, li, gap), filter, pick() and record. Returns the number linked."""
        if window:
            c = c[(c["gap"] >= WINDOW[0]) & (c["gap"] <= WINDOW[1])]
        c = c.drop_duplicates(["ri", "li"])
        c = self.score(c)
        ok = self.accept(c, need_span)
        bad = pd.Index(c.loc[~ok, "ri"].unique()).difference(pd.Index(c.loc[ok, "ri"].unique()))
        for r in bad:
            self.unverified.setdefault(r, method)
        c = c[ok]
        kept, amb, lost = O.pick(c)
        if len(amb):
            best = c.sort_values(["ri", "sc", "rd", "dist"], ascending=[True, False, False, True])
            top = best.drop_duplicates("ri")[["ri", "sc", "rd", "dist"]]
            tied = c.merge(top, on=["ri", "sc", "rd", "dist"])
            tied = tied[tied["ri"].isin(amb)]
            for r, g in tied.groupby("ri"):
                self.ambiguous[r] = (method, sorted(g["li"].tolist()))
        for r in lost:
            self.lost.setdefault(r, method)
        kept = kept.assign(method=method).astype({"ri": "int64", "li": "int64"})
        kept = kept.merge(c[["ri", "li", "in_exp"]], on=["ri", "li"], how="left")
        self.links.append(kept)
        self.taken_r |= set(kept["ri"])
        self.taken_l |= set(kept["li"])
        for r in kept["ri"]:
            self.lost.pop(r, None)
            self.unverified.pop(r, None)
        self.counts[method] = {"candidates": int(len(c)), "linked": int(len(kept)), "ambiguous": int(len(amb)),
                               "lost_to_better_row": int(len(lost)), "linked_identical_scores": int((kept["sc"] == 2).sum()),
                               "linked_round_agrees": int((kept["rd"] == 2).sum())}
        log(f"  {self.name} / {method}: {len(kept):,} linked, {len(amb):,} ambiguous, {len(lost):,} lost")
        return len(kept)

    def pair_pass(self, method: str, src_long: pd.DataFrame, forms, extra_on=None, s0_long_: pd.DataFrame | None = None,
                  window: bool = True, need_span: bool = True) -> int:
        """Both players agree under one key form (ids, full names or abbreviated names)."""
        open_r = self.open_rows()
        sl = src_long[src_long["ri"].isin(open_r) & src_long["form"].isin(forms)]
        if sl.empty:
            self.counts[method] = {"candidates": 0, "linked": 0}
            return 0
        free = self.free_matches()
        tl = s0_long_ if s0_long_ is not None else s0_long(self.s0, free, forms=tuple(f for f in forms if f in "FAI"))
        tl = tl[tl["li"].isin(free) & tl["form"].isin(forms) & tl["key"].isin(set(sl["key"]))]
        sp = pairs_from_long(sl, "ri", "slot")
        tp = pairs_from_long(tl, "li", "side")
        on = ["tour", "form", "pair"]
        if extra_on:
            sp = sp.merge(self.src[extra_on], left_on="ri", right_index=True)
            tp = tp.merge(self.s0[extra_on], left_on="li", right_index=True)
            on = on + extra_on
        c = sp.merge(tp, on=on)[["ri", "li"]].drop_duplicates()
        return self._keep(method, self.gaps(c), window=window, need_span=need_span)

    def anchor_pass(self, method: str, src_long: pd.DataFrame, forms=("F", "I"), need_score: bool = True,
                    extra_on=None, window: bool = True, s0_long_: pd.DataFrame | None = None,
                    need_in_exp: bool = True) -> int:
        """One player identical, the other not (another spelling: the two other names must share a word),
        with a date inside the match's expected span (need_in_exp) and identical set scores (need_score)
        or, for a source without scores, an agreeing round; unique both ways."""
        open_r = self.open_rows()
        sl = src_long[src_long["ri"].isin(open_r) & src_long["form"].isin(forms)]
        free = self.free_matches()
        tl = s0_long_ if s0_long_ is not None else s0_long(self.s0, free, forms=tuple(f for f in forms if f in "FAI"))
        tl = tl[tl["li"].isin(free) & tl["form"].isin(forms) & tl["key"].isin(set(sl["key"]))]
        on = ["tour", "form", "key"]
        if extra_on:
            sl = sl.merge(self.src[extra_on], left_on="ri", right_index=True)
            tl = tl.merge(self.s0[extra_on], left_on="li", right_index=True)
            on = on + extra_on
        j = sl[["ri", "slot"] + on].merge(tl[["li", "side"] + on], on=on)
        if j.empty:
            self.counts[method] = {"candidates": 0, "linked": 0}
            return 0
        j = self.gaps(j[["ri", "li", "slot", "side"]].drop_duplicates())
        if window:
            j = j[(j["gap"] >= WINDOW[0]) & (j["gap"] <= WINDOW[1])]
        # the anchored slot/side; a candidate anchored on both sides would be a pair (left to pair passes)
        k = j.groupby(["ri", "li"]).agg(slot=("slot", "first"), side=("side", "first"), n_slot=("slot", "nunique"),
                                         gap=("gap", "first")).reset_index()
        k = k[k["n_slot"] == 1]
        c = self.score(k)
        ri, li = c["ri"].to_numpy(dtype="int64"), c["li"].to_numpy(dtype="int64")
        other_src = np.where(c["slot"].to_numpy() == 0, self.src["name2"].to_numpy(dtype=object)[ri],
                             self.src["name1"].to_numpy(dtype=object)[ri])
        other_s0 = np.where(c["side"].to_numpy() == 0, self.s0["b_name"].to_numpy(dtype=object)[li],
                            self.s0["a_name"].to_numpy(dtype=object)[li])
        share = np.array([share_word(a, b) for a, b in zip(other_src, other_s0)], dtype=bool)
        inexp = c["in_exp"].to_numpy() if need_in_exp else np.ones(len(c), dtype=bool)
        confirm = ((c["sc"] == 2) & (c["rd"] >= 1)) if need_score else (c["rd"] == 2)
        c = c[confirm.to_numpy() & inexp & share]
        one = c.groupby("ri")["li"].transform("nunique").eq(1) & c.groupby("li")["ri"].transform("nunique").eq(1)
        kept = c[one][["ri", "li", "gap", "sc", "rd", "dist", "in_exp"]].assign(method=method)
        self.links.append(kept.astype({"ri": "int64", "li": "int64"}))
        self.taken_r |= set(kept["ri"])
        self.taken_l |= set(kept["li"])
        for r in kept["ri"]:
            self.lost.pop(r, None)
            self.unverified.pop(r, None)
        self.counts[method] = {"candidates": int(len(c)), "linked": int(len(kept)),
                               "not_unique": int(c.loc[~one, "ri"].nunique())}
        log(f"  {self.name} / {method}: {len(kept):,} linked ({int(c.loc[~one, 'ri'].nunique()):,} not unique)")
        return len(kept)

    def direct(self, method: str, pairs: pd.DataFrame) -> int:
        """Links known outright (ri, li), e.g. a Stage 0 row that is the source row itself."""
        pairs = pairs[~pairs["ri"].isin(list(self.taken_r)) & ~pairs["li"].isin(list(self.taken_l))]
        pairs = pairs.drop_duplicates("ri").drop_duplicates("li")
        c = self.score(self.gaps(pairs[["ri", "li"]]))
        kept = c[["ri", "li", "gap", "sc", "rd", "dist", "in_exp"]].assign(method=method)
        self.links.append(kept.astype({"ri": "int64", "li": "int64"}))
        self.taken_r |= set(kept["ri"])
        self.taken_l |= set(kept["li"])
        self.counts[method] = {"linked": int(len(kept))}
        log(f"  {self.name} / {method}: {len(kept):,} linked")
        return len(kept)

    # -- learned ids -----------------------------------------------------------------------------
    def learn_ids(self, src_long: pd.DataFrame, pid_cols=("pid1", "pid2"), min_votes: int = 1) -> pd.Series:
        """Source player id -> Stage 0 player id, from the links made so far: each linked row's two
        players are matched to Stage 0's sides by a shared key; a source id that always meets one
        Stage 0 id (and at least ``min_votes`` times) is learned."""
        lk = self.result()
        if lk.empty:
            return pd.Series(dtype=object)
        sl = src_long[src_long["ri"].isin(lk["ri"])]
        tl = s0_long(self.s0, pd.Index(lk["li"].unique()))
        j = sl.merge(lk[["ri", "li"]], on="ri").merge(tl[["li", "side", "form", "key"]], on=["li", "form", "key"])
        j = j[["ri", "li", "slot", "side"]].drop_duplicates()
        n = j.groupby(["ri", "li", "slot"])["side"].transform("nunique")
        j = j[n == 1]
        pid = np.where(j["slot"].to_numpy() == 0, self.src.loc[j["ri"], pid_cols[0]].to_numpy(),
                       self.src.loc[j["ri"], pid_cols[1]].to_numpy())
        sid = np.where(j["side"].to_numpy() == 0, self.s0.loc[j["li"], "player_a_id"].to_numpy(),
                       self.s0.loc[j["li"], "player_b_id"].to_numpy())
        v = pd.DataFrame({"pid": pid, "sid": sid})
        v = v[(v["pid"].astype(str) != "") & v["pid"].notna()]
        votes = v.groupby(["pid", "sid"]).size().rename("n").reset_index()
        per = votes.groupby("pid")["sid"].nunique()
        good = votes[votes["pid"].isin(per.index[per == 1]) & (votes["n"] >= min_votes)]
        # a Stage 0 id claimed by two source ids is kept for both (the source may list one player twice)
        return good.set_index("pid")["sid"]

    # -- result ----------------------------------------------------------------------------------
    def result(self) -> pd.DataFrame:
        if not self.links:
            return pd.DataFrame(columns=["ri", "li", "gap", "sc", "rd", "dist", "in_exp", "method"])
        return pd.concat(self.links, ignore_index=True)

    def status(self) -> pd.Series:
        st = pd.Series("unlinked", index=self.src.index, dtype=object)
        st[list(self.unverified)] = "candidates_failed_checks"
        st[list(self.lost)] = "match_taken_by_better_row"
        st[list(self.ambiguous)] = "ambiguous"
        lk = self.result()
        st[lk["ri"].to_numpy()] = "linked"
        return st


def src_long_from(src: pd.DataFrame, f1: str | None = None, f2: str | None = None, a1: str | None = None,
                  a2: str | None = None, i1: str | None = None, i2: str | None = None,
                  extra: dict | None = None) -> pd.DataFrame:
    """(ri, tour, slot, form, key) from a source frame's key columns: F full keys (one per slot), A
    abbreviated keys (a tuple per slot), I Stage 0 ids; ``extra`` adds {form: (col1, col2)} single keys."""
    parts = []
    base = lambda slot: pd.DataFrame({"ri": src.index, "tour": src["tour"].to_numpy(), "slot": slot})  # noqa: E731
    for slot, f, a, i in ((0, f1, a1, i1), (1, f2, a2, i2)):
        if f:
            parts.append(base(slot).assign(form="F", key=src[f].to_numpy()))
        if a:
            parts.append(base(slot).assign(form="A", key=src[a].to_numpy()).explode("key"))
        if i:
            parts.append(base(slot).assign(form="I", key=src[i].to_numpy()))
    for form, (c1, c2) in (extra or {}).items():
        parts.append(base(0).assign(form=form, key=src[c1].to_numpy()))
        parts.append(base(1).assign(form=form, key=src[c2].to_numpy()))
    out = pd.concat(parts, ignore_index=True)
    out = out[out["key"].notna()]
    out = out[out["key"].astype(str) != ""]
    return out.drop_duplicates(["ri", "slot", "form", "key"]).reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# Output

OUT_COLS = ["match_id", "source", "source_key", "date_local", "start_utc", "date_basis", "link_method",
            "score_agrees", "round_agrees"]


def tri(v: pd.Series) -> pd.Series:
    return v.map({2: True, 0: False}).astype("boolean")


def region_of(tz: pd.Series) -> np.ndarray:
    """'Americas', 'Oceania', 'EurAfrAsia' or 'unknown' from an IANA zone."""
    z = tz.fillna("").astype(str)
    return np.select([z.eq(""), z.str.startswith("America/"), z.str.match(r"^(Australia|Pacific)/")],
                     ["unknown", "Americas", "Oceania"], "EurAfrAsia")


def local_dates(start_utc: pd.Series, tz: pd.Series) -> pd.Series:
    """The calendar day of each UTC instant in its row's zone (NaT where the zone or time is missing)."""
    out = pd.Series(pd.NaT, index=start_utc.index, dtype="datetime64[ns]")
    ok = start_utc.notna() & tz.notna()
    for zone, idx in start_utc[ok].groupby(tz[ok]).groups.items():
        out.loc[idx] = start_utc.loc[idx].dt.tz_convert(zone).dt.tz_localize(None).dt.normalize().astype("datetime64[ns]")
    return out


def write_links(frame: pd.DataFrame, path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    schema = pa.schema([("match_id", pa.string()), ("source", pa.string()), ("source_key", pa.string()),
                        ("date_local", pa.date32()), ("start_utc", pa.timestamp("us", tz="UTC")),
                        ("date_basis", pa.string()), ("link_method", pa.string()),
                        ("score_agrees", pa.bool_()), ("round_agrees", pa.bool_())])
    f = frame[OUT_COLS].copy()
    arrays = [
        pa.array(f["match_id"].astype(str).tolist(), pa.string()),
        pa.array(f["source"].astype(str).tolist(), pa.string()),
        pa.array(f["source_key"].astype(str).tolist(), pa.string()),
        pa.array([None if pd.isna(d) else pd.Timestamp(d).date() for d in f["date_local"]], pa.date32()),
        pa.array([None if pd.isna(t) else pd.Timestamp(t).tz_convert("UTC").to_pydatetime() for t in f["start_utc"]],
                 pa.timestamp("us", tz="UTC")),
        pa.array(f["date_basis"].astype(str).tolist(), pa.string()),
        pa.array(f["link_method"].astype(str).tolist(), pa.string()),
        pa.array([None if pd.isna(v) else bool(v) for v in f["score_agrees"]], pa.bool_()),
        pa.array([None if pd.isna(v) else bool(v) for v in f["round_agrees"]], pa.bool_()),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_arrays(arrays, schema=schema), path)
