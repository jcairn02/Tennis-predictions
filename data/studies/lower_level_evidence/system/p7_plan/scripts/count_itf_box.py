"""G's dry run, step 2a (counting only, no outcome read): ITF and ITFQ box-score matches per tour and season in a Stage 0,
the same rows role B's level_seasons counts (completed, standard format, has_box), and whether each season_used would
pass B's two-season rule on the count part (>= 100 box-score matches in >= 2 seasons of the fit window, results in by
the season's cutoff). Also: how many of those matches the reference strength file covers (relationship.load drops
rows whose opponent strength is missing: TourStat's np.isfinite(elo_opp) filter).

Run: ./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/count_itf_box.py <stage0 folder> <out.csv>
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path("C:/Users/zerom/Documents/Tennis-predictions")
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as C  # noqa: E402

STRENGTH = ROOT / "data/studies/lower_level_evidence/system/classes/strength_elo.parquet"
FIT_SEASONS, FIRST_TARGET_YEAR, MIN_MATCHES, MIN_SEASONS = 6, 2011, 100, 2   # relationship.py:93-103


def main() -> int:
    stage0, out = Path(sys.argv[1]), Path(sys.argv[2])
    m = C.load_matches(stage0, columns=["tour", "year", "map_level", "status", "format", "has_box", "tournament_date"])
    m = m[m["bucket"].isin(["ITF", "ITFQ"])]
    box = m["status"].eq("completed") & m["format"].eq("standard") & m["has_box"].fillna(False).astype(bool)
    s_ids = set(pq.read_table(STRENGTH, columns=["match_id"]).column(0).to_pylist())
    m = m.assign(box=box, in_strength=m["match_id"].isin(s_ids))
    g = (m[m["box"]].groupby(["tour", "bucket", "year"])
         .agg(box_matches=("match_id", "size"), box_matches_in_reference_strength=("in_strength", "sum"))
         .reset_index())
    g.to_csv(out, index=False)
    print(g[g["year"].between(2013, 2026)].to_string(index=False))
    # season_used -> seasons of the window (lo - 2 .. hi, relationship.level_seasons) with >= 100 box-score matches
    rows = []
    for (tour, lvl), gg in g.groupby(["tour", "bucket"]):
        have = dict(zip(gg["year"], gg["box_matches"]))
        for Y in range(2013, 2027):
            lo, hi = max(FIRST_TARGET_YEAR, Y - FIT_SEASONS), Y - 1
            yrs = [y for y in range(lo - 2, hi + 1) if have.get(y, 0) >= MIN_MATCHES]
            rows.append({"tour": tour, "level": lvl, "season_used": Y, "seasons_with_100": ",".join(map(str, yrs)),
                         "count_rule_met": len(yrs) >= MIN_SEASONS})
    r = pd.DataFrame(rows)
    r.to_csv(out.with_name(out.stem + "_season_rule.csv"), index=False)
    print(r[r["count_rule_met"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
