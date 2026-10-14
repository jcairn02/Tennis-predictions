"""Stage 2, part 4: the shot-level rows in the list of every feature tried so far.

Every row the shared harness has scored, from the predictability diagnostic's Stage 4 rundown, the UFC study's stages
(A, B, C, D and D's profiles) and this study's Stage 2, in one table: the same pool, the same walk-forward fit and the
same scores (alone, given surface Elo, given the closing odds), so the rows are comparable. Ranked per tour by the gain on
the closing odds, and also given Elo. These are the original harness's numbers; the feature-alpha audit's repaired
rebuild of the leading box-score profile is quoted separately in the write-up.

Run:  ./python.sh src/eda/shot_level/stage2_list.py
Writes data/studies/shot_level/stage2_feature_list.csv (one row per scored row of every study) and
stage2_feature_list.json (per tour: the ranks of the shot-level rows, the top rows overall).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import common as S  # noqa: E402

SOURCES = [("predictability_diagnostic stage 4", ROOT / "data/studies/predictability_diagnostic/stage4_ranking.csv")] + \
          [(f"ufc_ideas {p.stem.replace('_ranking', '')}", p) for p in sorted((ROOT / "data/studies/ufc_ideas").glob("stage*_ranking.csv"))] + \
          [("shot_level stage 2", S.OUT / "stage2_ranking.csv")]
KEEP = ["tour", "id", "form", "name", "group", "inputs", "alone_imp", "elo_imp", "elo_lo", "elo_hi", "elo_scored",
        "market_imp", "market_lo", "market_hi", "market_scored", "elo_clears_line", "market_clears_line", "reading"]


def main() -> int:
    parts = []
    for study, path in SOURCES:
        if not path.exists():
            continue
        r = pd.read_csv(path)
        for c in KEEP:
            if c not in r:
                r[c] = np.nan
        r = r[KEEP].copy()
        r.insert(0, "study", study)
        parts.append(r)
    t = pd.concat(parts, ignore_index=True)
    t["shot_level"] = t["study"].eq("shot_level stage 2")
    out = {}
    for tour, g in t.groupby("tour"):
        g = g.copy()
        g["rank_market"] = g["market_imp"].rank(ascending=False, method="min")
        g["rank_elo"] = g["elo_imp"].rank(ascending=False, method="min")
        t.loc[g.index, "rank_market"] = g["rank_market"]
        t.loc[g.index, "rank_elo"] = g["rank_elo"]
        sl = g[g["shot_level"]]
        best_m = sl.sort_values("market_imp", ascending=False).head(5)
        best_e = sl.sort_values("elo_imp", ascending=False).head(5)
        out[tour] = {
            "rows": int(len(g)), "shot_level_rows": int(len(sl)),
            "top_market": g.sort_values("market_imp", ascending=False).head(10)[["study", "id", "form", "inputs", "market_imp", "market_lo", "market_hi", "elo_imp"]].to_dict("records"),
            "top_elo": g.sort_values("elo_imp", ascending=False).head(10)[["study", "id", "form", "inputs", "elo_imp", "elo_lo", "elo_hi", "market_imp"]].to_dict("records"),
            "shot_best_market": best_m[["id", "form", "inputs", "market_imp", "market_lo", "market_hi", "rank_market", "elo_imp", "rank_elo"]].to_dict("records"),
            "shot_best_elo": best_e[["id", "form", "inputs", "elo_imp", "elo_lo", "elo_hi", "rank_elo", "market_imp", "rank_market"]].to_dict("records"),
            "shot_in_top_50_market": int((sl["rank_market"] <= 50).sum()),
            "shot_in_top_50_elo": int((sl["rank_elo"] <= 50).sum()),
            "earlier_rows_with_market_above_best_shot": int(((~g["shot_level"]) & (g["market_imp"] > sl["market_imp"].max())).sum()),
            "earlier_rows_with_elo_above_best_shot": int(((~g["shot_level"]) & (g["elo_imp"] > sl["elo_imp"].max())).sum()),
        }
    t.to_csv(S.OUT / "stage2_feature_list.csv", index=False)
    (S.OUT / "stage2_feature_list.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    with pd.option_context("display.width", 250):
        for tour, o in out.items():
            print(tour, {k: v for k, v in o.items() if not isinstance(v, list)})
            print(pd.DataFrame(o["top_market"]).round(3).to_string())
            print(pd.DataFrame(o["shot_best_market"]).round(3).to_string())
            print(pd.DataFrame(o["top_elo"]).round(3).to_string())
            print(pd.DataFrame(o["shot_best_elo"]).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
