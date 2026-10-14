"""A seeded sample of the data map's gaps, for checking candidate sources match by match.

Each gap in data/data_map.yaml whose selection has a ``below`` grain is a set of known matches that lack
that grain (data/studies/data_map/matches.parquet). The sample is drawn in two stages, so that every
match of a stratum has about the same chance of being checked:

1. tournament editions, with probability proportional to their number of gap matches (without
   replacement), a fixed number per stratum;
2. a fixed number of gap matches in each drawn edition, uniformly ("check" rows).

The drawn editions' other gap matches are kept too ("listing" rows): a source's listing can be measured
on all of them for the cost of listing the edition once.

The Grand Slam gap is small enough to take every edition (tour, Slam and year) and draw matches within
each. The women's shot gap is left out: no source probed with this sample holds shots.

Usage:
    ./python.sh src/eda/gap_sources/sample.py [--seed 20260929]

Writes data/studies/gap_sources/sample_editions.csv and sample_matches.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MATCHES = PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet"
CATALOG = PROJECT_ROOT / "data" / "data_map.yaml"
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources"

GRAIN_RANK = {"result": 1, "stats": 2, "point": 3, "shot": 4}

# gap id -> (stratum columns, editions drawn per stratum or a dict per stratum, matches checked per edition)
PLAN = {
    "itf_detail": (["tour", "year"], 2, 3),
    "challenger_points_2025": (["year"], {2025: 5, 2026: 3}, 4),
    "atp_points_2025": (["year"], {2025: 6, 2026: 3}, 4),
    "wta_2018_points": (["year"], 8, 4),
    "slam_points_ao_rg": (["tour", "tname", "year"], None, 2),   # None: every edition
}


def gap_population(m: pd.DataFrame, select: dict) -> pd.DataFrame:
    sel = m["tour"].isin(select["tours"]) & m["level"].isin(select["levels"]) & m["year"].isin(select["years"])
    sel &= m["best"].map(GRAIN_RANK) < GRAIN_RANK[select["below"]]
    return m[sel].copy()


def edition_key(frame: pd.DataFrame, slam: bool) -> pd.Series:
    """Tour, tournament name and year; outside the Slams also the ISO week of the tournament start."""
    base = frame["tour"] + "|" + frame["tname"].fillna("") + "|" + frame["year"].astype(str)
    if slam:
        return base
    week = frame["d"].dt.isocalendar().week.astype(str).str.zfill(2)
    return base + "|w" + week


def draw(seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = pd.read_parquet(MATCHES)
    gaps = {g["id"]: g for g in yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["gaps"]}
    rng = np.random.default_rng(seed)
    editions, matches = [], []
    for gap_id, (strata_cols, per_stratum, k) in PLAN.items():
        pop = gap_population(m, gaps[gap_id]["select"])
        pop["edition"] = edition_key(pop, slam=gap_id == "slam_points_ao_rg")
        # the universe's matches of the same editions, gap or not, help locate an edition elsewhere
        uni = m[m["tour"].isin(pop["tour"].unique())].copy()
        uni["edition"] = edition_key(uni, slam=gap_id == "slam_points_ao_rg")
        sizes_all = uni.groupby("edition").size()
        for stratum, g in pop.groupby(strata_cols):
            stratum = stratum if isinstance(stratum, tuple) else (stratum,)
            label = "|".join(str(s) for s in stratum)
            sizes = g.groupby("edition").size()
            if per_stratum is None:
                chosen = list(sizes.index)
                prob = pd.Series(1.0, index=sizes.index)
            else:
                n = per_stratum[stratum[-1]] if isinstance(per_stratum, dict) else per_stratum
                n = min(n, len(sizes))
                p = (sizes / sizes.sum()).to_numpy()
                chosen = list(rng.choice(sizes.index.to_numpy(), size=n, replace=False, p=p))
                prob = (n * sizes / sizes.sum()).clip(upper=1.0)   # first-order inclusion, approximately
            for ed in chosen:
                em = g[g["edition"] == ed]
                pick = set(rng.choice(em["uid"].to_numpy(), size=min(k, len(em)), replace=False))
                editions.append({
                    "gap": gap_id, "stratum": label, "edition": ed, "tour": em["tour"].iloc[0],
                    "tname": em["tname"].iloc[0], "year": int(em["year"].iloc[0]),
                    "d_min": em["d"].min().date(), "d_max": em["d"].max().date(),
                    "levels": ";".join(sorted(em["level"].unique())), "gap_matches": len(em),
                    "edition_matches": int(sizes_all.get(ed, len(em))), "stratum_gap_matches": int(len(g)),
                    "stratum_editions": int(len(sizes)), "inclusion_prob": round(float(prob[ed]), 5),
                    "checked": len(pick)})
                em = em.assign(gap=gap_id, stratum=label,
                               role=np.where(em["uid"].isin(pick), "check", "listing"))
                matches.append(em)
    cols = ["gap", "stratum", "edition", "role", "uid", "tour", "level", "draw", "year", "d", "name1", "name2",
            "tname", "creator", "best", "sources"]
    return pd.DataFrame(editions), pd.concat(matches, ignore_index=True)[cols]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=20260929)
    args = parser.parse_args()
    editions, matches = draw(args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    editions.to_csv(OUT / "sample_editions.csv", index=False)
    matches["d"] = matches["d"].dt.date
    matches.to_csv(OUT / "sample_matches.csv", index=False)
    print(editions.groupby("gap").agg(editions=("edition", "size"), gap_matches=("gap_matches", "sum"),
                                      checked=("checked", "sum")).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
