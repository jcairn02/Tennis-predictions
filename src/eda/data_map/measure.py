"""Measure what data/ holds for every singles match since 2018: by tour, level, year and grain.

These are the data map's numbers. One list of matches (the *universe*) is built from the result
files. Every other source is then linked to it by the two players' surnames and the date, so a
match counts once however many sources hold it. A source row that links to nothing is a match the
result files lack, and joins the universe. Each match ends with its best grain:

    shot    every stroke of every rally (volunteer charts, Hawk-Eye ball tracking)
    point   every point in order, with who won it
    stats   match or set totals (aces, double faults, serve points won, break points ...)
    result  who won, and the score

and a status for where that grain comes from, read from the catalog (data/data_map.yaml):
``on_disk``, ``downloading`` (a scrape a Claude Code session is running now) or ``assumed``
(not downloaded; counted as held on the owner's instruction).

Singles only. Walkovers are left out: no point was played, so no finer grain can exist.
2026 runs to the last complete week (a Sunday) before the build. Where no source holds a
level's 2026 weeks at all, the missing matches are estimated from the same weeks of 2025.

Usage:
    ./python.sh src/eda/data_map/measure.py [--end YYYY-MM-DD] [--refresh]

Writes to data/studies/data_map/:
    coverage_cells.csv    one row per tour, level and year (tracked)
    coverage.json         the cells, per-source counts and the link report, for the map (tracked)
    matches.parquet       every match with its best grain and sources (gitignored)
    _cache/               extracted summaries of the slow sources (gitignored)
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = PROJECT_ROOT / "data"
DUMP = DATA / "dump"
RAW = DATA / "raw"
OUT = DATA / "studies" / "data_map"
CACHE = OUT / "_cache"
CATALOG = DATA / "data_map.yaml"
HANDOFF = RAW / "public_dump" / "atp_pipeline_handoff"

START = pd.Timestamp("2018-01-01")
FIRST_YEAR = 2018

GRAIN_RANK = {"result": 1, "stats": 2, "point": 3, "shot": 4}
STATUS_RANK = {"on_disk": 3, "downloading": 2, "assumed": 1}

LEVELS = [
    ("GS", "Grand Slam main draw"),
    ("GSQ", "Grand Slam qualifying"),
    ("FIN", "Tour Finals"),
    ("T1000", "Masters 1000 / WTA 1000"),
    ("T500", "ATP 500 / WTA 500"),
    ("T250", "ATP 250 / WTA 250"),
    ("TEAM", "Team events and Olympics"),
    ("TQ", "Tour-level qualifying"),
    ("CH", "Challenger / WTA 125 main draw"),
    ("CHQ", "Challenger / WTA 125 qualifying"),
    ("ITF", "ITF World Tennis Tour main draw"),
    ("ITFQ", "ITF qualifying"),
]
GRID_LEVELS = [code for code, _ in LEVELS]
QUAL_OF = {"GS": "GSQ", "T1000": "TQ", "T500": "TQ", "T250": "TQ", "FIN": "TQ", "CH": "CHQ", "ITF": "ITFQ"}
MAIN_OF = {"GSQ": "GS", "TQ": "T250", "CHQ": "CH", "ITFQ": "ITF"}
WTA_API_LEVELS = {"FIN", "T1000", "T500", "T250", "TQ", "CH", "CHQ"}   # what the WTA API lists
SLAM_PATTERNS = {"AO": "australian", "RG": "roland|french", "W": "wimbledon", "USO": "us open"}
SLAM_LEVELS = frozenset({"GS", "GSQ"})
# The editions' own name test: "us open" whole words only (Sackmann's "Doha Aus Open Qualies" holds it inside a word)
SLAM_NAMES = {"AO": r"australian|\baus open\b", "RG": r"roland|french", "W": r"wimbledon", "USO": r"\bus open\b"}
# Days before the main draw's first day an edition's matches may be dated (its qualifying): three weeks, six for the
# 2021 Australian Open, whose qualifying was played in Doha and Dubai four weeks early; and 16 days after it
SLAM_LEAD, SLAM_LEAD_EXCEPT, SLAM_TAIL = 21, {(2021, "AO"): 42}, 16

# Statuses used when the catalog is missing or does not name a dataset.
DEFAULT_STATUS = {"wta_events": "on_disk", "tdi": "on_disk", "wta_box": "on_disk"}


# --------------------------------------------------------------------------------------------
# Names, dates, levels

_PARTICLES = {"jr", "sr", "ii", "iii", "iv", "de", "da", "van", "von", "del", "der", "la", "le", "di", "dos"}


def _ascii(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def surname_key(name) -> str:
    """The last word of a player's name, lower-case ASCII: 'C. Alcaraz', 'Carlos Alcaraz' -> 'alcaraz'.

    Initials, suffixes and particles are skipped, and hyphens and apostrophes split words, so
    'F. Auger-Aliassime' and 'Felix Auger Aliassime' agree, and so do 'Surname F.' forms.
    """
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    return _surname(str(name))


@lru_cache(maxsize=None)
def _surname(name: str) -> str:
    words = _words(name)
    return words[-1] if words else ""


@lru_cache(maxsize=None)
def _words(name: str) -> tuple:
    words = [w for w in re.split(r"[^a-z]+", _ascii(name).lower()) if len(w) >= 2]
    return tuple([w for w in words if w not in _PARTICLES] or words)


@lru_cache(maxsize=None)
def same_player(a: str, b: str) -> bool:
    """Loose test that two spellings name one player, for a pair whose other surname already agrees.

    True when either name's last word is a word of the other ('Riske' / 'Alison Riske Amritraj',
    'Wu Tung-Lin' / 'Tung-Lin Wu'), or is a prefix of one of its words at four letters or more,
    as when a source cuts names at 20 characters ('F. MELIGENI RODRIGUE'). A shared first name
    alone ('Alex Molcan' / 'Alex de Minaur') is not enough.
    """
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    for key, other in ((wa[-1], wb), (wb[-1], wa)):
        if key in other:
            return True
        if len(key) >= 4 and any(w.startswith(key) and len(w) > len(key) for w in other):
            return True
    return False


@lru_cache(maxsize=None)
def _first_name(name: str) -> str:
    """A name's first name as written, lower-case ASCII: 'Carlos Alcaraz' -> 'carlos', 'C. Alcaraz' and
    'Alcaraz C.' -> 'c'; '' for a lone surname."""
    words = [w for w in re.split(r"[^a-z]+", _ascii(name).lower()) if w]
    if len(words) < 2:
        return ""
    return words[-1] if len(words[-1]) == 1 and len(words[0]) > 1 else words[0]


@lru_cache(maxsize=None)
def same_first_name(a: str, b: str) -> bool:
    """Whether two spellings can carry one first name: the same, an initial of the other, or the same
    first three letters ('Mariya' / 'Mariia'). Names written in another order agree when they share two
    words ('Wu Tung-Lin' / 'Tung-Lin Wu'), and a lone surname agrees with anything. Keeps 'Mary Liu' and
    'Claire Liu', or two sisters, apart; a married name keeps the first name ('Storm Sanders' / 'Storm Hunter')."""
    fa, fb = _first_name(a), _first_name(b)
    if not fa or not fb:
        return True
    if len(fa) == 1 or len(fb) == 1:
        return fa[0] == fb[0]
    n = min(3, len(fa), len(fb))
    return fa[:n] == fb[:n] or len(set(_words(a)) & set(_words(b))) >= 2


def pair_key(k1: pd.Series, k2: pd.Series) -> pd.Series:
    a, b = k1.fillna("").astype(str), k2.fillna("").astype(str)
    lo = pd.Series(np.where(a <= b, a, b), index=k1.index)
    hi = pd.Series(np.where(a <= b, b, a), index=k1.index)
    return (lo + "|" + hi).where((a != "") & (b != "") & (a != b), None)


def to_date(series: pd.Series, fmt: str | None = None) -> pd.Series:
    """Dates from strings. Without ``fmt`` each value is parsed on its own ('mixed'): sources mix
    '2024-08-19T15:00:00+00:00' with other forms, and a single inferred format would blank the rest."""
    if fmt:
        return pd.to_datetime(series, format=fmt, errors="coerce")
    return pd.to_datetime(series, errors="coerce", utc=True, format="mixed").dt.tz_localize(None)


def is_qual_round(rounds: pd.Series) -> pd.Series:
    r = rounds.fillna("").astype(str).str.strip().str.lower()
    return r.str.match(r"^q\d") | r.str.contains("qualif")


_ROUND_WORDS = {"round of 128": "R128", "round of 64": "R64", "round of 32": "R32", "round of 16": "R16",
                "quarterfinal": "QF", "quarterfinals": "QF", "quarter-finals": "QF", "semifinal": "SF",
                "semifinals": "SF", "semi-finals": "SF", "final": "F", "qualifying round 1": "Q1",
                "qualifying round 2": "Q2", "qualifying round 3": "Q3", "qualification round 1": "Q1",
                "qualification round 2": "Q2", "qualification final": "Q3"}
_ROUND_CODES = {"R128", "R64", "R32", "R16", "QF", "SF", "F", "Q1", "Q2", "Q3", "Q4"}


def canon_round(value) -> str | None:
    """'R32', 'Round of 32' -> 'R32'; None where a label does not say which round it is."""
    s = str(value or "").strip()
    s = _ROUND_WORDS.get(s.lower(), s.upper())
    return s if s in _ROUND_CODES else None


_SLAM_MAIN_ROUNDS = {"1": "R128", "2": "R64", "3": "R32", "4": "R16", "5": "QF", "6": "SF", "7": "F",
                     "Q": "QF", "S": "SF", "F": "F", "1st round": "R128", "2nd round": "R64", "3rd round": "R32",
                     "4th round": "R16", "quarterfinals": "QF", "semifinals": "SF", "final": "F"}
_SLAM_QUAL_ROUNDS = {"1": "Q1", "2": "Q2", "3": "Q3", "1st round": "Q1", "2nd round": "Q2", "final round": "Q3"}


def slam_round(code, qual: bool) -> str | None:
    """A Grand Slam round in the Sackmann form: IBM round codes ('1'..'4', 'Q', 'S', 'F') or AO names."""
    key = str(code or "").strip()
    table = _SLAM_QUAL_ROUNDS if qual else _SLAM_MAIN_ROUNDS
    return table.get(key, table.get(key.lower()))


_TEAM_NAMES = re.compile(r"united cup|atp cup|laver cup|davis cup|billie jean king|bjk cup|fed cup|olympic|hopman")


def tour_level_atp(code: str, name: str) -> str:
    n = (name or "").lower()
    if _TEAM_NAMES.search(n):          # Tennis My Life files some United Cup ties under a tour level
        return "TEAM"
    if code in ("M", "1000"):
        # Tennis My Life files Winston-Salem 2026 under 'M'; the nine Masters are all named '... Masters'
        return "T1000" if "masters" in n else "T250"
    simple = {"G": "GS", "500": "T500", "250": "T250", "F": "FIN", "D": "TEAM", "O": "TEAM", "C": "CH"}
    if code in simple:
        return simple[code]
    if code == "A":
        if "next" in n and "gen" in n:
            return "FIN"
        if any(k in n for k in ("atp cup", "united cup", "laver")):
            return "TEAM"
        return "T250"
    return "OTHER"


def tour_level_wta(code: str, name: str) -> str:
    n = (name or "").lower()
    if _TEAM_NAMES.search(n):
        return "TEAM"
    simple = {"G": "GS", "PM": "T1000", "P5": "T1000", "1000": "T1000", "P": "T500", "500": "T500",
              "I": "T250", "250": "T250", "F": "FIN", "D": "TEAM", "O": "TEAM", "C": "CH"}
    if code in simple:
        return simple[code]
    if code == "A":
        return "TEAM" if "united cup" in n else "T250"
    if code == "W":
        return "CH" if "125" in n else "T250"
    if re.match(r"^\d", code or "") or code in ("35+H", "50+H"):
        return "ITF"
    return "OTHER"


def to_qual(level):
    return QUAL_OF.get(level, level) if isinstance(level, str) else level


def last_complete_sunday(today: datetime) -> pd.Timestamp:
    t = pd.Timestamp(today.date())
    back = (t.weekday() + 1) % 7 or 7
    return t - pd.Timedelta(days=back)


def catalog_status() -> dict:
    """Status of each dataset the measurement treats specially, from data/data_map.yaml."""
    status = dict(DEFAULT_STATUS)
    if CATALOG.exists():
        import yaml  # PyYAML; declared in environment.yml
        doc = yaml.safe_load(CATALOG.read_text(encoding="utf-8")) or {}
        for ds in doc.get("datasets") or []:
            for mid in ds.get("measured_as") or []:
                if isinstance(mid, dict):
                    status[mid["id"]] = mid.get("status", ds.get("status"))
                else:
                    status[mid] = ds.get("status")
    return status


# --------------------------------------------------------------------------------------------
# The universe and linking

def slam_rows(rows: pd.DataFrame) -> pd.Series:
    """Which rows are Grand Slam rows: level GS or GSQ, or no level and a tournament name that names a Slam (api-tennis
    gives its Slam rows none)."""
    level = rows["level"] if "level" in rows else pd.Series(None, index=rows.index, dtype=object)
    names = rows["tname"].fillna("").astype(str).str.lower() if "tname" in rows else pd.Series("", index=rows.index)
    unknown = level.isna() | level.eq("OTHER")
    return level.isin(SLAM_LEVELS) | (unknown & names.str.contains("|".join(SLAM_NAMES.values())))


def slam_editions(frame: pd.DataFrame, starts: dict) -> pd.Series:
    """The Grand Slam ('AO', 'RG', 'W', 'USO') of each Grand Slam row (d, year[, slam, tname]): its own ``slam``,
    else the Slam its tournament name names, else the edition whose window holds its date (``SLAM_LEAD`` days before
    the main draw's first day to ``SLAM_TAIL`` after it), the nearest first day first. None outside every window."""
    out = frame["slam"].astype(object) if "slam" in frame else pd.Series(None, index=frame.index, dtype=object)
    names = frame["tname"].fillna("").astype(str).str.lower() if "tname" in frame else pd.Series("", index=frame.index)
    for slam, pattern in SLAM_NAMES.items():
        out = out.where(out.notna() | ~names.str.contains(pattern), slam)
    todo = out.isna()
    if todo.any():
        by_year: dict[int, list] = {}
        for (year, slam), start in starts.items():
            by_year.setdefault(int(year), []).append((slam, pd.Timestamp(start)))
        guess = []
        for d, year in zip(frame.loc[todo, "d"], frame.loc[todo, "year"]):
            best = None
            for slam, start in by_year.get(int(year), []) if pd.notna(year) and pd.notna(d) else []:
                lead = SLAM_LEAD_EXCEPT.get((int(year), slam), SLAM_LEAD)
                if start - pd.Timedelta(days=lead) <= d <= start + pd.Timedelta(days=SLAM_TAIL):
                    gap = abs((d - start).days)
                    if best is None or gap < best[0]:
                        best = (gap, slam)
            guess.append(best[1] if best else None)
        out[todo] = guess
    return out


@lru_cache(maxsize=None)
def near_surname(a: str, b: str) -> bool:
    """Two spellings of one surname a letter apart, both of five letters or more, and first names agreeing: the
    transliterations of 'Wuerth' / 'Wurth', 'Goerges' / 'Görges', 'Sobolieva' / 'Soboleva'."""
    x, y = surname_key(a), surname_key(b)
    if x == y or min(len(x), len(y)) < 5 or abs(len(x) - len(y)) > 1 or not same_first_name(a, b):
        return False
    if len(x) == len(y):
        return sum(c != d for c, d in zip(x, y)) == 1
    short, long_ = (x, y) if len(x) < len(y) else (y, x)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def slam_place(n1: str, n2: str, rnd, level, d, known: list) -> float:
    """The uid among ``known`` (uid, name1, name2, rnd, level, d: Grand Slam matches of one edition and tour) that a
    row of that edition is, or NaN.

    Best: both players the same player in one orientation (``same_player``: a surname of one is a word of the other,
    so 'Cori Gauff' / 'Coco Gauff' and 'Mayar Sherif' / 'Mayar Sherif Ahmed Abdelaziz' agree, while first names alone
    never do: 'Valentin Royer v Marc Polmans' is not 'Valentin Vacherot v Marc-Andrea Huesler'), with both first
    names agreeing, or the same round given by both (a pair meets once per round, so a nickname cannot mislead there).
    Next: both the same player, first names unread, since a pair meets once in an edition. Sources hide first names
    in surnames ('Sherif Ahmed Abdelaziz' and 'Burillo Escorihuela' in the WTA's lists, 'Von Deichmann'), initials
    ('C. J. Barranco') and surname-first forms ('H. Hsu Yu'). 'Xiyu Wang' and 'Yafan Wang' are the same player here,
    so a namesake's match against the same opponent can be taken when the row's own is missing, as the generic first
    pass does everywhere else in the map; when both are known, the first name decides. Then: a surname spelt a
    letter apart (``near_surname``: 'Wuerth' / 'Wurth', 'J. Görges' / 'Julia Goerges', 'Sobolieva' / 'Soboleva'),
    with the first names agreeing and the other player the same. Last: a changed
    surname, with the same round and draw, both first names the same and one surname the same ('Denisa Allertova' /
    'Denisa Satralova'). A pair meets once in an edition, so the round and the draw (main or qualifying) only rank
    within a tier: sources mislabel both (SofaScore's copy calls Wimbledon 2022's second qualifying round the third and
    files 342 qualifying matches of 2021-2024 as main draw; the Australian Open's archived draws call the qualifying's
    last round 'Final'). Within a tier: the same round first, then the same draw, the most name words shared, the
    nearest date, the lowest uid."""
    rnd = rnd if isinstance(rnd, str) else None
    best, best_key = np.nan, None
    for uid, a, b, r, lv, du in known:
        r = r if isinstance(r, str) else None
        same_round = rnd is not None and rnd == r
        agree = 2 if same_round else (1 if rnd is None or r is None else 0)
        near = -abs((d - du).days) if pd.notna(d) and pd.notna(du) else -9999
        for x, y in ((a, b), (b, a)):
            p1, p2 = same_player(n1, x), same_player(n2, y)
            f1, f2 = same_first_name(n1, x), same_first_name(n2, y)
            if p1 and p2 and (same_round or (f1 and f2)):
                key = (3, agree, lv == level, name_word_fit(n1, x) + name_word_fit(n2, y), near, -uid)
            elif p1 and p2:
                key = (2, agree, lv == level, name_word_fit(n1, x) + name_word_fit(n2, y), near, -uid)
            elif (p1 or near_surname(n1, x)) and (p2 or near_surname(n2, y)):
                key = (1, agree, lv == level, name_word_fit(n1, x) + name_word_fit(n2, y), near, -uid)
            elif same_round and lv == level and f1 and f2 and (p1 or p2):
                key = (0, agree, True, 0, near, -uid)
            else:
                continue
            if best_key is None or key > best_key:
                best, best_key = uid, key
    return best


MATCH_COLUMNS = ["uid", "tour", "level", "draw", "year", "d", "pair", "k1", "k2", "rnd", "name1", "name2",
                 "tname", "creator"]


class Universe:
    """Every match known to the map, and which source holds it at which grain."""

    def __init__(self, end: pd.Timestamp):
        self.end = end
        self.matches = pd.DataFrame({c: pd.Series(dtype="object") for c in MATCH_COLUMNS})
        self.matches["d"] = pd.Series(dtype="datetime64[ns]")
        self.cover: list[pd.DataFrame] = []
        self.report: dict[str, dict] = {}
        self._next = 0

    def _prepare(self, rows: pd.DataFrame) -> pd.DataFrame:
        rows = rows.copy()
        rows["d"] = pd.to_datetime(rows["d"], errors="coerce").astype("datetime64[ns]")
        rows["name1"] = rows["name1"].fillna("").astype(str)
        rows["name2"] = rows["name2"].fillna("").astype(str)
        rows["k1"], rows["k2"] = rows["name1"].map(surname_key), rows["name2"].map(surname_key)
        rows["pair"] = pair_key(rows["k1"], rows["k2"])
        rows["rnd"] = rows["round"].map(canon_round) if "round" in rows else None
        if "year" not in rows:
            rows["year"] = rows["d"].dt.year
        rows["year"] = pd.to_numeric(rows["year"], errors="coerce")
        keep = rows["pair"].notna() & rows["d"].notna() & rows["year"].between(FIRST_YEAR, self.end.year)
        keep &= (rows["d"] >= START - pd.Timedelta(days=14)) & (rows["d"] <= self.end + pd.Timedelta(days=1))
        rows = rows[keep].copy()
        rows["rid"] = np.arange(len(rows))
        return rows

    def link(self, rows: pd.DataFrame, lo: int = -10, hi: int = 21) -> pd.Series:
        """uid of the universe match each row is, or NaN.

        A Grand Slam row (level GS or GSQ) is placed among the Grand Slam matches of its own edition only
        (``_link_slam``), and a row of another known level never joins a Grand Slam match (16 Oct 2026). The
        generic passes work on surnames and dates alone, and across levels they gave a Slam's match to the same
        pair's meeting at another event in the window (the 2021 Australian Open quarter-final Djokovic-Zverev to
        their ATP Cup match a week earlier) or the reverse (the Challenger of the week after to a US Open qualifying
        match); within a Slam they missed late rounds one file dates by the event's start and another by the day
        played, and spellings such as 'Cori Gauff'. Rows of no known level keep the generic passes over every match.
        """
        out = pd.Series(np.nan, index=rows.index)
        if rows.empty or self.matches.empty:
            return out
        level = rows["level"] if "level" in rows else pd.Series(None, index=rows.index, dtype=object)
        at_slam = slam_rows(rows)
        other = level.notna() & ~level.eq("OTHER") & ~at_slam
        slam_matches = self.matches["level"].isin(SLAM_LEVELS)
        if at_slam.any():
            placed, outside = self._link_slam(rows[at_slam])
            out[at_slam] = placed
            if outside.any():             # no edition window holds it: the generic passes, among Slam matches only
                rest = rows[at_slam][outside.to_numpy()]
                out[rest.index] = self._link_generic(rest, self.matches[slam_matches], lo, hi)
        if other.any():
            out[other] = self._link_generic(rows[other], self.matches[~slam_matches], lo, hi)
        free = ~at_slam & ~other
        if free.any():
            out[free] = self._link_generic(rows[free], self.matches, lo, hi)
        return out

    def _link_slam(self, rows: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """(uid, outside) of Grand Slam rows: ``slam_place`` among the known Grand Slam matches of the same edition
        (``slam_editions``) and tour, NaN where none is the row's match (one the universe lacks, which then joins it
        instead of borrowing another event's); ``outside`` marks the rows no edition window holds."""
        out = pd.Series(np.nan, index=rows.index)
        starts = slam_starts(self.matches)
        editions = slam_editions(rows, starts)
        m = self.matches[self.matches["level"].isin(SLAM_LEVELS)]
        m = m.assign(slam=slam_editions(m, starts).to_numpy())
        for (slam, tour, year), group in rows.assign(slam=editions).dropna(subset=["slam"]).groupby(
                ["slam", "tour", "year"]):
            cands = m[m["slam"].eq(slam) & m["tour"].eq(tour) & m["year"].eq(year)]
            known = list(zip(cands["uid"], cands["name1"].astype(str), cands["name2"].astype(str), cands["rnd"],
                             cands["level"], cands["d"]))
            index: dict[str, list[int]] = {}       # a word's first four letters -> candidates (same_player needs one)
            for k, (_, a, b, *_) in enumerate(known):
                for w in set(_words(a)) | set(_words(b)):
                    index.setdefault(w[:4], []).append(k)
            for i, n1, n2, rnd, lv, d in zip(group.index, group["name1"], group["name2"], group["rnd"],
                                             group["level"], group["d"]):
                near = sorted({k for w in set(_words(n1)) | set(_words(n2)) for k in index.get(w[:4], ())})
                out[i] = slam_place(n1, n2, rnd, lv, d, [known[k] for k in near])
        return out, editions.isna()

    def _slam_repeats(self, new: pd.DataFrame) -> list:
        """Index of the Grand Slam rows of ``new`` (rows about to join the universe) that another of them already is
        (``slam_place`` within the edition and tour, in order): left out of the new matches, they are then linked to
        the one they repeat."""
        slam = new[new["level"].isin(SLAM_LEVELS)]
        if len(slam) < 2:
            return []
        frames = [f for f in (self.matches, slam) if not f.empty]
        starts = slam_starts(pd.concat(frames, ignore_index=True)[["level", "tname", "year", "d"]])
        repeats = []
        for _, group in slam.assign(slam=slam_editions(slam, starts)).dropna(subset=["slam"]).groupby(
                ["slam", "tour", "year"]):
            kept: list = []
            index: dict[str, list[int]] = {}
            for i, n1, n2, rnd, lv, d in zip(group.index, group["name1"], group["name2"], group["rnd"],
                                             group["level"], group["d"]):
                prefixes = {w[:4] for w in set(_words(n1)) | set(_words(n2))}
                near = sorted({k for p in prefixes for k in index.get(p, ())})
                if near and pd.notna(slam_place(n1, n2, rnd, lv, d, [kept[k] for k in near])):
                    repeats.append(i)
                    continue
                for p in prefixes:
                    index.setdefault(p, []).append(len(kept))
                kept.append((len(kept), n1, n2, rnd, lv, d))
        return repeats

    def _link_generic(self, rows: pd.DataFrame, matches: pd.DataFrame, lo: int, hi: int) -> pd.Series:
        """uid among ``matches`` of each row, or NaN: the generic passes.

        First pass: same tour, same pair of surname keys, date in the window. Second pass, for the
        rest: one surname key agrees and the other two names pass ``same_player`` (married names,
        names cut short, surname-first order). The window allows for one source dating a match by
        its tournament's first day and another by the day it was played (a Slam final is 14 days
        after the start; qualifying comes before it). The second and third passes also need both
        players' first names to agree (``same_first_name``): a surname key alone is shared by sisters
        and by many players at the ITF events of one week.
        """
        if rows.empty or matches.empty:
            return pd.Series(np.nan, index=rows.index)
        rows = rows.copy()
        # Grand Slam qualifying can be dated weeks away from the main draw, either way (the 2021
        # Australian Open's was played in Doha and Dubai four weeks early; one source dates it by its own
        # week, another by the main event's), and a Slam has one match per player per round
        slam = rows["level"].isin(["GS", "GSQ"]) if "level" in rows else pd.Series(False, index=rows.index)
        gsq = rows.get("level", pd.Series(None, index=rows.index)).eq("GSQ")
        rows["lo"], rows["hi"] = np.where(gsq, -40, lo), np.where(gsq, 40, hi)
        right = matches[["uid", "tour", "pair", "d", "draw"]].rename(columns={"d": "d_u", "draw": "draw_u"})
        cand = rows[["rid", "tour", "pair", "d", "draw", "lo", "hi"]].merge(right, on=["tour", "pair"])
        found = self._best(cand, lo, hi)
        todo = rows[~rows["rid"].isin(found.index)]
        if not todo.empty:
            keys = ["rid", "tour", "d", "draw"]
            left = pd.concat([todo[keys].assign(key=todo["k1"], own=todo["name1"], other=todo["name2"]),
                              todo[keys].assign(key=todo["k2"], own=todo["name2"], other=todo["name1"])])
            m = matches
            ukeys = ["uid", "tour", "d", "draw"]
            right = pd.concat([m[ukeys].assign(key=m["k1"], uown=m["name1"], uother=m["name2"]),
                               m[ukeys].assign(key=m["k2"], uown=m["name2"], uother=m["name1"])])
            cand = left.merge(right.rename(columns={"d": "d_u", "draw": "draw_u"}), on=["tour", "key"])
            delta = (cand["d"] - cand["d_u"]).dt.days
            cand = cand[(delta >= lo) & (delta <= hi)]
            if not cand.empty:
                ok = [same_player(a, b) and same_first_name(a, b) and same_first_name(c, d)
                      for a, b, c, d in zip(cand["other"], cand["uother"], cand["own"], cand["uown"])]
                found = pd.concat([found, self._best(cand[ok], lo, hi)])
        # Third pass, for a player who changed surname ('D. Gavrilova', later 'Daria Saville'): the
        # other player, the same round, and the same tournament week (within three days).
        # At a Grand Slam the full window is safe (Slams are weeks apart); elsewhere, the same week.
        todo = rows[~rows["rid"].isin(found.index) & rows["rnd"].notna()]
        if not todo.empty:
            keys = ["rid", "tour", "d", "draw", "rnd", "lo", "hi"]
            left = pd.concat([todo[keys].assign(key=todo["k1"], own=todo["name1"], other=todo["name2"]),
                              todo[keys].assign(key=todo["k2"], own=todo["name2"], other=todo["name1"])])
            m = matches[matches["rnd"].notna()]
            ukeys = ["uid", "tour", "d", "draw", "rnd"]
            right = pd.concat([m[ukeys].assign(key=m["k1"], uown=m["name1"], uother=m["name2"]),
                               m[ukeys].assign(key=m["k2"], uown=m["name2"], uother=m["name1"])])
            cand = left.merge(right.rename(columns={"d": "d_u", "draw": "draw_u"}), on=["tour", "key", "rnd"])
            delta = (cand["d"] - cand["d_u"]).dt.days.to_numpy()
            at_slam = cand["rid"].isin(rows.loc[slam, "rid"]).to_numpy()
            near = np.where(at_slam, (delta >= cand["lo"].to_numpy()) & (delta <= cand["hi"].to_numpy()),
                            np.abs(delta) <= 3)
            cand, at_slam = cand[near], at_slam[near]
            # the player whose surname agrees must keep a first name; the other may have changed surname
            ok = np.array([same_first_name(a, b) and (same_first_name(c, d) or same_player(c, d))
                           for a, b, c, d in zip(cand["own"], cand["uown"], cand["other"], cand["uother"])], dtype=bool)
            found = pd.concat([found, self._best(cand[at_slam & ok], lo, hi),
                               self._best(cand[~at_slam & ok].drop(columns=["lo", "hi"]), -3, 3)])
            found = found[~found.index.duplicated()]
        return rows["rid"].map(found)

    @staticmethod
    def _best(cand: pd.DataFrame, lo: int, hi: int) -> pd.Series:
        if cand.empty:
            return pd.Series(dtype="float64")
        delta = (cand["d"] - cand["d_u"]).dt.days
        low = cand["lo"] if "lo" in cand else lo
        high = cand["hi"] if "hi" in cand else hi
        inside = (delta >= low) & (delta <= high)
        cand, delta = cand[inside].copy(), delta[inside]
        mismatch = cand["draw"].notna() & cand["draw_u"].notna() & (cand["draw"] != cand["draw_u"])
        cand["score"] = (delta - 3).abs() + np.where(mismatch, 40, 0)
        return cand.sort_values(["rid", "score"]).drop_duplicates("rid").set_index("rid")["uid"]

    def add(self, src: str, rows: pd.DataFrame, grain="grain", status="on_disk", add_new: bool = True,
            group: str | None = None) -> pd.DataFrame:
        """Link rows (tour, d, name1, name2, level, draw[, year, round, group]) and record their grain.

        ``grain`` and ``status`` are column names or constants. Unlinked rows join the universe
        when ``add_new``. Their level is the row's own, else the level most of the same ``group``
        (a tournament or tier id) linked to, else the row's ``level_fallback``, else 'OTHER'.
        """
        n_in = len(rows)
        rows = self._prepare(rows)
        for col, val in (("grain", grain), ("status", status)):
            rows[col] = rows[val] if isinstance(val, str) and val in rows else val
        for col in ("level", "draw", "tname", "round", "level_fallback"):
            if col not in rows:
                rows[col] = None
        # rows a source-specific key has already placed (e.g. ATP tournament id and player codes)
        preset = rows["preset_uid"] if "preset_uid" in rows else pd.Series(np.nan, index=rows.index)
        rows["uid"] = preset
        rest = rows["uid"].isna()
        if rest.any():
            rows.loc[rest, "uid"] = self.link(rows[rest])
        linked = rows["uid"].notna()
        if add_new and (~linked).any():
            new = rows[~linked].copy()
            if group and group in rows:
                lv = rows.loc[linked, [group, "uid"]].merge(self.matches[["uid", "level"]], on="uid")
                lv["level"] = lv["level"].map(lambda x: MAIN_OF.get(x, x))
                # the Finals' own matches are all in the result files; anything else filed under
                # a Finals tournament id (a wildcard play-off, say) is not a Finals match
                lv = lv[lv["level"].isin(GRID_LEVELS) & ~lv["level"].eq("FIN")]
                if not lv.empty:
                    majority = lv.groupby(group)["level"].agg(lambda s: s.value_counts().index[0])
                    guess = new[group].map(majority)
                    guess = guess.where(~new["draw"].eq("qual"), guess.map(to_qual))
                    new["level"] = new["level"].where(new["level"].notna(), guess)
            fallback = new["level_fallback"].where(~new["draw"].eq("qual"), new["level_fallback"].map(to_qual))
            new["level"] = new["level"].where(new["level"].notna(), fallback).fillna("OTHER")
            # one match listed twice in the source: same pair, same round, within five days; at a Grand Slam, also
            # under two spellings (the WTA website's 'Viktoriya Tomova' / 'Viktoria Tomova-Traycheva')
            new = new.sort_values(["tour", "pair", "d"])
            gap = new.groupby(["tour", "pair", new["round"].fillna("")])["d"].diff().dt.days
            new = new[gap.isna() | (gap > 5)].copy()
            new = new.drop(index=self._slam_repeats(new))
            new["uid"] = np.arange(self._next, self._next + len(new))
            self._next += len(new)
            new["creator"] = src
            frames = [f for f in (self.matches, new[MATCH_COLUMNS]) if not f.empty]
            self.matches = pd.concat(frames, ignore_index=True)
            self.matches["uid"] = self.matches["uid"].astype("int64")
            self.matches["year"] = pd.to_numeric(self.matches["year"]).astype("int64")
            self.matches["d"] = pd.to_datetime(self.matches["d"])
            rows.loc[new.index, "uid"] = new["uid"]
            dup = rows["uid"].isna()
            if dup.any():
                rows.loc[dup, "uid"] = self.link(rows[dup])
        held = rows[rows["uid"].notna()]
        self.cover.append(pd.DataFrame({"uid": held["uid"].astype("int64"), "src": src,
                                        "grain": held["grain"], "status": held["status"]}))
        self.report[src] = {"rows_read": int(n_in), "rows_in_window": int(len(rows)),
                            "linked_to_known_match": int(linked.sum()),
                            "added_as_new_match": int(rows["uid"].notna().sum() - linked.sum()),
                            "not_placed": int(rows["uid"].isna().sum())}
        return rows

    def credit(self, src: str, uids, grain: str, status: str, note: str | None = None) -> int:
        """Credit universe matches directly (in-progress or assumed batches, keyed by scope)."""
        uids = pd.Series(list(uids), dtype="int64").drop_duplicates()
        self.cover.append(pd.DataFrame({"uid": uids, "src": src, "grain": grain, "status": status}))
        rep = self.report.setdefault(src, {"credited_matches": 0})
        rep["credited_matches"] = rep.get("credited_matches", 0) + int(len(uids))
        if note:
            rep["note"] = note
        return int(len(uids))


# --------------------------------------------------------------------------------------------
# Result sources (they build the universe)

def _year_of(path: Path) -> int | None:
    m = re.search(r"(19|20)\d{2}", path.name)
    return int(m.group(0)) if m else None


def _read_years(pattern: str, columns: list[str] | None = None) -> pd.DataFrame:
    frames = []
    for path in sorted(DUMP.glob(pattern)):
        year = _year_of(path)
        if year is None or year < FIRST_YEAR:
            continue
        frame = pd.read_parquet(path, columns=columns)
        frame["season"] = year
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


MATCH_COLS = ["tourney_id", "tourney_name", "tourney_level", "tourney_date", "round", "winner_id", "winner_name",
              "loser_id", "loser_name", "score", "w_svpt"]


def id_key(season: pd.Series, tournament: pd.Series, id1: pd.Series, id2: pd.Series) -> pd.Series:
    """'2023_339_A0E2_S0AG': season, ATP tournament id and the two ATP player codes (sorted)."""
    a, b = id1.fillna("").astype(str), id2.fillna("").astype(str)
    lo = pd.Series(np.where(a <= b, a, b), index=a.index)
    hi = pd.Series(np.where(a <= b, b, a), index=a.index)
    return season.astype(str) + "_" + tournament.fillna("").astype(str) + "_" + lo + "_" + hi


def _match_rows(frame: pd.DataFrame, tour: str, level_fn) -> pd.DataFrame:
    score = frame["score"].fillna("").astype(str)
    walkover = score.str.contains(r"W/O|walkover", case=False, regex=True) | score.str.strip().eq("")
    frame = frame[~walkover]
    out = pd.DataFrame({
        "tour": tour,
        "d": to_date(frame["tourney_date"], "%Y%m%d"),
        "year": frame["season"],
        "name1": frame["winner_name"], "name2": frame["loser_name"],
        "tname": frame["tourney_name"], "round": frame["round"],
        "code": frame["tourney_level"].fillna("").astype(str),
        "draw": np.where(is_qual_round(frame["round"]), "qual", "main"),
        "grain": np.where(pd.to_numeric(frame["w_svpt"], errors="coerce").fillna(0) > 0, "stats", "result"),
        # for repair_tml_dates: the score and the tournament id ('2018-06486' and '2018-6486' agree)
        "score": frame["score"].fillna("").astype(str),
        "tid": frame["tourney_id"].fillna("").astype(str).str.replace(r"-0+(\d)", r"-\1", regex=True),
    })
    out["level"] = [level_fn(c, n) for c, n in zip(out["code"], out["tname"])]
    q = out["draw"].eq("qual")
    out.loc[q, "level"] = out.loc[q, "level"].map(to_qual)
    # Tennis My Life's ids are the ATP's own (tournament '2023-339', players 'S0AG'), as Infosys uses
    out["atp_key"] = id_key(frame["season"], frame["tourney_id"].fillna("").astype(str).str.partition("-")[2],
                            frame["winner_id"], frame["loser_id"])
    return out


def load_tml() -> pd.DataFrame:
    parts = [_match_rows(_read_years("matches/tennis_my_life/atp_main/*.parquet", MATCH_COLS), "M", tour_level_atp)]
    q = _read_years("matches/tennis_my_life/atp_qualifying/*.parquet", MATCH_COLS)
    qr = _match_rows(q, "M", tour_level_atp)
    qr["draw"] = "qual"
    qr["level"] = np.where(qr["code"].eq("G"), "GSQ", "TQ")
    parts.append(qr)
    parts.append(_match_rows(_read_years("matches/tennis_my_life/atp_challenger/*.parquet", MATCH_COLS), "M",
                             tour_level_atp))
    parts.append(_match_rows(_read_years("matches/tennis_my_life/wta_main/*.parquet", MATCH_COLS), "W",
                             tour_level_wta))
    for name, tour, fn in (("ongoing_tourneys", "M", tour_level_atp),
                           ("challenger_ongoing_tourneys", "M", tour_level_atp),
                           ("wta_ongoing_tourneys", "W", tour_level_wta)):
        path = DUMP / "matches" / "tennis_my_life" / "ongoing" / f"{name}.parquet"
        if path.exists():
            frame = pd.read_parquet(path, columns=MATCH_COLS)
            frame["season"] = pd.to_numeric(frame["tourney_date"].str[:4], errors="coerce")
            parts.append(_match_rows(frame, tour, fn))
    rows = pd.concat(parts, ignore_index=True)
    return rows[rows["d"] >= START - pd.Timedelta(days=14)]


def load_sackmann(tml_levels: dict) -> pd.DataFrame:
    parts = []
    for pattern, tour, fn in (("matches/sackmann_archive/atp/atp_matches_20[0-9][0-9].parquet", "M", tour_level_atp),
                              ("matches/sackmann_archive/atp/atp_matches_qual_chall_*.parquet", "M", tour_level_atp),
                              ("matches/sackmann_archive/wta/wta_matches_20[0-9][0-9].parquet", "W", tour_level_wta),
                              ("matches/sackmann_archive/wta/wta_matches_qual_itf_*.parquet", "W", tour_level_wta)):
        rows = _match_rows(_read_years(pattern, MATCH_COLS), tour, fn)
        # Sackmann does not split 250 from 500, and its WTA codes blur 500 and 1000: take the level
        # Tennis My Life gives the same tournament in the same season, where there is one.
        key = list(zip(rows["tour"], rows["year"], rows["tname"].str.lower().str.strip()))
        known = pd.Series([tml_levels.get(k) for k in key], index=rows.index)
        fix = known.notna() & ~rows["level"].isin(["CH", "CHQ", "ITF", "ITFQ"])
        rows.loc[fix & rows["draw"].eq("main"), "level"] = known
        rows.loc[fix & rows["draw"].eq("qual"), "level"] = known.map(to_qual)
        parts.append(rows)
    fut = _match_rows(_read_years("matches/sackmann_archive/atp/atp_matches_futures_*.parquet", MATCH_COLS), "M",
                      lambda c, n: "ITF")
    fut.loc[fut["draw"].eq("qual"), "level"] = "ITFQ"
    parts.append(fut)
    return pd.concat(parts, ignore_index=True)


# words a tournament name shares with too many others to tell two events apart
_EVENT_GENERIC = frozenset({"atp", "wta", "itf", "challenger", "challengers", "open", "masters", "cup", "the", "and",
                            "tennis", "international", "championships", "championship", "trophy", "men", "mens",
                            "women", "womens", "tour", "series", "qualifying", "qualies", "del", "des"})
REDATE_DAYS = (10, 366)   # a twin more than 10 days and at most a year away from Tennis My Life's date


@lru_cache(maxsize=None)
def event_words(name: str) -> frozenset:
    """A tournament name's distinctive words: 'ATP Tenerife 3 Challenger' and 'Tenerife 1' -> {'tenerife'}."""
    return frozenset(w for w in re.split(r"[^a-z]+", _ascii(str(name or "")).lower())
                     if len(w) >= 3 and w not in _EVENT_GENERIC)


@lru_cache(maxsize=None)
def set_games(score: str) -> tuple:
    """Games per set, whoever is written first: '7-6(5) 3-6 6-4' -> (13, 9, 10); a match tiebreak '[10-8]' is a set
    (18), as TennisLive writes it; a score with no set -> ()."""
    return tuple(int(a) + int(b) for a, b in re.findall(r"(\d+)-(\d+)", re.sub(r"\(\d+\)", "", str(score or ""))))


def repair_tml_dates(tml: pd.DataFrame, refs: list[tuple[str, pd.DataFrame]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tennis My Life files some Challenger editions under another edition's name and date: the 2018 Irving Challenger
    as Dallas (29 January), Biella 2 to 7 of 2021 as Biella 1 (14 February), Tenerife 3 of 2024 as Tenerife 1 (21
    January). The linker's window (-10 to +21 days) then misses the same match in Sackmann's files, which joins the map
    as a second match (about 900 of them, P5 of 9-10 Oct 2026). Stage 0's own linker tolerates this (stage0_build.pick).

    A Tennis My Life row whose own match a reference lists more than 10 days and at most a year away takes that
    reference's date and tournament name, so that the reference's row then links to it. Its own match: the same tour,
    surname pair (pair_key), round and games per set, in an event of the same tournament id or sharing a distinctive
    word of its name (event_words). The references are asked in order (Sackmann's files, then TennisLive's listings for
    the editions Sackmann lacks); a row that any reference lists within 10 days of its own date is left as it is, and
    so is a row whose twins sit at two different dates or events. Then the rest of a Tennis My Life event moves with
    it, when at least half of the event's rows were moved, all to one date and event, and none was found at its own
    date (``source`` "event"). Returns the rows (``d`` and ``tname`` changed) and one row per change (``row``: the
    row's index in ``tml``)."""
    report_cols = ["row", "source", "tour", "year", "tid", "tname_was", "d_was", "tname", "d", "days", "name1", "name2",
                   "round", "score"]
    t = tml.copy()

    def keyed(f: pd.DataFrame) -> pd.DataFrame:
        if f.empty or "tour" not in f:
            return pd.DataFrame(columns=["tour", "pair", "rnd", "games", "d", "tname", "tid"])
        k = pd.DataFrame({"tour": f["tour"].to_numpy(),
                          "pair": pair_key(f["name1"].map(surname_key), f["name2"].map(surname_key)).to_numpy(),
                          "rnd": f["round"].map(canon_round).fillna("").to_numpy(),
                          "games": f["score"].fillna("").astype(str).map(set_games).to_numpy(),
                          "d": pd.to_datetime(f["d"]).to_numpy(), "tname": f["tname"].fillna("").to_numpy(),
                          "tid": (f["tid"] if "tid" in f else pd.Series("", index=f.index)).fillna("").to_numpy()},
                         index=f.index)
        return k[k["pair"].notna() & k["games"].map(len).gt(0) & k["d"].notna()]

    tk = keyed(t)
    tk = tk.assign(i=tk.index)
    near, cands = set(), []
    for name, ref in refs:
        rk = keyed(ref)
        if rk.empty:
            continue
        c = tk.merge(rk, on=["tour", "pair", "rnd", "games"], suffixes=("", "_r"))
        gap = (c["d_r"] - c["d"]).dt.days
        near |= set(c.loc[gap.abs() <= REDATE_DAYS[0], "i"])
        same_event = (c["tid"].ne("") & c["tid"].eq(c["tid_r"])) | np.array(
            [bool(event_words(a) & event_words(b)) for a, b in zip(c["tname"], c["tname_r"])], dtype=bool)
        far = c[(gap.abs() > REDATE_DAYS[0]) & (gap.abs() <= REDATE_DAYS[1]) & same_event]
        cands.append(far.assign(source=name, order=len(cands)))
    report = pd.DataFrame(columns=report_cols)
    if not cands:
        return t, report
    c = pd.concat(cands, ignore_index=True)
    c = c[~c["i"].isin(near)]
    c = c[c["order"].eq(c.groupby("i")["order"].transform("min"))]          # the first reference that lists it
    one = c.groupby("i")[["d_r", "tname_r"]].nunique()
    one = one.index[(one["d_r"] == 1) & (one["tname_r"] == 1)]
    pick = c[c["i"].isin(one)].drop_duplicates("i").set_index("i")
    moved = pd.DataFrame({"source": pick["source"], "d": pick["d_r"], "tname": pick["tname_r"]})
    # the rest of an event moves with it
    tid = (t["tid"] if "tid" in t else pd.Series("", index=t.index)).fillna("").astype(str)
    ekey = (t["tour"].astype(str) + "|" + tid + "|" + t["tname"].fillna("").astype(str) + "|"
            + pd.to_datetime(t["d"]).dt.strftime("%Y-%m-%d").fillna(""))
    size = ekey.value_counts()
    held_at_own_date = set(ekey.loc[ekey.index.isin(list(near))])
    for key, idx in moved.groupby(ekey.loc[moved.index]).groups.items():
        targets = moved.loc[idx, ["d", "tname"]].drop_duplicates()
        if len(targets) != 1 or 2 * len(idx) < size[key] or key in held_at_own_date:
            continue
        rest = ekey.index[ekey.eq(key) & ~ekey.index.isin(moved.index)]
        if len(rest):
            moved = pd.concat([moved, pd.DataFrame({"source": "event", "d": targets["d"].iloc[0],
                                                    "tname": targets["tname"].iloc[0]}, index=rest)])
    report = pd.DataFrame({"row": moved.index, "source": moved["source"], "tour": t.loc[moved.index, "tour"],
                           "year": t.loc[moved.index, "year"] if "year" in t else None,
                           "tid": tid.loc[moved.index], "tname_was": t.loc[moved.index, "tname"],
                           "d_was": pd.to_datetime(t.loc[moved.index, "d"]), "tname": moved["tname"],
                           "d": pd.to_datetime(moved["d"]),
                           "name1": t.loc[moved.index, "name1"], "name2": t.loc[moved.index, "name2"],
                           "round": t.loc[moved.index, "round"], "score": t.loc[moved.index, "score"]},
                          index=moved.index)
    report["days"] = (report["d"] - report["d_was"]).dt.days
    t.loc[moved.index, "d"] = pd.to_datetime(moved["d"]).to_numpy()
    t.loc[moved.index, "tname"] = moved["tname"].to_numpy()
    return t, report[report_cols].sort_values(["d_was", "tname_was", "round"]).reset_index(drop=True)


def load_wta_lists() -> pd.DataFrame:
    """The WTA API match lists on disk: every played singles match, with its tier and match id."""
    editions = pd.read_parquet(DUMP / "points" / "wta" / "editions.parquet", columns=["tournament_id", "year", "tier"])
    tiers = {(str(t), int(y)): tier for t, y, tier in editions.itertuples(index=False)}
    tier_level = {"1000": "T1000", "500": "T500", "250": "T250", "125": "CH", "finals": "FIN", "slam": "GS",
                  "team": "TEAM"}
    records = []
    for path in sorted((RAW / "point_sources" / "wta" / "tournaments").glob("*/matches.json")):
        tid, _, year = path.parent.name.partition("_")
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for m in doc.get("matches") or []:
            if m.get("DrawMatchType") != "S":
                continue
            records.append({
                "tid": tid, "list_year": int(year), "match_id": m.get("MatchID"),
                "state": m.get("MatchState"), "winner": str(m.get("Winner") or ""),
                "qual": m.get("DrawLevelType") == "Q", "stamp": m.get("MatchTimeStamp"),
                "name1": m.get("PlayerNameLastA", ""), "name2": m.get("PlayerNameLastB", ""),
                "round": m.get("RoundID") or m.get("DateSeq"), "tier": tiers.get((tid, int(year)))})
    lists = pd.DataFrame(records)
    played = lists["state"].eq("F") & ~lists["winner"].isin(["6", "7", "", "0"])
    lists = lists[played].copy()
    lists["d"] = to_date(lists["stamp"])
    lists["tour"] = "W"
    lists["level"] = lists["tier"].map(tier_level)
    lists.loc[lists["qual"], "level"] = lists.loc[lists["qual"], "level"].map(to_qual)
    lists["draw"] = np.where(lists["qual"], "qual", "main")
    lists["grain"] = "result"
    lists["group"] = lists["tid"]
    return lists


def slam_starts(matches: pd.DataFrame) -> dict:
    """(year, slam) -> first day of the main draw, from the Grand Slam rows already known."""
    gs = matches[matches["level"].eq("GS")]
    out = {}
    for slam, pattern in SLAM_PATTERNS.items():
        hit = gs[gs["tname"].fillna("").str.lower().str.contains(pattern)]
        for year, d in hit.groupby("year")["d"].min().items():
            out[(int(year), slam)] = d
    return out


def load_slam_feeds(starts: dict) -> pd.DataFrame:
    """Singles matches of the Wimbledon, US Open and Australian Open feeds (walkovers left out)."""
    parts = []
    for site, slam in (("wimbledon", "W"), ("usopen", "USO")):
        m = pd.read_parquet(DUMP / "points" / site / "matches.parquet")
        m = m[m["event"].isin(["MS", "LS", "WS", "QS", "RS", "MQ", "WQ"])]
        m = m[~m["entry.status"].fillna("").astype(str).str.lower().str.contains("walkover")]
        pts = pd.to_numeric(m["history_points"], errors="coerce").fillna(0)
        year = pd.to_numeric(m["year"], errors="coerce")
        start = year.map(lambda y: starts.get((int(y), slam)))
        qual = m["event"].isin(["QS", "RS", "MQ", "WQ"])
        rows = pd.DataFrame({
            "tour": np.where(m["event"].isin(["MS", "QS", "MQ"]), "M", "W"),
            "d": pd.to_datetime(pd.to_numeric(m["entry.epoch"], errors="coerce"), unit="ms", errors="coerce"),
            "year": year, "name1": m["entry.team1.lastNameA"], "name2": m["entry.team2.lastNameA"],
            "round": [slam_round(c, q) for c, q in zip(m["entry.roundCode"], qual)],
            "draw": np.where(qual, "qual", "main"),
            "grain": np.where(pts > 0, "point", np.where(m["stats_outcome"].eq("ok"), "stats", "result")),
            "site": site})
        rows["d"] = rows["d"].fillna(pd.to_datetime(start))
        rows["level"] = np.where(rows["draw"].eq("qual"), "GSQ", "GS")
        parts.append(rows)
    ao = pd.read_parquet(DUMP / "points" / "ausopen" / "matches.parquet")
    ao = ao[ao["event"].isin(["MS", "WS", "MQ", "WQ"])]
    ao = ao[~ao["match_status_name"].fillna("").astype(str).str.lower().str.contains("walkover")]
    has_pts = pd.to_numeric(ao["points"], errors="coerce").fillna(0) > 0
    qual = ao["event"].isin(["MQ", "WQ"])
    rows = pd.DataFrame({
        "tour": np.where(ao["event"].isin(["MS", "MQ"]), "M", "W"),
        "d": to_date(ao["date"]), "year": pd.to_numeric(ao["year"], errors="coerce"),
        "name1": ao["team1_names"], "name2": ao["team2_names"],
        "round": [slam_round(c, q) for c, q in zip(ao["round_name"], qual)],
        "draw": np.where(qual, "qual", "main"),
        "grain": np.where(has_pts, "point", np.where(ao["stats_sets"].fillna("").astype(str) != "", "stats", "result")),
        "site": np.where(ao["route"].eq("wayback"), "ausopen_wayback", "ausopen")})
    rows["level"] = np.where(rows["draw"].eq("qual"), "GSQ", "GS")
    parts.append(rows)
    arch = pd.read_parquet(DUMP / "points" / "ausopen" / "archived_draws.parquet")
    arch = arch[arch["event"].isin(["MS", "WS", "MQ", "WQ", "QS"]) & arch["team1_names"].notna()
                & arch["winner_team"].notna()]
    year = pd.to_numeric(arch["year"], errors="coerce")
    rows = pd.DataFrame({
        "tour": np.where(arch["event"].isin(["MS", "MQ", "QS"]), "M", "W"),
        "d": to_date(arch["date"]).fillna(year.map(lambda y: starts.get((int(y), "AO")))),
        "year": year, "name1": arch["team1_names"], "name2": arch["team2_names"], "round": arch["round_name"],
        "draw": np.where(arch["event"].isin(["MQ", "WQ", "QS"]), "qual", "main"),
        "grain": "result", "site": "ausopen_archived_draws"})
    rows["level"] = np.where(rows["draw"].eq("qual"), "GSQ", "GS")
    parts.append(rows)
    return pd.concat(parts, ignore_index=True)


def load_api_tennis() -> pd.DataFrame:
    frames = [pd.read_csv(p, dtype=str, low_memory=False,
                          usecols=["event_date", "event_first_player", "event_second_player", "event_status",
                                   "event_type_type", "event_qualification", "tournament_name", "tournament_key",
                                   "tournament_round"])
              for p in sorted((HANDOFF / "api_tennis").glob("fixtures_*.csv*"))]
    f = pd.concat(frames, ignore_index=True)
    f = f[f["event_type_type"].isin(["Atp Singles", "Challenger Men Singles", "Itf Men Singles"])]
    f = f[f["event_status"].isin(["Finished", "Retired", "Awarded"])]
    # a few doubles matches are filed as singles ('Almeida/ Cigarran')
    f = f[~(f["event_first_player"].fillna("").str.contains("/") | f["event_second_player"].fillna("").str.contains("/"))]
    qual = f["event_qualification"].eq("True")
    base = f["event_type_type"].map({"Atp Singles": None, "Challenger Men Singles": "CH", "Itf Men Singles": "ITF"})
    team = f["tournament_name"].fillna("").str.contains("Davis Cup|United Cup|ATP Cup|Laver Cup|Olympic", case=False)
    base = base.where(~team, "TEAM")
    return pd.DataFrame({
        "tour": "M", "d": to_date(f["event_date"], "%Y-%m-%d"),
        "name1": f["event_first_player"], "name2": f["event_second_player"], "round": f["tournament_round"],
        "draw": np.where(qual, "qual", "main"),
        "level": np.where(qual, base.map(to_qual), base), "level_fallback": "T250",
        "tname": f["tournament_name"], "group": f["tournament_key"], "grain": "result"})


# --------------------------------------------------------------------------------------------
# Point and shot sources

def load_slam_pbp(starts: dict) -> pd.DataFrame:
    parts = []
    slam_of = {"ausopen": "AO", "frenchopen": "RG", "wimbledon": "W", "usopen": "USO"}
    for path in sorted((DUMP / "points" / "sackmann_archive" / "slam_pointbypoint").glob("*-matches.parquet")):
        year = _year_of(path)
        if year < FIRST_YEAR:
            continue
        slam = slam_of.get(path.name.split("-")[1])
        m = pd.read_parquet(path)
        pts_path = path.with_name(path.name.replace("-matches", "-points"))
        with_pts = set(pd.read_parquet(pts_path, columns=["match_id"])["match_id"]) if pts_path.exists() else set()
        # match numbers are 1RNN (men) / 2RNN (women), or MSRNN / WSRNN (2021 Australian Open); R is the round
        num = m["match_num"].fillna("").astype(str)
        digit = np.where(num.str[:1].str.isdigit(), num.str[1:2], num.str[2:3])
        parts.append(pd.DataFrame({
            "tour": np.where(num.str[:1].isin(["1", "M"]), "M", "W"), "d": starts.get((year, slam)), "year": year,
            "name1": m["player1"], "name2": m["player2"], "level": "GS", "draw": "main",
            "round": [slam_round(x, False) for x in digit],
            "grain": np.where(m["match_id"].isin(with_pts), "point", "result")}))
    return pd.concat(parts, ignore_index=True)


COURT_VISION_TNAME = {"AO": "Australian Open", "RG": "Roland Garros"}
_AO_ROUNDS = {1: "R128", 2: "R64", 3: "R32", 4: "R16", 5: "QF", 6: "SF", 7: "F"}
_RG_ROUNDS = [(64, "R128"), (32, "R64"), (16, "R32"), (8, "R16"), (4, "QF"), (2, "SF"), (1, "F")]


def court_vision_round(slam: str, code: str) -> str | None:
    """The round in a Court Vision match code: AO 'MS101' (round 1, match 01), RG 'SM001' (match 1 is the final;
    matches 64-127 are the first round). None when the code has no number."""
    digits = re.sub(r"\D", "", str(code or ""))
    if not digits:
        return None
    num = int(digits)
    if slam == "AO":
        return _AO_ROUNDS.get(num // 100)
    return next((rnd for lo, rnd in _RG_ROUNDS if num >= lo), None)


def _letters(name) -> str:
    return re.sub(r"[^a-z]", "", _ascii(str(name or "")).lower())


def _fits(catalogue_name: str, letters: str) -> bool:
    """'A.DAVIDOVICHFOKINA' fits 'alejandrodavidovichfokina': the surname ends the name and the initial starts it."""
    parts = str(catalogue_name or "").split(".")
    surname, initial = _letters(parts[-1]), _letters(parts[0])[:1] if len(parts) > 1 else ""
    return bool(surname) and letters.endswith(surname) and letters.startswith(initial)


def place_in_slam(rows: pd.DataFrame, matches: pd.DataFrame, fit) -> pd.Series:
    """uid of each row (tour, year, tname, name1, name2, round) among the main-draw matches of the same Slam, year and
    tour, or NaN. ``fit(row_name, known_name)`` scores how well two names agree (0: not at all); both players must
    fit in one orientation. The best total wins, the round decides between equals, and a row still tied is left
    to the generic linker. Needed because the generic linker works on surnames and dates alone: it cannot tell
    sisters or namesakes apart (Mirra and Erika Andreeva both played Sabalenka at Roland Garros 2024; Diane Parry
    played Xiyu and Yafan Wang at the 2024 US Open), and it can take a pair's meeting at the week-before event."""
    out = pd.Series(np.nan, index=rows.index)
    gs = matches[matches["level"].eq("GS")]
    for (tour, year, tname), group in rows.groupby(["tour", "year", "tname"]):
        cands = gs[gs["tour"].eq(tour) & gs["year"].eq(year) & gs["tname"].eq(tname)]
        known = list(zip(cands["uid"], cands["name1"], cands["name2"], cands["rnd"]))
        for i, n1, n2, rnd in zip(group.index, group["name1"], group["name2"], group["round"]):
            rnd = canon_round(rnd)
            scored = []
            for uid, a, b, r in known:
                score = max(_pair_fit(fit, n1, n2, a, b), _pair_fit(fit, n1, n2, b, a))
                if score:
                    scored.append(((score, rnd is not None and r == rnd), uid))
            if not scored:
                continue
            best = max(key for key, _ in scored)
            top = [uid for key, uid in scored if key == best]
            if len(top) == 1:
                out[i] = top[0]
    return out


def _pair_fit(fit, n1, n2, a, b) -> int:
    s1, s2 = fit(n1, a), fit(n2, b)
    return s1 + s2 if s1 and s2 else 0


def court_vision_uids(rows: pd.DataFrame, matches: pd.DataFrame) -> pd.Series:
    """Court Vision rows placed by ``_fits``: the catalogue runs compound surnames together ('P.CARRENOBUSTA'), which
    the generic linker misses when both players' are."""
    return place_in_slam(rows, matches, lambda cat, known: int(_fits(cat, _letters(known))))


def name_word_fit(a, b) -> int:
    """Name words two spellings share ('Fábián Marozsán' and 'Fabian Marozsan': 2; 'Yafan Wang' and 'Xiyu Wang': 1)."""
    return len(set(_words(str(a or ""))) & set(_words(str(b or ""))))


def sofascore_slam_uids(rows: pd.DataFrame, matches: pd.DataFrame) -> pd.Series:
    """SofaScore Slam events placed by the name words they share with a known match (their round names are
    SofaScore's, 'Round of 128' or 'R128')."""
    return place_in_slam(rows, matches, name_word_fit)


def load_slam_ball_tracking(starts: dict) -> pd.DataFrame:
    """The Hawk-Eye Court Vision copy of the Australian Open (2020-24) and Roland Garros (2019-24): shot where its
    tracking JSON is on disk with trajectories for 90% of the points, else point where its per-point CSV has any.

    The copy has no match dates, so a row is dated three days after the tournament's first day, the offset the
    linker expects of a source dated by the day played. Dated by the first day itself, a pair that also met the
    week before (Djokovic and Zverev at the 2021 ATP Cup, Svitolina and Parry at Strasbourg 2024) tied with the
    Slam match and could take the row."""
    path = DUMP / "points" / "slam_ball_tracking" / "matches.parquet"
    columns = ["tour", "d", "year", "name1", "name2", "level", "draw", "round", "grain"]
    if not path.exists():
        return pd.DataFrame(columns=columns)
    m = pd.read_parquet(path)
    year = pd.to_numeric(m["year"], errors="coerce")
    code = m["match_id"].fillna("").str.split("_").str[-1]
    points = pd.to_numeric(m["n_csv_points"], errors="coerce").fillna(0)
    first_day = pd.to_datetime(pd.Series([starts.get((int(y), s)) for y, s in zip(year, m["slam"])], index=m.index))
    return pd.DataFrame({
        "tour": m["tour"], "d": first_day + pd.Timedelta(days=3), "year": year,
        "name1": m["player1"], "name2": m["player2"], "tname": m["slam"].map(COURT_VISION_TNAME),
        "level": "GS", "draw": "main",
        "round": [court_vision_round(s, c) for s, c in zip(m["slam"], code)],
        "grain": np.where(m["tracked"].eq("TRUE"), "shot", np.where(points > 0, "point", "result"))})


def _signature(paths: list[Path]) -> str:
    return ";".join(f"{p.name}:{p.stat().st_size}:{int(p.stat().st_mtime)}" for p in paths)


def load_infosys(refresh: bool = False) -> pd.DataFrame:
    """One row per Infosys match (infosys_deep and infosys_full merged): names, ids, point rows."""
    paths = sorted((HANDOFF / "infosys_deep").glob("*_data.jsonl*")) + sorted((HANDOFF / "infosys_full").glob("*_data.jsonl*"))
    cache, meta = CACHE / "infosys_matches.parquet", CACHE / "infosys_matches.json"
    sig = _signature(paths)
    if not refresh and cache.exists() and meta.exists() and json.loads(meta.read_text())["signature"] == sig:
        return pd.read_parquet(cache)
    records: dict[tuple, dict] = {}
    for path in paths:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rec = json.loads(line)
                key = (str(rec.get("year")), str(rec.get("tournament_id")), str(rec.get("match_id")))
                points = sum(len(cat.get(side) or [])
                             for cat in (rec.get("rally_analysis") or {}).get("rallyData") or []
                             for side in ("t1err", "t1win", "t2err", "t2win"))
                old = records.get(key)
                if old is None or points > old["points"]:
                    records[key] = {"year": key[0], "tournament_id": key[1], "match_code": key[2],
                                    "match_date": rec.get("match_date"), "name1": rec.get("player1_name"),
                                    "name2": rec.get("player2_name"), "id1": rec.get("player1_id"),
                                    "id2": rec.get("player2_id"), "points": points,
                                    "stats": bool(rec.get("keystats")) or bool((old or {}).get("stats"))}
    frame = pd.DataFrame(list(records.values()))
    CACHE.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(cache, index=False)
    meta.write_text(json.dumps({"signature": sig, "rows": len(frame)}), encoding="utf-8")
    return frame


def infosys_rows(frame: pd.DataFrame) -> pd.DataFrame:
    f = frame[frame["match_code"].fillna("").astype(str).str.match(r"^[MQ]S")].copy()
    qual = f["match_code"].str.startswith("Q")
    return pd.DataFrame({
        "tour": "M", "d": to_date(f["match_date"], "%Y-%m-%d"), "year": pd.to_numeric(f["year"], errors="coerce"),
        "name1": f["name1"], "name2": f["name2"], "draw": np.where(qual, "qual", "main"), "level": None,
        "grain": np.where(f["points"] > 0, "point", np.where(f["stats"], "stats", "result")),
        "group": f["tournament_id"].astype(str),
        "key": f["year"].astype(str) + "_" + f["tournament_id"].astype(str) + "_" + f["match_code"].astype(str),
        "atp_key": id_key(f["year"], f["tournament_id"], f["id1"], f["id2"])})


def load_court_vision() -> pd.DataFrame:
    rows = [{"key": f"{p.parent.name}_{p.name[:-8]}", "year": int(p.parent.name)}
            for p in (HANDOFF / "court_vision").rglob("*.json.gz")]
    return pd.DataFrame(rows)


def _events_state(path: Path) -> str:
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            head = handle.read(40)
    except (OSError, EOFError):
        return "unreadable"
    return "empty" if head.replace(" ", "").startswith('{"Events":[]') else "points"


def wta_events_state(lists: pd.DataFrame, refresh: bool = False) -> pd.Series:
    """For each listed match: 'points', 'empty' or 'missing', from its raw umpire's log."""
    cache = CACHE / "wta_events_state.json"
    known = {} if refresh or not cache.exists() else json.loads(cache.read_text(encoding="utf-8"))
    root = RAW / "point_sources" / "wta" / "matches"
    out = []
    for tid, year, mid in zip(lists["tid"], lists["list_year"], lists["match_id"]):
        rel = f"{tid}_{year}/{mid}/events.json.gz"
        state = known.get(rel)
        if state not in ("points", "empty"):
            path = root / rel
            state = _events_state(path) if path.exists() else "missing"
            if state in ("points", "empty"):
                known[rel] = state
        out.append(state)
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(known), encoding="utf-8")
    return pd.Series(out, index=lists.index)


def load_tdi(finished: bool) -> pd.DataFrame:
    """Every singles match id TDI's scrape selected: listing details, and whether its page is on disk."""
    ids = pd.read_parquet(DUMP / "points" / "tdi" / "match_ids.parquet")
    staged = pd.read_parquet(DUMP / "points" / "tdi" / "matches.parquet",
                             columns=["match_id", "points", "level", "draw", "completed_on", "team_a_names",
                                      "team_b_names", "tournament_id", "draw_type", "in_index", "in_wayback_list"])
    ids = ids[ids["draw_type"].eq("singles")]
    rows = pd.DataFrame({
        "match_id": ids["match_id"], "d": to_date(ids["stamp_day"].fillna(ids["listing_day"]), "%Y-%m-%d"),
        "name1": ids["team1_names"], "name2": ids["team2_names"], "round": ids["round"],
        "draw": np.where(ids["round"].fillna("").str.contains("Qualif"), "qual", "main"),
        "group": ids["tournament_id"]})
    # Wayback-only ids (2025 to early 2026): only a staged page says who played
    wb = staged[staged["in_wayback_list"].eq("TRUE") & staged["in_index"].eq("FALSE")
                & staged["draw_type"].eq("singles")]
    rows = pd.concat([rows, pd.DataFrame({
        "match_id": wb["match_id"], "d": to_date(wb["completed_on"].str[:10], "%Y-%m-%d"),
        "name1": wb["team_a_names"], "name2": wb["team_b_names"],
        "draw": np.where(wb["draw"].eq("qualifying"), "qual", "main"), "group": wb["tournament_id"]})],
        ignore_index=True)
    kind = rows["group"].map(staged.dropna(subset=["level"]).groupby("tournament_id")["level"]
                             .agg(lambda s: s.value_counts().index[0]))
    rows["level"] = np.where(kind.eq("challenger"), np.where(rows["draw"].eq("qual"), "CHQ", "CH"), None)
    rows["level_fallback"] = "T250"
    page_dir = RAW / "point_sources" / "tdi" / "matches"
    on_disk = rows["match_id"].map(lambda m: (page_dir / str(m)[:2] / f"{m}.html.gz").exists())
    staged_points = pd.to_numeric(rows["match_id"].map(staged.set_index("match_id")["points"]), errors="coerce")
    rows["status"] = np.where(on_disk, "on_disk", "absent" if finished else "downloading")
    # a staged page with no points is a result only; pages not staged yet are counted as point pages
    rows["grain"] = np.where(staged_points.eq(0), "result", "point")
    rows["tour"] = "M"
    return rows


def load_mcp() -> pd.DataFrame:
    base = DUMP / "points" / "match_charting_project"
    with_points = set()
    for path in (base / "points").glob("*.parquet"):
        with_points |= set(pd.read_parquet(path, columns=["match_id"])["match_id"].unique())
    parts = []
    for g, tour in (("m", "M"), ("w", "W")):
        m = pd.read_parquet(base / "metadata" / f"charting-{g}-matches.parquet")
        parts.append(pd.DataFrame({
            "match_id": m["match_id"], "tour": tour, "d": to_date(m["Date"], "%Y%m%d"),
            "name1": m["Player 1"], "name2": m["Player 2"], "tname": m["Tournament"], "round": m["Round"],
            "draw": np.where(is_qual_round(m["Round"]), "qual", "main"),
            "grain": np.where(m["match_id"].isin(with_points), "shot", "stats")}))
    return pd.concat(parts, ignore_index=True)


def load_ta_charts(export_ids: set) -> pd.DataFrame:
    rows = []
    for path in sorted((HANDOFF / "mcp" / "charts").glob("mcp_*.jsonl*")):
        year = _year_of(path)
        if year is None or year < FIRST_YEAR - 1:
            continue
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("match_id") in export_ids or not rec.get("pointlog_size"):
                    continue
                rows.append({"d": rec.get("match_date"), "name1": rec.get("player1_name"),
                             "name2": rec.get("player2_name"), "tname": rec.get("tournament"),
                             "round": rec.get("round")})
    f = pd.DataFrame(rows)
    return pd.DataFrame({"tour": "M", "d": to_date(f["d"], "%Y-%m-%d"), "name1": f["name1"], "name2": f["name2"],
                         "tname": f["tname"], "round": f["round"],
                         "draw": np.where(is_qual_round(f["round"]), "qual", "main"), "grain": "shot"})


def load_sofascore() -> pd.DataFrame:
    base = DUMP / "points" / "sofascore"
    ev = pd.read_parquet(base / "events.parquet")
    ev = ev[ev["home_type"].eq("1") & ev["status_type"].eq("finished")]
    pts = set(pd.read_parquet(base / "points.parquet", columns=["event_id"])["event_id"].unique())
    sts = set(pd.read_parquet(base / "statistics.parquet", columns=["event_id"])["event_id"].unique())
    cat = ev["category_name"].map({"Challenger": "CH", "ITF Men": "ITF", "Davis Cup": "TEAM"})
    qual = is_qual_round(ev["round_name"])
    return pd.DataFrame({
        "tour": "M", "d": to_date(ev["start_utc"]), "name1": ev["home_name"], "name2": ev["away_name"],
        "tname": ev["tournament_name"], "round": ev["round_name"], "draw": np.where(qual, "qual", "main"),
        "level": np.where(qual, cat.map(to_qual), cat), "group": ev["unique_tournament_id"],
        "grain": np.where(ev["event_id"].isin(pts), "point", np.where(ev["event_id"].isin(sts), "stats", "result"))})


SOFASCORE_TOUR = {"ATP": "M", "Challenger": "M", "ITF Men": "M", "WTA": "W", "WTA 125": "W", "ITF Women": "W"}
SOFASCORE_FALLBACK = {"ATP": "T250", "Challenger": "CH", "ITF Men": "ITF", "WTA": "T250", "WTA 125": "CH",
                      "ITF Women": "ITF"}


def load_sofascore_editions() -> pd.DataFrame:
    """SofaScore events listed by tournament edition whose point record or box score was fetched (a listing
    alone adds nothing to a known match)."""
    base = DUMP / "points" / "sofascore_editions"
    ev = pd.read_parquet(base / "events.parquet")
    pts = set(pd.read_parquet(base / "points.parquet", columns=["event_id"])["event_id"].unique())
    sts = set(pd.read_parquet(base / "statistics.parquet", columns=["event_id"])["event_id"].unique())
    ev = ev[ev["doubles"].eq("FALSE") & ev["status_type"].eq("finished") & ev["event_id"].isin(pts | sts)]
    # qualifying by its round name, or by the tournament name ('Miami, USA, Qualifying'): some have no round name
    qual = is_qual_round(ev["round_name"]) | ev["tournament_name"].fillna("").str.contains("qualifying", case=False)
    return pd.DataFrame({
        "event_id": ev["event_id"],
        "tour": ev["category_name"].map(SOFASCORE_TOUR), "d": to_date(ev["start_utc"]), "name1": ev["home_name"],
        "name2": ev["away_name"], "tname": ev["tournament_name"], "round": ev["round_name"],
        "draw": np.where(qual, "qual", "main"), "level": None,
        "level_fallback": ev["category_name"].map(SOFASCORE_FALLBACK), "group": ev["unique_tournament_id"],
        "grain": np.where(ev["event_id"].isin(pts), "point", "stats")}).dropna(subset=["tour"])


def placement_index(matches: pd.DataFrame, aliases: pd.DataFrame | None = None, with_draw: bool = False) -> pd.Series:
    """Key -> uid, for placing the gap downloads by the keys their frozen lists hold (tour, tournament, date and names;
    with ``with_draw`` the draw too): every map match's own key, and ``aliases``, the keys of the copies merged into a
    match (build(): a Tennis My Life row's name and date before repair_tml_dates moved it, and the Sackmann and
    API-Tennis rows that then joined it). A key that names two matches places neither."""
    def key(f: pd.DataFrame) -> pd.Series:
        k = (f["tour"].astype(str) + "|" + f["tname"].fillna("").astype(str) + "|"
             + pd.to_datetime(f["d"]).dt.strftime("%Y-%m-%d") + "|" + f["name1"].fillna("").astype(str) + "|"
             + f["name2"].fillna("").astype(str))
        return k + "|" + f["draw"].fillna("").astype(str) if with_draw else k

    parts = [pd.DataFrame({"key": key(matches).to_numpy(), "uid": matches["uid"].to_numpy()})]
    if aliases is not None and len(aliases):
        parts.append(pd.DataFrame({"key": key(aliases).to_numpy(), "uid": aliases["uid"].to_numpy()}))
    k = pd.concat(parts, ignore_index=True).drop_duplicates()
    k = k[~k["key"].duplicated(keep=False)]
    return pd.Series(k["uid"].to_numpy(), index=k["key"].to_numpy())


def sofascore_edition_uids(rows: pd.DataFrame, matches: pd.DataFrame, paths: list[Path] | None = None,
                           aliases: pd.DataFrame | None = None) -> pd.Series:
    """For each row's event, the map match the by-edition adapter linked it to (its per-match tables,
    data/studies/gap_downloads/sofascore_<gap>_matches.csv, gzipped for the ITF gaps), where that match is still in
    the map, also under a key merged into it (``aliases``, placement_index); else NaN.

    The adapter links inside one tournament's SofaScore season. The generic link can instead take the same
    pair's meeting a few days earlier at another event, because the map dates 2026 matches by the day played
    and scores candidates by their distance from three days."""
    if paths is None:
        folder = DATA / "studies" / "gap_downloads"
        paths = sorted([*folder.glob("sofascore_*_matches.csv"), *folder.glob("sofascore_*_matches.csv.gz")])
    cols = ["tour", "tname", "d", "name1", "name2", "creator", "event_id"]
    # a list frozen before its gap's first run has no event_id column yet: it places nothing
    links = (pd.concat([pd.read_csv(p, usecols=lambda c: c in cols, dtype=str).reindex(columns=cols) for p in paths])
             if paths else pd.DataFrame(columns=cols))
    # a match the map holds twice (a name spelt two ways) links both rows to one event: credit Tennis My Life's
    links = links.dropna(subset=["event_id"]).sort_values("creator", key=lambda s: s.ne("tml"), kind="stable")
    links = links.drop_duplicates("event_id")

    def key(f: pd.DataFrame, day: pd.Series) -> pd.Series:
        return (f["tour"] + "|" + f["tname"].fillna("") + "|" + day + "|" + f["name1"].fillna("") + "|"
                + f["name2"].fillna(""))

    uid = placement_index(matches, aliases)               # a key two matches share places neither
    target = pd.Series(key(links, links["d"]).to_numpy(), index=links["event_id"].to_numpy())
    return rows["event_id"].map(target).map(uid)


def load_sirgenkii() -> pd.DataFrame:
    """SirGenkii/infotennis (ATP Stats Centre, 27 Dec 2024 to 7 Apr 2025): one row per match of its results
    table, at the finest grain its other tables hold for it."""
    base = DUMP / "points" / "sirgenkii_infotennis"
    key = ["year", "tournament_id", "match_id"]
    res = pd.read_parquet(base / "atp_results.parquet",
                          columns=key + ["round", "player1_name", "player1_id", "player2_name", "player2_id", "score"])
    # played singles only: United Cup doubles rubbers ('A, B') and unplayed matches carry no match id or score
    doubles = res["player1_name"].str.contains(",", na=False) | res["player2_name"].str.contains(",", na=False)
    res = res[res["match_id"].notna() & res["score"].fillna("").str.strip().ne("") & ~doubles].copy()
    res["match_id"] = res["match_id"].str.lower()
    res = res.drop_duplicates(key)
    held = {}
    for table in ("atp_court_vision", "atp_rally_analysis", "atp_key_stats"):
        t = pd.read_parquet(base / f"{table}.parquet", columns=key)
        held[table] = set(zip(t["year"], t["tournament_id"], t["match_id"].str.lower()))
    keys = list(zip(res["year"], res["tournament_id"], res["match_id"]))
    grain = ["shot" if k in held["atp_court_vision"] else "point" if k in held["atp_rally_analysis"]
             else "stats" if k in held["atp_key_stats"] else "result" for k in keys]
    # date_start is 'YYYY.MM.DD - YYYY.MM.DD' and some first dates are placeholders (Delray Beach
    # '2025.02.01 - 2025.02.16'), so the week is the last day less six; the ATP ids place most matches anyway
    cal = pd.read_parquet(base / "atp_calendars.parquet", columns=["year", "tournament_id", "date_start"])
    cal = cal.drop_duplicates(["year", "tournament_id"])
    week = dict(zip(zip(cal["year"], cal["tournament_id"]),
                    to_date(cal["date_start"].str.split(" - ").str[-1], "%Y.%m.%d") - pd.Timedelta(days=6)))
    return pd.DataFrame({
        "tour": "M", "d": [week.get((y, t)) for y, t in zip(res["year"], res["tournament_id"])],
        "year": pd.to_numeric(res["year"], errors="coerce"), "name1": res["player1_name"],
        "name2": res["player2_name"], "round": res["round"],
        "draw": np.where(res["match_id"].str.startswith("q"), "qual", "main"), "level": None, "level_fallback": "T250",
        "group": res["tournament_id"], "grain": grain,
        "atp_key": id_key(res["year"], res["tournament_id"], res["player1_id"].str.upper(), res["player2_id"].str.upper())})


def load_infosys_atp() -> pd.DataFrame:
    """The ATP Stats Centre's own Infosys files of 2018 to Oct 2021, decrypted on 8 Oct 2026 and staged
    (src/ingest/point_sources/infosys_atp_stage.py): one row per planned match code whose files hold Court Vision
    points (shot), MatchBeats points (point) or key statistics (stats). The 2021 MatchBeats files of 43 events hold
    players but no point; a code with nothing more is left out rather than added as a match. The files carry no date,
    so a row takes its tournament's first day (ManTennisData's calendar); the ATP ids place it, as for Infosys."""
    path = DUMP / "points" / "infosys_atp" / "matches.parquet"
    columns = ["tour", "d", "year", "name1", "name2", "round", "draw", "level", "level_fallback", "group", "grain",
               "atp_key"]
    if not path.exists():
        return pd.DataFrame(columns=columns)
    m = pd.read_parquet(path)
    m = m[m["purpose"].eq("plan")].copy()
    pts, sets, cv = (pd.to_numeric(m[c], errors="coerce").fillna(0) for c in ("points", "keystats_sets", "cv_points"))
    m = m[(pts > 0) | (sets > 0) | (cv > 0)].copy()
    pts, sets, cv = pts.loc[m.index], sets.loc[m.index], cv.loc[m.index]
    t = pd.read_parquet(DUMP / "matches" / "mantennisdata" / "atp_tournaments.parquet", columns=["id", "start_dtm"])
    start = dict(zip(t["id"].astype(str), to_date(t["start_dtm"], "%Y%m%d")))
    return pd.DataFrame({
        "tour": "M", "d": [start.get(f"{y}-{e}") for y, e in zip(m["year"], m["event_id"])],
        "year": pd.to_numeric(m["year"], errors="coerce"),
        "name1": m["p1_last_name"].fillna(m["p1_name"]), "name2": m["p2_last_name"].fillna(m["p2_name"]),
        "round": m["round_from_code"], "draw": m["draw"], "level": None, "level_fallback": "T250",
        "group": m["event_id"], "grain": np.where(cv > 0, "shot", np.where(pts > 0, "point", "stats")),
        "atp_key": id_key(m["year"], m["event_id"], m["p1_id"].str.upper(), m["p2_id"].str.upper())})


def load_infosys_challengers() -> pd.DataFrame:
    """The ATP Stats Centre's Challenger point files of 2021-2024, fetched for the P6 data issues and staged in tables of
    their own (src/ingest/point_sources/infosys_challengers_stage.py; owner, 14 Oct 2026: on the map, kept out of the
    serve-speed history). One row per match code whose MatchBeats file holds points, or whose rally analysis holds
    entries (point); a code with neither is left out rather than added as a match. The day is the Hugging Face copy's
    match date where it lists the code, else Stage 0's tournament date; the ATP ids place it, as for Infosys."""
    path = DUMP / "points" / "infosys_challengers" / "matches.parquet"
    columns = ["tour", "d", "year", "name1", "name2", "round", "draw", "level", "level_fallback", "group", "grain",
               "atp_key"]
    if not path.exists():
        return pd.DataFrame(columns=columns)
    m = pd.read_parquet(path)
    pts, ra = (pd.to_numeric(m[c], errors="coerce").fillna(0) for c in ("points", "rally_entries"))
    m = m[(pts > 0) | (ra > 0)].copy()
    qual = m["family"].eq("QS")
    return pd.DataFrame({
        "tour": "M", "d": to_date(m["copy_match_date"].fillna(m["stage0_tournament_date"]), "%Y-%m-%d"),
        "year": pd.to_numeric(m["year"], errors="coerce"),
        "name1": m["p1_last_name"].fillna(m["p1_name"]), "name2": m["p2_last_name"].fillna(m["p2_name"]),
        "round": m["round_from_code"], "draw": np.where(qual, "qual", "main"), "level": None,
        "level_fallback": np.where(qual, "CHQ", "CH"), "group": m["event_id"], "grain": "point",
        "atp_key": id_key(m["year"], m["event_id"], m["p1_id"].str.upper(), m["p2_id"].str.upper())})


def load_infosys_atp_recent() -> pd.DataFrame:
    """The ATP Stats Centre's own Infosys files of 2025-2026, tour level and Challengers (work package P9,
    src/ingest/point_sources/infosys_atp_recent.py), decrypted at staging into tables of their own
    (infosys_atp_recent_stage.py), apart from the serve-speed history's. One row per match code whose files hold Court
    Vision points (shot), MatchBeats points or rally entries (point), or key statistics (stats); a code with nothing
    more (an empty document) is left out rather than added as a match. The files carry no date, so a row takes its
    tournament's first day (ManTennisData's calendar); the ATP ids place it, as for Infosys."""
    path = DUMP / "points" / "infosys_atp_recent" / "matches.parquet"
    columns = ["tour", "d", "year", "name1", "name2", "round", "draw", "level", "level_fallback", "group", "grain",
               "atp_key"]
    if not path.exists():
        return pd.DataFrame(columns=columns)
    m = pd.read_parquet(path)
    pts, ra, sets, cv = (pd.to_numeric(m[c], errors="coerce").fillna(0)
                         for c in ("points", "rally_entries", "keystats_sets", "cv_points"))
    keep = (pts > 0) | (ra > 0) | (sets > 0) | (cv > 0)
    m, pts, ra, cv = m[keep].copy(), pts[keep], ra[keep], cv[keep]
    return pd.DataFrame({
        "tour": "M", "d": to_date(m["tournament_start"], "%Y%m%d"), "year": pd.to_numeric(m["year"], errors="coerce"),
        "name1": m["p1_last_name"].fillna(m["p1_name"]), "name2": m["p2_last_name"].fillna(m["p2_name"]),
        "round": m["round_from_code"], "draw": np.where(m["family"].eq("QS"), "qual", "main"), "level": None,
        "level_fallback": np.where(m["series"].eq("ch"), "CH", "T250"), "group": m["event_id"],
        "grain": np.where(cv > 0, "shot", np.where((pts > 0) | (ra > 0), "point", "stats")),
        "atp_key": id_key(m["year"], m["event_id"], m["p1_id"].str.upper(), m["p2_id"].str.upper())})


def load_sofascore_tournaments() -> pd.DataFrame:
    """SofaScore events listed by tournament season for the gap slam_points_ao_rg whose point and statistics
    documents were asked for; the seasons' other events add nothing a known match lacks. Walkovers are left out,
    as everywhere on the map."""
    base = DUMP / "points" / "sofascore_tournaments"
    columns = ["tour", "d", "name1", "name2", "tname", "round", "draw", "level", "group", "grain"]
    if not (base / "events.parquet").exists():
        return pd.DataFrame(columns=columns)
    ev = pd.read_parquet(base / "events.parquet")
    ev = ev[ev["home_type"].eq("1") & ev["status_type"].eq("finished") & ev["pbp_status"].notna()
            & ~ev["status_description"].fillna("").str.lower().eq("walkover")]
    pts = set(pd.read_parquet(base / "points.parquet", columns=["event_id"])["event_id"].unique())
    sts = set(pd.read_parquet(base / "statistics.parquet", columns=["event_id"])["event_id"].unique())
    qual = is_qual_round(ev["round_name"])
    slam = ev["unique_tournament_name"].fillna("").str.extract(
        r"^(Australian Open|Roland Garros|Wimbledon|US Open), (?:Men|Women)$")[0]
    d = to_date(ev["start_utc"])
    return pd.DataFrame({
        "tour": ev["category_name"].map({"ATP": "M", "WTA": "W"}), "d": d, "year": d.dt.year,
        "name1": ev["home_name"], "name2": ev["away_name"], "tname": slam, "round": ev["round_name"],
        "draw": np.where(qual, "qual", "main"), "level": np.where(slam.notna(), np.where(qual, "GSQ", "GS"), None),
        "group": ev["unique_tournament_id"],
        "grain": np.where(ev["event_id"].isin(pts), "point", np.where(ev["event_id"].isin(sts), "stats", "result"))
    }).dropna(subset=["tour"])


def load_tennislive(sampled: bool = False, gaps: bool = False) -> pd.DataFrame:
    """TennisLive match pages (src/ingest/point_sources/tennislive.py): the pages a player listing asked for (the ten
    careers), with ``sampled`` the pages the event mode's samples drew (tennislive_events.py), or with ``gaps`` the
    pages the gap mode linked to the map's gap matches (tennislive_gaps.py, work package P5). The tour is the match
    URL's (/atp/ or /wta/)."""
    base = DUMP / "points" / "tennislive"
    m = pd.read_parquet(base / "matches.parquet")
    for col in ("listed_for_slugs", "sampled_in", "gaps_in"):
        if col not in m:                      # tables staged before the event mode (8 Oct 2026) or the gap mode
            m[col] = m["url"] if col == "listed_for_slugs" else None
    m = m[m["gaps_in" if gaps else "sampled_in" if sampled else "listed_for_slugs"].notna()]
    m = m[m["doubles"].eq("FALSE") & ~m["end_reason"].fillna("").eq("walkover")]
    pts = set(pd.read_parquet(base / "points.parquet", columns=["url"])["url"].unique())
    sts = set(pd.read_parquet(base / "statistics.parquet", columns=["url"])["url"].unique())
    return pd.DataFrame({
        "url": m["url"],
        "tour": m["url"].str.extract(r"^/(atp|wta)/", expand=False).map({"atp": "M", "wta": "W"}),
        "d": to_date(m["reference_utc"]), "name1": m["player1_name"], "name2": m["player2_name"],
        "tname": m["tournament_name"], "round": m["stage"],
        "draw": np.where(m["stage"].fillna("").str.contains("qualif"), "qual", "main"),
        "group": m["tournament_rank"],
        "grain": np.where(m["url"].isin(pts), "point", np.where(m["url"].isin(sts), "stats", "result"))
    }).dropna(subset=["tour"])


def tennislive_gap_uids(rows: pd.DataFrame, matches: pd.DataFrame, paths: list[Path] | None = None,
                        aliases: pd.DataFrame | None = None) -> pd.DataFrame:
    """The gap mode's pages (load_tennislive(gaps=True)) with ``preset_uid``: the map match tennislive_gaps.py linked
    each to and asked its page for (its per-target tables, data/studies/gap_downloads/tennislive_<gap>_matches.csv.gz),
    found by tour, tournament, date, names and draw (a pair can meet in the qualifying and again in the main draw of
    one event), where that match is still in the map, also under a key merged into it (``aliases``, placement_index),
    and no other match has its key; a page it places nowhere keeps
    one row without. A match the map holds twice (Tennis My Life's misdated copy and Sackmann's, or two spellings of a
    name) has both copies linked to one page, and both are credited: the page is given one row per copy. A placed page
    takes its match's date, year and names, the map's own keys: the qualifying of an early-January event, played in
    late December, stays in the map's window as its match does, and two brothers TennisLive writes under one surname
    ('Arklon' and 'Conner Huertas Del Pino') keep the map's pair."""
    if paths is None:
        paths = sorted((DATA / "studies" / "gap_downloads").glob("tennislive_*_matches.csv.gz"))
    cols = ["tour", "tname", "d", "name1", "name2", "draw", "tl_url", "tl_selected"]
    links = (pd.concat([pd.read_csv(p, usecols=lambda c: c in cols, dtype=str).reindex(columns=cols) for p in paths])
             if paths else pd.DataFrame(columns=cols))
    links = links[links["tl_selected"].eq("True")].dropna(subset=["tl_url"])

    def key(f: pd.DataFrame, day: pd.Series) -> pd.Series:
        return (f["tour"] + "|" + f["tname"].fillna("") + "|" + day + "|" + f["name1"].fillna("") + "|"
                + f["name2"].fillna("") + "|" + f["draw"].fillna(""))

    uid = placement_index(matches, aliases, with_draw=True)   # a key two matches share places neither
    links = links.assign(preset_uid=key(links, links["d"]).map(uid)).dropna(subset=["preset_uid"])
    links = links.drop_duplicates(["tl_url", "preset_uid"])[["tl_url", "preset_uid"]].rename(columns={"tl_url": "url"})
    out = rows.merge(links, on="url", how="left").reset_index(drop=True)
    own = matches.drop_duplicates("uid").set_index("uid")
    placed = out["preset_uid"].notna()
    out["d"] = pd.to_datetime(out["preset_uid"].map(own["d"]).where(placed, out["d"]))
    for c in ("name1", "name2"):
        out[c] = out["preset_uid"].map(own[c]).where(placed, out[c])
    out["year"] = out["preset_uid"].map(own["year"]).where(placed, out["d"].dt.year)
    return out


def load_flashscore_points() -> pd.DataFrame:
    """Flashscore's point feeds (src/ingest/point_sources/flashscore_points.py): one row per feed with a point record,
    with the handoff copy's date, players and tournament. Work package P13's are ITF main draws (a grade such as
    "M15"); work package P6's (flashscore_p6.py) are men's ATP and Challenger matches, main draw or qualifying, whose
    grade is Flashscore's category: their level and draw are left to the match they are placed on."""
    path = DUMP / "points" / "flashscore_points" / "matches.parquet"
    cols = ["fs_id", "tour", "d", "name1", "name2", "tname", "round", "draw", "level", "group", "grain"]
    if not path.exists():
        return pd.DataFrame(columns=cols)
    m = pd.read_parquet(path)
    m = m[m["feed_status"].eq("200") & pd.to_numeric(m["fb_points"], errors="coerce").gt(0)]
    itf = m["grade"].fillna("").str.fullmatch(r"[MW]\d{2,3}")
    return pd.DataFrame({"fs_id": m["fs_id"], "tour": m["tour"], "d": to_date(m["fs_date"], "%Y%m%d"),
                         "name1": m["fs_home"], "name2": m["fs_away"], "tname": m["fs_tournament"], "round": None,
                         "draw": np.where(itf, "main", None), "level": np.where(itf, "ITF", None),
                         "group": m["fs_tournament"], "grain": "point"})


def flashscore_point_uids(rows: pd.DataFrame, matches: pd.DataFrame, paths: list[Path] | None = None,
                          aliases: pd.DataFrame | None = None) -> pd.DataFrame:
    """Flashscore's feeds (load_flashscore_points) with ``preset_uid``: the map match flashscore_points.py linked each
    to (its per-target tables, data/studies/gap_downloads/flashscore_<gap>_matches.csv.gz) or flashscore_p6.py did
    (data/studies/p6_data_issues/flashscore/fetch_matches.csv.gz, less the links its link check refused:
    ``link_refused``), found by tour, tournament, date and names, where that match is still in the map (also under a
    key merged into it: ``aliases``, placement_index) and no other match has its key. A feed linked to two map rows
    (a match the map holds twice) is given one row per copy, and a placed feed takes its match's date, year and names,
    as tennislive_gap_uids does."""
    if paths is None:
        paths = sorted((DATA / "studies" / "gap_downloads").glob("flashscore_*_matches.csv.gz"))
        paths += [p for p in [DATA / "studies" / "p6_data_issues" / "flashscore" / "fetch_matches.csv.gz"] if p.exists()]
    cols = ["tour", "tname", "d", "name1", "name2", "fs_id", "link_refused"]
    links = (pd.concat([pd.read_csv(p, usecols=lambda c: c in cols, dtype=str).reindex(columns=cols) for p in paths])
             if paths else pd.DataFrame(columns=cols))
    links = links.dropna(subset=["fs_id"])
    links = links[links["fs_id"].ne("") & ~links["link_refused"].fillna("").str.lower().eq("true")]

    def key(f: pd.DataFrame, day: pd.Series) -> pd.Series:
        return (f["tour"] + "|" + f["tname"].fillna("") + "|" + day + "|" + f["name1"].fillna("") + "|"
                + f["name2"].fillna(""))

    uid = placement_index(matches, aliases)               # a key two matches share places neither
    links = links.assign(preset_uid=key(links, links["d"]).map(uid)).dropna(subset=["preset_uid"])
    links = links.drop_duplicates(["fs_id", "preset_uid"])[["fs_id", "preset_uid"]]
    out = rows.merge(links, on="fs_id", how="left").reset_index(drop=True)
    own = matches.drop_duplicates("uid").set_index("uid")
    placed = out["preset_uid"].notna()
    out["d"] = pd.to_datetime(out["preset_uid"].map(own["d"]).where(placed, out["d"]))
    for c in ("name1", "name2"):
        out[c] = out["preset_uid"].map(own[c]).where(placed, out[c])
    out["year"] = out["preset_uid"].map(own["year"]).where(placed, out["d"].dt.year)
    return out


_TENNISLIVE_KINDS = {"itf": "ITF", "challenger": "CH", "wta125": "CH", "slam": "GS", "finals": "FIN", "tour": None}


def load_tennislive_listed() -> pd.DataFrame:
    """TennisLive's event listings (src/ingest/point_sources/tennislive_events.py): every played singles match of the
    events' results sections (and of the date pages of events without a page), as a result. They add the matches the
    result files lack: men's ITF qualifying of every year, the ITF matches since June 2026 (men) and early September
    (women), and events the files miss.

    Every match is dated by a Monday, as the result files date theirs: its event's (the first week the site's catalog
    lists it in), or for an event of two or three weeks (a Slam, a 1000) the Monday of the week it was played. Dated
    by the day played, a Thursday-to-Sunday match would fall outside the three days the linker allows for a changed
    name in the same round and week ('Stefano D'Agostino' / 'Stefano Dagostino').

    The level of an ITF event's match is ITF or ITFQ, and of a Slam's GS or GSQ (TennisLive's rank 4). Any other
    event's comes from the matches it shares with the result files (``group``), and only failing those from its kind
    and TennisLive rank (Challenger or WTA 125: CH; Finals: FIN; rank 2: T250, rank 3: T1000): TennisLive ranks a few
    250s with the WTA 125s."""
    base = DUMP / "points" / "tennislive"
    columns = ["tour", "d", "name1", "name2", "tname", "round", "draw", "level", "level_fallback", "group", "grain"]
    if not (base / "listed.parquet").exists() or not (base / "events.parquet").exists():
        return pd.DataFrame(columns=columns)
    want = ["event_key", "event_name", "event_kind", "event_rank", "tour", "discipline", "junior", "played",
            "match_id", "player1_name", "player2_name", "start_utc", "draw", "round", "score"]
    have = set(pq.read_schema(base / "listed.parquet").names)
    li = pd.read_parquet(base / "listed.parquet", columns=[c for c in want if c in have]).reindex(columns=want)
    first_week = pd.read_parquet(base / "events.parquet", columns=["key", "first_week"]).set_index("key")["first_week"]
    li = li[li["discipline"].eq("singles") & li["played"].eq("TRUE") & ~li["junior"].eq("TRUE")
            & li["event_kind"].isin(list(_TENNISLIVE_KINDS))]
    li = li.drop_duplicates(["event_key", "match_id"])
    qual = li["draw"].eq("qualifying")
    itf, slam = li["event_kind"].eq("itf"), li["event_kind"].eq("slam")
    level = pd.Series(np.where(itf, np.where(qual, "ITFQ", "ITF"), np.where(qual, "GSQ", "GS")), index=li.index)
    level = level.where(itf | slam)
    kind_level = li["event_kind"].map(_TENNISLIVE_KINDS).fillna(li["event_rank"].map({"2": "T250", "3": "T1000"}))
    monday = to_date(li["event_key"].map(first_week), "%Y-%m-%d")
    played = to_date(li["start_utc"].str[:10], "%Y-%m-%d")
    played_monday = played - pd.to_timedelta(played.dt.weekday, unit="D")
    return pd.DataFrame({
        "tour": li["tour"].map({"atp": "M", "wta": "W"}),
        "d": monday.where(~(played_monday > monday), played_monday).fillna(played_monday),
        "name1": li["player1_name"], "name2": li["player2_name"],
        "tname": li["event_name"].fillna("").str.replace(r"^(ATP|WTA)\s+", "", regex=True),
        "round": li["round"], "draw": np.where(qual, "qual", "main"), "level": level,
        "level_fallback": kind_level.where(~(itf | slam)), "group": li["event_key"], "grain": "result",
        "score": li["score"]   # player 1 first; repair_tml_dates compares games per set only
    }).dropna(subset=["tour"])


def load_lta_sample() -> pd.DataFrame:
    idx = pd.read_parquet(DUMP / "matches" / "live_tennis_api_zenodo" / "matches.parquet",
                          columns=["match_id", "player1_id", "player2_id", "tournament", "tier_key", "round",
                                   "scheduled_time_utc", "is_qualifying"])
    sample = set(pd.read_parquet(DUMP / "points" / "live_tennis_api_zenodo" / "points_sample_2026-06.parquet",
                                 columns=["match_id"])["match_id"].unique())
    idx = idx[idx["match_id"].isin(sample)]
    players = pd.read_parquet(DUMP / "players" / "live_tennis_api_zenodo" / "players.parquet",
                              columns=["player_id", "name", "tour"]).set_index("player_id")
    tour = idx["player1_id"].map(players["tour"]).fillna(idx["player2_id"].map(players["tour"]))
    qual = idx["is_qualifying"].astype(str).str.lower().eq("true")
    return pd.DataFrame({
        "tour": tour.map({"atp": "M", "wta": "W"}), "d": to_date(idx["scheduled_time_utc"]),
        "name1": idx["player1_id"].map(players["name"]), "name2": idx["player2_id"].map(players["name"]),
        "tname": idx["tournament"], "round": idx["round"], "draw": np.where(qual, "qual", "main"),
        "group": idx["tier_key"].astype(str), "grain": "point"}).dropna(subset=["tour"])


def load_itf_live() -> pd.DataFrame:
    """The ITF live-data API (src/ingest/point_sources/itf_live.py; the last 14 days, captured daily from 8 Oct 2026):
    each singles match's latest listed state, played (over, not a walkover), at the finest grain its documents hold:
    point when its point-by-point answer has points, stats when its statistics answer has values, else result (the
    day list's winner and score). It adds matches the map lacks: the result files hold almost no men's ITF results
    after early June 2026. Dated by the day played (dateStartLocal). Qualifying rounds come as R64/R32/R16 of the
    qualifying draw; they are passed as 'Q-R16' and so on, so that they never read as main-draw rounds. About 2% of
    played matches are listed "Complete" without a winner (the API's record stopped before the end); such a match
    counts only when its statistics or points hold it."""
    base = DUMP / "points" / "itf_live"
    columns = ["match_id", "tour", "d", "name1", "name2", "tname", "round", "draw", "level", "group", "grain"]
    if not (base / "matches.parquet").exists() or not (base / "documents.parquet").exists():
        return pd.DataFrame(columns=columns)
    m = pd.read_parquet(base / "matches.parquet",
                        columns=["latest", "match_id", "match_type", "gender", "status", "status_state_type", "draw",
                                 "round", "date_start_local", "list_date", "side1_players", "side2_players",
                                 "event_name", "event_tennis_id", "winner_side_id"])
    m = m[m["latest"].eq("TRUE") & m["match_type"].fillna("").str.lower().eq("singles")
          & m["status_state_type"].fillna("").str.lower().eq("post") & ~m["status"].fillna("").str.lower().eq("walkover")]
    docs = pd.read_parquet(base / "documents.parquet", columns=["match_id", "kind", "has_data"])
    docs = docs[docs["has_data"].eq("TRUE")]
    pts, sts = set(docs.loc[docs["kind"].eq("points"), "match_id"]), set(docs.loc[docs["kind"].eq("stats"), "match_id"])
    m = m[m["winner_side_id"].notna() | m["match_id"].isin(pts | sts)]
    qual = m["draw"].fillna("").str.contains("qualif", case=False)
    return pd.DataFrame({
        "match_id": m["match_id"], "tour": m["gender"].map({"men": "M", "women": "W"}),
        "d": to_date(m["date_start_local"].fillna(m["list_date"]), "%Y-%m-%d"),
        "name1": m["side1_players"], "name2": m["side2_players"], "tname": m["event_name"],
        "round": np.where(qual, "Q-" + m["round"].fillna(""), m["round"]), "draw": np.where(qual, "qual", "main"),
        "level": np.where(qual, "ITFQ", "ITF"), "group": m["event_tennis_id"],
        "grain": np.where(m["match_id"].isin(pts), "point", np.where(m["match_id"].isin(sts), "stats", "result"))
    }).dropna(subset=["tour"])


def load_infosys_slams(starts: dict) -> pd.DataFrame:
    """The Australian Open's and Roland-Garros's Infosys match centres (AO 2025, RG 2025, RG 2026), decrypted at
    staging: one row per singles match code whose file holds points or set statistics, with its Slam and both players'
    full names (the linker places it within its edition, ``slam_place``). A code with neither (a walkover, say) is
    left out rather than added as a match."""
    path = DUMP / "points" / "infosys_slams" / "matches.parquet"
    columns = ["tour", "d", "year", "name1", "name2", "round", "draw", "level", "grain", "slam"]
    if not path.exists():
        return pd.DataFrame(columns=columns)
    m = pd.read_parquet(path)
    pts = pd.to_numeric(m["points"], errors="coerce").fillna(0)
    sets = pd.to_numeric(m["keystats_sets"], errors="coerce").fillna(0)
    m = m[(pts > 0) | (sets > 0)].copy()
    year = pd.to_numeric(m["year"], errors="coerce")
    start = [starts.get((int(y), s)) for y, s in zip(year, m["slam"])]
    qual = m["draw"].eq("qual")

    def full(side):
        name = (m[f"{side}_first_name"].fillna("") + " " + m[f"{side}_last_name"].fillna("")).str.strip()
        return name.where(name.ne(""), m[f"{side}_name"])

    return pd.DataFrame({
        "tour": m["tour"], "d": to_date(m["match_date"]).fillna(pd.Series(start, index=m.index)), "year": year,
        "name1": full("p1"), "name2": full("p2"),
        "round": m["round_from_code"], "draw": np.where(qual, "qual", "main"), "level": np.where(qual, "GSQ", "GS"),
        "grain": np.where(pts.loc[m.index] > 0, "point", "stats"), "slam": m["slam"]})


def first_listed(value) -> str:
    """The first name of a staged JSON list ('["Bernarda PERA"]' -> 'Bernarda PERA'); any other string as it is."""
    if not isinstance(value, str) or not value.strip():
        return ""
    try:
        names = json.loads(value)
    except ValueError:
        return value
    return str(names[0]) if isinstance(names, list) and names else value


def load_rolandgarros(starts: dict) -> pd.DataFrame:
    """Roland-Garros's own match statistics (rolandgarros.com's match API, 2019-2026, staged 9 Oct 2026): one row per
    singles code the site answered, main draw and qualifying, dated by its schedule day, else the day it ended, else
    the main draw's first day. A code with statistics is a stats row, any other a result row; walkovers are left out
    (every played code of 2019-2026 has statistics). The linker places them within their edition (``slam_place``)."""
    path = DUMP / "points" / "rolandgarros" / "matches.parquet"
    columns = ["tour", "d", "year", "name1", "name2", "round", "draw", "level", "grain", "slam"]
    if not path.exists():
        return pd.DataFrame(columns=columns)
    m = pd.read_parquet(path)
    walkover = (m["a_end_cause"].fillna("").str.startswith("w/o") | m["b_end_cause"].fillna("").str.startswith("w/o"))
    m = m[m["answer"].eq("ok") & ~walkover].copy()
    year = pd.to_numeric(m["year"], errors="coerce")
    ended = pd.to_datetime(pd.to_numeric(m["end_timestamp"], errors="coerce"), unit="ms", errors="coerce").dt.normalize()
    start = pd.to_datetime(pd.Series([starts.get((int(y), "RG")) if pd.notna(y) else None for y in year], index=m.index))
    qual = m["draw"].eq("qual")
    return pd.DataFrame({
        "tour": m["tour"], "d": to_date(m["date_schedule"], "%Y%m%d").fillna(ended).fillna(start), "year": year,
        "name1": m["a_names"].map(first_listed), "name2": m["b_names"].map(first_listed),
        "round": m["round_from_code"], "draw": np.where(qual, "qual", "main"), "level": np.where(qual, "GSQ", "GS"),
        "grain": np.where(m["has_statistics"].fillna("").str.upper().eq("TRUE"), "stats", "result"), "slam": "RG"})


MARCOSJN2 = RAW / "gap_sources" / "marcosjn2"
_POINTS_LEVEL = {"2000": "GS", "1000": "T1000", "500": "T500", "250": "T250", "125": "CH"}


def load_marcosjn2(refresh: bool = False) -> pd.DataFrame:
    """Kaggle `marcosjn2` (a SofaScore scrape of ATP and WTA tour-level matches, 2015 to June 2025): every
    point's winner in order, so point grain. Read once from its JSON lines and cached."""
    paths = sorted(MARCOSJN2.glob("*-matches.jsonl"))
    columns = ["tour", "d", "name1", "name2", "tname", "round", "draw", "level", "level_fallback", "grain"]
    if not paths:
        return pd.DataFrame(columns=columns)
    cache, meta = CACHE / "marcosjn2_matches.parquet", CACHE / "marcosjn2_matches.json"
    sig = _signature(paths)
    if not refresh and cache.exists() and meta.exists() and json.loads(meta.read_text())["signature"] == sig:
        return pd.read_parquet(cache)
    rows = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rec = json.loads(line)
                date = (rec.get("meta") or {}).get("date") or ""
                if date[:4] < str(FIRST_YEAR - 1):
                    continue
                players, tour = rec.get("players") or {}, (rec.get("meta") or {}).get("gender")
                sets = ((rec.get("sequence") or {}).get("sets")) or []
                has_points = any(g.get("point_sequence") for s in sets for g in (s.get("games") or []))
                rows.append({"tour": "M" if tour == "M" else "W", "d": date, "name1": (players.get("home") or {}).get("name"),
                             "name2": (players.get("away") or {}).get("name"), "tname": (rec.get("tournament") or {}).get("name"),
                             "points": str((rec.get("tournament") or {}).get("points")),
                             "round": (rec.get("round") or {}).get("name"), "has_points": has_points})
    f = pd.DataFrame(rows)
    qual = is_qual_round(f["round"])
    team = f["tname"].fillna("").str.lower().str.contains(_TEAM_NAMES)
    base = f["points"].map(_POINTS_LEVEL).where(~team, "TEAM")
    out = pd.DataFrame({
        "tour": f["tour"], "d": to_date(f["d"], "%Y-%m-%d"), "name1": f["name1"], "name2": f["name2"],
        "tname": f["tname"], "round": f["round"], "draw": np.where(qual, "qual", "main"),
        "level": np.where(qual, base.map(to_qual), base), "level_fallback": None,
        "grain": np.where(f["has_points"], "point", "result")})
    CACHE.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache, index=False)
    meta.write_text(json.dumps({"signature": sig, "rows": len(out)}), encoding="utf-8")
    return out


WTA_SITE = RAW / "gap_sources" / "bwandowando"
_WTA_SITE_LEVEL = {"ITF": "ITF", "WTA 125": "CH", "125K": "CH", "WTA 250": "T250", "International": "T250",
                   "WTA 500": "T500", "Premier": "T500", "WTA 1000": "T1000", "Premier 5": "T1000",
                   "Premier Mandatory": "T1000", "Grand Slam": "GS", "Finals": "FIN"}


def wta_site_name(s) -> str:
    """'SURNAME,  FIRST  CTY' (the WTA site's form) -> 'First Surname'."""
    s = str(s or "")
    if "," not in s:
        return s.strip()
    last, rest = s.split(",", 1)
    parts = rest.split()
    if len(parts) > 1 and len(parts[-1]) == 3 and parts[-1].isupper():    # a country code, not a first name
        parts = parts[:-1]
    return " ".join(parts + [last.strip()])


_WTA_SITE_ROUNDS = ["R128", "R64", "R32", "R16", "Q", "S", "F"]


def wta_site_rounds(m: pd.DataFrame) -> pd.Series:
    """The WTA site's rounds in the map's form. It names a qualifying round by its place in the qualifying
    draw ('R128' opens a Slam's 128-player qualifying, 'R32' a 32-player one), so a tournament's first
    qualifying round is Q1. In a main draw 'Q' and 'S' are the quarter- and semi-finals."""
    name = m["round_name"].fillna("").astype(str).str.strip()
    order = name.map({r: i for i, r in enumerate(_WTA_SITE_ROUNDS)})
    qual = m["qpm_flag"].eq("Q")
    first = order.where(qual).groupby(m["pseudo_tournament_id"]).transform("min")
    step = (order - first).where(qual)
    q = step.map(lambda s: f"Q{int(s) + 1}" if pd.notna(s) else None)
    return pd.Series(np.where(qual, q, name.replace({"Q": "QF", "S": "SF"})), index=m.index)


WTA_SITE_API = DUMP / "points" / "wta" / "player_results"   # the same records from the WTA API (P2(b), 11 Oct 2026)
# The copy's last ten editions (version 29: those starting 7-14 Sep 2026) file their singles under the wrong editions
# (ITF W50s under WTA 125 titles among them); the WTA API's rows hold the same matches under their true events, so the
# copy's listings of these editions are left out (docs/studies/p6_data_issues/, 14 Oct 2026). The same list as the
# lower-level feed's builder (candidate_stage0.WTA_SITE_MISFILED).
WTA_SITE_MISFILED = frozenset({163248187558, 322715938447, 354561979229, 491515815086, 540307471641,   # 7 Sep
                               968402780291, 118580316990, 179051761652, 663626961107, 790501073046})  # 13-14 Sep


def wta_site_folder() -> Path:
    """The newest Kaggle copy on disk: a v<N>/ folder beside version 29 (kept at the root), else the root."""
    held = [(int(p.name[1:]), p) for p in WTA_SITE.glob("v*") if p.name[1:].isdigit() and (p / "matches.csv").exists()]
    return max(held)[1] if held else WTA_SITE


def wta_site_api_rows(paths: list[Path], editions: pd.DataFrame) -> pd.DataFrame:
    """The WTA API's player-matches results (src/ingest/point_sources/wta.py --player-matches; played singles, one
    row per match) in the Kaggle rows' columns. Each row takes its Kaggle edition's pseudo id, found by tournament
    group and start date, so that the two copies of a match share a key; an edition the copy lacks gets its own."""
    cols = ["tournament_group_id", "start_date", "title", "level", "qpm_flag", "round_name", "winner_name",
            "loser_name"]
    a = pd.concat([pd.read_parquet(p, columns=cols) for p in paths], ignore_index=True)
    a["start"] = pd.to_datetime(a["start_date"], errors="coerce")
    a = a[a["start"] >= START - pd.Timedelta(days=14)]
    e = editions.dropna(subset=["tournamentGroupId", "start"])
    lookup = dict(zip(zip(e["tournamentGroupId"].astype("int64").astype(str), e["start"].dt.strftime("%Y-%m-%d")),
                      e["pseudo_tournament_id"]))
    key = list(zip(a["tournament_group_id"].astype(str), a["start"].dt.strftime("%Y-%m-%d")))
    return pd.DataFrame({"pseudo_tournament_id": [lookup.get(k, f"api:{k[0]}:{k[1]}") for k in key],
                         "qpm_flag": a["qpm_flag"].to_numpy(), "round_name": a["round_name"].to_numpy(),
                         "name1": a["winner_name"].to_numpy(), "name2": a["loser_name"].to_numpy(),
                         "title": a["title"].to_numpy(), "start": a["start"].to_numpy(), "level": a["level"].to_numpy()})


def load_wta_site(refresh: bool = False) -> pd.DataFrame:
    """The WTA website's match records (Kaggle `bwandowando/womens-tennis-association-matches-1975-present`,
    built from wtatennis.com player by player): every women's singles result, ITF and qualifying included.

    Each match is listed once per player, and 12% of the ITF rows again under a second pseudo id: rows are
    kept once per tournament, draw, round and pair. Byes, walkovers and unplayed matches are left out.

    The newest Kaggle copy on disk is read (version 29 at the folder's root, any later one in v<N>/). The same
    records fetched from the WTA API's player-matches endpoint (work package P2(b), 11 Oct 2026; the copy ends with
    the editions of 7 Sep 2026) are added after the copy's rows, under the same rule, so a match both hold is kept
    once, from the copy."""
    folder = wta_site_folder()
    paths = [folder / "matches.csv", folder / "tournaments.csv"]
    api_paths = sorted(WTA_SITE_API.glob("*.parquet")) if WTA_SITE_API.exists() else []
    columns = ["tour", "d", "name1", "name2", "tname", "round", "draw", "level", "grain"]
    if not all(p.exists() for p in paths):
        return pd.DataFrame(columns=columns)
    cache, meta = CACHE / "wta_site_matches.parquet", CACHE / "wta_site_matches.json"
    sig = _signature(paths + api_paths) + ";misfiled editions left out (14 Oct 2026)"   # the rule is part of the cache
    if not refresh and cache.exists() and meta.exists() and json.loads(meta.read_text())["signature"] == sig:
        return pd.read_parquet(cache)
    t = pd.read_csv(paths[1], low_memory=False,
                    usecols=["pseudo_tournament_id", "title", "startDate", "level", "tournamentGroupId"])
    t["start"] = pd.to_datetime(t["startDate"], errors="coerce")
    t = t[t["start"] >= START - pd.Timedelta(days=14)]
    m = pd.read_csv(paths[0], low_memory=False,
                    usecols=["pseudo_match_id", "pseudo_tournament_id", "reason_code", "round_name", "qpm_flag",
                             "team_name_1", "team_name_2", "scores"])
    m = m[m["pseudo_tournament_id"].isin(set(t["pseudo_tournament_id"]))]
    m = m[~pd.to_numeric(m["pseudo_tournament_id"], errors="coerce").isin(WTA_SITE_MISFILED)]
    m = m.drop_duplicates("pseudo_match_id")
    m = m[~m["reason_code"].isin(["B", "D", "UNP", "V"])]
    m = m.merge(t.drop(columns=["tournamentGroupId"]), on="pseudo_tournament_id", how="left")
    m["name1"], m["name2"] = m["team_name_1"].map(wta_site_name), m["team_name_2"].map(wta_site_name)
    if api_paths:
        m = pd.concat([m[["pseudo_tournament_id", "qpm_flag", "round_name", "name1", "name2", "title", "start",
                          "level"]], wta_site_api_rows(api_paths, t)], ignore_index=True)
        m["pseudo_tournament_id"] = m["pseudo_tournament_id"].astype(str)
    m["pair"] = pair_key(m["name1"].map(surname_key), m["name2"].map(surname_key))
    m = m[~(m["pair"].notna() & m.duplicated(["pseudo_tournament_id", "qpm_flag", "round_name", "pair"]))]
    qual = m["qpm_flag"].eq("Q")
    team = m["title"].fillna("").str.lower().str.contains(_TEAM_NAMES)
    base = m["level"].map(_WTA_SITE_LEVEL).where(~team, "TEAM")
    out = pd.DataFrame({
        "tour": "W", "d": m["start"], "name1": m["name1"], "name2": m["name2"], "tname": m["title"],
        "round": wta_site_rounds(m), "draw": np.where(qual, "qual", "main"),
        "level": np.where(qual, base.map(to_qual), base), "grain": "result"})
    CACHE.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache, index=False)
    meta.write_text(json.dumps({"signature": sig, "rows": len(out)}), encoding="utf-8")
    return out


def wta_stats_keys() -> set:
    """(tournament id, year, match id) of every WTA match with a staged box score (batches B3 and B9)."""
    keys = set()
    for path in sorted((DUMP / "points" / "wta" / "stats").glob("*.parquet")):
        year = _year_of(path)
        # the staged files carry 'year' twice, which the dataset reader refuses; read the two columns directly
        t = pq.ParquetFile(path).read(columns=["tournament_id", "match_id"]).to_pandas()
        keys |= set(zip(t["tournament_id"].astype(str), [year] * len(t), t["match_id"].astype(str)))
    return keys


# --------------------------------------------------------------------------------------------
# Build

def build(end: pd.Timestamp, refresh: bool = False, log=print) -> tuple[Universe, dict]:
    status = catalog_status()
    u, notes, t0 = Universe(end), {"statuses_used": {}}, time.time()

    def step(msg):
        log(f"[{time.time() - t0:5.0f}s] {msg}: {len(u.matches):,} matches")

    tml = load_tml()
    tml_levels = {}
    for tour, year, name, level, draw in zip(tml["tour"], tml["year"], tml["tname"].str.lower().str.strip(),
                                             tml["level"], tml["draw"]):
        if draw == "main":
            tml_levels.setdefault((tour, year, name), level)
    sack = load_sackmann(tml_levels)
    listed = load_tennislive_listed()
    # Tennis My Life's misdated Challenger editions take their own date, so the other files' rows link to them
    tml, u.tml_redated = repair_tml_dates(tml, [("sackmann", sack), ("tennislive_listed", listed)])
    placed_tml = u.add("tml", tml)
    u.report["tml"]["redated"] = {"rows": int(len(u.tml_redated)),
                                  "by_reference": {str(k): int(v) for k, v in
                                                   u.tml_redated["source"].value_counts().items()}}
    atp_uid = (placed_tml[placed_tml["tour"].eq("M")].dropna(subset=["uid"])
               .drop_duplicates("atp_key").set_index("atp_key")["uid"])
    step(f"Tennis My Life ({len(u.tml_redated):,} rows of misdated editions given their own date)")
    # the gap downloads' frozen lists keep the keys of the copies a re-dated match now merges: Tennis My Life's old
    # name and date, and the Sackmann and API-Tennis rows that join it (placement_index)
    rep = u.tml_redated
    alias_cols = ["tour", "tname", "d", "name1", "name2", "draw", "uid"]
    aliases = [pd.DataFrame({"tour": rep["tour"].to_numpy(), "tname": rep["tname_was"].to_numpy(),
                             "d": pd.to_datetime(rep["d_was"]).to_numpy(), "name1": rep["name1"].to_numpy(),
                             "name2": rep["name2"].to_numpy(),
                             "draw": tml["draw"].reindex(rep["row"].to_numpy()).to_numpy(),
                             "uid": placed_tml["uid"].reindex(rep["row"].to_numpy()).to_numpy()})]
    merged = set(aliases[0]["uid"].dropna())

    def slam_keys(placed: pd.DataFrame) -> pd.DataFrame:
        # Grand Slam rows place within their edition (16 Oct 2026): the copy a row used to make on its own (a late round
        # dated by the event's start, 'Cori Gauff', 'Sherif Ahmed Abdelaziz') is gone, so its key places as an alias
        return placed.loc[slam_rows(placed) & placed["uid"].notna(), alias_cols]

    placed_sack = u.add("sackmann", sack)
    aliases += [placed_sack.loc[placed_sack["uid"].isin(merged), alias_cols], slam_keys(placed_sack)]
    step("Sackmann")
    lists = u.add("wta_lists", load_wta_lists(), group="group")
    aliases.append(slam_keys(lists))
    step("WTA match lists")
    starts = slam_starts(u.matches)
    feeds = load_slam_feeds(starts)
    for site in ("wimbledon", "usopen", "ausopen", "ausopen_wayback", "ausopen_archived_draws"):
        src = "slam_draws" if site == "ausopen_archived_draws" else site
        aliases.append(slam_keys(u.add(src, feeds[feeds["site"].eq(site)])))
    step("Slam feeds")
    # the WTA website's own records: women's ITF qualifying and results the other files lack
    aliases.append(slam_keys(u.add("wta_site", load_wta_site(refresh))))
    step("WTA website records")
    placed_api = u.add("api_tennis", load_api_tennis(), group="group")
    aliases += [placed_api.loc[placed_api["uid"].isin(merged), alias_cols], slam_keys(placed_api)]
    step("api-tennis")
    # TennisLive's event listings: men's ITF qualifying and the ITF results since June 2026 the files lack
    aliases.append(slam_keys(u.add("tennislive_listed", listed, group="group")))
    step("TennisLive event listings")
    tdi_status = status.get("tdi", "downloading")
    tdi = load_tdi(finished=tdi_status == "on_disk")
    notes["tdi_singles_ids"], notes["tdi_pages_on_disk"] = int(len(tdi)), int(tdi["status"].eq("on_disk").sum())
    placed = u.add("tdi", tdi[tdi["status"].ne("absent")], status="status", group="group")
    aliases.append(slam_keys(placed))
    # the listing cards themselves (with scores) are on disk, whether or not the page is yet
    u.credit("tdi_listing", placed["uid"].dropna(), "result", "on_disk")
    step("TDI")
    aliases.append(slam_keys(u.add("slam_pbp", load_slam_pbp(starts))))
    # the Court Vision copy covers matches the result files list: a row that links to none is a failed link
    cv = load_slam_ball_tracking(starts)
    cv["preset_uid"] = court_vision_uids(cv, u.matches)
    u.add("slam_ball_tracking", cv, add_new=False)
    u.report["slam_ball_tracking"]["placed_by_names_and_round"] = int(cv["preset_uid"].notna().sum())
    info = infosys_rows(load_infosys(refresh))
    info["preset_uid"] = info["atp_key"].map(atp_uid)          # ids first: Infosys dates can be weeks off
    irows = u.add("infosys", info, group="group")
    u.report["infosys"]["placed_by_atp_ids"] = int(info["preset_uid"].notna().sum())
    step("Infosys")
    cv = load_court_vision()
    cv["uid"] = cv["key"].map(irows.dropna(subset=["uid"]).set_index("key")["uid"])
    placed = cv.dropna(subset=["uid"])
    u.credit("court_vision", placed["uid"], "shot", "on_disk",
             note="placed through the Infosys record with the same year, tournament and match code")
    u.report["court_vision"].update({"rows_read": int(len(cv)), "not_placed": int(cv["uid"].isna().sum())})
    sg = load_sirgenkii()
    sg["preset_uid"] = sg["atp_key"].map(atp_uid)                # ids first, as for Infosys
    u.add("sirgenkii", sg, group="group")
    u.report["sirgenkii"]["placed_by_atp_ids"] = int(sg["preset_uid"].notna().sum())
    mcp = load_mcp()
    u.add("mcp", mcp)
    u.add("ta_charts", load_ta_charts(set(mcp["match_id"])))
    aliases.append(slam_keys(u.add("sofascore", load_sofascore(), group="group")))
    u.aliases = pd.concat([a for a in aliases if len(a)], ignore_index=True).dropna(subset=["uid"])
    se = load_sofascore_editions()
    se["preset_uid"] = sofascore_edition_uids(se, u.matches, aliases=u.aliases)     # the adapter's own links first
    u.add("sofascore_editions", se, group="group")
    u.report["sofascore_editions"]["placed_by_adapter_links"] = int(se["preset_uid"].notna().sum())
    # listed by the Slam seasons of a gap of known matches: an event that links to none is a failed link
    sst = load_sofascore_tournaments()
    sst["preset_uid"] = sofascore_slam_uids(sst, u.matches)
    u.add("sofascore_tournaments", sst, group="group", add_new=False)
    u.report["sofascore_tournaments"]["placed_by_names_and_round"] = int(sst["preset_uid"].notna().sum())
    u.add("tennislive", load_tennislive(), group="group")
    u.add("tennislive_samples", load_tennislive(sampled=True), group="group")
    # the gap mode's pages, of known matches: placed on the matches it linked them to, else a failed link
    tg = tennislive_gap_uids(load_tennislive(gaps=True), u.matches, aliases=u.aliases)
    u.add("tennislive_gaps", tg, group="group", add_new=False)
    u.report["tennislive_gaps"]["placed_by_adapter_links"] = int(tg["preset_uid"].notna().sum())
    # Flashscore's point feeds of P13, of known matches: placed on the matches it linked them to, else a failed link
    fp = flashscore_point_uids(load_flashscore_points(), u.matches, aliases=u.aliases)
    u.add("flashscore_points", fp, group="group", add_new=False)
    u.report["flashscore_points"]["placed_by_adapter_links"] = int(fp["preset_uid"].notna().sum())
    u.add("lta_sample", load_lta_sample(), group="group")
    u.add("itf_live", load_itf_live(), group="group")
    u.add("infosys_slams", load_infosys_slams(starts))
    u.add("rolandgarros", load_rolandgarros(starts))       # Roland-Garros's own statistics
    ia = load_infosys_atp()
    ia["preset_uid"] = ia["atp_key"].map(atp_uid)                # ids first, as for Infosys: the files carry no date
    u.add("infosys_atp", ia, group="group")
    u.report["infosys_atp"]["placed_by_atp_ids"] = int(ia["preset_uid"].notna().sum())
    ic = load_infosys_challengers()
    ic["preset_uid"] = ic["atp_key"].map(atp_uid)                # ids first: Tennis My Life's Challenger ids are the ATP's
    u.add("infosys_challengers", ic, group="group")
    u.report["infosys_challengers"]["placed_by_atp_ids"] = int(ic["preset_uid"].notna().sum())
    ir = load_infosys_atp_recent()
    ir["preset_uid"] = ir["atp_key"].map(atp_uid)                # ids first (P9): the files carry no date
    u.add("infosys_atp_recent", ir, group="group")
    u.report["infosys_atp_recent"]["placed_by_atp_ids"] = int(ir["preset_uid"].notna().sum())
    u.add("marcosjn2", load_marcosjn2(refresh))
    step("charts, SofaScore, TennisLive, Live Tennis API, Infosys Slams and ATP, Roland-Garros, marcosjn2")

    # WTA API: the umpire's point log (batch B1), then the batches assumed held
    state = wta_events_state(lists, refresh)
    placed = lists.assign(state=state.values).dropna(subset=["uid"])
    has_log = placed.loc[placed["state"].eq("points"), "uid"].astype("int64")
    empty = placed.loc[placed["state"].eq("empty"), "uid"].astype("int64")
    u.credit("wta_events", has_log, "point", "on_disk")
    notes["wta_logs_with_points"], notes["wta_logs_empty"] = int(has_log.nunique()), int(empty.nunique())
    m = u.matches
    wta = m["tour"].eq("W") & m["level"].isin(WTA_API_LEVELS)
    b1 = status.get("wta_events", "downloading")
    notes["statuses_used"]["wta_events"] = b1
    # B1 has read every 2020-2026 match list; what it has still to fetch is the listed matches
    # whose log is not on disk yet. A match no list holds gets nothing from B1.
    if b1 in ("downloading", "assumed"):
        waiting = placed.loc[placed["state"].eq("missing") & placed["list_year"].between(2020, 2026), "uid"]
        waiting = waiting.astype("int64")
        waiting = waiting[~waiting.isin(set(has_log) | set(empty))]
        notes["wta_b1_pending"] = u.credit("wta_events", waiting, "point", b1)
    notes["wta_in_scope_without_list"] = int((wta & m["year"].between(2019, 2026)
                                              & ~m["uid"].isin(placed["uid"].astype("int64"))).sum())
    # Box scores (batches B3, B9): each listed match whose staged box score exists. A batch still only
    # assumed (not downloaded) is credited over its whole scope instead.
    st = status.get("wta_box", "on_disk")
    notes["statuses_used"]["wta_box"] = st
    if st == "assumed":
        scope = (wta & m["year"].between(2019, 2026)) | (m["tour"].eq("W") & m["level"].isin({"GS", "GSQ"})
                                                         & m["year"].between(2024, 2026))
        notes["wta_box_matches"] = u.credit("wta_box", m.loc[scope, "uid"], "stats", st)
    else:
        keys = wta_stats_keys()
        boxed = [(str(t), int(y), str(mid)) in keys for t, y, mid in
                 zip(placed["tid"], placed["list_year"], placed["match_id"])]
        notes["wta_box_matches"] = u.credit("wta_box", placed.loc[boxed, "uid"].astype("int64"), "stats", st)
    notes["statuses_used"]["tdi"] = tdi_status
    step("WTA API batches")
    return u, notes


# --------------------------------------------------------------------------------------------
# Roll-up

def best_grains(u: Universe) -> tuple[pd.DataFrame, pd.DataFrame]:
    cover = pd.concat(u.cover, ignore_index=True)
    cover["rank"] = cover["grain"].map(GRAIN_RANK)
    cover["srank"] = cover["status"].map(STATUS_RANK)
    m = u.matches.copy()
    m["uid"] = m["uid"].astype("int64")
    m["year"] = m["year"].astype("int64")
    best = cover.sort_values(["rank", "srank"], ascending=False).drop_duplicates("uid").set_index("uid")
    disk = (cover[cover["status"].eq("on_disk")].sort_values("rank", ascending=False)
            .drop_duplicates("uid").set_index("uid"))
    m["best"] = m["uid"].map(best["grain"])
    m["best_status"] = m["uid"].map(best["status"])
    m["best_on_disk"] = m["uid"].map(disk["grain"])
    m["sources"] = m["uid"].map(cover.groupby("uid")["src"].agg(lambda s: ";".join(sorted(set(s)))))
    return m, cover


def slams_held(year: int, level: str, end: pd.Timestamp) -> int:
    """Grand Slams played that season by ``end``: 2020 lost Wimbledon, and the US Open's qualifying."""
    if year == 2020:
        return 3 if level == "GS" else 2
    last_days = [(1, 31), (6, 10), (7, 16), (9, 12)]      # roughly when each Slam is over
    return sum(pd.Timestamp(year, mo, day) <= end for mo, day in last_days)


def expected_missing(m: pd.DataFrame, end: pd.Timestamp) -> pd.DataFrame:
    """Matches that were played but that no file in data/ lists, estimated three ways.

    * Grand Slams, any year: each edition played has 127 main-draw and 112 qualifying singles
      matches per tour; a shortfall of ten or more is counted.
    * The current season: after the last week holding a fifth of the previous season's matches
      that week, the rest of the season to ``end``, when those weeks hold under half of what the
      same weeks held the season before. Totals over the whole tail are compared, so an event
      that moved a week (Washington: week 30 in 2025, weeks 31-32 in 2026) nets out.
    * The previous season, for a level that no source holds at all that year (under a fifth of the
      season before): the whole season, from the season before.

    Nothing is estimated for a level no source has ever listed (men's ITF qualifying): there is no
    baseline. Years before the previous season are not estimated: the result files are taken as
    complete there, and real changes of format (the 2019 Challenger draws) would read as gaps.
    """
    grid = m[m["level"].isin(GRID_LEVELS)].copy()
    out = []
    for (tour, level, year), g in grid[grid["level"].isin(["GS", "GSQ"])].groupby(["tour", "level", "year"]):
        n = slams_held(int(year), level, end) * (127 if level == "GS" else 112)
        if n - len(g) >= 10:
            out.append({"tour": tour, "level": level, "year": int(year), "missing": int(n - len(g)),
                        "how": f"{n} expected from the draw sizes"})
    grid["wk"] = grid["d"].dt.isocalendar().week.astype(int)
    this, prev, prev2 = end.year, end.year - 1, end.year - 2
    totals = grid.groupby(["tour", "level", "year"]).size()
    last_wk = int(end.isocalendar().week)
    for (tour, level) in {(t, lv) for t, lv, _ in totals.index if lv not in ("GS", "GSQ")}:
        n_prev, n_prev2 = totals.get((tour, level, prev), 0), totals.get((tour, level, prev2), 0)
        if n_prev2 >= 500 and n_prev < 0.2 * n_prev2:
            out.append({"tour": tour, "level": level, "year": prev, "missing": int(n_prev2 - n_prev),
                        "how": f"no source holds this level in {prev}: the whole season, from {prev2}"})
            base_year = prev2
        else:
            base_year = prev
        sel = (grid["tour"] == tour) & (grid["level"] == level)
        now = grid[sel & (grid["year"] == this) & (grid["d"] <= end)].groupby("wk").size()
        base = grid[sel & (grid["year"] == base_year)].groupby("wk").size()
        good = [w for w in range(1, last_wk + 1) if base.get(w, 0) >= 20 and now.get(w, 0) >= 0.2 * base.get(w, 0)]
        last_good = max(good) if good else 0
        tail = range(last_good + 1, last_wk + 1)
        base_tail, now_tail = sum(base.get(w, 0) for w in tail), sum(now.get(w, 0) for w in tail)
        if base_tail >= 50 and now_tail < 0.5 * base_tail:
            miss = base_tail - now_tail
            out.append({"tour": tour, "level": level, "year": this, "missing": int(miss),
                        "how": f"no source after ISO week {last_good}: weeks {last_good + 1}-{last_wk} "
                               f"estimated from the same weeks of {base_year}"})
    return pd.DataFrame(out, columns=["tour", "level", "year", "missing", "how"])


def roll_up(m: pd.DataFrame, cover: pd.DataFrame, end: pd.Timestamp,
            status: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    grid = m[m["level"].isin(GRID_LEVELS) & m["year"].between(FIRST_YEAR, end.year)]
    rows = []
    for (tour, level, year), g in grid.groupby(["tour", "level", "year"]):
        row = {"tour": tour, "level": level, "year": int(year), "matches": int(len(g))}
        for grain in GRAIN_RANK:
            row[f"best_{grain}"] = int(g["best"].eq(grain).sum())
        for grain in GRAIN_RANK:
            row[f"disk_{grain}"] = int(g["best_on_disk"].eq(grain).sum())
        for st in STATUS_RANK:
            row[f"status_{st}"] = int(g["best_status"].eq(st).sum())
        rows.append(row)
    # every tour, level and year gets a cell, including those no source lists a match for
    full = pd.MultiIndex.from_product([["M", "W"], GRID_LEVELS, range(FIRST_YEAR, end.year + 1)],
                                      names=["tour", "level", "year"])
    cells = pd.DataFrame(rows).set_index(["tour", "level", "year"]).reindex(full, fill_value=0).reset_index()
    miss = expected_missing(m, end)
    cells = cells.merge(miss.rename(columns={"missing": "missing_estimate", "how": "missing_how"}),
                        on=["tour", "level", "year"], how="left")
    cells["missing_estimate"] = cells["missing_estimate"].fillna(0).astype(int)
    cells["missing_how"] = cells["missing_how"].fillna("")
    # The WTA's Slam box scores (batch B9, 2024-26) list Slam matches the other files lack, such as
    # the 2026 Roland Garros women's qualifying: credit the estimated shortfall to that batch.
    st = (status or {}).get("wta_box")
    if st == "assumed":           # once downloaded, the WTA's Slam lists enumerate these matches themselves
        fill = (cells["tour"].eq("W") & cells["level"].isin(["GS", "GSQ"]) & cells["year"].between(2024, 2026)
                & cells["missing_estimate"].gt(0))
        cells["filled_by_batch"] = np.where(fill, cells["missing_estimate"], 0)
        cells.loc[fill, "best_stats"] += cells.loc[fill, "missing_estimate"]
        cells.loc[fill, f"status_{st}"] += cells.loc[fill, "missing_estimate"]
        cells.loc[fill, "matches"] += cells.loc[fill, "missing_estimate"]
        cells.loc[fill, "missing_how"] += "; listed by the WTA's Slam box scores (batch B9), counted as stats"
        cells.loc[fill, "missing_estimate"] = 0
    else:
        cells["filled_by_batch"] = 0
    cg = cover.merge(grid[["uid", "tour", "level", "year"]], on="uid")
    per_src = (cg.groupby(["src", "tour", "level", "year", "grain", "status"])["uid"].nunique()
               .rename("matches").reset_index())
    return cells, per_src


def run(end: pd.Timestamp, refresh: bool = False, log=print) -> dict:
    u, notes = build(end, refresh=refresh, log=log)
    m, cover = best_grains(u)
    cells, per_src = roll_up(m, cover, end, status=catalog_status())
    OUT.mkdir(parents=True, exist_ok=True)
    cells.to_csv(OUT / "coverage_cells.csv", index=False)
    keep = ["uid", "tour", "level", "draw", "year", "d", "name1", "name2", "tname", "creator", "best",
            "best_status", "best_on_disk", "sources"]
    m[keep].astype({"name1": str, "name2": str, "tname": str, "draw": str, "level": str}).to_parquet(
        OUT / "matches.parquet", index=False)
    redated = getattr(u, "tml_redated", None)
    if redated is not None:      # Tennis My Life's rows of misdated editions and the date each was given
        redated.to_csv(OUT / "tml_redated.csv", index=False)
    outside = m[~m["level"].isin(GRID_LEVELS)]
    payload = {
        "generated_by": "src/eda/data_map/measure.py",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": {"start": str(START.date()), "end": str(end.date())},
        "levels": [{"code": c, "name": n} for c, n in LEVELS],
        "cells": cells.to_dict(orient="records"),
        "per_source": per_src.to_dict(orient="records"),
        "link_report": u.report,
        "notes": notes,
        "outside_grid": {"matches": int(len(outside)),
                         "by_creator": {k: int(v) for k, v in outside.groupby("creator").size().items()}},
        "totals": {"matches": int(len(m) - len(outside)),
                   "by_best": {k: int(v) for k, v in m[m["level"].isin(GRID_LEVELS)]["best"].value_counts().items()}},
    }
    (OUT / "coverage.json").write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure the data map's coverage numbers.")
    parser.add_argument("--end", help="last day counted (default: the last complete Sunday)")
    parser.add_argument("--refresh", action="store_true", help="re-read the slow sources instead of the cache")
    args = parser.parse_args()
    end = pd.Timestamp(args.end) if args.end else last_complete_sunday(datetime.now())
    payload = run(end, refresh=args.refresh)
    print(json.dumps({"window": payload["window"], "totals": payload["totals"], "notes": payload["notes"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
