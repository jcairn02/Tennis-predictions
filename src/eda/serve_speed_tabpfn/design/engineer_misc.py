"""Design R1 (speed-data engineer), step 10: small checks quoted in 1_engineer.md. Values only; no match result.

    1 the key-statistic ceiling rule restricted to seasons 2021-2023 (the basis shift is frozen on <= 2023)
    2 ManTennisData rows whose round disagrees with the linked Stage 0 match's round (probable mislinks)
    3 frame coverage totals by tour and window (training 2014-2023, test 2024-2026) from engineer_coverage_frame.csv

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_misc.py
Writes data/studies/serve_speed_tabpfn/design/engineer_misc.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402


def main() -> None:
    res = {"reads_results": False}
    r = pd.read_parquet(EC.RECORDS)
    r = r[r["linked"]]
    m = EC.stage0(cols=["match_id", "year", "round"])
    ks = r[r["source"].eq("mantennisdata") & r["spd1"].notna()].drop_duplicates(["match_id", "side"], keep=False)
    p = r[r["source"].eq("infosys") & (r["n1"] > 0)]
    j = ks.merge(p, on=["match_id", "side"], suffixes=("_k", "_p")).merge(m, on="match_id")
    j = j[j["year"] <= 2023]
    comp = j[(j["f1_p"] == j["ks_first_in_k"]) & (j["n1_p"] == j["f1_p"])]
    d = comp["spd1_k"] - comp["spd1_p"]
    res["ceiling_rule_2021_23"] = {"complete_tables": int(len(comp)),
                                   "equal_ceil": int((comp["spd1_k"] == np.ceil(comp["spd1_p"] - 1e-9)).sum()),
                                   "median_diff": round(float(d.median()), 3), "mean_diff": round(float(d.mean()), 3)}
    g = j[j["n1_p"] / j["f1_p"] >= 0.5]
    dg = g["spd1_k"] - g["spd1_p"]
    res["all_gated_2021_23"] = {"n": int(len(g)), "median": round(float(dg.median()), 3),
                                "mean": round(float(dg.mean()), 3), "abs_gt_3": int((dg.abs() > 3).sum())}
    # 2 round disagreement
    sp = pd.read_parquet(EC.SPEEDS, columns=["source", "round", "match_id", "side", "ks_spd1"])
    md = sp[sp["source"].eq("mantennisdata") & sp["match_id"].notna()].merge(
        m.rename(columns={"round": "round_s0"}), on="match_id")
    res["mantd_round_mismatch_rows"] = int((md["round"] != md["round_s0"]).sum())
    res["mantd_linked_rows"] = int(len(md))
    # 4 same-player changes between consecutive editions of each Slam (main draws, n1 >= 20, n1-weighted per player)
    p = pd.read_parquet(EC.OUT / "engineer_panel0.parquet")
    p = p[p["slam"].ne("") & ~p["qualifying"].astype(bool) & ~p["implausible"] & (p["n1"] >= 20)]
    per = (p.assign(s=p["spd1"] * p["n1"]).groupby(["tour", "slam", "year", "player_id"])[["s", "n1"]].sum()
           .assign(v=lambda x: x["s"] / x["n1"])["v"].reset_index())
    pairs = []
    for (tour, slam), g in per.groupby(["tour", "slam"]):
        yrs = sorted(g["year"].unique())
        for y0, y1 in zip(yrs[:-1], yrs[1:]):
            a = g[g["year"].eq(y0)].set_index("player_id")["v"]
            b = g[g["year"].eq(y1)].set_index("player_id")["v"]
            common = a.index.intersection(b.index)
            if len(common) >= 10:
                pairs.append({"tour": tour, "slam": slam, "from": int(y0), "to": int(y1), "players": int(len(common)),
                              "median_change_kmh": round(float((b[common] - a[common]).median()), 2)})
    res["same_player_slam_changes"] = pairs
    # 3 frame coverage totals
    c = pd.read_csv(EC.OUT / "engineer_coverage_frame.csv")
    c["window"] = np.select([c["year"] <= 2023, c["year"] <= 2026], ["train_2013_23", "test_2024_26"], "")
    tot = c.groupby(["tour", "window"])[["frame", "both14", "both364", "one14", "neither364"]].sum()
    res["frame_totals"] = tot.reset_index().to_dict(orient="records")
    by_year = c.groupby(["tour", "year"])[["frame", "both14", "both364", "one14"]].sum()
    for col in ("both14", "both364", "one14"):
        by_year[f"{col}_share"] = (by_year[col] / by_year["frame"]).round(3)
    res["frame_by_year"] = by_year.reset_index().to_dict(orient="records")
    (EC.OUT / "engineer_misc.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "frame_by_year"}, indent=1, default=str))
    print(by_year.to_string())


if __name__ == "__main__":
    main()
