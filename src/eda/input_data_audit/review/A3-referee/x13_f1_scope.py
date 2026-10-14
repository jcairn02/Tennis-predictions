"""F1: the exact scope rows in the live Stage 0 (7 Oct), the fix simulated, Stage 0's checks re-run.

Writes f1_scope.csv (one row per player row of the 30 events' main draws with a box in Stage 0) and prints the counts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

ev = pd.read_csv(rc.AUD / "box_wta2015_events.csv", parse_dates=["tournament_date"])
events = ev[ev["in_fault"]][["tournament_date", "tournament_name"]]
print(f"events in_fault: {len(events)}; player rows claimed: {int(ev.loc[ev['in_fault'], 'rows'].sum())}")

m, p = rc.stage0()
mm = m[m["tour"].eq("wta") & m["year"].eq(2015) & ~m["qualifying"]]
mm = mm.merge(events, on=["tournament_date", "tournament_name"])
print("Stage 0 matches of the 30 events:", len(mm), "levels:", mm["level"].value_counts().to_dict(),
      "sources:", mm["source"].value_counts().to_dict(), "box:", mm["has_box"].value_counts().to_dict())
print(mm.groupby("box_status").size().to_string())

# raw rows of these matches
raw = pd.read_parquet(rc.SACK / "wta" / "wta_matches_2015.parquet")
raw_idx = raw.set_index(["_source_file", "_row"])
pl = p[p["match_id"].isin(mm["match_id"])].merge(mm[["match_id", "tournament_name", "tournament_date", "round", "score",
                                                     "status", "status_detail", "source_file", "source_row", "format"]],
                                                 on="match_id")
pl["raw_side"] = ""
for side, who in (("w", "winner"), ("l", "loser")):
    rid = raw_idx.loc[list(zip(pl["source_file"], pl["source_row"])), f"{who}_id"].astype(str).to_numpy()
    pl.loc[("wta:" + pd.Series(rid, index=pl.index)).eq(pl["player_id"]), "raw_side"] = side
print("player rows:", len(pl), "raw side found:", pl["raw_side"].ne("").sum())
for b in rc.BOX:
    vals = []
    for (sf, r_), s in zip(zip(pl["source_file"], pl["source_row"]), pl["raw_side"]):
        vals.append(raw_idx.loc[(sf, r_), f"{s}_{rc.SRC[b]}"] if s else np.nan)
    pl[f"raw_{b}"] = rc.num(pd.Series(vals, index=pl.index).astype("string"))
hb = pl[pl["has_box"]]
same = np.all([hb[b].fillna(-1).eq(hb[f"raw_{b}"].fillna(-1)).to_numpy(dtype=bool) for b in rc.BOX], axis=0)
print(f"rows with a Stage 0 box: {len(hb)}; Stage 0 counts equal the raw counts on {int(same.sum())}")
nb = pl[~pl["has_box"]]
print(f"rows without a Stage 0 box: {len(nb)}; of which raw box full: "
      f"{int(nb[[f'raw_{b}' for b in rc.BOX[:6]]].notna().all(axis=1).sum())}")
print(nb[["match_id", "player_name", "round", "score", "status_detail"] + [f"raw_{b}" for b in rc.BOX]].head(20).to_string())

# simulate on the matches with a box: both rows fixed together
mid = hb["match_id"].unique()
both = pl[pl["match_id"].isin(mid)].copy()
W = both[both["won"]].set_index("match_id")
L = both[~both["won"]].set_index("match_id")
L = L.loc[W.index]
wb, lb = W[[f"raw_{b}" for b in rc.BOX]].set_axis(rc.BOX, axis=1), L[[f"raw_{b}" for b in rc.BOX]].set_axis(rc.BOX, axis=1)
short = W["format"].eq("short_sets")
before = rc.box_checks(wb, lb, W["score"], W["status"], W["status_detail"], short)
wf, lf = wb.copy(), lb.copy()
wf["svpt"] = wf["svpt"] + wf["df"]
lf["svpt"] = lf["svpt"] + lf["df"]
after = rc.box_checks(wf, lf, W["score"], W["status"], W["status_detail"], short)
print("\nmatches simulated:", len(W))
print("before: has_box (replica)", int(before["has_box"].sum()), "| stage0_build.box_scores", int(before["has_box_stage0"].sum()))
print("after:  has_box (replica)", int(after["has_box"].sum()), "| stage0_build.box_scores", int(after["has_box_stage0"].sum()))
print("failed checks after:", after[["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]].sum().to_dict())
print("replica == stage0 after:", bool((after["has_box"] == after["has_box_stage0"]).all()))
defb = pd.concat([rc.definition_fails(wb), rc.definition_fails(lb)])
defa = pd.concat([rc.definition_fails(wf), rc.definition_fails(lf)])
print(f"definition test failures (player rows): before {int(defb.sum())}, after {int(defa.sum())}")
# points per game before/after (B9 margin)
from_score = rc.score_parts(W["score"], short, None, W["status"])
ppg_b = (wb["svpt"] + lb["svpt"]) / (from_score["games_w"] + from_score["games_l"] - from_score["std_tb"])
ppg_a = (wf["svpt"] + lf["svpt"]) / (from_score["games_w"] + from_score["games_l"] - from_score["std_tb"])
print(f"serve points per game (non-tiebreak games): before median {ppg_b.median():.2f}, after {ppg_a.median():.2f}")

# MCP agreement after the fix, on the scope rows
j = pd.read_csv(rc.OUT / "f1_mcp_rows.csv", parse_dates=["tdate"])
j = j[j["in_window"] & j["tourney_name"].ne("Doha")][["_source_file", "_row", "side", "serve_pts", "dfs", "verdict"]]
out = pl[pl["has_box"]].copy()
out["svpt_new"] = out["raw_svpt"] + out["raw_df"]
out = out.merge(j.rename(columns={"side": "raw_side", "_source_file": "source_file", "_row": "source_row"}),
                on=["source_file", "source_row", "raw_side"], how="left")
print(f"\nscope rows with an MCP chart: {int(out['serve_pts'].notna().sum())}; svpt_new == MCP: "
      f"{int((out['svpt_new'] == out['serve_pts']).sum())}; svpt_old == MCP: {int((out['svpt'] == out['serve_pts']).sum())}")
print(out["verdict"].value_counts().to_string())
out["def_fail_before"] = rc.definition_fails(out.rename(columns={}))
res = out[["match_id", "player_id", "player_name", "tournament_name", "tournament_date", "round", "source_file",
           "source_row", "raw_side", "svpt", "df", "svpt_new", "first_in", "second_won", "def_fail_before", "serve_pts",
           "verdict"]].rename(columns={"source_file": "_source_file", "source_row": "_row", "svpt": "svpt_old",
                                       "serve_pts": "mcp_serve_pts", "verdict": "mcp_verdict"})
mt = after.reset_index()[["match_id", "has_box", "has_box_stage0"]].rename(
    columns={"has_box": "passes_B0_B9_after", "has_box_stage0": "stage0_box_scores_keeps_after"})
res = res.merge(mt, on="match_id", how="left")
res.to_csv(rc.OUT / "f1_scope.csv", index=False)
print(f"wrote f1_scope.csv: {len(res)} player rows, {res['match_id'].nunique()} matches; "
      f"all pass after: {bool(res['passes_B0_B9_after'].all())}")
print(res.groupby("tournament_name").size().sort_values().head(40).to_string())
