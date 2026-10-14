"""Design R1 (speed-data engineer), step 3: the basis offset between the ATP Stats Centre's key statistic ("1st Serve
Average Speed": ManTennisData, and the handoff's decrypted copy of the same files) and the point mean of timed first
serves in (the held Infosys points, stage1_points_infosys; SirGenkii for Jan-Apr 2025). Values only; no result.

Questions: the median, mean and spread of key statistic - point mean on the same player-matches; whether it depends on
the number of first serves or on how complete the point table is; and whether a constant offset or a per-match rule
(rounding) explains it.

Completeness of the point table for a player-match: f1 (first-serve-in points in the table, timed or not) equals the key
statistics' own count of first serves in (ks_first_in), and n1 (timed) equals f1.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_basis.py
Writes data/studies/serve_speed_tabpfn/design/engineer_basis.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402


def summarise(d: pd.Series) -> dict:
    d = d.dropna()
    return {"n": int(len(d)), "median": round(float(d.median()), 3), "mean": round(float(d.mean()), 3),
            "sd": round(float(d.std()), 3), "mad": round(float((d - d.median()).abs().median()), 3),
            "abs_gt_1": int((d.abs() > 1).sum()), "abs_gt_3": int((d.abs() > 3).sum()), "q": EC.q(d)}


def rules(ks: pd.Series, pm: pd.Series) -> dict:
    return {"equal_ceil": int((ks == np.ceil(pm - 1e-9)).sum()), "equal_round": int((ks == np.round(pm)).sum()),
            "equal_floor": int((ks == np.floor(pm + 1e-9)).sum()), "n": int(len(ks)),
            "in_0_1": int(((ks - pm >= -1e-9) & (ks - pm < 1)).sum())}


def main() -> None:
    r = pd.read_parquet(EC.RECORDS)
    r = r[r["linked"]]
    pts = r[r["source"].isin(["infosys", "sirgenkii"])][["source", "match_id", "side", "spd1", "n1", "f1", "spd1_sum",
                                                          "spd1_sumsq", "timed_share"]]
    out = {"reads_results": False}
    for ks_src in ("mantennisdata", "handoff_ks"):
        ks = r[r["source"].eq(ks_src) & r["spd1"].notna()].drop_duplicates(["match_id", "side"], keep=False)
        ks = ks[["match_id", "side", "spd1", "ks_first_in", "ks_first_total", "points_missing"]].rename(
            columns={"spd1": "ks"})
        for psrc in ("infosys", "sirgenkii"):
            p = pts[pts["source"].eq(psrc)]
            j = ks.merge(p, on=["match_id", "side"])
            j = j[j["n1"] > 0]
            if j.empty:
                continue
            j["d"] = j["ks"] - j["spd1"]
            j["complete"] = (j["f1"] == j["ks_first_in"]) & (j["n1"] == j["f1"])
            j["gate"] = j["timed_share"] >= 0.5
            j["cover"] = j["n1"] / j["ks_first_in"]
            key = f"{ks_src}_vs_{psrc}"
            res = {"all": summarise(j["d"]), "gated": summarise(j.loc[j["gate"], "d"]),
                   "complete": summarise(j.loc[j["complete"], "d"]),
                   "incomplete_gated": summarise(j.loc[~j["complete"] & j["gate"], "d"]),
                   "rules_complete": rules(j.loc[j["complete"], "ks"], j.loc[j["complete"], "spd1"]),
                   "rules_gated": rules(j.loc[j["gate"], "ks"], j.loc[j["gate"], "spd1"]),
                   "share_complete": round(float(j["complete"].mean()), 4)}
            # dependence on the number of first serves (gated rows)
            g = j[j["gate"]].copy()
            g["n_bin"] = pd.cut(g["ks_first_in"], [0, 20, 30, 40, 50, 60, 80, 200])
            res["by_first_in"] = (g.groupby("n_bin", observed=True)["d"]
                                  .agg(n="size", median="median", mean="mean", sd="std",
                                       p90=lambda x: x.quantile(0.9)).round(3).reset_index()
                                  .astype({"n_bin": str}).to_dict(orient="records"))
            g["cov_bin"] = pd.cut(g["cover"], [0, 0.6, 0.8, 0.9, 0.95, 0.99, 1.0001, 10])
            res["by_coverage_timed_over_box"] = (g.groupby("cov_bin", observed=True)["d"]
                                                 .agg(n="size", median="median", mean="mean", sd="std")
                                                 .round(3).reset_index().astype({"cov_bin": str})
                                                 .to_dict(orient="records"))
            # within-match sd of first-serve speeds (from points) -> the sampling sd of a match mean
            sd_srv = np.sqrt(np.maximum(g["spd1_sumsq"] / g["n1"] - (g["spd1_sum"] / g["n1"]) ** 2, 0))
            res["within_match_sd_first_serve_kmh"] = EC.q(sd_srv)
            if "points_missing" in j and j["points_missing"].notna().any():
                res["by_points_missing_flag"] = (j[j["gate"]].groupby(j["points_missing"].astype(str))["d"]
                                                 .agg(n="size", median="median", mean="mean", sd="std").round(3)
                                                 .reset_index().to_dict(orient="records"))
            # the big gaps: what they look like
            big = g[g["d"].abs() > 3]
            res["big_gaps"] = {"n": int(len(big)), "share_complete": round(float(big["complete"].mean()), 3),
                               "cover_median": round(float(big["cover"].median()), 3),
                               "first_in_minus_table_f1_median": float((big["ks_first_in"] - big["f1"]).median()),
                               "sign_positive_share": round(float((big["d"] > 0).mean()), 3)}
            ok = g[g["d"].abs() <= 3]
            res["small_gaps"] = {"n": int(len(ok)), "share_complete": round(float(ok["complete"].mean()), 3),
                                 "cover_median": round(float(ok["cover"].median()), 3)}
            out[key] = res
            EC.log(f"{key}: all {res['all']['median']:+.3f}/{res['all']['mean']:+.3f} (n={res['all']['n']}); "
                   f"complete {res['complete']['median']:+.3f}/{res['complete']['mean']:+.3f} "
                   f"(n={res['complete']['n']}); rules on complete {res['rules_complete']}")
    (EC.OUT / "engineer_basis.json").write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, default=str)[:12000])


if __name__ == "__main__":
    main()
