"""Task 2/3: does any season's market read differently against references that do not come from tennis-data?
Per tour x season on the frame: share of matches where the market favourite is the better-ranked player, the correlation
of the market's log-odds with Elo's, the mean gap, and the market's log loss relative to Elo's.
Output: out/a11_season_consistency.csv
"""
import numpy as np
import pandas as pd

from _common import OUTD, logit

D = pd.read_parquet(OUTD / "a03_joined.parquet")
D = D[D["p_elo"].notna()]
D["zm"] = logit(D["p_mkt"])
D["ze"] = logit(np.clip(D["p_elo"], 1e-6, 1 - 1e-6))
y = D["a_won"].astype(float)
D["ll_m"] = -(y * np.log(D["p_mkt"]) + (1 - y) * np.log(1 - D["p_mkt"]))
D["ll_e"] = -(y * np.log(D["p_elo"]) + (1 - y) * np.log(1 - D["p_elo"]))
both = D["rank_a"].notna() & D["rank_b"].notna() & (D["rank_a"] != D["rank_b"]) & (D["p_mkt"] != 0.5)
D["fav_better_ranked"] = np.where(both, (D["p_mkt"] > .5) == (D["rank_a"] < D["rank_b"]), np.nan)
g = D.groupby(["tour", "season"])
out = pd.DataFrame({"n": g.size(), "fav_better_ranked": g["fav_better_ranked"].mean(),
                    "corr_logit_mkt_elo": g.apply(lambda x: np.corrcoef(x["zm"], x["ze"])[0, 1]),
                    "mean_abs_gap": g.apply(lambda x: (x["zm"] - x["ze"]).abs().mean()),
                    "logloss_mkt": g["ll_m"].mean(), "logloss_elo": g["ll_e"].mean()}).reset_index()
out["mkt_minus_elo_ll"] = out["logloss_mkt"] - out["logloss_elo"]
out.to_csv(OUTD / "a11_season_consistency.csv", index=False)
print(out.round(4).to_string())
