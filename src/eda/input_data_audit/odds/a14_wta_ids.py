"""Task 5 (outside the odds): WTA main-tour matches from June 2026 whose player ids are first seen on/after 25 May 2026
(cold-started players) in the 30 Sep and 7 Oct Stage 0, and the market-Elo gap on the frame's rows by month.
Output: out/a14_wta_ids.json
"""
import json

import numpy as np
import pandas as pd

from _common import NEW, OLD, OUTD, logit

res = {}
for lab, base in (("30sep", OLD), ("7oct", NEW)):
    mp = pd.read_parquet(base / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name"])
    s = pd.read_parquet(base / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_date", "level", "qualifying"])
    x = mp.merge(s, on="match_id")
    first = x.groupby("player_id")["tournament_date"].min()
    w = x[(x["tour"] == "wta") & (x["tournament_date"] >= "2026-06-01") & (~x["qualifying"]) & x["level"].isin(["GS", "T1000", "T500", "T250"])]
    res[lab] = {"wta_main_player_rows_from_june_2026": int(len(w)),
                "with_id_first_seen_from_2026-05-25": int((w["player_id"].map(first) >= pd.Timestamp("2026-05-25")).sum())}
D = pd.read_parquet(OUTD / "a03_joined.parquet")
D = D[D["p_elo"].notna() & (D["tour"] == "wta") & (D["season"] == 2026)].copy()
mp = pd.read_parquet(OLD / "stage0_match_players.parquet", columns=["match_id", "player_id"])
s = pd.read_parquet(OLD / "stage0_matches.parquet", columns=["match_id", "tournament_date"])
first = mp.merge(s, on="match_id").groupby("player_id")["tournament_date"].min()
D["new_id"] = (D["player_a_id"].map(first) >= pd.Timestamp("2026-05-25")) | (D["player_b_id"].map(first) >= pd.Timestamp("2026-05-25"))
D["gap"] = np.abs(logit(D["p_mkt"]) - logit(np.clip(D["p_elo"], 1e-6, 1 - 1e-6)))
D["month"] = pd.to_datetime(D["td_date"]).dt.strftime("%Y-%m")
res["frame_wta_2026_rows_with_cold_started_player"] = int(D["new_id"].sum())
res["gap_by_month_and_new_id"] = D.groupby(["month", "new_id"])["gap"].agg(["size", "mean"]).round(3).reset_index().to_dict("records")
(OUTD / "a14_wta_ids.json").write_text(json.dumps(res, indent=1, default=str))
print(json.dumps(res, indent=1, default=str))
