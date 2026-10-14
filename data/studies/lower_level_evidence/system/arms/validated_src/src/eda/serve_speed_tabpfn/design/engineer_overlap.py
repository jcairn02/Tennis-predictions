"""Design R1 (speed-data engineer), step 2: where several sources time the same player-match, how often, and how they
agree. Values only; reads no match result.

Input: engineer_records.parquet (engineer_records.py). A record counts when it is linked to a Stage 0 side and timed
(point means: at least half the first serves in timed; key statistics and the AO match centre: a plausible value).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_overlap.py
Writes data/studies/serve_speed_tabpfn/design/engineer_overlap.json
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402


def load() -> pd.DataFrame:
    r = pd.read_parquet(EC.RECORDS)
    r = r[r["linked"] & r["timed"] & r["gate_half"].astype(bool)].copy()
    m = EC.stage0(cols=["match_id", "tour", "year", "level", "qualifying", "tournament_name", "tournament_id"])
    r = r.merge(m, on="match_id", how="left")
    r["slam"] = EC.slam_of(r["level"], r["tournament_name"]).to_numpy()
    r["lgroup"] = EC.level_group(r["level"], r["qualifying"]).to_numpy()
    return r


def pair_stats(a: pd.DataFrame, b: pd.DataFrame, sa: str, sb: str) -> dict | None:
    j = a.merge(b, on=["match_id", "side"], suffixes=("_a", "_b"))
    if j.empty:
        return None
    d = j["spd1_a"] - j["spd1_b"]
    out = {"pair": f"{sa} - {sb}", "player_matches": int(len(j)), "matches": int(j["match_id"].nunique()),
           "years": sorted(int(y) for y in j["year_a"].dropna().unique()),
           "tours": j["tour_a"].value_counts().to_dict(),
           "diff_mean": round(float(d.mean()), 3), "diff_median": round(float(d.median()), 3),
           "diff_sd": round(float(d.std()), 3), "abs_diff_median": round(float(d.abs().median()), 3),
           "abs_gt_1": int((d.abs() > 1).sum()), "abs_gt_3": int((d.abs() > 3).sum()),
           "abs_gt_10": int((d.abs() > 10).sum()), "quantiles": EC.q(d),
           "corr": round(float(np.corrcoef(j["spd1_a"], j["spd1_b"])[0, 1]), 4) if len(j) > 2 else None}
    if "n1_a" in j and "n1_b" in j:
        out["n1_ratio_median"] = round(float((j["n1_a"] / j["n1_b"]).median()), 3)
    # by Slam family and year where relevant
    if j["slam_a"].ne("").any():
        out["by_slam_year"] = (j.assign(d=d).groupby(["slam_a", "year_a"])["d"]
                               .agg(["size", "mean", "median"]).round(3).reset_index()
                               .rename(columns={"slam_a": "slam", "year_a": "year"}).to_dict(orient="records"))
    return out


def main() -> None:
    r = load()
    EC.log(f"{len(r):,} timed, linked records")
    srcs = sorted(r["source"].unique())
    by = {s: r[r["source"].eq(s)] for s in srcs}
    # duplicates within a source (a Stage 0 side timed twice by one source)
    dup_within = {s: int(g.duplicated(["match_id", "side"]).sum()) for s, g in by.items()}
    for s in srcs:
        by[s] = by[s].drop_duplicates(["match_id", "side"])
    # how many sources time each player-match
    k = r.drop_duplicates(["source", "match_id", "side"])
    combo = k.groupby(["match_id", "side"])["source"].apply(lambda x: "+".join(sorted(x)))
    meta = k.drop_duplicates(["match_id", "side"]).set_index(["match_id", "side"])[["tour", "year", "lgroup"]]
    cm = meta.join(combo.rename("sources"))
    combos = (cm.groupby(["tour", "sources"]).size().sort_values(ascending=False).reset_index(name="player_matches")
              .to_dict(orient="records"))
    n_sources = cm["sources"].str.count(r"\+") + 1
    pairs = []
    for sa, sb in combinations(srcs, 2):
        ps = pair_stats(by[sa], by[sb], sa, sb)
        if ps:
            pairs.append(ps)
            EC.log(f"{ps['pair']}: n={ps['player_matches']} median {ps['diff_median']:+.2f} mean {ps['diff_mean']:+.2f} "
                   f"sd {ps['diff_sd']:.2f} |d|>3: {ps['abs_gt_3']}")
    # RG key statistic against the same file's point mean, and the AO match centre's rounding rule
    sl = by["infosys_slams"]
    rg = sl[sl["ks_spd1"].notna()]
    d_rg = rg["ks_spd1"] - rg["spd1"]
    rounding = {"rg_keystat_vs_points": {
        "player_matches": int(len(rg)), "equal_round": int((rg["ks_spd1"] == np.round(rg["spd1"])).sum()),
        "equal_floor": int((rg["ks_spd1"] == np.floor(rg["spd1"])).sum()),
        "equal_ceil": int((rg["ks_spd1"] == np.ceil(rg["spd1"])).sum()), "diff_median": round(float(d_rg.median()), 3),
        "diff_mean": round(float(d_rg.mean()), 3)}}
    for other in ("infosys_slams", "slam_tracking", "slam_pbp"):
        j = by["ausopen_mc"].merge(by[other], on=["match_id", "side"], suffixes=("_mc", "_p"))
        if len(j):
            d = j["spd1_mc"] - j["spd1_p"]
            rounding[f"ausopen_mc_vs_{other}"] = {
                "player_matches": int(len(j)), "years": sorted(int(y) for y in j["year_mc"].unique()),
                "equal_round": int((j["spd1_mc"] == np.round(j["spd1_p"])).sum()),
                "equal_floor": int((j["spd1_mc"] == np.floor(j["spd1_p"])).sum()),
                "equal_ceil": int((j["spd1_mc"] == np.ceil(j["spd1_p"])).sum()),
                "diff_median": round(float(d.median()), 3), "diff_mean": round(float(d.mean()), 3),
                "first_in_equal": int((j["n1_mc"] == j["f1_p"]).sum())}
    out = {"reads_results": False, "records_timed_linked": int(len(r)),
           "records_by_source": r["source"].value_counts().to_dict(),
           "duplicates_within_source": dup_within,
           "player_matches_timed": int(len(cm)),
           "player_matches_by_number_of_sources": n_sources.value_counts().sort_index().to_dict(),
           "player_matches_multi_source_by_tour_year": (cm[n_sources > 1].groupby(["tour", "year"]).size()
                                                         .reset_index(name="n").to_dict(orient="records")),
           "source_combinations": combos[:40], "pairs": pairs, "rounding": rounding}
    (EC.OUT / "engineer_overlap.json").write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("pairs", "source_combinations")}, indent=1,
                     default=str)[:4000])
    print(pd.DataFrame(combos[:25]).to_string(index=False))


if __name__ == "__main__":
    main()
