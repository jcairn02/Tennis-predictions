"""Audit step 3: what the raw AO Hawk-Eye copy's speed fields are, CSV vs JSON, per year (read-only)."""
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path.cwd()
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_colwidth", 120)
B = ROOT / "data/dump/points/slam_ball_tracking"
print("shots schema", pq.read_schema(B / "shots" / "AO_2024.parquet").names)

for y in (2022, 2023, 2024):
    p = pd.read_parquet(B / "points" / f"AO_{y}.parquet", columns=["match_id", "tour", "point_ID", "serve_num", "serve_speed_kph",
                                                                   "point_end_type", "is_fault", "is_doublefault", "is_ace",
                                                                   "server_id", "spin_rpm", "is_track_avail"])
    s = p["serve_speed_kph"].astype(str)
    unit = s.str.replace(r"[\d.\s-]", "", regex=True)
    print(f"\n=== AO {y} CSV points {len(p)}; units: {unit.value_counts().to_dict()}")
    v = pd.to_numeric(s.str.extract(r"([\d.]+)")[0], errors="coerce")
    dec = s.str.contains(r"\.\d", regex=True)
    pet = p["point_end_type"].astype(str)
    print(pd.crosstab(pet, dec, margins=True))
    print("zero speeds by type:", pd.crosstab(pet, v.eq(0)).iloc[:, -1].to_dict())
    j = pd.read_parquet(B / "json_points" / f"AO_{y}.parquet")
    print("json rows", len(j))
    print(j[["match_id", "point_key", "pointId", "ballSpeed", "ballSpeedFrench", "returnSpeed", "returnSpeedFrench",
             "serve", "pointEndType", "serveType", "strokeType", "rallyLength", "court", "other_fields"]].head(6).to_string())
    # ballSpeed strings
    for c in ("ballSpeed", "ballSpeedFrench"):
        bs = j[c].astype(str)
        print(c, "patterns:", bs.str.replace(r"\d", "9", regex=True).value_counts().head(8).to_dict())
