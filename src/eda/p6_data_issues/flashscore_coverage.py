"""How many of the P6 targets SofaScore has no point record for could Flashscore fill (docs/studies/p6_data_issues/)?

Offline. The Flashscore copy on disk (the Hugging Face handoff, data/raw/public_dump/atp_pipeline_handoff/
flashscore_full/) has no points, but each record lists Flashscore's own tabs (``available_data``), and "MH" is the
point-by-point tab, which Flashscore's live site serves as a complete record (work package P13's research,
docs/research/gap-sources/itf_2025_points.md: 4 of 4 checked). So a target linked to a record with MH has a complete
point record one request away.

1. **Index** (--index; once): every record of the copy dated 2017-12-15 or later, one row per Flashscore match id
   (the richest copy kept): date, category, tournament, players and their slugs, set scores, duration, tabs.
   Written to the session scratchpad (--index-path), not tracked: about a million rows.
2. **Targets:** the gap tables of the ATP gap and P6's seven (data/studies/gap_downloads/sofascore_<gap>_matches.csv)
   with no SofaScore point record (not linked, or HTTP 404).
3. **Link:** each target to the record of its tour (men: ATP, Challenger and ITF men's categories; women: WTA and ITF
   women's) dated from 3 days before to 14 after the target's date, whose two players each share a name word with a
   different target player (sofascore_editions.pair_score on the record's names and slugs); the most words shared,
   then the nearest date.
4. **Count** by gap, year, level and draw: linked; with the point-by-point tab; with a duration.

Writes data/studies/p6_data_issues/flashscore/coverage.csv (counts), targets.csv.gz (one row per target: its record,
tabs, duration) and summary.json.

Usage: ./python.sh src/eda/p6_data_issues/flashscore_coverage.py [--index] [--index-path <parquet>]
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import sofascore_editions as E     # noqa: E402

HANDOFF = PROJECT_ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff" / "flashscore_full"
OUT = PROJECT_ROOT / "data" / "studies" / "p6_data_issues" / "flashscore"
GAPS = ["atp_points_2025", "challenger_points_2025", "wta125_points_2019_2026", "tour_points_rest",
        "challenger_points_2022_2024", "atp_points_2018_2020", "wta_2018_points", "challenger_points_2018_2021"]
FIELDS = ["match_id", "match_date", "category", "tournament_name", "tournament_slug", "round", "home_player",
          "away_player", "home_player_slug", "away_player_slug", "set_scores", "match_duration", "available_data"]
WINDOW = (-3, 14)


def tour_of(category: str):
    c = str(category or "").lower()
    if "wta" in c or "women" in c:
        return "W"
    if "atp" in c or "challenger" in c or "men" in c:
        return "M"
    return None


def build_index(path: Path) -> pd.DataFrame:
    """Every record dated from mid-December 2017, one per match id, the copy with the most fields filled kept."""
    best: dict[str, dict] = {}
    for name in sorted(glob.glob(str(HANDOFF / "flashscore_full_*.jsonl*"))):
        opener = gzip.open if name.endswith(".gz") else open
        with opener(name, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                mid, day = r.get("match_id"), str(r.get("match_date") or "")
                if not mid or day < "20171215":
                    continue
                row = {f: r.get(f) for f in FIELDS}
                filled = sum(v not in (None, "", "None") for v in row.values())
                if mid not in best or filled > best[mid][1]:
                    best[mid] = (row, filled)
    frame = pd.DataFrame([v[0] for v in best.values()])
    frame["d"] = pd.to_datetime(frame["match_date"], format="%Y%m%d", errors="coerce")
    frame["tour"] = frame["category"].map(tour_of)
    frame["mh"] = frame["available_data"].fillna("").str.split(",").map(lambda tabs: "MH" in tabs)
    frame["has_duration"] = frame["match_duration"].fillna("").str.contains(":")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.astype({c: "string" for c in FIELDS}).to_parquet(path, index=False)
    return frame


def missing_targets() -> pd.DataFrame:
    """The targets of each gap with no SofaScore point record."""
    frames = []
    for gap in GAPS:
        m = pd.read_csv(E.targets_path(gap), low_memory=False, parse_dates=["d"])
        m = m[~pd.to_numeric(m["pbp_status"], errors="coerce").eq(200)]
        frames.append(m[E.TARGET_COLUMNS + ["listed", "pbp_status"]])
    return pd.concat(frames, ignore_index=True)


def link(targets: pd.DataFrame, index: pd.DataFrame) -> pd.DataFrame:
    index = index[index["tour"].notna() & index["d"].notna()].copy()
    index["hw"] = [E.words(a) | E.words(str(b or "").replace("-", " "))
                   for a, b in zip(index["home_player"], index["home_player_slug"])]
    index["aw"] = [E.words(a) | E.words(str(b or "").replace("-", " "))
                   for a, b in zip(index["away_player"], index["away_player_slug"])]
    by_tour_day = {k: g for k, g in index.groupby(["tour", "d"])}
    out = []
    for t in targets.itertuples(index=False):
        a, b = E.words(t.name1), E.words(t.name2)
        best, key = None, None
        for off in range(WINDOW[0], WINDOW[1] + 1):
            day = pd.Timestamp(t.d) + pd.Timedelta(days=off)
            g = by_tour_day.get((t.tour, day))
            if g is None:
                continue
            for r in g.itertuples(index=False):
                score = E.pair_score(a, b, r.hw, r.aw)
                if score and (key is None or (score, -abs(off)) > key):
                    best, key = r, (score, -abs(off))
        row = {c: getattr(t, c) for c in ("gap", "uid", "tour", "level", "draw", "year", "d", "tname", "name1",
                                          "name2", "creator", "listed", "pbp_status")}
        if best is not None:
            row.update(fs_id=best.match_id, fs_date=best.d.date(), fs_category=best.category,
                       fs_tournament=best.tournament_name or best.tournament_slug, fs_home=best.home_player,
                       fs_away=best.away_player, fs_score=best.set_scores, fs_duration=best.match_duration,
                       fs_tabs=best.available_data, fs_mh=bool(best.mh), fs_has_duration=bool(best.has_duration))
        out.append(row)
    return pd.DataFrame(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--index", action="store_true", help="(re)build the index of the handoff copy")
    parser.add_argument("--index-path", required=True, help="where the index is kept (the session scratchpad)")
    args = parser.parse_args()
    path = Path(args.index_path)
    index = build_index(path) if args.index or not path.exists() else pd.read_parquet(path)
    if "d" not in index or index["d"].dtype == object:
        index["d"] = pd.to_datetime(index["match_date"], format="%Y%m%d", errors="coerce")
    for col in ("mh", "has_duration"):
        index[col] = index[col].astype(str).eq("True") if index[col].dtype != bool else index[col]
    targets = missing_targets()
    linked = link(targets, index)
    OUT.mkdir(parents=True, exist_ok=True)
    linked.to_csv(OUT / "targets.csv.gz", index=False, compression="gzip")
    linked["found"] = linked["fs_id"].notna() if "fs_id" in linked else False
    for col in ("fs_mh", "fs_has_duration"):
        linked[col] = linked.get(col, pd.Series(False, index=linked.index)).fillna(False).astype(bool)
    cov = (linked.groupby(["gap", "year", "level", "draw"])
           .agg(targets=("uid", "size"), flashscore_record=("found", "sum"), point_tab=("fs_mh", "sum"),
                duration=("fs_has_duration", "sum")).reset_index())
    cov.to_csv(OUT / "coverage.csv", index=False)
    summary = {"index_records": int(len(index)), "index_by_category": index["category"].value_counts().head(20).to_dict(),
               "targets_without_sofascore_points": int(len(linked)),
               "with_a_flashscore_record": int(linked["found"].sum()), "with_the_point_tab": int(linked["fs_mh"].sum()),
               "with_a_duration": int(linked["fs_has_duration"].sum()),
               "by_gap": {g: {"targets": int(len(x)), "record": int(x["found"].sum()), "point_tab": int(x["fs_mh"].sum())}
                          for g, x in linked.groupby("gap")}}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
