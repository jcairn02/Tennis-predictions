"""Counting only (no result read): the frozen frame's matches per tour and season, and per calendar week, for the
forward test's sizing in the P7 plan (section 6.3). Reads match_id, tour, season and the tournament date of the 67,226
frame matches; writes p7_plan/frame_weeks.csv and prints a summary.

Run: ./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/frame_weeks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("C:/Users/zerom/Documents/Tennis-predictions")
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as C  # noqa: E402

OUT = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "p7_plan"


def main() -> int:
    cols = ["match_id", "tour", "season", "tournament_date", "date"]     # never a_won or any input
    import pyarrow.parquet as pq
    names = set(pq.read_schema(C.FRAME).names)
    use = [c for c in cols if c in names]
    f = pd.read_parquet(C.FRAME, columns=use)
    if "tournament_date" not in f.columns:
        m = C.load_matches(columns=["tournament_date"])
        f = f.merge(m[["match_id", "tournament_date"]], on="match_id", how="left")
    f["d"] = pd.to_datetime(f["tournament_date"])
    f["tour"] = f["tour"].astype(str)
    by_season = f.groupby(["tour", "season"]).size().rename("matches").reset_index()
    # calendar weeks with at least one match, per tour and season; and the mean per calendar week over full seasons
    f["week"] = f["d"].dt.to_period("W-SUN")
    wk = f.groupby(["tour", "season", "week"]).size().rename("matches").reset_index()
    full = [2021, 2022, 2023, 2024, 2025]
    rows = []
    for tour, g in wk[wk["season"].isin(full)].groupby("tour"):
        per_season = g.groupby("season")["matches"].sum()
        weeks_with_play = g.groupby("season")["week"].nunique()
        rows.append({"tour": tour, "seasons": f"{full[0]}-{full[-1]}",
                     "matches_per_season_mean": round(float(per_season.mean()), 1),
                     "weeks_with_play_mean": round(float(weeks_with_play.mean()), 1),
                     "matches_per_week_with_play": round(float(per_season.mean() / weeks_with_play.mean()), 1),
                     "matches_per_calendar_week": round(float(per_season.mean() / 52.18), 1)})
    summ = pd.DataFrame(rows)
    # the months: how much of a season is played after mid-November (the decision is expected about mid-November 2026)
    f["month"] = f["d"].dt.month
    month = (f[f["season"].isin(full)].groupby(["tour", "month"]).size() / len(full)).rename("matches_per_season")
    out = {"by_season": by_season.to_dict("records"), "summary": summ.to_dict("records"),
           "by_month_mean_2021_2025": month.reset_index().to_dict("records")}
    (OUT / "frame_weeks.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    wk.to_csv(OUT / "frame_weeks.csv", index=False)
    print(by_season.pivot(index="season", columns="tour", values="matches").to_string())
    print(summ.to_string(index=False))
    print(month.unstack(0).round(1).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
