"""Task 3/4 detail on the model frame rows (from out/a03_joined.parquet):
    * rows whose average-odds probability disagrees with Pinnacle by more than 0.10, with B365 and Max as referees
    * rows where an average quote exceeds the maximum quote (impossible for a true average)
    * the five flagged events, the Elo/rank reversals and the both-ranks-disagree rows

Outputs (out/): a04_pinnacle_disagree.csv, a04_avg_gt_max.csv, a04_flagged_events_rows.csv, a04_rank_mismatch.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from _common import OUTD

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 60)
D = pd.read_parquet(OUTD / "a03_joined.parquet")


def devig(a, b):
    return (1 / a) / (1 / a + 1 / b)


D["p_ps"] = devig(D["ps_a"], D["ps_b"])
D["p_b365"] = devig(D["b365_a"], D["b365_b"])
D["p_max"] = devig(D["max_a"], D["max_b"])
D["d_ps"] = (D["p_mkt"] - D["p_ps"])
D["d_b365"] = (D["p_mkt"] - D["p_b365"])
D["d_max"] = (D["p_mkt"] - D["p_max"])
show = ["match_id", "tabpfn_split", "tournament_name", "round", "td_date", "td_winner", "td_loser", "a_won", "rank_a", "rank_b",
        "avg_a", "avg_b", "max_a", "max_b", "ps_a", "ps_b", "b365_a", "b365_b", "p_mkt", "p_ps", "p_b365", "p_max", "p_elo"]

# 1. disagreement with Pinnacle
dis = D[D["d_ps"].abs() > 0.10].copy()


def verdict(r):
    """Which quote is the odd one out: the average (if B365 and Max side with Pinnacle) or Pinnacle."""
    refs = [r["p_b365"], r["p_max"]]
    refs = [x for x in refs if np.isfinite(x)]
    if not refs:
        return "no referee"
    near_ps = sum(abs(x - r["p_ps"]) < abs(x - r["p_mkt"]) for x in refs)
    if near_ps == len(refs):
        return "average is the outlier"
    if near_ps == 0:
        return "pinnacle is the outlier"
    return "split"


dis["verdict"] = dis.apply(verdict, axis=1)
dis = dis.sort_values("d_ps", key=np.abs, ascending=False)
dis[show + ["d_ps", "verdict"]].to_csv(OUTD / "a04_pinnacle_disagree.csv", index=False)
print("rows |p_mkt - p_ps| > 0.10:", len(dis), dis["verdict"].value_counts().to_dict(),
      dis.groupby(["verdict", "tabpfn_split"]).size().to_dict())
print(dis[show + ["d_ps", "verdict"]].round(3).to_string())

# rows with no Pinnacle: use B365 and Max
nops = D[D["p_ps"].isna()]
d2 = nops[(nops["d_b365"].abs() > 0.15) & (nops["d_max"].abs() > 0.15)]
print("\nrows without Pinnacle:", len(nops), "| average disagrees with both B365 and Max by > 0.15:", len(d2))
print(d2[show + ["d_b365", "d_max"]].round(3).to_string())

# 2. average above maximum
tol = 0.011
gt = D[((D["avg_a"] > D["max_a"] + tol) | (D["avg_b"] > D["max_b"] + tol))].copy()
gt["excess_a"] = gt["avg_a"] - gt["max_a"]
gt["excess_b"] = gt["avg_b"] - gt["max_b"]
gt[show + ["excess_a", "excess_b"]].to_csv(OUTD / "a04_avg_gt_max.csv", index=False)
print("\nframe rows with an average quote above the max quote (+0.011):", len(gt), gt.groupby("tabpfn_split").size().to_dict())
print(gt[show + ["excess_a", "excess_b"]].round(3).to_string())

# 3. flagged events
ev = pd.read_csv(OUTD / "a03_events_flagged.csv")
rows = D.merge(ev[["tour", "season", "tournament_id"]], on=["tour", "season", "tournament_id"])
rows["fav_rank_better"] = np.where(rows["p_mkt"] > .5, rows["rank_a"] < rows["rank_b"], rows["rank_b"] < rows["rank_a"])
rows[show + ["fav_won", "fav_rank_better", "link", "same_set_scores", "rank_agrees_a", "rank_agrees_b"]].to_csv(
    OUTD / "a04_flagged_events_rows.csv", index=False)
for (t, s, tid), g in rows.groupby(["tour", "season", "tournament_name"]):
    print(f"\n== {t} {s} {tid}: n={len(g)} fav won {int(g['fav_won'].sum())}; fav better-ranked {int(g['fav_rank_better'].sum())};"
          f" |p_mkt-p_ps|>0.05: {int((g['d_ps'].abs() > .05).sum())}; rank_agree both true: "
          f"{int((g['rank_agrees_a'].fillna(False) & g['rank_agrees_b'].fillna(False)).sum())}; links {g['link'].value_counts().to_dict()}")
    print(g[["round", "td_winner", "td_loser", "a_won", "rank_a", "rank_b", "avg_a", "avg_b", "ps_a", "ps_b", "p_mkt", "p_elo",
             "fav_won"]].round(3).to_string())

# 4. rank mismatch on both sides, Elo reversals
rm = D[(D["rank_agrees_a"] == False) & (D["rank_agrees_b"] == False)].copy()  # noqa: E712
rm[show + ["link", "same_set_scores"]].to_csv(OUTD / "a04_rank_mismatch.csv", index=False)
print("\nboth ranks disagree:", len(rm), rm.groupby(["tour", "season"]).size().to_dict())
print(rm[show + ["link", "same_set_scores"]].head(70).round(3).to_string())
