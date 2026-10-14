"""Stage 1, part 1: the common point table, built from every point-level source (src/eda/shot_level/points.py).

Writes one Parquet per source, data/studies/shot_level/stage1_points_<source>.parquet (gitignored), and a census of
what each source's points carry by year (stage1_points_census.csv): points, and the share with a rally length, with a
classified ending (and of which kind), with the last shot's hitter, the serve number, the serve speed, the placement,
net flags, return depth and the wing. The census is how the statistics' definitions were checked against the sources
before any statistic was computed; nothing here reads who won a match.

Run:  ./python.sh src/eda/shot_level/stage1_points.py [--only slam_pbp,mcp,...] [--workers 5]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import points as P  # noqa: E402


def census(pts: pd.DataFrame, years: pd.Series) -> pd.DataFrame:
    d = pts.assign(year=pts["key"].map(years))
    end = d["end"]
    rows = []
    for (src, y), g in d.groupby(["source", "year"], dropna=False):
        e = g["end"]
        rows.append({"source": src, "year": y, "matches": g["key"].nunique(), "points": len(g),
                     "rally_known": (g["rally"] >= 0).mean(), "end_known": (e > 0).mean(),
                     **{f"end_{k}": (e == v).mean() for k, v in P.END.items() if v > 0},
                     "ender_known": (g["ender"] > 0).mean(), "serve_no_known": (g["serve_no"] > 0).mean(),
                     "second_serve_share": (g["serve_no"] == 2).sum() / max((g["serve_no"] > 0).sum(), 1),
                     "speed_known": g["speed"].notna().mean(), "place_known": (g["place"] > 0).mean(),
                     "net_known": (g["net1"] >= 0).mean(), "net_share": ((g["net1"] > 0) | (g["net2"] > 0)).sum() / max((g["net1"] >= 0).sum(), 1),
                     "ret_deep_known": (g["ret_deep"] >= 0).mean(), "wing_known": (g["wing"] > 0).mean(),
                     "mean_rally": g.loc[g["rally"] > 0, "rally"].mean(),
                     "ace_rally_1": ((g["rally"] == 1) & (e == P.END["ace"])).sum() / max((e == P.END["ace"]).sum(), 1),
                     "server_won": (g["server"] == g["winner"]).mean()})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=5)
    args = ap.parse_args()
    only = [x for x in args.only.split(",") if x] or list(P.ADAPTERS)
    src = pd.read_parquet(S.OUT / "stage0_source_matches.parquet", columns=["source", "key", "year"])
    cens = []
    for name in only:
        S.log(f"building {name}")
        fn = P.ADAPTERS[name]
        pts = fn(args.workers) if name == "infosys" else fn()
        years = src[src["source"].eq(name)].drop_duplicates("key").set_index("key")["year"]
        known = pts["key"].isin(years.index)
        S.log(f"  {len(pts)} points in {pts['key'].nunique()} matches; {int(known.sum())} points in matches Stage 0 lists")
        pts.to_parquet(S.OUT / f"stage1_points_{name}.parquet", index=False)
        cens.append(census(pts, years))
    c = pd.concat(cens, ignore_index=True)
    path = S.OUT / "stage1_points_census.csv"
    if args.only and path.exists():
        old = pd.read_csv(path)
        c = pd.concat([old[~old["source"].isin(only)], c], ignore_index=True)
    c.to_csv(path, index=False)
    S.log(f"wrote stage1_points_*.parquet and {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
