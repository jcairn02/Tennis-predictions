"""Audit step 7: AO 2024 by court, by day, within-match fault-vs-in, and against the AO match centre's own published
"1st Serve Average" (Wayback captures). Read-only on the repo."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 60)

pm = pd.read_parquet(SCR / "pm_slam_points.parquet")
ao = pm[(pm["slam"] == "AO") & pm["player_id"].notna() & (pm["mq"] == "M")].copy()

# 1) within-match: first-serve fault minus first serve in, same player-match (n >= 10 each)
w = ao[(ao["size_in1"] >= 10) & (ao["size_fault1"] >= 10)].copy()
w["d_fault_in"] = w["mean_fault1"] - w["mean_in1"]
w["d_in1_in2"] = w["mean_in1"] - w["mean_in2"]
print("=== within player-match: fault1 - in1 and in1 - in2 (km/h), AO main draw")
print(w.groupby(["tour", "year"]).agg(n=("d_fault_in", "size"), fault_minus_in=("d_fault_in", "median"),
                                      in1_minus_in2=("d_in1_in2", "median")).round(2).to_string())

# 2) per court: each player-match's first-serve-in mean minus the same player's AO mean in the reference years
def ref_mean(years):
    r = ao[ao["year"].isin(years) & ao["size_in1"].notna()]
    s = r.assign(s=r["size_in1"] * r["mean_in1"]).groupby(["tour", "player_id"])[["s", "size_in1"]].sum()
    s = s[s["size_in1"] >= 20]
    return (s["s"] / s["size_in1"]).rename("ref")

out = []
for y, refy in ((2022, (2023,)), (2023, (2022,)), (2024, (2023, 2025)), (2025, (2023,))):
    r = ref_mean(refy)
    d = ao[(ao["year"] == y) & (ao["size_in1"] >= 10)].join(r, on=["tour", "player_id"])
    d = d[d["ref"].notna()]
    d["dev"] = d["mean_in1"] - d["ref"]
    g = d.groupby(["tour", "court"]).agg(pm=("dev", "size"), median_dev=("dev", "median"), mean_dev=("dev", "mean"))
    g = g[g["pm"] >= 8].round(2)
    g["year"], g["ref"] = y, "+".join(map(str, refy))
    out.append(g.reset_index())
    print(f"=== AO {y}: first serves in, player-match minus the same player's AO {refy} mean, by court (>= 8)")
    print(g.to_string())
pd.concat(out).to_csv(SCR / "t_ao_by_court.csv", index=False)

# 3) per day (obs) for 2024 and 2023
out = []
for y, refy in ((2023, (2022,)), (2024, (2023, 2025)), (2025, (2023,))):
    r = ref_mean(refy)
    d = ao[(ao["year"] == y) & (ao["size_in1"] >= 10)].join(r, on=["tour", "player_id"])
    d = d[d["ref"].notna()]
    d["dev"] = d["mean_in1"] - d["ref"]
    d["date"] = pd.to_datetime(d["obs"], unit="D").dt.date
    g = d.groupby(["date"]).agg(pm=("dev", "size"), rounds=("round", lambda s: ",".join(sorted(set(s)))),
                                median_dev=("dev", "median"), mean_dev=("dev", "mean")).round(2)
    print(f"=== AO {y}: by day (both tours)")
    print(g.to_string())
    g["year"] = y
    out.append(g.reset_index())
pd.concat(out).to_csv(SCR / "t_ao_by_day.csv", index=False)

# 4) the AO match centre's published "1st Serve Average" (Wayback captures) vs the copy's mean of first serves in
A = ROOT / "data/dump/points/ausopen"
st = pd.read_parquet(A / "set_statistics.parquet", columns=["record_key", "year", "event", "match_id", "set", "stat",
                                                            "team1_primary", "team2_primary"])
st = st[st["stat"].eq("1st Serve Average") & st["set"].eq("All") & st["event"].isin(["MS", "WS", "MQ", "WQ"])]
mm = pd.read_parquet(A / "matches.parquet", columns=["record_key", "team1_names", "team2_names", "match_status_name"])
st = st.merge(mm, on="record_key", how="left")
st["year"] = st["year"].astype(int)
pts = pd.read_parquet(SCR / "pts_slam_points.parquet")
# the Hawk-Eye copy keys are AO_<year>_<year>_<code>; Infosys AO_<year>_<code>
he = pts[(pts["slam"] == "AO") & (pts["kind"] == "in1") & np.isfinite(pts["spd"])].copy()
he["code"] = he["key"].str.split("_").str[-1]
he_m = he.groupby(["year", "code", "player_no"])["spd"].agg(["mean", "size"]).reset_index()
B = ROOT / "data/dump/points/slam_ball_tracking"
names = pd.read_parquet(B / "matches.parquet", columns=["slam", "year", "match_id", "player1", "player2"])
names = names[names["slam"].eq("AO")]
names["code"] = names["match_id"].str.split("_").str[-1]
names["year"] = names["year"].astype(int)
inf_names = pd.read_parquet(ROOT / "data/dump/points/infosys_slams/matches.parquet",
                            columns=["slam", "year", "match_id", "p1_last_name", "p2_last_name"])
inf_names = inf_names[inf_names["slam"].eq("AO")].rename(columns={"match_id": "code", "p1_last_name": "player1",
                                                                   "p2_last_name": "player2"})
inf_names["year"] = inf_names["year"].astype(int)
allnames = pd.concat([names[["year", "code", "player1", "player2"]], inf_names[["year", "code", "player1", "player2"]]])


def sur(x):
    x = str(x or "").upper().replace(".", " ").strip()
    return x.split()[-1] if x else ""


rows = []
for r in st.itertuples(index=False):
    v1, v2 = pd.to_numeric(r.team1_primary, errors="coerce"), pd.to_numeric(r.team2_primary, errors="coerce")
    nm = allnames[(allnames["year"] == r.year) & (allnames["code"] == r.match_id)]
    if nm.empty:
        continue
    nm = nm.iloc[0]
    for team, v in ((r.team1_names, v1), (r.team2_names, v2)):
        if not (v and v > 40):
            continue
        t = sur(team)
        no = 1 if sur(nm["player1"]) == t else 2 if sur(nm["player2"]) == t else 0
        if not no:
            continue
        h = he_m[(he_m["year"] == r.year) & (he_m["code"] == r.match_id) & (he_m["player_no"] == no)]
        if h.empty:
            continue
        rows.append({"year": r.year, "code": r.match_id, "status": r.match_status_name, "player": team, "ao_mc": v,
                     "copy_mean": round(float(h["mean"].iloc[0]), 2), "n": int(h["size"].iloc[0]),
                     "diff": round(v - float(h["mean"].iloc[0]), 2)})
mc = pd.DataFrame(rows)
print("=== AO match centre published 1st Serve Average vs the point copy's mean of first serves in")
print(mc.to_string(index=False))
print(mc.groupby("year").agg(n=("diff", "size"), med=("diff", "median"), mean=("diff", "mean"),
                              eq_round=("diff", lambda d: None)).to_string())
mc["eq_floor"] = mc["ao_mc"] == np.floor(mc["copy_mean"])
mc["eq_round"] = mc["ao_mc"] == np.round(mc["copy_mean"])
print(mc.groupby("year")[["eq_floor", "eq_round"]].sum())
mc.to_csv(SCR / "t_ao_mc_vs_copy.csv", index=False)
