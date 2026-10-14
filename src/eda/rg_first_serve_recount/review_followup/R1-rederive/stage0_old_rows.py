"""R1-rederive (SVX addendum): Stage 0's raw rows of the Australian Open 2018-2024 and 2026, and Roland Garros 2013-2015.

One load: stage0_build.normalise(stage0_build.load_raw()). Keeps the rows of tournament ids <year>-580 (AO) and
<year>-520 (RG) of those editions, from both sources, with the nine counts as read and the live Stage 0 match each raw
row became (match id, source, box status), joined on source file and row.

Writes data/studies/rg_first_serve_recount/followup/review/R1-rederive/work/stage0_old_rows.parquet.
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/stage0_old_rows.py
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
TIDS = {f"{y}-580" for y in (2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026)} | {f"{y}-520" for y in (2013, 2014, 2015)}


def main() -> None:
    df = B.normalise(B.load_raw())
    gc.collect()
    season = df["season"].astype("float")
    name = df["tourney_name"].str.lower()
    if "--rg2016-2018" in sys.argv:      # the SVX addendum 2: Roland Garros 2016-2018 (written to its own file)
        rg_years, ao_years, tag = [2016, 2017, 2018], [], "_rg1618"
    else:
        rg_years, ao_years, tag = [2013, 2014, 2015], [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026], ""
    tids = {f"{y}-580" for y in ao_years} | {f"{y}-520" for y in rg_years}
    # Sackmann's WTA files of 2013-2015 give Roland Garros another tournament id: take the names too
    by_name = (season.isin(rg_years) & name.str.contains("roland garros|french open", regex=True)) | \
        (season.isin(ao_years) & name.str.contains("australian open"))
    keep = (df["tid"].isin(tids) | by_name) & season.isin(rg_years + ao_years)
    cols = ["rid", "source", "group", "tour", "season", "tid", "tourney_id", "tourney_name", "round", "match_num",
            "winner_id", "loser_id", "winner_name", "loser_name", "wkey", "lkey", "score", "best_of", "winner_ioc",
            "loser_ioc", "_source_file", "_row"] + [f"{s}_{c}" for s in "wl" for c in COUNTS]
    x = df.loc[keep, cols].copy()
    del df
    gc.collect()
    for c in [f"{s}_{k}" for s in "wl" for k in COUNTS]:
        x[c] = B.num(x[c])
    m = pd.read_parquet(C.MATCHES, columns=["match_id", "source_file", "source_row", "has_box", "box_status",
                                            "status_detail", "source"])
    x = x.merge(m.rename(columns={"source_file": "_source_file", "source_row": "_row", "match_id": "s0_match_id",
                                  "has_box": "s0_has_box", "box_status": "s0_box_status",
                                  "status_detail": "s0_status_detail", "source": "s0_source"}),
                on=["_source_file", "_row"], how="left")
    x.to_parquet(OUT / f"stage0_old_rows{tag}.parquet", index=False)
    print(x.groupby(["season", "tour", "tid", "source", x["s0_match_id"].notna()]).size().to_string())


if __name__ == "__main__":
    main()
