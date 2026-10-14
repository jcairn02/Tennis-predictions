"""F4 calibration: on all Sackmann rows with a box (both tours, main and qual/chall/ITF files, 2010-2026) outside the
repeat groups, how often does a box fail the break-margin test, and what is the range of serve points per non-tiebreak
game? Completed matches only. Writes f4_calibration.csv."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

frames = []
for tour, pats in (("atp", ["atp_matches_[0-9]*.parquet", "atp_matches_qual_chall_*.parquet"]),
                   ("wta", ["wta_matches_[0-9]*.parquet", "wta_matches_qual_itf_*.parquet"])):
    for pat in pats:
        d = R.sack(tour, pat)
        d["tour"] = tour
        frames.append(d)
s = pd.concat(frames, ignore_index=True)
s = s[R.has_box(s)].copy()
rep = pd.read_csv(R.OUT / "f4_groups.csv")
s = s[~(s["_source_file"] + "#" + s["_row"].astype(str)).isin(rep["_source_file"] + "#" + rep["_row"].astype(str))]
g = np.array([R.games_of(x) for x in s["score"]], dtype=float)
s["gw"], s["gl"], s["tw"], s["tl"], s["ntb"], s["ret"] = g.T
s = s[(s["ret"] == 0) & s["score"].str.match(r"^\d")]
bcw = s["w_bp_faced"] - s["w_bp_saved"]
bcl = s["l_bp_faced"] - s["l_bp_saved"]
margin = (s["gw"] - s["tw"]) - (s["gl"] - s["tl"])
s["bm_ok"] = (margin - 2 * (bcl - bcw)).abs() <= 1
games = s["gw"] + s["gl"] - s["ntb"]
s["ppg"] = (s["w_svpt"] + s["l_svpt"]) / games
s = s[games > 0]
out = {"rows": len(s), "break_margin_fail_share": float(1 - s["bm_ok"].mean())}
for tour, d in s.groupby("tour"):
    out[f"{tour}_break_margin_fail_share"] = float(1 - d["bm_ok"].mean())
    q = d["ppg"].quantile([0.0001, 0.001, 0.01, 0.5, 0.99, 0.999, 0.9999])
    for k, v in q.items():
        out[f"{tour}_ppg_q{k}"] = round(float(v), 2)
    out[f"{tour}_ppg_min"] = round(float(d["ppg"].min()), 2)
    out[f"{tour}_ppg_max"] = round(float(d["ppg"].max()), 2)
    out[f"{tour}_share_ppg_gt_8.5"] = float((d["ppg"] > 8.5).mean())
    out[f"{tour}_share_ppg_lt_4.8"] = float((d["ppg"] < 4.8).mean())
# by number of games (WTA), the 99.9th percentile of ppg in short matches
w = s[s["tour"].eq("wta")]
for lo, hi in ((12, 14), (15, 17), (18, 20), (21, 23)):
    d = w[(games.loc[w.index] >= lo) & (games.loc[w.index] <= hi)]
    out[f"wta_games_{lo}_{hi}_ppg_q0.999"] = round(float(d["ppg"].quantile(0.999)), 2)
    out[f"wta_games_{lo}_{hi}_ppg_max"] = round(float(d["ppg"].max()), 2)
    out[f"wta_games_{lo}_{hi}_n"] = len(d)
r = pd.Series(out)
r.to_csv(R.OUT / "f4_calibration.csv")
print(r.to_string())
