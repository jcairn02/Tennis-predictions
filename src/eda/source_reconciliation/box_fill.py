"""Blank box scores in Stage 0 that another source on disk could fill: for each Stage 0 match without a full box,
which readers hold a full box (all nine counts, both players) for it, by tour, level group and season.

A fill changes no count the model already reads; it adds information where Stage 0 has none (its row failed a check,
its source published none, or the source has no such draw). How such data enters is decided by kind elsewhere (the
frozen-reference rule, the gap-fill policy of 14 Oct 2026); this only measures what exists, and how well each
source agrees with Stage 0 where both hold the match (engine_pairs.csv), so the two can be read together.

Writes data/studies/source_reconciliation/box/fill_candidates.csv (tour x level group x season x reader: Stage 0
matches without a full box, of them with a full box in the reader) and fill_summary.json.
Run: ./python.sh src/eda/source_reconciliation/box_fill.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation.box_engine import LEVEL_GROUP  # noqa: E402

BOX = C.OUT / "box"
READERS = BOX / "readers"
SKIP = {"lead_stage0", "lead_sackmann_raw", "lead_tml_raw"}


def full_matches(path: Path) -> pd.Series:
    f = pd.read_parquet(path, columns=["match_id", "player_id", "complete"] + C.COUNTS)
    f = f.drop_duplicates(["match_id", "player_id"])
    ok = f[C.COUNTS].notna().all(axis=1)
    per = ok.groupby(f["match_id"]).agg(["sum", "size"])
    return per.index[(per["sum"] == 2) & (per["size"] == 2)].to_series()


def main() -> int:
    m = pd.read_parquet(C.SNAP / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "map_level", "status", "box_status"])
    m["level_group"] = m["map_level"].map(LEVEL_GROUP).fillna("other")
    played = m["status"].isin(["completed", "retired"])
    blank = m[played & m["box_status"].ne("full")].copy()
    rows = []
    summary = {"stage0_played_without_full_box": int(len(blank)),
               "by_box_status": blank["box_status"].value_counts().to_dict(), "readers": {}}
    for path in sorted(READERS.glob("*.parquet")):
        name = path.stem
        if name in SKIP:
            continue
        if not {"reader", "match_id", "player_id", "complete"} <= set(pq.read_schema(path).names):
            continue
        fm = set(full_matches(path))
        hit = blank["match_id"].isin(fm)
        g = blank.assign(filled=hit).groupby(["tour", "level_group", "year"]).agg(
            blank=("match_id", "size"), fillable=("filled", "sum")).reset_index()
        g = g[g["fillable"] > 0]
        g.insert(0, "reader", name)
        rows.append(g)
        summary["readers"][name] = int(hit.sum())
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(BOX / "fill_candidates.csv", index=False)
    C.write_json(BOX / "fill_summary.json", summary)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
