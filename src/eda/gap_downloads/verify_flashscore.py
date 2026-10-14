"""Check Flashscore's point records (work package P13) against the official result: does each record have the target
match's winner and set scores?

For every target of the gap's Flashscore table (data/studies/gap_downloads/flashscore_<gap>_matches.csv.gz) with a
point record on disk, the record's sets (the games after each set's last game) and winner are compared with the result
file the map took the target from: Tennis My Life's or Sackmann's row for the same match, found as verify_links.py
finds it (tournament, date, both names, draw; Tennis My Life's row first). The Flashscore players are put in the
target's order by the link rule's surname words. Verdicts, as verify_links.py's:
    agrees                       same winner, same games in every set (at a retirement, all but the unfinished set)
    winner agrees, score differs
    winner differs               a wrong link, or a result recorded differently
    no official row              the target came from a file this check does not read (TennisLive's listings, the
                                 WTA website records ...); the ``creator`` column names it
    no record                    the feed was empty; not fetched: not asked yet; not linked: no Flashscore record named
                                 the pair

Writes data/studies/gap_downloads/flashscore_<gap>_link_check.csv.gz (one row per target) and
flashscore_<gap>_link_check.json (counts overall, by month and by the file read).

Usage: ./python.sh src/eda/gap_downloads/verify_flashscore.py [--gap itf_points_2025_2026]
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
from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import flashscore_points as F        # noqa: E402


def target_order(name1, home) -> bool:
    """True when the Flashscore record's home player is the target's name1 (by the link rule's first surname word)."""
    words = F.surname_words(home)
    return bool(words) and words[0] in F.name_words(name1)


def record_sets(parsed: dict, home_is_name1: bool) -> list[tuple[int, int]]:
    """The record's games per set in the target's order (name1 first)."""
    sets = [s["score"] for s in parsed["sets"] if s["score"]]
    return sets if home_is_name1 else [(a, h) for h, a in sets]


def compare(sets: list[tuple[int, int]], score) -> str:
    """``sets``: the record's games per set, name1 first, name1 being the official winner (the result files name the
    winner first); ``score``: the official score."""
    theirs = V.tml_sets(score)
    if not sets:
        return "no record"
    won = sum(a > b for a, b in sets) - sum(b > a for a, b in sets)
    retired = any(end in str(score or "").upper() for end in ("RET", "DEF"))
    if sets == theirs or (retired and len(sets) == len(theirs) and sets[:-1] == theirs[:-1]):
        return "agrees"
    if won < 0 and not retired:
        return "winner differs"
    return "winner agrees, score differs"


def check(gap: str) -> tuple[pd.DataFrame, dict]:
    t = pd.read_csv(F.table_path(gap, "matches"), dtype=str, keep_default_na=False)
    receipts = P.receipts_for(F.SOURCE)
    official = {k[:5]: (k[5], k[6]) for k in V.official_rows(set(t["tname"])).itertuples(index=False)}
    out = []
    for r in t.itertuples(index=False):
        key = (r.tname, pd.Timestamp(r.d).strftime("%Y-%m-%d"), r.name1, r.name2, r.draw)
        score, source = official.get(key, (None, None))
        row = {"gap": r.gap, "edition": r.edition, "uid": r.uid, "tour": r.tour, "d": r.d, "tname": r.tname,
               "name1": r.name1, "name2": r.name2, "creator": r.creator, "fs_id": r.fs_id, "fs_home": r.fs_home,
               "fs_away": r.fs_away, "official": source, "official_score": score}
        text = F.read_feed(receipts, r.fs_id) if r.fs_id else None
        if not r.fs_id:
            row["verdict"] = "not linked"
        elif F.feed_status(receipts, r.fs_id) == "not fetched":
            row["verdict"] = "not fetched"
        elif text is None:
            row["verdict"] = "no record"
        else:
            sets = record_sets(F.parse_feed(text), target_order(r.name1, r.fs_home))
            row["fs_sets"] = " ".join(f"{a}-{b}" for a, b in sets)
            row["verdict"] = "no official row" if source is None else compare(sets, score)
        out.append(row)
    frame = pd.DataFrame(out)
    month = pd.to_datetime(frame["d"]).dt.strftime("%Y-%m")
    summary = {"gap": gap, "generated_at": P.utc_now_iso(),
               "verdicts": frame["verdict"].value_counts().to_dict(),
               "by_month": {m: g["verdict"].value_counts().to_dict() for m, g in frame.groupby(month)},
               "by_official_file": {str(k): g["verdict"].value_counts().to_dict()
                                    for k, g in frame.groupby(frame["official"].fillna("none"))},
               "no_official_row_by_creator": frame.loc[frame["verdict"].eq("no official row"), "creator"]
               .value_counts().to_dict(),
               "differs_examples": frame[frame["verdict"].isin(["winner differs", "winner agrees, score differs"])]
               [["d", "tname", "name1", "name2", "fs_home", "fs_away", "official_score", "fs_sets", "verdict"]]
               .head(30).astype(str).to_dict(orient="records")}
    return frame, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gap", default=F.DEFAULT_GAP)
    args = parser.parse_args()
    P.configure_stdout()
    frame, summary = check(args.gap)
    frame.to_csv(F.table_path(args.gap, "link_check"), index=False)
    (F.STUDY / f"flashscore_{args.gap}_link_check.json").write_text(json.dumps(summary, indent=1, default=str) + "\n",
                                                                     encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("verdicts", "no_official_row_by_creator", "differs_examples")},
                     indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
