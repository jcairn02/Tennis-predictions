"""Borrowed links in the by-edition SofaScore gaps: the links to refuse (docs/studies/p6_data_issues/).

When SofaScore lacks a target's match, an event of one of its players whose opponent shares only a first name can
take its place (Forli 2022: Musetti v Gigante is not listed, and Angelini v Arnaldi shares "Lorenzo" and "Matteo").
A surname rule alone would also refuse correct links, because SofaScore shows a player's current name on old
matches (Jaksic now Jovic, Rueffer now Papadakis). So a link is refused only when both tests fail:

* **the surnames:** a target player shares no surname word with the SofaScore player on its side, in either
  orientation. SofaScore's surname is read from its slug, which runs surname first ('barranco-cosano-javier',
  'moeller-elmer'), against its name, which runs given names first ('Javier Barranco Cosano', 'Elmer Møller'): the
  given names are the longest start of the name that ends the slug, the rest of both is the surname, in both
  spellings. A word of three letters or more spelt within SURNAME_SIMILARITY counts (Moeller and Møller, Azoides and
  Azoidis, Sin and Shin). Where the two
  do not line up (names written surname first, 'Wu Yibing'), the short name's words ('Y. Wu');
* **the official result:** Tennis My Life's or Sackmann's row of the target (src/eda/gap_downloads/verify_links.py)
  gives another winner, or the same winner with other games in a set.

A link the official result cannot test (no official row, or SofaScore lists no winner) is kept.

Writes data/studies/p6_data_issues/borrowed_links/: links.csv.gz (every linked target, with both tests),
vetoes.csv (the refused links), summary.json. With --apply, also the adapter's veto file,
data/studies/gap_downloads/sofascore_link_vetoes.csv, which sofascore_editions.list_and_link reads.

Usage: ./python.sh src/eda/p6_data_issues/borrowed_links.py [--gaps g1,g2] [--apply]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import verify_links as V                # noqa: E402
from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import sofascore_editions as E       # noqa: E402

OUT = PROJECT_ROOT / "data" / "studies" / "p6_data_issues" / "borrowed_links"
# the ATP gap of 30 Sep and P6's seven; P7's ITF gaps are another session's, still being collected
GAPS = ["atp_points_2025", "challenger_points_2025", "wta125_points_2019_2026", "tour_points_rest",
        "challenger_points_2022_2024", "atp_points_2018_2020", "wta_2018_points", "challenger_points_2018_2021"]
DISAGREE = {"winner differs", "winner agrees, score differs"}
LETTERS = str.maketrans({"ø": "o", "æ": "ae", "œ": "oe", "ß": "ss", "đ": "d", "ł": "l", "ı": "i", "þ": "th"})
SURNAME_SIMILARITY = 0.8  # Moeller ~ Moller 0.92, Azoides ~ Azoidis 0.86; Shevchenko ~ Shevtsov 0.56


def name_parts(name) -> list[str]:
    """The name's lower-case ASCII words of two letters or more, in order, particles left out (Wu and Li kept)."""
    text = str(name or "").lower().translate(LETTERS)
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return [w for w in re.split(r"[^a-z]+", text) if len(w) >= 2 and w not in E.PARTICLES]


def surname_words(team: dict) -> frozenset:
    """A SofaScore player's surname words, from the slug against the name; else the short name's words."""
    name, slug = name_parts(team.get("name")), name_parts((team.get("slug") or "").replace("-", " "))
    for n in range(min(len(name), len(slug)) - 1, 0, -1):     # at least one surname word is left
        if name[:n] == slug[-n:]:
            return frozenset(name[n:]) | frozenset(slug[:-n])
    return frozenset(name_parts(team.get("shortName")))


def shares_surname(words: frozenset, surnames: frozenset) -> bool:
    """A word in common, or one spelt within SURNAME_SIMILARITY; a side with no surname found passes."""
    if not surnames or words & surnames:
        return True
    return any(len(w) >= 3 and len(s) >= 3 and SequenceMatcher(None, w, s).ratio() >= SURNAME_SIMILARITY
               for w in words for s in surnames)   # three letters: Sin ~ Shin 0.86 (San Hui Sin, Sanhui Shin)


def surnames_agree(name1, name2, event: dict) -> bool:
    """Whether each target player shares a surname word with one side of the event, in either orientation."""
    a, b = frozenset(name_parts(name1)), frozenset(name_parts(name2))
    home, away = surname_words(event.get("homeTeam") or {}), surname_words(event.get("awayTeam") or {})
    return any(shares_surname(a, x) and shares_surname(b, y) for x, y in ((home, away), (away, home)))


def gap_links(gap: str) -> pd.DataFrame:
    """Every linked target of a gap, rebuilt offline with the adapter's own rules and no vetoes, with both tests."""
    targets, _ = E.load_targets(gap, refresh=False)
    targets = targets.assign(w1=targets["name1"].map(E.words), w2=targets["name2"].map(E.words))
    known = E.known_matches(targets)
    known = known.assign(w1=known["name1"].map(E.words), w2=known["name2"].map(E.words))
    lister = E.Lister(None, P.receipts_for(E.SOURCE), offline=True)
    _, rows, linked = E.list_and_link(lister, targets, known, log_every=10 ** 6, vetoes={})
    official = {k[:5]: (k[5], k[6]) for k in V.official_rows(set(targets["tname"].dropna())).itertuples(index=False)}
    out = []
    for r in rows:
        if not r["listed"]:
            continue
        event = linked[r["event_id"]]
        key = (r["tname"], pd.Timestamp(r["d"]).strftime("%Y-%m-%d"), r["name1"], r["name2"], r["draw"])
        score, source = official.get(key, (None, None))
        verdict = "no official row" if source is None else V.compare(event, r["name1"], score)
        home, away = event.get("homeTeam") or {}, event.get("awayTeam") or {}
        out.append({"gap": gap, "uid": r["uid"], "edition": r["edition"], "tname": r["tname"],
                    "d": pd.Timestamp(r["d"]).date(), "level": r["level"], "draw": r["draw"], "name1": r["name1"],
                    "name2": r["name2"], "creator": r["creator"], "event_id": int(r["event_id"]),
                    "ss_home": home.get("name"), "ss_away": away.get("name"), "ss_home_slug": home.get("slug"),
                    "ss_away_slug": away.get("slug"), "ss_score": " ".join(f"{w}-{l}" for w, l in V.ss_sets(event)),
                    "official": source, "official_score": score, "verdict": verdict,
                    "surnames_agree": surnames_agree(r["name1"], r["name2"], event)})
    return pd.DataFrame(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gaps", default=",".join(GAPS))
    parser.add_argument("--apply", action="store_true", help="also write the adapter's veto file")
    args = parser.parse_args()
    P.configure_stdout()
    OUT.mkdir(parents=True, exist_ok=True)
    links = pd.concat([gap_links(g) for g in args.gaps.split(",")], ignore_index=True)
    links["veto"] = ~links["surnames_agree"] & links["verdict"].isin(DISAGREE)
    links.to_csv(OUT / "links.csv.gz", index=False, compression="gzip")
    vetoes = links[links["veto"]].assign(reason="the surnames differ and the official result disagrees")
    vetoes.to_csv(OUT / "vetoes.csv", index=False)
    summary = {"generated_at": P.utc_now_iso(), "rule": "refuse a link when no surname matches and the official "
               "winner or set scores differ",
               "links": int(len(links)),
               "by_gap": {g: {"links": int(len(x)), "surnames_differ": int((~x["surnames_agree"]).sum()),
                              "vetoes": int(x["veto"].sum())} for g, x in links.groupby("gap")},
               "surnames_differ_by_verdict": links.loc[~links["surnames_agree"], "verdict"].value_counts().to_dict(),
               "vetoes": int(len(vetoes))}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    if args.apply:
        cols = ["gap", "uid", "event_id", "reason", "tname", "d", "name1", "name2", "ss_home", "ss_away", "verdict",
                "official_score", "ss_score"]
        vetoes[cols].to_csv(E.VETOES, index=False)
        print(f"wrote {P.rel(E.VETOES)}: {len(vetoes)} vetoes")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
