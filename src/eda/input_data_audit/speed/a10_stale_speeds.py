"""Audit step 10: repeated ("stale") serve speeds - a row carrying the previous serve's speed - in every point source the
panel reads (stage1_points_<src>.parquet, as panel.py reads them; and the raw Hawk-Eye rows with faults kept), per source x
event x year. Read-only on the repo; writes scratch/t_stale_speeds.csv."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
SHOT = ROOT / "data/studies/shot_level"
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 600)

links = pd.read_parquet(SHOT / "stage0_source_matches.parquet", columns=["source", "key", "match_id", "tour", "year"])
s0 = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "level", "tournament_name", "qualifying"])


def event_of(name, level):
    n = str(name or "").lower()
    if level != "GS":
        return "tour"
    return "AO" if "austral" in n else "RG" if ("roland" in n or "french" in n) else "W" if "wimbledon" in n else \
        "USO" if ("us open" in n or "u.s. open" in n) else "slam"


rows = []
for src in ("slam_pbp", "slam_tracking", "slamtracker", "infosys", "sirgenkii"):
    p = pd.read_parquet(SHOT / f"stage1_points_{src}.parquet", columns=["key", "seq", "server", "serve_no", "end", "speed"])
    p = p.sort_values(["key", "seq"]).reset_index(drop=True)
    same_key = p["key"].eq(p["key"].shift())
    prev = p["speed"].shift()
    rep_any = same_key & p["speed"].notna() & prev.eq(p["speed"])
    # previous serve by the same server in the same match
    p["prev_same_srv"] = p.groupby(["key", "server"])["speed"].shift()
    rep_srv = p["speed"].notna() & p["prev_same_srv"].eq(p["speed"])
    p["rep_any"], p["rep_srv"] = rep_any, rep_srv
    lk = links[links["source"].eq(src)].drop_duplicates("key")[["key", "match_id", "year"]]
    lk = lk.merge(s0, on="match_id", how="left")
    lk["event"] = [event_of(n, l) for n, l in zip(lk["tournament_name"], lk["level"])]
    p = p.merge(lk[["key", "year", "event", "qualifying"]], on="key", how="left")
    p["is_in1"] = p["serve_no"].eq(1) & ~p["end"].eq(2) & p["speed"].notna()
    p["is_in2"] = p["serve_no"].eq(2) & ~p["end"].eq(2) & p["speed"].notna()
    g = p[p["speed"].notna()].groupby(["event", "year"], dropna=False).agg(
        timed=("speed", "size"), rep_prev_row=("rep_any", "mean"), rep_prev_same_server=("rep_srv", "mean"),
        in2_over_175=("speed", lambda s: np.nan))
    # second serves above 175 km/h (men's first-serve-like) share, unweighted
    t2 = p[p["is_in2"]].groupby(["event", "year"], dropna=False)["speed"].apply(lambda s: (s > 175).mean())
    g["in2_over_175"] = t2
    g["src"] = src
    rows.append(g.reset_index())
out = pd.concat(rows, ignore_index=True)
out = out[out["timed"] >= 500]
print(out.round(4).to_string(index=False))
out.to_csv(SCR / "t_stale_speeds.csv", index=False)

# infosys_slams raw points
ip = pd.read_parquet(ROOT / "data/dump/points/infosys_slams/points.parquet",
                     columns=["slam", "year", "match_id", "seq", "server", "serve", "serveSpeed", "faultSrvSpd", "result"])
ip["spd"] = pd.to_numeric(ip["serveSpeed"], errors="coerce").where(lambda x: (x > 40) & (x <= 270))
ip = ip.sort_values(["slam", "year", "match_id", "seq"])
k = ip["slam"].astype(str) + ip["year"].astype(str) + ip["match_id"].astype(str)
ip["rep"] = k.eq(k.shift()) & ip["spd"].notna() & ip["spd"].eq(ip["spd"].shift())
ip["prev_srv"] = ip.groupby([k, ip["server"]])["spd"].shift()
ip["rep_srv"] = ip["spd"].notna() & ip["prev_srv"].eq(ip["spd"])
print(ip[ip["spd"].notna()].groupby(["slam", "year"]).agg(timed=("spd", "size"), rep_prev_row=("rep", "mean"),
                                                          rep_prev_same_server=("rep_srv", "mean")).round(4))

# the raw Hawk-Eye rows WITH the fault rows (the stage1 table drops them): repeated speed vs the previous serve
B = ROOT / "data/dump/points/slam_ball_tracking/points"
res = []
for f in sorted(B.glob("*.parquet")):
    r = pd.read_parquet(f, columns=["match_id", "tour", "serve_num", "point_end_type", "serve_speed_kph"])
    r["spd"] = pd.to_numeric(r["serve_speed_kph"].astype(str).str.extract(r"([\d.]+)")[0], errors="coerce")
    r["spd"] = r["spd"].where((r["spd"] > 40) & (r["spd"] <= 270))
    same = r["match_id"].eq(r["match_id"].shift())
    r["rep"] = same & r["spd"].notna() & r["spd"].eq(r["spd"].shift())
    pet = r["point_end_type"].astype(str)
    sec = r["serve_num"].astype(str).eq("2") & ~pet.eq("DoubleFault")
    after_fault = same & pet.shift().eq("Faulty Serve")
    first_in = r["serve_num"].astype(str).eq("1") & ~pet.isin(["Faulty Serve"])
    res.append({"file": f.stem, "rows": len(r), "timed": int(r["spd"].notna().sum()),
                "rep_prev_serve": round(float(r.loc[r["spd"].notna(), "rep"].mean()), 4),
                "rep_first_in": round(float(r.loc[first_in & r["spd"].notna(), "rep"].mean()), 4),
                "rep_second_after_fault": round(float(r.loc[sec & after_fault & r["spd"].notna(), "rep"].mean()), 4),
                "second_rows_without_fault_before": round(float((sec & ~after_fault).sum() / max(sec.sum(), 1)), 4),
                "fault_rows_without_point_id": int((pet.eq("Faulty Serve") & r["spd"].isna()).sum())})
res = pd.DataFrame(res)
print(res.to_string(index=False))
res.to_csv(SCR / "t_hawkeye_raw_repeats.csv", index=False)
