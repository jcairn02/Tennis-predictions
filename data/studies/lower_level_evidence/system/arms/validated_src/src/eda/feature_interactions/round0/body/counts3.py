"""Round 0, body-and-schedule brainstormer: last prevalence counts (no outcome read).

* main-tour 250/500 matches in the 8 days before a Grand Slam's first main-draw day, with a top-20 player;
* age bands of main-tour player-matches;
* matches at high-altitude venues (name match).

Target rows: main-tour main draws (GS, T1000, T500, T250, FIN), 2013-2021 and 2022-2024.
Run: ./python.sh src/eda/feature_interactions/round0/body/counts3.py
Writes: data/studies/feature_interactions/round0/body/counts3.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
S0 = ROOT / "data/studies/predictability_diagnostic"
TM = ROOT / "data/studies/match_timing/timing.parquet"
OUT = ROOT / "data/studies/feature_interactions/round0/body"
MAIN = {"GS", "T1000", "T500", "T250", "FIN"}
HIGH = r"(?i)bogot|quito|gstaad|guadalaj"   # above about 1,000 m
MID = r"(?i)kitzb|madrid"                   # about 650-760 m


def main() -> None:
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "round", "tournament_id",
                                 "tournament_name"])
    m = m[(m["year"] <= 2024) & (m["year"] >= 2012)]
    m = m.merge(pd.read_parquet(TM, columns=["match_id", "obs"]), on="match_id", how="left")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "rank", "age"])
    gs = m[(m["level"] == "GS") & ~m["qualifying"]].groupby(["tour", "tournament_id"])["obs"].min().reset_index()
    tgt = m[m["level"].isin(MAIN) & ~m["qualifying"] & (m["year"] >= 2013)].copy()
    tgt["window"] = np.where(tgt["year"] <= 2021, "2013-2021", "2022-2024")
    # days to the next Slam main-draw start of the same tour
    nxt = np.full(len(tgt), np.nan)
    for tour, x in tgt.groupby("tour"):
        starts = np.sort(gs.loc[gs["tour"] == tour, "obs"].to_numpy())
        i = np.searchsorted(starts, x["obs"].to_numpy(), side="right")
        ok = i < len(starts)
        v = np.full(len(x), np.nan)
        v[ok] = starts[i[ok]] - x["obs"].to_numpy()[ok]
        nxt[tgt.index.get_indexer(x.index)] = v
    tgt["days_to_slam"] = nxt
    best = p.groupby("match_id")["rank"].min().rename("best_rank")
    tgt = tgt.join(best, on="match_id")
    res: dict = {}
    for (tour, win), x in tgt.groupby(["tour", "window"]):
        small = x["level"].isin(["T250", "T500"])
        pre = small & (x["days_to_slam"] <= 8)
        res[f"{tour}|{win}"] = {
            "matches": int(len(x)),
            "250_500_within_8d_before_slam": int(pre.sum()),
            "...with_a_top20_player": int((pre & (x["best_rank"] <= 20)).sum()),
            "250_500_with_a_top10_player_any_week": int((small & (x["best_rank"] <= 10)).sum()),
            "high_altitude_matches": int(x["tournament_name"].str.contains(HIGH, regex=True).sum()),
            "mid_altitude_matches": int(x["tournament_name"].str.contains(MID, regex=True).sum()),
        }
    pm = p.merge(tgt[["match_id", "tour", "window"]], on="match_id")
    for (tour, win), x in pm.groupby(["tour", "window"]):
        res[f"{tour}|{win}"]["age_band_share"] = (pd.cut(x["age"], [0, 20.99, 23.99, 29.99, 32.99, 60],
                                                         labels=["<=20", "21-23", "24-29", "30-32", "33+"])
                                                  .value_counts(normalize=True).round(4).to_dict())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "counts3.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
