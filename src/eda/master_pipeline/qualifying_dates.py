"""How well the linker's estimate of a qualifying match's main-draw start hits the date training gives its event
(master pipeline process log, Part 8; src/pipeline/qualifying.main_draw_start).

Stage 0 dates an event by its main draw's first date (stage0_build, rule C05), qualifying included; before the main
draw is played, a live run's Stage 0 takes the date the linker estimates (live_rows' event_main_date). For every
tour-level and Slam qualifying match of 2025-2026 in the active instance's build tree, both tours, every source:
    the match's day        the instance timeline's observed day (obs)
    the previous edition   the same tour and event code a year earlier (its Stage 0 id: YYYY-code, a split id's
                           first two parts, the lower-level feed's W-WTAID-code), its main-draw date in Stage 0
    the estimate           main_draw_start(the day, Slam or not, that date)
    the truth              the match's Stage 0 tournament_date, the date training read
Writes data/studies/master_pipeline/qualifying_replay/main_date_check.csv (one row per match) and .json (the shares).
Run: ./python.sh src/eda/master_pipeline/qualifying_dates.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import qualifying as Q  # noqa: E402

TREE = Path("C:/Users/zerom/tnr_tpl1021")            # template_2026-10-21b's build tree (selected_instance.json)
OUT = ROOT / "data" / "studies" / "master_pipeline" / "qualifying_replay"
LEVELS = ("GS", "T1000", "T500", "T250")


def code_of(tid: str) -> str | None:
    """An event's code from its Stage 0 id: 2026-9410, 2026-5014-20261005, 2026-W-WTAID-2092-2026."""
    m = re.search(r"WTAID-(\d+)", tid) or re.match(r"^\d{4}-([^-]+)", tid)
    return m.group(1) if m else None


def main() -> int:
    m = pd.read_parquet(TREE / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "tournament_id", "tournament_date",
                                 "tournament_name", "round", "source"])
    t = pd.read_parquet(TREE / "data/studies/match_timing/timing.parquet", columns=["match_id", "obs", "exact"])
    m["match_id"] = m["match_id"].astype(str)
    m["code"] = m["tournament_id"].astype(str).map(code_of)
    ed = (m[~m["qualifying"].astype(bool)].groupby(["tour", "year", "code"])["tournament_date"]
          .agg(lambda s: s.mode().iloc[0]))                          # each edition's main-draw date
    q = m[m["qualifying"].astype(bool) & m["level"].isin(LEVELS) & m["year"].isin([2025, 2026])].merge(
        t.astype({"match_id": str}), on="match_id", how="left")
    q = q[q["obs"].notna()].copy()
    q["day"] = pd.to_datetime(q["obs"].to_numpy(dtype="float64"), unit="D").normalize()
    prev = [ed.get((tr, int(y) - 1, c)) for tr, y, c in zip(q["tour"], q["year"], q["code"])]
    q["previous_date"] = pd.to_datetime(pd.Series(prev, index=q.index))
    q["estimate"] = [Q.main_draw_start(d, lv == "GS", p) for d, lv, p in zip(q["day"], q["level"], q["previous_date"])]
    q["truth"] = pd.to_datetime(q["tournament_date"])
    q["error_days"] = (q["estimate"] - q["truth"]).dt.days
    q["abs_error"] = q["error_days"].abs()
    q.drop(columns=["obs"]).to_csv(OUT / "main_date_check.csv", index=False)

    def shares(g: pd.DataFrame) -> dict:
        return {"matches": int(len(g)), "editions": int(g["tournament_id"].nunique()),
                "exact": round(float((g["abs_error"] == 0).mean()), 4),
                "within_1_day": round(float((g["abs_error"] <= 1).mean()), 4),
                "within_2_days": round(float((g["abs_error"] <= 2).mean()), 4),
                "median_abs": float(g["abs_error"].median()), "max_abs": int(g["abs_error"].max()),
                "with_previous_edition": round(float(g["previous_date"].notna().mean()), 4)}
    out = {"all": shares(q)}
    for keys, g in q.groupby(["tour", "level"]):
        out["|".join(map(str, keys))] = shares(g)
    for keys, g in q.groupby(["year"]):
        out[f"season {keys[0] if isinstance(keys, tuple) else keys}"] = shares(g)
    worst = (q[q["abs_error"] > 1].groupby(["tour", "tournament_name", "tournament_id"])
             .agg(matches=("match_id", "size"), truth=("truth", "first"), estimate=("estimate", "first"),
                  error_days=("error_days", "first")).reset_index())
    out["editions_off_by_more_than_a_day"] = json.loads(worst.to_json(orient="records", date_format="iso"))
    (OUT / "main_date_check.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "editions_off_by_more_than_a_day"}, indent=1))
    print(worst.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
