"""Round 0, body-and-schedule brainstormer: further prevalence counts (no outcome of the current match is read).

* on-site matches before this one (same tournament id, qualifying included): the A/B difference;
* a team-tie match (level TEAM) in the 14 days before;
* the previous match went the distance (deciding set) and the rest before this one;
* season-to-date matches by month, and age.

Target rows: main-tour main draws (GS, T1000, T500, T250, FIN), 2013-2021 and 2022-2024.
Run: ./python.sh src/eda/feature_interactions/round0/body/counts2.py
Writes: data/studies/feature_interactions/round0/body/counts2.json
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


def main() -> None:
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "round", "best_of",
                                 "tournament_id", "status", "order", "draw_size"])
    m = m[m["year"] <= 2024]
    m = m.merge(pd.read_parquet(TM, columns=["match_id", "obs"]), on="match_id", how="left")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "sets_won_d", "age"])
    d = p.merge(m, on="match_id").sort_values(["player_id", "order"]).reset_index(drop=True)
    played = d["status"].isin(["completed", "retired"])
    d = d[played].copy()
    g = d.groupby("player_id", sort=False)
    d["onsite_before"] = d.groupby(["player_id", "tournament_id"], sort=False).cumcount()
    d["prev_sets"] = g["sets_won_d"].shift(1)
    d["prev_best_of"] = g["best_of"].shift(1)
    d["prev_obs"] = g["obs"].shift(1)
    d["prev_tid"] = g["tournament_id"].shift(1)
    d["rest"] = d["obs"] - d["prev_obs"]
    d["prev_decider"] = d["prev_sets"] == d["prev_best_of"]
    # team tie within the 14 days before (by obs day), player's own order
    team = (d["level"] == "TEAM").to_numpy()
    obs = d["obs"].to_numpy()
    flag = np.zeros(len(d), dtype=bool)
    for _, idx in d.groupby("player_id", sort=False).indices.items():
        o = obs[idx]
        tcum = np.concatenate([[0], np.cumsum(team[idx])])
        lo = np.searchsorted(o, o - 14, side="left")
        ar = np.arange(len(idx))
        flag[idx] = (tcum[ar] - tcum[lo]) > 0
    d["team_14d"] = flag
    d["season_matches_before"] = d.groupby(["player_id", "year"], sort=False).cumcount()
    tgt = d[d["level"].isin(MAIN) & ~d["qualifying"] & (d["year"] >= 2013)].copy()
    tgt["window"] = np.where(tgt["year"] <= 2021, "2013-2021", "2022-2024")
    res: dict = {}
    pair = tgt.groupby("match_id").agg(n=("player_id", "size"), o1=("onsite_before", "first"),
                                       o2=("onsite_before", "last"), tour=("tour", "first"),
                                       window=("window", "first"), rnd=("round", "first"),
                                       t1=("team_14d", "first"), t2=("team_14d", "last"),
                                       d1=("prev_decider", "first"), d2=("prev_decider", "last"),
                                       r1=("rest", "first"), r2=("rest", "last"),
                                       s1=("prev_tid", "first"), s2=("prev_tid", "last"),
                                       tid=("tournament_id", "first"))
    pair = pair[pair["n"] == 2]
    pair["onsite_gap"] = (pair["o1"] - pair["o2"]).abs()
    for (tour, win), x in pair.groupby(["tour", "window"]):
        r = {"matches": int(len(x))}
        r["onsite_gap_share"] = (pd.cut(x["onsite_gap"], [-1, 0, 1, 2, 100], labels=["0", "1", "2", "3+"])
                                 .value_counts(normalize=True).round(4).to_dict())
        r["onsite_gap_ge1_not_R1_count"] = int(((x["onsite_gap"] >= 1) & ~x["rnd"].isin(["R128", "R64", "R32"])).sum())
        r["either_team_tie_14d_count"] = int((x["t1"] | x["t2"]).sum())
        both_in_event = (x["s1"] == x["tid"]) & (x["s2"] == x["tid"])
        one_decider = both_in_event & (x["d1"] != x["d2"])
        r["both_prev_in_event_share"] = round(float(both_in_event.mean()), 4)
        r["in_event_exactly_one_prev_went_to_decider_count"] = int(one_decider.sum())
        r["...and_rest_le_1_for_the_decider_player"] = int((one_decider & (((x["d1"] == True) & (x["r1"] <= 1))  # noqa: E712
                                                                         | ((x["d2"] == True) & (x["r2"] <= 1)))).sum())  # noqa: E712
        res[f"{tour}|{win}"] = r
    tm = tgt.copy()
    tm["month"] = pd.to_datetime(tm["obs"], unit="D").dt.month
    res["season_matches_before_median_by_month_atp_2013_2021"] = (
        tm[(tm["tour"] == "atp") & (tm["window"] == "2013-2021")].groupby("month")["season_matches_before"]
        .median().to_dict())
    res["season_matches_before_median_by_month_wta_2013_2021"] = (
        tm[(tm["tour"] == "wta") & (tm["window"] == "2013-2021")].groupby("month")["season_matches_before"]
        .median().to_dict())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "counts2.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
