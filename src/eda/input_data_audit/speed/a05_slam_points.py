"""Audit step 5: per player-match serve speeds straight from the raw AO/RG point files (Hawk-Eye Court Vision copy
2019-2024; decrypted Infosys 2025-2026), with first serves in, second serves in, first-serve faults, court, round and
day. Read-only on the repo; writes scratch/pm_slam_points.parquet and scratch/pts_slam_points.parquet.

Definitions (identical to panel.py where they overlap):
  first serve in   serve number 1, not a double fault, not a 'Faulty Serve' row, speed in (40, 270]
  second serve in  serve number 2, not a double fault
  first-serve fault  Hawk-Eye: 'Faulty Serve' row (serve_num 1); Infosys: faultSrvSpd on a point played on serve 2
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
B = ROOT / "data/dump/points/slam_ball_tracking"
INFO = ROOT / "data/dump/points/infosys_slams"
S0 = ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet"
TIMING = ROOT / "data/studies/match_timing/timing.parquet"
LINKS = ROOT / "data/studies/shot_level/stage0_source_matches.parquet"
SPEEDS = ROOT / "data/studies/serve_speed_acquisition/speeds.parquet"
ID_MAP = ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/id_map.csv"
LO, HI = 40.0, 270.0


def plaus(x):
    v = pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(float)
    return np.where((v > LO) & (v <= HI), v, np.nan)


def hawkeye() -> pd.DataFrame:
    m = pd.read_parquet(B / "matches.parquet", columns=["slam", "year", "match_id", "player1_id", "player2_id",
                                                        "court_name", "match_type"])
    parts = []
    for f in sorted((B / "points").glob("*.parquet")):
        parts.append(pd.read_parquet(f, columns=["match_id", "slam", "year", "tour", "point_ID", "serve_num", "server_id",
                                                 "point_end_type", "serve_speed_kph", "is_fault", "is_doublefault"]))
    p = pd.concat(parts, ignore_index=True)
    p = p.merge(m, on=["slam", "year", "match_id"], how="left")
    p["key"] = p["slam"].astype(str) + "_" + p["year"].astype(str) + "_" + p["match_id"].astype(str)
    p["spd"] = plaus(p["serve_speed_kph"].astype(str).str.extract(r"([\d.]+)")[0])
    pet = p["point_end_type"].astype(str)
    sn = pd.to_numeric(p["serve_num"], errors="coerce")
    p["kind"] = np.select([pet.eq("Faulty Serve") & sn.eq(1), pet.eq("Faulty Serve"), pet.eq("DoubleFault"),
                           sn.eq(1), sn.eq(2)], ["fault1", "fault_other", "df", "in1", "in2"], "other")
    p["player_no"] = np.select([p["server_id"].eq(p["player1_id"]), p["server_id"].eq(p["player2_id"])], [1, 2], 0)
    p["src"] = "slam_tracking"
    lk = pd.read_parquet(LINKS, columns=["source", "key", "match_id", "a1"])
    lk = lk[lk["source"].eq("slam_tracking") & lk["match_id"].notna()].drop_duplicates("key")
    p = p.merge(lk[["key", "match_id", "a1"]].rename(columns={"match_id": "s0_id"}), on="key", how="left")
    t = p["a1"].eq(True).fillna(False).to_numpy(bool)
    f = p["a1"].eq(False).fillna(False).to_numpy(bool)
    one, two = p["player_no"].eq(1).to_numpy(bool), p["player_no"].eq(2).to_numpy(bool)
    p["side"] = np.select([(t & one) | (f & two), (t & two) | (f & one)], ["A", "B"], "")
    remap = pd.read_csv(ID_MAP, usecols=["old_match_id", "new_match_id"])
    rm = dict(zip(remap["old_match_id"], remap["new_match_id"]))
    p["s0_id"] = p["s0_id"].map(lambda x: rm.get(x, x) if isinstance(x, str) else x)
    p["court"] = p["court_name"].astype(str)
    p["year"] = pd.to_numeric(p["year"]).astype(int)
    return p[["src", "slam", "year", "key", "s0_id", "side", "player_no", "kind", "spd", "court"]]


def infosys() -> pd.DataFrame:
    p = pd.read_parquet(INFO / "points.parquet", columns=["slam", "year", "match_id", "server", "serve", "serveSpeed",
                                                          "faultSrvSpd", "result"])
    p = p[p["server"].astype(str).isin(["1", "2"])].copy()
    m = pd.read_parquet(INFO / "matches.parquet", columns=["slam", "year", "match_id", "court_name"])
    p = p.merge(m, on=["slam", "year", "match_id"], how="left")
    p["key"] = p["slam"].astype(str) + "_" + p["year"].astype(str) + "_" + p["match_id"].astype(str)
    p["player_no"] = p["server"].astype(int)
    sv = p["serve"].astype(str)
    df = p["result"].astype(str).eq("DF")
    spd = plaus(p["serveSpeed"])
    flt = plaus(p["faultSrvSpd"])
    rows = pd.DataFrame({"key": p["key"], "slam": p["slam"], "year": p["year"].astype(int), "player_no": p["player_no"],
                         "court": p["court_name"].astype(str),
                         "kind": np.select([df, sv.eq("1"), sv.eq("2")], ["df", "in1", "in2"], "other"), "spd": spd})
    # first-serve faults: the fault speed carried on points played on the second serve (and on double faults)
    fr = rows[(sv.eq("2")).to_numpy()].copy()
    fr["kind"], fr["spd"] = "fault1", flt[sv.eq("2").to_numpy()]
    rows = pd.concat([rows, fr], ignore_index=True)
    sp = pd.read_parquet(SPEEDS, columns=["source", "source_key", "player_no", "match_id", "side"])
    sp = sp[sp["source"].eq("infosys_slams")].drop(columns="source").rename(columns={"source_key": "key",
                                                                                     "match_id": "s0_id"})
    rows = rows.merge(sp, on=["key", "player_no"], how="left")
    rows["src"] = "infosys_slams"
    rows["side"] = rows["side"].fillna("")
    return rows[["src", "slam", "year", "key", "s0_id", "side", "player_no", "kind", "spd", "court"]]


def main():
    pts = pd.concat([hawkeye(), infosys()], ignore_index=True)
    s0 = pd.read_parquet(S0, columns=["match_id", "tour", "year", "level", "qualifying", "round", "round_order",
                                      "tournament_id", "player_a_id", "player_b_id"]).rename(
        columns={"match_id": "s0_id", "year": "s0_year"})
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs"]).rename(columns={"match_id": "s0_id"})
    pts = pts.merge(s0, on="s0_id", how="left").merge(tm, on="s0_id", how="left")
    pts["player_id"] = np.where(pts["side"].eq("A"), pts["player_a_id"], np.where(pts["side"].eq("B"),
                                                                                    pts["player_b_id"], None))
    pts = pts.drop(columns=["player_a_id", "player_b_id"])
    pts["mq"] = np.where(pts["qualifying"].astype("boolean").fillna(False), "Q", "M")
    pts.to_parquet(SCR / "pts_slam_points.parquet", index=False)
    ok = pts[np.isfinite(pts["spd"])].copy()
    ok["pm"] = ok["key"] + "|" + ok["player_no"].astype(str)
    g = ok.groupby(["pm", "kind"])["spd"].agg(["size", "mean", "median"]).unstack("kind")
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    info = ok.drop_duplicates("pm").set_index("pm")[["src", "slam", "year", "key", "s0_id", "side", "player_no",
                                                      "player_id", "tour", "mq", "round", "round_order", "court",
                                                      "es", "lf", "obs"]]
    w = info.join(g).reset_index()
    w.to_parquet(SCR / "pm_slam_points.parquet", index=False)
    print(w.groupby(["src", "slam", "year"]).size())
    print("unlinked player rows:", int(w["player_id"].isna().sum()))
    print(pts.groupby(["src", "slam", "year", "kind"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
