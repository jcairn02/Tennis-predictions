"""R1-rederive (round 2): Stage 0's raw rows of Roland Garros 2019-2026, as the build reads them.

Reads every source row with the build's own loader, once: stage0_build.normalise(stage0_build.load_raw()). Keeps the
rows of Roland Garros (Sackmann's tournament id <year>-520; Tennis My Life's rows found by name, listed below) of
2019-2026, both tours, every round, with the key apply_box_overrides looks a row up by (source, tour, tid, round, wkey,
lkey) and the nine counts as read, before Stage 0's checks. Adds, from the live Stage 0 tables, the match id, box status
and source of the match each raw row became (joined on source file and row), and the rows of the key that would
collide (an override must find exactly one row of its source).

Writes data/studies/rg_first_serve_recount/followup/review/R1-rederive/work/stage0_rg_rows.parquet
       and work/stage0_rg_matches.parquet (the live Stage 0 matches of RG 2019-2026, with their player rows' boxes).
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/stage0_rows.py
"""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive" / "work"
COUNTS = list(C.BOX_SOURCE_NAMES.values())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = B.load_raw()
    print("raw rows", len(raw))
    df = B.normalise(raw)
    del raw
    gc.collect()
    season = df["season"].astype("float")
    in_years = season.between(2019, 2026)
    sack_rg = df["source"].eq("sackmann") & df["tid"].str.fullmatch(r"20(19|2[0-6])-520")
    name = df["tourney_name"].str.lower()
    tml_rg = df["source"].eq("tml") & in_years & name.str.contains("roland|french open|paris", regex=True)
    # what TML calls its RG rows, for the record
    print("TML candidate names:", df.loc[tml_rg, ["tour", "group", "tourney_name", "tid", "season"]]
          .value_counts().to_string())
    keep = (sack_rg | tml_rg) & in_years
    cols = ["rid", "source", "group", "tour", "season", "tid", "tourney_id", "tourney_name", "tourney_date", "round",
            "match_num", "winner_id", "loser_id", "winner_name", "loser_name", "wkey", "lkey", "pair", "score",
            "best_of", "minutes", "winner_ioc", "loser_ioc", "winner_seed", "loser_seed", "winner_entry", "loser_entry",
            "winner_rank", "loser_rank", "winner_age", "loser_age", "_source_file", "_row"] + \
        [f"{s}_{c}" for s in "wl" for c in COUNTS]
    rg = df.loc[keep, cols].copy()
    # the key apply_box_overrides uses, and how many rows of the same source carry it (anywhere in the raw rows)
    key_all = df["source"] + "|" + df["tour"] + "|" + df["tid"] + "|" + df["round"] + "|" + df["wkey"] + "|" + df["lkey"]
    counts = key_all[df["tid"].isin(set(rg["tid"]))].value_counts()
    del df, key_all
    gc.collect()
    rg["ov_key"] = rg["source"] + "|" + rg["tour"] + "|" + rg["tid"] + "|" + rg["round"] + "|" + rg["wkey"] + "|" + \
        rg["lkey"]
    rg["ov_key_rows"] = rg["ov_key"].map(counts).fillna(0).astype(int)
    for c in [f"{s}_{k}" for s in "wl" for k in COUNTS]:
        rg[c] = B.num(rg[c])
    # the live Stage 0 match each raw row became
    m = pd.read_parquet(C.MATCHES, columns=["match_id", "tour", "year", "round", "qualifying", "tournament_id",
                                            "tournament_name", "status", "status_detail", "score", "has_box",
                                            "box_status", "source", "tml_link", "source_file", "source_row",
                                            "player_a_id", "player_b_id", "a_won"])
    m_rg = m[m["tournament_id"].isin(set(rg["tid"])) | m["source_file"].isin(set(rg["_source_file"]))
             & m["source_row"].isin(set(rg["_row"]))].copy()
    m_rg = m_rg[m_rg["year"].between(2019, 2026)]
    rg = rg.merge(m_rg[["source_file", "source_row", "match_id", "has_box", "box_status", "status_detail"]]
                  .rename(columns={"source_file": "_source_file", "source_row": "_row", "match_id": "s0_match_id",
                                   "has_box": "s0_has_box", "box_status": "s0_box_status",
                                   "status_detail": "s0_status_detail"}),
                  on=["_source_file", "_row"], how="left")
    rg.to_parquet(OUT / "stage0_rg_rows.parquet", index=False)
    mp = pd.read_parquet(C.MATCH_PLAYERS)
    mp = mp[mp["match_id"].isin(set(m_rg["match_id"]))]
    mp.to_parquet(OUT / "stage0_rg_match_players.parquet", index=False)
    m_rg.to_parquet(OUT / "stage0_rg_matches.parquet", index=False)
    print(rg.groupby(["season", "source", "tour", rg["round"].str.startswith("Q")]).size().to_string())
    print("rows whose override key is not unique in its source:", int((rg["ov_key_rows"] != 1).sum()))
    print("raw rows not found in the live Stage 0 table:", int(rg["s0_match_id"].isna().sum()))
    print(rg[rg["s0_match_id"].isna()].groupby(["season", "source", "tour"]).size().to_string())


if __name__ == "__main__":
    main()
