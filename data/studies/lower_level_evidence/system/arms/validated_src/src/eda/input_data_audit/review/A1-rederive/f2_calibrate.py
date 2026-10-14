"""F2 step 3: how often does a box that an independent record shows to be genuine (WTA API equal as recorded on all 18
counts) still 'fit only when exchanged'? Split by the games margin and the recorded winner's point deficit.

Population: Stage 0 WTA matches 2019-2026 linked to the WTA API (wta_api_agree_*_matches.csv): 'equal' = genuine,
'exchanged' = verified exchange. Identity per my f2_internal definitions; a +-1 tolerant version as well.
Writes f2_calibration.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 250)
ag = pd.read_csv(R.OUT / "wta_api_agree_2019_2020_2021_2022_2023_2024_2025_2026_matches.csv")
m, p = R.stage0()
key = m["source_file"] + "#" + m["source_row"].astype(str)
m = m.assign(key=key)
ag["key"] = ag["_source_file"] + "#" + ag["_row"].astype(str)
mm = m[m["key"].isin(ag["key"]) & m["has_box"] & m["status"].eq("completed")]
pw = p[p["won"]].set_index("match_id")
pl = p[~p["won"]].set_index("match_id")
W, L = pw.loc[mm["match_id"]], pl.loc[mm["match_id"]]
g = np.array([R.games_of(s) for s in mm["score"]], dtype=float)
rev = mm["score_flag"].eq("read_reversed").to_numpy()
gw, gl, tw, tl = g[:, 0].copy(), g[:, 1].copy(), g[:, 2].copy(), g[:, 3].copy()
gw[rev], gl[rev], tw[rev], tl[rev] = g[rev, 1], g[rev, 0], g[rev, 3], g[rev, 2]


def bg(a, b):
    return (a["sv_gms"].to_numpy() - (a["bp_faced"].to_numpy() - a["bp_saved"].to_numpy())
            + (b["bp_faced"].to_numpy() - b["bp_saved"].to_numpy()))


def pts(a, b):
    return (a["first_won"].to_numpy() + a["second_won"].to_numpy()
            + b["svpt"].to_numpy() - b["first_won"].to_numpy() - b["second_won"].to_numpy())


bw, bl = bg(W, L), bg(L, W)
c = pd.DataFrame({"match_id": mm["match_id"].to_numpy(), "key": mm["key"].to_numpy(),
                  "gw": gw - tw, "gl": gl - tl, "bw": bw, "bl": bl,
                  "pts_w": pts(W, L), "pts_l": pts(L, W)})
c["fit_rec"] = (c["bw"] == c["gw"]) & (c["bl"] == c["gl"])
c["fit_exc"] = (c["bw"] == c["gl"]) & (c["bl"] == c["gw"])
c["fit_rec1"] = ((c["bw"] - c["gw"]).abs() <= 1) & ((c["bl"] - c["gl"]).abs() <= 1)
c["fit_exc1"] = ((c["bw"] - c["gl"]).abs() <= 1) & ((c["bl"] - c["gw"]).abs() <= 1)
c["margin"] = (c["gw"] - c["gl"]).abs()
c["deficit"] = c["pts_l"] - c["pts_w"]   # > 0: recorded winner won fewer points
c = c.merge(ag[["key", "cls"]], on="key", how="left")
c["pattern_exact"] = c["fit_exc"] & ~c["fit_rec"]
c["pattern_tol"] = c["fit_exc1"] & ~c["fit_rec1"]
c.to_csv(R.OUT / "f2_calibration.csv", index=False)
print(c["cls"].value_counts().to_dict())
for cls in ("equal", "exchanged", "other"):
    d = c[c["cls"].eq(cls)]
    print(f"\n== {cls}: {len(d)} matches")
    t = d.assign(mb=pd.cut(d["margin"], [-1, 1, 2, 3, 5, 99], labels=["0-1", "2", "3", "4-5", "6+"]),
                 db=pd.cut(d["deficit"], [-999, 0, 4, 9, 999], labels=["<=0", "1-4", "5-9", "10+"]))
    print("pattern_exact by margin x deficit:\n", pd.crosstab(t["mb"], t["db"], values=t["pattern_exact"], aggfunc="sum").fillna(0).astype(int).to_string())
    print("pattern_tol by margin x deficit:\n", pd.crosstab(t["mb"], t["db"], values=t["pattern_tol"], aggfunc="sum").fillna(0).astype(int).to_string())
    print("all matches by margin x deficit:\n", pd.crosstab(t["mb"], t["db"]).to_string())
