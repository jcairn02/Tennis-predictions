"""Audit step 2: raw Hawk-Eye Court Vision copy (slam_ball_tracking) schemas and AO 2024 serve_speed_kph strings."""
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path.cwd()
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_colwidth", 80)
B = ROOT / "data/dump/points/slam_ball_tracking"
for sub in ("points", "json_points", "shots"):
    for f in sorted((B / sub).glob("*.parquet")):
        print(sub, f.name, pq.read_metadata(f).num_rows, pq.read_schema(f).names)
print("matches", pq.read_schema(B / "matches.parquet").names)
print("json_matches", pq.read_schema(B / "json_matches.parquet").names)

m = pd.read_parquet(B / "matches.parquet")
print(m.groupby(["slam", "year"]).size())
print(m.head(3).T)
for y in (2022, 2023, 2024):
    p = pd.read_parquet(B / "points" / f"AO_{y}.parquet")
    print(f"\n=== AO {y} points: {len(p)} rows")
    print(p.head(3).T)
    s = p["serve_speed_kph"].astype(str)
    print("serve_speed_kph sample:", s.sample(15, random_state=1).tolist())
    # pattern classes of the string
    pat = s.str.replace(r"\d", "9", regex=True)
    print(pat.value_counts().head(15))
    print(p["point_end_type"].value_counts())
    print(p["serve_num"].value_counts(dropna=False))
