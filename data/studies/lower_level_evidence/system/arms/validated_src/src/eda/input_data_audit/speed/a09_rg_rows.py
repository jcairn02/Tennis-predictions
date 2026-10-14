"""Audit step 9: the raw rows of RG 2022/2023/2024 (Hawk-Eye copy): how faults and second serves are recorded."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 30)
B = ROOT / "data/dump/points/slam_ball_tracking"
cols = ["match_id", "tour", "point_ID", "set_num", "game_num", "point_num", "serve_num", "server_id", "point_end_type",
        "serve_speed_kph", "is_fault", "is_doublefault", "is_ace", "rally_length", "is_track_avail", "x_serve_bounce",
        "y_serve_bounce"]
for y in (2022, 2023, 2024):
    p = pd.read_parquet(B / "points" / f"RG_{y}.parquet", columns=cols)
    p["spd"] = pd.to_numeric(p["serve_speed_kph"].astype(str).str.extract(r"([\d.]+)")[0], errors="coerce")
    print(f"\n===== RG {y}: rows {len(p)}; matches {p['match_id'].nunique()}")
    print(pd.crosstab(p["point_end_type"].astype(str), p["serve_num"].astype(str), margins=True))
    # per point id: how many rows (1 = no fault row, 2 = fault + point)
    pid = p["point_ID"].astype(str).str.rsplit("_", n=1).str[0]
    p["pkey"] = p["match_id"].astype(str) + "|" + pid
    cnt = p.groupby("pkey").size()
    print("rows per point:", cnt.value_counts().to_dict())
    m = p["match_id"].iloc[0] if y != 2024 else p["match_id"].unique()[3]
    s = p[p["match_id"] == m].head(40)
    print(s[["match_id", "point_ID", "serve_num", "server_id", "point_end_type", "serve_speed_kph", "is_fault",
             "is_doublefault", "rally_length"]].to_string(index=False))
    # second-serve points with and without a fault row before them
    sec = p[p["serve_num"].astype(str).eq("2") & ~p["point_end_type"].astype(str).eq("Faulty Serve")]
    has_fault = sec["pkey"].isin(set(p.loc[p["point_end_type"].astype(str).eq("Faulty Serve"), "pkey"]))
    print("second-serve point rows:", len(sec), "with a fault row:", int(has_fault.sum()))
    for tour in ("M", "W"):
        k = sec["tour"].astype(str).eq(tour)
        print(f"  {tour}: second-serve speed median with fault row {sec.loc[k & has_fault, 'spd'].median()}, "
              f"without {sec.loc[k & ~has_fault, 'spd'].median()}; n {int((k & has_fault).sum())} / {int((k & ~has_fault).sum())}")
    # by match: share of second-serve points lacking a fault row
    g = sec.assign(nf=~has_fault).groupby("match_id")["nf"].mean()
    print("share of 2nd-serve points without fault row, by match: quantiles", g.quantile([0, .1, .25, .5, .75, .9, 1]).round(2).to_dict())
