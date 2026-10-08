"""R4 red team (auditor): values-only sanity of the built columns (features/speed.parquet), 2022-2026 (2022-23 as the
reference period). No outcome of any kind is read: only the feature file and the frame keys' level.

Per tour x season x Slam / non-Slam: matches; spd_f's mean (side A is random, so about 0), SD, 1/5/50/95/99th
percentiles, the share exactly 0 (no history on either side), the share |spd_f| < 0.05, the share clipped at +-4, the
largest |value|; spd_f_all for women; spd_raw's presence, SD and clipping; corr(spd_f, spd_raw) where both exist; the
per-side posterior SD and history counts. Also: the matches at the clip, and the 2024-26 distribution against 2022-23
(a two-sample KS distance on spd_f, men non-Slam and Slam).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_r4_values.py
Writes data/studies/serve_speed_tabpfn/design/auditor_r4_values.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design" / "auditor_r4_values.json"
FEAT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "features" / "speed.parquet"
KEYS = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "frame_keys.parquet"


def main() -> None:
    s = pd.read_parquet(FEAT)
    k = pd.read_parquet(KEYS, columns=["match_id", "level"])
    s = s.merge(k, on="match_id", how="left", validate="one_to_one")
    s["slam"] = s["level"].eq("GS")
    s = s[s["season"] >= 2022]
    rows = []
    for (tour, season, slam), g in s.groupby(["tour", "season", "slam"]):
        col = g["spd_f"] if tour == "atp" else g["spd_f_all"]
        q = col.quantile([0.01, 0.05, 0.5, 0.95, 0.99]).round(3).to_list()
        r = {"tour": tour, "season": int(season), "slam": bool(slam), "matches": int(len(g)),
             "column": "spd_f" if tour == "atp" else "spd_f_all (spd_f is 0)",
             "mean": round(float(col.mean()), 4), "sd": round(float(col.std()), 4), "p01_p05_p50_p95_p99": q,
             "share_exact_0": round(float((col == 0).mean()), 4),
             "share_abs_lt_0.05": round(float((col.abs() < 0.05).mean()), 4),
             "clipped": int((col.abs() >= 4).sum()), "max_abs": round(float(col.abs().max()), 3),
             "spd_f_women_nonzero": int((g["spd_f"] != 0).sum()) if tour == "wta" else None,
             "spd_raw_present": int(g["spd_raw"].notna().sum()),
             "spd_raw_sd": round(float(g["spd_raw"].std()), 4) if g["spd_raw"].notna().sum() > 1 else None,
             "spd_raw_clipped": int((g["spd_raw"].abs() >= 4).sum()),
             "corr_spd_f_spd_raw": round(float(g[["spd_f", "spd_raw"]].dropna().corr().iloc[0, 1]), 3)
             if g["spd_raw"].notna().sum() > 30 and tour == "atp" else None,
             "median_f_sd_a": round(float(g["f_sd_a"].median()), 3),
             "median_hist_a": float(g["hist_a"].median())}
        rows.append(r)
    res = {"reads_results": False, "by_tour_season_slam": rows}
    # 2024-26 against 2022-23 (men, spd_f): two-sample KS distance
    men = s[s["tour"].eq("atp")]
    res["ks_distance_vs_2022_23"] = {}
    for slam in (False, True):
        ref = men[(men["season"] <= 2023) & (men["slam"] == slam)]["spd_f"]
        for season in (2024, 2025, 2026):
            x = men[(men["season"] == season) & (men["slam"] == slam)]["spd_f"]
            r_ = ks_2samp(ref, x)
            res["ks_distance_vs_2022_23"][f"{'slam' if slam else 'non_slam'}_{season}"] = round(float(r_.statistic), 4)
    # the largest values: are they plausible (sides' f_hat, history counts)?
    top = men.reindex(men["spd_f_unclipped_km_h"].abs().sort_values(ascending=False).index).head(10)
    res["largest_men"] = top[["match_id", "season", "spd_f", "spd_f_unclipped_km_h", "f_hat_a", "f_hat_b", "hist_a",
                              "hist_b", "k14_a", "k14_b", "f_sd_a", "f_sd_b"]].round(3).to_dict(orient="records")
    # side-level f_hat range (km/h), men 2024-26
    sides = pd.concat([men[["season", "f_hat_a"]].rename(columns={"f_hat_a": "f"}),
                       men[["season", "f_hat_b"]].rename(columns={"f_hat_b": "f"})])
    res["men_side_f_hat"] = {int(se): {"sd": round(float(g["f"].std()), 3), "min": round(float(g["f"].min()), 2),
                                       "max": round(float(g["f"].max()), 2),
                                       "share_abs_gt_8": round(float((g["f"].abs() > 8).mean()), 5)}
                             for se, g in sides.groupby("season")}
    OUT.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    print(pd.DataFrame(rows).drop(columns=["column"]).to_string(index=False))
    print(json.dumps(res["ks_distance_vs_2022_23"]))
    print(json.dumps(res["men_side_f_hat"]))
    print(pd.DataFrame(res["largest_men"]).to_string(index=False))


if __name__ == "__main__":
    main()
