"""R2-skeptic: which record is right on the disputed rows? The points the two records book on different serves have a
fingerprint: the share the server won.

Per side, d = Sackmann's first serves in - the official's; dw = Sackmann's first-serve points won - the official's.
If the official record is right and Sackmann books a + error (a true second-serve point as a first serve, never a double
fault: double faults agree in classes A and B), the moved point is won at p2in (the side's rate on second-serve points
in play); a - error books a true first-serve point as a second serve, won at p1. If instead the official record is wrong
on a point, the roles swap. Expected moved-point wins under each hypothesis are computed from each side's own official
rates (p1 = first-serve points won / first serves in; p2in = second-serve points won / (second-serve points - double
faults)), so the comparison respects who served where.

    H_off   the official record is right; every disagreement is Sackmann's error:
            "+" rows: E[dw] = d * p2in;  "-" rows: E[-dw] = |d| * p1
    H_sack  Sackmann is right; every disagreement is the official record's error:
            "+" rows: E[dw] = d * p1;    "-" rows: E[-dw] = |d| * p2in
For "0" rows (moved points both ways, net 0) dw has E = n (p2in - p1) < 0 under H_off (n pairs), E = n (p1 - p2in) > 0 under
H_sack, and 0 when each record makes the same kind of error (a second serve booked as a first) once.

Writes moved_points.csv (by fix, sign, |d| bin, event, draw) and moved_points.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/moved_points.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"


def rates(s: pd.DataFrame) -> pd.DataFrame:
    s = s.copy()
    s["p1"] = s["off_first_won"] / s["off_first_in"]
    s["p2in"] = s["off_second_won"] / (s["off_svpt"] - s["off_first_in"] - s["off_df"])
    s["p2"] = s["off_second_won"] / (s["off_svpt"] - s["off_first_in"])
    return s


def summarise(g: pd.DataFrame) -> dict:
    d = g["d_first_in"].abs()
    dw = np.where(g["d_first_in"] > 0, g["d_first_won"], -g["d_first_won"])     # wins among the moved points
    out = {"rows": int(len(g)), "moved": int(d.sum()), "won": int(np.sum(dw)),
           "share": round(float(np.sum(dw) / d.sum()), 4) if d.sum() else None}
    plus = g["d_first_in"] > 0
    e_off = np.where(plus, d * g["p2in"], d * g["p1"])
    e_sack = np.where(plus, d * g["p1"], d * g["p2in"])
    var_off = np.where(plus, d * g["p2in"] * (1 - g["p2in"]), d * g["p1"] * (1 - g["p1"]))
    var_sack = np.where(plus, d * g["p1"] * (1 - g["p1"]), d * g["p2in"] * (1 - g["p2in"]))
    if d.sum():
        out.update({"expected_if_official_right": round(float(np.nansum(e_off)), 1),
                    "z_official_right": round(float((np.sum(dw) - np.nansum(e_off)) / np.sqrt(np.nansum(var_off))), 2),
                    "expected_if_sackmann_right": round(float(np.nansum(e_sack)), 1),
                    "z_sackmann_right": round(float((np.sum(dw) - np.nansum(e_sack)) / np.sqrt(np.nansum(var_sack))), 2),
                    "mean_p1": round(float(g["p1"].mean()), 3), "mean_p2in": round(float(g["p2in"].mean()), 3)})
    else:     # "0" rows: the change in first-serve points won
        out.update({"sum_d_first_won": int(g["d_first_won"].sum()),
                    "expected_per_pair_if_official_right": round(float((g["p2in"] - g["p1"]).mean()), 3)})
    return out


def main() -> int:
    v = pd.read_csv(OUT / "value_check.csv", low_memory=False)
    v = rates(v)
    v["sign"] = np.sign(v["d_first_in"]).map({1: "+", -1: "-", 0: "0"})
    v["dbin"] = pd.cut(v["d_first_in"].abs(), [-1, 0, 1, 2, 3, 5, 10, 200], labels=["0", "1", "2", "3", "4-5", "6-10", "11+"])
    res = {}
    rows = []
    for keys in (["fix", "sign"], ["event", "draw", "sign"], ["fix", "sign", "dbin"], ["event", "year", "draw", "sign"]):
        for k, g in v.groupby(keys, observed=True):
            rec = {**dict(zip(keys, k if isinstance(k, tuple) else (k,))), **summarise(g)}
            rec["grouping"] = "+".join(keys)
            rows.append(rec)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "moved_points.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 300)
    pd.set_option("display.max_columns", 30)
    print(t.drop(columns=["grouping"]).to_string())
    (OUT / "moved_points.json").write_text(json.dumps(rows, indent=1, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
