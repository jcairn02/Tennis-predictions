"""R1 design checks of the integration strategist that need no match result:

    determinism     the base arm "model" exists in two folders for 2019 seeds 0-2 (feature interactions' and the
                    rating race's): are the saved forecasts identical? (decides whether reused base fits are safe)
    seed intervals  in the surface-IOS study's PUBLISHED results.csv, how often a four-week-block interval comparing two
                    single seeds of the same arm excludes 0 (re-reading a published table; no new outcome computation)
    published       B-INJ's capture slope and column-arm result (feature interactions, published)

Writes data/studies/serve_speed_tabpfn/design/strategist_checks.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/strategist_checks.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design"
FI = ROOT / "data" / "studies" / "feature_interactions"
RACE = ROOT / "data" / "studies" / "surface_rating_race" / "local"


def determinism() -> dict:
    rows = []
    for p in sorted((FI / "local").glob("model__*__seed*.npz")):
        q = RACE / p.name
        if not q.exists():
            continue
        with np.load(p) as a, np.load(q) as b:
            same_ids = bool(np.array_equal(a["ids_td"], b["ids_td"]))
            rows.append({"file": p.name, "same_ids": same_ids,
                         "max_abs_diff": float(np.abs(a["p_td"] - b["p_td"]).max()) if same_ids else None})
    return {"pairs": len(rows), "all_identical": all(r["same_ids"] and r["max_abs_diff"] == 0.0 for r in rows),
            "rows": rows}


def seed_intervals() -> dict:
    r = pd.read_csv(ROOT / "data" / "studies" / "surface_ios" / "results.csv")
    s = r[r["base"].str.contains(r"_s\d$") & r["model"].str.contains(r"_s\d$") & r["window"].str.fullmatch(r"\d{4}")]
    s = s.assign(excl=(s["lo"] > 0) | (s["hi"] < 0), z=s["gain"] / ((s["hi"] - s["lo"]) / (2 * 1.98)))
    out = {}
    for metric, g in s.groupby("metric"):
        out[metric] = {"rows": int(len(g)), "share_excluding_0": float(g["excl"].mean()), "sd_z": float(g["z"].std())}
    return out


def published() -> dict:
    g5 = json.loads((FI / "g5" / "binj_g5.json").read_text(encoding="utf-8"))
    fin = json.loads((FI / "final" / "final_results.json").read_text(encoding="utf-8"))
    return {"binj_capture_slope": g5["capture"]["slope"], "binj_corr_dev_term": g5["capture"]["corr_dev_term"],
            "binj_pooled_z": g5["capture"]["z_pooled"], "binj_column_arm_2025_2026": fin["column_arm"]}


def main() -> int:
    res = {"rules": "no match result read; published tables re-read", "determinism": determinism(),
           "seed_vs_seed_block_intervals": seed_intervals(), "published": published()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "strategist_checks.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    d = res["determinism"]
    print({"determinism_pairs": d["pairs"], "all_identical": d["all_identical"]})
    print(json.dumps(res["seed_vs_seed_block_intervals"], indent=1))
    print(json.dumps(res["published"], indent=1)[:900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
