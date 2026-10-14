"""B1 scout: outcome-free novelty of two rough candidate encodings against the model's own inputs.

R^2 of each candidate x on the frame's non-price, non-context inputs (pairs entered as A - B), seasons 2013-2024
(doubles: 2018-2024, the seasons TennisLive covers). Also the plain correlation with sets_14d. No result column is read.
Rough encodings (the builders will define their own):
  dbl7   = log1p(doubles matches in days -7..-1)_A - same_B
  short  = max(0, 24 - rest_h)_A/24 - same_B   (0 when a player's rest in hours is unknown)
  gap    = clip(rest_h_A - rest_h_B, -36, 36)/12 when both rests < 72 h, else 0
Run: ./python.sh data/studies/unpriced_leads/team/rhythm_body/novelty.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
FR = ROOT / "data/studies/current_best_model/template_2026-10-10/model_frame.parquet"

import pyarrow.parquet as pq  # noqa: E402
cols = pq.ParquetFile(FR).schema_arrow.names      # the schema only: no column's values are read here
ins = [c for c in cols if c.startswith("in_") and c not in
       ("in_odds_logit", "in_tour", "in_surface", "in_level", "in_indoor", "in_best_of", "in_round", "in_ios_points_short")]
fr = pd.read_parquet(FR, columns=["match_id", "tour", "season"] + ins)   # never the result column
X = fr.copy()
for p in ("surf_season", "surf_layoff"):
    X[f"in_{p}"] = X[f"in_{p}_a"] - X[f"in_{p}_b"]
    X = X.drop(columns=[f"in_{p}_a", f"in_{p}_b"])
xin = [c for c in X.columns if c.startswith("in_")]
f = pd.read_parquet(OUT / "scratch_features.parquet")
X = X.merge(f, on="match_id", how="left")
X["dbl7"] = np.log1p(X["d7_a"].fillna(0)) - np.log1p(X["d7_b"].fillna(0))
sh = lambda h: np.where(h.notna(), np.clip(24 - h, 0, 24) / 24, 0.0)  # noqa: E731
X["short"] = sh(X["rh_a"]) - sh(X["rh_b"])
both = X["rh_a"].lt(72) & X["rh_b"].lt(72)
X["gap"] = np.where(both, np.clip(X["rh_a"] - X["rh_b"], -36, 36) / 12, 0.0)
res = {}
for cand, seasons in (("dbl7", (2018, 2024)), ("short", (2013, 2024)), ("gap", (2013, 2024))):
    for tour in ("atp", "wta"):
        g = X[(X["tour"] == tour) & X["season"].between(*seasons)].dropna(subset=xin)
        A = np.column_stack([np.ones(len(g))] + [g[c].to_numpy(float) for c in xin])
        y = g[cand].to_numpy(float)
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        r2 = 1 - np.var(y - A @ beta) / np.var(y)
        r_sets = float(np.corrcoef(y, g["in_sets_14d"])[0, 1])
        nz = float((y != 0).mean())
        res[f"{cand}_{tour}"] = {"seasons": seasons, "n": int(len(g)), "nonzero_share": round(nz, 3),
                                 "r2_on_inputs": round(float(r2), 3), "corr_sets_14d": round(r_sets, 3)}
        print(cand, tour, res[f"{cand}_{tour}"])
(OUT / "novelty.json").write_text(json.dumps(res, indent=1))
