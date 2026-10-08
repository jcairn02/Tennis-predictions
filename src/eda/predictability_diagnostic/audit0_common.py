"""Shared loaders for the audit of Stage 0 (the audit0_*.py scripts).

The audit reads the Stage 0 tables and the staged source rows (data/dump/matches) directly. It does
not import stage0_build.py: names, scores and box-score counts are parsed here again, so a check
does not repeat the code it checks. Evidence goes to data/studies/predictability_diagnostic/audit0/;
nothing Stage 0 wrote is changed.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DUMP = ROOT / "data" / "dump" / "matches"
STUDY = ROOT / "data" / "studies" / "predictability_diagnostic"
MATCHES = STUDY / "stage0_matches.parquet"
PLAYERS = STUDY / "stage0_match_players.parquet"
AUDIT = STUDY / "audit0"
MAP_DIR = ROOT / "data" / "studies" / "data_map"

# The staged singles files: every Sackmann and Tennis My Life (TML) file group except doubles.
STAGED = [  # (source, tour, glob under data/dump/matches)
    ("sackmann", "atp", "sackmann_archive/atp/atp_matches_[0-9]*.parquet"),
    ("sackmann", "atp", "sackmann_archive/atp/atp_matches_qual_chall_*.parquet"),
    ("sackmann", "atp", "sackmann_archive/atp/atp_matches_futures_*.parquet"),
    ("sackmann", "wta", "sackmann_archive/wta/wta_matches_[0-9]*.parquet"),
    ("sackmann", "wta", "sackmann_archive/wta/wta_matches_qual_itf_*.parquet"),
    ("tml", "atp", "tennis_my_life/atp_main/*.parquet"),
    ("tml", "atp", "tennis_my_life/atp_challenger/*.parquet"),
    ("tml", "atp", "tennis_my_life/atp_qualifying/*.parquet"),
    ("tml", "wta", "tennis_my_life/wta_main/*.parquet"),
    ("tml", "atp", "tennis_my_life/ongoing/ongoing_tourneys.parquet"),
    ("tml", "atp", "tennis_my_life/ongoing/challenger_ongoing_tourneys.parquet"),
    ("tml", "wta", "tennis_my_life/ongoing/wta_ongoing_tourneys.parquet"),
]
BOX_COLS = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]


def out_dir() -> Path:
    AUDIT.mkdir(parents=True, exist_ok=True)
    return AUDIT


def write_json(name: str, obj) -> Path:
    path = out_dir() / name
    path.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    return path


def load_staged(columns: list[str] | None = None, first_season: int = 2009) -> pd.DataFrame:
    """Every staged singles row of the two result sources, with source, tour, file and season.

    ``_source_file`` and ``_row`` identify a row (they are what Stage 0 stores as source_file and
    source_row)."""
    frames = []
    for source, tour, pattern in STAGED:
        for path in sorted(DUMP.glob(pattern)):
            m = re.search(r"(\d{4})", path.name)
            season = int(m.group(1)) if m else None
            if season is not None and season < first_season:
                continue
            cols = None if columns is None else list(dict.fromkeys(columns + ["_source_file", "_row"]))
            df = pd.read_parquet(path, columns=cols)
            df["source"], df["tour"], df["staged_file"], df["file_season"] = source, tour, path.name, season
            frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["_row"] = pd.to_numeric(out["_row"]).astype("int64")
    return out


def load_matches(columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(MATCHES, columns=columns)


def load_players(columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(PLAYERS, columns=columns)


def names_by_side(mp: pd.DataFrame | None = None) -> pd.DataFrame:
    """match_id -> name_A, name_B, winner name, loser name (from stage0_match_players)."""
    mp = load_players(["match_id", "side", "won", "player_name", "player_id"]) if mp is None else mp
    a = mp[mp["side"].eq("A")].set_index("match_id")
    b = mp[mp["side"].eq("B")].set_index("match_id")
    w = mp[mp["won"]].set_index("match_id")
    l = mp[~mp["won"]].set_index("match_id")
    return pd.DataFrame({"name_a": a["player_name"], "name_b": b["player_name"], "winner_name": w["player_name"],
                         "loser_name": l["player_name"], "winner_id": w["player_id"], "loser_id": l["player_id"]})


# ------------------------------------------------------------------------------------------------
# Names (written here again, not taken from scan.py)

_PARTICLES = {"de", "da", "di", "del", "della", "der", "den", "van", "von", "la", "le", "dos", "das", "du", "jr", "sr"}


@lru_cache(maxsize=None)
def tokens(name: str) -> tuple:
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    return tuple(w for w in re.split(r"[^a-z]+", s) if w)


@lru_cache(maxsize=None)
def full_key(name: str) -> str:
    """Order-free key of every word: 'Zhang Zhizhen' and 'Zhizhen Zhang' agree."""
    return " ".join(sorted(tokens(name)))


@lru_cache(maxsize=None)
def distinctive(name: str) -> frozenset:
    """Words of a name that can identify a player: at least three letters, particles dropped."""
    return frozenset(w for w in tokens(name) if len(w) >= 3 and w not in _PARTICLES)


def same_person(a: str, b: str) -> bool:
    """Loose: the two spellings share a distinctive word (surname variants, married names aside)."""
    return bool(distinctive(a) & distinctive(b))


_EVENT_GENERIC = {"open", "cup", "atp", "wta", "itf", "challenger", "masters", "finals", "championships", "international",
                  "tennis", "trophy", "group", "play", "offs", "the", "and", "tour", "qualifying", "qualies"}


@lru_cache(maxsize=None)
def event_words(name) -> frozenset:
    """Distinctive words of a tournament name ('BJK Cup Finals' -> {'bjk'}; 'Davis Cup G2 R1: CYP vs EGY'
    -> {'davis', 'cyp', 'egy'})."""
    return frozenset(w for w in tokens(name) if len(w) >= 3 and w not in _EVENT_GENERIC)


def pair_key(a: pd.Series, b: pd.Series) -> pd.Series:
    ka, kb = a.map(full_key), b.map(full_key)
    return pd.Series(np.where(ka < kb, ka + "|" + kb, kb + "|" + ka), index=a.index)


# ------------------------------------------------------------------------------------------------
# Scores (written here again, not taken from stage0_build.py)

_SET = re.compile(r"^(\d{1,2})-(\d{1,2})(?:\((\d+)\))?$")
_MTB = re.compile(r"^\[(\d+)-(\d+)\]$")


@lru_cache(maxsize=None)
def parse_score(score: str) -> tuple:
    """(sets, markers): sets as (winner games, loser games, tiebreak points or None, is a match
    tiebreak) as written, and every other token, lower case, joined by spaces."""
    s = str(score or "").replace("&nbsp;", " ").replace(",", " ")
    sets, other = [], []
    for tok in s.split():
        m = _SET.match(tok)
        if m:
            sets.append((int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None, False))
            continue
        m = _MTB.match(tok)
        if m:
            sets.append((int(m.group(1)), int(m.group(2)), None, True))
            continue
        other.append(tok.lower())
    return tuple(sets), " ".join(other)


def set_done(a: int, b: int, tb, mtb: bool, short: bool = False) -> bool:
    """Whether a set's numbers finish it: 6-x by two, 7-5, 7-6, a long final set, a match tiebreak
    to 10 by two, or first to 4 in the short-set format."""
    hi, lo = max(a, b), min(a, b)
    if mtb:
        return hi >= 10 and hi - lo >= 2 or (hi, lo) == (1, 0)
    if short:
        return hi == 4 and lo <= 3 or (hi, lo) == (5, 4)
    if hi == 6 and lo <= 4:
        return True
    if hi == 7 and lo in (5, 6):
        return True
    return hi > 7 and hi - lo == 2 or (hi > 7 and hi - lo == 1 and tb is not None) or (hi > 7 and lo == hi - 1 == 12)


def set_tally(score: str, short: bool = False) -> tuple:
    """(finished sets won by the first-written player, by the second, whether the last set is finished)."""
    sets, _ = parse_score(score)
    won_w = sum(1 for a, b, tb, mtb in sets if set_done(a, b, tb, mtb, short) and a > b)
    won_l = sum(1 for a, b, tb, mtb in sets if set_done(a, b, tb, mtb, short) and b > a)
    return won_w, won_l, bool(sets) and set_done(*sets[-1], short)


def classify_score(score: str, best_of: float | None, short: bool = False) -> str:
    """The audit's own reading of a score string: walkover, retired, defaulted, abandoned, bye,
    blank, unreadable, completed, completed_reversed (the loser's side written first),
    unfinished_unmarked (a completed-looking score whose last set is unfinished) or
    short_of_best_of (every set finished, the winner ahead but short of the sets needed)."""
    raw = str(score or "").strip()
    if raw == "" or raw.lower() == "&nbsp;":
        return "blank"
    sets, marks = parse_score(raw)
    games = sum(a + b for a, b, _, mtb in sets if not mtb)
    if re.search(r"\bret|^re$|retired|\bre\b", marks):
        return "retired"
    if re.search(r"\bdef|default|disq", marks):
        return "defaulted"
    if "w/o" in marks or "walkover" in marks or re.search(r"\bwo\b", marks):
        return "walkover_after_play" if games > 0 else "walkover"
    if "bye" in marks:
        return "bye"
    if re.search(r"abd|aband|unfinished|\bwea\b|^ab\.?$|\bsusp", marks):
        return "abandoned"
    if marks or not sets:
        return "unreadable"
    need = int(best_of) // 2 + 1 if best_of and not np.isnan(best_of) else 2
    won_w, won_l, last_done = set_tally(raw, short)
    if won_w >= need:
        return "completed"
    if won_l >= need and won_l > won_w:
        return "completed_reversed"
    if not last_done:
        return "unfinished_unmarked"
    if won_w > won_l:
        return "short_of_best_of"
    return "inconsistent"


def games_in_score(score: str, short: bool = False) -> tuple:
    """(games won by the first-written player, by the second, standard tiebreak games), match
    tiebreaks excluded; a tiebreak set such as 7-6 counts as 13 games, one of them a tiebreak."""
    sets, _ = parse_score(score)
    gw = gl = tb = 0
    for a, b, t, mtb in sets:
        if mtb:
            continue
        gw, gl = gw + a, gl + b
        hi, lo = max(a, b), min(a, b)
        if short:
            tb += int((hi, lo) == (4, 3))
        else:
            tb += int(t is not None or (hi, lo) in ((7, 6), (13, 12)))
    return gw, gl, tb


def binom_share(k: int, n: int) -> dict:
    """A share with its 95% Wilson interval."""
    if n == 0:
        return {"n": 0, "k": 0, "share": None, "lo": None, "hi": None}
    p = k / n
    z = 1.959964
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return {"n": int(n), "k": int(k), "share": round(p, 5), "lo": round(mid - half, 5), "hi": round(mid + half, 5)}
