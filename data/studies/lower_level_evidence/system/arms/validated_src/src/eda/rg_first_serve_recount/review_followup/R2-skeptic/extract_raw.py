"""R2-skeptic (round 2): Stage 0's raw rows of Roland Garros 2019-2026, read once with the build's own loader
(stage0_build.normalise(stage0_build.load_raw())), and the override keys' match counts over the whole raw table.

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    raw_rg.parquet       every raw row (any source) whose normalised tournament id is <year>-520 (2019-2026) or whose
                         tournament name says Roland Garros: the build's keys (source, tour, tid, round, wkey, lkey),
                         names, score, minutes, the nine counts per side, _source_file, _row
    override_keys.csv    for every row of the lead's proposed_overrides.csv: how many raw rows of its source carry its
                         key in the WHOLE raw table (apply_box_overrides needs exactly one)
Memory: the raw table is held once, filtered, then freed.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/extract_raw.py
"""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"


def main() -> int:
    raw = B.normalise(B.load_raw())
    key = raw["source"] + "|" + raw["tour"] + "|" + raw["tid"] + "|" + raw["round"] + "|" + raw["wkey"] + "|" + raw["lkey"]
    ov = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    want = ov["source"] + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|" + ov["loser_key"]
    counts = key[key.isin(set(want))].value_counts()
    pd.DataFrame({"feed_key": ov["feed_key"], "stage0_match_id": ov["stage0_match_id"], "key": want,
                  "raw_rows_with_key": want.map(counts).fillna(0).astype(int)}).to_csv(OUT / "override_keys.csv",
                                                                                      index=False)
    rg = raw["tid"].str.fullmatch(r"20(19|2[0-6])-520") | raw["tourney_name"].str.contains("roland", case=False)
    keep = (["source", "group", "tour", "tid", "tourney_id", "tourney_name", "tourney_date", "round", "winner_name",
             "loser_name", "winner_id", "loser_id", "wkey", "lkey", "score", "minutes", "best_of", "_source_file", "_row",
             "rid"] + B.OVERRIDE_COUNTS)
    sub = raw.loc[rg, keep].copy()
    del raw, key
    gc.collect()
    for c in B.OVERRIDE_COUNTS:
        sub[c] = sub[c].astype(str)
    sub["_row"] = pd.to_numeric(sub["_row"], errors="coerce").astype("Int64")
    sub.to_parquet(OUT / "raw_rg.parquet", index=False)
    print(sub.groupby(["source", "tour", "tid"]).size().to_string())
    print("override keys: rows naming exactly one raw row:",
          int(want.map(counts).fillna(0).eq(1).sum()), "of", len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
