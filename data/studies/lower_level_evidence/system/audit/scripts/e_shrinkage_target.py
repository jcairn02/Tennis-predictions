"""Role E (red team), CP1: does the boundary statistic (men's def_bp_faced_pg at Challengers, free w at the cap 3) move
the shrinkage target of every statistic? Recomputes B's DerSimonian-Laird level mean (relationship.shrinkage, as
shrink_point applies it: each statistic's free w at its own h*) with and without that statistic. Reads B's outputs of
seasons <= 2024 only (params_round1.parquet, params_points.parquet). Writes audit/shrinkage_target_atp_CH.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

REL = Path(__file__).resolve().parents[2] / "relationship"
OUT = Path(__file__).resolve().parents[1] / "shrinkage_target_atp_CH.csv"


def dl(g):
    w = g["w"].to_numpy(float)
    se = np.maximum(np.nan_to_num(g["se"].to_numpy(float), nan=1.0), 0.02)
    u = 1 / se ** 2
    wfe = (u * w).sum() / u.sum()
    q = (u * (w - wfe) ** 2).sum()
    den = u.sum() - (u ** 2).sum() / u.sum()
    t2 = max(0.0, (q - (len(w) - 1)) / den) if den > 0 else 0.0
    v = 1 / (se ** 2 + t2)
    return (v * w).sum() / v.sum(), t2


p1 = pd.read_parquet(REL / "params_round1.parquet")
pts = pd.read_parquet(REL / "params_points.parquet")
hstar = {(r.stat, r.tour, r.season): r.h for r in pts.itertuples()}
r = p1[~p1["formulation"].astype(str).str.endswith("ncfree")].copy()
r = r[[hstar.get((a, b, c)) == h for a, b, c, h in zip(r["stat"], r["tour"], r["season"], r["h"])]]
r = r[(r["tour"] == "atp") & (r["level"] == "CH") & (r["season"] <= 2024)]
dev = pd.read_parquet(REL / "params_dev.parquet")
rows = []
for y, g in r.groupby("season"):
    a, b = dl(g), dl(g[g["stat"] != "def_bp_faced_pg"])
    d = g[g["stat"] == "def_bp_faced_pg"]
    b_mean = dev[(dev["season_used"] == y) & (dev["tour"] == "atp") & (dev["level"] == "CH") &
                 (dev["stat"] == "spw")]["w_level_mean"].iloc[0]
    rows.append({"season": y, "wbar_all": a[0], "tau2_all": a[1], "B_w_level_mean": b_mean,
                 "wbar_without_def_bp_faced_pg": b[0], "tau2_without": b[1],
                 "def_bp_faced_pg_free_w": float(d["w"].iloc[0]), "def_bp_faced_pg_se": float(d["se"].iloc[0])})
t = pd.DataFrame(rows)
t.to_csv(OUT, index=False)
print(t.round(3).to_string())
