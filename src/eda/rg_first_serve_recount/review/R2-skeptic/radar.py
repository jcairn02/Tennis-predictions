"""R2-skeptic: a physical referee for RG 2023-2025. MatchBeats stores, on second-serve points, the radar speed of the
faulted first serve (faultSrvSpd > 0); never on first-serve points (0 of ~150k). A recorded fault speed means a first
serve was struck and missed, so the point was played on the second serve (or was a double fault).

Per player row (the official record's MatchBeats, this player serving):
    n2_off   official second-serve points = svpt - official first serves in
    n_fs     second-serve points with a recorded fault speed (a lower bound on the true second-serve points)
    n2_sack  Sackmann's second-serve points = svpt - Sackmann's first serves in
Tests:
    refutes_sackmann   n_fs > n2_sack: Sackmann's row has fewer second-serve points than the radar's faulted first
                       serves, so Sackmann's first serves in are impossible (too high) by at least n_fs - n2_sack
    full_cover         n_fs == n2_off: every official second-serve point carries a measured fault
For "-" rows (official first serves in above Sackmann's), the fault speeds cannot show an official error (serve-1
points never carry one), so the serve speeds are used instead: a first-serve point whose speed is at or below the
player's own median second-serve speed in that match is "slow". Its frequency per row is compared between "-" rows and
the equal rows of the same editions (a mislabelled second serve would show as an excess of slow first serves).

Writes radar_sides.csv and radar_summary.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/radar.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"


def per_side(pts: pd.DataFrame) -> pd.DataFrame:
    order = {"match-beats": 0, "match-centre": 0, "match-beats-api": 1}
    pts = pts.assign(_o=pts["route"].map(order))
    pts = pts[pts["_o"].eq(pts.groupby(["year", "code"])["_o"].transform("min"))].copy()
    pts["sp"] = pd.to_numeric(pts["speed"], errors="coerce")
    pts["fs"] = pd.to_numeric(pts["fault_speed"], errors="coerce")
    rows = []
    for (y, c, srv), g in pts.groupby(["year", "code", "server"]):
        s1 = g[g["serve"].eq("1")]
        s2 = g[g["serve"].eq("2")]
        s2_in = s2[~s2["result"].eq("DF")]
        med2 = s2_in.loc[s2_in["sp"] > 0, "sp"].median()
        sp1 = s1.loc[s1["sp"] > 0, "sp"]
        rows.append({"year": y, "code": c, "mb_slot": int(srv), "n1": len(s1), "n2": len(s2),
                     "n_fs": int((s2["fs"] > 0).sum()), "n2_with_speed": int((s2["sp"] > 0).sum()),
                     "n1_with_speed": int(len(sp1)), "med_sp1": sp1.median(), "med_sp2in": med2,
                     "n1_slow": int((sp1 <= med2).sum()) if pd.notna(med2) else None,
                     "n_df": int(s2["result"].eq("DF").sum()),
                     "n_df_fs": int((s2["result"].eq("DF") & (s2["fs"] > 0)).sum())})
    return pd.DataFrame(rows)


def main() -> int:
    s = pd.read_parquet(OUT / "my_sides.parquet")
    pts = pd.read_parquet(OUT / "mb_points.parquet")
    pts = pts[pts["year"].between(2019, 2025)]
    r = per_side(pts)
    s = s[s["event"].eq("RG")].merge(r, on=["year", "code", "mb_slot"], how="left")
    s["n2_off"] = s["off_svpt"] - s["off_first_in"]
    s["n2_sack"] = s["raw_svpt"] - s["raw_first_in"]
    s["mb_complete_side"] = s["mb_svpt"].eq(s["off_svpt"]) & s["mb_first_in"].eq(s["off_first_in"])
    s["refutes_sackmann"] = s["n_fs"] > s["n2_sack"]
    s["full_cover"] = s["n_fs"].eq(s["n2_off"])
    s["sign"] = np.sign(s["d_first_in"]).map({1.0: "+", -1.0: "-", 0.0: "0"})
    v = pd.read_csv(OUT / "value_check.csv", usecols=["fix", "source_file", "source_row", "side"])
    s = s.merge(v, on=["source_file", "source_row", "side"], how="left")
    s.to_csv(OUT / "radar_sides.csv", index=False)

    out = {}
    rad = s[s["year"].between(2023, 2025)]
    # coverage: share of official second-serve points carrying a fault speed, by year and draw
    cov = rad[rad["mb_complete_side"]].groupby(["year", "draw"]).apply(
        lambda g: pd.Series({"sides": len(g), "fs_share": round(g["n_fs"].sum() / g["n2_off"].sum(), 4),
                             "full_cover_sides": int(g["full_cover"].sum())}))
    out["coverage"] = cov.reset_index().to_dict("records")
    # control of the referee: on rows where Sackmann and the official agree (equal / other), the radar never
    # refutes the shared count (if it did, the radar or its attachment would be unreliable)
    eq = rad[rad["my_cls"].isin(["equal", "other"]) & rad["mb_complete_side"]]
    out["agreeing_rows_refuted"] = {"rows": int(len(eq)), "refuted": int(eq["refutes_sackmann"].sum()),
                                    "official_second_points_without_fault_speed": int((eq["n2_off"] - eq["n_fs"]).sum())}
    # proposed rows
    prop = rad[rad["fix"].notna()]
    out["proposed_2023_2025"] = prop.groupby(["fix", "sign"]).apply(
        lambda g: pd.Series({"sides": len(g), "mb_complete": int(g["mb_complete_side"].sum()),
                             "refutes_sackmann": int(g["refutes_sackmann"].sum()),
                             "full_cover": int(g["full_cover"].sum()),
                             "refuted_or_full_cover_plus": int((g["refutes_sackmann"]).sum())})).reset_index() \
        .to_dict("records")
    # "+" rows: how many of Sackmann's extra first serves the radar disproves (n_fs - n2_sack, capped at d)
    plus = prop[prop["sign"].eq("+")].copy()
    plus["disproved"] = np.clip(plus["n_fs"] - plus["n2_sack"], 0, None)
    plus["disproved"] = np.minimum(plus["disproved"], plus["d_first_in"])
    out["plus_extra_first_serves"] = {"sides": int(len(plus)), "extra_first_serves": int(plus["d_first_in"].sum()),
                                      "disproved_by_radar": int(plus["disproved"].sum()),
                                      "sides_fully_disproved": int((plus["disproved"] == plus["d_first_in"]).sum()),
                                      "sides_partly_disproved": int(((plus["disproved"] > 0)
                                                                     & (plus["disproved"] < plus["d_first_in"])).sum()),
                                      "sides_not_disproved": int((plus["disproved"] == 0).sum())}
    # "-" rows: slow first serves, against the equal rows of the same editions
    def slow(g):
        g = g[g["n1_with_speed"] >= 10]
        return pd.Series({"sides": len(g), "slow_first_serves": int(g["n1_slow"].sum()),
                          "per_side": round(float(g["n1_slow"].mean()), 3) if len(g) else None,
                          "first_with_speed": int(g["n1_with_speed"].sum()),
                          "slow_share": round(float(g["n1_slow"].sum() / g["n1_with_speed"].sum()), 4) if len(g) else None,
                          "moved_points": int(-g.loc[g["d_first_in"] < 0, "d_first_in"].sum())})
    out["minus_slow_first_serves"] = rad[rad["my_cls"].isin(["equal", "split", "split_other"])].groupby(
        ["sign"]).apply(slow).reset_index().to_dict("records")
    allyears = s[s["year"].between(2019, 2025) & s["my_cls"].isin(["equal", "split", "split_other"])]
    out["minus_slow_first_serves_by_year"] = allyears.groupby(["year", "sign"]).apply(slow).reset_index() \
        .to_dict("records")
    (OUT / "radar_summary.json").write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
