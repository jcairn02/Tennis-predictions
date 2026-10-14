"""An independent check of lane A's replay of the hawkilol Court Vision copy, on a seeded sample.

Lane A (hawkilol_matches.py) labels a match "complete" when its per-point rows replay to the official score.
Its session was stopped while it was reworking that replay, so this re-derives the games of each set with
separate, simpler code and compares them with the official score, for a seeded sample of the matches
labelled complete in the AO/RG gap of 2022-24:

* a game's winner is the winner of its last point row (the row with the highest point and serve number);
* a set's games are counted per player id; the set is compared with the official set as an unordered pair
  of game counts (orientation is not needed for a completeness check).

Usage:
    ./python.sh src/eda/gap_sources/hawkilol_spotcheck.py [--n 40]

Reads data/studies/gap_sources/hawkilol_matches.csv and data/raw/gap_sources/hawkilol/pbp_data_csvs/.
Writes data/studies/gap_sources/hawkilol_spotcheck.csv.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW = PROJECT_ROOT / "data" / "raw" / "gap_sources" / "hawkilol"
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "hawkilol_spotcheck.csv"


def official_sets(score: str) -> list[tuple[int, int]]:
    """'7-6(5) 3-6 6-4' -> [(7, 6), (3, 6), (6, 4)]; retirement marks and the like are ignored."""
    return [(int(a), int(b)) for a, b in re.findall(r"(\d+)-(\d+)", re.sub(r"\(\d+\)", "", str(score or "")))]


def replay_sets(path: Path) -> list[tuple[int, int]]:
    p = pd.read_csv(path, low_memory=False)
    for c in ("set_num", "game_num", "point_num", "serve_num"):
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p = p.dropna(subset=["set_num", "game_num", "point_num", "point_winner_id"])
    last = p.sort_values(["set_num", "game_num", "point_num", "serve_num"]).groupby(["set_num", "game_num"]).tail(1)
    out = []
    for _, s in last.groupby("set_num"):
        counts = s["point_winner_id"].astype(str).value_counts()
        vals = sorted(counts.tolist() + [0] * (2 - len(counts)), reverse=True)[:2]
        out.append((vals[0], vals[1]))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=40)
    args = parser.parse_args()
    h = pd.read_csv(PROJECT_ROOT / "data" / "studies" / "gap_sources" / "hawkilol_matches.csv", low_memory=False)
    in_gap = h["fills_slam_points"].astype(str).str.lower().eq("true") | h["gap"].astype(str).str.contains("slam", na=False)
    pool = h[in_gap & h["year"].between(2022, 2024) & h["pbp_status"].eq("complete")]
    sample = pool.sample(min(args.n, len(pool)), random_state=20260929)
    rows = []
    for r in sample.itertuples(index=False):
        want = [tuple(sorted(s, reverse=True)) for s in official_sets(r.official_score)]
        got = replay_sets(RAW / r.file)
        rows.append({"year": r.year, "slam": r.slam, "event": r.event, "match_id": r.match_id,
                     "official_score": r.official_score, "official_sets": want, "replayed_sets": got,
                     "agrees": got == want})
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT, index=False)
    print(f"{int(frame['agrees'].sum())} of {len(frame)} sampled 'complete' matches replay to the official score")
    print(frame[~frame["agrees"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
