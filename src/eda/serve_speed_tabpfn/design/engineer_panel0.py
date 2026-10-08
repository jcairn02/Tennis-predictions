"""Design R1 (speed-data engineer), step 4: a draft panel, one row per Stage 0 player-match with a usable first-serve
speed, built from engineer_records.parquet by the proposed source choice. Values only; reads no match result.

Choice per player-match (proposal, from engineer_overlap / engineer_basis):
    1. a point mean that passes the half-timed gate, the source with the most timed first serves in (ties: infosys_slams,
       sirgenkii, infosys, slam_tracking, slamtracker, slam_pbp);
    2. else the ATP key statistic (ManTennisData, else the handoff's identical copy), minus 0.5 km/h (the statistic is the
       ceiling of the point mean), unless the held point table for that player-match exists and times under 80% of
       the first serves in (the key statistic is unreliable there), or the key statistic is duplicated with different
       values;
    3. else the AO match centre's average (floored point mean), plus 0.5 km/h.
Plausibility (flag only here; the rule is set in engineer_noise.py): men < 120 or women < 100 km/h.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_panel0.py
Writes data/studies/serve_speed_tabpfn/design/engineer_panel0.parquet and engineer_panel0.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

PANEL0 = EC.OUT / "engineer_panel0.parquet"
PRIORITY = ["infosys_slams", "sirgenkii", "infosys", "slam_tracking", "slamtracker", "slam_pbp"]
BASIS_SHIFT = {"keystat_atp": -0.5, "mc_rounded": +0.5, "point_mean": 0.0}
KEEP = ["source", "basis", "match_id", "side", "spd1_raw", "spd1", "n1", "f1", "timed_share", "spd2", "n2", "spd_max",
        "fault1", "nfault1", "spd1_sumsq", "n_sources", "alt_sources"]


def build() -> tuple[pd.DataFrame, dict]:
    r = pd.read_parquet(EC.RECORDS)
    r = r[r["linked"]].copy()
    info = {}
    # point means
    pts = r[r["basis"].eq("point_mean")]
    pts_ok = pts[pts["gate_half"].astype(bool) & pts["spd1"].notna()].copy()
    pts_ok["prio"] = pts_ok["source"].map({s: i for i, s in enumerate(PRIORITY)})
    pts_ok = pts_ok.sort_values(["match_id", "side", "n1", "prio"], ascending=[True, True, False, True])
    nsrc = pts_ok.groupby(["match_id", "side"])["source"].agg(lambda x: "+".join(sorted(set(x))))
    best_pts = pts_ok.drop_duplicates(["match_id", "side"]).copy()
    # key statistics
    ks = r[r["basis"].eq("keystat_atp") & r["spd1"].notna()].copy()
    ks["prio"] = ks["source"].map({"mantennisdata": 0, "handoff_ks": 1})
    # duplicated keys inside a source with different values: drop the key (ambiguous link)
    spread = ks.groupby(["source", "match_id", "side"])["spd1"].agg(["size", "min", "max"])
    bad = spread[(spread["size"] > 1) & (spread["max"] - spread["min"] > 0.5)].reset_index()
    info["keystat_duplicates_conflicting"] = bad.groupby("source").size().to_dict()
    info["keystat_duplicates_total"] = spread[spread["size"] > 1].reset_index().groupby("source").size().to_dict()
    ks = ks.merge(bad[["source", "match_id", "side"]].assign(_bad=True), on=["source", "match_id", "side"], how="left")
    ks = ks[ks["_bad"].isna()].drop(columns="_bad")
    ks = ks.sort_values(["match_id", "side", "prio"]).drop_duplicates(["match_id", "side"])
    # a held point table that times under 80% of the box first serves in: the key statistic is unreliable
    cover = pts[["match_id", "side", "n1"]].groupby(["match_id", "side"])["n1"].max().rename("pt_n1")
    ks = ks.join(cover, on=["match_id", "side"])
    ks["pt_cover"] = ks["pt_n1"] / ks["ks_first_in"]
    low = ks["pt_cover"].notna() & (ks["pt_cover"] < 0.8)
    have_pts = ks.set_index(["match_id", "side"]).index.isin(best_pts.set_index(["match_id", "side"]).index)
    info["keystat_dropped_low_point_cover"] = int((low & ~have_pts).sum())
    ks = ks[~low | have_pts]
    # AO match centre
    mc = r[r["basis"].eq("mc_rounded") & r["spd1"].notna()].copy()
    mcs = mc.groupby(["match_id", "side"])["spd1"].agg(["size", "min", "max"])
    mc_bad = mcs[(mcs["size"] > 1) & (mcs["max"] - mcs["min"] > 0.5)].index
    mc = mc[~mc.set_index(["match_id", "side"]).index.isin(mc_bad)].drop_duplicates(["match_id", "side"])
    # stack in priority order
    best_pts["tier"], ks["tier"], mc["tier"] = 1, 2, 3
    allc = pd.concat([best_pts, ks, mc], ignore_index=True)
    allc = allc.sort_values(["match_id", "side", "tier"])
    avail = allc.groupby(["match_id", "side"])["source"].agg(lambda x: "+".join(sorted(set(x))))
    p = allc.drop_duplicates(["match_id", "side"]).copy()
    p["spd1_raw"] = p["spd1"]
    p["spd1"] = p["spd1_raw"] + p["basis"].map(BASIS_SHIFT)
    p["alt_sources"] = p.set_index(["match_id", "side"]).index.map(avail)
    p["n_sources"] = p["alt_sources"].str.count(r"\+") + 1
    p = p[KEEP]
    # Stage 0 (rebuilt) and the clock
    m = EC.stage0(cols=["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "surface", "indoor",
                        "tournament_id", "tournament_name", "tournament_date", "player_a_id", "player_b_id"])
    p = p.merge(m, on="match_id", how="left")
    info["not_in_rebuilt_stage0"] = int(p["tour"].isna().sum())
    p = p[p["tour"].notna()].copy()
    p["player_id"] = np.where(p["side"].eq("A"), p["player_a_id"], p["player_b_id"])
    p = p.drop(columns=["player_a_id", "player_b_id"])
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es", "lf", "obs", "exact"])
    p = p.merge(tm, on="match_id", how="left")
    p["slam"] = EC.slam_of(p["level"], p["tournament_name"]).to_numpy()
    p["lgroup"] = EC.level_group(p["level"], p["qualifying"]).to_numpy()
    p["family"] = np.where(p["slam"].ne(""), p["slam"], np.where(p["basis"].eq("point_mean"), "tour_pts", "tour_ks"))
    p["implausible"] = np.where(p["tour"].eq("atp"), p["spd1"] < 120, p["spd1"] < 100)
    return p, info


def main() -> None:
    p, info = build()
    p.to_parquet(PANEL0, index=False)
    info.update({"reads_results": False, "rows": int(len(p)),
                 "by_tour_source": p.groupby(["tour", "source"]).size().unstack(0, fill_value=0).to_dict(),
                 "by_tour_year": p.groupby(["tour", "year"]).size().unstack(0, fill_value=0).to_dict(),
                 "by_tour_lgroup": p.groupby(["tour", "lgroup"]).size().unstack(0, fill_value=0).to_dict(),
                 "missing_clock": int(p["es"].isna().sum()), "implausible": int(p["implausible"].sum())})
    (EC.OUT / "engineer_panel0.json").write_text(json.dumps(info, indent=1, default=str) + "\n", encoding="utf-8")
    EC.log(json.dumps(info, indent=1, default=str)[:3000])
    print(p.groupby(["tour", "year", "source"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
