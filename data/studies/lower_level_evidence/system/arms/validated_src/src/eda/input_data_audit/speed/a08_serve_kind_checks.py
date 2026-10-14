"""Audit step 8: first/second/fault serve consistency within matches, per Slam edition of the raw point copies
(Hawk-Eye AO/RG 2019-24, Infosys AO/RG 2025-26). A first/second-serve or fault mix-up shows as an odd within-match gap."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)

pm = pd.read_parquet(SCR / "pm_slam_points.parquet")
w = pm[(pm["size_in1"] >= 10) & (pm["size_in2"] >= 5)].copy()
w["in1_in2"] = w["mean_in1"] - w["mean_in2"]
w["f1_in1"] = w["mean_fault1"] - w["mean_in1"]
w["f1_in2"] = w["mean_fault1"] - w["mean_in2"]
w["share_in2"] = w["size_in2"] / (w["size_in1"] + w["size_in2"])
w["share_f"] = w["size_fault1"] / (w["size_in1"] + w["size_in2"])
t = w.groupby(["src", "slam", "tour", "year"]).agg(pm=("in1_in2", "size"), in1=("mean_in1", "median"),
                                                     in2=("mean_in2", "median"), fault1=("mean_fault1", "median"),
                                                     in1_minus_in2=("in1_in2", "median"),
                                                     fault1_minus_in1=("f1_in1", "median"),
                                                     fault1_minus_in2=("f1_in2", "median"),
                                                     share_second=("share_in2", "median"),
                                                     faults_per_point=("share_f", "median")).round(2)
print(t.to_string())
t.to_csv(SCR / "t_serve_kind_within_match.csv")

# point-level: speed distribution of second-serve rows by edition (men): bimodality = mixed first-serve speeds
pts = pd.read_parquet(SCR / "pts_slam_points.parquet", columns=["src", "slam", "year", "tour", "kind", "spd", "court"])
q = pts[np.isfinite(pts["spd"]) & pts["kind"].isin(["in1", "in2", "fault1"])]
qq = q.groupby(["slam", "tour", "year", "kind"])["spd"].quantile([0.1, 0.5, 0.9]).unstack().round(1)
print(qq.to_string())
# second serves faster than 175 km/h (men) / 150 (women) share
q2 = q[q["kind"].eq("in2")]
thr = np.where(q2["tour"].eq("atp"), 175, 150)
print((q2.assign(fast=q2["spd"].to_numpy() > thr).groupby(["slam", "tour", "year"])["fast"].mean().round(3)
       .unstack("year")).to_string())
