"""Real coverage of the shot-level per-player values (feature-interactions data map, round 0).

data/studies/shot_level/stage3_sides.parquet holds every shot-level statistic for A and B ("A|<stat>|<side>|<form>"),
with a prior where a player has no data, and an indicator "A|<stat>|<side>|<form>|has". Its plain columns are therefore
never missing; this script measures the share of model matches where BOTH players have real data (both |has = 1), by
tour and period (d = 2013-2021, r = 2022-2024). Counts only. Read-only.
Writes data/studies/feature_interactions/inventory/coverage_shot_sides.csv.
Run: ./python.sh src/eda/feature_interactions/inventory/shot_sides.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[4]
S = ROOT / "data" / "studies"
OUT = S / "feature_interactions" / "inventory"
MODEL = S / "surface_rating_race" / "model" / "model_frame.parquet"
SIDES = S / "shot_level" / "stage3_sides.parquet"


def main() -> int:
    mf = pd.read_parquet(MODEL, columns=["match_id", "season", "tour"])
    mf = mf[mf["season"] <= 2024].reset_index(drop=True)
    mf["period"] = np.where(mf["season"] <= 2021, "d", "r")
    names = pq.read_schema(SIDES).names
    has = [n for n in names if n.startswith("A|") and n.endswith("|has")]
    rows = []
    for i in range(0, len(has), 60):
        chunk = has[i:i + 60]
        cols = ["match_id"] + chunk + ["B" + c[1:] for c in chunk]
        d = mf[["match_id"]].merge(pq.read_table(SIDES, columns=cols).to_pandas(), on="match_id", how="left")
        for c in chunk:
            both = (d[c].fillna(0).to_numpy() > 0.5) & (d["B" + c[1:]].fillna(0).to_numpy() > 0.5)
            r = {"feature": c[2:-4]}
            for t in ("atp", "wta"):
                for p in ("d", "r"):
                    m = (mf["tour"].to_numpy() == t) & (mf["period"].to_numpy() == p)
                    r[f"cov_{t}_{p}"] = round(float(both[m].mean()), 4)
            rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "coverage_shot_sides.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 300):
        print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
