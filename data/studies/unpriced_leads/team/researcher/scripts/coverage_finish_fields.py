"""R1 researcher scratch: are TennisLive's finish-time fields real, and how complete are Stage 0's minutes?

Presence only (values are not read for 2025-26): share of TennisLive listings whose `finished_at`, `duration` and
`observed_finished_at` hold a real value (not '', '0', None), by start year; share of main-tour main-draw matches with
Stage 0 `minutes` present, by year and tour.

Run: ./python.sh data/studies/unpriced_leads/team/researcher/scripts/coverage_finish_fields.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1] / "coverage_finish_fields.json"


def main() -> None:
    d = pd.read_parquet(ROOT / "data/dump/points/tennislive/listed.parquet",
                        columns=["discipline", "start_utc", "finished_at", "duration", "observed_finished_at"])
    d["yr"] = d["start_utc"].astype(str).str[:4]
    res: dict = {"tennislive_rows": int(len(d))}
    for c in ("finished_at", "duration", "observed_finished_at"):
        v = d[c].astype(str).str.strip()
        real = ~v.isin(["", "0", "None", "nan", "NaT", "0.0"])
        res[f"tennislive_{c}_real_share"] = round(float(real.mean()), 5)
        res[f"tennislive_{c}_real_share_by_year"] = d.assign(r=real).groupby("yr")["r"].mean().round(4).to_dict()
    m = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                        columns=["tour", "year", "level", "qualifying", "minutes"])
    mm = m[m.level.isin(["GS", "T1000", "T500", "T250", "FIN"]) & (~m.qualifying.astype(bool))]
    t = mm.assign(p=mm.minutes.notna()).groupby(["year", "tour"])["p"].mean().unstack().round(3)
    res["stage0_minutes_present_main_tour"] = {str(k): v for k, v in t.to_dict(orient="index").items()}
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
