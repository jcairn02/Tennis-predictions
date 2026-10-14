"""R1-rederive (group SVX): Stage 0's raw rows of the Australian Open 2025, as the build reads them.

One load: stage0_build.normalise(stage0_build.load_raw()). Keeps every row of tournament id 2025-580 (Sackmann) and
TML's rows named "Australian Open" of 2025, with the nine counts as read, the key columns, and the live Stage 0 match
each raw row became (match id, box status), joined on source file and row.

Writes data/studies/rg_first_serve_recount/followup/review/R1-rederive/work/stage0_ao_rows.parquet.
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/stage0_ao_rows.py
"""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive" / "work"
COUNTS = list(C.BOX_SOURCE_NAMES.values())


def main() -> None:
    df = B.normalise(B.load_raw())
    gc.collect()
    keep = (df["source"].eq("sackmann") & df["tid"].eq("2025-580")) | \
        (df["source"].eq("tml") & df["season"].astype("float").eq(2025) &
         df["tourney_name"].str.contains("australian open", case=False))
    cols = ["rid", "source", "group", "tour", "season", "tid", "tourney_id", "tourney_name", "round", "match_num",
            "winner_id", "loser_id", "winner_name", "loser_name", "wkey", "lkey", "score", "best_of", "winner_ioc",
            "loser_ioc", "_source_file", "_row"] + [f"{s}_{c}" for s in "wl" for c in COUNTS]
    ao = df.loc[keep, cols].copy()
    del df
    gc.collect()
    for c in [f"{s}_{k}" for s in "wl" for k in COUNTS]:
        ao[c] = B.num(ao[c])
    m = pd.read_parquet(C.MATCHES, columns=["match_id", "source_file", "source_row", "has_box", "box_status",
                                            "status_detail", "year", "tournament_id"])
    m = m[m["year"].eq(2025)]
    ao = ao.merge(m[["source_file", "source_row", "match_id", "has_box", "box_status", "status_detail"]]
                  .rename(columns={"source_file": "_source_file", "source_row": "_row", "match_id": "s0_match_id",
                                   "has_box": "s0_has_box", "box_status": "s0_box_status",
                                   "status_detail": "s0_status_detail"}), on=["_source_file", "_row"], how="left")
    ao.to_parquet(OUT / "stage0_ao_rows.parquet", index=False)
    print(ao.groupby(["source", "tour", ao["round"].str.fullmatch(r"Q\d")]).size().to_string())
    print("in the live Stage 0:", int(ao["s0_match_id"].notna().sum()), "of", len(ao))


if __name__ == "__main__":
    main()
