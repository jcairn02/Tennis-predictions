"""B3-referee, F14/F15: the confirmed scope (key statistics with y_raw >= own spd_max - 1; and the strict tier alone)
simulated: every flagged record marked not a candidate, panel.choose() re-run, value-level drops applied.
Writes data/studies/input_data_audit/fixes/B3-referee/f14_scope_sim.json and f14_scope_sim_rows.csv (read-only on the repo).
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


def simulate(rec, pan, s0m, nm, fl, PN):
    ms = fl[fl["linked"]][["match_id", "side"]].drop_duplicates()
    r = rec.merge(ms, on=["match_id", "side"], how="inner").copy()
    bad = r.set_index(KEY).index.isin(pd.MultiIndex.from_frame(fl[KEY]))
    r.loc[bad, "valid"] = False
    r.loc[bad, "invalid_reason"] = "b3"
    best = PN.choose(r, s0m)
    pr = pan.set_index(["match_id", "side"])
    best = best.merge(pr[["tour", "player_id", "drop_reason", "y", "source", "use", "year"]].rename(
        columns={"drop_reason": "old_drop", "y": "old_y", "source": "old_source", "use": "old_use"}),
        left_on=["match_id", "side"], right_index=True, how="left")
    low = np.where(best["tour"].eq("atp"), best["y"] < PN.MEN_MIN, best["y"] < PN.WOMEN_MIN)
    reason = best["drop_reason"].astype(object).copy()
    reason[(reason == "") & best["old_drop"].eq("no_clock").to_numpy()] = "no_clock"
    reason[(reason == "") & low] = "implausible"
    reason[(reason == "") & (best["n"].fillna(0).round() < PN.MIN_N)] = "low_n"
    best["new_use"] = reason.eq("")
    best["new_drop"] = reason
    best = best.merge(nm, left_on=["match_id", "side"], right_index=True, how="left")
    ch = best[best["old_use"].fillna(False)].copy()
    return ch


def main() -> None:
    from src.eda.serve_speed_tabpfn import panel as PN
    from f14_f16_speed import norms
    rec = pd.read_parquet(SP / "speed_records.parquet")
    pan = pd.read_parquet(SP / "speed_panel.parquet")
    s0m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "level"])
    u = pan[pan["use"]].copy()
    u = u.join(norms(u))
    nm = u.set_index(["match_id", "side"])[["norm_y", "norm_n"]]
    ks = rec["kind"].eq("keystat") & rec["spd_max"].notna()
    res, rows = {}, []
    for name, rule in (("strict", ks & (rec["y_raw"] > rec["spd_max"])),
                       ("ge_max_minus_1", ks & (rec["y_raw"] >= rec["spd_max"] - 1))):
        ch = simulate(rec, pan, s0m, nm, rec[rule], PN)
        ch["variant"] = name
        rows.append(ch)
        newu = ch[ch["new_use"]]
        res[name] = {"records": int(rule.sum()), "use_rows_affected": int(len(ch)),
                     "fallback_point_mean": int((ch["new_use"] & ch["kind"].eq("point_mean")).sum()),
                     "fallback_other": int((ch["new_use"] & ~ch["kind"].eq("point_mean")).sum()),
                     "no_fallback": int((~ch["new_use"]).sum()),
                     "test_years_2024_26_affected": int(ch["year"].between(2024, 2026).sum()),
                     "old_abs_dev_from_norm_median": float((ch["old_y"] - ch["norm_y"]).abs().median()),
                     "new_abs_dev_from_norm_median": float((newu["y"] - newu["norm_y"]).abs().median()),
                     "new_abs_dev_gt_10": int(((newu["y"] - newu["norm_y"]).abs() > 10).sum())}
    pd.concat(rows)[["variant", "match_id", "side", "player_id", "year", "old_source", "old_y", "source", "kind", "y", "n",
                     "new_use", "new_drop", "norm_y", "norm_n"]].to_csv(OUT / "f14_scope_sim_rows.csv", index=False)
    (OUT / "f14_scope_sim.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
