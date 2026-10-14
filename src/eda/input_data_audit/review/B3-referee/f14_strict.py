"""B3-referee, F14/F15 refined: the rule "first-serve average strictly above the same record's own maximum", applied to
every record (chosen or not), with the panel's choice re-simulated once for all flagged records together.

Read-only. Writes data/studies/input_data_audit/fixes/B3-referee/f14_strict_rows.csv, f14_strict_scope.csv and
f14_strict_summary.json.

Also measures, on records that are NOT flagged, how a key statistic compares with an independent point mean of the same
player-match (the panel's KS_SHIFT says ks = ceiling of the point mean, so ks - pm should sit near +0.5), and the same
gap on the flagged records, to show which field (average or maximum) is wrong.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
SP = ROOT / "data/studies/serve_speed_tabpfn"
S0 = ROOT / "data/studies/predictability_diagnostic"
KEY = ["match_id", "side", "source", "source_key"]


def main() -> None:
    from src.eda.serve_speed_tabpfn import panel as PN
    sys.path.insert(0, str(Path(__file__).parent))
    from f14_f16_speed import norms  # noqa: E402
    rec = pd.read_parquet(SP / "speed_records.parquet")
    pan = pd.read_parquet(SP / "speed_panel.parquet")
    s0m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "level"])
    u = pan[pan["use"]].copy()
    u = u.join(norms(u))

    strict = rec["spd_max"].notna() & (rec["y_raw"] > rec["spd_max"])
    flagged = rec[strict].copy()
    summ = {"records_strict_all": int(strict.sum()),
            "by_source_valid": {f"{a}|{b}": int(v) for (a, b), v in flagged.groupby(["source", "valid"]).size().items()},
            "linked": int(flagged["linked"].sum())}

    # independent point mean vs key statistic on the same player-match
    pm = rec[rec["kind"].eq("point_mean") & rec["valid"]].sort_values("n", ascending=False).drop_duplicates(["match_id", "side"])
    ks = rec[rec["kind"].eq("keystat") & rec["valid"]].copy()
    ks = ks.merge(pm[["match_id", "side", "y", "n"]].rename(columns={"y": "pm_y", "n": "pm_n"}), on=["match_id", "side"])
    ks["gap"] = ks["y_raw"] - ks["pm_y"]
    ks["strict"] = ks["spd_max"].notna() & (ks["y_raw"] > ks["spd_max"])
    ks["near"] = ks["spd_max"].notna() & (ks["y_raw"] >= ks["spd_max"] - 1) & ~ks["strict"]
    summ["ks_minus_pointmean"] = {
        grp: {"n": int(len(g)), "median": float(g["gap"].median()), "p10": float(g["gap"].quantile(.1)),
              "p90": float(g["gap"].quantile(.9)), "share_gt_5": float((g["gap"] > 5).mean())}
        for grp, g in (("not_flagged", ks[~ks["strict"] & ~ks["near"]]), ("strict_gt_max", ks[ks["strict"]]),
                       ("within_1_or_equal", ks[ks["near"]])) if len(g)}

    # re-simulate the panel's choice for every player-match that holds a strict record
    ms = flagged[flagged["linked"]][["match_id", "side"]].drop_duplicates()
    r = rec.merge(ms, on=["match_id", "side"], how="inner").copy()
    bad = r.set_index(KEY).index.isin(pd.MultiIndex.from_frame(flagged[KEY]))
    r.loc[bad, "valid"] = False
    r.loc[bad, "invalid_reason"] = "b3_strict"
    best = PN.choose(r, s0m)
    pr = pan.set_index(["match_id", "side"])
    best = best.merge(pr[["tour", "player_id", "drop_reason", "y", "source", "use"]].rename(
        columns={"drop_reason": "old_drop", "y": "old_y", "source": "old_source", "use": "old_use"}),
        left_on=["match_id", "side"], right_index=True, how="left")
    low = np.where(best["tour"].eq("atp"), best["y"] < PN.MEN_MIN, best["y"] < PN.WOMEN_MIN)
    reason = best["drop_reason"].astype(object).copy()
    reason[(reason == "") & best["old_drop"].eq("no_clock").to_numpy()] = "no_clock"
    reason[(reason == "") & low] = "implausible"
    reason[(reason == "") & (best["n"].fillna(0).round() < PN.MIN_N)] = "low_n"
    best["new_use"] = reason.eq("")
    best["new_drop"] = reason
    nm = u.set_index(["match_id", "side"])[["norm_y", "norm_n"]]
    best = best.merge(nm, left_on=["match_id", "side"], right_index=True, how="left")
    best["changed"] = (best["old_source"] != best["source"]) | (best["old_use"] != best["new_use"])
    best["old_minus_norm"] = best["old_y"] - best["norm_y"]
    best["new_minus_norm"] = np.where(best["new_use"], best["y"] - best["norm_y"], np.nan)
    keep = ["match_id", "side", "player_id", "tour", "old_source", "old_y", "old_use", "old_minus_norm", "source", "y", "n",
            "new_use", "new_drop", "new_minus_norm", "norm_y", "norm_n", "changed"]
    best[keep].to_csv(OUT / "f14_strict_rows.csv", index=False)
    ch = best[best["changed"] & best["old_use"].fillna(False)]
    summ["player_matches_with_a_strict_record"] = int(len(best))
    summ["use_rows_changed"] = int(len(ch))
    summ["use_rows_changed_fallback"] = ch["new_use"].value_counts().to_dict()
    summ["use_rows_changed_fallback_source"] = ch[ch["new_use"]]["source"].value_counts().to_dict()
    summ["old_minus_norm_abs_median"] = float(ch["old_minus_norm"].abs().median())
    summ["new_minus_norm_abs_median"] = float(ch["new_minus_norm"].abs().median())
    summ["new_minus_norm_abs_gt_10"] = ch[ch["new_minus_norm"].abs() > 10][
        ["match_id", "side", "old_y", "y", "source", "norm_y", "norm_n"]].round(1).astype(str).to_dict("records")
    summ["old_minus_norm_le_10_among_changed"] = ch[ch["old_minus_norm"].abs() <= 10][
        ["match_id", "side", "old_y", "y", "source", "norm_y", "norm_n"]].round(1).astype(str).to_dict("records")
    # the scope file: every strict record, identified as in speed_records.parquet
    flagged[KEY + ["y_raw", "spd_max", "n", "spd2_raw", "valid", "invalid_reason"]].to_csv(
        OUT / "f14_strict_scope.csv", index=False)
    (OUT / "f14_strict_summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
