"""What the data map holds for the P6 targets that the Flashscore fetch asked about (read-only).

The targets are the 3,480 whose record in the Flashscore copy lists the point-by-point tab
(data/studies/p6_data_issues/flashscore/targets.csv.gz). Each is found on the map's match table
(data/studies/data_map/matches.parquet) by its key as frozen with P6's targets (tour, tournament, date, both names);
a target whose key the map no longer holds (a match re-dated or merged since 12 Oct) is counted as not found. For the
targets found: the map's best grain, and whether its sources include TennisLive's gap pages (P5; points with the
set-closing games usually missing), Flashscore's feeds and the ATP's Challenger files. When the fetch's own table is
on disk, also: the feed's outcome and whether the link was refused.

Run before and after the map rebuild:
    ./python.sh src/eda/p6_data_issues/checks/flashscore_on_map.py [--out <json>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
FLASH = ROOT / "data" / "studies" / "p6_data_issues" / "flashscore"
SOURCES = ["tennislive_gaps", "flashscore_points", "infosys_challengers", "sofascore_editions"]


def key(f: pd.DataFrame) -> pd.Series:
    d = pd.to_datetime(f["d"]).dt.strftime("%Y-%m-%d")
    return f["tour"] + "|" + f["tname"].fillna("") + "|" + d + "|" + f["name1"].fillna("") + "|" + f["name2"].fillna("")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", help="also write the counts to this JSON file")
    args = parser.parse_args()
    t = pd.read_csv(FLASH / "targets.csv.gz", dtype=str, keep_default_na=False)
    t = t[t["fs_mh"].eq("True")].copy()
    fetch = FLASH / "fetch_matches.csv.gz"
    if fetch.exists():
        f = pd.read_csv(fetch, dtype=str, keep_default_na=False)
        if len(f) == len(t):                                  # the whole run's table, not a trial's
            cols = [c for c in ("feed_status", "fb_verdict", "link_refused") if c in f]
            t = t.merge(f[["gap", "uid", "fs_id"] + cols], on=["gap", "uid", "fs_id"], how="left")
    m = pd.read_parquet(ROOT / "data" / "studies" / "data_map" / "matches.parquet",
                        columns=["uid", "tour", "tname", "d", "name1", "name2", "best", "sources"])
    m["key"] = key(m)
    m = m.drop_duplicates("key")
    t["key"] = key(t)
    t = t.merge(m[["key", "uid", "best", "sources"]].rename(columns={"uid": "map_uid"}), on="key", how="left")
    t["found"] = t["map_uid"].notna()
    t["point"] = t["best"].isin(["point", "shot"])
    for s in SOURCES:
        t[s] = t["sources"].fillna("").str.split(";").map(lambda xs, s=s: s in xs)

    def cell(g: pd.DataFrame) -> dict:
        out = {"targets": int(len(g)), "found": int(g["found"].sum()), "point_or_shot": int(g["point"].sum())}
        out.update({s: int(g[s].sum()) for s in SOURCES})
        out["point_without_tennislive_pages"] = int((g["point"] & ~g["tennislive_gaps"]).sum())
        if "fb_verdict" in g:
            out["feed_complete"] = int(g["fb_verdict"].eq("complete").sum())
            out["link_refused"] = int(g["link_refused"].eq("True").sum())
            # a complete record on the map for the target itself: its link kept, the map's match carrying Flashscore
            done = g["flashscore_points"] & g["fb_verdict"].eq("complete") & ~g["link_refused"].eq("True")
            out["complete_flashscore_placed"] = int(done.sum())
            out["complete_flashscore_where_tennislive_pages"] = int((done & g["tennislive_gaps"]).sum())
            out["complete_flashscore_where_no_point_before"] = int((done & ~g["tennislive_gaps"]
                                                                    & ~g["infosys_challengers"]
                                                                    & ~g["sofascore_editions"]).sum())
        return out

    year = pd.to_datetime(t["d"]).dt.year.astype(str)
    summary = {"map_built": pd.Timestamp((ROOT / "data/studies/data_map/matches.parquet").stat().st_mtime,
                                         unit="s").strftime("%Y-%m-%d %H:%M UTC"),
               "all": cell(t), "by_gap": {g: cell(x) for g, x in t.groupby("gap")},
               "by_gap_year": {f"{g}|{y}": cell(x) for (g, y), x in t.groupby([t["gap"], year])}}
    print(json.dumps({k: summary[k] for k in ("map_built", "all", "by_gap")}, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
