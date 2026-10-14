"""R1 researcher scratch: outcome-free coverage counts for partial-information sources.

Reads no result column. Counts, for main-tour main-draw matches (Stage 0 levels GS, T1000, T500, T250, FIN),
how many have a clock start time (start_utc) in any match-timing link file, by year and tour; and how many
Flashscore records carry an end time. Also counts doubles listings in TennisLive's event listings.

Run: ./python.sh data/studies/unpriced_leads/team/researcher/scripts/coverage_clock.py
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1] / "coverage_clock.json"


def main() -> None:
    m = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying"])
    main_ = m[m.level.isin(["GS", "T1000", "T500", "T250", "FIN"]) & (~m.qualifying.astype(bool))].copy()
    res: dict = {"main_tour_main_draw_rows": int(len(main_)), "by_source": {}}
    ids: set = set()
    for f in sorted(glob.glob(str(ROOT / "data/studies/match_timing/links/*.parquet"))):
        name = Path(f).stem
        if name in ("flashscore_ambiguous", "flashscore_records"):
            continue
        import pyarrow.parquet as pq
        if "start_utc" not in pq.read_schema(f).names:
            res["by_source"][name] = {"rows_with_start_utc": 0, "note": "no start_utc column"}
            continue
        d = pd.read_parquet(f, columns=["match_id", "start_utc"])
        d = d[d.start_utc.notna()]
        res["by_source"][name] = {"rows_with_start_utc": int(len(d)),
                                  "main_tour_matches": int(main_.match_id.isin(d.match_id).sum())}
        ids |= set(d.match_id)
    main_["clock"] = main_.match_id.isin(ids)
    tab = main_.groupby(["year", "tour"])["clock"].mean().unstack().round(3)
    res["share_with_clock_by_year_tour"] = {str(k): v for k, v in tab.to_dict(orient="index").items()}
    r = pd.read_parquet(ROOT / "data/studies/match_timing/links/flashscore_records.parquet",
                        columns=["start_utc", "end_utc"])
    res["flashscore_records"] = {"rows": int(len(r)), "with_end_utc": int(r.end_utc.notna().sum())}
    # doubles in TennisLive's event listings (outcome-free: only counts of listed rows by kind)
    p = ROOT / "data/dump/points/tennislive/listed.parquet"
    if p.exists():
        cols = pd.read_parquet(p).columns.tolist()
        res["tennislive_listed_columns"] = cols
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1)[:4000])


if __name__ == "__main__":
    main()
