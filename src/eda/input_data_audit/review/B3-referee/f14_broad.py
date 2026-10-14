"""B3-referee, F14 variants: rule ">= max" and ">= max - 1" applied to every record; fallback simulated for each variant.

Read-only. Writes data/studies/input_data_audit/fixes/B3-referee/f14_variants.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
SP = ROOT / "data/studies/serve_speed_tabpfn"
S0 = ROOT / "data/studies/predictability_diagnostic"
KEY = ["match_id", "side", "source", "source_key"]


def main() -> None:
    from src.eda.serve_speed_tabpfn import panel as PN
    from f14_f16_speed import norms
    rec = pd.read_parquet(SP / "speed_records.parquet")
    pan = pd.read_parquet(SP / "speed_panel.parquet")
    s0m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "level"])
    u = pan[pan["use"]].copy()
    u = u.join(norms(u))
    nm = u.set_index(["match_id", "side"])[["norm_y", "norm_n"]]
    pr = pan.set_index(["match_id", "side"])
    res = {}
    for name, rule in (("gt", rec["y_raw"] > rec["spd_max"]), ("ge", rec["y_raw"] >= rec["spd_max"]),
                       ("ge_minus1", rec["y_raw"] >= rec["spd_max"] - 1)):
        rule = rule & rec["spd_max"].notna()
        fl = rec[rule]
        ms = fl[fl["linked"]][["match_id", "side"]].drop_duplicates()
        r = rec.merge(ms, on=["match_id", "side"], how="inner").copy()
        bad = r.set_index(KEY).index.isin(pd.MultiIndex.from_frame(fl[KEY]))
        r.loc[bad, "valid"] = False
        r.loc[bad, "invalid_reason"] = "b3"
        best = PN.choose(r, s0m)
        best = best.merge(pr[["tour", "drop_reason", "y", "source", "use"]].rename(
            columns={"drop_reason": "old_drop", "y": "old_y", "source": "old_source", "use": "old_use"}),
            left_on=["match_id", "side"], right_index=True, how="left")
        low = np.where(best["tour"].eq("atp"), best["y"] < PN.MEN_MIN, best["y"] < PN.WOMEN_MIN)
        reason = best["drop_reason"].astype(object).copy()
        reason[(reason == "") & best["old_drop"].eq("no_clock").to_numpy()] = "no_clock"
        reason[(reason == "") & low] = "implausible"
        reason[(reason == "") & (best["n"].fillna(0).round() < PN.MIN_N)] = "low_n"
        best["new_use"] = reason.eq("")
        best = best.merge(nm, left_on=["match_id", "side"], right_index=True, how="left")
        ch = best[best["old_use"].fillna(False) & ((best["old_source"] != best["source"]) | ~best["new_use"])]
        same_val = ch["new_use"] & ((ch["y"] - ch["old_y"]).abs() <= 0.6)
        res[name] = {"records": int(rule.sum()), "records_by_source": fl["source"].value_counts().to_dict(),
                     "use_rows_affected": int(len(ch)),
                     "fallback_point_mean": int((ch["new_use"] & ch["kind"].eq("point_mean")).sum()),
                     "fallback_keystat_same_value": int((same_val & ch["kind"].eq("keystat")).sum()),
                     "fallback_keystat_other_value": int((ch["new_use"] & ch["kind"].eq("keystat") & ~same_val).sum()),
                     "fallback_mc": int((ch["new_use"] & ch["kind"].eq("mc_floor")).sum()),
                     "no_fallback": int((~ch["new_use"]).sum()),
                     "old_abs_dev_from_norm_median": float((ch["old_y"] - ch["norm_y"]).abs().median()),
                     "new_abs_dev_from_norm_median": float((ch.loc[ch["new_use"], "y"] - ch.loc[ch["new_use"], "norm_y"]).abs().median())}
    (OUT / "f14_variants.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
