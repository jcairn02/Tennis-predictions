"""F6: Roland Garros 2015-2025 and the Olympics in Stage 0: pooled first-serve-in rates and first-serve points won by
edition (tour x qualifying), and, for RG 2019-2024 matches in the ball-tracking dump, per-player first serves in and
serve points against Stage 0. Writes f6_editions.csv, f6_balltracking_vs_stage0.csv."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 200)
m, p = R.stage0()
ev = m[(m["tournament_name"].str.contains("Roland Garros|Olympics", na=False)) & m["has_box"]]
pp = p[p["match_id"].isin(ev["match_id"])].merge(ev[["match_id", "year", "tour", "qualifying", "tournament_name", "source"]],
                                                  on="match_id")
g = pp.groupby(["tournament_name", "tour", "qualifying", "year"]).agg(rows=("svpt", "size"), svpt=("svpt", "sum"),
                                                                     fi=("first_in", "sum"), fw=("first_won", "sum"),
                                                                     sw=("second_won", "sum"), src=("source", "first"))
g["first_in_pct"] = (100 * g["fi"] / g["svpt"]).round(1)
g["first_won_pct"] = (100 * g["fw"] / g["fi"]).round(1)
g["second_won_pct"] = (100 * g["sw"] / (g["svpt"] - g["fi"])).round(1)
g = g.reset_index()
g.to_csv(R.OUT / "f6_editions.csv", index=False)
print(g[g["year"] >= 2012][["tournament_name", "tour", "qualifying", "year", "rows", "src", "first_in_pct", "first_won_pct",
                            "second_won_pct"]].to_string())

# ball tracking RG 2019-2024 (rows are serves; faulty first serves are their own rows)
bm = pd.read_parquet(R.DUMP / "points" / "slam_ball_tracking" / "matches.parquet")
rows = []
for yr in range(2019, 2025):
    f = R.DUMP / "points" / "slam_ball_tracking" / "points" / f"RG_{yr}.parquet"
    if not f.exists():
        continue
    pt = pd.read_parquet(f).drop_duplicates(["match_id", "point_ID"])
    pt = pt[pt["point_end_type"] != "Faulty Serve"]
    mt = bm[(bm["slam"] == "RG") & (bm["year"].astype(str) == str(yr))]
    s0 = pp[(pp["tournament_name"].eq("Roland Garros")) & (pp["year"].eq(yr)) & ~pp["qualifying"]]
    s0 = s0.assign(last=s0["player_name"].map(lambda x: R.nkey(x).replace(" ", "")))
    for r in mt.to_dict("records"):
        tour = "atp" if "Men" in str(r["match_type"]) else "wta"
        q = pt[pt["match_id"].eq(r["match_id"])]
        if q.empty:
            continue
        for pid, nm, opp in ((r["player1_id"], r["player1"], r["player2"]), (r["player2_id"], r["player2"], r["player1"])):
            ln = R.nkey(str(nm).split(".", 1)[-1]).replace(" ", "")
            lo = R.nkey(str(opp).split(".", 1)[-1]).replace(" ", "")
            c = s0[(s0["tour"].eq(tour)) & s0["last"].str.endswith(ln)]
            oppids = s0[(s0["tour"].eq(tour)) & s0["last"].str.endswith(lo)]["player_id"]
            c = c[c["opponent_id"].isin(oppids)]
            if len(c) != 1:
                continue
            s = q[q["server_id"].astype(str) == str(pid)]
            rows.append({"year": yr, "tour": tour, "match_id": c["match_id"].iloc[0], "player": c["player_name"].iloc[0],
                         "bt_svpt": len(s), "bt_first_in": int((s["serve_num"].astype(str) == "1").sum()),
                         "s0_svpt": c["svpt"].iloc[0], "s0_first_in": c["first_in"].iloc[0]})
B = pd.DataFrame(rows)
B.to_csv(R.OUT / "f6_balltracking_vs_stage0.csv", index=False)
B["d_fi"] = B["s0_first_in"] - B["bt_first_in"]
B["sv_eq"] = B["s0_svpt"].eq(B["bt_svpt"])
print(B.groupby(["year", "tour"]).agg(rows=("d_fi", "size"), svpt_equal=("sv_eq", "mean"),
                                      first_in_equal=("d_fi", lambda x: (x == 0).mean()),
                                      first_in_s0_higher=("d_fi", lambda x: (x > 0).mean()),
                                      mean_diff=("d_fi", "mean"),
                                      bt_first_in_pct=("bt_first_in", "sum"), bt_svpt=("bt_svpt", "sum")).to_string())
