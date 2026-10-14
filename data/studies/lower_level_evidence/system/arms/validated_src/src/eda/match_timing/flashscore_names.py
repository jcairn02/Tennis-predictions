"""Player-name keys for linking Flashscore matches to Stage 0 (link_flashscore.py).

Flashscore writes players as "Surname F." ("Nishikori K.", "Del Potro J. M.", "Auger-Aliassime F.",
"Wang Xiy.", "Zahlavova Strycova B."); its feeds also give a name slug with every name token
("ferrer-david", "son-ha-yoon", sometimes first name first: "guy-den-ouden"). Stage 0 (Sackmann) writes
"First Last". Two kinds of key, both on scan.py's normalisation (accents, case and punctuation removed,
hyphens to spaces):

    S:<surname> <first initial>   Flashscore: the tokens before the first abbreviated token, and that
                                  token's first letter. Stage 0: every "surname span + first initial" form
                                  of the name (scan.py's td_variants: "Juan Martin Del Potro" gives
                                  "del potro j" among others), plus the first token as surname with the
                                  second's initial, for names written surname first ("Zhang Shuai").
    F:<sorted tokens>             every token of the name, sorted (scan.py's name_key): the Flashscore slug
                                  against the Stage 0 name, so "ferrer-david" equals "David Ferrer".

Loose keys (used only at lower priority, with identical set scores required): every shorter span of
the Flashscore surname with the initial, so "Zahlavova Strycova B." also gives "strycova b"
(married and compound surnames), skipping spans made only of particles or of one- or two-letter words.
"""
from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.merge_feasibility import scan as S  # noqa: E402

PARTICLES = {"de", "da", "del", "della", "dei", "di", "do", "dos", "das", "du", "van", "von", "der", "den", "la", "le",
             "el", "al", "bin", "ben", "ter", "ten", "y", "e", "st", "san", "mc", "mac", "jr", "sr", "ii", "iii"}
ABBREV = re.compile(r"^[^\W\d_]{1,4}\.(?:-?[^\W\d_]{0,3}\.?)*$")      # "K.", "Xiy.", "J.-W.", "Ka."
PAREN = re.compile(r"\s*\([^)]*\)\s*")
APOSTROPHES = re.compile(r"['’`´]")


def unglue(name: str) -> str:
    """Apostrophes dropped rather than read as a space, so "O'Connell" and the slug "oconnell" agree."""
    return APOSTROPHES.sub("", str(name or ""))


@lru_cache(maxsize=None)
def fs_parts(display: str) -> tuple[tuple[str, ...], str]:
    """(normalised surname tokens, first initial) of a Flashscore "Surname F." name."""
    raw = PAREN.sub(" ", str(display or "")).strip()
    toks = raw.split()
    if not toks:
        return (), ""
    cut = next((i for i, t in enumerate(toks) if i > 0 and ABBREV.match(t)), None)
    if cut is None:                       # no abbreviated token: the last token is the first name
        if len(toks) < 2:
            return tuple(S.norm(raw).split()), ""
        cut = len(toks) - 1
    surname = tuple(S.norm(" ".join(toks[:cut])).split())
    initial = next((ch for ch in S.norm(toks[cut]) if ch.isalpha()), "")
    return surname, initial


@lru_cache(maxsize=None)
def fs_strict_keys(display: str, slug: str) -> frozenset:
    keys = set()
    for form in {str(display or ""), unglue(display)}:
        surname, initial = fs_parts(form)
        if surname and initial:
            keys.add("S:" + " ".join(surname) + " " + initial)
    slug_toks = [t for t in S.norm(str(slug or "").replace("-", " ")).split() if t]
    if len(slug_toks) >= 2:
        keys.add("F:" + " ".join(sorted(slug_toks)))
    return frozenset(keys)


@lru_cache(maxsize=None)
def fs_loose_keys(display: str) -> frozenset:
    surname, initial = fs_parts(display)
    if len(surname) < 2 or not initial:
        return frozenset()
    keys = set()
    n = len(surname)
    for k in range(n):
        for m in range(k + 1, n + 1):
            span = surname[k:m]
            if m - k == n:
                continue
            if all(t in PARTICLES or len(t) <= 2 for t in span):
                continue
            keys.add("S:" + " ".join(span) + " " + initial)
    return frozenset(keys)


def _alike(a: str, b: str) -> bool:
    """Two given names that may be the same: one a prefix of the other ("stan", "stanislas"; an initial), close
    spellings ("yevgeny", "evgeny"), or the same first two letters and a fair likeness ("aleksandr", "alexander");
    not "karolina" and "kristyna"."""
    if a.startswith(b) or b.startswith(a):
        return True
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= 0.8 or (a[:2] == b[:2] and ratio >= 0.6)


@lru_cache(maxsize=None)
def given_names_conflict(fs_display: str, fs_slug: str, s0_full: str) -> bool | None:
    """Whether the given names in Flashscore's slug clearly differ from Stage 0's ("pliskova-karolina" against
    "Kristyna Pliskova"); None when it cannot be told (no slug, or no given name left on a side). Given names are
    the tokens outside Flashscore's surname, so a married name ("Volodko K." / "volodko-kateryna" against
    "Kateryna Bondarenko") or a name written surname first does not conflict."""
    slug_toks = S.norm(unglue(fs_slug).replace("-", " ")).split()
    if not slug_toks:
        return None
    surname = set(fs_parts(unglue(fs_display))[0])
    given_fs = [t for t in slug_toks if t not in surname]
    given_s0 = [t for t in S.norm(unglue(s0_full)).split() if t not in surname]
    if not given_fs or not given_s0:
        return None
    return not any(_alike(a, b) for a in given_fs for b in given_s0)


@lru_cache(maxsize=None)
def initial_agrees(fs_display: str, s0_full: str) -> bool:
    """Flashscore's first initial is the initial of Stage 0's given name: the first token, or, where Stage 0
    shares a surname token with Flashscore (a name written surname first), the tokens outside that surname."""
    surname, initial = fs_parts(unglue(fs_display))
    toks = S.norm(unglue(s0_full)).split()
    if not initial or not toks:
        return False
    shared = set(surname) & set(toks)
    given = ([t for t in toks if t not in shared] or toks[:1]) if shared else toks[:1]
    return any(t[0] == initial for t in given)


@lru_cache(maxsize=None)
def stage0_keys(full: str) -> frozenset:
    keys = set()
    for form in {str(full or ""), unglue(full)}:
        t = S.norm(form).split()
        if not t:
            continue
        if form == unglue(full):
            keys.add("F:" + " ".join(sorted(t)))
        if len(t) >= 2:
            keys |= {"S:" + v for v in S.td_variants(form)}
            keys.add("S:" + t[0] + " " + t[1][0])              # written surname first
            if len(t) >= 3:
                keys.add("S:" + " ".join(t[:2]) + " " + t[2][0])
    return frozenset(keys)
