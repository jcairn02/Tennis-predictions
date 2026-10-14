"""R2-skeptic: does the official record ever book a true first serve as a second serve on the "+" rows (which would make
Sackmann right there)? RG 2023-2025, radar fault speeds.

If Sackmann were right on k of a "+" side's d disputed points, those k official second-serve points had no faulted first
serve, so they carry no fault speed: the side's uncovered official second-serve points (n2_off - n_fs) would exceed what
the radar's coverage on that court predicts by k. Coverage is taken from the same match's other side when that side is
an agreeing row (equal or other with equal serve points), so court, day and radar are the same.

Also, per "+" side: disproved = min(d, n_fs - n2_sack) of Sackmann's d extra first serves are impossible by the radar.

Writes radar_excess.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/radar_excess.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"


def main() -> int:
    s = pd.read_csv(OUT / "radar_sides.csv", low_memory=False)
    s = s[s["year"].between(2023, 2025) & s["mb_complete_side"]].copy()
    s["unc"] = s["n2_off"] - s["n_fs"]
    agree = s["my_cls"].isin(["equal", "other"]) & s["raw_svpt"].eq(s["off_svpt"])
    key = ["year", "code"]
    base = s[agree][key + ["n2_off", "unc"]].rename(columns={"n2_off": "o_n2", "unc": "o_unc"})
    plus = s[s["sign"].eq("+") & s["fix"].notna()].merge(base, on=key, how="inner")
    plus = plus[plus["o_n2"] > 0]
    plus["cov_rate_unc"] = plus["o_unc"] / plus["o_n2"]
    plus["exp_unc"] = plus["n2_off"] * plus["cov_rate_unc"]
    out = {}
    for name, g in (("all_plus_paired", plus), ("plus_d1", plus[plus["d_first_in"].eq(1)]),
                    ("plus_d2_3", plus[plus["d_first_in"].between(2, 3)]), ("plus_d4up", plus[plus["d_first_in"] >= 4]),
                    ("opponent_full_cover", plus[plus["o_unc"].eq(0)])):
        out[name] = {"sides": int(len(g)), "disputed_points": int(g["d_first_in"].sum()),
                     "uncovered_observed": int(g["unc"].sum()), "uncovered_expected_if_official_right":
                     round(float(g["exp_unc"].sum()), 1),
                     "uncovered_expected_if_sackmann_right": round(float(g["exp_unc"].sum() + g["d_first_in"].sum()), 1),
                     "sides_with_unc_ge_d": int((g["unc"] >= g["d_first_in"]).sum())}
    # in matches where the opponent's second serves are fully covered (radar on every faulted first serve), how often
    # does the "+" side have an uncovered point at all?
    full = plus[plus["o_unc"].eq(0)]
    out["opponent_full_cover_detail"] = {"plus_sides": int(len(full)),
                                         "plus_sides_with_zero_uncovered": int(full["unc"].eq(0).sum()),
                                         "plus_sides_uncovered_values": full["unc"].value_counts().sort_index().to_dict()}
    # equal-vs-equal: how often does one side have uncovered points when the other is fully covered (radar misses)
    eqs = s[agree].merge(base, on=key)
    eqs = eqs[(eqs["n2_off"] != eqs["o_n2"]) | (eqs["unc"] != eqs["o_unc"]) | True]
    pairs = s[agree].groupby(key).filter(lambda g: len(g) == 2)
    pr = []
    for k, g in pairs.groupby(key):
        a, b = g.iloc[0], g.iloc[1]
        for x, y in ((a, b), (b, a)):
            if y["unc"] == 0 and y["n2_off"] > 0:
                pr.append(x["unc"])
    out["agreeing_pairs_when_other_full_cover"] = {"sides": len(pr), "with_zero_uncovered": int(sum(u == 0 for u in pr)),
                                                   "uncovered_total": int(sum(pr))}
    (OUT / "radar_excess.json").write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
