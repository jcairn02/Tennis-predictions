"""Coverage across the splice: which draws Stage 0 still receives once Tennis My Life is its only source of results.

TML publishes ATP main-tour, Challenger main-draw, ATP qualifying and WTA main-tour season files, with no women's
qualifying, WTA 125, ITF or Challenger qualifying files, all of which Sackmann's files carried. This compares Stage 0's
matches of 1 June - 28 September 2026 with the same weeks of 2025, by tour, level and draw, and lists which held
official source has box scores for the draws TML lacks (from the match-timing link files).

Writes data/studies/data_continuity/coverage_splice.csv. Run: ./python.sh src/eda/data_continuity/coverage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402

WINDOW = ("06-01", "09-29")      # tournament weeks; Stage 0's TML copy runs to the week of 21 Sep 2026


def main() -> int:
    m, _ = K.load_stage0()
    m["tdate"] = pd.to_datetime(m["tournament_date"], errors="coerce")
    links = {}
    for name in ("wta_api", "tdi", "slam_feeds", "sofascore"):
        lk = pd.read_parquet(K.LINKS / f"{name}.parquet", columns=["match_id"])
        links[name] = set(lk["match_id"])
    parts = []
    for year in (2025, 2026):
        s = m[(m["tdate"] >= f"{year}-{WINDOW[0]}") & (m["tdate"] < f"{year}-{WINDOW[1]}")].copy()
        s["draw"] = s["qualifying"].map({True: "qualifying", False: "main"})
        g = s.groupby(["tour", "level", "draw"]).agg(matches=("match_id", "size"), with_box=("has_box", "sum"))
        for name, ids in links.items():
            g[f"linked_{name}"] = s.assign(x=s["match_id"].isin(ids)).groupby(["tour", "level", "draw"])["x"].sum()
        parts.append(g.add_suffix(f"_{year}"))
    out = pd.concat(parts, axis=1).fillna(0).astype(int)
    out["kept_share"] = (out["matches_2026"] / out["matches_2025"].where(out["matches_2025"] > 0)).round(3)
    out = out.reset_index()
    out.to_csv(K.OUT / "coverage_splice.csv", index=False)
    print(out[["tour", "level", "draw", "matches_2025", "matches_2026", "kept_share", "linked_wta_api_2026",
               "linked_tdi_2026", "linked_slam_feeds_2026"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
