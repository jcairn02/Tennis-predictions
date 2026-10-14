"""R1 researcher scratch: outcome-free availability counts.

1. Box-score availability (Stage 0 `has_box`, a data flag) by level and year: main tour, Challenger, ITF, both tours.
   Also the share with tiebreak counts present (`tb_won_d` non-null), seasons <= 2024 only, because the number of
   tiebreaks played is derived from the score.
2. Presence (non-null only; values not read) of a Flashscore end time for main-tour main-draw matches, by year.

Run: ./python.sh data/studies/unpriced_leads/team/researcher/scripts/coverage_box_end.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1] / "coverage_box_end.json"


def main() -> None:
    m = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "has_box"])
    res: dict = {}
    m["lvl"] = m["level"].where(~m["qualifying"].astype(bool), m["level"] + "Q")
    grp = m[m.level.isin(["GS", "T1000", "T500", "T250", "FIN", "CH", "ITF"])]
    tab = grp.groupby(["tour", "lvl", "year"])["has_box"].mean().round(3)
    res["has_box_share"] = {f"{t}|{l}": tab.loc[(t, l)].to_dict() for t, l in tab.index.droplevel(2).unique()}
    # tiebreak-count presence, <= 2024 only
    mp = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_match_players.parquet",
                         columns=["match_id", "tb_won_d"])
    mm = m[m.year <= 2024][["match_id", "tour", "year", "lvl"]].merge(mp, on="match_id", how="left")
    mm["tb_present"] = mm["tb_won_d"].notna()
    t2 = mm[mm.lvl.isin(["GS", "T1000", "T500", "T250", "CH"])].groupby(["tour", "lvl"])["tb_present"].mean().round(3)
    res["tb_count_present_share_le2024"] = {f"{a}|{b}": float(v) for (a, b), v in t2.items()}
    # Flashscore end-time presence for main-tour main draw (values not read)
    link = pd.read_parquet(ROOT / "data/studies/match_timing/links/flashscore.parquet", columns=["match_id", "source_key"])
    rec = pd.read_parquet(ROOT / "data/studies/match_timing/links/flashscore_records.parquet",
                          columns=["fs_match_id", "end_utc"])
    rec["has_end"] = rec["end_utc"].notna()
    link = link.merge(rec[["fs_match_id", "has_end"]], left_on="source_key", right_on="fs_match_id", how="left")
    main_ = m[m.level.isin(["GS", "T1000", "T500", "T250", "FIN"]) & (~m.qualifying.astype(bool))][["match_id", "tour", "year"]]
    main_ = main_.merge(link[["match_id", "has_end"]].drop_duplicates("match_id"), on="match_id", how="left")
    main_["has_end"] = main_["has_end"].fillna(False).astype(bool)
    t3 = main_.groupby(["year", "tour"])["has_end"].mean().unstack().round(3)
    res["flashscore_end_present_main_tour"] = {str(k): v for k, v in t3.to_dict(orient="index").items()}
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str)[:7000])


if __name__ == "__main__":
    main()
