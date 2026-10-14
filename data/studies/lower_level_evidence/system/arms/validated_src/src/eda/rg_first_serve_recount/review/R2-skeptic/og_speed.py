"""R2-skeptic: a physical check for the Olympic rows (no fault speed is published there, but most points carry the
served ball's speed). If Sackmann were right on a "+" side, d of the official's second-serve points were really first
serves in, and their recorded speeds would look like that player's first serves. So, per side with speeds:
    fast2 = official second-serve points in play (PS2 / PR2 / A2) whose speed is at or above the player's own median
            first-serve speed in the match (first-serve points: PS1 / PR1 / A1)
Compared with the same measure on the agreeing sides (equal / other with equal serve points): an excess of fast second
serves on "+" sides near d would support Sackmann; none supports the official record.
The same for RG 2022-2025 from MatchBeats speeds (serve 2, not double faults), as a cross-check.
Writes og_speed.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/og_speed.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"


def og_side_speeds() -> pd.DataFrame:
    p = pd.read_parquet(OUT / "og_pbp.parquet")
    p = p[p["result"].notna()].copy()
    p["sp"] = pd.to_numeric(p["speed"], errors="coerce")
    rows = []
    for (u, srv), g in p.groupby(["unit", "server"]):
        f = g[g["result"].isin(["PS1", "PR1", "A1"]) & (g["sp"] > 0)]
        s = g[g["result"].isin(["PS2", "PR2", "A2"]) & (g["sp"] > 0)]
        med1 = f["sp"].median()
        rows.append({"unit": u, "athlete_code": srv, "n1_sp": len(f), "n2_sp": len(s), "med1": med1,
                     "fast2": int((s["sp"] >= med1).sum()) if len(f) else None,
                     "n2_all": int(g["result"].isin(["PS2", "PR2", "A2", "DF"]).sum())})
    return pd.DataFrame(rows)


def rg_side_speeds() -> pd.DataFrame:
    p = pd.read_parquet(OUT / "mb_points.parquet")
    order = {"match-beats": 0, "match-centre": 0, "match-beats-api": 1}
    p = p.assign(_o=p["route"].map(order))
    p = p[p["_o"].eq(p.groupby(["year", "code"])["_o"].transform("min")) & p["year"].between(2022, 2025)].copy()
    p["sp"] = pd.to_numeric(p["speed"], errors="coerce")
    rows = []
    for (y, c, srv), g in p.groupby(["year", "code", "server"]):
        f = g[g["serve"].eq("1") & (g["sp"] > 0)]
        s = g[g["serve"].eq("2") & ~g["result"].eq("DF") & (g["sp"] > 0)]
        med1 = f["sp"].median()
        rows.append({"year": y, "code": c, "mb_slot": int(srv), "n1_sp": len(f), "n2_sp": len(s), "med1": med1,
                     "fast2": int((s["sp"] >= med1).sum()) if len(f) else None})
    return pd.DataFrame(rows)


def compare(s: pd.DataFrame, label: str) -> dict:
    s = s[(s["n1_sp"] >= 10) & (s["n2_sp"] >= 5)].copy()
    agree = s["my_cls"].isin(["equal", "other"]) & s["raw_svpt"].eq(s["off_svpt"])
    base_rate = s.loc[agree, "fast2"].sum() / s.loc[agree, "n2_sp"].sum()
    out = {"label": label, "agreeing_sides": int(agree.sum()), "fast2_rate_agreeing": round(float(base_rate), 4)}
    for sign in ("+", "-", "0"):
        g = s[s["sign"].eq(sign) & s["my_cls"].isin(["split", "split_other"])]
        if g.empty:
            continue
        exp = g["n2_sp"] * base_rate
        cover = (g["n2_sp"] / (g["off_svpt"] - g["off_first_in"])).clip(upper=1)      # share of seconds with a speed
        out[sign] = {"sides": int(len(g)), "disputed_points": int(g["d_first_in"].abs().sum()),
                     "fast2_observed": int(g["fast2"].sum()), "fast2_expected_if_official_right": round(float(exp.sum()), 1),
                     "fast2_expected_if_sackmann_right_approx": round(float(exp.sum() + (g["d_first_in"].clip(lower=0)
                                                                                          * cover * 0.5).sum()), 1)}
    return out


def main() -> int:
    s = pd.read_parquet(OUT / "my_sides.parquet")
    s["sign"] = np.sign(s["d_first_in"]).map({1.0: "+", -1.0: "-", 0.0: "0"})
    og = s[s["event"].eq("OG")].merge(og_side_speeds(), on=["unit", "athlete_code"], how="left")
    rg = s[s["event"].eq("RG") & s["year"].between(2022, 2025)].merge(rg_side_speeds(), on=["year", "code", "mb_slot"],
                                                                      how="left")
    res = [compare(og, "OG 2024 (play-by-play speeds)"), compare(rg[rg["year"].eq(2022)], "RG 2022 (MatchBeats speeds)"),
           compare(rg[rg["year"].between(2023, 2025)], "RG 2023-2025 (MatchBeats speeds)")]
    (OUT / "og_speed.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
