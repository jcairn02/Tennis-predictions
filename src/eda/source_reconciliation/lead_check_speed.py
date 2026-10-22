"""The lead's re-check of subagent 6's speed headlines (Part G), from its files, by separate code:
    1. the rows ks_within5 changes in the history (histories/current.parquet against histories/ks_within5.parquet);
    2. the share of key-statistic rows more than 5 and 10 km/h from a complete point mean (panel_rows.parquet), and
       whether, where they differ by more than 5, the point mean sits nearer the player's norm;
    3. the matches whose spd_L moves by at least 0.25, 0.5 and 1 unit under ks_within5 (spdl/current.parquet against
       spdl/ks_within5.parquet), scenario B, men's 2024-2026 and 2019-2023 matches of the template frame.
No result of any match is read. Writes data/studies/source_reconciliation/speed/lead_check.json.
Run: ./python.sh src/eda/source_reconciliation/lead_check_speed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402

SPD = C.OUT / "speed"


def main() -> int:
    out = {}
    cur = pd.read_parquet(SPD / "histories" / "current.parquet")
    alt = pd.read_parquet(SPD / "histories" / "ks_within5.parquet")
    key = ["match_id", "side"]
    j = cur[key + ["y", "source"]].merge(alt[key + ["y"]], on=key, suffixes=("", "_alt"), how="outer", indicator=True)
    changed = j["_merge"].eq("both") & ((j["y"] - j["y_alt"]).abs() > 1e-9)
    out["history_rows"] = {"current": int(len(cur)), "ks_within5": int(len(alt)),
                           "only_in_one": int((j["_merge"] != "both").sum()), "changed": int(changed.sum()),
                           "changed_by_source": j[changed]["source"].value_counts().to_dict(),
                           "abs_change_quantiles": j.loc[changed, "y"].sub(j.loc[changed, "y_alt"]).abs()
                           .quantile([0.1, 0.5, 0.9]).round(2).tolist()}
    pr = pd.read_parquet(SPD / "panel_rows.parquet")
    ks = pr[pr["kind"].astype(str).str.contains("ks|key", case=False, regex=True) & pr["ref_mb"].notna()
            & pr["pt_complete"].astype("boolean").fillna(False)]
    d = (ks["y_mb"] - ks["ref_mb"]).abs()
    out["key_statistic_vs_complete_point_mean"] = {"rows": int(len(ks)), "beyond_5": round(float((d > 5).mean()), 4),
                                                   "beyond_10": round(float((d > 10).mean()), 4)}
    big = ks[d > 5]
    if "norm_dev" in big:
        out["where_beyond_5"] = {"rows": int(len(big)), "norm_dev_median_abs": round(float(big["norm_dev"].abs().median()), 2)}
    a = pd.read_parquet(SPD / "spdl" / "current.parquet", columns=["match_id", "spd_L_B"])
    b = pd.read_parquet(SPD / "spdl" / "ks_within5.parquet", columns=["match_id", "spd_L_B"])
    frame = pd.read_parquet(C.STUDIES / "current_best_model" / "template_2026-10-14" / "model_frame.parquet",
                            columns=["match_id", "tour", "season"])
    s = a.merge(b, on="match_id", suffixes=("", "_alt")).merge(frame, on="match_id")
    s = s[s["tour"].eq("atp")]
    mv = (s["spd_L_B"] - s["spd_L_B_alt"]).abs()
    for label, mask in (("2024-26", s["season"].between(2024, 2026)), ("2019-23", s["season"].between(2019, 2023))):
        x = mv[mask & s["spd_L_B"].notna() & s["spd_L_B_alt"].notna()]
        out[f"spdL_B_moves_{label}"] = {"matches": int(mask.sum()), "with_both": int(len(x)),
                                        "ge_0_25": int((x >= 0.25).sum()), "ge_0_5": int((x >= 0.5).sum()),
                                        "ge_1": int((x >= 1).sum()), "max": round(float(x.max()), 3)}
    C.write_json(SPD / "lead_check.json", out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
