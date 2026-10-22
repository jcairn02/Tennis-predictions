"""Check Flashscore's point records against the official result: does each record have the target match's winner and
set scores? Work package P13's ITF records (--gap), and work package P6's ATP and Challenger records (--p6;
docs/studies/p6_data_issues/, section 2).

For every target of a per-target table with a point record on disk (P13's
data/studies/gap_downloads/flashscore_<gap>_matches.csv.gz, or P6's
data/studies/p6_data_issues/flashscore/fetch_matches.csv.gz), the record's sets (the games after each set's last game)
and winner are compared with the result file the map took the target from: Tennis My Life's or Sackmann's row for the
same match, found as verify_links.py finds it (tournament, date, both names, draw; Tennis My Life's row first). The
Flashscore players are put in the target's order by their surnames (home_is_name1). Verdicts, as verify_links.py's:
    agrees                       same winner, same games in every set (at a retirement, all but the unfinished set)
    winner agrees, score differs
    winner differs               a wrong link, or a result recorded differently
    no official row              the target came from a file this check does not read (TennisLive's listings, the
                                 WTA website records ...); the ``creator`` column names it
    no record                    the feed was empty; not fetched: not asked yet; not linked: no Flashscore record named
                                 the pair

**Borrowed links (P6).** P13 linked a target only when both Flashscore players' surnames are words of the target's
names; P6's links (src/eda/p6_data_issues/flashscore_coverage.py) count shared name words, first names included, so
one player's match against another opponent with the same first name can take a target's place. Each linked target
is therefore given P6's surname test (``surnames``: borrowed_links.surnames_agree's rule on Flashscore's surname
words). A link is refused (``link_refused``) when the official row contradicts the record: another winner, or other
games in a set. Links without an official row are kept. ``both_tests_fail`` is the rule first declared, P6's rule
for SofaScore's links (the study's README, section 1: refused only when the surnames differ too); the trial of 16
Oct 2026 found a link it keeps that is wrong, Klizan v Darian King taken by Klizan v Evan King: Flashscore names a
player by surname and initial ("King E."), so the surname test cannot tell two players of one surname apart.

Writes data/studies/gap_downloads/flashscore_<gap>_link_check.csv.gz (one row per target) and
flashscore_<gap>_link_check.json (counts overall, by month and by the file read); with --p6,
data/studies/p6_data_issues/flashscore/link_check.csv.gz, link_check.json and link_vetoes.csv (the refused links,
which flashscore_p6.py marks in its per-target table, so the map does not place them).

Usage: ./python.sh src/eda/gap_downloads/verify_flashscore.py [--gap itf_points_2025_2026 | --p6]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import verify_links as V                # noqa: E402
from src.eda.p6_data_issues import borrowed_links as BL            # noqa: E402
from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import flashscore_p6 as FP           # noqa: E402
from src.ingest.point_sources import flashscore_points as F        # noqa: E402

REFUSABLE = ("winner differs", "winner agrees, score differs")
VETO_COLUMNS = ["gap", "uid", "fs_id", "d", "tname", "draw", "name1", "name2", "fs_home", "fs_away", "official",
                "official_score", "fs_sets", "verdict", "surnames"]


def target_order(name1, home) -> bool:
    """True when the Flashscore record's home player is the target's name1 (by the link rule's first surname word)."""
    words = F.surname_words(home)
    return bool(words) and words[0] in F.name_words(name1)


def home_is_name1(name1, name2, fs_home, fs_away) -> bool:
    """Whether the record's home player is the target's name1: the orientation in which more of the two players'
    surnames match (borrowed_links' tolerant test, so "O'Connell C." is Christopher Oconnell, and a surname word both
    target players share, Ribeiro E. against Igor Ribeiro Marcondes and Eduardo Ribeiro, is decided by the other
    player); on a tie, target_order's first surname word. Added 16 Oct 2026: the first-word rule alone reversed the
    sets of such records (9 of P6's links)."""
    a, b = frozenset(BL.name_parts(name1)), frozenset(BL.name_parts(name2))
    home, away = (frozenset(BL.name_parts(F.surname_text(x))) for x in (fs_home, fs_away))
    direct = BL.shares_surname(a, home) + BL.shares_surname(b, away)
    swapped = BL.shares_surname(b, home) + BL.shares_surname(a, away)
    return direct > swapped if direct != swapped else target_order(name1, fs_home)


def record_sets(parsed: dict, home_is_name1: bool) -> list[tuple[int, int]]:
    """The record's games per set in the target's order (name1 first)."""
    sets = [s["score"] for s in parsed["sets"] if s["score"]]
    return sets if home_is_name1 else [(a, h) for h, a in sets]


def compare(sets: list[tuple[int, int]], score) -> str:
    """``sets``: the record's games per set, name1 first, name1 being the official winner (the result files name the
    winner first); ``score``: the official score."""
    sets, theirs = V.unplayed_dropped(sets), V.unplayed_dropped(V.tml_sets(score))   # never-started 0-0 sets out
    if not sets:
        return "no record"
    won = sum(a > b for a, b in sets) - sum(b > a for a, b in sets)
    retired = any(end in str(score or "").upper() for end in ("RET", "DEF"))
    if sets == theirs or (retired and len(sets) == len(theirs) and sets[:-1] == theirs[:-1]):
        return "agrees"
    if won < 0 and not retired:
        return "winner differs"
    return "winner agrees, score differs"


def surnames_agree(name1, name2, fs_home, fs_away) -> bool:
    """P6's surname test (borrowed_links.surnames_agree) on a Flashscore record: in one orientation, each target player
    shares a surname word, or one spelt within the tolerance, with the Flashscore player on its side."""
    a, b = frozenset(BL.name_parts(name1)), frozenset(BL.name_parts(name2))
    home, away = (frozenset(BL.name_parts(F.surname_text(x))) for x in (fs_home, fs_away))
    return any(BL.shares_surname(a, x) and BL.shares_surname(b, y) for x, y in ((home, away), (away, home)))


def refused(verdict: str) -> bool:
    """The official row contradicts the record: another winner, or other games in a set."""
    return verdict in REFUSABLE


def both_tests_fail(surnames: bool, verdict: str) -> bool:
    """The rule first declared (P6's for SofaScore): no surname match, and the official result differs."""
    return not surnames and verdict in REFUSABLE


def check_table(t: pd.DataFrame, label: str) -> tuple[pd.DataFrame, dict]:
    """Each target's verdict (one row per target of a per-target table, read as strings) and the counts."""
    receipts = P.receipts_for(F.SOURCE)
    official = {k[:5]: (k[5], k[6]) for k in V.official_rows(set(t["tname"])).itertuples(index=False)}
    out = []
    for r in t.itertuples(index=False):
        key = (r.tname, pd.Timestamp(r.d).strftime("%Y-%m-%d"), r.name1, r.name2, r.draw)
        score, source = official.get(key, (None, None))
        row = {"gap": r.gap, "edition": getattr(r, "edition", ""), "uid": r.uid, "tour": r.tour,
               "level": getattr(r, "level", ""), "draw": r.draw, "d": r.d, "tname": r.tname, "name1": r.name1,
               "name2": r.name2, "creator": r.creator, "fs_id": r.fs_id, "fs_home": r.fs_home, "fs_away": r.fs_away,
               "official": source, "official_score": score}
        text = F.read_feed(receipts, r.fs_id) if r.fs_id else None
        if not r.fs_id:
            row["verdict"] = "not linked"
        elif F.feed_status(receipts, r.fs_id) == "not fetched":
            row["verdict"] = "not fetched"
        elif text is None:
            row["verdict"] = "no record"
        else:
            sets = record_sets(F.parse_feed(text), home_is_name1(r.name1, r.name2, r.fs_home, r.fs_away))
            row["fs_sets"] = " ".join(f"{a}-{b}" for a, b in sets)
            row["verdict"] = "no official row" if source is None else compare(sets, score)
        row["surnames"] = surnames_agree(r.name1, r.name2, r.fs_home, r.fs_away) if r.fs_id else None
        row["link_refused"] = bool(r.fs_id) and refused(row["verdict"])
        row["both_tests_fail"] = bool(r.fs_id) and both_tests_fail(row["surnames"], row["verdict"])
        out.append(row)
    frame = pd.DataFrame(out)
    month = pd.to_datetime(frame["d"]).dt.strftime("%Y-%m")
    linked = frame[frame["fs_id"].astype(bool)]
    summary = {"table": label, "generated_at": P.utc_now_iso(),
               "verdicts": frame["verdict"].value_counts().to_dict(),
               "by_month": {m: g["verdict"].value_counts().to_dict() for m, g in frame.groupby(month)},
               "by_gap_year": {f"{g}|{y}": x["verdict"].value_counts().to_dict()
                               for (g, y), x in frame.groupby([frame["gap"], pd.to_datetime(frame["d"]).dt.year])},
               "by_official_file": {str(k): g["verdict"].value_counts().to_dict()
                                    for k, g in frame.groupby(frame["official"].fillna("none"))},
               "no_official_row_by_creator": frame.loc[frame["verdict"].eq("no official row"), "creator"]
               .value_counts().to_dict(),
               "surnames_differ_by_verdict": linked.loc[~linked["surnames"].astype(bool), "verdict"]
               .value_counts().to_dict(),
               "link_refused": int(frame["link_refused"].sum()),
               "both_tests_fail": int(frame["both_tests_fail"].sum()),
               "verdict_by_surnames": {str(k): g["verdict"].value_counts().to_dict()
                                       for k, g in linked.groupby(linked["surnames"].astype(str))},
               "differs_examples": frame[frame["verdict"].isin(REFUSABLE)]
               [["d", "tname", "name1", "name2", "fs_home", "fs_away", "official_score", "fs_sets", "verdict",
                 "surnames"]].head(30).astype(str).to_dict(orient="records")}
    return frame, summary


def check(gap: str) -> tuple[pd.DataFrame, dict]:
    """P13's table of ``gap``."""
    frame, summary = check_table(pd.read_csv(F.table_path(gap, "matches"), dtype=str, keep_default_na=False), gap)
    return frame, {"gap": gap, **summary}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gap", default=F.DEFAULT_GAP)
    parser.add_argument("--p6", action="store_true", help="P6's ATP and Challenger records (flashscore_p6.py)")
    args = parser.parse_args()
    P.configure_stdout()
    if args.p6:
        frame, summary = check_table(pd.read_csv(FP.OUT / "fetch_matches.csv.gz", dtype=str, keep_default_na=False),
                                     "p6")
        frame.to_csv(FP.OUT / "link_check.csv.gz", index=False)
        frame.loc[frame["link_refused"], VETO_COLUMNS].to_csv(FP.VETOES, index=False)
        summary_path = FP.OUT / "link_check.json"
    else:
        frame, summary = check(args.gap)
        frame.to_csv(F.table_path(args.gap, "link_check"), index=False)
        summary_path = F.STUDY / f"flashscore_{args.gap}_link_check.json"
    summary_path.write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("verdicts", "no_official_row_by_creator", "verdict_by_surnames",
                                              "link_refused", "both_tests_fail", "differs_examples")},
                     indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
