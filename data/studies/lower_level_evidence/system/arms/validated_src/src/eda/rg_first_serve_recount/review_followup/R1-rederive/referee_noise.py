"""R1-rederive (round 2): how noisy are the referees, and do they read RG's or the row's value on the small differences?

Baseline: sides of RG 2019-2025 where the row and RG's statistics agree on first serves in, and the referee holds the
player's points (its serve points equal RG's; Court Vision: 2019, 2020, 2022 only, no point lacking its second serve).
The referee's first serves in minus the agreed value gives its own noise. Then the disputed sides of W22 (proposed or
referee_contradicts matches), by the size of the row's difference from RG: how often the referee reads RG's value, and
how often the row's.

Writes referee_noise.csv. Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/referee_noise.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"


def main() -> None:
    d = pd.read_csv(HERE / "sides.csv", low_memory=False)
    m = pd.read_csv(HERE / "matches.csv", low_memory=False)
    d = d.merge(m[["rid", "cls", "group_id"]], on="rid").copy()
    d["dfi"] = d["raw_first_in"] - d["off_first_in"]
    out = []
    for ref, years in (("mcp", list(range(2019, 2026))), ("cv", [2019, 2020, 2022])):
        held = d["year"].isin(years) & d[f"{ref}_svpt"].eq(d["off_svpt"])
        if ref == "cv":
            held &= d["cv_gap"].fillna(0).eq(0)
        base = d[held & d["raw_first_in"].eq(d["off_first_in"])]
        e = base[f"{ref}_first_in"] - base["off_first_in"]
        for k, v in e.clip(-3, 3).value_counts().sort_index().items():
            out.append({"referee": ref, "set": "baseline_row_equals_rg", "size": int(k), "sides": int(v),
                        "share": round(v / len(base), 4), "reads_rg": None, "reads_row": None})
        dis = d[held & d["group_id"].eq("W22") & d["cls"].isin(["proposed", "referee_contradicts"]) & d["dfi"].ne(0)]
        for k, g in dis.groupby(dis["dfi"].clip(-3, 3)):
            out.append({"referee": ref, "set": "disputed_W22_by_row_minus_rg", "size": int(k), "sides": int(len(g)),
                        "share": None, "reads_rg": int(g[f"{ref}_first_in"].eq(g["off_first_in"]).sum()),
                        "reads_row": int(g[f"{ref}_first_in"].eq(g["raw_first_in"]).sum())})
    r = pd.DataFrame(out)
    r.to_csv(HERE / "referee_noise.csv", index=False)
    print(r.to_string())


if __name__ == "__main__":
    main()
