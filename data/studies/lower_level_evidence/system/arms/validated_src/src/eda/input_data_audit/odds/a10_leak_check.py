"""Task 5: do some 'closing' prices already know the result (captured in play)? Checks on the model frame:
    * market vs Elo disagreement sets: is the market right more often than its own probability says?
    * retirements: calibration of the market on matches that ended in retirement vs completed ones
    * rows where every book is extreme (>= 0.95) but Elo says the match was competitive
Outputs (out/): a10_leak_check.json, a10_extreme_vs_elo.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from _common import OUTD, logit

pd.set_option("display.width", 250)
D = pd.read_parquet(OUTD / "a03_joined.parquet")
y = D["a_won"].astype(float).to_numpy()
p = D["p_mkt"].to_numpy(dtype=float)
pe = np.clip(D["p_elo"].to_numpy(dtype=float), 1e-6, 1 - 1e-6)
pw = np.where(y == 1, p, 1 - p)          # market's probability of the actual winner
ew = np.where(y == 1, pe, 1 - pe)        # Elo's
fav = np.maximum(p, 1 - p)
out = {}
gap = logit(p) - logit(pe)
for thr in (1.5, 2.0, 2.5):
    m = np.abs(gap) >= thr
    mk_right = ((p > .5) == (y == 1))[m]
    out[f"disagree_logit_ge_{thr}"] = {"n": int(m.sum()), "market_fav_won": round(float(mk_right.mean()), 4),
                                         "market_fav_expected": round(float(fav[m].mean()), 4),
                                         "z": round(float((mk_right.sum() - fav[m].sum()) / np.sqrt((fav[m] * (1 - fav[m])).sum())), 2)}
for st in ("completed", "retired"):
    m = (D["status"] == st).to_numpy()
    out[f"status_{st}"] = {"n": int(m.sum()), "logloss": round(float(-np.log(pw[m]).mean()), 4),
                           "logloss_expected": round(float(-(p[m] * np.log(p[m]) + (1 - p[m]) * np.log(1 - p[m])).mean()), 4),
                           "fav_win_rate": round(float(((p[m] > .5) == (y[m] == 1)).mean()), 4),
                           "mean_fav_p": round(float(fav[m].mean()), 4),
                           "share_winner_p_ge_0.95": round(float((pw[m] >= .95).mean()), 4)}
ext = D[(pw >= 0.95) & (ew <= 0.6)].copy()
ext["p_winner_mkt"] = pw[(pw >= 0.95) & (ew <= 0.6)]
ext["p_winner_elo"] = ew[(pw >= 0.95) & (ew <= 0.6)]
ext[["match_id", "tabpfn_split", "tournament_name", "round", "status", "score", "td_winner", "td_loser", "rank_a", "rank_b",
     "avg_a", "avg_b", "ps_a", "ps_b", "b365_a", "b365_b", "p_winner_mkt", "p_winner_elo"]].to_csv(OUTD / "a10_extreme_vs_elo.csv", index=False)
out["winner_p_ge_0.95_but_elo_le_0.6"] = int(len(ext))
rev = D[(pw <= 0.05) & (ew >= 0.4)]
out["loser_p_ge_0.95_but_elo_winner_ge_0.4"] = int(len(rev))
(OUTD / "a10_leak_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
print(ext[["match_id", "tabpfn_split", "tournament_name", "round", "status", "score", "td_winner", "td_loser", "rank_a", "rank_b",
           "avg_a", "avg_b", "b365_a", "b365_b", "p_winner_mkt", "p_winner_elo"]].round(3).to_string())
print(rev[["match_id", "tabpfn_split", "tournament_name", "round", "status", "score", "td_winner", "td_loser", "rank_a", "rank_b",
           "avg_a", "avg_b", "b365_a", "b365_b", "p_mkt", "p_elo"]].round(3).to_string())
