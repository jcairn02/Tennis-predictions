"""F1 step 1: per-event profile of Sackmann's WTA box scores, 2014-2016 (main file and qual/ITF file).

Per event: matches with a box, player rows, the definition test (second_won + df <= svpt - first_in) failure share,
second-serve points won share with svpt as written and with svpt + df, df share, first-in share.
Writes f1_events_2014_2016.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

frames = []
for yr in (2014, 2015, 2016):
    for pat, kind in ((f"wta_matches_{yr}.parquet", "main"), (f"wta_matches_qual_itf_{yr}.parquet", "qual_itf")):
        d = R.sack("wta", pat)
        d["kind"] = kind
        frames.append(d)
s = pd.concat(frames, ignore_index=True)
s["box"] = R.has_box(s)
rows = []
for side in ("w", "l"):
    t = s[s["box"]].copy()
    t["side"] = side
    for b in R.BOX:
        t[b] = t[f"{side}_{b}"]
    rows.append(t[["_file", "_row", "kind", "tourney_id", "tourney_name", "tourney_level", "tdate", "round", "side"] + R.BOX])
pr = pd.concat(rows, ignore_index=True)
pr["second_pts"] = pr["svpt"] - pr["first_in"]
pr["def_fail"] = (pr["second_won"] + pr["df"]) > pr["second_pts"]
pr["qual"] = pr["round"].str.upper().str.match(r"^Q\d")
g = pr.groupby(["kind", "tourney_level", "tourney_id", "tourney_name", "tdate", "qual"])
ev = g.agg(rows=("svpt", "size"), def_fail=("def_fail", "sum"), svpt=("svpt", "sum"), df=("df", "sum"),
           first_in=("first_in", "sum"), second_won=("second_won", "sum"), first_won=("first_won", "sum"),
           df0=("df", lambda x: int((x == 0).sum()))).reset_index()
ev["def_fail_share"] = ev["def_fail"] / ev["rows"]
ev["second_won_pct"] = 100 * ev["second_won"] / (ev["svpt"] - ev["first_in"])
ev["second_won_pct_plus_df"] = 100 * ev["second_won"] / (ev["svpt"] + ev["df"] - ev["first_in"])
ev["first_in_pct"] = 100 * ev["first_in"] / ev["svpt"]
ev["first_in_pct_plus_df"] = 100 * ev["first_in"] / (ev["svpt"] + ev["df"])
ev["df_per_pt"] = 100 * ev["df"] / ev["svpt"]
ev = ev.sort_values(["tdate", "tourney_name"])
ev.to_csv(R.OUT / "f1_events_2014_2016.csv", index=False)
pd.set_option("display.width", 250)
cols = ["kind", "tourney_level", "tourney_name", "tdate", "qual", "rows", "def_fail", "def_fail_share",
        "second_won_pct", "second_won_pct_plus_df", "first_in_pct", "df_per_pt"]
print(ev[ev["tdate"].dt.year.eq(2015) | (ev["tdate"] >= "2014-12-01") & (ev["tdate"] < "2016-03-01")][cols]
      .to_string(index=False, float_format=lambda x: f"{x:.3f}"))
# tour-season def-fail share
pr["year"] = pr["tdate"].dt.year
print(pr.groupby(["year", "kind"]).agg(rows=("def_fail", "size"), fail=("def_fail", "sum"), share=("def_fail", "mean")))
