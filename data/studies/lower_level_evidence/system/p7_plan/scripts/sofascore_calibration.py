"""The P7 plan's counting calibration (section 2.3): SofaScore's box-score counts against the box score Stage 0 already
holds for the same match (Sackmann's or TML's official counts), from a candidate Stage 0's box layers (role F's
box_layers.parquet: kind "identical" or "revision", old = Stage 0's counts, new = SofaScore's). Per count, tour, level
and year: player rows compared, the share exactly equal, and the mean and SD of SofaScore minus official.

It compares two sources' records of the same match (a data-quality check, as the timeline's linker compares set
scores); it uses no count as evidence of a player's performance. --max-year (default 2024) keeps the 2025-2026 holdout's
box scores unread until the lead says the holdout is spent (this run's checkpoint 3); on the P7 day run it with
--max-year 2026 --levels ITF after the unlock.

Run: ./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/sofascore_calibration.py \
        --candidate data/studies/lower_level_evidence/system/stage0/C0_P7 --out <csv> [--levels ITF] [--max-year 2026]
The plan's rule (fixed before P7 lands): a count passes when, over the ITF rows compared, the exact agreement is >= 90%
and |mean difference| <= 0.25 per player-match; a failing count is a decision point for the lead (P7_plan.md 2.3).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("C:/Users/zerom/Documents/Tennis-predictions")
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as C  # noqa: E402

COUNTS = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
AGREE_MIN, MEAN_MAX = 0.90, 0.25


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default="sofascore")
    ap.add_argument("--levels", default="", help="buckets to keep, comma list (e.g. ITF); default all")
    ap.add_argument("--max-year", type=int, default=2024)
    a = ap.parse_args()
    cand = Path(a.candidate)
    L = pd.read_parquet(cand / "box_layers.parquet")
    L = L[L["source"].eq(a.source) & L["kind"].isin(["identical", "revision"])]
    m = C.load_matches(cand, columns=["year", "map_level", "tour", "tournament_date"])
    m = m[~C.in_holdout(m["tournament_date"])] if a.max_year <= 2024 else m
    L = L.merge(m[["match_id", "year", "bucket", "tour"]], on="match_id", how="inner")
    L = L[L["year"] <= a.max_year]
    if a.levels:
        L = L[L["bucket"].isin([x.strip() for x in a.levels.split(",") if x.strip()])]
    rows = []
    for (tour, lvl, yr), g in L.groupby(["tour", "bucket", "year"]):
        for c in COUNTS:
            old = np.r_[g[f"old_A_{c}"].to_numpy(float), g[f"old_B_{c}"].to_numpy(float)]
            new = np.r_[g[f"new_A_{c}"].to_numpy(float), g[f"new_B_{c}"].to_numpy(float)]
            ok = np.isfinite(old) & np.isfinite(new)
            if not ok.any():
                continue
            d = new[ok] - old[ok]
            rows.append({"tour": tour, "level": lvl, "year": int(yr), "count": c, "player_rows": int(ok.sum()),
                         "exact_share": round(float((d == 0).mean()), 4), "mean_diff": round(float(d.mean()), 3),
                         "sd_diff": round(float(d.std()), 3)})
    t = pd.DataFrame(rows)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(out, index=False)
    if len(t):
        pooled = (t.assign(w=t["player_rows"], e=t["exact_share"] * t["player_rows"], s=t["mean_diff"] * t["player_rows"])
                  .groupby("count")[["w", "e", "s"]].sum())
        pooled["exact_share"] = (pooled["e"] / pooled["w"]).round(4)
        pooled["mean_diff"] = (pooled["s"] / pooled["w"]).round(3)
        pooled["passes"] = (pooled["exact_share"] >= AGREE_MIN) & (pooled["mean_diff"].abs() <= MEAN_MAX)
        pooled = pooled.rename(columns={"w": "player_rows"})[["player_rows", "exact_share", "mean_diff", "passes"]]
        print(pooled.to_string())
        out.with_suffix(".json").write_text(json.dumps({"filters": vars(a), "matches": int(len(L)),
                                                        "pooled": pooled.reset_index().to_dict("records")},
                                                       indent=1, default=str), encoding="utf-8")
    print(f"{len(L):,} matches compared; {len(t)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
