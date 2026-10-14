"""R1-rederive: serve speeds as a check of RG's serve labels on the '-' and '0' sides (RG 2023-2025, radar courts).

If RG had labelled k second-serve points as first serves on a side where Sackmann has k more second-serve points
('-' sides), those k points would carry second-serve speeds while labelled serve 1. Per side, count the serve-1 points
whose speed is at most the server's own median second-serve speed in the match ("slow first serves"), and compare the
classes (equal sides are the control). Writes speed_sides.csv and prints the comparison.
Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/speeds.py
"""
from __future__ import annotations

import glob
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.ingest.point_sources.infosys_slams import blocks_of, decrypt  # noqa: E402

HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive"
RAW = ROOT / "data" / "raw" / "point_sources" / "infosys_slams" / "RG"


def main() -> None:
    rows = []
    for year, route in ((2023, "match-beats"), (2024, "match-beats"), (2025, "match-centre")):
        for path in sorted(glob.glob(str(RAW / str(year) / route / "*.json.gz"))):
            code = Path(path).name.split(".")[0]
            with gzip.open(path, "rb") as fh:
                blocks = blocks_of(route, json.loads(fh.read()))
            if "mbData" not in blocks:
                continue
            mb = decrypt(blocks["mbData"])
            if not isinstance(mb, dict) or not mb.get("setData"):
                continue
            sp = {"1": {1: [], 2: []}, "2": {1: [], 2: []}}
            for st in mb.get("setData") or []:
                for g in st.get("gameData") or []:
                    for p in g.get("pointData") or []:
                        t, s, v = str(p.get("server")), p.get("serve"), p.get("serveSpeed") or 0
                        if t in sp and s in (1, 2) and v > 0 and p.get("result") != "DF":
                            sp[t][s].append(float(v))
            pdx = mb.get("playerData") or {}
            for t in ("1", "2"):
                s1, s2 = np.array(sp[t][1]), np.array(sp[t][2])
                med2 = float(np.median(s2)) if len(s2) >= 5 else np.nan
                rows.append({"year": year, "code": code, "player_id": str(pdx.get(f"tm{t}Ply1Id")), "n1_spd": len(s1),
                             "n2_spd": len(s2), "med1": float(np.median(s1)) if len(s1) else np.nan, "med2": med2,
                             "slow1": int((s1 <= med2).sum()) if not np.isnan(med2) else np.nan})
    sp = pd.DataFrame(rows)
    d = pd.read_csv(HERE / "sides.csv", keep_default_na=False, na_values=[""], dtype={"rec_id": str})
    d = d[d["event"].eq("RG") & d["year"].ge(2023)]
    j = d.merge(sp, left_on=["year", "key", "rec_id"], right_on=["year", "code", "player_id"], how="inner")
    j = j[j["n1_spd"].ge(20) & j["n2_spd"].ge(5)]
    j["lab"] = np.where(j["cls"].isin(["split", "split_other"]), "split" + j["sign"], j["cls"])
    j["slow1_share"] = j["slow1"] / j["n1_spd"]
    j.to_csv(HERE / "speed_sides.csv", index=False)
    g = j.groupby("lab").agg(sides=("lab", "size"), slow1_mean=("slow1", "mean"), share=("slow1_share", "mean"),
                             k_mean=("d_first_in", "mean"))
    print(g.round(3).to_string())
    # the '-' sides: does the excess of slow first serves over the equal sides' share reach |k|?
    base = j.loc[j["lab"].eq("equal"), "slow1_share"].mean()
    m = j[j["lab"].eq("split-")].copy()
    m["expected_slow_if_rg_right"] = base * m["n1_spd"]
    m["excess"] = m["slow1"] - m["expected_slow_if_rg_right"]
    print(f"'-' sides with speeds: {len(m)}; mean excess of slow first serves over the equal sides' share "
          f"{m['excess'].mean():.2f} (mean |k| {(-m['d_first_in']).mean():.2f})")


if __name__ == "__main__":
    main()
