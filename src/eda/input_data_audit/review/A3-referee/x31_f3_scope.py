"""F3 scope files from x30_f3.py's f3_adelaide2_matches.csv.

f3a_scope.csv  the 38 Adelaide 2 2022 matches whose box equals an Adelaide 2021 box: both player rows, blank.
f3b_scope.csv  the same rows with the WTA API's counts for that player (37 matches), or blank (the walkover);
               plus the post-replacement checks (B0-B9, games identity) and the API result string.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

A = pd.read_csv(rc.OUT / "f3_adelaide2_matches.csv")
raw = pd.read_parquet(rc.SACK / "wta" / "wta_matches_2022.parquet")
q = pd.read_parquet(rc.SACK / "wta" / "wta_matches_qual_itf_2022.parquet")
raw = pd.concat([raw, q], ignore_index=True).set_index(["_source_file", "_row"])
m, p = rc.stage0()
api = rc.wta_api_totals()
api = api[(api["tournament_id"] == "2030") & (api["year"] == "2022")]

copies = A[A["copy_of_2021"].fillna("").ne("")]
print("copied matches:", len(copies))
rows_a, rows_b = [], []
for _, r in copies.iterrows():
    rr = raw.loc[(r["_source_file"], r["_row"])]
    s0 = m[(m["source_file"] == r["_source_file"]) & (m["source_row"] == r["_row"])]
    mid = s0["match_id"].iloc[0] if len(s0) else None
    status = s0["status"].iloc[0] if len(s0) else ""
    for side, who in (("w", "winner"), ("l", "loser")):
        pid = f"wta:{rr[f'{who}_id']}"
        base = {"match_id": mid, "player_id": pid, "player_name": rr[f"{who}_name"], "round": r["round"],
                "score": r["score"], "_source_file": r["_source_file"], "_row": r["_row"], "raw_side": side,
                "copied_from_2021": r["copy_of_2021"]}
        rows_a.append({**base, "operation": "blank all nine counts (box missing)"})
        held = bool(r["api_box_held"]) and bool(r["api_box_passes_B0_B9"]) if pd.notna(r["api_box_passes_B0_B9"]) else False
        rep = {f"new_{b}": (r[f"api_{side}_{b}"] if held else np.nan) for b in rc.BOX}
        rows_b.append({**base, "operation": "replace the nine counts with the WTA API's" if held else
                       "blank (the WTA API holds no statistics: walkover)", **rep})
fa, fb = pd.DataFrame(rows_a), pd.DataFrame(rows_b)

# post-replacement simulation per match (F3b)
sim = []
for mid, g in fb[fb["operation"].str.startswith("replace")].groupby("match_id"):
    s0 = m[m["match_id"] == mid].iloc[0]
    w = g[g["raw_side"] == "w"].iloc[0]
    l_ = g[g["raw_side"] == "l"].iloc[0]
    # Stage 0 winner may differ from the raw winner (rule D5); order by Stage 0's winner for the identity
    pw = p[(p["match_id"] == mid) & p["won"]].iloc[0]
    pl = p[(p["match_id"] == mid) & ~p["won"]].iloc[0]
    W_ = w if pw["player_id"] == w["player_id"] else l_
    L_ = l_ if pw["player_id"] == w["player_id"] else w
    wb = pd.DataFrame([{b: W_[f"new_{b}"] for b in rc.BOX}])
    lb = pd.DataFrame([{b: L_[f"new_{b}"] for b in rc.BOX}])
    c = rc.box_checks(wb, lb, pd.Series([s0["score"]]), pd.Series([s0["status"]]), pd.Series([s0["status_detail"]]))
    ident = rc.games_identity(pd.Series([pw["games_won_n"]]), pd.Series([pl["games_won_n"]]), wb, lb,
                              pd.Series([pw["tb_won_n"] if pd.notna(pw["tb_won_n"]) else 0]),
                              pd.Series([pl["tb_won_n"] if pd.notna(pl["tb_won_n"]) else 0]))
    pwon, plost = rc.points_won(wb, lb)
    res = api[(api["pk"].isin([rc.name_key(pw["player_name"])]) | api["ok"].isin([rc.name_key(pw["player_name"])]))]
    sim.append({"match_id": mid, "passes_B0_B9": bool(c["has_box"][0]), "stage0_box_scores_keeps": bool(c["has_box_stage0"][0]),
                "identity_both": bool(ident["both_fit"][0]) if pd.notna(pw["games_won_n"]) else None,
                "winner_more_points": bool(pwon[0] > plost[0])})
sim = pd.DataFrame(sim)
fb = fb.merge(sim, on="match_id", how="left")
fa.to_csv(rc.OUT / "f3a_scope.csv", index=False)
fb.to_csv(rc.OUT / "f3b_scope.csv", index=False)
print("F3a rows:", len(fa), "matches:", fa["match_id"].nunique(), "missing match_id:", int(fa["match_id"].isna().sum()))
print("F3b replaced rows:", int(fb["operation"].str.startswith("replace").sum()), "blanked rows:",
      int(fb["operation"].str.startswith("blank").sum()))
print("F3b after replacement: passes B0-B9", int(sim["passes_B0_B9"].sum()), "of", len(sim),
      "| identity both", int(sim["identity_both"].fillna(False).sum()), "| winner more points",
      int(sim["winner_more_points"].sum()))
print(sim[~sim["identity_both"].fillna(True) | ~sim["winner_more_points"]].to_string())
